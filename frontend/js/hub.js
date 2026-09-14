/* Interview Hub: what interview do I want to practice? Shows doc requirements per type. */
const ITYPES = [
  ["hr", "HR Interview", "Confidence, clarity, storytelling.", "Presence and relevance.", null],
  ["technical", "Technical Interview", "Correctness + clear explanation.", "Reasoning out loud.", null],
  ["project", "Project Interview", "Your work, decisions, outcomes.", "Ownership and depth.", null],
  ["behavioral", "Behavioral Interview", "Challenge, failure, conflict stories.", "STAR structure.", null],
  ["resume", "Resume-Based", "Questions from your resume sections — experience, projects, skills.", "Needs a resume upload.", "resume"],
  ["jd", "JD-Based", "Questions matched to the job description — requirements, gaps, fit.", "Needs a JD upload.", "jd"],
  ["topic", "Topic-Based", "Deep drill into your uploaded material.", "Needs a topic/document upload.", "any"],
  ["mixed", "Mixed Interview", "HR + technical + behavioral — the full loop.", "No documents needed.", null],
  ["custom", "Custom Interview", "Your focus, your material — tell the AI what to probe.", "No documents needed.", null],
];

const page = buildShell("Interview coach", "BERREADY / Interview");
page.innerHTML = `
  <p class="sub">A realistic AI interviewer — adaptive follow-ups, minimal interruption, full report at the end.</p>
  <div class="card mb"><div class="row"><div><h3>Prepare with your documents</h3>
    <p class="sub" style="margin:0">Upload resume, JD or topic material so questions target you — <span id="docCount">…</span></p></div>
    <span style="flex:1"></span><a class="btn primary" href="/prepare">Open preparation</a></div></div>
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
  document.getElementById("types").innerHTML = ITYPES.map(([k, t, d, f, need]) => {
    let badge = "";
    let hint = "";
    if (need === "resume") {
      if (DOC_MAP.resume) {
        badge = `<span class="pill ok">Resume ready</span>`;
      } else {
        badge = `<span class="pill warn">Resume needed</span>`;
        hint = `<div class="small" style="color:var(--warn);margin-top:4px">Upload a resume for section-specific questions.</div>`;
      }
    } else if (need === "jd") {
      if (DOC_MAP.jd) {
        badge = `<span class="pill ok">JD ready</span>`;
      } else {
        badge = `<span class="pill warn">JD needed</span>`;
        hint = `<div class="small" style="color:var(--warn);margin-top:4px">Upload a job description for matched questions.</div>`;
      }
    } else if (need === "any") {
      const docCount = Object.values(DOC_MAP).reduce((a, b) => a + b, 0);
      if (docCount) {
        badge = `<span class="pill ok">${docCount} doc${docCount > 1 ? "s" : ""} ready</span>`;
      } else {
        badge = `<span class="pill warn">Material needed</span>`;
        hint = `<div class="small" style="color:var(--warn);margin-top:4px">Upload topic material for targeted questions.</div>`;
      }
    }
    return `<div class="card mode"><div class="m-ic">◈</div><div><h3>${t}</h3><p>${d} Focus: ${f}</p>${badge}${hint}</div>
     <a class="btn primary go" href="/interview-setup?type=${k}">Start</a></div>`;
  }).join("");
}
