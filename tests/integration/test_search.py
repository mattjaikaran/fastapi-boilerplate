import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_search_requires_auth(client: AsyncClient):
    response = await client.get("/api/search?q=test")
    assert response.status_code == 401


@pytest.mark.integration
async def test_search_returns_results_structure(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/search?q=test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "hits" in data
    assert "total" in data
    assert data["query"] == "test"


@pytest.mark.integration
async def test_search_empty_query(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/search?q=zzznoresultsexpected", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["hits"] == []
    assert data["total"] == 0


@pytest.mark.integration
async def test_search_finds_user_by_email(client: AsyncClient, auth_headers: dict, user):
    email_prefix = user.email.split("@")[0]
    response = await client.get(f"/api/search?q={email_prefix}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    user_hits = [h for h in data["hits"] if h["resource_type"] == "users"]
    assert len(user_hits) >= 1
    assert any(user.email in h["title"] for h in user_hits)


@pytest.mark.integration
async def test_search_finds_todo(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/todos",
        json={"title": "Unique searchable todo item"},
        headers=auth_headers,
    )
    response = await client.get("/api/search?q=searchable", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    todo_hits = [h for h in data["hits"] if h["resource_type"] == "todos"]
    assert any("searchable" in h["title"].lower() for h in todo_hits)


@pytest.mark.integration
async def test_search_limit_param(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/search?q=e&limit=3", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["hits"]) <= 3
