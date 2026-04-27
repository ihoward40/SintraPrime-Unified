"""Phase 16B — Stripe Billing Portal tests (107 tests)."""
import time
import pytest
from phase16.stripe_billing.models import (
    BillingInterval, PlanTier, SubscriptionStatus, UsageMetric,
)
from phase16.stripe_billing.billing_portal import (
    BillingPortal, UsageMeter, InvoiceGenerator, PLAN_CATALOG,
)


@pytest.fixture
def portal():
    return BillingPortal()


@pytest.fixture
def customer(portal):
    return portal.create_customer("alice@firm.com", "Alice Smith", PlanTier.PROFESSIONAL)


@pytest.fixture
def subscription(portal, customer):
    return portal.create_subscription(customer.customer_id)


# ─────────────────────────────────────────────────────────────
# Plan catalog tests (12)
# ─────────────────────────────────────────────────────────────
class TestPlanCatalog:
    def test_three_plans_exist(self):
        assert len(PLAN_CATALOG) == 3

    def test_starter_plan_exists(self):
        assert PlanTier.STARTER in PLAN_CATALOG

    def test_professional_plan_exists(self):
        assert PlanTier.PROFESSIONAL in PLAN_CATALOG

    def test_enterprise_plan_exists(self):
        assert PlanTier.ENTERPRISE in PLAN_CATALOG

    def test_starter_monthly_price(self):
        assert PLAN_CATALOG[PlanTier.STARTER].monthly_price_cents == 9900

    def test_professional_monthly_price(self):
        assert PLAN_CATALOG[PlanTier.PROFESSIONAL].monthly_price_cents == 29900

    def test_enterprise_monthly_price(self):
        assert PLAN_CATALOG[PlanTier.ENTERPRISE].monthly_price_cents == 99900

    def test_annual_cheaper_than_12x_monthly(self):
        for plan in PLAN_CATALOG.values():
            assert plan.annual_price_cents < plan.monthly_price_cents * 12

    def test_annual_savings_positive(self):
        for plan in PLAN_CATALOG.values():
            assert plan.annual_savings_cents() > 0

    def test_get_price_monthly(self):
        plan = PLAN_CATALOG[PlanTier.STARTER]
        assert plan.get_price(BillingInterval.MONTHLY) == 9900

    def test_get_price_annual(self):
        plan = PLAN_CATALOG[PlanTier.STARTER]
        assert plan.get_price(BillingInterval.ANNUAL) == 99_000

    def test_enterprise_unlimited_limits(self):
        plan = PLAN_CATALOG[PlanTier.ENTERPRISE]
        assert plan.usage_limits.get("queries") == -1


