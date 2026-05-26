import uuid

from fastapi import APIRouter

from app.api.auth.dependencies import AdminUser, CurrentUser
from app.api.feature_flags.schemas import (
    FeatureFlagCreate,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
    FlagEvalResponse,
    OrgOverrideRequest,
)
from app.api.feature_flags.service import FeatureFlagService
from app.config.database import DBSession

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


def _svc(db: DBSession) -> FeatureFlagService:
    return FeatureFlagService(db)


@router.post("", response_model=FeatureFlagResponse, status_code=201)
async def create_flag(
    _: AdminUser, body: FeatureFlagCreate, db: DBSession
) -> FeatureFlagResponse:
    flag = await _svc(db).create(body)
    return FeatureFlagResponse.model_validate(flag)


@router.get("", response_model=FeatureFlagListResponse)
async def list_flags(
    _: AdminUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 50,
) -> FeatureFlagListResponse:
    items, total = await _svc(db).list(page=page, page_size=page_size)
    return FeatureFlagListResponse(
        items=[FeatureFlagResponse.model_validate(f) for f in items], total=total
    )


@router.get("/eval/{key}", response_model=FlagEvalResponse)
async def evaluate_flag(
    key: str,
    current_user: CurrentUser,
    db: DBSession,
    org_id: uuid.UUID | None = None,
) -> FlagEvalResponse:
    enabled, source = await _svc(db).evaluate(key, org_id=org_id)
    return FlagEvalResponse(key=key, enabled=enabled, source=source)


@router.get("/{flag_id}", response_model=FeatureFlagResponse)
async def get_flag(
    _: AdminUser, flag_id: uuid.UUID, db: DBSession
) -> FeatureFlagResponse:
    flag = await _svc(db).get_by_id(flag_id)
    return FeatureFlagResponse.model_validate(flag)


@router.patch("/{flag_id}", response_model=FeatureFlagResponse)
async def update_flag(
    _: AdminUser, flag_id: uuid.UUID, body: FeatureFlagUpdate, db: DBSession
) -> FeatureFlagResponse:
    svc = _svc(db)
    flag = await svc.get_by_id(flag_id)
    updated = await svc.update(flag, body)
    return FeatureFlagResponse.model_validate(updated)


@router.delete("/{flag_id}", status_code=204)
async def delete_flag(_: AdminUser, flag_id: uuid.UUID, db: DBSession) -> None:
    svc = _svc(db)
    flag = await svc.get_by_id(flag_id)
    await svc.delete(flag)


@router.put("/{flag_id}/orgs/{org_id}", response_model=dict)
async def set_org_override(
    _: AdminUser,
    flag_id: uuid.UUID,
    org_id: uuid.UUID,
    body: OrgOverrideRequest,
    db: DBSession,
) -> dict:
    await _svc(db).set_org_override(flag_id, org_id, body.enabled)
    return {"flag_id": str(flag_id), "org_id": str(org_id), "enabled": body.enabled}


@router.delete("/{flag_id}/orgs/{org_id}", status_code=204)
async def delete_org_override(
    _: AdminUser, flag_id: uuid.UUID, org_id: uuid.UUID, db: DBSession
) -> None:
    await _svc(db).delete_org_override(flag_id, org_id)
