import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID and timing header to every response.

    Priority:
      1. Use ``X-Request-ID`` from the incoming request (idempotent replay support)
      2. Otherwise generate a new UUID v4

    Exposed response headers:
      - ``X-Request-ID``: correlation ID (echoed back)
      - ``X-Response-Time``: wall-clock duration in milliseconds (e.g. "42ms")
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        elapsed_ms = round((time.perf_counter() - start) * 1000)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        structlog.contextvars.clear_contextvars()
        return response
