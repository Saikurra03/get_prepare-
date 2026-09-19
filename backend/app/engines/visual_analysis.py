"""Visual analysis engine — processes visual events from the browser-side sampler
and generates visual communication coaching. Never sees raw video — only structured data."""
from __future__ import annotations


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
}


def analyze_visuals(visual_events: list[dict], question: str, answer: str,
                    interview_type: str, difficulty: str = "intermediate") -> dict:
    """Process visual events from the browser sampler and generate coaching.
    Returns: {observations: list, coaching: str, summary: dict, score_impact: float}"""
    if not visual_events:
        return {"observations": [], "coaching": "", "summary": {}, "score_impact": 0.0}

    difficulty = difficulty if difficulty in ("beginner", "intermediate", "advanced", "expert") else "intermediate"

    # Categorize events
    gaze_events = [e for e in visual_events if e.get("type") == "gaze_away"]
    posture_events = [e for e in visual_events if e.get("type") == "slouching"]
    movement_events = [e for e in visual_events if e.get("type") == "excessive_movement"]
    hands_events = [e for e in visual_events if e.get("type") == "hands_hidden"]
    shoulder_events = [e for e in visual_events if e.get("type") == "uneven_shoulders"]

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

    # Generate coaching — pick the highest-priority issue
    coaching = ""
    priority_order = ["gaze_away", "slouching", "excessive_movement", "hands_hidden", "uneven_shoulders"]
    for evt_type in priority_order:
        evt_count = sum(1 for o in observations if o["type"] == evt_type)
        if evt_count > 0:
            coaching = EVENT_COACHING.get(evt_type, {}).get(difficulty, "")
            if evt_count > 1:
                coaching = f"(Occurred {evt_count} times) {coaching}"
            break

    # Compute score impact (negative = penalty, max -1.5)
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
    score_impact = max(-1.5, score_impact)

    # Summary stats
    summary = {
        "gaze_away_count": len(gaze_events),
        "gaze_away_total_sec": round(total_gaze_duration),
        "slouch_count": len(posture_events),
        "slouch_total_sec": round(total_slouch_duration),
        "excessive_movement_count": len(movement_events),
        "hands_hidden_count": len(hands_events),
        "total_snapshots": len(visual_events),
        "events": visual_events,
    }

    return {
        "observations": observations,
        "coaching": coaching,
        "summary": summary,
        "score_impact": score_impact,
    }


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

    total_gaze = sum(e.get("duration", 0) for e in gaze_events)
    total_slouch = sum(e.get("duration", 0) for e in posture_events)

    patterns = []
    if len(gaze_events) >= 3:
        patterns.append("Frequent camera look-away across multiple answers")
    if len(posture_events) >= 3:
        patterns.append("Recurring posture slouching throughout the interview")
    if len(movement_events) >= 5:
        patterns.append("Consistent excessive head movement")

    strengths = []
    if len(gaze_events) == 0:
        strengths.append("Strong camera attention throughout")
    if len(posture_events) == 0:
        strengths.append("Consistent upright posture")
    if len(hands_events) == 0:
        strengths.append("Good hand visibility for gesture communication")

    # Determine highest priority
    priority = ""
    if gaze_events:
        priority = "Improve camera attention — look at the lens during key points"
    elif posture_events:
        priority = "Maintain upright posture throughout the interview"
    elif movement_events:
        priority = "Reduce head movement for a more composed presence"

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
            "rating": "good" if len(hands_events) <= 1 else "needs_improvement",
        },
        "patterns": patterns,
        "strengths": strengths,
        "priority": priority,
    }
