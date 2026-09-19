/* Live Interview: real interview room. One-click submit, compact live report, retry. */
const sid = new URLSearchParams(location.search).get("sid");
if (!sid) location.href = "/interview";
const page = buildShell("Interview", "BERREADY / Interview / Live");
const media = createMedia();
const visual = createVisualSampler();
let answered = 0, t0 = Date.now(), tick = null, submitting = false, retryMode = false;
let currentRequestId = 0;
let NQ = 5;
let _lastBlobUrl = null;
let _lastAudioEl = null;
let _visualReady = false;
let _cameraChecked = false;

page.innerHTML = `
  <div class="card mb"><div class="row"><div><div class="small dim" id="ivMeta">Preparing…</div>
    <div class="question" id="q" style="margin-top:4px">Loading your interview…</div>
    <div class="row"><button class="ghost" id="bSpeak" title="Read this question aloud">🔊 Read aloud</button></div>
    <div class="small mut" id="bridge"></div></div><span style="flex:1"></span>
    <div class="timer" id="tm" style="font-size:18px">00:00</div></div></div>
  <div class="live"><div><video class="cam" id="v" autoplay muted playsinline></video>
    <div class="statusbar"><span><span class="dot" id="dCam"></span>Camera</span>
    <span><span class="dot" id="dMic"></span>Mic</span>
    <span><span class="dot rec" id="dRec" style="display:none"></span><span id="recT">● idle</span></span>
    <span class="small dim" id="cnt"></span></div>
    <div class="row"><button id="bCam">Camera</button><button id="bMic">Mic</button></div>
    <div id="modelAnswer" class="mt" style="display:none"></div></div>
    <div><div class="card"><div class="small dim" id="ansLabel">Your answer — speak or type</div>
      <div class="transcript" id="tx" contenteditable="true">…</div>
      <div class="row mt">
        <button class="primary" id="bRecord">🎙️ Start Recording</button>
        <button class="primary" id="bStopRecord" style="display:none">■ Stop & Transcribe</button>
        <button class="primary" id="bTalk">🎤 Browser STT</button>
        <button class="primary" id="bSend">Submit answer</button>
        <button class="ghost" id="bRetryQ">Retry answer</button>
      </div>
      <div id="sttStatus" class="small mut mt"></div>
      <div id="eval" class="mt"></div></div>
      <div class="row mt"><button class="danger" id="bEnd">End interview</button></div></div></div>`;

tick = setInterval(() => { const el = document.getElementById("tm"); if (el) el.textContent = fmtDur(Date.now() - t0); }, 500);
document.getElementById("bSpeak").onclick = (e) => {
  const t = document.getElementById("q").textContent;
  if (!t || /loading|could not/i.test(t)) return;
  e.target.textContent = speakNow(t) ? "■ Stop" : "🔊 Read aloud";
};
if (prefs.get("cam", false)) toggleCam(); else document.getElementById("bCam").onclick = toggleCam;
async function toggleCam() {
  const on = await media.camera(document.getElementById("v"), !media.camOn, () => alert("Camera unavailable — continuing audio-only."));
  document.getElementById("dCam").classList.toggle("on", on);
  // Run camera check after camera turns on
  if (on && !_cameraChecked) {
    _cameraChecked = true;
    runCameraCheck();
  }
}

/* --- Camera Readiness Check --- */
async function runCameraCheck() {
  const statusEl = document.getElementById("sttStatus");
  statusEl.innerHTML = `<span class="small mut">🔍 Checking camera readiness…</span>`;
  // Load MediaPipe in background
  const loaded = await visual.loadVision();
  if (!loaded) {
    statusEl.innerHTML = `<span class="small mut">⚠ Visual analysis unavailable — proceeding without it.</span>`;
    return;
  }
  // Run check on the camera feed
  const videoEl = document.getElementById("v");
  const result = await visual.cameraCheck(videoEl);
  _visualReady = result.ready;
  if (result.issues.length === 0) {
    statusEl.innerHTML = `<span class="small mut" style="color:var(--ok)">✓ Camera ready — visual coaching enabled.</span>`;
  } else {
    const msgs = result.recommendations.map(r => `<div class="small">• ${esc(r)}</div>`).join("");
    statusEl.innerHTML = `<div style="padding:8px;background:var(--bg2);border-radius:6px;margin-top:4px">
      <div class="small" style="color:var(--warn);font-weight:600">📷 Camera suggestions:</div>
      ${msgs}
      <div class="small dim" style="margin-top:4px">Interview will continue — these are suggestions only.</div></div>`;
    _visualReady = true; // still usable
  }
  // Start visual sampling if camera is on
  if (media.camOn) {
    visual.startSampling(videoEl, 3000);
  }
}
document.getElementById("bMic").onclick = () => {
  const on = media.toggleMic(); document.getElementById("dMic").classList.toggle("on", on);
};

