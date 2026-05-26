import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_list_audit_logs_requires_admin(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/audit", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_list_audit_logs_as_admin(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/audit", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.integration
async def test_list_audit_logs_requires_auth(client: AsyncClient):
    response = await client.get("/api/audit")
    assert response.status_code == 401


@pytest.mark.integration
async def test_list_my_audit_logs(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/audit/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
async def test_list_my_audit_logs_requires_auth(client: AsyncClient):
    response = await client.get("/api/audit/me")
    assert response.status_code == 401


@pytest.mark.integration
async def test_admin_audit_pagination(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/audit?page=1&page_size=5", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


@pytest.mark.integration
async def test_admin_filter_by_resource_type(client: AsyncClient, admin_headers: dict):
    response = await client.get("/api/audit?resource_type=user", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["resource_type"] == "user"
