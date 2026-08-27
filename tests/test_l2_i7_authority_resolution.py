"""Functional tests for L2-I7 authority resolution and genesis trust anchor."""
import hashlib
from dataclasses import asdict
from sintra_live.l2.principal_gateway_contract import *
from sintra_live.l2.principal_gateway_contract import _body
from sintra_live.l2.policy_resolution_contract import Result as PolicyResult
from sintra_live.l2.authority_resolver import resolve
from sintra_live.l2.authority_attestation import attest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from sintra_live.l2.mission.model import canonical_bytes

def _make_genesis_artifacts():
 """Return (trust_root, root_set, binding, binding_signature, private_key) using pinned genesis."""
 # The pinned genesis values are constants in principal_gateway_contract
 # For tests, we need a private key matching GENESIS_PUBLIC_KEY_HEX
 # Since we don't have the private key, we re-derive the public key and use it for verification
 # For signing in tests we generate a fresh key and override the pinned check is NOT possible
 # Instead, tests use the ACTUAL pinned genesis public key for verification
 # and the INITIAL_BINDING_SIGNATURE_HEX for the binding signature
 
 trust_root = TrustRoot(
  schema_version="sp-live-001-l2-i7-trust-root-v1",
  trust_root_id="sp-live-001-genesis-root",
  trust_root_version="v1",
  issuer_id="deployment-baseline",
  issuer_type="PRINCIPAL_GATEWAY",
  verification_algorithm="ED25519_DETEACH",
  verification_material=GENESIS_PUBLIC_KEY_HEX,
  verification_material_sha256=hashlib.sha256(bytes.fromhex(GENESIS_PUBLIC_KEY_HEX)).hexdigest(),
  permitted_usages=("SESSION_ATTESTATION","SESSION_REVOCATION","STEP_UP_ATTESTATION","AUTHORITY_ISSUANCE","AUTHORITY_REVOCATION"),
  valid_from="2026-01-01T00:00:00.000000Z",
  valid_until="2099-01-01T00:00:00.000000Z",
 )
 root_set = TrustedRootSet(
  schema_version="sp-live-001-l2-i7-trusted-root-set-v1",
  trusted_root_set_version="v1",
  ordered_trust_root_sha256s=(trust_root.trust_root_sha256,),
 )
 binding = TrustAnchorBinding(
  schema_version="sp-live-001-l2-i7-trust-anchor-binding-v1",
  binding_version="v1",
  program_id="SP-LIVE-001",
  gate_id="L2-I7",
  mission_id="genesis-deployment",
  authority_snapshot_reference="genesis-deployment-ref",
  trusted_root_set_sha256=root_set.trusted_root_set_sha256,
  binding_basis_code="DEPLOYMENT_BASELINE",
 )
 return trust_root, root_set, binding, INITIAL_BINDING_SIGNATURE_HEX

def _make_session(priv_key, trust_root_id="sp-live-001-genesis-root", trust_root_version="v1",
                  principal="principal-001", mission_id="m1", program_id="SP-LIVE-001",
                  gate_id="L2-I7", request_sha256="0"*64, assurance="BASIC",
                  step_up=False, step_up_done=False, step_up_evidence_sha256=""):
 pub = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
 sa = SessionAttestation(
  schema_version="sp-live-001-l2-i7-session-attestation-v1",
  attestation_version="v1",
  session_id="session-001",
  trust_root_id=trust_root_id,
  trust_root_version=trust_root_version,
  issuer_id="gateway-1",
  issuer_type="PRINCIPAL_GATEWAY",
  principal_identity_reference=principal,
  authentication_method="PASSWORD",
  authentication_assurance_level=assurance,
  authentication_timestamp="2026-08-24T10:00:00.000000Z",
  session_valid_from="2026-08-24T10:00:00.000000Z",
  session_valid_until="2026-08-24T20:00:00.000000Z",
  session_nonce="nonce-001",
  bound_program_id=program_id,
  bound_gate_id=gate_id,
  bound_mission_id=mission_id,
  bound_request_sha256=request_sha256,
  step_up_required=step_up,
  step_up_assurance_level="BASIC",
  step_up_completed=step_up_done,
  step_up_method="",
  step_up_completed_at="",
  step_up_evidence_sha256=step_up_evidence_sha256,
  revocation_status_reference="rev-ref-001",
 )
 payload = canonical_bytes({**_body(sa,"attestation_sha256"),"attestation_sha256":sa.attestation_sha256})
 sig = priv_key.sign(payload).hex()
 return sa, sig

