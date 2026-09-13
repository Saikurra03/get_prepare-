"""Session + profile persistence (JSON files). Derived coaching data only — no raw A/V."""
from __future__ import annotations
import json
import os
import time
import uuid
from backend.app.config import settings

def _dir() -> str:
    d = settings.data_dir
    os.makedirs(d, exist_ok=True)
    return d

def _path(name: str) -> str:
    return os.path.join(_dir(), name)

def _load(name: str, default):
    p = _path(name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save(name: str, obj) -> None:
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

# ---- sessions ----
def create_session(kind: str, meta: dict | None = None) -> dict:
    sessions = _load("sessions.json", [])
    s = {"id": uuid.uuid4().hex[:10], "kind": kind, "created": time.time(),
         "meta": meta or {}, "turns": [], "status": "active"}
    sessions.append(s)
    _save("sessions.json", sessions)
    return s

def get_session(sid: str) -> dict | None:
    for s in _load("sessions.json", []):
        if s["id"] == sid:
            return s
    return None

def append_turn(sid: str, turn: dict) -> dict | None:
    sessions = _load("sessions.json", [])
    for s in sessions:
        if s["id"] == sid:
            s["turns"].append(turn)
            _save("sessions.json", sessions)
            return s
    return None

def finish_session(sid: str, report: dict | None = None) -> dict | None:
    sessions = _load("sessions.json", [])
    for s in sessions:
        if s["id"] == sid:
            s["status"] = "finished"
            if report is not None:
                s["report"] = report
            _save("sessions.json", sessions)
            if report or s.get("turns"):
                update_profile_from_session(s)
            return s
    return None

def list_sessions() -> list[dict]:
    return _load("sessions.json", [])

# ---- documents ----
def save_document(doc: dict) -> list[dict]:
    docs = _load("documents.json", [])
    docs.append(doc)
    _save("documents.json", docs)
    return docs

def list_documents() -> list[dict]:
    return _load("documents.json", [])

def get_documents(ids: list[str]) -> list[dict]:
    docs = _load("documents.json", [])
    return [d for d in docs if d["id"] in ids]

def clear_documents() -> None:
    _save("documents.json", [])

# ---- profile ----
DEFAULT_PROFILE = {
    "strengths": [], "weaknesses": [], "recurring_patterns": {},
    "sessions_completed": 0, "training_focus": "stronger interview answers",
    "avg_score": 0.0,
}

def get_profile() -> dict:
    return _load("profile.json", dict(DEFAULT_PROFILE))

def update_profile_from_session(session: dict) -> dict:
    profile = get_profile()
    profile["sessions_completed"] = profile.get("sessions_completed", 0) + 1
    issues: dict[str, int] = profile.get("recurring_patterns", {})
    for t in session.get("turns", []):
        iss = t.get("issue") or (t.get("evaluation") or {}).get("main_issue")
        if iss:
            issues[iss] = issues.get(iss, 0) + 1
    profile["recurring_patterns"] = issues
    if issues:
        top = max(issues, key=issues.get)
        # progress: stop repeating same basic advice once count is high -> move focus
        profile["training_focus"] = {
            "fillers": "eliminate fillers; practice 20-second answers",
            "weak_opening": "stronger openings: main point in first 10 seconds",
            "long_sentences": "conciseness: max 2 short sentences per point",
            "vague_language": "specificity: one concrete example per answer",
            "structure": "STAR structure for interview answers",
        }.get(top, f"improve {top}")
        profile["weaknesses"] = sorted(issues, key=issues.get, reverse=True)[:3]
    rep = session.get("report") or {}
    if rep.get("overall"):
        prev = profile.get("avg_score", 0.0)
        n = profile["sessions_completed"]
        profile["avg_score"] = round((prev * (n - 1) + float(rep["overall"])) / n, 2)
    _save("profile.json", profile)
    return profile
