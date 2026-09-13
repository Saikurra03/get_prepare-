"""Interview routes: plan -> answer/evaluate -> retry -> finish (report)."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.engines import interview as eng
from backend.app.documents import context_builder
from backend.app.session import manager as store

router = APIRouter(prefix="/api/interview", tags=["interview"])

class PlanIn(BaseModel):
    doc_ids: list[str] = []
    interview_type: str = "mixed"
    difficulty: str = "intermediate"
    role: str = ""

class AnswerIn(BaseModel):
    session_id: str
    answer: str

@router.post("/plan")
def plan(inp: PlanIn):
    docs = store.get_documents(inp.doc_ids) if inp.doc_ids else store.list_documents()
    ctx = context_builder.build_context(docs)
    jd_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "jd")
    resume_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "resume")
    signals = context_builder.extract_signals(jd_text, resume_text)
    if inp.role:
        ctx = f"Target role: {inp.role}\n" + ctx
    p = eng.build_plan(inp.interview_type, inp.difficulty, ctx or "General candidate.", signals)
    session = store.create_session("interview", {"type": inp.interview_type,
                                                 "difficulty": inp.difficulty, "role": p.get("role", inp.role),
                                                 "context": ctx[:4000], "jd": jd_text[:4000]})
    first_q = (p["questions"] or ["Tell me about yourself."])[0]
    store.append_turn(session["id"], {"question": first_q, "answer": None})
    return {"session_id": session["id"], **p, "current_question": first_q}

@router.post("/answer")
def answer(inp: AnswerIn):
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
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
    itype = s["meta"].get("type", "mixed")
    profile_note = f"focus: {store.get_profile().get('training_focus', '')}"
    # Evaluate + draft follow-up CONCURRENTLY (halves submit latency vs serial AI calls).
    with ThreadPoolExecutor(max_workers=2) as pool:
        ev_fut = pool.submit(eng.evaluate_answer, target["question"], inp.answer, itype)
        nxt_fut = pool.submit(eng.next_question,
                              turns + [{"question": target["question"], "answer": inp.answer[:3000]}],
                              s["meta"].get("context", ""), itype,
                              s["meta"].get("difficulty", "intermediate"), profile_note)
        ev = ev_fut.result()
        nxt = nxt_fut.result()
    target["answer"] = inp.answer[:3000]
    target["evaluation"] = ev
    _persist_turns(inp.session_id, turns)
    store.append_turn(inp.session_id, {"question": nxt["question"], "answer": None, "bridge": nxt["bridge"]})
    return {"evaluation": ev, "bridge": nxt["bridge"], "next_question": nxt["question"],
            "retry_suggested": ev.get("retry_suggested", False),
            "retry_instruction": ev.get("retry_instruction", "")}

@router.post("/retry")
def retry(inp: AnswerIn):
    """Re-answer the last answered question: replaces its answer+evaluation,
    drops the stale pending follow-up, generates a fresh one. Returns old/new for comparison."""
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    if not inp.answer or not inp.answer.strip():
        return {"error": "empty speech — retry not heard. Check microphone.", "code": "empty_speech"}
    turns = s.get("turns", [])
    idx = next((i for i in range(len(turns) - 1, -1, -1) if turns[i].get("answer")), None)
    if idx is None:
        return {"error": "nothing to retry yet", "code": "no_answer"}
    old = {"answer": turns[idx]["answer"], "score": (turns[idx].get("evaluation") or {}).get("score")}
    # drop any unanswered turns after it (stale follow-up), then re-evaluate in place
    turns = turns[:idx + 1]
    itype = s["meta"].get("type", "mixed")
    profile_note = f"focus: {store.get_profile().get('training_focus', '')}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        ev_fut = pool.submit(eng.evaluate_answer, turns[idx]["question"], inp.answer, itype)
        nxt_fut = pool.submit(eng.next_question,
                              turns[:-1] + [{"question": turns[idx]["question"], "answer": inp.answer[:3000]}],
                              s["meta"].get("context", ""), itype,
                              s["meta"].get("difficulty", "intermediate"), profile_note)
        ev = ev_fut.result()
        nxt = nxt_fut.result()
    turns[idx]["answer"] = inp.answer[:3000]
    turns[idx]["evaluation"] = ev
    _persist_turns(inp.session_id, turns)
    store.append_turn(inp.session_id, {"question": nxt["question"], "answer": None, "bridge": nxt["bridge"]})
    return {"evaluation": ev, "bridge": nxt["bridge"], "next_question": nxt["question"],
            "old": old, "new": {"score": ev.get("score")},
            "retry_suggested": ev.get("retry_suggested", False),
            "retry_instruction": ev.get("retry_instruction", "")}

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
    report = eng.final_report(done, s["meta"].get("role", "Candidate"), s["meta"].get("jd", ""))
    finished = store.finish_session(inp.session_id, report)
    return {"session_id": inp.session_id, "report": report, "turns": len(done)}
