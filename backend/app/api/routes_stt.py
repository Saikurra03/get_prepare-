"""STT routes: transcribe audio using server-side Whisper."""
from __future__ import annotations
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/stt", tags=["stt"])


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float
    provider: str
    model: str
    confidence: float | None = None
    fallback_used: bool = False


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("en"),
    request_id: str | None = Form(None),
):
    """Transcribe uploaded audio file using server-side Whisper.
    
    Returns transcription with metadata. Falls back gracefully if STT unavailable.
    """
    # Validate file
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be audio/*")
    
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    # Size limit: 25MB (Whisper API limit)
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")
    
    try:
        from backend.app.engines import stt as stt_engine
        result = stt_engine.transcribe_audio(audio_bytes, language)
        
        return TranscribeResponse(
            text=result.text,
            language=result.language,
            duration=result.duration,
            provider=result.provider,
            model=result.model,
            confidence=result.confidence,
            fallback_used=result.fallback_used,
        )
    except RuntimeError as exc:
        # STT unavailable - return error for client to fall back to browser STT
        raise HTTPException(
            status_code=503,
            detail=f"Server STT unavailable: {exc}. Use browser Web Speech API fallback."
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"STT error: {exc}")


@router.get("/health")
def stt_health():
    """Check STT provider availability."""
    from backend.app.engines import stt as stt_engine
    provider = stt_engine.STTProvider()
    return {
        "available": provider.is_configured(),
        "model": provider._model,
        "provider": "groq",
    }