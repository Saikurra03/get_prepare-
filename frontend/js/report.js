/* Interview Report: full per-question breakdown + aggregate analysis. */
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

  /* --- Per-question breakdown --- */
  const details = r.question_details || [];
  let questionHtml = "";
  if (details.length) {
    const cards = details.map((qd, i) => {
      const ev = qd.evaluation || {};
      const coaching = qd.coaching || {};
      const dims = ev.dimensions || {};
      const rel = ev.relevance || {};
      const isSkipped = qd.answer === "[skipped]" || qd.answer === "[topic changed]";

      // Score
      const scoreHtml = isSkipped
        ? `<span class="score" style="background:var(--warn);color:#fff">Skipped</span>`
        : `<span class="score">${ev.score ?? "—"}/10</span>`;

      // Strengths
      const goodHtml = (ev.good || []).map(g => `<div class="small">✓ ${esc(g)}</div>`).join("");

      // Sentences
      const sents = (ev.sentences || []).map(s =>
        `<div class="small">✎ <i>"${esc(s.problem)}"</i> → ${esc(s.fix)}</div>`).join("");

      // Better examples
      const better = (ev.better_examples || []).map(b =>
        `<div class="small">"${esc(b.text)}"<br/><span class="dim">Why stronger: ${esc(b.why)}</span></div>`).join("");

      // Visual observations
      const visEvents = qd.visual_observations || [];
      const visItems = [];
      const gazeAway = visEvents.filter(e => e.type === "gaze_away");
      const slouching = visEvents.filter(e => e.type === "slouching");
      const gestures = visEvents.filter(e => e.type === "gesture");
      if (gazeAway.length) visItems.push(`👁 Looked away ${gazeAway.length}x`);
      if (slouching.length) visItems.push(`🧍 Slouched ${slouching.length}x`);
      if (gestures.length) visItems.push(`🤌 ${gestures.length} gestures`);
      const visHtml = visItems.length ? `<div class="small dim" style="margin-top:4px">📷 ${visItems.join(" · ")}</div>` : "";

      // Coaching
      const coachingHtml = coaching.priority ? `
        <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);border-radius:6px;padding:8px;margin-top:8px">
          ${coaching.appreciation ? `<div class="small" style="color:var(--ok)"><b>💬</b> ${esc(coaching.appreciation)}</div>` : ""}
          <div class="small"><b>🎯</b> ${esc(coaching.priority)}</div>
          ${coaching.specific_feedback ? `<div class="small">${esc(coaching.specific_feedback)}</div>` : ""}
          ${coaching.improvement ? `<div class="small" style="color:var(--accent)"><b>✨</b> ${esc(coaching.improvement)}</div>` : ""}
        </div>` : "";

      // Model answer
      const modelHtml = qd.model_answer ? `
        <div style="background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);border-radius:6px;padding:8px;margin-top:8px">
          <div class="small" style="color:var(--ok);font-weight:600">📝 Model Answer (8-9/10)</div>
          <div class="small" style="line-height:1.5">${esc(qd.model_answer)}</div>
        </div>` : "";

      return `
        <details class="card mt" ${i === 0 ? "open" : ""}>
          <summary style="cursor:pointer;display:flex;align-items:center;gap:8px">
            <span class="small dim" style="min-width:24px">Q${i + 1}</span>
            <span class="small" style="flex:1"><b>${esc(qd.question)}</b></span>
            ${scoreHtml}
          </summary>
          <div style="padding:12px 0 0">
            <div class="small"><b>Your answer:</b> ${isSkipped ? `<i class="dim">${esc(qd.answer)}</i>` : esc(qd.answer)}</div>
            ${!isSkipped ? `
              ${goodHtml}
              ${ev.biggest_issue ? `<div class="small">⚠ ${esc(ev.biggest_issue)}</div>` : ""}
              ${rel.note ? `<div class="small dim">🎯 ${esc(rel.verdict || "")}: ${esc(rel.note)}</div>` : ""}
              ${sents ? `<div class="small mt"><b>Sentence fixes:</b>${sents}</div>` : ""}
              ${better ? `<div class="small mt"><b>Better way to say it:</b>${better}</div>` : ""}
              <div class="small dim mt">Clarity: ${esc(dims.clarity || "—")} · Conciseness: ${esc(dims.conciseness || "—")} · Specificity: ${esc(dims.specificity || "—")}</div>
              <div class="small dim">Vocabulary: ${esc(ev.vocabulary || "—")} · Fillers: ${esc(ev.fillers || "—")} · Pacing: ${esc(ev.pacing || "—")}</div>
              ${visHtml}
            ` : ""}
            ${coachingHtml}
            ${modelHtml}
          </div>
        </details>`;
    }).join("");
    questionHtml = `<div class="card mt"><h3>📋 Question-by-Question Breakdown</h3></div>${cards}`;
  }

  /* --- Visual Communication section --- */
  const vc = r.visual_communication;
  let visualHtml = "";
  if (vc && Object.keys(vc).length > 0) {
    const items = [];
    if (vc.camera_attention) {
      const ca = vc.camera_attention;
      items.push(`<div><b>Camera Attention:</b> ${ca.gaze_away_count} look-away${ca.gaze_away_count !== 1 ? "s" : ""} (${ca.gaze_away_total_sec}s) — <span style="color:${ca.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ca.rating}</span></div>`);
    }
    if (vc.posture) {
      const p = vc.posture;
      items.push(`<div><b>Posture:</b> ${p.slouch_count} slouch${p.slouch_count !== 1 ? "es" : ""} (${p.slouch_total_sec}s) — <span style="color:${p.rating === "good" ? "var(--ok)" : "var(--warn)"}">${p.rating}</span></div>`);
    }
    if (vc.movement) {
      items.push(`<div><b>Movement:</b> ${vc.movement.excessive_count} excessive — <span style="color:${vc.movement.rating === "good" ? "var(--ok)" : "var(--warn)"}">${vc.movement.rating}</span></div>`);
    }
    if (vc.body_alignment) {
      const ba = vc.body_alignment;
      const baItems = [];
      if (ba.torso_lean_count > 0) baItems.push(`${ba.torso_lean_count} lean${ba.torso_lean_count !== 1 ? "s" : ""}`);
      if (ba.shoulder_rotation_count > 0) baItems.push(`${ba.shoulder_rotation_count} rotation${ba.shoulder_rotation_count !== 1 ? "s" : ""}`);
      if (baItems.length) items.push(`<div><b>Body Alignment:</b> ${baItems.join(", ")} — <span style="color:${ba.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ba.rating}</span></div>`);
    }
    if (vc.gestures) {
      const ge = vc.gestures;
      items.push(`<div><b>Gestures:</b> ${ge.gesture_count} used — <span style="color:${ge.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ge.rating}</span></div>`);
      if (ge.gesture_breakdown && Object.keys(ge.gesture_breakdown).length) {
        items.push(`<div class="dim" style="padding-left:12px">${Object.entries(ge.gesture_breakdown).map(([k, v]) => `${k.replace("_", " ")}×${v}`).join(", ")}</div>`);
      }
    }
    if (vc.strengths && vc.strengths.length) items.push(`<div style="color:var(--ok)">✓ ${esc(vc.strengths.join(" · "))}</div>`);
    if (vc.patterns && vc.patterns.length) items.push(`<div style="color:var(--warn)">⚠ ${esc(vc.patterns.join(" · "))}</div>`);
    if (vc.priority) items.push(`<div><b>Priority:</b> ${esc(vc.priority)}</div>`);
    visualHtml = `<div class="card mt"><h3>📷 Visual Communication</h3><div class="small">${items.join("")}</div></div>`;
  }

  /* --- Dashboard (Phase 5): charts of real report numbers only --- */
  const skippedOf = (qd) => qd.answer === "[skipped]" || qd.answer === "[topic changed]";
  const scoredPts = [], fillerPts = [];
  details.forEach((qd, i) => {
    const ev = qd.evaluation || {};
    if (!skippedOf(qd) && typeof ev.score === "number") scoredPts.push({ label: `Q${i + 1}`, value: ev.score });
    if (!skippedOf(qd)) fillerPts.push({ label: `Q${i + 1}`, value: (ev.signals || {}).filler_total ?? 0 });
  });
  const skippedN = details.filter(skippedOf).length;
  const answeredN = details.length - skippedN;
  let dashHtml = "";
  if (details.length) {
    const cells = [];
    const trend = Charts.line(scoredPts);
    if (trend) cells.push(`<div class="card"><div class="small dim" style="margin-bottom:6px">Score trend (0–10)</div>${trend}</div>`);
    const cov = Charts.donut([
      { label: "Answered", value: answeredN, color: "var(--ok)" },
      { label: "Skipped", value: skippedN, color: "var(--warn)" },
    ], { centerLabel: "answers" });
    if (cov) cells.push(`<div class="card"><div class="small dim" style="margin-bottom:6px">Answer coverage</div>${cov}</div>`);
    const fill = fillerPts.length ? Charts.bars(fillerPts, { labelW: 44 }) : "";
    if (fill) cells.push(`<div class="card"><div class="small dim" style="margin-bottom:6px">Fillers per answer</div>${fill}</div>`);
    if (vc && Object.keys(vc).length) {
      const visBars = Charts.bars([
        { label: "Look-aways", value: vc.camera_attention?.gaze_away_count ?? 0, color: "var(--warn)" },
        { label: "Slouches", value: vc.posture?.slouch_count ?? 0, color: "var(--warn)" },
        { label: "Excess move", value: vc.movement?.excessive_count ?? 0, color: "var(--warn)" },
        { label: "Gestures", value: vc.gestures?.gesture_count ?? 0, color: "var(--ok)" },
      ]);
      if (visBars) cells.push(`<div class="card"><div class="small dim" style="margin-bottom:6px">Camera signals (session)</div>${visBars}</div>`);
    }
    if (cells.length) dashHtml = `<div class="dash mt">${cells.join("")}</div>`;
  }

  /* --- Main report --- */
  page.innerHTML = `
    <div class="card"><div class="small dim">${esc(d.meta?.role || "")} · ${esc(d.meta?.type || "")} · ${esc(fmtT(d.created))}</div>
      <h2>Overall: ${r.overall ?? "—"}/10 <span class="dim" style="font-size:13px;font-weight:400">(${r.answers_evaluated ?? 0} answers)</span></h2>
      <p>${esc(r.summary || "")}</p></div>
    ${dashHtml}
    <div class="grid g2 mt">
      <div class="card"><h3>Strongest areas</h3><div class="small">${esc((r.strengths || []).join(" · ") || "—")}</div></div>
      <div class="card"><h3>Biggest weakness</h3><div class="small">${esc(r.biggest_weakness || "—")}</div></div>
    </div>
    <div class="grid g2 mt">
      <div class="card"><h3>Best answer</h3><div class="small">${esc(r.best_answer?.question || "—")} <span class="score">${r.best_answer?.score ?? ""}</span></div></div>
      <div class="card"><h3>Weakest answer</h3><div class="small">${
        r.weakest_answer?.tied
          ? `<span class="dim">No single weakest answer — every scored answer tied at ${r.weakest_answer?.score ?? r.best_answer?.score ?? "—"}/10.</span>`
          : `${esc(r.weakest_answer?.question || "—")}<br/><span class="dim">Issue: ${esc(r.weakest_answer?.issue || "—")}</span>`}</div></div>
    </div>
    ${questionHtml}
    ${sec("Communication", esc(r.communication || ""))}
    ${visualHtml}
    ${sec("Technical performance", esc(r.technical || ""))}
    ${sec("Role alignment", esc(r.role_alignment || ""))}
    ${sec("Recurring problems", esc((r.recurring_problems || []).join(" · ") || "—"))}
    ${sec("Answer relevance", esc(r.relevance_summary || ""))}
    ${sec("Sentence & grammar patterns", esc(r.sentence_patterns || ""))}
    <div class="card mt"><h3>Most important improvement</h3><div class="small"><b>${esc(r.top_priority || r.biggest_weakness || "—")}</b></div></div>
    <div class="card mt"><h3>Next training target</h3><div class="small">${(r.training || []).map((t) => `• ${esc(t)}`).join("<br/>") || "—"}
    <br/>Recommended next session: <b>${esc(r.next_practice || "—")}</b></div>
      <div class="row mt"><a class="btn primary" href="/practice">Train now</a>
      <a class="btn ghost" href="/history">All sessions</a></div></div>`;
})();
