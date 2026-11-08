"""Async HTTP client for the django-ninja-boilerplate API.

The Django service exposes its API under ``/api/`` without a version prefix and
authenticates machine-to-machine callers with the ``X-API-Key`` header. See
``docs/INTEGRATIONS.md`` for setup and usage.
"""

from collections.abc import Mapping
from types import TracebackType
from typing import Self, cast

import httpx

from app.config.settings import settings

API_KEY_HEADER = "X-API-Key"
HEALTH_PATH = "/health/"

type JSONValue = (
    dict[str, JSONValue] | list[JSONValue] | str | int | float | bool | None
)
type QueryParams = Mapping[str, str | int | float | bool | None]


class NinjaClientError(Exception):
    """Raised when the Django Ninja service is unreachable or answers non-2xx."""

    def __init__(self, status_code: int | None, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        prefix = (
            f"Django Ninja API error {status_code}"
            if status_code is not None
            else "Django Ninja request failed"
        )
        super().__init__(f"{prefix}: {detail}")


class NinjaClient:
    """Thin ``httpx.AsyncClient`` wrapper around django-ninja-boilerplate."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url if base_url is not None else settings.NINJA_BASE_URL,
            headers={
                API_KEY_HEADER: (
                    api_key if api_key is not None else settings.NINJA_API_KEY
                )
            },
            timeout=timeout if timeout is not None else settings.NINJA_TIMEOUT_SECONDS,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    async def get(self, path: str, *, params: QueryParams | None = None) -> JSONValue:
        """GET ``path`` and return the decoded JSON payload."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, *, json: JSONValue = None) -> JSONValue:
        """POST ``json`` to ``path`` and return the decoded JSON payload."""
        return await self._request("POST", path, json=json)

    async def health(self) -> bool:
        """Return ``True`` when the Django service answers its health probe."""
        try:
            await self._request("GET", HEALTH_PATH)
        except NinjaClientError:
            return False
        return True

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: QueryParams | None = None,
        json: JSONValue = None,
    ) -> JSONValue:
        try:
            response = await self._client.request(
                method, path, params=params, json=json
            )
        except httpx.HTTPError as exc:
            raise NinjaClientError(None, str(exc)) from exc
        if not response.is_success:
            raise NinjaClientError(response.status_code, response.text)
        return cast("JSONValue", response.json())


_client: NinjaClient | None = None


def get_ninja_client() -> NinjaClient:
    """FastAPI dependency returning the shared client, created on first use."""
    global _client
    if _client is None:
        _client = NinjaClient()
    return _client


async def close_ninja_client() -> None:
    """Close the shared client. Called from the application shutdown hook."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
