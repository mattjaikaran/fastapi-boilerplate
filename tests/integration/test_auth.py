import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "newuser@example.com"
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


@pytest.mark.integration
async def test_register_duplicate_email(client: AsyncClient, user):
    response = await client.post(
        "/api/auth/register",
        json={"email": user.email, "password": "password123"},
    )
    assert response.status_code == 409


@pytest.mark.integration
async def test_login(client: AsyncClient, user):
    response = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == user.email
    assert "access_token" in data["tokens"]


@pytest.mark.integration
async def test_login_wrong_password(client: AsyncClient, user):
    response = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_get_me(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "email" in data


@pytest.mark.integration
async def test_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.integration
async def test_refresh_token(client: AsyncClient, user):
    login = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    refresh_token = login.json()["tokens"]["refresh_token"]

    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.integration
async def test_logout(client: AsyncClient, user):
    login = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    refresh_token = login.json()["tokens"]["refresh_token"]

    response = await client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert response.status_code == 200

    # Refresh with revoked token should fail
    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401
