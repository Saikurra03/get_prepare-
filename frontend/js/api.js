/* Thin typed wrapper over the real backend APIs. No fake data. */
const api = {
  async _j(res) {
    if (!res.ok) throw new Error(`request failed (${res.status})`);
    return res.json();
  },
  get(p) { return fetch(p).then(api._j); },
  post(p, body, opts = {}) {
    return fetch(p, { method: "POST", headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), ...opts }).then(api._j);
  },
  health: () => api.get("/api/health"),
  sessionHealth: () => api.get("/api/session/health"),
  profile: () => api.get("/api/session/profile"),
  sessions: () => api.get("/api/session/list"),
  sessionDetail: (sid) => api.get(`/api/session/detail?sid=${encodeURIComponent(sid)}`),
  createSession: (kind, meta) => api.post("/api/session/create", { kind, ...meta }),
  analyze: (t) => api.post("/api/coach/analyze", t),
  retryCompare: (first, second) => api.post("/api/coach/retry-compare", { first, second }),
  docs: () => api.get("/api/documents/list"),
  uploadDoc: (file, kind) => {
    const fd = new FormData(); fd.append("file", file); fd.append("kind", kind);
    return fetch("/api/documents/upload", { method: "POST", body: fd }).then(api._j);
  },
  clearDocs: () => api.post("/api/documents/clear", {}),
  planInterview: (b) => api.post("/api/interview/plan", b),
  answerInterview: (sid, answer) => api.post("/api/interview/answer", { session_id: sid, answer }),
  retryInterview: (sid, answer) => api.post("/api/interview/retry", { session_id: sid, answer }),
  finishInterview: (sid) => api.post("/api/interview/finish", { session_id: sid, answer: "" }),
};
const prefs = {
  get(k, d) { try { const v = localStorage.getItem("br:" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("br:" + k, JSON.stringify(v)); } catch {} },
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtT = (ts) => { try { return new Date(ts * 1000).toLocaleString(); } catch { return ""; } };
const fmtDur = (ms) => { const s = Math.floor(ms / 1000); return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
