import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_list_notifications_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "unread_count" in data


@pytest.mark.integration
async def test_list_notifications_requires_auth(client: AsyncClient):
    response = await client.get("/api/notifications")
    assert response.status_code == 401


@pytest.mark.integration
async def test_login_creates_notification(client: AsyncClient, user):
    response = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    notif_response = await client.get("/api/notifications", headers=headers)
    assert notif_response.status_code == 200
    data = notif_response.json()
    assert data["total"] >= 1
    titles = [n["title"] for n in data["items"]]
    assert any("login" in t.lower() for t in titles)


@pytest.mark.integration
async def test_mark_read(client: AsyncClient, auth_headers: dict, user):
    # Login again to generate a notification
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    notifs = await client.get("/api/notifications", headers=headers)
    items = notifs.json()["items"]
    assert len(items) >= 1
    notification_id = items[0]["id"]

    response = await client.post(
        "/api/notifications/mark-read",
        json={"notification_ids": [notification_id]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["marked_read"] >= 1


@pytest.mark.integration
async def test_mark_all_read(client: AsyncClient, user):
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/notifications/mark-all-read", headers=headers)
    assert response.status_code == 200
    assert "marked_read" in response.json()


@pytest.mark.integration
async def test_unread_only_filter(client: AsyncClient, user):
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/notifications?unread_only=true", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert all(item["read_at"] is None for item in data["items"])


@pytest.mark.integration
async def test_delete_notification(client: AsyncClient, user):
    login = await client.post("/api/auth/login", json={"email": user.email, "password": "password123"})
    token = login.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    notifs = await client.get("/api/notifications", headers=headers)
    items = notifs.json()["items"]
    if not items:
        pytest.skip("No notifications to delete")

    notification_id = items[0]["id"]
    response = await client.delete(f"/api/notifications/{notification_id}", headers=headers)
    assert response.status_code == 204
