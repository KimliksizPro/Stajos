import pytest

from config import BaseConfig, TestingConfig


def test_ai_defaults_are_safe():
    assert BaseConfig.AI_ENABLED is False
    assert BaseConfig.AI_BASE_URL == "https://api.openai.com/v1"
    assert BaseConfig.AI_API_KEY == ""
    assert BaseConfig.AI_MODEL == "gpt-4o-mini"
    assert BaseConfig.AI_TIMEOUT_SECONDS == 30
    assert BaseConfig.AI_MAX_WORKERS == 2
    assert BaseConfig.AI_RECOVERY_ENABLED is True
    assert BaseConfig.AI_RECOVERY_BATCH_SIZE == 100
    assert BaseConfig.AI_STALE_AFTER_SECONDS == 300


def test_testing_config_disables_ai_and_recovery():
    assert TestingConfig.AI_ENABLED is False
    assert TestingConfig.AI_RECOVERY_ENABLED is False


def test_validate_ai_does_nothing_when_disabled():
    class DisabledConfig(BaseConfig):
        AI_ENABLED = False
        AI_BASE_URL = ""
        AI_API_KEY = ""
        AI_MODEL = ""
        AI_TIMEOUT_SECONDS = 0
        AI_MAX_WORKERS = 0
        AI_RECOVERY_BATCH_SIZE = 0
        AI_STALE_AFTER_SECONDS = 0

    DisabledConfig.validate_ai()


@pytest.mark.parametrize("setting", ["AI_BASE_URL", "AI_API_KEY", "AI_MODEL"])
def test_validate_ai_rejects_missing_required_setting(setting):
    class EnabledConfig(BaseConfig):
        AI_ENABLED = True
        AI_API_KEY = "secret"

    setattr(EnabledConfig, setting, "")

    with pytest.raises(ValueError, match=setting):
        EnabledConfig.validate_ai()


@pytest.mark.parametrize(
    "setting",
    [
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_WORKERS",
        "AI_RECOVERY_BATCH_SIZE",
        "AI_STALE_AFTER_SECONDS",
    ],
)
def test_validate_ai_rejects_non_positive_numeric_setting(setting):
    class EnabledConfig(BaseConfig):
        AI_ENABLED = True
        AI_API_KEY = "secret"

    setattr(EnabledConfig, setting, 0)

    with pytest.raises(ValueError, match=setting):
        EnabledConfig.validate_ai()
