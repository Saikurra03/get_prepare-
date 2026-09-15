"""Document upload: Uploaded -> Processing -> Analyzed -> Ready. Scoped by section."""
from __future__ import annotations
import time
import uuid
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from backend.app.documents import extractor, context_builder
from backend.app.session import manager as store

router = APIRouter(prefix="/api/documents", tags=["documents"])

_ACCEPT_PREFIXES = (
    "application/pdf", "application/vnd.openxmlformats", "application/msword",
    "application/vnd.ms-powerpoint", "text/", "application/json",
    "application/x-python", "application/x-javascript", "application/javascript",
    "application/xml", "image/svg",
)

@router.post("/upload")
async def upload(file: UploadFile = File(...), kind: str = Form("document"), section: str = Form("")):
    data = await file.read()
    if not data:
        return {"error": f"{file.filename} is empty", "code": "empty_file", "status": "failed"}
    if len(data) > 15 * 1024 * 1024:
        return {"error": f"{file.filename} too large (max 15MB)", "code": "too_large", "status": "failed"}
    ct = (file.content_type or "").lower()
    if ct and not any(ct.startswith(p) for p in _ACCEPT_PREFIXES):
        pass
    try:
        text = extractor.extract_text(file.filename or "upload.txt", data)
    except ValueError as exc:
        return {"error": str(exc), "code": "invalid_document", "status": "failed"}
    doc = {"id": uuid.uuid4().hex[:8], "filename": file.filename, "kind": kind,
           "section": section or "", "chars": len(text), "text": text[:20000],
           "status": "analyzed", "uploaded": time.time()}
    store.save_document(doc)
    sig = context_builder.extract_signals(
        jd_text=text if kind == "jd" else "",
        resume_text=text if kind == "resume" else "")
    return {"status": "ready", "doc_id": doc["id"], "filename": doc["filename"],
            "chars": doc["chars"], "signals": sig,
            "flow": ["uploaded", "processing", "analyzed", "ready"]}

@router.get("/list")
def list_docs(section: str = ""):
    docs = store.list_documents(section=section)
    return {"documents": [{k: d[k] for k in ("id", "filename", "kind", "chars", "status", "section") if k in d} for d in docs]}

class ClearIn(BaseModel):
    section: str = ""

@router.post("/clear")
def clear(inp: ClearIn = ClearIn()):
    store.clear_documents(section=inp.section)
    return {"status": "cleared"}

class RemoveIn(BaseModel):
    doc_id: str = ""

@router.post("/remove")
def remove(inp: RemoveIn):
    from backend.app.session.manager import _load, _save
    docs = _load("documents.json", [])
    kept = [d for d in docs if d["id"] != inp.doc_id]
    if len(kept) == len(docs):
        return {"error": "document not found", "code": "no_doc"}
    _save("documents.json", kept)
    return {"status": "removed", "doc_id": inp.doc_id}


class PasteIn(BaseModel):
    text: str
    kind: str = "document"
    filename: str = ""
    section: str = ""

@router.post("/paste")
def paste(inp: PasteIn):
    text = (inp.text or "").strip()
    if not text:
        return {"error": "empty text — nothing to save", "code": "empty_text", "status": "failed"}
    if len(text) > 200_000:
        text = text[:200_000] + "\n\n[TRUNCATED: text too large, first 200k chars kept]"
    kind = inp.kind if inp.kind in ("resume", "jd", "topic", "document") else "document"
    filename = inp.filename.strip() or f"pasted_{kind}.txt"
    doc = {"id": uuid.uuid4().hex[:8], "filename": filename, "kind": kind,
           "section": inp.section or "", "chars": len(text), "text": text[:20000],
           "status": "analyzed", "uploaded": time.time()}
    store.save_document(doc)
    sig = context_builder.extract_signals(
        jd_text=text if kind == "jd" else "",
        resume_text=text if kind == "resume" else "")
    return {"status": "ready", "doc_id": doc["id"], "filename": doc["filename"],
            "chars": doc["chars"], "signals": sig}
