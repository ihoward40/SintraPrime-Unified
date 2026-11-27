"""Agent Nova — Autonomous real-world execution engine.

SP-TRANSACTION-CAPACITY-001 is installed here as a package-level fail-closed
pre-dispatch gate.  Python executes this package initializer before resolving
``agents.nova.nova_agent`` imports, so both package imports and direct submodule
imports receive the governed ``NovaAgent.execute_action`` implementation.
"""

from functools import wraps
from typing import Any

from legal_intelligence.transaction_capacity_gate import TransactionCapacityGate

from .nova_agent import NovaAgent


_transaction_capacity_gate = TransactionCapacityGate()
_original_execute_action = NovaAgent.execute_action


@wraps(_original_execute_action)
def _governed_execute_action(
    self: NovaAgent,
    action_type: str,
    params: dict[str, Any],
    approval_required: bool | None = None,
):
    """Enforce SP-TRANSACTION-CAPACITY-001 before approval or execution.

    The gate runs before Nova's dispatcher can dynamically generate a handler,
    create an approval request, or execute a registered action.  A successful
    gate report is embedded into the action params so downstream audit records
    preserve exactly what was classified and permitted.
    """
    governed_params = dict(params)
    report = _transaction_capacity_gate.enforce(action_type, governed_params)
    governed_params["_sp_transaction_capacity_001"] = report.as_dict()
    return _original_execute_action(
        self,
        action_type,
        governed_params,
        approval_required=approval_required,
    )


# Idempotent patching protects reload/test environments from wrapper stacking.
if not getattr(NovaAgent.execute_action, "_sp_transaction_capacity_001", False):
    _governed_execute_action._sp_transaction_capacity_001 = True
    NovaAgent.execute_action = _governed_execute_action


__all__ = ["NovaAgent"]
