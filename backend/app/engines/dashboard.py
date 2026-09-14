"""Long-term performance dashboard: factual 4-5 line summary + section breakdown.

Built ONLY from real stored data (sessions, evaluations, profile). No fake scores,
no motivational filler. Insufficient data -> explicit fallback line.
"""
from __future__ import annotations
from backend.app.session import manager as store

MIN_SESSIONS = 2

SECTION_OF = {
    "interview": "Interviews",
    "podcast": "Podcast",
    "practice": None,  # resolved via scenario below
}
SCENARIO_SECTION = {
    "story": "Storytelling",
    "presentation": "Public Speaking",
    "podcast": "Podcast",
    "wit": "Wit",
    "spontaneous": "Q&A",
    "qa": "Q&A",
}

def _section(s: dict) -> str:
    if s.get("kind") == "interview":
        return "Interviews"
    if s.get("kind") == "podcast":
        return "Podcast"
    return SCENARIO_SECTION.get((s.get("meta") or {}).get("scenario"), "Communication")


def build_dashboard() -> dict:
    sessions = store.list_sessions()
    profile = store.get_profile()
    done = [s for s in sessions if s.get("status") == "finished"]
    # Sections with real completed sessions ONLY — never zero-count placeholders.
    by_section: dict[str, int] = {}
    for s in done:
        sec = _section(s)
        by_section[sec] = by_section.get(sec, 0) + 1

    interviews = [s for s in done if s.get("kind") == "interview"]
    # interview averages from stored reports (real)
    overalls = [s["report"]["overall"] for s in interviews
                if isinstance(s.get("report"), dict) and s["report"].get("overall") is not None]
    interview_avg = round(sum(overalls) / len(overalls), 1) if overalls else None
    by_type: dict[str, float] = {}
    for s in interviews:
        rep = s.get("report") or {}
        if rep.get("overall") is None:
            continue
        t = (s.get("meta") or {}).get("type", "mixed")
        by_type.setdefault(t, []).append(rep["overall"])
    by_type = {k: round(sum(v) / len(v), 1) for k, v in by_type.items()}

    if len(done) < MIN_SESSIONS:
        return {
            "summary_lines": ["Not enough completed sessions to determine a reliable trend."],
            "sections": by_section, "interview_avg": interview_avg, "interview_n": len(overalls),
            "by_type": by_type,
            "strengths": profile.get("strengths", []),
            "recurring": profile.get("weaknesses", []),
            "focus": profile.get("training_focus", ""),
            "sessions_completed": profile.get("sessions_completed", 0),
            "recent": _recent(sessions),
            "metrics": _metrics(interviews),
            "recent_charts": _recent_charts(done),
            "trend": _trend_points(interviews),
        }

    # relevance across evaluated answers (real verdicts)
    verdicts = []
    for s in interviews:
        for t in s.get("turns", []):
            v = ((t.get("evaluation") or {}).get("relevance") or {}).get("verdict")
            if v:
                verdicts.append(v)
    n_direct = sum(1 for v in verdicts if v == "directly")

    pats = profile.get("recurring_patterns", {}) or {}
    top_issue = max(pats, key=pats.get) if pats else None
    focus = profile.get("training_focus", "")

    lines: list[str] = []
    if verdicts:
        ratio = n_direct / len(verdicts)
        if ratio >= 0.5:
            lines.append(
                f"Your interview answers are generally relevant ({n_direct}/{len(verdicts)} rated directly on-point)"
                + (", but several responses take too long to reach the main point." if top_issue in ("weak_opening", "long_sentences", "structure") else "."))
        else:
            lines.append(
                f"Only {n_direct}/{len(verdicts)} answers rated directly on-point — "
                "most need tighter focus on the question asked.")
    elif interviews:
        lines.append(f"You have completed {len(interviews)} interview(s)" +
                     (f" averaging {interview_avg}/10." if interview_avg is not None else "."))
    if top_issue == "fillers":
        lines.append("Filler usage appears repeatedly during longer answers.")
    elif top_issue:
        lines.append(f"The most repeated pattern is {top_issue.replace('_', ' ')}.")
    tech = by_type.get("technical")
    beh = by_type.get("behavioral")
    if tech is not None and beh is not None:
        stronger = "Technical explanations" if tech >= beh else "Behavioral answers"
        lines.append(f"{stronger} score higher ({tech} vs {beh}).")
    elif interview_avg is not None:
        lines.append(f"Interview performance averages {interview_avg}/10 across {len(overalls)} scored session(s).")
    lines.append("Pronunciation analysis is available only for sessions with sufficient audio quality; "
                "current sessions are scored from transcripts.")
    if focus:
        lines.append(f"Your current focus should be {focus}.")
    lines = lines[:5]

    return {
        "summary_lines": lines,
        "sections": by_section, "interview_avg": interview_avg, "interview_n": len(overalls),
        "by_type": by_type,
        "strengths": profile.get("strengths", []),
        "recurring": profile.get("weaknesses", []),
        "focus": focus,
        "sessions_completed": profile.get("sessions_completed", 0),
        "recent": _recent(sessions),
        "metrics": _metrics(interviews),
        "recent_charts": _recent_charts(done),
        "trend": _trend_points(interviews),
    }


