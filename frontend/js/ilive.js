/* Live Interview: real interview room. One-click submit, compact live report, retry. */
const sid = new URLSearchParams(location.search).get("sid");
if (!sid) location.href = "/interview";
const page = buildShell("Interview", "BERREADY / Interview / Live");
const media = createMedia();
let answered = 0, t0 = Date.now(), tick = null, submitting = false, retryMode = false;
let currentRequestId = 0;
let NQ = 5;
let _lastBlobUrl = null;   // blob URL of the most recent recording for replay
let _lastAudioEl = null;   // currently playing Audio element

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
    <div class="row"><button id="bCam">Camera</button><button id="bMic">Mic</button></div></div>
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
  
  document.getElementById("tx").textContent = transcript || "…";
  document.getElementById("dRec").style.display = "none";
  document.getElementById("dRec").classList.remove("rec");
  document.getElementById("recT").textContent = "● idle";
};

document.getElementById("bTalk").onclick = (e) => media.listen(
  (t) => { document.getElementById("tx").textContent = t; document.getElementById("sttStatus").innerHTML = `<span class="small mut">🎤 Browser STT active</span>`; },
  (on) => { document.getElementById("dRec").style.display = on ? "" : "none";
    document.getElementById("recT").textContent = on ? "● listening" : "● idle";
    document.body.classList.toggle("speaking", on); e.target.textContent = on ? "■ Stop" : "🎤 Browser STT"; },
  () => { document.getElementById("sttStatus").innerHTML = `<span style="color:var(--warn)">Microphone unavailable — type your answer.</span>`; });

document.getElementById("bRetryQ").onclick = () => {
  if (submitting) return;
  retryMode = true;
  document.getElementById("tx").textContent = ""; document.getElementById("tx").focus();
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

function reportPanel(ev, cmp) {
  const rel = ev.relevance || {};
  const dims = ev.dimensions || {};
  const tech = ev.technical && ev.technical !== "n/a" ? `<div class="small">⚙ Technical: ${esc(ev.technical)}</div>` : "";
  const sents = (ev.sentences || []).map((s) =>
    `<div class="small">✎ <i>“${esc(s.problem)}”</i><br/>→ ${esc(s.fix)}</div>`).join("");
  const better = (ev.better_examples || []).map((b) =>
    `<div class="small">“${esc(b.text)}”<br/><span class="dim">Why stronger: ${esc(b.why)}</span></div>`).join("");
  const replayHtml = _lastBlobUrl
    ? `<button class="ghost" id="bReplay" title="Replay your recorded answer">▶ Replay answer</button>`
    : "";
  return `<div class="card quiet" style="border:1px solid var(--line-soft)">
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
  currentRequestId = Date.now(); // Unique ID for deduplication
  const myRequestId = currentRequestId;
  const a = document.getElementById("tx").textContent.trim();
  if (!a || a === "…") { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Empty — answer not heard. Check microphone.</span>`; return; }
  media.stopListen(); document.body.classList.remove("speaking");
  setSubmitting(true, "Analyzing answer…");
  document.getElementById("eval").innerHTML = `<span class="small mut">Analyzing your answer…</span>`;
  const wasRetry = retryMode;
  try {
    const r = await (wasRetry ? api.retryInterview(sid, a) : api.answerInterview(sid, a));
    if (myRequestId !== currentRequestId) return; // Another request superseded this one
    if (r.error) {
      if (r.code === "in_flight") { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Answer already being processed — please wait.</span>`; }
      else { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">${esc(r.error)}</span>`; }
      setSubmitting(false); return;
    }
    // Use backend's authoritative answered count (handles retries correctly).
    if (r.answered !== undefined) answered = r.answered;
    else if (!wasRetry) answered++;
    retryMode = false;
    document.getElementById("ansLabel").textContent = "Your answer — speak or type";
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("eval").innerHTML = reportPanel(r.evaluation, wasRetry ? r : null)
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
    document.getElementById("tx").textContent = "";
    document.getElementById("cnt").textContent = `Question ${answered} of ${NQ}`;
    // Stop if at question limit (backend says so, or frontend count matches).
    if (r.at_limit || (!wasRetry && answered >= NQ)) { endInterview(); return; }
    document.getElementById("q").textContent = r.next_question;
    document.getElementById("sttStatus").innerHTML = "";
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