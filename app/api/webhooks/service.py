import hashlib
import hmac
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhooks.model import WebhookEvent, WebhookEventStatus


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def validate_signature(
        self,
        payload: bytes,
        signature: str | None,
        secret: str,
        algorithm: str = "sha256",
    ) -> bool:
        if not signature or not secret:
            return False
        expected = hmac.new(
            secret.encode(),
            payload,
            getattr(hashlib, algorithm, hashlib.sha256),
        ).hexdigest()
        # Support "sha256=..." prefix (GitHub style)
        received = signature.split("=", 1)[-1]
        return hmac.compare_digest(expected, received)

    async def record_event(
        self,
        source: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        signature_valid: bool,
        event_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> WebhookEvent:
        if idempotency_key:
            existing = await self.db.execute(
                select(WebhookEvent).where(
                    WebhookEvent.source == source,
                    WebhookEvent.idempotency_key == idempotency_key,
                )
            )
            dup = existing.scalar_one_or_none()
            if dup:
                return dup

        event = WebhookEvent(
            source=source,
            event_type=event_type,
            payload=payload,
            headers=headers,
            signature_valid=signature_valid,
            status=WebhookEventStatus.pending if signature_valid else WebhookEventStatus.skipped,
            idempotency_key=idempotency_key,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)

        if signature_valid:
            self._dispatch(event)

        return event

    def _dispatch(self, event: WebhookEvent) -> None:
        from app.workers.tasks.webhooks import process_webhook_event

        process_webhook_event.delay(str(event.id))

    async def get_by_id(self, event_id: uuid.UUID) -> WebhookEvent | None:
        return await self.db.get(WebhookEvent, event_id)

    async def list_events(
        self,
        page: int = 1,
        page_size: int = 50,
        source: str | None = None,
        status: WebhookEventStatus | None = None,
    ) -> tuple[list[WebhookEvent], int]:
        query = select(WebhookEvent)
        if source:
            query = query.where(WebhookEvent.source == source)
        if status:
            query = query.where(WebhookEvent.status == status)

        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        events = list(
            (
                await self.db.execute(
                    query.order_by(WebhookEvent.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return events, total

    async def mark_processed(self, event: WebhookEvent) -> None:
        from datetime import UTC, datetime

        event.status = WebhookEventStatus.processed
        self.db.add(event)
        await self.db.flush()

    async def mark_failed(self, event: WebhookEvent, error: str) -> None:
        event.status = WebhookEventStatus.failed
        event.error = error
        self.db.add(event)
        await self.db.flush()
