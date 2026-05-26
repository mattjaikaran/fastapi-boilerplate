import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class FeatureFlagCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    enabled: bool = False
    extra: dict = {}

    @field_validator("key")
    @classmethod
    def key_format(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError(
                "Key must contain only alphanumeric characters,"
                " hyphens, underscores, or dots"
            )
        return v.lower()


class FeatureFlagUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    extra: dict | None = None


class OrgOverrideRequest(BaseModel):
    enabled: bool


class FeatureFlagResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    description: str | None
    enabled: bool
    extra: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeatureFlagListResponse(BaseModel):
    items: list[FeatureFlagResponse]
    total: int


class FlagEvalResponse(BaseModel):
    key: str
    enabled: bool
    source: str  # "org_override" | "global"
