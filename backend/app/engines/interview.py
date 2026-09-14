"""Interview engine: plan generation, adaptive follow-ups, evaluation, report."""
from __future__ import annotations
import random
from backend.app.ai import service
from backend.app.engines import speech_analysis as sa

TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"]

BASE_QUESTIONS = {
    "hr": ["Tell me about yourself in 60 seconds.", "Why this role?", "What is your biggest strength?"],
    "technical": ["Explain a technical concept you know well simply.", "How would you debug a failing system?"],
    "project": ["Walk me through your most important project and YOUR contribution.", "What was the hardest bug and how did you fix it?"],
    "behavioral": ["Tell me about a challenge you overcame.", "Tell me about a failure and what you learned."],
    "resume": ["Explain the project on your resume you are proudest of.", "What exactly did YOU do vs your team?"],
    "jd": ["Which requirement in the JD is your strongest match? Prove it.", "Where is your biggest gap vs this JD?"],
    "topic": ["Explain the core idea of the uploaded topic in 60 seconds.", "Give a real example."],
    "mixed": ["Tell me about yourself.", "Explain your best project.", "Tell me about a conflict."],
    "custom": ["Tell me about yourself.", "What should we focus on first?", "Give me a specific example from your experience."],
}

def build_plan(interview_type: str, difficulty: str, context: str, signals: dict | None = None) -> dict:
    interview_type = interview_type if interview_type in TYPES else "mixed"
    seeds = list(BASE_QUESTIONS[interview_type])
    prompt = (
        f"You are a realistic {interview_type} interviewer ({difficulty} level).\n"
        f"Candidate context:\n{context[:4000]}\nSignals: {signals or {}}\n"
        f"Seed questions: {seeds}\n"
        "Create an interview plan: 5 questions tailored to this candidate, increasing depth. "
        "Reply JSON: {\"role\": str, \"focus\": [str], \"questions\": [str]}"
    )
    try:
        data, resp = service.generate_json(prompt)
        qs = data.get("questions") or seeds
        return {"role": data.get("role", "Candidate"), "focus": data.get("focus", seeds[:2]),
                "questions": qs[:6], "provider": resp.provider, "fallback_active": resp.fallback_active}
    except Exception:
        random.shuffle(seeds)
        return {"role": "Candidate", "focus": seeds[:2], "questions": seeds[:5],
                "provider": "offline", "fallback_active": False}

def next_question(history: list[dict], context: str, interview_type: str, difficulty: str,
                  profile_note: str = "") -> dict:
    last = history[-1] if history else {}
    last_q = last.get("question", "")
    last_a = (last.get("answer") or "")[:1500]
    prev_fb = ""
    if len(history) >= 2:
        ev = (history[-2].get("evaluation") or {})
        if ev.get("main_issue"):
            prev_fb = f" Known weakness to probe: {ev['main_issue']}."
    prompt = (
        f"You are conducting a {interview_type} interview ({difficulty}).\nContext: {context[:3000]}\n"
        f"Last question: {last_q}\nLast answer: {last_a}\n"
        f"Candidate profile: {profile_note[:300]}.{prev_fb}\n"
        "Ask ONE adaptive follow-up that goes deeper (why/how/prove it), referencing their words. "
        "Keep it under 25 words. Also give a minimal bridge line (<=10 words, e.g. 'Good. Let's go deeper.'). "
        "Reply JSON: {\"bridge\": str, \"question\": str}"
    )
    try:
        data, resp = service.generate_json(prompt, max_tokens=400)
        return {"bridge": data.get("bridge", "Good. Let's go deeper."),
                "question": data.get("question", "Can you give a specific example?"),
                "provider": resp.provider, "fallback_active": resp.fallback_active}
    except Exception:
        sig = sa.analyze(last_a)
        q = ("What exactly did YOU do there — be specific?"
             if sa.top_issue(sig) in ("vague_language", "structure")
             else "Why did you choose that approach over alternatives?")
        return {"bridge": "Let's explore that.", "question": q,
                "provider": "offline", "fallback_active": False}

EVAL_FIELDS = ("score, strength, main_issue, retry_suggested, retry_instruction, "
    "good, biggest_issue, relevance, sentences, better_examples, interviewer_want, "
    "dimensions, articulation, pronunciation")

