from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    pass


class AIProviderInterface(ABC):
    @abstractmethod
    def refine(self, raw_content: str) -> str:
        raise NotImplementedError


__all__ = ["AIProviderError", "AIProviderInterface"]
