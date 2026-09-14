# BERREADY — COMPLETE FIXING PLAN

Based on comprehensive codebase inspection (70+ files inspected across backend, frontend, tests, config).

---

## EXECUTIVE SUMMARY

**Architecture**: FastAPI backend + vanilla JS frontend, 4 AI providers (Gemini/Groq/OpenRouter/Cohere) with key rotation, browser Web Speech API for STT, JSON file storage.

**Critical Finding**: STT uses **browser Web Speech API** (not a selectable model) — this is the root cause of word substitution errors. No server-side STT exists.

---

## PHASE 1 FINDINGS — CATEGORIZED

### 🔴 CRITICAL BUGS (Fix Immediately)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| C1 | **STT uses browser Web Speech API only** — no server-side STT, no model selection, poor accuracy for technical terms/accents | `media.js`, `workspace.js`, `ilive.js` | Words incorrectly replaced; no fallback; no model choice |
| C2 | **Interview question count not enforced** — `NQ` from prefs (default 5) vs plan generates up to 6; retry adds extra questions | `ilive.js:6`, `routes_interview.py:35`, `interview.py:35` | User gets ≠ selected question count |
| C3 | **Race condition in submit** — `submitting` flag but no request deduplication at API level; rapid clicks can create duplicate turns | `ilive.js:88`, `routes_interview.py:40` | Duplicate API calls, corrupted session state |
| C4 | **Retry adds extra question** — retry replaces answer but appends new follow-up, exceeding question count | `routes_interview.py:73`, `ilive.js:48` | Exceeds selected question count |
| C5 | **ThreadPoolExecutor per request** — creates new executor per `/answer` and `/retry` call | `routes_interview.py:57`, `routes_interview.py:91` | Resource waste, potential thread exhaustion |

### 🟠 FUNCTIONAL PROBLEMS (High Priority)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| F1 | **No server-side STT** — only browser Web Speech API; cannot use Whisper or better models | `media.js`, no backend STT endpoint | Cannot fix accuracy; no model choice |
| F2 | **Question count mismatch** — plan generates up to 6, `NQ` defaults to 5, adaptive follow-ups unlimited | `interview.py:35`, `ilive.js:6`, `routes_interview.py:68` | Unpredictable question count |
| F3 | **No audio recording** — cannot replay, cannot send to server-side STT | `media.js`, `workspace.js`, `ilive.js` | No review, no server STT possible |
| F4 | **Interview finish logic** — `answered >= NQ` check but adaptive follow-ups continue past NQ | `ilive.js:109` | Session doesn't end at selected count |
| F5 | **Retry flow** — replaces answer but appends new follow-up question | `routes_interview.py:102` | Question count drift |
| F6 | **No request deduplication at API level** — frontend flag only | `routes_interview.py` | Duplicate submissions under load |

### 🟡 STT ACCURACY PROBLEMS (Critical - User Reported)

| # | Issue | Root Cause | Fix Strategy |
|---|-------|------------|--------------|
| S1 | Words incorrectly replaced | Browser Web Speech API (Chrome=Google cloud, Safari=Apple, Firefox=limited) | Add server-side Whisper (Groq/OpenAI/local) |
| S2 | No model selection | Only browser API available | Add Groq Whisper / OpenAI Whisper endpoint |
| S3 | No confidence scores | Browser API doesn't expose reliably | Server STT returns confidence |
| S4 | No audio recording for review | Only real-time transcript | Add MediaRecorder + audio upload |
| S5 | Technical terms misrecognized | Browser STT not trained on domain vocab | Whisper handles technical terms better |
| S6 | No manual correction UI | Transcript is contenteditable but no STT alternatives | Show confidence + alternatives |

### 🟢 DASHBOARD/HISTORY PROBLEMS (Medium)

