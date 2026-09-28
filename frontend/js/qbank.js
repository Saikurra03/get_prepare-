/* Question list builder (Phase 4): upload/paste your own questions, set
   count + difficulty + order, then launch the full-screen mock room.
   The AI NEVER invents or rewrites questions — it only evaluates answers. */
const page = buildShell("Question list", "BERREADY / Interview / Question list");
let PARSED = [];

page.innerHTML = `
  <p class="sub">Bring your own questions — interview packs, past papers, company lists. Any length, any number of questions.</p>
  <div class="grid g2">
    <div class="card"><h3>Your questions</h3>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <label class="btn" style="cursor:pointer;margin:0">Upload file
          <input type="file" id="qbFile" accept=".txt,.md,.csv,.json" style="display:none"/></label>
        <button class="ghost" id="qbPasteBtn" type="button">Paste text</button>
        <span class="small dim">.txt · .md · .csv · .json</span>
      </div>
      <div id="qbPasteBox" style="display:none;margin-top:10px">
        <textarea id="qbText" rows="9" placeholder="One question per line — numbering (1. Q2:) and bullets are cleaned automatically.&#10;What is your greatest strength?&#10;Describe a conflict you resolved." style="width:100%;font-family:inherit;font-size:13px;resize:vertical"></textarea>
        <div class="row mt" style="gap:6px">
          <button class="primary" id="qbParse" type="button">Build list</button>
          <button class="ghost" id="qbClear" type="button">Clear</button>
        </div>
      </div>
      <div id="qbStatus" class="small mut mt"></div>
      <div id="qbPreview" class="qb-list mt"><div class="qb-empty">No questions yet — upload a file or paste your list.</div></div>
    </div>
    <div class="card"><h3>Session controls</h3>
      <div style="padding:8px 10px;background:rgba(91,140,255,.08);border:1px solid rgba(91,140,255,.25);border-radius:8px;margin-bottom:10px">
        <div class="small">🔒 The AI <b>never invents, rewrites or reorders</b> your questions — it only evaluates your answers.</div>
      </div>
      <div class="qb-controls">
        <div><label class="fl">Questions to ask</label>
          <select id="qbCount"><option value="0">All questions</option><option>3</option><option selected>5</option>
            <option>7</option><option>10</option><option>15</option><option>20</option></select></div>
        <div><label class="fl">Difficulty</label>
          <select id="qbDiff">${["beginner", "intermediate", "advanced", "expert"].map(d =>
            `<option ${d === prefs.get("diff", "intermediate") ? "selected" : ""}>${d}</option>`).join("")}</select></div>
        <div><label class="fl">Order</label>
          <select id="qbOrder"><option value="sequential">As listed</option><option value="random">Random</option></select></div>
      </div>
      <div class="qb-controls mt">
        <div><label class="fl">Evaluation focus</label>
          <select id="qbType">
            <option value="mixed" selected>Mixed (full loop)</option><option value="hr">HR</option>
            <option value="technical">Technical</option><option value="behavioral">Behavioral</option>
            <option value="project">Project</option></select></div>
        <div style="flex:1;min-width:180px"><label class="fl">Role (optional)</label>
          <input type="text" id="qbRole" placeholder="e.g. Software Engineer" style="width:100%" value="${esc(prefs.get("role", ""))}"/></div>
      </div>
      <div class="row mt"><button class="primary" id="qbStart">Start mock interview</button>
        <a class="btn ghost" href="/interview">Back</a></div>
      <div id="qbErr" class="small mt" style="color:var(--bad)"></div>
      <div id="qbSummary" class="small dim mt"></div>
    </div>
  </div>`;

const $ = (id) => document.getElementById(id);

function renderPreview() {
  if (!PARSED.length) {
    $("qbPreview").innerHTML = `<div class="qb-empty">No questions yet — upload a file or paste your list.</div>`;
    $("qbSummary").textContent = "";
    return;
  }
  $("qbPreview").innerHTML = PARSED.map((q, i) =>
    `<div class="qb-item"><span class="qb-n">${i + 1}.</span><span>${esc(q)}</span></div>`).join("");
  const cnt = $("qbCount").value;
  const use = cnt === "0" ? PARSED.length : Math.min(parseInt(cnt, 10), PARSED.length);
  $("qbSummary").textContent = `Ready: ${use} of ${PARSED.length} question${PARSED.length > 1 ? "s" : ""} will be asked.`;
}

async function parseText(text, filename, how) {
  if (!text.trim()) { $("qbStatus").innerHTML = `<span style="color:var(--warn)">Nothing to parse.</span>`; return; }
  $("qbStatus").textContent = "Parsing…";
  try {
    const r = await api.parseQuestions(text, filename);
    PARSED = r.questions || [];
    $("qbStatus").innerHTML = PARSED.length
      ? `<span style="color:var(--ok)">✓ ${PARSED.length} question${PARSED.length > 1 ? "s" : ""} found (${how}).</span>`
      : `<span style="color:var(--warn)">No usable questions found — one per line helps.</span>`;
    renderPreview();
  } catch {
    $("qbStatus").innerHTML = `<span style="color:var(--bad)">Server unreachable — try again.</span>`;
  }
}

$("qbFile").onchange = (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => parseText(String(reader.result || ""), f.name, `file ${f.name}`);
  reader.readAsText(f);
};
$("qbPasteBtn").onclick = () => {
  const box = $("qbPasteBox");
  const shown = box.style.display !== "none";
  box.style.display = shown ? "none" : "";
  if (!shown) $("qbText").focus();
};
$("qbParse").onclick = () => parseText($("qbText").value, "", "pasted text");
$("qbClear").onclick = () => { $("qbText").value = ""; PARSED = []; $("qbStatus").textContent = ""; renderPreview(); };
$("qbCount").onchange = renderPreview;

$("qbStart").onclick = async () => {
  const btn = $("qbStart"), err = $("qbErr");
  err.textContent = "";
  if (!PARSED.length) { err.textContent = "Add at least one question first."; return; }
  const cnt = $("qbCount").value;
  btn.disabled = true; btn.textContent = "Preparing…";
  prefs.set("diff", $("qbDiff").value);
  const role = $("qbRole").value.trim();
  if (role) prefs.set("role", role);
  try {
    const r = await api.planInterview({
      interview_type: $("qbType").value,
      difficulty: $("qbDiff").value,
      role,
      num_questions: cnt === "0" ? PARSED.length : parseInt(cnt, 10),
      questions: PARSED,
      order: $("qbOrder").value,
      doc_ids: [],
    });
    if (r.error) { err.textContent = r.error; btn.disabled = false; btn.textContent = "Start mock interview"; return; }
    location.href = `/mock?sid=${r.session_id}`;
  } catch {
    err.textContent = "Could not start — is the server running?";
    btn.disabled = false; btn.textContent = "Start mock interview";
  }
};

renderPreview();