# ─────────────────────────────────────────────────────────────
# Customer management tests (15)
# ─────────────────────────────────────────────────────────────
class TestCustomerManagement:
    def test_create_customer(self, portal):
        c = portal.create_customer("bob@firm.com", "Bob Jones")
        assert c.customer_id.startswith("cus_")
        assert c.email == "bob@firm.com"

    def test_customer_default_plan(self, portal):
        c = portal.create_customer("x@y.com", "X Y")
        assert c.plan_tier == PlanTier.STARTER

    def test_customer_custom_plan(self, portal):
        c = portal.create_customer("x@y.com", "X Y", PlanTier.ENTERPRISE)
        assert c.plan_tier == PlanTier.ENTERPRISE

    def test_customer_has_stripe_id(self, portal):
        c = portal.create_customer("x@y.com", "X Y")
        assert c.stripe_customer_id.startswith("cus_stripe_")

    def test_get_customer(self, portal, customer):
        retrieved = portal.get_customer(customer.customer_id)
        assert retrieved.email == customer.email

    def test_get_nonexistent_customer(self, portal):
        assert portal.get_customer("nonexistent") is None

    def test_update_customer_name(self, portal, customer):
        portal.update_customer(customer.customer_id, name="Alice Updated")
        assert portal.get_customer(customer.customer_id).name == "Alice Updated"

    def test_update_customer_plan(self, portal, customer):
        portal.update_customer(customer.customer_id, plan_tier=PlanTier.ENTERPRISE)
        assert portal.get_customer(customer.customer_id).plan_tier == PlanTier.ENTERPRISE

    def test_update_nonexistent_raises(self, portal):
        with pytest.raises(KeyError):
            portal.update_customer("nonexistent", name="X")

    def test_multiple_customers(self, portal):
        for i in range(5):
            portal.create_customer(f"user{i}@firm.com", f"User {i}")
        stats = portal.get_stats()
        assert stats["total_customers"] >= 5

    def test_customer_billing_interval_default(self, portal):
        c = portal.create_customer("x@y.com", "X Y")
        assert c.billing_interval == BillingInterval.MONTHLY

    def test_customer_annual_billing(self, portal):
        c = portal.create_customer("x@y.com", "X Y", billing_interval=BillingInterval.ANNUAL)
        assert c.billing_interval == BillingInterval.ANNUAL

    def test_customer_metadata_default_empty(self, portal):
        c = portal.create_customer("x@y.com", "X Y")
        assert c.metadata == {}

    def test_customer_unique_ids(self, portal):
        ids = {portal.create_customer(f"u{i}@x.com", f"U{i}").customer_id for i in range(10)}
        assert len(ids) == 10

    def test_customer_name_stored(self, portal):
        c = portal.create_customer("x@y.com", "Jane Doe")
        assert portal.get_customer(c.customer_id).name == "Jane Doe"


# ─────────────────────────────────────────────────────────────
# Subscription management tests (20)
# ─────────────────────────────────────────────────────────────
class TestSubscriptionManagement:
    def test_create_subscription(self, portal, customer, subscription):
        assert subscription.subscription_id.startswith("sub_")
        assert subscription.customer_id == customer.customer_id

    def test_subscription_active_by_default(self, portal, customer, subscription):
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_subscription_trialing_with_trial(self, portal, customer):
        sub = portal.create_subscription(customer.customer_id, trial_days=14)
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.trial_end is not None

    def test_subscription_plan_matches_customer(self, portal, customer, subscription):
        assert subscription.plan.tier == customer.plan_tier

    def test_subscription_has_period(self, portal, customer, subscription):
        assert subscription.current_period_end > subscription.current_period_start

    def test_subscription_is_active_property(self, portal, customer, subscription):
        assert subscription.is_active is True

    def test_cancel_at_period_end(self, portal, customer, subscription):
        portal.cancel_subscription(subscription.subscription_id, at_period_end=True)
        sub = portal.get_subscription(subscription.subscription_id)
        assert sub.cancel_at_period_end is True
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_cancel_immediately(self, portal, customer, subscription):
        portal.cancel_subscription(subscription.subscription_id, at_period_end=False)
        sub = portal.get_subscription(subscription.subscription_id)
        assert sub.status == SubscriptionStatus.CANCELED

    def test_upgrade_subscription(self, portal, customer, subscription):
        portal.upgrade_subscription(subscription.subscription_id, PlanTier.ENTERPRISE)
        sub = portal.get_subscription(subscription.subscription_id)
        assert sub.plan.tier == PlanTier.ENTERPRISE

    def test_get_subscription(self, portal, customer, subscription):
        retrieved = portal.get_subscription(subscription.subscription_id)
        assert retrieved.subscription_id == subscription.subscription_id

    def test_get_nonexistent_subscription(self, portal):
        assert portal.get_subscription("nonexistent") is None

    def test_list_subscriptions(self, portal, customer):
        portal.create_subscription(customer.customer_id)
        portal.create_subscription(customer.customer_id)
        subs = portal.list_subscriptions(customer.customer_id)
        assert len(subs) >= 2

    def test_cancel_nonexistent_raises(self, portal):
        with pytest.raises(KeyError):
            portal.cancel_subscription("nonexistent")

    def test_upgrade_nonexistent_raises(self, portal):
        with pytest.raises(KeyError):
            portal.upgrade_subscription("nonexistent", PlanTier.ENTERPRISE)

    def test_subscription_stripe_id(self, portal, customer, subscription):
        assert subscription.stripe_subscription_id.startswith("sub_stripe_")

    def test_subscription_annual_period(self, portal):
        c = portal.create_customer("x@y.com", "X", billing_interval=BillingInterval.ANNUAL)
        sub = portal.create_subscription(c.customer_id)
        period_days = (sub.current_period_end - sub.current_period_start) / 86400
        assert period_days >= 364

    def test_subscription_monthly_period(self, portal, customer, subscription):
        period_days = (subscription.current_period_end - subscription.current_period_start) / 86400
        assert period_days >= 29

    def test_multiple_subscriptions_same_customer(self, portal, customer):
        s1 = portal.create_subscription(customer.customer_id)
        s2 = portal.create_subscription(customer.customer_id)
        assert s1.subscription_id != s2.subscription_id

    def test_canceled_not_active(self, portal, customer, subscription):
        portal.cancel_subscription(subscription.subscription_id, at_period_end=False)
        sub = portal.get_subscription(subscription.subscription_id)
        assert sub.is_active is False

    def test_subscription_metadata_default_empty(self, portal, customer, subscription):
        assert subscription.metadata == {}


