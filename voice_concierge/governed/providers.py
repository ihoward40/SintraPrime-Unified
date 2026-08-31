"""Provider protocol layer for SP-VOICE-001 — Increment Two.

Defines the typed contract every voice-originated capability provider must
implement, plus a deterministic, policy-independent mapping from a normalized
intent to the capability domain it targets (email, calendar, messaging, task,
filing, payment, generic). Capability resolution is separate from risk
classification (``classifier.py``): risk decides IF an action may proceed,
capability resolution decides WHICH provider handles it once policy allows or
requires confirmation.

This module defines the protocol only. It contains NO concrete providers and
performs NO I/O. Concrete implementations (Increment Two ships mock-only
implementations — see ``mock_providers.py``) must never contact a real
telephony, calendar, messaging, or payment backend from this package. Real
provider adapters, if ever introduced, belong to a future increment with its
own governance review and are explicitly out of scope here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from .command_envelope import RiskClass, VoiceCommandEnvelope


class VoiceCapability(StrEnum):
    """Capability domain a voice-originated action targets."""

    EMAIL = "email"
    CALENDAR = "calendar"
    MESSAGING = "messaging"
    TASK = "task"
    FILING = "filing"
    PAYMENT = "payment"
    GENERIC = "generic"


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Ordered by precedence — first bucket that matches wins. Order matters because
# some verbs are shared across domains (e.g. "send" appears for email and
# messaging); more specific nouns are checked first.
_CAPABILITY_PATTERNS: list[tuple[list[re.Pattern[str]], VoiceCapability]] = [
    (
        _compile([r"\be-?mail\b", r"\binbox\b", r"\bcompose\b.*\bmail\b"]),
        VoiceCapability.EMAIL,
    ),
    (
        _compile(
            [r"\bcalendar\b", r"\bmeeting\b", r"\bevent\b", r"\bschedule\b", r"\bappointment\b"]
        ),
        VoiceCapability.CALENDAR,
    ),
    (
        _compile(
            [
                r"\bpay\b",
                r"\bspend\b",
                r"\bpurchase\b",
                r"\bbuy\b",
                r"\binvoice\b",
                r"\brefund\b",
                r"\btransfer funds\b",
                r"\bwire\b",
            ]
        ),
        VoiceCapability.PAYMENT,
    ),
    (
        _compile(
            [
                r"\bfile (a |an |the )",
                r"\be-?file\b",
                r"\bmotion\b",
                r"\bcourt filing\b",
                r"\bpleading\b",
            ]
        ),
        VoiceCapability.FILING,
    ),
    (
        _compile(
            [
                r"\bmessage\b",
                r"\btext\b",
                r"\bslack\b",
                r"\bnotify\b",
                r"\btweet\b",
                r"\bpost\b",
                r"\bpublish\b",
            ]
        ),
        VoiceCapability.MESSAGING,
    ),
    (
        _compile(
            [
                r"\btask\b",
                r"\bbranch\b",
                r"\bcommit\b",
                r"\btests?\b",
                r"\breport\b",
                r"\bchecklist\b",
                r"\bmemo\b",
                r"\bsummary\b",
                r"\bdocument\b",
            ]
        ),
        VoiceCapability.TASK,
    ),
]


def resolve_capability(
    normalized_intent: str,
    requested_capability: str | None = None,
) -> VoiceCapability:
    """Deterministically resolve which capability domain an intent targets.

    An explicit ``requested_capability`` (from the envelope) is honored only
    if it names a known capability; otherwise inference falls back to the
    keyword patterns. Unmatched intents fail safe to ``GENERIC`` so an
    unrecognized capability never silently resolves to a sensitive domain
    like payment or filing.
    """
    if requested_capability:
        try:
            return VoiceCapability(requested_capability.strip().lower())
        except ValueError:
            pass  # fall through to keyword inference

    text = (normalized_intent or "").strip().lower()
    if not text:
        return VoiceCapability.GENERIC
    for patterns, capability in _CAPABILITY_PATTERNS:
        if any(p.search(text) for p in patterns):
            return capability
    return VoiceCapability.GENERIC


@dataclass(frozen=True)
class ProviderResult:
    """Immutable outcome of a single provider execution.

    ``mock`` is always ``True`` in Increment Two — every provider shipped in
    this package is a sandboxed simulation. ``resource_id`` is always prefixed
    ``mock-`` so no downstream consumer can mistake it for a real external
    identifier (phone number, calendar event, message ID, ledger entry, etc.).
    """

    capability: VoiceCapability
    action: str
    resource_id: str
    summary: str
    mock: bool = True
    artifacts: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class ProviderExecutionError(Exception):
    """Raised when a mock provider cannot simulate the requested action."""


@runtime_checkable
class VoiceActionProvider(Protocol):
    """Protocol every capability provider (mock or, in a future increment,
    real) must implement. Providers execute NOTHING on their own initiative —
    they are only ever invoked by the orchestrator after policy has decided
    the action is allowed, draft-only, or explicitly confirmed.
    """

    capability: VoiceCapability

    def execute(
        self,
        envelope: VoiceCommandEnvelope,
        *,
        risk_class: RiskClass,
    ) -> ProviderResult:
        """Simulate (or, in a future increment, perform) the requested action."""
        ...
