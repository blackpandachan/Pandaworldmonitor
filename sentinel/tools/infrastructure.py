import httpx

from sentinel.config import settings
from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB


async def fetch_infrastructure_status(check_types: list[str] | None = None, cache: TTLCache | None = None, db: SentinelDB | None = None) -> dict:
    check_types = check_types or ["internet_outages"]
    report: dict = {"checks": {}, "status": "ok"}

    async def _fetch_cloudflare() -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                # lightweight public endpoint footprint
                response = await client.get("https://radar.cloudflare.com/api/data/netflows/summary")
                if response.status_code >= 400:
                    return None
                return response.json()
        except Exception:
            return None

    if "internet_outages" in check_types:
        data = await (cache.get_or_fetch("cloudflare:netflows", 3600, _fetch_cloudflare) if cache else _fetch_cloudflare())
        report["checks"]["internet_outages"] = {
            "available": bool(data),
            "sample": (data or {}),
        }

    if db:
        await db.record_source_status("infrastructure", "ok")
    return report
