from abc import ABC, abstractmethod
from typing import Callable

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        timeout: float = 25.0,
        validate: Callable[[str], bool] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse | None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...
