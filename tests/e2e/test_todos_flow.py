"""E2E: todos user journeys — create, filter, stats, bulk ops."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestTodosJourney:
    async def test_full_todo_lifecycle(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create
        create_resp = await client.post(
            "/api/todos",
            json={"title": "Buy groceries", "priority": "high"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        todo_id = create_resp.json()["id"]
        assert create_resp.json()["is_completed"] is False

        # Get
        get_resp = await client.get(f"/api/todos/{todo_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Buy groceries"

        # Toggle
        toggle_resp = await client.post(
            f"/api/todos/{todo_id}/toggle", headers=auth_headers
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_completed"] is True

        # Update
        update_resp = await client.patch(
            f"/api/todos/{todo_id}",
            json={"title": "Buy groceries and cook dinner"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        assert "groceries" in update_resp.json()["title"]

        # Delete
        del_resp = await client.delete(f"/api/todos/{todo_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        # Verify gone
        gone_resp = await client.get(f"/api/todos/{todo_id}", headers=auth_headers)
        assert gone_resp.status_code == 404

    async def test_list_with_filters(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create todos with different priorities
        for priority in ["low", "medium", "high"]:
            await client.post(
                "/api/todos",
                json={"title": f"Task {priority}", "priority": priority},
                headers=auth_headers,
            )

        # Filter by priority
        resp = await client.get(
            "/api/todos?priority=high", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["priority"] == "high" for t in data["items"])

    async def test_search_todos(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post(
            "/api/todos",
            json={"title": "Unique banana task 99"},
            headers=auth_headers,
        )
        resp = await client.get("/api/todos?search=banana", headers=auth_headers)
        assert resp.status_code == 200
        assert any("banana" in t["title"].lower() for t in resp.json()["items"])

    async def test_stats_endpoint(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/todos/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "completed" in data
        assert "pending" in data
        assert "overdue" in data
        assert "due_today" in data
        assert "by_priority" in data

    async def test_bulk_update(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        ids = []
        for i in range(3):
            r = await client.post(
                "/api/todos",
                json={"title": f"Bulk todo {i}"},
                headers=auth_headers,
            )
            ids.append(r.json()["id"])

        resp = await client.patch(
            "/api/todos/bulk",
            json={"ids": ids, "is_completed": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert all(t["is_completed"] is True for t in resp.json())

    async def test_bulk_delete(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        ids = []
        for i in range(2):
            r = await client.post(
                "/api/todos",
                json={"title": f"Delete me {i}"},
                headers=auth_headers,
            )
            ids.append(r.json()["id"])

        resp = await client.post(
            "/api/todos/bulk-delete",
            json={"ids": ids},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2

    async def test_cannot_access_other_users_todo(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        admin_headers: dict[str, str],
    ) -> None:
        # Create todo as regular user
        r = await client.post(
            "/api/todos",
            json={"title": "Private todo"},
            headers=auth_headers,
        )
        todo_id = r.json()["id"]

        # Admin can't access it (todos are user-scoped)
        resp = await client.get(f"/api/todos/{todo_id}", headers=admin_headers)
        assert resp.status_code in (403, 404)
