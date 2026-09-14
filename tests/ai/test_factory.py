"""Task 5 RED: factory wiring tests (must FAIL before implementation)."""

import pytest

from app.ai.executor import AIExecutor
from app.ai.factory import create_ai_executor, create_ai_provider, start_ai_recovery
from app.ai.openai_provider import OpenAIProvider
from config import TestingConfig


def _enabled_config(**overrides):
    cfg = {
        "AI_ENABLED": True,
        "AI_BASE_URL": "https://api.openai.com/v1",
        "AI_API_KEY": "test-key",
        "AI_MODEL": "gpt-4o-mini",
        "AI_TIMEOUT_SECONDS": 30,
        "AI_MAX_WORKERS": 2,
        "AI_RECOVERY_ENABLED": True,
        "AI_RECOVERY_BATCH_SIZE": 100,
        "AI_STALE_AFTER_SECONDS": 300,
    }
    cfg.update(overrides)
    return cfg


def test_create_ai_provider_returns_none_when_disabled():
    assert create_ai_provider({"AI_ENABLED": False}) is None


def test_create_ai_provider_builds_openai_provider_when_enabled():
    provider = create_ai_provider(_enabled_config())

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4o-mini"
    assert provider.client is not None


@pytest.mark.parametrize("setting", ["AI_BASE_URL", "AI_API_KEY", "AI_MODEL"])
def test_create_ai_provider_rejects_missing_setting(setting):
    with pytest.raises(ValueError, match=setting):
        create_ai_provider(_enabled_config(**{setting: ""}))


@pytest.mark.parametrize(
    "setting",
    [
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_WORKERS",
        "AI_RECOVERY_BATCH_SIZE",
        "AI_STALE_AFTER_SECONDS",
    ],
)
def test_create_ai_provider_rejects_non_positive_setting(setting):
    with pytest.raises(ValueError, match=setting):
        create_ai_provider(_enabled_config(**{setting: 0}))


def test_create_ai_executor_returns_none_without_provider(app):
    assert create_ai_executor(app, None) is None
    assert "ai_provider" not in app.extensions
    assert "ai_executor" not in app.extensions


def test_create_ai_executor_registers_extensions_and_atexit(app, monkeypatch):
    registered = []
    monkeypatch.setattr("atexit.register", registered.append)

    provider = create_ai_provider(_enabled_config())
    executor = create_ai_executor(app, provider)
    try:
        assert isinstance(executor, AIExecutor)
        assert app.extensions["ai_provider"] is provider
        assert app.extensions["ai_executor"] is executor
        assert registered == [executor.shutdown]
    finally:
        executor.shutdown(wait=True)


def test_create_app_disabled_has_no_ai_extensions(app):
    assert "ai_provider" not in app.extensions
    assert "ai_executor" not in app.extensions


def test_create_app_enabled_wires_extensions(monkeypatch):
    from app import create_app

    monkeypatch.setattr(TestingConfig, "AI_ENABLED", True)
    monkeypatch.setattr(TestingConfig, "AI_API_KEY", "test-key")
    monkeypatch.setattr(TestingConfig, "AI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setattr(TestingConfig, "AI_MODEL", "gpt-4o-mini")

    enabled_app = create_app("testing")
    try:
        assert "ai_provider" in enabled_app.extensions
        assert "ai_executor" in enabled_app.extensions
    finally:
        executor = enabled_app.extensions.get("ai_executor")
        if executor is not None:
            executor.shutdown(wait=True)


def test_create_app_never_runs_recovery(monkeypatch):
    from app import create_app
    from app.services import ai_service

    calls = []
    monkeypatch.setattr(
        ai_service.AIService,
        "recover_pending",
        lambda *args, **kwargs: calls.append((args, kwargs)) or 0,
    )

    create_app("testing")

    assert calls == []


def test_start_ai_recovery_returns_zero_when_disabled(app):
    assert start_ai_recovery(app) == 0


def test_start_ai_recovery_returns_zero_when_recovery_disabled(app):
    app.config["AI_ENABLED"] = True
    app.config["AI_RECOVERY_ENABLED"] = False

    assert start_ai_recovery(app) == 0


def test_start_ai_recovery_returns_zero_without_executor(app):
    app.config["AI_ENABLED"] = True
    app.config["AI_RECOVERY_ENABLED"] = True

    assert start_ai_recovery(app) == 0


def test_start_ai_recovery_delegates_with_configured_values(app, monkeypatch):
    from app.services import ai_service

    class FakeExecutor:
        pass

    app.config["AI_ENABLED"] = True
    app.config["AI_RECOVERY_ENABLED"] = True
    app.config["AI_RECOVERY_BATCH_SIZE"] = 42
    app.config["AI_STALE_AFTER_SECONDS"] = 77
    fake = FakeExecutor()
    app.extensions["ai_executor"] = fake

    seen = {}

    def fake_recover(app_arg, executor_arg, *, batch_size, stale_after_seconds):
        seen["executor"] = executor_arg
        seen["batch_size"] = batch_size
        seen["stale_after_seconds"] = stale_after_seconds
        return 7

    monkeypatch.setattr(ai_service.AIService, "recover_pending", fake_recover)

    assert start_ai_recovery(app) == 7
    assert seen == {"executor": fake, "batch_size": 42, "stale_after_seconds": 77}
