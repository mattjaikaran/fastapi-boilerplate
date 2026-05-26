import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class OTPPurpose(str, enum.Enum):
    email_verification = "email_verification"
    password_reset = "password_reset"
    two_factor = "two_factor"
    magic_link = "magic_link"


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")  # type: ignore[name-defined]  # noqa: F821

    @property
    def is_expired(self) -> bool:
        from datetime import UTC

        from datetime import datetime as dt

        return dt.now(UTC) > self.expires_at


class OTPCode(BaseModel):
    __tablename__ = "otp_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    purpose: Mapped[OTPPurpose] = mapped_column(Enum(OTPPurpose), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="otp_codes")  # type: ignore[name-defined]  # noqa: F821

    @property
    def is_expired(self) -> bool:
        from datetime import UTC

        from datetime import datetime as dt

        return dt.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired and self.attempts < 5


from app.api.users.model import User  # noqa: E402, F401
