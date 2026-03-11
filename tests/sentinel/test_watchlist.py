from datetime import UTC, datetime

from sentinel.models.news import Classification, NewsArticle
from sentinel.storage.db import SentinelDB
from sentinel.tools.watchlist import check_watchlist_alerts, manage_watchlist


async def test_watchlist_alert_matching(tmp_path) -> None:
    db = SentinelDB(str(tmp_path / "watch.db"))
    await db.initialize()

    await manage_watchlist(action="add", item={"type": "country", "value": "ukraine", "notify_severity": "medium"}, db=db)

    article = NewsArticle(
        id="w1",
        title="Ukraine reports new missile strike",
        url="https://example.com/w1",
        source="Example",
        source_tier=1,
        published_at=datetime.now(UTC),
        classification=Classification(severity="high", category="conflict", confidence=0.8, source="keyword"),
    )
    await db.upsert_articles([article])

    alerts = await check_watchlist_alerts(db=db)
    assert alerts
    assert alerts[0]["item"]["value"].lower() == "ukraine"