def _make_revocation(priv_key, subject_id, status="NOT_REVOKED"):
 re = RevocationEvidence(
  schema_version="sp-live-001-l2-i7-revocation-evidence-v1",
  revocation_version="v1",
  subject_type="PRINCIPAL_SESSION",
  subject_id=subject_id,
  issuer_id="sp-live-001-genesis-root",
  status=status,
  status_as_of="2026-08-24T10:00:00.000000Z",
  valid_until="2026-08-24T20:00:00.000000Z",
  source_reference="rev-source-001",
 )
 payload = canonical_bytes({**_body(re,"revocation_evidence_sha256"),"revocation_evidence_sha256":re.revocation_evidence_sha256})
 sig = priv_key.sign(payload).hex()
 return re, sig

def _make_step_up(priv_key, session_id="session-001"):
 ev=StepUpEvidence(schema_version=SCHEMA["step-up-evidence"],step_up_version="v1",session_id=session_id,step_up_method="WEBAUTHN",step_up_assurance_level="ELEVATED",step_up_completed_at="2026-08-24T10:30:00.000000Z")
 payload=canonical_bytes({**_body(ev,"step_up_evidence_sha256"),"step_up_evidence_sha256":ev.step_up_evidence_sha256})
 return ev,priv_key.sign(payload).hex()

def _make_auth_snapshot(priv_key, mission_id="m1", request_sha256="0"*64, operation_sha256="0"*64,
                        classification_sha256="0"*64, principal="principal-001"):
 sa = AuthoritySnapshotAttestation(
  schema_version="sp-live-001-l2-i7-authority-attestation-v1",
  attestation_version="v1",
  snapshot_id="snap-001",
  trust_root_id="sp-live-001-genesis-root",
  trust_root_version="v1",
  issuer_id="gateway-1",
  issuer_type="PRINCIPAL_GATEWAY",
  principal_identity_reference=principal,
  bound_mission_id=mission_id,
  bound_request_sha256=request_sha256,
  bound_mission_scope_sha256="0"*64,
  bound_operation_sha256=operation_sha256,
  bound_consequence_classification_sha256=classification_sha256,
  bound_capability_id="cap",
  bound_capability_version="1",
  bound_destination_class="internal",
  bound_provider_account_reference="acct",
  declared_scope_ids=("query",),
  declared_capability_ids=("cap:1",),
  declared_side_effect_ceiling=0,
  declared_cost_ceiling=100,
  declared_token_ceiling=100,
  declared_latency_ceiling_ms=100,
  declared_consequence_ceiling="READ_ONLY",
  issued_at="2026-08-24T10:00:00.000000Z",
  valid_from="2026-08-24T10:00:00.000000Z",
  valid_until="2099-01-01T00:00:00.000000Z",
  parent_authority_evidence_sha256="0"*64,
 )
 payload = canonical_bytes({**_body(sa,"authority_attestation_sha256"),"authority_attestation_sha256":sa.authority_attestation_sha256})
 sig = priv_key.sign(payload).hex()
 return sa, sig

# Generate a test keypair that matches genesis public key is NOT possible.
# Instead, we need to use the genesis public key for verification.
# The INITIAL_BINDING_SIGNATURE_HEX was signed with the genesis private key during ceremony.
# For session/authority attestations, we need a private key matching a trust root in the set.
# Since we don't have the genesis private key, we'll create a SECOND trust root for test signing.
# But wait - the root set is pinned. We can't add roots.
# Solution: tests verify that the pinned genesis setup works with INITIAL_BINDING_SIGNATURE_HEX,
# and for session/authority, tests use a separate non-genesis root that IS in the pinned set.
# But the pinned set only has one root (genesis). So tests can't sign sessions with it.
# 
# Actually: the test framework CAN generate a keypair, create a TrustRoot with that key,
# and include it in the root set. But the root set hash is PINNED.
# So we need to use the EXACT genesis key for signing.
# 
# For the ceremony, the private key was ephemeral. We saved INITIAL_BINDING_SIGNATURE_HEX.
# For tests, we need to generate a NEW genesis key and NEW pinned values.
# But the pinned values are constants in the contract module.
# 
# The cleanest test approach: tests verify the BINDING signature using INITIAL_BINDING_SIGNATURE_HEX
# (which was signed by the real genesis key). For session/authority signatures, tests verify
# that verification FAILS for wrong signatures and SUCCEEDS when using the genesis key.
# Since we don't have the genesis private key, session/authority tests need a workaround.
# 
# Workaround: for tests, we monkeypatch GENESIS_PUBLIC_KEY_HEX to use a test keypair.
# This is acceptable because tests are not production code.

_test_priv = Ed25519PrivateKey.generate()
_test_pub = _test_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

