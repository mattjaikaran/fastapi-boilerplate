import uuid

from fastapi import APIRouter, Query

from app.api.api_keys.schemas import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from app.api.api_keys.service import APIKeyService
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
async def get_profile(current_user: CurrentUser, db: DBSession) -> UserResponse:
    return await UserService(db).to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UserUpdate, current_user: CurrentUser, db: DBSession
) -> UserResponse:
    service = UserService(db)
    user = await service.update(current_user, body)
    return await service.to_response(user)


@router.delete("/me", status_code=204)
async def delete_account(current_user: CurrentUser, db: DBSession) -> None:
    service = UserService(db)
    await service.soft_delete(current_user)


# API key management
@router.post("/me/api-keys", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: APIKeyCreate, current_user: CurrentUser, db: DBSession
) -> APIKeyCreatedResponse:
    service = APIKeyService(db)
    api_key, raw_key = await service.create(current_user.id, body)
    return APIKeyCreatedResponse(
        **APIKeyResponse.model_validate(api_key).model_dump(), raw_key=raw_key
    )


@router.get("/me/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> APIKeyListResponse:
    service = APIKeyService(db)
    keys, total = await service.list_for_user(
        current_user.id, page=page, page_size=page_size
    )
    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in keys], total=total
    )


@router.delete("/me/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    service = APIKeyService(db)
    await service.revoke(key_id, current_user.id)


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
    users, total = await service.list_users(
        page=page, page_size=page_size, search=search
    )
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
