from datetime import UTC, date, datetime, time, timedelta

import httpx

from sentinel.config import settings
from sentinel.models.events import ConflictEvent
from sentinel.models.geo import GeoPoint
from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB


def _parse_occurred(value: str, fallback: date) -> datetime:
    try:
        parsed_date = date.fromisoformat(value)
        return datetime.combine(parsed_date, time.min, tzinfo=UTC)
    except Exception:
        return datetime.combine(fallback, time.min, tzinfo=UTC)


async def fetch_conflict_events(
    country: str | None = None,
    days_back: int = 30,
    cache: TTLCache | None = None,
    db: SentinelDB | None = None,
) -> list[ConflictEvent]:
    if not settings.acled_api_key or not settings.acled_email:
        return []

    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days_back)
    params = {
        "key": settings.acled_api_key,
        "email": settings.acled_email,
        "event_date": f"{start_date.isoformat()}|{end_date.isoformat()}",
        "event_date_where": "BETWEEN",
        "limit": 500,
    }
    if country:
        params["country"] = country

    cache_key = f"acled:{country or 'all'}:{days_back}"

    async def _fetch() -> list[dict] | None:
        try:
            async with httpx.AsyncClient(timeout=20.0, trust_env=settings.sentinel_http_trust_env) as client:
                response = await client.get("https://api.acleddata.com/acled/read", params=params)
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception:
            return None

    payload = await (cache.get_or_fetch(cache_key, 900, _fetch) if cache else _fetch())
    if not payload:
        return []

    events: list[ConflictEvent] = []
    for row in payload:
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            identifier = str(row.get("event_id_cnty") or row.get("event_id_no_cnty") or "")
            if not identifier:
                continue
            events.append(
                ConflictEvent(
                    id=identifier,
                    event_type=row.get("event_type", "unknown"),
                    country=row.get("country", "unknown"),
                    location=GeoPoint(latitude=lat, longitude=lon),
                    occurred_at=_parse_occurred(str(row.get("event_date", "")), end_date),
                    fatalities=int(row.get("fatalities") or 0),
                    actors=[a for a in [row.get("actor1", ""), row.get("actor2", "")] if a],
                    source="acled",
                    admin1=row.get("admin1", ""),
                )
            )
        except Exception:
            continue

    if db:
        await db.upsert_conflict_events(events)
    return events
