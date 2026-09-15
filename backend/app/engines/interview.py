"""Interview engine: plan generation, adaptive follow-ups, evaluation, report.
Each interview type has its own system prompt. Feedback adapts to difficulty level."""
from __future__ import annotations
import random
from backend.app.ai import service
from backend.app.engines import speech_analysis as sa

TYPES = ["hr", "technical", "project", "behavioral", "resume", "jd", "topic", "mixed", "custom"]
DIFFICULTIES = ["beginner", "intermediate", "advanced", "expert"]

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

# Difficulty-specific evaluation tone
DIFF_EVAL_TONE = {
    "beginner": (
        "This is a BEGINNER candidate. Be encouraging and supportive. "
        "Focus evaluation on: basic structure (did they answer the question?), "
        "effort and willingness to communicate, clarity of basic ideas. "
        "Score generously — a beginner who tries hard and communicates basic ideas deserves 5-7. "
        "Don't punish lack of depth or advanced technical detail. "
        "Main feedback should be about building confidence and basic structure."
    ),
    "intermediate": (
        "This is an INTERMEDIATE candidate. Balanced feedback. "
        "Evaluate: answer structure, relevance, specificity of examples, "
        "communication clarity, and basic technical correctness where applicable. "
        "Score fairly — reward good structure and specific examples, "
        "flag missing depth or vague language. Main feedback should help them level up."
    ),
    "advanced": (
        "This is an ADVANCED candidate. Push for excellence. "
        "Evaluate: depth of technical reasoning, specificity of outcomes and metrics, "
        "quality of trade-off analysis, clarity under pressure, "
        "ability to handle follow-up probing. "
        "Score严格 — vague or surface-level answers should score 4-6 even if structurally correct. "
        "Main feedback should target precision and depth."
    ),
    "expert": (
        "This is an EXPERT candidate. Ruthless, detailed critique. "
        "Evaluate: technical accuracy and nuance, evidence-backed claims, "
        "system-level thinking, edge case awareness, communication under scrutiny, "
        "ability to defend decisions against challenge. "
        "Score严格 — only truly excellent, well-structured, evidence-rich answers deserve 8+. "
        "Main feedback should focus on what separates good from great."
    ),
}

# Difficulty-specific coaching tone
DIFF_COACHING_TONE = {
    "beginner": (
        "You are coaching a BEGINNER. Be warm, patient, and encouraging. "
        "Focus on ONE simple improvement they can make. "
        "Don't overwhelm with corrections. Build their confidence. "
        "Use simple language. Total response under 120 words."
    ),
    "intermediate": (
        "You are coaching an INTERMEDIATE candidate. Be supportive but honest. "
        "Give one clear priority and one concrete way to improve. "
        "Balance encouragement with constructive feedback. "
        "Total response under 150 words."
    ),
    "advanced": (
        "You are coaching an ADVANCED candidate. Be direct and specific. "
        "Focus on what separates their answer from an excellent one. "
        "Push for precision, depth, and better evidence. "
        "Total response under 150 words."
    ),
    "expert": (
        "You are coaching an EXPERT candidate. Be precise and technical. "
        "Focus on nuance, edge cases, and what would make this answer exceptional. "
        "Don't waste time on basics. Challenge them to be better. "
        "Total response under 150 words."
    ),
}

