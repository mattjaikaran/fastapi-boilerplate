import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class FeatureFlag(BaseModel):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    org_overrides: Mapped[list["OrgFeatureFlag"]] = relationship(
        "OrgFeatureFlag", back_populates="flag", cascade="all, delete-orphan"
    )


class OrgFeatureFlag(BaseModel):
    __tablename__ = "org_feature_flags"

    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    flag: Mapped[FeatureFlag] = relationship(
        "FeatureFlag", back_populates="org_overrides"
    )

    __table_args__ = (
        UniqueConstraint("flag_id", "org_id", name="uq_org_feature_flag"),
    )
