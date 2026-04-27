"""Phase 16B — Stripe Billing Portal: main implementation."""
from __future__ import annotations
import time
import threading
import uuid
from typing import Any, Dict, List, Optional

from phase16.stripe_billing.models import (
    BillingInterval, BillingPortalSession, Customer, Invoice,
    Plan, PlanTier, Subscription, SubscriptionStatus, UsageMetric, UsageRecord,
)


# ─────────────────────────────────────────────────────────────
# Plan Catalog
# ─────────────────────────────────────────────────────────────
PLAN_CATALOG: Dict[PlanTier, Plan] = {
    PlanTier.STARTER: Plan(
        plan_id="plan_starter",
        tier=PlanTier.STARTER,
        name="Starter",
        monthly_price_cents=9900,
        annual_price_cents=99_000,
        features=["50 AI queries/mo", "5 documents", "Email support"],
        usage_limits={"queries": 50, "documents": 5, "agents": 1, "api_calls": 500},
        stripe_price_id_monthly="price_starter_monthly",
        stripe_price_id_annual="price_starter_annual",
    ),
    PlanTier.PROFESSIONAL: Plan(
        plan_id="plan_professional",
        tier=PlanTier.PROFESSIONAL,
        name="Professional",
        monthly_price_cents=29900,
        annual_price_cents=299_000,
        features=["500 AI queries/mo", "50 documents", "Priority support", "CPA routing"],
        usage_limits={"queries": 500, "documents": 50, "agents": 5, "api_calls": 5000},
        stripe_price_id_monthly="price_pro_monthly",
        stripe_price_id_annual="price_pro_annual",
    ),
    PlanTier.ENTERPRISE: Plan(
        plan_id="plan_enterprise",
        tier=PlanTier.ENTERPRISE,
        name="Enterprise",
        monthly_price_cents=99900,
        annual_price_cents=999_000,
        features=["Unlimited queries", "Unlimited documents", "Dedicated support", "Custom integrations"],
        usage_limits={"queries": -1, "documents": -1, "agents": -1, "api_calls": -1},
        stripe_price_id_monthly="price_enterprise_monthly",
        stripe_price_id_annual="price_enterprise_annual",
    ),
}


# ─────────────────────────────────────────────────────────────
# Usage Meter
# ─────────────────────────────────────────────────────────────
class UsageMeter:
    """Tracks per-customer usage for metered billing."""

    def __init__(self):
        self._records: Dict[str, List[UsageRecord]] = {}
        self._lock = threading.Lock()

    def record(self, customer_id: str, metric: UsageMetric, quantity: int = 1,
               subscription_id: str = "") -> UsageRecord:
        record = UsageRecord(
            record_id=f"ur_{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            metric=metric,
            quantity=quantity,
            timestamp=time.time(),
            subscription_id=subscription_id,
        )
        with self._lock:
            self._records.setdefault(customer_id, []).append(record)
        return record

    def get_usage(self, customer_id: str, metric: UsageMetric,
                  since: Optional[float] = None) -> int:
        with self._lock:
            records = self._records.get(customer_id, [])
        total = 0
        for r in records:
            if r.metric == metric:
                if since is None or r.timestamp >= since:
                    total += r.quantity
        return total

    def get_all_usage(self, customer_id: str,
                      since: Optional[float] = None) -> Dict[str, int]:
        return {
            metric.value: self.get_usage(customer_id, metric, since)
            for metric in UsageMetric
        }

    def check_limit(self, customer_id: str, metric: UsageMetric,
                    plan: Plan, since: Optional[float] = None) -> bool:
        """Return True if customer is within their plan limit."""
        limit = plan.usage_limits.get(metric.value, 0)
        if limit == -1:  # unlimited
            return True
        used = self.get_usage(customer_id, metric, since)
        return used < limit

    def reset(self, customer_id: str) -> None:
        with self._lock:
            self._records.pop(customer_id, None)