| # | Issue | Location | Status |
|---|-------|----------|--------|
| D1 | **Mostly fixed** — dashboard shows only real data, metrics have basis, trend at ≥2 pts | `dashboard.py`, `progress.js` | ✅ Mostly OK |
| D2 | **History filters** — bucket logic maps podcast→podcast, story→storytelling, but "qa" and "spontaneous" both map to "qa" | `history.js:4` | Minor |
| D3 | **Zero-count sections never render** — enforced in backend | `dashboard.py:38` | ✅ Fixed |
| D4 | **Profile dashboard** — uses real session data | `profile.js`, `dashboard.py` | ✅ OK |
| D4 | **Trend needs ≥2 points** — enforced | `progress.js:87` | ✅ Fixed |

### 🟣 FAKE/HARDCODED DATA (Low-Medium)

| # | Item | Location | Type |
|---|------|----------|------|
| FK1 | `coach()` offline fallback hardcoded responses | `coaching.py:52` | Offline fallback |
| FK2 | `interview.py` offline fallback questions | `interview.py:37` | Offline fallback |
| FK3 | `interview.py` offline fallback evaluation | `interview.py:122` | Offline fallback |
| FK4 | `dashboard.py` fallback summary line | `dashboard.py:59` | Explicit "not enough data" |
| FK5 | `speech_analysis.py` hardcoded filler/qualifier lists | `speech_analysis.py:5` | Heuristic (acceptable) |
| FK6 | `coaching.py` hardcoded scenario focus map | `coaching.py:7` | Config (acceptable) |

### 🔵 UNWANTED/UNUSED CODE (Low)

| # | Item | Location | Reason |
|---|------|----------|--------|
| U1 | `vision.py` + `vision_eng` import | `routes_coach.py:6`, `vision.py` | Never used (frame always None) |
| U2 | `cohere_provider.py`, `openrouter_provider.py` | `ai/` | Exist but untested; keys in .env |
| U3 | `workspace.js` podcast mode | `workspace.js` | No podcast-specific backend |
| U4 | `ThreadPoolExecutor` per request | `routes_interview.py:57,91` | Resource waste |
| U5 | `speech_analysis.py` in `vision.py` import | `vision.py:1` | Unused import |

---

## PHASE 2 — COMPLETE FIXING PLAN

### PRIORITY 0: STT ARCHITECTURE REDESIGN (Week 1)

**Goal**: Replace browser-only STT with server-side Whisper (Groq) + keep browser as fallback

| Task | Description | Files |
|------|-------------|-------|
| **P0.1** | Add `/api/stt/transcribe` endpoint accepting audio/webm or audio/wav | New: `routes_stt.py`, `engines/stt.py` |
| **P0.2** | Integrate Groq Whisper (`whisper-large-v3-turbo`) as primary STT | `engines/stt.py`, `groq_provider.py` |
| **P0.3** | Add audio recording in frontend (MediaRecorder) → upload to `/api/stt/transcribe` | `media.js`, `workspace.js`, `ilive.js` |
| **P0.4** | Keep browser Web Speech API as real-time preview + fallback | `media.js` |
| **P0.5** | Show STT confidence + alternatives in UI; allow manual correction | `media.js`, `workspace.js`, `ilive.js` |
| **P0.6** | Add STT provider to key rotation (Groq key used for Whisper) | `key_manager.py`, `provider_manager.py` |
| **P0.7** | STT config in `.env`: `STT_PROVIDER=groq`, `STT_MODEL=whisper-large-v3-turbo` | `.env.example`, `config.py` |

**Why Groq Whisper?**
- Already have Groq keys and provider infrastructure
- `whisper-large-v3-turbo` is fast (~10x realtime) and accurate
- Fits existing key rotation/fallback architecture
- No new dependencies beyond `groq` SDK (already in requirements)

### PRIORITY 1: INTERVIEW FLOW FIXES (Week 1-2)

