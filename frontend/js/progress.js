/* Overview: what is actually happening with my performance? Real data only.
   No completed sessions -> single empty state. Sections render only with real data.
   Every chart links back to the session(s) it came from. */
const page = buildShell("Overview", "BERREADY / Progress / Overview");
const COLORS = ["#5b8cff", "#34d399", "#fbbf24", "#f472b6", "#22d3ee", "#a78bfa", "#fb923c"];
page.innerHTML = `<div class="card">Loading your performance…</div>`;

const donut = (parts) => {
  const total = parts.reduce((a, p) => a + p[1], 0);
  if (!total) return "";
  let acc = 0;
  const segs = parts.map(([label, v], i) => {
    const a0 = (acc / total) * 360, a1 = ((acc + v) / total) * 360; acc += v;
    const large = a1 - a0 > 180 ? 1 : 0;
    const p = (deg, r) => [50 + r * Math.cos((deg - 90) * Math.PI / 180), 50 + r * Math.sin((deg - 90) * Math.PI / 180)];
    const [x0, y0] = p(a0, 38), [x1, y1] = p(a1, 38);
    const [ix0, iy0] = p(a1, 24), [ix1, iy1] = p(a0, 24);
    return `<path d="M${x0},${y0} A38,38 0 ${large},1 ${x1},${y1} L${ix0},${iy0} A24,24 0 ${large},0 ${ix1},${iy1} Z"
      fill="${COLORS[i % COLORS.length]}" opacity="0.9"><title>${esc(label)}: ${v}</title></path>`;
  }).join("");
  return `<div class="row"><svg width="150" height="150" viewBox="0 0 100 100">${segs}
    <text x="50" y="54" text-anchor="middle" fill="var(--ink)" font-size="16" font-weight="800">${total}</text></svg>
    <div>${parts.map(([label, v], i) => `<div class="small"><span style="color:${COLORS[i % COLORS.length]}">●</span>
      <a href="/history?f=${secFilter(label)}">${esc(label)}</a> — <b>${v}</b></div>`).join("")}</div></div>
    <div class="small dim">Completed sessions by section.</div>`;
};
const secFilter = (label) => ({ Interviews: "interview", Communication: "communication", Storytelling: "story",
  "Public Speaking": "speaking", "Q&A": "qa", Wit: "communication", Podcast: "podcast" }[label] || "all");

const gauge = (avg) => {
  const frac = Math.max(0, Math.min(1, avg / 10));
  const ang = 180 * (1 - frac);
  const x = 100 - 80 * Math.cos(ang * Math.PI / 180), y = 100 - 80 * Math.sin(ang * Math.PI / 180);
  return `<a href="/history?f=interview" style="text-decoration:none;color:inherit"><svg width="200" height="112" viewBox="0 0 200 112">
    <path d="M20,100 A80,80 0 0,1 180,100" fill="none" stroke="var(--line)" stroke-width="14" stroke-linecap="round"/>
    <line x1="100" y1="100" x2="${x}" y2="${y}" stroke="var(--acc)" stroke-width="4" stroke-linecap="round"/>
    <circle cx="100" cy="100" r="7" fill="var(--acc)"/>
    <text x="100" y="92" text-anchor="middle" fill="var(--ink)" font-size="20" font-weight="800">${avg}/10</text></svg>
    <div class="small dim">Average interview score (click to inspect sessions).</div></a>`;
};

