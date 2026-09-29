/* Settings: AI Engine (safe status only), Audio & Camera tests, Preferences. */
const page = buildShell("Settings", "BERREADY / Settings");
const media = createMedia();
page.innerHTML = `
  <div class="card"><h3>AI Engine</h3><div id="eng" class="small mut">Loading…</div>
    <p class="small dim">Automatic failover is always enabled — if one provider or key hits a limit, the next takes over silently. Key values are never shown anywhere in this app.</p></div>
  <div class="card mt"><h3>Audio & camera</h3>
    <div class="row"><button id="bCamT">Test camera</button><button id="bMicT">Test microphone</button></div>
    <video class="cam mt" id="v" autoplay muted playsinline style="max-width:320px"></video>
    <div id="micOut" class="small mut mt">Mic test listens for 5 seconds and shows what it hears.</div></div>
  <div class="card mt"><h3>Response latency</h3><div id="lat" class="small mut">Loading…</div>
    <p class="small dim">Server timings cover the last 100 API routes (in-memory, reset on deploy). Client timings show this browser's recent round-trips.</p></div>
  <div class="card mt"><h3>Appearance</h3>
    <div class="row" id="themePair" data-pair>
      <button id="thLight" data-theme-set="light">Light</button>
      <button id="thDark" data-theme-set="dark">Dark</button>
    </div>
    <p class="small dim">Your choice is saved on this device and applied to every screen.</p></div>
  <div class="card mt"><h3>Preferences</h3>
    <label class="fl">Default interview difficulty</label>
    <select id="p_diff"><option>beginner</option><option>intermediate</option><option>advanced</option><option>expert</option></select>
    <label class="fl">Default number of questions</label>
    <select id="p_nq"><option>3</option><option>5</option><option>7</option></select>
    <div class="row mt"><button class="primary" id="bSave">Save</button><span class="small dim" id="saved"></span></div></div>`;
(async () => {
  try {
    const st = await api.status();
    const provList = (st.provider_order || []).map(p => {
      const avail = (st.providers || {})[p] === "available";
      return `${esc(p.charAt(0).toUpperCase() + p.slice(1))}: ${avail ? '<span style="color:var(--good)">available</span>' : '<span class="dim">no keys</span>'}`;
    }).join(" · ");
    const activeLine = st.ai_ready
      ? `<span style="color:var(--good)">● Active: ${esc((st.active_provider || "").charAt(0).toUpperCase() + (st.active_provider || "").slice(1))}</span> ${st.active_key ? `(${esc(st.active_key)})` : ""}`
      : `<span style="color:var(--warn)">● No active provider yet — will activate on first AI call</span>`;
    document.getElementById("eng").innerHTML =
      `${activeLine}<br/>Failover: <b>enabled</b> · Configured: <b>${st.configured_count || 0}</b> provider(s)<br/>Priority: <b>${esc((st.provider_order || []).join(" → "))}</b><br/>${provList}<br/>
       <div class="small dim mt">Requests: ${st.activity?.api_requests ?? 0} API · ${st.activity?.ai_calls ?? 0} AI calls · ${st.activity?.ai_success ?? 0} success · ${st.activity?.errors ?? 0} errors</div>`;

    /* Latency panel */
    const aiLast = st.activity?.ai_last_ms != null ? `${st.activity.ai_last_ms} ms` : "—";
    const aiAvg = st.activity?.ai_avg_ms != null ? `${st.activity.ai_avg_ms} ms` : "—";
    const lat = st.latency || {};
    const rows = Object.keys(lat).length
      ? Object.entries(lat)
          .sort((a, b) => (b[1].n * b[1].avg_ms) - (a[1].n * a[1].avg_ms))
          .slice(0, 8)
          .map(([p, v]) => `<tr><td>${esc(p)}</td><td class="tr">${v.n}</td><td class="tr">${v.avg_ms} ms</td><td class="tr">${v.last_ms} ms</td><td class="tr">${v.max_ms} ms</td></tr>`)
          .join("")
      : `<tr><td colspan="5" class="dim">No API calls recorded yet on this instance.</td></tr>`;
    const recent = (window.api && api.timings || []).slice(-8).reverse()
      .map(t => `<tr><td>${esc(t.p)}</td><td class="tr">—</td><td class="tr">${t.ms} ms</td><td class="tr">—</td><td class="tr">—</td></tr>`).join("")
      || `<tr><td colspan="5" class="dim">No client round-trips yet in this tab.</td></tr>`;
    document.getElementById("lat").innerHTML =
      `AI call: last <b>${aiLast}</b> · average <b>${aiAvg}</b>
       <div class="mt"><table class="small" style="width:100%;border-collapse:collapse">
       <tr class="dim"><th style="text-align:left">route</th><th class="tr">n</th><th class="tr">avg</th><th class="tr">last</th><th class="tr">max</th></tr>
       ${rows}</table>
       <div class="mt dim">This browser (recent round-trips):</div>
       <table class="small" style="width:100%;border-collapse:collapse">
       <tr class="dim"><th style="text-align:left">request</th><th class="tr">n</th><th class="tr">avg</th><th class="tr">last</th><th class="tr">max</th></tr>
       ${recent}</table></div>`;
  } catch { document.getElementById("eng").textContent = "Server unreachable."; }
})();
document.getElementById("p_diff").value = prefs.get("diff", "intermediate");
document.getElementById("p_nq").value = prefs.get("nQ", "5");
if (window.theme) theme.mount(document.getElementById("themePair"));
document.getElementById("bSave").onclick = () => {
  prefs.set("diff", document.getElementById("p_diff").value);
  prefs.set("nQ", document.getElementById("p_nq").value);
  document.getElementById("saved").textContent = "Saved.";
};
document.getElementById("bCamT").onclick = async () => {
  await media.camera(document.getElementById("v"), true, () => alert("Camera unavailable or permission denied."));
  setTimeout(() => media.camera(document.getElementById("v"), false), 8000);
};
document.getElementById("bMicT").onclick = () => {
  if (!media.speakSupported()) { document.getElementById("micOut").textContent = "Speech recognition not supported in this browser — typing fallback will be used."; return; }
  document.getElementById("micOut").textContent = "Listening for 5 seconds…";
  media.listen((t) => { document.getElementById("micOut").textContent = `Heard: “${t}”`; },
    () => {}, () => { document.getElementById("micOut").textContent = "Mic unavailable or permission denied."; });
  setTimeout(() => media.stopListen(), 5000);
};
