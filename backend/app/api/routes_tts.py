"""TTS routes: ElevenLabs text-to-speech. Key stays server-side."""
from __future__ import annotations
import httpx
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from backend.app.config import settings

router = APIRouter(prefix="/api/tts", tags=["tts"])

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class TTSIn(BaseModel):
    text: str
    voice_id: str = ""  # optional override, defaults to config


@router.post("/speak")
async def speak(inp: TTSIn):
    """Convert text to speech using ElevenLabs. Returns audio/mpeg bytes."""
    if not inp.text or not inp.text.strip():
        return Response(content=b"", media_type="audio/mpeg", status_code=200)

    api_key = settings.elevenlabs_api_key
    if not api_key:
        return {"error": "ElevenLabs API key not configured", "code": "no_key"}

    voice_id = inp.voice_id or settings.elevenlabs_voice_id
    if not voice_id:
        return {"error": "No voice ID configured", "code": "no_voice"}

    url = ELEVENLABS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": inp.text[:5000],
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return Response(content=resp.content, media_type="audio/mpeg")
            else:
                # Return the actual ElevenLabs error for debugging.
                detail = ""
                try:
                    err = resp.json()
                    detail = err.get("detail", {}).get("message", "") or str(err)
                except Exception:
                    detail = resp.text[:200]
                return {
                    "error": f"ElevenLabs error ({resp.status_code}): {detail}",
                    "code": "tts_error",
                    "status": resp.status_code,
                }
    except httpx.TimeoutException:
        return {"error": "TTS request timed out (60s)", "code": "timeout"}
    except httpx.ConnectError:
        return {"error": "Could not connect to ElevenLabs API", "code": "connect_error"}
    except Exception as e:
        return {"error": f"TTS request failed: {str(e)[:200]}", "code": "tts_failed"}


@router.get("/health")
def tts_health():
    """Check if ElevenLabs is configured."""
    has_key = bool(settings.elevenlabs_api_key)
    has_voice = bool(settings.elevenlabs_voice_id)
    return {"configured": has_key and has_voice, "has_key": has_key, "has_voice": has_voice}
