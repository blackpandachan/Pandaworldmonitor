import asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from sentinel.tools.conflict import fetch_conflict_events
from sentinel.tools.dashboard import get_dashboard_state, get_map_layer_data
from sentinel.tools.gdelt import fetch_gdelt_events
from sentinel.tools.infrastructure import fetch_infrastructure_status
from sentinel.tools.intelligence import (
    compare_briefs,
    compute_risk_scores,
    generate_delta_brief,
    generate_situation_brief,
    list_brief_history,
)
from sentinel.tools.natural import fetch_natural_events
from sentinel.tools.news import fetch_news, search_news_archive
from sentinel.tools.watchlist import check_watchlist_alerts, manage_watchlist

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/news")
async def news(request: Request, max_age_hours: int = 24, tier_max: int = 3) -> list[dict]:
    data = await fetch_news(max_age_hours=max_age_hours, tier_max=tier_max, cache=request.app.state.cache, db=request.app.state.db)
    return [item.model_dump(mode="json") for item in data]


@router.get("/news/search")
async def news_search(request: Request, query: str, days_back: int = 7) -> list[dict]:
    return await search_news_archive(query=query, days_back=days_back, db=request.app.state.db)


@router.get("/conflict")
async def conflict(request: Request, country: str | None = None, days_back: int = 30) -> list[dict]:
    data = await fetch_conflict_events(country=country, days_back=days_back, cache=request.app.state.cache, db=request.app.state.db)
    return [item.model_dump(mode="json") for item in data]


@router.get("/natural")
async def natural(request: Request, days_back: int = 7, min_magnitude: float | None = None) -> list[dict]:
    data = await fetch_natural_events(days_back=days_back, min_magnitude=min_magnitude, cache=request.app.state.cache, db=request.app.state.db)
    return [item.model_dump(mode="json") for item in data]


@router.get("/infrastructure")
async def infrastructure(request: Request) -> dict:
    return await fetch_infrastructure_status(cache=request.app.state.cache, db=request.app.state.db)


@router.get("/gdelt")
async def gdelt(request: Request, query: str, mode: str = "artlist", max_results: int = 50) -> list[dict]:
    return await fetch_gdelt_events(query=query, mode=mode, max_results=max_results, cache=request.app.state.cache)


@router.post("/watchlist")
async def watchlist_manage(request: Request, payload: dict) -> dict:
    return await manage_watchlist(action=payload.get("action", "list"), item=payload.get("item"), db=request.app.state.db)


@router.get("/watchlist/alerts")
async def watchlist_alerts(request: Request) -> list[dict]:
    return await check_watchlist_alerts(db=request.app.state.db)


@router.get("/brief/situation")
async def brief_situation(request: Request, region: str | None = None, country: str | None = None, hours_back: int = 24) -> dict:
    return await generate_situation_brief(region=region, country=country, hours_back=hours_back, db=request.app.state.db)


@router.get("/brief/delta")
async def brief_delta(request: Request, hours_back: int = 6, region: str | None = None) -> dict:
    return await generate_delta_brief(hours_back=hours_back, region=region, db=request.app.state.db)


@router.get("/brief/history")
async def brief_history(request: Request, brief_type: str | None = None, limit: int = 20) -> list[dict]:
    return await list_brief_history(db=request.app.state.db, brief_type=brief_type, limit=limit)


@router.get("/brief/compare")
async def brief_compare(request: Request, first_id: int, second_id: int) -> dict:
    return await compare_briefs(db=request.app.state.db, first_id=first_id, second_id=second_id)


@router.get("/risk-scores")
async def risk_scores(request: Request, countries: str | None = None) -> list[dict]:
    parsed = countries.split(",") if countries else None
    return await compute_risk_scores(countries=parsed, db=request.app.state.db)




@router.get("/map/layers")
async def map_layers(request: Request, layers: str = "conflicts,natural,news", hours_back: int = 24) -> dict:
    parsed_layers = [layer.strip() for layer in layers.split(",") if layer.strip()]
    return await get_map_layer_data(layers=parsed_layers, hours_back=hours_back, db=request.app.state.db, cache=request.app.state.cache)


@router.get("/dashboard/state")
async def dashboard_state(request: Request) -> dict:
    return await get_dashboard_state(db=request.app.state.db, cache=request.app.state.cache)


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    app = websocket.app
    try:
        while True:
            state = await get_dashboard_state(db=app.state.db, cache=app.state.cache)
            await websocket.send_json({"type": "state_update", "data": state})
            try:
                incoming = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                if incoming.get("type") == "request_brief":
                    params = incoming.get("params", {})
                    brief = await generate_situation_brief(
                        region=params.get("region"),
                        country=params.get("country"),
                        hours_back=int(params.get("hours_back", 24)),
                        db=app.state.db,
                    )
                    await websocket.send_json({"type": "brief", "data": brief})
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        return
