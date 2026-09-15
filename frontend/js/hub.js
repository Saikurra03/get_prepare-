/* Interview Coach: clean landing. Click a type → navigate to Preparation with type pre-selected. */
const ITYPES = [
  ["hr", "HR Interview", "Confidence, clarity, storytelling.", "Presence and relevance."],
  ["technical", "Technical Interview", "Correctness + clear explanation.", "Reasoning out loud."],
  ["project", "Project Interview", "Your work, decisions, outcomes.", "Ownership and depth."],
  ["behavioral", "Behavioral Interview", "Challenge, failure, conflict stories.", "STAR structure."],
  ["resume", "Resume-Based", "Questions from your resume — experience, projects, skills.", "Needs a resume upload."],
  ["jd", "JD-Based", "Questions matched to the job description — requirements, gaps, fit.", "Needs a JD upload."],
  ["topic", "Topic-Based", "Deep drill into your uploaded material.", "Needs a topic/document."],
  ["mixed", "Mixed Interview", "HR + technical + behavioral — the full loop.", "No documents needed."],
  ["custom", "Custom Interview", "Your focus, your material — tell the AI what to probe.", "No documents needed."],
];

const page = buildShell("Interview coach", "BERREADY / Interview");
page.innerHTML = `
  <p class="sub">A realistic AI interviewer — adaptive follow-ups, minimal interruption, full report at the end.</p>
  <div class="card mb">
    <div class="row">
      <div><h3>Prepare with your documents</h3>
        <p class="sub" style="margin:0">Upload resume, JD or topic material so questions target you — <span id="docCount">…</span></p></div>
      <span style="flex:1"></span>
      <a class="btn primary" href="/prepare">Open preparation</a>
    </div>
  </div>
  <div class="grid g2" id="types"></div>`;

let DOC_MAP = {};
(async () => {
  try {
    const d = await api.docs();
    const docs = d.documents || [];
    document.getElementById("docCount").textContent = `${docs.length} document(s) ready`;
    docs.forEach((doc) => { DOC_MAP[doc.kind] = (DOC_MAP[doc.kind] || 0) + 1; });
  } catch {}
  renderTypes();
})();

function renderTypes() {
  document.getElementById("types").innerHTML = ITYPES.map(([k, t, d, f]) => {
    const need = k === "resume" ? "resume" : k === "jd" ? "jd" : k === "topic" ? "any" : null;
    let badge = "";
    if (need === "resume") {
      badge = DOC_MAP.resume
        ? `<span class="pill ok">Resume ready</span>`
        : `<span class="pill warn">Resume needed</span>`;
    } else if (need === "jd") {
      badge = DOC_MAP.jd
        ? `<span class="pill ok">JD ready</span>`
        : `<span class="pill warn">JD needed</span>`;
    } else if (need === "any") {
      const total = Object.values(DOC_MAP).reduce((a, b) => a + b, 0);
      badge = total
        ? `<span class="pill ok">${total} doc${total > 1 ? "s" : ""} ready</span>`
        : `<span class="pill warn">Material needed</span>`;
    }
    return `<div class="card mode">
      <div class="m-ic">◈</div>
      <div><h3>${t}</h3><p>${d} Focus: ${f}</p>${badge}</div>
      <a class="btn primary go" href="/prepare?type=${k}">Start</a>
    </div>`;
  }).join("");
}
