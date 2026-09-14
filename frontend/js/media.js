/* Shared camera / mic / speech helpers. Graceful when hardware is missing. */
function createMedia() {
  const m = {
    stream: null,
    camOn: false,
    micOn: false,
    rec: null,
    mediaRecorder: null,
    audioChunks: [],
    recording: false,
    browserTranscript: "",
    useServerSTT: true,
  };

  m.camera = async (videoEl, on, onErr) => {
    if (on && !m.camOn) {
      try {
        m.stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoEl.srcObject = m.stream; m.camOn = true;
      } catch { onErr && onErr("camera"); }
    } else if (!on && m.camOn) {
      m.stream?.getTracks().forEach((t) => t.stop());
      videoEl.srcObject = null; m.camOn = false;
    }
    return m.camOn;
  };

  m.toggleMic = () => { m.micOn = !m.micOn; return m.micOn; };

  m.speakSupported = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  /* --- Browser Web Speech API (fallback/real-time preview) --- */
  m.listen = (onText, onState, onError) => {
    if (m.rec) { m.rec.stop(); m.rec = null; onState(false); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { onError("unsupported"); return; }
    const rec = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    m.rec = rec; onState(true);
    m.browserTranscript = "";
    rec.onresult = (e) => {
      let t = "";
      for (const r of e.results) t += r[0].transcript + " ";
      m.browserTranscript = t.trim();
      onText(m.browserTranscript);
    };
    rec.onerror = () => { m.rec = null; onState(false); onError("mic"); };
    rec.onend = () => { m.rec = null; onState(false); };
    try { rec.start(); } catch { m.rec = null; onState(false); }
  };

  m.stopListen = () => { try { m.rec?.stop(); } catch {} m.rec = null; };

  /* --- Server-side STT with MediaRecorder --- */
  m.startRecording = async () => {
    if (m.recording) return false;
    try {
      // Request audio-only stream for recording
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      m.stream = audioStream;
      m.audioChunks = [];
      
      // Use webm/opus for good compression
      const options = { mimeType: "audio/webm;codecs=opus" };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        // Fallback for Safari
        options.mimeType = "audio/webm";
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = "";
      }
      
      m.mediaRecorder = new MediaRecorder(audioStream, options);
      
      m.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) m.audioChunks.push(e.data);
      };
      
      m.mediaRecorder.onstop = () => {
        // Recording stopped, audio is ready in m.audioChunks
      };
      
      m.mediaRecorder.start(100); // Collect data every 100ms
      m.recording = true;
      return true;
    } catch (err) {
      console.error("Failed to start recording:", err);
      return false;
    }
  };

  m.stopRecording = () => {
    return new Promise((resolve) => {
      if (!m.recording || !m.mediaRecorder) {
        resolve(null);
        return;
      }
      m.mediaRecorder.onstop = () => {
        const blob = new Blob(m.audioChunks, { type: "audio/webm" });
        m.recording = false;
        m.stream?.getTracks().forEach(t => t.stop());
        m.stream = null;
        resolve(blob);
      };
      m.mediaRecorder.stop();
    });
  };

  m.uploadRecording = async (blob, language = "en") => {
    if (!blob || blob.size === 0) return { text: "", fallback: true };
    
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    formData.append("language", "en");
    
    try {
      const response = await fetch("/api/stt/transcribe", {
        method: "POST",
        body: formData,
      });
      
      if (response.ok) {
        const data = await response.json();
        return { text: data.text || "", fallback: false, confidence: data.confidence };
      } else {
        console.warn("Server STT failed:", response.status, await response.text());
        return { text: "", fallback: true };
      }
    } catch (err) {
      console.warn("Server STT error:", err);
      return { text: "", fallback: true };
    }
  };

  m.getBrowserTranscript = () => m.browserTranscript;

  m.isRecording = () => m.recording;

  m.setUseServerSTT = (val) => { m.useServerSTT = !!val; };

  return m;
}

/* Opt-in read-aloud for a single question. Never auto-plays; toggle to stop. */
let _speaking = false;
function speakNow(text) {
  try {
    if (_speaking) { speechSynthesis.cancel(); _speaking = false; return false; }
    const u = new SpeechSynthesisUtterance(text);
    u.onend = () => { _speaking = false; const b = document.getElementById("bSpeak"); if (b) b.textContent = "🔊"; };
    speechSynthesis.cancel(); speechSynthesis.speak(u); _speaking = true; return true;
  } catch { return false; }
}