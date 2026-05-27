"""E2E: complete authentication user journeys."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestRegistrationAndLoginFlow:
    async def test_register_login_refresh_logout(self, client: AsyncClient) -> None:
        email = "e2e_test_user@example.com"
        password = "SuperSecret99!"

        # Register
        resp = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "first_name": "E2E", "last_name": "Test"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["user"]["email"] == email
        access_token = body["tokens"]["access_token"]
        refresh_token = body["tokens"]["refresh_token"]

        # Get profile
        me_resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email

        # Refresh tokens
        refresh_resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # Old refresh token is invalidated
        old_refresh_resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert old_refresh_resp.status_code == 401

        # Logout
        logout_resp = await client.post(
            "/api/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
        )
        assert logout_resp.status_code == 200

    async def test_duplicate_registration_returns_409(self, client: AsyncClient, user: object) -> None:
        resp = await client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 409

    async def test_login_wrong_password(self, client: AsyncClient, user: object) -> None:
        resp = await client.post(
            "/api/auth/login", json={"email": "test@example.com", "password": "wrongpassword"}
        )
        assert resp.status_code == 401

    async def test_response_has_request_id(self, client: AsyncClient) -> None:
        resp = await client.get("/api/health/live")
        assert "x-request-id" in resp.headers
        assert "x-response-time" in resp.headers


@pytest.mark.e2e
class TestPasswordResetFlow:
    async def test_forgot_and_reset_password(
        self, client: AsyncClient, db: object, user: object
    ) -> None:
        # Request reset (always returns 200 to avoid email enumeration)
        resp = await client.post(
            "/api/auth/forgot-password", json={"email": "test@example.com"}
        )
        assert resp.status_code == 200

        # Invalid OTP format
        resp = await client.post(
            "/api/auth/reset-password",
            json={"token": "notvalid", "new_password": "newpass123"},
        )
        assert resp.status_code == 401

    async def test_forgot_unknown_email_returns_200(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert resp.status_code == 200


@pytest.mark.e2e
class TestTOTPFlow:
    async def test_setup_and_verify_totp(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Setup TOTP
        setup_resp = await client.post("/api/auth/totp/setup", headers=auth_headers)
        assert setup_resp.status_code == 200
        data = setup_resp.json()
        assert "secret" in data
        assert "provisioning_uri" in data

        # Verify with correct code
        import pyotp
        totp = pyotp.TOTP(data["secret"])
        verify_resp = await client.post(
            "/api/auth/totp/verify",
            headers=auth_headers,
            json={"code": totp.now()},
        )
        assert verify_resp.status_code == 200

    async def test_verify_totp_wrong_code(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        await client.post("/api/auth/totp/setup", headers=auth_headers)
        resp = await client.post(
            "/api/auth/totp/verify", headers=auth_headers, json={"code": "000000"}
        )
        assert resp.status_code == 401


@pytest.mark.e2e
class TestMagicLinkFlow:
    async def test_request_magic_link_unknown_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/magic-link/request", json={"email": "nobody@nowhere.com"}
        )
        assert resp.status_code == 200  # Always 200 to avoid enumeration

    async def test_verify_magic_link_invalid_token(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/magic-link/verify", json={"token": "bad:token"}
        )
        assert resp.status_code == 401
