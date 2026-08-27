"""Canonical P5 adapter for mission-bound memory retrieval and model routing.

This adapter delegates exclusively to the immutable L2 I3/I5 implementations.
It owns no mission, authority, approval, memory, model, or provider state and
performs no external provider invocation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from .memory_retrieval import retrieve_memory as _retrieve_memory
from .model_routing_attestation import attest as _attest_model


class ProviderBoundaryError(RuntimeError):
    """Raised when a denied/unsealed provider boundary would otherwise be crossed."""


@dataclass(frozen=True)
class CanonicalMemoryRequest:
    aggregate: Any
    query: Any
    candidates: Tuple[Any, ...]


@dataclass(frozen=True)
class MemoryReceipt:
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    retrieval_evidence_sha256: str
    selected_item_ids: Tuple[str, ...]
    authority_delta: int = 0
    canonical_state_source: str = "sintra_live/l2"


@dataclass(frozen=True)
class CanonicalModelRequest:
    aggregate: Any
    requirement: Any
    policy: Any
    catalog_entries: Tuple[Any, ...]
    reconciliation_complete: bool = True
    reconciliation_authority_delta: int = 0


@dataclass(frozen=True)
class ModelRoutingReceipt:
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    model_decision_sha256: str
    selected_identity_key: Tuple[str, ...]
    selected_catalog_entry_sha256: str
    estimated_total_cost_microunits: int
    provider_invoked: bool
    authority_delta: int = 0
    canonical_state_source: str = "sintra_live/l2"


@dataclass(frozen=True)
class P5MissionProjection:
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    memory_status: str
    memory_retrieval_evidence_sha256: str
    memory_selected_item_count: int
    model_routing_status: str
    model_decision_sha256: str
    selected_model_identity: Tuple[str, ...]
    canonical_state_source: str = "sintra_live/l2"

    @classmethod
    def from_receipts(cls, aggregate: Any, *, memory: Any, model: Any) -> "P5MissionProjection":
        mission_id, version, aggregate_sha256 = MemoryModelGateway._binding(aggregate)
        expected = (mission_id, version, aggregate_sha256)
        for receipt in (memory, model):
            actual = (
                getattr(receipt, "mission_id", None),
                getattr(receipt, "aggregate_version", None),
                getattr(receipt, "aggregate_sha256", None),
            )
            if actual != expected:
                raise ValueError("P5 receipt binding does not match canonical aggregate")
        return cls(
            mission_id=mission_id,
            aggregate_version=version,
            aggregate_sha256=aggregate_sha256,
            memory_status="COMPLETE",
            memory_retrieval_evidence_sha256=memory.retrieval_evidence_sha256,
            memory_selected_item_count=len(memory.selected_item_ids),
            model_routing_status="COMPLETE",
            model_decision_sha256=model.model_decision_sha256,
            selected_model_identity=tuple(model.selected_identity_key),
        )


class MemoryModelGateway:
    """Thin fail-closed production adapter over canonical L2 I3 and I5 APIs."""

    def __init__(
        self,
        *,
        memory_retriever: Callable[..., Any] = _retrieve_memory,
        model_attestor: Callable[..., Any] = _attest_model,
    ) -> None:
        self._memory_retriever = memory_retriever
        self._model_attestor = model_attestor

    @staticmethod
    def _binding(aggregate: Any) -> tuple[str, int, str]:
        identity = getattr(aggregate, "identity", None)
        mission_id = getattr(identity, "mission_id", "")
        version = getattr(aggregate, "version", None)
        aggregate_sha256 = getattr(aggregate, "aggregate_sha256", "")
        if not mission_id or not isinstance(version, int) or not aggregate_sha256:
            raise ValueError("canonical aggregate identity is incomplete")
        return mission_id, version, aggregate_sha256

    def retrieve_memory(self, request: CanonicalMemoryRequest) -> MemoryReceipt:
        mission_id, version, aggregate_sha256 = self._binding(request.aggregate)
        result = self._memory_retriever(request.aggregate, request.query, request.candidates)
        if getattr(result, "authority_delta", None) != 0:
            raise PermissionError("memory retrieval authority delta must be zero")
        evidence_sha = getattr(result, "retrieval_record_sha256", "") or getattr(
            result, "retrieval_evidence_sha256", ""
        )
        if not evidence_sha:
            raise ValueError("required retrieval evidence is missing")
        selected = tuple(getattr(result, "selected_item_ids", ())) or tuple(
            item.memory_item_id for item in getattr(result, "selected_items", ())
        )
        return MemoryReceipt(
            mission_id=mission_id,
            aggregate_version=version,
            aggregate_sha256=aggregate_sha256,
            retrieval_evidence_sha256=evidence_sha,
            selected_item_ids=selected,
        )

    def select_model(self, request: CanonicalModelRequest) -> ModelRoutingReceipt:
        mission_id, version, aggregate_sha256 = self._binding(request.aggregate)
        if request.reconciliation_authority_delta != 0:
            raise PermissionError("reconciliation authority delta must be zero")
        outcome = self._model_attestor(
            request.requirement,
            request.policy,
            request.catalog_entries,
            mission_state="SPECIALISTS_RECONCILED",
            terminal=bool(getattr(request.aggregate, "terminal", False)),
            cancelled=bool(getattr(request.aggregate, "cancelled", False)),
            reconciliation_complete=request.reconciliation_complete,
            reconciliation_authority_delta=0,
        )
        result_value = getattr(getattr(outcome, "result", None), "value", "")
        decision = getattr(outcome, "decision", None)
        if result_value != "COMPLETE" or decision is None:
            reason = getattr(outcome, "reason_code", "MODEL_ROUTING_DENIED")
            raise ProviderBoundaryError(f"model routing denied: {reason}")
        fallback_ids = tuple(getattr(decision, "fallback_identity_keys", ()))
        fallback_hashes = tuple(getattr(decision, "fallback_catalog_entry_sha256s", ()))
        if len(fallback_ids) != len(fallback_hashes):
            raise ProviderBoundaryError("fallback identities are not fully sealed")
        if fallback_ids or fallback_hashes:
            raise ProviderBoundaryError("provider fallback is prohibited at this authority boundary")
        if bool(getattr(decision, "provider_invoked", False)):
            raise ProviderBoundaryError("provider invocation is outside gateway authority")
        if getattr(decision, "authority_delta", None) != 0:
            raise ProviderBoundaryError("model decision authority delta must be zero")
        requirement_sha = getattr(request.requirement, "requirement_sha256", None)
        if not requirement_sha:
            raise ProviderBoundaryError("model requirement binding is incomplete")
        if getattr(decision, "requirement_sha256", None) != requirement_sha:
            raise ProviderBoundaryError("model decision binding mismatch")
        for name, expected in (
            ("mission_id", mission_id),
            ("aggregate_version", version),
            ("aggregate_sha256", aggregate_sha256),
        ):
            actual = getattr(request.requirement, name, None)
            if actual != expected:
                raise ProviderBoundaryError(f"model requirement {name} binding mismatch")
        decision_sha = getattr(decision, "model_decision_sha256", "")
        selected_hash = getattr(decision, "selected_catalog_entry_sha256", "")
        if not decision_sha or not selected_hash:
            raise ProviderBoundaryError("sealed model decision evidence is incomplete")
        return ModelRoutingReceipt(
            mission_id=mission_id,
            aggregate_version=version,
            aggregate_sha256=aggregate_sha256,
            model_decision_sha256=decision_sha,
            selected_identity_key=tuple(getattr(decision, "selected_identity_key", ())),
            selected_catalog_entry_sha256=selected_hash,
            estimated_total_cost_microunits=int(
                getattr(decision, "estimated_total_cost_microunits", 0)
            ),
            provider_invoked=False,
        )
