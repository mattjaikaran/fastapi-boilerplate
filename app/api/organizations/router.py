import uuid

from fastapi import APIRouter

from app.api.auth.dependencies import CurrentUser
from app.api.organizations.schemas import (
    InviteMemberRequest,
    MemberResponse,
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.api.organizations.service import OrganizationService
from app.config.database import DBSession
from app.core.exceptions import ForbiddenError

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _svc(db: DBSession) -> OrganizationService:
    return OrganizationService(db)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> OrganizationResponse:
    org = await _svc(db).create(owner_id=current_user.id, data=body)
    return OrganizationResponse.model_validate(org)


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    current_user: CurrentUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 20,
) -> OrganizationListResponse:
    orgs, total = await _svc(db).list_for_user(user_id=current_user.id, page=page, page_size=page_size)
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(o) for o in orgs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> OrganizationResponse:
    svc = _svc(db)
    org = await svc.get_by_id(org_id)
    await svc._require_member(org_id, current_user.id)
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> OrganizationResponse:
    svc = _svc(db)
    org = await svc.get_by_id(org_id)
    updated = await svc.update(org, actor_id=current_user.id, data=body)
    return OrganizationResponse.model_validate(updated)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    svc = _svc(db)
    org = await svc.get_by_id(org_id)
    await svc.delete(org, actor_id=current_user.id)


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> list[MemberResponse]:
    svc = _svc(db)
    await svc._require_member(org_id, current_user.id)
    members = await svc.list_members(org_id)
    return [MemberResponse.model_validate(m) for m in members]


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=201)
async def add_member(
    org_id: uuid.UUID,
    body: InviteMemberRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> MemberResponse:
    member = await _svc(db).add_member(org_id, actor_id=current_user.id, data=body)
    return MemberResponse.model_validate(member)


@router.delete("/{org_id}/members/{user_id}", status_code=204)
async def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await _svc(db).remove_member(org_id, user_id=user_id, actor_id=current_user.id)
