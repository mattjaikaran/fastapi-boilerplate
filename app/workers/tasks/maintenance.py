import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.tasks.maintenance.expire_api_keys")
def expire_api_keys() -> dict:
    """Mark expired API keys. Expiry checked at read time via is_active property."""
    logger.info("expire_api_keys_task_ran")
    return {"status": "ok"}


@celery_app.task(name="app.workers.tasks.maintenance.cleanup_audit_logs")
def cleanup_audit_logs(retain_days: int = 365) -> dict:
    """Delete audit log entries older than retain_days."""
    import asyncio
    from datetime import UTC, datetime, timedelta

    async def _run() -> int:
        from sqlalchemy import delete

        from app.api.audit.model import AuditLog
        from app.config.database import engine

        cutoff = datetime.now(UTC) - timedelta(days=retain_days)
        async with engine.begin() as conn:
            result = await conn.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff)
            )
            return result.rowcount  # type: ignore[return-value]

    deleted = asyncio.run(_run())
    logger.info("cleanup_audit_logs_done", deleted=deleted, retain_days=retain_days)
    return {"deleted": deleted}


@celery_app.task(name="app.workers.tasks.maintenance.cleanup_notifications")
def cleanup_notifications(retain_days: int = 90) -> dict:
    """Delete read notifications older than retain_days."""
    import asyncio
    from datetime import UTC, datetime, timedelta

    async def _run() -> int:
        from sqlalchemy import delete

        from app.api.notifications.model import Notification
        from app.config.database import engine

        cutoff = datetime.now(UTC) - timedelta(days=retain_days)
        async with engine.begin() as conn:
            result = await conn.execute(
                delete(Notification).where(
                    Notification.read_at.isnot(None),
                    Notification.created_at < cutoff,
                )
            )
            return result.rowcount  # type: ignore[return-value]

    deleted = asyncio.run(_run())
    logger.info("cleanup_notifications_done", deleted=deleted, retain_days=retain_days)
    return {"deleted": deleted}
