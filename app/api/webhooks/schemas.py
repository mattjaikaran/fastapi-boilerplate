import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.webhooks.model import WebhookEventStatus


class WebhookEventResponse(BaseModel):
    id: uuid.UUID
    source: str
    event_type: str | None
    payload: dict[str, Any]
    signature_valid: bool
    status: WebhookEventStatus
    error: str | None
    idempotency_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookEventListResponse(BaseModel):
    items: list[WebhookEventResponse]
    total: int
    page: int
    page_size: int
