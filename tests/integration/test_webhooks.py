import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_receive_webhook(client: AsyncClient):
    response = await client.post(
        "/api/webhooks/stripe",
        json={"type": "payment_intent.succeeded", "data": {"id": "pi_123"}},
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@pytest.mark.integration
async def test_receive_webhook_with_event_type_header(client: AsyncClient):
    response = await client.post(
        "/api/webhooks/github",
        json={"action": "opened"},
        headers={
            "content-type": "application/json",
            "x-github-event": "pull_request",
        },
    )
    assert response.status_code == 202


@pytest.mark.integration
async def test_receive_webhook_empty_body(client: AsyncClient):
    response = await client.post("/api/webhooks/test-source")
    assert response.status_code == 202


@pytest.mark.integration
async def test_list_webhook_events_requires_admin(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/webhooks/events", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_list_webhook_events_as_admin(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/webhooks/test",
        json={"event": "test.event"},
    )
    response = await client.get("/api/webhooks/events", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
async def test_get_webhook_event_by_id(client: AsyncClient, admin_headers: dict):
    await client.post("/api/webhooks/test", json={"x": 1})

    events = await client.get("/api/webhooks/events", headers=admin_headers)
    items = events.json()["items"]
    assert len(items) >= 1
    event_id = items[0]["id"]

    response = await client.get(f"/api/webhooks/events/{event_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == event_id


@pytest.mark.integration
async def test_idempotency_key_deduplicates(client: AsyncClient, admin_headers: dict):
    payload = {"event": "duplicate.test"}
    headers = {"x-idempotency-key": "idempotency-abc-123", "content-type": "application/json"}

    await client.post("/api/webhooks/idempotent-source", json=payload, headers=headers)
    await client.post("/api/webhooks/idempotent-source", json=payload, headers=headers)

    events = await client.get(
        "/api/webhooks/events?source=idempotent-source",
        headers=admin_headers,
    )
    assert events.status_code == 200
    # Idempotent key should prevent double processing
    assert events.json()["total"] == 1
