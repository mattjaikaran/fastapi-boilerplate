import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.api.users.model import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None


class UserResponse(UserBase):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_email_verified: bool
    is_totp_enabled: bool
    full_name: str
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_subscribed: bool = False
    subscription_plan: str | None = None


class UserAdminUpdate(UserUpdate):
    role: UserRole | None = None
    is_active: bool | None = None
    is_email_verified: bool | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int
