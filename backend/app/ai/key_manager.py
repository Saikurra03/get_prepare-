"""Centralized API key pools + rotation health.

- Keys come ONLY from environment variables (never hardcoded, never logged, never sent to frontend).
- Numbered keys define rotation order: GEMINI_API_KEY_1, _2, ... then legacy GEMINI_API_KEY.
  Same pattern for GROQ_API_KEY_1, ... (generic: <PREFIX>_API_KEY_<N>).
- Rate-limited keys get a temporary cooldown with exponential backoff; invalid keys get a long cooldown.
- All status output uses safe labels ("Key 2") — key values never appear in logs or API responses.
"""
from __future__ import annotations
import os
import time
import logging
from dataclasses import dataclass

log = logging.getLogger("beready.keys")

MAX_NUMBERED_KEYS = 20


def _get_any(*names: str) -> str:
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return ""


def _collect(prefix: str) -> list[str]:
    """Read-only env scan. Order: _1.._N, then legacy single key. Deduplicated.

    Accepts UPPER and lower case spellings (e.g. OPENROUTER_API_KEY_1 and
    openrouter_api_key_1) since env naming varies.
    """
    keys: list[str] = []
    up, lo = prefix.upper(), prefix.lower()
    for i in range(1, MAX_NUMBERED_KEYS + 1):
        v = _get_any(f"{up}_API_KEY_{i}", f"{lo}_API_KEY_{i}", f"{lo}_api_key_{i}")
        if v and v not in keys:
            keys.append(v)
    legacy = _get_any(f"{up}_API_KEY", f"{lo}_API_KEY", f"{lo}_api_key")
    if legacy and legacy not in keys:
        keys.append(legacy)
    return keys


@dataclass
class KeySlot:
    provider: str          # "gemini" / "groq" (lowercase)
    index: int             # 1-based display number
    key: str               # SECRET — never log, never return to callers
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    total_failures: int = 0
    total_success: int = 0

    @property
    def label(self) -> str:
        return f"Key {self.index}"

    def available(self, now: float | None = None) -> bool:
        return (time.time() if now is None else now) >= self.cooldown_until


def _is_auth_error(exc: Exception) -> bool:
    if getattr(exc, "status", None) == 401:
        return True
    low = str(exc).lower()
    return "invalid api key" in low or "unauthorized" in low


class KeyManager:
    """Holds one KeySlot list per provider. Add new keys via env only — no code changes."""

    def __init__(self) -> None:
        self._slots: dict[str, list[KeySlot]] = {}

    def reload(self) -> None:
        """Drop cached slots (picks up env changes). Used in tests."""
        self._slots = {}

    def _ensure(self, provider: str) -> list[KeySlot]:
        prefix = provider.upper()
        if prefix not in self._slots:
            self._slots[prefix] = [
                KeySlot(provider.lower(), i + 1, k)
                for i, k in enumerate(_collect(prefix))
            ]
        return self._slots[prefix]

    def has_keys(self, provider: str) -> bool:
        return bool(self._ensure(provider))

    def slots_for(self, provider: str) -> list[KeySlot]:
        return list(self._ensure(provider))

    def available_keys(self, provider: str, now: float | None = None) -> list[KeySlot]:
        now = time.time() if now is None else now
        return [s for s in self._ensure(provider) if s.available(now)]

    def configured_providers(self, names: list[str]) -> list[str]:
        return [n for n in names if self.has_keys(n)]

    def mark_success(self, slot: KeySlot) -> None:
        slot.consecutive_failures = 0
        slot.total_success += 1
        log.info("%s %s ok", slot.provider, slot.label)

    def mark_failure(self, slot: KeySlot, exc: Exception) -> int:
        """Put the failed key on cooldown. Returns cooldown seconds. Never retries same key in-request."""
        slot.total_failures += 1
        slot.consecutive_failures += 1
        if _is_auth_error(exc):
            secs = int(os.environ.get("AI_INVALID_KEY_COOLDOWN_SECONDS", "1800"))
        else:
            base = int(os.environ.get("AI_KEY_COOLDOWN_SECONDS", "60"))
            secs = min(base * (2 ** (slot.consecutive_failures - 1)), 900)
        slot.cooldown_until = time.time() + secs
        # Safe: label only, never the key value.
        log.warning("%s %s failed (%s) — cooldown %ss", slot.provider, slot.label, exc, secs)
        return secs

    def safe_health(self) -> dict:
        """Admin/debug view. Contains counts and labels only — no secrets."""
        out: dict = {}
        for prefix, slots in self._slots.items():
            out[prefix.lower()] = {
                "keys": len(slots),
                "available": sum(1 for s in slots if s.available()),
                "labels": [s.label for s in slots],
                "failures": {s.label: s.total_failures for s in slots},
            }
        return out


key_manager = KeyManager()
