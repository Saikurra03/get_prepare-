"""Self Introduction — separate question/evaluation/feedback system: strict
question rules, six-dimension rubric, server-computed score, honest offline
scoring regression, report shape, and other-type isolation."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from backend.app.engines import interview as eng
from backend.app.engines import selfintro

RUBRIC_DIMS = {"structure", "clarity", "relevance", "technical_accuracy",
               "conciseness", "delivery"}

ANSWER = ("I am a software engineer with five years of experience building payment systems. "
          "At Acme I led the migration of our checkout service to an event-driven architecture, "
          "which cut payment failures by 40 percent. I also mentored two junior engineers. "
          "Now I am looking for a role where I can own reliability end to end.")

STRONG_ANSWER = (
    "Good morning sir, I am Priya Sharma, currently pursuing my B.Tech in Computer "
    "Science at City College, graduating in 2027. My key skills are Python and data "
    "analysis. I built an attendance tracker using Python and SQL that my class now "
    "uses daily, and I received the best student award last year. My career goal is "
    "to become a data analyst where I can turn raw data into decisions."
)


@pytest.fixture
def offline_ai(monkeypatch):
    """Remove all AI keys so engine calls take their offline branches (fast, no network)."""
    from backend.app.ai.key_manager import key_manager
    for k in list(os.environ):
        if re.search(r"(GEMINI|GROQ|OPENROUTER|COHERE).*API_KEY", k, re.I):
            monkeypatch.delenv(k, raising=False)
    key_manager.reload()
    yield
    key_manager.reload()


def _mean(rubric):
    numeric = [v for v in rubric.values() if not isinstance(v, str)]
    assert numeric, "at least one numeric dimension expected"
    return round(sum(numeric) / len(numeric), 1)


def test_selfintro_registered():
    assert "selfintro" in eng.TYPES
    assert eng.BASE_QUESTIONS["selfintro"] == ["Tell me about yourself."]
    assert "selfintro" in eng.TYPE_PLAN_INSTRUCTIONS
    assert "selfintro" in eng.TYPE_EVAL_INSTRUCTIONS
    assert "selfintro" in eng.TYPE_FOLLOWUP_INSTRUCTIONS


def test_build_plan_always_one_valid_question(offline_ai):
    p = eng.build_plan("selfintro", "intermediate", "General candidate", {}, 7)
    assert len(p["questions"]) == 1
    q = p["questions"][0]["q"].strip()
    assert q
    assert selfintro.is_valid_question(q)


def test_question_validation_rules():
    # Allowed: self-introduction openers only.
    assert selfintro.is_valid_question("Tell me about yourself.")
    assert selfintro.is_valid_question("Can you briefly introduce yourself?")
    assert selfintro.is_valid_question("Please give me a brief introduction about yourself.")
    assert selfintro.is_valid_question("Tell me about yourself in a short and concise way.")
    assert selfintro.is_valid_question(
        "Could you introduce yourself and briefly mention your education, key skills, and interests?")
    # STRICTLY FORBIDDEN: resume/behavioral/experience/challenge/follow-up/why/how/hr-style.
    for bad in (
        "Walk me through your resume and your experience.",
        "Tell me about yourself and your past experience.",
        "What was a challenge you faced in your previous role?",
        "Tell me about a project you built.",
        "Why do you want to work here?",
        "How did you handle a conflict with a teammate?",
        "What is your biggest strength?",
        "Follow up: you mentioned your degree — why did you choose it?",
        "Describe a situation where you showed leadership.",
    ):
        assert not selfintro.is_valid_question(bad), bad
    assert not selfintro.is_valid_question("")
    assert not selfintro.is_valid_question("x" * 300)


def test_plan_route_clamps_to_one(offline_ai):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "selfintro",
                                            "difficulty": "beginner",
                                            "num_questions": 7}).json()
    assert p["total_questions"] == 1
    assert p["current_question"].strip()


def test_rubric_generated_and_score_is_mean(offline_ai):
    ev = eng.evaluate_answer("Tell me about yourself.", ANSWER, "selfintro")
    rub = ev["rubric"]
    assert set(rub) == RUBRIC_DIMS
    assert ev["score"] == _mean(rub)


def test_score_is_rubric_mean_never_model_score(offline_ai):
    """The headline score is recomputed server-side from the rubric; a bogus
    model "score" field is ignored; n/a dimensions are excluded from the mean."""
    rub = {"structure": 8, "clarity": 6, "relevance": "n/a",
           "technical_accuracy": "n/a", "conciseness": 7, "delivery": 9}
    out = selfintro._finalize({"score": 2.0, "rubric": rub}, ANSWER,
                              {"word_count": 50}, "groq")
    assert out["score"] == 7.5          # mean(8, 6, 7, 9) — the model's 2.0 discarded
    assert out["provider"] == "groq"


def test_offline_rubric_has_na_technical_accuracy(offline_ai):
    ev = eng.evaluate_answer("Tell me about yourself.", ANSWER, "selfintro")
    assert ev["rubric"]["technical_accuracy"] == "n/a"   # no judgeable evidence offline
    assert ev["provider"] == "offline"


def test_strong_answer_not_capped_at_60_percent(offline_ai):
    """Root-cause regression: the old offline rubric stacked the same
    penalties across dimensions and capped relevance at 7.0, pushing strong
    answers to ~6/10. A complete strong answer must now score 8+."""
    ev = eng.evaluate_answer("Tell me about yourself.", STRONG_ANSWER, "selfintro")
    assert ev["provider"] == "offline"
    assert ev["score"] >= 8.0, ev["score"]
    assert ev["score"] == _mean(ev["rubric"])
    assert all(ev["coverage"].values()), ev["coverage"]
    # Honest spread: an empty answer must stay at the floor, not near 6.
    empty = eng.evaluate_answer("Tell me about yourself.", "", "selfintro")
    assert empty["score"] <= 2.5
    # A messy, off-content answer scores strictly below the strong answer.
    messy = eng.evaluate_answer(
        "Tell me about yourself.",
        "i am so like you know um i worked on java, spring, react, angular, docker, "
        "kubernetes, aws, sql, mongodb, kafka, redis. i am a hard worker and a team player.",
        "selfintro")
    assert messy["score"] < ev["score"]
    assert messy["skip_issues"], "tech dump / generic statements must be flagged"


def test_feedback_shape_offline(offline_ai):
    ev = eng.evaluate_answer("Tell me about yourself.", ANSWER, "selfintro")
    assert 2 <= len(ev["what_worked"]) <= 3
    assert 2 <= len(ev["fix_next"]) <= 3
    assert isinstance(ev["coach_next_step"], str) and ev["coach_next_step"].strip()
    assert isinstance(ev["better_approach"], str) and ev["better_approach"].strip()
    assert ev["focus_skip"]["say"].strip() and ev["focus_skip"]["avoid"].strip()
    asmt = ev["assessment"]
    assert all(str(asmt.get(k, "")).strip() for k in ("worked", "missing", "change_next"))
    # Compat aliases used by older consumers.
    assert ev["strengths"] == ev["what_worked"]
    assert ev["improvements"] == ev["fix_next"]
    assert ev["coaching_tip"] == ev["coach_next_step"]
    # 5-field coaching box derives from the evaluation, no generic HR prompt.
    c = eng.generate_coaching("Tell me about yourself.", ANSWER, ev, "selfintro")
    for k in ("appreciation", "priority", "specific_feedback", "improvement", "next_step"):
        assert str(c.get(k, "")).strip(), k
    assert c["priority"].startswith("Priority:")


def test_final_report_selfintro_shape(offline_ai):
    ev = eng.evaluate_answer("Tell me about yourself.", ANSWER, "selfintro")
    hist = [{"question": "Tell me about yourself.", "answer": ANSWER, "evaluation": ev}]
    r = eng.final_report(hist, "Software Engineer", "", "selfintro")
    assert 2 <= len(r["strengths"]) <= 3
    assert 2 <= len(r["training"]) <= 3
    assert isinstance(r["next_practice"], str) and r["next_practice"].strip()
    assert r["focus_skip"]["say"].strip()
    assert r["better_approach"].strip()
    assert r["summary"].strip()
    assert 0 < r["overall"] <= 10
    assert r["overall"] == ev["score"]


def test_final_report_no_answer_is_honest(offline_ai):
    """A skipped/absent answer never gets a fake score or hallucinated critique."""
    r = eng.final_report([], "Role", "", "selfintro")
    assert r["overall"] is None
    assert "No self-introduction" in r["summary"]
    assert not r["strengths"]
    assert not r["training"]
    assert "record" in r["next_practice"]


def test_model_answer_suppressed_for_selfintro(offline_ai):
    out = eng.generate_model_answer("Tell me about yourself.", ANSWER, "selfintro")
    assert out == {"model_answer": ""}


def test_other_interview_types_unchanged(offline_ai):
    """No rubric/feedback-shape keys leak into other types."""
    ev = eng.evaluate_answer("Tell me about a challenge.", ANSWER, "hr")
    for k in ("rubric", "strengths", "improvements", "coaching_tip",
              "focus_skip", "better_approach", "coverage", "what_worked"):
        assert k not in ev, k
    p = eng.build_plan("hr", "intermediate", "ctx", {}, 5)
    assert len(p["questions"]) >= 1
    hist = [{"question": "Q", "answer": ANSWER, "evaluation": ev}]
    r = eng.final_report(hist, "Engineer", "", "hr")
    for k in ("coaching_tip", "focus_skip", "better_approach"):
        assert k not in r, k


def test_full_flow_selfintro(offline_ai):
    """Hub -> prepare -> 1 question -> answer (with video events) -> result."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "selfintro",
                                            "difficulty": "beginner",
                                            "num_questions": 5}).json()
    sid = p["session_id"]
    assert p["total_questions"] == 1

    events = [{"type": "gaze_away", "duration": 5, "detail": "Looked away"},
              {"type": "slouching", "duration": 8, "detail": "Slouched"}]
    a = c.post("/api/interview/answer",
               json={"session_id": sid, "answer": STRONG_ANSWER,
                     "visual": {"events": events, "summary": {}}}).json()
    assert a.get("at_limit") is True     # single-question session ends after the answer

    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    rep = f["report"]
    assert 2 <= len(rep["strengths"]) <= 3
    assert 2 <= len(rep["training"]) <= 3
    assert rep["next_practice"].strip()
    assert rep["focus_skip"]["say"].strip()
    assert rep["better_approach"].strip()
    assert rep["overall"] is not None and rep["overall"] >= 8.0

    qd = rep["question_details"][0]
    ev = qd["evaluation"]
    assert set(ev["rubric"]) == RUBRIC_DIMS
    # Video events present, yet the score is the pure rubric mean.
    assert ev["score"] == _mean(ev["rubric"])
    assert ev["coverage"] and all(ev["coverage"].values())
    # Visual feedback still shows when valid camera analysis exists.
    assert qd["visual_coaching"]
    assert "visual_communication" in rep
    # Coaching is derived from the evaluation itself.
    assert qd["coaching"]["priority"].startswith("Priority:")
    assert not qd.get("model_answer")
