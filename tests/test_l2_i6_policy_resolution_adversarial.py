"""Adversarial tests for L2-I6 policy resolution."""
import ast,pathlib
import pytest
from dataclasses import replace
from tests.test_l2_i6_policy_resolution import *
from sintra_live.l2.policy_resolution_contract import *
from sintra_live.l2.policy_resolver import resolve,interpret

def test_duplicate_policy_identity_denied():
 p=base_policies();p.append(pol(category="MISSION",policy_id="p_MISSION",policy_version="1"));r=attest(**base_kwargs(policies=p));assert r.result is Result.DENY and r.record.primary_reason_code=="DUPLICATE_POLICY_IDENTITY"
def test_policy_expired_deny():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p1",effect="ALLOW",valid_from="2020-01-01T00:00:00.000000Z",valid_until="2025-01-01T00:00:00.000000Z");r=attest(**base_kwargs(policies=p));assert r.result is Result.DENY and r.record.primary_reason_code=="POLICY_EXPIRED"
def test_missing_category_incomplete():
 p=[pol(category=c,policy_id=f"p_{c}") for c in ("MISSION","DATA","MODEL","CAPABILITY","EVIDENCE")];r=attest(**base_kwargs(policies=p));assert r.result is Result.INCOMPLETE
def test_authority_evidence_binding_invalid():
 _op=op();a=AuthorityEvidence(schema_version=SCHEMA['authority-evidence'],program_id="WRONG",gate_id="I6",mission_id="m1",bound_operation_sha256=_op.proposed_operation_sha256,valid_from="2020-01-01T00:00:00.000000Z",valid_until="2099-01-01T00:00:00.000000Z")
 p=base_policies();p[5]=pol(category="EVIDENCE",policy_id="p_ev",effect="ALLOW",required_evidence=("AUTHORITY_EVIDENCE",));r=attest(**base_kwargs(operation=_op,policies=p,authority_evidence=a));assert r.result is Result.DENY and r.record.primary_reason_code=="AUTHORITY_EVIDENCE_BINDING_INVALID"
def test_revoked_evidence_required_denies():
 _op=op();a=AuthorityEvidence(schema_version=SCHEMA['authority-evidence'],program_id="SP",gate_id="I6",mission_id="m1",bound_operation_sha256=_op.proposed_operation_sha256,valid_from="2020-01-01T00:00:00.000000Z",valid_until="2099-01-01T00:00:00.000000Z",revoked=True)
 p=base_policies();p[5]=pol(category="EVIDENCE",policy_id="p_ev",effect="ALLOW",required_evidence=("AUTHORITY_EVIDENCE",));r=attest(**base_kwargs(operation=_op,policies=p,authority_evidence=a));assert r.result is Result.DENY and r.record.primary_reason_code=="REQUIRED_EVIDENCE_REVOKED" and r.record.current_authority_resolved is False
def test_expired_evidence_required_denies():
 _op=op();a=AuthorityEvidence(schema_version=SCHEMA['authority-evidence'],program_id="SP",gate_id="I6",mission_id="m1",bound_operation_sha256=_op.proposed_operation_sha256,valid_from="2020-01-01T00:00:00.000000Z",valid_until="2025-01-01T00:00:00.000000Z")
 p=base_policies();p[5]=pol(category="EVIDENCE",policy_id="p_ev",effect="ALLOW",required_evidence=("AUTHORITY_EVIDENCE",));r=attest(**base_kwargs(operation=_op,policies=p,authority_evidence=a));assert r.result is Result.DENY and r.record.primary_reason_code=="REQUIRED_EVIDENCE_EXPIRED" and r.record.current_authority_resolved is False
def test_outcome_type_mismatch_on_allow():
 d=attest(**base_kwargs())
 with pytest.raises(ValueError):replace(d.record,result=Result.DENY)
def test_outcome_type_mismatch_on_deny():
 d=attest(**base_kwargs(mission_allowed=("other",)))
 with pytest.raises(ValueError):replace(d.record,result=Result.ALLOW)