def evaluate_answer(question: str, answer: str, interview_type: str) -> dict:
    """Live per-answer report. Only uses evidence in the transcript; audio-only
    metrics (articulation/pronunciation) are marked unavailable, never invented."""
    sig = sa.analyze(answer)
    prompt = (
        f"Evaluate this {interview_type} interview answer for a live coaching panel.\n"
        f"Q: {question}\nA: {answer[:1500]}\nSignals: {sig}\n"
        "Reply JSON with exactly these keys: "
        "{\"score\": 0-10, \"strength\": str, \"main_issue\": str, "
        "\"retry_suggested\": true/false, \"retry_instruction\": str, "
        "\"good\": [1-2 short strings of what worked], "
        "\"biggest_issue\": str (one line), "
        "\"relevance\": {\"verdict\": \"directly|partially|missed\", \"note\": str explaining why, quoting the answer}, "
        "\"sentences\": [{\"problem\": str quoting the weak sentence (max 25 words), \"fix\": str how to reshape it}] (max 2, [] if fine), "
        "\"better_examples\": [{\"text\": str (1-2 improved versions grounded in the user's actual answer), \"why\": str}] (max 2), "
        "\"interviewer_want\": str (what the interviewer was really listening for), "
        "\"dimensions\": {\"clarity\": str, \"conciseness\": str, \"specificity\": str} (one short line each), "
        "\"vocabulary\": str (one line on word choice: precise vs vague), "
        "\"fillers\": str (describe filler usage using these real counts: "
        f"fillers={sig.get('filler_total', 0)}, hedges={sig.get('qualifier_total', 0)}), "
        "\"pacing\": str (estimate from transcript length only — label it an estimate, "
        f"this answer has {sig.get('word_count', 0)} words), "
        "\"completeness\": str (did the answer finish the point or trail off?), "
        "\"technical\": str (technical correctness — or the literal string \"n/a\" "
        "for non-technical interview types), "
        "\"articulation\": \"unavailable\", "
        "\"pronunciation\": \"unavailable\"} "
        "Set articulation/pronunciation to the literal string \"unavailable\" — "
        "they cannot be measured from a text transcript."
    )
    try:
        data, resp = service.generate_json(prompt, max_tokens=1100)
        data["articulation"] = "unavailable"  # enforce honesty even if model improvises
        data["pronunciation"] = "unavailable"
        data.setdefault("vocabulary", "—")
        data.setdefault("fillers", f"{sig.get('filler_total', 0)} fillers in transcript")
        data.setdefault("pacing", "estimate from transcript only")
        data.setdefault("completeness", "—")
        data.setdefault("technical", "n/a")
        data.setdefault("good", [])
        data.setdefault("sentences", [])
        data.setdefault("better_examples", [])
        data.setdefault("dimensions", {})
        if not isinstance(data.get("relevance"), dict):
            data["relevance"] = {"verdict": "partially", "note": str(data.get("relevance", ""))}
        return {**data, "signals": sig, "provider": resp.provider}
    except Exception:
        score = max(3.0, min(8.5, 7.0 - 0.4 * sig.get("filler_total", 0)))
        sent_fix = []
        if sig.get("long_sentences"):
            sent_fix = [{"problem": "one or more sentences run over 25 words",
                         "fix": "Split long sentences: one idea per sentence, then pause."}]
        return {"score": round(score, 1), "strength": "addressed the question",
                "main_issue": sa.top_issue(sig), "retry_suggested": score < 6.5,
                "retry_instruction": "Retry leading with your main point in 10 seconds.",
                "good": ["addressed the question"], "biggest_issue": sa.top_issue(sig),
                "relevance": {"verdict": "partially",
                              "note": "Offline evaluation — full relevance analysis needs the AI."},
                "sentences": sent_fix, "better_examples": [],
                "interviewer_want": "A specific, concise answer with your personal contribution.",
                "dimensions": {"clarity": f"{sig.get('word_count', 0)} words, {sig.get('filler_total', 0)} fillers",
                               "conciseness": "shorter is stronger" if sig.get("word_count", 0) > 120 else "good length",
                               "specificity": "add one concrete example" if sig.get("qualifier_total", 0) >= 3 else "concrete enough"},
                "vocabulary": "precise enough" if sig.get("qualifier_total", 0) < 3 else "too many hedges — swap vague words for concrete ones",
                "fillers": f"{sig.get('filler_total', 0)} fillers, {sig.get('qualifier_total', 0)} hedges in {sig.get('word_count', 0)} words",
                "pacing": f"estimate from transcript only: {sig.get('word_count', 0)} words",
                "completeness": "answer ends" if sig.get("word_count", 0) >= 20 else "answer seems cut short — finish the point",
                "technical": "n/a",
                "articulation": "unavailable", "pronunciation": "unavailable",
                "signals": sig, "provider": "offline"}