# ─────────────────────────────────────────────────────────────
# Invoice Generator
# ─────────────────────────────────────────────────────────────
class InvoiceGenerator:
    """Generates and manages invoices for subscriptions."""

    def __init__(self):
        self._invoices: Dict[str, Invoice] = {}
        self._lock = threading.Lock()

    def create_invoice(self, customer: Customer, subscription: Subscription,
                       usage_records: Optional[List[UsageRecord]] = None) -> Invoice:
        plan = subscription.plan
        base_amount = plan.get_price(customer.billing_interval)
        line_items: List[Dict[str, Any]] = [
            {"description": f"{plan.name} Plan", "amount_cents": base_amount}
        ]

        # Add usage overages
        if usage_records:
            overage_cents = self._compute_overages(usage_records, plan)
            if overage_cents > 0:
                line_items.append({"description": "Usage overage", "amount_cents": overage_cents})

        total = sum(item["amount_cents"] for item in line_items)
        invoice = Invoice(
            invoice_id=f"inv_{uuid.uuid4().hex[:8]}",
            customer_id=customer.customer_id,
            subscription_id=subscription.subscription_id,
            amount_due_cents=total,
            amount_paid_cents=0,
            status="open",
            line_items=line_items,
            created_at=time.time(),
        )
        with self._lock:
            self._invoices[invoice.invoice_id] = invoice
        return invoice

    def mark_paid(self, invoice_id: str) -> Invoice:
        with self._lock:
            inv = self._invoices.get(invoice_id)
            if not inv:
                raise KeyError(f"Invoice {invoice_id} not found")
            inv.amount_paid_cents = inv.amount_due_cents
            inv.status = "paid"
            inv.paid_at = time.time()
        return inv

    def void_invoice(self, invoice_id: str) -> Invoice:
        with self._lock:
            inv = self._invoices.get(invoice_id)
            if not inv:
                raise KeyError(f"Invoice {invoice_id} not found")
            inv.status = "void"
        return inv

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        with self._lock:
            return self._invoices.get(invoice_id)

    def list_invoices(self, customer_id: str) -> List[Invoice]:
        with self._lock:
            return [inv for inv in self._invoices.values()
                    if inv.customer_id == customer_id]

    def _compute_overages(self, records: List[UsageRecord], plan: Plan) -> int:
        """Compute overage charges at $0.01 per excess unit."""
        overage_units = 0
        by_metric: Dict[str, int] = {}
        for r in records:
            by_metric[r.metric.value] = by_metric.get(r.metric.value, 0) + r.quantity
        for metric_name, used in by_metric.items():
            limit = plan.usage_limits.get(metric_name, 0)
            if limit > 0 and used > limit:
                overage_units += used - limit
        return overage_units  # 1 cent per unit


