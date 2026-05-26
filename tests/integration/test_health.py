import pytest
from httpx import AsyncClient


@pytest.mark.smoke
async def test_liveness(client: AsyncClient):
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.smoke
async def test_info(client: AsyncClient):
    response = await client.get("/api/health/info")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "version" in data
