"""Session + profile routes."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.session import manager as store
from backend.app.ai import service

router = APIRouter(prefix="/api/session", tags=["session"])

class CreateIn(BaseModel):
    kind: str = "practice"
    scenario: str = "conversation"

class FinishIn(BaseModel):
    session_id: str = ""

@router.post("/create")
def create(inp: CreateIn):
    return store.create_session(inp.kind, {"scenario": inp.scenario})

@router.post("/finish")
def finish(inp: FinishIn):
    s = store.finish_session(inp.session_id)
    if not s:
        return {"error": "session not found", "code": "no_session"}
    return {"id": s["id"], "status": s["status"]}

@router.get("/profile")
def profile():
    p = store.get_profile()
    return {**p, "ai": service.provider_status()}

@router.get("/list")
def list_all():
    return {"sessions": [{k: s[k] for k in ("id", "kind", "status", "meta") if k in s}
                         for s in store.list_sessions()]}

@router.get("/detail")
def detail(sid: str):
    s = store.get_session(sid)
    if not s:
        return {"error": "session not found", "code": "no_session"}
    return s

@router.get("/dashboard")
def dashboard():
    from backend.app.engines import dashboard as dash
    return dash.build_dashboard()

@router.get("/health")
def health():
    st = service.provider_status()
    return {"ok": True, "ai_ready": st.get("ready", False), "ai_provider": st.get("display"),
            "detail": {k: st[k] for k in ("provider", "key_label", "fallback_active", "debug") if k in st}}
