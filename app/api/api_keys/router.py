import uuid

from fastapi import APIRouter

from app.api.api_keys.schemas import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from app.api.api_keys.service import APIKeyService
from app.api.auth.dependencies import CurrentUser
from app.config.database import DBSession

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _svc(db: DBSession) -> APIKeyService:
    return APIKeyService(db)


@router.post("", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> APIKeyCreatedResponse:
    api_key, raw_key = await _svc(db).create(current_user.id, body)
    response = APIKeyCreatedResponse.model_validate(api_key)
    response.raw_key = raw_key
    return response


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: CurrentUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 20,
) -> APIKeyListResponse:
    items, total = await _svc(db).list_for_user(
        current_user.id, page=page, page_size=page_size
    )
    return APIKeyListResponse(
        items=[APIKeyResponse.model_validate(k) for k in items],
        total=total,
    )


@router.post("/{api_key_id}/revoke", status_code=200)
async def revoke_api_key(
    api_key_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    await _svc(db).revoke(api_key_id, current_user.id)
    return {"revoked": True}


@router.delete("/{api_key_id}", status_code=204)
async def delete_api_key(
    api_key_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await _svc(db).delete(api_key_id, current_user.id)
