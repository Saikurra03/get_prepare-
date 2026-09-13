"""Deterministic speech-signal analysis (no AI needed). AI adds coaching on top."""
from __future__ import annotations
import re

FILLERS = {"um", "uh", "like", "you know", "basically", "actually", "literally",
           "sort of", "kind of", "i mean", "well", "so", "right", "hmm"}
QUALIFIERS = {"maybe", "just", "very", "really", "quite", "somewhat", "perhaps",
              "probably", "a bit", "stuff", "things", "whatever"}

def analyze(transcript: str) -> dict:
    t = (transcript or "").strip()
    words = re.findall(r"[A-Za-z']+", t.lower())
    n = len(words)
    sentences = [s for s in re.split(r"[.!?]+", t) if s.strip()]
    long_sent = sum(1 for s in sentences if len(s.split()) > 25)
    filler_hits: dict[str, int] = {}
    for f in FILLERS:
        c = len(re.findall(r"\b" + re.escape(f) + r"\b", t.lower()))
        if c:
            filler_hits[f] = c
    qual = sum(len(re.findall(r"\b" + re.escape(q) + r"\b", t.lower())) for q in QUALIFIERS)
    # crude repetition: same word 3+ times
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    repeated = {w: c for w, c in freq.items() if c >= 4 and len(w) > 3}
    # time to main point: position of first concrete content word (heuristic)
    vague_openers = ("i think", "so basically", "well", "you know", "like")
    slow_start = any(t.lower().startswith(v) for v in vague_openers)
    return {
        "word_count": n,
        "sentence_count": len(sentences),
        "long_sentences": long_sent,
        "filler_counts": filler_hits,
        "filler_total": sum(filler_hits.values()),
        "qualifier_total": qual,
        "repeated_words": repeated,
        "slow_start": slow_start,
        "empty": n < 3,
    }

def top_issue(signals: dict) -> str:
    if signals.get("empty"):
        return "empty_speech"
    if signals.get("filler_total", 0) >= 4:
        return "fillers"
    if signals.get("long_sentences", 0) >= 2:
        return "long_sentences"
    if signals.get("slow_start"):
        return "weak_opening"
    if signals.get("qualifier_total", 0) >= 4:
        return "vague_language"
    if signals.get("repeated_words"):
        return "repetition"
    return "structure"
