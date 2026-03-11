import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any


class TTLCache:
    def __init__(self, max_size: int = 10000) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._inflight: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        if len(self._store) >= self._max_size:
            self._store.pop(next(iter(self._store)))
        self._store[key] = (value, time.time() + ttl)

    async def get_or_fetch(self, key: str, ttl: int, fetcher: Callable[[], Awaitable[Any]]) -> Any | None:
        cached = await self.get(key)
        if cached is not None:
            return cached

        async with self._lock:
            if key in self._inflight:
                future = self._inflight[key]
            else:
                future = asyncio.create_task(fetcher())
                self._inflight[key] = future

        try:
            value = await future
            if value is not None:
                await self.set(key, value, ttl)
            return value
        finally:
            async with self._lock:
                self._inflight.pop(key, None)
