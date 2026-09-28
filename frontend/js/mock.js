/* Full-screen mock interview environment (Phase 3).
   One immersive room for all 12 modes: the 9 interview types plus the
   Public Speaking / Storytelling / Communication practice modes.
   Same interview API (plan → answer/skip/change-topic → finish), same
   media + visual modules as /interview-live — distraction-free front-end. */
const qp = new URLSearchParams(location.search);

const MODE_MAP = {
  communication: { label: "Communication Practice", focus: "Clear, confident everyday speaking — clarity, natural flow, fewer fillers." },
  story:         { label: "Storytelling Studio", focus: "A personal or professional story with a hook, stakes and a memorable ending." },
  speaking:      { label: "Public Speaking", focus: "A short speech with a strong opening, structured points and a confident closing." },
  wit:           { label: "Wit & Engagement", focus: "Playful, natural engagement — clever framing without forcing jokes." },
  qa:            { label: "Spontaneous Q&A", focus: "Fast structured answers under pressure — think, structure, speak." },
  podcast:       { label: "Podcast Studio", focus: "Conversational energy, hooks and listener focus." },
  conversation:  { label: "General Conversation", focus: "Free-form talk — stay natural, clear and engaging." },
};

const modeKey = MODE_MAP[qp.get("mode")] ? qp.get("mode") : null;
let sid = qp.get("sid");
let answered = 0, NQ = 5, submitting = false, recording = false;
let t0 = Date.now(), tick = null;
let _lastBlobUrl = null;
let _autoRead = prefs.get("autoRead", true);
const media = createMedia();
const visual = createVisualSampler();

/* ---------- Fullscreen layout (no app shell — immersive) ---------- */
document.body.innerHTML = `
<div class="mock">
  <div class="mock-top">
    <span class="mock-brand">BERREADY</span>
    <span class="mock-mode" id="mMode">${modeKey ? esc(MODE_MAP[modeKey].label) : "Mock interview"}</span>
    <span class="mock-spacer"></span>
    <span class="mock-pill" id="mAI">AI…</span>
    <span class="mock-pill" id="mSig" title="Camera signals gathered for this question">👁 0</span>
    <span class="mock-dots" id="mDots"></span>
    <span class="mock-timer" id="mTm">00:00</span>
    <button class="danger" id="bExit">Exit</button>
  </div>
  <div class="mock-body">
    <div class="mock-stage">
      <div class="mock-q-label" id="mQLabel">Interviewer</div>
      <div class="mock-q" id="q">Preparing your room…</div>
      <div class="mock-bridge" id="bridge"></div>
      <div class="mock-meta"><span id="mRole"></span></div>
    </div>
    <div class="mock-side">
      <video class="mock-video" id="v" autoplay muted playsinline></video>
      <div class="mock-status">
        <span><span class="dot" id="dCam"></span> Camera</span>
        <span><span class="dot" id="dMic"></span> Mic</span>
        <span><span class="dot rec" id="dRec" style="display:none"></span><span id="recT">idle</span></span>
        <span class="mock-spacer"></span>
        <button class="ghost" id="bCam">Camera</button>
        <button class="ghost" id="bMic">Mic</button>
      </div>
      <div class="mock-side-card">Answer out loud or type below — <b>Ctrl+Enter</b> submits.
        Nothing is shown mid-interview; all coaching lands in the final report.</div>
    </div>
  </div>
  <div class="mock-bottom">
    <div class="mock-tx" id="tx" contenteditable="true" data-ph="Your answer — speak or type…"></div>
    <div class="mock-ctrls">
      <button class="primary" id="bRecord">🎙️ Record</button>
      <button class="primary" id="bStopRecord" style="display:none">■ Stop</button>
      <button id="bTalk">🎤 Browser STT</button>
      <button class="primary" id="bSend">Submit answer</button>
      <button class="ghost" id="bSkip">⏭ Skip</button>
      <button class="ghost" id="bNew">🔄 New topic</button>
      <button class="ghost" id="bSpeak" title="Read question aloud">🔊</button>
      <label class="small dim" style="display:flex;gap:4px;align-items:center;cursor:pointer">
        <input type="checkbox" id="cbRead" ${_autoRead ? "checked" : ""} style="margin:0"/> Auto-read</label>
    </div>
  </div>
  <div class="mock-foot">
    <div class="mock-msg" id="msg"></div>
    <span class="mock-spacer"></span>
    <button class="danger" id="bEnd">End &amp; see report</button>
  </div>
</div>`;

const $ = (id) => document.getElementById(id);
const qText = (t) => { $("q").textContent = t; };

