import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit.model import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        extra: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            extra=extra or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        actor_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        q = select(AuditLog)
        if actor_id:
            q = q.where(AuditLog.actor_id == actor_id)
        if org_id:
            q = q.where(AuditLog.org_id == org_id)
        if action:
            q = q.where(AuditLog.action == action)
        if resource_type:
            q = q.where(AuditLog.resource_type == resource_type)

        total = (
            await self.db.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        items = list(
            (
                await self.db.execute(
                    q.order_by(AuditLog.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total
