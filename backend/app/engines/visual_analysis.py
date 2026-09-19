"""Visual analysis engine — processes visual events from the browser-side sampler
and generates visual communication coaching. Never sees raw video — only structured data.
Phase 7: gesture analysis, content-aware coaching, long-term pattern tracking."""
from __future__ import annotations
import re


# Visual event types and their coaching implications
EVENT_COACHING = {
    "gaze_away": {
        "beginner": "Try to look at the camera more — it helps you connect with the interviewer.",
        "intermediate": "Maintain camera attention, especially during key points.",
        "advanced": "Camera attention dropped during important sections — keep eye contact with the lens.",
        "expert": "Significant gaze deviation detected — in a live interview this would reduce engagement.",
    },
    "slouching": {
        "beginner": "Try sitting a bit more upright — it helps you sound more confident.",
        "intermediate": "Watch your posture — sitting upright projects presence.",
        "advanced": "Posture degraded during the answer — maintain an upright position throughout.",
        "expert": "Posture inconsistency detected — stability projects authority.",
    },
    "excessive_movement": {
        "beginner": "Try to stay a bit more still — it helps you look composed.",
        "intermediate": "Reduce head movement — it can distract from your message.",
        "advanced": "Excessive movement detected — minimize fidgeting for stronger presence.",
        "expert": "Movement patterns suggest restlessness — practice stable positioning.",
    },
    "hands_hidden": {
        "beginner": "Try to keep your hands visible — it makes you look more open.",
        "intermediate": "Keep hands in frame for natural gesture communication.",
        "advanced": "Hands were not visible for an extended period — use gestures to support your points.",
        "expert": "Limited gesture visibility — hands should be visible for effective non-verbal communication.",
    },
    "uneven_shoulders": {
        "beginner": "Try to sit straight — it helps you look more relaxed.",
        "intermediate": "Keep shoulders level for a more balanced appearance.",
        "advanced": "Shoulder alignment was uneven — adjust your seating position.",
        "expert": "Postural asymmetry detected — practice balanced positioning.",
    },
    "torso_lean": {
        "beginner": "Try to stay centered in the camera — it helps you look stable.",
        "intermediate": "Avoid leaning to one side — centered posture looks more professional.",
        "advanced": "Torso lean detected — maintain centered alignment for a composed presence.",
        "expert": "Asymmetric body positioning — practice centered stance for executive presence.",
    },
    "shoulder_rotation": {
        "beginner": "Try to face the camera squarely with both shoulders.",
        "intermediate": "Maintain a forward-facing position to appear engaged.",
        "advanced": "Shoulder rotation detected — face the camera directly.",
        "expert": "Body rotation reduces direct engagement — maintain forward-facing alignment.",
    },
}

# Content-aware coaching: map answer keywords to visual suggestions
CONTENT_KEYWORDS = {
    "first": "Consider using your index finger to visually emphasize 'first' — it makes your point clearer.",
    "second": "When listing items like 'second', use two fingers to reinforce your point visually.",
    "third": "For 'third', show three fingers to help the listener follow your list.",
    "example": "When saying 'for example', an open palm gesture can introduce the example naturally.",
    "important": "When saying 'the important thing', a pointing gesture adds emphasis.",
    "however": "When saying 'however', a slight hand transition helps signal the contrast.",
    "big picture": "When discussing 'big picture', spreading hands apart visually reinforces the concept.",
    "team": "When talking about 'team', gesturing outward shows inclusiveness.",
    "problem": "When stating a 'problem', bringing hands together conveys focus on the issue.",
    "solution": "When offering a 'solution', an open palm forward gesture adds confidence.",
    "growth": "When discussing 'growth', an upward hand movement reinforces the positive trajectory.",
    "process": "When explaining a 'process', using sequential finger counting helps the listener follow along.",
    "list": "When presenting a 'list', numbered finger gestures help the audience track each item.",
    "compare": "When comparing two things, using both hands to represent each side is effective.",
    "time": "When mentioning timeframes, pointing to an imaginary timeline adds clarity.",
    "risk": "When discussing 'risk', a cautious hand gesture shows awareness and seriousness.",
    "opportunity": "When discussing 'opportunity', open palms convey optimism and openness.",
    "strength": "When highlighting 'strength', a firm hand gesture adds conviction.",
    "weakness": "When addressing 'weakness', a measured hand position shows self-awareness.",
    "goal": "When stating a 'goal', pointing forward shows direction and intent.",
    "experience": "When sharing 'experience', an open palm toward yourself adds authenticity.",
    "skill": "When mentioning 'skill', a confident gesture reinforces your capability.",
    "learn": "When discussing 'learning', a curious hand position shows openness to growth.",
    "lead": "When talking about 'leadership', a forward gesture shows initiative.",
    "collaborate": "When saying 'collaborate', bringing hands together symbolizes partnership.",
}


