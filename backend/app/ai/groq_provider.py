"""Groq provider via official `groq` SDK (OpenAI-compatible)."""
from __future__ import annotations
import re
from .base import AIProvider, AIResponse, ProviderFailure
from .key_manager import key_manager
from backend.app.config import settings


def _classify_groq_error(exc: Exception) -> ProviderFailure:
    msg = str(exc)
    low = msg.lower()
    status = None
    m = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", msg)
    if m:
        status = int(m.group(1))
    if status == 401 or "invalid api key" in low or "unauthorized" in low:
        return ProviderFailure(f"Groq auth error: {msg}", status=status, retryable=False)
    return ProviderFailure(f"Groq failure: {msg}", status=status or 429, retryable=True)


class GroqProvider(AIProvider):
    name = "groq"

    def is_configured(self) -> bool:
        return key_manager.has_keys("groq")

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse:
        slots = key_manager.slots_for("groq")
        if not slots:
            raise ProviderFailure("Groq not configured (no GROQ_API_KEY_* set)", retryable=False)
        return self.generate_with_key(prompt, system, max_tokens,
                                       api_key=slots[0].key, key_label=slots[0].label)

    def generate_with_key(self, prompt: str, system: str = "", max_tokens: int = 1200,
                           api_key: str = "", key_label: str = "") -> AIResponse:
        if not api_key:
            raise ProviderFailure("Groq not configured (empty key slot)", retryable=False)
        try:
            from groq import Groq
        except Exception as exc:
            raise ProviderFailure(f"Groq SDK unavailable: {exc}", retryable=False)
        last_err: Exception | None = None
        for model in (settings.groq_model, settings.groq_fallback_model):
            try:
                client = Groq(api_key=api_key, timeout=settings.timeout_seconds)
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt})
                resp = client.chat.completions.create(
                    model=model, messages=msgs, temperature=0.7, max_tokens=max_tokens,
                )
                text = (resp.choices[0].message.content or "") if resp.choices else ""
                if not text.strip():
                    raise ValueError("empty response from Groq")
                return AIResponse(text=text.strip(), provider="groq", model=model,
                                  key_label=key_label)
            except Exception as exc:
                last_err = exc
                # Auth errors: don't try second model, fail fast.
                if "401" in str(exc) or "unauthorized" in str(exc).lower():
                    break
                continue
        raise _classify_groq_error(last_err or RuntimeError("unknown groq error"))
