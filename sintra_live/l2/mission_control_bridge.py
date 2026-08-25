"""Thin adapter bridging agentos Mission Control to the canonical L2 mission store.

This bridge lets agentos use the L2 ``MissionStore`` as the system of record
without duplicating or modifying the L2 state machine.  All state transitions
are delegated to the L2 store via ``MissionStore.transition`` / ``MissionStore.cancel``.

The adapter exposes an agentos-style interface (``start``, ``update``,
``complete``, ``cancel``) while internally mapping to the L2
``TransitionRequest`` / ``MissionStore`` API.

Design rules (P3):
  * The L2 store is the **only** state machine.  This bridge owns no
    transition logic of its own.
  * The L2 store is never modified — only called.
  * If a requested transition is not enabled in the current L2 policy,
    the L2 store denies it and the bridge surfaces the denial faithfully.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from sintra_live.l2.mission import (
    MissionIdentity,
    MissionScope,
    MissionState as L2MissionState,
    MissionStore,
    TransitionOutcome,
    TransitionRequest,
    TransitionResult,
    utc_now,
)
from sintra_live.l2.mission.errors import MissionStoreError

# Sentinel hash for payloads that carry no discrete evidence blob.
_EMPTY_EVIDENCE_SHA256 = hashlib.sha256(b"").hexdigest()
_DEFAULT_ACTOR = "agentos-bridge"
_DEFAULT_CANCELLATION_AUTHORITY = "agentos-bridge"

__all__ = [
    "MissionControlBridge",
    "BridgeStartRequest",
    "BridgeTransitionResult",
]


@dataclass(frozen=True)
class BridgeStartRequest:
    """Agentos-style parameters describing a mission to start.

    Fields mirror the subset of the L2 ``MissionScope`` / ``MissionIdentity``
    inputs that an agentos caller can meaningfully supply.  Anything omitted
    is filled in with safe defaults by the bridge.
    """

    purpose: str
    principal_reference: str
    mission_id: Optional[str] = None
    program_id: str = "SP-LIVE-001"
    gate_id: str = "L2-I1"
    request_id: Optional[str] = None
    request_sha256: Optional[str] = None
    mission_scope_sha256: Optional[str] = None
    authority_snapshot_reference: str = "agentos-default-authority"
    allowed_operations: Tuple[str, ...] = ("mission.read", "mission.transition")
    prohibited_operations: Tuple[str, ...] = ("external.write", "provider.call")
    consequence_ceiling: str = "E0"
    budget_ceilings: Tuple[Tuple[str, int], ...] = (("tokens", 0),)
    required_evidence_types: Tuple[str, ...] = ("transition",)
    expiry: str = "2030-01-01T00:00:00.000000Z"
    cancellation_authority: str = _DEFAULT_CANCELLATION_AUTHORITY
    actor_reference: str = _DEFAULT_ACTOR
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BridgeTransitionResult:
    """Agentos-friendly view of an L2 ``TransitionResult``."""

    mission_id: str
    applied: bool
    replayed: bool
    denied: bool
    state: str
    version: int
    reason: str
    raw: TransitionResult


def _coerce_sha256(value: Optional[str], seed: bytes) -> str:
    if value:
        return value
    return hashlib.sha256(seed).hexdigest()


class MissionControlBridge:
    """Bridge adapter wrapping the L2 ``MissionStore``.

    Exposes four agentos-style operations:

      * ``start(request)``  — creates a mission in the L2 store (genesis).
      * ``update(mission_id, to_state, reason, ...)`` — transitions to the
        next enabled L2 state.
      * ``complete(mission_id, ...)``  — attempts the transition(s) toward
        ``COMPLETE``; delegates to the L2 store which enforces the enabled
        subset.
      * ``cancel(mission_id, ...)``  — delegates to ``MissionStore.cancel``.

    The bridge performs **no** state-machine logic.  Every state change is
    a ``TransitionRequest`` evaluated by the L2 store's CAS + I1 policy.
    """

    def __init__(self, store_root: Path | str, *, lock_timeout_ms: int = 5000):
        self._store = MissionStore(store_root, lock_timeout_ms=lock_timeout_ms)

    # ------------------------------------------------------------------
    # L2 store passthrough (read-only)
    # ------------------------------------------------------------------

    @property
    def store(self) -> MissionStore:
        """The underlying L2 store (read access for inspection/tests)."""
        return self._store

    def load(self, mission_id: str):
        """Return the current L2 mission aggregate."""
        return self._store.load(mission_id)

    def project_p5(self, mission_id: str, *, memory_receipt: Any, model_receipt: Any):
        """Project P5 state from the exact canonical L2 aggregate and sealed receipts."""
        from .p5_memory_model_gateway import P5MissionProjection

        return P5MissionProjection.from_receipts(
            self._store.load(mission_id),
            memory=memory_receipt,
            model=model_receipt,
        )

    # ------------------------------------------------------------------
    # Agentos-style interface
    # ------------------------------------------------------------------

    def start(self, request: BridgeStartRequest) -> BridgeTransitionResult:
        """Create a mission in the L2 store (genesis aggregate)."""
        mission_id = request.mission_id or f"agentos-{uuid.uuid4().hex[:12]}"
        request_id = request.request_id or f"req-{uuid.uuid4().hex[:8]}"
        request_sha256 = _coerce_sha256(
            request.request_sha256, f"{mission_id}:{request_id}".encode()
        )
        scope_sha256 = _coerce_sha256(
            request.mission_scope_sha256, request.purpose.encode()
        )

        identity = MissionIdentity(
            program_id=request.program_id,
            gate_id=request.gate_id,
            mission_id=mission_id,
            request_id=request_id,
            request_sha256=request_sha256,
            principal_identity_reference=request.principal_reference,
            mission_scope_sha256=scope_sha256,
            authority_snapshot_reference=request.authority_snapshot_reference,
        )

        scope = MissionScope(
            purpose=request.purpose,
            allowed_operations=request.allowed_operations,
            prohibited_operations=request.prohibited_operations,
            consequence_ceiling=request.consequence_ceiling,
            budget_ceilings=request.budget_ceilings,
            side_effect_budget=0,
            required_evidence_types=request.required_evidence_types,
            expiry=request.expiry,
            cancellation_authority=request.cancellation_authority,
        )

        created_at = utc_now()
        aggregate = self._store.create(identity, scope, created_at=created_at)
        return BridgeTransitionResult(
            mission_id=mission_id,
            applied=True,
            replayed=False,
            denied=False,
            state=aggregate.current_state.value,
            version=aggregate.version,
            reason="mission created (genesis)",
            raw=TransitionResult(
                TransitionOutcome.APPLIED,
                mission_id,
                None,
                "genesis",
                aggregate.version,
                aggregate.current_state.value,
                aggregate.previous_event_sha256,
                aggregate.aggregate_sha256,
                {"genesis": True},
            ),
        )

    def update(
        self,
        mission_id: str,
        to_state: L2MissionState,
        *,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        actor_reference: str = _DEFAULT_ACTOR,
        evidence_sha256: Optional[str] = None,
        cancellation_authority_reference: Optional[str] = None,
    ) -> BridgeTransitionResult:
        """Transition a mission to ``to_state`` via the L2 store.

        The L2 store enforces CAS, idempotency, and the I1 enabled-transition
        subset.  This method owns no transition logic.
        """
        req = self._build_request(
            mission_id,
            to_state,
            reason=reason or f"agentos update -> {to_state.value}",
            idempotency_key=idempotency_key,
            actor_reference=actor_reference,
            evidence_sha256=evidence_sha256,
            cancellation_authority_reference=cancellation_authority_reference,
        )
        result = self._store.transition(req)
        return self._wrap(mission_id, result)

    def complete(
        self,
        mission_id: str,
        *,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        actor_reference: str = _DEFAULT_ACTOR,
        evidence_sha256: Optional[str] = None,
    ) -> BridgeTransitionResult:
        """Attempt to transition the mission toward ``COMPLETE``.

        The L2 store decides whether ``COMPLETE`` (or any intermediate) is
        reachable from the current state under the enabled I1 policy.  The
        bridge issues a single ``TransitionRequest`` to ``COMPLETE`` and
        faithfully reports the L2 store's decision.
        """
        return self.update(
            mission_id,
            L2MissionState.COMPLETE,
            reason=reason or "agentos complete",
            idempotency_key=idempotency_key,
            actor_reference=actor_reference,
            evidence_sha256=evidence_sha256,
        )

    def cancel(
        self,
        mission_id: str,
        *,
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        actor_reference: str = _DEFAULT_ACTOR,
        cancellation_authority_reference: Optional[str] = None,
    ) -> BridgeTransitionResult:
        """Cancel a mission via ``MissionStore.cancel``."""
        aggregate = self._store.load(mission_id)
        authority_ref = (
            cancellation_authority_reference
            or aggregate.scope.cancellation_authority
        )
        req = self._build_request(
            mission_id,
            L2MissionState.CANCELLED,
            reason=reason or "agentos cancel",
            idempotency_key=idempotency_key,
            actor_reference=actor_reference,
            evidence_sha256=None,
            cancellation_authority_reference=authority_ref,
        )
        result = self._store.cancel(req)
        return self._wrap(mission_id, result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_request(
        self,
        mission_id: str,
        to_state: L2MissionState,
        *,
        reason: str,
        idempotency_key: Optional[str],
        actor_reference: str,
        evidence_sha256: Optional[str],
        cancellation_authority_reference: Optional[str],
    ) -> TransitionRequest:
        aggregate = self._store.load(mission_id)
        key = idempotency_key or f"agentos-{uuid.uuid4().hex[:12]}"
        evidence = evidence_sha256 or _EMPTY_EVIDENCE_SHA256
        return TransitionRequest(
            mission_id=mission_id,
            idempotency_key=key,
            expected_version=aggregate.version,
            expected_state=aggregate.current_state,
            expected_previous_event_sha256=aggregate.previous_event_sha256,
            to_state=to_state,
            reason=reason,
            evidence_sha256=evidence,
            actor_reference=actor_reference,
            cancellation_authority_reference=cancellation_authority_reference,
        )

    @staticmethod
    def _wrap(mission_id: str, result: TransitionResult) -> BridgeTransitionResult:
        return BridgeTransitionResult(
            mission_id=mission_id,
            applied=result.applied,
            replayed=result.replayed,
            denied=result.denied,
            state=result.state,
            version=result.version,
            reason=result.reason,
            raw=result,
        )