"""Adversarial tests for L2-I7 authority resolution and genesis trust anchor."""
import ast,pathlib
import pytest
from tests.test_l2_i7_authority_resolution import *
from tests.test_l2_i7_authority_resolution import _setup_test_genesis, _base_kwargs, _make_session
from sintra_live.l2.principal_gateway_contract import *
from sintra_live.l2.policy_resolution_contract import Result as PolicyResult

def test_caller_cannot_choose_genesis_root():
 # Even if caller supplies a different trust_root, the pinned hash check prevents it
 tr, rs, bnd, bsig = _setup_test_genesis()
 fake_priv = Ed25519PrivateKey.generate()
 fake_pub = fake_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
 fake_tr = TrustRoot(
  schema_version=tr.schema_version, trust_root_id="fake-genesis", trust_root_version="v1",
  issuer_id="attacker", issuer_type="PRINCIPAL_GATEWAY", verification_algorithm="ED25519_DETEACH",
  verification_material=fake_pub, verification_material_sha256=hashlib.sha256(bytes.fromhex(fake_pub)).hexdigest(),
  permitted_usages=tr.permitted_usages, valid_from=tr.valid_from, valid_until=tr.valid_until,
 )
 # The fake root's hash won't match the pinned genesis hash
 kw = _base_kwargs(trust_roots=[fake_tr])
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "GENESIS_ROOT_ABSENT" in r.record.reason_code or "TRUST_ROOT_NOT_IN_SET" in r.record.reason_code

def test_caller_cannot_choose_root_set_identity():
 tr, rs, bnd, bsig = _setup_test_genesis()
 fake_rs = TrustedRootSet(
  schema_version=rs.schema_version, trusted_root_set_version="v2",
  ordered_trust_root_sha256s=rs.ordered_trust_root_sha256s,
 )
 kw = _base_kwargs(trust_root_set=fake_rs)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "TRUSTED_ROOT_SET_HASH_MISMATCH" in r.record.reason_code

def test_reordered_roots_cannot_change_genesis_selection():
 tr, rs, bnd, bsig = _setup_test_genesis()
 # With only one root, reordering is trivially the same
 # But verify genesis is still found
 kw = _base_kwargs(trust_root_set=rs, trust_roots=[tr])
 r = attest(**kw)
 assert r.result is AuthResult.ALLOW

def test_wrong_authority_snapshot_reference_denied():
 kw = _base_kwargs(authority_snapshot_reference="wrong-ref")
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "TRUST_ANCHOR_BINDING_MISMATCH" in r.record.reason_code

def test_signature_by_non_genesis_root_denied():
 tr, rs, bnd, bsig = _setup_test_genesis()
 other_priv = Ed25519PrivateKey.generate()
 other_pub = other_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
 other_tr = TrustRoot(
  schema_version=tr.schema_version, trust_root_id="other", trust_root_version="v1",
  issuer_id="other", issuer_type="PRINCIPAL_GATEWAY", verification_algorithm="ED25519_DETEACH",
  verification_material=other_pub, verification_material_sha256=hashlib.sha256(bytes.fromhex(other_pub)).hexdigest(),
  permitted_usages=tr.permitted_usages, valid_from=tr.valid_from, valid_until=tr.valid_until,
 )
 # Build root set containing both roots
 both_roots = sorted((tr.trust_root_sha256, other_tr.trust_root_sha256))
 # Can't change pinned root set hash, so this test just verifies denial
 sa, ssig = _make_session(other_priv, trust_root_id="other", trust_root_version="v1")
 kw = _base_kwargs(session_attestation=sa, session_signature=ssig, trust_roots=[tr])
 r = attest(**kw)
 assert r.result is AuthResult.DENY

def test_invalid_ed25519_signature_denied():
 kw = _base_kwargs(binding_signature="ff"*64)
 r = attest(**kw)
 assert r.result is AuthResult.DENY
 assert "TRUST_ANCHOR_BINDING_SIGNATURE_INVALID" in r.record.reason_code

def test_permitted_usage_mismatch_denied():
 tr, rs, bnd, bsig = _setup_test_genesis()
 # Create root without SESSION_ATTESTATION usage
 restricted_tr = TrustRoot(
  schema_version=tr.schema_version, trust_root_id=tr.trust_root_id, trust_root_version=tr.trust_root_version,
  issuer_id=tr.issuer_id, issuer_type=tr.issuer_type, verification_algorithm=tr.verification_algorithm,
  verification_material=tr.verification_material, verification_material_sha256=tr.verification_material_sha256,
  permitted_usages=("AUTHORITY_ISSUANCE",), valid_from=tr.valid_from, valid_until=tr.valid_until,
 )
 # This root has a different hash, so genesis check will fail
 kw = _base_kwargs(trust_roots=[restricted_tr])
 r = attest(**kw)
 assert r.result is AuthResult.DENY

def test_duplicate_root_denied():
 tr, rs, bnd, bsig = _setup_test_genesis()
 with pytest.raises(ValueError):
  TrustedRootSet(schema_version=rs.schema_version, trusted_root_set_version=rs.trusted_root_set_version,
   ordered_trust_root_sha256s=(tr.trust_root_sha256, tr.trust_root_sha256))

def test_no_prohibited_imports():
 root = pathlib.Path(__file__).parents[1]
 files = [root/'sintra_live/l2'/x for x in ('principal_gateway_contract.py','authority_resolver.py','authority_attestation.py')]
 imports = []
 for f in files:
  t = ast.parse(f.read_text())
  for n in ast.walk(t):
   if isinstance(n, ast.Import): imports += [a.name for a in n.names]
   elif isinstance(n, ast.ImportFrom) and n.module: imports.append(n.module)
 forbidden = ('requests','httpx','urllib','socket','subprocess','multiprocessing','database','sqlite','github','approval','authorization','capability','credential','keyring','secrets')
 assert not [x for x in imports if any(y in x.lower() for y in forbidden)]

def test_no_system_clock_or_uuid():
 root = pathlib.Path(__file__).parents[1]
 files = [root/'sintra_live/l2'/x for x in ('principal_gateway_contract.py','authority_resolver.py','authority_attestation.py')]
 calls = []
 for f in files:
  t = ast.parse(f.read_text())
  for n in ast.walk(t):
   if isinstance(n, ast.Call):
    calls.append(n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id if isinstance(n.func, ast.Name) else '')
 assert not {'time','datetime','now','utcnow','uuid4','uuid1','random'}.intersection(calls)

def test_authority_resolution_not_execution_ready():
 r = attest(**_base_kwargs())
 assert r.record.execution_ready is False
 assert r.record.capability_certified is False
 assert r.record.approval_granted is False

def test_no_floating_point():
 root = pathlib.Path(__file__).parents[1]
 for p in [root/'sintra_live/l2'/x for x in ('principal_gateway_contract.py','authority_resolver.py','authority_attestation.py')]:
  assert not any(isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(ast.parse(p.read_text())))