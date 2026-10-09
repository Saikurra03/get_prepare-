/* Live Interview: clean flow — question → answer → next question. All feedback at the end. */
const sid = new URLSearchParams(location.search).get("sid");
if (!sid) location.href = "/interview";
document.body.classList.add("il-root");
document.body.classList.add("immersive");
const media = createMedia();
const visual = createVisualSampler();
let answered = 0, t0 = Date.now(), tick = null, submitting = false;
let NQ = 5;
let _lastBlobUrl = null;
let _lastAudioEl = null;
let _autoRead = prefs.get("autoRead", true);

/* Immersive full-viewport room — no app shell (Zoom/Meet-style). */
document.body.innerHTML = `
<div class="immersive">
  <header class="immersive-topbar">
    <span class="immersive-brand">BERREADY</span>
    <span class="immersive-mode">Live interview</span>
    <span class="immersive-spacer"></span>
    <span class="immersive-pill" id="ivAI">AI…</span>
    <span class="immersive-pill" id="cnt">Question 1 of 5</span>
    <span class="immersive-timer" id="tm">00:00</span>
    <button class="icon-btn immersive-theme" id="bTheme" title="Switch theme">☾</button>
    <button class="danger immersive-exit" id="bEnd">End interview</button>
  </header>
  <div class="immersive-body">
    <section class="immersive-stage">
      <div class="immersive-q-label">Interviewer</div>
      <div class="immersive-q" id="q">Loading your interview…</div>
      <div class="immersive-bridge small mut" id="bridge"></div>
      <div class="row immersive-read">
        <button class="ghost immersive-stt" id="bSpeak" title="Read this question aloud">🔊 Read aloud</button>
        <label class="small dim" style="display:flex;align-items:center;gap:4px;cursor:pointer">
          <input type="checkbox" id="cbAutoRead" ${_autoRead ? "checked" : ""} style="margin:0"/> Auto-read
        </label>
      </div>
      <div class="immersive-meta" id="ivMeta">Preparing…</div>
    </section>
    <aside class="immersive-side">
      <video class="immersive-video" id="v" autoplay muted playsinline></video>
      <div class="immersive-status">
        <span><span class="dot" id="dCam"></span>Camera</span>
        <span><span class="dot" id="dMic"></span>Mic</span>
        <span><span class="dot rec" id="dRec" style="display:none"></span><span id="recT">● idle</span></span>
      </div>
      <div class="row"><button id="bCam">Camera</button><button id="bMic">Mic</button></div>
      <div class="immersive-hint">Speak or type your answer below — nothing is shown mid-interview;
        all coaching lands in the final report.</div>
    </aside>
  </div>
  <footer class="immersive-foot">
    <div class="immersive-ansrow">
      <div class="immersive-ans">
        <div class="small dim" id="ansLabel">Your answer — speak or type</div>
        <div class="immersive-tx" id="tx" contenteditable="true">…</div>
      </div>
      <div class="immersive-ctrls">
        <button class="primary" id="bRecord">🎙️ Start Recording</button>
        <button class="primary" id="bStopRecord" style="display:none">■ Stop & Transcribe</button>
        <button class="primary" id="bTalk">🎤 Browser STT</button>
        <button class="primary" id="bSend">Submit answer</button>
        <button class="ghost" id="bSkip" title="Skip this question">⏭ Skip</button>
        <button class="ghost" id="bChangeTopic" title="Switch to a different topic">🔄 New Topic</button>
      </div>
    </div>
    <div class="immersive-status">
      <span id="sttStatus" class="small mut"></span>
      <span id="statusMsg" class="small"></span>
    </div>
  </footer>
</div>`;

if (window.theme) theme.mount(document.getElementById("bTheme"));

/* --- AI status pill (same behaviour as the shell's, self-hosted) --- */
async function refreshAI() {
  const el = document.getElementById("ivAI");
  if (!el) return;
  try {
    const st = await api.status();
    el.textContent = st.ai_ready ? `${st.active_provider || "AI"} ready` : "AI offline";
  } catch { el.textContent = "server unreachable"; }
}
refreshAI(); setInterval(refreshAI, 20000);

tick = setInterval(() => { const el = document.getElementById("tm"); if (el) el.textContent = fmtDur(Date.now() - t0); }, 500);

/* --- Auto-read toggle --- */
document.getElementById("cbAutoRead").onchange = (e) => { _autoRead = e.target.checked; prefs.set("autoRead", _autoRead); };

