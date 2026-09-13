"""OpenRouter provider (OpenAI-compatible chat completions over httpx, no extra SDK)."""
from __future__ import annotations
import re
import httpx
from .base import AIProvider, AIResponse, ProviderFailure
from .key_manager import key_manager
from backend.app.config import settings

URL = "https://openrouter.ai/api/v1/chat/completions"


def _classify(exc: Exception) -> ProviderFailure:
    msg = str(exc)
    low = msg.lower()
    status = None
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            status = exc.response.status_code
        except Exception:
            status = None
    if status is None:
        m = re.search(r"\b(400|401|402|403|404|429|500|502|503|504)\b", msg)
        if m:
            status = int(m.group(1))
    if status == 401 or "invalid api key" in low or "unauthorized" in low or "invalid_api_key" in low:
        return ProviderFailure(f"OpenRouter auth error: {msg[:200]}", status=status or 401, retryable=False)
    return ProviderFailure(f"OpenRouter failure: {msg[:200]}", status=status or 429, retryable=True)


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    def is_configured(self) -> bool:
        return key_manager.has_keys("openrouter")

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse:
        slots = key_manager.slots_for("openrouter")
        if not slots:
            raise ProviderFailure("OpenRouter not configured (no OPENROUTER_API_KEY_* set)", retryable=False)
        return self.generate_with_key(prompt, system, max_tokens,
                                       api_key=slots[0].key, key_label=slots[0].label)

    def generate_with_key(self, prompt: str, system: str = "", max_tokens: int = 1200,
                           api_key: str = "", key_label: str = "") -> AIResponse:
        if not api_key:
            raise ProviderFailure("OpenRouter not configured (empty key slot)", retryable=False)
        last_err: Exception | None = None
        for model in (settings.openrouter_model, settings.openrouter_fallback_model):
            try:
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt})
                with httpx.Client(timeout=settings.timeout_seconds) as client:
                    r = client.post(
                        URL,
                        headers={"Authorization": f"Bearer {api_key}",
                                 "Content-Type": "application/json",
                                 "HTTP-Referer": "https://localhost:8000",
                                 "X-Title": "BeReady Boy Coach"},
                        json={"model": model, "messages": msgs,
                              "temperature": 0.7, "max_tokens": max_tokens},
                    )
                    r.raise_for_status()
                    data = r.json()
                choices = (data or {}).get("choices") or []
                text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
                if isinstance(text, list):  # some models return content parts
                    text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
                if not str(text).strip():
                    raise ValueError("empty response from OpenRouter")
                return AIResponse(text=str(text).strip(), provider="openrouter", model=model,
                                  key_label=key_label)
            except Exception as exc:
                last_err = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                    break  # bad key: don't waste the fallback model on the same key
                continue
        raise _classify(last_err or RuntimeError("unknown openrouter error"))
