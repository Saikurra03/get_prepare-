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

  // Visual Communication section
  const vc = r.visual_communication;
  let visualHtml = "";
  if (vc && Object.keys(vc).length > 0) {
    const items = [];
    if (vc.camera_attention) {
      const ca = vc.camera_attention;
      items.push(`<div><b>Camera Attention:</b> ${ca.gaze_away_count} look-away${ca.gaze_away_count !== 1 ? "s" : ""} (${ca.gaze_away_total_sec}s total) — <span style="color:${ca.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ca.rating}</span></div>`);
    }
    if (vc.posture) {
      const p = vc.posture;
      items.push(`<div><b>Posture:</b> ${p.slouch_count} slouch${p.slouch_count !== 1 ? "es" : ""} (${p.slouch_total_sec}s total) — <span style="color:${p.rating === "good" ? "var(--ok)" : "var(--warn)"}">${p.rating}</span></div>`);
    }
    if (vc.movement) {
      items.push(`<div><b>Movement:</b> ${vc.movement.excessive_count} excessive movement${vc.movement.excessive_count !== 1 ? "s" : ""} — <span style="color:${vc.movement.rating === "good" ? "var(--ok)" : "var(--warn)"}">${vc.movement.rating}</span></div>`);
    }
    if (vc.body_alignment) {
      const ba = vc.body_alignment;
      const baItems = [];
      if (ba.torso_lean_count > 0) baItems.push(`${ba.torso_lean_count} lean${ba.torso_lean_count !== 1 ? "s" : ""}`);
      if (ba.shoulder_rotation_count > 0) baItems.push(`${ba.shoulder_rotation_count} rotation${ba.shoulder_rotation_count !== 1 ? "s" : ""}`);
      if (baItems.length > 0) {
        items.push(`<div><b>Body Alignment:</b> ${baItems.join(", ")} — <span style="color:${ba.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ba.rating}</span></div>`);
      }
    }
    if (vc.gestures) {
      const ge = vc.gestures;
      items.push(`<div><b>Gestures:</b> ${ge.gesture_count} used, ${ge.hands_hidden_count} time${ge.hands_hidden_count !== 1 ? "s" : ""} hands hidden — <span style="color:${ge.rating === "good" ? "var(--ok)" : "var(--warn)"}">${ge.rating}</span></div>`);
      if (ge.gesture_breakdown && Object.keys(ge.gesture_breakdown).length > 0) {
        const gItems = Object.entries(ge.gesture_breakdown).map(([k, v]) => `${k.replace("_", " ")}×${v}`).join(", ");
        items.push(`<div style="padding-left:12px" class="dim">Gesture types: ${gItems}</div>`);
      }
    }
    if (vc.strengths && vc.strengths.length) {
      items.push(`<div style="color:var(--ok);margin-top:4px">✓ ${esc(vc.strengths.join(" · "))}</div>`);
    }
    if (vc.patterns && vc.patterns.length) {
      items.push(`<div style="color:var(--warn);margin-top:4px">⚠ ${esc(vc.patterns.join(" · "))}</div>`);
    }
    if (vc.priority) {
      items.push(`<div style="margin-top:4px"><b>Priority:</b> ${esc(vc.priority)}</div>`);
    }
    visualHtml = `<div class="card mt"><h3>📷 Visual Communication</h3><div class="small">${items.join("")}</div></div>`;
  }

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
    ${visualHtml}
    ${sec("Technical performance", esc(r.technical || ""))}
    ${sec("Role alignment", esc(r.role_alignment || ""))}
    ${sec("Recurring problems", esc((r.recurring_problems || []).join(" · ") || "—"))}
    ${sec("Answer relevance", esc(r.relevance_summary || ""))}
    ${sec("Sentence & grammar patterns", esc(r.sentence_patterns || ""))}
    ${sec("Pronunciation / articulation", esc(r.pronunciation_note || ""))}
    <div class="card mt"><h3>Most important improvement</h3><div class="small"><b>${esc(r.top_priority || r.biggest_weakness || "—")}</b></div></div>
    <div class="card mt"><h3>Next training target</h3><div class="small">${(r.training || []).map((t) => `• ${esc(t)}`).join("<br/>") || "—"}
    <br/>Recommended next session: <b>${esc(r.next_practice || "—")}</b></div>
      <div class="row mt"><a class="btn primary" href="/practice">Train now</a>
      <a class="btn ghost" href="/history">All sessions</a></div></div>`;
})();
