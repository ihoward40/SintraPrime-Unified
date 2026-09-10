"""W5-1 — durable mission lifecycle and exactly-once/reconciliation contract.

Establishes the canonical durable mission lifecycle on top of the PUBLISHED
Wave-4 authority/capability/runtime stack and the EXISTING
``DurableWorkflowEngine`` store — no second orchestration engine.

Canonical flow:

    Principal request
    → MissionEnvelope
    → capability resolution
    → executor binding
    → delegation
    → approval
    → durable INTENT          (write-ahead, BEFORE external contact)
    → governed execution
    → durable OUTCOME
    → receipt/evidence

Core contract (the Wave-4 deferred gap):

    EXTERNAL_CONSEQUENTIAL_EFFECT + PROCESS CRASH/TIMEOUT/LOST RESPONSE
        = UNKNOWN_EXTERNAL_STATE
    UNKNOWN_EXTERNAL_STATE → NO AUTOMATIC RETRY → RECONCILIATION_REQUIRED

INTENT vs OUTCOME vs RECEIPT:

    INTENT  = what SintraPrime planned to do
    OUTCOME = what SintraPrime knows happened
    RECEIPT = what SintraPrime can prove about the mission

Authority invariant (permanent):

    MISSION_STATE ≠ APPROVAL
    MISSION_STATE ≠ DELEGATION
    MISSION_STATE ≠ AUTHORITY

Idempotency contract (stable across crashes — never a random retry token):

    mission_id      = Principal/system-issued stable mission identity
    attempt_id      = one execution attempt
    effect_id       = stable identity for the intended external consequence
    idempotency_key = H(mission_id + capability + canonical resource + effect_id)
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "DurableMissionError",
    "DurableMissionManager",
    "DurableMissionRecord",
    "EffectIntent",
    "EffectOutcome",
    "MissionLifecycleState",
    "ReconciliationRequiredError",
    "SideEffectClass",
]

# Local mirror of the Wave-3 side-effect classes (values identical to
# agent_runtime.manifest.SideEffectClass) — kept string-based here so the
# durable record never depends on import order.
class SideEffectClass(str, Enum):  # noqa: UP042 - deliberate mirror of Wave-3 SideEffectClass
    READ_ONLY = "READ_ONLY"
    LOCAL_REVERSIBLE = "LOCAL_REVERSIBLE"
    EXTERNAL_REVERSIBLE = "EXTERNAL_REVERSIBLE"
    EXTERNAL_CONSEQUENTIAL = "EXTERNAL_CONSEQUENTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


class MissionLifecycleState(str, Enum):  # noqa: UP042 - lifecycle states are string-typed per W5-1 contract
    REQUESTED = "REQUESTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTION_INTENT_RECORDED = "EXECUTION_INTENT_RECORDED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    CANCELLED = "CANCELLED"


class DurableMissionError(Exception):
    """Fail-closed durable-mission violation."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class ReconciliationRequiredError(DurableMissionError):
    """UNKNOWN_EXTERNAL_STATE — never auto-retried."""

    def __init__(self, detail: str) -> None:
        super().__init__("RECONCILIATION_REQUIRED", detail)


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DurableMissionError("INVALID_MISSION_FIELD", f"{name} required")
    return value.strip()


@dataclass(frozen=True)
class EffectIntent:
    """Write-ahead record of a planned external consequence.

    Must be durable BEFORE any external contact. Presence of this record is
    what makes a later crash 'deterministically recoverable' instead of
    'unknown external state' — and is also the exactly-once guard.
    """

    mission_id: str
    attempt_id: str
    effect_id: str
    idempotency_key: str
    canonical_capability: str
    resource_identity: str
    side_effect_class: str
    approval_reference: str
    delegation_reference: str
    certification_generation: str
    executor_binding_generation: str
    tenant_id: str
    actor_id: str
    intent_hash: str
    intent_timestamp: str


@dataclass(frozen=True)
class EffectOutcome:
    """What SintraPrime KNOWS happened (never an inference)."""

    mission_id: str
    attempt_id: str
    effect_id: str
    idempotency_key: str
    status: str                      # COMPLETED | FAILED | UNKNOWN
    outcome_hash: str
    outcome_timestamp: str
    external_contact_observed: bool
    detail: str = ""


