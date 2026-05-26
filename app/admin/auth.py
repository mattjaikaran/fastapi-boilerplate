from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config.settings import settings
from app.core.security.password import verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        if request.method != "POST":
            return False

        form = await request.form()
        email = form.get("username")  # sqladmin uses "username" field name
        password = form.get("password")

        if not email or not password:
            return False

        from app.api.users.service import UserService
        from app.config.database import async_session_factory

        async with async_session_factory() as db:
            service = UserService(db)
            user = await service.get_by_email(str(email))

        if not user or not user.is_active or not user.is_admin:
            return False

        if not user.hashed_password or not verify_password(str(password), user.hashed_password):
            return False

        request.session["admin_user_id"] = str(user.id)
        request.session["admin_authenticated"] = True
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        if not request.session.get("admin_authenticated"):
            return False

        user_id_str = request.session.get("admin_user_id")
        if not user_id_str:
            return False

        import uuid

        from app.api.users.service import UserService
        from app.config.database import async_session_factory

        try:
            user_id = uuid.UUID(user_id_str)
            async with async_session_factory() as db:
                service = UserService(db)
                user = await service.get_by_id(user_id)
            return user.is_active and user.is_admin
        except Exception:
            request.session.clear()
            return False


authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
