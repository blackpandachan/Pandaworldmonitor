from sentinel.storage.db import SentinelDB
from sentinel.tools.conflict import fetch_conflict_events
from sentinel.tools.infrastructure import fetch_infrastructure_status
from sentinel.tools.intelligence import compute_risk_scores, detect_convergence
from sentinel.tools.natural import fetch_natural_events
from sentinel.tools.news import fetch_news
from sentinel.tools.watchlist import check_watchlist_alerts


async def get_map_layer_data(layers: list[str], hours_back: int = 24, db: SentinelDB | None = None, cache=None) -> dict:
    payload: dict = {"layers": {}}
    if "conflicts" in layers:
        payload["layers"]["conflicts"] = [e.model_dump(mode="json") for e in await fetch_conflict_events(days_back=max(1, hours_back // 24), db=db, cache=cache)]
    if "natural" in layers or "fires" in layers:
        payload["layers"]["natural"] = [e.model_dump(mode="json") for e in await fetch_natural_events(days_back=max(1, hours_back // 24), db=db, cache=cache)]
    if "news" in layers:
        payload["layers"]["news"] = [a.model_dump(mode="json") for a in await fetch_news(max_age_hours=hours_back, db=db, cache=cache)]
    if "outages" in layers:
        payload["layers"]["outages"] = await fetch_infrastructure_status(cache=cache, db=db)
    return payload


async def get_dashboard_state(db: SentinelDB | None = None, cache=None) -> dict:
    articles = await fetch_news(max_age_hours=24, db=db, cache=cache)
    risk_scores = await compute_risk_scores(db=db)
    convergence_alerts = await detect_convergence(db=db)
    watchlist_alerts = await check_watchlist_alerts(db=db)
    data_freshness = await db.get_data_freshness() if db else {}
    last_brief = await db.latest_brief() if db else None
    return {
        "articles": [a.model_dump(mode="json") for a in articles[:100]],
        "risk_scores": risk_scores,
        "convergence_alerts": convergence_alerts,
        "watchlist_alerts": watchlist_alerts,
        "data_freshness": data_freshness,
        "last_brief": last_brief,
    }
