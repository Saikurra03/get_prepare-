"""Server-side Speech-to-Text using Groq Whisper (whisper-large-v3-turbo).

Primary STT provider with browser Web Speech API as fallback.
"""
from __future__ import annotations
import os
import logging
from dataclasses import dataclass
from backend.app.config import settings

log = logging.getLogger("beready.stt")

# Groq Whisper models available
WHISPER_MODELS = {
    "whisper-large-v3": "whisper-large-v3",
    "whisper-large-v3-turbo": "whisper-large-v3-turbo",
    "distil-whisper-large-v3-en": "distil-whisper-large-v3-en",
}

DEFAULT_MODEL = "whisper-large-v3-turbo"


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration: float
    provider: str
    model: str
    confidence: float | None = None
    fallback_used: bool = False


class STTProvider:
    """Groq Whisper STT provider."""

    def __init__(self):
        self._model = os.getenv("STT_MODEL", DEFAULT_MODEL)
        if self._model not in WHISPER_MODELS:
            log.warning("Unknown STT model %s, falling back to %s", self._model, DEFAULT_MODEL)
            self._model = DEFAULT_MODEL

    def is_configured(self) -> bool:
        """Check if Groq API key is available for STT."""
        # Reuse Groq keys from key_manager
        from backend.app.ai.key_manager import key_manager
        return key_manager.has_keys("groq")

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> TranscriptionResult:
        """Transcribe audio bytes using Groq Whisper."""
        if not self.is_configured():
            raise RuntimeError("No Groq API key configured for STT")

        try:
            from groq import Groq
        except ImportError:
            raise RuntimeError("groq SDK not installed")

        # Get available Groq key (reuse key rotation logic)
        from backend.app.ai.key_manager import key_manager
        slots = key_manager.available_keys("groq")
        if not slots:
            raise RuntimeError("All Groq keys on cooldown")

        # Try each available key
        last_error = None
        for slot in slots:
            try:
                client = Groq(api_key=slot.key, timeout=settings.timeout_seconds)
                
                # Create file-like object for audio
                import io
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "audio.webm"
                
                # Transcribe with Whisper
                response = client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                    language=language if language != "auto" else None,
                    response_format="verbose_json",
                    temperature=0.0,
                )
                
                # Extract result
                text = getattr(response, "text", "") or ""
                detected_language = getattr(response, "language", language)
                duration = getattr(response, "duration", 0.0)
                
                # Whisper doesn't return confidence directly; estimate from segments if available
                confidence = None
                segments = getattr(response, "segments", None)
                if segments:
                    confs = [getattr(s, "avg_logprob", None) for s in segments]
                    confs = [c for c in confs if c is not None]
                    if confs:
                        # Convert logprob to 0-1 confidence
                        import math
                        avg_logprob = sum(confs) / len(confs)
                        confidence = max(0.0, min(1.0, (avg_logprob + 1.0) / 1.0))
                
                key_manager.mark_success(slot)
                log.info("STT transcription successful: %d chars, lang=%s", len(text), detected_language)
                
                return TranscriptionResult(
                    text=text.strip(),
                    language=detected_language,
                    duration=duration,
                    provider="groq",
                    model=self._model,
                    confidence=confidence,
                )
                
            except Exception as exc:
                last_error = exc
                key_manager.mark_failure(slot, exc)
                log.warning("STT failed with %s: %s", slot.label, exc)
                continue
        
        raise RuntimeError(f"All Groq keys failed for STT: {last_error}")


def transcribe_audio(audio_bytes: bytes, language: str = "en") -> TranscriptionResult:
    """Main entry point for STT transcription."""
    provider = STTProvider()
    return provider.transcribe(audio_bytes, language)


def transcribe_with_fallback(audio_bytes: bytes, language: str = "en") -> TranscriptionResult:
    """Try server-side STT first, fall back to browser transcript if provided."""
    try:
        result = transcribe_audio(audio_bytes, language)
        result.fallback_used = False
        return result
    except Exception as exc:
        log.warning("Server STT failed, will use browser transcript: %s", exc)
        # Return empty result with fallback flag - caller should use browser transcript
        raise RuntimeError(f"Server STT unavailable: {exc}") from exc