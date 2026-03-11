import json
from datetime import UTC, datetime

import aiosqlite

from sentinel.config import settings
from sentinel.models.events import ConflictEvent, NaturalEvent
from sentinel.models.news import NewsArticle
from sentinel.models.watchlist import WatchlistItem


class SentinelDB:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.sentinel_db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_tier INTEGER NOT NULL,
                    published_at TEXT NOT NULL,
                    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    classification_json TEXT,
                    location_json TEXT,
                    entities_json TEXT,
                    summary TEXT
                );
                CREATE TABLE IF NOT EXISTS conflict_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    country TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    occurred_at TEXT NOT NULL,
                    fatalities INTEGER DEFAULT 0,
                    actors_json TEXT,
                    source TEXT NOT NULL,
                    admin1 TEXT,
                    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS natural_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    occurred_at TEXT NOT NULL,
                    magnitude REAL,
                    source TEXT NOT NULL,
                    details_json TEXT,
                    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    notify_severity TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    region TEXT,
                    country TEXT,
                    brief_text TEXT NOT NULL,
                    model TEXT NOT NULL,
                    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS data_freshness (
                    source TEXT PRIMARY KEY,
                    last_success TEXT,
                    last_error TEXT,
                    error_message TEXT,
                    status TEXT NOT NULL DEFAULT 'unknown'
                );
                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_conflict_occurred ON conflict_events(occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_natural_occurred ON natural_events(occurred_at DESC);
                """
            )
            await db.commit()

    async def record_source_status(self, source: str, status: str, error_message: str | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            if status == "ok":
                await db.execute(
                    """
                    INSERT INTO data_freshness (source, last_success, status, error_message)
                    VALUES (?, ?, 'ok', NULL)
                    ON CONFLICT(source) DO UPDATE SET last_success=excluded.last_success, status='ok', error_message=NULL
                    """,
                    (source, now),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO data_freshness (source, last_error, status, error_message)
                    VALUES (?, ?, 'error', ?)
                    ON CONFLICT(source) DO UPDATE SET last_error=excluded.last_error, status='error', error_message=excluded.error_message
                    """,
                    (source, now, error_message or "unknown"),
                )
            await db.commit()

    async def get_data_freshness(self) -> dict[str, str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT source, COALESCE(last_success, last_error) FROM data_freshness")
            rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    async def upsert_articles(self, articles: list[NewsArticle]) -> None:
        if not articles:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT INTO articles (id, title, url, source, source_tier, published_at, classification_json, location_json, entities_json, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    source=excluded.source,
                    source_tier=excluded.source_tier,
                    classification_json=excluded.classification_json,
                    summary=excluded.summary
                """,
                [
                    (
                        a.id,
                        a.title,
                        a.url,
                        a.source,
                        a.source_tier,
                        a.published_at.isoformat(),
                        json.dumps(a.classification.model_dump()) if a.classification else None,
                        json.dumps(a.location.model_dump()) if a.location else None,
                        json.dumps(a.entities),
                        a.summary,
                    )
                    for a in articles
                ],
            )
            await db.commit()

    async def get_recent_articles(self, hours_back: int = 24, limit: int = 200) -> list[dict]:
        cutoff = datetime.fromtimestamp(datetime.now(UTC).timestamp() - (hours_back * 3600), tz=UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, title, url, source, source_tier, published_at, classification_json
                FROM articles WHERE published_at >= ?
                ORDER BY published_at DESC LIMIT ?
                """,
                (cutoff, limit),
            )
            rows = await cursor.fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "title": r[1],
                    "url": r[2],
                    "source": r[3],
                    "source_tier": r[4],
                    "published_at": r[5],
                    "classification": json.loads(r[6]) if r[6] else None,
                }
            )
        return out

    async def upsert_conflict_events(self, events: list[ConflictEvent]) -> None:
        if not events:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT INTO conflict_events (id, event_type, country, latitude, longitude, occurred_at, fatalities, actors_json, source, admin1)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                [
                    (
                        e.id,
                        e.event_type,
                        e.country,
                        e.location.latitude,
                        e.location.longitude,
                        e.occurred_at.isoformat(),
                        e.fatalities,
                        json.dumps(e.actors),
                        e.source,
                        e.admin1,
                    )
                    for e in events
                ],
            )
            await db.commit()

    async def upsert_natural_events(self, events: list[NaturalEvent]) -> None:
        if not events:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT INTO natural_events (id, event_type, title, latitude, longitude, occurred_at, magnitude, source, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                [
                    (
                        e.id,
                        e.event_type,
                        e.title,
                        e.location.latitude,
                        e.location.longitude,
                        e.occurred_at.isoformat(),
                        e.magnitude,
                        e.source,
                        json.dumps(e.details),
                    )
                    for e in events
                ],
            )
            await db.commit()

    async def search_articles(self, query: str, days_back: int = 7) -> list[dict]:
        cutoff = (datetime.now(UTC)).timestamp() - days_back * 86400
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=UTC).isoformat()
        pattern = f"%{query.lower()}%"
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, title, url, source, published_at FROM articles
                WHERE lower(title) LIKE ? AND published_at >= ?
                ORDER BY published_at DESC
                LIMIT 200
                """,
                (pattern, cutoff_iso),
            )
            rows = await cursor.fetchall()
        return [{"id": r[0], "title": r[1], "url": r[2], "source": r[3], "published_at": r[4]} for r in rows]

    async def manage_watchlist(self, action: str, item: WatchlistItem | None = None) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            if action == "add" and item:
                await db.execute(
                    "INSERT INTO watchlist(type, value, notify_severity) VALUES (?, ?, ?)",
                    (item.type, item.value, item.notify_severity),
                )
                await db.commit()
            elif action == "remove" and item:
                await db.execute(
                    "DELETE FROM watchlist WHERE type = ? AND value = ?",
                    (item.type, item.value),
                )
                await db.commit()
            cursor = await db.execute("SELECT type, value, notify_severity, created_at FROM watchlist ORDER BY id DESC")
            rows = await cursor.fetchall()
        return [{"type": r[0], "value": r[1], "notify_severity": r[2], "created_at": r[3]} for r in rows]

    async def store_brief(self, brief_type: str, brief_text: str, model: str, region: str | None = None, country: str | None = None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO briefs(type, region, country, brief_text, model) VALUES (?, ?, ?, ?, ?)",
                (brief_type, region, country, brief_text, model),
            )
            await db.commit()

    async def latest_brief(self) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT type, region, country, brief_text, model, generated_at FROM briefs ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "type": row[0],
            "region": row[1],
            "country": row[2],
            "brief_text": row[3],
            "model": row[4],
            "generated_at": row[5],
        }
