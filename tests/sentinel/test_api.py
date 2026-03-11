from httpx import ASGITransport, AsyncClient

from sentinel.main import app


async def test_health_endpoint() -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_natural_endpoint_returns_list() -> None:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/natural", params={"days_back": 1})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
