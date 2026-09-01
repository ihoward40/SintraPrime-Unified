"""Server-owned Mission Control capability policy resolver.

Fail-closed policy over an existing DurableWorkflowEngine registry.
No client workflow selection, no client approval flags, no role-escalation rules.
"""

from __future__ import annotations

from enum import StrEnum

from orchestration.durable_execution import DurableWorkflowEngine


class CapabilityDecision(StrEnum):
    DENY = "DENY"
    DIRECT_ALLOWED = "DIRECT_ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class CapabilityPolicyError(ValueError):
    """Capability policy refused the execution request."""


# Server-owned capability classifications. Production must contain only real
# capabilities with legitimate server registration and authorization evidence.
#
# The first and currently only production capability is the internal legal
# workflow — a nonconsequential internal state-transformation workflow with
# zero external side effects.  It is classified APPROVAL_REQUIRED because the
# constitutional default for any production capability with an approval
# artifact path is that the Principal must explicitly approve each Run.
_CAPABILITY_CLASSIFICATIONS: dict[str, CapabilityDecision] = {
    "legal_workflow": CapabilityDecision.APPROVAL_REQUIRED,
}


def _is_server_allowed_capability(capability: str) -> bool:
    """Only explicitly classified server capabilities are allowed."""
    return capability in _CAPABILITY_CLASSIFICATIONS


def _is_production_test_capability(capability: str) -> bool:
    """Reject acceptance-only or no-op names in production policy."""
    return capability.startswith(("mission_control.noop", "mission_control.test."))


def resolve_capability_policy(
    engine: DurableWorkflowEngine,
    *,
    capability: str | None,
) -> CapabilityDecision:
    """Return the server policy decision for a resolved capability.

    Rules (fail-closed):
        - missing capability → DENY
        - not server-allowed → DENY
        - not registered in engine → DENY
        - test/no-op capability → DENY
        - DIRECT_ALLOWED classified capability → DIRECT_ALLOWED
        - APPROVAL_REQUIRED classified capability → APPROVAL_REQUIRED
    """
    if not capability:
        raise CapabilityPolicyError("CAPABILITY_DENIED")
    if _is_production_test_capability(capability):
        raise CapabilityPolicyError("CAPABILITY_DENIED")
    if not _is_server_allowed_capability(capability):
        raise CapabilityPolicyError("CAPABILITY_DENIED")
    if capability not in engine._registered:
        raise CapabilityPolicyError("CAPABILITY_DENIED")
    decision = _CAPABILITY_CLASSIFICATIONS[capability]
    if decision not in {CapabilityDecision.DIRECT_ALLOWED, CapabilityDecision.APPROVAL_REQUIRED}:
        raise CapabilityPolicyError("CAPABILITY_DENIED")
    return decision
