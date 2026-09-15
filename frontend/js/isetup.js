/* Interview Setup: per-type config, real upload/paste, doc validation. Then start. */
const qs = new URLSearchParams(location.search);
const page = buildShell("Interview setup", "BERREADY / Interview / Setup");
const TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"];
const selType = qs.get("type") || "mixed";
const KIND_LABEL = { jd: "Job Description", resume: "Resume / CV", topic: "Topic", document: "Other" };

const TYPE_META = {
  hr:          { label: "HR Interview", tip: "Focus on presence, clarity, and storytelling. The AI will test how you present yourself.", needDoc: null, acceptKind: null },
  technical:   { label: "Technical Interview", tip: "Focus on correctness and reasoning out loud. Explain your thought process step by step.", needDoc: null, acceptKind: null },
  project:     { label: "Project Interview", tip: "Focus on ownership, decisions, and outcomes. Be specific about YOUR contribution.", needDoc: null, acceptKind: null },
  behavioral:  { label: "Behavioral Interview", tip: "Use STAR structure (Situation, Task, Action, Result) for challenge, failure, and conflict stories.", needDoc: null, acceptKind: null },
  resume:      { label: "Resume-Based", tip: "Questions target each section of your resume — experience, projects, skills. Be ready to go deep.", needDoc: "resume", acceptKind: "resume" },
  jd:          { label: "JD-Based", tip: "Questions match the job description requirements. The AI will probe fit, gaps, and alignment.", needDoc: "jd", acceptKind: "jd" },
  topic:       { label: "Topic-Based", tip: "Deep drill into your uploaded material. The AI will test your understanding and explanation ability.", needDoc: "any", acceptKind: "topic" },
  mixed:       { label: "Mixed Interview", tip: "Combines HR, technical, and behavioral questions — the full interview loop.", needDoc: null, acceptKind: null },
  custom:      { label: "Custom Interview", tip: "Tell the AI exactly what to focus on. Your material, your rules.", needDoc: null, acceptKind: null },
};

page.innerHTML = `
  <div class="grid g2"><div class="card"><h3>Configuration</h3>
    <div id="typeTip" class="small" style="margin:8px 0;padding:8px;background:var(--bg-soft);border-radius:6px"></div>
    <label class="fl">Interview type</label><select id="s_type">${TYPES.map((t) => `<option ${t === selType ? "selected" : ""}>${TYPE_META[t].label}</option>`).join("")}</select>
    <div id="customBox" style="display:${selType === "custom" ? "" : "none"}">
      <label class="fl">Custom focus</label><input type="text" id="s_custom" placeholder="e.g. system design + leadership" style="width:100%"/></div>
    <label class="fl">Role</label><input type="text" id="s_role" placeholder="e.g. Software Engineer" style="width:100%" value="${esc(prefs.get("role", ""))}"/>
    <label class="fl">Difficulty</label><select id="s_diff">
      ${["beginner", "intermediate", "advanced", "expert"].map((d) => `<option ${d === prefs.get("diff", "intermediate") ? "selected" : ""}>${d}</option>`).join("")}</select>
    <label class="fl">Number of questions</label><select id="s_n"><option>3</option><option selected>5</option><option>7</option><option>10</option></select>
  </div>
  <div class="card"><h3>Documents & devices</h3>
    <div id="docSection"></div>
    <label class="fl">Devices</label><div class="row"><button id="bCam">Camera: off</button><button id="bMic">Mic: off</button></div>
    <div class="row mt"><button class="primary" id="bGo">Start interview</button><a class="btn ghost" href="/interview">Back</a></div>
    <div id="err" class="small mt" style="color:var(--bad)"></div>
  </div></div>`;

const media = createMedia();
let ALL_DOCS = [];

document.getElementById("bCam").onclick = async (e) => {
  alert("Camera turns on in the live room. Setup only records your choice.");
  prefs.set("cam", !prefs.get("cam", false));
  e.target.textContent = `Camera: ${prefs.get("cam") ? "on" : "off"}`;
};
document.getElementById("bCam").textContent = `Camera: ${prefs.get("cam", false) ? "on" : "off"}`;
document.getElementById("bMic").onclick = (e) => {
  prefs.set("mic", !prefs.get("mic", false));
  e.target.textContent = `Mic: ${prefs.get("mic", false) ? "on" : "off"}`;
};
document.getElementById("bMic").textContent = `Mic: ${prefs.get("mic", false) ? "on" : "off"}`;

