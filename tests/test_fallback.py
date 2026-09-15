"""Provider fallback: Gemini 429 -> Groq; Groq fail -> error; no keys -> offline sentinel."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["AI_PROVIDER_ORDER"] = "gemini,groq,openrouter,cohere"
from backend.app.ai.base import AIResponse, ProviderFailure
from backend.app.ai.provider_manager import ProviderManager

class Fail:
    name = "gemini"
    def is_configured(self): return True
    def generate(self, *a, **k): raise ProviderFailure("429 rate limit exceeded", status=429)

class Ok:
    name = "groq"
    def is_configured(self): return True
    def generate(self, prompt, system="", max_tokens=100): return AIResponse("hello", "groq", "m")

class Fail2:
    name = "groq"
    def is_configured(self): return True
    def generate(self, *a, **k): raise ProviderFailure("500 unavailable", status=500)

class Unconfigured:
    name = "gemini"
    def is_configured(self): return False
    def generate(self, *a, **k): raise AssertionError("should not be called")

def test_fallback_gemini_to_groq():
    m = ProviderManager([Fail(), Ok()])
    r = m.generate("hi")
    assert r.provider == "groq" and m.fallback_active

def test_all_fail_raises_without_faking_quota():
    m = ProviderManager([Fail(), Fail2()])
    try:
        m.generate("hi")
        assert False, "should raise"
    except ProviderFailure as e:
        assert "429" in str(e) and "quota" not in str(e).lower() or "rate limit" in str(e).lower()

def test_unconfigured_skipped():
    m = ProviderManager([Unconfigured(), Ok()])
    r = m.generate("hi")
    assert r.provider == "groq"

def test_rate_limit_status_preserved():
    try:
        raise ProviderFailure("quota exceeded", status=429)
    except ProviderFailure as e:
        assert e.status == 429 and e.retryable
