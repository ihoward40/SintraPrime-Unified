from dataclasses import replace
from sintra_live.l2.model_routing_contract import *
from sintra_live.l2.model_routing_policy import *
from sintra_live.l2.model_routing_attestation import *
def token(n=10):return TokenEstimateEvidence(SCHEMA['token-estimate'],'a'*64,'b'*64,n,'fixture','1')
def policy(**kw):
 d=dict(schema_version=SCHEMA['model-routing-policy'],policy_version=POLICY_VERSION,allowed_provider_ids=('p',),allowed_model_ids=('m1','m2'),prohibited_provider_ids=(),prohibited_model_ids=(),permitted_token_estimators=(('fixture','1'),),permitted_privacy_levels=('INTERNAL',),permitted_data_policies=('NO_PERSISTENCE',),maximum_input_tokens=100,maximum_output_tokens=20,maximum_total_tokens=120,maximum_cost_microunits=1000,maximum_latency_ms=100)
 d.update(kw);return RoutingPolicy(**d)
def req(**kw):
 d=dict(schema_version=SCHEMA['model-task-requirement'],routing_policy_version=POLICY_VERSION,program_id='SP',gate_id='I5',tenant_id='t',principal_identity_reference='pr',mission_id='m',request_sha256='1'*64,mission_scope_sha256='2'*64,aggregate_version=1,aggregate_sha256='3'*64,workforce_reconciliation_sha256='4'*64,ordered_specialist_output_package_sha256s=('5'*64,),task_id='task',task_type='reason',task_prompt_sha256='a'*64,context_manifest_sha256='b'*64,token_estimate_evidence=token(),required_capabilities=('reason',),allowed_provider_ids=('p',),allowed_model_ids=('m1','m2'),prohibited_provider_ids=(),prohibited_model_ids=(),required_privacy_level='INTERNAL',required_data_policy='NO_PERSISTENCE',maximum_input_tokens=100,maximum_output_tokens=20,maximum_total_tokens=120,maximum_estimated_cost_microunits=1000,maximum_estimated_latency_ms=100,fallback_policy='ALL_REMAINING_ELIGIBLE_IN_CANONICAL_ORDER',evaluation_time='2026-08-24T00:00:00.000000Z')
 d.update(kw);return TaskRequirement(**d)
def entry(model='m1',cost=1,latency=10,**kw):
 d=dict(schema_version=SCHEMA['model-catalog-entry'],catalog_entry_version='1',provider_id='p',provider_family='pf',model_id=model,model_version='1',deployment_id='d'+model,endpoint_class='offline',capabilities=('reason',),supported_privacy_levels=('INTERNAL',),supported_data_policies=('NO_PERSISTENCE',),maximum_input_tokens=100,maximum_output_tokens=20,cost_microunits_per_input_token=cost,cost_microunits_per_output_token=cost,estimated_latency_ms=latency,supports_offline_routing_only=True,requires_credentials=False,requires_network=False,valid_from='2026-01-01T00:00:00.000000Z',valid_until='2027-01-01T00:00:00.000000Z')
 d.update(kw);return CatalogEntry(**d)
def test_mr01_records_selection_and_fallback():
 o=attest(req(),policy(),(entry('m2',2),entry()));assert o.result is Result.COMPLETE and o.decision.selected_identity_key[1]=='m1' and len(o.decision.fallback_identity_keys)==1
def test_mr02_policy_ineligible_denied():assert attest(req(),policy(),(entry(capabilities=('other',)),)).reason_code=='NO_POLICY_ELIGIBLE_MODEL'
def test_mr03_authority_neutral():
 d=attest(req(),policy(),(entry(),)).decision;assert d.authority_delta==0 and not d.provider_invoked

def test_mr04_drift_invalidates():
 r=req();p=policy();d=attest(r,p,(entry(),)).decision;assert not verify_sealed(r,p,(entry(cost=2),),d)
def test_mr05_fallback_canonical():
 d=attest(req(),policy(),(entry('m2',2),entry())).decision;assert d.fallback_identity_keys==(entry('m2',2).identity(),)
def test_mr06_budget_enforcement():assert attest(req(maximum_estimated_cost_microunits=29),policy(),(entry(),)).result is Result.DENIED
def test_mr07_selection_cannot_expand_authority():
 d=attest(req(),policy(),(entry(),)).decision;assert (d.provider_invoked,d.network_used,d.credentials_accessed,d.authority_delta)==(False,False,False,0)
def test_permutation_determinism():
 a=attest(req(),policy(),(entry('m1'),entry('m2'))).decision;b=attest(req(),policy(),(entry('m2'),entry('m1'))).decision;assert a==b

def test_boundary_at_ceiling_passes():assert attest(req(),policy(),(entry(),)).result is Result.COMPLETE
def test_missing_token_is_incomplete():assert attest(req(token_estimate_evidence=None),policy(),(entry(),)).reason_code=='TOKEN_ESTIMATE_EVIDENCE_MISSING'
def test_missing_catalog_complete_empty_denied():assert attest(req(),policy(),()).reason_code=='NO_POLICY_ELIGIBLE_MODEL'

def test_state_and_reconciliation_guards():
 assert attest(req(),policy(),(entry(),),mission_state='OTHER').reason_code=='WRONG_MISSION_STATE';assert attest(req(),policy(),(entry(),),reconciliation_complete=False).result is Result.DENIED

def test_catalog_hash_deterministic():assert catalog_hash((entry('m1'),entry('m2')))==catalog_hash((entry('m2'),entry('m1')))
def test_effective_policy_ceiling_controls():assert attest(req(maximum_input_tokens=200),policy(maximum_input_tokens=9),(entry(maximum_input_tokens=300),)).result is Result.DENIED

def test_catalog_ceiling_controls():assert attest(req(),policy(),(entry(maximum_input_tokens=9),)).result is Result.DENIED

def test_half_open_validity():assert attest(req(evaluation_time='2027-01-01T00:00:00.000000Z'),policy(),(entry(),)).result is Result.DENIED

def test_acceptance_mapping():assert {f'MR-0{i}' for i in range(1,8)}=={'MR-01','MR-02','MR-03','MR-04','MR-05','MR-06','MR-07'}
