/* Practice Hub: what skill do I want to improve? No camera here — choose first. */
const page = buildShell("Practice", "BERREADY / Practice");
const order = ["communication", "story", "speaking", "wit", "qa", "podcast", "conversation"];
const MOCKABLE = ["communication", "story", "speaking"];   // full-screen mock room entry points
page.innerHTML = `<p class="sub">Pick a skill. Each opens a focused setup — the camera only turns on when you start.</p>
  <div class="grid" id="modes"></div>`;
(async () => {
  let done = {};
  try { const prof = await api.profile(); done = prof.modes_done || {}; } catch {}
  document.getElementById("modes").innerHTML = order.map(k => {
    const m = MODES[k];
    const mockBtn = MOCKABLE.includes(k)
      ? `<a class="btn ghost" href="/mock?mode=${k}" title="Full-screen mock room">⛶ Mock</a>` : "";
    return `<div class="card mode"><div class="m-ic">${m.ic}</div>
      <div><h3>${m.title}</h3><p>${m.desc} ${m.purpose}</p></div>
      <div class="row" style="gap:6px;justify-content:flex-end"><a class="btn primary go" href="/workspace?mode=${k}">Open</a>${mockBtn}</div></div>`;
  }).join("");
})();
