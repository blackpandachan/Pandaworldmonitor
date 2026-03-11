import httpx

from sentinel.config import settings
from sentinel.storage.cache import TTLCache


async def fetch_gdelt_events(query: str, mode: str = "artlist", max_results: int = 50, cache: TTLCache | None = None) -> list[dict]:
    max_results = max(1, min(max_results, 250))
    params = {
        "query": query,
        "mode": mode,
        "maxrecords": max_results,
        "format": "json",
    }

    async def _fetch() -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                response = await client.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    key = f"gdelt:{query}:{mode}:{max_results}"
    payload = await (cache.get_or_fetch(key, 1800, _fetch) if cache else _fetch())
    if not payload:
        return []
    return payload.get("articles", []) if isinstance(payload, dict) else []