def final_report(history: list[dict], role: str, jd_text: str = "") -> dict:
    scores = [h.get("evaluation", {}).get("score", 0) for h in history if h.get("evaluation")]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    best = max(history, key=lambda h: h.get("evaluation", {}).get("score", 0)) if history else {}
    worst = min(history, key=lambda h: h.get("evaluation", {}).get("score", 10)) if history else {}
    # Real aggregates across the completed answers — computed, never invented.
    issues = [(h.get("evaluation") or {}).get("main_issue") for h in history]
    issues = [i for i in issues if i]
    recurring = sorted(set(issues), key=issues.count, reverse=True)[:2]
    verdicts = [((h.get("evaluation") or {}).get("relevance") or {}).get("verdict", "partially")
                for h in history if h.get("evaluation")]
    n_direct = sum(1 for v in verdicts if v == "directly")
    relevance_summary = (f"{n_direct}/{len(verdicts)} answers directly addressed the question."
                         if verdicts else "No answers evaluated.")
    tot_fill = sum(((h.get("evaluation") or {}).get("signals") or {}).get("filler_total", 0) for h in history)
    tot_long = sum(((h.get("evaluation") or {}).get("signals") or {}).get("long_sentences", 0) for h in history)
    tot_words = sum(((h.get("evaluation") or {}).get("signals") or {}).get("word_count", 0) for h in history)
    sentence_patterns = (f"Across {len(history)} answers: {tot_fill} fillers, "
                         f"{tot_long} over-long sentences, {tot_words} words total.")
    pronunciation_note = ("Not enough data to evaluate pronunciation/articulation: "
                          "sessions are scored from text transcripts, not analyzed audio.")
    prompt = (
        f"Write a final {role} interview report. Q&A: "
        f"{str([(h.get('question'), (h.get('answer') or '')[:400]) for h in history])[:4000]}\n"
        f"JD excerpt: {jd_text[:1500]}\n"
        f"Measured aggregates: relevance {relevance_summary} {sentence_patterns} "
        f"Recurring issues: {recurring}.\n"
        "Reply JSON: {\"summary\": str, \"strengths\": [str,str], "
        "\"biggest_weakness\": str, \"communication\": str, \"technical\": str, "
        "\"role_alignment\": str, \"training\": [str,str], "
        "\"top_priority\": str (single most important improvement), "
        "\"next_practice\": str (one concrete next session, e.g. 'Spontaneous Q&A')}."
    )
    try:
        data, resp = service.generate_json(prompt)
    except Exception:
        data, resp = ({"summary": f"Answered {len(history)} questions, avg score {avg}.",
                       "strengths": ["showed up and communicated", "gave relevant examples"],
                       "biggest_weakness": recurring[0] if recurring else "slow time-to-main-point",
                       "communication": "Work on shorter sentences and fewer fillers.",
                       "technical": "Add concrete reasoning and examples.",
                       "role_alignment": "Tie answers to JD requirements explicitly.",
                       "training": ["Lead with the main point in 10 seconds.",
                                    "Use one specific project example per answer."],
                       "top_priority": recurring[0] if recurring else "concise structured answers",
                       "next_practice": "Spontaneous Q&A"},
                      type("R", (), {"provider": "offline"})())
    data.setdefault("top_priority", data.get("biggest_weakness", "—"))
    data.setdefault("next_practice", "Practice")
    return {"overall": avg, "answers_evaluated": len(scores),
            "best_answer": {"question": best.get("question"), "score": (best.get("evaluation") or {}).get("score")},
            "weakest_answer": {"question": worst.get("question"),
                               "issue": (worst.get("evaluation") or {}).get("main_issue")},
            **data,
            # measured aggregates always win over model text
            "recurring_problems": recurring,
            "relevance_summary": relevance_summary,
            "sentence_patterns": sentence_patterns,
            "pronunciation_note": pronunciation_note,
            "provider": getattr(resp, "provider", "offline")}
