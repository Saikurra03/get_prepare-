/* Persistent app shell: sidebar nav, topbar, AI pill, mobile bottom nav. */
const NAV = [
  { sec: null, items: [{ path: "/", label: "Home", ic: "⌂" }] },
  { sec: "Practice", items: [
    { path: "/practice", label: "All practice", ic: "◉" },
    { path: "/workspace?mode=communication", label: "Communication", ic: "◐", sub: 1 },
    { path: "/workspace?mode=story", label: "Storytelling", ic: "✎", sub: 1 },
    { path: "/workspace?mode=speaking", label: "Public speaking", ic: "▤", sub: 1 },
    { path: "/workspace?mode=wit", label: "Wit", ic: "✦", sub: 1 },
    { path: "/workspace?mode=qa", label: "Spontaneous Q&A", ic: "⚡", sub: 1 },
    { path: "/workspace?mode=podcast", label: "Podcast", ic: "◍", sub: 1 },
  ]},
  { sec: "Interview", items: [
    { path: "/interview", label: "Interview coach", ic: "◈" },
    { path: "/prepare", label: "Preparation", ic: "⧉", sub: 1 },
    { path: "/prepare#docs", label: "Documents", ic: "🗎", sub: 1 },
  ]},
  { sec: "Progress", items: [
    { path: "/progress", label: "Overview", ic: "▦" },
    { path: "/history", label: "History", ic: "🕘", sub: 1 },
    { path: "/profile", label: "Profile", ic: "⛉", sub: 1 },
  ]},
  { sec: "Learn", items: [
    { path: "/slang", label: "Slang Lab", ic: "💬" },
  ]},
  { sec: null, items: [{ path: "/settings", label: "Settings", ic: "⚙" }] },
];
const MOBILE_NAV = [
  { path: "/", label: "Home", ic: "⌂" }, { path: "/practice", label: "Practice", ic: "◉" },
  { path: "/interview", label: "Interview", ic: "◈" }, { path: "/progress", label: "Progress", ic: "▦" },
  { path: "/settings", label: "Settings", ic: "⚙" },
];

function shellActive(path) {
  const cur = location.pathname + location.search;
  if (path === "/") return location.pathname === "/";
  if (path.startsWith("/workspace")) {
    if (!cur.startsWith("/workspace")) return false;
    const want = new URLSearchParams(path.split("?")[1]).get("mode");
    return new URLSearchParams(location.search).get("mode") === want;
  }
  return location.pathname === path;
}

function buildShell(title, crumb) {
  document.body.classList.add("shell-root");
  const wrap = document.createElement("div");
  wrap.className = "shell";
  const nav = NAV.map(g =>
    (g.sec ? `<div class="nav-sec">${g.sec}</div>` : "") + g.items.map(i =>
      `<a class="nav-item${i.sub ? " nav-sub" : ""}${shellActive(i.path) ? " active" : ""}" href="${i.path}">
        <span class="ic">${i.ic}</span><span class="tx">${i.label}</span></a>`).join("")
  ).join("");
  wrap.innerHTML = `
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">B</div>
        <div><div class="brand-name">BERREADY</div><div class="brand-sub">AI coaching platform</div></div></div>
      <nav>${nav}</nav>
      <div class="side-foot"><div class="ai-pill"><span class="dot" id="aiDot"></span><span id="aiLabel">AI…</span></div></div>
    </aside>
    <div class="main">
      <div class="topbar">
        <button class="icon-btn" id="navToggle" title="Collapse sidebar">☰</button>
        <div><div class="crumb">${crumb}</div><h1>${title}</h1></div>
      </div>
      <div class="content" id="page"></div>
    </div>
    <nav class="bottomnav">${MOBILE_NAV.map(i =>
      `<a href="${i.path}" class="${shellActive(i.path) ? "active" : ""}"><span class="ic">${i.ic}</span>${i.label}</a>`).join("")}</nav>`;
  document.body.prepend(wrap);
  if (prefs.get("navCollapsed", false)) document.body.classList.add("nav-collapsed");
  document.getElementById("navToggle").onclick = () => {
    document.body.classList.toggle("nav-collapsed");
    prefs.set("navCollapsed", document.body.classList.contains("nav-collapsed"));
  };
  refreshAI();
  setInterval(refreshAI, 20000);
  return document.getElementById("page");
}
async function refreshAI() {
  try {
    const st = await api.status();
    const el = document.getElementById("aiLabel"), d = document.getElementById("aiDot");
    if (!el) return;
    if (st.backend !== "connected") {
      el.textContent = "Backend offline";
      d.className = "dot";
    } else if (st.ai_ready) {
      const prov = st.active_provider ? st.active_provider.charAt(0).toUpperCase() + st.active_provider.slice(1) : "?";
      el.textContent = prov + " active";
      d.className = "dot on";
    } else if (st.configured_count > 0) {
      el.textContent = st.configured_count + " provider" + (st.configured_count > 1 ? "s" : "") + " ready";
      d.className = "dot";
    } else {
      el.textContent = "No AI keys";
      d.className = "dot";
    }
  } catch { /* stay quiet */ }
}
