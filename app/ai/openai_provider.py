from openai import OpenAI

from app.ai.base_provider import AIProviderError, AIProviderInterface
from app.ai.prompts import SYSTEM_GUARDRAIL


class OpenAIProvider(AIProviderInterface):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
        client=None,
    ):
        self.model = model
        self.client = client or OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    def refine(self, raw_content: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_GUARDRAIL},
                    {"role": "user", "content": raw_content},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("missing response content")
            return content
        except Exception as exc:
            raise AIProviderError("AI provider request failed") from exc
