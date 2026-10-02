"""Interview routes: plan -> answer/skip/change-topic -> finish (report).
Questions come from a pre-generated list. No instant feedback during the interview.
Heavy analysis (evaluation/coaching/model answer) runs in background AFTER the
response is sent — the next question appears instantly; /finish joins the jobs."""
from __future__ import annotations
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.engines import interview as eng
from backend.app.engines import question_source
from backend.app.engines import speech_analysis as sa
from backend.app.engines import visual_analysis as vis
from backend.app.documents import context_builder
from backend.app.session import manager as store

log = logging.getLogger("beready.interview")

router = APIRouter(prefix="/api/interview", tags=["interview"])

_executor = ThreadPoolExecutor(max_workers=4)
_in_flight: dict[str, bool] = {}
_pending: dict[str, list] = {}   # session_id -> background analysis futures
_JOIN_TIMEOUT = 180.0            # seconds to wait for background analysis at /finish


class PlanIn(BaseModel):
    doc_ids: list[str] = []
    interview_type: str = "mixed"
    difficulty: str = "intermediate"
    role: str = ""
    num_questions: int = 5
    questions: list[str] = []   # user-supplied question list (qbank mode) — AI never invents
    order: str = "sequential"   # sequential | random


class ParseIn(BaseModel):
    text: str = ""
    filename: str = ""


class AnswerIn(BaseModel):
    session_id: str
    answer: str = ""          # optional: /skip and /change-topic don't send one
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
    with store.lock():
        raw_id = session_id
        decoded = _decode_session(session_id)
        if decoded:
            raw_id = decoded.get("id", session_id)
        sessions = _load("sessions.json", [])
        for ss in sessions:
            if ss["id"] == raw_id:
                ss["meta"] = meta
                break
        else:
            log.warning("persist_meta: session %s not found in storage", raw_id)
        _save("sessions.json", sessions)


def _analyze_turn_job(session_id: str, tid: str, question: str, answer: str,
                      itype: str, diff: str, ctx: str, visual_events: list) -> None:
    """Background analysis for one answer: evaluation + visual + coaching + model answer.
    Runs after the /answer response is sent — never blocks the interview flow.

    Each stage is guarded separately: a failure in coaching/model/visual can never
    throw away an evaluation that was already computed successfully."""
    t0 = time.perf_counter()
    try:
        # 1) Evaluation — the one thing the report cannot work without.
        try:
            ev = eng.evaluate_answer(question, answer, itype, diff, context=ctx)
        except Exception:
            log.exception("evaluate_answer failed for turn %s — scoring from transcript signals", tid)
            sig = sa.analyze(answer)
            score = max(3.0, min(8.5, 7.0 - 0.4 * sig.get("filler_total", 0)))
            ev = {"score": round(score, 1), "strength": "answered the question",
                  "main_issue": sa.top_issue(sig), "retry_suggested": score < 6.5,
                  "retry_instruction": "Retry leading with your main point in 10 seconds.",
                  "good": ["answered the question"], "biggest_issue": sa.top_issue(sig),
                  "relevance": {"verdict": "partially", "note": "Scored from transcript signals."},
                  "sentences": [], "better_examples": [], "dimensions": {},
                  "vocabulary": "", "fillers": "", "pacing": "", "completeness": "",
                  "technical": "n/a", "articulation": "unavailable", "pronunciation": "unavailable",
                  "signals": sig, "provider": "offline"}

        # 2) Visual analysis (optional enrichment — score impact only).
        visual_result: dict = {}
        try:
            visual_result = vis.analyze_visuals(visual_events, question, answer, itype, diff)
            # Self Introduction scores are transcript-based only (items 27/29) —
            # video never changes the score. Visual coaching text still shows
            # when valid camera data exists (item 28).
            if itype != "selfintro" and visual_result.get("score_impact", 0):
                ev["score"] = max(1.0, min(10.0, ev.get("score", 5) + visual_result["score_impact"]))
        except Exception:
            log.exception("visual analysis failed for turn %s (evaluation kept)", tid)

        # 3) Coaching + model answer (optional enrichment).
        coaching = None
        try:
            coaching = eng.generate_coaching(question, answer, ev, itype, diff)
        except Exception:
            log.exception("coaching generation failed for turn %s (evaluation kept)", tid)
        model = ""
        try:
            model = eng.generate_model_answer(question, answer, itype, ctx, diff).get("model_answer", "")
        except Exception:
            log.exception("model answer generation failed for turn %s (evaluation kept)", tid)

        payload = {"evaluation": ev, "analysis_pending": False}
        if coaching is not None:
            payload["coaching"] = coaching
        if model:
            payload["model_answer"] = model
        if visual_result:
            payload["visual_coaching"] = visual_result.get("coaching", "")
        store.update_turn(session_id, tid, payload)
    except Exception:
        # Absolute last resort — never leave a turn stuck pending.
        log.exception("background analysis failed for turn %s", tid)
        try:
            sig = sa.analyze(answer)
            store.update_turn(session_id, tid, {
                "evaluation": {"score": max(1.0, min(8.5, 7.0 - 0.4 * sig.get("filler_total", 0))),
                               "strength": "", "main_issue": "analysis unavailable",
                               "good": [], "biggest_issue": "analysis unavailable",
                               "relevance": {"verdict": "partially", "note": ""},
                               "dimensions": {}, "vocabulary": "", "fillers": "",
                               "pacing": "", "completeness": "", "technical": "n/a",
                               "articulation": "unavailable", "pronunciation": "unavailable",
                               "signals": sig},
                "coaching": {"appreciation": "", "priority": "", "specific_feedback": "",
                             "improvement": "", "next_step": ""},
                "model_answer": "",
                "analysis_pending": False,
            })
        except Exception:
            log.exception("failed to clear pending analysis for turn %s", tid)
    finally:
        try:
            from backend.app.main import _record_latency
            _record_latency("background:analysis", (time.perf_counter() - t0) * 1000)
        except Exception:
            pass