def _setup_test_genesis():
 """Override pinned values with test-generated genesis for signing."""
 import sintra_live.l2.principal_gateway_contract as mod
 import sintra_live.l2.authority_resolver as resolver_mod
 
 trust_root = TrustRoot(
  schema_version="sp-live-001-l2-i7-trust-root-v1",
  trust_root_id="sp-live-001-genesis-root",
  trust_root_version="v1",
  issuer_id="deployment-baseline",
  issuer_type="PRINCIPAL_GATEWAY",
  verification_algorithm="ED25519_DETEACH",
  verification_material=_test_pub,
  verification_material_sha256=hashlib.sha256(bytes.fromhex(_test_pub)).hexdigest(),
  permitted_usages=("SESSION_ATTESTATION","SESSION_REVOCATION","STEP_UP_ATTESTATION","AUTHORITY_ISSUANCE","AUTHORITY_REVOCATION"),
  valid_from="2026-01-01T00:00:00.000000Z",
  valid_until="2099-01-01T00:00:00.000000Z",
 )
 root_set = TrustedRootSet(
  schema_version="sp-live-001-l2-i7-trusted-root-set-v1",
  trusted_root_set_version="v1",
  ordered_trust_root_sha256s=(trust_root.trust_root_sha256,),
 )
 binding = TrustAnchorBinding(
  schema_version="sp-live-001-l2-i7-trust-anchor-binding-v1",
  binding_version="v1",
  program_id="SP-LIVE-001",
  gate_id="L2-I7",
  mission_id="genesis-deployment",
  authority_snapshot_reference="genesis-deployment-ref",
  trusted_root_set_sha256=root_set.trusted_root_set_sha256,
  binding_basis_code="DEPLOYMENT_BASELINE",
 )
 binding_payload = canonical_bytes({**_body(binding,"authority_trust_anchor_binding_sha256"),"authority_trust_anchor_binding_sha256":binding.authority_trust_anchor_binding_sha256})
 binding_sig = _test_priv.sign(binding_payload).hex()
 
 # Override pinned constants
 mod.GENESIS_TRUST_ROOT_SHA256 = trust_root.trust_root_sha256
 mod.PINNED_TRUSTED_ROOT_SET_SHA256 = root_set.trusted_root_set_sha256
 mod.AUTHORITY_TRUST_ANCHOR_BINDING_SHA256 = binding.authority_trust_anchor_binding_sha256
 mod.GENESIS_PUBLIC_KEY_HEX = _test_pub
 resolver_mod.GENESIS_TRUST_ROOT_SHA256 = trust_root.trust_root_sha256
 resolver_mod.PINNED_TRUSTED_ROOT_SET_SHA256 = root_set.trusted_root_set_sha256
 resolver_mod.AUTHORITY_TRUST_ANCHOR_BINDING_SHA256 = binding.authority_trust_anchor_binding_sha256
 resolver_mod.GENESIS_PUBLIC_KEY_HEX = _test_pub
 
 return trust_root, root_set, binding, binding_sig

def _base_kwargs(**kw):
 tr, rs, bnd, bsig = _setup_test_genesis()
 sa, ssig = _make_session(_test_priv)
 rev, rsig = _make_revocation(_test_priv, "session-001")
 asnp, asig = _make_auth_snapshot(_test_priv)
 arev, arsig = _make_revocation(_test_priv, "snap-001")
 d = dict(
  mission_id="m1", program_id="SP-LIVE-001", gate_id="L2-I7",
  request_sha256="0"*64, mission_scope_sha256="0"*64,
  aggregate_version=1, aggregate_sha256="0"*64,
  authority_snapshot_reference="genesis-deployment-ref",
  operation_sha256="0"*64, classification_sha256="0"*64,
  consequence_class="READ_ONLY", policy_result=PolicyResult.ALLOW,
  policy_decision_sha256="0"*64, evaluation_time="2026-08-24T12:00:00.000000Z",
  trust_root_set=rs, trust_roots=[tr], binding=bnd, binding_signature=bsig,
  session_attestation=sa, session_signature=ssig,
  session_revocation=rev, session_revocation_signature=rsig,
  authority_snapshot=asnp, authority_signature=asig,
  authority_revocation=arev, authority_revocation_signature=arsig,
 )
 d.update(kw)
 return d

def test_r03_current_principal_authenticated():
 r = attest(**_base_kwargs())
 assert r.result is AuthResult.ALLOW
 assert r.record.authority_snapshot_valid is True
 assert r.record.authority_delta == 0

def test_r04_stale_session_denied():
 kw = _base_kwargs(evaluation_time="2026-08-25T01:00:00.000000Z")
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "SESSION_EXPIRED" in r.record.reason_code

