/* Interview Coach: clean landing. Click a type → navigate to Preparation with type pre-selected. */
const ITYPES = [
  ["selfintro", "Self Introduction", "One 'Tell me about yourself' answer — scored on Structure, Clarity, Relevance, Technical Accuracy, Conciseness and Delivery.", "Resume optional."],
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
  <div class="card" style="background:var(--clay-card);border-radius:var(--radius-lg);padding:var(--space-lg)var(--space-xl);margin-bottom:var(--space-lg)">
    <p class="sub" style="margin:0">A realistic AI interviewer — adaptive follow-ups, minimal interruption, full report at the end.</p>
  </div>
  <div class="grid g2 mb" style="gap:var(--space-md)">
    <div class="card mode" style="flex:1;min-height:0">
      <div class="m-ic">⛶</div>
      <div><h3>Full-screen mock room</h3><p style="flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-line-height:1.4;">Immersive, distraction-free interview — camera, timer, progress dots, report at the end.</p></div>
      <a class="btn primary go" href="/mock">Enter room</a>
    </div>
    <div class="card mode" style="flex:1;min-height:0">
      <div class="m-ic">☰</div>
      <div><h3>Your question list</h3><p style="flex:1;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-line-height:1.4;">Upload or paste your own questions — count, difficulty and order are yours. The AI never invents them.</p></div>
      <a class="btn primary go" href="/qbank">Build list</a>
    </div>
  </div>
  <div class="grid g2"id="types"></div>`;