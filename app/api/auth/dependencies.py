from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.users.model import User, UserRole
from app.api.users.service import UserService
from app.config.database import DBSession
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.exceptions.auth import InvalidTokenError
from app.core.security import decode_token
from app.services.cache import get_cache_service

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
) -> User:
    if not credentials:
        raise UnauthorizedError()

    try:
        payload = decode_token(credentials.credentials)
    except InvalidTokenError:
        raise UnauthorizedError(detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError(detail="Expected access token")

    import uuid

    user_id = uuid.UUID(payload["sub"])
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user.is_active:
        raise ForbiddenError(detail="Account is inactive")

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active:
        raise ForbiddenError(detail="Account is inactive")
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_admin:
        raise ForbiddenError(detail="Admin access required")
    return user


async def get_current_superuser(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user.role != UserRole.superuser:
        raise ForbiddenError(detail="Superuser access required")
    return user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin)]
SuperUser = Annotated[User, Depends(get_current_superuser)]
