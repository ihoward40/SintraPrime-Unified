"""P5 canonical L2 memory and model-routing production adapter tests."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from sintra_live.l2.p5_memory_model_gateway import (
    CanonicalMemoryRequest,
    CanonicalModelRequest,
    MemoryModelGateway,
    ProviderBoundaryError,
    P5MissionProjection,
)


@dataclass(frozen=True)
class Identity:
    program_id: str = "SP-LIVE-001"
    gate_id: str = "P5"
    mission_id: str = "mission-p5-001"
    request_id: str = "request-001"
    request_sha256: str = "a" * 64
    mission_scope_sha256: str = "b" * 64
    principal_identity_reference: str = "principal-001"


@dataclass(frozen=True)
class Aggregate:
    identity: Identity = Identity()
    version: int = 3
    aggregate_sha256: str = "c" * 64
    terminal: bool = False
    cancelled: bool = False
    current_state: object = None


class FakeMemoryRetriever:
    def __init__(self):
        self.calls = []

    def __call__(self, aggregate, query, candidates):
        self.calls.append((aggregate, query, tuple(candidates)))
        return type("MemoryResult", (), {
            "mission_id": "mission-p5-001",
            "aggregate_version": 3,
            "aggregate_sha256": "c" * 64,
            "retrieval_evidence_sha256": "d" * 64,
            "selected_item_ids": ("memory-1",),
            "authority_delta": 0,
            "result": type("Result", (), {"value": "COMPLETE"})(),
        })()


class FakeModelAttestor:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def __call__(self, requirement, policy, catalog, **bindings):
        self.calls.append((requirement, policy, tuple(catalog), bindings))
        return self.outcome


class FakeOutcome:
    def __init__(self, result="COMPLETE", decision=None, reason_code=""):
        self.result = type("Result", (), {"value": result})()
        self.decision = decision
        self.reason_code = reason_code


class FakeDecision:
    model_decision_sha256 = "e" * 64
    selected_identity_key = ("provider-a", "family", "model-a", "v1", "deploy", "offline")
    selected_catalog_entry_sha256 = "f" * 64
    fallback_identity_keys = ()
    fallback_catalog_entry_sha256s = ()
    estimated_total_cost_microunits = 100
    provider_invoked = False
    authority_delta = 0
    requirement_sha256 = "required"


def test_memory_retrieval_is_bound_to_canonical_mission_identity():
    retriever = FakeMemoryRetriever()
    gateway = MemoryModelGateway(memory_retriever=retriever)
    aggregate = Aggregate()
    request = CanonicalMemoryRequest(
        aggregate=aggregate,
        query=object(),
        candidates=(object(),),
    )
    receipt = gateway.retrieve_memory(request)
    assert receipt.mission_id == aggregate.identity.mission_id
    assert receipt.aggregate_version == aggregate.version
    assert receipt.aggregate_sha256 == aggregate.aggregate_sha256
    assert receipt.retrieval_evidence_sha256 == "d" * 64
    assert receipt.authority_delta == 0
    assert retriever.calls[0][0] is aggregate


def test_memory_result_without_required_evidence_fails_closed():
    retriever = FakeMemoryRetriever()
    retriever.__call__ = lambda *args: object()
    gateway = MemoryModelGateway(memory_retriever=lambda *args: type("Result", (), {"authority_delta": 0})())
    with pytest.raises(ValueError, match="retrieval evidence"):
        gateway.retrieve_memory(CanonicalMemoryRequest(Aggregate(), object(), ()))


def test_model_selection_uses_l2_attestation_and_preserves_mission_identity():
    attestor = FakeModelAttestor(FakeOutcome(decision=FakeDecision()))
    gateway = MemoryModelGateway(model_attestor=attestor)
    aggregate = Aggregate()
    requirement = type("Requirement", (), {
        "requirement_sha256": "required",
        "mission_id": aggregate.identity.mission_id,
        "aggregate_version": aggregate.version,
        "aggregate_sha256": aggregate.aggregate_sha256,
    })()
    receipt = gateway.select_model(
        CanonicalModelRequest(
            aggregate=aggregate,
            requirement=requirement,
            policy=object(),
            catalog_entries=(object(),),
            reconciliation_complete=True,
            reconciliation_authority_delta=0,
        )
    )
    assert receipt.mission_id == aggregate.identity.mission_id
    assert receipt.aggregate_sha256 == aggregate.aggregate_sha256
    assert receipt.model_decision_sha256 == "e" * 64
    assert receipt.authority_delta == 0
    assert receipt.provider_invoked is False
    assert attestor.calls[0][3]["reconciliation_authority_delta"] == 0


def test_nonzero_reconciliation_authority_is_denied_before_routing():
    attestor = FakeModelAttestor(FakeOutcome(decision=FakeDecision()))
    gateway = MemoryModelGateway(model_attestor=attestor)
    with pytest.raises(PermissionError, match="authority delta"):
        gateway.select_model(
            CanonicalModelRequest(Aggregate(), object(), object(), (), True, 1)
        )
    assert attestor.calls == []


def test_denied_model_attestation_cannot_fall_back_silently():
    gateway = MemoryModelGateway(
        model_attestor=FakeModelAttestor(FakeOutcome(result="DENIED", reason_code="NO_ELIGIBLE_MODEL"))
    )
    with pytest.raises(ProviderBoundaryError, match="NO_ELIGIBLE_MODEL"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), object(), object(), ()))


def test_provider_fallback_must_be_explicitly_sealed():
    decision = FakeDecision()
    decision.fallback_identity_keys = (("provider-b", "family", "model-b", "v1", "deploy", "offline"),)
    decision.fallback_catalog_entry_sha256s = ()
    gateway = MemoryModelGateway(model_attestor=FakeModelAttestor(FakeOutcome(decision=decision)))
    with pytest.raises(ProviderBoundaryError, match="fallback"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), object(), object(), ()))


def test_provider_execution_is_never_performed_by_gateway():
    decision = FakeDecision()
    decision.provider_invoked = True
    gateway = MemoryModelGateway(model_attestor=FakeModelAttestor(FakeOutcome(decision=decision)))
    with pytest.raises(ProviderBoundaryError, match="provider invocation"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), object(), object(), ()))


def test_nonempty_sealed_fallback_is_prohibited():
    decision = FakeDecision()
    decision.fallback_identity_keys = (("provider-b", "model-b", "v1", "deploy"),)
    decision.fallback_catalog_entry_sha256s = ("9" * 64,)
    gateway = MemoryModelGateway(model_attestor=FakeModelAttestor(FakeOutcome(decision=decision)))
    requirement = type("Requirement", (), {
        "requirement_sha256": "required",
        "mission_id": "mission-p5-001",
        "aggregate_version": 3,
        "aggregate_sha256": "c" * 64,
    })()
    with pytest.raises(ProviderBoundaryError, match="fallback is prohibited"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), requirement, object(), ()))


def test_missing_model_requirement_binding_fails_closed():
    gateway = MemoryModelGateway(
        model_attestor=FakeModelAttestor(FakeOutcome(decision=FakeDecision()))
    )
    with pytest.raises(ProviderBoundaryError, match="requirement binding is incomplete"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), object(), object(), ()))


def test_gateway_rejects_memory_receipt_with_nonzero_authority_delta():
    result = type("MemoryResult", (), {
        "retrieval_record_sha256": "d" * 64,
        "selected_items": (),
        "authority_delta": 1,
        "result": type("Result", (), {"value": "COMPLETE"})(),
    })()
    gateway = MemoryModelGateway(memory_retriever=lambda *args: result)
    with pytest.raises(PermissionError, match="authority delta"):
        gateway.retrieve_memory(CanonicalMemoryRequest(Aggregate(), object(), ()))


def test_gateway_rejects_model_decision_binding_mismatch():
    decision = FakeDecision()
    decision.authority_delta = 0
    decision.requirement_sha256 = "wrong"
    requirement = type("Requirement", (), {
        "requirement_sha256": "required",
        "mission_id": "mission-p5-001",
        "aggregate_version": 3,
        "aggregate_sha256": "c" * 64,
    })()
    gateway = MemoryModelGateway(model_attestor=FakeModelAttestor(FakeOutcome(decision=decision)))
    with pytest.raises(ProviderBoundaryError, match="binding"):
        gateway.select_model(CanonicalModelRequest(Aggregate(), requirement, object(), ()))


def test_projection_exposes_canonical_memory_and_model_state():
    projection = P5MissionProjection.from_receipts(
        Aggregate(),
        memory=type("MemoryReceipt", (), {
            "mission_id": "mission-p5-001",
            "aggregate_version": 3,
            "aggregate_sha256": "c" * 64,
            "retrieval_evidence_sha256": "d" * 64,
            "selected_item_ids": ("m1",),
        })(),
        model=type("ModelReceipt", (), {
            "mission_id": "mission-p5-001",
            "aggregate_version": 3,
            "aggregate_sha256": "c" * 64,
            "model_decision_sha256": "e" * 64,
            "selected_identity_key": ("p", "m", "v", "d"),
        })(),
    )
    assert projection.mission_id == "mission-p5-001"
    assert projection.aggregate_version == 3
    assert projection.aggregate_sha256 == "c" * 64
    assert projection.memory_status == "COMPLETE"
    assert projection.model_routing_status == "COMPLETE"
    assert projection.canonical_state_source == "sintra_live/l2"


def test_mission_control_bridge_projects_p5_from_canonical_store():
    from sintra_live.l2.mission_control_bridge import MissionControlBridge

    aggregate = Aggregate()
    bridge = object.__new__(MissionControlBridge)
    bridge._store = type("Store", (), {"load": lambda self, mission_id: aggregate})()
    memory = type("MemoryReceipt", (), {
        "mission_id": aggregate.identity.mission_id,
        "aggregate_version": aggregate.version,
        "aggregate_sha256": aggregate.aggregate_sha256,
        "retrieval_evidence_sha256": "d" * 64,
        "selected_item_ids": ("m1",),
    })()
    model = type("ModelReceipt", (), {
        "mission_id": aggregate.identity.mission_id,
        "aggregate_version": aggregate.version,
        "aggregate_sha256": aggregate.aggregate_sha256,
        "model_decision_sha256": "e" * 64,
        "selected_identity_key": ("p", "m", "v", "d"),
    })()
    projection = bridge.project_p5(
        aggregate.identity.mission_id, memory_receipt=memory, model_receipt=model
    )
    assert projection.aggregate_sha256 == aggregate.aggregate_sha256
    assert projection.canonical_state_source == "sintra_live/l2"


def test_projection_rejects_receipts_from_another_aggregate():
    memory = type("MemoryReceipt", (), {
        "mission_id": "other",
        "aggregate_version": 3,
        "aggregate_sha256": "c" * 64,
        "retrieval_evidence_sha256": "d" * 64,
        "selected_item_ids": (),
    })()
    model = type("ModelReceipt", (), {
        "mission_id": "mission-p5-001",
        "aggregate_version": 3,
        "aggregate_sha256": "c" * 64,
        "model_decision_sha256": "e" * 64,
        "selected_identity_key": (),
    })()
    with pytest.raises(ValueError, match="receipt binding"):
        P5MissionProjection.from_receipts(Aggregate(), memory=memory, model=model)


def test_missing_receipt_binding_and_authority_fields_fail_closed():
    gateway = MemoryModelGateway(memory_retriever=lambda *args: type("Result", (), {
        "retrieval_record_sha256": "d" * 64,
        "selected_items": (),
    })())
    with pytest.raises(PermissionError, match="authority delta"):
        gateway.retrieve_memory(CanonicalMemoryRequest(Aggregate(), object(), ()))

    unbound = type("Receipt", (), {
        "retrieval_evidence_sha256": "d" * 64,
        "selected_item_ids": (),
        "model_decision_sha256": "e" * 64,
        "selected_identity_key": (),
    })()
    with pytest.raises(ValueError, match="receipt binding"):
        P5MissionProjection.from_receipts(Aggregate(), memory=unbound, model=unbound)
