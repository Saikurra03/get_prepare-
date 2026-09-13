"""Interview generation, follow-up, scoring, JD/resume reflection (offline-safe)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.engines import interview as eng
from backend.app.documents import context_builder

def test_plan_offline_has_questions():
    p = eng.build_plan("mixed", "intermediate", "Software Engineer with Python")
    assert len(p["questions"]) >= 3

def test_followup_adaptive():
    hist = [{"question": "Explain your project.", "answer": "We built a payment system using retries."}]
    n = eng.next_question(hist, "payments", "project", "intermediate")
    assert len(n["question"]) > 5 and "bridge" in n

def test_evaluate_weak_answer_suggests_retry():
    ev = eng.evaluate_answer("Tell me about a challenge.", "um like stuff happened", "behavioral")
    assert "score" in ev and ev["score"] < 7

def test_evaluate_strong_answer():
    ev = eng.evaluate_answer("Explain project.", "I cut checkout failures 40% by adding idempotent retries in Python.", "technical")
    assert ev["score"] >= 5

def test_final_report_shape():
    hist = [{"question": "Q1", "answer": "A1 blah", "evaluation": {"score": 8, "main_issue": "structure"}},
            {"question": "Q2", "answer": "A2 um stuff", "evaluation": {"score": 5, "main_issue": "fillers"}}]
    r = eng.final_report(hist, "Engineer", "Python retries")
    for k in ("overall", "summary", "strengths", "biggest_weakness", "communication", "technical", "role_alignment", "training"):
        assert k in r, k
    assert r["overall"] == 6.5

def test_jd_resume_signals():
    sig = context_builder.extract_signals("Python FastAPI retries", "Python project with retries")
    assert sig["overlap"], "JD+resume overlap should be detected"

def test_context_caps_huge_docs():
    ctx = context_builder.build_context([{"kind": "jd", "filename": "jd.pdf", "text": "x" * 20000}], max_chars=6000)
    assert len(ctx) <= 6000

def test_evaluate_rich_live_report_shape():
    ev = eng.evaluate_answer("Tell me about a challenge?", "We had a bug and I fixed it with retries.", "behavioral")
    for k in ("score", "strength", "main_issue", "retry_suggested", "retry_instruction",
              "good", "biggest_issue", "relevance", "sentences", "better_examples",
              "interviewer_want", "dimensions"):
        assert k in ev, k
    # honesty: audio-only metrics never invented
    assert ev["articulation"] == "unavailable" and ev["pronunciation"] == "unavailable"
    assert ev["relevance"]["verdict"] in ("directly", "partially", "missed")

def test_custom_type_supported():
    p = eng.build_plan("custom", "beginner", "Custom focus: system design.")
    assert len(p["questions"]) >= 1

def test_next_question_accepts_profile_note():
    hist = [{"question": "Q?", "answer": "A."}]
    n = eng.next_question(hist, "ctx", "hr", "beginner", "focus: confidence")
    assert n["question"]

def test_answer_retry_loop():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "behavioral", "difficulty": "beginner"}).json()
    sid = p["session_id"]
    a1 = c.post("/api/interview/answer", json={"session_id": sid, "answer": "We had a deploy issue um like stuff."}).json()
    assert "evaluation" in a1 and a1["evaluation"]["articulation"] == "unavailable"
    r = c.post("/api/interview/retry", json={"session_id": sid, "answer": "We had a deploy outage. I rolled back in 10 minutes."}).json()
    assert r["old"]["answer"].startswith("We had a deploy issue") and "evaluation" in r
    d = c.get(f"/api/session/detail?sid={sid}").json()
    answered = [t for t in d["turns"] if t.get("answer")]
    assert len(answered) == 1 and answered[0]["answer"].startswith("We had a deploy outage")
    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    assert f["report"]["answers_evaluated"] == 1