def test_injection_capability_certified():
 r=attest(**base_kwargs())
 with pytest.raises(ValueError):replace(r.record,capability_certified=True)
def test_injection_approval_granted():
 r=attest(**base_kwargs())
 with pytest.raises(ValueError):replace(r.record,approval_granted=True)
def test_injection_execution_ready():
 r=attest(**base_kwargs())
 with pytest.raises(ValueError):replace(r.record,execution_ready=True)
def test_injection_authority_delta():
 r=attest(**base_kwargs())
 with pytest.raises(ValueError):replace(r.record,authority_delta=1)
def test_drift_mission_consequence():
 r=attest(**base_kwargs());r2=attest(**base_kwargs(mission_consequence_ceiling="READ_ONLY"));assert r.record.policy_decision_sha256!=r2.record.policy_decision_sha256
def test_drift_operation_hash():
 o=op();o2=op(operation_type="other");r=attest(**base_kwargs(operation=o));r2=attest(**base_kwargs(operation=o2))
 def h(x):return getattr(x.record,'policy_decision_sha256',None) or getattr(x.record,'policy_denial_sha256',None)
 assert h(r)!=h(r2)
def test_drift_policy_set():
 r=attest(**base_kwargs());p=base_policies();p[0]=pol(category="MISSION",policy_id="p_x",effect="ALLOW");r2=attest(**base_kwargs(policies=p));assert r.record.policy_decision_sha256!=r2.record.policy_decision_sha256
def test_drift_evaluation_time():
 r=attest(**base_kwargs());r2=attest(**base_kwargs(evaluation_time="2026-08-25T00:00:00.000000Z"));assert r.record.policy_decision_sha256!=r2.record.policy_decision_sha256
def test_no_floating_point():
 root=pathlib.Path(__file__).parents[1]
 for p in [root/'sintra_live/l2'/x for x in ('policy_resolution_contract.py','policy_resolver.py','policy_attestation.py')]:
  assert not any(isinstance(n,ast.Constant) and isinstance(n.value,float) for n in ast.walk(ast.parse(p.read_text())))
def test_no_prohibited_imports_or_calls():
 root=pathlib.Path(__file__).parents[1];files=[root/'sintra_live/l2'/x for x in ('policy_resolution_contract.py','policy_resolver.py','policy_attestation.py')];imports=[];calls=[]
 for f in files:
  t=ast.parse(f.read_text())
  for n in ast.walk(t):
   if isinstance(n,ast.Import):imports+=[a.name for a in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:imports.append(n.module)
   elif isinstance(n,ast.Call):calls.append(n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else '')
 forbidden=('requests','httpx','urllib','socket','subprocess','multiprocessing','provider','credential','database','sqlite','approval','authorization','capability','github','workforce_launcher','memory_retrieval','mission.store','model_routing_policy','model_routing_attestation')
 assert not [x for x in imports if any(y in x.lower() for y in forbidden)]
 assert not {'open','read_text','write_text','time','datetime','now','uuid4','random','evaluate_transition','retrieve_memory','launch','route'}.intersection(calls)
def test_permutation_determinism():
 a=attest(**base_kwargs());b=attest(**base_kwargs(policies=list(reversed(base_policies()))));assert a.record.policy_decision_sha256==b.record.policy_decision_sha256
def test_consequence_ordering():
 assert ORDER.index("READ_ONLY")<ORDER.index("FINANCIAL")<ORDER.index("GOVERNANCE_PROTECTED")
def test_noncanonical_set_denied():
 with pytest.raises(ValueError):pol(category="MISSION",policy_id="p1",effect="ALLOW",allowed_operations=("b","a"))
def test_policy_widens_mission_denied():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p_MISSION",effect="ALLOW",allowed_operations=("other","query"));r=attest(**base_kwargs(mission_allowed=("query",),operation=op(operation_type="other"),policies=p));assert r.result is Result.DENY