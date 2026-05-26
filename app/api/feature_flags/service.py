import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.feature_flags.model import FeatureFlag, OrgFeatureFlag
from app.api.feature_flags.schemas import FeatureFlagCreate, FeatureFlagUpdate
from app.core.exceptions import ConflictError, NotFoundError


class FeatureFlagService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: FeatureFlagCreate) -> FeatureFlag:
        existing = (
            await self.db.execute(
                select(FeatureFlag).where(FeatureFlag.key == data.key)
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(detail=f"Flag key '{data.key}' already exists")
        flag = FeatureFlag(**data.model_dump())
        self.db.add(flag)
        await self.db.flush()
        await self.db.refresh(flag)
        return flag

    async def get_by_key(self, key: str) -> FeatureFlag:
        flag = (
            await self.db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
        ).scalar_one_or_none()
        if not flag:
            raise NotFoundError(detail=f"Feature flag '{key}' not found")
        return flag

    async def get_by_id(self, flag_id: uuid.UUID) -> FeatureFlag:
        flag = await self.db.get(FeatureFlag, flag_id)
        if not flag:
            raise NotFoundError(detail=f"Feature flag {flag_id} not found")
        return flag

    async def list(
        self, page: int = 1, page_size: int = 50
    ) -> tuple[list[FeatureFlag], int]:
        q = select(FeatureFlag)
        total = (
            await self.db.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        items = list(
            (
                await self.db.execute(
                    q.order_by(FeatureFlag.key)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total

    async def update(self, flag: FeatureFlag, data: FeatureFlagUpdate) -> FeatureFlag:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(flag, field, value)
        self.db.add(flag)
        await self.db.flush()
        await self.db.refresh(flag)
        return flag

    async def delete(self, flag: FeatureFlag) -> None:
        await self.db.delete(flag)
        await self.db.flush()

    async def set_org_override(
        self, flag_id: uuid.UUID, org_id: uuid.UUID, enabled: bool
    ) -> OrgFeatureFlag:
        existing = (
            await self.db.execute(
                select(OrgFeatureFlag).where(
                    OrgFeatureFlag.flag_id == flag_id, OrgFeatureFlag.org_id == org_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.enabled = enabled
            self.db.add(existing)
            await self.db.flush()
            return existing
        override = OrgFeatureFlag(flag_id=flag_id, org_id=org_id, enabled=enabled)
        self.db.add(override)
        await self.db.flush()
        await self.db.refresh(override)
        return override

    async def delete_org_override(self, flag_id: uuid.UUID, org_id: uuid.UUID) -> None:
        existing = (
            await self.db.execute(
                select(OrgFeatureFlag).where(
                    OrgFeatureFlag.flag_id == flag_id, OrgFeatureFlag.org_id == org_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            await self.db.delete(existing)
            await self.db.flush()

    async def evaluate(
        self, key: str, org_id: uuid.UUID | None = None
    ) -> tuple[bool, str]:
        """Returns (enabled, source) where source is 'org_override' or 'global'."""
        flag = await self.get_by_key(key)
        if org_id:
            override = (
                await self.db.execute(
                    select(OrgFeatureFlag).where(
                        OrgFeatureFlag.flag_id == flag.id,
                        OrgFeatureFlag.org_id == org_id,
                    )
                )
            ).scalar_one_or_none()
            if override is not None:
                return override.enabled, "org_override"
        return flag.enabled, "global"
