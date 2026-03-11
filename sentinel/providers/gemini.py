import asyncio
import json
from typing import Callable

from sentinel.providers.base import LLMProvider, LLMResponse
from sentinel.providers.utils import strip_thinking_tags

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.model = model
        self._client = genai.Client(api_key=api_key) if genai and api_key else None

    def is_available(self) -> bool:
        return self._client is not None

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        timeout: float = 25.0,
        validate: Callable[[str], bool] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse | None:
        if not self._client or not types:
            return None

        prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=config,
                ),
                timeout=timeout,
            )
        except Exception:
            return None

        content = strip_thinking_tags(getattr(response, "text", "") or "")
        if json_mode:
            try:
                json.loads(content)
            except Exception:
                return None
        if not content:
            return None
        if validate and not validate(content):
            return None
        return LLMResponse(content=content, model=self.model, provider="gemini")
