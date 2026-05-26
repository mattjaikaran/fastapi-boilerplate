import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_organization(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/organizations",
        json={"name": "Acme Corp", "slug": "acme-corp"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert data["plan"] == "free"


@pytest.mark.integration
async def test_create_organization_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/organizations",
        json={"name": "No Auth Org", "slug": "no-auth-org"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_create_duplicate_slug_fails(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/organizations",
        json={"name": "First Org", "slug": "dup-slug"},
        headers=auth_headers,
    )
    response = await client.post(
        "/api/organizations",
        json={"name": "Second Org", "slug": "dup-slug"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.integration
async def test_list_organizations(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/organizations",
        json={"name": "List Org 1", "slug": "list-org-1"},
        headers=auth_headers,
    )
    response = await client.get("/api/organizations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert "items" in data


@pytest.mark.integration
async def test_get_organization(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/organizations",
        json={"name": "Get Org", "slug": "get-org"},
        headers=auth_headers,
    )
    org_id = create.json()["id"]

    response = await client.get(f"/api/organizations/{org_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == org_id


@pytest.mark.integration
async def test_update_organization(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/organizations",
        json={"name": "Update Org", "slug": "update-org"},
        headers=auth_headers,
    )
    org_id = create.json()["id"]

    response = await client.patch(
        f"/api/organizations/{org_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.integration
async def test_list_members(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/organizations",
        json={"name": "Members Org", "slug": "members-org"},
        headers=auth_headers,
    )
    org_id = create.json()["id"]

    response = await client.get(f"/api/organizations/{org_id}/members", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    roles = [m["role"] for m in data]
    assert "owner" in roles


@pytest.mark.integration
async def test_delete_organization(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/organizations",
        json={"name": "Delete Org", "slug": "delete-org"},
        headers=auth_headers,
    )
    org_id = create.json()["id"]

    response = await client.delete(f"/api/organizations/{org_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/organizations/{org_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.integration
async def test_non_member_cannot_view_org(client: AsyncClient, auth_headers: dict, db):
    create = await client.post(
        "/api/organizations",
        json={"name": "Private Org", "slug": "private-org"},
        headers=auth_headers,
    )
    org_id = create.json()["id"]

    # Create another user and get their token
    from app.api.users.schemas import UserCreate
    from app.api.users.service import UserService

    svc = UserService(db)
    other_user = await svc.create(
        UserCreate(email="other@example.com", password="password123", first_name="Other", last_name="User")
    )
    other_user.is_email_verified = True
    db.add(other_user)
    await db.commit()

    login = await client.post("/api/auth/login", json={"email": "other@example.com", "password": "password123"})
    other_token = login.json()["tokens"]["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = await client.get(f"/api/organizations/{org_id}", headers=other_headers)
    assert response.status_code == 403