def analyze_visuals(visual_events: list[dict], question: str, answer: str,
                    interview_type: str, difficulty: str = "intermediate") -> dict:
    """Process visual events from the browser sampler and generate coaching.
    Returns: {observations, coaching, content_coaching, summary, score_impact, gesture_analysis}"""
    if not visual_events:
        return {"observations": [], "coaching": "", "content_coaching": "",
                "summary": {}, "score_impact": 0.0, "gesture_analysis": {}}

    difficulty = difficulty if difficulty in ("beginner", "intermediate", "advanced", "expert") else "intermediate"

    # Categorize events
    gaze_events = [e for e in visual_events if e.get("type") == "gaze_away"]
    posture_events = [e for e in visual_events if e.get("type") == "slouching"]
    movement_events = [e for e in visual_events if e.get("type") == "excessive_movement"]
    hands_events = [e for e in visual_events if e.get("type") == "hands_hidden"]
    shoulder_events = [e for e in visual_events if e.get("type") == "uneven_shoulders"]
    lean_events = [e for e in visual_events if e.get("type") == "torso_lean"]
    rotation_events = [e for e in visual_events if e.get("type") == "shoulder_rotation"]
    gesture_events = [e for e in visual_events if e.get("type") == "gesture"]
    hands_together_events = [e for e in visual_events if e.get("type") == "hands_together"]

    # Build observations list
    observations = []
    total_gaze_duration = 0
    total_slouch_duration = 0

    for e in gaze_events:
        dur = e.get("duration", 0)
        total_gaze_duration += dur
        observations.append({
            "type": "gaze_away",
            "detail": e.get("detail", "Looked away from camera"),
            "severity": "high" if dur > 5 else "medium" if dur > 2 else "low",
        })

    for e in posture_events:
        dur = e.get("duration", 0)
        total_slouch_duration += dur
        observations.append({
            "type": "slouching",
            "detail": e.get("detail", "Posture slouched"),
            "severity": "high" if dur > 10 else "medium" if dur > 5 else "low",
        })

    for e in movement_events:
        observations.append({
            "type": "excessive_movement",
            "detail": e.get("detail", "Excessive head movement"),
            "severity": "medium",
        })

    for e in hands_events:
        observations.append({
            "type": "hands_hidden",
            "detail": e.get("detail", "Hands not visible"),
            "severity": "low",
        })

    for e in shoulder_events:
        observations.append({
            "type": "uneven_shoulders",
            "detail": e.get("detail", "Shoulders uneven"),
            "severity": "low",
        })

    for e in lean_events:
        observations.append({
            "type": "torso_lean",
            "detail": e.get("detail", "Torso leaning"),
            "severity": "medium",
        })

    for e in rotation_events:
        observations.append({
            "type": "shoulder_rotation",
            "detail": e.get("detail", "Shoulder rotation"),
            "severity": "low",
        })

    # Gesture analysis
    gesture_analysis = _analyze_gestures(gesture_events, difficulty)

    # Generate primary coaching — pick the highest-priority issue
    coaching = ""
    priority_order = ["gaze_away", "slouching", "excessive_movement", "torso_lean",
                      "hands_hidden", "uneven_shoulders", "shoulder_rotation"]
    for evt_type in priority_order:
        evt_count = sum(1 for o in observations if o["type"] == evt_type)
        if evt_count > 0:
            coaching = EVENT_COACHING.get(evt_type, {}).get(difficulty, "")
            if evt_count > 1:
                coaching = f"(Occurred {evt_count} times) {coaching}"
            break

    # Content-aware coaching: analyze answer for keywords and suggest matching gestures
    content_coaching = _content_aware_coaching(answer, gesture_events, difficulty)

    # Compute score impact (negative = penalty, max -2.0)
    score_impact = 0.0
    if total_gaze_duration > 10:
        score_impact -= 0.5
    elif total_gaze_duration > 5:
        score_impact -= 0.3
    if total_slouch_duration > 10:
        score_impact -= 0.4
    elif total_slouch_duration > 5:
        score_impact -= 0.2
    if len(movement_events) > 3:
        score_impact -= 0.3
    if len(hands_events) > 2:
        score_impact -= 0.1
    if len(lean_events) > 2:
        score_impact -= 0.2
    if len(rotation_events) > 2:
        score_impact -= 0.1
    # Positive: good gesture variety
    if gesture_analysis.get("variety_score", 0) > 0.6:
        score_impact += 0.2
    score_impact = max(-2.0, min(1.0, score_impact))

    # Summary stats
    summary = {
        "gaze_away_count": len(gaze_events),
        "gaze_away_total_sec": round(total_gaze_duration),
        "slouch_count": len(posture_events),
        "slouch_total_sec": round(total_slouch_duration),
        "excessive_movement_count": len(movement_events),
        "hands_hidden_count": len(hands_events),
        "torso_lean_count": len(lean_events),
        "shoulder_rotation_count": len(rotation_events),
        "gesture_count": len(gesture_events),
        "hands_together_count": len(hands_together_events),
        "total_snapshots": len(visual_events),
        "events": visual_events,
    }

    return {
        "observations": observations,
        "coaching": coaching,
        "content_coaching": content_coaching,
        "summary": summary,
        "score_impact": score_impact,
        "gesture_analysis": gesture_analysis,
    }


