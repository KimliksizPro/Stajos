from concurrent.futures import Future, ThreadPoolExecutor

from flask import Flask

from app.ai.base_provider import AIProviderInterface

__all__ = ["AIExecutor"]


class AIExecutor:
    """Bounded background executor; submits log ids only (Faz 5 Task 4)."""

    def __init__(
        self, app: Flask, provider: AIProviderInterface, max_workers: int = 2
    ) -> None:
        self._app = app
        self._provider = provider
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, log_id: str) -> Future:
        from app.services.ai_service import AIService

        return self._executor.submit(
            AIService.process_log, self._app, log_id, self._provider
        )

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