# Difficulty-specific model answer length and style
DIFF_MODEL_STYLE = {
    "beginner": {
        "length": "80-120 words",
        "style": "simple, clear, natural interview speech. Use everyday language. "
                 "Sound like a real person talking, not a textbook. "
                 "Focus on getting the basics right: answer the question, be specific, show effort.",
    },
    "intermediate": {
        "length": "100-150 words",
        "style": "well-structured, confident interview speech. "
                 "Sound natural and conversational, like someone who has prepared but isn't reading a script. "
                 "Include one specific example or metric.",
    },
    "advanced": {
        "length": "120-180 words",
        "style": "detailed, precise, evidence-backed interview speech. "
                 "Sound like an experienced professional who knows their craft. "
                 "Include specific metrics, technical decisions, and trade-offs.",
    },
    "expert": {
        "length": "150-200 words",
        "style": "comprehensive, nuanced, authoritative interview speech. "
                 "Sound like a senior leader who can defend every claim. "
                 "Include metrics, edge cases, system-level thinking, and clear reasoning.",
    },
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


def generate_coaching(question: str, answer: str, evaluation: dict, interview_type: str,
                      difficulty: str = "intermediate") -> dict:
    """Generate supportive coaching feedback. Adapts tone and depth to difficulty level."""
    interview_type = interview_type if interview_type in TYPES else "mixed"
    difficulty = difficulty if difficulty in DIFFICULTIES else "intermediate"
    score = evaluation.get("score", 5)
    strengths = evaluation.get("good", [])
    main_issue = evaluation.get("main_issue", "")
    better = evaluation.get("better_examples", [])
    rel = evaluation.get("relevance", {})
    dims = evaluation.get("dimensions", {})
    retry_instruction = evaluation.get("retry_instruction", "")

    diff_tone = DIFF_COACHING_TONE.get(difficulty, DIFF_COACHING_TONE["intermediate"])

    prompt = (
        f"{diff_tone}\n\n"
        f"You are coaching after a {interview_type} interview answer ({difficulty} level).\n\n"
        f"Question: {question}\n"
        f"Candidate's answer: {answer[:1500]}\n\n"
        f"Evaluation:\n"
        f"- Score: {score}/10\n"
        f"- Strengths: {strengths}\n"
        f"- Main issue: {main_issue}\n"
        f"- Relevance: {rel.get('verdict', 'partially')} — {rel.get('note', '')}\n"
        f"- Dimensions: {dims}\n"
        f"- Better examples: {[b.get('text', '') for b in better[:2]]}\n"
        f"- Retry instruction: {retry_instruction}\n\n"
        "Write a coaching response with exactly these 5 parts:\n\n"
        "1. APPRECIATION: One genuine sentence about what the candidate did well, "
        "based on their actual answer. Be specific — reference something they actually said.\n\n"
        "2. PRIORITY: One sentence on the single most important thing to improve. "
        "Start with 'Priority:'\n\n"
        "3. SPECIFIC FEEDBACK: 1-2 sentences explaining the key strengths or problems found. "
        "Reference the actual answer content.\n\n"
        "4. IMPROVEMENT: A concrete better way to say it, based on what they actually said. "
        "If the answer was already strong, suggest a minor polish. "
        "Format: 'Try: ...' or 'Better: ...'\n\n"
        "5. NEXT_STEP: One encouraging sentence to keep them motivated for the next question.\n\n"
        "Reply JSON: {\"appreciation\": str, \"priority\": str, "
        "\"specific_feedback\": str, \"improvement\": str, \"next_step\": str}"
    )

    fallback_coaching = _offline_coaching(question, score, main_issue, strengths, better,
                                           retry_instruction, difficulty)

    try:
        data, resp = service.generate_json(prompt, system=diff_tone, max_tokens=500)
        return {
            "appreciation": data.get("appreciation", fallback_coaching["appreciation"]),
            "priority": data.get("priority", fallback_coaching["priority"]),
            "specific_feedback": data.get("specific_feedback", fallback_coaching["specific_feedback"]),
            "improvement": data.get("improvement", fallback_coaching["improvement"]),
            "next_step": data.get("next_step", fallback_coaching["next_step"]),
            "provider": resp.provider,
        }
    except Exception:
        return {**fallback_coaching, "provider": "offline"}


def _offline_coaching(question: str, score: float, main_issue: str,
                      strengths: list, better: list, retry_instruction: str,
                      difficulty: str = "intermediate") -> dict:
    """Fallback coaching when AI is unavailable — adapts to difficulty."""
    # Beginner: warm, simple, encouraging
    if difficulty == "beginner":
        appreciation = "Good effort — you answered the question"
        if strengths:
            appreciation += f" and showed {strengths[0].lower()}"
        appreciation += "."
        if score >= 7:
            appreciation = "Nice work — you communicated your idea clearly."
        elif score >= 5:
            appreciation = "You're on the right track — keep building on this."
        else:
            appreciation = "You gave it a try — that's what matters. Let's refine it."

        priority = f"Priority: {main_issue}." if main_issue else "Priority: try to structure your answer with a clear start and end."
        specific = f"Score: {score}/10."
        if strengths:
            specific += f" Good: {', '.join(strengths[:2])}."
        improvement = ""
        if better and better[0].get("text"):
            improvement = f"Try: {better[0]['text']}"
        elif retry_instruction:
            improvement = f"Better: {retry_instruction}"
        else:
            improvement = "Try: say your answer in 2 short sentences."
        next_step = "You're doing well — let's try the next question."

    # Expert: sharp, technical, demanding
    elif difficulty == "expert":
        appreciation = "Solid response"
        if strengths:
            appreciation += f" — {strengths[0].lower()}"
        appreciation += "."
        if score >= 8:
            appreciation = "Excellent answer — well-structured with strong evidence."
        elif score >= 6:
            appreciation = "Competent answer, but room for more depth and precision."
        else:
            appreciation = "Below expectations for this level — needs more rigor."

        priority = f"Priority: {main_issue}." if main_issue else "Priority: strengthen with specific evidence and edge case awareness."
        specific = f"Score: {score}/10."
        if strengths:
            specific += f" Strong: {', '.join(strengths[:2])}."
        improvement = ""
        if better and better[0].get("text"):
            improvement = f"Better: {better[0]['text']}"
        elif retry_instruction:
            improvement = f"Better: {retry_instruction}"
        else:
            improvement = "Try: add one specific metric or trade-off analysis."
        next_step = "Ready for the next challenge — push for excellence."

    # Intermediate and Advanced: balanced
    else:
        appreciation = "Good answer — you addressed the question"
        if strengths:
            appreciation += f" and showed strength in {strengths[0].lower()}"
        appreciation += "."
        if score >= 7:
            appreciation = "Strong answer — you communicated clearly and hit the key points."
        elif score >= 5:
            appreciation = "Solid attempt — you covered the main idea and showed some structure."
        else:
            appreciation = "You gave it a go — with some adjustments, this can become much stronger."

        priority = f"Priority: {main_issue}." if main_issue else "Priority: tighten your answer to lead with the main point."
        specific = f"Score: {score}/10."
        if strengths:
            specific += f" What worked: {', '.join(strengths[:2])}."
        improvement = ""
        if better and better[0].get("text"):
            improvement = f"Try: {better[0]['text']}"
        elif retry_instruction:
            improvement = f"Better: {retry_instruction}"
        else:
            improvement = "Try: restate your answer in 2 short sentences, starting with the result."
        next_step = "Ready for the next question — keep building on this."

    return {
        "appreciation": appreciation,
        "priority": priority,
        "specific_feedback": specific,
        "improvement": improvement,
        "next_step": next_step,
    }


def generate_model_answer(question: str, answer: str, interview_type: str, context: str = "",
                          difficulty: str = "intermediate") -> dict:
    """Generate a complete ideal answer. Adapts length and style to difficulty level.
    Answer must sound like natural interview speech — flowing, confident, human."""
    interview_type = interview_type if interview_type in TYPES else "mixed"
    difficulty = difficulty if difficulty in DIFFICULTIES else "intermediate"
    style = DIFF_MODEL_STYLE.get(difficulty, DIFF_MODEL_STYLE["intermediate"])

    type_hints = {
        "hr": "Focus on presence, clear self-presentation, and genuine motivation.",
        "technical": "Focus on correctness, clear explanation of technical concepts, and reasoning.",
        "project": "Focus on personal ownership, specific technical decisions, and measurable outcomes.",
        "behavioral": "Focus on STAR structure (Situation-Task-Action-Result) with concrete examples.",
        "resume": "Focus on specific projects and skills from the resume, with concrete examples.",
        "jd": "Focus on alignment with job description requirements and honest gap acknowledgment.",
        "topic": "Focus on deep understanding of the material with practical applications.",
        "mixed": "Balance clarity, specificity, and structure across all areas.",
        "custom": "Focus on the custom area with specific examples.",
    }
    hint = type_hints.get(interview_type, type_hints["mixed"])

    prompt = (
        f"Question: {question}\n"
        f"Candidate's attempt: {answer[:1000]}\n\n"
        f"Context: {context[:2000]}\n\n"
        f"Interview type: {interview_type} | Difficulty: {difficulty}\n"
        f"Guidelines: {hint}\n\n"
        f"Write a model answer ({style['length']}) that would score 8-9/10.\n"
        f"Style: {style['style']}\n\n"
        "CRITICAL: This must sound like a REAL PERSON talking in an interview. "
        "Not a definition, not a textbook, not a list. "
        "It should flow naturally — like someone thinking out loud with confidence. "
        "Use connecting phrases: 'So basically...', 'What I did was...', 'The key thing here is...'. "
        "Make it specific to this candidate's context. "
        "Reply JSON: {\"model_answer\": str}"
    )

    fallback = _offline_model_answer(question, interview_type, difficulty)

    try:
        data, resp = service.generate_json(prompt, system=MODEL_ANSWER_SYSTEM, max_tokens=600)
        ma = data.get("model_answer", "")
        if not ma or len(ma) < 30:
            return {**fallback, "provider": resp.provider}
        return {"model_answer": ma, "provider": resp.provider}
    except Exception:
        return {**fallback, "provider": "offline"}


MODEL_ANSWER_SYSTEM = (
    "You are an expert interview coach demonstrating an ideal answer. "
    "Write a complete, natural, confident response that would score 8-9/10. "
    "Use specific details from the candidate's context when available. "
    "Sound human and authentic — like a real person talking in an interview, "
    "not a definition or textbook entry. Use conversational connectors."
)


def _offline_model_answer(question: str, interview_type: str, difficulty: str = "intermediate") -> dict:
    """Fallback model answer when AI is unavailable — adapts to difficulty."""
    q_lower = question.lower()

    if difficulty == "beginner":
        if "yourself" in q_lower or "tell me about" in q_lower:
            return {"model_answer": (
                "So basically, I'm a software developer with about two years of experience. "
                "I mainly work with Python and JavaScript, building web apps. "
                "At my current job, I helped fix our payment system which was failing a lot — "
                "I added some retry logic and that cut the failures by about 40 percent. "
                "I enjoy solving problems like that, finding what's broken and making it work better."
            )}
        if "strength" in q_lower:
            return {"model_answer": (
                "I'd say my biggest strength is that I'm really good at figuring out what's wrong "
                "and fixing it step by step. Like when our checkout was broken, I didn't just guess — "
                "I looked at the logs, found the specific error, and wrote a test to make sure it wouldn't "
                "happen again. I think that patient, methodical approach helps me a lot."
            )}
        return {"model_answer": (
            "That's a good question. So what I'd say is, in my experience, the most important thing "
            "is to stay organized and communicate with your team. For example, when I was working on "
            "a project last month, I made sure to document everything I was doing so my teammate could "
            "pick up where I left off if needed. I think that kind of planning really helps."
        )}

    elif difficulty == "expert":
        if "yourself" in q_lower or "tell me about" in q_lower:
            return {"model_answer": (
                "Sure. So I've spent the last six years building distributed systems, mostly in fintech. "
                "The thread I keep coming back to is reliability engineering — designing systems that "
                "degrade gracefully instead of failing silently. At my last role, I led the architecture "
                "of a payment processing pipeline handling about two million transactions daily. "
                "We reduced mean time to recovery from forty-five minutes to under three by implementing "
                "circuit breakers and structured observability. What drives me is the intersection of "
                "technical depth and business impact — understanding not just how to build something, "
                "but why it matters for the people using it."
            )}
        if "challenge" in q_lower or "failure" in q_lower:
            return {"model_answer": (
                "Right, so there was this incident about eight months ago where our primary database "
                "started lagging during peak hours. I noticed the symptoms first — response times "
                "creeping up, connection pool exhaustion. I traced it to a missing index on a query "
                "that was doing a full table scan on a sixty-million-row table. But the interesting part "
                "wasn't the fix — it was the systemic issue. We had no query performance monitoring. "
                "So I designed a query latency alerting system, added slow query logging, and built "
                "a runbook. The key lesson: the fix is temporary, but the system you build around it "
                "is what prevents the next incident."
            )}
        return {"model_answer": (
            "That's an interesting question. From a system design perspective, I'd approach it "
            "by first defining the failure modes and then working backward to the architecture. "
            "For instance, if we're talking about a notification system, I'd consider at-least-once "
            "delivery semantics, idempotency keys for deduplication, and graceful degradation "
            "when downstream services are unavailable. The trade-off I'd highlight is between "
            "consistency and availability — you can guarantee delivery but accept latency, or you "
            "can prioritize speed and handle eventual consistency. The right choice depends on "
            "the business context, which is why I always start with the requirements before the architecture."
        )}

    # Intermediate and Advanced (default)
    if "yourself" in q_lower or "tell me about" in q_lower:
        return {"model_answer": (
            "I'm a software engineer with about three years of experience building web applications. "
            "Most of my work has been in Python and React, focusing on backend reliability. "
            "In my current role, I led the redesign of our checkout system — it was failing about "
            "twelve percent of the time, which was costing us real revenue. I implemented idempotent "
            "retries with proper error handling, and we got that down to under three percent. "
            "What I enjoy most is taking something that's broken and making it work reliably — "
            "finding the root cause, not just patching symptoms."
        )}
    if "strength" in q_lower:
        return {"model_answer": (
            "I'd say my biggest strength is debugging complex systems. I'm methodical about it — "
            "I start with the logs, look for patterns, write a failing test to reproduce the issue, "
            "then fix it. For example, we had this intermittent payment failure that only happened "
            "in production. I traced it to a race condition in the retry queue, wrote a test that "
            "reproduced it, and fixed it with proper locking. That approach — reproduce first, "
            "then fix — has saved me countless hours."
        )}
    if "challenge" in q_lower or "failure" in q_lower:
        return {"model_answer": (
            "We had a production outage last year where payments were silently failing. "
            "I took ownership — first I traced it to a missing error handler in the retry logic, "
            "then I wrote a fix with proper idempotency checks and deployed it within two hours. "
            "But the bigger lesson was afterward — I set up monitoring alerts so we'd catch similar "
            "issues before customers reported them. The key takeaway was: always add observability "
            "before you need it, not after."
        )}
    return {"model_answer": (
        f"For this question, a strong answer would start with context — "
        "what the situation was, what your role was. Then move to what you actually did, "
        "specifically. Not 'we did this' but 'I did this.' End with the result — "
        "ideally with a number or concrete outcome. That structure works at any level."
    )}


def evaluate_answer(question: str, answer: str, interview_type: str,
                    difficulty: str = "intermediate") -> dict:
    """Live per-answer report. Adapts evaluation strictness to difficulty level.
    Audio-only metrics are marked unavailable, never invented."""
    interview_type = interview_type if interview_type in TYPES else "mixed"
    difficulty = difficulty if difficulty in DIFFICULTIES else "intermediate"
    sig = sa.analyze(answer)
    type_eval = TYPE_EVAL_INSTRUCTIONS.get(interview_type, TYPE_EVAL_INSTRUCTIONS["mixed"])
    diff_tone = DIFF_EVAL_TONE.get(difficulty, DIFF_EVAL_TONE["intermediate"])

    prompt = (
        f"{diff_tone}\n\n"
        f"Evaluate this {interview_type} interview answer ({difficulty} level).\n"
        f"Type criteria: {type_eval}\n\n"
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
                 interview_type: str = "", difficulty: str = "intermediate") -> dict:
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
    diff_tone = DIFF_EVAL_TONE.get(difficulty, DIFF_EVAL_TONE["intermediate"])

    prompt = (
        f"{diff_tone}\n\n"
        f"Write a final {interview_type} interview report for a {role} position ({difficulty} level).\n"
        f"Type criteria: {type_eval}\n\n"
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
