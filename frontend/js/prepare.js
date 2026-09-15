/* Preparation — central workspace. Type auto-selected from URL. Upload/paste real documents. Start → live interview.
   Documents are scoped to section="interview" so they never appear in other practice areas. */
const qs = new URLSearchParams(location.search);
const selType = qs.get("type") || "mixed";
const TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"];
const KIND_LABEL = { jd: "Job Description", resume: "Resume / CV", topic: "Topic", document: "Other" };
const ACCEPT_EXT = ".pdf,.docx,.txt,.md,.csv,.json,.py,.java,.js,.ts,.sql,.html,.css,.ppt,.pptx,.rtf";

const TYPE_META = {
  hr:          { label: "HR Interview",           tip: "Focus on presence, clarity, and storytelling. The AI will test how you present yourself.", needDoc: null,      acceptKind: null },
  technical:   { label: "Technical Interview",     tip: "Focus on correctness and reasoning out loud. Explain your thought process step by step.", needDoc: null,      acceptKind: null },
  project:     { label: "Project Interview",       tip: "Focus on ownership, decisions, and outcomes. Be specific about YOUR contribution.",     needDoc: null,      acceptKind: null },
  behavioral:  { label: "Behavioral Interview",    tip: "Use STAR structure (Situation, Task, Action, Result) for challenge, failure, and conflict stories.", needDoc: null, acceptKind: null },
  resume:      { label: "Resume-Based",            tip: "Questions target each section of your resume — experience, projects, skills. Be ready to go deep.", needDoc: "resume", acceptKind: "resume" },
  jd:          { label: "JD-Based",                tip: "Questions match the job description requirements. The AI will probe fit, gaps, and alignment.", needDoc: "jd",     acceptKind: "jd" },
  topic:       { label: "Topic-Based",             tip: "Deep drill into your uploaded material. The AI will test your understanding and explanation ability.", needDoc: "any", acceptKind: "topic" },
  mixed:       { label: "Mixed Interview",         tip: "Combines HR, technical, and behavioral questions — the full interview loop.",             needDoc: null,      acceptKind: null },
  custom:      { label: "Custom Interview",        tip: "Tell the AI exactly what to focus on. Your material, your rules.",                     needDoc: null,      acceptKind: null },
};

const page = buildShell("Preparation", "BERREADY / Interview / Preparation");

page.innerHTML = `
  <p class="sub" id="topTip"></p>
  <div class="grid g2">
    <div>
      <div class="card mb">
        <h3>Interview type</h3>
        <select id="s_type" style="width:100%">
          ${TYPES.map((t) => `<option value="${t}" ${t === selType ? "selected" : ""}>${TYPE_META[t].label}</option>`).join("")}
        </select>
        <div id="typeTip" class="small" style="margin:8px 0;padding:8px;background:var(--bg-soft, var(--bg2));border-radius:6px"></div>
        <div id="customBox" style="display:${selType === "custom" ? "" : "none"}">
          <label class="fl">Custom focus</label>
          <input type="text" id="s_custom" placeholder="e.g. system design + leadership" style="width:100%"/>
        </div>
      </div>

      <div class="card mb">
        <h3>Interview settings</h3>
        <label class="fl">Role</label>
        <input type="text" id="s_role" placeholder="e.g. Software Engineer" style="width:100%" value="${esc(prefs.get("role", ""))}"/>
        <label class="fl">Difficulty</label>
        <select id="s_diff" style="width:100%">
          ${["beginner", "intermediate", "advanced", "expert"].map((d) => `<option ${d === prefs.get("diff", "intermediate") ? "selected" : ""}>${d}</option>`).join("")}
        </select>
        <label class="fl">Number of questions</label>
        <select id="s_n" style="width:100%">
          <option>3</option><option selected>5</option><option>7</option><option>10</option>
        </select>
      </div>
    </div>

    <div>
      <div class="card mb" id="docCard">
        <h3>Documents</h3>
        <div id="docSection"></div>
      </div>

      <div class="card">
        <div class="row">
          <button class="primary" id="bGo">Start interview</button>
          <a class="btn ghost" href="/interview">Back</a>
        </div>
        <div id="err" class="small mt" style="color:var(--bad)"></div>
      </div>
    </div>
  </div>`;

let ALL_DOCS = [];

function getSelectedType() {
  const idx = document.getElementById("s_type").selectedIndex;
  return TYPES[idx];
}

