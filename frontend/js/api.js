/* Thin typed wrapper over the real backend APIs. No fake data. */
const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "";
const api = {
  async _j(res) {
    if (!res.ok) throw new Error(`request failed (${res.status})`);
    return res.json();
  },
  get(p) { return fetch(API_BASE + p).then(api._j); },
  post(p, body, opts = {}) {
    return fetch(API_BASE + p, { method: "POST", headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), ...opts }).then(api._j);
  },
  health: () => api.get("/api/health"),
  sessionHealth: () => api.get("/api/session/health"),
  profile: () => api.get("/api/session/profile"),
  dashboard: () => api.get("/api/session/dashboard"),
  sessions: () => api.get("/api/session/list"),
  sessionDetail: (sid) => api.get(`/api/session/detail?sid=${encodeURIComponent(sid)}`),
  createSession: (kind, meta) => api.post("/api/session/create", { kind, ...meta }),
  analyze: (t) => api.post("/api/coach/analyze", t),
  retryCompare: (first, second) => api.post("/api/coach/retry-compare", { first, second }),
  docs: (section) => api.get(`/api/documents/list${section ? "?section=" + encodeURIComponent(section) : ""}`),
  uploadDoc: (file, kind, section) => {
    const fd = new FormData(); fd.append("file", file); fd.append("kind", kind);
    if (section) fd.append("section", section);
    return fetch(API_BASE + "/api/documents/upload", { method: "POST", body: fd }).then(api._j);
  },
  clearDocs: (section) => api.post("/api/documents/clear", { section: section || "" }),
  pasteDoc: (text, kind, filename, section) => api.post("/api/documents/paste", { text, kind, filename: filename || "", section: section || "" }),
  planInterview: (b) => api.post("/api/interview/plan", b),
  answerInterview: (sid, answer) => api.post("/api/interview/answer", { session_id: sid, answer }),
  retryInterview: (sid, answer) => api.post("/api/interview/retry", { session_id: sid, answer }),
  finishInterview: (sid) => api.post("/api/interview/finish", { session_id: sid, answer: "" }),
  sttTranscribe: (blob, language = "en") => {
    const fd = new FormData();
    fd.append("file", blob, "recording.webm");
    fd.append("language", language);
    return fetch(API_BASE + "/api/stt/transcribe", { method: "POST", body: fd }).then(api._j);
  },
  sttHealth: () => api.get("/api/stt/health"),
  ttsSpeak: (text, voiceId) => fetch(API_BASE + "/api/tts/speak", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice_id: voiceId || "" }),
  }),
  ttsHealth: () => api.get("/api/tts/health"),
  status: () => api.get("/api/status"),
};
const prefs = {
  get(k, d) { try { const v = localStorage.getItem("br:" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("br:" + k, JSON.stringify(v)); } catch {} },
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtT = (ts) => { if (!ts) return "—"; const d = new Date(ts * 1000); return isNaN(d.getTime()) ? "—" : d.toLocaleString(); };
const fmtDur = (ms) => { const s = Math.floor(ms / 1000); return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
