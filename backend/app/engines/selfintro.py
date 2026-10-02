"""Self Introduction — SEPARATE evaluation & feedback system.

Independent from the generic interview evaluators (HR / behavioral / topic):
one question, one six-dimension rubric, fresher self-introduction rules.

Honest scoring (root-cause fix for the repeated ~60% results):
- score = server-side mean of the numeric rubric dimensions; "n/a" excluded;
  the model's headline score is never trusted.
- The offline fallback measures each dimension from its OWN evidence — it no
  longer stacks the same filler/long-sentence penalty across three dimensions
  and no longer caps relevance at 7.0 (the old behaviour that pushed strong
  answers down to ~6/10 whenever the AI provider was on cooldown).
- The evaluation prompt carries explicit anti-anchor guidance ("do not
  default every answer to 6") and its own industry-interviewer system prompt
  instead of the generic difficulty tones.
"""
from __future__ import annotations
import random
import re

from backend.app.ai import service
from backend.app.engines import speech_analysis as sa

DIMS = ("structure", "clarity", "relevance", "technical_accuracy",
        "conciseness", "delivery")

# ---------------------------------------------------------------------------
# Question rules — the ONLY questions a self-introduction session may ask.
# ---------------------------------------------------------------------------
ALLOWED_VARIANTS = [
    "Tell me about yourself.",
    "Can you briefly introduce yourself?",
    "Tell me about yourself in a short and concise way.",
    "Please give me a brief introduction about yourself.",
    "Could you introduce yourself and briefly mention your education, key skills, and interests?",
]

_ALLOW_RE = re.compile(
    r"(tell me about yourself|introduce yourself|introduction about yourself)", re.I)
_DENY_RE = re.compile(
    r"(resume|curriculum vitae|\bcv\b|walk me through|challenge|failure|conflict|"
    r"behavioral|leadership|teamwork|journey|inspired|motivat|driven you|"
    r"\bwhy\b|\bhow\b|experience|project|situation|scenario|\bstrength\b|"
    r"\bweakness\b|company|previous|\bpast\b|\bjd\b|job description|follow[- ]?up|\bstar\b)",
    re.I)

_QUESTION_SYSTEM = (
    "You write ONE self-introduction opener for an interview. Nothing else. "
    "Never ask about resume, experience, projects, challenges, why/how questions, "
    "or anything an HR/behavioral interview would ask.")


def is_valid_question(q: str) -> bool:
    """True only for questions whose single goal is: let the candidate
    introduce themselves (item: STRICT RULES)."""
    q = (q or "").strip()
    if not q or len(q) > 220:
        return False
    if not _ALLOW_RE.search(q):
        return False
    if _DENY_RE.search(q):
        return False
    return True


def build_plan(difficulty: str, context: str) -> dict:
    """Exactly one self-introduction question; AI output is validated and
    falls back to the allowed fixed variants when it violates the rules."""
    question = None
    provider = "offline"
    prompt = (
        f"Write exactly ONE self-introduction question for a {difficulty}-level "
        "interview. The candidate should simply introduce themselves (who they "
        "are, current education/status, key skills, one project or achievement, "
        "career goal).\n"
        f"Allowed forms only, e.g.: {ALLOWED_VARIANTS}\n"
        "FORBIDDEN (reject these): resume walkthrough, experience/projects/"
        "challenges, why/how questions, behavioral questions, follow-ups, "
        "anything that turns this into an HR interview.\n"
        "Reply JSON: {\"question\": str}"
    )
    try:
        data, resp = service.generate_json(prompt, system=_QUESTION_SYSTEM, max_tokens=200)
        cand = str(data.get("question", "")).strip()
        if is_valid_question(cand):
            question, provider = cand, resp.provider
    except Exception:
        pass
    if not question:
        question = random.choice(ALLOWED_VARIANTS)
    return {"role": "Candidate", "focus": ["self-introduction"],
            "questions": [{"q": question, "topic": "self-intro"}],
            "provider": provider, "fallback_active": provider == "offline"}