/* --- Read aloud --- */
document.getElementById("bSpeak").onclick = (e) => {
  const t = document.getElementById("q").textContent;
  if (!t || /loading|could not/i.test(t)) return;
  e.target.textContent = speakNow(t) ? "■ Stop" : "🔊 Read aloud";
};

function autoReadQuestion() {
  if (!_autoRead) return;
  const t = document.getElementById("q").textContent;
  if (!t || /loading|could not/i.test(t)) return;
  setTimeout(() => speakNow(t), 300);
}

/* --- Camera --- */
document.getElementById("bCam").onclick = toggleCam;
if (prefs.get("cam", false)) toggleCam();
async function toggleCam() {
  const on = await media.camera(document.getElementById("v"), !media.camOn, () => alert("Camera unavailable — continuing audio-only."));
  document.getElementById("dCam").classList.toggle("on", on);
  if (on) visual.startSampling(document.getElementById("v"), 3000);
  else visual.stopSampling();
}
document.getElementById("bMic").onclick = () => {
  const on = media.toggleMic(); document.getElementById("dMic").classList.toggle("on", on);
};

/* --- Visual sampling lifecycle (per question) --- */
function collectVisual() {
  // Snapshot the current question's visual data for the backend, then reset.
  visual.stopSampling();
  const payload = { events: visual.getEvents(), summary: visual.getSummary() };
  visual.clearEvents();
  return payload;
}
function resumeVisual() {
  if (media.camOn) visual.startSampling(document.getElementById("v"), 3000);
}
function dropVisual() {
  // Discard visual data for a skipped/changed question and re-arm for the next one.
  visual.stopSampling();
  visual.clearEvents();
}

