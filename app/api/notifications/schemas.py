import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.notifications.model import NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID | None
    type: NotificationType
    title: str
    body: str | None
    extra: dict
    read_at: datetime | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: list[uuid.UUID]