| Task | Description | Files |
|------|-------------|-------|
| **P1.1** | Fix question count: plan generates exactly `N` questions; no extra adaptive beyond N | `interview.py:build_plan`, `routes_interview.py` |
| **P1.2** | Add `question_number` and `total_questions` to session meta; enforce in backend | `routes_interview.py`, `session/manager.py` |
| **P1.3** | Request deduplication: add `request_id` to AnswerIn; reject duplicates at API level | `routes_interview.py`, `ilive.js` |
| **P1.4** | Fix retry: replace answer in-place WITHOUT adding new follow-up; decrement remaining count | `routes_interview.py:73`, `interview.py` |
| **P1.5** | Enforce exact question count: stop at N, go to finish | `ilive.js`, `routes_interview.py` |
| **P1.6** | Shared ThreadPoolExecutor (module-level) instead of per-request | `routes_interview.py` |
| **P1.7** | Validate `NQ` against plan's actual question count on setup | `isetup.js`, `routes_interview.py` |

### PRIORITY 2: DASHBOARD/HISTORY CLEANUP (Week 2)

| Task | Description | Files |
|------|-------------|-------|
| **P2.1** | Verify zero fake data in dashboard — audit `progress.js` for any hardcoded defaults | `progress.js` |
| **P2.2** | History filter: fix "qa" vs "spontaneous" bucket collision | `history.js:4` |
| **P2.3** | Profile dashboard: ensure all metrics traced to real sessions | `profile.js`, `dashboard.py` |
| **P2.4** | Remove any remaining hardcoded fallbacks that show as real data | `progress.js`, `profile.js` |
| **P2.5** | Add "Not enough data" for sections with 0 completed sessions (already done) | — |

### PRIORITY 3: FAKE DATA REMOVAL (Week 2)

| Task | Description | Files |
|------|-------------|-------|
| **P3.1** | Move offline fallbacks to explicit "offline mode" responses — never masquerade as real | `coaching.py`, `interview.py` |
| **P3.2** | Ensure all offline responses marked `provider: "offline"` and UI shows indicator | `coaching.py`, `interview.py`, `service.py` |
| **P3.3** | Remove vision.py (unused) | `vision.py`, `routes_coach.py`, `coaching.py` |
| **P3.4** | Audit cohere/openrouter providers — if untested, mark as experimental or remove | `ai/` |

### PRIORITY 4: CLEANUP & TECH DEBT (Week 2-3)

| Task | Description | Files |
|------|-------------|-------|
| **P4.1** | Replace per-request ThreadPoolExecutor with shared module-level executor | `routes_interview.py` |
| **P4.2** | Add request deduplication middleware or endpoint-level check | `routes_interview.py` |
| **P4.3** | Session storage: add file locking or migrate to SQLite for concurrency | `session/manager.py` |
| **P4.4** | Remove unused imports (vision in coaching, etc.) | `coaching.py`, `routes_coach.py` |
| **P4.5** | Add integration tests for: STT endpoint, interview question count enforcement, retry flow, request deduplication | `tests/` |

---

## PHASE 3 — FUTURE IMPLEMENTATION (Post-Fix)

*Marked for after all bugs fixed. Do NOT implement during bug-fix phase.*

| # | Item | Description | Priority |
|---|------|-------------|----------|
| FI1 | **Local Whisper (WASM)** | Client-side whisper.cpp for offline, zero-latency STT | Medium |
| FI2 | **SQLite/PostgreSQL** | Replace JSON files for concurrent access, queries | High |
| FI3 | **WebSocket STT** | Streaming audio → streaming transcript (lower latency) | Medium |
| FI4 | **Speaker diarization** | Separate interviewer/candidate in recordings | Low |
| FI5 | **Pronunciation scoring** | Phoneme-level analysis via Whisper + phoneme alignment | Medium |
| FI6 | **Interview templates** | Save/load custom interview configurations | Low |
| FI7 | **Export/Import sessions** | JSON/PDF export for portability | Low |
| FI8 | **Multi-user support** | Auth, user isolation, shared sessions | High |
| FI9 | **Mobile app / PWA** | Offline practice, background sync | Medium |
| FI10 | **Analytics API** | Query language for session data | Low |

---

## FILES TO CHANGE — SUMMARY

