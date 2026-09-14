"""FastAPI app: API + multi-page frontend. Keys never leave server."""
from __future__ import annotations
import os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.api import routes_coach, routes_documents, routes_interview, routes_session, routes_stt, routes_tts

app = FastAPI(title="BERREADY — Communication + Interview Coach", version="0.3.0")

# CORS — allow Netlify frontend (or any configured origin) to call the API.
_cors_raw = os.getenv("CORS_ORIGINS", "*")
_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
# Wildcard with credentials is invalid per CORS spec — disable credentials for wildcard.
_has_wildcard = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=not _has_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Activity Tracking (in-memory, resets on deploy) ---
_activity = {
    "total_requests": 0,
    "api_requests": 0,
    "ai_calls": 0,
    "ai_success": 0,
    "ai_failures": 0,
    "last_request_time": None,
    "last_ai_time": None,
    "errors": 0,
}

@app.middleware("http")
async def track_activity(request: Request, call_next):
    _activity["total_requests"] += 1
    _activity["last_request_time"] = time.time()
    if request.url.path.startswith("/api/"):
        _activity["api_requests"] += 1
    response = await call_next(request)
    if response.status_code >= 400:
        _activity["errors"] += 1
    return response

app.include_router(routes_coach.router)
app.include_router(routes_documents.router)
app.include_router(routes_interview.router)
app.include_router(routes_session.router)
app.include_router(routes_stt.router)
app.include_router(routes_tts.router)

# backend/app/main.py -> up 2 = BEREADY_BOY, + frontend
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FRONTEND = os.path.join(ROOT, "frontend")

# IA page table: URL path -> html file. One purpose per page.
PAGES = {
    "": "index.html",               # Home / Command Center
    "practice": "practice.html",     # Practice Hub
    "workspace": "workspace.html",   # Live practice workspace (all practice modes)
    "interview": "interview.html",   # Interview Hub
    "prepare": "prepare.html",       # Interview Preparation + Documents
    "interview-setup": "isetup.html",
    "interview-live": "ilive.html",
    "report": "report.html",         # Interview report
    "progress": "progress.html",     # Progress Overview
    "history": "history.html",       # Session History
    "profile": "profile.html",       # Communication Profile
    "settings": "settings.html",
    "slang": "slang.html",
}


def _probe_providers() -> dict:
    """Check which providers have keys available (no API calls, just env scan)."""
    from backend.app.ai.key_manager import _collect
    from backend.app.config import settings
    result = {}
    for p in settings.provider_order:
        keys = _collect(p.upper())
        if keys:
            result[p] = "available"
        else:
            result[p] = "no_keys"
    return result


@app.get("/api/health")
def health():
    from backend.app.ai import service
    from backend.app.config import settings
    st = service.provider_status()
    providers = _probe_providers()
    configured_count = sum(1 for v in providers.values() if v == "available")
    return {
        "ok": True,
        "ai_ready": st.get("ready", False),
        "ai_provider": st.get("display"),
        "active_provider": st.get("provider"),
        "active_key": st.get("key_label"),
        "fallback_enabled": True,
        "providers": providers,
        "configured_providers": configured_count,
        "order": settings.provider_order,
        "detail": {k: st[k] for k in ("provider", "key_label", "fallback_active", "debug") if k in st},
    }


@app.get("/api/status")
def status():
    """Full backend status: health + providers + activity. Safe — no secrets."""
    from backend.app.ai import service
    from backend.app.config import settings
    st = service.provider_status()
    providers = _probe_providers()
    configured_count = sum(1 for v in providers.values() if v == "available")
    return {
        "backend": "connected",
        "version": "0.3.0",
        "ai_ready": st.get("ready", False),
        "active_provider": st.get("provider"),
        "active_key_label": st.get("key_label"),
        "fallback_enabled": True,
        "fallback_active": st.get("fallback_active", False),
        "providers": providers,
        "configured_count": configured_count,
        "provider_order": settings.provider_order,
        "activity": {
            "total_requests": _activity["total_requests"],
            "api_requests": _activity["api_requests"],
            "ai_calls": _activity["ai_calls"],
            "ai_success": _activity["ai_success"],
            "ai_failures": _activity["ai_failures"],
            "errors": _activity["errors"],
            "last_request": _activity["last_request_time"],
            "last_ai_call": _activity["last_ai_time"],
        },
        "services": {
            "stt": {"configured": bool(settings.stt_provider and settings.stt_model), "provider": settings.stt_provider, "model": settings.stt_model},
            "tts": {"configured": bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id)},
        },
    }


if os.path.isdir(FRONTEND):
    # Serve JS/CSS/images from root AND /static (Netlify uses root paths).
    from starlette.applications import Starlette
    _static_app = Starlette(routes=[
        # Mount static files at both /static and root
    ])
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND, "js")), name="js")
    app.mount("/css", StaticFiles(directory=FRONTEND), name="css")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND, PAGES[""]))

    @app.get("/{page}")
    def page(page: str):
        if page not in PAGES or page == "":
            raise HTTPException(status_code=404)
        return FileResponse(os.path.join(FRONTEND, PAGES[page]))
