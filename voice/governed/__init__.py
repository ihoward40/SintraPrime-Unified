"""SP-VOICE-001 — Governed Voice Operations (Increment One: Foundation).

Governing rule:

    Voice may request and coordinate. Existing SintraPrime policy decides,
    records, approves, executes, or refuses.

This package provides the governed foundation only: an immutable voice command
envelope, a deterministic risk classifier, a policy decision layer, a session
state machine, confirmation semantics, correlated receipts, and disabled-by-
default feature flags. It routes NO production actions and touches NO production
Hermes state — orchestrator routing arrives in Increment Two.
"""

from __future__ import annotations

from .classifier import classify
from .command_envelope import (
    ConfirmationState,
    RiskClass,
    VoiceCommandEnvelope,
    VoiceSource,
    create_envelope,
    generate_command_id,
    generate_correlation_id,
    generate_session_id,
)
from .confirmation import (
    CONFIRMATION_TTL,
    ConfirmationOutcome,
    PendingConfirmation,
)
from .flags import TranscriptRetention, VoiceFeatureFlags
from .policy import PolicyDecision, PolicyResult, evaluate
from .receipts import VoiceReceipt, build_receipt, transcript_hash
from .session import (
    ChildTask,
    InvalidTransitionError,
    SessionState,
    VoiceSession,
)

__all__ = [
    "CONFIRMATION_TTL",
    "ChildTask",
    "ConfirmationOutcome",
    "ConfirmationState",
    "InvalidTransitionError",
    "PendingConfirmation",
    "PolicyDecision",
    "PolicyResult",
    "RiskClass",
    "SessionState",
    "TranscriptRetention",
    "VoiceCommandEnvelope",
    "VoiceFeatureFlags",
    "VoiceReceipt",
    "VoiceSession",
    "VoiceSource",
    "build_receipt",
    "classify",
    "create_envelope",
    "evaluate",
    "generate_command_id",
    "generate_correlation_id",
    "generate_session_id",
    "transcript_hash",
]
