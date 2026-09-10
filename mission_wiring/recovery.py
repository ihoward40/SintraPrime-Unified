"""W5-2 — restart/recovery census for the durable mission kernel.

Deliberately tiny: reuses the W5-2 reconciliation queue's recovery pass and
presents the deterministic startup census.

Decision table (permanent):

    COMPLETED / FAILED / CANCELLED         → terminal, never execute again
    EXECUTING + durable OUTCOME            → reconstruct from durable outcome
    EXECUTING + INTENT + no OUTCOME        → RECONCILIATION_REQUIRED
    EXECUTION_INTENT_RECORDED (no contact) → safe deterministic recovery
    RECONCILIATION_REQUIRED                → restore queue entry, no auto-exec
    REQUESTED / AWAITING_APPROVAL / APPROVED → bookkeeping
                                             (authority must still be
                                              independently valid)

THE boundary:

    RESTARTED_STATE ≠ AUTHORITY

If a subsequent action is required, it routes again through the canonical
kernel (authority, approval, budget, capability gates).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mission_wiring.reconciliation import ReconciliationQueue

__all__ = ["RestartCensus", "restart_census"]


@dataclass
class RestartCensus:
    """Deterministic startup census (W5-1 kernel: no scheduler, no engine)."""

    terminal_missions: int = 0
    safe_resumable_missions: int = 0
    reconciliation_required: int = 0
    invalid_or_corrupt_records: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def restart_census(mission_manager: Any, queue: ReconciliationQueue | None = None) -> dict:
    """Classify every persisted mission after a restart.

    `mission_manager._records` is the durable store (W5-1 kernel — no
    scheduler). Corruption is counted, never silently dropped.
    """
    q = queue if queue is not None else ReconciliationQueue()
    return q.recover_after_restart(mission_manager)