function updateTip() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  document.getElementById("topTip").textContent = meta.tip;
  document.getElementById("typeTip").textContent = meta.tip;
  document.getElementById("customBox").style.display = type === "custom" ? "" : "none";
  document.getElementById("docCard").style.display = meta.needDoc ? "" : "none";
  renderDocSection();
}

document.getElementById("s_type").onchange = updateTip;

const DOC_SECTION = "interview";

async function refreshDocs() {
  try { ALL_DOCS = (await api.docs(DOC_SECTION)).documents || []; } catch {}
  renderDocSection();
}

function renderDocSection() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  const section = document.getElementById("docSection");
  if (!meta.needDoc) {
    section.innerHTML = `<div class="small dim">No documents needed — questions are general for this type.</div>`;
    return;
  }

  const docs = ALL_DOCS;
  const acceptKind = meta.acceptKind;
  const relevant = acceptKind ? docs.filter((d) => d.kind === acceptKind) : docs;
  const hasRequired = relevant.length > 0;

  let existingHtml = "";
  if (docs.length) {
    existingHtml = `
      <div class="small" style="margin:0 0 6px;font-weight:600">Your documents:</div>
      ${docs.map((d) => {
        const isRelevant = !acceptKind || d.kind === acceptKind;
        return `<label style="display:flex;align-items:center;gap:8px;font-weight:400;padding:4px 0;${isRelevant ? "" : "opacity:0.5"}">
          <input type="checkbox" data-doc="${d.id}" ${isRelevant ? "checked" : ""}/>
          <span>${esc(d.filename)} <span class="dim">(${esc(KIND_LABEL[d.kind] || d.kind)})</span></span>
        </label>`;
      }).join("")}`;
  }

  const uploadHtml = `
    <div style="border:1px dashed var(--line);border-radius:6px;padding:12px;margin-top:8px">
      <div class="small" style="font-weight:600;margin-bottom:6px">Add ${acceptKind ? KIND_LABEL[acceptKind] || "document" : "document"}</div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <label class="btn" style="cursor:pointer;margin:0">
          Upload file <input type="file" id="docFile" accept="${ACCEPT_EXT}" style="display:none"/>
        </label>
        <button class="ghost" id="bPaste" type="button">Paste text</button>
      </div>
      <div id="uploadStatus" class="small mut mt"></div>
      <div id="pasteBox" style="display:none;margin-top:8px">
        <textarea id="pasteText" rows="6" placeholder="Paste your resume, job description, or topic text here…" style="width:100%;font-family:inherit;font-size:13px;resize:vertical"></textarea>
        <div class="row mt" style="gap:6px">
          <select id="pasteKind" style="width:auto">
            ${acceptKind ? `<option value="${acceptKind}" selected>${KIND_LABEL[acceptKind] || acceptKind}</option>` : ""}
            <option value="resume">Resume / CV</option>
            <option value="jd">Job Description</option>
            <option value="topic">Topic</option>
            <option value="document">Other</option>
          </select>
          <button class="primary" id="bSavePaste" type="button">Save text</button>
          <button class="ghost" id="bCancelPaste" type="button">Cancel</button>
        </div>
        <div id="pasteStatus" class="small mut mt"></div>
      </div>
    </div>`;

  let banner = "";
  if (!docs.length) {
    banner = `<div style="padding:8px;background:var(--bg2);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--warn)">No documents yet — upload or paste your ${acceptKind ? KIND_LABEL[acceptKind]?.toLowerCase() || "material" : "material"} below.</div></div>`;
  } else if (!hasRequired && acceptKind) {
    banner = `<div style="padding:8px;background:var(--bg2);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--warn)">No ${KIND_LABEL[acceptKind]?.toLowerCase() || "matching"} documents — upload or paste one below for targeted questions.</div></div>`;
  } else if (hasRequired) {
    banner = `<div style="padding:6px;background:rgba(52,211,153,0.1);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--ok)">✓ ${relevant.length} ${KIND_LABEL[acceptKind]?.toLowerCase() || "matching"} document${relevant.length > 1 ? "s" : ""} ready — questions will be tailored.</div></div>`;
  }

  section.innerHTML = banner + existingHtml + uploadHtml;

  // Wire file upload
  document.getElementById("docFile").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const st = document.getElementById("uploadStatus");
    st.innerHTML = `Uploading <b>${esc(f.name)}</b>…`;
    try {
      const r = await api.uploadDoc(f, acceptKind || "document", DOC_SECTION);
      if (r.error) { st.innerHTML = `<span style="color:var(--bad)">Failed: ${esc(r.error)}</span>`; return; }
      st.innerHTML = `<span style="color:var(--ok)">✓ Uploaded (${(r.chars / 1000).toFixed(1)}k chars)</span>`;
      await refreshDocs();
      const cb = document.querySelector(`[data-doc="${r.doc_id}"]`);
      if (cb) cb.checked = true;
    } catch { st.innerHTML = `<span style="color:var(--bad)">Upload failed — server unreachable.</span>`; }
  };

  // Wire paste toggle
  document.getElementById("bPaste").onclick = () => {
    const box = document.getElementById("pasteBox");
    const shown = box.style.display !== "none";
    box.style.display = shown ? "none" : "";
    if (!shown) document.getElementById("pasteText").focus();
  };

  // Wire paste save
  document.getElementById("bSavePaste").onclick = async () => {
    const text = document.getElementById("pasteText").value.trim();
    const kind = document.getElementById("pasteKind").value;
    const st = document.getElementById("pasteStatus");
    if (!text) { st.innerHTML = `<span style="color:var(--warn)">Paste some text first.</span>`; return; }
    st.innerHTML = `Saving…`;
    try {
      const r = await api.pasteDoc(text, kind, `${KIND_LABEL[kind] || "pasted"}.txt`, DOC_SECTION);
      if (r.error) { st.innerHTML = `<span style="color:var(--bad)">Failed: ${esc(r.error)}</span>`; return; }
      st.innerHTML = `<span style="color:var(--ok)">✓ Saved (${(r.chars / 1000).toFixed(1)}k chars)</span>`;
      document.getElementById("pasteText").value = "";
      await refreshDocs();
      const cb = document.querySelector(`[data-doc="${r.doc_id}"]`);
      if (cb) cb.checked = true;
    } catch { st.innerHTML = `<span style="color:var(--bad)">Save failed.</span>`; }
  };

  // Wire paste cancel
  document.getElementById("bCancelPaste").onclick = () => {
    document.getElementById("pasteBox").style.display = "none";
  };
}

