/* Session History: list with filters + drill-down (overview, transcript, feedback, retry). */
const sid = new URLSearchParams(location.search).get("sid");
const page = buildShell("History", "BERREADY / Progress / History");
const bucket = (s) => s.kind === "interview" ? "interview"
  : s.kind === "podcast" ? "podcast"
  : s.meta?.scenario === "story" ? "story"
  : ["presentation"].includes(s.meta?.scenario) ? "speaking"
  : ["spontaneous", "qa"].includes(s.meta?.scenario) ? "qa" : "communication";
const BUCKETS = [["all", "All"], ["interview", "Interview"], ["communication", "Communication"], ["story", "Storytelling"], ["speaking", "Public speaking"], ["podcast", "Podcast"], ["qa", "Q&A"]];
let ALL = [];

async function listView(f = "all") {
  page.innerHTML = `<div class="row mb">${BUCKETS.map(([k, l]) => `<button class="${f === k ? "primary" : "ghost"}" data-f="${k}">${l}</button>`).join("")}</div><div id="tbl"></div>`;
  document.querySelectorAll("[data-f]").forEach((b) => b.onclick = () => listView(b.dataset.f));
  const rows = ALL.filter((s) => f === "all" || bucket(s) === f);
  document.getElementById("tbl").innerHTML = rows.length ? `<div class="card"><table class="t">
    <tr><th>Date</th><th>Type</th><th>Detail</th><th>Result</th><th>Status</th><th></th></tr>` +
    rows.map((s) => `<tr><td>${esc(fmtT(s.created))}</td><td>${esc(s.kind)}</td>
      <td>${esc(s.meta?.scenario || s.meta?.type || "—")}</td>
      <td>${s.kind === "interview" && s.status === "finished" ? `<a href="/report?sid=${s.id}">report</a>` : `<span class="dim">—</span>`}</td>
      <td>${esc(s.status)}</td><td><a href="/history?sid=${s.id}">Open</a></td></tr>`).join("") + `</table></div>`
    : `<div class="card">No sessions in this view yet.</div>`;
}
async function detailView() {
  page.innerHTML = `<div class="card">Loading session…</div>`;
  let d;
  try { d = await api.sessionDetail(sid); } catch { page.innerHTML = `<div class="card">Server unreachable.</div>`; return; }
  if (d.error) { page.innerHTML = `<div class="card">Session not found.</div>`; return; }
  const turns = (d.turns || []).map((t, i) => {
    const q = t.question ? `<div class="small dim">Q${i + 1}: ${esc(t.question)}</div>` : "";
    const a = t.answer ? `<p>${esc(t.answer)}</p>` : (t.transcript ? `<p>${esc(t.transcript)}</p>` : "");
    const fb = t.feedback ? `<div class="feedback small">${esc(t.feedback)}</div>`
      : t.evaluation ? `<div class="small">Score <b>${t.evaluation.score}</b> · ${esc(t.evaluation.main_issue || "")}${t.evaluation.retry_suggested ? ` · retry: ${esc(t.evaluation.retry_instruction || "")}` : ""}</div>` : "";
    return `<div class="card mt">${q}${a}${fb}</div>`;
  }).join("");
  page.innerHTML = `<a class="btn ghost mb" href="/history">← All sessions</a>
    <div class="card"><div class="small dim">${esc(d.kind)} · ${esc(d.meta?.scenario || d.meta?.type || "")} · ${esc(fmtT(d.created))} · ${esc(d.status)}</div>
    <h2>Session overview</h2>
    ${d.report ? `<p>${esc(d.report.summary || "")} <b>${d.report.overall ?? ""}/10</b></p>
      <div class="row"><a class="btn primary" href="/report?sid=${d.id}">Full report</a></div>` : ""}
    <div class="row mt"><a class="btn" href="/workspace?mode=${d.kind === "podcast" ? "podcast" : "communication"}">Retry as practice</a></div></div>
    <h3 class="mt">Transcript & AI feedback</h3>${turns || "<p class='mut'>No turns recorded.</p>"}`;
}
(async () => {
  try { ALL = ((await api.sessions()).sessions || []).slice().reverse(); } catch { page.innerHTML = `<div class="card">Server unreachable.</div>`; return; }
  if (sid) { detailView(); return; }
  const f0 = new URLSearchParams(location.search).get("f") || "all";
  listView(BUCKETS.some(([k]) => k === f0) ? f0 : "all");
})();
