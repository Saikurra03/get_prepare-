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
  <div class="card mt"><h3>Preferences</h3>
    <label class="fl">Default interview difficulty</label>
    <select id="p_diff"><option>beginner</option><option>intermediate</option><option>advanced</option><option>expert</option></select>
    <label class="fl">Default number of questions</label>
    <select id="p_nq"><option>3</option><option>5</option><option>7</option></select>
    <div class="row mt"><button class="primary" id="bSave">Save</button><span class="small dim" id="saved"></span></div></div>`;
(async () => {
  try {
    const h = await api.health();
    document.getElementById("eng").innerHTML =
      `Status: <b>${esc(h.ai_provider || "offline")}</b><br/>Provider available: <b>${h.ai_ready ? "yes" : "no"}</b><br/>
       Automatic failover: <b>enabled</b><br/>Provider priority: <b>${esc((h.order || []).join(" → "))}</b>`;
  } catch { document.getElementById("eng").textContent = "Server unreachable."; }
})();
document.getElementById("p_diff").value = prefs.get("diff", "intermediate");
document.getElementById("p_nq").value = prefs.get("nQ", "5");
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
