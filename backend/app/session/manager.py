"""Session + profile persistence (JSON files). Derived coaching data only — no raw A/V.
Session data is also encoded in the session ID for resilience against ephemeral disk."""
from __future__ import annotations
import json
import os
import time
import uuid
import base64
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

# ---- session ID encoding (resilience for ephemeral disk) ----
_SESSION_PREFIX = "s_"

def _encode_session(session: dict) -> str:
    """Encode minimal session identity into the session ID for disk-independent recovery.
    Only stores id + kind + created — NOT turns, meta, or report (too large for URLs)."""
    compact = {
        "id": session["id"],
        "kind": session.get("kind", "interview"),
        "created": session.get("created", 0),
    }
    raw = json.dumps(compact, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return _SESSION_PREFIX + encoded

def _decode_session(sid: str) -> dict | None:
    """Decode session data from the session ID. Returns None if invalid."""
    if not sid.startswith(_SESSION_PREFIX):
        return None
    try:
        encoded = sid[len(_SESSION_PREFIX):]
        # Re-add padding
        padded = encoded + "=" * (4 - len(encoded) % 4)
        raw = base64.urlsafe_b64decode(padded)
        return json.loads(raw)
    except Exception:
        return None

# ---- sessions ----
def create_session(kind: str, meta: dict | None = None) -> dict:
    sessions = _load("sessions.json", [])
    s = {"id": uuid.uuid4().hex[:10], "kind": kind, "created": time.time(),
         "meta": meta or {}, "turns": [], "status": "active"}
    sessions.append(s)
    _save("sessions.json", sessions)
    # Return with encoded ID for resilience
    return {**s, "id": _encode_session(s)}

def get_session(sid: str) -> dict | None:
    # Decode raw ID from encoded session ID
    decoded = _decode_session(sid)
    raw_id = decoded["id"] if decoded and decoded.get("id") else sid
    # First try: load from file using raw ID
    for s in _load("sessions.json", []):
        if s["id"] == raw_id:
            return s
    # Fallback: file lost (Render ephemeral disk). Reconstruct minimal session from encoded data.
    if decoded and decoded.get("id"):
        return {
            "id": decoded["id"],
            "kind": decoded.get("kind", "interview"),
            "created": decoded.get("created", 0),
            "meta": {}, "turns": [], "status": "active",
        }
    return None

def _save_session(session: dict) -> None:
    """Save session to file AND update encoded ID."""
    sessions = _load("sessions.json", [])
    raw_id = _decode_session(session["id"])["id"] if session["id"].startswith(_SESSION_PREFIX) else session["id"]
    found = False
    for i, s in enumerate(sessions):
        if s["id"] == raw_id:
            sessions[i] = {**session, "id": raw_id}
            found = True
            break
    if not found:
        sessions.append({**session, "id": raw_id})
    _save("sessions.json", sessions)

def append_turn(sid: str, turn: dict) -> dict | None:
    s = get_session(sid)
    if not s:
        return None
    s["turns"].append(turn)
    _save_session(s)
    return s

def finish_session(sid: str, report: dict | None = None) -> dict | None:
    s = get_session(sid)
    if not s:
        return None
    s["status"] = "finished"
    if report is not None:
        s["report"] = report
    _save_session(s)
    if report or s.get("turns"):
        update_profile_from_session(s)
    return s

def list_sessions() -> list[dict]:
    return _load("sessions.json", [])

# ---- documents ----
def save_document(doc: dict) -> list[dict]:
    docs = _load("documents.json", [])
    docs.append(doc)
    _save("documents.json", docs)
    return docs

def list_documents(section: str = "") -> list[dict]:
    docs = _load("documents.json", [])
    if section:
        docs = [d for d in docs if d.get("section") == section]
    return docs

def get_documents(ids: list[str]) -> list[dict]:
    docs = _load("documents.json", [])
    return [d for d in docs if d["id"] in ids]

def clear_documents(section: str = "") -> None:
    if section:
        docs = _load("documents.json", [])
        docs = [d for d in docs if d.get("section") != section]
        _save("documents.json", docs)
    else:
        _save("documents.json", [])

# ---- profile ----
DEFAULT_PROFILE = {
    "strengths": [], "weaknesses": [], "recurring_patterns": {},
    "sessions_completed": 0, "training_focus": "stronger interview answers",
    "avg_score": 0.0,
    "visual_patterns": {
        "gaze_away_total": 0, "slouch_total": 0, "movement_total": 0,
        "hands_hidden_total": 0, "gesture_total": 0,
        "best_visual_session": None, "worst_visual_session": None,
    },
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
    # Track visual patterns across sessions
    vp = profile.get("visual_patterns", DEFAULT_PROFILE["visual_patterns"])
    vc = rep.get("visual_communication", {})
    if vc:
        ca = vc.get("camera_attention", {})
        po = vc.get("posture", {})
        mv = vc.get("movement", {})
        ge = vc.get("gestures", {})
        vp["gaze_away_total"] = vp.get("gaze_away_total", 0) + ca.get("gaze_away_count", 0)
        vp["slouch_total"] = vp.get("slouch_total", 0) + po.get("slouch_count", 0)
        vp["movement_total"] = vp.get("movement_total", 0) + mv.get("excessive_count", 0)
        vp["hands_hidden_total"] = vp.get("hands_hidden_total", 0) + ge.get("hands_hidden_count", 0)
        vp["gesture_total"] = vp.get("gesture_total", 0) + ge.get("gesture_count", 0)
        # Track best/worst visual sessions
        visual_score = (5 - min(ca.get("gaze_away_count", 0), 5)
                        - min(po.get("slouch_count", 0), 5)
                        - min(mv.get("excessive_count", 0), 5))
        if vp.get("best_visual_session") is None or visual_score > vp.get("best_visual_score", 0):
            vp["best_visual_session"] = session.get("id", "")
            vp["best_visual_score"] = visual_score
        if vp.get("worst_visual_session") is None or visual_score < vp.get("worst_visual_score", 10):
            vp["worst_visual_session"] = session.get("id", "")
            vp["worst_visual_score"] = visual_score
    profile["visual_patterns"] = vp
    _save("profile.json", profile)
    return profile
