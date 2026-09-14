import json
from dataclasses import dataclass

from app.utils.validators import normalize_name


@dataclass(frozen=True)
class AIResult:
    refined_content: str
    technologies: tuple[str, ...]
    topics: tuple[str, ...]
    tags: tuple[str, ...]


class AIOutputError(ValueError):
    pass


def parse_ai_output(payload: str) -> AIResult:
    try:
        data = json.loads(payload)
        required_keys = {"refined_content", "technologies", "topics", "tags"}
        if not isinstance(data, dict) or set(data) != required_keys:
            raise ValueError

        content = data["refined_content"]
        if not isinstance(content, str):
            raise TypeError
        content = content.strip()
        if not content or len(content) > 50000:
            raise ValueError

        parsed_lists = {}
        for field in ("technologies", "topics", "tags"):
            values = data[field]
            if not isinstance(values, list) or len(values) > 25:
                raise TypeError

            names = []
            normalized_names = set()
            for value in values:
                if not isinstance(value, str):
                    raise TypeError
                name = value.strip()
                normalized = normalize_name(name)
                if not name or len(name) > 100 or normalized in normalized_names:
                    raise ValueError
                names.append(name)
                normalized_names.add(normalized)
            parsed_lists[field] = tuple(names)

        return AIResult(content, **parsed_lists)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise AIOutputError("Invalid AI output") from None
