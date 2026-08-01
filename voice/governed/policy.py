"""Policy decision layer for SP-VOICE-001.

Encodes the governing rule:

    Voice may request and coordinate. Existing SintraPrime policy decides,
    records, approves, executes, or refuses.

This module is the *decides / approves / refuses* half. It is a pure,
side-effect-free function of (risk class, feature flags). It performs NO
execution, NO routing to Hermes or providers, and touches NO production state —
that is Increment Two. It only computes what the required confirmation state and
policy decision are for a classified request.

Decision matrix:

    risk_class        flag gate                       decision            confirmation
    ----------------- ------------------------------- ------------------- ----------------
    read              enabled                         allowed             not_required
    draft             enabled                         allowed (draft)     not_required
    write             enabled + write_actions_enabled confirmation_req    required
    sensitive_write   (always requires confirm)       confirmation_req    required
    prohibited        —                               refused             denied

If the master ``enabled`` flag is false, every request is refused (disabled by
default). If a write is requested while ``write_actions_enabled`` is false, it is
refused — a capability flag can gate DOWN to refusal but never UP to execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .command_envelope import ConfirmationState, RiskClass
from .flags import VoiceFeatureFlags


class PolicyDecision(StrEnum):
    ALLOWED = "allowed"
    ALLOWED_DRAFT_ONLY = "allowed_draft_only"
    CONFIRMATION_REQUIRED = "confirmation_required"
    REFUSED = "refused"


@dataclass(frozen=True)
class PolicyResult:
    """Immutable outcome of a policy evaluation."""

    decision: PolicyDecision
    confirmation_state: ConfirmationState
    reason: str


def evaluate(risk_class: RiskClass, flags: VoiceFeatureFlags) -> PolicyResult:
    """Return the deterministic policy result for a classified request.

    Never raises for a known risk class; unknown enum values fall through to a
    fail-safe refusal.
    """
    if risk_class == RiskClass.PROHIBITED:
        return PolicyResult(
            PolicyDecision.REFUSED,
            ConfirmationState.DENIED,
            "prohibited action refused and logged",
        )

    # Master kill-switch: capability disabled by default.
    if not flags.enabled:
        return PolicyResult(
            PolicyDecision.REFUSED,
            ConfirmationState.DENIED,
            f"{FLAG_DISABLED_REASON} ({risk_class})",
        )

    if risk_class == RiskClass.READ:
        return PolicyResult(
            PolicyDecision.ALLOWED,
            ConfirmationState.NOT_REQUIRED,
            "read on authorized resource",
        )

    if risk_class == RiskClass.DRAFT:
        return PolicyResult(
            PolicyDecision.ALLOWED_DRAFT_ONLY,
            ConfirmationState.NOT_REQUIRED,
            "draft-only execution",
        )

    if risk_class == RiskClass.WRITE:
        if not flags.write_actions_enabled:
            return PolicyResult(
                PolicyDecision.REFUSED,
                ConfirmationState.DENIED,
                "write actions disabled by feature flag",
            )
        return PolicyResult(
            PolicyDecision.CONFIRMATION_REQUIRED,
            ConfirmationState.REQUIRED,
            "write requires typed-workflow authorization",
        )

    if risk_class == RiskClass.SENSITIVE_WRITE:
        return PolicyResult(
            PolicyDecision.CONFIRMATION_REQUIRED,
            ConfirmationState.REQUIRED,
            "sensitive write requires exact-target confirmation",
        )

    # Defensive fail-safe for any unmapped value.
    return PolicyResult(
        PolicyDecision.REFUSED,
        ConfirmationState.DENIED,
        "unclassified risk refused",
    )


FLAG_DISABLED_REASON = "SP-VOICE-001 disabled by feature flag"
