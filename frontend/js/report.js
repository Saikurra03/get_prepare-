/* Interview Report: overall, strengths, weakness, best/worst, comms, technical, alignment, training. */
const sid = new URLSearchParams(location.search).get("sid");
const page = buildShell("Interview report", "BERREADY / Interview / Report");
page.innerHTML = `<div class="card">Loading your report…</div>`;
(async () => {
  if (!sid) { page.innerHTML = `<div class="card">No session selected. <a href="/interview">Start one</a>.</div>`; return; }
  let d;
  try { d = await api.sessionDetail(sid); } catch { page.innerHTML = `<div class="card">Server unreachable.</div>`; return; }
  if (d.error || !d.report) { page.innerHTML = `<div class="card">Report not ready. <a href="/interview-live?sid=${sid}">Back to interview</a>.</div>`; return; }
  const r = d.report;
  const sec = (t, body) => body ? `<div class="card mt"><h3>${t}</h3><div class="small">${body}</div></div>` : "";
  page.innerHTML = `
    <div class="card"><div class="small dim">${esc(d.meta?.role || "")} · ${esc(d.meta?.type || "")} · ${esc(fmtT(d.created))}</div>
      <h2>Overall: ${r.overall ?? "—"}/10 <span class="dim" style="font-size:13px;font-weight:400">(${r.answers_evaluated ?? 0} answers)</span></h2>
      <p>${esc(r.summary || "")}</p></div>
    <div class="grid g2 mt">
      <div class="card"><h3>Strongest areas</h3><div class="small">${esc((r.strengths || []).join(" · ") || "—")}</div></div>
      <div class="card"><h3>Biggest weakness</h3><div class="small">${esc(r.biggest_weakness || "—")}</div></div>
    </div>
    <div class="grid g2 mt">
      <div class="card"><h3>Best answer</h3><div class="small">${esc(r.best_answer?.question || "—")} <span class="score">${r.best_answer?.score ?? ""}</span></div></div>
      <div class="card"><h3>Weakest answer</h3><div class="small">${esc(r.weakest_answer?.question || "—")}<br/><span class="dim">Issue: ${esc(r.weakest_answer?.issue || "—")}</span></div>
        <div class="row mt"><a class="btn" href="/workspace?mode=qa">Retry it in Q&A</a></div></div>
    </div>
    ${sec("Communication", esc(r.communication || ""))}
    ${sec("Technical performance", esc(r.technical || ""))}
    ${sec("Role alignment", esc(r.role_alignment || ""))}
    ${sec("Recurring problems", esc((r.recurring_problems || []).join(" · ") || "—"))}
    ${sec("Answer relevance", esc(r.relevance_summary || ""))}
    ${sec("Sentence & grammar patterns", esc(r.sentence_patterns || ""))}
    ${sec("Pronunciation / articulation", esc(r.pronunciation_note || ""))}
    <div class="card mt"><h3>Most important improvement</h3><div class="small"><b>${esc(r.top_priority || r.biggest_weakness || "—")}</b></div></div>
    <div class="card mt"><h3>Next training target</h3><div class="small">${(r.training || []).map((t) => `• ${esc(t)}`).join("<br/>") || "—"}
    <br/>Recommended next session: <b>${esc(r.next_practice || "—")}</b></div>
    <div class="card mt"><h3>Next training target</h3><div class="small">${(r.training || []).map((t) => `• ${esc(t)}`).join("<br/>") || "—"}</div>
      <div class="row mt"><a class="btn primary" href="/practice">Train now</a>
      <a class="btn ghost" href="/history">All sessions</a></div></div>`;
})();
