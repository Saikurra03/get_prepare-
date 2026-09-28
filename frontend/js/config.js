/* Frontend config — API base URL, set per environment. */
window.APP_CONFIG = window.APP_CONFIG || {};
// Local dev (python run.py) serves frontend + API from the same origin — use it.
// Deployed frontends keep calling the Render backend.
const _isLocal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
window.APP_CONFIG.API_BASE = window.APP_CONFIG.API_BASE || (_isLocal ? "" : "https://beready-kz42.onrender.com");
