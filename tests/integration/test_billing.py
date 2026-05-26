import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_get_subscription_no_stripe(client: AsyncClient, auth_headers: dict):
    """When Stripe is not configured, subscription endpoint returns null."""
    response = await client.get("/api/billing/subscription", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.integration
async def test_get_subscription_requires_auth(client: AsyncClient):
    response = await client.get("/api/billing/subscription")
    assert response.status_code == 401


@pytest.mark.integration
async def test_checkout_without_stripe_config(client: AsyncClient, auth_headers: dict):
    """Checkout returns 501 when STRIPE_API_KEY is not set."""
    response = await client.post(
        "/api/billing/checkout",
        json={"price_id": "price_fake123", "success_url": "http://localhost/success", "cancel_url": "http://localhost/cancel"},
        headers=auth_headers,
    )
    assert response.status_code == 501


@pytest.mark.integration
async def test_portal_without_stripe_config(client: AsyncClient, auth_headers: dict):
    """Portal returns 501 when STRIPE_API_KEY is not set."""
    response = await client.post(
        "/api/billing/portal",
        json={"return_url": "http://localhost/billing"},
        headers=auth_headers,
    )
    assert response.status_code == 501


@pytest.mark.integration
async def test_cancel_without_stripe_config(client: AsyncClient, auth_headers: dict):
    """Cancel returns 501 when STRIPE_API_KEY is not set."""
    response = await client.post("/api/billing/cancel", headers=auth_headers)
    assert response.status_code == 501


@pytest.mark.integration
async def test_stripe_webhook_without_secret(client: AsyncClient):
    """Stripe webhook returns 501 when webhook secret is not configured."""
    response = await client.post(
        "/api/billing/stripe-webhook",
        content=b'{"type":"payment_intent.succeeded"}',
        headers={"content-type": "application/json", "stripe-signature": "t=fake,v1=fake"},
    )
    assert response.status_code == 501
