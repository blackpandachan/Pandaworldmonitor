import asyncio

from sentinel.storage.cache import TTLCache


async def test_inflight_coalescing() -> None:
    cache = TTLCache()
    calls = {"count": 0}

    async def fetcher() -> str:
        calls["count"] += 1
        await asyncio.sleep(0.05)
        return "value"

    results = await asyncio.gather(
        cache.get_or_fetch("k", 30, fetcher),
        cache.get_or_fetch("k", 30, fetcher),
    )

    assert results == ["value", "value"]
    assert calls["count"] == 1
