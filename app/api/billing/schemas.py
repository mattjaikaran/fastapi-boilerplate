import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.billing.model import SubscriptionStatus


class CheckoutSessionRequest(BaseModel):
    price_id: str | None = None
    organization_id: uuid.UUID | None = None
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class BillingPortalRequest(BaseModel):
    return_url: str


class BillingPortalResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    stripe_subscription_id: str
    stripe_price_id: str
    plan: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool

    model_config = {"from_attributes": True}
