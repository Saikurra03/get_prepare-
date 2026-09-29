/* Compact post-interview results screen.
   All numbers derive from the stored report of THIS session — no sample data. */
const qsid = new URLSearchParams(location.search).get("sid");
const page = buildShell("Interview results", "BERREADY / Results");

const SKIP = ["[skipped]", "[topic changed]"];
const pct = (n, d) => (d > 0 ? Math.round((n / d) * 100) : null);

function tile(k, v, basis) {
  return `<div class="card res-tile"><div class="k">${k}</div>
    <div class="v">${v}</div><div class="small dim">${basis}</div></div>`;
}

(async () => {
  if (!qsid) { page.innerHTML = `<div class="card">No session selected. <a href="/history">Open history</a></div>`; return; }
  page.innerHTML = `<div class="card">Loading results…</div>`;
  let d;
  try { d = await api.sessionDetail(qsid); } catch { page.innerHTML = `<div class="card">Server unreachable. <a href="/history">Back to history</a></div>`; return; }
  if (d.error) { page.innerHTML = `<div class="card">Session not found. <a href="/history">Back to history</a></div>`; return; }
  const r = d.report;
  if (!r) {
    page.innerHTML = `<div class="card"><h2>Report not ready</h2>
      <p class="mut">This session has no stored report${d.status === "finished" ? "" : " — the interview is still in progress"}.</p>
      <div class="row mt"><a class="btn primary" href="/history">Back to history</a>
      ${d.status === "active" ? `<a class="btn" href="/interview">Start an interview</a>` : ""}</div></div>`;
    return;
  }

  const details = r.question_details || [];
  const real = details.filter((qd) => !SKIP.includes((qd.answer || "").trim()));
  const skipped = details.length - real.length;
  const withEv = real.filter((qd) => qd.evaluation && qd.evaluation.score != null);
  const scores = withEv.map((qd) => Number(qd.evaluation.score));
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;

  // Overall: measured mean of every answered (non-skipped) question.
  const overall10 = r.overall != null ? Number(r.overall) : avg;
  const overall100 = overall10 != null ? Math.round(overall10 * 10) : null;

  // Relevance: verdicts measured per answer.
  const withRel = real.filter((qd) => qd.evaluation && qd.evaluation.relevance && qd.evaluation.relevance.verdict);
  const direct = withRel.filter((qd) => qd.evaluation.relevance.verdict === "directly").length;
  const relPct = pct(direct, withRel.length);

  // Conciseness / Completeness: from deterministic transcript signals (if captured).
  const withSig = real.filter((qd) => qd.evaluation && qd.evaluation.signals);
  const concPct = pct(withSig.filter((qd) => !qd.evaluation.signals.long_sentences).length, withSig.length);
  const compPct = pct(withSig.filter((qd) => Number(qd.evaluation.signals.word_count) >= 20).length, withSig.length);

  // Communication metrics from actual signals.
  const fillers = withSig.reduce((a, qd) => a + (qd.evaluation.signals.filler_total || 0), 0);
  const hedges = withSig.reduce((a, qd) => a + (qd.evaluation.signals.qualifier_total || 0), 0);
  const words = withSig.reduce((a, qd) => a + (qd.evaluation.signals.word_count || 0), 0);
  const per100 = words > 0 ? (fillers / words) * 100 : null;
  const fillerLevel = per100 == null ? "—" : per100 < 1 ? "very low" : per100 < 2 ? "low" : per100 < 3.5 ? "moderate" : "high";
  const avgWords = real.length && words ? Math.round(words / real.length) : null;

  const total = d.meta?.num_questions || details.length || null;
  const strengths = (r.strengths || []).filter(Boolean);
  const training = (r.training || []).filter(Boolean).slice(0, 3);
  const recurring = r.recurring_problems || [];
  const date = fmtT(d.created || d.meta?.created);
  const itype = d.meta?.type || d.kind;
  const role = d.meta?.role || "";

  const scoreBig = overall100 != null ? `${overall100}` : "—";
  const answeredLine = [
    total ? `${real.length} of ${total} questions answered` : `${real.length} answers`,
    skipped ? `${skipped} skipped` : null, itype, date,
  ].filter(Boolean).join(" · ");

  page.innerHTML = `
  <div class="card">
    <div class="res-hero">
      <div class="res-score">${scoreBig}<span class="res-of">/100</span></div>
      <div class="res-meter">
        <div class="meter"><i style="width:${overall100 != null ? Math.max(2, Math.min(100, overall100)) : 0}%"></i></div>
        <div class="small mut">${esc(answeredLine)}${role ? ` · ${esc(role)}` : ""}</div>
      </div>
      <div class="row">
        <a class="btn primary" href="/report?sid=${encodeURIComponent(qsid)}">View question analysis</a>
        <a class="btn" href="/interview">Practice again</a>
      </div>
    </div>
    ${r.summary ? `<p class="mut mt">${esc(r.summary)}</p>` : ""}
  </div>

  <div class="grid g4 mt">
    ${tile("Answer quality", avg != null ? `${avg.toFixed(1)}<span class="res-of">/10</span>` : "—",
       `mean of ${scores.length} scored answers`)}
    ${tile("Relevance", relPct != null ? `${relPct}%` : "—",
       `${direct} of ${withRel.length} answers stayed on the question`)}
    ${tile("Conciseness", concPct != null ? `${concPct}%` : "—",
       withSig.length ? `${withSig.length} answers with transcript signals` : "no transcript signals")}
    ${tile("Completeness", compPct != null ? `${compPct}%` : "—",
       withSig.length ? `answers with 20+ words` : "no transcript signals")}
  </div>

  <div class="grid g2 mt">
    <div class="card">
      <h3>Key feedback</h3>
      ${strengths[0] ? `<p><b style="color:var(--ok)">+</b> ${esc(strengths[0])}</p>` : ""}
      ${r.top_priority ? `<p><b style="color:var(--warn)">!</b> ${esc(r.top_priority)}</p>` : ""}
      ${r.biggest_weakness ? `<p class="small mut">${esc(r.biggest_weakness)}</p>` : ""}
      ${recurring.length ? `<div class="chips mt">${recurring.map((p) => `<span class="pill">${esc(p)}</span>`).join("")}</div>` : ""}
    </div>
    <div class="card">
      <h3>Strengths</h3>
      ${strengths.length ? `<ul class="res-list">${strengths.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`
        : `<p class="mut small">No strengths were recorded for this session.</p>`}
      ${r.relevance_summary ? `<p class="small dim mt">${esc(r.relevance_summary)}</p>` : ""}
    </div>
  </div>

  <div class="grid g2 mt">
    <div class="card">
      <h3>Training plan</h3>
      ${training.length ? `<ol class="res-list">${training.map((t) => `<li>${esc(t)}</li>`).join("")}</ol>`
        : `<p class="mut small">Finish a full interview to get a personalised plan.</p>`}
      ${r.next_practice ? `<p class="small mt"><span class="dim">Next session:</span> <b>${esc(r.next_practice)}</b></p>` : ""}
    </div>
    <div class="card">
      <h3>Communication</h3>
      <div class="grid g2">
        <div><div class="small dim">Fillers</div><div><b>${fillers}</b> · ${esc(fillerLevel)}${per100 != null ? ` <span class="dim">(${per100.toFixed(1)}/100 words)</span>` : ""}</div></div>
        <div><div class="small dim">Hedging words</div><div><b>${hedges}</b></div></div>
        <div><div class="small dim">Avg answer length</div><div><b>${avgWords != null ? avgWords : "—"}</b> words</div></div>
        <div><div class="small dim">Words total</div><div><b>${words || "—"}</b></div></div>
      </div>
      ${r.communication ? `<p class="small mut mt">${esc(r.communication)}</p>` : ""}
      ${r.pronunciation_note ? `<p class="small dim mt">${esc(r.pronunciation_note)}</p>` : ""}
    </div>
  </div>

  <div class="row mt">
    <a class="btn" href="/report?sid=${encodeURIComponent(qsid)}">Full question-by-question analysis →</a>
    <a class="btn ghost" href="/">Back to dashboard</a>
  </div>`;
})();
