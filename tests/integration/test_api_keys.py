import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_api_key(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/api-keys",
        json={"name": "My Key", "scopes": ["read", "write"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Key"
    assert "raw_key" in data
    assert data["raw_key"] is not None
    assert "key_prefix" in data
    assert data["is_active"] is True


@pytest.mark.integration
async def test_create_api_key_requires_auth(client: AsyncClient):
    response = await client.post("/api/api-keys", json={"name": "Key"})
    assert response.status_code == 401


@pytest.mark.integration
async def test_raw_key_not_shown_on_list(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/api-keys",
        json={"name": "Listed Key"},
        headers=auth_headers,
    )
    response = await client.get("/api/api-keys", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "raw_key" not in item


@pytest.mark.integration
async def test_list_api_keys(client: AsyncClient, auth_headers: dict):
    await client.post("/api/api-keys", json={"name": "Key A"}, headers=auth_headers)
    await client.post("/api/api-keys", json={"name": "Key B"}, headers=auth_headers)

    response = await client.get("/api/api-keys", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.integration
async def test_revoke_api_key(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/api-keys",
        json={"name": "Revoke Me"},
        headers=auth_headers,
    )
    key_id = create.json()["id"]

    response = await client.post(f"/api/api-keys/{key_id}/revoke", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["revoked"] is True


@pytest.mark.integration
async def test_revoke_already_revoked_key(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/api-keys",
        json={"name": "Revoke Twice"},
        headers=auth_headers,
    )
    key_id = create.json()["id"]

    await client.post(f"/api/api-keys/{key_id}/revoke", headers=auth_headers)
    response = await client.post(f"/api/api-keys/{key_id}/revoke", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_delete_api_key(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/api-keys",
        json={"name": "Delete Me"},
        headers=auth_headers,
    )
    key_id = create.json()["id"]

    response = await client.delete(f"/api/api-keys/{key_id}", headers=auth_headers)
    assert response.status_code == 204
