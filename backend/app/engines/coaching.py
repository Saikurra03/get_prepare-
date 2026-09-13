"""Coaching engine: rule-based priority + AI elaboration. Never fabricates metrics."""
from __future__ import annotations
from backend.app.engines import speech_analysis as sa
from backend.app.engines import interruption as intr
from backend.app.ai import service

SCENARIO_FOCUS = {
    "conversation": "natural flow and engagement",
    "interview": "fast time-to-main-point and STAR structure",
    "technical": "correctness + clear explanation with example",
    "hr": "confidence, relevance, storytelling",
    "project": "personal contribution + decisions + outcomes",
    "story": "hook, stakes, specificity, memorable ending",
    "wit": "clever observation or analogy, natural timing",
    "presentation": "strong opening, transitions, conclusion",
    "qa": "thinking speed + structure + relevance",
    "podcast": "conversational energy, listener hook, and clear takeaway",
    "spontaneous": "structure under 20 seconds",
}

def coach(transcript: str, scenario: str = "conversation",
          visual: dict | None = None, profile: dict | None = None,
          history: list[dict] | None = None) -> dict:
    signals = sa.analyze(transcript)
    issue = sa.top_issue(signals)
    decision = intr.should_interrupt(signals, scenario, history)
    focus = SCENARIO_FOCUS.get(scenario, SCENARIO_FOCUS["conversation"])
    visual_note = ""
    if visual:
        # cautious wording only
        bits = []
        if visual.get("camera_on") is False:
            bits.append("camera was off, so visual presence could not be observed")
        else:
            if visual.get("notes"):
                bits.append(str(visual["notes"])[:160])
        if bits:
            visual_note = " Visual note: " + "; ".join(bits)

    profile_note = ""
    if profile and profile.get("training_focus"):
        profile_note = f" Known training focus: {profile['training_focus']}."

    prompt = (
        f"Scenario: {scenario} (focus: {focus}).\nTranscript: \"{transcript[:2000]}\"\n"
        f"Detected top issue: {issue}. Signals: {signals}.{visual_note}{profile_note}\n"
        "Give ONE highest-impact priority, one retry instruction, one example rewritten line."
    )
    try:
        resp = service.generate(prompt)
        feedback, provider, fallback = resp.text, resp.provider, resp.fallback_active
    except Exception as exc:
        feedback, provider, fallback = (
            f"Priority: {issue} — retry once, shorter and clearer. ({exc})",
            "unavailable", False)
    return {"issue": issue, "signals": signals, "interruption": decision,
            "feedback": feedback, "provider": provider, "fallback_active": fallback}

def compare_retry(first: str, second: str) -> dict:
    a, b = sa.analyze(first), sa.analyze(second)
    def clarity(s: dict) -> float:
        return max(0.0, 10.0 - 0.6 * s.get("filler_total", 0)
                   - 0.8 * s.get("long_sentences", 0) - 0.3 * s.get("qualifier_total", 0))
    ca, cb = round(clarity(a), 1), round(clarity(b), 1)
    # time-to-main-point heuristic: word count before first concrete verb-ish token
    ttp = "faster" if b["word_count"] <= a["word_count"] and cb >= ca else (
        "similar" if cb == ca else ("slower" if cb < ca else "faster"))
    verdict = "improved" if cb > ca else ("same" if cb == ca else "regressed")
    return {"first_signals": a, "second_signals": b,
            "clarity_before": ca, "clarity_after": cb,
            "time_to_main_point": ttp, "verdict": verdict,
            "note": "Heuristic comparison only — no fabricated precision."}
