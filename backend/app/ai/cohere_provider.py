"""Cohere provider (Cohere v2 Chat API over httpx, no extra SDK)."""
from __future__ import annotations
import re
import httpx
from .base import AIProvider, AIResponse, ProviderFailure
from .key_manager import key_manager
from backend.app.config import settings

URL = "https://api.cohere.com/v2/chat"


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
        m = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", msg)
        if m:
            status = int(m.group(1))
    if status == 401 or "invalid api key" in low or "unauthorized" in low or "invalid token" in low:
        return ProviderFailure(f"Cohere auth error: {msg[:200]}", status=status or 401, retryable=False)
    return ProviderFailure(f"Cohere failure: {msg[:200]}", status=status or 429, retryable=True)


def _extract_text(data: dict) -> str:
    msg = (data or {}).get("message") or {}
    parts = msg.get("content") or []
    texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"]
    if texts:
        return "".join(texts)
    # fallbacks for shape variations
    if isinstance(msg.get("content"), str):
        return msg["content"]
    return str((data or {}).get("text", ""))


class CohereProvider(AIProvider):
    name = "cohere"

    def is_configured(self) -> bool:
        return key_manager.has_keys("cohere")

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse:
        slots = key_manager.slots_for("cohere")
        if not slots:
            raise ProviderFailure("Cohere not configured (no COHERE_API_KEY_* set)", retryable=False)
        return self.generate_with_key(prompt, system, max_tokens,
                                       api_key=slots[0].key, key_label=slots[0].label)

    def generate_with_key(self, prompt: str, system: str = "", max_tokens: int = 1200,
                           api_key: str = "", key_label: str = "") -> AIResponse:
        if not api_key:
            raise ProviderFailure("Cohere not configured (empty key slot)", retryable=False)
        last_err: Exception | None = None
        for model in (settings.cohere_model, settings.cohere_fallback_model):
            try:
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt})
                with httpx.Client(timeout=settings.timeout_seconds) as client:
                    r = client.post(
                        URL,
                        headers={"Authorization": f"Bearer {api_key}",
                                 "Content-Type": "application/json"},
                        json={"model": model, "messages": msgs,
                              "temperature": 0.7, "max_tokens": max_tokens},
                    )
                    r.raise_for_status()
                    text = _extract_text(r.json())
                if not str(text).strip():
                    raise ValueError("empty response from Cohere")
                return AIResponse(text=str(text).strip(), provider="cohere", model=model,
                                  key_label=key_label)
            except Exception as exc:
                last_err = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                    break
                continue
        raise _classify(last_err or RuntimeError("unknown cohere error"))