function getSelectedType() {
  const idx = document.getElementById("s_type").selectedIndex;
  return TYPES[idx];
}

async function refreshDocs() {
  try { ALL_DOCS = (await api.docs("interview")).documents || []; } catch {}
  renderDocSection();
}

function renderDocSection() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  const docSection = document.getElementById("docSection");

  if (!meta.needDoc) {
    docSection.innerHTML = `<div class="small dim" style="margin-bottom:8px">No documents needed — questions are general for this type.</div>`;
    return;
  }

  const docs = ALL_DOCS;
  const acceptKind = meta.acceptKind;

  // Filter docs relevant to this type
  const relevant = acceptKind ? docs.filter((d) => d.kind === acceptKind) : docs;
  const hasRequired = relevant.length > 0;

  // Build existing docs list
  let existingDocsHtml = "";
  if (docs.length) {
    const checkAll = hasRequired;
    existingDocsHtml = `
      <div class="small" style="margin:8px 0 4px">Your documents:</div>
      ${docs.map((d) => {
        const isRelevant = !acceptKind || d.kind === acceptKind;
        return `<label style="display:block;font-weight:400;${isRelevant ? "" : "opacity:0.5"}">
          <input type="checkbox" data-doc="${d.id}" ${isRelevant ? "checked" : ""}/>
          ${esc(d.filename)} <span class="dim">(${esc(KIND_LABEL[d.kind] || d.kind)})</span>
          ${isRelevant && acceptKind ? `<span style="color:var(--good)">✓</span>` : ""}
        </label>`;
      }).join("")}`;
  }

  // Upload + paste section
  const uploadHtml = `
    <div style="border:1px dashed var(--line);border-radius:6px;padding:12px;margin-top:8px">
      <div class="small" style="font-weight:600;margin-bottom:6px">Add ${acceptKind ? KIND_LABEL[acceptKind] || "document" : "document"}</div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <label class="btn" style="cursor:pointer;margin:0">
          Upload file <input type="file" id="docFile" accept=".pdf,.docx,.txt,.md" style="display:none"/>
        </label>
        <button class="ghost" id="bPaste" type="button">Paste text</button>
      </div>
      <div id="uploadStatus" class="small mut mt"></div>
      <div id="pasteBox" style="display:none;margin-top:8px">
        <textarea id="pasteText" rows="6" placeholder="Paste your resume, job description, or topic text here…" style="width:100%;font-family:inherit;font-size:13px;resize:vertical"></textarea>
        <div class="row mt" style="gap:6px">
          <select id="pasteKind" style="width:auto">
            ${acceptKind ? `<option value="${acceptKind}" selected>${KIND_LABEL[acceptKind] || acceptKind}</option>` : ""}
            <option value="resume" ${acceptKind === "resume" ? "" : ""}>Resume / CV</option>
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

  // Status banner
  let banner = "";
  if (!docs.length) {
    banner = `<div style="padding:8px;background:var(--bg-soft);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--warn)">⚠ No documents yet — upload or paste your ${acceptKind ? KIND_LABEL[acceptKind]?.toLowerCase() || "material" : "material"} below.</div></div>`;
  } else if (!hasRequired && acceptKind) {
    banner = `<div style="padding:8px;background:var(--bg-soft);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--warn)">⚠ No ${KIND_LABEL[acceptKind]?.toLowerCase() || "matching"} documents found — upload or paste one below for targeted questions.</div></div>`;
  } else if (hasRequired) {
    banner = `<div style="padding:6px;background:rgba(52,211,153,0.1);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--good)">✓ ${relevant.length} ${KIND_LABEL[acceptKind]?.toLowerCase() || "matching"} document${relevant.length > 1 ? "s" : ""} ready — questions will be tailored.</div></div>`;
  }

  docSection.innerHTML = banner + existingDocsHtml + uploadHtml;

  // Wire up file upload
  document.getElementById("docFile").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const status = document.getElementById("uploadStatus");
    status.innerHTML = `Uploading <b>${esc(f.name)}</b>…`;
    try {
      const r = await api.uploadDoc(f, acceptKind || "document", "interview");
      if (r.error) { status.innerHTML = `<span style="color:var(--bad)">Failed: ${esc(r.error)}</span>`; return; }
      status.innerHTML = `<span style="color:var(--good)">✓ Uploaded (${(r.chars / 1000).toFixed(1)}k chars)</span>`;
      await refreshDocs();
      // Auto-check the new doc
      const newCb = document.querySelector(`[data-doc="${r.doc_id}"]`);
      if (newCb) newCb.checked = true;
    } catch { status.innerHTML = `<span style="color:var(--bad)">Upload failed — server unreachable.</span>`; }
  };

  // Wire up paste toggle
  const bPaste = document.getElementById("bPaste");
  const pasteBox = document.getElementById("pasteBox");
  if (bPaste) {
    bPaste.onclick = () => {
      const shown = pasteBox.style.display !== "none";
      pasteBox.style.display = shown ? "none" : "";
      if (!shown) document.getElementById("pasteText").focus();
    };
  }

  // Wire up paste save
  const bSavePaste = document.getElementById("bSavePaste");
  if (bSavePaste) {
    bSavePaste.onclick = async () => {
      const text = document.getElementById("pasteText").value.trim();
      const kind = document.getElementById("pasteKind").value;
      const status = document.getElementById("pasteStatus");
      if (!text) { status.innerHTML = `<span style="color:var(--warn)">Paste some text first.</span>`; return; }
      status.innerHTML = `Saving…`;
      try {
        const r = await api.pasteDoc(text, kind, `${KIND_LABEL[kind] || "pasted"}.txt`, "interview");
        if (r.error) { status.innerHTML = `<span style="color:var(--bad)">Failed: ${esc(r.error)}</span>`; return; }
        status.innerHTML = `<span style="color:var(--good)">✓ Saved (${(r.chars / 1000).toFixed(1)}k chars)</span>`;
        document.getElementById("pasteText").value = "";
        await refreshDocs();
        const newCb = document.querySelector(`[data-doc="${r.doc_id}"]`);
        if (newCb) newCb.checked = true;
      } catch { status.innerHTML = `<span style="color:var(--bad)">Save failed.</span>`; }
    };
  }

  // Wire up paste cancel
  const bCancelPaste = document.getElementById("bCancelPaste");
  if (bCancelPaste) {
    bCancelPaste.onclick = () => { pasteBox.style.display = "none"; };
  }
}

function updateTip() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  document.getElementById("typeTip").textContent = meta.tip;
  document.getElementById("customBox").style.display = type === "custom" ? "" : "none";
  renderDocSection();
}

document.getElementById("s_type").onchange = updateTip;

(async () => { await refreshDocs(); updateTip(); })();

document.getElementById("bGo").onclick = async () => {
  const btn = document.getElementById("bGo");
  const errEl = document.getElementById("err");
  errEl.textContent = "";
  const type = getSelectedType();
  const meta = TYPE_META[type];

  const docIds = [...document.querySelectorAll("[data-doc]:checked")].map((c) => c.dataset.doc);
  const custom = (document.getElementById("s_custom")?.value || "").trim();
  const role = document.getElementById("s_role").value;

  // Validate document requirements
  if (meta.needDoc === "resume" && !docIds.some((id) => ALL_DOCS.find((d) => d.id === id && d.kind === "resume"))) {
    errEl.textContent = "Resume-Based interview requires a resume. Upload or paste one above.";
    return;
  }
  if (meta.needDoc === "jd" && !docIds.some((id) => ALL_DOCS.find((d) => d.id === id && d.kind === "jd"))) {
    errEl.textContent = "JD-Based interview requires a job description. Upload or paste one above.";
    return;
  }
  if (meta.needDoc === "any" && docIds.length === 0 && ALL_DOCS.length > 0) {
    errEl.textContent = "Select at least one document for a Topic-Based interview, or switch to a general type.";
    return;
  }
  if (meta.needDoc === "any" && ALL_DOCS.length === 0) {
    errEl.textContent = "Topic-Based interview requires material. Upload or paste a document above.";
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
