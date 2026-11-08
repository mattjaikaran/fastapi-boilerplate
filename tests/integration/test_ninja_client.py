"""Smoke: django-ninja integration client contract."""

import json

import httpx
import pytest
import respx

from app.services.integrations.ninja_client import NinjaClient, NinjaClientError

BASE_URL = "http://ninja.test/api"


@pytest.mark.smoke
async def test_get_sends_api_key_and_decodes_json() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/todos/").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        async with NinjaClient(base_url=BASE_URL, api_key="test-key") as client:
            payload = await client.get("/todos/")

    assert payload == [{"id": 1}]
    assert route.calls.last.request.headers["X-API-Key"] == "test-key"


@pytest.mark.smoke
async def test_post_sends_json_body() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.post("/todos/").mock(
            return_value=httpx.Response(201, json={"id": 7, "title": "Ship it"})
        )
        async with NinjaClient(base_url=BASE_URL, api_key="test-key") as client:
            payload = await client.post("/todos/", json={"title": "Ship it"})

    assert payload == {"id": 7, "title": "Ship it"}
    assert json.loads(route.calls.last.request.content) == {"title": "Ship it"}


@pytest.mark.smoke
async def test_non_2xx_raises_client_error() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos/").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        async with NinjaClient(base_url=BASE_URL, api_key="bad") as client:
            with pytest.raises(NinjaClientError) as exc_info:
                await client.get("/todos/")

    assert exc_info.value.status_code == 401
    assert "Invalid API key" in exc_info.value.detail


@pytest.mark.smoke
async def test_health_reports_reachability() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/health/").mock(return_value=httpx.Response(200, json={}))
        async with NinjaClient(base_url=BASE_URL, api_key="test-key") as client:
            assert await client.health() is True

    with respx.mock(base_url=BASE_URL) as router:
        router.get("/health/").mock(return_value=httpx.Response(503))
        async with NinjaClient(base_url=BASE_URL, api_key="test-key") as client:
            assert await client.health() is False


@pytest.mark.smoke
async def test_transport_error_maps_to_client_error() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos/").mock(side_effect=httpx.ConnectError("boom"))
        async with NinjaClient(base_url=BASE_URL, api_key="test-key") as client:
            with pytest.raises(NinjaClientError) as exc_info:
                await client.get("/todos/")

    assert exc_info.value.status_code is None
