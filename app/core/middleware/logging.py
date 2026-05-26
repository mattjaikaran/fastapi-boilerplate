import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        response: Response = await call_next(request)  # type: ignore[operator]

        duration_ms = (time.perf_counter() - start) * 1000
        await logger.ainfo(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )
        return response
