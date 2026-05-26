import uuid
from datetime import UTC, datetime

import stripe as stripe_lib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.billing.model import BillingCustomer, Subscription, SubscriptionStatus
from app.api.billing.schemas import CheckoutSessionRequest
from app.api.users.model import User
from app.config.settings import settings
from app.core.exceptions import NotFoundError


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        stripe_lib.api_key = settings.STRIPE_API_KEY

    async def get_or_create_customer(self, user: User) -> BillingCustomer:
        result = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.user_id == user.id)
        )
        customer = result.scalar_one_or_none()
        if customer:
            return customer

        stripe_customer = stripe_lib.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": str(user.id)},
        )
        customer = BillingCustomer(
            user_id=user.id,
            stripe_customer_id=stripe_customer.id,
        )
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    async def create_checkout_session(
        self,
        user: User,
        data: CheckoutSessionRequest,
    ) -> tuple[str, str]:
        customer = await self.get_or_create_customer(user)
        price_id = data.price_id or settings.STRIPE_DEFAULT_PRICE_ID

        session = stripe_lib.checkout.Session.create(
            customer=customer.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            metadata={
                "user_id": str(user.id),
                "organization_id": str(data.organization_id) if data.organization_id else "",
            },
        )
        return session.url, session.id

    async def create_portal_session(self, user: User, return_url: str) -> str:
        customer = await self.get_or_create_customer(user)
        session = stripe_lib.billing_portal.Session.create(
            customer=customer.stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    async def get_active_subscription(self, user: User) -> Subscription | None:
        customer = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.user_id == user.id)
        )
        billing = customer.scalar_one_or_none()
        if not billing:
            return None

        result = await self.db.execute(
            select(Subscription).where(
                Subscription.customer_id == billing.id,
                Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trialing]),
            )
        )
        return result.scalar_one_or_none()

    async def cancel_subscription(self, user: User) -> Subscription:
        sub = await self.get_active_subscription(user)
        if not sub:
            raise NotFoundError(detail="No active subscription found")

        stripe_lib.Subscription.modify(
            sub.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        sub.cancel_at_period_end = True
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def handle_stripe_event(self, event: dict) -> None:
        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data)
        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data)

    async def _handle_checkout_completed(self, session_data: dict) -> None:
        stripe_sub_id = session_data.get("subscription")
        customer_id = session_data.get("customer")
        if not stripe_sub_id or not customer_id:
            return

        result = await self.db.execute(
            select(BillingCustomer).where(BillingCustomer.stripe_customer_id == customer_id)
        )
        billing = result.scalar_one_or_none()
        if not billing:
            return

        stripe_sub = stripe_lib.Subscription.retrieve(stripe_sub_id)
        org_id_str = session_data.get("metadata", {}).get("organization_id")
        org_id = uuid.UUID(org_id_str) if org_id_str else None

        sub = Subscription(
            customer_id=billing.id,
            organization_id=org_id,
            stripe_subscription_id=stripe_sub.id,
            stripe_price_id=stripe_sub["items"]["data"][0]["price"]["id"],
            plan=stripe_sub["items"]["data"][0]["price"].get("nickname") or "pro",
            status=SubscriptionStatus(stripe_sub.status),
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start, tz=UTC),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC),
        )
        self.db.add(sub)
        await self.db.flush()

    async def _handle_subscription_updated(self, sub_data: dict) -> None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == sub_data["id"])
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return

        sub.status = SubscriptionStatus(sub_data["status"])
        sub.cancel_at_period_end = sub_data.get("cancel_at_period_end", False)
        if sub_data.get("current_period_start"):
            sub.current_period_start = datetime.fromtimestamp(sub_data["current_period_start"], tz=UTC)
        if sub_data.get("current_period_end"):
            sub.current_period_end = datetime.fromtimestamp(sub_data["current_period_end"], tz=UTC)
        self.db.add(sub)
        await self.db.flush()

    async def _handle_subscription_deleted(self, sub_data: dict) -> None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == sub_data["id"])
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return
        sub.status = SubscriptionStatus.canceled
        self.db.add(sub)
        await self.db.flush()
