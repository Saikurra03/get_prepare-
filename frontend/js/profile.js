/* Profile = long-term performance dashboard. Real data only. */
const page = buildShell("My performance", "BERREADY / Progress / Profile");
page.innerHTML = `<div id="box"><div class="card">Loading your performance…</div></div>`;
(async () => {
  let d;
  try { d = await api.dashboard(); }
  catch { document.getElementById("box").innerHTML = `<div class="card">Server unreachable.</div>`; return; }
  const secs = d.sections || {};
  const secNames = ["Interviews", "Communication", "Storytelling", "Public Speaking", "Q&A", "Wit", "Podcast"];
  document.getElementById("box").innerHTML = `
    <div class="card"><div class="small dim">Performance summary · ${d.sessions_completed ?? 0} completed sessions</div>
      ${(d.summary_lines || []).map((l) => `<p style="margin:6px 0">${esc(l)}</p>`).join("")}</div>
    <div class="card mt"><h3>Section-wise performance</h3>
      <div class="grid g3">${secNames.map((s) => `<div><div class="small dim">${s}</div>
        <h2>${secs[s] ?? 0}</h2>${s === "Interviews" && d.interview_avg != null ? `<div class="small dim">avg ${d.interview_avg}/10</div>` : `<div class="small dim">sessions</div>`}</div>`).join("")}</div>
      ${Object.keys(d.by_type || {}).length ? `<div class="small mut mt">By interview type: ${Object.entries(d.by_type).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")}</div>` : ""}</div>
    <div class="grid g2 mt">
      <div class="card"><h3>Observed strengths</h3><div class="small">${esc((d.strengths || []).join(", ") || "Emerging — complete more sessions.")}</div></div>
      <div class="card"><h3>Recurring problems</h3><div class="small">${esc((d.recurring || []).join(", ") || "None flagged yet.")}</div></div>
    </div>
    <div class="card mt"><h3>Current training focus</h3><b>${esc(d.focus || "—")}</b>
      <div class="row mt"><a class="btn primary" href="/practice">Practice this →</a></div></div>
    <div class="card mt"><h3>Recent sessions</h3>
      ${(d.recent || []).length ? `<table class="t"><tr><th>Date</th><th>Type</th><th>Status</th><th></th></tr>` +
        d.recent.map((s) => `<tr><td>${esc(fmtT(s.created))}</td><td>${esc(s.detail || s.kind)}</td><td>${esc(s.status)}</td><td><a href="/history?sid=${s.id}">Open</a></td></tr>`).join("") + `</table>`
        : `<span class="dim">No sessions yet.</span>`}</div>`;
})();
