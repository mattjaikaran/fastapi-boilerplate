import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"
    superuser = "superuser"


class User(SoftDeleteMixin, BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.user, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    otp_codes: Mapped[list["OTPCode"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "OTPCode", back_populates="user", cascade="all, delete-orphan"
    )
    todos: Mapped[list["Todo"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Todo", back_populates="user", cascade="all, delete-orphan"
    )
    files: Mapped[list["FileUpload"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "FileUpload", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts) or self.email.split("@")[0]

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.admin, UserRole.superuser)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# Import here to avoid circular dependency
from app.api.auth.model import OTPCode, RefreshToken  # noqa: E402, F401
from app.api.files.model import FileUpload  # noqa: E402, F401
from app.api.todos.model import Todo  # noqa: E402, F401
