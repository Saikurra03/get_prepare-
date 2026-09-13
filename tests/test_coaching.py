"""Coaching priority, interruption, retry, scoring, vision wording."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.engines import speech_analysis as sa, interruption as intr, coaching
from backend.app.engines import vision as vis

def test_minor_grammar_not_interrupted():
    s = sa.analyze("Yesterday I go to store and buyed some stuff.")
    d = intr.should_interrupt(s, "conversation")
    assert d["interrupt"] is False  # scenario 3

def test_boring_story_hook():
    s = sa.analyze("So basically um like my story is about stuff and things and whatever happened.")
    assert sa.top_issue(s) in ("fillers", "vague_language", "weak_opening")

def test_rambling_detected():
    s = sa.analyze(" ".join(["and then we had many problems with the system"] * 40) + " um uh like basically actually")
    d = intr.should_interrupt(s, "practice")
    assert d["score"] >= 3

def test_strong_story_no_fake_criticism():
    r = coaching.compare_retry("We had 48 hours before launch and payments were failing. I added idempotent retries and cut failures 40%.",
                               "We had 48 hours before launch and payments were failing. I added idempotent retries and cut failures 40%.")
    assert r["verdict"] == "same"  # must not invent improvement

def test_retry_improvement():
    r = coaching.compare_retry("um so basically like you know the project was difficult because we had many problems and stuff",
                               "We cut checkout failures 40% by adding idempotent retries.")
    assert r["verdict"] == "improved" and r["clarity_after"] > r["clarity_before"]

def test_vision_no_psych_claims():
    v = vis.analyze_frame(b"12345678901234567890", True, True)
    assert "emotionally" not in v["notes"].lower() and "disconnected" not in v["notes"].lower()

def test_camera_off_path():
    v = vis.analyze_frame(None, False, False)
    assert "off" in v["notes"].lower()

def test_empty_speech():
    s = sa.analyze("  ")
    assert s["empty"] and sa.top_issue(s) == "empty_speech"
