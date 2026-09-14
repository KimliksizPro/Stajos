"""AI factory wiring (Faz 5 Task 5).

Disabled: no SDK client, no executor, no extensions. Enabled: validate
config, register provider/executor in ``app.extensions``. Recovery stays an
explicit hook so tests and CLI migrate commands never trigger it.
"""

import atexit
import logging
from collections.abc import Mapping
from typing import Optional

from flask import Flask

from app.ai.base_provider import AIProviderInterface
from app.ai.executor import AIExecutor
from app.ai.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

__all__ = ["create_ai_provider", "create_ai_executor", "start_ai_recovery"]

_REQUIRED_SETTINGS = ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL")
_POSITIVE_SETTINGS = (
    "AI_TIMEOUT_SECONDS",
    "AI_MAX_WORKERS",
    "AI_RECOVERY_BATCH_SIZE",
    "AI_STALE_AFTER_SECONDS",
)


def create_ai_provider(config: Mapping) -> Optional[AIProviderInterface]:
    """Build the AI provider, or None when AI is disabled.

    No SDK client is constructed while disabled. Raises ValueError when
    enabled but required/positive settings are invalid.
    """
    if not config.get("AI_ENABLED"):
        return None
    for setting in _REQUIRED_SETTINGS:
        if not config.get(setting):
            raise ValueError(f"{setting} must be set when AI is enabled")
    for setting in _POSITIVE_SETTINGS:
        try:
            numeric = int(config.get(setting))
        except (TypeError, ValueError):
            raise ValueError(f"{setting} must be positive") from None
        if numeric <= 0:
            raise ValueError(f"{setting} must be positive")
    return OpenAIProvider(
        api_key=config.get("AI_API_KEY"),
        base_url=config.get("AI_BASE_URL"),
        model=config.get("AI_MODEL"),
        timeout_seconds=int(config.get("AI_TIMEOUT_SECONDS")),
    )


def create_ai_executor(
    app: Flask, provider: Optional[AIProviderInterface]
) -> Optional[AIExecutor]:
    """Register provider/executor in app.extensions, or None without provider."""
    if provider is None:
        return None
    max_workers = int(app.config.get("AI_MAX_WORKERS", 2))
    if max_workers <= 0:
        raise ValueError("AI_MAX_WORKERS must be positive")
    executor = AIExecutor(app, provider, max_workers=max_workers)
    app.extensions["ai_provider"] = provider
    app.extensions["ai_executor"] = executor
    atexit.register(executor.shutdown)
    return executor


def start_ai_recovery(app: Flask) -> int:
    """Explicit startup hook: resubmit pending logs, else 0.

    Call from the real process startup path after migrations. Never called
    automatically during tests or CLI migrate commands.
    """
    if not app.config.get("AI_ENABLED") or not app.config.get(
        "AI_RECOVERY_ENABLED"
    ):
        return 0
    executor = app.extensions.get("ai_executor")
    if executor is None:
        logger.warning("AI recovery skipped: executor not wired")
        return 0
    from app.services.ai_service import AIService

    return AIService.recover_pending(
        app,
        executor,
        batch_size=int(app.config.get("AI_RECOVERY_BATCH_SIZE", 100)),
        stale_after_seconds=int(app.config.get("AI_STALE_AFTER_SECONDS", 300)),
    )
