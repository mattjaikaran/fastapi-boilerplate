import uuid

from fastapi import APIRouter, Request

from app.api.auth.dependencies import CurrentUser
from app.api.notifications.schemas import (
    MarkReadRequest,
    NotificationListResponse,
    NotificationResponse,
)
from app.api.notifications.service import NotificationService
from app.config.database import DBSession
from app.core.rate_limit import limiter

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _svc(db: DBSession) -> NotificationService:
    return NotificationService(db)


@router.get("", response_model=NotificationListResponse)
@limiter.limit("60/minute")
async def list_notifications(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> NotificationListResponse:
    items, total, unread_count = await _svc(db).list_for_user(
        current_user.id, page=page, page_size=page_size, unread_only=unread_only
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
    )


@router.post("/mark-read", status_code=200)
@limiter.limit("30/minute")
async def mark_read(
    request: Request,
    body: MarkReadRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    count = await _svc(db).mark_read(current_user.id, body.notification_ids)
    return {"marked_read": count}


@router.post("/mark-all-read", status_code=200)
@limiter.limit("10/minute")
async def mark_all_read(request: Request, current_user: CurrentUser, db: DBSession) -> dict:
    count = await _svc(db).mark_all_read(current_user.id)
    return {"marked_read": count}


@router.delete("/{notification_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_notification(
    request: Request,
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    await _svc(db).delete(current_user.id, notification_id)
