"""ProviderManager: ordered provider x key rotation with bounded attempts.

Flow per request:
  Gemini Key 1 -> (429/quota/timeout) -> Gemini Key 2 -> ... -> Groq Key 1 -> ...

Rules:
- Each key slot is tried at most ONCE per request — a failed key is never retried in-request.
- Failed keys go on temporary cooldown (exponential backoff); invalid keys get a long cooldown.
- Total attempts capped by AI_MAX_ATTEMPTS (default 10). No infinite loops.
- Small exponential backoff sleep between attempts (tunable via AI_RETRY_BASE_MS).
- Only safe labels ("Gemini — Key 2 active") leave this module. Key values never logged/exposed.
"""
from __future__ import annotations
import logging
import os
import time
from .base import AIProvider, AIResponse, ProviderFailure
from .key_manager import key_manager
from backend.app.config import settings

log = logging.getLogger("beready.ai")

OFFLINE_SENTINEL = "OFFLINE_NO_KEYS"


class ProviderManager:
    def __init__(self, providers: list[AIProvider], sleep_fn=None):
        self._providers = {p.name: p for p in providers}
        self._sleep = sleep_fn or time.sleep
        self.last_provider: str | None = None
        self.last_key_label: str | None = None
        self.fallback_active: bool = False

    def _ordered(self) -> list[AIProvider]:
        # Re-read from env each call so tests can override AI_PROVIDER_ORDER
        raw = os.environ.get("AI_PROVIDER_ORDER", "groq,gemini,openrouter,cohere")
        order = [p.strip().lower() for p in raw.split(",") if p.strip()]
        ordered = [self._providers[n] for n in order if n in self._providers]
        rest = [p for n, p in self._providers.items() if n not in order]
        return ordered + rest

    def _max_attempts(self) -> int:
        try:
            return max(1, int(os.environ.get("AI_MAX_ATTEMPTS", str(settings.max_attempts))))
        except ValueError:
            return 10

    def _backoff_sleep(self, retry_number: int) -> None:
        """Exponential backoff between attempts: base * 2^(n-1), capped at 1s."""
        try:
            base_ms = int(os.environ.get("AI_RETRY_BASE_MS", str(settings.retry_base_ms)))
        except ValueError:
            base_ms = 150
        if base_ms <= 0:
            return
        delay = min(base_ms / 1000.0 * (2 ** (retry_number - 1)), 1.0)
        try:
            self._sleep(delay)
        except Exception:
            pass

    def _supports_rotation(self, provider: AIProvider) -> bool:
        return hasattr(provider, "generate_with_key") and key_manager.has_keys(provider.name)

    def _anything_configured(self) -> bool:
        for p in self._ordered():
            try:
                if p.is_configured():
                    return True
            except Exception:
                continue
            if key_manager.has_keys(p.name):
                return True
        return False

    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse:
        errors: list[str] = []
        attempts = 0
        limit = self._max_attempts()

        for provider in self._ordered():
            if attempts >= limit:
                break
            if self._supports_rotation(provider):
                slots = key_manager.available_keys(provider.name)
                if not slots:
                    errors.append(f"{provider.name}: all keys cooling down")
                    log.warning("Provider %s skipped — all keys on cooldown", provider.name)
                    continue
                for slot in slots:
                    if attempts >= limit:
                        break
                    if attempts > 0:
                        self._backoff_sleep(attempts)
                    attempts += 1
                    try:
                        resp = provider.generate_with_key(
                            prompt, system=system, max_tokens=max_tokens,
                            api_key=slot.key, key_label=slot.label)
                    except ProviderFailure as exc:
                        key_manager.mark_failure(slot, exc)
                        errors.append(f"{provider.name} {slot.label}: {exc}")
                        continue  # next key — never retry this slot in-request
                    key_manager.mark_success(slot)
                    self.last_provider = resp.provider
                    self.last_key_label = slot.label
                    resp.key_label = slot.label
                    self.fallback_active = attempts > 1
                    resp.fallback_active = self.fallback_active
                    if self.fallback_active:
                        log.warning("AI rotation: now=%s %s after: %s",
                                    resp.provider, slot.label, " | ".join(errors))
                    return resp
            else:
                # Legacy path (providers without per-key support, e.g. test doubles).
                try:
                    configured = provider.is_configured()
                except Exception:
                    configured = False
                if not configured:
                    errors.append(f"{provider.name}: not configured")
                    continue
                if attempts > 0:
                    self._backoff_sleep(attempts)
                attempts += 1
                try:
                    resp = provider.generate(prompt, system=system, max_tokens=max_tokens)
                    self.last_provider = resp.provider
                    self.last_key_label = getattr(resp, "key_label", "") or None
                    self.fallback_active = attempts > 1
                    resp.fallback_active = self.fallback_active
                    return resp
                except ProviderFailure as exc:
                    errors.append(f"{provider.name}: {exc}")
                    log.warning("Provider %s failed (retryable=%s status=%s): %s",
                                provider.name, exc.retryable, exc.status, exc)
                    continue

        if not self._anything_configured():
            raise ProviderFailure(OFFLINE_SENTINEL + ": no AI keys configured", retryable=False)
        raise ProviderFailure(
            f"All AI providers/keys failed after {attempts} attempts: " + " | ".join(errors),
            retryable=True)
