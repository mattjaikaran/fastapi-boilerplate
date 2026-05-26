from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from sqlalchemy import text

from app.config.database import async_session_factory
from app.config.settings import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", include_in_schema=False)
@router.get("/live")
async def liveness() -> ORJSONResponse:
    return ORJSONResponse({"status": "ok", "timestamp": datetime.now(UTC).isoformat()})


@router.get("/ready")
async def readiness() -> ORJSONResponse:
    checks: dict[str, str] = {}
    healthy = True

    # Database check
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    return ORJSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "checks": checks,
            "version": settings.APP_VERSION,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@router.get("/info")
async def info() -> ORJSONResponse:
    return ORJSONResponse(
        {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "env": settings.APP_ENV,
        }
    )