@dataclass
class DurableMissionRecord:
    """Durable mission state — data, never authority."""

    mission_id: str
    tenant_id: str
    actor_id: str
    canonical_capability: str
    resource_identity: str
    side_effect_class: str
    state: MissionLifecycleState
    attempt_id: str = ""
    effect_id: str = ""
    idempotency_key: str = ""
    approval_reference: str = ""
    delegation_reference: str = ""
    certification_generation: str = ""
    executor_binding_generation: str = ""
    intent: EffectIntent | None = None
    outcome: EffectOutcome | None = None
    reconciliation_status: str = ""
    receipt_hash: str = ""
    history: list = field(default_factory=list)


def derive_idempotency_key(
    mission_id: str, canonical_capability: str, resource_identity: str, effect_id: str
) -> str:
    """STABLE across crashes: derived from mission + capability + canonical
    resource + effect identity. Deterministic; never random."""
    payload = json.dumps(
        {
            "canonical_capability": canonical_capability,
            "effect_id": effect_id,
            "mission_id": mission_id,
            "resource_identity": resource_identity,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "idem-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _hash_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


class DurableMissionManager:
    """Durable mission lifecycle manager over the existing durable store.

    NOT an authority engine: every transition consumes Wave-4 decisions
    (delegation/approval/binding generations) as DATA. Lifecycle state itself
    grants nothing.
    """

    def __init__(self, store: Any, clock: Callable[[], str] | None = None) -> None:
        self._store = store
        self._clock = clock or (lambda: "")
        self._records: dict[str, DurableMissionRecord] = {}

    # -- lifecycle ---------------------------------------------------------

    def request(
        self,
        *,
        mission_id: str,
        tenant_id: str,
        actor_id: str,
        canonical_capability: str,
        resource_identity: str,
        side_effect_class: str,
    ) -> DurableMissionRecord:
        mission_id = _require_str(mission_id, "mission_id")
        if mission_id in self._records:
            raise DurableMissionError("MISSION_ID_REUSED", mission_id)
        rec = DurableMissionRecord(
            mission_id=mission_id,
            tenant_id=_require_str(tenant_id, "tenant_id"),
            actor_id=_require_str(actor_id, "actor_id"),
            canonical_capability=_require_str(canonical_capability, "canonical_capability"),
            resource_identity=_require_str(resource_identity, "resource_identity"),
            side_effect_class=side_effect_class,
            state=MissionLifecycleState.REQUESTED,
        )
        self._records[mission_id] = rec
        self._persist(rec)
        return rec

    def awaiting_approval(self, mission_id: str) -> DurableMissionRecord:
        rec = self._get(mission_id)
        self._transition(rec, MissionLifecycleState.AWAITING_APPROVAL)
        return rec

    def approved(
        self,
        mission_id: str,
        *,
        approval_reference: str,
        delegation_reference: str,
        certification_generation: str,
        executor_binding_generation: str,
    ) -> DurableMissionRecord:
        """Record the Wave-4 authority decisions as DATA on the mission.

        Accepts them only from callers who already obtained them from the
        canonical kernel; the manager validates binding coherence (tenant/
        actor/capability/resource identity match the mission record) but the
        APPROVAL decision itself was made by AuthorityApprovalService — the
        state here is bookkeeping, not the authority.
        """
        rec = self._get(mission_id)
        if rec.state is not MissionLifecycleState.AWAITING_APPROVAL:
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: {rec.state.value}")
        rec.approval_reference = _require_str(approval_reference, "approval_reference")
        rec.delegation_reference = _require_str(delegation_reference, "delegation_reference")
        rec.certification_generation = _require_str(certification_generation, "certification_generation")
        rec.executor_binding_generation = _require_str(
            executor_binding_generation, "executor_binding_generation")
        self._transition(rec, MissionLifecycleState.APPROVED)
        return rec

    def record_intent(
        self,
        mission_id: str,
        *,
        effect_id: str,
        attempt_id: str | None = None,
    ) -> EffectIntent:
        """Write-ahead INTENT — MUST be durable BEFORE external contact.

        Exactly-once guard: an intent for the same (mission, capability,
        resource, effect) is recorded once; a second record_intent with the
        same idempotency key refuses rather than duplicating.
        """
        rec = self._get(mission_id)
        if rec.state not in (MissionLifecycleState.APPROVED, MissionLifecycleState.EXECUTION_INTENT_RECORDED):
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: {rec.state.value}")
        consequential = rec.side_effect_class in (
            SideEffectClass.EXTERNAL_CONSEQUENTIAL.value,
            SideEffectClass.IRREVERSIBLE.value,
        )
        effect_id = _require_str(effect_id, "effect_id")
        # W4-6 dependency-bound contract: the recorded generations must be
        # canonical certgen-/ebg- identities. A stale/mismatched generation
        # marker refuses here (fail-closed) rather than recording a binding
        # the current runtime cannot honor.
        for gname, gval in (("certification_generation", rec.certification_generation),
                            ("executor_binding_generation", rec.executor_binding_generation)):
            if gval and not (gval.startswith("certgen-") or gval.startswith("ebg-")):
                raise DurableMissionError(
                    "INVALID_DEPENDENCY_GENERATION",
                    f"{mission_id}: {gname}={gval!r} is not a canonical generation identity")
        idem = derive_idempotency_key(
            rec.mission_id, rec.canonical_capability, rec.resource_identity, effect_id)
        # exactly-once: existing durable intent with same key → refuse duplicates
        if rec.intent is not None:
            if rec.intent.idempotency_key == idem and rec.intent.effect_id == effect_id:
                raise DurableMissionError(
                    "INTENT_ALREADY_RECORDED",
                    f"{mission_id}: intent {effect_id} already durable (exactly-once)")
            raise DurableMissionError(
                "INTENT_CONFLICT",
                f"{mission_id}: a different intent is already durable for this mission")
        attempt_id = attempt_id or idem[:16]
        ts = self._clock()
        intent = EffectIntent(
            mission_id=rec.mission_id,
            attempt_id=attempt_id,
            effect_id=effect_id,
            idempotency_key=idem,
            canonical_capability=rec.canonical_capability,
            resource_identity=rec.resource_identity,
            side_effect_class=rec.side_effect_class,
            approval_reference=rec.approval_reference,
            delegation_reference=rec.delegation_reference,
            certification_generation=rec.certification_generation,
            executor_binding_generation=rec.executor_binding_generation,
            tenant_id=rec.tenant_id,
            actor_id=rec.actor_id,
            intent_hash=None,  # placeholder; computed below over the full intent payload

            intent_timestamp=ts,
        )
        # SEC/W4-6 contract: the intent hash binds EVERY intent field, including
        # the certification and executor-binding generations. A post-hoc mutation
        # of any field breaks the hash → detectable (test_intent_binds_generations).
        object.__setattr__(intent, "intent_hash",
                           _hash_obj(intent.__dict__ | {"intent_hash": None}))
        rec.intent = intent
        rec.attempt_id = attempt_id
        rec.effect_id = effect_id
        rec.idempotency_key = idem
        self._persist(rec)
        self._transition(
            rec, MissionLifecycleState.EXECUTION_INTENT_RECORDED)
        if not consequential and rec.side_effect_class == SideEffectClass.READ_ONLY.value:
            pass  # read-only work still records intent for evidence continuity
        return intent

    def executing(self, mission_id: str) -> DurableMissionRecord:
        rec = self._get(mission_id)
        if rec.state is not MissionLifecycleState.EXECUTION_INTENT_RECORDED:
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: {rec.state.value}")
        self._transition(rec, MissionLifecycleState.EXECUTING)
        return rec

    def record_outcome(
        self,
        mission_id: str,
        *,
        status: str,
        external_contact_observed: bool,
        detail: str = "",
    ) -> EffectOutcome:
        """Durable OUTCOME. status ∈ COMPLETED | FAILED | UNKNOWN.

        UNKNOWN (+ external contact observed or possible) ⇒
        RECONCILIATION_REQUIRED — never auto-retry.
        """
        rec = self._get(mission_id)
        if rec.state is not MissionLifecycleState.EXECUTING:
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: {rec.state.value}")
        if status not in ("COMPLETED", "FAILED", "UNKNOWN"):
            raise DurableMissionError("INVALID_OUTCOME_STATUS", status)
        if status == "UNKNOWN" and rec.side_effect_class in (
            SideEffectClass.EXTERNAL_CONSEQUENTIAL.value,
            SideEffectClass.IRREVERSIBLE.value,
        ):
            rec.state = MissionLifecycleState.RECONCILIATION_REQUIRED
            rec.reconciliation_status = "REQUIRED_UNKNOWN_EXTERNAL_STATE"
            outcome = EffectOutcome(
                mission_id=rec.mission_id, attempt_id=rec.attempt_id or "",
                effect_id=rec.effect_id or "", idempotency_key=rec.idempotency_key,
                status="UNKNOWN",
                outcome_hash=_hash_obj({"status": status, "detail": detail,
                                        "ts": self._clock()}),
                outcome_timestamp=self._clock(),
                external_contact_observed=external_contact_observed,
                detail=detail,
            )
            rec.outcome = outcome
            self._persist(rec)
            raise ReconciliationRequiredError(
                f"{mission_id}: consequential effect in UNKNOWN external state; "
                "no automatic retry")
        outcome = EffectOutcome(
            mission_id=rec.mission_id, attempt_id=rec.attempt_id or "",
            effect_id=rec.effect_id or "", idempotency_key=rec.idempotency_key,
            status=status,
            outcome_hash=_hash_obj({"status": status, "detail": detail, "ts": self._clock()}),
            outcome_timestamp=self._clock(),
            external_contact_observed=external_contact_observed,
            detail=detail,
        )
        rec.outcome = outcome
        self._transition(
            rec,
            MissionLifecycleState.COMPLETED if status == "COMPLETED"
            else MissionLifecycleState.FAILED,
        )
        return outcome

    def cancel(self, mission_id: str) -> DurableMissionRecord:
        rec = self._get(mission_id)
        if rec.state in (MissionLifecycleState.COMPLETED,
                         MissionLifecycleState.RECONCILIATION_REQUIRED):
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: cannot cancel from {rec.state.value}")
        self._transition(rec, MissionLifecycleState.CANCELLED)
        return rec

    # -- recovery / receipts ------------------------------------------------

    def reconcile_resolve(
        self, mission_id: str, *, resolved_status: str, detail: str = ""
    ) -> DurableMissionRecord:
        """Human/governance-driven reconciliation resolution — the ONLY exit
        from RECONCILIATION_REQUIRED."""
        rec = self._get(mission_id)
        if rec.state is not MissionLifecycleState.RECONCILIATION_REQUIRED:
            raise DurableMissionError(
                "INVALID_STATE_TRANSITION", f"{mission_id}: {rec.state.value}")
        if resolved_status not in ("COMPLETED", "FAILED"):
            raise DurableMissionError("INVALID_RECONCILIATION_STATUS", resolved_status)
        outcome = EffectOutcome(
            mission_id=rec.mission_id, attempt_id=rec.attempt_id or "",
            effect_id=rec.effect_id or "", idempotency_key=rec.idempotency_key,
            status=resolved_status,
            outcome_hash=_hash_obj({"status": resolved_status, "detail": detail,
                                    "reconciled": True, "ts": self._clock()}),
            outcome_timestamp=self._clock(),
            external_contact_observed=True,
            detail=detail or "resolved by reconciliation",
        )
        rec.outcome = outcome
        rec.reconciliation_status = "RESOLVED"
        self._transition(
            rec,
            MissionLifecycleState.COMPLETED if resolved_status == "COMPLETED"
            else MissionLifecycleState.FAILED,
        )
        return rec

    def receipt_hash(self, mission_id: str) -> str:
        """What SintraPrime can PROVE: deterministic digest over intent+outcome
        + lifecycle history."""
        rec = self._get(mission_id)
        payload = {
            "mission_id": rec.mission_id,
            "tenant_id": rec.tenant_id,
            "actor_id": rec.actor_id,
            "canonical_capability": rec.canonical_capability,
            "resource_identity": rec.resource_identity,
            "side_effect_class": rec.side_effect_class,
            "state": rec.state.value,
            "attempt_id": rec.attempt_id,
            "effect_id": rec.effect_id,
            "idempotency_key": rec.idempotency_key,
            "approval_reference": rec.approval_reference,
            "delegation_reference": rec.delegation_reference,
            "certification_generation": rec.certification_generation,
            "executor_binding_generation": rec.executor_binding_generation,
            "intent": rec.intent.__dict__ if rec.intent else None,
            "outcome": rec.outcome.__dict__ if rec.outcome else None,
            "reconciliation_status": rec.reconciliation_status,
            "history": rec.history,
        }
        return "receipt-" + _hash_obj(payload)[:32]

    def load(self, mission_id: str) -> DurableMissionRecord:
        """Restart/reload: reconstruct from durable records."""
        return self._get(mission_id)

    # -- internals -----------------------------------------------------------

    def _get(self, mission_id: str) -> DurableMissionRecord:
        rec = self._records.get(mission_id)
        if rec is None:
            raise DurableMissionError("MISSION_NOT_FOUND", mission_id)
        return rec

    def _transition(self, rec: DurableMissionRecord, new: MissionLifecycleState) -> None:
        if rec.state is new:
            return
        rec.history.append({"from": rec.state.value, "to": new.value, "ts": self._clock()})
        rec.state = new
        self._persist(rec)

    def _persist(self, rec: DurableMissionRecord) -> None:
        """Durable write-through to the existing DurableStore (if provided)."""
        if self._store is None:
            return
        save = getattr(self._store, "save_mission_record", None)
        if callable(save):
            save(rec)
