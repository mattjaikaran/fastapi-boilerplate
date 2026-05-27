from app.models.base import Base, BaseModel, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = ["Base", "BaseModel", "TimestampMixin", "UUIDMixin", "SoftDeleteMixin"]


def register_all_models() -> None:
    """Import all ORM models so SQLAlchemy/Alembic can discover them.

    Called explicitly from migrations/env.py and app startup — NOT at module
    load time, to avoid circular imports during the router import chain.
    """
    from app.api.api_keys.model import APIKey  # noqa: F401
    from app.api.audit.model import AuditLog  # noqa: F401
    from app.api.auth.model import OTPCode, RefreshToken  # noqa: F401
    from app.api.billing.model import BillingCustomer, Subscription  # noqa: F401
    from app.api.feature_flags.model import FeatureFlag, OrgFeatureFlag  # noqa: F401
    from app.api.files.model import FileUpload  # noqa: F401
    from app.api.jobs.model import BackgroundJob  # noqa: F401
    from app.api.notifications.model import Notification  # noqa: F401
    from app.api.organizations.model import Organization, OrganizationMember  # noqa: F401
    from app.api.todos.model import Todo  # noqa: F401
    from app.api.users.model import User  # noqa: F401
    from app.api.auth.webauthn_model import WebAuthnCredential  # noqa: F401
    from app.api.webhooks.model import WebhookEvent  # noqa: F401
