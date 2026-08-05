"""SIGMA_LEASE_EXPIRY_CONTINUATION_GATE service.

Implements the mandatory Sigma condition from ADR-002 Section 2.5:

> Define explicit criteria for executor continuation after lease expiry
> during Brain unavailability, including mandatory reconciliation and
> completion reporting when the Brain recovers.

This gate is a BLOCKING gate for all cancellation controls. While the gate
state is BLOCKED, no cancellation mutation endpoint may accept requests.

The gate is read-only in the Foundation phase — there is no mutation endpoint
to transition the gate state. The state will transition to DEFINED when an
implementation ADR or narrowly scoped amendment defines the criteria, and to
SATISFIED when the criteria are implemented and certified.

This service is pure read logic — it does not modify any state.
"""

from __future__ import annotations

from typing import Literal

from ..schemas.mission_control_projection import (
    CancellationControlStatus,
    SigmaGateStatus,
)

GATE_ID: Literal["SIGMA_LEASE_EXPIRY_CONTINUATION_GATE"] = "SIGMA_LEASE_EXPIRY_CONTINUATION_GATE"

# The gate is BLOCKED in the Foundation phase. The state is a constant —
# it does not transition at runtime. Transition requires an ADR amendment
# and explicit Principal authorization, not a code path.
GATE_STATE: Literal["BLOCKED"] = "BLOCKED"

SIGMA_CRITERIA: list[str] = [
    "Explicit criteria for when optional executor continuation is permitted after lease expiry",
    "Definition of what constitutes 'local state sufficient to complete the task'",
    "Mandatory completion reporting on Brain recovery",
    "Reconciliation between executor-reported state and Brain ledger on recovery",
    "Handling of conflicting results if multiple executors continued during unavailability",
]

GATE_DESCRIPTION = (
    "Sigma security review condition (ADR-002 Section 2.5): executor "
    "continuation after lease expiry during Brain unavailability must "
    "define explicit criteria, mandatory reconciliation, and completion "
    "reporting. Until this gate is SATISFIED, all cancellation controls "
    "remain DISABLED."
)


def get_gate_status() -> SigmaGateStatus:
    """Return the current read-only status of the Sigma gate.

    The gate is BLOCKED in the Foundation phase. Cancellation controls
    are DISABLED.
    """
    return SigmaGateStatus(
        gate_id=GATE_ID,
        state=GATE_STATE,
        description=GATE_DESCRIPTION,
        criteria=SIGMA_CRITERIA,
        cancellation_controls="DISABLED",
        blocking_phase_3b=True,
    )


def get_cancellation_status() -> CancellationControlStatus:
    """Return the read-only cancellation control status.

    All three ADR-002 cancellation scopes (execution, tenant, platform)
    are DISABLED while the Sigma gate is BLOCKED.
    """
    gate = get_gate_status()
    return CancellationControlStatus(
        execution_scoped="DISABLED",
        tenant_scoped="DISABLED",
        platform_break_glass="DISABLED",
        gate=gate,
        reason=(
            f"{GATE_ID} is {gate.state}. "
            "Cancellation controls are disabled until the gate is SATISFIED."
        ),
    )


def is_cancellation_blocked() -> bool:
    """Return True if cancellation controls are blocked by the Sigma gate.

    This function is the programmatic gate check. Any future code path that
    attempts to exercise cancellation must call this and respect the result.
    """
    return GATE_STATE == "BLOCKED"
