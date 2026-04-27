"""
Phase 18A — Stripe Webhook Handler + Billing Events
====================================================
Handles all Stripe webhook events relevant to SintraPrime's billing lifecycle:
  - customer.subscription.created / updated / deleted
  - invoice.payment_succeeded / failed
  - payment_intent.succeeded / payment_failed
  - customer.created / deleted
  - checkout.session.completed

Provides:
  - StripeWebhookHandler: signature verification + event routing
  - BillingEventBus: in-process pub/sub for billing events
  - BillingEventStore: append-only event log with replay capability
  - SubscriptionStateManager: tracks current subscription state per customer
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------

class BillingEventType(str, Enum):
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    INVOICE_PAID = "invoice.payment_succeeded"
    INVOICE_FAILED = "invoice.payment_failed"
    PAYMENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_FAILED = "payment_intent.payment_failed"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_DELETED = "customer.deleted"
    CHECKOUT_COMPLETED = "checkout.session.completed"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    UNPAID = "unpaid"
    PAUSED = "paused"


@dataclass
class BillingEvent:
    id: str
    event_type: BillingEventType
    stripe_event_id: str
    customer_id: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "stripe_event_id": self.stripe_event_id,
            "customer_id": self.customer_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "processed": self.processed,
            "error": self.error,
        }


@dataclass
class SubscriptionState:
    customer_id: str
    subscription_id: str
    status: SubscriptionStatus
    plan_id: str
    plan_name: str
    amount: int  # in cents
    currency: str
    current_period_start: float
    current_period_end: float
    cancel_at_period_end: bool = False
    trial_end: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    @property
    def days_until_renewal(self) -> float:
        return max(0.0, (self.current_period_end - time.time()) / 86400)


@dataclass
class WebhookVerificationResult:
    valid: bool
    event_type: Optional[str] = None
    event_id: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Billing Event Bus
# ---------------------------------------------------------------------------

class BillingEventBus:
    """Thread-safe in-process pub/sub for billing events."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[BillingEvent], None]]] = {}
        self._wildcard_handlers: List[Callable[[BillingEvent], None]] = []
        self._lock = threading.Lock()

    def subscribe(
        self,
        event_type: BillingEventType,
        handler: Callable[[BillingEvent], None],
    ) -> None:
        with self._lock:
            key = event_type.value
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(handler)

    def subscribe_all(self, handler: Callable[[BillingEvent], None]) -> None:
        with self._lock:
            self._wildcard_handlers.append(handler)

    def publish(self, event: BillingEvent) -> int:
        """Publish an event and return the number of handlers called."""
        with self._lock:
            specific = list(self._handlers.get(event.event_type.value, []))
            wildcards = list(self._wildcard_handlers)

        called = 0
        for handler in specific + wildcards:
            try:
                handler(event)
                called += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("BillingEventBus handler error: %s", exc)
        return called

    def handler_count(self, event_type: Optional[BillingEventType] = None) -> int:
        with self._lock:
            if event_type is None:
                return sum(len(v) for v in self._handlers.values()) + len(
                    self._wildcard_handlers
                )
            return len(self._handlers.get(event_type.value, []))

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._wildcard_handlers.clear()


# ---------------------------------------------------------------------------
# Billing Event Store
# ---------------------------------------------------------------------------

