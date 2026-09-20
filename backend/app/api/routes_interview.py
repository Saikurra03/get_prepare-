"""Interview routes: plan -> answer/skip/change-topic -> finish (report).
Questions come from a pre-generated list. No instant feedback during the interview."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.engines import interview as eng
from backend.app.engines import visual_analysis as vis
from backend.app.documents import context_builder
from backend.app.session import manager as store

router = APIRouter(prefix="/api/interview", tags=["interview"])

_executor = ThreadPoolExecutor(max_workers=4)
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
    visual: dict | None = None


def _get_next_question(meta: dict, turns: list[dict]) -> dict | None:
    """Pick the next question from the pre-generated list based on question_index."""
    questions = meta.get("questions", [])
    idx = meta.get("question_index", 0)
    if idx >= len(questions):
        return None
    q = questions[idx]
    return {"q": q["q"] if isinstance(q, dict) else q, "topic": q.get("topic", "general") if isinstance(q, dict) else "general"}


def _get_next_different_topic(meta: dict, turns: list[dict]) -> dict | None:
    """Pick the next question that has a different topic than the current one."""
    questions = meta.get("questions", [])
    idx = meta.get("question_index", 0)
    if idx >= len(questions):
        return None
    current_topic = questions[idx].get("topic", "general") if isinstance(questions[idx], dict) else "general"
    # Look ahead for a different topic
    for i in range(idx + 1, len(questions)):
        q = questions[i]
        topic = q.get("topic", "general") if isinstance(q, dict) else "general"
        if topic != current_topic:
            return {"q": q["q"] if isinstance(q, dict) else q, "topic": topic, "jump_to": i}
    # No different topic found — just use next
    return None


def _advance_question(session_id: str, meta: dict, turns: list[dict], jump_to: int | None = None) -> dict | None:
    """Advance to next question, update session meta. Returns the next question or None."""
    if jump_to is not None:
        meta["question_index"] = jump_to
    else:
        meta["question_index"] = meta.get("question_index", 0) + 1
    # Persist the updated question_index
    _persist_meta(session_id, meta)
    nq = _get_next_question(meta, turns)
    return nq


def _persist_meta(session_id: str, meta: dict) -> None:
    """Persist updated meta back to session."""
    from backend.app.session.manager import _load, _save, _decode_session
    raw_id = session_id
    decoded = _decode_session(session_id)
    if decoded:
        raw_id = decoded.get("id", session_id)
    sessions = _load("sessions.json", [])
    for ss in sessions:
        if ss["id"] == raw_id:
            ss["meta"] = meta
            break
    _save("sessions.json", sessions)


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
    questions = p.get("questions", [])
    session = store.create_session("interview", {
        "type": inp.interview_type,
        "difficulty": inp.difficulty,
        "role": p.get("role", inp.role),
        "context": ctx[:8000],
        "jd": jd_text[:6000],
        "num_questions": inp.num_questions,
        "questions": questions,
        "question_index": 0,
    })
    first_q = questions[0]["q"] if questions and isinstance(questions[0], dict) else (questions[0] if questions else "Tell me about yourself.")
    store.append_turn(session["id"], {"question": first_q, "answer": None})
    return {"session_id": session["id"], "role": p.get("role"),
            "current_question": first_q, "total_questions": len(questions)}


@router.post("/answer")
def answer(inp: AnswerIn):
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
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

    max_q = s["meta"].get("num_questions", 5)
    answered_count = sum(1 for t in turns if t.get("answer"))

    _in_flight[inp.session_id] = True
    try:
        itype = s["meta"].get("type", "mixed")
        diff = s["meta"].get("difficulty", "intermediate")
        ctx = s["meta"].get("context", "")
        # Run evaluation, coaching, model answer in background (stored for report, NOT shown now)
        ev_fut = _executor.submit(eng.evaluate_answer, target["question"], inp.answer, itype, diff)
        ma_fut = _executor.submit(eng.generate_model_answer, target["question"], inp.answer, itype, ctx, diff)
        ev = ev_fut.result()
        coaching_fut = _executor.submit(eng.generate_coaching, target["question"], inp.answer, ev, itype, diff)
        model = ma_fut.result()
        coaching = coaching_fut.result()
        # Process visual data
        visual_events = (inp.visual or {}).get("events", [])
        visual_result = vis.analyze_visuals(visual_events, target["question"], inp.answer, itype, diff)
        if visual_result.get("score_impact", 0) != 0:
            ev["score"] = max(1.0, min(10.0, ev.get("score", 5) + visual_result["score_impact"]))
        # Save answer + evaluation to turn (for final report)
        target["answer"] = inp.answer[:3000]
        target["evaluation"] = ev
        target["coaching"] = coaching
        target["model_answer"] = model.get("model_answer", "")
        target["visual_events"] = visual_events
        target["visual_coaching"] = visual_result.get("coaching", "")
        _persist_turns(inp.session_id, turns)
        # Advance to next question from the pre-generated list
        new_answered = answered_count + 1
        nq = _advance_question(inp.session_id, s["meta"], turns)
        if nq is None or new_answered >= max_q:
            return {"next_question": None, "bridge": "That's all the questions. Let me prepare your report.",
                    "answered": new_answered, "at_limit": True}
        # Append the next question turn
        bridge = f"Good. Let's move on."
        store.append_turn(inp.session_id, {"question": nq["q"], "answer": None, "bridge": bridge})
        return {"next_question": nq["q"], "bridge": bridge,
                "answered": new_answered, "at_limit": False}
    finally:
        _in_flight.pop(inp.session_id, None)


@router.post("/skip")
def skip(inp: AnswerIn):
    """Skip the current question — counts as answered with score 0."""
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "request already being processed", "code": "in_flight"}
    turns = s.get("turns", [])
    target = None
    for t in reversed(turns):
        if t.get("question") and not t.get("answer"):
            target = t
            break
    if target is None:
        return {"error": "no pending question", "code": "no_question"}

    max_q = s["meta"].get("num_questions", 5)
    answered_count = sum(1 for t in turns if t.get("answer"))
    # Mark as skipped
    target["answer"] = "[skipped]"
    target["evaluation"] = {"score": 0, "strength": "", "main_issue": "skipped",
                            "good": [], "biggest_issue": "Skipped", "relevance": {"verdict": "skipped", "note": "Question was skipped"},
                            "dimensions": {}, "vocabulary": "", "fillers": "", "pacing": "", "completeness": ""}
    target["coaching"] = {"appreciation": "", "priority": "", "specific_feedback": "Question was skipped.",
                          "improvement": "", "next_step": ""}
    target["model_answer"] = ""
    _persist_turns(inp.session_id, turns)
    new_answered = answered_count + 1
    nq = _advance_question(inp.session_id, s["meta"], turns)
    if nq is None or new_answered >= max_q:
        return {"next_question": None, "bridge": "That's all the questions.",
                "answered": new_answered, "at_limit": True}
    bridge = "Moving on."
    store.append_turn(inp.session_id, {"question": nq["q"], "answer": None, "bridge": bridge})
    return {"next_question": nq["q"], "bridge": bridge,
            "answered": new_answered, "at_limit": False}


@router.post("/change-topic")
def change_topic(inp: AnswerIn):
    """Skip current question and jump to a question with a different topic."""
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "request already being processed", "code": "in_flight"}
    turns = s.get("turns", [])
    target = None
    for t in reversed(turns):
        if t.get("question") and not t.get("answer"):
            target = t
            break
    if target is None:
        return {"error": "no pending question", "code": "no_question"}

    max_q = s["meta"].get("num_questions", 5)
    answered_count = sum(1 for t in turns if t.get("answer"))
    # Mark as topic-changed
    target["answer"] = "[topic changed]"
    target["evaluation"] = {"score": 0, "strength": "", "main_issue": "topic_changed",
                            "good": [], "biggest_issue": "Topic changed", "relevance": {"verdict": "skipped", "note": "Switched to different topic"},
                            "dimensions": {}, "vocabulary": "", "fillers": "", "pacing": "", "completeness": ""}
    target["coaching"] = {"appreciation": "", "priority": "", "specific_feedback": "Switched to a different topic.",
                          "improvement": "", "next_step": ""}
    target["model_answer"] = ""
    _persist_turns(inp.session_id, turns)
    new_answered = answered_count + 1
    # Try to find a different topic
    jump = _get_next_different_topic(s["meta"], turns)
    jump_to = jump["jump_to"] if jump else None
    nq = _advance_question(inp.session_id, s["meta"], turns, jump_to=jump_to)
    if nq is None or new_answered >= max_q:
        return {"next_question": None, "bridge": "That's all the questions.",
                "answered": new_answered, "at_limit": True}
    bridge = "Switching to a new topic."
    store.append_turn(inp.session_id, {"question": nq["q"], "answer": None, "bridge": bridge})
    return {"next_question": nq["q"], "bridge": bridge,
            "answered": new_answered, "at_limit": False}


def _persist_turns(session_id: str, turns: list[dict]) -> None:
    from backend.app.session.manager import _load, _save, _decode_session
    raw_id = session_id
    decoded = _decode_session(session_id)
    if decoded:
        raw_id = decoded.get("id", session_id)
    sessions = _load("sessions.json", [])
    for ss in sessions:
        if ss["id"] == raw_id:
            ss["turns"] = turns
            break
    _save("sessions.json", sessions)


@router.post("/finish")
def finish(inp: AnswerIn):
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    done = [t for t in s.get("turns", []) if t.get("answer")]
    # Build per-question details for the report
    question_details = []
    for t in done:
        qd = {
            "question": t.get("question", ""),
            "answer": t.get("answer", ""),
            "evaluation": t.get("evaluation", {}),
            "coaching": t.get("coaching", {}),
            "model_answer": t.get("model_answer", ""),
            "visual_observations": t.get("visual_events", []),
            "visual_coaching": t.get("visual_coaching", ""),
        }
        question_details.append(qd)
    report = eng.final_report(done, s["meta"].get("role", "Candidate"),
                               s["meta"].get("jd", ""), s["meta"].get("type", ""),
                               s["meta"].get("difficulty", "intermediate"))
    # Add per-question breakdown
    report["question_details"] = question_details
    # Add visual communication summary
    all_visual_events = [{"events": t.get("visual_events", [])} for t in done if t.get("visual_events")]
    visual_summary = vis.visual_summary_for_report(all_visual_events, s["meta"].get("difficulty", "intermediate"))
    if visual_summary:
        report["visual_communication"] = visual_summary
    finished = store.finish_session(inp.session_id, report)
    return {"session_id": inp.session_id, "report": report, "turns": len(done)}
