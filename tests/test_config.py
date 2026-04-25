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
    monkeypatch.setenv("APP_HAIKU_MODEL", "test-haiku")
    monkeypatch.setenv("APP_ANTHROPIC_API_KEY", "sk-test")

    s = Settings()
    assert s.env == "staging"
    assert s.log_level == "DEBUG"
    assert s.haiku_model == "test-haiku"
    assert s.anthropic_api_key == "sk-test"


def test_settings_defaults() -> None:
    s = Settings()
    assert s.app_name == "buena-context"
    assert s.haiku_model == "claude-haiku-4-5-20251001"
    assert s.sonnet_model == "claude-sonnet-4-6"
    assert s.webhook_hmac_secret is None


def test_get_settings_is_cached() -> None:
    a = get_settings()
    b = get_settings()
    assert a is b