class BillingEventStore:
    """Append-only in-memory event log with replay capability."""

    def __init__(self, max_events: int = 10_000) -> None:
        self._events: List[BillingEvent] = []
        self._lock = threading.Lock()
        self._max_events = max_events

    def append(self, event: BillingEvent) -> None:
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events :]

    def get_by_customer(self, customer_id: str) -> List[BillingEvent]:
        with self._lock:
            return [e for e in self._events if e.customer_id == customer_id]

    def get_by_type(self, event_type: BillingEventType) -> List[BillingEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def get_failed(self) -> List[BillingEvent]:
        with self._lock:
            return [e for e in self._events if e.error is not None]

    def replay(
        self,
        bus: BillingEventBus,
        event_type: Optional[BillingEventType] = None,
    ) -> int:
        with self._lock:
            events = (
                [e for e in self._events if e.event_type == event_type]
                if event_type
                else list(self._events)
            )
        replayed = 0
        for event in events:
            bus.publish(event)
            replayed += 1
        return replayed

    @property
    def total(self) -> int:
        with self._lock:
            return len(self._events)

    def stats(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for e in self._events:
                counts[e.event_type.value] = counts.get(e.event_type.value, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Subscription State Manager
# ---------------------------------------------------------------------------

class SubscriptionStateManager:
    """Tracks current subscription state per customer."""

    def __init__(self) -> None:
        self._states: Dict[str, SubscriptionState] = {}
        self._lock = threading.Lock()

    def upsert(self, state: SubscriptionState) -> None:
        with self._lock:
            self._states[state.customer_id] = state

    def get(self, customer_id: str) -> Optional[SubscriptionState]:
        with self._lock:
            return self._states.get(customer_id)

    def delete(self, customer_id: str) -> bool:
        with self._lock:
            if customer_id in self._states:
                del self._states[customer_id]
                return True
            return False

    def all_active(self) -> List[SubscriptionState]:
        with self._lock:
            return [s for s in self._states.values() if s.is_active]

    def past_due(self) -> List[SubscriptionState]:
        with self._lock:
            return [
                s
                for s in self._states.values()
                if s.status == SubscriptionStatus.PAST_DUE
            ]

    @property
    def total(self) -> int:
        with self._lock:
            return len(self._states)

    def mrr(self) -> int:
        """Monthly Recurring Revenue in cents."""
        with self._lock:
            return sum(
                s.amount
                for s in self._states.values()
                if s.status == SubscriptionStatus.ACTIVE
            )


# ---------------------------------------------------------------------------
# Stripe Webhook Handler
# ---------------------------------------------------------------------------

class StripeWebhookHandler:
    """
    Verifies Stripe webhook signatures and routes events to the BillingEventBus.

    Usage:
        handler = StripeWebhookHandler(
            webhook_secret="whsec_...",
            event_bus=BillingEventBus(),
            event_store=BillingEventStore(),
            state_manager=SubscriptionStateManager(),
        )
        result = handler.process(raw_body=b"...", signature_header="t=...,v1=...")
    """

    TOLERANCE_SECONDS = 300  # 5-minute replay attack window

    def __init__(
        self,
        webhook_secret: str,
        event_bus: BillingEventBus,
        event_store: BillingEventStore,
        state_manager: SubscriptionStateManager,
    ) -> None:
        self._secret = webhook_secret
        self._bus = event_bus
        self._store = event_store
        self._state_manager = state_manager
        self._processed_ids: set[str] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(
        self, raw_body: bytes, signature_header: str
    ) -> WebhookVerificationResult:
        """Verify Stripe webhook signature (Stripe-Signature header)."""
        try:
            parts = dict(item.split("=", 1) for item in signature_header.split(","))
            timestamp = parts.get("t")
            v1_sig = parts.get("v1")
            if not timestamp or not v1_sig:
                return WebhookVerificationResult(
                    valid=False, error="Missing t= or v1= in signature header"
                )

            # Replay attack check
            age = abs(time.time() - int(timestamp))
            if age > self.TOLERANCE_SECONDS:
                return WebhookVerificationResult(
                    valid=False,
                    error=f"Webhook timestamp too old ({age:.0f}s > {self.TOLERANCE_SECONDS}s)",
                )

            # HMAC-SHA256 verification
            signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
            expected = hmac.new(
                self._secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected, v1_sig):
                return WebhookVerificationResult(valid=False, error="Signature mismatch")

            payload = json.loads(raw_body)
            return WebhookVerificationResult(
                valid=True,
                event_type=payload.get("type"),
                event_id=payload.get("id"),
            )
        except Exception as exc:  # noqa: BLE001
            return WebhookVerificationResult(valid=False, error=str(exc))

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def process(
        self, raw_body: bytes, signature_header: str, skip_verification: bool = False
    ) -> Dict[str, Any]:
        """
        Verify + parse + route a Stripe webhook payload.
        Returns a result dict with status, event_id, and handlers_called.
        """
        if not skip_verification:
            verification = self.verify_signature(raw_body, signature_header)
            if not verification.valid:
                return {"status": "rejected", "reason": verification.error}

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            return {"status": "error", "reason": f"Invalid JSON: {exc}"}

        stripe_event_id = payload.get("id", "")
        event_type_str = payload.get("type", "")

        # Idempotency check
        with self._lock:
            if stripe_event_id in self._processed_ids:
                return {"status": "duplicate", "event_id": stripe_event_id}
            self._processed_ids.add(stripe_event_id)

        # Map to BillingEventType
        try:
            event_type = BillingEventType(event_type_str)
        except ValueError:
            return {
                "status": "ignored",
                "event_id": stripe_event_id,
                "reason": f"Unhandled event type: {event_type_str}",
            }

        customer_id = self._extract_customer_id(payload)
        billing_event = BillingEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            stripe_event_id=stripe_event_id,
            customer_id=customer_id,
            payload=payload.get("data", {}).get("object", {}),
        )

        # Update subscription state
        self._update_state(event_type, billing_event.payload, customer_id)

        # Store and publish
        self._store.append(billing_event)
        handlers_called = self._bus.publish(billing_event)
        billing_event.processed = True

        return {
            "status": "processed",
            "event_id": stripe_event_id,
            "event_type": event_type_str,
            "customer_id": customer_id,
            "handlers_called": handlers_called,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_customer_id(self, payload: Dict[str, Any]) -> str:
        obj = payload.get("data", {}).get("object", {})
        return (
            obj.get("customer")
            or obj.get("id", "")
            if payload.get("type", "").startswith("customer")
            else obj.get("customer", "unknown")
        )

    def _update_state(
        self,
        event_type: BillingEventType,
        obj: Dict[str, Any],
        customer_id: str,
    ) -> None:
        if event_type == BillingEventType.SUBSCRIPTION_DELETED:
            self._state_manager.delete(customer_id)
            return

        if event_type in (
            BillingEventType.SUBSCRIPTION_CREATED,
            BillingEventType.SUBSCRIPTION_UPDATED,
        ):
            plan = obj.get("plan") or (obj.get("items", {}).get("data") or [{}])[0].get(
                "plan", {}
            )
            state = SubscriptionState(
                customer_id=customer_id,
                subscription_id=obj.get("id", ""),
                status=SubscriptionStatus(obj.get("status", "active")),
                plan_id=plan.get("id", ""),
                plan_name=plan.get("nickname") or plan.get("id", ""),
                amount=plan.get("amount", 0),
                currency=plan.get("currency", "usd"),
                current_period_start=float(obj.get("current_period_start", 0)),
                current_period_end=float(obj.get("current_period_end", 0)),
                cancel_at_period_end=obj.get("cancel_at_period_end", False),
                trial_end=obj.get("trial_end"),
                metadata=obj.get("metadata", {}),
            )
            self._state_manager.upsert(state)

    @property
    def processed_count(self) -> int:
        with self._lock:
            return len(self._processed_ids)
