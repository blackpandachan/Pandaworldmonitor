import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import feedparser
import httpx

from sentinel.analysis.classifier import classify_by_keyword
from sentinel.config import settings
from sentinel.models.news import NewsArticle
from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB


def _load_feeds() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "feeds.json"
    return json.loads(path.read_text())


def _parse_entry_datetime(entry: dict) -> datetime:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            return datetime(*parsed[:6], tzinfo=UTC)
    return datetime.now(UTC)


async def fetch_news(
    max_age_hours: int = 24,
    tier_max: int = 3,
    cache: TTLCache | None = None,
    db: SentinelDB | None = None,
) -> list[NewsArticle]:
    cutoff = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
    output: list[NewsArticle] = []
    seen_titles: set[str] = set()

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, trust_env=settings.sentinel_http_trust_env) as client:
        for feed in _load_feeds():
            if feed["tier"] > tier_max:
                continue
            cache_key = f"rss:{feed['url']}"

            async def _fetch() -> str | None:
                try:
                    response = await client.get(feed["url"])
                    response.raise_for_status()
                    return response.text
                except Exception:
                    return None

            raw = await (cache.get_or_fetch(cache_key, 600, _fetch) if cache else _fetch())
            if not raw:
                continue

            parsed = feedparser.parse(raw)
            for entry in parsed.entries:
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                normalized = " ".join(title.lower().split())
                if normalized in seen_titles:
                    continue
                published = _parse_entry_datetime(entry)
                if published.timestamp() < cutoff:
                    continue

                seen_titles.add(normalized)
                article_id = hashlib.sha256(f"{title}|{entry.get('link', '')}".encode()).hexdigest()
                output.append(
                    NewsArticle(
                        id=article_id,
                        title=title,
                        url=entry.get("link", ""),
                        source=feed["name"],
                        source_tier=feed["tier"],
                        published_at=published,
                        classification=classify_by_keyword(title),
                    )
                )

    output.sort(key=lambda item: (item.published_at, item.source_tier), reverse=True)
    if db:
        await db.upsert_articles(output)
    return output


async def search_news_archive(query: str, days_back: int = 7, db: SentinelDB | None = None) -> list[dict]:
    if not db:
        return []
    return await db.search_articles(query=query, days_back=days_back)
