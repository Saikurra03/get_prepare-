# BeReady Boy — AI Communication Coach + AI Interview Coach

> "A world-class communication coach and interviewer sitting beside me while I speak."
> NOT an AI grammar checker with a camera.

## Stack (verified Sep 2026)
- Backend: FastAPI (Python 3.12), modular: `ai/ documents/ engines/ session/ api/`
- Frontend: static HTML/CSS/JS (no build step), Web Speech API + getUserMedia + SpeechSynthesis
- AI: Gemini (`google-genai` SDK, default `gemini-2.5-flash`) + Groq (`groq` SDK, default `llama-3.3-70b-versatile`), auto-fallback on 429/quota/timeout/network/malformed
- Docs: pypdf + python-docx + txt

## Quickstart
```powershell
cd C:\Users\saiku\OneDrive\Desktop\BEREADY_BOY
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill GEMINI_API_KEY and/or GROQ_API_KEY
python run.py                 # http://127.0.0.1:8000
```

## Flow
SPEAK -> LISTEN/WATCH -> UNDERSTAND -> ANALYZE -> COACH -> RETRY -> COMPARE -> REMEMBER -> ADAPT

- Live coaching: minimal UI while speaking, detailed feedback after. Interrupt only on IMPACT x FREQUENCY x CONTEXT.
- Interview mode: upload JD/Resume/topic PDF -> analyzed -> adaptive questions on screen + optional AI voice -> voice answers -> follow-ups -> final report + retry.
- Privacy: camera/mic indicators, no raw A/V stored by default (only derived coaching data in `backend/data/`).

## API (selected)
- `GET /api/health` — provider status (subtle: "Gemini" / "Groq — fallback active")
- `POST /api/coach/analyze` — {transcript, scenario, visual_signals, profile} -> {priority_feedback, interruption, scores}
- `POST /api/coach/retry-compare` — {first, second} -> improvement diff
- `POST /api/documents/upload` — pdf/docx/txt -> {doc_id, summary, skills, status}
- `POST /api/interview/plan` — {doc_ids, interview_type, difficulty, role} -> {plan, questions}
- `POST /api/interview/next` — {session_id, last_answer} -> adaptive follow-up
- `POST /api/interview/finish` — {session_id} -> full report
- `GET/POST /api/session/*` — sessions + personal communication profile

## Multiple API keys + rotation
Add as many keys as you have — no code changes needed:
`GEMINI_API_KEY_1.._N`, `GROQ_API_KEY_1.._N` (legacy single `GEMINI_API_KEY`/`GROQ_API_KEY` also work).
Per request: Gemini Key 1 → Key 2 → … → Groq Key 1 → …. A key that hits 429/quota/timeout
takes a cooldown (exponential backoff, tunable via `AI_KEY_COOLDOWN_SECONDS`) and is never
retried twice in one request; attempts are capped by `AI_MAX_ATTEMPTS`. Frontend only ever
sees `AI Ready` (debug: `Gemini — Key 2 active`) — key values never leave the server.

## Tests
```powershell
pytest -q
```
Covers: fallback (429/quota/timeout), doc extraction, response parsing, coaching priority, interruption, retry, interview gen + follow-up, scoring, profile, session persistence, mic/camera failure paths, invalid docs.

## North star
After repeated use, can the user walk into an interview, speak naturally, explain complex ideas clearly, answer unexpected questions, tell memorable stories, and hold attention?
