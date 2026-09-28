"""Interview generation, follow-up, scoring, JD/resume reflection (offline-safe)."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from backend.app.engines import interview as eng
from backend.app.engines import visual_analysis as vis
from backend.app.documents import context_builder


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

def test_answer_flow_and_finish_report(offline_ai):
    """Current clean flow: plan -> answer (no feedback returned) -> skip -> finish report."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "behavioral",
                                            "difficulty": "beginner",
                                            "num_questions": 2}).json()
    sid = p["session_id"]
    assert p["current_question"] and p["total_questions"] >= 1

    # Answer q1: next question comes back, but NO evaluation (feedback only at finish)
    a1 = c.post("/api/interview/answer",
                json={"session_id": sid, "answer": "We had a deploy issue um like stuff."}).json()
    assert "evaluation" not in a1
    assert a1["answered"] == 1
    assert a1.get("next_question") or a1.get("at_limit")

    # Skip q2: counts as answered with score 0, reaches the limit
    sk = c.post("/api/interview/skip", json={"session_id": sid, "answer": ""}).json()
    assert sk["answered"] == 2 and sk["at_limit"] is True

    # Finish: full report with per-question breakdown (evaluation lives here)
    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""}).json()
    rep = f["report"]
    assert rep["answers_evaluated"] == 2
    assert len(rep["question_details"]) == 2
    ev = rep["question_details"][0]["evaluation"]
    assert "score" in ev
    # honesty: audio-only metrics are never invented
    assert ev["articulation"] == "unavailable" and ev["pronunciation"] == "unavailable"
    assert rep["question_details"][1]["evaluation"]["main_issue"] == "skipped"

    # Session is finished and readable from the detail endpoint
    d = c.get(f"/api/session/detail?sid={sid}").json()
    assert d["status"] == "finished"
    answered = [t for t in d["turns"] if t.get("answer")]
    assert len(answered) == 2

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

def test_generate_model_answer_returns_text():
    ma = eng.generate_model_answer("Tell me about yourself.", "I am a developer", "hr")
    assert "model_answer" in ma
    assert len(ma["model_answer"]) > 30

def test_generate_model_answer_offline_fallback():
    """Model answer works even when AI is unavailable."""
    ma = eng.generate_model_answer("Tell me about yourself.", "I am a developer", "hr", "")
    assert ma["model_answer"]
    assert len(ma["model_answer"]) > 30

def test_visual_analysis_empty_events():
    """Visual analysis with no events returns empty results."""
    r = vis.analyze_visuals([], "q", "a", "hr", "beginner")
    assert r["observations"] == []
    assert r["coaching"] == ""
    assert r["score_impact"] == 0.0

def test_visual_analysis_gaze_away():
    """Visual analysis detects gaze-away events."""
    events = [{"type": "gaze_away", "duration": 5, "detail": "Looked away"}]
    r = vis.analyze_visuals(events, "q", "a", "hr", "beginner")
    assert len(r["observations"]) == 1
    assert r["observations"][0]["type"] == "gaze_away"
    assert r["coaching"] != ""

def test_visual_analysis_multiple_event_types():
    """Visual analysis handles multiple event types."""
    events = [
        {"type": "gaze_away", "duration": 3, "detail": "Looked away"},
        {"type": "slouching", "duration": 8, "detail": "Slouched"},
        {"type": "excessive_movement", "duration": 0, "detail": "Moved head"},
        {"type": "hands_hidden", "duration": 0, "detail": "Hands not visible"},
    ]
    r = vis.analyze_visuals(events, "q", "a", "hr", "intermediate")
    assert len(r["observations"]) == 4
    assert r["score_impact"] < 0  # Should have some penalty

def test_visual_summary_for_report():
    """Visual summary aggregates across multiple answers."""
    all_events = [
        {"events": [{"type": "gaze_away", "duration": 3}, {"type": "slouching", "duration": 5}]},
        {"events": [{"type": "gaze_away", "duration": 4}, {"type": "excessive_movement", "duration": 0}]},
    ]
    s = vis.visual_summary_for_report(all_events, "intermediate")
    assert s["camera_attention"]["gaze_away_count"] == 2
    assert s["posture"]["slouch_count"] == 1
    assert s["movement"]["excessive_count"] == 1

def test_visual_summary_empty():
    """Visual summary with no events returns empty dict."""
    s = vis.visual_summary_for_report([], "beginner")
    assert s == {}

def test_visual_analysis_gesture_events():
    """Visual analysis detects and analyzes gesture events."""
    events = [
        {"type": "gesture", "duration": 0, "detail": "Gesture: pointing", "gesture": "pointing", "gesture_confidence": 0.8},
        {"type": "gesture", "duration": 0, "detail": "Gesture: open palm", "gesture": "open_palm", "gesture_confidence": 0.85},
        {"type": "gesture", "duration": 0, "detail": "Gesture: counting", "gesture": "counting", "gesture_confidence": 0.6},
    ]
    r = vis.analyze_visuals(events, "q", "a", "hr", "intermediate")
    assert r["gesture_analysis"]["variety_score"] > 0
    assert r["gesture_analysis"]["total"] == 3
    assert "pointing" in r["gesture_analysis"]["breakdown"]

def test_visual_analysis_content_aware_coaching():
    """Content-aware coaching suggests gestures for answer keywords."""
    answer = "First, I want to say that the example I gave shows my team collaboration skills."
    events = [{"type": "gesture", "duration": 0, "detail": "Gesture: neutral", "gesture": "neutral", "gesture_confidence": 0.5}]
    r = vis.analyze_visuals(events, "q", answer, "hr", "beginner")
    assert r["content_coaching"] != ""  # Should have content-aware suggestion

