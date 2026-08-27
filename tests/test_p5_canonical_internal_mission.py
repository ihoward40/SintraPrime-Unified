"""P5 end-to-end canonical memory → model routing path."""
from tests.test_l2_i3_memory_retrieval import agg as memory_agg, query, cand
from tests.test_l2_i5_model_routing import req, policy, entry

from sintra_live.l2.memory_retrieval import retrieve_memory
from sintra_live.l2.model_routing_attestation import attest
from sintra_live.l2.p5_memory_model_gateway import (
    CanonicalMemoryRequest,
    CanonicalModelRequest,
    MemoryModelGateway,
    P5MissionProjection,
)


def test_p5_memory_and_model_routing_bind_to_same_canonical_mission():
    aggregate = memory_agg()
    gateway = MemoryModelGateway(memory_retriever=retrieve_memory, model_attestor=attest)

    memory_receipt = gateway.retrieve_memory(
        CanonicalMemoryRequest(aggregate, query(aggregate), (cand(),))
    )
    requirement = req(
        program_id=aggregate.identity.program_id,
        gate_id=aggregate.identity.gate_id,
        principal_identity_reference=aggregate.identity.principal_identity_reference,
        mission_id=aggregate.identity.mission_id,
        request_sha256=aggregate.identity.request_sha256,
        mission_scope_sha256=aggregate.identity.mission_scope_sha256,
        aggregate_version=aggregate.version,
        aggregate_sha256=aggregate.aggregate_sha256,
    )
    model_receipt = gateway.select_model(
        CanonicalModelRequest(aggregate, requirement, policy(), (entry(),))
    )
    projection = P5MissionProjection.from_receipts(
        aggregate, memory=memory_receipt, model=model_receipt
    )

    assert memory_receipt.mission_id == model_receipt.mission_id == aggregate.identity.mission_id
    assert memory_receipt.aggregate_sha256 == model_receipt.aggregate_sha256
    assert memory_receipt.retrieval_evidence_sha256
    assert model_receipt.model_decision_sha256
    assert memory_receipt.authority_delta == model_receipt.authority_delta == 0
    assert model_receipt.provider_invoked is False
    assert projection.memory_status == projection.model_routing_status == "COMPLETE"
    assert projection.canonical_state_source == "sintra_live/l2"
