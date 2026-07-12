"""Security helpers for monetization case starts.

Trust boundary for POST /api/monetization/start-case:

Stripe -> verified webhook handler -> normalized internal payment event -> HMAC
signing -> start-case route -> transactional generation.

This module implements model B: a trusted internal gateway event. The upstream
webhook handler is responsible for verifying Stripe's webhook signature and for
normalizing Stripe Checkout state into the strict event contract below. The
start-case route does not trust request fields alone; it verifies the signed raw
body, header bindings, payment state, tier amount, currency, and case/session
identity before any filesystem side effects are allowed.
"""

from __future__ import annotations

import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    from ..config import TIER_AMOUNTS
except ImportError:  # Allows standalone test loading without importing package initializers.
    TIER_AMOUNTS = {"starter": 9900, "pro": 49900, "enterprise": None}

CASE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

PAYMENT_EVENT_SCHEMA_VERSION = "internal_payment_event.v1"
ALLOWED_EVENT_TYPE = "checkout.session.completed"
REQUIRED_FIELDS = {
    "event_id",
    "event_type",
    "payment_session_id",
    "payment_status",
    "session_status",
    "amount_total",
    "currency",
    "tier",
    "case_id",
    "stripe_created_at",
    "verified_at",
    "key_id",
    "schema_version",
}
OPTIONAL_FIELDS = {
    "refunded",
    "expired",
    "email",
    "client_name",
    "phone",
    "case_type",
    "matter_type",
    "creditor_name",
    "court",
    "jurisdiction",
    "venue",
}


class CaseSecurityError(ValueError):
    """Raised when a case start request fails security validation."""


@dataclass(frozen=True)
class VerifiedPaymentEvent:
    event_id: str
    event_type: str
    payment_session_id: str
    payment_status: str
    session_status: str
    amount_total: int
    currency: str
    tier: str
    case_id: str
    stripe_created_at: str
    verified_at: str
    key_id: str
    schema_version: str
    body_sha256: str


def validate_case_id(case_id: str) -> str:
    if not CASE_ID_RE.fullmatch(case_id):
        raise CaseSecurityError(
            "case_id must match ^[A-Z0-9][A-Z0-9_-]{2,63}$"
        )
    if case_id.rstrip(" .") != case_id:
        raise CaseSecurityError("case_id must not end with a space or period")
    if case_id.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        raise CaseSecurityError("case_id uses a reserved Windows device name")
    if any(part in case_id for part in ("..", "/", "\\")):
        raise CaseSecurityError("case_id must not contain traversal or path separators")
    if re.match(r"^[A-Za-z]:", case_id):
        raise CaseSecurityError("case_id must not contain a drive letter")
    return case_id


def contained_child(root: Path, child_name: str) -> Path:
    root_resolved = root.resolve()
    target = (root_resolved / validate_case_id(child_name)).resolve()
    if target.parent != root_resolved:
        raise CaseSecurityError("case path escaped the clients directory")
    return target


def stable_idempotency_key(event_id: str) -> str:
    if not event_id or len(event_id) > 160:
        raise CaseSecurityError("X-Start-Case-Event-Id is required and must be <= 160 chars")
    return sha256(event_id.encode("utf-8")).hexdigest()


def body_digest(body: bytes) -> str:
    return sha256(body).hexdigest()


def canonical_signature_input(*, key_id: str, timestamp: str, event_id: str, raw_body_sha256: str) -> bytes:
    """Return exact HMAC input: v1\n<key_id>\n<timestamp>\n<event_id>\n<body_sha256>."""
    return f"v1\n{key_id}\n{timestamp}\n{event_id}\n{raw_body_sha256}".encode()


def _configured_keys() -> dict[str, str]:
    keys_json = os.getenv("MONETIZATION_START_CASE_HMAC_KEYS")
    keys: dict[str, str] = {}
    if keys_json:
        try:
            loaded = json.loads(keys_json)
        except json.JSONDecodeError as exc:
            raise CaseSecurityError("MONETIZATION_START_CASE_HMAC_KEYS is invalid JSON") from exc
        if not isinstance(loaded, dict):
            raise CaseSecurityError("MONETIZATION_START_CASE_HMAC_KEYS must be a JSON object")
        keys.update({str(k): str(v) for k, v in loaded.items() if v})

    current_id = os.getenv("MONETIZATION_START_CASE_CURRENT_KEY_ID")
    current_secret = os.getenv("MONETIZATION_START_CASE_CURRENT_SECRET")
    previous_id = os.getenv("MONETIZATION_START_CASE_PREVIOUS_KEY_ID")
    previous_secret = os.getenv("MONETIZATION_START_CASE_PREVIOUS_SECRET")
    legacy_secret = os.getenv("MONETIZATION_START_CASE_WEBHOOK_SECRET")

    if current_id and current_secret:
        keys[current_id] = current_secret
    if previous_id and previous_secret:
        keys[previous_id] = previous_secret
    if legacy_secret and "legacy" not in keys:
        keys["legacy"] = legacy_secret
    if not keys:
        raise CaseSecurityError("no start-case HMAC keys are configured")
    return keys


