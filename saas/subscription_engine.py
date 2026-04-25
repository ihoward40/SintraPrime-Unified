"""
Subscription Engine for SintraPrime-Unified SaaS

Manages subscription lifecycle, Stripe integration, plan tiers, billing, and trial management.
"""

import stripe
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Tuple
from decimal import Decimal
import hashlib
import hmac

logger = logging.getLogger(__name__)


class PlanTier(str, Enum):
    """Available subscription plan tiers."""
    SOLO = "solo"
    PROFESSIONAL = "professional"
    LAW_FIRM = "law_firm"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle states."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    REACTIVATED = "reactivated"


@dataclass
class SubscriptionPlan:
    """Represents a subscription plan tier."""
    id: str
    name: str
    price: Decimal
    max_users: int
    queries_per_day: int
    voice_minutes_per_month: int
    document_pages_per_month: int
    has_white_label: bool
    has_client_portal: bool
    has_custom_models: bool
    dedicated_support: bool
    sla_uptime: Optional[float] = None
    stripe_price_id: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))


@dataclass
class UsageMetrics:
    """Usage metrics for a subscription."""
    api_calls: int = 0
    voice_minutes: int = 0
    documents_generated: int = 0
    active_users: int = 0
    storage_gb: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass
class OverageAlert:
    """Alert for usage overages."""
    metric: str
    current_usage: int
    limit: int
    percentage: float
    alert_level: str  # "warning" (80%) or "critical" (100%)
    triggered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subscription:
    """Represents a subscription."""
    id: str
    customer_id: str
    tenant_id: str
    plan_id: str
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str]
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime]
    cancel_at: Optional[datetime]
    canceled_at: Optional[datetime]
    cancel_reason: Optional[str]
    auto_renew: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Invoice:
    """Represents a billing invoice."""
    id: str
    subscription_id: str
    customer_id: str
    amount: Decimal
    currency: str
    status: str  # "draft", "open", "paid", "void", "uncollectible"
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime]
    pdf_url: Optional[str]
    line_items: List[Dict] = field(default_factory=list)


@dataclass
class Coupon:
    """Represents a discount coupon."""
    code: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: Decimal
    max_redemptions: Optional[int]
    redemptions_used: int
    expiry_date: Optional[datetime]
    active: bool