# ---------------------------------------------------------------------------
# Coverage of what a fresher's introduction SHOULD include (requirement 2).
# ---------------------------------------------------------------------------
_WHO_OPEN = re.compile(
    r"^\s*(?:(?:good (?:morning|afternoon|evening)|hello|hi)\b[^,]{0,25},?\s*)?"
    r"(?:my name is|i am|i'm)\b", re.I)
_COVER_PATTERNS = {
    "who_i_am": re.compile(r"\bmy name is\b", re.I),
    "education_status": re.compile(
        r"\b(pursuing|studying|student|degree|bachelor|b\.?tech|m\.?tech|master|"
        r"graduate|graduating|college|university|school|diploma|expected to graduate)\b", re.I),
    "key_skills": re.compile(
        r"\b(skills?|skilled|proficient|technologies|tech stack|stack|familiar with|hands[- ]on)\b", re.I),
    "projects_achievements": re.compile(
        r"\b(project|built|developed|designed|created|implemented|capstone|internship|"
        r"certification|award|achiev)", re.I),
    "career_goal": re.compile(
        r"\b(goal|aim|looking for|seeking|aspire|hoping to|want to (?:become|work)|"
        r"pursuing a career|career (?:as|in)|next step|opportunity)\b", re.I),
}
COV_LABELS = {
    "who_i_am": "who you are",
    "education_status": "current education/status",
    "key_skills": "key skills",
    "projects_achievements": "a project or achievement",
    "career_goal": "career goal",
}
COV_PRAISE = {
    "who_i_am": "opens clearly with who you are",
    "education_status": "states current education/status",
    "key_skills": "names key skills clearly",
    "projects_achievements": "includes a concrete project or achievement",
    "career_goal": "closes with a career goal",
}
_COV_ORDER = ("who_i_am", "education_status", "key_skills",
              "projects_achievements", "career_goal")
_FIX_FOR_MISSING = {
    "who_i_am": "Start with one sentence: your name and current focus.",
    "education_status": "Add one line on your current education or status.",
    "key_skills": "Name your two strongest skills and back each with one proof.",
    "projects_achievements": "Add one project or achievement with a concrete result.",
    "career_goal": "End with your career goal in one sentence.",
}
_TECH_DUMP = re.compile(r"\b[\w+#.]+(?:\s*,\s*[\w+#.]+){4,}")
_GENERIC_MARKS = re.compile(
    r"\b(hard[- ]working|team player|self[- ]motivated|give my best|passionate about|"
    r"dynamic|creative thinker|good communication skills)\b", re.I)


def detect_coverage(answer: str) -> dict:
    cov = {k: bool(rx.search(answer or "")) for k, rx in _COVER_PATTERNS.items()}
    cov["who_i_am"] = bool(_WHO_OPEN.match(answer or "") or cov["who_i_am"])
    return cov


