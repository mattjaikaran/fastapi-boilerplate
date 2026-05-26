import uuid
from typing import Any

import orjson
from fastapi import APIRouter, Header, HTTPException, Request

from app.api.auth.dependencies import AdminUser
from app.api.webhooks.model import WebhookEventStatus
from app.api.webhooks.schemas import WebhookEventListResponse, WebhookEventResponse
from app.api.webhooks.service import WebhookService
from app.config.database import DBSession
from app.config.settings import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Map source names to their HMAC secrets from settings.
# Add more sources by extending this mapping.
_SOURCE_SECRETS: dict[str, str] = {}


def _get_secret(source: str) -> str | None:
    return _SOURCE_SECRETS.get(source)


@router.post("/{source}", status_code=202)
async def receive_webhook(
    source: str,
    request: Request,
    db: DBSession,
    x_hub_signature_256: str | None = Header(default=None),
    x_signature: str | None = Header(default=None),
    x_webhook_signature: str | None = Header(default=None),
    x_event_type: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_idempotency_key: str | None = Header(default=None),
) -> dict[str, str]:
    body = await request.body()

    try:
        payload: dict[str, Any] = orjson.loads(body) if body else {}
    except Exception:
        payload = {"raw": body.decode(errors="replace")}

    signature = x_hub_signature_256 or x_signature or x_webhook_signature
    secret = _get_secret(source)
    svc = WebhookService(db)
    signature_valid = svc.validate_signature(body, signature, secret or "") if secret else True

    event_type = (
        x_event_type
        or x_github_event
        or payload.get("type")
        or payload.get("event_type")
        or payload.get("event")
    )

    relevant_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower().startswith("x-") or k.lower() in ("content-type",)
    }

    await svc.record_event(
        source=source,
        payload=payload,
        headers=relevant_headers,
        signature_valid=signature_valid,
        event_type=event_type,
        idempotency_key=x_idempotency_key,
    )

    return {"status": "accepted"}


@router.get("/events", response_model=WebhookEventListResponse)
async def list_events(
    _: AdminUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 50,
    source: str | None = None,
    status: WebhookEventStatus | None = None,
) -> WebhookEventListResponse:
    events, total = await WebhookService(db).list_events(
        page=page, page_size=page_size, source=source, status=status
    )
    return WebhookEventListResponse(
        items=[WebhookEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}", response_model=WebhookEventResponse)
async def get_event(
    event_id: uuid.UUID,
    _: AdminUser,
    db: DBSession,
) -> WebhookEventResponse:
    event = await WebhookService(db).get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return WebhookEventResponse.model_validate(event)
