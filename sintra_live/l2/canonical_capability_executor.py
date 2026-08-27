"""L2-I8 canonical capability executor interface — contract only, no execution.

Defines the protocol/interface for a future live executor.
The I8 offline gate does not authorize invocation of this interface.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from sintra_live.l2.capability_registry_contract import CapabilityResolutionRecord
from sintra_live.l2.action_envelope_contract import ActionEnvelope
from sintra_live.l2.principal_approval_contract import PrincipalApprovalRecord


@runtime_checkable
class CanonicalCapabilityExecutor(Protocol):
    """Canonical executor interface contract.

    A live implementation must:
    - accept only an ActionEnvelope, PrincipalApprovalRecord, and CapabilityResolutionRecord
    - verify that resolution.result == ALLOW before any I/O
    - verify that execution_ready is False before I/O (it always is from I8)
    - use the envelope-supplied execution_id and nonce (never auto-generate)
    - bind the provider class, mode, account, and credential boundary exactly
    - return a durable AttemptRecord with hash-linked evidence
    - never fall back to mock/dry-run providers
    - never expand authority beyond the envelope and approval

    The I8 offline implementation gate does NOT authorize invoking this interface.
    """

    def execute(
        self,
        envelope: ActionEnvelope,
        approval: PrincipalApprovalRecord,
        resolution: CapabilityResolutionRecord,
    ) -> Dict[str, Any]:
        """Execute one approved action and return a durable AttemptRecord.

        This method is a contract definition only. No implementation is
        authorized under the I8 offline gate.
        """
        ...


__all__ = ["CanonicalCapabilityExecutor"]