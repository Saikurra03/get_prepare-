"""Build compact interview context from extracted docs (avoid sending huge docs every call)."""
from __future__ import annotations

def build_context(docs: list[dict], max_chars: int = 10000) -> str:
    """docs: [{kind, filename, text}]. Returns compacted context with per-doc caps.
    Each doc gets at least 1500 chars to ensure enough material for meaningful questions."""
    out: list[str] = []
    per = max(1500, max_chars // max(1, len(docs)))
    for d in docs:
        kind = d.get("kind", "document")
        text = (d.get("text") or "")[:per]
        out.append(f"[{kind.upper()}: {d.get('filename','')}]\n{text}")
    ctx = "\n\n".join(out)
    return ctx[:max_chars]

def extract_signals(jd_text: str = "", resume_text: str = "") -> dict:
    """Lightweight keyword signals so JD+resume comparison works offline."""
    import re
    def skills(t: str) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}", t)
        seen, res = set(), []
        for w in words:
            lw = w.lower()
            if len(res) >= 20:
                break
            if lw not in seen and (w[0].isupper() or "+" in w or "#" in w or len(w) > 5):
                seen.add(lw)
                res.append(w)
        return res
    jd_s, re_s = skills(jd_text), skills(resume_text)
    overlap = [s for s in re_s if s.lower() in jd_text.lower()][:10]
    gaps = [s for s in jd_s if s.lower() not in resume_text.lower()][:10]
    return {"jd_skills": jd_s[:15], "resume_skills": re_s[:15], "overlap": overlap, "gaps": gaps}