# ─────────────────────────────────────────────────────────────
# Usage metering tests (20)
# ─────────────────────────────────────────────────────────────
class TestUsageMetering:
    def test_record_usage(self, portal, customer):
        record = portal.record_usage(customer.customer_id, UsageMetric.QUERIES)
        assert record.quantity == 1

    def test_record_usage_custom_quantity(self, portal, customer):
        portal.record_usage(customer.customer_id, UsageMetric.QUERIES, quantity=10)
        assert portal.get_usage(customer.customer_id, UsageMetric.QUERIES) == 10

    def test_usage_accumulates(self, portal, customer):
        for _ in range(5):
            portal.record_usage(customer.customer_id, UsageMetric.QUERIES)
        assert portal.get_usage(customer.customer_id, UsageMetric.QUERIES) == 5

    def test_usage_per_metric(self, portal, customer):
        portal.record_usage(customer.customer_id, UsageMetric.QUERIES, 3)
        portal.record_usage(customer.customer_id, UsageMetric.DOCUMENTS, 2)
        assert portal.get_usage(customer.customer_id, UsageMetric.QUERIES) == 3
        assert portal.get_usage(customer.customer_id, UsageMetric.DOCUMENTS) == 2

    def test_check_usage_limit_within(self, portal, customer):
        portal.record_usage(customer.customer_id, UsageMetric.QUERIES, 10)
        assert portal.check_usage_limit(customer.customer_id, UsageMetric.QUERIES) is True

    def test_check_usage_limit_exceeded(self, portal, customer):
        portal.record_usage(customer.customer_id, UsageMetric.QUERIES, 600)
        assert portal.check_usage_limit(customer.customer_id, UsageMetric.QUERIES) is False

    def test_enterprise_unlimited(self, portal):
        c = portal.create_customer("x@y.com", "X", PlanTier.ENTERPRISE)
        portal.record_usage(c.customer_id, UsageMetric.QUERIES, 999999)
        assert portal.check_usage_limit(c.customer_id, UsageMetric.QUERIES) is True

    def test_usage_meter_reset(self):
        meter = UsageMeter()
        meter.record("c1", UsageMetric.QUERIES, 10)
        meter.reset("c1")
        assert meter.get_usage("c1", UsageMetric.QUERIES) == 0

    def test_usage_meter_get_all(self):
        meter = UsageMeter()
        meter.record("c1", UsageMetric.QUERIES, 5)
        meter.record("c1", UsageMetric.DOCUMENTS, 2)
        all_usage = meter.get_all_usage("c1")
        assert all_usage["queries"] == 5
        assert all_usage["documents"] == 2

    def test_usage_meter_since_filter(self):
        meter = UsageMeter()
        meter.record("c1", UsageMetric.QUERIES, 5)
        future = time.time() + 10
        assert meter.get_usage("c1", UsageMetric.QUERIES, since=future) == 0

    def test_usage_record_has_timestamp(self, portal, customer):
        record = portal.record_usage(customer.customer_id, UsageMetric.API_CALLS)
        assert record.timestamp > 0

    def test_usage_record_id_unique(self, portal, customer):
        r1 = portal.record_usage(customer.customer_id, UsageMetric.QUERIES)
        r2 = portal.record_usage(customer.customer_id, UsageMetric.QUERIES)
        assert r1.record_id != r2.record_id

    def test_check_limit_nonexistent_customer(self, portal):
        assert portal.check_usage_limit("nonexistent", UsageMetric.QUERIES) is False

    def test_usage_zero_initially(self, portal, customer):
        assert portal.get_usage(customer.customer_id, UsageMetric.STORAGE_GB) == 0

    def test_usage_thread_safety(self):
        import threading
        meter = UsageMeter()
        errors = []
        def worker():
            try:
                meter.record("c1", UsageMetric.QUERIES)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert meter.get_usage("c1", UsageMetric.QUERIES) == 50

    def test_usage_metric_enum_values(self):
        assert UsageMetric.QUERIES.value == "queries"
        assert UsageMetric.DOCUMENTS.value == "documents"

    def test_record_returns_usage_record(self, portal, customer):
        from phase16.stripe_billing.models import UsageRecord
        record = portal.record_usage(customer.customer_id, UsageMetric.AGENTS)
        assert isinstance(record, UsageRecord)

    def test_starter_query_limit(self, portal):
        c = portal.create_customer("x@y.com", "X", PlanTier.STARTER)
        portal.record_usage(c.customer_id, UsageMetric.QUERIES, 49)
        assert portal.check_usage_limit(c.customer_id, UsageMetric.QUERIES) is True
        portal.record_usage(c.customer_id, UsageMetric.QUERIES, 2)
        assert portal.check_usage_limit(c.customer_id, UsageMetric.QUERIES) is False

    def test_check_limit_plan_catalog(self):
        meter = UsageMeter()
        plan = PLAN_CATALOG[PlanTier.STARTER]
        meter.record("c1", UsageMetric.QUERIES, 40)
        assert meter.check_limit("c1", UsageMetric.QUERIES, plan) is True

    def test_check_limit_exceeded_plan_catalog(self):
        meter = UsageMeter()
        plan = PLAN_CATALOG[PlanTier.STARTER]
        meter.record("c1", UsageMetric.QUERIES, 60)
        assert meter.check_limit("c1", UsageMetric.QUERIES, plan) is False


