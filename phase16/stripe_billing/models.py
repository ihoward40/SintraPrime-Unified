"""Phase 16B — Stripe Billing Portal: data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanTier(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"


class UsageMetric(str, Enum):
    QUERIES = "queries"
    DOCUMENTS = "documents"
    AGENTS = "agents"
    API_CALLS = "api_calls"
    STORAGE_GB = "storage_gb"


@dataclass
class Plan:
    """A SintraPrime billing plan."""
    plan_id: str
    tier: PlanTier
    name: str
    monthly_price_cents: int
    annual_price_cents: int
    features: List[str] = field(default_factory=list)
    usage_limits: Dict[str, int] = field(default_factory=dict)
    stripe_price_id_monthly: str = ""
    stripe_price_id_annual: str = ""

    def get_price(self, interval: BillingInterval) -> int:
        return self.annual_price_cents if interval == BillingInterval.ANNUAL else self.monthly_price_cents

    def annual_savings_cents(self) -> int:
        return self.monthly_price_cents * 12 - self.annual_price_cents


@dataclass
class Customer:
    """A SintraPrime customer."""
    customer_id: str
    email: str
    name: str
    stripe_customer_id: str = ""
    plan_tier: PlanTier = PlanTier.STARTER
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """An active subscription."""
    subscription_id: str
    customer_id: str
    plan: Plan
    status: SubscriptionStatus
    current_period_start: float = 0.0
    current_period_end: float = 0.0
    trial_end: Optional[float] = None
    cancel_at_period_end: bool = False
    stripe_subscription_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)


@dataclass
class UsageRecord:
    """A usage record for metered billing."""
    record_id: str
    customer_id: str
    metric: UsageMetric
    quantity: int
    timestamp: float
    subscription_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """A billing invoice."""
    invoice_id: str
    customer_id: str
    subscription_id: str
    amount_due_cents: int
    amount_paid_cents: int
    status: str  # draft, open, paid, void, uncollectible
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    stripe_invoice_id: str = ""
    created_at: float = 0.0
    paid_at: Optional[float] = None

    @property
    def is_paid(self) -> bool:
        return self.status == "paid"


@dataclass
class BillingPortalSession:
    """A Stripe billing portal session."""
    session_id: str
    customer_id: str
    url: str
    return_url: str
    expires_at: float
    created_at: float = 0.0
