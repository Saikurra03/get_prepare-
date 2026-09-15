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
    assert ev["score"] >= 3 and ev["score"] <= 10

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

def test_evaluate_extra_dimensions_present():
    ev = eng.evaluate_answer("Explain retries?", "We used retries um like to fix stuff.", "technical")
    for k in ("vocabulary", "fillers", "pacing", "completeness", "technical"):
        assert k in ev, k
    assert ev["articulation"] == "unavailable" and ev["pronunciation"] == "unavailable"

def test_final_report_aggregates():
    hist = [
        {"question": "Q1", "answer": "A1 with um filler words here",
         "evaluation": {"score": 7, "main_issue": "fillers",
                        "relevance": {"verdict": "directly", "note": "x"},
                        "signals": {"filler_total": 2, "long_sentences": 1, "word_count": 40}}},
        {"question": "Q2", "answer": "A2 also um fillers",
         "evaluation": {"score": 5, "main_issue": "fillers",
                        "relevance": {"verdict": "partially", "note": "y"},
                        "signals": {"filler_total": 3, "long_sentences": 0, "word_count": 30}}},
    ]
    r = eng.final_report(hist, "Engineer", "")
    assert r["recurring_problems"] == ["fillers"]
    assert "1/2" in r["relevance_summary"] and "directly" in r["relevance_summary"]
    assert "5 fillers" in r["sentence_patterns"]
    assert "Not enough data" in r["pronunciation_note"]
    for k in ("top_priority", "next_practice"):
        assert k in r, k

def test_dashboard_endpoint_shape():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    d = c.get("/api/session/dashboard").json()
    for k in ("summary_lines", "sections", "strengths", "recurring", "focus", "recent"):
        assert k in d, k
    assert 1 <= len(d["summary_lines"]) <= 5
    assert all(isinstance(l, str) and l for l in d["summary_lines"])

def test_dashboard_no_fake_data_invariants():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    d = c.get("/api/session/dashboard").json()
    # no zero-count sections ever displayed
    assert all(v > 0 for v in (d["sections"] or {}).values())
    # recent charts trace to real finished sessions only
    listed = {s["id"] for s in c.get("/api/session/list").json()["sessions"] if s["status"] == "finished"}
    for rc in d.get("recent_charts", []):
        assert rc["id"] in listed
        assert rc["section"]  # every chart belongs to a real section
    # every metric carries its basis; nothing precanned
    for name, m in (d.get("metrics") or {}).items():
        assert "value" in m and "basis" in m, name
        assert "answer" in m["basis"]
    # trend points link to real sessions
    for p in d.get("trend", []):
        assert p["sid"] in listed and p["overall"] is not None

def test_generate_coaching_returns_5_fields():
    ev = eng.evaluate_answer("Explain a challenge.", "We had a bug and I fixed it.", "behavioral")
    coaching = eng.generate_coaching("Explain a challenge.", "We had a bug and I fixed it.", ev, "behavioral")
    for k in ("appreciation", "priority", "specific_feedback", "improvement", "next_step"):
        assert k in coaching, f"missing coaching field: {k}"
        assert isinstance(coaching[k], str) and len(coaching[k]) > 5, f"coaching.{k} too short"

def test_generate_coaching_offline_fallback():
    """Coaching works even when AI is unavailable."""
    ev = {"score": 6, "main_issue": "fillers", "good": ["good structure"], "better_examples": [],
          "signals": {"filler_total": 3}, "relevance": {"verdict": "partially", "note": ""}, "dimensions": {}}
    coaching = eng.generate_coaching("Tell me about yourself.", "um so I did stuff", ev, "hr")
    assert coaching["appreciation"]
    assert "Priority:" in coaching["priority"]
    assert coaching["improvement"]
    assert coaching["next_step"]
