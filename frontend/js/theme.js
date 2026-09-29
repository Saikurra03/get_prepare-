/* Light/Dark theme — values live in styles.css as tokens
   (:root = light, :root[data-theme="dark"] = dark). This module only picks
   which theme is active, persists the choice, and keeps buttons in sync. */
const THEME_KEY = "berready-theme";

const theme = {
  read() {
    let saved = null;
    try { saved = localStorage.getItem(THEME_KEY); } catch {}
    if (saved === "light" || saved === "dark") return saved;
    return (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
  },
  current() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  },
  set(t) {
    t = t === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem(THEME_KEY, t); } catch {}
    theme.paint();
    return t;
  },
  toggle() {
    return theme.set(theme.current() === "dark" ? "light" : "dark");
  },
  /* Refresh every theme control on the page (☀ when dark, ☾ when light). */
  paint() {
    const dark = theme.current() === "dark";
    document.querySelectorAll(".theme-toggle").forEach((b) => {
      b.textContent = dark ? "☀" : "☾";
      b.title = dark ? "Switch to light mode" : "Switch to dark mode";
      b.setAttribute("aria-label", b.title);
    });
    (theme._painters || []).forEach((f) => f());
  },
  /* Wire up a button (or a [data-pair] pair inside it) as a theme control. */
  mount(el) {
    if (!el) return;
    if (!document.documentElement.dataset.theme) document.documentElement.dataset.theme = theme.read();
    if (el.hasAttribute("data-pair")) {
      const light = el.querySelector("[data-theme-set='light']");
      const dark = el.querySelector("[data-theme-set='dark']");
      if (light) light.onclick = () => theme.set("light");
      if (dark) dark.onclick = () => theme.set("dark");
      const mark = () => {
        const cur = theme.current();
        if (light) light.classList.toggle("primary", cur === "light");
        if (dark) dark.classList.toggle("primary", cur === "dark");
      };
      const origPaint = theme._painters || (theme._painters = []);
      origPaint.push(mark); mark();
    } else {
      el.classList.add("theme-toggle");
      el.onclick = () => theme.toggle();
    }
    theme.paint();
  },
};
theme._painters = [];

/* Keep multiple tabs in sync. */
window.addEventListener("storage", (e) => {
  if (e.key === THEME_KEY && (e.newValue === "light" || e.newValue === "dark")) {
    document.documentElement.dataset.theme = e.newValue;
    theme.paint();
    (theme._painters || []).forEach((f) => f());
  }
});

/* Apply the stored/OS theme as soon as this script loads (covers pages whose
   inline head snippet was stripped by a proxy/cache). */
if (!document.documentElement.dataset.theme) document.documentElement.dataset.theme = theme.read();

window.theme = theme;
