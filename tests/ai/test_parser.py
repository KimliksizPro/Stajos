import json
from dataclasses import FrozenInstanceError

import pytest

from app.ai.parser import AIOutputError, AIResult, parse_ai_output


def valid_payload(**overrides):
    data = {
        "refined_content": " Refined text ",
        "technologies": [" Flask "],
        "topics": [" API "],
        "tags": [" backend "],
    }
    data.update(overrides)
    return json.dumps(data)


def test_parses_trimmed_immutable_result():
    result = parse_ai_output(valid_payload())

    assert result == AIResult(
        refined_content="Refined text",
        technologies=("Flask",),
        topics=("API",),
        tags=("backend",),
    )
    with pytest.raises(FrozenInstanceError):
        result.refined_content = "changed"


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '```json\n{"refined_content": "text", "technologies": [], "topics": [], "tags": []}\n```',
        'explanation {"refined_content": "text", "technologies": [], "topics": [], "tags": []}',
        '{"refined_content": "text", "technologies": [], "topics": [], "tags": []} trailing',
        "[]",
        valid_payload(tags=None),
        json.dumps({"refined_content": "text", "technologies": [], "topics": []}),
        valid_payload(extra=[]),
        valid_payload(refined_content=1),
        valid_payload(refined_content="   "),
        valid_payload(refined_content="x" * 50001),
        valid_payload(technologies="Flask"),
        valid_payload(technologies=[1]),
        valid_payload(technologies=[] if False else ["x"] * 26),
        valid_payload(technologies=["   "]),
        valid_payload(technologies=["x" * 101]),
        valid_payload(technologies=[" Flask ", "flask"]),
        valid_payload(topics=["API", " api "]),
        valid_payload(tags=["Backend", "backend"]),
    ],
    ids=lambda payload: f"invalid-{len(payload)}",
)
def test_rejects_invalid_payloads_with_sanitized_error(payload):
    with pytest.raises(AIOutputError) as exc_info:
        parse_ai_output(payload)

    assert str(exc_info.value) == "Invalid AI output"
    assert payload not in str(exc_info.value)


def test_accepts_documented_boundaries_and_empty_lists():
    result = parse_ai_output(
        valid_payload(
            refined_content="x" * 50000,
            technologies=[str(index).rjust(100, "x") for index in range(25)],
            topics=[],
            tags=[],
        )
    )

    assert len(result.refined_content) == 50000
    assert len(result.technologies) == 25
    assert result.topics == ()
    assert result.tags == ()


def test_rejects_non_string_payload_with_sanitized_error():
    with pytest.raises(AIOutputError, match="^Invalid AI output$"):
        parse_ai_output(object())