def _analyze_gestures(gesture_events: list[dict], difficulty: str) -> dict:
    """Analyze gesture patterns across the answer."""
    if not gesture_events:
        return {"variety_score": 0.0, " dominant": None, "breakdown": {},
                "coaching": "Try incorporating natural hand gestures to support your points."}

    breakdown = {}
    for e in gesture_events:
        g = e.get("gesture", "unknown")
        breakdown[g] = breakdown.get(g, 0) + 1

    total = len(gesture_events)
    unique_types = len(breakdown)
    variety_score = min(1.0, unique_types / 4.0)  # 4+ unique gestures = max variety

    dominant = max(breakdown, key=breakdown.get) if breakdown else None

    coaching = ""
    if variety_score < 0.25:
        coaching = {
            "beginner": "Try adding more varied hand gestures — they make you look more expressive.",
            "intermediate": "Your gesture variety is low — try using different hand movements to emphasize points.",
            "advanced": "Limited gesture diversity detected — varied hand movements enhance communication.",
            "expert": "Gesture repertoire is narrow — practice a wider range of natural hand movements.",
        }.get(difficulty, "")
    elif dominant in ("fist", "thumbs_down"):
        coaching = {
            "beginner": "Consider using more open hand gestures — they look more approachable.",
            "intermediate": "Open palm gestures are more engaging than closed fists in interviews.",
            "advanced": "Closed hand gestures detected — open palms project confidence and openness.",
            "expert": "Dominant closed gestures reduce perceived openness — practice open-hand communication.",
        }.get(difficulty, "")

    return {
        "variety_score": round(variety_score, 2),
        "dominant": dominant,
        "breakdown": breakdown,
        "total": total,
        "coaching": coaching,
    }


def _content_aware_coaching(answer: str, gesture_events: list[dict], difficulty: str) -> str:
    """Analyze answer content and suggest gestures that would match the words being said."""
    if not answer or len(answer) < 20:
        return ""

    answer_lower = answer.lower()
    suggestions = []

    # Check which keywords appear in the answer
    for keyword, suggestion in CONTENT_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', answer_lower):
            suggestions.append(suggestion)

    # Check if gestures were actually used during the answer
    gesture_types = set(e.get("gesture", "") for e in gesture_events)
    has_gestures = bool(gesture_types and gesture_types != {"neutral"})

    # Filter: only suggest if gestures were sparse but content calls for them
    if not has_gestures and suggestions:
        # Pick top 2 most relevant suggestions
        selected = suggestions[:2]
        intro = {
            "beginner": "Your answer mentions concepts that work well with hand gestures:",
            "intermediate": "Consider adding gestures to match your content:",
            "advanced": "Content-gesture alignment opportunity:",
            "expert": "Non-verbal content reinforcement available:",
        }.get(difficulty, "")
        return f"{intro} " + " ".join(selected)
    elif has_gestures and suggestions:
        # Good: they're using gestures with content
        return ""

    return ""