def _recent(sessions: list[dict], n: int = 5) -> list[dict]:
    out = []
    for s in list(sessions)[-n:]:
        out.append({"id": s["id"], "kind": s.get("kind"),
                    "detail": (s.get("meta") or {}).get("scenario") or (s.get("meta") or {}).get("type", ""),
                    "status": s.get("status"), "created": s.get("created")})
    return list(reversed(out))


def _eval_turns(interviews: list[dict]) -> list[dict]:
    """Evaluated interview answers only — the only place numeric signals live."""
    out = []
    for s in interviews:
        for t in s.get("turns", []):
            if t.get("answer") and t.get("evaluation"):
                out.append({"sid": s["id"], **t})
    return out


def _metrics(interviews: list[dict]) -> dict:
    """Every entry carries its basis (N answers) or supported:false. No defaults."""
    turns = _eval_turns(interviews)
    m: dict = {}
    if not turns:
        return m
    n = len(turns)
    scores = [t["evaluation"].get("score") for t in turns if t["evaluation"].get("score") is not None]
    if scores:
        m["avg_answer_score"] = {"value": round(sum(scores) / len(scores), 1), "basis": f"{len(scores)} answers"}
    verdicts = [(t["evaluation"].get("relevance") or {}).get("verdict") for t in turns]
    verdicts = [v for v in verdicts if v]
    if verdicts:
        m["direct_rate"] = {"value": round(100 * sum(1 for v in verdicts if v == "directly") / len(verdicts)),
                            "basis": f"{len(verdicts)} answers"}
    sigs = [(t["evaluation"].get("signals") or {}) for t in turns]
    sigs = [s for s in sigs if s.get("word_count")]
    if sigs:
        k = len(sigs)
        m["fillers_per_answer"] = {"value": round(sum(s.get("filler_total", 0) for s in sigs) / k, 1), "basis": f"{k} answers"}
        m["long_sentences_per_answer"] = {"value": round(sum(s.get("long_sentences", 0) for s in sigs) / k, 1), "basis": f"{k} answers"}
        m["words_per_answer"] = {"value": round(sum(s.get("word_count", 0) for s in sigs) / k), "basis": f"{k} answers"}
    # technical correctness only where the evaluator actually judged it
    judged = [t for t in turns if (t["evaluation"].get("technical") not in (None, "n/a", ""))]
    if judged:
        js = [t["evaluation"]["score"] for t in judged if t["evaluation"].get("score") is not None]
        if js:
            m["technical_avg"] = {"value": round(sum(js) / len(js), 1), "basis": f"{len(js)} technical answers"}
    return m


def _recent_charts(done: list[dict], n: int = 8) -> list[dict]:
    """One real entry per recent COMPLETED session. Only metrics that exist for it."""
    out = []
    for s in list(done)[-n:]:
        entry: dict = {"id": s["id"], "section": _section(s), "created": s.get("created"),
                       "kind": s.get("kind")}
        if s.get("kind") == "interview":
            turns = [t for t in s.get("turns", []) if t.get("answer") and t.get("evaluation")]
            rep = s.get("report") or {}
            entry["answers"] = len(turns)
            if rep.get("overall") is not None:
                entry["overall"] = rep["overall"]
            scores = [t["evaluation"].get("score") for t in turns if t["evaluation"].get("score") is not None]
            if scores:
                entry["avg_score"] = round(sum(scores) / len(scores), 1)
            v = [((t["evaluation"] or {}).get("relevance") or {}).get("verdict") for t in turns]
            v = [x for x in v if x]
            if v:
                entry["direct"] = f"{sum(1 for x in v if x == 'directly')}/{len(v)}"
            f = sum(((t["evaluation"] or {}).get("signals") or {}).get("filler_total", 0) for t in turns)
            entry["fillers"] = f
            if rep.get("recurring_problems"):
                entry["issues"] = rep["recurring_problems"][:2]
        else:
            turns = s.get("turns", [])
            entry["turns"] = len(turns)
            entry["words"] = sum(len((t.get("transcript") or t.get("answer") or "").split()) for t in turns)
            iss = [t.get("issue") for t in turns if t.get("issue")]
            if iss:
                entry["issues"] = sorted(set(iss), key=iss.count, reverse=True)[:2]
        out.append(entry)
    return list(reversed(out))


def _trend_points(interviews: list[dict]) -> list[dict]:
    pts = []
    for s in interviews:
        rep = s.get("report") or {}
        if rep.get("overall") is not None:
            pts.append({"sid": s["id"], "created": s.get("created"), "overall": rep["overall"]})
    return pts
