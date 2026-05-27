"""E2E: API key management user journey."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestAPIKeysJourney:
    async def test_create_use_revoke_api_key(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create
        create_resp = await client.post(
            "/api/users/me/api-keys",
            json={"name": "Test key", "scopes": ["read"]},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert "raw_key" in data
        raw_key = data["raw_key"]
        key_id = data["id"]

        # Use key to authenticate
        me_resp = await client.get("/api/auth/me", headers={"X-Api-Key": raw_key})
        assert me_resp.status_code == 200

        # List keys
        list_resp = await client.get("/api/users/me/api-keys", headers=auth_headers)
        assert list_resp.status_code == 200
        assert any(k["id"] == key_id for k in list_resp.json()["items"])

        # Revoke
        revoke_resp = await client.delete(
            f"/api/users/me/api-keys/{key_id}", headers=auth_headers
        )
        assert revoke_resp.status_code == 204

        # Key is now invalid
        invalid_resp = await client.get("/api/auth/me", headers={"X-Api-Key": raw_key})
        assert invalid_resp.status_code == 401

    async def test_raw_key_only_returned_once(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/users/me/api-keys",
            json={"name": "One-time key"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        assert "raw_key" in create_resp.json()

        # Listing keys does NOT expose raw key
        list_resp = await client.get("/api/users/me/api-keys", headers=auth_headers)
        for key in list_resp.json()["items"]:
            assert "raw_key" not in key
