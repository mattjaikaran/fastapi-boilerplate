import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.api.organizations.model import OrgRole


class OrganizationCreate(BaseModel):
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    is_active: bool
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrgRole
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: OrgRole = OrgRole.member


class UpdateMemberRoleRequest(BaseModel):
    role: OrgRole


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int
    page: int
    page_size: int
