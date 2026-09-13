"""Interruption decision: IMPACT x FREQUENCY x CONTEXT. Default = don't interrupt."""
from __future__ import annotations

def should_interrupt(signals: dict, scenario: str, history: list[dict] | None = None) -> dict:
    history = history or []
    filler = signals.get("filler_total", 0)
    words = signals.get("word_count", 0)
    long_sent = signals.get("long_sentences", 0)
    # impact scores
    impact = 0
    reasons: list[str] = []
    if words > 180 and (long_sent >= 2 or filler >= 5):
        impact += 3
        reasons.append("rambling: long answer losing main point")
    if filler >= 6:
        impact += 2
        reasons.append("repeated distracting fillers")
    if signals.get("empty"):
        impact += 1
        reasons.append("empty speech")
    # frequency: same issue 2+ times in history
    freq_bonus = 0
    if history:
        last_issues = [h.get("issue") for h in history[-3:]]
        if last_issues and len(set(last_issues)) == 1:
            freq_bonus = 1
            reasons.append("recurring pattern")
    # context: practice/retry scenarios tolerate more interruption
    context_allow = scenario in ("practice", "retry", "presentation", "interview")
    score = impact + freq_bonus
    interrupt = (score >= 3 and context_allow) or score >= 4
    return {"interrupt": interrupt, "score": score,
            "reasons": reasons or ["no meaningful interruption value — collect for later"]}
