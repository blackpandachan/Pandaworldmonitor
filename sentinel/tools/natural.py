from datetime import UTC, datetime, timedelta

import httpx

from sentinel.config import settings
from sentinel.models.events import NaturalEvent
from sentinel.models.geo import GeoPoint
from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB


async def fetch_natural_events(
    days_back: int = 7,
    min_magnitude: float | None = None,
    cache: TTLCache | None = None,
    db: SentinelDB | None = None,
) -> list[NaturalEvent]:
    start = datetime.now(UTC) - timedelta(days=days_back)
    events: list[NaturalEvent] = []

    usgs_params = {"format": "geojson", "starttime": start.date().isoformat(), "orderby": "time"}
    if min_magnitude is not None:
        usgs_params["minmagnitude"] = min_magnitude

    async def _fetch_usgs() -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                usgs = await client.get("https://earthquake.usgs.gov/fdsnws/event/1/query", params=usgs_params)
                usgs.raise_for_status()
                return usgs.json()
        except Exception:
            return None

    usgs_payload = await (cache.get_or_fetch(f"usgs:{days_back}:{min_magnitude}", 300, _fetch_usgs) if cache else _fetch_usgs())

    if usgs_payload:
        for feat in usgs_payload.get("features", []):
            coords = feat.get("geometry", {}).get("coordinates", [0, 0])
            props = feat.get("properties", {})
            try:
                events.append(
                    NaturalEvent(
                        id=feat.get("id", ""),
                        event_type="earthquake",
                        title=props.get("title", "Earthquake"),
                        location=GeoPoint(latitude=float(coords[1]), longitude=float(coords[0])),
                        occurred_at=datetime.fromtimestamp(props.get("time", 0) / 1000, tz=UTC),
                        magnitude=props.get("mag"),
                        source="usgs",
                        details={"place": props.get("place")},
                    )
                )
            except Exception:
                continue

    async def _fetch_eonet() -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                response = await client.get(
                    "https://eonet.gsfc.nasa.gov/api/v3/events",
                    params={"start": start.date().isoformat(), "status": "open"},
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    eonet_payload = await (cache.get_or_fetch(f"eonet:{days_back}", 1800, _fetch_eonet) if cache else _fetch_eonet())
    if eonet_payload:
        for item in eonet_payload.get("events", []):
            geometry = item.get("geometry", [])
            if not geometry:
                continue
            latest = geometry[-1]
            coords = latest.get("coordinates", [0, 0])
            try:
                occurred_at = datetime.fromisoformat(latest.get("date", "").replace("Z", "+00:00"))
            except Exception:
                occurred_at = datetime.now(UTC)
            events.append(
                NaturalEvent(
                    id=item.get("id", ""),
                    event_type=(item.get("categories") or [{"title": "natural"}])[0]["title"].lower(),
                    title=item.get("title", "Natural Event"),
                    location=GeoPoint(latitude=float(coords[1]), longitude=float(coords[0])),
                    occurred_at=occurred_at,
                    source="eonet",
                    details={"link": item.get("link")},
                )
            )

    # Optional FIRMS ingestion when key exists (kept lightweight for Phase 1)
    if settings.nasa_firms_api_key:
        async def _fetch_firms() -> str | None:
            url = (
                "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                f"{settings.nasa_firms_api_key}/VIIRS_SNPP_NRT/world/1/{start.date().isoformat()}"
            )
            try:
                async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text
            except Exception:
                return None

        _ = await (cache.get_or_fetch(f"firms:{days_back}", 1800, _fetch_firms) if cache else _fetch_firms())

    events.sort(key=lambda item: item.occurred_at, reverse=True)
    if db:
        await db.upsert_natural_events(events)
    return events
