/* Home / Command Center: what should I practice today? */
const page = buildShell("Home", "BERREADY / Home");
page.innerHTML = `
  <h2 id="greet">Welcome</h2><p class="sub" id="dateLine"></p>
  <div class="grid g2">
    <div class="card"><h3>Continue practice</h3><div id="contBox" class="small mut">Loading…</div></div>
    <div class="card"><h3>Recommended for you</h3><div id="recBox" class="small mut">Loading…</div></div>
  </div>
  <div class="grid g3 mt">
    <div class="card"><h3>Current focus</h3><div id="focusBox" class="small mut">…</div></div>
    <div class="card"><h3>Progress snapshot</h3><div id="snapBox" class="small mut">…</div></div>
    <div class="card"><h3>AI engine</h3><div id="engBox" class="small mut">…</div></div>
  </div>
  <div class="card mt"><h3>Recent sessions</h3><div id="recentBox" class="small mut">Loading…</div></div>
  <div class="card mt"><h3>Quick actions</h3><div class="row">
    <a class="btn primary" href="/workspace?mode=communication">Start speaking</a>
    <a class="btn" href="/interview">Mock interview</a>
    <a class="btn" href="/prepare">Upload resume / JD</a>
    <a class="btn" href="/workspace?mode=qa">20-second challenge</a>
  </div></div>`;

(async () => {
  const h = new Date().getHours();
  document.getElementById("greet").textContent = (h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening") + " — what should we train today?";
  document.getElementById("dateLine").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  try {
    const [prof, sess, health] = await Promise.all([api.profile(), api.sessions(), api.health()]);
    const list = (sess.sessions || []).slice().reverse();
    // continue: most recent session
    document.getElementById("contBox").innerHTML = list.length
      ? `Last: <b>${esc(list[0].kind)}</b> · ${esc(fmtT(list[0].meta?.created))} · ${esc(list[0].status)}<br/>
         <a class="btn mt" href="/history?sid=${list[0].id}">Review it</a>
         <a class="btn ghost" href="/practice">Start new</a>`
      : `No sessions yet. <a class="btn mt" href="/practice">Choose a practice</a>`;
    // recommended from training focus
    const focus = prof.training_focus || "stronger interview answers";
    const rec = /story/i.test(focus) ? ["story", "Storytelling Studio"]
      : /filler|concise|opening|specific/i.test(focus) ? ["communication", "Communication"]
      : /interview/i.test(focus) ? ["__interview__", "Mock Interview"] : ["communication", "Communication"];
    document.getElementById("recBox").innerHTML =
      `Based on your patterns: <b>${esc(focus)}</b><br/><a class="btn primary mt" href="${rec[0] === "__interview__" ? "/interview" : "/workspace?mode=" + rec[0]}">Practice: ${rec[1]}</a>`;
    document.getElementById("focusBox").innerHTML =
      `<b>${esc(focus)}</b><br/><span class="dim">Weaknesses: ${esc((prof.weaknesses || []).join(", ") || "—")}</span>`;
    document.getElementById("snapBox").innerHTML =
      `Sessions: <b>${prof.sessions_completed ?? 0}</b><br/>Avg interview score: <b>${prof.avg_score ?? "—"}</b>`;
    document.getElementById("engBox").innerHTML = (() => {
      if (!health.ok) return `<span style="color:var(--bad)">Backend unreachable</span>`;
      if (health.ai_ready) {
        const p = health.active_provider ? health.active_provider.charAt(0).toUpperCase() + health.active_provider.slice(1) : "";
        return `<span style="color:var(--good)">● AI Ready</span><br/>Active: <b>${esc(p)}</b> ${health.active_key ? `(${esc(health.active_key)})` : ""}<br/>Failover: <b>enabled</b>`;
      }
      const available = Object.entries(health.providers || {}).filter(([,v]) => v === "available").map(([k]) => k);
      if (available.length) return `<span style="color:var(--warn)">● Backend connected</span><br/>${esc(available.join(", ").replace(/\b\w/g, c => c.toUpperCase()))} configured — will activate on first AI call`;
      return `<span style="color:var(--bad)">● No AI keys configured</span>`;
    })();
    // recent
    document.getElementById("recentBox").innerHTML = list.length ? `<table class="t"><tr><th>Date</th><th>Type</th><th>Status</th><th></th></tr>` +
      list.slice(0, 5).map(s => `<tr><td>${esc(fmtT(s.created || s.meta?.created))}</td><td>${esc(s.meta?.scenario || s.kind)}</td><td>${esc(s.status)}</td><td><a href="/history?sid=${s.id}">Open</a></td></tr>`).join("") + `</table>`
      : "Nothing yet — your sessions will appear here.";
  } catch { ["contBox","recBox","focusBox","snapBox","engBox","recentBox"].forEach(id => { const e = document.getElementById(id); if (e) e.textContent = "Could not load. Is the server running?"; }); }
})();