/* --- Recording + Server STT flow --- */
let recording = false;
document.getElementById("bRecord").onclick = async () => {
  const ok = await media.startRecording();
  if (!ok) { document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">Failed to start recording — check mic permission.</span>`; return; }
  recording = true;
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
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  if (blob && blob.size > 0) { _lastBlobUrl = URL.createObjectURL(blob); }
  if (blob) {
    const result = await media.uploadRecording(blob, "en");
    transcript = result.text || "";
    const took = result.ms ? ` in ${(result.ms / 1000).toFixed(1)}s` : "";
    if (result.confidence !== undefined) {
      document.getElementById("sttStatus").innerHTML = `<span class="small mut">Transcribed (${(result.confidence * 100).toFixed(0)}%)${took} ${result.fallback ? "⚠️ browser fallback" : "✅ server Whisper"}</span>`;
    }
  }
  if (!transcript) {
    const browserText = media.getBrowserTranscript();
    if (browserText) { transcript = browserText; }
  }
  const existing = document.getElementById("tx").textContent.trim();
  const hasExisting = existing && existing !== "…" && existing.length > 0;
  document.getElementById("tx").textContent = hasExisting ? (existing + " " + (transcript || "")).trim() : (transcript || "…");
  document.getElementById("dRec").style.display = "none";
  document.getElementById("dRec").classList.remove("rec");
  document.getElementById("recT").textContent = "● idle";
  if (transcript) {
    document.getElementById("sttStatus").innerHTML = `<span style="color:var(--ok)">✅ Transcript ready — edit if needed, then Submit</span>`;
  } else {
    document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">No speech detected — type your answer or record again.</span>`;
  }
};

document.getElementById("bTalk").onclick = (e) => {
  const t = document.getElementById("q").textContent;
  if (!t || /loading|could not/i.test(t)) return;
  e.target.textContent = speakNow(t) ? "■ Stop" : "🔊 Read aloud";
  media.listen(
    (t) => { document.getElementById("tx").textContent = t; document.getElementById("sttStatus").innerHTML = `<span class="small mut">🎤 Browser STT active</span>`; },
    (on) => { document.getElementById("dRec").style.display = on ? "" : "none";
      document.getElementById("recT").textContent = on ? "● listening" : "● idle";
      document.body.classList.toggle("speaking", on); e.target.textContent = on ? "■ Stop" : "🎤 Browser STT"; },
    () => { document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">Microphone unavailable — type your answer.</span>`; });
};

function setSubmitting(on, label) {
  submitting = on;
  const b = document.getElementById("bSend");
  b.disabled = on; b.textContent = label || "Submit answer";
  document.getElementById("bTalk").disabled = on;
  document.getElementById("bSkip").disabled = on;
  document.getElementById("bChangeTopic").disabled = on;
  document.getElementById("bEnd").disabled = on;
  document.getElementById("bRecord").disabled = on;
  document.getElementById("bStopRecord").disabled = on;
}

function showStatus(msg, type) {
  const el = document.getElementById("statusMsg");
  const color = type === "ok" ? "var(--ok)" : type === "warn" ? "var(--warn)" : "var(--dim, #999)";
  el.innerHTML = `<span style="color:${color}">${esc(msg)}</span>`;
}

/* --- Submit answer --- */
document.getElementById("bSend").onclick = async () => {
  if (submitting) return;
  const a = document.getElementById("tx").textContent.trim();
  if (!a || a === "…") { showStatus("Empty — answer not heard. Check microphone.", "warn"); return; }
  media.stopListen(); document.body.classList.remove("speaking");
  const visualPayload = collectVisual();
  setSubmitting(true, "Submitting…");
  showStatus("Saving your answer — next question coming up…", "dim");
  try {
    const r = await api.answerInterview(sid, a, visualPayload);
    if (r.error) { showStatus(r.error, "warn"); setSubmitting(false); return; }
    if (r.answered !== undefined) answered = r.answered;
    document.getElementById("tx").textContent = "";
    media.clearBrowserTranscript();
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ${NQ}`;
    // If at limit, end interview
    if (r.at_limit || !r.next_question) {
      showStatus("Interview complete! Preparing your report…", "ok");
      setSubmitting(false);
      endInterview();
      return;
    }
    // Show bridge transition, then next question
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("q").textContent = r.next_question;
    document.getElementById("ansLabel").textContent = "Your answer — speak or type";
    document.getElementById("sttStatus").innerHTML = "";
    showStatus("", "dim");
    setSubmitting(false);
    resumeVisual();
    autoReadQuestion();
  } catch { showStatus("Server unreachable — try once more.", "warn"); setSubmitting(false); }
};

/* --- Skip question --- */
document.getElementById("bSkip").onclick = async () => {
  if (submitting) return;
  setSubmitting(true, "Skipping…");
  media.stopListen(); document.body.classList.remove("speaking");
  dropVisual();
  try {
    const r = await api.skipInterview(sid);
    if (r.error) { showStatus(r.error, "warn"); setSubmitting(false); return; }
    if (r.answered !== undefined) answered = r.answered;
    document.getElementById("tx").textContent = "";
    media.clearBrowserTranscript();
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ${NQ}`;
    if (r.at_limit || !r.next_question) {
      showStatus("Interview complete!", "ok");
      setSubmitting(false);
      endInterview();
      return;
    }
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("q").textContent = r.next_question;
    showStatus("Question skipped.", "dim");
    setSubmitting(false);
    resumeVisual();
    autoReadQuestion();
  } catch { showStatus("Server unreachable.", "warn"); setSubmitting(false); }
};

/* --- Change topic --- */
document.getElementById("bChangeTopic").onclick = async () => {
  if (submitting) return;
  setSubmitting(true, "Changing topic…");
  media.stopListen(); document.body.classList.remove("speaking");
  dropVisual();
  try {
    const r = await api.changeTopicInterview(sid);
    if (r.error) { showStatus(r.error, "warn"); setSubmitting(false); return; }
    if (r.answered !== undefined) answered = r.answered;
    document.getElementById("tx").textContent = "";
    media.clearBrowserTranscript();
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ${NQ}`;
    if (r.at_limit || !r.next_question) {
      showStatus("Interview complete!", "ok");
      setSubmitting(false);
      endInterview();
      return;
    }
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("q").textContent = r.next_question;
    showStatus("Switched to a new topic.", "dim");
    setSubmitting(false);
    resumeVisual();
    autoReadQuestion();
  } catch { showStatus("Server unreachable.", "warn"); setSubmitting(false); }
};

/* --- End interview --- */
async function endInterview() {
  clearInterval(tick); media.stopListen(); visual.stopSampling();
  if (_lastAudioEl) { try { _lastAudioEl.pause(); } catch {} _lastAudioEl = null; }
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  try { await api.finishInterview(sid); } catch {}
  location.href = `/result?sid=${sid}`;
}
document.getElementById("bEnd").onclick = endInterview;

/* --- Load session on mount --- */
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
    autoReadQuestion();
  } catch { document.getElementById("q").textContent = "Could not load — is the server running?"; }
})();