class SubscriptionEngine:
    """
    Manages subscription lifecycle, Stripe integration, and billing.
    
    Handles:
    - Customer and subscription creation
    - Plan upgrades/downgrades
    - Trial management
    - Metered billing
    - Overage alerts
    - Coupon/discount system
    - Webhook events
    """

    # Plan definitions
    PLANS = {
        PlanTier.SOLO: SubscriptionPlan(
            id=PlanTier.SOLO,
            name="Solo",
            price=Decimal("49"),
            max_users=1,
            queries_per_day=50,
            voice_minutes_per_month=60,
            document_pages_per_month=500,
            has_white_label=False,
            has_client_portal=False,
            has_custom_models=False,
            dedicated_support=False,
        ),
        PlanTier.PROFESSIONAL: SubscriptionPlan(
            id=PlanTier.PROFESSIONAL,
            name="Professional",
            price=Decimal("149"),
            max_users=5,
            queries_per_day=500,
            voice_minutes_per_month=300,
            document_pages_per_month=2000,
            has_white_label=False,
            has_client_portal=False,
            has_custom_models=False,
            dedicated_support=True,
        ),
        PlanTier.LAW_FIRM: SubscriptionPlan(
            id=PlanTier.LAW_FIRM,
            name="Law Firm",
            price=Decimal("499"),
            max_users=25,
            queries_per_day=-1,  # unlimited
            voice_minutes_per_month=-1,  # unlimited
            document_pages_per_month=-1,  # unlimited
            has_white_label=True,
            has_client_portal=True,
            has_custom_models=False,
            dedicated_support=True,
        ),
        PlanTier.ENTERPRISE: SubscriptionPlan(
            id=PlanTier.ENTERPRISE,
            name="Enterprise",
            price=Decimal("1999"),
            max_users=-1,  # unlimited
            queries_per_day=-1,  # unlimited
            voice_minutes_per_month=-1,  # unlimited
            document_pages_per_month=-1,  # unlimited
            has_white_label=True,
            has_client_portal=True,
            has_custom_models=True,
            dedicated_support=True,
            sla_uptime=0.9995,
        ),
    }

    TRIAL_DAYS = 14

    def __init__(self, stripe_api_key: str, webhook_secret: str):
        """Initialize Stripe integration."""
        stripe.api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        self._subscriptions: Dict[str, Subscription] = {}
        self._coupons: Dict[str, Coupon] = {}
        self._invoices: Dict[str, Invoice] = {}
        self._payment_methods: Dict[str, Dict] = {}
        self._overage_alerts: Dict[str, List[OverageAlert]] = {}

    def create_customer(
        self,
        tenant_id: str,
        email: str,
        name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Create a Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "tenant_id": tenant_id,
                    **(metadata or {})
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for tenant {tenant_id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            raise

    def create_subscription(
        self,
        customer_id: str,
        tenant_id: str,
        plan_id: str,
        trial: bool = True,
        coupon_code: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            customer_id: Stripe customer ID
            tenant_id: SintraPrime tenant ID
            plan_id: Plan tier (from PlanTier enum)
            trial: Enable 14-day free trial
            coupon_code: Optional coupon code for discount
            idempotency_key: Prevent duplicate charges
            
        Returns:
            Subscription object
        """
        plan = self.PLANS.get(plan_id)
        if not plan:
            raise ValueError(f"Invalid plan: {plan_id}")

        try:
            subscription_params = {
                "customer": customer_id,
                "items": [
                    {
                        "price": plan.stripe_price_id or f"price_{plan_id}",
                        "quantity": 1
                    }
                ],
                "metadata": {
                    "tenant_id": tenant_id,
                    "plan": plan_id,
                },
                "expand": ["latest_invoice.payment_intent"],
            }

            if trial:
                subscription_params["trial_period_days"] = self.TRIAL_DAYS

            if coupon_code:
                coupon = self._coupons.get(coupon_code)
                if coupon and coupon.active:
                    if coupon.max_redemptions is None or \
                       coupon.redemptions_used < coupon.max_redemptions:
                        subscription_params["coupon"] = coupon_code
                        coupon.redemptions_used += 1

            headers = {}
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key

            stripe_sub = stripe.Subscription.create(
                **subscription_params,
                **{"headers": headers} if headers else {}
            )

            trial_end = None
            if trial:
                trial_end = datetime.utcnow() + timedelta(days=self.TRIAL_DAYS)

            subscription = Subscription(
                id=f"sub_{tenant_id}_{int(datetime.utcnow().timestamp())}",
                customer_id=customer_id,
                tenant_id=tenant_id,
                plan_id=plan_id,
                status=SubscriptionStatus.TRIAL if trial else SubscriptionStatus.ACTIVE,
                stripe_subscription_id=stripe_sub.id,
                current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end),
                trial_end=trial_end,
                cancel_at=None,
                canceled_at=None,
                cancel_reason=None,
            )

            self._subscriptions[subscription.id] = subscription
            logger.info(f"Created subscription {subscription.id} for tenant {tenant_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    def upgrade_plan(self, subscription_id: str, new_plan_id: str) -> Subscription:
        """
        Upgrade a subscription to a higher-tier plan.
        
        Uses proration for mid-cycle upgrades.
        """
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        new_plan = self.PLANS.get(new_plan_id)
        if not new_plan:
            raise ValueError(f"Invalid plan: {new_plan_id}")

        try:
            # Update the Stripe subscription
            updated_stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[
                    {
                        "id": stripe.Subscription.retrieve(
                            subscription.stripe_subscription_id
                        ).items.data[0].id,
                        "price": new_plan.stripe_price_id or f"price_{new_plan_id}",
                    }
                ],
                proration_behavior="create_prorations",
            )

            subscription.plan_id = new_plan_id
            subscription.updated_at = datetime.utcnow()

            logger.info(f"Upgraded subscription {subscription_id} to {new_plan_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to upgrade subscription: {e}")
            raise

    def downgrade_plan(
        self,
        subscription_id: str,
        new_plan_id: str,
        downgrade_at: str = "immediately"
    ) -> Subscription:
        """
        Downgrade a subscription to a lower-tier plan.
        
        Args:
            subscription_id: Subscription ID
            new_plan_id: New plan tier
            downgrade_at: "immediately" or "end_of_cycle"
        """
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        new_plan = self.PLANS.get(new_plan_id)
        if not new_plan:
            raise ValueError(f"Invalid plan: {new_plan_id}")

        try:
            proration = "create_prorations" if downgrade_at == "immediately" else "none"

            updated_stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[
                    {
                        "id": stripe.Subscription.retrieve(
                            subscription.stripe_subscription_id
                        ).items.data[0].id,
                        "price": new_plan.stripe_price_id or f"price_{new_plan_id}",
                    }
                ],
                proration_behavior=proration,
            )

            subscription.plan_id = new_plan_id
            subscription.updated_at = datetime.utcnow()

            logger.info(f"Downgraded subscription {subscription_id} to {new_plan_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to downgrade subscription: {e}")
            raise

    def cancel_subscription(
        self,
        subscription_id: str,
        reason: str,
        immediate: bool = False
    ) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            reason: Cancellation reason
            immediate: Cancel immediately or at period end
        """
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        try:
            if immediate:
                stripe_sub = stripe.Subscription.delete(
                    subscription.stripe_subscription_id
                )
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
            else:
                stripe_sub = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at = datetime.fromtimestamp(
                    stripe_sub.cancel_at
                )

            subscription.cancel_reason = reason
            subscription.updated_at = datetime.utcnow()

            logger.info(f"Canceled subscription {subscription_id}: {reason}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    def reactivate_subscription(self, subscription_id: str) -> Subscription:
        """Reactivate a canceled subscription."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")

        if subscription.status != SubscriptionStatus.CANCELED:
            raise ValueError(
                f"Cannot reactivate subscription with status: {subscription.status}"
            )

        try:
            # Create a new subscription for the customer
            plan = self.PLANS[subscription.plan_id]
            new_subscription = self.create_subscription(
                customer_id=subscription.customer_id,
                tenant_id=subscription.tenant_id,
                plan_id=subscription.plan_id,
                trial=False
            )
            new_subscription.status = SubscriptionStatus.REACTIVATED
            logger.info(f"Reactivated subscription {subscription_id}")
            return new_subscription

        except Exception as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            raise

    def track_metered_usage(
        self,
        subscription_id: str,
        metric: str,
        quantity: int
    ) -> bool:
        """Track metered usage for billing (voice minutes, document pages)."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return False

        try:
            # Report usage to Stripe
            stripe.SubscriptionItem.create_usage_record(
                subscription.stripe_subscription_id,
                quantity=quantity,
                timestamp=int(datetime.utcnow().timestamp()),
            )
            logger.debug(
                f"Tracked {metric}: {quantity} units for subscription {subscription_id}"
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to track metered usage: {e}")
            return False

    def check_usage_alerts(
        self,
        subscription_id: str,
        usage_metrics: UsageMetrics
    ) -> List[OverageAlert]:
        """Check for usage overages and generate alerts."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return []

        plan = self.PLANS[subscription.plan_id]
        alerts = []

        # Check API calls
        if plan.queries_per_day > 0:
            percentage = (usage_metrics.api_calls / plan.queries_per_day) * 100
            if percentage >= 100:
                alerts.append(
                    OverageAlert(
                        metric="api_calls",
                        current_usage=usage_metrics.api_calls,
                        limit=plan.queries_per_day,
                        percentage=percentage,
                        alert_level="critical",
                    )
                )
            elif percentage >= 80:
                alerts.append(
                    OverageAlert(
                        metric="api_calls",
                        current_usage=usage_metrics.api_calls,
                        limit=plan.queries_per_day,
                        percentage=percentage,
                        alert_level="warning",
                    )
                )

        # Check voice minutes
        if plan.voice_minutes_per_month > 0:
            percentage = (usage_metrics.voice_minutes / plan.voice_minutes_per_month) * 100
            if percentage >= 100:
                alerts.append(
                    OverageAlert(
                        metric="voice_minutes",
                        current_usage=usage_metrics.voice_minutes,
                        limit=plan.voice_minutes_per_month,
                        percentage=percentage,
                        alert_level="critical",
                    )
                )
            elif percentage >= 80:
                alerts.append(
                    OverageAlert(
                        metric="voice_minutes",
                        current_usage=usage_metrics.voice_minutes,
                        limit=plan.voice_minutes_per_month,
                        percentage=percentage,
                        alert_level="warning",
                    )
                )

        self._overage_alerts[subscription_id] = alerts
        return alerts

    def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_value: Decimal,
        max_redemptions: Optional[int] = None,
        expiry_date: Optional[datetime] = None
    ) -> Coupon:
        """Create a promotional coupon."""
        coupon = Coupon(
            code=code.upper(),
            discount_type=discount_type,
            discount_value=discount_value,
            max_redemptions=max_redemptions,
            redemptions_used=0,
            expiry_date=expiry_date,
            active=True,
        )
        self._coupons[code.upper()] = coupon
        logger.info(f"Created coupon {code}")
        return coupon

    def validate_coupon(self, code: str) -> Tuple[bool, Optional[Coupon]]:
        """Validate a coupon code."""
        coupon = self._coupons.get(code.upper())
        if not coupon:
            return False, None

        if not coupon.active:
            return False, coupon

        if coupon.expiry_date and datetime.utcnow() > coupon.expiry_date:
            coupon.active = False
            return False, coupon

        if coupon.max_redemptions and coupon.redemptions_used >= coupon.max_redemptions:
            coupon.active = False
            return False, coupon

        return True, coupon

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self._subscriptions.get(subscription_id)

    def get_customer_subscriptions(self, customer_id: str) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        return [
            sub for sub in self._subscriptions.values()
            if sub.customer_id == customer_id
        ]

    def get_usage_report(self, subscription_id: str) -> Dict:
        """Get usage report for a subscription."""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return {}

        plan = self.PLANS[subscription.plan_id]
        return {
            "subscription_id": subscription_id,
            "plan": subscription.plan_id,
            "status": subscription.status,
            "period_start": subscription.current_period_start.isoformat(),
            "period_end": subscription.current_period_end.isoformat(),
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "plan_details": {
                "queries_per_day": plan.queries_per_day,
                "voice_minutes_per_month": plan.voice_minutes_per_month,
                "document_pages_per_month": plan.document_pages_per_month,
                "max_users": plan.max_users,
            },
        }

    def handle_webhook(self, payload: str, signature: str) -> Dict:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return {"error": "Invalid signature"}

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "invoice.payment_succeeded":
            logger.info(f"Invoice paid: {data['id']}")
            return {"status": "processed"}

        elif event_type == "invoice.payment_failed":
            logger.warning(f"Invoice payment failed: {data['id']}")
            # Trigger retry logic and dunning management
            return {"status": "processed"}

        elif event_type == "customer.subscription.deleted":
            logger.info(f"Subscription deleted: {data['id']}")
            return {"status": "processed"}

        elif event_type == "customer.subscription.updated":
            logger.info(f"Subscription updated: {data['id']}")
            return {"status": "processed"}

        return {"status": "received"}

    def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get plan details."""
        return self.PLANS.get(plan_id)

    def list_plans(self) -> List[SubscriptionPlan]:
        """List all available plans."""
        return list(self.PLANS.values())
