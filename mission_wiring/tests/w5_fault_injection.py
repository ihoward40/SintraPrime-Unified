"""W5-1 — durability fault-injection harness.

Crash points are FIRST-CLASS fixtures: the harness executes a mission flow
with a controlled crash at a precise step, then reconstructs from durable
records and classifies the post-crash world. This is the acceptance surface
for exactly-once/reconciliation semantics.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from mission_wiring.durable_mission import (
    DurableMissionError,
    DurableMissionManager,
    DurableMissionRecord,
    MissionLifecycleState,
    ReconciliationRequiredError,
)


class CrashInjector(Exception):
    """Simulated process crash at a named step."""


@dataclass
class FaultInjectionHarness:
    """Executes mission flows with crashes injected at precise boundaries.

    The 'durable store' is an in-memory record of exactly what survived the
    crash — writes listed in ``volatile_writes`` are lost, everything else
    persists (that's the fault-injection model: the durable record survives,
    in-process state does not).
    """

    durable: dict = field(default_factory=dict)   # mission_id -> persisted snapshot
    volatile_writes: set = field(default_factory=set)  # steps whose writes are LOST

    def save_mission_record(self, rec: DurableMissionRecord) -> None:
        if getattr(self, "_crash_arm", None) == "before_persist":
            raise CrashInjector(f"crash before persist ({self._crash_step})")
        self.durable[rec.mission_id] = _snapshot(rec)

    def start_mission(self, manager_kwargs: dict) -> DurableMissionManager:
        mgr = DurableMissionManager(self, clock=lambda: "T0")
        return mgr

    def arm_crash(self, step: str) -> None:
        self._crash_arm = "before_persist"
        self._crash_step = step

    def disarm(self) -> None:
        self._crash_arm = None
        self._crash_step = None

    def crash_now(self) -> None:
        """Simulate the process dying: volatile state is discarded; durable
        records survive."""
        self._crash_arm = None
        self._crash_step = None

    def reload_manager(self) -> DurableMissionManager:
        """RESTART: reconstruct the manager from durable records only."""
        mgr = DurableMissionManager(self, clock=lambda: "T1")
        for mid, snap in self.durable.items():
            rec = _restore(snap)
            mgr._records[mid] = rec
        return mgr


def _snapshot(rec: DurableMissionRecord) -> dict:
    return json.loads(json.dumps({
        "mission_id": rec.mission_id, "tenant_id": rec.tenant_id,
        "actor_id": rec.actor_id,
        "canonical_capability": rec.canonical_capability,
        "resource_identity": rec.resource_identity,
        "side_effect_class": rec.side_effect_class,
        "state": rec.state.value,
        "attempt_id": rec.attempt_id, "effect_id": rec.effect_id,
        "idempotency_key": rec.idempotency_key,
        "approval_reference": rec.approval_reference,
        "delegation_reference": rec.delegation_reference,
        "certification_generation": rec.certification_generation,
        "executor_binding_generation": rec.executor_binding_generation,
        "intent": rec.intent.__dict__ if rec.intent else None,
        "outcome": rec.outcome.__dict__ if rec.outcome else None,
        "reconciliation_status": rec.reconciliation_status,
        "history": rec.history,
    }))


def _restore(snap: dict) -> DurableMissionRecord:
    from mission_wiring.durable_mission import EffectIntent, EffectOutcome
    rec = DurableMissionRecord(
        mission_id=snap["mission_id"], tenant_id=snap["tenant_id"],
        actor_id=snap["actor_id"],
        canonical_capability=snap["canonical_capability"],
        resource_identity=snap["resource_identity"],
        side_effect_class=snap["side_effect_class"],
        state=MissionLifecycleState(snap["state"]),
        attempt_id=snap.get("attempt_id", ""),
        effect_id=snap.get("effect_id", ""),
        idempotency_key=snap.get("idempotency_key", ""),
        approval_reference=snap.get("approval_reference", ""),
        delegation_reference=snap.get("delegation_reference", ""),
        certification_generation=snap.get("certification_generation", ""),
        executor_binding_generation=snap.get("executor_binding_generation", ""),
        intent=EffectIntent(**snap["intent"]) if snap.get("intent") else None,
        outcome=EffectOutcome(**snap["outcome"]) if snap.get("outcome") else None,
        reconciliation_status=snap.get("reconciliation_status", ""),
        history=list(snap.get("history", [])),
    )
    return rec


# --------------------------------------------------------- standard fixtures --

def _approved_mission_kwargs() -> dict:
    return dict(
        mission_id="mission.w5-001", tenant_id="tenant.default",
        actor_id="agent.browser.worker",
        canonical_capability="computer.browser.navigate",
        resource_identity="https://example.com",
        side_effect_class="EXTERNAL_CONSEQUENTIAL",
    )


def make_approved_mission(mgr: DurableMissionManager) -> DurableMissionRecord:
    rec = mgr.request(**_approved_mission_kwargs())
    mgr.awaiting_approval(rec.mission_id)
    return mgr.approved(
        rec.mission_id,
        approval_reference="approval-w5-1",
        delegation_reference="deleg-w5-1",
        certification_generation="certgen-24fbaf3c8fa1a07d65cf310960e421bf",
        executor_binding_generation="ebg-44efb071ec7e",
    )
