/* Interview Preparation: upload → states → understood → generate. Real doc data only. */
const page = buildShell("Preparation", "BERREADY / Interview / Preparation");
const KIND_LABEL = { jd: "Job Description", resume: "Resume / CV", topic: "Topic PDF", project: "Project Report", company: "Company Information", questions: "Custom Questions / Material", document: "Other material" };
page.innerHTML = `
  <p class="sub">What material should the AI use? Only selected documents feed your interview — nothing silent.</p>
  <div class="card"><h3>Add material</h3><div class="row">
    <select id="kind">${Object.entries(KIND_LABEL).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select>
    <input type="file" id="file" accept=".pdf,.docx,.txt,.md"/>
    <button class="primary" id="bUp">Upload</button></div>
    <div id="flow" class="small mut mt">Uploading → Processing → Analyzing → Ready</div></div>
  <div class="card mt"><h3>My documents</h3><div id="docs">Loading…</div></div>
  <div class="card mt"><h3>What the system understood</h3><div id="understood" class="small mut">Upload a resume and JD to see skills, overlap and gaps.</div></div>
  <div class="card mt"><div class="row"><a class="btn primary" id="bGen" href="/interview-setup">Generate interview →</a></div></div>`;

async function refresh() {
  let docs = [];
  try { docs = (await api.docs()).documents || []; } catch { document.getElementById("docs").textContent = "Server unreachable."; return; }
  document.getElementById("docs").innerHTML = docs.length ? `<table class="t"><tr><th>File</th><th>Type</th><th>Size</th><th>Status</th><th></th></tr>` +
    docs.map((d) => `<tr><td>${esc(d.filename)}</td><td>${esc(KIND_LABEL[d.kind] || d.kind)}</td>
      <td>${(d.chars / 1000).toFixed(1)}k chars</td>
      <td><span class="pill ok">${esc(d.status)}</span></td>
      <td><button class="ghost" data-rm="${d.id}">Remove</button></td></tr>`).join("") + `</table>`
    : `<span class="dim">No documents yet.</span>`;
  document.querySelectorAll("[data-rm]").forEach((b) => b.onclick = async () => {
    await api.post("/api/documents/remove", { doc_id: b.dataset.rm }); refresh();
  });
  // understood: from full docs (signals recomputed client-side would need text; use stored excerpt via detail? keep honest: show kinds/coverage)
  const hasJd = docs.some((d) => d.kind === "jd"), hasResume = docs.some((d) => d.kind === "resume"), hasTopic = docs.some((d) => d.kind === "topic");
  const areas = [];
  if (hasResume) areas.push("resume projects & experience");
  if (hasJd) areas.push("role requirements & responsibilities");
  if (hasTopic) areas.push("technical topics");
  document.getElementById("understood").innerHTML = areas.length
    ? `Interview can target: <b>${areas.map(esc).join(", ")}</b>. Skill overlap and gap analysis runs automatically when you generate the interview.`
    : `Upload a resume and JD to see skills, overlap and gaps.`;
  const last = sessionStorage.getItem("br:lastSignals");
  if (last) { try { const s = JSON.parse(last);
    document.getElementById("understood").innerHTML += `<div class="mt">Last analyzed — resume skills: <b>${esc((s.resume_skills || []).slice(0, 8).join(", "))}</b><br/>
      JD skills: <b>${esc((s.jd_skills || []).slice(0, 8).join(", "))}</b><br/>
      Overlap: <b>${esc((s.overlap || []).join(", ") || "—")}</b> · Gaps: <b>${esc((s.gaps || []).join(", ") || "—")}</b></div>`;
  } catch {} }
}
document.getElementById("bUp").onclick = async () => {
  const f = document.getElementById("file").files[0];
  if (!f) { alert("Choose a PDF, DOCX or TXT file first."); return; }
  const flow = document.getElementById("flow");
  flow.innerHTML = `Uploading <b>${esc(f.name)}</b> → Processing…`;
  try {
    const r = await api.uploadDoc(f, document.getElementById("kind").value);
    if (r.error) { flow.innerHTML = `<span class="pill bad">Failed</span> ${esc(r.error)}`; return; }
    flow.innerHTML = `Uploaded → Processing → Analyzing → <span class="pill ok">Ready for Interview</span> (${(r.chars / 1000).toFixed(1)}k chars)`;
    if (r.signals) sessionStorage.setItem("br:lastSignals", JSON.stringify(r.signals));
    document.getElementById("file").value = "";
    refresh();
  } catch { flow.innerHTML = `<span class="pill bad">Failed</span> — server unreachable or file too large.`; }
};
refresh();
