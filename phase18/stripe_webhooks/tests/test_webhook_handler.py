"""
Phase 18A — Stripe Webhook Handler Tests
"""
import hashlib
import hmac
import json
import time
import uuid
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from phase18.stripe_webhooks.webhook_handler import (
    BillingEvent,
    BillingEventBus,
    BillingEventStore,
    BillingEventType,
    StripeWebhookHandler,
    SubscriptionState,
    SubscriptionStateManager,
    SubscriptionStatus,
    WebhookVerificationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "whsec_test_secret_key_12345"


def _make_signature(secret: str, body: bytes, timestamp: int = None) -> str:
    ts = timestamp or int(time.time())
    signed = f"{ts}.{body.decode('utf-8')}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _make_payload(event_type: str, customer_id: str = "cus_test123", extra: dict = None) -> bytes:
    obj = {
        "id": f"sub_{uuid.uuid4().hex[:8]}",
        "customer": customer_id,
        "status": "active",
        "current_period_start": int(time.time()),
        "current_period_end": int(time.time()) + 2592000,
        "cancel_at_period_end": False,
        "plan": {
            "id": "plan_pro",
            "nickname": "Pro",
            "amount": 9900,
            "currency": "usd",
        },
    }
    if extra:
        obj.update(extra)
    payload = {
        "id": f"evt_{uuid.uuid4().hex[:8]}",
        "type": event_type,
        "data": {"object": obj},
    }
    return json.dumps(payload).encode()


@pytest.fixture
def bus():
    return BillingEventBus()


@pytest.fixture
def store():
    return BillingEventStore()


@pytest.fixture
def state_manager():
    return SubscriptionStateManager()


@pytest.fixture
def handler(bus, store, state_manager):
    return StripeWebhookHandler(
        webhook_secret=WEBHOOK_SECRET,
        event_bus=bus,
        event_store=store,
        state_manager=state_manager,
    )


# ---------------------------------------------------------------------------
# BillingEventBus tests
# ---------------------------------------------------------------------------

class TestBillingEventBus:
    def test_subscribe_and_publish(self, bus):
        received = []
        bus.subscribe(BillingEventType.INVOICE_PAID, lambda e: received.append(e))
        event = BillingEvent(
            id=str(uuid.uuid4()),
            event_type=BillingEventType.INVOICE_PAID,
            stripe_event_id="evt_1",
            customer_id="cus_1",
            payload={},
        )
        count = bus.publish(event)
        assert count == 1
        assert len(received) == 1
        assert received[0].event_type == BillingEventType.INVOICE_PAID

    def test_wildcard_handler(self, bus):
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        for et in [BillingEventType.INVOICE_PAID, BillingEventType.SUBSCRIPTION_CREATED]:
            event = BillingEvent(
                id=str(uuid.uuid4()),
                event_type=et,
                stripe_event_id=f"evt_{et.value}",
                customer_id="cus_1",
                payload={},
            )
            bus.publish(event)
        assert len(received) == 2

    def test_multiple_handlers_same_event(self, bus):
        counts = [0, 0]
        bus.subscribe(BillingEventType.PAYMENT_SUCCEEDED, lambda e: counts.__setitem__(0, counts[0] + 1))
        bus.subscribe(BillingEventType.PAYMENT_SUCCEEDED, lambda e: counts.__setitem__(1, counts[1] + 1))
        event = BillingEvent(
            id=str(uuid.uuid4()),
            event_type=BillingEventType.PAYMENT_SUCCEEDED,
            stripe_event_id="evt_pay",
            customer_id="cus_1",
            payload={},
        )
        bus.publish(event)
        assert counts == [1, 1]

    def test_handler_exception_does_not_propagate(self, bus):
        def bad_handler(e):
            raise RuntimeError("handler error")
        bus.subscribe(BillingEventType.INVOICE_FAILED, bad_handler)
        event = BillingEvent(
            id=str(uuid.uuid4()),
            event_type=BillingEventType.INVOICE_FAILED,
            stripe_event_id="evt_fail",
            customer_id="cus_1",
            payload={},
        )
        # Should not raise
        count = bus.publish(event)
        assert count == 0  # handler raised, so 0 successful

    def test_no_handlers_returns_zero(self, bus):
        event = BillingEvent(
            id=str(uuid.uuid4()),
            event_type=BillingEventType.CUSTOMER_CREATED,
            stripe_event_id="evt_cust",
            customer_id="cus_1",
            payload={},
        )
        assert bus.publish(event) == 0

    def test_handler_count(self, bus):
        bus.subscribe(BillingEventType.INVOICE_PAID, lambda e: None)
        bus.subscribe(BillingEventType.INVOICE_PAID, lambda e: None)
        bus.subscribe_all(lambda e: None)
        assert bus.handler_count(BillingEventType.INVOICE_PAID) == 2
        assert bus.handler_count() == 3

    def test_clear(self, bus):
        bus.subscribe(BillingEventType.INVOICE_PAID, lambda e: None)
        bus.subscribe_all(lambda e: None)
        bus.clear()
        assert bus.handler_count() == 0


# ---------------------------------------------------------------------------
# BillingEventStore tests
# ---------------------------------------------------------------------------

class TestBillingEventStore:
    def _make_event(self, event_type: BillingEventType, customer_id: str = "cus_1") -> BillingEvent:
        return BillingEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            stripe_event_id=f"evt_{uuid.uuid4().hex[:6]}",
            customer_id=customer_id,
            payload={},
        )

    def test_append_and_total(self, store):
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        store.append(self._make_event(BillingEventType.SUBSCRIPTION_CREATED))
        assert store.total == 2

    def test_get_by_customer(self, store):
        store.append(self._make_event(BillingEventType.INVOICE_PAID, "cus_A"))
        store.append(self._make_event(BillingEventType.INVOICE_PAID, "cus_B"))
        store.append(self._make_event(BillingEventType.SUBSCRIPTION_CREATED, "cus_A"))
        result = store.get_by_customer("cus_A")
        assert len(result) == 2
        assert all(e.customer_id == "cus_A" for e in result)

    def test_get_by_type(self, store):
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        store.append(self._make_event(BillingEventType.INVOICE_FAILED))
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        result = store.get_by_type(BillingEventType.INVOICE_PAID)
        assert len(result) == 2

    def test_get_failed(self, store):
        e1 = self._make_event(BillingEventType.INVOICE_PAID)
        e2 = self._make_event(BillingEventType.INVOICE_FAILED)
        e2.error = "Card declined"
        store.append(e1)
        store.append(e2)
        failed = store.get_failed()
        assert len(failed) == 1
        assert failed[0].error == "Card declined"

    def test_replay(self, store, bus):
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        for i in range(5):
            store.append(self._make_event(BillingEventType.INVOICE_PAID))
        replayed = store.replay(bus)
        assert replayed == 5
        assert len(received) == 5

    def test_replay_filtered_by_type(self, store, bus):
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        store.append(self._make_event(BillingEventType.INVOICE_FAILED))
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        replayed = store.replay(bus, BillingEventType.INVOICE_PAID)
        assert replayed == 2
        assert len(received) == 2

    def test_max_events_cap(self):
        small_store = BillingEventStore(max_events=3)
        for i in range(5):
            small_store.append(self._make_event(BillingEventType.INVOICE_PAID))
        assert small_store.total == 3

    def test_stats(self, store):
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        store.append(self._make_event(BillingEventType.INVOICE_PAID))
        store.append(self._make_event(BillingEventType.SUBSCRIPTION_CREATED))
        stats = store.stats()
        assert stats[BillingEventType.INVOICE_PAID.value] == 2
        assert stats[BillingEventType.SUBSCRIPTION_CREATED.value] == 1


