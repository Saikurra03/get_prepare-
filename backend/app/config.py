"""Central config. All model names come from env (replaceable)."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

def _order() -> list[str]:
    raw = os.getenv("AI_PROVIDER_ORDER", "groq,gemini,openrouter,cohere")
    return [p.strip().lower() for p in raw.split(",") if p.strip()]

@dataclass
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
    gemini_fallback_model: str = field(default_factory=lambda: os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite"))
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
    groq_fallback_model: str = field(default_factory=lambda: os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b"))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"))
    openrouter_fallback_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.1-8b-instruct"))
    cohere_model: str = field(default_factory=lambda: os.getenv("COHERE_MODEL", "command-r"))
    cohere_fallback_model: str = field(default_factory=lambda: os.getenv("COHERE_FALLBACK_MODEL", "command-r-plus"))
    provider_order: list[str] = field(default_factory=_order)
    timeout_seconds: int = field(default_factory=lambda: int(os.getenv("AI_TIMEOUT_SECONDS", "30")))
    max_attempts: int = field(default_factory=lambda: int(os.getenv("AI_MAX_ATTEMPTS", "10")))
    key_cooldown_seconds: int = field(default_factory=lambda: int(os.getenv("AI_KEY_COOLDOWN_SECONDS", "60")))
    retry_base_ms: int = field(default_factory=lambda: int(os.getenv("AI_RETRY_BASE_MS", "150")))
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "backend/data"))
    # STT config
    stt_model: str = field(default_factory=lambda: os.getenv("STT_MODEL", "whisper-large-v3-turbo"))
    stt_provider: str = field(default_factory=lambda: os.getenv("STT_PROVIDER", "groq"))
    # ElevenLabs TTS config
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", ""))

settings = Settings()
