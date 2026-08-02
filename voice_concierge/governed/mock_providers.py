"""Mock capability providers for SP-VOICE-001 — Increment Two.

Every provider in this module is a sandboxed simulation. NONE of them place a
real phone call, send a real email or message, create a real calendar event,
submit a real filing, or move real money. Each returns a ``ProviderResult``
with ``mock=True`` and a ``mock-`` prefixed resource id so no caller can
mistake the output for a real external side effect.

Providers are intentionally simple and deterministic: given the same envelope
they produce the same shape of result (modulo a fresh id), so orchestration
and receipts are reproducible in tests and demos.
"""

from __future__ import annotations

import uuid

from .command_envelope import RiskClass, VoiceCommandEnvelope
from .providers import ProviderResult, VoiceCapability


def _mock_id(prefix: str) -> str:
    return f"mock-{prefix}-{uuid.uuid4().hex[:12]}"


class _BaseMockProvider:
    capability: VoiceCapability
    _noun: str

    def execute(self, envelope: VoiceCommandEnvelope, *, risk_class: RiskClass) -> ProviderResult:
        action = "draft" if risk_class == RiskClass.DRAFT else "read" if risk_class == RiskClass.READ else "simulate"
        resource_id = _mock_id(self._noun)
        return ProviderResult(
            capability=self.capability,
            action=action,
            resource_id=resource_id,
            summary=(
                f"[MOCK/SANDBOX] {action} {self._noun} for '{envelope.normalized_intent}' "
                f"— no real {self._noun} was affected."
            ),
            artifacts=[resource_id],
            details={"target_resource": envelope.target_resource, "risk_class": str(risk_class)},
        )


class MockEmailProvider(_BaseMockProvider):
    """Simulates drafting/sending email. Never contacts a real mail transport."""

    capability = VoiceCapability.EMAIL
    _noun = "email"


class MockCalendarProvider(_BaseMockProvider):
    """Simulates calendar event creation. Never contacts a real calendar."""

    capability = VoiceCapability.CALENDAR
    _noun = "calendar-event"


class MockMessagingProvider(_BaseMockProvider):
    """Simulates chat/SMS/social posting. Never sends a real message."""

    capability = VoiceCapability.MESSAGING
    _noun = "message"


class MockTaskProvider(_BaseMockProvider):
    """Simulates repository/task-board actions (branch, commit, task, report)."""

    capability = VoiceCapability.TASK
    _noun = "task"


class MockFilingProvider(_BaseMockProvider):
    """Simulates court/regulatory filing submission. Never files anything real."""

    capability = VoiceCapability.FILING
    _noun = "filing"


class MockPaymentProvider(_BaseMockProvider):
    """Simulates payment/transfer actions. Never moves real money."""

    capability = VoiceCapability.PAYMENT
    _noun = "payment"


class MockGenericProvider(_BaseMockProvider):
    """Fallback simulator for unrecognized capability domains."""

    capability = VoiceCapability.GENERIC
    _noun = "action"


DEFAULT_MOCK_PROVIDERS: dict[VoiceCapability, _BaseMockProvider] = {
    VoiceCapability.EMAIL: MockEmailProvider(),
    VoiceCapability.CALENDAR: MockCalendarProvider(),
    VoiceCapability.MESSAGING: MockMessagingProvider(),
    VoiceCapability.TASK: MockTaskProvider(),
    VoiceCapability.FILING: MockFilingProvider(),
    VoiceCapability.PAYMENT: MockPaymentProvider(),
    VoiceCapability.GENERIC: MockGenericProvider(),
}


def default_mock_registry() -> dict[VoiceCapability, _BaseMockProvider]:
    """Return a fresh copy of the default mock provider registry.

    A fresh dict is returned (not the module-level singleton) so tests and
    callers may safely mutate or substitute providers without cross-test
    leakage.
    """
    return dict(DEFAULT_MOCK_PROVIDERS)