# ---------------------------------------------------------------------------
# SubscriptionStateManager tests
# ---------------------------------------------------------------------------

class TestSubscriptionStateManager:
    def _make_state(self, customer_id: str = "cus_1", status: SubscriptionStatus = SubscriptionStatus.ACTIVE) -> SubscriptionState:
        return SubscriptionState(
            customer_id=customer_id,
            subscription_id=f"sub_{uuid.uuid4().hex[:6]}",
            status=status,
            plan_id="plan_pro",
            plan_name="Pro",
            amount=9900,
            currency="usd",
            current_period_start=time.time(),
            current_period_end=time.time() + 2592000,
        )

    def test_upsert_and_get(self, state_manager):
        state = self._make_state("cus_1")
        state_manager.upsert(state)
        result = state_manager.get("cus_1")
        assert result is not None
        assert result.customer_id == "cus_1"
        assert result.is_active

    def test_upsert_overwrites(self, state_manager):
        state1 = self._make_state("cus_1", SubscriptionStatus.ACTIVE)
        state2 = self._make_state("cus_1", SubscriptionStatus.PAST_DUE)
        state_manager.upsert(state1)
        state_manager.upsert(state2)
        result = state_manager.get("cus_1")
        assert result.status == SubscriptionStatus.PAST_DUE

    def test_delete(self, state_manager):
        state_manager.upsert(self._make_state("cus_1"))
        assert state_manager.delete("cus_1") is True
        assert state_manager.get("cus_1") is None
        assert state_manager.delete("cus_1") is False

    def test_all_active(self, state_manager):
        state_manager.upsert(self._make_state("cus_1", SubscriptionStatus.ACTIVE))
        state_manager.upsert(self._make_state("cus_2", SubscriptionStatus.PAST_DUE))
        state_manager.upsert(self._make_state("cus_3", SubscriptionStatus.TRIALING))
        active = state_manager.all_active()
        assert len(active) == 2
        assert all(s.is_active for s in active)

    def test_past_due(self, state_manager):
        state_manager.upsert(self._make_state("cus_1", SubscriptionStatus.ACTIVE))
        state_manager.upsert(self._make_state("cus_2", SubscriptionStatus.PAST_DUE))
        past_due = state_manager.past_due()
        assert len(past_due) == 1
        assert past_due[0].customer_id == "cus_2"

    def test_mrr(self, state_manager):
        state_manager.upsert(self._make_state("cus_1", SubscriptionStatus.ACTIVE))  # 9900
        state_manager.upsert(self._make_state("cus_2", SubscriptionStatus.ACTIVE))  # 9900
        state_manager.upsert(self._make_state("cus_3", SubscriptionStatus.PAST_DUE))  # not counted
        assert state_manager.mrr() == 19800

    def test_total(self, state_manager):
        state_manager.upsert(self._make_state("cus_1"))
        state_manager.upsert(self._make_state("cus_2"))
        assert state_manager.total == 2

    def test_days_until_renewal(self, state_manager):
        state = self._make_state("cus_1")
        state.current_period_end = time.time() + 86400 * 15  # 15 days
        assert 14 < state.days_until_renewal < 16