# ─────────────────────────────────────────────────────────────
# Billing Portal
# ─────────────────────────────────────────────────────────────
class BillingPortal:
    """Main billing portal — manages customers, subscriptions, and invoices."""

    def __init__(self, base_url: str = "https://sintra.prime/billing"):
        self._base_url = base_url
        self._customers: Dict[str, Customer] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._sessions: Dict[str, BillingPortalSession] = {}
        self._usage_meter = UsageMeter()
        self._invoice_gen = InvoiceGenerator()
        self._lock = threading.Lock()

    # ── Customer management ──────────────────────────────────
    def create_customer(self, email: str, name: str,
                        plan_tier: PlanTier = PlanTier.STARTER,
                        billing_interval: BillingInterval = BillingInterval.MONTHLY) -> Customer:
        customer = Customer(
            customer_id=f"cus_{uuid.uuid4().hex[:8]}",
            email=email,
            name=name,
            stripe_customer_id=f"cus_stripe_{uuid.uuid4().hex[:8]}",
            plan_tier=plan_tier,
            billing_interval=billing_interval,
        )
        with self._lock:
            self._customers[customer.customer_id] = customer
        return customer

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        with self._lock:
            return self._customers.get(customer_id)

    def update_customer(self, customer_id: str, **kwargs) -> Customer:
        with self._lock:
            customer = self._customers.get(customer_id)
            if not customer:
                raise KeyError(f"Customer {customer_id} not found")
            for k, v in kwargs.items():
                if hasattr(customer, k):
                    setattr(customer, k, v)
        return customer

    # ── Subscription management ──────────────────────────────
    def create_subscription(self, customer_id: str,
                             plan_tier: PlanTier = None,
                             billing_interval: BillingInterval = None,
                             trial_days: int = 0) -> Subscription:
        with self._lock:
            customer = self._customers.get(customer_id)
            if not customer:
                raise KeyError(f"Customer {customer_id} not found")
        tier = plan_tier or customer.plan_tier
        interval = billing_interval or customer.billing_interval
        plan = PLAN_CATALOG[tier]
        now = time.time()
        trial_end = now + trial_days * 86400 if trial_days > 0 else None
        status = SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE
        sub = Subscription(
            subscription_id=f"sub_{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            plan=plan,
            status=status,
            current_period_start=now,
            current_period_end=now + (365 if interval == BillingInterval.ANNUAL else 30) * 86400,
            trial_end=trial_end,
            stripe_subscription_id=f"sub_stripe_{uuid.uuid4().hex[:8]}",
        )
        with self._lock:
            self._subscriptions[sub.subscription_id] = sub
        return sub

    def upgrade_subscription(self, subscription_id: str,
                              new_tier: PlanTier) -> Subscription:
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            if not sub:
                raise KeyError(f"Subscription {subscription_id} not found")
            sub.plan = PLAN_CATALOG[new_tier]
        return sub

    def cancel_subscription(self, subscription_id: str,
                             at_period_end: bool = True) -> Subscription:
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            if not sub:
                raise KeyError(f"Subscription {subscription_id} not found")
            if at_period_end:
                sub.cancel_at_period_end = True
            else:
                sub.status = SubscriptionStatus.CANCELED
        return sub

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        with self._lock:
            return self._subscriptions.get(subscription_id)

    def list_subscriptions(self, customer_id: str) -> List[Subscription]:
        with self._lock:
            return [s for s in self._subscriptions.values()
                    if s.customer_id == customer_id]

    # ── Usage metering ───────────────────────────────────────
    def record_usage(self, customer_id: str, metric: UsageMetric,
                     quantity: int = 1) -> UsageRecord:
        return self._usage_meter.record(customer_id, metric, quantity)

    def get_usage(self, customer_id: str, metric: UsageMetric) -> int:
        return self._usage_meter.get_usage(customer_id, metric)

    def check_usage_limit(self, customer_id: str, metric: UsageMetric) -> bool:
        customer = self.get_customer(customer_id)
        if not customer:
            return False
        plan = PLAN_CATALOG[customer.plan_tier]
        return self._usage_meter.check_limit(customer_id, metric, plan)

    # ── Invoicing ────────────────────────────────────────────
    def generate_invoice(self, customer_id: str,
                         subscription_id: str) -> Invoice:
        customer = self.get_customer(customer_id)
        sub = self.get_subscription(subscription_id)
        if not customer or not sub:
            raise KeyError("Customer or subscription not found")
        return self._invoice_gen.create_invoice(customer, sub)

    def pay_invoice(self, invoice_id: str) -> Invoice:
        return self._invoice_gen.mark_paid(invoice_id)

    def list_invoices(self, customer_id: str) -> List[Invoice]:
        return self._invoice_gen.list_invoices(customer_id)

    # ── Portal sessions ──────────────────────────────────────
    def create_portal_session(self, customer_id: str,
                               return_url: str = "") -> BillingPortalSession:
        session = BillingPortalSession(
            session_id=f"bps_{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            url=f"{self._base_url}/session/{uuid.uuid4().hex[:16]}",
            return_url=return_url or self._base_url,
            expires_at=time.time() + 3600,
            created_at=time.time(),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_portal_session(self, session_id: str) -> Optional[BillingPortalSession]:
        with self._lock:
            return self._sessions.get(session_id)

    # ── Plan catalog ─────────────────────────────────────────
    def get_plan(self, tier: PlanTier) -> Plan:
        return PLAN_CATALOG[tier]

    def list_plans(self) -> List[Plan]:
        return list(PLAN_CATALOG.values())

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for s in self._subscriptions.values() if s.is_active)
            mrr = sum(
                s.plan.monthly_price_cents
                for s in self._subscriptions.values()
                if s.is_active
            )
        return {
            "total_customers": len(self._customers),
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": active,
            "mrr_cents": mrr,
        }
