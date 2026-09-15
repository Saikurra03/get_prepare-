"""Interview routes: plan -> answer/evaluate -> retry -> finish (report)."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.engines import interview as eng
from backend.app.documents import context_builder
from backend.app.session import manager as store

router = APIRouter(prefix="/api/interview", tags=["interview"])

# Shared executor — one pool for the whole app, not per-request.
_executor = ThreadPoolExecutor(max_workers=4)

# In-flight request guard: prevents duplicate concurrent requests per session.
_in_flight: dict[str, bool] = {}


class PlanIn(BaseModel):
    doc_ids: list[str] = []
    interview_type: str = "mixed"
    difficulty: str = "intermediate"
    role: str = ""
    num_questions: int = 5


class AnswerIn(BaseModel):
    session_id: str
    answer: str


@router.post("/plan")
def plan(inp: PlanIn):
    docs = store.get_documents(inp.doc_ids) if inp.doc_ids else store.list_documents(section="interview")
    ctx = context_builder.build_context(docs)
    jd_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "jd")
    resume_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "resume")
    signals = context_builder.extract_signals(jd_text, resume_text)
    if inp.role:
        ctx = f"Target role: {inp.role}\n" + ctx
    p = eng.build_plan(inp.interview_type, inp.difficulty, ctx or "General candidate.", signals, inp.num_questions)
    session = store.create_session("interview", {"type": inp.interview_type,
                                                 "difficulty": inp.difficulty, "role": p.get("role", inp.role),
                                                 "context": ctx[:8000], "jd": jd_text[:6000],
                                                 "num_questions": inp.num_questions})
    first_q = (p["questions"] or ["Tell me about yourself."])[0]
    store.append_turn(session["id"], {"question": first_q, "answer": None})
    return {"session_id": session["id"], **p, "current_question": first_q}


@router.post("/answer")
def answer(inp: AnswerIn):
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    # Dedup: reject if a request for this session is already in flight.
    if _in_flight.get(inp.session_id):
        return {"error": "answer already being processed", "code": "in_flight"}
    if not inp.answer or not inp.answer.strip():
        return {"error": "empty speech — answer not heard. Check microphone.", "code": "empty_speech"}
    turns = s.get("turns", [])
    target = None
    for t in reversed(turns):
        if t.get("question") and not t.get("answer"):
            target = t
            break
    if target is None:
        return {"error": "no pending question", "code": "no_question"}

    # Question count guard: use configurable limit from session meta.
    max_q = s["meta"].get("num_questions", 5)
    answered_count = sum(1 for t in turns if t.get("answer"))
    # Allow answering the current pending question even if at limit (it was already presented).
    # But don't generate a follow-up if we're at the limit.
    at_limit = answered_count >= max_q  # will be checked after answer is saved

    _in_flight[inp.session_id] = True
    try:
        itype = s["meta"].get("type", "mixed")
        profile_note = f"focus: {store.get_profile().get('training_focus', '')}"
        # Evaluate + draft follow-up + coaching CONCURRENTLY (all three AI calls run in parallel).
        ev_fut = _executor.submit(eng.evaluate_answer, target["question"], inp.answer, itype)
        nxt_fut = _executor.submit(eng.next_question,
                                  turns + [{"question": target["question"], "answer": inp.answer[:3000]}],
                                  s["meta"].get("context", ""), itype,
                                  s["meta"].get("difficulty", "intermediate"), profile_note)
        ev = ev_fut.result()
        coaching_fut = _executor.submit(eng.generate_coaching, target["question"], inp.answer, ev, itype)
        nxt = nxt_fut.result()
        coaching = coaching_fut.result()
        target["answer"] = inp.answer[:3000]
        target["evaluation"] = ev
        _persist_turns(inp.session_id, turns)
        # Only append follow-up if NOT at question limit.
        new_answered = answered_count + 1
        if new_answered < max_q:
            store.append_turn(inp.session_id, {"question": nxt["question"], "answer": None, "bridge": nxt["bridge"]})
        return {"evaluation": ev, "coaching": coaching, "bridge": nxt["bridge"], "next_question": nxt["question"],
                "retry_suggested": ev.get("retry_suggested", False),
                "retry_instruction": ev.get("retry_instruction", ""),
                "answered": new_answered, "at_limit": new_answered >= max_q}
    finally:
        _in_flight.pop(inp.session_id, None)


@router.post("/retry")
def retry(inp: AnswerIn):
    """Re-answer the last answered question: replaces its answer+evaluation,
    drops the stale pending follow-up, generates a fresh one. Returns old/new for comparison."""
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "answer already being processed", "code": "in_flight"}
    if not inp.answer or not inp.answer.strip():
        return {"error": "empty speech — retry not heard. Check microphone.", "code": "empty_speech"}
    turns = s.get("turns", [])
    idx = next((i for i in range(len(turns) - 1, -1, -1) if turns[i].get("answer")), None)
    if idx is None:
        return {"error": "nothing to retry yet", "code": "no_answer"}
    old = {"answer": turns[idx]["answer"], "score": (turns[idx].get("evaluation") or {}).get("score")}
    # drop any unanswered turns after it (stale follow-up), then re-evaluate in place
    turns = turns[:idx + 1]

    _in_flight[inp.session_id] = True
    try:
        itype = s["meta"].get("type", "mixed")
        profile_note = f"focus: {store.get_profile().get('training_focus', '')}"
        ev_fut = _executor.submit(eng.evaluate_answer, turns[idx]["question"], inp.answer, itype)
        nxt_fut = _executor.submit(eng.next_question,
                                  turns[:-1] + [{"question": turns[idx]["question"], "answer": inp.answer[:3000]}],
                                  s["meta"].get("context", ""), itype,
                                  s["meta"].get("difficulty", "intermediate"), profile_note)
        ev = ev_fut.result()
        coaching_fut = _executor.submit(eng.generate_coaching, turns[idx]["question"], inp.answer, ev, itype)
        nxt = nxt_fut.result()
        coaching = coaching_fut.result()
        turns[idx]["answer"] = inp.answer[:3000]
        turns[idx]["evaluation"] = ev
        _persist_turns(inp.session_id, turns)
        # Retry replaces answer in-place — always append follow-up (retry doesn't change question count).
        store.append_turn(inp.session_id, {"question": nxt["question"], "answer": None, "bridge": nxt["bridge"]})
        return {"evaluation": ev, "coaching": coaching, "bridge": nxt["bridge"], "next_question": nxt["question"],
                "old": old, "new": {"score": ev.get("score")},
                "retry_suggested": ev.get("retry_suggested", False),
                "retry_instruction": ev.get("retry_instruction", "")}
    finally:
        _in_flight.pop(inp.session_id, None)


def _persist_turns(session_id: str, turns: list[dict]) -> None:
    from backend.app.session.manager import _load, _save
    sessions = _load("sessions.json", [])
    for ss in sessions:
        if ss["id"] == session_id:
            ss["turns"] = turns
            break
    _save("sessions.json", sessions)


@router.post("/finish")
def finish(inp: AnswerIn):
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    done = [t for t in s.get("turns", []) if t.get("answer")]
    report = eng.final_report(done, s["meta"].get("role", "Candidate"),
                               s["meta"].get("jd", ""), s["meta"].get("type", ""))
    finished = store.finish_session(inp.session_id, report)
    return {"session_id": inp.session_id, "report": report, "turns": len(done)}
