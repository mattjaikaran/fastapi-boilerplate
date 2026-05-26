import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_webhook_event(self, event_id: str) -> None:
    import asyncio
    import uuid

    asyncio.run(_process(self, uuid.UUID(event_id)))


async def _process(task, event_id) -> None:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api.webhooks.model import WebhookEvent
    from app.api.webhooks.service import WebhookService
    from app.config.database import async_session_factory

    async with async_session_factory() as db:
        async with db.begin():
            event = await db.get(WebhookEvent, event_id)
            if not event:
                return

            svc = WebhookService(db)
            try:
                await _handle_event(event)
                await svc.mark_processed(event)
            except Exception as exc:
                logger.exception("webhook_processing_failed", event_id=str(event_id), error=str(exc))
                await svc.mark_failed(event, error=str(exc))
                raise task.retry(exc=exc)


async def _handle_event(event: "WebhookEvent") -> None:
    """Dispatch to source-specific handlers. Add your own handlers here."""
    logger.info(
        "webhook_event_received",
        source=event.source,
        event_type=event.event_type,
        event_id=str(event.id),
    )