def compute_score(rubric: dict) -> float | None:
    """Server-side mean of the numeric dimensions; 'n/a' excluded."""
    vals = [float(v) for v in (rubric or {}).values()
            if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _normalize_rubric(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    out: dict = {}
    for dim in DIMS:
        v = raw.get(dim)
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("n/a", "na", "not applicable", "not judgeable",
                     "insufficient evidence", "unavailable"):
                out[dim] = "n/a"
                continue
            try:
                v = float(s)
            except ValueError:
                out[dim] = "n/a"
                continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[dim] = round(max(0.0, min(10.0, float(v))), 1)
        else:
            out[dim] = "n/a"
    return out


# ---------------------------------------------------------------------------
# Offline pack — deterministic evaluation from transcript signals only.
# Each rubric dimension is derived from its OWN evidence (no stacked penalties).
# ---------------------------------------------------------------------------
def _clamp(x: float, lo: float = 2.0, hi: float = 9.5) -> float:
    return round(max(lo, min(hi, x)), 1)


def _offline_pack(answer: str, sig: dict) -> dict:
    n = sig.get("word_count", 0)
    fills = sig.get("filler_total", 0)
    hedges = sig.get("qualifier_total", 0)
    longs = sig.get("long_sentences", 0)
    sents = sig.get("sentence_count", 0)
    rep = sig.get("repeated_words") or {}
    slow = bool(sig.get("slow_start"))
    covered = detect_coverage(answer)
    cov_count = sum(covered.values())
    missing = [k for k in _COV_ORDER if not covered[k]]

    if sig.get("empty") or n == 0:
        rubric = {"structure": 2.0, "clarity": 2.0, "relevance": 2.0,
                  "technical_accuracy": "n/a", "conciseness": 2.0, "delivery": 2.0}
    else:
        structure = _clamp(
            5.0 + (1.5 if sents >= 3 else 0.5 if sents == 2 else 0.0)
            + (1.5 if cov_count >= 4 else 1.0 if cov_count >= 2 else 0.0)
            + (0.5 if not slow else 0.0) - 0.3 * min(longs, 2))
        clarity = _clamp(8.5 - 0.35 * max(0, fills - 1) - 0.25 * min(longs, 3)
                         - (0.4 if slow else 0.0))
        # Relevance is coverage of the expected self-introduction content —
        # previously hard-capped at 7.0 even for perfect answers.
        relevance = _clamp(5.0 + 0.8 * cov_count - (2.5 if n < 15 else 0.0))
        if 60 <= n <= 180:
            conciseness = 8.5
        elif 180 < n <= 240:
            conciseness = 7.5
        elif 40 <= n < 60 or 240 < n <= 300:
            conciseness = 6.5
        elif 20 <= n < 40:
            conciseness = 5.5
        elif n < 20:
            conciseness = 3.5
        else:
            conciseness = 5.0
        if rep:
            conciseness = max(2.0, conciseness - 0.4)
        delivery = _clamp(8.5 - 0.4 * max(0, fills - 1) - 0.3 * min(longs, 2)
                          - (0.4 if slow else 0.0))
        rubric = {"structure": structure, "clarity": clarity,
                  "relevance": relevance, "technical_accuracy": "n/a",
                  "conciseness": round(conciseness, 1), "delivery": delivery}

    # WHAT WORKED (2-3)
    what_worked = [COV_PRAISE[k] for k in _COV_ORDER if covered[k]]
    if 60 <= n <= 180:
        what_worked.append("kept the introduction to a focused length")
    elif fills <= 1 and n > 0:
        what_worked.append("few filler words — clean delivery")
    if longs == 0 and sents >= 3:
        what_worked.append("short, easy-to-follow sentences")
    if not what_worked:
        what_worked = [f"answered the introduction ({n} words)"]
    what_worked = what_worked[:3]

    # FIX NEXT (2-3, most impactful first: missing content, then signals)
    fix_next = [_FIX_FOR_MISSING[k] for k in missing]
    if fills >= 3:
        fix_next.append(f"Remove filler words ({fills} in this answer) — pause instead.")
    if longs >= 2:
        fix_next.append(f"Split the {longs} long sentences into 15-word sentences.")
    if n > 250:
        fix_next.append("Cut to 60-90 seconds — details like that belong in later interview questions.")
    elif 0 < n < 40:
        fix_next.append(f"Expand beyond {n} words: education, skills, one project, a goal.")
    if rep and len(fix_next) < 3:
        w = sorted(rep, key=lambda k: rep[k], reverse=True)[0]
        fix_next.append(f"Stop repeating '{w}' — say it once.")
    if len(fix_next) < 2:
        fix_next.append("Use a five-beat structure: who → education → skills → project → goal.")
    if len(fix_next) < 2:
        fix_next.append("Record a 60-second version and cut anything that does not serve those five beats.")
    fix_next = fix_next[:3]

    # WHAT TO SKIP (unnecessary content actually present)
    skip_issues: list[str] = []
    if _TECH_DUMP.search(answer or ""):
        skip_issues.append("lists too many technologies instead of a few relevant ones")
    if rep:
        skip_issues.append("repeats the same skill or word several times")
    if len(_GENERIC_MARKS.findall(answer or "")) >= 2:
        skip_issues.append("generic statements (hard worker / team player) without evidence")
    if n > 250:
        skip_issues.append("long personal background and details that belong in later interview questions")
    elif n > 220:
        skip_issues.append("long personal background that should be trimmed")
    skip_issues = skip_issues[:3]

    # FOCUS / SKIP
    say = ("Who you are → current education/status → two key skills → one "
           "project with a result → career goal — 60 seconds total.")
    if missing:
        say += f" You still need: {', '.join(COV_LABELS[k] for k in missing)}."
    avoid = ("; ".join(skip_issues).capitalize() + ".") if skip_issues else \
        "Long personal history, repeated skills, technology dumps, and generic claims."

    # BETTER APPROACH — structure built only from what the candidate said.
    have = [COV_LABELS[k] for k in _COV_ORDER if covered[k]]
    better_approach = (
        "Structure for your next attempt: (1) who you are — one sentence; "
        "(2) current education/status; (3) two key skills; (4) one "
        "project/achievement with its result; (5) career goal. Keep it to 60 "
        "seconds."
        + (f" You already cover: {'; '.join(have)}." if have else "")
        + (f" Add or strengthen: {'; '.join(COV_LABELS[k] for k in missing)}."
           if missing else " Nothing major is missing — tighten the wording."))

    # COACH'S NEXT STEP — one specific practice
    if missing:
        step = _FIX_FOR_MISSING[missing[0]].rstrip(".") + " Time the full answer at 60 seconds."
    elif fills >= 3:
        step = "Record again and replace every filler word with a pause."
    elif longs >= 2:
        step = "Rewrite the long sentences into 15-word sentences, then say it twice."
    else:
        step = "Record a 60-second version, listen once, and tighten any slow section."

    assessment = {
        "worked": "; ".join(what_worked[:2]).capitalize() + ".",
        "missing": ("Missing: " + ", ".join(COV_LABELS[k] for k in missing) + ".")
                   if missing else
                   (("Watch out: " + skip_issues[0] + ".") if skip_issues else "Nothing major missing."),
        "change_next": fix_next[0],
    }

    score = compute_score(rubric) or 5.0
    main_issue = (skip_issues[0] if skip_issues else
                  (f"Missing: {COV_LABELS[missing[0]]}" if missing else fix_next[0]))
    return {
        "rubric": rubric,
        "score": score,
        "coverage": covered,
        "skip_issues": skip_issues,
        "what_worked": what_worked,
        "fix_next": fix_next,
        "focus_skip": {"say": say, "avoid": avoid},
        "better_approach": better_approach,
        "coach_next_step": step,
        "assessment": assessment,
        "strength": what_worked[0],
        "main_issue": main_issue,
        "biggest_issue": main_issue,
        "retry_suggested": score < 6.5,
        "retry_instruction": fix_next[0],
        "good": what_worked[:2],
        "relevance": {"verdict": "directly" if cov_count >= 4 else "partially" if cov_count >= 2 else "missed",
                      "note": f"Covers {cov_count}/5 expected elements of a self-introduction."},
        "sentences": [],
        "better_examples": [],
        "interviewer_want": ("A 60-second self-introduction: who you are, "
                             "education, key skills, one project, career goal."),
        "dimensions": {"clarity": f"{fills} fillers, {n} words",
                       "conciseness": "focused length" if 60 <= n <= 180 else f"{n} words",
                       "specificity": f"{cov_count}/5 elements covered"},
        "vocabulary": "precise enough" if hedges < 4 else f"{hedges} hedging words — swap for concrete claims",
        "fillers": f"{fills} fillers, {hedges} hedges in {n} words",
        "pacing": f"estimate from transcript only: {n} words",
        "completeness": "answered" if n >= 20 else "answer seems cut short — finish the point",
        "technical": "n/a",
        "articulation": "unavailable",
        "pronunciation": "unavailable",
    }


# ---------------------------------------------------------------------------
# Evaluation (separate prompt — never the generic HR/behavioral logic).
# ---------------------------------------------------------------------------
_EVAL_SYSTEM = (
    "You are an industry interviewer evaluating a fresher's SELF-INTRODUCTION "
    "only. You never evaluate behavioral answers, problem-solving, system "
    "design, leadership scenarios, or any other interview competency.")


def _ai_evaluate(answer: str, context: str, difficulty: str) -> tuple[dict, str]:
    ctx = (f"\nOptional resume/context (only to check factual alignment):\n"
           f"{context[:1200]}\n") if context else ""
    prompt = (
        f"Candidate answered the single self-introduction question "
        f"({difficulty} level): \"Tell me about yourself.\"\n{ctx}\n"
        f"Transcript:\n{answer[:2500]}\n\n"
        "Evaluate ONLY this self-introduction as an industry interviewer "
        "judging a fresher.\n\n"
        "Scoring guidance for \"rubric\" (0-10 each, or \"n/a\" when there is "
        "not enough evidence):\n"
        "- structure: clear opening → education → skills → project → goal\n"
        "- clarity: easy to follow, no rambling\n"
        "- relevance: stays on the self-introduction, covers expected content\n"
        "- technical_accuracy: honest, verifiable skill/project claims "
        "(\"n/a\" if nothing judgeable)\n"
        "- conciseness: focused, interview-appropriate length\n"
        "- delivery: flow and pacing visible in the transcript\n"
        "Score honestly across the FULL 0-10 range: a complete, well-structured "
        "introduction with concrete evidence deserves 8-10; partially complete "
        "or loosely organized deserves 5-7; missing most content deserves 0-4. "
        "Do NOT default every answer to 6 and do NOT cap strong answers.\n\n"
        "Also check whether the introduction covers: who I am, current "
        "education/status, key skills, 1-2 projects/achievements, career goal.\n"
        "Flag unnecessary content: long personal background, repeated skills, "
        "too many technologies, generic statements, irrelevant information, "
        "details that belong in later interview questions.\n\n"
        "Reply JSON: {"
        "\"rubric\": {\"structure\": 0-10, \"clarity\": 0-10, \"relevance\": 0-10, "
        "\"technical_accuracy\": 0-10 or \"n/a\", \"conciseness\": 0-10, \"delivery\": 0-10}, "
        "\"coverage\": {\"who_i_am\": bool, \"education_status\": bool, \"key_skills\": bool, "
        "\"projects_achievements\": bool, \"career_goal\": bool}, "
        "\"skip_issues\": [0-3 short strings of unnecessary content actually present], "
        "\"what_worked\": [2-3 short strings], "
        "\"fix_next\": [2-3 short strings — the most impactful, specific to this answer], "
        "\"focus_skip\": {\"say\": str (what to say), \"avoid\": str (what to avoid)}, "
        "\"better_approach\": str (a personalized improved self-introduction built ONLY "
        "from the candidate's actual words — never invent projects, skills, achievements), "
        "\"coach_next_step\": str (ONE specific thing to practice next), "
        "\"assessment\": {\"worked\": str, \"missing\": str, \"change_next\": str}, "
        "\"main_issue\": str, \"retry_suggested\": true/false, \"retry_instruction\": str, "
        "\"relevance\": {\"verdict\": \"directly|partially|missed\", \"note\": str}, "
        "\"dimensions\": {\"clarity\": str, \"conciseness\": str, \"specificity\": str}}"
    )
    data, resp = service.generate_json(prompt, system=_EVAL_SYSTEM, max_tokens=1800)
    return data, resp.provider


def _str_list(v, pad_from: list[str], lo: int = 2, hi: int = 3) -> list[str]:
    out = [str(s).strip() for s in (v or []) if isinstance(s, (str, int, float))
           and str(s).strip()][:hi]
    for s in pad_from:
        if len(out) >= lo:
            break
        if s not in out:
            out.append(s)
    return out


def _finalize(data: dict, answer: str, sig: dict, provider: str) -> dict:
    """Assemble the final evaluation: offline pack as the guaranteed floor,
    AI fields layered on top, score ALWAYS recomputed from the rubric."""
    out = _offline_pack(answer, sig)
    if isinstance(data, dict) and data:
        if isinstance(data.get("rubric"), dict):
            out["rubric"] = data["rubric"]
        if isinstance(data.get("coverage"), dict):
            out["coverage"] = {k: bool(data["coverage"].get(k, out["coverage"].get(k, False)))
                               for k in _COV_ORDER}
        if data.get("skip_issues") is not None:
            out["skip_issues"] = [str(s).strip() for s in (data.get("skip_issues") or [])
                                  if str(s).strip()][:3]
        if data.get("what_worked"):
            out["what_worked"] = _str_list(data.get("what_worked"), out["what_worked"])
        if data.get("fix_next"):
            out["fix_next"] = _str_list(data.get("fix_next"), out["fix_next"])
        fs = data.get("focus_skip")
        if isinstance(fs, dict) and (fs.get("say") or fs.get("avoid")):
            out["focus_skip"] = {"say": str(fs.get("say") or out["focus_skip"]["say"]),
                                 "avoid": str(fs.get("avoid") or out["focus_skip"]["avoid"])}
        if isinstance(data.get("better_approach"), str) and data["better_approach"].strip():
            out["better_approach"] = data["better_approach"].strip()
        if isinstance(data.get("coach_next_step"), str) and data["coach_next_step"].strip():
            out["coach_next_step"] = data["coach_next_step"].strip()
        asmt = data.get("assessment")
        if isinstance(asmt, dict) and any(asmt.get(k) for k in ("worked", "missing", "change_next")):
            out["assessment"] = {k: str(asmt.get(k) or out["assessment"][k])
                                 for k in ("worked", "missing", "change_next")}
        for k in ("main_issue", "retry_instruction", "interviewer_want"):
            if isinstance(data.get(k), str) and data[k].strip():
                out[k] = data[k].strip()
        if isinstance(data.get("relevance"), dict) and data["relevance"].get("verdict"):
            out["relevance"] = {"verdict": str(data["relevance"]["verdict"]),
                                "note": str(data["relevance"].get("note", ""))}
        if isinstance(data.get("dimensions"), dict) and data["dimensions"]:
            out["dimensions"] = {k: str(v) for k, v in data["dimensions"].items()}

    rubric = _normalize_rubric(out.get("rubric"))
    score = compute_score(rubric)
    if score is None:
        rubric = _normalize_rubric(_offline_pack(answer, sig)["rubric"])
        score = compute_score(rubric) or 5.0
    out["rubric"] = rubric
    out["score"] = score                      # server-computed — never the model's
    out["retry_suggested"] = score < 6.5
    # Compat aliases for older consumers/tests.
    out["strengths"] = out["what_worked"]
    out["improvements"] = out["fix_next"]
    out["coaching_tip"] = out["coach_next_step"]
    out["good"] = out["what_worked"][:2]
    out["biggest_issue"] = out["main_issue"]
    out["technical"] = ("n/a" if rubric.get("technical_accuracy") == "n/a"
                        else str(rubric["technical_accuracy"]))
    out["signals"] = sig
    out["provider"] = provider
    return out


def evaluate(answer: str, context: str = "", difficulty: str = "intermediate") -> dict:
    """Self-introduction evaluation. Never raises; AI failure falls back to
    the deterministic pack."""
    difficulty = difficulty if difficulty in ("beginner", "intermediate", "advanced", "expert") else "intermediate"
    sig = sa.analyze(answer or "")
    try:
        data, provider = _ai_evaluate(answer or "", context or "", difficulty)
    except Exception:
        data, provider = {}, "offline"
    try:
        return _finalize(data, answer or "", sig, provider)
    except Exception:
        return _finalize({}, answer or "", sig, "offline")


def coaching(evaluation: dict) -> dict:
    """5-field coaching box derived from the self-introduction evaluation —
    no generic HR coaching prompt, no extra AI call."""
    ev = evaluation or {}
    ww = ev.get("what_worked") or ev.get("strengths") or []
    fx = ev.get("fix_next") or ev.get("improvements") or []
    fs = ev.get("focus_skip") or {}
    asmt = ev.get("assessment") or {}
    step = (ev.get("coach_next_step") or ev.get("coaching_tip")
            or "Record a 60-second version and tighten one slow section.")
    return {"appreciation": (ww[0] if ww else "You completed your self-introduction").strip().capitalize() + ".",
            "priority": f"Priority: {fx[0] if fx else 'Tighten the structure.'}",
            "specific_feedback": asmt.get("missing") or (fx[1] if len(fx) > 1 else asmt.get("worked", "")),
            "improvement": f"Try: {fs['say']}" if fs.get("say") else step,
            "next_step": step}


def report_narrative(real: list[dict], avg: float, coverage_note: str) -> dict:
    """Final-report narrative for self-introduction sessions: short, fixed
    structure, built ONLY from the actual evaluation (no generic HR narrative,
    no AI drift — e.g. no hallucinated claims about skipped answers)."""
    if not real:
        return {"summary": ("No self-introduction was recorded, so nothing was "
                            "scored. Answer the single question to get feedback."),
                "strengths": [], "biggest_weakness": "", "training": [],
                "top_priority": "", "next_practice": "Start the Self Introduction again and record one full answer.",
                "focus_skip": {"say": "Who you are → education → skills → project → goal (60 seconds).",
                               "avoid": "Skipping the question — feedback only comes from your actual answer."},
                "better_approach": "", "communication": "No answer captured.",
                "technical": "n/a",
                "role_alignment": "Not assessed — no answer captured."}
    ev = real[0].get("evaluation") or {}
    ww = _str_list(ev.get("what_worked") or ev.get("strengths"), [], 0, 3)
    fx = _str_list(ev.get("fix_next") or ev.get("improvements"), [], 0, 3)
    fs = ev.get("focus_skip") or {"say": "", "avoid": ""}
    asmt = ev.get("assessment") or {}
    step = (ev.get("coach_next_step") or ev.get("coaching_tip")
            or "Record a 60-second version and tighten one slow section.")
    summary = " ".join(s for s in (asmt.get("worked"), asmt.get("missing"),
                                   asmt.get("change_next")) if s).strip()
    if not summary:
        summary = (f"What worked: {'; '.join(ww) or 'you answered'}. "
                   f"What to change: {'; '.join(fx[:2])}.")
    sig = ev.get("signals") or {}
    comm = (f"Transcript signals: {sig.get('word_count', 0)} words, "
            f"{sig.get('filler_total', 0)} fillers, "
            f"{sig.get('long_sentences', 0)} sentences over 25 words."
            if sig else "No transcript signals were captured.")
    tech = ev.get("technical") or "n/a"
    return {"summary": (f"{coverage_note} {summary}").strip(),
            "strengths": ww,
            "biggest_weakness": asmt.get("missing") or (fx[0] if fx else ""),
            "training": fx,
            "top_priority": fx[0] if fx else "",
            "next_practice": step,
            "focus_skip": {"say": fs.get("say", ""), "avoid": fs.get("avoid", "")},
            "better_approach": str(ev.get("better_approach") or ""),
            "communication": comm,
            "technical": f"Technical accuracy: {tech}" if tech != "n/a" else "Technical accuracy: n/a — no judgeable technical claims.",
            "role_alignment": ("Assessed from the self-introduction transcript only"
                               + (" (resume context was provided)." if False else "."))}
