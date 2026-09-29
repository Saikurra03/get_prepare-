"""Question-list mode (qbank): parsing + plan uses ONLY user questions — no AI."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from backend.app.engines import question_source as qs


# ---------------- parse_questions ----------------

def test_parse_numbered_and_bulleted_lines():
    text = """
1. What is your greatest strength?
2) Describe a conflict you resolved.
- Tell me about a failure.
• How do you prioritize tasks?
Q3: Why this company?
"""
    out = qs.parse_questions(text)
    assert out == [
        "What is your greatest strength?",
        "Describe a conflict you resolved.",
        "Tell me about a failure.",
        "How do you prioritize tasks?",
        "Why this company?",
    ]


def test_parse_json_array_and_objects():
    assert qs.parse_questions('["Question one?", "Question two?"]') == ["Question one?", "Question two?"]
    assert qs.parse_questions('{"questions": [{"q": "From object?"}, {"question": "Second object?"}]}') == \
        ["From object?", "Second object?"]


def test_parse_csv_takes_first_column():
    out = qs.parse_questions("What is Docker?,hint about containers\nHow does DNS work?,hint2",
                             source="questions.csv")
    assert out == ["What is Docker?", "How does DNS work?"]


def test_parse_drops_blanks_duplicates_and_tiny_lines():
    text = "What is your biggest win?\n\n  \nok\nWhat is your biggest win?\nWhat is your biggest win?"
    out = qs.parse_questions(text)
    assert out == ["What is your biggest win?"]


def test_parse_preserves_order_and_count():
    text = "\n".join(f"Question number {i} about something?" for i in range(50))
    out = qs.parse_questions(text)
    assert len(out) == 50
    assert out[0] == "Question number 0 about something?"
    assert out[49] == "Question number 49 about something?"


def test_parse_empty_input():
    assert qs.parse_questions("") == []
    assert qs.parse_questions("   \n  \n") == []


def test_parse_does_not_mangle_prose_prefixes():
    """Numbered prefixes need punctuation; abbreviations like e.g. survive."""
    text = ("Question 3 of 5 in the loop?\n"
            "e.g. Explain your biggest project?\n"
            "Q1 - Why should we hire you?")
    out = qs.parse_questions(text)
    assert out[0] == "Question 3 of 5 in the loop?"
    assert out[1].startswith("e.g.")
    assert out[2] == "Why should we hire you?"


# ---------------- select_questions ----------------

def test_select_sequential_keeps_order_and_count():
    items = [f"Q{i}?" for i in range(10)]
    assert qs.select_questions(items, 4, "sequential") == items[:4]
    assert qs.select_questions(items, 99, "sequential") == items
    assert qs.select_questions(items, 0, "sequential") == items


def test_select_random_is_permutation_not_invention():
    items = [f"Q{i}?" for i in range(10)]
    got = qs.select_questions(items, 10, "random")
    assert sorted(got) == sorted(items)          # same set, nothing new
    got3 = qs.select_questions(items, 3, "random")
    assert len(got3) == 3 and all(q in items for q in got3)


# ---------------- plan endpoint with user questions ----------------

@pytest.fixture
def offline_ai(monkeypatch):
    from backend.app.ai.key_manager import key_manager
    for k in list(os.environ):
        if re.search(r"(GEMINI|GROQ|OPENROUTER|COHERE).*API_KEY", k, re.I):
            monkeypatch.delenv(k, raising=False)
    key_manager.reload()
    yield
    key_manager.reload()


def _client():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


def test_plan_uses_user_questions_verbatim_sequential(offline_ai):
    """No AI: meta.questions is exactly the user's list, in order."""
    c = _client()
    mine = ["What is your greatest strength?",
            "Describe a conflict you resolved.",
            "Tell me about a failure."]
    r = c.post("/api/interview/plan", json={
        "interview_type": "hr", "difficulty": "advanced",
        "num_questions": 3, "questions": mine, "order": "sequential",
    }).json()
    assert r["question_source"] == "user"
    assert r["total_questions"] == 3
    assert r["current_question"] == mine[0]
    d = c.get(f"/api/session/detail?sid={r['session_id']}").json()
    stored = [t["q"] for t in d["meta"]["questions"]]
    assert stored == mine
    assert d["meta"]["question_source"] == "user"


def test_plan_count_limits_and_excess_uses_all(offline_ai):
    c = _client()
    mine = [f"Question {i} of the list?" for i in range(10)]
    r = c.post("/api/interview/plan", json={"num_questions": 4, "questions": mine}).json()
    assert r["total_questions"] == 4
    r2 = c.post("/api/interview/plan", json={"num_questions": 50, "questions": mine}).json()
    assert r2["total_questions"] == 10


def test_plan_random_order_preserves_membership(offline_ai):
    c = _client()
    mine = [f"Unique question {i}?" for i in range(8)]
    r = c.post("/api/interview/plan", json={"num_questions": 8, "questions": mine, "order": "random"}).json()
    d = c.get(f"/api/session/detail?sid={r['session_id']}").json()
    stored = [t["q"] for t in d["meta"]["questions"]]
    assert sorted(stored) == sorted(mine)   # permutation of user's list only


def test_question_list_mode_answers_and_finishes(offline_ai):
    """Full flow works with user questions: answer -> finish report."""
    c = _client()
    mine = ["What is your greatest strength?", "Describe a project you led."]
    r = c.post("/api/interview/plan", json={"num_questions": 2, "questions": mine}).json()
    sid = r["session_id"]
    a = c.post("/api/interview/answer", json={"session_id": sid,
                                              "answer": "I stay calm under pressure and communicate early."})
    assert a.status_code == 200 and a.json().get("analysis_pending") is True
    a2 = c.post("/api/interview/answer", json={"session_id": sid,
                                               "answer": "I led a two-person team to ship a payment retry system."})
    assert a2.json().get("at_limit") is True
    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    assert f["report"]["answers_evaluated"] == 2
    assert f["report"]["question_details"][0]["question"] == mine[0]


def test_parse_questions_endpoint(offline_ai):
    c = _client()
    r = c.post("/api/interview/parse-questions",
               json={"text": "1. First question here?\n2. Second question here?\n\n1. First question here?",
                     "filename": "list.txt"}).json()
    assert r["count"] == 2
    assert r["questions"] == ["First question here?", "Second question here?"]
