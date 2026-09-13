"""Provider interface + failure taxonomy. No direct SDK dependency here."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    fallback_active: bool = False
    key_label: str = ""  # safe label only ("Key 2") — never a secret

class ProviderFailure(Exception):
    """Raised only for real failures -> triggers fallback. Never faked."""
    def __init__(self, message: str, status: int | None = None, retryable: bool = True):
        super().__init__(message)
        self.status = status
        self.retryable = retryable

class AIProvider(Protocol):
    name: str
    def is_configured(self) -> bool: ...
    def generate(self, prompt: str, system: str = "", max_tokens: int = 1200) -> AIResponse: ...
    def generate_with_key(self, prompt: str, system: str = "", max_tokens: int = 1200,
                           api_key: str = "", key_label: str = "") -> AIResponse: ...
