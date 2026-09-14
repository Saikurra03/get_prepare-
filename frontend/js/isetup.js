/* Interview Setup: type, role, difficulty, questions, docs, voice, camera, mic. Then start. */
const qs = new URLSearchParams(location.search);
const page = buildShell("Interview setup", "BERREADY / Interview / Setup");
const TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"];
const selType = qs.get("type") || "mixed";
page.innerHTML = `
  <div class="grid g2"><div class="card"><h3>Configuration</h3>
    <label class="fl">Interview type</label><select id="s_type">${TYPES.map((t) => `<option ${t === selType ? "selected" : ""}>${t}</option>`).join("")}</select>
    <div id="customBox" style="display:${selType === "custom" ? "" : "none"}">
      <label class="fl">Custom focus</label><input type="text" id="s_custom" placeholder="e.g. system design + leadership" style="width:100%"/></div>
    <label class="fl">Role</label><input type="text" id="s_role" placeholder="e.g. Software Engineer" style="width:100%" value="${esc(prefs.get("role", ""))}"/>
    <label class="fl">Difficulty</label><select id="s_diff">
      ${["beginner", "intermediate", "advanced", "expert"].map((d) => `<option ${d === prefs.get("diff", "intermediate") ? "selected" : ""}>${d}</option>`).join("")}</select>
    <label class="fl">Number of questions</label><select id="s_n"><option>3</option><option selected>5</option><option>7</option><option>10</option></select>
  </div>
  <div class="card"><h3>Documents & devices</h3>
    <div id="docBox" class="small mut">Loading documents…</div>
    <label class="fl">Devices</label><div class="row"><button id="bCam">Camera: off</button><button id="bMic">Mic: off</button></div>
    <div class="row mt"><button class="primary" id="bGo">Start interview</button><a class="btn ghost" href="/interview">Back</a></div>
    <div id="err" class="small mt" style="color:var(--bad)"></div>
  </div></div>`;
const media = createMedia();
document.getElementById("bCam").onclick = async (e) => {
  alert("Camera turns on in the live room. Setup only records your choice.");
  prefs.set("cam", !prefs.get("cam", false));
  e.target.textContent = `Camera: ${prefs.get("cam") ? "on" : "off"}`;
};
document.getElementById("bCam").textContent = `Camera: ${prefs.get("cam", false) ? "on" : "off"}`;
document.getElementById("bMic").onclick = (e) => {
  prefs.set("mic", !prefs.get("mic", false));
  e.target.textContent = `Mic: ${prefs.get("mic", false) ? "on" : "off"}`;
};
document.getElementById("bMic").textContent = `Mic: ${prefs.get("mic", false) ? "on" : "off"}`;
(async () => {
  try {
    const docs = (await api.docs()).documents || [];
    const pre = (qs.get("docs") || "").split(",").filter(Boolean);
    document.getElementById("docBox").innerHTML = docs.length
      ? docs.map((d) => `<label style="display:block;font-weight:400"><input type="checkbox" data-doc="${d.id}" ${pre.length ? (pre.includes(d.id) ? "checked" : "") : "checked"}/> ${esc(d.filename)} <span class="dim">(${esc(d.kind)})</span></label>`).join("") +
        `<p class="small dim">Only checked documents feed this interview. <a href="/prepare">Manage</a></p>`
      : `No documents. <a href="/prepare">Upload resume / JD</a> for a personalized interview — or start general.`;
  } catch { document.getElementById("docBox").textContent = "Server unreachable."; }
})();
document.getElementById("s_type").onchange = (e) => {
  document.getElementById("customBox").style.display = e.target.value === "custom" ? "" : "none";
};
document.getElementById("bGo").onclick = async () => {
  const btn = document.getElementById("bGo"); btn.disabled = true; btn.textContent = "Preparing…";
  const docIds = [...document.querySelectorAll("[data-doc]:checked")].map((c) => c.dataset.doc);
  const type = document.getElementById("s_type").value;
  const custom = (document.getElementById("s_custom")?.value || "").trim();
  const role = document.getElementById("s_role").value;
  prefs.set("role", role);
  prefs.set("diff", document.getElementById("s_diff").value);
  prefs.set("nQ", document.getElementById("s_n").value);
  try {
    const r = await api.planInterview({ doc_ids: docIds, interview_type: type,
      difficulty: document.getElementById("s_diff").value,
      role: type === "custom" && custom ? `Custom focus: ${custom}. Role: ${role}` : role,
      num_questions: parseInt(document.getElementById("s_n").value, 10) });
    location.href = `/interview-live?sid=${r.session_id}`;
  } catch { document.getElementById("err").textContent = "Could not start — is the server running?"; btn.disabled = false; btn.textContent = "Start interview"; }
};