// Start interview
document.getElementById("bGo").onclick = async () => {
  const btn = document.getElementById("bGo");
  const errEl = document.getElementById("err");
  errEl.textContent = "";
  const type = getSelectedType();
  const meta = TYPE_META[type];

  const docIds = [...document.querySelectorAll("[data-doc]:checked")].map((c) => c.dataset.doc);
  const custom = (document.getElementById("s_custom")?.value || "").trim();
  const role = document.getElementById("s_role").value;

  // Validate documents
  if (meta.needDoc === "resume" && !docIds.some((id) => ALL_DOCS.find((d) => d.id === id && d.kind === "resume"))) {
    errEl.textContent = "Resume-Based interview requires a resume. Upload or paste one above.";
    return;
  }
  if (meta.needDoc === "jd" && !docIds.some((id) => ALL_DOCS.find((d) => d.id === id && d.kind === "jd"))) {
    errEl.textContent = "JD-Based interview requires a job description. Upload or paste one above.";
    return;
  }
  if (meta.needDoc === "any" && ALL_DOCS.length === 0) {
    errEl.textContent = "Topic-Based interview requires material. Upload or paste a document above.";
    return;
  }
  if (meta.needDoc === "any" && docIds.length === 0 && ALL_DOCS.length > 0) {
    errEl.textContent = "Select at least one document for a Topic-Based interview.";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Preparing…";
  prefs.set("role", role);
  prefs.set("diff", document.getElementById("s_diff").value);
  prefs.set("nQ", document.getElementById("s_n").value);

  try {
    const r = await api.planInterview({
      doc_ids: docIds,
      interview_type: type,
      difficulty: document.getElementById("s_diff").value,
      role: type === "custom" && custom ? `Custom focus: ${custom}. Role: ${role}` : role,
      num_questions: parseInt(document.getElementById("s_n").value, 10),
    });
    location.href = `/interview-live?sid=${r.session_id}`;
  } catch {
    errEl.textContent = "Could not start — is the server running?";
    btn.disabled = false;
    btn.textContent = "Start interview";
  }
};

// Init
(async () => { await refreshDocs(); updateTip(); })();
