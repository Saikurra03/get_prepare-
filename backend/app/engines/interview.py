"""Interview engine: plan generation, adaptive follow-ups, evaluation, report.
Each interview type has its own system prompt for plan, evaluation, and follow-up."""
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

# Type-specific system instructions for plan generation
TYPE_PLAN_INSTRUCTIONS = {
    "hr": (
        "You are a senior HR interviewer. Generate questions about: self-introduction, "
        "career motivation, strengths/weaknesses, teamwork, conflict resolution, "
        "leadership style, why this company/role, salary expectations, availability. "
        "Focus on presence, confidence, clarity, and cultural fit. "
        "If a resume is provided, ask about specific experience listed on it."
    ),
    "technical": (
        "You are a senior technical interviewer. Generate questions about: "
        "core technical skills, system design, debugging approach, coding methodology, "
        "architecture decisions, trade-offs, technical depth in the candidate's stack. "
        "If technical material or resume is provided, ask about specific technologies mentioned. "
        "Questions should test actual understanding, not just buzzword recall."
    ),
    "project": (
        "You are a technical lead interviewing about projects. Generate questions about: "
        "specific projects from the candidate's resume/material, their personal contribution, "
        "technical decisions made, challenges faced, outcomes and metrics, "
        "what they would do differently, team dynamics, technologies used. "
        "If project material is provided, ask about specific details from it."
    ),
    "behavioral": (
        "You are a behavioral interviewer using STAR method. Generate questions about: "
        "specific situations showing leadership, conflict, failure, teamwork, "
        "deadline pressure, difficult decisions, receiving feedback. "
        "Each question should prompt for Situation-Task-Action-Result structure. "
        "Ask for concrete examples, not hypotheticals."
    ),
    "resume": (
        "You are an interviewer who has read the candidate's resume carefully. "
        "Generate questions that target SPECIFIC sections of the resume: "
        "specific projects, specific skills, specific experiences listed. "
        "Ask about things actually written on the resume — not generic questions. "
        "Probe for depth: 'You listed X — tell me about a specific time you used it.'"
    ),
    "jd": (
        "You are an interviewer comparing a candidate against a job description. "
        "Generate questions that test alignment with JD requirements: "
        "specific requirements from the JD, gaps between candidate and JD, "
        "how candidate's experience maps to the role, what candidate brings that JD asks for. "
        "If both JD and resume are provided, compare them and probe gaps."
    ),
    "topic": (
        "You are an expert interviewer testing knowledge of a specific topic. "
        "Generate questions that test deep understanding of the uploaded material: "
        "core concepts, practical applications, edge cases, trade-offs, "
        "real-world examples, how the topic connects to broader knowledge. "
        "Questions must come FROM the material — not generic questions about the topic area."
    ),
    "mixed": (
        "You are conducting a comprehensive interview covering multiple areas. "
        "Combine: HR questions (self-introduction, motivation), technical questions "
        "(skills, problem-solving), and behavioral questions (STAR examples). "
        "Balance the mix across all three areas. Adapt based on candidate responses."
    ),
    "custom": (
        "You are following the candidate's custom interview instructions. "
        "Focus on what the candidate specified. Ask targeted questions about "
        "the custom focus area they described. Adapt based on their responses."
    ),
}

# Type-specific evaluation instructions
TYPE_EVAL_INSTRUCTIONS = {
    "hr": (
        "Evaluate for HR criteria: confidence, clarity of self-presentation, "
        "relevant experience, cultural fit indicators, communication style, "
        "authenticity, self-awareness. Check if answers show genuine motivation."
    ),
    "technical": (
        "Evaluate for technical criteria: accuracy of technical claims, "
        "depth of understanding, problem-solving approach, ability to explain "
        "complex concepts clearly, awareness of trade-offs, practical experience."
    ),
    "project": (
        "Evaluate for project criteria: clear personal contribution (not team), "
        "specific technical decisions, measurable outcomes, lessons learned, "
        "ownership of challenges, realistic assessment of what went well/poorly."
    ),
    "behavioral": (
        "Evaluate for behavioral criteria: STAR structure (Situation-Task-Action-Result), "
        "specific concrete examples (not hypotheticals), personal role in the outcome, "
        "self-reflection and learning, relevance of the example to the question."
    ),
    "resume": (
        "Evaluate for resume accuracy: claims match resume content, "
        "depth of experience matches stated roles, specific examples for listed projects, "
        "honest representation of skills and contributions."
    ),
    "jd": (
        "Evaluate for JD alignment: answers address specific JD requirements, "
        "experience maps to role needs, gaps are acknowledged honestly, "
        "candidate shows understanding of the role's actual responsibilities."
    ),
    "topic": (
        "Evaluate for topic mastery: accurate understanding of material, "
        "ability to explain concepts clearly, practical application knowledge, "
        "awareness of edge cases and limitations, depth beyond surface-level."
    ),
    "mixed": (
        "Evaluate across all dimensions: communication clarity, technical depth, "
        "STAR structure for behavioral, self-presentation, relevance of examples. "
        "Weight based on what the answer attempted to address."
    ),
    "custom": (
        "Evaluate based on the custom focus area specified. "
        "Check relevance to the custom instructions, depth of response, "
        "clarity of communication, and specific examples."
    ),
}

