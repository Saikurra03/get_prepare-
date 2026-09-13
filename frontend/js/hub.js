/* Interview Hub: what interview do I want to practice? */
const ITYPES = [
  ["hr", "HR Interview", "Confidence, clarity, storytelling.", "Presence and relevance."],
  ["technical", "Technical Interview", "Correctness + clear explanation.", "Reasoning out loud."],
  ["project", "Project Interview", "Your work, decisions, outcomes.", "Ownership and depth."],
  ["behavioral", "Behavioral Interview", "Challenge, failure, conflict stories.", "STAR structure."],
  ["resume", "Resume-Based", "Questions from your resume.", "Needs a resume upload."],
  ["jd", "JD-Based", "Questions from the job description.", "Needs a JD upload."],
  ["topic", "Topic-Based", "Drilled on your material.", "Needs a topic PDF."],
  ["mixed", "Mixed Interview", "HR + technical + behavioral.", "The full loop."],
  ["custom", "Custom Interview", "Your focus, your material.", "Tell the AI what to probe."],
];
const page = buildShell("Interview coach", "BERREADY / Interview");
page.innerHTML = `
  <p class="sub">A realistic AI interviewer — adaptive follow-ups, minimal interruption, full report at the end.</p>
  <div class="card mb"><div class="row"><div><h3>Prepare with your documents</h3>
    <p class="sub" style="margin:0">Upload resume, JD or topic material so questions target you — <span id="docCount">…</span></p></div>
    <span style="flex:1"></span><a class="btn primary" href="/prepare">Open preparation</a></div></div>
  <div class="grid g2" id="types"></div>`;
document.getElementById("types").innerHTML = ITYPES.map(([k, t, d, f]) =>
  `<div class="card mode"><div class="m-ic">◈</div><div><h3>${t}</h3><p>${d} Focus: ${f}</p></div>
   <a class="btn primary go" href="/interview-setup?type=${k}">Start</a></div>`).join("");
(async () => { try { const d = await api.docs(); document.getElementById("docCount").textContent = `${d.documents.length} document(s) ready`; } catch {} })();
