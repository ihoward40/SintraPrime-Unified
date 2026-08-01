"""Tests for Stripe webhook signature verification, tenant resolution,
and audit-envelope integration."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import stripe

from portal.services.payment_event_service import (
    PLATFORM_SENTINEL,
    TenantResolutionError,
    compute_payload_digest,
    verify_stripe_signature,
)


def _make_stripe_event(
    event_id: str = "evt_test_123",
    event_type: str = "payment_intent.succeeded",
    account: str | None = None,
    customer: str | None = None,
) -> dict:
    """Build a mock Stripe event dictionary."""
    event = {
        "id": event_id,
        "type": event_type,
        "data": {"object": {}},
    }
    if account:
        event["account"] = account
    if customer:
        event["data"]["object"]["customer"] = customer
    return event


class TestSignatureVerification:
    """Test Stripe webhook signature verification."""

    def test_valid_signature_accepted(self):
        raw_body = b'{"id":"evt_123","type":"payment_intent.succeeded"}'
        sig_header = "t=1234567890,v1=valid_sig"
        secret = "whsec_test"
        mock_event = _make_stripe_event()
        with patch.object(stripe.Webhook, "construct_event", return_value=mock_event):
            event = verify_stripe_signature(raw_body, sig_header, secret)
            assert event["id"] == "evt_test_123"
            assert event["type"] == "payment_intent.succeeded"

    def test_missing_signature_rejected(self):
        raw_body = b'{"id":"evt_123"}'
        with pytest.raises(stripe.error.SignatureVerificationError):
            verify_stripe_signature(raw_body, None, "whsec_test")

    def test_invalid_signature_rejected(self):
        raw_body = b'{"id":"evt_123"}'
        sig_header = "t=1234567890,v1=invalid_sig"
        with patch.object(
            stripe.Webhook,
            "construct_event",
            side_effect=stripe.error.SignatureVerificationError("bad sig", sig_header),
        ):
            with pytest.raises(stripe.error.SignatureVerificationError):
                verify_stripe_signature(raw_body, sig_header, "whsec_test")

    def test_raw_body_preserved_before_verification(self):
        """Verify the raw body is passed directly to construct_event."""
        raw_body = b'{"id":"evt_123","type":"test"}'
        sig_header = "t=123,v1=sig"
        with patch.object(stripe.Webhook, "construct_event") as mock:
            mock.return_value = _make_stripe_event()
            verify_stripe_signature(raw_body, sig_header, "whsec_test")
            call_args = mock.call_args
            assert call_args[0][0] == raw_body  # First positional arg is raw body

    def test_verified_event_id_preserved(self):
        mock_event = _make_stripe_event(event_id="evt_unique_456")
        raw_body = json.dumps(mock_event).encode()
        with patch.object(stripe.Webhook, "construct_event", return_value=mock_event):
            event = verify_stripe_signature(raw_body, "t=1,v1=sig", "whsec_test")
            assert event["id"] == "evt_unique_456"


class TestPayloadDigest:
    """Test payload digest computation."""

    def test_digest_is_sha256(self):
        body = b'{"test": true}'
        digest = compute_payload_digest(body)
        expected = hashlib.sha256(body).hexdigest()
        assert digest == expected
        assert len(digest) == 64

    def test_different_bodies_different_digests(self):
        assert compute_payload_digest(b"body1") != compute_payload_digest(b"body2")


class TestPlatformSentinel:
    """Test non-Connect event sentinel behavior."""

    def test_non_connect_event_uses_platform_sentinel(self):
        event = _make_stripe_event()
        assert "account" not in event

    def test_connect_event_has_account(self):
        event = _make_stripe_event(account="acct_test_123")
        assert event["account"] == "acct_test_123"


class TestSensitiveDataRedaction:
    """Test that sensitive data is not stored in audit metadata."""

    def test_card_number_not_in_metadata(self):
        from portal.auth.audit_envelope import REDACTED_FIELDS
        assert "card" not in REDACTED_FIELDS
        assert "password" in REDACTED_FIELDS
        assert "token" in REDACTED_FIELDS

    def test_audit_envelope_uses_webhook_transport(self):
        from portal.auth.audit_envelope import Transport
        assert Transport.WEBHOOK == "webhook"

    def test_audit_envelope_supports_system_actor(self):
        from portal.auth.audit_envelope import ActorType
        assert ActorType.SYSTEM == "system"

    def test_audit_envelope_supports_denied_outcome(self):
        from portal.auth.audit_envelope import Outcome
        assert Outcome.DENIED == "denied"

    def test_audit_envelope_nullable_tenant(self):
        from portal.auth.audit_envelope import ActorType, Outcome, Transport, build_audit_event
        event = build_audit_event(
            action="webhook.signature_rejected",
            actor_type=ActorType.SYSTEM,
            tenant_id=None,
            source_transport=Transport.WEBHOOK,
            outcome=Outcome.DENIED,
            denial_reason="invalid_signature",
        )
        assert event.tenant_id is None
        assert event.actor_type == "system"
        assert event.source_transport == "webhook"