def visual_summary_for_report(all_visual_events: list[dict], difficulty: str = "intermediate") -> dict:
    """Aggregate visual observations across all answers for the final report."""
    if not all_visual_events:
        return {}

    all_events = []
    for ve in all_visual_events:
        all_events.extend(ve.get("events", []))

    if not all_events:
        return {}

    gaze_events = [e for e in all_events if e.get("type") == "gaze_away"]
    posture_events = [e for e in all_events if e.get("type") == "slouching"]
    movement_events = [e for e in all_events if e.get("type") == "excessive_movement"]
    hands_events = [e for e in all_events if e.get("type") == "hands_hidden"]
    gesture_events = [e for e in all_events if e.get("type") == "gesture"]
    lean_events = [e for e in all_events if e.get("type") == "torso_lean"]
    rotation_events = [e for e in all_events if e.get("type") == "shoulder_rotation"]

    total_gaze = sum(e.get("duration", 0) for e in gaze_events)
    total_slouch = sum(e.get("duration", 0) for e in posture_events)

    # Gesture breakdown across entire interview
    gesture_breakdown = {}
    for e in gesture_events:
        g = e.get("gesture", "unknown")
        gesture_breakdown[g] = gesture_breakdown.get(g, 0) + 1

    patterns = []
    if len(gaze_events) >= 3:
        patterns.append("Frequent camera look-away across multiple answers")
    if len(posture_events) >= 3:
        patterns.append("Recurring posture slouching throughout the interview")
    if len(movement_events) >= 5:
        patterns.append("Consistent excessive head movement")
    if len(lean_events) >= 3:
        patterns.append("Repeated torso leaning to one side")
    if len(gesture_events) < 3:
        patterns.append("Limited use of hand gestures for emphasis")

    strengths = []
    if len(gaze_events) == 0:
        strengths.append("Strong camera attention throughout")
    if len(posture_events) == 0:
        strengths.append("Consistent upright posture")
    if len(hands_events) == 0:
        strengths.append("Good hand visibility for gesture communication")
    if len(gesture_events) >= 8:
        strengths.append("Good variety of hand gestures used")
    if len(lean_events) == 0 and len(rotation_events) == 0:
        strengths.append("Stable, centered body positioning")

    # Determine highest priority
    priority = ""
    if gaze_events:
        priority = "Improve camera attention — look at the lens during key points"
    elif posture_events:
        priority = "Maintain upright posture throughout the interview"
    elif movement_events:
        priority = "Reduce head movement for a more composed presence"
    elif lean_events:
        priority = "Stay centered in the camera frame"
    elif len(gesture_events) < 3:
        priority = "Incorporate more hand gestures to support your verbal points"

    return {
        "camera_attention": {
            "gaze_away_count": len(gaze_events),
            "gaze_away_total_sec": round(total_gaze),
            "rating": "good" if len(gaze_events) <= 1 else "needs_improvement" if len(gaze_events) <= 3 else "poor",
        },
        "posture": {
            "slouch_count": len(posture_events),
            "slouch_total_sec": round(total_slouch),
            "rating": "good" if len(posture_events) <= 1 else "needs_improvement" if len(posture_events) <= 3 else "poor",
        },
        "movement": {
            "excessive_count": len(movement_events),
            "rating": "good" if len(movement_events) <= 2 else "needs_improvement",
        },
        "gestures": {
            "hands_hidden_count": len(hands_events),
            "gesture_count": len(gesture_events),
            "gesture_breakdown": gesture_breakdown,
            "rating": "good" if len(hands_events) <= 1 and len(gesture_events) >= 3 else "needs_improvement",
        },
        "body_alignment": {
            "torso_lean_count": len(lean_events),
            "shoulder_rotation_count": len(rotation_events),
            "rating": "good" if len(lean_events) <= 1 and len(rotation_events) <= 1 else "needs_improvement",
        },
        "patterns": patterns,
        "strengths": strengths,
        "priority": priority,
    }
