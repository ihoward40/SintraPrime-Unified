"""Deterministic L2-I7 authority resolver with pinned genesis trust anchor."""
from .principal_gateway_contract import *
from .principal_gateway_contract import _body, _ts
from sintra_live.l2.policy_resolution_contract import Result as PolicyResult,Consequence,ORDER as CON_ORDER

CONSEQUENCE_ORDER=CON_ORDER

def _required_assurance(consequence_class):
 if consequence_class in ("READ_ONLY","REVERSIBLE_INTERNAL","SCOPED_WRITE"):return "BASIC"
 return "ELEVATED"

def resolve(*,mission_id,program_id,gate_id,request_sha256,mission_scope_sha256,aggregate_version,aggregate_sha256,authority_snapshot_reference,operation_sha256,classification_sha256,consequence_class,policy_result,policy_decision_sha256,evaluation_time,trust_root_set,trust_roots,binding,binding_signature,session_attestation,session_signature,session_revocation=None,session_revocation_signature=None,authority_snapshot=None,authority_signature=None,authority_revocation=None,authority_revocation_signature=None,step_up_evidence=None,step_up_signature=None):
 ts(evaluation_time)
 # 1. Recompute root-set hash
 root_set_hash=trust_root_set.trusted_root_set_sha256
 # 2. Compare to pinned root-set hash
 if root_set_hash!=PINNED_TRUSTED_ROOT_SET_SHA256:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUSTED_ROOT_SET_HASH_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # 3. Verify each trust_root_sha256 is in the root set
 root_map={r.trust_root_sha256:r for r in trust_roots}
 root_identity_map={(r.trust_root_id,r.trust_root_version):r for r in trust_roots}
 for rsha in trust_root_set.ordered_trust_root_sha256s:
  if rsha not in root_map:return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUST_ROOT_NOT_IN_SET",operation_sha256,classification_sha256,policy_decision_sha256)
 # 4. Genesis root must be present
 if GENESIS_TRUST_ROOT_SHA256 not in root_map:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"GENESIS_ROOT_ABSENT",operation_sha256,classification_sha256,policy_decision_sha256)
 genesis_root=root_map[GENESIS_TRUST_ROOT_SHA256]
 # 5. Verify binding hash
 if binding.authority_trust_anchor_binding_sha256!=AUTHORITY_TRUST_ANCHOR_BINDING_SHA256:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUST_ANCHOR_BINDING_HASH_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 # 6. Verify binding's authority_snapshot_reference matches mission
 if binding.authority_snapshot_reference!=authority_snapshot_reference:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUST_ANCHOR_BINDING_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # 7. Verify binding's trusted_root_set_sha256 matches root set hash
 if binding.trusted_root_set_sha256!=root_set_hash:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUST_ANCHOR_BINDING_ROOT_SET_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # 8. Verify binding signature against genesis public key
 binding_payload=canonical_bytes({**_body(binding,"authority_trust_anchor_binding_sha256"),"authority_trust_anchor_binding_sha256":binding.authority_trust_anchor_binding_sha256})
 if not verify_ed25519(GENESIS_PUBLIC_KEY_HEX,binding_payload,binding_signature):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"TRUST_ANCHOR_BINDING_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 # 9. Trust established. Now verify session attestation.
 # Verify session signature
 session_payload=canonical_bytes({**_body(session_attestation,"attestation_sha256"),"attestation_sha256":session_attestation.attestation_sha256})
 session_root=root_identity_map.get((session_attestation.trust_root_id,session_attestation.trust_root_version))
 if not session_root or not session_root.permits("SESSION_ATTESTATION"):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SESSION_ISSUER_NOT_TRUSTED",operation_sha256,classification_sha256,policy_decision_sha256)
 if not verify_ed25519(session_root.verification_material,session_payload,session_signature):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHENTICATION_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 # Session binding
 if session_attestation.bound_program_id!=program_id or session_attestation.bound_gate_id!=gate_id or session_attestation.bound_mission_id!=mission_id or session_attestation.bound_request_sha256!=request_sha256:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SESSION_BINDING_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # Session validity
 if evaluation_time<session_attestation.session_valid_from:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SESSION_NOT_YET_VALID",operation_sha256,classification_sha256,policy_decision_sha256)
 if evaluation_time>=session_attestation.session_valid_until:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SESSION_EXPIRED",operation_sha256,classification_sha256,policy_decision_sha256)
 # Session revocation
 if session_revocation is None:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"REVOCATION_EVIDENCE_MISSING",operation_sha256,classification_sha256,policy_decision_sha256)
 # Use session's trust root for revocation if it permits SESSION_REVOCATION
 revoc_r=root_identity_map.get((session_attestation.trust_root_id,session_attestation.trust_root_version))
 if revoc_r and revoc_r.permits("SESSION_REVOCATION"):
  revoc_payload=canonical_bytes({**_body(session_revocation,"revocation_evidence_sha256"),"revocation_evidence_sha256":session_revocation.revocation_evidence_sha256})
  if not verify_ed25519(revoc_r.verification_material,revoc_payload,session_revocation_signature or ""):
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"REVOCATION_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 if session_revocation.status=="REVOKED":
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SESSION_REVOKED",operation_sha256,classification_sha256,policy_decision_sha256)
 if session_revocation.status=="UNKNOWN":
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"REVOCATION_STATUS_UNKNOWN",operation_sha256,classification_sha256,policy_decision_sha256)
 if evaluation_time>=session_revocation.valid_until:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"REVOCATION_EVIDENCE_EXPIRED",operation_sha256,classification_sha256,policy_decision_sha256)
 # Step-up
 required_assurance=_required_assurance(consequence_class)
 if required_assurance=="ELEVATED":
  if not session_attestation.step_up_completed:
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"STEP_UP_REQUIRED",operation_sha256,classification_sha256,policy_decision_sha256)
  if step_up_evidence is None or not session_attestation.step_up_evidence_sha256:
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"STEP_UP_EVIDENCE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
  if step_up_evidence.step_up_evidence_sha256!=session_attestation.step_up_evidence_sha256 or step_up_evidence.session_id!=session_attestation.session_id:
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"STEP_UP_EVIDENCE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
  step_root=root_identity_map.get((session_attestation.trust_root_id,session_attestation.trust_root_version))
  step_payload=canonical_bytes({**_body(step_up_evidence,"step_up_evidence_sha256"),"step_up_evidence_sha256":step_up_evidence.step_up_evidence_sha256})
  if not step_root or not step_root.permits("STEP_UP_ATTESTATION") or not verify_ed25519(step_root.verification_material,step_payload,step_up_signature or ""):
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"STEP_UP_EVIDENCE_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
  if session_attestation.authentication_assurance_level!="ELEVATED":
   return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"STEP_UP_ASSURANCE_INSUFFICIENT",operation_sha256,classification_sha256,policy_decision_sha256)
 # Policy decision permits?
 if policy_result not in (PolicyResult.ALLOW,PolicyResult.APPROVAL_REQUIRED):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"POLICY_DECISION_DOES_NOT_PERMIT",operation_sha256,classification_sha256,policy_decision_sha256)
 # Authority snapshot validation
 if authority_snapshot is None:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_SNAPSHOT_MISSING",operation_sha256,classification_sha256,policy_decision_sha256)
 # Verify authority snapshot signature
 auth_root=root_identity_map.get((authority_snapshot.trust_root_id,authority_snapshot.trust_root_version))
 if not auth_root or not auth_root.permits("AUTHORITY_ISSUANCE"):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_ISSUER_NOT_TRUSTED",operation_sha256,classification_sha256,policy_decision_sha256)
 auth_payload=canonical_bytes({**_body(authority_snapshot,"authority_attestation_sha256"),"authority_attestation_sha256":authority_snapshot.authority_attestation_sha256})
 if not verify_ed25519(auth_root.verification_material,auth_payload,authority_signature or ""):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 # Snapshot binding checks
 if authority_snapshot.bound_mission_id!=mission_id or authority_snapshot.bound_request_sha256!=request_sha256:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SNAPSHOT_BINDING_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 if authority_snapshot.bound_operation_sha256!=operation_sha256:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SNAPSHOT_BINDING_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # Validity
 if evaluation_time<authority_snapshot.valid_from:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SNAPSHOT_NOT_YET_VALID",operation_sha256,classification_sha256,policy_decision_sha256)
 if evaluation_time>=authority_snapshot.valid_until:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SNAPSHOT_EXPIRED",operation_sha256,classification_sha256,policy_decision_sha256)
 # Authority revocation
 if authority_revocation is None:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_REVOCATION_EVIDENCE_MISSING",operation_sha256,classification_sha256,policy_decision_sha256)
 auth_rev_root=root_identity_map.get((authority_snapshot.trust_root_id,authority_snapshot.trust_root_version))
 auth_rev_payload=canonical_bytes({**_body(authority_revocation,"revocation_evidence_sha256"),"revocation_evidence_sha256":authority_revocation.revocation_evidence_sha256})
 if not auth_rev_root or not auth_rev_root.permits("AUTHORITY_REVOCATION") or not verify_ed25519(auth_rev_root.verification_material,auth_rev_payload,authority_revocation_signature or ""):
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_REVOCATION_SIGNATURE_INVALID",operation_sha256,classification_sha256,policy_decision_sha256)
 if authority_revocation.status=="REVOKED":
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_SNAPSHOT_REVOKED",operation_sha256,classification_sha256,policy_decision_sha256)
 if authority_revocation.status=="UNKNOWN":
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_SNAPSHOT_REVOCATION_UNKNOWN",operation_sha256,classification_sha256,policy_decision_sha256)
 if evaluation_time>=authority_revocation.valid_until:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"AUTHORITY_SNAPSHOT_REVOCATION_EXPIRED",operation_sha256,classification_sha256,policy_decision_sha256)
 # Principal binding
 if authority_snapshot.principal_identity_reference!=session_attestation.principal_identity_reference:
  return _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,"SNAPSHOT_BINDING_MISMATCH",operation_sha256,classification_sha256,policy_decision_sha256)
 # ALLOW
 rec=AuthorityResolution(schema_version=SCHEMA["authority-resolution"],resolver_version=RESOLVER_VERSION,result=AuthResult.ALLOW.value,reason_code="ALL_CHECKS_PASSED",principal_auth_sha256="",authority_snapshot_validation_sha256="",policy_decision_sha256=policy_decision_sha256,trust_root_id=GENESIS_TRUST_ROOT_ID,trust_root_version=GENESIS_TRUST_ROOT_VERSION,program_id=program_id,gate_id=gate_id,principal_identity_reference=session_attestation.principal_identity_reference,mission_id=mission_id,request_sha256=request_sha256,mission_scope_sha256=mission_scope_sha256,aggregate_version=aggregate_version,aggregate_sha256=aggregate_sha256,proposed_operation_sha256=operation_sha256,consequence_classification_sha256=classification_sha256,evaluation_time=evaluation_time,authority_snapshot_valid=True)
 return Resolution(AuthResult.ALLOW,rec)

def _deny(mission_id,program_id,gate_id,request_sha256,evaluation_time,reason,operation_sha256,classification_sha256,policy_decision_sha256):
 rec=AuthorityResolution(schema_version=SCHEMA["authority-resolution"],resolver_version=RESOLVER_VERSION,result=AuthResult.DENY.value,reason_code=reason,principal_auth_sha256="",authority_snapshot_validation_sha256="",policy_decision_sha256=policy_decision_sha256,trust_root_id="",trust_root_version="",program_id=program_id,gate_id=gate_id,principal_identity_reference="",mission_id=mission_id,request_sha256=request_sha256,mission_scope_sha256="",aggregate_version=0,aggregate_sha256="",proposed_operation_sha256=operation_sha256,consequence_classification_sha256=classification_sha256,evaluation_time=evaluation_time,authority_snapshot_valid=False)
 return Resolution(AuthResult.DENY,rec)