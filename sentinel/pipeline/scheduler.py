from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB
from sentinel.tools.conflict import fetch_conflict_events
from sentinel.tools.infrastructure import fetch_infrastructure_status
from sentinel.tools.natural import fetch_natural_events
from sentinel.tools.news import fetch_news


def build_scheduler(db: SentinelDB, cache: TTLCache) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(fetch_news, "interval", minutes=15, kwargs={"db": db, "cache": cache}, id="rss_feeds")
    scheduler.add_job(fetch_natural_events, "interval", minutes=5, kwargs={"db": db, "cache": cache, "days_back": 1}, id="earthquakes")
    scheduler.add_job(fetch_conflict_events, "interval", minutes=30, kwargs={"db": db, "cache": cache}, id="conflict")
    scheduler.add_job(fetch_infrastructure_status, "interval", minutes=60, kwargs={"db": db, "cache": cache}, id="infrastructure")
    return scheduler