### New Files
- `backend/app/engines/stt.py` — Whisper integration
- `backend/app/api/routes_stt.py` — `/api/stt/transcribe` endpoint
- `tests/test_stt.py` — STT integration tests
- `tests/test_interview_flow.py` — Question count, retry, deduplication tests

### Modified Files (Backend)
- `backend/app/config.py` — STT config
- `backend/app/ai/key_manager.py` — STT provider key support
- `backend/app/ai/provider_manager.py` — STT in rotation
- `backend/app/ai/groq_provider.py` — Whisper support
- `backend/app/engines/interview.py` — Question count enforcement, retry fix
- `backend/app/engines/dashboard.py` — Already good; verify
- `backend/app/api/routes_interview.py` — Question count, deduplication, retry fix, shared executor
- `backend/app/api/routes_stt.py` — **NEW** STT endpoint
- `backend/app/api/routes_coach.py` — Remove vision import
- `backend/app/main.py` — Register STT router
- `backend/app/session/manager.py` — Question count in session meta
- `requirements.txt` — Verify `groq` supports Whisper (already does)

### Modified Files (Frontend)
- `frontend/js/media.js` — Audio recording + STT upload + browser fallback
- `frontend/js/ilive.js` — Question count enforcement, deduplication, retry fix
- `frontend/js/workspace.js` — Same STT improvements
- `frontend/js/api.js` — STT endpoint + request_id
- `frontend/js/progress.js` — Verify no fake data
- `frontend/js/history.js` — Fix qa/spontaneous bucket
- `frontend/index.html`, `interview.html`, etc. — No visual changes

### Tests
- `tests/test_stt.py` — STT transcription accuracy, fallback
- `tests/test_interview_flow.py` — Question count, retry, deduplication
- `tests/test_dashboard.py` — No fake data invariants

---

## TESTING STRATEGY

| Test | Method | Expected |
|------|--------|----------|
| STT accuracy | Upload known audio → compare transcript | Groq Whisper >95% on clear audio |
| STT fallback | Disable Groq key → browser STT used | Graceful degradation |
| Question count | Start 5-question interview → count questions | Exactly 5 asked |
| Retry flow | Answer → retry → verify count | Count unchanged |
| Duplicate submit | Rapid click Submit 5x | Only 1 API call |
| Dashboard empty | Fresh profile → /progress | "No completed sessions" |
| Dashboard real | Complete interview → /progress | Real metrics, basis shown |
| Trend | 1 session → no trend; 2+ → trend line | Correct gating |

---

## STT PROVIDER DECISION: **Groq Whisper (whisper-large-v3-turbo)**

**Rationale:**
1. **Already integrated** — Groq provider exists, keys configured, rotation works
2. **Speed** — ~10x realtime on Groq LPU; sub-second for typical answers
3. **Accuracy** — Large-v3-turbo is SOTA for open models; handles technical terms well
4. **Cost** — Free tier generous; pay-as-you-go cheap
5. **Architecture fit** — Reuses existing key_manager, provider_manager, fallback chain
6. **No new deps** — `groq` SDK already in requirements.txt

**Fallback chain**: Groq Whisper → OpenAI Whisper (if OpenRouter supports) → Browser Web Speech API

---

## ESTIMATED EFFORT

| Phase | Tasks | Est. Days |
|-------|-------|-----------|
| P0: STT Architecture | 7 tasks | 3-4 |
| P1: Interview Flow | 7 tasks | 3-4 |
| P2: Dashboard/History | 5 tasks | 2 |
| P3: Fake Data Removal | 4 tasks | 1 |
| P4: Cleanup/Tech Debt | 5 tasks | 2 |
| **Testing & Integration** | | 2-3 |
| **Total** | | **11-15 days** |

---

## APPROVAL REQUEST

**Ready to implement?** This plan addresses all critical bugs (especially STT), fixes interview flow, cleans dashboard/history, removes fake data, and reduces tech debt — all while keeping the blue/dark visual design intact.

**Do you approve this plan?** If yes, I'll begin Phase 3 implementation immediately.