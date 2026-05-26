import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_flag_requires_admin(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/feature-flags",
        json={"key": "test-flag", "name": "Test Flag"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.integration
async def test_create_flag_as_admin(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/feature-flags",
        json={"key": "my-new-flag", "name": "My New Flag", "enabled": False},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "my-new-flag"
    assert data["enabled"] is False


@pytest.mark.integration
async def test_create_flag_requires_auth(client: AsyncClient):
    response = await client.post("/api/feature-flags", json={"key": "x", "name": "x"})
    assert response.status_code == 401


@pytest.mark.integration
async def test_list_flags_as_admin(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/feature-flags",
        json={"key": "list-flag-1", "name": "Flag 1"},
        headers=admin_headers,
    )
    response = await client.get("/api/feature-flags", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.integration
async def test_get_flag_by_id(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/feature-flags",
        json={"key": "get-by-id-flag", "name": "Get By ID Flag"},
        headers=admin_headers,
    )
    flag_id = create.json()["id"]

    response = await client.get(f"/api/feature-flags/{flag_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == flag_id


@pytest.mark.integration
async def test_update_flag(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/feature-flags",
        json={"key": "update-flag", "name": "Update Flag"},
        headers=admin_headers,
    )
    flag_id = create.json()["id"]

    response = await client.patch(
        f"/api/feature-flags/{flag_id}",
        json={"enabled": True},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.integration
async def test_evaluate_flag(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    await client.post(
        "/api/feature-flags",
        json={"key": "eval-flag", "name": "Eval Flag", "enabled": True},
        headers=admin_headers,
    )

    response = await client.get("/api/feature-flags/eval/eval-flag", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "eval-flag"
    assert data["enabled"] is True
    assert data["source"] == "global"


@pytest.mark.integration
async def test_delete_flag(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/feature-flags",
        json={"key": "delete-flag", "name": "Delete Flag"},
        headers=admin_headers,
    )
    flag_id = create.json()["id"]

    response = await client.delete(f"/api/feature-flags/{flag_id}", headers=admin_headers)
    assert response.status_code == 204
