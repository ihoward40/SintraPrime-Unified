"""JARVIS-001-B1 action failure taxonomy (B1-9).

Distinct from inference-provider error kinds by design: governed action
execution has its own failure vocabulary. Never overload provider inference
errors for action execution.
"""
from __future__ import annotations


class ActionError(Exception):
    """Raised when a governed action cannot proceed or complete safely."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else f"{code}: {detail}")


# Backward-compatible alias used across the B1 seam.
ActionFailure = ActionError


ACTION_FAILURE_CODES = (
    "AUTHORITY_DENIED",
    "APPROVAL_MISSING",
    "APPROVAL_EXPIRED",
    "APPROVAL_MISMATCH",
    "APPROVAL_REPLAY",
    "TENANT_MISMATCH",
    "EXECUTOR_UNAVAILABLE",
    "PROVIDER_AUTH_FAILURE",
    "PROVIDER_RATE_LIMIT",
    "PROVIDER_ERROR",
    "TIMEOUT",
    "SIDE_EFFECT_UNKNOWN",
    "SIDE_EFFECT_FAILED",
    "SIDE_EFFECT_SUCCEEDED",
    "VERIFICATION_FAILED",
    "VERIFICATION_INCONCLUSIVE",
    "IDEMPOTENCY_CONFLICT",
    "RECEIPT_WRITE_FAILED",
    "ACTION_TYPE_NOT_ALLOWLISTED",
    "PROPOSED_ACTION_INVALID",
)
