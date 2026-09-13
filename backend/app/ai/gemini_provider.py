"""Gemini provider via official `google-genai` SDK (Sep 2026)."""
from __future__ import annotations
import re
from .base import AIProvider, AIResponse, ProviderFailure
from .key_manager import key_manager
from backend.app.config import settings


def _classify_gemini_error(exc: Exception) -> ProviderFailure:
    msg = str(exc)
    low = msg.lower()
    status = None
    m = re.search(r"\b(429|500|502|503|504)\b", msg)
    if m:
        status = int(m.group(1))
    retryable_kw = ("429", "rate limit", "quota", "exceed", "timeout", "timed out",
                    "unavailable", "overloaded", "500", "502", "503", "504",
                    "network", "connection", "malformed", "empty response")
    retryable = any(k in low for k in retryable_kw) or status in (429, 500, 502, 503, 504)
    if not retryable:
        # Non-retryable (e.g. bad key, invalid arg) still surfaces as failure,
        # manager decides whether to try next provider.
        return ProviderFailure(f"Gemini error: {msg}", status=status, retryable=True)
    return ProviderFailure(f"Gemini failure: {msg}", status=status or 429, retryable=True)


class GeminiProvider(AIProvider):
    name = "gemini"

    def is_configured(self) -> bool:
        return key_manager.has_keys("gemini")

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse:
        slots = key_manager.slots_for("gemini")
        if not slots:
            raise ProviderFailure("Gemini not configured (no GEMINI_API_KEY_* set)", retryable=False)
        return self.generate_with_key(prompt, system, max_tokens,
                                       api_key=slots[0].key, key_label=slots[0].label)

    def generate_with_key(self, prompt: str, system: str = "", max_tokens: int = 1200,
                           api_key: str = "", key_label: str = "") -> AIResponse:
        if not api_key:
            raise ProviderFailure("Gemini not configured (empty key slot)", retryable=False)
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # SDK missing
            raise ProviderFailure(f"Gemini SDK unavailable: {exc}", retryable=False)
        # Try primary then fallback model on same provider before giving up.
        last_err: Exception | None = None
        for model in (settings.gemini_model, settings.gemini_fallback_model):
            try:
                client = genai.Client(api_key=api_key)
                cfg = types.GenerateContentConfig(
                    system_instruction=system or None,
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
                resp = client.models.generate_content(
                    model=model, contents=prompt, config=cfg,
                )
                text = getattr(resp, "text", "") or ""
                if not text.strip():
                    raise ValueError("empty response from Gemini")
                return AIResponse(text=text.strip(), provider="gemini", model=model,
                                  key_label=key_label)
            except Exception as exc:
                last_err = exc
                continue
        raise _classify_gemini_error(last_err or RuntimeError("unknown gemini error"))
