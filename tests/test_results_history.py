"""Result & history correctness:
- /finish processes EVERY answered question (no drops, no single-question results)
- overall = measured mean of real answers (skips never inject fake 0s)
- report narrative is derived from the actual answers (no canned text)
- finished sessions are idempotent (profile never double-counted)
- /api/session/list exposes date/type/questions/score/report for the history page
- tests run against an isolated DATA_DIR (see conftest.py) — real history stays clean
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from backend.app.engines import interview as eng
from backend.app.session import manager as store


@pytest.fixture
def offline_ai(monkeypatch):
    # Import config FIRST: it runs load_dotenv() and may add keys to the env.
    import backend.app.config  # noqa: F401
    from backend.app.ai.key_manager import key_manager
    import re
    for k in list(os.environ):
        if re.search(r"(GEMINI|GROQ|OPENROUTER|COHERE).*API_KEY", k, re.I):
            monkeypatch.delenv(k, raising=False)
    key_manager.reload()
    yield
    key_manager.reload()


@pytest.fixture
def client(offline_ai):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


def _plan(client, n=3, itype="behavioral"):
    # Explicit user question list → deterministic count, plan never calls the AI.
    p = client.post("/api/interview/plan", json={
        "interview_type": itype, "difficulty": "beginner", "num_questions": n,
        "questions": [f"Question number {i}: describe your approach." for i in range(1, n + 1)],
    }).json()
    assert "session_id" in p, p
    assert p["total_questions"] == n, p
    return p["session_id"]


ANSWERS = [
    "I led a migration of our billing service to Postgres and cut failed deploys by 40 percent using automated rollback checks.",
    "When our API slowed down I profiled the endpoints, found N plus one queries, added indexes and reduced latency from 800 to 120 milliseconds.",
    "I learned Terraform in one week by building our staging environment from scratch, then documented the pipeline for the whole team.",
]


def test_finish_processes_all_answers(client):
    sid = _plan(client, n=3)
    for a in ANSWERS:
        r = client.post("/api/interview/answer", json={"session_id": sid, "answer": a}).json()
        assert not r.get("error"), r
    f = client.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    rep = f["report"]
    details = rep["question_details"]
    # every answered question is present and scored
    assert len(details) == 3
    assert rep["answers_evaluated"] == 3
    for qd in details:
        assert qd["evaluation"].get("score") is not None, qd["question"]
    # overall is the measured mean of ALL per-question scores — not one answer
    scores = [float(qd["evaluation"]["score"]) for qd in details]
    assert rep["overall"] == round(sum(scores) / len(scores), 1)
    assert rep.get("coverage") and "3" in rep["coverage"]


def test_finish_excludes_skips_from_overall(client):
    sid = _plan(client, n=2)
    r = client.post("/api/interview/answer", json={"session_id": sid, "answer": ANSWERS[0]}).json()
    assert r.get("next_question") or r.get("at_limit")
    client.post("/api/interview/skip", json={"session_id": sid, "answer": ""})
    f = client.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    rep = f["report"]
    assert len(rep["question_details"]) == 2          # breakdown shows everything
    assert rep["answers_evaluated"] == 2
    assert rep["questions_skipped"] == 1
    assert rep["questions_answered"] == 1
    # the skipped question must NOT drag the score with a fake 0
    real_score = float(rep["question_details"][0]["evaluation"]["score"])
    assert rep["overall"] == real_score


def test_finish_recovers_answers_without_evaluation(client):
    """Turns that lost their analysis (restart / crash) are scored at /finish."""
    s = store.create_session("interview", {"type": "behavioral", "difficulty": "beginner",
                                           "num_questions": 2, "question_index": 2})
    store.append_turn(s["id"], {"question": "Q1?", "answer": ANSWERS[0]})
    store.append_turn(s["id"], {"question": "Q2?", "answer": ANSWERS[1]})
    f = client.post("/api/interview/finish", json={"session_id": s["id"], "answer": ""}).json()
    assert not f.get("error"), f
    rep = f["report"]
    assert len(rep["question_details"]) == 2
    for qd in rep["question_details"]:
        assert qd["evaluation"].get("score") is not None, qd["question"]
    assert rep["overall"] > 0


def test_finish_is_idempotent_for_profile(client):
    sid = _plan(client, n=2)
    for a in ANSWERS[:2]:
        client.post("/api/interview/answer", json={"session_id": sid, "answer": a})
    f1 = client.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    n1 = store.get_profile()["sessions_completed"]
    f2 = client.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    n2 = store.get_profile()["sessions_completed"]
    assert n2 == n1, "double finish must not double-count the profile"
    assert f2.get("already_finished") is True
    assert f2["report"]["overall"] == f1["report"]["overall"]


def test_list_exposes_history_fields(client):
    sid = _plan(client, n=2)
    client.post("/api/interview/answer", json={"session_id": sid, "answer": ANSWERS[0]})
    client.post("/api/interview/finish", json={"session_id": sid, "answer": ""})
    sessions = client.get("/api/session/list").json()["sessions"]
    raw = store._decode_session(sid)["id"]
    row = next(x for x in sessions if x["id"] == raw)
    assert row["created"], "date must be present"
    assert row["kind"] == "interview" and row["status"] == "finished"
    assert row["num_questions"] == 2
    assert row["answered"] >= 1
    assert row["has_report"] is True and row["score"] is not None
    # payload is slim — no giant question lists / resume context in the list
    assert "questions" not in row["meta"] and "context" not in row["meta"]


def test_offline_report_derived_from_real_answers(monkeypatch):
    """No canned strengths — the offline narrative is built from the answers."""
    def boom(*a, **k):
        raise RuntimeError("ai down")
    monkeypatch.setattr("backend.app.engines.interview.service.generate_json", boom)
    hist = [
        {"question": "Q1", "answer": "A1 um like you know",
         "evaluation": {"score": 5, "main_issue": "fillers",
                        "relevance": {"verdict": "partially", "note": ""},
                        "good": [], "strength": "addressed the question",
                        "signals": {"filler_total": 6, "long_sentences": 2,
                                    "word_count": 40, "qualifier_total": 5}}},
        {"question": "Q2", "answer": "A2",
         "evaluation": {"score": 7, "main_issue": "structure",
                        "relevance": {"verdict": "directly", "note": ""},
                        "good": ["clear example"], "strength": "clear example",
                        "signals": {"filler_total": 0, "long_sentences": 0,
                                    "word_count": 60, "qualifier_total": 1}}},
    ]
    r = eng.final_report(hist, "Engineer", "")
    canned = "showed up and communicated"
    assert canned not in " ".join(r["strengths"])
    assert "clear example" in " ".join(r["strengths"]), r["strengths"]
    assert "fillers" in r["biggest_weakness"].lower() or "fillers" in r["recurring_problems"]
    # communication numbers come from the actual signals
    assert "6 fillers" in r["communication"], r["communication"]
    assert r["overall"] == 6.0
    assert "1/2" in r["relevance_summary"]
    assert r["provider"] == "offline"
    assert r["top_priority"] and r["next_practice"] and r["training"]


def _turn(q, score, issue="structure"):
    return {"question": q, "answer": "A clear answer with a concrete result of 40 percent.",
            "evaluation": {"score": score, "main_issue": issue,
                           "relevance": {"verdict": "directly", "note": ""},
                           "good": [], "strength": "",
                           "signals": {"filler_total": 0, "long_sentences": 0,
                                       "word_count": 60, "qualifier_total": 0}}}


def test_best_and_weakest_never_show_the_same_question(monkeypatch):
    """A full score tie must not label one question both best and weakest."""
    def boom(*a, **k):
        raise RuntimeError("ai down")
    monkeypatch.setattr("backend.app.engines.interview.service.generate_json", boom)

    # all equal → no honest "weakest"
    r = eng.final_report([_turn("Q1", 7), _turn("Q2", 7), _turn("Q3", 7)], "Engineer", "")
    assert r["overall"] == 7.0
    assert r["best_answer"]["question"] == "Q1" and r["best_answer"]["score"] == 7
    assert r["weakest_answer"].get("tied") is True
    assert "question" not in r["weakest_answer"]

    # scores differ → weakest is the genuinely lowest one
    r2 = eng.final_report([_turn("Q1", 9), _turn("Q2", 4, "fillers"),
                           _turn("Q3", 7)], "Engineer", "")
    assert not r2["weakest_answer"].get("tied")
    assert r2["weakest_answer"]["question"] == "Q2"
    assert r2["weakest_answer"]["issue"] == "fillers"
    assert r2["best_answer"]["question"] == "Q1"