def _parse_utc_timestamp(value: str, *, field_name: str) -> datetime:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CaseSecurityError(f"{field_name} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise CaseSecurityError(f"{field_name} must include timezone information")
    return parsed.astimezone(UTC)


def _validate_signature_timestamp(timestamp: str) -> None:
    parsed = _parse_utc_timestamp(timestamp, field_name="X-Start-Case-Timestamp")
    now = datetime.now(UTC)
    max_age = int(os.getenv("MONETIZATION_START_CASE_MAX_AGE_SECONDS", "300"))
    skew = int(os.getenv("MONETIZATION_START_CASE_CLOCK_SKEW_SECONDS", "60"))
    if parsed < now - timedelta(seconds=max_age + skew):
        raise CaseSecurityError("start-case signature timestamp is expired")
    if parsed > now + timedelta(seconds=skew):
        raise CaseSecurityError("start-case signature timestamp is too far in the future")


def _supported_currency() -> set[str]:
    configured = os.getenv("MONETIZATION_SUPPORTED_CURRENCIES", "usd")
    return {c.strip().lower() for c in configured.split(",") if c.strip()}


def _tier_amounts() -> dict[str, int]:
    amounts: dict[str, int] = {}
    for tier, amount in TIER_AMOUNTS.items():
        override = os.getenv(f"MONETIZATION_TIER_AMOUNT_{tier.upper()}")
        if override:
            amounts[tier] = int(override)
        elif isinstance(amount, int):
            amounts[tier] = amount
    return amounts


def _load_event(body: bytes) -> dict[str, Any]:
    try:
        event = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CaseSecurityError("start-case body must be strict UTF-8 JSON") from exc
    if not isinstance(event, dict):
        raise CaseSecurityError("start-case body must be a JSON object")
    unknown = set(event) - REQUIRED_FIELDS - OPTIONAL_FIELDS
    missing = REQUIRED_FIELDS - set(event)
    if unknown:
        raise CaseSecurityError(f"unknown internal payment event fields: {', '.join(sorted(unknown))}")
    if missing:
        raise CaseSecurityError(f"missing internal payment event fields: {', '.join(sorted(missing))}")
    return event


def _validate_event_contract(event: dict[str, Any]) -> None:
    if event["schema_version"] != PAYMENT_EVENT_SCHEMA_VERSION:
        raise CaseSecurityError("unsupported internal payment event schema_version")
    if event["event_type"] != ALLOWED_EVENT_TYPE:
        raise CaseSecurityError("unsupported internal payment event type")
    if event["payment_status"] != "paid":
        raise CaseSecurityError("payment_status must be paid")
    if event["session_status"] != "complete":
        raise CaseSecurityError("session_status must be complete")
    if event.get("refunded") is True:
        raise CaseSecurityError("refunded payment events are not accepted")
    if event.get("expired") is True:
        raise CaseSecurityError("expired payment events are not accepted")
    if str(event["currency"]).lower() not in _supported_currency():
        raise CaseSecurityError("unsupported payment currency")
    tier = str(event["tier"])
    amounts = _tier_amounts()
    if tier not in amounts:
        raise CaseSecurityError("unsupported or unpriced payment tier")
    if not isinstance(event["amount_total"], int):
        raise CaseSecurityError("amount_total must be an integer number of minor currency units")
    if event["amount_total"] != amounts[tier]:
        raise CaseSecurityError("amount_total does not match configured tier price")
    validate_case_id(str(event["case_id"]))
    _parse_utc_timestamp(str(event["stripe_created_at"]), field_name="stripe_created_at")
    _parse_utc_timestamp(str(event["verified_at"]), field_name="verified_at")
    for field in ("event_id", "payment_session_id", "key_id"):
        value = event[field]
        if not isinstance(value, str) or not value or len(value) > 200:
            raise CaseSecurityError(f"{field} must be a non-empty string <= 200 chars")


def verify_signed_internal_event(
    *,
    body: bytes,
    key_id: str,
    timestamp: str,
    event_id: str,
    signature: str,
) -> VerifiedPaymentEvent:
    if not key_id or not timestamp or not event_id or not signature:
        raise CaseSecurityError("start-case signature headers are required")
    _validate_signature_timestamp(timestamp)
    keys = _configured_keys()
    if key_id not in keys:
        raise CaseSecurityError("unknown start-case HMAC key id")
    digest = body_digest(body)
    expected = hmac.new(
        keys[key_id].encode("utf-8"),
        canonical_signature_input(
            key_id=key_id,
            timestamp=timestamp,
            event_id=event_id,
            raw_body_sha256=digest,
        ),
        sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise CaseSecurityError("invalid start-case signature")

    event = _load_event(body)
    _validate_event_contract(event)
    if event["event_id"] != event_id:
        raise CaseSecurityError("header event id does not match signed event body")
    if event["key_id"] != key_id:
        raise CaseSecurityError("header key id does not match signed event body")

    return VerifiedPaymentEvent(
        event_id=str(event["event_id"]),
        event_type=str(event["event_type"]),
        payment_session_id=str(event["payment_session_id"]),
        payment_status=str(event["payment_status"]),
        session_status=str(event["session_status"]),
        amount_total=int(event["amount_total"]),
        currency=str(event["currency"]).lower(),
        tier=str(event["tier"]),
        case_id=str(event["case_id"]),
        stripe_created_at=str(event["stripe_created_at"]),
        verified_at=str(event["verified_at"]),
        key_id=str(event["key_id"]),
        schema_version=str(event["schema_version"]),
        body_sha256=digest,
    )


# Backward-compatible helper retained for existing imports/tests. New route code uses
# verify_signed_internal_event because legacy event_id.body HMAC is insufficient for
# payment trust-boundary enforcement.
def verify_hmac_signature(*, body: bytes, event_id: str, signature: str) -> None:
    secret = os.getenv("MONETIZATION_START_CASE_WEBHOOK_SECRET")
    if not secret:
        raise CaseSecurityError("MONETIZATION_START_CASE_WEBHOOK_SECRET is not configured")
    payload = event_id.encode("utf-8") + b"." + body
    expected = hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise CaseSecurityError("invalid start-case signature")