const trendSvg = (pts) => {
  const W = 520, H = 150, P = 26;
  const xs = (i) => pts.length < 2 ? W / 2 : P + (i * (W - 2 * P)) / (pts.length - 1);
  const ys = (v) => H - P - (v / 10) * (H - 2 * P);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${xs(i)},${ys(p.overall)}`).join(" ");
  return `<svg width="100%" viewBox="0 0 ${W} ${H}" style="max-width:560px">
    <line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" stroke="var(--line)"/>
    <path d="${line}" fill="none" stroke="var(--acc)" stroke-width="2.5"/>
    ${pts.map((p, i) => `<a href="/report?sid=${p.sid}"><circle cx="${xs(i)}" cy="${ys(p.overall)}" r="6" fill="var(--acc)">
      <title>${esc(fmtT(p.created))}: ${p.overall}/10 — open report</title></circle></a>`).join("")}</svg>
    <div class="small dim">Interview overall over time. Click a point for its report.</div>`;
};

(async () => {
  let d;
  try { d = await api.dashboard(); }
  catch { page.innerHTML = `<div class="card">Server unreachable.</div>`; return; }
  const doneTotal = Object.values(d.sections || {}).reduce((a, b) => a + b, 0);
  if (!doneTotal) {
    page.innerHTML = `<div class="card"><h3>No completed sessions yet.</h3>
      <p class="sub">Charts, scores and trends appear here automatically once you finish a real session.</p>
      <div class="row"><a class="btn primary" href="/practice">Start practicing</a>
      <a class="btn" href="/interview">Mock interview</a></div></div>`;
    return;
  }
  const parts = Object.entries(d.sections || {});
  const m = d.metrics || {};
  const card = (t, v, basis, link) => `<a href="${link}" style="text-decoration:none;color:inherit"><div class="card">
    <div class="small dim">${t}</div><h2>${v}</h2><div class="small dim">${esc(basis)}</div></div></a>`;
  const cards = [];
  if (m.avg_answer_score) cards.push(card("Avg answer score", `${m.avg_answer_score.value}/10`, `across ${m.avg_answer_score.basis}`, "/history?f=interview"));
  if (m.direct_rate) cards.push(card("Directly on-point", `${m.direct_rate.value}%`, `across ${m.direct_rate.basis}`, "/history?f=interview"));
  if (m.fillers_per_answer) cards.push(card("Fillers / answer", m.fillers_per_answer.value, `across ${m.fillers_per_answer.basis}`, "/history?f=interview"));
  if (m.long_sentences_per_answer) cards.push(card("Long sentences / answer", m.long_sentences_per_answer.value, `across ${m.long_sentences_per_answer.basis}`, "/history?f=interview"));
  if (m.words_per_answer) cards.push(card("Words / answer", m.words_per_answer.value, `across ${m.words_per_answer.basis}`, "/history?f=interview"));
  if (m.technical_avg) cards.push(card("Technical avg", `${m.technical_avg.value}/10`, `across ${m.technical_avg.basis}`, "/history?f=interview"));
  const trend = d.trend || [];
  page.innerHTML = `
    <p class="sub">Everything here comes from your ${doneTotal} completed session(s). Click anything to trace it back.</p>
    <div class="grid g2">
      <div class="card"><h3>Sessions by section</h3>${donut(parts)}</div>
      ${d.interview_avg != null ? `<div class="card"><h3>Interview performance</h3>${gauge(d.interview_avg)}
        <div class="small dim">Across ${d.interview_n ?? "?"} scored session(s).</div></div>` : ""}
    </div>
    ${cards.length ? `<h3 class="mt">Measured metrics</h3><div class="grid g3">${cards.join("")}</div>` : ""}
    <div class="card mt"><h3>Trend</h3>
      ${trend.length >= 2 ? trendSvg(trend.slice(-10)) : `<span class="small mut">Not enough completed sessions to determine a reliable trend.</span>`}</div>
    <div class="card mt"><h3>Not currently measurable</h3>
      <div class="small mut">Articulation, pronunciation and pauses/hesitation are not measured from text transcripts — shown as “not enough data” on every report rather than invented.</div></div>
    <div class="card mt"><h3>Recent charts</h3><div class="row mb" id="rcF"></div><div id="rcBox"></div></div>`;
  // recent charts with section filter
  const charts = d.recent_charts || [];
  const secs = ["all", ...new Set(charts.map((c) => c.section))];
  const box = document.getElementById("rcBox"), fbox = document.getElementById("rcF");
  const draw = (f) => {
    fbox.innerHTML = secs.map((s) => `<button class="${f === s ? "primary" : "ghost"}" data-s="${esc(s)}">${esc(s)}</button>`).join("");
    fbox.querySelectorAll("[data-s]").forEach((b) => b.onclick = () => draw(b.dataset.s));
    const rows = charts.filter((c) => f === "all" || c.section === f);
    box.innerHTML = rows.length ? rows.map((c) => {
      const bits = [];
      if (c.overall != null) bits.push(`overall <b>${c.overall}/10</b>`);
      if (c.avg_score != null) bits.push(`avg answer <b>${c.avg_score}</b>`);
      if (c.direct) bits.push(`direct <b>${c.direct}</b>`);
      if (c.fillers != null && c.kind === "interview") bits.push(`fillers <b>${c.fillers}</b>`);
      if (c.turns != null) bits.push(`turns <b>${c.turns}</b>`);
      if (c.words != null) bits.push(`words <b>${c.words}</b>`);
      if (c.issues) bits.push(`issues: <b>${c.issues.map(esc).join(", ")}</b>`);
      const link = c.kind === "interview" ? `/report?sid=${c.id}` : `/history?sid=${c.id}`;
      return `<div class="card quiet mb" style="border:1px solid var(--line-soft)">
        <div class="row"><b>${esc(c.section)}</b><span class="dim small">${esc(fmtT(c.created))}</span>
        <span style="flex:1"></span><a class="btn ghost" href="${link}">Open</a></div>
        <div class="small mut">${bits.join(" · ") || "completed"}</div></div>`;
    }).join("") : `<span class="dim">No completed sessions yet.</span>`;
  };
  draw("all");
})();
