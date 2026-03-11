from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from sentinel.api.server import router as api_router
from sentinel.config import settings
from sentinel.pipeline.scheduler import build_scheduler
from sentinel.storage.cache import TTLCache
from sentinel.storage.db import SentinelDB
from sentinel.tools.conflict import fetch_conflict_events
from sentinel.tools.dashboard import get_dashboard_state, get_map_layer_data
from sentinel.tools.gdelt import fetch_gdelt_events
from sentinel.tools.infrastructure import fetch_infrastructure_status
from sentinel.tools.intelligence import (
    classify_articles,
    compute_risk_scores,
    detect_convergence,
    generate_delta_brief,
    generate_situation_brief,
    list_brief_history,
    compare_briefs,
)
from sentinel.tools.natural import fetch_natural_events
from sentinel.tools.news import fetch_news, search_news_archive
from sentinel.tools.watchlist import check_watchlist_alerts, manage_watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SentinelDB()
    await db.initialize()
    cache = TTLCache()
    app.state.db = db
    app.state.cache = cache
    scheduler = build_scheduler(db=db, cache=cache)
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Sentinel", lifespan=lifespan)
app.include_router(api_router)

mcp = FastMCP(name="sentinel")


@mcp.tool()
async def mcp_fetch_news(max_age_hours: int = 24, tier_max: int = 3) -> list[dict]:
    return [item.model_dump(mode="json") for item in await fetch_news(max_age_hours=max_age_hours, tier_max=tier_max, cache=app.state.cache, db=app.state.db)]


@mcp.tool()
async def mcp_fetch_conflict_events(country: str | None = None, days_back: int = 30) -> list[dict]:
    return [item.model_dump(mode="json") for item in await fetch_conflict_events(country=country, days_back=days_back, cache=app.state.cache, db=app.state.db)]


@mcp.tool()
async def mcp_fetch_natural_events(days_back: int = 7, min_magnitude: float | None = None) -> list[dict]:
    return [
        item.model_dump(mode="json")
        for item in await fetch_natural_events(days_back=days_back, min_magnitude=min_magnitude, cache=app.state.cache, db=app.state.db)
    ]


@mcp.tool()
async def mcp_fetch_infrastructure_status(check_types: list[str] | None = None) -> dict:
    return await fetch_infrastructure_status(check_types=check_types, cache=app.state.cache, db=app.state.db)


@mcp.tool()
async def mcp_fetch_gdelt_events(query: str, mode: str = "artlist", max_results: int = 50) -> list[dict]:
    return await fetch_gdelt_events(query=query, mode=mode, max_results=max_results, cache=app.state.cache)


@mcp.tool()
async def mcp_search_news_archive(query: str, days_back: int = 7) -> list[dict]:
    return await search_news_archive(query=query, days_back=days_back, db=app.state.db)


@mcp.tool()
async def mcp_classify_articles(articles: list[dict]) -> list[dict]:
    return await classify_articles(articles=articles)


@mcp.tool()
async def mcp_generate_situation_brief(region: str | None = None, country: str | None = None, hours_back: int = 24) -> dict:
    return await generate_situation_brief(region=region, country=country, hours_back=hours_back, db=app.state.db)


@mcp.tool()
async def mcp_generate_delta_brief(hours_back: int = 6, region: str | None = None) -> dict:
    return await generate_delta_brief(hours_back=hours_back, region=region, db=app.state.db)


@mcp.tool()
async def mcp_compute_risk_scores(countries: list[str] | None = None) -> list[dict]:
    return await compute_risk_scores(countries=countries, db=app.state.db)


@mcp.tool()
async def mcp_detect_convergence(hours_back: int = 24, min_event_types: int = 3) -> list[dict]:
    return await detect_convergence(hours_back=hours_back, min_event_types=min_event_types, db=app.state.db)


@mcp.tool()
async def mcp_manage_watchlist(action: str, item: dict | None = None) -> dict:
    return await manage_watchlist(action=action, item=item, db=app.state.db)


@mcp.tool()
async def mcp_check_watchlist_alerts() -> list[dict]:
    return await check_watchlist_alerts(db=app.state.db)


@mcp.tool()
async def mcp_get_map_layer_data(layers: list[str], hours_back: int = 24) -> dict:
    return await get_map_layer_data(layers=layers, hours_back=hours_back, db=app.state.db, cache=app.state.cache)


@mcp.tool()
async def mcp_list_brief_history(brief_type: str | None = None, limit: int = 20) -> list[dict]:
    return await list_brief_history(db=app.state.db, brief_type=brief_type, limit=limit)


@mcp.tool()
async def mcp_compare_briefs(first_id: int, second_id: int) -> dict:
    return await compare_briefs(db=app.state.db, first_id=first_id, second_id=second_id)


@mcp.tool()
async def mcp_get_dashboard_state() -> dict:
    return await get_dashboard_state(db=app.state.db, cache=app.state.cache)


app.mount("/mcp", mcp.streamable_http_app())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("sentinel.main:app", host=settings.sentinel_host, port=settings.sentinel_port, reload=False)
