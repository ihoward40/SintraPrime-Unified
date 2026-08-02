"""SP-VOICE-001 — Governed Voice Operations (Increment One + Two).

Governing rule:

    Voice may request and coordinate. Existing SintraPrime policy decides,
    records, approves, executes, or refuses.

Increment One provides the governed foundation: an immutable voice command
envelope, a deterministic risk classifier, a policy decision layer, a session
state machine, confirmation semantics, correlated receipts, and disabled-by-
default feature flags.

Increment Two adds the orchestrator and mock provider layer: policy-approved
reads/drafts execute immediately against sandboxed mock providers; writes and
sensitive writes execute against mock providers ONLY after exact-target
confirmation. Every provider in this package is a simulation — this package
routes NO production actions and touches NO production Hermes state, no real
phone/calendar/messaging/filing/payment backend.
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
from .mock_providers import DEFAULT_MOCK_PROVIDERS, default_mock_registry
from .orchestrator import (
    OrchestrationOutcome,
    cancel_voice_command,
    confirm_voice_command,
    handle_voice_command,
)
from .policy import PolicyDecision, PolicyResult, evaluate
from .providers import (
    ProviderExecutionError,
    ProviderResult,
    VoiceActionProvider,
    VoiceCapability,
    resolve_capability,
)
from .receipts import VoiceReceipt, build_receipt, transcript_hash
from .session import (
    ChildTask,
    InvalidTransitionError,
    SessionState,
    VoiceSession,
)

__all__ = [
    "CONFIRMATION_TTL",
    "DEFAULT_MOCK_PROVIDERS",
    "ChildTask",
    "ConfirmationOutcome",
    "ConfirmationState",
    "InvalidTransitionError",
    "OrchestrationOutcome",
    "PendingConfirmation",
    "PolicyDecision",
    "PolicyResult",
    "ProviderExecutionError",
    "ProviderResult",
    "RiskClass",
    "SessionState",
    "TranscriptRetention",
    "VoiceActionProvider",
    "VoiceCapability",
    "VoiceCommandEnvelope",
    "VoiceFeatureFlags",
    "VoiceReceipt",
    "VoiceSession",
    "VoiceSource",
    "build_receipt",
    "cancel_voice_command",
    "classify",
    "confirm_voice_command",
    "create_envelope",
    "default_mock_registry",
    "evaluate",
    "generate_command_id",
    "generate_correlation_id",
    "generate_session_id",
    "handle_voice_command",
    "resolve_capability",
    "transcript_hash",
]
