from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_todo(client: AsyncClient, auth_headers: dict) -> None:
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
async def test_list_todos(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/api/todos", json={"title": "Todo 1"}, headers=auth_headers)
    await client.post("/api/todos", json={"title": "Todo 2"}, headers=auth_headers)

    response = await client.get("/api/todos", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert "pages" in data


@pytest.mark.integration
async def test_update_todo(client: AsyncClient, auth_headers: dict) -> None:
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
async def test_delete_todo(client: AsyncClient, auth_headers: dict) -> None:
    create = await client.post("/api/todos", json={"title": "Delete me"}, headers=auth_headers)
    todo_id = create.json()["id"]

    response = await client.delete(f"/api/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/todos/{todo_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.integration
async def test_toggle_todo(client: AsyncClient, auth_headers: dict) -> None:
    create = await client.post("/api/todos", json={"title": "Toggle me"}, headers=auth_headers)
    todo_id = create.json()["id"]
    assert not create.json()["is_completed"]

    toggled = await client.post(f"/api/todos/{todo_id}/toggle", headers=auth_headers)
    assert toggled.status_code == 200
    assert toggled.json()["is_completed"] is True

    toggled_back = await client.post(f"/api/todos/{todo_id}/toggle", headers=auth_headers)
    assert toggled_back.json()["is_completed"] is False


@pytest.mark.integration
async def test_stats_endpoint(client: AsyncClient, auth_headers: dict) -> None:
    # Create a mix
    await client.post("/api/todos", json={"title": "Pending"}, headers=auth_headers)
    r = await client.post("/api/todos", json={"title": "Completed"}, headers=auth_headers)
    await client.post(f"/api/todos/{r.json()['id']}/toggle", headers=auth_headers)

    resp = await client.get("/api/todos/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "completed" in data
    assert "pending" in data
    assert "overdue" in data
    assert "due_today" in data
    assert set(data["by_priority"].keys()) == {"low", "medium", "high"}


@pytest.mark.integration
async def test_search_todos(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/api/todos",
        json={"title": "Learn FastAPI the hard way"},
        headers=auth_headers,
    )
    resp = await client.get("/api/todos?search=FastAPI", headers=auth_headers)
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()["items"]]
    assert any("FastAPI" in t for t in titles)


@pytest.mark.integration
async def test_filter_by_priority(client: AsyncClient, auth_headers: dict) -> None:
    for priority in ["low", "medium", "high"]:
        await client.post(
            "/api/todos",
            json={"title": f"Task {priority}", "priority": priority},
            headers=auth_headers,
        )

    resp = await client.get("/api/todos?priority=high", headers=auth_headers)
    assert resp.status_code == 200
    assert all(t["priority"] == "high" for t in resp.json()["items"])


@pytest.mark.integration
async def test_bulk_update(client: AsyncClient, auth_headers: dict) -> None:
    ids = []
    for i in range(3):
        r = await client.post(
            "/api/todos", json={"title": f"Bulk {i}"}, headers=auth_headers
        )
        ids.append(r.json()["id"])

    resp = await client.patch(
        "/api/todos/bulk",
        json={"ids": ids, "is_completed": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert all(t["is_completed"] is True for t in resp.json())


@pytest.mark.integration
async def test_bulk_delete(client: AsyncClient, auth_headers: dict) -> None:
    ids = []
    for i in range(2):
        r = await client.post(
            "/api/todos", json={"title": f"BulkDel {i}"}, headers=auth_headers
        )
        ids.append(r.json()["id"])

    resp = await client.post(
        "/api/todos/bulk-delete", json={"ids": ids}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2


@pytest.mark.integration
async def test_todos_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/todos")
    assert response.status_code == 401


@pytest.mark.integration
async def test_cannot_access_other_users_todo(
    client: AsyncClient, auth_headers: dict, admin_headers: dict
) -> None:
    r = await client.post(
        "/api/todos", json={"title": "Private"}, headers=auth_headers
    )
    todo_id = r.json()["id"]

    resp = await client.get(f"/api/todos/{todo_id}", headers=admin_headers)
    assert resp.status_code in (403, 404)