function showMsg(m, type) {
  const c = type === "ok" ? "var(--ok)" : type === "warn" ? "var(--warn)" : "var(--dim,#999)";
  $("msg").innerHTML = `<span style="color:${c}">${esc(m)}</span>`;
}
function renderCount() { $("mMode").textContent = `${modeKey ? MODE_MAP[modeKey].label : "Mock"} · Q ${Math.min(answered + 1, NQ)}/${NQ}`; }
function renderDots() {
  if (NQ > 24) { $("mDots").innerHTML = ""; return; }
  let h = "";
  for (let i = 0; i < NQ; i++) h += `<span class="mock-dot${i < answered ? " done" : i === answered ? " now" : ""}"></span>`;
  $("mDots").innerHTML = h;
}
function setSubmitting(on, label) {
  submitting = on;
  for (const id of ["bSend", "bSkip", "bNew", "bEnd", "bExit", "bRecord", "bStopRecord", "bTalk"])
    $(id).disabled = on;
  $("bSend").textContent = label || "Submit answer";
}

/* ---------- Plan the session when arriving without ?sid= ---------- */
async function ensureSession() {
  if (sid) return true;
  const body = modeKey
    ? {
        interview_type: "custom",
        difficulty: qp.get("difficulty") || prefs.get("diff", "intermediate"),
        role: `${MODE_MAP[modeKey].label} — ${MODE_MAP[modeKey].focus}` +
              (qp.get("prompt") ? ` Prompt: ${qp.get("prompt")}` : "") +
              (qp.get("topic") ? ` Topic: ${qp.get("topic")}` : ""),
        num_questions: parseInt(qp.get("n") || prefs.get("nQ", "5"), 10),
      }
    : {
        doc_ids: (qp.get("docs") || "").split(",").filter(Boolean),
        interview_type: qp.get("type") || "mixed",
        difficulty: qp.get("difficulty") || prefs.get("diff", "intermediate"),
        role: qp.get("role") || prefs.get("role", ""),
        num_questions: parseInt(qp.get("n") || prefs.get("nQ", "5"), 10),
      };
  try {
    const r = await api.planInterview(body);
    if (r.error) { showMsg(r.error, "warn"); return false; }
    sid = r.session_id;
    history.replaceState(null, "", `/mock?sid=${sid}`);
    return true;
  } catch { showMsg("Could not reach the server — is it running?", "warn"); return false; }
}

/* ---------- Camera / mic / visual lifecycle ---------- */
async function toggleCam() {
  const on = await media.camera($("v"), !media.camOn, () => alert("Camera unavailable — continuing audio-only."));
  $("dCam").classList.toggle("on", on);
  if (on) visual.startSampling($("v"), 3000);
  else visual.stopSampling();
}
function collectVisual() {
  visual.stopSampling();
  const payload = { events: visual.getEvents(), summary: visual.getSummary() };
  visual.clearEvents();
  return payload;
}
function resumeVisual() { if (media.camOn) visual.startSampling($("v"), 3000); }
function dropVisual() { visual.stopSampling(); visual.clearEvents(); }

/* ---------- Read aloud ---------- */
function autoReadQuestion() {
  if (!_autoRead) return;
  const t = $("q").textContent;
  if (!t || /preparing|loading|could not/i.test(t)) return;
  setTimeout(() => speakNow(t), 300);
}
$("cbRead").onchange = (e) => { _autoRead = e.target.checked; prefs.set("autoRead", _autoRead); };
$("bSpeak").onclick = (e) => {
  const t = $("q").textContent;
  if (!t || /preparing|loading/i.test(t)) return;
  e.target.textContent = speakNow(t) ? "■" : "🔊";
};

/* ---------- Recording + STT ---------- */
$("bRecord").onclick = async () => {
  const ok = await media.startRecording();
  if (!ok) { showMsg("Failed to start recording — check mic permission.", "warn"); return; }
  recording = true;
  $("bRecord").style.display = "none";
  $("bStopRecord").style.display = "";
  $("bTalk").disabled = true; $("bSend").disabled = true;
  $("recT").textContent = "recording";
  $("dRec").style.display = ""; $("dRec").classList.add("rec");
  showMsg("🔴 Recording… speak now", "dim");
};
$("bStopRecord").onclick = async () => {
  if (!recording) return;
  recording = false;
  $("bStopRecord").style.display = "none";
  $("bRecord").style.display = "";
  $("bTalk").disabled = false; $("bSend").disabled = false;
  $("recT").textContent = "transcribing";
  showMsg("⏳ Transcribing with server Whisper…", "dim");
  const blob = await media.stopRecording();
  let transcript = "";
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  if (blob && blob.size > 0) _lastBlobUrl = URL.createObjectURL(blob);
  if (blob) {
    const result = await media.uploadRecording(blob, "en");
    transcript = result.text || "";
    if (result.confidence !== undefined) {
      const took = result.ms ? ` in ${(result.ms / 1000).toFixed(1)}s` : "";
      showMsg(`Transcribed (${(result.confidence * 100).toFixed(0)}%)${took} — edit if needed, then Submit`, "ok");
    }
  }
  if (!transcript) transcript = media.getBrowserTranscript() || "";
  const tx = $("tx");
  const prev = tx.textContent.trim();
  const had = prev && prev !== "…";
  tx.textContent = had ? `${prev} ${transcript}`.trim() : (transcript || "");
  $("dRec").style.display = "none"; $("dRec").classList.remove("rec");
  $("recT").textContent = "idle";
  if (!transcript) showMsg("No speech detected — type your answer or record again.", "warn");
};
$("bTalk").onclick = (e) => media.listen(
  (t) => { $("tx").textContent = t; showMsg("🎤 Browser STT active", "dim"); },
  (on) => {
    $("dRec").style.display = on ? "" : "none";
    $("recT").textContent = on ? "listening" : "idle";
    e.target.textContent = on ? "■ Stop" : "🎤 Browser STT";
  },
  () => showMsg("Microphone unavailable — type your answer.", "warn"));

