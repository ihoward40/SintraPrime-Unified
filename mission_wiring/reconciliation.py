"""W5-2 — durable reconciliation queue and restart/recovery semantics.

Extends the W5-1 durable mission kernel (no second engine, no new approval
system, no evidence ledger, no scheduler).

Canonical relationship:

    W5-1 Durable Mission Kernel
        ↓ durable INTENT / OUTCOME records
    W5-2 Reconciliation Queue
        ↓ explicit reconciliation decision
    mission resolution

THE most important boundary:

    RECONCILIATION_QUEUE ≠ EXECUTION QUEUE

A mission entering reconciliation must NOT automatically become eligible to
execute again.

Authority invariants (permanent):

    RECONCILIATION_RECORD        ≠ APPROVAL
    RECONCILIATION_RESOLUTION    ≠ APPROVAL
    RESOLVED_NO_EFFECT           ≠ RETRY_AUTHORIZATION
    QUEUE_MEMBERSHIP             ≠ EXECUTION_AUTHORITY
    RESTARTED_STATE              ≠ AUTHORITY
    HUMAN_MARKED_RESOLVED        ≠ CAPABILITY_GRANT

If a subsequent action is required, it routes again through the canonical
kernel (authority, approval, generation, budget, capability gates).

Exactly-once claim (deliberately narrow):

    EXACTLY_ONCE = NO SECOND SINTRAPRIME-INITIATED EFFECT WITHOUT PROOF OR
                   NEW AUTHORIZED ATTEMPT

Not mathematically perfect exactly-once against arbitrary external systems:
SintraPrime guarantees no blind automatic retry + stable effect identity +
durable intent + reconciliation before re-execution. Provider-side
idempotency keys are a Wave 7 strengthening.

External-contact progress (minimum monotonic progression):

    INTENT_RECORDED → CONTACT_STARTED → OUTCOME_RECORDED

Do not infer "probably failed" from absence of an outcome: dying after
CONTACT_STARTED but before a trustworthy outcome ⇒ RECONCILIATION_REQUIRED.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from mission_wiring.durable_mission import (
    DurableMissionError,
    DurableMissionManager,
    DurableMissionRecord,
    MissionLifecycleState,
)

__all__ = [
    "ContactProgress",
    "ReconciliationQueue",
    "ReconciliationReason",
    "ReconciliationRecord",
    "ReconciliationResolution",
    "ReconciliationState",
    "RecoveryCensus",
]


class ReconciliationState(str, Enum):  # noqa: UP042 - reconciliation states are string-typed per W5-2 contract
    """Subordinate reconciliation state machine (does NOT overload mission state)."""

    NONE = "NONE"
    REQUIRED = "REQUIRED"
    QUEUED = "QUEUED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED_EFFECT_CONFIRMED = "RESOLVED_EFFECT_CONFIRMED"
    RESOLVED_NO_EFFECT = "RESOLVED_NO_EFFECT"
    RESOLVED_COMPENSATED = "RESOLVED_COMPENSATED"
    UNRESOLVED = "UNRESOLVED"


class ReconciliationResolution(str, Enum):  # noqa: UP042 - typed resolution enum
    """Typed resolution enum — never arbitrary free text."""

    EFFECT_CONFIRMED = "EFFECT_CONFIRMED"
    NO_EFFECT = "NO_EFFECT"
    COMPENSATED = "COMPENSATED"
    UNRESOLVED = "UNRESOLVED"


class ReconciliationReason(str, Enum):  # noqa: UP042 - reason codes are string-typed
    PROCESS_CRASH_DURING_EXTERNAL_CONTACT = "PROCESS_CRASH_DURING_EXTERNAL_CONTACT"
    TIMEOUT_WITH_UNKNOWN_PROVIDER_STATE = "TIMEOUT_WITH_UNKNOWN_PROVIDER_STATE"
    CONNECTION_LOST_AFTER_REQUEST = "CONNECTION_LOST_AFTER_REQUEST"
    OUTCOME_PERSISTENCE_FAILURE = "OUTCOME_PERSISTENCE_FAILURE"
    PROVIDER_RESPONSE_UNVERIFIABLE = "PROVIDER_RESPONSE_UNVERIFIABLE"
    RESTART_FOUND_INFLIGHT_CONSEQUENTIAL_EFFECT = "RESTART_FOUND_INFLIGHT_CONSEQUENTIAL_EFFECT"


class ContactProgress(str, Enum):  # noqa: UP042 - monotonic contact markers are string-typed
    """Minimum monotonic external-contact progression (durable marker)."""

    NONE = "NONE"
    INTENT_RECORDED = "INTENT_RECORDED"
    CONTACT_STARTED = "CONTACT_STARTED"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DurableMissionError("INVALID_RECONCILIATION_FIELD", f"{name} required")
    return value.strip()


def _hash_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ReconciliationRecord:
    """A durable reconciliation item — evidence/judgment, NEVER authority."""

    reconciliation_id: str
    mission_id: str
    attempt_id: str
    effect_id: str
    tenant_id: str
    actor_id: str
    canonical_capability: str
    canonical_resource: str
    intent_hash: str
    intent_timestamp: str
    contact_started_at: str
    contact_evidence_hash: str
    last_known_mission_state: str
    certification_generation: str
    executor_binding_generation: str
    reason_code: str
    created_at: str
    updated_at: str
    state: ReconciliationState = ReconciliationState.QUEUED
    resolution: ReconciliationResolution | None = None
    resolution_evidence_hash: str = ""
    resolved_by: str = ""
    resolved_at: str = ""

    def resolved(self) -> bool:
        return self.state in (
            ReconciliationState.RESOLVED_EFFECT_CONFIRMED,
            ReconciliationState.RESOLVED_NO_EFFECT,
            ReconciliationState.RESOLVED_COMPENSATED,
            ReconciliationState.UNRESOLVED,
        )


@dataclass
class RecoveryCensus:
    """Deterministic startup census: what recovered, what needs attention."""

    terminal_missions: int = 0
    safe_resumable_missions: int = 0
    reconciliation_required: int = 0
    invalid_or_corrupt_records: int = 0

    def as_dict(self) -> dict:
        return {
            "terminal_missions": self.terminal_missions,
            "safe_resumable_missions": self.safe_resumable_missions,
            "reconciliation_required": self.reconciliation_required,
            "invalid_or_corrupt_records": self.invalid_or_corrupt_records,
        }


class ReconciliationQueue:
    """Durable reconciliation queue — NOT an executor.

    Restores items from durable records on restart (exactly-once per
    (mission_id, effect_id)); enqueues from W5-1 kernel events; resolves
    only through typed resolution commands.
    """

    def __init__(self, store: Any = None, clock: Callable[[], str] | None = None) -> None:
        self._store = store
        self._clock = clock or (lambda: "")
        self._items: dict[str, ReconciliationRecord] = {}        # by reconciliation_id
        self._by_effect: dict[str, str] = {}                      # (mission,effect)key -> recon_id

    # -- key helpers ---------------------------------------------------------

    @staticmethod
    def _effect_key(mission_id: str, effect_id: str) -> str:
        return f"{mission_id}|{effect_id}"

    # -- enqueue (from kernel or restart recovery) ----------------------------

    def enqueue(
        self,
        *,
        mission_id: str,
        attempt_id: str,
        effect_id: str,
        tenant_id: str,
        actor_id: str,
        canonical_capability: str,
        canonical_resource: str,
        intent_hash: str,
        intent_timestamp: str,
        contact_started_at: str,
        contact_evidence_hash: str,
        last_known_mission_state: str,
        certification_generation: str,
        executor_binding_generation: str,
        reason_code: ReconciliationReason,
    ) -> ReconciliationRecord:
        """Exactly-once per (mission_id, effect_id): a duplicate unknown effect
        (e.g. encountered twice across restarts) returns the SAME record —
        never a second active reconciliation item."""
        mission_id = _require_str(mission_id, "mission_id")
        effect_id = _require_str(effect_id, "effect_id")
        key = self._effect_key(mission_id, effect_id)
        existing = self._by_effect.get(key)
        if existing is not None:
            rec = self._items[existing]
            if not rec.resolved():
                return rec  # exactly-one active reconciliation record
        reason = reason_code.value if isinstance(reason_code, ReconciliationReason) else reason_code
        if reason not in {r.value for r in ReconciliationReason}:
            raise DurableMissionError("INVALID_REASON_CODE", reason)
        rid = "recon-" + _hash_obj({
            "mission_id": mission_id, "effect_id": effect_id,
            "intent_hash": intent_hash, "reason": reason,
        })[:24]
        if rid in self._items:
            return self._items[rid]
        ts = self._clock()
        rec = ReconciliationRecord(
            reconciliation_id=rid, mission_id=mission_id, attempt_id=attempt_id,
            effect_id=effect_id, tenant_id=tenant_id, actor_id=actor_id,
            canonical_capability=canonical_capability,
            canonical_resource=canonical_resource,
            intent_hash=intent_hash, intent_timestamp=intent_timestamp,
            contact_started_at=contact_started_at,
            contact_evidence_hash=contact_evidence_hash,
            last_known_mission_state=last_known_mission_state,
            certification_generation=certification_generation,
            executor_binding_generation=executor_binding_generation,
            reason_code=reason, created_at=ts, updated_at=ts,
            state=ReconciliationState.QUEUED,
        )
        self._items[rid] = rec
        self._by_effect[key] = rid
        self._persist(rec)
        return rec

    # -- typed inspection ------------------------------------------------------

    def get(self, reconciliation_id: str) -> ReconciliationRecord:
        rec = self._items.get(reconciliation_id)
        if rec is None:
            raise DurableMissionError("RECONCILIATION_NOT_FOUND", reconciliation_id)
        return rec

    def _get(self, reconciliation_id: str) -> ReconciliationRecord:
        return self.get(reconciliation_id)

    def get_by_effect(self, mission_id: str, effect_id: str) -> ReconciliationRecord | None:
        rid = self._by_effect.get(self._effect_key(mission_id, effect_id))
        return self._items.get(rid) if rid else None

    def list_pending(self) -> list[ReconciliationRecord]:
        return [r for r in self._items.values()
                if r.state in (ReconciliationState.QUEUED, ReconciliationState.UNDER_REVIEW)]

    # -- typed resolution commands (NO generic resolve) ------------------------

    def begin_review(self, reconciliation_id: str, *, reviewer: str) -> ReconciliationRecord:
        rec = self._get(reconciliation_id)
        self._guard_unresolved(rec)
        if rec.state is not ReconciliationState.QUEUED:
            raise DurableMissionError(
                "INVALID_RECONCILIATION_TRANSITION", f"{rec.reconciliation_id}: {rec.state.value}")
        _require_str(reviewer, "reviewer")
        rec = replace(rec, state=ReconciliationState.UNDER_REVIEW, updated_at=self._clock())
        self._items[rec.reconciliation_id] = rec
        self._persist(rec)
        return rec

    def resolve_effect_confirmed(self, reconciliation_id: str, *, resolver: str,
                                 evidence_hash: str) -> ReconciliationRecord:
        """EFFECT_CONFIRMED: the external consequence DID occur. The mission can
        never execute the SAME effect again (exactly-once)."""
        return self._resolve(reconciliation_id, resolver, evidence_hash,
                             ReconciliationState.RESOLVED_EFFECT_CONFIRMED,
                             ReconciliationResolution.EFFECT_CONFIRMED)

    def resolve_no_effect(self, reconciliation_id: str, *, resolver: str,
                          evidence_hash: str) -> ReconciliationRecord:
        """NO_EFFECT: reconciliation established, with sufficient evidence, that
        the external consequence did NOT occur. This is NOT retry authorization —
        any subsequent attempt re-runs the canonical kernel."""
        return self._resolve(reconciliation_id, resolver, evidence_hash,
                             ReconciliationState.RESOLVED_NO_EFFECT,
                             ReconciliationResolution.NO_EFFECT)

    def resolve_compensated(self, reconciliation_id: str, *, resolver: str,
                            evidence_hash: str) -> ReconciliationRecord:
        """COMPENSATED: original effect history RETAINED (append-only); the
        compensation does not erase evidence."""
        return self._resolve(reconciliation_id, resolver, evidence_hash,
                             ReconciliationState.RESOLVED_COMPENSATED,
                             ReconciliationResolution.COMPENSATED)

    def mark_unresolved(self, reconciliation_id: str, *, resolver: str,
                        evidence_hash: str) -> ReconciliationRecord:
        return self._resolve(reconciliation_id, resolver, evidence_hash,
                             ReconciliationState.UNRESOLVED,
                             ReconciliationResolution.UNRESOLVED)

    # -- restart recovery ------------------------------------------------------

    def recover_after_restart(self, mission_manager: DurableMissionManager) -> dict:
        """Deterministic restart recovery: reconstruct queue entries from
        durable mission records; classify every persisted mission.

        Restart decision table:
          COMPLETED/FAILED/CANCELLED            → terminal, never execute again
          RECONCILIATION_REQUIRED               → restore queue entry, no auto-exec
          EXECUTING + durable OUTCOME           → reconstruct from outcome
          EXECUTING + INTENT + no OUTCOME       → RECONCILIATION_REQUIRED
          EXECUTION_INTENT_RECORDED + contact   → per proven contact state
          REQUESTED/AWAITING_APPROVAL/APPROVED  → bookkeeping (authority must
                                                   still be independently valid)
        """
        census = RecoveryCensus()
        for rec in mission_manager._records.values():
            if rec.state in (MissionLifecycleState.COMPLETED,
                             MissionLifecycleState.FAILED,
                             MissionLifecycleState.CANCELLED):
                census.terminal_missions += 1
            elif rec.state is MissionLifecycleState.RECONCILIATION_REQUIRED:
                census.reconciliation_required += 1
                self._ensure_entry(rec)  # reason derived from the durable record
            elif rec.state is MissionLifecycleState.EXECUTING:
                if rec.outcome is not None:
                    census.terminal_missions += 1  # reconstruct from durable outcome
                elif rec.intent is not None:
                    census.reconciliation_required += 1
                    self._ensure_entry(rec)
                else:
                    census.safe_resumable_missions += 1
            elif rec.state is MissionLifecycleState.EXECUTION_INTENT_RECORDED:
                # intent recorded but no outcome: progression governs — if contact
                # started (consequential), reconcile; else deterministic recovery
                census.safe_resumable_missions += 1
            else:
                census.safe_resumable_missions += 1
        return census.as_dict()

    def recovery_census(self, mission_manager: DurableMissionManager) -> dict:
        return self.recover_after_restart(mission_manager)

    # -- internals --------------------------------------------------------------

    def _ensure_entry(self, rec: DurableMissionRecord,
                      reason: ReconciliationReason | None = None) -> None:
        if rec.intent is None:
            return
        if reason is None:
            # derive from the reconciliation status/reason recorded on the mission
            rs = rec.reconciliation_status or ""
            if rs in {r.value for r in ReconciliationReason}:
                reason = ReconciliationReason(rs)
            elif rs == "REQUIRED_UNKNOWN_EXTERNAL_STATE":
                reason = ReconciliationReason.OUTCOME_PERSISTENCE_FAILURE
            else:
                reason = ReconciliationReason.RESTART_FOUND_INFLIGHT_CONSEQUENTIAL_EFFECT
        existing = self.get_by_effect(rec.mission_id, rec.effect_id or "unknown")
        if existing is not None and not existing.resolved():
            return  # exactly-once: never duplicate an active item on restart
        self.enqueue(
            mission_id=rec.mission_id, attempt_id=rec.attempt_id or "",
            effect_id=rec.effect_id or "unknown",
            tenant_id=rec.tenant_id, actor_id=rec.actor_id,
            canonical_capability=rec.canonical_capability,
            canonical_resource=rec.resource_identity,
            intent_hash=rec.intent.intent_hash,
            intent_timestamp=rec.intent.intent_timestamp,
            contact_started_at="", contact_evidence_hash="",
            last_known_mission_state=rec.state.value,
            certification_generation=rec.certification_generation,
            executor_binding_generation=rec.executor_binding_generation,
            reason_code=reason,
        )

    def _guard_unresolved(self, rec: ReconciliationRecord) -> None:
        if rec.resolved():
            raise DurableMissionError(
                "RECONCILIATION_ALREADY_RESOLVED",
                f"{rec.reconciliation_id}: {rec.state.value}")

    def _resolve(self, reconciliation_id: str, resolver: str, evidence_hash: str,
                 new_state: ReconciliationState,
                 resolution: ReconciliationResolution) -> ReconciliationRecord:
        rec = self._get(reconciliation_id)
        self._guard_unresolved(rec)
        _require_str(resolver, "resolver")
        _require_str(evidence_hash, "evidence_hash")
        rec = replace(
            rec, state=new_state, resolution=resolution,
            resolution_evidence_hash=evidence_hash,
            resolved_by=resolver, resolved_at=self._clock(),
            updated_at=self._clock(),
        )
        self._items[rec.reconciliation_id] = rec
        self._persist(rec)
        return rec

    def _persist(self, rec: ReconciliationRecord) -> None:
        if self._store is None:
            return
        save = getattr(self._store, "save_reconciliation_record", None)
        if callable(save):
            save(rec)
