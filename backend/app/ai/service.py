"""AIService: single entry for all AI calls. Offline heuristic fallback so MVP is testable without keys."""
from __future__ import annotations
import json
import re
import logging
from .provider_manager import ProviderManager, OFFLINE_SENTINEL
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider
from .cohere_provider import CohereProvider
from .base import AIResponse

log = logging.getLogger("beready.ai")

_manager = ProviderManager([GeminiProvider(), GroqProvider(), OpenRouterProvider(), CohereProvider()])

COACH_SYSTEM = (
    "You are BeReady, a world-class communication coach and interviewer. "
    "Optimize for NATURAL + CLEAR + ENGAGING + MEMORABLE, never robotic. "
    "Give exactly ONE highest-impact priority, one concrete retry instruction, one example line. "
    "Be kind, specific, brief (<120 words). Never make clinical psychological claims."
)

def provider_status() -> dict:
    """Safe status only: 'AI Ready' for users, 'Gemini — Key 2 active' for debug. Never a secret."""
    if not _manager.last_provider:
        return {"provider": None, "key_label": None, "fallback_active": False,
                "ready": False, "display": "offline (no keys)", "debug": "offline (no keys)"}
    label = _manager.last_key_label or ""
    debug = f"{_manager.last_provider.capitalize()} — {label} active" if label else _manager.last_provider
    display = "AI Ready" + (" — fallback active" if _manager.fallback_active else "")
    return {"provider": _manager.last_provider, "key_label": label,
            "fallback_active": _manager.fallback_active,
            "ready": True, "display": display, "debug": debug}

def _offline_coach(prompt: str) -> str:
    """Deterministic heuristic when no keys configured — used by tests and offline demo."""
    low = prompt.lower()
    if "story" in low:
        return ("Priority: weak hook — open with stakes in one line. "
                "Retry: restate your first sentence starting with the moment of tension. "
                'Example: "We had 48 hours before launch and payments were failing."')
    if "interview" in low:
        return ("Priority: slow time-to-main-point — lead with the result. "
                "Retry: answer again starting with your conclusion in 10 seconds. "
                'Example: "I cut checkout failures 40% by adding idempotent retries."')
    return ("Priority: filler + long sentences — shorten and pause. "
            "Retry: say it again in 2 short sentences with zero fillers. "
            'Example: "We faced X. I fixed it by doing Y."')

def generate(prompt: str, system: str = COACH_SYSTEM, max_tokens: int = 1200) -> AIResponse:
    import time as _time
    from backend.app.main import _activity
    _activity["ai_calls"] += 1
    try:
        resp = _manager.generate(prompt, system=system, max_tokens=max_tokens)
        _activity["ai_success"] += 1
        _activity["last_ai_time"] = _time.time()
        return resp
    except Exception as exc:
        _activity["ai_failures"] += 1
        if OFFLINE_SENTINEL in str(exc):
            log.info("offline mode: no AI keys, using heuristic")
            tag = "offline"
            return AIResponse(text=_offline_coach(prompt), provider=tag, model="heuristic", fallback_active=False)
        raise

def generate_json(prompt: str, system: str = COACH_SYSTEM, max_tokens: int = 1500) -> tuple[dict, AIResponse]:
    """Ask for JSON; robustly extract {...} even if model adds prose."""
    resp = generate(prompt + "\n\nReply with valid JSON only.", system=system, max_tokens=max_tokens)
    m = re.search(r"\{.*\}", resp.text, re.DOTALL)
    if not m:
        raise ValueError(f"malformed AI response (no JSON): {resp.text[:200]}")
    try:
        return json.loads(m.group(0)), resp
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed AI JSON: {exc}") from exc
