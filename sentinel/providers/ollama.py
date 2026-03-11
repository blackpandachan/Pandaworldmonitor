from typing import Callable

import httpx

from sentinel.config import settings
from sentinel.providers.base import LLMProvider, LLMResponse
from sentinel.providers.utils import strip_thinking_tags


class OllamaProvider(LLMProvider):
    def __init__(self, api_url: str, model: str):
        self.api_url = api_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_url)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        timeout: float = 25.0,
        validate: Callable[[str], bool] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse | None:
        prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=settings.sentinel_http_trust_env) as client:
                res = await client.post(f"{self.api_url}/api/generate", json=payload)
                res.raise_for_status()
                content = strip_thinking_tags(res.json().get("response", ""))
        except Exception:
            return None
        if not content:
            return None
        if validate and not validate(content):
            return None
        return LLMResponse(content=content, model=self.model, provider="ollama")
