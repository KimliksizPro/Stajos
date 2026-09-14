import json
from types import SimpleNamespace

import pytest

from app.ai.base_provider import AIProviderError, AIProviderInterface
from app.ai.openai_provider import OpenAIProvider


class FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_client(content=None, error=None):
    completions = FakeCompletions(content=content, error=error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_provider_implements_interface_and_sends_guarded_json_request():
    response = json.dumps(
        {
            "refined_content": "Refined text",
            "technologies": ["Flask"],
            "topics": ["API"],
            "tags": ["backend"],
        }
    )
    client, completions = make_client(content=response)
    provider = OpenAIProvider(
        api_key="secret",
        base_url="https://example.test/v1",
        model="test-model",
        timeout_seconds=12,
        client=client,
    )

    result = provider.refine("Built an API with Flask")

    assert isinstance(provider, AIProviderInterface)
    assert result == response
    assert len(completions.calls) == 1
    request = completions.calls[0]
    assert request["model"] == "test-model"
    assert request["response_format"] == {"type": "json_object"}
    assert request["messages"][1] == {
        "role": "user",
        "content": "Built an API with Flask",
    }
    guardrail = request["messages"][0]["content"]
    assert "only" in guardrail.lower()
    assert "invent" in guardrail.lower()
    for key in ("refined_content", "technologies", "topics", "tags"):
        assert key in guardrail


def test_provider_rejects_missing_content_with_sanitized_error():
    client, completions = make_client(content=None)
    provider = OpenAIProvider(
        api_key="secret",
        base_url="https://example.test/v1",
        model="test-model",
        timeout_seconds=12,
        client=client,
    )

    with pytest.raises(AIProviderError) as exc_info:
        provider.refine("raw secret content")

    assert str(exc_info.value) == "AI provider request failed"
    assert "raw secret content" not in str(exc_info.value)


def test_provider_sanitizes_sdk_failures():
    client, _ = make_client(error=RuntimeError("secret provider details"))
    provider = OpenAIProvider(
        api_key="api-key-secret",
        base_url="https://example.test/v1",
        model="test-model",
        timeout_seconds=12,
        client=client,
    )

    with pytest.raises(AIProviderError) as exc_info:
        provider.refine("raw secret content")

    assert str(exc_info.value) == "AI provider request failed"
    assert "secret" not in str(exc_info.value)
