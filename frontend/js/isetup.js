/* Interview Setup: per-type configuration, document validation, guidance. Then start. */
const qs = new URLSearchParams(location.search);
const page = buildShell("Interview setup", "BERREADY / Interview / Setup");
const TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"];
const selType = qs.get("type") || "mixed";

const TYPE_META = {
  hr:          { label: "HR Interview", tip: "Focus on presence, clarity, and storytelling. The AI will test how you present yourself.", needDoc: null },
  technical:   { label: "Technical Interview", tip: "Focus on correctness and reasoning out loud. Explain your thought process step by step.", needDoc: null },
  project:     { label: "Project Interview", tip: "Focus on ownership, decisions, and outcomes. Be specific about YOUR contribution.", needDoc: null },
  behavioral:  { label: "Behavioral Interview", tip: "Use STAR structure (Situation, Task, Action, Result) for challenge, failure, and conflict stories.", needDoc: null },
  resume:      { label: "Resume-Based", tip: "Questions target each section of your resume — experience, projects, skills. Be ready to go deep.", needDoc: "resume" },
  jd:          { label: "JD-Based", tip: "Questions match the job description requirements. The AI will probe fit, gaps, and alignment.", needDoc: "jd" },
  topic:       { label: "Topic-Based", tip: "Deep drill into your uploaded material. The AI will test your understanding and explanation ability.", needDoc: "any" },
  mixed:       { label: "Mixed Interview", tip: "Combines HR, technical, and behavioral questions — the full interview loop.", needDoc: null },
  custom:      { label: "Custom Interview", tip: "Tell the AI exactly what to focus on. Your material, your rules.", needDoc: null },
};

page.innerHTML = `
  <div class="grid g2"><div class="card"><h3 id="cfgTitle">Configuration</h3>
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

function renderDocSection() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  const docSection = document.getElementById("docSection");

  if (!meta.needDoc) {
    docSection.innerHTML = `<div class="small dim" style="margin-bottom:8px">No documents required for ${esc(meta.label)} — questions are general.</div>`;
    return;
  }

  const docs = ALL_DOCS;
  let required = [];
  let filterFn;
  if (meta.needDoc === "resume") {
    required = docs.filter((d) => d.kind === "resume");
    filterFn = (d) => d.kind === "resume";
  } else if (meta.needDoc === "jd") {
    required = docs.filter((d) => d.kind === "jd");
    filterFn = (d) => d.kind === "jd";
  } else {
    required = docs;
    filterFn = null;
  }

  const filtered = filterFn ? docs.filter(filterFn) : docs;
  const hasRequired = required.length > 0;

  if (!docs.length) {
    docSection.innerHTML = `
      <div style="padding:10px;background:var(--bg-soft);border-radius:6px;margin-bottom:8px">
        <div class="small" style="color:var(--bad);font-weight:600">⚠ No documents uploaded</div>
        <div class="small dim">${esc(meta.label)} works best with uploaded material.
          <a href="/prepare" style="color:var(--acc)">Upload now →</a></div>
      </div>`;
    return;
  }

  if (!hasRequired) {
    const needLabel = meta.needDoc === "resume" ? "a resume" : meta.needDoc === "jd" ? "a job description" : "topic material";
    docSection.innerHTML = `
      <div style="padding:10px;background:var(--bg-soft);border-radius:6px;margin-bottom:8px">
        <div class="small" style="color:var(--warn);font-weight:600">⚠ No ${needLabel} found</div>
        <div class="small dim">Upload ${needLabel} for targeted questions, or start with general questions.
          <a href="/prepare" style="color:var(--acc)">Upload →</a></div>
      </div>
      <div class="small dim">Available documents:</div>
      ${docs.map((d) => `<label style="display:block;font-weight:400"><input type="checkbox" data-doc="${d.id}" /> ${esc(d.filename)} <span class="dim">(${esc(d.kind)})</span></label>`).join("")}
      <p class="small dim">Checked documents will provide extra context.</p>`;
    return;
  }

  docSection.innerHTML = `
    <div style="padding:8px;background:rgba(52,211,153,0.1);border-radius:6px;margin-bottom:8px">
      <div class="small" style="color:var(--good)">✓ ${required.length} ${meta.needDoc} document${required.length > 1 ? "s" : ""} ready</div>
      <div class="small dim">Questions will target your ${meta.needDoc === "resume" ? "resume sections" : meta.needDoc === "jd" ? "job description match" : "uploaded material"}.</div>
    </div>
    ${filtered.map((d) => `<label style="display:block;font-weight:400"><input type="checkbox" data-doc="${d.id}" checked/> ${esc(d.filename)} <span class="dim">(${esc(d.kind)})</span></label>`).join("")}
    ${docs.length > filtered.length ? `<div class="small dim mt">Other documents (optional context):</div>` + docs.filter((d) => !filterFn(d)).map((d) => `<label style="display:block;font-weight:400"><input type="checkbox" data-doc="${d.id}"/> ${esc(d.filename)} <span class="dim">(${esc(d.kind)})</span></label>`).join("") : ""}
    <p class="small dim">Only checked documents feed this interview. <a href="/prepare">Manage</a></p>`;
}

function updateTip() {
  const type = getSelectedType();
  const meta = TYPE_META[type];
  document.getElementById("typeTip").textContent = meta.tip;
  document.getElementById("customBox").style.display = type === "custom" ? "" : "none";
  renderDocSection();
}

document.getElementById("s_type").onchange = updateTip;

(async () => {
  try {
    ALL_DOCS = (await api.docs()).documents || [];
  } catch {}
  updateTip();
})();

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
    errEl.textContent = "Resume-Based interview requires a resume upload. Upload one in Preparation first.";
    return;
  }
  if (meta.needDoc === "jd" && !docIds.some((id) => ALL_DOCS.find((d) => d.id === id && d.kind === "jd"))) {
    errEl.textContent = "JD-Based interview requires a job description upload. Upload one in Preparation first.";
    return;
  }
  if (meta.needDoc === "any" && docIds.length === 0 && ALL_DOCS.length > 0) {
    errEl.textContent = "Select at least one document for a Topic-Based interview, or switch to a general type.";
    return;
  }
  if (meta.needDoc === "any" && ALL_DOCS.length === 0) {
    errEl.textContent = "Topic-Based interview requires uploaded material. Upload a document in Preparation first.";
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