def _join_pending(session_id: str, timeout: float = _JOIN_TIMEOUT) -> None:
    """Wait for this session's background analysis jobs to finish. Never raises."""
    for f in _pending.pop(session_id, []):
        try:
            f.result(timeout=timeout)
        except Exception:
            log.warning("background analysis job failed for session %s", session_id)


@router.post("/parse-questions")
def parse_questions(inp: ParseIn):
    """Preview-parse an uploaded/pasted question list (qbank live preview)."""
    qs = question_source.parse_questions(inp.text, inp.filename)
    return {"questions": qs, "count": len(qs)}


@router.post("/plan")
def plan(inp: PlanIn):
    # Self Introduction is a fixed single-question session (item 5).
    if inp.interview_type == "selfintro":
        inp.num_questions = 1
    docs = store.get_documents(inp.doc_ids) if inp.doc_ids else store.list_documents(section="interview")
    ctx = context_builder.build_context(docs)
    jd_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "jd")
    resume_text = " ".join(d.get("text", "") for d in docs if d.get("kind") == "resume")
    signals = context_builder.extract_signals(jd_text, resume_text)
    if inp.role:
        ctx = f"Target role: {inp.role}\n" + ctx

    if inp.questions:
        # Question-list mode: the user's questions verbatim (normalized list
        # format only). build_plan is NEVER called — no AI invents questions.
        cleaned = question_source.parse_questions("\n".join(str(q) for q in inp.questions))
        chosen = question_source.select_questions(cleaned, inp.num_questions, inp.order)
        questions = [{"q": q, "topic": "question-list"} for q in chosen]
        p = {"role": inp.role or "Candidate", "focus": [], "provider": "user", "fallback_active": False}
        n_q = len(questions)
        source = "user"
    else:
        p = eng.build_plan(inp.interview_type, inp.difficulty, ctx or "General candidate.", signals, inp.num_questions)
        questions = p.get("questions", [])
        n_q = inp.num_questions
        source = "ai"

    session = store.create_session("interview", {
        "type": inp.interview_type,
        "difficulty": inp.difficulty,
        "role": p.get("role", inp.role),
        "context": ctx[:8000],
        "jd": jd_text[:6000],
        "num_questions": n_q,
        "questions": questions,
        "question_index": 0,
        "question_source": source,
    })
    first_q = questions[0]["q"] if questions and isinstance(questions[0], dict) else (questions[0] if questions else "Tell me about yourself.")
    store.append_turn(session["id"], {"question": first_q, "answer": None})
    return {"session_id": session["id"], "role": p.get("role"),
            "current_question": first_q, "total_questions": len(questions),
            "question_source": source}


@router.post("/answer")
def answer(inp: AnswerIn):
    if not store.get_session(inp.session_id):
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "answer already being processed", "code": "in_flight"}
    _in_flight[inp.session_id] = True
    try:
        # Read-modify-write holds the session lock so a background analysis job
        # finishing mid-request cannot be clobbered by a stale turns write.
        with store.lock():
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

            max_q = s["meta"].get("num_questions", 5)
            answered_count = sum(1 for t in turns if t.get("answer"))

            itype = s["meta"].get("type", "mixed")
            diff = s["meta"].get("difficulty", "intermediate")
            ctx = s["meta"].get("context", "")
            visual_events = (inp.visual or {}).get("events", [])
            # Fast path: persist the answer NOW, hand analysis to a background job.
            # The response returns immediately — evaluation/coaching/model answer
            # are stored on the turn when the job completes (shown only at /finish).
            tid = uuid.uuid4().hex[:10]
            target["answer"] = inp.answer[:3000]
            target["tid"] = tid
            target["visual_events"] = visual_events
            target["analysis_pending"] = True
            _persist_turns(inp.session_id, turns)
            job = _executor.submit(_analyze_turn_job, inp.session_id, tid,
                                   target["question"], inp.answer[:3000],
                                   itype, diff, ctx, visual_events)
            _pending.setdefault(inp.session_id, []).append(job)
            # Advance to next question from the pre-generated list
            new_answered = answered_count + 1
            nq = _advance_question(inp.session_id, s["meta"], turns)
            if nq is None or new_answered >= max_q:
                return {"next_question": None, "bridge": "That's all the questions. Let me prepare your report.",
                        "answered": new_answered, "at_limit": True, "analysis_pending": True}
            # Append the next question turn
            bridge = f"Good. Let's move on."
            store.append_turn(inp.session_id, {"question": nq["q"], "answer": None, "bridge": bridge})
            return {"next_question": nq["q"], "bridge": bridge,
                    "answered": new_answered, "at_limit": False, "analysis_pending": True}
    finally:
        _in_flight.pop(inp.session_id, None)


