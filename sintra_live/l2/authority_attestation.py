"""I7 authority attestation: thin wrapper around the resolver for sealed-decision verification."""
from .principal_gateway_contract import *
from .authority_resolver import resolve

def attest(*, mission_id, program_id, gate_id, request_sha256, mission_scope_sha256,
           aggregate_version, aggregate_sha256, authority_snapshot_reference,
           operation_sha256, classification_sha256, consequence_class, policy_result,
           policy_decision_sha256, evaluation_time, trust_root_set, trust_roots,
           binding, binding_signature, session_attestation, session_signature,
           session_revocation=None, session_revocation_signature=None,
           authority_snapshot=None, authority_signature=None,
           authority_revocation=None, authority_revocation_signature=None,
           step_up_evidence=None, step_up_signature=None):
    return resolve(
        mission_id=mission_id, program_id=program_id, gate_id=gate_id,
        request_sha256=request_sha256, mission_scope_sha256=mission_scope_sha256,
        aggregate_version=aggregate_version, aggregate_sha256=aggregate_sha256,
        authority_snapshot_reference=authority_snapshot_reference,
        operation_sha256=operation_sha256, classification_sha256=classification_sha256,
        consequence_class=consequence_class, policy_result=policy_result,
        policy_decision_sha256=policy_decision_sha256, evaluation_time=evaluation_time,
        trust_root_set=trust_root_set, trust_roots=trust_roots,
        binding=binding, binding_signature=binding_signature,
        session_attestation=session_attestation, session_signature=session_signature,
        session_revocation=session_revocation,
        session_revocation_signature=session_revocation_signature,
        authority_snapshot=authority_snapshot, authority_signature=authority_signature,
        authority_revocation=authority_revocation,
        authority_revocation_signature=authority_revocation_signature,
        step_up_evidence=step_up_evidence, step_up_signature=step_up_signature,
    )