# ---------------------------------------------------------------------------
# StripeWebhookHandler tests
# ---------------------------------------------------------------------------

class TestStripeWebhookHandler:
    def test_valid_signature(self, handler):
        body = _make_payload("customer.subscription.created")
        sig = _make_signature(WEBHOOK_SECRET, body)
        result = handler.verify_signature(body, sig)
        assert result.valid is True

    def test_invalid_signature(self, handler):
        body = _make_payload("customer.subscription.created")
        sig = _make_signature("wrong_secret", body)
        result = handler.verify_signature(body, sig)
        assert result.valid is False
        assert "mismatch" in result.error.lower()

    def test_expired_timestamp(self, handler):
        body = _make_payload("customer.subscription.created")
        old_ts = int(time.time()) - 400  # 400s ago > 300s tolerance
        sig = _make_signature(WEBHOOK_SECRET, body, timestamp=old_ts)
        result = handler.verify_signature(body, sig)
        assert result.valid is False
        assert "old" in result.error.lower()

    def test_missing_signature_parts(self, handler):
        body = _make_payload("customer.subscription.created")
        result = handler.verify_signature(body, "invalid_header")
        assert result.valid is False

    def test_process_subscription_created(self, handler, state_manager):
        body = _make_payload("customer.subscription.created", "cus_abc")
        result = handler.process(body, "", skip_verification=True)
        assert result["status"] == "processed"
        assert result["event_type"] == "customer.subscription.created"
        state = state_manager.get("cus_abc")
        assert state is not None
        assert state.is_active

    def test_process_subscription_deleted(self, handler, state_manager):
        # First create
        body_create = _make_payload("customer.subscription.created", "cus_del")
        handler.process(body_create, "", skip_verification=True)
        assert state_manager.get("cus_del") is not None
        # Then delete
        body_delete = _make_payload("customer.subscription.deleted", "cus_del")
        handler.process(body_delete, "", skip_verification=True)
        assert state_manager.get("cus_del") is None

    def test_process_invoice_paid(self, handler, store):
        body = _make_payload("invoice.payment_succeeded", "cus_pay")
        result = handler.process(body, "", skip_verification=True)
        assert result["status"] == "processed"
        events = store.get_by_type(BillingEventType.INVOICE_PAID)
        assert len(events) == 1

    def test_process_invoice_failed(self, handler, bus):
        received = []
        bus.subscribe(BillingEventType.INVOICE_FAILED, lambda e: received.append(e))
        body = _make_payload("invoice.payment_failed", "cus_fail")
        handler.process(body, "", skip_verification=True)
        assert len(received) == 1

    def test_idempotency_duplicate_event(self, handler):
        body = _make_payload("invoice.payment_succeeded", "cus_idem")
        handler.process(body, "", skip_verification=True)
        result2 = handler.process(body, "", skip_verification=True)
        assert result2["status"] == "duplicate"

    def test_unhandled_event_type_ignored(self, handler):
        payload = {"id": "evt_unknown", "type": "some.unknown.event", "data": {"object": {}}}
        body = json.dumps(payload).encode()
        result = handler.process(body, "", skip_verification=True)
        assert result["status"] == "ignored"

    def test_invalid_json_returns_error(self, handler):
        result = handler.process(b"not json", "", skip_verification=True)
        assert result["status"] == "error"

    def test_handlers_called_count(self, handler, bus):
        counts = []
        bus.subscribe(BillingEventType.PAYMENT_SUCCEEDED, lambda e: counts.append(1))
        bus.subscribe(BillingEventType.PAYMENT_SUCCEEDED, lambda e: counts.append(1))
        body = _make_payload("payment_intent.succeeded", "cus_cnt")
        result = handler.process(body, "", skip_verification=True)
        assert result["handlers_called"] == 2

    def test_processed_count_increments(self, handler):
        for i in range(3):
            body = _make_payload("invoice.payment_succeeded", f"cus_{i}")
            handler.process(body, "", skip_verification=True)
        assert handler.processed_count == 3

    def test_checkout_session_completed(self, handler, store):
        body = _make_payload("checkout.session.completed", "cus_checkout")
        result = handler.process(body, "", skip_verification=True)
        assert result["status"] == "processed"

    def test_subscription_updated_changes_state(self, handler, state_manager):
        body_create = _make_payload("customer.subscription.created", "cus_upd")
        handler.process(body_create, "", skip_verification=True)
        # Update with past_due status
        body_update = _make_payload(
            "customer.subscription.updated", "cus_upd",
            extra={"status": "past_due"}
        )
        handler.process(body_update, "", skip_verification=True)
        state = state_manager.get("cus_upd")
        assert state.status == SubscriptionStatus.PAST_DUE

    def test_full_pipeline_with_verification(self):
        """End-to-end: real HMAC signature generation + verification + processing."""
        bus = BillingEventBus()
        store = BillingEventStore()
        state_manager = SubscriptionStateManager()
        h = StripeWebhookHandler(WEBHOOK_SECRET, bus, store, state_manager)

        received = []
        bus.subscribe(BillingEventType.SUBSCRIPTION_CREATED, lambda e: received.append(e))

        body = _make_payload("customer.subscription.created", "cus_e2e")
        sig = _make_signature(WEBHOOK_SECRET, body)
        result = h.process(body, sig, skip_verification=False)
        assert result["status"] == "processed"
        assert len(received) == 1
        assert state_manager.get("cus_e2e") is not None
