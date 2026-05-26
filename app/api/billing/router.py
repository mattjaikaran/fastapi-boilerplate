import stripe as stripe_lib
from fastapi import APIRouter, Header, HTTPException, Request

from app.api.auth.dependencies import CurrentUser
from app.api.billing.schemas import (
    BillingPortalRequest,
    BillingPortalResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionResponse,
)
from app.api.billing.service import BillingService
from app.config.database import DBSession
from app.config.settings import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _svc(db: DBSession) -> BillingService:
    return BillingService(db)


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    body: CheckoutSessionRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> CheckoutSessionResponse:
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    url, session_id = await _svc(db).create_checkout_session(current_user, body)
    return CheckoutSessionResponse(checkout_url=url, session_id=session_id)


@router.post("/portal", response_model=BillingPortalResponse)
async def create_portal(
    body: BillingPortalRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> BillingPortalResponse:
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    url = await _svc(db).create_portal_session(current_user, body.return_url)
    return BillingPortalResponse(portal_url=url)


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    current_user: CurrentUser,
    db: DBSession,
) -> SubscriptionResponse | None:
    sub = await _svc(db).get_active_subscription(current_user)
    if not sub:
        return None
    return SubscriptionResponse.model_validate(sub)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    current_user: CurrentUser,
    db: DBSession,
) -> SubscriptionResponse:
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=501, detail="Stripe is not configured")
    sub = await _svc(db).cancel_subscription(current_user)
    return SubscriptionResponse.model_validate(sub)


@router.post("/stripe-webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    db: DBSession,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
) -> dict[str, str]:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Stripe webhook secret not configured")

    body = await request.body()
    try:
        event = stripe_lib.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe_lib.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")

    await _svc(db).handle_stripe_event(dict(event))
    return {"status": "ok"}
