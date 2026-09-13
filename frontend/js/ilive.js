/* Live Interview: real interview room. One-click submit, compact live report, retry. */
const sid = new URLSearchParams(location.search).get("sid");
if (!sid) location.href = "/interview";
const page = buildShell("Interview", "BERREADY / Interview / Live");
const media = createMedia();
const NQ = parseInt(prefs.get("nQ", "5"), 10) || 5;
let answered = 0, t0 = Date.now(), tick = null, submitting = false, retryMode = false;

page.innerHTML = `
  <div class="card mb"><div class="row"><div><div class="small dim" id="ivMeta">Preparing…</div>
    <div class="question" id="q" style="margin-top:4px">Loading your interview…</div>
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
      <div class="row mt"><button class="primary" id="bTalk">🎤 Answer</button>
      <button class="primary" id="bSend">Submit answer</button><button class="ghost" id="bRetryQ">Retry answer</button></div>
      <div id="eval" class="mt"></div></div>
      <div class="row mt"><button class="danger" id="bEnd">End interview</button></div></div></div>`;

tick = setInterval(() => { const el = document.getElementById("tm"); if (el) el.textContent = fmtDur(Date.now() - t0); }, 500);
if (prefs.get("cam", false)) toggleCam(); else document.getElementById("bCam").onclick = toggleCam;
async function toggleCam() {
  const on = await media.camera(document.getElementById("v"), !media.camOn, () => alert("Camera unavailable — continuing audio-only."));
  document.getElementById("dCam").classList.toggle("on", on);
}
document.getElementById("bMic").onclick = () => {
  const on = media.toggleMic(); document.getElementById("dMic").classList.toggle("on", on);
};
document.getElementById("bTalk").onclick = (e) => media.listen(
  (t) => { document.getElementById("tx").textContent = t; },
  (on) => { document.getElementById("dRec").style.display = on ? "" : "none";
    document.getElementById("recT").textContent = on ? "● listening" : "● idle";
    document.body.classList.toggle("speaking", on); e.target.textContent = on ? "■ Stop" : "🎤 Answer"; },
  () => alert("Microphone unavailable — type your answer."));
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
}
function reportPanel(ev, cmp) {
  const rel = ev.relevance || {};
  const dims = ev.dimensions || {};
  const sents = (ev.sentences || []).map((s) =>
    `<div class="small">✎ <i>“${esc(s.problem)}”</i><br/>→ ${esc(s.fix)}</div>`).join("");
  const better = (ev.better_examples || []).map((b) =>
    `<div class="small">“${esc(b.text)}”<br/><span class="dim">Why stronger: ${esc(b.why)}</span></div>`).join("");
  return `<div class="card quiet" style="border:1px solid var(--line-soft)">
    <b>Answer feedback</b> <span class="score">${ev.score ?? "—"}/10</span>
    ${(ev.good || []).map((g) => `<div class="small">✓ ${esc(g)}</div>`).join("")}
    ${ev.biggest_issue ? `<div class="small">⚠ ${esc(ev.biggest_issue)}</div>` : ""}
    ${rel.note ? `<div class="small">🎯 Relevance (${esc(rel.verdict || "")}): ${esc(rel.note)}</div>` : ""}
    ${ev.interviewer_want ? `<div class="small">👔 Interviewer wanted: ${esc(ev.interviewer_want)}</div>` : ""}
    ${sents ? `<div class="mt"><b class="small">Sentence formation</b>${sents}</div>` : ""}
    ${better ? `<div class="mt"><b class="small">Better way to say it</b>${better}</div>` : ""}
    <div class="small dim mt">Clarity: ${esc(dims.clarity || "—")} · Conciseness: ${esc(dims.conciseness || "—")} · Specificity: ${esc(dims.specificity || "—")}</div>
    <div class="small dim">Articulation: n/a from transcript · Pronunciation: n/a from transcript</div>
    ${cmp ? `<div class="small mt"><b>Retry comparison:</b> ${cmp.old?.score ?? "—"} → ${cmp.new?.score ?? "—"}</div>` : ""}
  </div>`;
}
document.getElementById("bSend").onclick = async () => {
  if (submitting) return; // ONE CLICK: ignore repeats while a request is in flight
  const a = document.getElementById("tx").textContent.trim();
  if (!a || a === "…") { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Empty — answer not heard. Check microphone.</span>`; return; }
  media.stopListen(); document.body.classList.remove("speaking");
  setSubmitting(true, "Analyzing answer…");
  document.getElementById("eval").innerHTML = `<span class="small mut">Analyzing your answer…</span>`;
  const wasRetry = retryMode;
  try {
    const r = await (wasRetry ? api.retryInterview(sid, a) : api.answerInterview(sid, a));
    if (r.error) { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">${esc(r.error)}</span>`; setSubmitting(false); return; }
    if (!wasRetry) answered++;
    retryMode = false;
    document.getElementById("ansLabel").textContent = "Your answer — speak or type";
    document.getElementById("bridge").textContent = r.bridge || "";
    document.getElementById("eval").innerHTML = reportPanel(r.evaluation, wasRetry ? r : null)
      + (r.retry_suggested && !wasRetry ? `<div class="row mt"><button id="bRetry2">🔁 ${esc(r.retry_instruction || "Retry this answer")}</button></div>` : "");
    const rb = document.getElementById("bRetry2");
    if (rb) rb.onclick = () => document.getElementById("bRetryQ").click();
    document.getElementById("tx").textContent = "";
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ~${NQ}`;
    if (!wasRetry && answered >= NQ) { endInterview(); return; }
    document.getElementById("q").textContent = r.next_question;
    setSubmitting(false);
  } catch { document.getElementById("eval").innerHTML = `<span class="small" style="color:var(--warn)">Server unreachable — your answer was not sent. Try once more.</span>`; setSubmitting(false); }
};
async function endInterview() {
  clearInterval(tick); media.stopListen();
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
    document.getElementById("q").textContent = (pending || first)?.question || "Tell me about yourself.";
    document.getElementById("ivMeta").textContent =
      `${d.meta?.role || "Candidate"} · ${d.meta?.type || ""} · ${d.meta?.difficulty || ""}`;
    document.getElementById("cnt").textContent = `Question ${answered + 1} of ~${NQ}`;
  } catch { document.getElementById("q").textContent = "Could not load — is the server running?"; }
})();
