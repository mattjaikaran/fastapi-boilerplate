import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.organizations.model import OrgRole, Organization, OrganizationMember
from app.api.organizations.schemas import InviteMemberRequest, OrganizationCreate, OrganizationUpdate
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, owner_id: uuid.UUID, data: OrganizationCreate) -> Organization:
        existing = await self.db.execute(
            select(Organization).where(Organization.slug == data.slug)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(detail=f"Slug '{data.slug}' is already taken")

        org = Organization(name=data.name, slug=data.slug, owner_id=owner_id)
        self.db.add(org)
        await self.db.flush()

        membership = OrganizationMember(
            organization_id=org.id,
            user_id=owner_id,
            role=OrgRole.owner,
        )
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def get_by_id(self, org_id: uuid.UUID) -> Organization:
        org = await self.db.get(Organization, org_id)
        if not org:
            raise NotFoundError(detail=f"Organization {org_id} not found")
        return org

    async def get_by_slug(self, slug: str) -> Organization:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError(detail=f"Organization '{slug}' not found")
        return org

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Organization], int]:
        base = (
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id)
        )
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        orgs = list(
            (
                await self.db.execute(
                    base.order_by(Organization.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return orgs, total

    async def update(
        self, org: Organization, actor_id: uuid.UUID, data: OrganizationUpdate
    ) -> Organization:
        await self._require_admin(org.id, actor_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(org, field, value)
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def delete(self, org: Organization, actor_id: uuid.UUID) -> None:
        await self._require_owner(org.id, actor_id)
        await self.db.delete(org)
        await self.db.flush()

    async def list_members(self, org_id: uuid.UUID) -> list[OrganizationMember]:
        result = await self.db.execute(
            select(OrganizationMember).where(OrganizationMember.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def add_member(
        self,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
        data: InviteMemberRequest,
    ) -> OrganizationMember:
        await self._require_admin(org_id, actor_id)

        existing = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == data.user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(detail="User is already a member of this organization")

        if data.role == OrgRole.owner:
            raise ForbiddenError(detail="Cannot assign owner role via invite")

        member = OrganizationMember(
            organization_id=org_id,
            user_id=data.user_id,
            role=data.role,
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)

        org = await self.get_by_id(org_id)
        await self._notify(data.user_id, title="Organization invite", body=f"You have been added to {org.name}.")

        return member

    async def remove_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        await self._require_admin(org_id, actor_id)

        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise NotFoundError(detail="Member not found")
        if member.role == OrgRole.owner:
            raise ForbiddenError(detail="Cannot remove the organization owner")

        await self.db.delete(member)
        await self.db.flush()

    async def get_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMember | None:
        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _require_admin(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.get_membership(org_id, user_id)
        if not membership or membership.role not in (OrgRole.owner, OrgRole.admin):
            raise ForbiddenError(detail="Requires admin or owner role in this organization")

    async def _require_owner(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.get_membership(org_id, user_id)
        if not membership or membership.role != OrgRole.owner:
            raise ForbiddenError(detail="Requires owner role in this organization")

    async def _require_member(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.get_membership(org_id, user_id)
        if not membership:
            raise ForbiddenError(detail="You are not a member of this organization")

    async def _notify(self, user_id: uuid.UUID, title: str, body: str | None = None) -> None:
        from app.api.notifications.model import NotificationType
        from app.api.notifications.service import NotificationService

        try:
            await NotificationService(self.db).create(user_id=user_id, title=title, body=body, type=NotificationType.info)
        except Exception:
            pass
