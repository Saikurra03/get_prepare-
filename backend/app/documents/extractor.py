"""Document text extraction: PDF / DOCX / TXT with clear errors for corrupt/unsupported/large files."""
from __future__ import annotations
import io

MAX_CHARS = 200_000

def extract_text(filename: str, data: bytes) -> str:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext == "pdf":
        return _pdf(data, filename)
    if ext == "docx":
        return _docx(data, filename)
    if ext in ("txt", "md"):
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError(f"Could not read {filename}: {exc}") from exc
        return _cap(text, filename)
    raise ValueError(f"Unsupported document type '.{ext}' for {filename}. Use PDF, DOCX, or TXT.")

def _cap(text: str, filename: str) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError(f"{filename} appears empty or is a scanned image PDF without text.")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[TRUNCATED: document too large, first 200k chars kept]"
    return text

def _pdf(data: bytes, filename: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise ValueError(f"PDF support unavailable: {exc}") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = [(p.extract_text() or "") for p in reader.pages]
    except Exception as exc:
        raise ValueError(f"Corrupted or unreadable PDF {filename}: {exc}") from exc
    return _cap("\n".join(parts), filename)

def _docx(data: bytes, filename: str) -> str:
    try:
        import docx
    except Exception as exc:
        raise ValueError(f"DOCX support unavailable: {exc}") from exc
    try:
        doc = docx.Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
    except Exception as exc:
        raise ValueError(f"Corrupted or unreadable DOCX {filename}: {exc}") from exc
    return _cap("\n".join(parts), filename)

def chunk(text: str, size: int = 4000, overlap: int = 400) -> list[str]:
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks
