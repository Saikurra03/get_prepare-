/* Communication Profile: what does the AI know about my patterns? Evidence-based. */
const page = buildShell("Profile", "BERREADY / Progress / Profile");
page.innerHTML = `<p class="sub">Built across sessions — never from a single one.</p><div id="box"><div class="card">Loading…</div></div>`;
(async () => {
  try {
    const p = await api.profile();
    const pats = p.recurring_patterns || {};
    document.getElementById("box").innerHTML = `
      <div class="grid g3">
        <div class="card"><h3>Sessions</h3><h2>${p.sessions_completed ?? 0}</h2><div class="small dim">Avg interview score: ${p.avg_score ?? "—"}</div></div>
        <div class="card"><h3>Strengths</h3><div class="small">${esc((p.strengths || []).join(", ") || "Emerging")}</div></div>
        <div class="card"><h3>Weaknesses</h3><div class="small">${esc((p.weaknesses || []).join(", ") || "None flagged")}</div></div>
      </div>
      <div class="card mt"><h3>Recurring patterns</h3>
        ${Object.keys(pats).length ? Object.entries(pats).sort((a, b) => b[1] - a[1]).map(([k, v]) => `<span class="score">${esc(k)} ×${v}</span>`).join("") : `<span class="dim">No repeating patterns yet — they appear after a few sessions.</span>`}</div>
      <div class="grid g2 mt">
        <div class="card"><h3>Voice & visual presence</h3><div class="small mut">Tracked from your session signals: fillers, pacing, structure, camera presence notes. Detail accumulates as you practice.</div></div>
        <div class="card"><h3>Answer quality & memorability</h3><div class="small mut">Interview scores and retry comparisons feed this over time.</div></div>
      </div>
      <div class="card mt"><h3>Current training focus</h3><b>${esc(p.training_focus || "—")}</b>
        <div class="row mt"><a class="btn primary" href="/practice">Practice this →</a></div></div>`;
  } catch { document.getElementById("box").innerHTML = `<div class="card">Server unreachable.</div>`; }
})();
