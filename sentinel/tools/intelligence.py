import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sentinel.providers.router import LLMRouter
from sentinel.storage.db import SentinelDB

COUNTRY_BASELINES = {
    "UA": 55,
    "SY": 50,
    "IL": 48,
    "RU": 45,
    "IR": 42,
    "US": 22,
    "CH": 8,
}

COUNTRY_ALIASES = {
    "UA": ["ukraine", "kyiv"],
    "SY": ["syria", "damascus"],
    "IL": ["israel", "tel aviv", "gaza"],
    "US": ["united states", "u.s.", "america", "washington"],
    "CH": ["switzerland", "bern", "zurich"],
}

SEVERITY_WEIGHTS = {"critical": 20, "high": 12, "medium": 6, "low": 2, "info": 1}


def _article_mentions_country(title: str, country_code: str) -> bool:
    lower = title.lower()
    aliases = COUNTRY_ALIASES.get(country_code, [country_code.lower()])
    return any(token in lower for token in aliases)


async def classify_articles(articles: list[dict], router: LLMRouter | None = None) -> list[dict]:
    router = router or LLMRouter()
    out: list[dict] = []
    for item in articles:
        base = item.get("classification")
        if base:
            out.append(item)
            continue
        result = await router.complete(
            tier="volume",
            messages=[{"role": "user", "content": f"Classify severity/category for: {item.get('title','')}"}],
            timeout=10.0,
        )
        if result:
            item["llm_classification"] = result.content
        out.append(item)
    return out


async def generate_situation_brief(
    region: str | None = None,
    country: str | None = None,
    hours_back: int = 24,
    db: SentinelDB | None = None,
    router: LLMRouter | None = None,
) -> dict:
    router = router or LLMRouter()
    articles = await db.get_recent_articles(hours_back=hours_back, limit=120) if db else []
    prompt = {
        "region": region,
        "country": country,
        "hours_back": hours_back,
        "article_count": len(articles),
        "top_headlines": [a["title"] for a in articles[:15]],
    }
    response = await router.complete(
        tier="quality",
        messages=[
            {"role": "system", "content": "You are a senior intelligence analyst."},
            {"role": "user", "content": f"Generate concise situation brief JSON from: {json.dumps(prompt)}"},
        ],
        timeout=20.0,
    )
    brief_text = response.content if response else "No model response available."
    brief = {
        "region": region,
        "country": country,
        "generated_at": datetime.now(UTC).isoformat(),
        "brief": brief_text,
        "sources_used": len(articles),
        "model": response.model if response else "none",
    }
    if db:
        await db.store_brief("situation", brief_text=brief_text, model=brief["model"], region=region, country=country)
    return brief


async def generate_delta_brief(hours_back: int = 6, region: str | None = None, db: SentinelDB | None = None, router: LLMRouter | None = None) -> dict:
    router = router or LLMRouter()
    now_items = await db.get_recent_articles(hours_back=hours_back, limit=200) if db else []
    prev_window_start = datetime.now(UTC) - timedelta(hours=hours_back * 2)
    prev_items = []
    if db:
        prev = await db.get_recent_articles(hours_back=hours_back * 2, limit=400)
        prev_items = [a for a in prev if a["published_at"] < prev_window_start.isoformat()]
    delta = {
        "new_count": len(now_items),
        "previous_count": len(prev_items),
        "new_headlines": [a["title"] for a in now_items[:10]],
    }
    response = await router.complete(
        tier="quality",
        messages=[{"role": "user", "content": f"Generate delta brief from this JSON: {json.dumps(delta)}"}],
        timeout=20.0,
    )
    brief_text = response.content if response else "No model response available."
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "comparing_to": prev_window_start.isoformat(),
        "brief": brief_text,
        "new_developments": delta["new_headlines"],
        "model": response.model if response else "none",
        "region": region,
    }
    if db:
        await db.store_brief("delta", brief_text=brief_text, model=payload["model"], region=region)
    return payload


