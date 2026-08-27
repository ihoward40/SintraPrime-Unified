import ast,pathlib
import pytest
from tests.test_l2_i5_model_routing import *

def test_duplicate_identity_denied():assert attest(req(),policy(),(entry(),entry(cost=2))).reason_code=='DUPLICATE_MODEL_IDENTITY'
def test_network_credential_offline_denied():
 for kw in ({'requires_network':True},{'requires_credentials':True},{'supports_offline_routing_only':False}):assert attest(req(),policy(),(entry(**kw),)).result is Result.DENIED
@pytest.mark.parametrize('field,value', [('input_token_estimate',True),('input_token_estimate',-1),('input_token_estimate',2**63),('input_token_estimate',1.5)])
def test_bad_numeric_denied(field,value):
 with pytest.raises(ValueError):token(value)
def test_multiplication_overflow_denied():assert attest(req(token_estimate_evidence=token(2**62)),policy(maximum_input_tokens=2**63-1,maximum_total_tokens=2**63-1), (entry(cost=3,maximum_input_tokens=2**63-1),)).reason_code=='INTEGER_OVERFLOW'
def test_addition_overflow_denied():assert attest(req(token_estimate_evidence=token(2**63-1),maximum_output_tokens=1,maximum_total_tokens=2**63-1),policy(maximum_input_tokens=2**63-1,maximum_total_tokens=2**63-1),(entry(maximum_input_tokens=2**63-1),)).reason_code=='INTEGER_OVERFLOW'
def test_privacy_data_exact_membership():
 assert attest(req(required_privacy_level='RESTRICTED'),policy(),(entry(),)).result is Result.DENIED;assert attest(req(required_data_policy='RETENTION_ALLOWED'),policy(),(entry(),)).result is Result.DENIED
def test_prompt_context_hash_bound_token_evidence():
 with pytest.raises(ValueError):replace(token(),task_prompt_sha256='c'*64)
def test_provider_receipt_and_flags_rejected():
 d=attest(req(),policy(),(entry(),)).decision
 for kw in ({'provider_invoked':True},{'network_used':True},{'credentials_accessed':True},{'provider_receipt_sha256':'a'*64},{'authority_delta':1}):
  with pytest.raises(ValueError):replace(d,**kw)
def test_terminal_cancelled_guards():
 assert attest(req(),policy(),(entry(),),terminal=True).reason_code=='TERMINAL_MISSION';assert attest(req(),policy(),(entry(),),cancelled=True).reason_code=='CANCELLED_MISSION'
def test_nonzero_reconciliation_authority_denied():assert attest(req(),policy(),(entry(),),reconciliation_authority_delta=1).reason_code=='I4_AUTHORITY_DELTA_NONZERO'
def test_all_candidate_exclusions():
 variants=(dict(provider_id='x'),dict(model_id='x'),dict(capabilities=('x',)),dict(maximum_input_tokens=9),dict(maximum_output_tokens=19),dict(estimated_latency_ms=101),dict(valid_from='2026-08-25T00:00:00.000000Z'))
 for kw in variants:assert attest(req(),policy(),(entry(**kw),)).result is Result.DENIED
def test_hashes_change_on_requirement_policy_catalog_drift():
 r=req();p=policy();e=entry();a=attest(r,p,(e,));assert replace(r,task_id='other').requirement_sha256!=r.requirement_sha256;assert replace(p,maximum_latency_ms=99).policy_sha256!=p.policy_sha256;assert replace(e,estimated_latency_ms=11).catalog_entry_sha256!=e.catalog_entry_sha256;assert a.decision.model_decision_sha256
def test_no_prohibited_imports_or_calls():
 root=pathlib.Path(__file__).parents[1];files=[root/'sintra_live/l2'/x for x in ('model_routing_contract.py','model_routing_policy.py','model_routing_attestation.py')];imports=[];calls=[]
 for f in files:
  t=ast.parse(f.read_text())
  for n in ast.walk(t):
   if isinstance(n,ast.Import):imports += [a.name for a in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:imports.append(n.module)
   elif isinstance(n,ast.Call):calls.append(n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else '')
 forbidden=('requests','httpx','urllib','socket','subprocess','multiprocessing','provider','credential','database','sqlite','approval','authorization','capability','github','workforce_launcher','memory_retrieval','mission.store');assert not [x for x in imports if any(y in x.lower() for y in forbidden)];assert not {'open','read_text','write_text','time','datetime','uuid4','random','evaluate_transition','retrieve_memory','launch'}.intersection(calls)
def test_no_floating_point_literals():
 root=pathlib.Path(__file__).parents[1]/'sintra_live/l2'
 for p in [root/'model_routing_contract.py',root/'model_routing_policy.py',root/'model_routing_attestation.py']:
  assert not any(isinstance(n,ast.Constant) and isinstance(n.value,float) for n in ast.walk(ast.parse(p.read_text())))
def test_allow_deny_and_capability_input_must_be_canonical():
 with pytest.raises(ValueError):policy(allowed_model_ids=('m2','m1'))
 with pytest.raises(ValueError):req(required_capabilities=('z','a'))
def test_fallback_reorders_with_cost_mechanically():
 d=attest(req(),policy(),(entry('m1',3),entry('m2',1))).decision;assert d.selected_identity_key[1]=='m2' and d.fallback_identity_keys[0][1]=='m1'
def test_catalog_entry_interval_invalid():
 with pytest.raises(ValueError):entry(valid_from='2027-01-01T00:00:00.000000Z',valid_until='2027-01-01T00:00:00.000000Z')
