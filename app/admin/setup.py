from fastapi import FastAPI
from sqladmin import Admin

from app.admin.auth import authentication_backend
from app.admin.views import (
    APIKeyAdmin,
    AuditLogAdmin,
    BackgroundJobAdmin,
    BillingCustomerAdmin,
    FeatureFlagAdmin,
    FileUploadAdmin,
    NotificationAdmin,
    OTPCodeAdmin,
    OrgFeatureFlagAdmin,
    OrganizationAdmin,
    OrganizationMemberAdmin,
    RefreshTokenAdmin,
    SubscriptionAdmin,
    TodoAdmin,
    UserAdmin,
    WebhookEventAdmin,
)
from app.config.database import engine
from app.config.settings import settings


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(
        app,
        engine,
        title=f"{settings.APP_NAME} Admin",
        base_url="/admin",
        authentication_backend=authentication_backend,
    )

    # Auth
    admin.add_view(UserAdmin)
    admin.add_view(RefreshTokenAdmin)
    admin.add_view(OTPCodeAdmin)

    # Content
    admin.add_view(TodoAdmin)
    admin.add_view(FileUploadAdmin)

    # Organizations
    admin.add_view(OrganizationAdmin)
    admin.add_view(OrganizationMemberAdmin)

    # Billing
    admin.add_view(BillingCustomerAdmin)
    admin.add_view(SubscriptionAdmin)

    # Integrations
    admin.add_view(WebhookEventAdmin)
    admin.add_view(APIKeyAdmin)

    # System
    admin.add_view(NotificationAdmin)
    admin.add_view(AuditLogAdmin)
    admin.add_view(FeatureFlagAdmin)
    admin.add_view(OrgFeatureFlagAdmin)
    admin.add_view(BackgroundJobAdmin)

    return admin