async def compute_risk_scores(countries: list[str] | None = None, db: SentinelDB | None = None) -> list[dict]:
    countries = countries or ["UA", "SY", "IL", "US", "CH"]
    if not db:
        return []

    articles_48h = await db.get_recent_articles(hours_back=48, limit=2000)
    conflicts_48h = await db.get_recent_conflict_events(hours_back=48, limit=2000)

    now_cutoff = datetime.now(UTC) - timedelta(hours=24)
    out: list[dict] = []

    for code in countries:
        baseline = float(COUNTRY_BASELINES.get(code, 12))

        matching_articles = [a for a in articles_48h if _article_mentions_country(a["title"], code)]
        info_velocity = min(25.0, sum(SEVERITY_WEIGHTS.get((a.get("classification") or {}).get("severity", "info"), 1) for a in matching_articles) * 0.3)

        recent_articles = [a for a in matching_articles if datetime.fromisoformat(a["published_at"]) >= now_cutoff]
        previous_articles = [a for a in matching_articles if datetime.fromisoformat(a["published_at"]) < now_cutoff]
        recent_velocity = sum(SEVERITY_WEIGHTS.get((a.get("classification") or {}).get("severity", "info"), 1) for a in recent_articles)
        previous_velocity = sum(SEVERITY_WEIGHTS.get((a.get("classification") or {}).get("severity", "info"), 1) for a in previous_articles)

        unrest_events = [e for e in conflicts_48h if e["country"].upper() == code]
        unrest_component = min(25.0, len(unrest_events) * 2.2 + sum(max(0, e.get("fatalities", 0)) for e in unrest_events) * 0.15)

        security_mentions = [
            a
            for a in matching_articles
            if (a.get("classification") or {}).get("category", "general") in {"conflict", "military", "terrorism"}
        ]
        security_component = min(25.0, len(security_mentions) * 1.8)

        score = baseline * 0.4 + unrest_component * 0.2 + security_component * 0.2 + info_velocity * 0.2
        floor = COUNTRY_BASELINES.get(code, 0)
        score = max(float(floor), min(100.0, score))

        trend = "stable"
        if recent_velocity > previous_velocity * 1.15:
            trend = "rising"
        elif previous_velocity > 0 and recent_velocity < previous_velocity * 0.85:
            trend = "falling"

        out.append(
            {
                "country_code": code,
                "country_name": code,
                "score": round(score, 2),
                "components": {
                    "baseline": round(baseline, 2),
                    "unrest": round(unrest_component, 2),
                    "security": round(security_component, 2),
                    "info_velocity": round(info_velocity, 2),
                },
                "trend": trend,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    return out


def _grid_cell(lat: float, lon: float) -> str:
    return f"{math.floor(lat)},{math.floor(lon)}"


async def detect_convergence(hours_back: int = 24, min_event_types: int = 3, db: SentinelDB | None = None) -> list[dict]:
    if not db:
        return []

    conflicts = await db.get_recent_conflict_events(hours_back=hours_back, limit=1000)
    natural = await db.get_recent_natural_events(hours_back=hours_back, limit=1000)
    articles = await db.get_recent_articles(hours_back=hours_back, limit=400)

    buckets: dict[str, dict] = defaultdict(lambda: {"event_types": set(), "events": []})

    for event in conflicts:
        cell = _grid_cell(event["latitude"], event["longitude"])
        buckets[cell]["event_types"].add("conflict")
        buckets[cell]["events"].append({"type": event.get("event_type", "conflict"), "source": "conflict", **event})

    for event in natural:
        cell = _grid_cell(event["latitude"], event["longitude"])
        buckets[cell]["event_types"].add("natural")
        buckets[cell]["events"].append({"type": event.get("event_type", "natural"), "source": "natural", **event})

    for article in articles:
        location = article.get("location")
        if not location:
            continue
        lat = location.get("latitude")
        lon = location.get("longitude")
        if lat is None or lon is None:
            continue
        cell = _grid_cell(float(lat), float(lon))
        cat = (article.get("classification") or {}).get("category", "news")
        buckets[cell]["event_types"].add(cat)
        buckets[cell]["events"].append({"type": cat, "source": "news", **article})

    alerts: list[dict] = []
    for cell, payload in buckets.items():
        distinct = payload["event_types"]
        if len(distinct) < min_event_types:
            continue
        events = payload["events"]
        score = min(100.0, len(distinct) * 22 + len(events) * 2.5)
        alerts.append(
            {
                "grid_cell": cell,
                "location_name": f"Cell {cell}",
                "event_types": sorted(list(distinct)),
                "event_count": len(events),
                "score": round(score, 2),
                "explanation": f"{len(distinct)} signal types converged across {len(events)} events in the same grid cell.",
                "events": events[:10],
            }
        )

    alerts.sort(key=lambda item: item["score"], reverse=True)
    return alerts[:20]


async def list_brief_history(db: SentinelDB, brief_type: str | None = None, limit: int = 20) -> list[dict]:
    return await db.list_briefs(limit=limit, brief_type=brief_type)


async def compare_briefs(db: SentinelDB, first_id: int, second_id: int) -> dict:
    first = await db.get_brief_by_id(first_id)
    second = await db.get_brief_by_id(second_id)
    if not first or not second:
        return {"error": "One or both brief IDs were not found."}

    first_words = set(first["brief_text"].lower().split())
    second_words = set(second["brief_text"].lower().split())
    added = sorted(second_words - first_words)[:25]
    removed = sorted(first_words - second_words)[:25]
    overlap = len(first_words & second_words)

    return {
        "first": first,
        "second": second,
        "summary": {
            "shared_terms": overlap,
            "added_terms": added,
            "removed_terms": removed,
        },
    }