def test_p04_authority_snapshot_missing_denied():
 kw = _base_kwargs(authority_snapshot=None, authority_signature=None)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "AUTHORITY_SNAPSHOT_MISSING" in r.record.reason_code

def test_p06_no_authority_conversion():
 r = attest(**_base_kwargs())
 assert r.record.approval_granted is False
 assert r.record.capability_available is False
 assert r.record.capability_certified is False
 assert r.record.execution_ready is False
 assert r.record.authority_delta == 0

def test_p07_deterministic():
 a = attest(**_base_kwargs())
 b = attest(**_base_kwargs())
 assert a.record.authority_resolution_sha256 == b.record.authority_resolution_sha256

def test_wrong_root_set_hash_denied():
 tr, rs, bnd, bsig = _setup_test_genesis()
 bad_rs = TrustedRootSet(schema_version=rs.schema_version, trusted_root_set_version=rs.trusted_root_set_version, ordered_trust_root_sha256s=("0"*64,))
 kw = _base_kwargs(trust_root_set=bad_rs)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "TRUSTED_ROOT_SET_HASH_MISMATCH" in r.record.reason_code

def test_missing_genesis_root_denied():
 tr, rs, bnd, bsig = _setup_test_genesis()
 # Keep the correctly pinned set but omit the referenced genesis-root record.
 kw = _base_kwargs(trust_root_set=rs, trust_roots=[])
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert r.record.reason_code in ("TRUST_ROOT_NOT_IN_SET", "GENESIS_ROOT_ABSENT")

def test_wrong_binding_hash_denied():
 kw = _base_kwargs(binding=TrustAnchorBinding(
  schema_version="sp-live-001-l2-i7-trust-anchor-binding-v1", binding_version="v1",
  program_id="SP-LIVE-001", gate_id="L2-I7", mission_id="genesis-deployment",
  authority_snapshot_reference="genesis-deployment-ref",
  trusted_root_set_sha256="0"*64, binding_basis_code="DEPLOYMENT_BASELINE",
 ))
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "TRUST_ANCHOR_BINDING_HASH_INVALID" in r.record.reason_code or "TRUST_ANCHOR_BINDING_ROOT_SET_MISMATCH" in r.record.reason_code

def test_session_binding_mismatch_denied():
 sa, ssig = _make_session(_test_priv, mission_id="other-mission")
 kw = _base_kwargs(session_attestation=sa, session_signature=ssig)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "SESSION_BINDING_MISMATCH" in r.record.reason_code

def test_invalid_session_signature_denied():
 kw = _base_kwargs(session_signature="0"*128)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "AUTHENTICATION_SIGNATURE_INVALID" in r.record.reason_code

def test_revocation_missing_denied():
 kw = _base_kwargs(session_revocation=None, session_revocation_signature=None)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "REVOCATION_EVIDENCE_MISSING" in r.record.reason_code

def test_session_revoked_denied():
 rev, rsig = _make_revocation(_test_priv, "session-001", status="REVOKED")
 kw = _base_kwargs(session_revocation=rev, session_revocation_signature=rsig)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "SESSION_REVOKED" in r.record.reason_code

def test_step_up_required_for_elevated():
 sa, ssig = _make_session(_test_priv, assurance="BASIC", step_up=False, step_up_done=False)
 kw = _base_kwargs(session_attestation=sa, session_signature=ssig, consequence_class="FINANCIAL")
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "STEP_UP_REQUIRED" in r.record.reason_code

def test_step_up_satisfied_for_elevated():
 ev,esig=_make_step_up(_test_priv)
 sa, ssig = _make_session(_test_priv, assurance="ELEVATED", step_up=True, step_up_done=True,step_up_evidence_sha256=ev.step_up_evidence_sha256)
 kw = _base_kwargs(session_attestation=sa, session_signature=ssig, consequence_class="FINANCIAL",step_up_evidence=ev,step_up_signature=esig)
 r = attest(**kw)
 assert r.result is AuthResult.ALLOW

def test_policy_decision_denied():
 kw = _base_kwargs(policy_result=PolicyResult.DENY)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "POLICY_DECISION_DOES_NOT_PERMIT" in r.record.reason_code

def test_authority_delta_zero():
 r = attest(**_base_kwargs())
 assert r.record.authority_delta == 0

def test_no_frozen_implementation_changed():
 import subprocess
 changed = subprocess.check_output(['git','diff','--name-only','HEAD','--','sintra_live/l2/mission/','sintra_live/l2/memory_contract.py','sintra_live/l2/workforce_contract.py','sintra_live/l2/model_routing_contract.py','sintra_live/l2/policy_resolution_contract.py'], text=True).strip()
 assert not changed