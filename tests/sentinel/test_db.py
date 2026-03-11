from datetime import UTC, datetime

from sentinel.models.news import NewsArticle
from sentinel.storage.db import SentinelDB


async def test_upsert_and_search_articles(tmp_path) -> None:
    db = SentinelDB(str(tmp_path / "test.db"))
    await db.initialize()
    article = NewsArticle(
        id="a1",
        title="Missile strike reported",
        url="https://example.com/1",
        source="Example",
        source_tier=1,
        published_at=datetime.now(UTC),
    )
    await db.upsert_articles([article])
    rows = await db.search_articles("missile", days_back=7)
    assert rows
    assert rows[0]["id"] == "a1"