@router.post("/skip")
def skip(inp: AnswerIn):
    """Skip the current question — counts as answered with score 0."""
    if not store.get_session(inp.session_id):
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "request already being processed", "code": "in_flight"}
    _in_flight[inp.session_id] = True
    try:
        with store.lock():
            s = store.get_session(inp.session_id)
            if not s:
                return {"error": "interview session not found", "code": "no_session"}
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
    finally:
        _in_flight.pop(inp.session_id, None)


@router.post("/change-topic")
def change_topic(inp: AnswerIn):
    """Skip current question and jump to a question with a different topic."""
    if not store.get_session(inp.session_id):
        return {"error": "interview session not found", "code": "no_session"}
    if _in_flight.get(inp.session_id):
        return {"error": "request already being processed", "code": "in_flight"}
    _in_flight[inp.session_id] = True
    try:
        with store.lock():
            s = store.get_session(inp.session_id)
            if not s:
                return {"error": "interview session not found", "code": "no_session"}
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
    finally:
        _in_flight.pop(inp.session_id, None)


def _persist_turns(session_id: str, turns: list[dict]) -> None:
    from backend.app.session.manager import _load, _save, _decode_session
    with store.lock():
        raw_id = session_id
        decoded = _decode_session(session_id)
        if decoded:
            raw_id = decoded.get("id", session_id)
        sessions = _load("sessions.json", [])
        for ss in sessions:
            if ss["id"] == raw_id:
                ss["turns"] = turns
                break
        else:
            log.warning("persist_turns: session %s not found in storage — write skipped", raw_id)
        _save("sessions.json", sessions)


@router.post("/finish")
def finish(inp: AnswerIn):
    if not store.get_session(inp.session_id):
        return {"error": "interview session not found", "code": "no_session"}
    # Never race an in-flight /answer — wait for it so no answer is left out.
    deadline = time.time() + 10.0
    while _in_flight.get(inp.session_id) and time.time() < deadline:
        time.sleep(0.1)
    # Wait for background analysis of every answered turn (evaluation, coaching,
    # model answer, visual analysis) before building the report.
    _join_pending(inp.session_id)
    s = store.get_session(inp.session_id)
    if not s:
        return {"error": "interview session not found", "code": "no_session"}
    # Idempotent: a finished session with a report is returned as-is
    # (re-running would double-count the profile).
    if s.get("status") == "finished" and s.get("report"):
        done_n = sum(1 for t in s.get("turns", []) if t.get("answer"))
        return {"session_id": inp.session_id, "report": s["report"],
                "turns": done_n, "already_finished": True}
    # Fallback: jobs lost (e.g. server restart) — run remaining analysis synchronously.
    for t in s.get("turns", []):
        if t.get("analysis_pending") and t.get("tid"):
            _analyze_turn_job(inp.session_id, t["tid"], t.get("question", ""),
                              t.get("answer", ""), s["meta"].get("type", "mixed"),
                              s["meta"].get("difficulty", "intermediate"),
                              s["meta"].get("context", ""), t.get("visual_events", []))
    # Reload so turns written by those jobs are visible, then guarantee coverage:
    # every answered (non-skipped) question must carry an evaluation.
    s = store.get_session(inp.session_id) or s
    needs = [t for t in s.get("turns", [])
             if t.get("answer") and t.get("answer") not in ("[skipped]", "[topic changed]")
             and not t.get("evaluation")]
    if any(not t.get("tid") for t in needs):
        for t in needs:
            if not t.get("tid"):
                t["tid"] = uuid.uuid4().hex[:10]
        _persist_turns(inp.session_id, s.get("turns", []))
    for t in needs:
        _analyze_turn_job(inp.session_id, t["tid"], t.get("question", ""), t.get("answer", ""),
                          s["meta"].get("type", "mixed"),
                          s["meta"].get("difficulty", "intermediate"),
                          s["meta"].get("context", ""), t.get("visual_events", []))
    s = store.get_session(inp.session_id) or s
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
