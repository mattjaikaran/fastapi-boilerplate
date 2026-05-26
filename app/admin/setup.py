from fastapi import FastAPI
from sqladmin import Admin

from app.admin.auth import authentication_backend
from app.admin.views import FileUploadAdmin, OTPCodeAdmin, RefreshTokenAdmin, TodoAdmin, UserAdmin
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

    admin.add_view(UserAdmin)
    admin.add_view(TodoAdmin)
    admin.add_view(FileUploadAdmin)
    admin.add_view(RefreshTokenAdmin)
    admin.add_view(OTPCodeAdmin)

    return admin