# Type-specific next-question instructions
TYPE_FOLLOWUP_INSTRUCTIONS = {
    "hr": "Ask a follow-up about their motivation, self-awareness, or how they handle specific workplace situations.",
    "technical": "Ask a deeper technical question — probe for implementation details, trade-offs, or alternative approaches.",
    "project": "Ask about a specific technical decision, outcome metric, or what they would change if they did it again.",
    "behavioral": "Ask for another specific example, or probe deeper into the STAR elements (What exactly did you do? What was the result?).",
    "resume": "Ask about a specific item on their resume — a project, skill, or experience they mentioned.",
    "jd": "Ask about how their specific experience maps to a JD requirement, or probe a gap area.",
    "topic": "Ask about a specific concept from the material, its application, or an edge case.",
    "mixed": "Adapt the follow-up to the area the candidate just addressed — go deeper or shift to a new area.",
    "custom": "Follow up on the custom focus area they specified.",
}


def build_plan(interview_type: str, difficulty: str, context: str,
               signals: dict | None = None, num_questions: int = 5) -> dict:
    interview_type = interview_type if interview_type in TYPES else "mixed"
    seeds = list(BASE_QUESTIONS[interview_type])
    type_instructions = TYPE_PLAN_INSTRUCTIONS.get(interview_type, TYPE_PLAN_INSTRUCTIONS["mixed"])

    prompt = (
        f"You are a realistic {interview_type} interviewer ({difficulty} level).\n"
        f"Type-specific guidance:\n{type_instructions}\n\n"
        f"Candidate context (resume, JD, project material, topic — whatever was uploaded):\n"
        f"{context[:6000]}\n\n"
        f"Skill signals: {signals or {}}\n\n"
        f"Seed questions (use as inspiration, customize to the candidate): {seeds}\n\n"
        f"Generate exactly {num_questions} questions for this {difficulty}-level {interview_type} interview. "
        "Questions must be SPECIFIC to this candidate's material and role — not generic. "
        "Increase depth as questions progress. "
        "Reply JSON: {\"role\": str, \"focus\": [str], \"questions\": [str]}"
    )
    try:
        data, resp = service.generate_json(prompt)
        qs = data.get("questions") or seeds
        return {"role": data.get("role", "Candidate"), "focus": data.get("focus", seeds[:2]),
                "questions": qs[:num_questions + 1], "provider": resp.provider, "fallback_active": resp.fallback_active}
    except Exception:
        random.shuffle(seeds)
        return {"role": "Candidate", "focus": seeds[:2], "questions": seeds[:num_questions],
                "provider": "offline", "fallback_active": False}


def next_question(history: list[dict], context: str, interview_type: str, difficulty: str,
                  profile_note: str = "") -> dict:
    interview_type = interview_type if interview_type in TYPES else "mixed"
    last = history[-1] if history else {}
    last_q = last.get("question", "")
    last_a = (last.get("answer") or "")[:2000]
    prev_fb = ""
    if len(history) >= 2:
        ev = (history[-2].get("evaluation") or {})
        if ev.get("main_issue"):
            prev_fb = f" Known weakness to probe: {ev['main_issue']}."
    type_hint = TYPE_FOLLOWUP_INSTRUCTIONS.get(interview_type, "")

    prompt = (
        f"You are conducting a {interview_type} interview ({difficulty}).\n"
        f"Type guidance: {type_hint}\n\n"
        f"Candidate context:\n{context[:4000]}\n\n"
        f"Last question: {last_q}\nLast answer: {last_a}\n\n"
        f"Candidate profile: {profile_note[:300]}.{prev_fb}\n\n"
        "Ask ONE adaptive follow-up that goes deeper, referencing their actual words. "
        "The question must be specific to the candidate's material/experience — not generic. "
        "Keep it under 30 words. Also give a brief bridge line (<=10 words). "
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
    """Live per-answer report. Type-specific evaluation. Audio-only
    metrics (articulation/pronunciation) are marked unavailable, never invented."""
    interview_type = interview_type if interview_type in TYPES else "mixed"
    sig = sa.analyze(answer)
    type_eval = TYPE_EVAL_INSTRUCTIONS.get(interview_type, TYPE_EVAL_INSTRUCTIONS["mixed"])

    prompt = (
        f"Evaluate this {interview_type} interview answer.\n"
        f"Evaluation criteria: {type_eval}\n\n"
        f"Q: {question}\nA: {answer[:2000]}\nSignals: {sig}\n\n"
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
        data["articulation"] = "unavailable"
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


def final_report(history: list[dict], role: str, jd_text: str = "",
                 interview_type: str = "") -> dict:
    scores = [h.get("evaluation", {}).get("score", 0) for h in history if h.get("evaluation")]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    best = max(history, key=lambda h: h.get("evaluation", {}).get("score", 0)) if history else {}
    worst = min(history, key=lambda h: h.get("evaluation", {}).get("score", 10)) if history else {}
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

    type_eval = TYPE_EVAL_INSTRUCTIONS.get(interview_type, TYPE_EVAL_INSTRUCTIONS["mixed"])

    prompt = (
        f"Write a final {interview_type} interview report for a {role} position.\n"
        f"Evaluation criteria: {type_eval}\n\n"
        f"Q&A:\n{str([(h.get('question'), (h.get('answer') or '')[:500]) for h in history])[:5000]}\n\n"
        f"JD excerpt: {jd_text[:1500]}\n\n"
        f"Measured aggregates: relevance {relevance_summary} {sentence_patterns} "
        f"Recurring issues: {recurring}.\n\n"
        "Reply JSON: {\"summary\": str, \"strengths\": [str,str], "
        "\"biggest_weakness\": str, \"communication\": str, \"technical\": str, "
        "\"role_alignment\": str, \"training\": [str,str], "
        "\"top_priority\": str (single most important improvement), "
        "\"next_practice\": str (one concrete next session)}."
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
            "recurring_problems": recurring,
            "relevance_summary": relevance_summary,
            "sentence_patterns": sentence_patterns,
            "pronunciation_note": pronunciation_note,
            "provider": getattr(resp, "provider", "offline")}
