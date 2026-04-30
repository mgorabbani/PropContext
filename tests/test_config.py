from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("APP_"):
            monkeypatch.delenv(key, raising=False)


def test_settings_loads_app_prefixed_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_FAST_MODEL", "test-fast")
    monkeypatch.setenv("APP_ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("APP_LLM_PROVIDER", "anthropic")

    s = Settings()
    assert s.env == "staging"
    assert s.log_level == "DEBUG"
    assert s.fast_model == "test-fast"
    assert s.anthropic_api_key == "sk-test"


def test_settings_defaults_for_gemini() -> None:
    s = Settings(_env_file=None)
    assert s.app_name == "propcontext"
    assert s.llm_provider == "gemini"
    assert s.fast_model == "gemini-2.5-flash-lite"
    assert s.smart_model == "gemini-2.5-pro"
    assert s.webhook_hmac_secret is None


def test_settings_defaults_for_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LLM_PROVIDER", "anthropic")
    s = Settings(_env_file=None)
    assert s.fast_model == "claude-haiku-4-5-20251001"
    assert s.smart_model == "claude-sonnet-4-6"


def test_get_settings_is_cached() -> None:
    a = get_settings()
    b = get_settings()
    assert a is b
