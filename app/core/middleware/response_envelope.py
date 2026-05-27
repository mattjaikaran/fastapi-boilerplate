from datetime import UTC, datetime

import orjson
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths that bypass envelope wrapping (docs, admin, metrics, health)
_EXCLUDED_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/admin",
    "/health",
    "/favicon.ico",
)


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wrap every JSON API response in a standard envelope.

    Shape::

        {
            "success": true,
            "data": <original payload>,
            "requestId": "<uuid>",
            "timestamp": "2024-01-01T00:00:00.000Z"
        }

    On 4xx/5xx the original error payload is kept under ``"data"`` with
    ``"success": false``.  Non-JSON responses (HTML, binary) pass through
    unchanged.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
            return await call_next(request)  # type: ignore[operator]

        response: Response = await call_next(request)  # type: ignore[operator]

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Buffer the response body
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk

        try:
            payload = orjson.loads(body)
        except Exception:
            # Unparseable JSON — return raw response untouched
            from starlette.responses import Response as _R
            return _R(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

        request_id: str | None = getattr(request.state, "request_id", None)
        success = response.status_code < 400

        envelope = {
            "success": success,
            "data": payload,
            "requestId": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        new_body = orjson.dumps(envelope)

        # Rebuild headers — update Content-Length, keep the rest
        headers = dict(response.headers)
        headers["content-length"] = str(len(new_body))
        headers["content-type"] = "application/json"

        from starlette.responses import Response as _R
        return _R(
            content=new_body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )
