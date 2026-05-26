import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_todo(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/todos",
        json={"title": "My first todo", "priority": "high"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My first todo"
    assert data["priority"] == "high"
    assert not data["is_completed"]


@pytest.mark.integration
async def test_list_todos(client: AsyncClient, auth_headers: dict):
    await client.post("/api/todos", json={"title": "Todo 1"}, headers=auth_headers)
    await client.post("/api/todos", json={"title": "Todo 2"}, headers=auth_headers)

    response = await client.get("/api/todos", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.integration
async def test_update_todo(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/todos", json={"title": "Update me"}, headers=auth_headers)
    todo_id = create.json()["id"]

    response = await client.patch(
        f"/api/todos/{todo_id}",
        json={"is_completed": True, "title": "Updated"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_completed"] is True
    assert response.json()["title"] == "Updated"


@pytest.mark.integration
async def test_delete_todo(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/todos", json={"title": "Delete me"}, headers=auth_headers)
    todo_id = create.json()["id"]

    response = await client.delete(f"/api/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.integration
async def test_todos_require_auth(client: AsyncClient):
    response = await client.get("/api/todos")
    assert response.status_code == 401
