from typing import Literal

from sentinel.config import settings
from sentinel.providers.base import LLMProvider, LLMResponse
from sentinel.providers.gemini import GeminiProvider
from sentinel.providers.ollama import OllamaProvider


class LLMRouter:
    FALLBACK_CHAINS: dict[str, list[str]] = {
        "local": ["volume", "quality"],
        "volume": ["local", "quality"],
        "quality": ["volume", "local"],
    }

    def __init__(self) -> None:
        self.providers: dict[str, LLMProvider] = {}
        if settings.gemini_api_key:
            self.providers["volume"] = GeminiProvider(settings.gemini_api_key, settings.gemini_volume_model)
            self.providers["quality"] = GeminiProvider(settings.gemini_api_key, settings.gemini_quality_model)
        if settings.ollama_api_url:
            self.providers["local"] = OllamaProvider(settings.ollama_api_url, settings.ollama_model)

    async def complete(
        self,
        tier: Literal["local", "volume", "quality"],
        messages: list[dict],
        **kwargs,
    ) -> LLMResponse | None:
        order = [tier] + self.FALLBACK_CHAINS.get(tier, [])
        for selected in order:
            provider = self.providers.get(selected)
            if provider and provider.is_available():
                result = await provider.complete(messages=messages, **kwargs)
                if result:
                    return result
        return None
