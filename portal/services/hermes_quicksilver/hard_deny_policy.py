"""Hard-deny policy evaluator for Hermes Quicksilver delegation.

Evaluated before any Hermes profile resolution or invocation. Hard deny
overrides every allow path, including approvals and administrator overrides.
"""

from __future__ import annotations

from typing import List

from portal.models.hermes_quicksilver import (
    Decision,
    DelegationRequest,
    HardDenyResult,
    SpecialistProfileMapping,
)

# Increment One built-in deny rules. These are repository-native defaults.
_DENIED_OPERATIONS = {
    "run_agent",
    "send_message",
    "execute_tool",
    "start_session",
    "resume_session",
    "modify_profile",
    "create_profile",
    "delete_profile",
    "switch_model",
    "install_dependency",
    "restart_gateway",
}

_INCREMENT_ONE_ALLOWED_OPERATIONS = {
    "list_profiles",
    "get_profile_metadata",
    "validate_profile_mapping",
    "check_runtime_compatibility",
}


class HermesHardDenyPolicy:
    """Fail-closed hard-deny evaluator."""

    def __init__(self, extra_denied_operations: List[str] | None = None):
        self.denied_operations = set(_DENIED_OPERATIONS)
        if extra_denied_operations:
            self.denied_operations.update(extra_denied_operations)

    def evaluate(
        self,
        request: DelegationRequest,
        mapping: SpecialistProfileMapping | None,
    ) -> HardDenyResult:
        """Return denied=True if the operation must not proceed."""
        matched: List[str] = []

        if request.operation not in _INCREMENT_ONE_ALLOWED_OPERATIONS:
            matched.append("operation_not_in_allowlist")

        if request.operation in self.denied_operations:
            matched.append("operation_hard_denied")

        if mapping is not None and request.operation in mapping.prohibited_tool_classes:
            matched.append("prohibited_tool_class")

        if mapping is not None and mapping.risk_ceiling.value == "HIGH":
            matched.append("high_risk_ceiling")

        if matched:
            return HardDenyResult(
                denied=True,
                reason_code="hard_denied",
                matched_rules=matched,
            )

        return HardDenyResult(denied=False)

    @staticmethod
    def is_operation_allowed(operation: str) -> bool:
        """Return True only for Increment One read-only operations."""
        return operation in _INCREMENT_ONE_ALLOWED_OPERATIONS
