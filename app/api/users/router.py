import uuid

from fastapi import APIRouter, Query

from app.api.auth.dependencies import AdminUser, CurrentUser
from app.api.users.schemas import (
    UserAdminUpdate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.api.users.service import UserService
from app.config.database import DBSession

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UserUpdate, current_user: CurrentUser, db: DBSession
) -> UserResponse:
    service = UserService(db)
    user = await service.update(current_user, body)
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=204)
async def delete_account(current_user: CurrentUser, db: DBSession) -> None:
    service = UserService(db)
    await service.soft_delete(current_user)


# Admin endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    _: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
) -> UserListResponse:
    service = UserService(db)
    users, total = await service.list_users(page=page, page_size=page_size, search=search)
    pages = -(-total // page_size)  # ceiling division
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, _: AdminUser, db: DBSession) -> UserResponse:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID, body: UserAdminUpdate, _: AdminUser, db: DBSession
) -> UserResponse:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    updated = await service.admin_update(user, body)
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, _: AdminUser, db: DBSession) -> None:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    await service.soft_delete(user)
