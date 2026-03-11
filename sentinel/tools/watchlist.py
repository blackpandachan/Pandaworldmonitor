from datetime import UTC, datetime

from sentinel.storage.db import SentinelDB


async def manage_watchlist(action: str, item: dict | None = None, db: SentinelDB | None = None) -> dict:
    if not db:
        return {"items": []}
    from sentinel.models.watchlist import WatchlistItem

    parsed = WatchlistItem(**item) if item else None
    items = await db.manage_watchlist(action=action, item=parsed)
    return {"items": items}


async def check_watchlist_alerts(db: SentinelDB | None = None) -> list[dict]:
    if not db:
        return []
    watch_items = await db.manage_watchlist(action="list")
    recent = await db.get_recent_articles(hours_back=24, limit=500)
    alerts: list[dict] = []
    for item in watch_items:
        value = item["value"].lower()
        for article in recent:
            if value in article["title"].lower():
                alerts.append(
                    {
                        "item": item,
                        "severity": (article.get("classification") or {}).get("severity", "info"),
                        "reason": f"Matched watchlist term '{item['value']}' in headline",
                        "article_id": article["id"],
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                )
    return alerts[:100]
