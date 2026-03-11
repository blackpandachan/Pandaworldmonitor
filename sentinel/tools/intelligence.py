import json
from datetime import UTC, datetime, timedelta

from sentinel.providers.router import LLMRouter
from sentinel.storage.db import SentinelDB


def _risk_from_articles(articles: list[dict], country_code: str) -> float:
    score = 10.0
    for article in articles:
        text = article["title"].lower()
        if country_code.lower() in text:
            sev = (article.get("classification") or {}).get("severity", "info")
            score += {"critical": 20, "high": 12, "medium": 6, "low": 2, "info": 1}.get(sev, 1)
    return min(100.0, score)


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


async def generate_situation_brief(region: str | None = None, country: str | None = None, hours_back: int = 24, db: SentinelDB | None = None, router: LLMRouter | None = None) -> dict:
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
    recent = await db.get_recent_articles(hours_back=48, limit=1000) if db else []
    out = []
    for code in countries:
        score = _risk_from_articles(recent, code)
        out.append(
            {
                "country_code": code,
                "country_name": code,
                "score": score,
                "components": {"baseline": 10, "info_velocity": max(0, score - 10)},
                "trend": "rising" if score >= 40 else "stable",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    return out


async def detect_convergence(hours_back: int = 24, min_event_types: int = 3, db: SentinelDB | None = None) -> list[dict]:
    articles = await db.get_recent_articles(hours_back=hours_back, limit=300) if db else []
    categories = {(a.get("classification") or {}).get("category", "general") for a in articles}
    if len(categories) < min_event_types:
        return []
    return [
        {
            "grid_cell": "global",
            "location_name": "Global",
            "event_types": sorted(list(categories))[:8],
            "event_count": len(articles),
            "score": min(100.0, len(articles) * 0.2 + len(categories) * 15),
            "explanation": "Multiple event categories are active simultaneously.",
            "events": articles[:10],
        }
    ]
