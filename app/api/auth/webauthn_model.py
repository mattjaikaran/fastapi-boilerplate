import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class WebAuthnCredential(BaseModel):
    """Stores a registered passkey / WebAuthn credential for a user.

    A user may register multiple credentials (e.g. Touch ID on laptop, Face ID
    on phone) so this is a many-to-one relationship with users.
    """

    __tablename__ = "webauthn_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aaguid: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    backup_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_state: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transports: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="webauthn_credentials"
    )


from app.api.users.model import User  # noqa: E402, F401
