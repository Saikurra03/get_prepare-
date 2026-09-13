"""Coach routes: analyze + retry-compare."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.engines import coaching
from backend.app.engines import vision as vision_eng
from backend.app.session import manager as store

router = APIRouter(prefix="/api/coach", tags=["coach"])

class AnalyzeIn(BaseModel):
    transcript: str
    scenario: str = "conversation"
    session_id: str | None = None
    camera_on: bool = True
    mic_on: bool = True
    visual_notes: str = ""

class RetryIn(BaseModel):
    first: str
    second: str

@router.post("/analyze")
def analyze(inp: AnalyzeIn):
    if not inp.transcript or not inp.transcript.strip():
        return {"error": "empty speech — no transcription received. Check microphone.", "code": "empty_speech"}
    visual = vision_eng.analyze_frame(None, inp.camera_on, inp.mic_on)
    if inp.visual_notes:
        visual["notes"] += "; user note: " + inp.visual_notes[:160]
    profile = store.get_profile()
    history = []
    if inp.session_id:
        s = store.get_session(inp.session_id)
        if s:
            history = s.get("turns", [])
    result = coaching.coach(inp.transcript, inp.scenario, visual, profile, history)
    if inp.session_id:
        store.append_turn(inp.session_id, {"transcript": inp.transcript[:2000],
                                           "issue": result["issue"], "feedback": result["feedback"]})
    return result

@router.post("/retry-compare")
def retry_compare(inp: RetryIn):
    if not inp.first.strip() or not inp.second.strip():
        return {"error": "both attempts required for comparison", "code": "missing_attempt"}
    return coaching.compare_retry(inp.first, inp.second)
