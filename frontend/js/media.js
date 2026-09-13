/* Shared camera / mic / speech helpers. Graceful when hardware is missing. */
function createMedia() {
  const m = { stream: null, camOn: false, micOn: false, rec: null };
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
  m.listen = (onText, onState, onError) => {
    if (m.rec) { m.rec.stop(); m.rec = null; onState(false); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { onError("unsupported"); return; }
    const rec = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    m.rec = rec; onState(true);
    rec.onresult = (e) => { let t = ""; for (const r of e.results) t += r[0].transcript + " "; onText(t); };
    rec.onerror = () => { m.rec = null; onState(false); onError("mic"); };
    rec.onend = () => { m.rec = null; onState(false); };
    try { rec.start(); } catch { m.rec = null; onState(false); }
  };
  m.stopListen = () => { try { m.rec?.stop(); } catch {} m.rec = null; };
  return m;
}