/* ---------- Question flow: submit / skip / new topic / end ---------- */
function afterAdvance(r, statusMsg) {
  if (r.answered !== undefined) answered = r.answered;
  $("tx").textContent = "";
  media.clearBrowserTranscript();
  renderCount(); renderDots();
  if (r.at_limit || !r.next_question) {
    showMsg("Interview complete! Preparing your report…", "ok");
    setSubmitting(false);
    endInterview();
    return;
  }
  $("bridge").textContent = r.bridge || "";
  qText(r.next_question);
  showMsg(statusMsg, "dim");
  setSubmitting(false);
  resumeVisual();
  autoReadQuestion();
}

$("bSend").onclick = async () => {
  if (submitting) return;
  const a = $("tx").textContent.trim();
  if (!a || a === "…") { showMsg("Empty — answer not heard. Check microphone.", "warn"); return; }
  media.stopListen(); document.body.classList.remove("speaking");
  const visualPayload = collectVisual();
  setSubmitting(true, "Submitting…");
  showMsg("Saving your answer — next question coming up…", "dim");
  try {
    const r = await api.answerInterview(sid, a, visualPayload);
    if (r.error) { showMsg(r.error, "warn"); setSubmitting(false); return; }
    afterAdvance(r, "");
  } catch { showMsg("Server unreachable — try once more.", "warn"); setSubmitting(false); }
};

$("bSkip").onclick = async () => {
  if (submitting) return;
  setSubmitting(true, "Skipping…");
  media.stopListen(); dropVisual();
  try {
    const r = await api.skipInterview(sid);
    if (r.error) { showMsg(r.error, "warn"); setSubmitting(false); return; }
    afterAdvance(r, "Question skipped.");
  } catch { showMsg("Server unreachable.", "warn"); setSubmitting(false); }
};

$("bNew").onclick = async () => {
  if (submitting) return;
  setSubmitting(true, "Changing topic…");
  media.stopListen(); dropVisual();
  try {
    const r = await api.changeTopicInterview(sid);
    if (r.error) { showMsg(r.error, "warn"); setSubmitting(false); return; }
    afterAdvance(r, "Switched to a new topic.");
  } catch { showMsg("Server unreachable.", "warn"); setSubmitting(false); }
};

async function endInterview() {
  clearInterval(tick); media.stopListen(); visual.stopSampling();
  if (_lastBlobUrl) { try { URL.revokeObjectURL(_lastBlobUrl); } catch {} _lastBlobUrl = null; }
  try { await api.finishInterview(sid); } catch {}
  location.href = `/report?sid=${sid}`;
}
$("bEnd").onclick = endInterview;
$("bExit").onclick = endInterview;

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); $("bSend").click(); }
});

/* ---------- Boot ---------- */
(async () => {
  if (!(await ensureSession())) {
    qText("Could not start the mock interview.");
    $("mTip") && ($("mTip").textContent = "");
    setSubmitting(true);
    return;
  }
  tick = setInterval(() => {
    $("mTm").textContent = fmtDur(Date.now() - t0);
    $("mSig").textContent = `👁 ${visual.getEvents().length}`;
  }, 1000);
  renderCount(); renderDots();
  $("bCam").onclick = toggleCam;
  $("bMic").onclick = () => $("dMic").classList.toggle("on", media.toggleMic());
  try {
    const st = await api.status();
    $("mAI").textContent = st.ai_ready ? `${st.active_provider || "AI"} ready` : "AI offline";
  } catch { $("mAI").textContent = "server unreachable"; }
  if (prefs.get("cam", false)) toggleCam();
  try {
    const d = await api.sessionDetail(sid);
    if (d.error) { qText("Session not found."); return; }
    const pending = (d.turns || []).find((t) => t.question && !t.answer);
    const first = (d.turns || []).find((t) => t.question);
    answered = (d.turns || []).filter((t) => t.answer).length;
    NQ = d.meta?.num_questions || 5;
    qText((pending || first)?.question || "Tell me about yourself.");
    $("mRole").textContent = `${d.meta?.role || "Candidate"} · ${d.meta?.type || ""} · ${d.meta?.difficulty || ""}`;
    if (d.meta?.question_source === "user") $("mQLabel").textContent = "Your question list";
    renderCount(); renderDots();
    autoReadQuestion();
  } catch { qText("Could not load — is the server running?"); }
})();
