/* Practice workspace: Setup → Live → Feedback → Retry → Results. One purpose: let me practice. */
const qs = new URLSearchParams(location.search);
const modeKey = MODES[qs.get("mode")] ? qs.get("mode") : "communication";
const M = MODES[modeKey];
const page = buildShell(M.title, `BERREADY / Practice / ${M.title}`);
const media = createMedia();
let sessionId = null, timer = null, t0 = 0, cfg = {}, firstText = "", lastResult = null;

const steps = ["Setup", "Live", "Feedback", "Retry", "Results"];
const EVAL_ON = {
  communication: "clarity · sentence formation · vocabulary · fillers · pacing",
  story: "hook · structure · specificity · pacing · engagement · ending",
  speaking: "clarity · pacing · structure · delivery · presence",
  wit: "naturalness · timing · relevance · engagement",
  qa: "thinking speed · relevance · clarity · structure",
  podcast: "communication · engagement · storytelling · delivery",
  conversation: "clarity · flow · engagement",
};
function stepBar(active) {
  return `<div class="stepper">${steps.map((s, i) => `<span class="step${i === active ? " on" : ""}">${s}</span>`).join("")}</div>`;
}
function setupFields() {
  let h = "";
  if (M.focuses) h += `<label class="fl">Focus</label><select id="f_focus">${M.focuses.map((f) => `<option>${f}</option>`).join("")}</select>`;
  if (M.kinds) h += `<label class="fl">${modeKey === "podcast" ? "Format" : "Style"}</label><select id="f_kind">${M.kinds.map((k) => `<option>${k}</option>`).join("")}</select>`;
  if (modeKey === "speaking" || modeKey === "podcast")
    h += `<label class="fl">Topic</label><input type="text" id="f_topic" placeholder="e.g. Why remote work wins" style="width:100%"/>`;
  if (modeKey === "speaking" || modeKey === "podcast")
    h += `<label class="fl">Target duration</label><select id="f_dur"><option>1 minute</option><option selected>2 minutes</option><option>5 minutes</option></select>`;
  if (M.prompts) h += `<label class="fl">Prompt</label><div class="row"><select id="f_prompt" style="flex:1">${M.prompts.map((p) => `<option>${esc(p)}</option>`).join("")}</select><button class="ghost" id="bDice" title="Random prompt">⚄</button></div>`;
  if (modeKey === "qa") h += `<p class="small mut">You get 10 seconds to think once the question appears, then speak.</p>`;
  return h;
}
function showSetup() {
  page.innerHTML = `${stepBar(0)}<div class="grid g2"><div class="card"><h3>Set up your session</h3>
    <p class="sub">${esc(M.purpose)}</p>${setupFields()}
    <label class="fl">Devices</label><div class="row">
    <button id="bCam">Camera: off</button><button id="bMic">Mic: off</button></div>
    <p class="small dim">Camera and mic stay off until you start. Nothing is recorded — only coaching notes are kept.</p></div>
    <div class="card"><h3>How it works</h3><p class="small mut">Speak → AI observes → one clear priority → retry → compare. Minimal UI while you talk; detail afterwards.</p>
    <div class="row mt"><button class="primary" id="bStart">Start practice</button><a class="btn ghost" href="/practice">Back</a></div></div></div>
    <div class="card mt dim-while-speaking" style="display:none"></div>`;
  document.getElementById("bDice") && (document.getElementById("bDice").onclick = () => {
    const s = document.getElementById("f_prompt"); s.selectedIndex = Math.floor(Math.random() * s.options.length);
  });
  document.getElementById("bCam").onclick = async (e) => {
    const on = await media.camera(document.getElementById("v"), !media.camOn, () => alert("Camera unavailable — continuing audio-only."));
    e.target.textContent = `Camera: ${on ? "on" : "off"}`;
  };
  document.getElementById("bMic").onclick = (e) => { e.target.textContent = `Mic: ${media.toggleMic() ? "on" : "off"}`; };
  document.getElementById("bStart").onclick = startLive;
}
function readCfg() {
  const v = (id) => document.getElementById(id)?.value || "";
  cfg = { focus: v("f_focus"), kind: v("f_kind"), topic: v("f_topic"), dur: v("f_dur"), prompt: v("f_prompt") };
}
async function startLive() {
  readCfg();
  try {
    const s = await api.post("/api/session/create", { kind: modeKey === "podcast" ? "podcast" : "practice", scenario: M.scenario });
    sessionId = s.id;
  } catch { sessionId = null; }
  const promptLine = cfg.prompt ? `<div class="card mb"><div class="small dim">Your prompt</div><div class="question">${esc(cfg.prompt)}</div>
    ${modeKey === "qa" ? `<div class="small mut">Think time: <b id="cd">10</b>s</div>` : ""}</div>` : "";
  const topicLine = cfg.topic ? `<div class="card mb"><div class="small dim">Topic${cfg.kind ? " · " + esc(cfg.kind) : ""}${cfg.dur ? " · " + esc(cfg.dur) : ""}</div><div class="question">${esc(cfg.topic)}</div></div>` : "";
  page.innerHTML = `${stepBar(1)}
    <div class="live"><div><video class="cam" id="v" autoplay muted playsinline></video>
      <div class="statusbar"><span><span class="dot" id="dCam"></span>Camera</span>
      <span><span class="dot" id="dMic"></span>Mic</span>
      <span><span class="dot rec" id="dRec" style="display:none"></span><span id="recT">ready</span></span>
      <span class="timer" id="tm">00:00</span></div></div>
      <div>${promptLine}${topicLine}
      <div class="card"><div class="transcript" id="tx" contenteditable="true">Your words appear here — or type if the mic is unavailable…</div>
      <div class="row mt"><button class="primary" id="bTalk">🎤 Speak</button>
      <button id="bDone">Done — feedback</button><button class="ghost" id="bCancel">Cancel</button></div></div></div></div>`;
  if (media.camOn) { try { document.getElementById("v").srcObject = media.stream; } catch {} document.getElementById("dCam").classList.add("on"); }
  t0 = Date.now(); timer = setInterval(() => { document.getElementById("tm").textContent = fmtDur(Date.now() - t0); }, 500);
  if (modeKey === "qa") {
    document.getElementById("bTalk").disabled = true;
    let n = 10; const cd = setInterval(() => {
      n--; const el = document.getElementById("cd"); if (el) el.textContent = n;
      if (n <= 0) { clearInterval(cd); document.getElementById("bTalk").disabled = false; }
    }, 1000);
  }
  document.getElementById("bTalk").onclick = (e) => media.listen(
    (t) => { document.getElementById("tx").textContent = t; },
    (on) => { document.getElementById("dRec").style.display = on ? "" : "none";
      document.getElementById("recT").textContent = on ? "listening…" : "ready";
      document.body.classList.toggle("speaking", on); e.target.textContent = on ? "■ Stop" : "🎤 Speak"; },
    () => alert("Microphone unavailable — type your answer instead."));
  document.getElementById("bCancel").onclick = () => { clearInterval(timer); media.stopListen(); showSetup(); };
  document.getElementById("bDone").onclick = getFeedback;
}
async function getFeedback() {
  clearInterval(timer); media.stopListen(); document.body.classList.remove("speaking");
  firstText = document.getElementById("tx").textContent.trim();
  if (!firstText) { alert("Nothing to analyze — speak or type first."); return startLive(); }
  page.innerHTML = `${stepBar(2)}<div class="card"><h3>Analyzing…</h3><p class="sub">The coach is finding your single highest-impact improvement.</p></div>`;
  let r;
  try {
    r = await api.analyze({ transcript: firstText, scenario: M.scenario, session_id: sessionId, camera_on: media.camOn, mic_on: media.micOn });
  } catch { page.innerHTML += `<div class="card mt">Could not reach the server.</div>`; return; }
  if (r.error) { alert(r.error); return startLive(); }
  lastResult = r;
  const s = r.signals || {};
  const chips = [`${s.word_count || 0} words`, `fillers: ${s.filler_total ?? 0}`, `long sentences: ${s.long_sentences ?? 0}`, `hedges: ${s.qualifier_total ?? 0}`]
    .map((c) => `<span class="score">${esc(c)}</span>`).join("");
  page.innerHTML = `${stepBar(2)}<div class="card"><div class="small dim">Your attempt</div>
    <p>${esc(firstText.slice(0, 600))}</p><div class="mb">${chips}</div></div>
    <div class="card mt"><h3>Coach — one priority</h3>
    <div class="small dim mb">Evaluated on: ${esc(EVAL_ON[modeKey] || EVAL_ON.conversation)}</div>
    <div class="feedback">${esc(r.feedback)}</div>
    ${r.interruption?.interrupt ? `<p class="small" style="color:var(--warn)">Worth interrupting for: ${esc(r.interruption.reasons.join("; "))}</p>` : ""}
    <div class="row mt"><button class="primary" id="bRetry">Retry this</button>
    <button id="bAgain">New attempt</button><button class="ghost" id="bFinish">Finish</button></div></div>`;
  document.getElementById("bRetry").onclick = showRetry;
  document.getElementById("bAgain").onclick = startLive;
  document.getElementById("bFinish").onclick = finish;
}
function showRetry() {
  page.innerHTML = `${stepBar(3)}<div class="card"><div class="small dim">Original</div><p>${esc(firstText.slice(0, 500))}</p></div>
    <div class="card mt"><h3>Retry — apply the coaching above</h3>
    <div class="transcript" id="tx2" contenteditable="true">Speak or type your improved version…</div>
    <div class="row mt"><button id="bTalk2">🎤 Speak retry</button><button class="primary" id="bCmp">Compare</button></div>
    <div id="cmpOut" class="mt"></div>
    <div class="row mt"><button class="ghost" id="bFinish2">Finish</button></div></div>`;
  document.getElementById("bTalk2").onclick = (e) => media.listen(
    (t) => { document.getElementById("tx2").textContent = t; }, (on) => { e.target.textContent = on ? "■ Stop" : "🎤 Speak retry"; }, () => alert("Mic unavailable — type instead."));
  document.getElementById("bCmp").onclick = async () => {
    const second = document.getElementById("tx2").textContent.trim();
    if (!second) { alert("Speak or type your retry first."); return; }
    const c = await api.retryCompare(firstText, second);
    document.getElementById("cmpOut").innerHTML = `<div class="card quiet" style="border:1px solid var(--line-soft)">
      <b>Verdict: ${esc(c.verdict)}</b> — clarity ${c.clarity_before} → ${c.clarity_after}, time-to-point: ${esc(c.time_to_main_point)}
      <br/><span class="small dim">${esc(c.note)}</span></div>`;
  };
  document.getElementById("bFinish2").onclick = finish;
}
async function finish() {
  if (sessionId) { try { await api.post("/api/session/finish", { session_id: sessionId }); } catch {} }
  const r = lastResult;
  page.innerHTML = `${stepBar(4)}<div class="card"><h3>Session complete</h3>
    <p>${r ? `Top issue worked on: <b>${esc(r.issue)}</b>. ${esc(r.feedback).slice(0, 220)}…` : "Well done for showing up and speaking."}</p>
    <div class="row mt"><a class="btn primary" href="/workspace?mode=${modeKey}">Practice again</a>
    <a class="btn" href="/progress">See progress</a><a class="btn ghost" href="/practice">All practice</a></div></div>`;
}
showSetup();
