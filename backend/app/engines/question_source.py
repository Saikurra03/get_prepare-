"""User-supplied question lists for mock interviews.

The user uploads or pastes their own questions. The AI NEVER invents,
rewrites, or reorders questions in this mode — it only evaluates answers.
Parsing normalizes common list formats (numbering, bullets, JSON, CSV).
"""
from __future__ import annotations
import json
import re
import random

# Strip common list prefixes: "1.", "1)", "Q1.", "-", "*", "•", "a)"
# Separator is REQUIRED (so "Question 3 of 5" stays intact) and a single
# letter must not be followed by a letter (so "e.g. ..." is never mangled).
_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"(?:Q|Question)\s*\d{1,3}\s*[.):\-]\s*|"      # Q1. / Question 2:
    r"\d{1,3}\s*[.):\-]\s*|"                        # 1. / 2) / 3-
    r"[a-zA-Z][.):](?![a-zA-Z])\s*|"                # a) / b. (not e.g.)
    r"[-*•–—]+\s*"                                  # bullets
    r")",
    re.IGNORECASE,
)


def _clean_line(line: str) -> str:
    line = line.replace("\u200b", "").strip()
    for _ in range(2):  # allow e.g. "- 1. Question" (bullet + numbering)
        new = _PREFIX_RE.sub("", line, count=1)
        if new == line:
            break
        line = new
    return re.sub(r"\s+", " ", line).strip()


def _from_json(text: str) -> list[str] | None:
    """Accept JSON arrays of strings or of objects with a question field."""
    try:
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, (list, dict)):
        return None
    items = data if isinstance(data, list) else data.get("questions", [])
    out: list[str] = []
    for it in items:
        if isinstance(it, str):
            out.append(_clean_line(it))
        elif isinstance(it, dict):
            q = it.get("q") or it.get("question") or it.get("text") or ""
            out.append(_clean_line(str(q)))
    return out


def _from_csv(text: str) -> list[str]:
    """CSV: first column per row (question), extra columns are ignored."""
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        first = line.split(",")[0]
        out.append(_clean_line(first))
    return out


def parse_questions(text: str, source: str = "") -> list[str]:
    """Parse uploaded/pasted questions into a clean ordered list.

    - .json source (or text starting with '[' / '{'): JSON list handling.
    - .csv source: first column per row.
    - otherwise: one question per line, numbering/bullets stripped.
    Blank lines drop out; exact duplicates keep only their first occurrence.
    No limit on the number of questions.
    """
    if not text or not text.strip():
        return []
    text = text.lstrip("\ufeff")

    src = (source or "").lower()
    if src.endswith(".json") or text.lstrip()[:1] in "[{":
        parsed = _from_json(text.strip())
        if parsed is not None:
            items = parsed
        else:
            items = [_clean_line(l) for l in text.splitlines()]
    elif src.endswith(".csv"):
        items = _from_csv(text)
    else:
        items = [_clean_line(l) for l in text.splitlines()]

    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or len(item) < 4:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def select_questions(questions: list[str], count: int, order: str = "sequential") -> list[str]:
    """Apply the user's count + order controls. Never invents or rewrites.

    order: "sequential" keeps list order; "random" shuffles a copy first.
    count <= 0 or larger than the list means "use every question".
    """
    items = list(questions)
    if (order or "sequential").lower() == "random":
        random.shuffle(items)
    if count and count > 0:
        items = items[:count]
    return items
