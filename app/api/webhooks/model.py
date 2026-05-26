import enum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class WebhookEventStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"
    skipped = "skipped"


class WebhookEvent(BaseModel):
    __tablename__ = "webhook_events"

    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[WebhookEventStatus] = mapped_column(
        Enum(WebhookEventStatus), default=WebhookEventStatus.pending, nullable=False, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<WebhookEvent source={self.source} type={self.event_type} status={self.status}>"