/* --- Recording + Server STT flow --- */
let recording = false;
document.getElementById("bRecord").onclick = async () => {
  const ok = await media.startRecording();
  if (!ok) { document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">Failed to start recording — check mic permission.</span>`; return; }
  recording = true;
  // Hide model answer when starting new recording
  const maEl = document.getElementById("modelAnswer");
  if (maEl) { maEl.style.display = "none"; maEl.innerHTML = ""; }
  document.getElementById("bRecord").style.display = "none";
  document.getElementById("bStopRecord").style.display = "";
  document.getElementById("bTalk").disabled = true;
  document.getElementById("bSend").disabled = true;
  document.getElementById("sttStatus").innerHTML = `<span class="small mut">🔴 Recording… speak now</span>`;
  document.getElementById("recT").textContent = "● recording";
  document.getElementById("dRec").style.display = "";
  document.getElementById("dRec").classList.add("rec");
};

document.getElementById("bStopRecord").onclick = async () => {
  if (!recording) return;
  recording = false;
  document.getElementById("bStopRecord").style.display = "none";
  document.getElementById("bRecord").style.display = "";
  document.getElementById("bTalk").disabled = false;
  document.getElementById("bSend").disabled = false;
  document.getElementById("sttStatus").innerHTML = `<span class="small mut">⏳ Transcribing with server Whisper…</span>`;
  document.getElementById("recT").textContent = "● transcribing";
  
  const blob = await media.stopRecording();
  let transcript = "";
  let usedFallback = false;

  // Store blob for replay — revoke old URL first
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  if (blob && blob.size > 0) {
    _lastBlobUrl = URL.createObjectURL(blob);
  }

  if (blob) {
    const result = await media.uploadRecording(blob, "en");
    transcript = result.text || "";
    usedFallback = result.fallback;
    if (result.confidence !== undefined) {
      document.getElementById("sttStatus").innerHTML = `<span class="small mut">Transcribed (confidence: ${(result.confidence * 100).toFixed(0)}%) ${usedFallback ? "⚠️ used browser fallback" : "✅ server Whisper"}</span>`;
    } else {
      document.getElementById("sttStatus").innerHTML = usedFallback
        ? `<span class="small mut">⚠️ Server STT unavailable — using browser transcript</span>`
        : `<span class="small mut">✅ Transcribed with server Whisper</span>`;
    }
  }
  
  // If server STT failed/empty, fall back to browser transcript
  if (!transcript) {
    const browserText = media.getBrowserTranscript();
    if (browserText) {
      transcript = browserText;
      usedFallback = true;
      document.getElementById("sttStatus").innerHTML = `<span class="small mut">⚠️ Using browser transcript (server STT unavailable)</span>`;
    }
  }
  
  // Append new transcription to existing text (don't erase previous input)
  const existing = document.getElementById("tx").textContent.trim();
  const hasExisting = existing && existing !== "…" && existing.length > 0;
  const finalText = hasExisting ? (existing + " " + (transcript || "")).trim() : (transcript || "…");
  document.getElementById("tx").textContent = finalText;
  document.getElementById("dRec").style.display = "none";
  document.getElementById("dRec").classList.remove("rec");
  document.getElementById("recT").textContent = "● idle";
};

document.getElementById("bTalk").onclick = (e) => media.listen(
  (t) => { document.getElementById("tx").textContent = t; document.getElementById("sttStatus").innerHTML = `<span class="small mut">🎤 Browser STT active</span>`; },
  (on) => { document.getElementById("dRec").style.display = on ? "" : "none";
    document.getElementById("recT").textContent = on ? "● listening" : "● idle";
    document.body.classList.toggle("speaking", on); e.target.textContent = on ? "■ Stop" : "🎤 Browser STT";
    // Hide model answer when starting new recording
    if (on) { const maEl = document.getElementById("modelAnswer"); if (maEl) { maEl.style.display = "none"; maEl.innerHTML = ""; } } },
  () => { document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">Microphone unavailable — type your answer.</span>`; });

document.getElementById("bRetryQ").onclick = () => {
  if (submitting) return;
  retryMode = true;
  // Hide model answer when retrying
  const maEl = document.getElementById("modelAnswer");
  if (maEl) { maEl.style.display = "none"; maEl.innerHTML = ""; }
  // Clear transcript AND browser STT memory for fresh start
  document.getElementById("tx").textContent = "";
  media.clearBrowserTranscript();
  document.getElementById("tx").focus();
  document.getElementById("ansLabel").textContent = "Your retry — improved version";
  document.getElementById("bSend").textContent = "Submit retry";
  document.getElementById("eval").innerHTML = `<span class="small mut">Lead with your main point in 10 seconds, one specific example.</span>`;
};

function setSubmitting(on, label) {
  submitting = on;
  const b = document.getElementById("bSend");
  b.disabled = on; b.textContent = label || (retryMode ? "Submit retry" : "Submit answer");
  document.getElementById("bTalk").disabled = on;
  document.getElementById("bRetryQ").disabled = on;
  document.getElementById("bEnd").disabled = on;
  document.getElementById("bRecord").disabled = on;
  document.getElementById("bStopRecord").disabled = on;
}

function reportPanel(ev, cmp, coaching, visualObs) {
  const rel = ev.relevance || {};
  const dims = ev.dimensions || {};
  const tech = ev.technical && ev.technical !== "n/a" ? `<div class="small">⚙ Technical: ${esc(ev.technical)}</div>` : "";
  const sents = (ev.sentences || []).map((s) =>
    `<div class="small">✎ <i>"${esc(s.problem)}"</i><br/>→ ${esc(s.fix)}</div>`).join("");
  const better = (ev.better_examples || []).map((b) =>
    `<div class="small">"${esc(b.text)}"<br/><span class="dim">Why stronger: ${esc(b.why)}</span></div>`).join("");
  const replayHtml = _lastBlobUrl
    ? `<button class="ghost" id="bReplay" title="Replay your recorded answer">▶ Replay answer</button>`
    : "";

  // Coaching section
  const coachingHtml = coaching ? `
    <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);border-radius:8px;padding:12px;margin-bottom:12px">
      ${coaching.appreciation ? `<div class="small" style="color:var(--ok);margin-bottom:6px"><b>💬</b> ${esc(coaching.appreciation)}</div>` : ""}
      ${coaching.priority ? `<div class="small" style="margin-bottom:6px"><b>🎯</b> ${esc(coaching.priority)}</div>` : ""}
      ${coaching.specific_feedback ? `<div class="small" style="margin-bottom:6px">${esc(coaching.specific_feedback)}</div>` : ""}
      ${coaching.improvement ? `<div class="small" style="margin-bottom:6px;color:var(--accent)"><b>✨</b> ${esc(coaching.improvement)}</div>` : ""}
      ${coaching.next_step ? `<div class="small dim">${esc(coaching.next_step)}</div>` : ""}
    </div>` : "";

  // Visual observations section
  let visualHtml = "";
  if (visualObs && visualObs.summary) {
    const s = visualObs.summary;
    const items = [];
    if (s.gaze_away_count > 0) items.push(`👁 Camera attention: looked away ${s.gaze_away_count} time${s.gaze_away_count > 1 ? "s" : ""} (${s.gaze_away_total_sec}s total)`);
    if (s.slouch_count > 0) items.push(`🧍 Posture: slouched ${s.slouch_count} time${s.slouch_count > 1 ? "s" : ""} (${s.slouch_total_sec}s total)`);
    if (s.excessive_movement_count > 0) items.push(`🔄 Movement: ${s.excessive_movement_count} excessive head movement${s.excessive_movement_count > 1 ? "s" : ""}`);
    if (s.hands_hidden_count > 0) items.push(`✋ Hands: not visible ${s.hands_hidden_count} time${s.hands_hidden_count > 1 ? "s" : ""}`);
    if (s.torso_lean_count > 0) items.push(`↔ Body: leaned ${s.torso_lean_count} time${s.torso_lean_count > 1 ? "s" : ""}`);
    if (s.shoulder_rotation_count > 0) items.push(`🔄 Shoulders: rotated ${s.shoulder_rotation_count} time${s.shoulder_rotation_count > 1 ? "s" : ""}`);
    // Gesture breakdown
    if (s.gesture_count > 0 && s.gesture_breakdown) {
      const gItems = Object.entries(s.gesture_breakdown).map(([k, v]) => `${k.replace("_", " ")}×${v}`).join(", ");
      items.push(`🤌 Gestures: ${s.gesture_count} detected (${gItems})`);
    }
    if (items.length === 0) items.push("✓ Good visual presence — stable camera attention and posture");

    const coaching_text = visualObs.coaching || "";
    const content_coaching = visualObs.content_coaching || "";
    visualHtml = `<div style="background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);border-radius:8px;padding:12px;margin-bottom:12px">
      <div class="small" style="font-weight:600;margin-bottom:6px">📷 Visual Communication</div>
      ${items.map(i => `<div class="small">${esc(i)}</div>`).join("")}
      ${coaching_text ? `<div class="small dim" style="margin-top:6px">${esc(coaching_text)}</div>` : ""}
      ${content_coaching ? `<div class="small" style="margin-top:6px;color:var(--accent)">💡 ${esc(content_coaching)}</div>` : ""}
    </div>`;
  }

  return `<div class="card quiet" style="border:1px solid var(--line-soft)">
    ${coachingHtml}
    ${visualHtml}
    <div class="row"><b>Answer feedback</b> <span class="score">${ev.score ?? "—"}/10</span>${replayHtml}</div>
    ${(ev.good || []).map((g) => `<div class="small">✓ ${esc(g)}</div>`).join("")}
    ${ev.biggest_issue ? `<div class="small">⚠ ${esc(ev.biggest_issue)}</div>` : ""}
    ${rel.note ? `<div class="small">🎯 Relevance (${esc(rel.verdict || "")}): ${esc(rel.note)}</div>` : ""}
    ${ev.interviewer_want ? `<div class="small">👔 Interviewer wanted: ${esc(ev.interviewer_want)}</div>` : ""}
    ${tech}
    ${sents ? `<div class="mt"><b class="small">Sentence formation</b>${sents}</div>` : ""}
    ${better ? `<div class="mt"><b class="small">Better way to say it</b>${better}</div>` : ""}
    <div class="small dim mt">Clarity: ${esc(dims.clarity || "—")} · Conciseness: ${esc(dims.conciseness || "—")} · Specificity: ${esc(dims.specificity || "—")}</div>
    <div class="small dim">Vocabulary: ${esc(ev.vocabulary || "—")} · Fillers: ${esc(ev.fillers || "—")}</div>
    <div class="small dim">Pacing: ${esc(ev.pacing || "—")} · Completeness: ${esc(ev.completeness || "—")}</div>
    <div class="small dim">Articulation: not enough data to evaluate · Pronunciation: not enough data to evaluate</div>
    ${cmp ? `<div class="small mt"><b>Retry comparison:</b> ${cmp.old?.score ?? "—"} → ${cmp.new?.score ?? "—"}</div>` : ""}
  </div>`;
}

document.getElementById("bSend").onclick = async () => {
  if (submitting) return;
  currentRequestId = Date.now();
  const myRequestId = currentRequestId;
  const a = document.getElementById("tx").textContent.trim();
  if (!a || a === "…") { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Empty — answer not heard. Check microphone.</span>`; return; }
  media.stopListen(); document.body.classList.remove("speaking");
  // Stop visual sampling and capture summary for this answer
  visual.stopSampling();
  const visualSummary = visual.getSummary();
  visual.clearEvents();
  setSubmitting(true, "Analyzing answer…");
  document.getElementById("eval").innerHTML = `<span class="small mut">Analyzing your answer…</span>`;
  const wasRetry = retryMode;
  try {
    // Send answer + visual data together
    const payload = { session_id: sid, answer: a, visual: visualSummary };
    const r = await (wasRetry ? api.retryInterview(sid, a) : api.answerInterview(sid, a));
    if (myRequestId !== currentRequestId) return;
    if (r.error) {
      if (r.code === "in_flight") { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Answer already being processed — please wait.</span>`; }
      else { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">${esc(r.error)}</span>`; }
      setSubmitting(false); return;
    }
    // Build visual observations for display
    const visualObs = {
      summary: visualSummary,
      coaching: r.visual_coaching || "",
      content_coaching: r.content_coaching || "",
      gesture_analysis: r.gesture_analysis || {},
    };
    if (r.answered !== undefined) answered = r.answered;
    else if (!wasRetry) answered++;
    retryMode = false;
    document.getElementById("ansLabel").textContent = "Your answer — speak or type";
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("eval").innerHTML = reportPanel(r.evaluation, wasRetry ? r : null, r.coaching, visualObs)
      + (r.retry_suggested && !wasRetry ? `<div class="row mt"><button id="bRetry2">🔁 ${esc(r.retry_instruction || "Retry this answer")}</button></div>` : "");
    const rb = document.getElementById("bRetry2");
    if (rb) rb.onclick = () => document.getElementById("bRetryQ").click();
    // Wire replay button — plays the original recording blob
    const replayBtn = document.getElementById("bReplay");
    if (replayBtn && _lastBlobUrl) {
      replayBtn.onclick = () => {
        if (_lastAudioEl && !_lastAudioEl.paused) { _lastAudioEl.pause(); _lastAudioEl = null; replayBtn.textContent = "▶ Replay answer"; return; }
        _lastAudioEl = new Audio(_lastBlobUrl);
        _lastAudioEl.onended = () => { replayBtn.textContent = "▶ Replay answer"; };
        _lastAudioEl.play();
        replayBtn.textContent = "■ Stop replay";
      };
    }
    // Show model answer below camera buttons (left column)
    const maEl = document.getElementById("modelAnswer");
    if (r.model_answer) {
      maEl.style.display = "";
      maEl.innerHTML = `<div class="card quiet" style="border:1px solid rgba(52,211,153,0.3);background:rgba(52,211,153,0.05)">
        <div class="small" style="color:var(--ok);font-weight:600;margin-bottom:6px">📝 Model Answer (8-9/10)</div>
        <div class="small" style="line-height:1.5">${esc(r.model_answer)}</div></div>`;
    } else {
      maEl.style.display = "none";
      maEl.innerHTML = "";
    }
    document.getElementById("tx").textContent = "";
    media.clearBrowserTranscript();
    document.getElementById("cnt").textContent = `Question ${answered} of ${NQ}`;
    // Stop if at question limit (backend says so, or frontend count matches).
    if (r.at_limit || (!wasRetry && answered >= NQ)) { endInterview(); return; }
    document.getElementById("q").textContent = r.next_question;
    document.getElementById("sttStatus").innerHTML = "";
    // Restart visual sampling for the next answer
    if (media.camOn) {
      visual.startSampling(document.getElementById("v"), 3000);
    }
    setSubmitting(false);
  } catch { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Server unreachable — your answer was not sent. Try once more.</span>`; setSubmitting(false); }
};

async function endInterview() {
  clearInterval(tick); media.stopListen();
  // Clean up blob URLs
  if (_lastAudioEl) { try { _lastAudioEl.pause(); } catch {} _lastAudioEl = null; }
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  try { await api.finishInterview(sid); } catch {}
  location.href = `/report?sid=${sid}`;
}
document.getElementById("bEnd").onclick = endInterview;
(async () => {
  try {
    const d = await api.sessionDetail(sid);
    if (d.error) { document.getElementById("q").textContent = "Session not found."; return; }
    const pending = (d.turns || []).find((t) => t.question && !t.answer);
    const first = (d.turns || []).find((t) => t.question);
    answered = (d.turns || []).filter((t) => t.answer).length;
    NQ = d.meta?.num_questions || 5;
    document.getElementById("q").textContent = (pending || first)?.question || "Tell me about yourself.";
    document.getElementById("ivMeta").textContent =
      `${d.meta?.role || "Candidate"} · ${d.meta?.type || ""} · ${d.meta?.difficulty || ""}`;
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ~${NQ}`;
  } catch { document.getElementById("q").textContent = "Could not load — is the server running?"; }
})();