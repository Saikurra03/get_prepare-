"""FastAPI app: API + multi-page frontend. Keys never leave server."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.api import routes_coach, routes_documents, routes_interview, routes_session, routes_stt, routes_tts

app = FastAPI(title="BERREADY — Communication + Interview Coach", version="0.2.0")

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

@app.get("/api/health")
def health():
    from backend.app.ai import service
    from backend.app.ai.key_manager import key_manager, _collect
    from backend.app.config import settings
    st = service.provider_status()
    # Key count diagnostics (never values) — helps debug "offline" on deploy.
    key_counts = {}
    for p in settings.provider_order:
        key_counts[p] = len(_collect(p.upper()))
    return {"ok": True, "ai_ready": st.get("ready", False), "ai_provider": st.get("display"),
            "order": settings.provider_order,
            "key_counts": key_counts,
            "detail": {k: st[k] for k in ("provider", "key_label", "fallback_active", "debug") if k in st}}

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