def test_visual_analysis_torso_lean():
    """Visual analysis detects torso lean events."""
    events = [
        {"type": "torso_lean", "duration": 0, "detail": "Torso leaning left"},
        {"type": "torso_lean", "duration": 0, "detail": "Torso leaning right"},
        {"type": "torso_lean", "duration": 0, "detail": "Torso leaning left"},
    ]
    r = vis.analyze_visuals(events, "q", "a", "hr", "advanced")
    lean_obs = [o for o in r["observations"] if o["type"] == "torso_lean"]
    assert len(lean_obs) == 3
    assert r["score_impact"] < 0

def test_visual_summary_body_alignment():
    """Visual summary includes body alignment data."""
    all_events = [
        {"events": [
            {"type": "torso_lean", "duration": 0},
            {"type": "shoulder_rotation", "duration": 0},
            {"type": "gesture", "duration": 0, "gesture": "pointing"},
        ]},
    ]
    s = vis.visual_summary_for_report(all_events, "intermediate")
    assert "body_alignment" in s
    assert s["body_alignment"]["torso_lean_count"] == 1
    assert s["body_alignment"]["shoulder_rotation_count"] == 1
    assert s["gestures"]["gesture_count"] == 1

def test_visual_analysis_low_gesture_variety():
    """Visual analysis penalizes low gesture variety."""
    events = [
        {"type": "gesture", "duration": 0, "detail": "Gesture: fist", "gesture": "fist", "gesture_confidence": 0.7},
        {"type": "gesture", "duration": 0, "detail": "Gesture: fist", "gesture": "fist", "gesture_confidence": 0.7},
    ]
    r = vis.analyze_visuals(events, "q", "a", "hr", "intermediate")
    assert r["gesture_analysis"]["variety_score"] < 0.5
    assert r["gesture_analysis"]["coaching"] != ""


# ---------------- Phase 2: background evaluation + latency ----------------

def test_answer_is_fast_and_finish_joins_background_jobs(offline_ai):
    """Answer returns immediately with analysis_pending; /finish joins the jobs."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "hr",
                                            "difficulty": "beginner",
                                            "num_questions": 2}).json()
    sid = p["session_id"]

    a = c.post("/api/interview/answer",
               json={"session_id": sid, "answer": "I handled a production incident by rolling back and adding alerts."})
    assert a.status_code == 200
    body = a.json()
    # No evaluation yet — analysis runs in the background
    assert body.get("analysis_pending") is True
    assert "evaluation" not in body
    assert body.get("next_question") or body.get("at_limit")

    # Finish must wait for the job and include the evaluation in the report
    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""})
    assert f.status_code == 200
    rep = f.json()["report"]
    details = rep["question_details"]
    assert len(details) == 1
    assert "score" in details[0]["evaluation"], "background evaluation should be joined by /finish"
    # No turn left stuck pending
    d = c.get(f"/api/session/detail?sid={sid}").json()
    assert all(not t.get("analysis_pending") for t in d["turns"])


def test_skip_without_answer_field_is_accepted():
    """Regression: /skip called with only session_id used to 422 (answer was required)."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "hr",
                                            "difficulty": "beginner",
                                            "num_questions": 3}).json()
    sid = p["session_id"]
    r = c.post("/api/interview/skip", json={"session_id": sid})
    assert r.status_code == 200, r.text
    assert r.json()["answered"] == 1
    # change-topic with the same minimal payload
    r2 = c.post("/api/interview/change-topic", json={"session_id": sid})
    assert r2.status_code == 200, r2.text
    assert r2.json()["answered"] == 2


def test_visual_payload_ingested_into_report(offline_ai):
    """Visual events sent with the answer land in the turn and the final report."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    p = c.post("/api/interview/plan", json={"interview_type": "hr",
                                            "difficulty": "beginner",
                                            "num_questions": 1}).json()
    sid = p["session_id"]
    events = [
        {"type": "gaze_away", "duration": 5, "detail": "Looked away"},
        {"type": "slouching", "duration": 4, "detail": "Slouched"},
    ]
    a = c.post("/api/interview/answer",
               json={"session_id": sid, "answer": "I prioritize tasks by impact and deadlines.",
                     "visual": {"events": events, "summary": {}}})
    assert a.status_code == 200 and a.json().get("analysis_pending") is True

    f = c.post("/api/interview/finish", json={"session_id": sid, "answer": ""})
    rep = f.json()["report"]
    qd = rep["question_details"][0]
    assert len(qd["visual_observations"]) == 2
    assert qd["visual_coaching"] != ""
    assert "visual_communication" in rep


def test_status_reports_latency_fields():
    """/api/status exposes per-route latency + AI timing; API responses carry X-Response-Time."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    c = TestClient(app)
    r = c.get("/api/status")
    assert r.status_code == 200
    st = r.json()
    assert "latency" in st and isinstance(st["latency"], dict)
    assert st["latency"], "the /api/status call itself should be recorded"
    act = st["activity"]
    assert "ai_last_ms" in act and "ai_avg_ms" in act
    assert act["ai_avg_ms"] is None or act["ai_avg_ms"] > 0
    assert "X-Response-Time" in r.headers

    # AI timing populated after an offline generate
    from backend.app.ai import service as ai_service
    ai_service.generate("Say hi.")
    st2 = c.get("/api/status").json()
    assert st2["activity"]["ai_last_ms"] is not None
    assert st2["activity"]["ai_avg_ms"] > 0
    assert "ai:generate" in st2["latency"]
