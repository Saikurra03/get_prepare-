/* Visual Sampler — MediaPipe-based face/body/hand landmark extraction.
   Runs entirely in the browser. Only structured data leaves — never raw video. */
function createVisualSampler() {
  const v = {
    faceLandmarker: null,
    poseLandmarker: null,
    handLandmarker: null,
    canvas: null,
    ctx: null,
    videoEl: null,
    sampling: false,
    sampleInterval: null,
    snapshots: [],          // [{time, face, pose, hands, observations}]
    events: [],             // [{time, type, detail, duration, context}]
    _lastGaze: null,
    _gazeStart: 0,
    _lastPosture: null,
    _postureStart: 0,
    _lastHands: null,
    _handsStart: 0,
    ready: false,
    loading: false,
  };

  /* ---- CDN loading ---- */
  const VISION_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/vision_bundle.mjs";
  const WASM_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm";

  async function loadVision() {
    if (v.ready || v.loading) return v.ready;
    v.loading = true;
    try {
      const vision = await import(VISION_CDN);
      const { FaceLandmarker, PoseLandmarker, HandLandmarker, FilesetResolver } = vision;
      const filesetResolver = await FilesetResolver.forVisionTasks(WASM_CDN);
      v.faceLandmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task", delegate: "GPU" },
        outputFaceBlendshapes: false,
        runningMode: "VIDEO",
        numFaces: 1,
      });
      v.poseLandmarker = await PoseLandmarker.createFromOptions(filesetResolver, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task", delegate: "GPU" },
        runningMode: "VIDEO",
        numPoses: 1,
      });
      v.handLandmarker = await HandLandmarker.createFromOptions(filesetResolver, {
        baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task", delegate: "GPU" },
        runningMode: "VIDEO",
        numHands: 2,
      });
      v.ready = true;
    } catch (e) {
      console.warn("MediaPipe load failed:", e);
      v.ready = false;
    }
    v.loading = false;
    return v.ready;
  }

  /* ---- Canvas setup ---- */
  function initCanvas(videoEl) {
    v.videoEl = videoEl;
    v.canvas = document.createElement("canvas");
    v.canvas.width = 320;
    v.canvas.height = 240;
    v.ctx = v.canvas.getContext("2d", { willReadFrequently: true });
  }

  function captureFrame() {
    if (!v.videoEl || !v.ctx) return null;
    const vw = v.videoEl.videoWidth || 320;
    const vh = v.videoEl.videoHeight || 240;
    v.ctx.drawImage(v.videoEl, 0, 0, v.canvas.width, v.canvas.height);
    return { timestamp: performance.now(), width: v.canvas.width, height: v.canvas.height };
  }

  /* ---- Landmark extraction ---- */
  function detectFace() {
    if (!v.faceLandmarker || !v.videoEl) return null;
    try {
      const results = v.faceLandmarker.detectForVideo(v.videoEl, performance.now());
      if (!results.faceLandmarks || !results.faceLandmarks.length) return null;
      const lm = results.faceLandmarks[0];
      return {
        landmarks: lm.length,
        nose: { x: lm[1].x, y: lm[1].y, z: lm[1].z },
        leftEye: { x: lm[33].x, y: lm[33].y, z: lm[33].z },
        rightEye: { x: lm[263].x, y: lm[263].y, z: lm[263].z },
        mouth: { x: lm[13].x, y: lm[13].y, z: lm[13].z },
        chin: { x: lm[152].x, y: lm[152].y, z: lm[152].z },
        forehead: { x: lm[10].x, y: lm[10].y, z: lm[10].z },
        faceSize: Math.abs(lm[263].x - lm[33].x),
        faceCenterX: (lm[1].x + lm[33].x + lm[263].x) / 3,
        faceCenterY: (lm[1].y + lm[33].y + lm[263].y) / 3,
        faceVisible: true,
      };
    } catch { return null; }
  }

  function detectPose() {
    if (!v.poseLandmarker || !v.videoEl) return null;
    try {
      const results = v.poseLandmarker.detectForVideo(v.videoEl, performance.now());
      if (!results.landmarks || !results.landmarks.length) return null;
      const lm = results.landmarks[0];
      const leftShoulder = lm[11];
      const rightShoulder = lm[12];
      const leftHip = lm[23];
      const rightHip = lm[24];
      const nose = lm[0];
      return {
        leftShoulder: { x: leftShoulder.x, y: leftShoulder.y },
        rightShoulder: { x: rightShoulder.x, y: rightShoulder.y },
        leftHip: { x: leftHip.x, y: leftHip.y },
        rightHip: { x: rightHip.x, y: rightHip.y },
        nose: { x: nose.x, y: nose.y },
        shoulderWidth: Math.abs(leftShoulder.x - rightShoulder.x),
        shoulderLevel: Math.abs(leftShoulder.y - rightShoulder.y),
        torsoVisible: true,
      };
    } catch { return null; }
  }

  function detectHands() {
    if (!v.handLandmarker || !v.videoEl) return null;
    try {
      const results = v.handLandmarker.detectForVideo(v.videoEl, performance.now());
      if (!results.landmarks || !results.landmarks.length) return { count: 0, hands: [] };
      const hands = results.landmarks.map((hand) => ({
        wrist: { x: hand[0].x, y: hand[0].y },
        indexTip: { x: hand[8].x, y: hand[8].y },
        thumbTip: { x: hand[4].x, y: hand[4].y },
        palmCenter: { x: (hand[0].x + hand[9].x) / 2, y: (hand[0].y + hand[9].y) / 2 },
      }));
      return { count: hands.length, hands };
    } catch { return { count: 0, hands: [] }; }
  }

  /* ---- Observation computation from landmarks ---- */
  function computeObservations(face, pose, hands, prevSnapshot) {
    const obs = {};

    // --- Gaze direction (from face landmarks) ---
    if (face) {
      const noseX = face.faceCenterX;
      if (noseX < 0.35) obs.gaze = "right";       // facing right of camera (user's left)
      else if (noseX > 0.65) obs.gaze = "left";    // facing left of camera (user's right)
      else obs.gaze = "center";                     // looking toward camera
      obs.faceVisible = face.faceVisible;
      obs.faceSize = face.faceSize;
    }

    // --- Head movement (compare with previous) ---
    if (face && prevSnapshot?.face) {
      const dx = Math.abs(face.faceCenterX - prevSnapshot.face.faceCenterX);
      const dy = Math.abs(face.faceCenterY - prevSnapshot.face.faceCenterY);
      const dz = Math.abs((face.nose.z || 0) - (prevSnapshot.face.nose.z || 0));
      obs.headMovement = dx + dy + dz;
      obs.headMoving = obs.headMovement > 0.02;
    }

    // --- Posture (from pose landmarks) ---
    if (pose) {
      obs.shoulderLevel = pose.shoulderLevel;
      obs.shoulderLevelOk = pose.shoulderLevel < 0.05;
      // Torso lean: compare shoulder center Y to hip center Y
      const shoulderCenterY = (pose.leftShoulder.y + pose.rightShoulder.y) / 2;
      const hipCenterY = (pose.leftHip.y + pose.rightHip.y) / 2;
      obs.torsoLength = hipCenterY - shoulderCenterY;
      obs.posture = obs.torsoLength > 0.3 ? "upright" : obs.torsoLength > 0.2 ? "slight_slouch" : "slouching";
      obs.torsoVisible = pose.torsoVisible;
    }

    // --- Hands visibility ---
    if (hands) {
      obs.handsVisible = hands.count;
      obs.handsInFrame = hands.count > 0;
    }

    return obs;
  }

  /* ---- Event detection from observations ---- */
  function detectEvents(obs, time, prevObs) {
    const events = [];
    const dt = prevObs ? (time - (prevObs._time || time)) / 1000 : 0;

    // Gaze away from camera
    if (obs.gaze && obs.gaze !== "center") {
      if (v._lastGaze !== "away") {
        v._lastGaze = "away";
        v._gazeStart = time;
      }
    } else {
      if (v._lastGaze === "away") {
        const dur = (time - v._gazeStart) / 1000;
        if (dur > 1.5) {
          events.push({ time: v._gazeStart, type: "gaze_away", duration: dur,
            detail: `Looked away from camera for ${dur.toFixed(1)}s` });
        }
        v._lastGaze = null;
      }
    }

    // Slouching
    if (obs.posture === "slouching") {
      if (v._lastPosture !== "slouching") {
        v._lastPosture = "slouching";
        v._postureStart = time;
      }
    } else if (obs.posture === "upright") {
      if (v._lastPosture === "slouching") {
        const dur = (time - v._postureStart) / 1000;
        if (dur > 3) {
          events.push({ time: v._postureStart, type: "slouching", duration: dur,
            detail: `Slouched for ${dur.toFixed(1)}s` });
        }
        v._lastPosture = null;
      }
    }

    // Hands not visible (if previously visible)
    if (obs.handsVisible === 0 && prevObs?.handsVisible > 0) {
      v._noHandsStart = time;
      v._lastHands = "none";
    } else if (obs.handsVisible > 0 && v._lastHands === "none") {
      const dur = (time - v._noHandsStart) / 1000;
      if (dur > 5) {
        events.push({ time: v._noHandsStart, type: "hands_hidden", duration: dur,
          detail: `Hands not visible for ${dur.toFixed(1)}s` });
      }
      v._lastHands = null;
    }

    // Head movement (excessive)
    if (obs.headMoving && obs.headMovement > 0.05) {
      events.push({ time, type: "excessive_movement", duration: 0,
        detail: "Excessive head movement detected" });
    }

    // Shoulder level (uneven)
    if (obs.shoulderLevelOk === false && obs.shoulderLevel > 0.05) {
      events.push({ time, type: "uneven_shoulders", duration: 0,
        detail: "Shoulders appear uneven" });
    }

    return events;
  }

  /* ---- Camera readiness check ---- */
  async function cameraCheck(videoEl) {
    if (!v.ready) await loadVision();
    if (!v.ready) return { ready: false, issues: ["MediaPipe not available"] };

    initCanvas(videoEl);
    const issues = [];
    const recommendations = [];

    // Sample 5 frames over 3 seconds
    for (let i = 0; i < 5; i++) {
      await new Promise(r => setTimeout(r, 600));
      captureFrame();
      const face = detectFace();
      const pose = detectPose();

      if (face) {
        // Face size check (framing)
        if (face.faceSize < 0.08) {
          issues.push("face_too_small");
          recommendations.push("Move closer to the camera so your face is clearly visible.");
        }
        if (face.faceSize > 0.5) {
          issues.push("face_too_large");
          recommendations.push("Move slightly back — your face fills too much of the frame.");
        }
        // Face position (centering)
        if (face.faceCenterX < 0.2 || face.faceCenterX > 0.8) {
          issues.push("face_off_center");
          recommendations.push("Center yourself in the camera frame.");
        }
        if (face.faceCenterY < 0.15) {
          issues.push("face_too_high");
          recommendations.push("Lower the camera slightly or sit lower.");
        }
        if (face.faceCenterY > 0.85) {
          issues.push("face_too_low");
          recommendations.push("Raise the camera slightly or sit taller.");
        }
      } else {
        issues.push("no_face");
        recommendations.push("No face detected — make sure your face is visible to the camera.");
      }

      if (pose) {
        if (pose.shoulderLevel > 0.06) {
          issues.push("uneven_shoulders");
          recommendations.push("Try to sit with shoulders level.");
        }
      }
    }

    // Lighting check via canvas brightness
    if (v.ctx) {
      const imgData = v.ctx.getImageData(0, 0, v.canvas.width, v.canvas.height);
      let totalBrightness = 0;
      const pixels = imgData.data.length / 4;
      for (let i = 0; i < imgData.data.length; i += 4) {
        totalBrightness += (imgData.data[i] + imgData.data[i+1] + imgData.data[i+2]) / 3;
      }
      const avgBrightness = totalBrightness / pixels;
      if (avgBrightness < 40) {
        issues.push("dark");
        recommendations.push("Your face appears dark — try facing a light source or turning on a lamp.");
      }
      if (avgBrightness > 220) {
        issues.push("overexposed");
        recommendations.push("The image is very bright — reduce backlighting or move away from the window.");
      }
    }

    const deduped = [...new Set(recommendations)];
    return {
      ready: issues.length === 0 || (issues.length > 0 && !issues.includes("no_face")),
      issues: [...new Set(issues)],
      recommendations: deduped,
    };
  }

  /* ---- Sampling control ---- */
  function startSampling(videoEl, intervalMs = 3000) {
    if (v.sampling) return;
    initCanvas(videoEl);
    v.sampling = true;
    v.snapshots = [];
    v.events = [];
    v._lastGaze = null;
    v._lastPosture = null;
    v._lastHands = null;

    let prevObs = null;
    v.sampleInterval = setInterval(() => {
      captureFrame();
      const face = detectFace();
      const pose = detectPose();
      const hands = detectHands();
      const obs = computeObservations(face, pose, hands, prevObs);
      obs._time = performance.now();

      const snap = { time: Date.now(), face, pose, hands, observations: obs };
      v.snapshots.push(snap);

      const newEvents = detectEvents(obs, snap.time, prevObs);
      v.events.push(...newEvents);

      prevObs = obs;
    }, intervalMs);
  }

  function stopSampling() {
    v.sampling = false;
    if (v.sampleInterval) { clearInterval(v.sampleInterval); v.sampleInterval = null; }
    // Flush any pending gaze/posture events
    const now = Date.now();
    if (v._lastGaze === "away") {
      const dur = (now - v._gazeStart) / 1000;
      if (dur > 1) v.events.push({ time: v._gazeStart, type: "gaze_away", duration: dur,
        detail: `Looked away from camera for ${dur.toFixed(1)}s` });
      v._lastGaze = null;
    }
    if (v._lastPosture === "slouching") {
      const dur = (now - v._postureStart) / 1000;
      if (dur > 2) v.events.push({ time: v._postureStart, type: "slouching", duration: dur,
        detail: `Slouched for ${dur.toFixed(1)}s` });
      v._lastPosture = null;
    }
  }

  function getSnapshots() { return v.snapshots; }
  function getEvents() { return v.events; }
  function clearEvents() { v.events = []; v.snapshots = []; }

  function getSummary() {
    const events = v.events;
    const gazeAway = events.filter(e => e.type === "gaze_away");
    const slouching = events.filter(e => e.type === "slouching");
    const movement = events.filter(e => e.type === "excessive_movement");
    const handsHidden = events.filter(e => e.type === "hands_hidden");
    const totalGazeAway = gazeAway.reduce((s, e) => s + (e.duration || 0), 0);
    const totalSlouch = slouching.reduce((s, e) => s + (e.duration || 0), 0);
    return {
      gaze_away_count: gazeAway.length,
      gaze_away_total_sec: Math.round(totalGazeAway),
      slouch_count: slouching.length,
      slouch_total_sec: Math.round(totalSlouch),
      excessive_movement_count: movement.length,
      hands_hidden_count: handsHidden.length,
      total_snapshots: v.snapshots.length,
      events: events,
    };
  }

  return {
    loadVision, initCanvas, cameraCheck,
    startSampling, stopSampling,
    getSnapshots, getEvents, clearEvents, getSummary,
    get ready() { return v.ready; },
    get loading() { return v.loading; },
    get sampling() { return v.sampling; },
  };
}
