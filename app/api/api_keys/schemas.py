import uuid
from datetime import datetime

from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str
    org_id: uuid.UUID | None = None
    scopes: list[str] = []
    expires_at: datetime | None = None


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    org_id: uuid.UUID | None
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(APIKeyResponse):
    """Only returned once at creation — includes the full raw key."""

    raw_key: str


class APIKeyListResponse(BaseModel):
    items: list[APIKeyResponse]
    total: int
