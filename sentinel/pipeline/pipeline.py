from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB
from sentinel.tools.conflict import fetch_conflict_events
from sentinel.tools.infrastructure import fetch_infrastructure_status
from sentinel.tools.natural import fetch_natural_events
from sentinel.tools.news import fetch_news


async def run_ingest_cycle(db: SentinelDB, cache: TTLCache) -> dict:
    news = await fetch_news(db=db, cache=cache)
    conflicts = await fetch_conflict_events(db=db, cache=cache)
    natural = await fetch_natural_events(db=db, cache=cache)
    infra = await fetch_infrastructure_status(db=db, cache=cache)
    return {
        "news": len(news),
        "conflicts": len(conflicts),
        "natural": len(natural),
        "infra_ok": bool(infra),
    }
