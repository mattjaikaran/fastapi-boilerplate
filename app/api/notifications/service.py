import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.notifications.model import Notification, NotificationType
from app.core.exceptions import NotFoundError


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        type: NotificationType = NotificationType.info,
        body: str | None = None,
        extra: dict | None = None,
        org_id: uuid.UUID | None = None,
    ) -> Notification:
        n = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            extra=extra or {},
            org_id=org_id,
        )
        self.db.add(n)
        await self.db.flush()
        await self.db.refresh(n)

        # Push to any active WebSocket connections for this user
        from app.api.ws.manager import ws_manager
        await ws_manager.send(user_id, {
            "event": "notification",
            "data": {
                "id": str(n.id),
                "type": n.type.value,
                "title": n.title,
                "body": n.body,
                "extra": n.extra,
                "created_at": n.created_at.isoformat(),
            },
        })

        return n

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int, int]:
        base = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            base = base.where(Notification.read_at.is_(None))

        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        unread_count = (
            await self.db.execute(
                select(func.count()).select_from(
                    select(Notification)
                    .where(
                        Notification.user_id == user_id, Notification.read_at.is_(None)
                    )
                    .subquery()
                )
            )
        ).scalar_one()

        items = list(
            (
                await self.db.execute(
                    base.order_by(Notification.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total, unread_count

    async def mark_read(
        self, user_id: uuid.UUID, notification_ids: list[uuid.UUID]
    ) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids),
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        return result.rowcount  # type: ignore[return-value]

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        return result.rowcount  # type: ignore[return-value]

    async def delete(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        n = await self.db.get(Notification, notification_id)
        if not n or n.user_id != user_id:
            raise NotFoundError(detail="Notification not found")
        await self.db.delete(n)
        await self.db.flush()
