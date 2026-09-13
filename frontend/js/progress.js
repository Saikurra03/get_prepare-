/* Progress Overview: am I improving? Real metrics only. */
const page = buildShell("Progress", "BERREADY / Progress");
page.innerHTML = `<p class="sub">Evidence from your sessions — no vanity metrics.</p>
  <div class="grid g3" id="dims"></div>
  <div class="card mt"><h3>Interview scores over time</h3><div id="trend" class="small mut">Loading…</div></div>
  <div class="grid g2 mt"><div class="card"><h3>Strengths</h3><div id="strBox" class="small mut">…</div></div>
  <div class="card"><h3>Recurring patterns</h3><div id="patBox" class="small mut">…</div></div></div>
  <div class="card mt"><h3>Current training focus</h3><div id="fBox"></div></div>`;
(async () => {
  try {
    const [prof, sess] = await Promise.all([api.profile(), api.sessions()]);
    const list = sess.sessions || [];
    const count = (f) => list.filter(f).length;
    const dims = [
      ["Overall communication", count(() => true), "sessions"],
      ["Interview", count((s) => s.kind === "interview"), "sessions"],
      ["Storytelling", count((s) => s.meta?.scenario === "story"), "sessions"],
      ["Public speaking", count((s) => s.meta?.scenario === "presentation" || s.meta?.scenario === "podcast"), "sessions"],
      ["Wit", count((s) => s.meta?.scenario === "wit"), "sessions"],
      ["Spontaneous Q&A", count((s) => ["spontaneous", "qa"].includes(s.meta?.scenario)), "sessions"],
    ];
    document.getElementById("dims").innerHTML = dims.map(([t, n, u]) =>
      `<div class="card"><div class="small dim">${t}</div><h2>${n} <span class="small dim" style="font-weight:400">${u}</span></h2></div>`).join("");
    document.getElementById("strBox").textContent = (prof.strengths || []).join(", ") || "Emerging — complete more sessions.";
    const pats = prof.recurring_patterns || {};
    document.getElementById("patBox").innerHTML = Object.keys(pats).length
      ? Object.entries(pats).sort((a, b) => b[1] - a[1]).map(([k, v]) => `<span class="score">${esc(k)} ×${v}</span>`).join("")
      : "No repeating patterns yet.";
    const f = prof.training_focus || "—";
    document.getElementById("fBox").innerHTML = `<b>${esc(f)}</b><br/><a class="btn primary mt" href="/practice">Recommended practice →</a>`;
    // trend: last 8 finished interviews, real overall scores
    const ivs = list.filter((s) => s.kind === "interview" && s.status === "finished").slice(-8);
    if (!ivs.length) { document.getElementById("trend").textContent = "No finished interviews yet."; return; }
    const rows = [];
    for (const s of ivs) {
      try { const d = await api.sessionDetail(s.id); if (d.report) rows.push({ t: s.created, v: d.report.overall }); } catch {}
    }
    document.getElementById("trend").innerHTML = rows.length ? rows.map((r) =>
      `<div class="row" style="gap:12px"><span class="dim" style="width:150px">${esc(fmtT(r.t))}</span>
       <span style="flex:1;background:var(--bg2);border-radius:6px"><span style="display:block;height:10px;border-radius:6px;background:var(--acc);width:${(r.v || 0) * 10}%"></span></span>
       <b>${r.v ?? "—"}/10</b></div>`).join("") : "No scored interviews yet.";
  } catch { page.innerHTML += `<div class="card mt">Server unreachable.</div>`; }
})();