# ─────────────────────────────────────────────────────────────
# Invoice generation tests (20)
# ─────────────────────────────────────────────────────────────
class TestInvoiceGeneration:
    def test_generate_invoice(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.invoice_id.startswith("inv_")

    def test_invoice_amount_matches_plan(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.amount_due_cents == subscription.plan.monthly_price_cents

    def test_invoice_status_open(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.status == "open"
        assert not inv.is_paid

    def test_pay_invoice(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        paid = portal.pay_invoice(inv.invoice_id)
        assert paid.is_paid
        assert paid.amount_paid_cents == paid.amount_due_cents

    def test_void_invoice(self):
        gen = InvoiceGenerator()
        from phase16.stripe_billing.models import Customer, Subscription, Plan
        customer = Customer("c1", "x@y.com", "X", plan_tier=PlanTier.STARTER)
        plan = PLAN_CATALOG[PlanTier.STARTER]
        sub = Subscription("s1", "c1", plan, SubscriptionStatus.ACTIVE)
        inv = gen.create_invoice(customer, sub)
        voided = gen.void_invoice(inv.invoice_id)
        assert voided.status == "void"

    def test_list_invoices(self, portal, customer, subscription):
        portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        invoices = portal.list_invoices(customer.customer_id)
        assert len(invoices) >= 2

    def test_invoice_has_line_items(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert len(inv.line_items) >= 1

    def test_invoice_created_at(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.created_at > 0

    def test_pay_nonexistent_invoice_raises(self):
        gen = InvoiceGenerator()
        with pytest.raises(KeyError):
            gen.mark_paid("nonexistent")

    def test_void_nonexistent_invoice_raises(self):
        gen = InvoiceGenerator()
        with pytest.raises(KeyError):
            gen.void_invoice("nonexistent")

    def test_invoice_customer_id(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.customer_id == customer.customer_id

    def test_invoice_subscription_id(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.subscription_id == subscription.subscription_id

    def test_invoice_with_overage(self):
        gen = InvoiceGenerator()
        from phase16.stripe_billing.models import Customer, Subscription, UsageRecord
        customer = Customer("c1", "x@y.com", "X", plan_tier=PlanTier.STARTER,
                            billing_interval=BillingInterval.MONTHLY)
        plan = PLAN_CATALOG[PlanTier.STARTER]
        sub = Subscription("s1", "c1", plan, SubscriptionStatus.ACTIVE)
        usage = [UsageRecord(f"ur{i}", "c1", UsageMetric.QUERIES, 1, time.time()) for i in range(60)]
        inv = gen.create_invoice(customer, sub, usage_records=usage)
        assert len(inv.line_items) == 2  # base + overage

    def test_invoice_paid_at_set(self, portal, customer, subscription):
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        paid = portal.pay_invoice(inv.invoice_id)
        assert paid.paid_at is not None

    def test_get_invoice(self):
        gen = InvoiceGenerator()
        from phase16.stripe_billing.models import Customer, Subscription
        customer = Customer("c1", "x@y.com", "X", plan_tier=PlanTier.STARTER)
        plan = PLAN_CATALOG[PlanTier.STARTER]
        sub = Subscription("s1", "c1", plan, SubscriptionStatus.ACTIVE)
        inv = gen.create_invoice(customer, sub)
        assert gen.get_invoice(inv.invoice_id) is not None

    def test_get_nonexistent_invoice(self):
        gen = InvoiceGenerator()
        assert gen.get_invoice("nonexistent") is None

    def test_invoice_unique_ids(self, portal, customer, subscription):
        ids = {portal.generate_invoice(customer.customer_id, subscription.subscription_id).invoice_id
               for _ in range(5)}
        assert len(ids) == 5

    def test_generate_invoice_nonexistent_customer_raises(self, portal, subscription):
        with pytest.raises(KeyError):
            portal.generate_invoice("nonexistent", subscription.subscription_id)

    def test_generate_invoice_nonexistent_subscription_raises(self, portal, customer):
        with pytest.raises(KeyError):
            portal.generate_invoice(customer.customer_id, "nonexistent")

    def test_enterprise_invoice_amount(self, portal):
        c = portal.create_customer("x@y.com", "X", PlanTier.ENTERPRISE)
        sub = portal.create_subscription(c.customer_id)
        inv = portal.generate_invoice(c.customer_id, sub.subscription_id)
        assert inv.amount_due_cents == 99900


# ─────────────────────────────────────────────────────────────
# Portal session tests (10)
# ─────────────────────────────────────────────────────────────
class TestPortalSessions:
    def test_create_session(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        assert session.session_id.startswith("bps_")

    def test_session_has_url(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        assert "sintra.prime/billing" in session.url

    def test_session_expires_in_one_hour(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        assert session.expires_at > time.time()
        assert session.expires_at <= time.time() + 3601

    def test_session_return_url(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id, return_url="https://myapp.com/billing")
        assert session.return_url == "https://myapp.com/billing"

    def test_get_session(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        retrieved = portal.get_portal_session(session.session_id)
        assert retrieved.customer_id == customer.customer_id

    def test_get_nonexistent_session(self, portal):
        assert portal.get_portal_session("nonexistent") is None

    def test_session_unique_ids(self, portal, customer):
        ids = {portal.create_portal_session(customer.customer_id).session_id for _ in range(5)}
        assert len(ids) == 5

    def test_session_created_at(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        assert session.created_at > 0

    def test_session_customer_id(self, portal, customer):
        session = portal.create_portal_session(customer.customer_id)
        assert session.customer_id == customer.customer_id

    def test_session_unique_url(self, portal, customer):
        s1 = portal.create_portal_session(customer.customer_id)
        s2 = portal.create_portal_session(customer.customer_id)
        assert s1.url != s2.url


# ─────────────────────────────────────────────────────────────
# Stats and integration tests (10)
# ─────────────────────────────────────────────────────────────
class TestStatsAndIntegration:
    def test_stats_initial(self, portal):
        stats = portal.get_stats()
        assert stats["total_customers"] == 0
        assert stats["mrr_cents"] == 0

    def test_stats_after_customer(self, portal, customer, subscription):
        stats = portal.get_stats()
        assert stats["total_customers"] >= 1
        assert stats["active_subscriptions"] >= 1

    def test_mrr_calculation(self, portal):
        c1 = portal.create_customer("a@b.com", "A", PlanTier.STARTER)
        c2 = portal.create_customer("b@b.com", "B", PlanTier.PROFESSIONAL)
        portal.create_subscription(c1.customer_id)
        portal.create_subscription(c2.customer_id)
        stats = portal.get_stats()
        assert stats["mrr_cents"] >= 9900 + 29900

    def test_list_plans(self, portal):
        plans = portal.list_plans()
        assert len(plans) == 3

    def test_get_plan(self, portal):
        plan = portal.get_plan(PlanTier.PROFESSIONAL)
        assert plan.tier == PlanTier.PROFESSIONAL

    def test_full_lifecycle(self, portal):
        c = portal.create_customer("full@test.com", "Full Test", PlanTier.PROFESSIONAL)
        sub = portal.create_subscription(c.customer_id)
        portal.record_usage(c.customer_id, UsageMetric.QUERIES, 100)
        inv = portal.generate_invoice(c.customer_id, sub.subscription_id)
        paid = portal.pay_invoice(inv.invoice_id)
        session = portal.create_portal_session(c.customer_id)
        assert paid.is_paid
        assert session.url is not None

    def test_upgrade_then_invoice(self, portal, customer, subscription):
        portal.upgrade_subscription(subscription.subscription_id, PlanTier.ENTERPRISE)
        inv = portal.generate_invoice(customer.customer_id, subscription.subscription_id)
        assert inv.amount_due_cents == 99900

    def test_cancel_then_not_in_mrr(self, portal, customer, subscription):
        portal.cancel_subscription(subscription.subscription_id, at_period_end=False)
        stats = portal.get_stats()
        # Canceled subscription should not count in MRR
        assert stats["mrr_cents"] == 0

    def test_concurrent_customer_creation(self, portal):
        import threading
        errors = []
        def worker(i):
            try:
                portal.create_customer(f"u{i}@test.com", f"User {i}")
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert portal.get_stats()["total_customers"] >= 20

    def test_annual_invoice_amount(self, portal):
        c = portal.create_customer("x@y.com", "X", PlanTier.STARTER, BillingInterval.ANNUAL)
        sub = portal.create_subscription(c.customer_id)
        inv = portal.generate_invoice(c.customer_id, sub.subscription_id)
        assert inv.amount_due_cents == 99_000
