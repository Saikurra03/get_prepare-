"""Multi-key rotation: order, 429 -> next key, 401 -> next key, cooldowns, bounds, secrecy."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from backend.app.ai.base import AIResponse, ProviderFailure
from backend.app.ai.key_manager import key_manager
from backend.app.ai.provider_manager import ProviderManager

PREFIXES = ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3",
            "GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3",
            "OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY_2", "openrouter_api_key",
            "COHERE_API_KEY_1", "COHERE_API_KEY_2", "cohere_api_key",
            "AI_PROVIDER_ORDER", "AI_MAX_ATTEMPTS", "AI_RETRY_BASE_MS", "AI_KEY_COOLDOWN_SECONDS",
            "AI_INVALID_KEY_COOLDOWN_SECONDS"]

@pytest.fixture
def clean_env(monkeypatch):
    for v in PREFIXES:
        monkeypatch.delenv(v, raising=False)
    key_manager.reload()
    monkeypatch.setenv("AI_RETRY_BASE_MS", "0")  # no sleeping in tests
    yield monkeypatch
    key_manager.reload()


class ScriptProvider:
    """Rotating provider stub: script maps key value -> 'ok' | error message."""
    def __init__(self, name, script, status=429):
        self.name = name
        self.script = script
        self.status = status
        self.calls: list[str] = []

    def is_configured(self):
        return key_manager.has_keys(self.name)

    def generate_with_key(self, prompt, system="", max_tokens=100, api_key="", key_label=""):
        self.calls.append(api_key)
        action = self.script.get(api_key, "ok")
        if action == "ok":
            return AIResponse("hi", self.name, "m", key_label=key_label)
        raise ProviderFailure(action, status=self.status)


def test_collect_order_and_dedupe(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "aaa")
    clean_env.setenv("GEMINI_API_KEY_2", "bbb")
    clean_env.setenv("GEMINI_API_KEY_3", "aaa")  # dupe ignored
    clean_env.setenv("GEMINI_API_KEY", "bbb")    # dupe of Key 2 ignored
    key_manager.reload()
    slots = key_manager.slots_for("gemini")
    assert [s.key for s in slots] == ["aaa", "bbb"]
    assert [s.label for s in slots] == ["Key 1", "Key 2"]


def test_legacy_key_becomes_slot(clean_env):
    clean_env.setenv("GROQ_API_KEY", "solo")
    key_manager.reload()
    slots = key_manager.slots_for("groq")
    assert len(slots) == 1 and slots[0].label == "Key 1"


def test_rotates_to_next_key_on_429(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "aaa")
    clean_env.setenv("GEMINI_API_KEY_2", "bbb")
    key_manager.reload()
    p = ScriptProvider("gemini", {"aaa": "429 rate limit exceeded"})
    m = ProviderManager([p], sleep_fn=lambda s: None)
    r = m.generate("hi")
    assert r.provider == "gemini" and r.key_label == "Key 2"
    assert p.calls == ["aaa", "bbb"]  # failed key never retried in-request
    assert m.fallback_active and m.last_key_label == "Key 2"
    # failed key now cooling down
    assert [s.label for s in key_manager.available_keys("gemini")] == ["Key 2"]


def test_invalid_key_tries_next(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "bad")
    clean_env.setenv("GEMINI_API_KEY_2", "good")
    key_manager.reload()
    p = ScriptProvider("gemini", {"bad": "401 invalid api key"}, status=401)
    m = ProviderManager([p], sleep_fn=lambda s: None)
    r = m.generate("hi")
    assert r.key_label == "Key 2" and p.calls == ["bad", "good"]


def test_falls_through_to_next_provider(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "g1")
    clean_env.setenv("GROQ_API_KEY_1", "q1")
    key_manager.reload()
    g = ScriptProvider("gemini", {"g1": "429 limited"})
    q = ScriptProvider("groq", {"q1": "ok"})
    m = ProviderManager([g, q], sleep_fn=lambda s: None)
    r = m.generate("hi")
    assert r.provider == "groq" and r.key_label == "Key 1"
    assert g.calls == ["g1"] and q.calls == ["q1"]


def test_all_keys_down_bounded_no_loop(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "a")
    clean_env.setenv("GEMINI_API_KEY_2", "b")
    clean_env.setenv("GROQ_API_KEY_1", "c")
    clean_env.setenv("AI_MAX_ATTEMPTS", "2")
    key_manager.reload()
    g = ScriptProvider("gemini", {"a": "429", "b": "429"})
    q = ScriptProvider("groq", {"c": "503 unavailable"}, status=503)
    m = ProviderManager([g, q], sleep_fn=lambda s: None)
    t0 = time.time()
    with pytest.raises(ProviderFailure):
        m.generate("hi")
    assert time.time() - t0 < 5
    assert len(g.calls) + len(q.calls) <= 2  # hard cap respected


def test_backoff_grows_between_attempts(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "a")
    clean_env.setenv("GEMINI_API_KEY_2", "b")
    clean_env.setenv("AI_RETRY_BASE_MS", "100")
    key_manager.reload()
    sleeps: list[float] = []
    p = ScriptProvider("gemini", {"a": "429"})
    m = ProviderManager([p], sleep_fn=sleeps.append)
    m.generate("hi")
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 1.0


def test_cooldown_expires(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "a")
    clean_env.setenv("AI_KEY_COOLDOWN_SECONDS", "1")
    key_manager.reload()
    p = ScriptProvider("gemini", {"a": "429"})
    m = ProviderManager([p], sleep_fn=lambda s: None)
    with pytest.raises(ProviderFailure):
        m.generate("hi")  # only key fails -> error, key cooling
    assert key_manager.available_keys("gemini") == []
    time.sleep(1.1)
    assert [s.label for s in key_manager.available_keys("gemini")] == ["Key 1"]


def test_status_never_exposes_secrets(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "super-secret-aaa")
    clean_env.setenv("GEMINI_API_KEY_2", "super-secret-bbb")
    key_manager.reload()
    p = ScriptProvider("gemini", {"super-secret-aaa": "429"})
    m = ProviderManager([p], sleep_fn=lambda s: None)
    m.generate("hi")
    from backend.app.ai import service as svc
    svc._manager = m  # point service at this manager for status check
    try:
        st = svc.provider_status()
        blob = str(st) + str(key_manager.safe_health())
        assert "super-secret" not in blob
        assert st["debug"] == "Gemini — Key 2 active"
        assert st["display"] == "AI Ready — fallback active"
    finally:
        from backend.app.ai.gemini_provider import GeminiProvider
        from backend.app.ai.groq_provider import GroqProvider
        from backend.app.ai.openrouter_provider import OpenRouterProvider
        from backend.app.ai.cohere_provider import CohereProvider
        svc._manager = ProviderManager(
            [GeminiProvider(), GroqProvider(), OpenRouterProvider(), CohereProvider()])


def test_offline_when_no_keys(clean_env):
    from backend.app.ai.provider_manager import OFFLINE_SENTINEL
    m = ProviderManager([], sleep_fn=lambda s: None)
    with pytest.raises(ProviderFailure) as e:
        m.generate("hi")
    assert OFFLINE_SENTINEL in str(e.value)


def test_lowercase_env_names_load(clean_env):
    clean_env.setenv("openrouter_api_key", "or-lower")
    clean_env.setenv("cohere_api_key", "co-lower")
    key_manager.reload()
    assert [s.key for s in key_manager.slots_for("openrouter")] == ["or-lower"]
    assert [s.key for s in key_manager.slots_for("cohere")] == ["co-lower"]


def test_four_provider_chain_order(clean_env):
    clean_env.setenv("GEMINI_API_KEY_1", "g")
    clean_env.setenv("GROQ_API_KEY_1", "q")
    clean_env.setenv("OPENROUTER_API_KEY_1", "o")
    clean_env.setenv("COHERE_API_KEY_1", "c")
    clean_env.setenv("AI_PROVIDER_ORDER", "gemini,groq,openrouter,cohere")
    key_manager.reload()
    # reload settings order (Settings snapshot was taken at import)
    from backend.app import config as cfg
    old = cfg.settings.provider_order
    cfg.settings.provider_order = ["gemini", "groq", "openrouter", "cohere"]
    try:
        g = ScriptProvider("gemini", {"g": "429"})
        q = ScriptProvider("groq", {"q": "429"})
        o = ScriptProvider("openrouter", {"o": "429"})
        c = ScriptProvider("cohere", {"c": "ok"})
        m = ProviderManager([g, q, o, c], sleep_fn=lambda s: None)
        r = m.generate("hi")
        assert (r.provider, r.key_label) == ("cohere", "Key 1")
        assert m.fallback_active
    finally:
        cfg.settings.provider_order = old


def test_openrouter_429_classified_retryable():
    from backend.app.ai.openrouter_provider import _classify as or_classify
    from backend.app.ai.cohere_provider import _classify as co_classify
    err = or_classify(RuntimeError("429 rate limit exceeded for model"))
    assert err.status == 429 and err.retryable
    auth = co_classify(RuntimeError("401 invalid api key"))
    assert auth.status == 401 and not auth.retryable
    for fn in (or_classify, co_classify):
        blob = str(fn(RuntimeError("x" * 500)))
        assert len(blob) < 400  # error text truncated, never leaks bodies/keys


def test_new_providers_unconfigured_without_keys(clean_env):
    from backend.app.ai.openrouter_provider import OpenRouterProvider
    from backend.app.ai.cohere_provider import CohereProvider
    assert not OpenRouterProvider().is_configured()
    assert not CohereProvider().is_configured()
