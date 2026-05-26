import uuid

from fastapi import APIRouter

from app.api.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.api.audit.service import AuditService
from app.api.auth.dependencies import AdminUser, CurrentUser
from app.config.database import DBSession

router = APIRouter(prefix="/audit", tags=["audit"])


def _svc(db: DBSession) -> AuditService:
    return AuditService(db)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    _: AdminUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 50,
    actor_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
) -> AuditLogListResponse:
    items, total = await _svc(db).list(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        org_id=org_id,
        action=action,
        resource_type=resource_type,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/me", response_model=AuditLogListResponse)
async def list_my_audit_logs(
    current_user: CurrentUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 50,
) -> AuditLogListResponse:
    items, total = await _svc(db).list(
        page=page, page_size=page_size, actor_id=current_user.id
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )
