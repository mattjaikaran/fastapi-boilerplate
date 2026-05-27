"""Middleware-level sliding-window rate limiter backed by Redis.

Replaces per-endpoint ``@limiter.limit()`` decorators with a single
middleware that applies a configurable limit to every API route.

Algorithm
---------
Uses a Redis sorted set keyed by identifier (``user_id`` when a valid JWT is
present, otherwise client IP).  Each request adds the current timestamp as
both score *and* member; entries older than the window are pruned atomically
via a Lua script before the count is evaluated.

Key format: ``rl:{identifier}``

Configuration (via Settings)
-----------------------------
``RATE_LIMIT_ENABLED``  – toggle (default ``True``)
``RATE_LIMIT_DEFAULT``  – ``"<count>/<unit>"`` e.g. ``"100/minute"``

Excluded paths
--------------
Docs, admin, metrics and health endpoints are exempt.
"""

from __future__ import annotations

import time

import redis.asyncio as aioredis
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config.settings import settings


logger = structlog.get_logger()

_EXCLUDED_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/admin",
    "/health",
    "/favicon.ico",
)

# Lua script for atomic sliding-window check-and-record.
# Returns: {allowed (0|1), remaining, reset_after_ms}
_SLIDING_WINDOW_LUA = """
local key      = KEYS[1]
local now      = tonumber(ARGV[1])
local window   = tonumber(ARGV[2])
local limit    = tonumber(ARGV[3])
local entry_id = ARGV[4]

local win_start = now - window

-- Remove entries that have left the window
redis.call('ZREMRANGEBYSCORE', key, '-inf', win_start)

local count = redis.call('ZCARD', key)

if count >= limit then
    -- Return denied; include time until oldest entry exits the window
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_ms = 0
    if #oldest >= 2 then
        reset_ms = math.max(0, math.floor((tonumber(oldest[2]) + window - now) * 1000))
    end
    return {0, 0, reset_ms}
end

-- Record this request
redis.call('ZADD', key, now, entry_id)
redis.call('PEXPIRE', key, window * 1000)

return {1, limit - count - 1, 0}
"""


def _parse_limit(raw: str) -> tuple[int, int]:
    """Parse ``"<count>/<unit>"`` → ``(count, window_seconds)``."""
    units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    count_str, unit_str = raw.split("/", 1)
    count = int(count_str.strip())
    unit = unit_str.strip().lower()
    window = units.get(unit)
    if window is None:
        raise ValueError(f"Unknown rate limit unit: {unit!r}")
    return count, window


def _extract_user_id(request: Request) -> str | None:
    """Try to read user_id from the JWT sub claim without a full auth dep."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:]
    try:
        from app.core.security.jwt import decode_token
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis sliding-window rate limiter applied at the middleware layer."""

    def __init__(self, app: object, redis_url: str = "", limit_str: str = "") -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._redis_url = redis_url or settings.REDIS_URL
        self._limit, self._window = _parse_limit(limit_str or settings.RATE_LIMIT_DEFAULT)
        self._redis: aioredis.Redis | None = None
        self._script: object = None  # registered script handle

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)  # type: ignore[operator]

        path = request.url.path
        if any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)  # type: ignore[operator]

        identifier = _extract_user_id(request) or (
            request.client.host if request.client else "unknown"
        )
        key = f"rl:{identifier}"
        now = time.time()
        entry_id = f"{now:.6f}"

        try:
            redis = await self._get_redis()
            if self._script is None:
                self._script = redis.register_script(_SLIDING_WINDOW_LUA)
            result = await self._script(keys=[key], args=[now, self._window, self._limit, entry_id])  # type: ignore[call-arg]
            allowed, remaining, reset_ms = int(result[0]), int(result[1]), int(result[2])
        except Exception as exc:
            # Fail open — Redis down should not block traffic
            await logger.awarning("rate_limit_redis_error", error=str(exc))
            return await call_next(request)  # type: ignore[operator]

        if not allowed:
            retry_after = max(1, reset_ms // 1000)
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "data": {"detail": "Too many requests", "retry_after": retry_after},
                    "requestId": getattr(request.state, "request_id", None),
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self._window),
                },
            )

        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self._window)
        return response
