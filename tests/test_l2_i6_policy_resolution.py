"""Functional tests for L2-I6 policy resolution."""
from dataclasses import replace
from sintra_live.l2.policy_resolution_contract import *
from sintra_live.l2.policy_resolver import resolve, interpret
from sintra_live.l2.policy_attestation import attest
MAX=2**63-1
def op(**kw):
 d=dict(schema_version=SCHEMA['proposed-operation'],program_id="SP",gate_id="I6",mission_id="m1",operation_type="query",capability_id="cap",capability_version="1",requested_side_effect_count=0,requested_cost=0,requested_tokens=10,requested_latency_ms=5,data_classifications=("INTERNAL",))
 d.update(kw);return Operation(**d)
def cls(**kw):
 d=dict(schema_version=SCHEMA['consequence-classification'],proposed_operation_sha256="0"*64,consequence_class="READ_ONLY",approval_requirement="NO_APPROVAL_REQUIRED")
 d.update(kw);return Classification(**d)
def pol(**kw):
 d=dict(schema_version=SCHEMA['policy-record'],policy_id="p1",policy_version="1",category="MISSION",effect="ALLOW",valid_from="2020-01-01T00:00:00.000000Z",valid_until="2099-01-01T00:00:00.000000Z")
 d.update(kw);return Policy(**d)
def base_policies():
 return [pol(category=c,policy_id=f"p_{c}",effect="ALLOW") for c in ("MISSION","DATA","MODEL","CONSEQUENCE","CAPABILITY","EVIDENCE")]
def base_kwargs(**kw):
 _op=op();d=dict(mission_id="m1",mission_allowed=("query",),mission_prohibited=(),mission_side_effect_budget=0,mission_cost_ceiling=100,mission_token_ceiling=100,mission_latency_ceiling=100,mission_consequence_ceiling="E0",operation=_op,classification=cls(proposed_operation_sha256=_op.proposed_operation_sha256),policies=base_policies(),evaluation_time="2026-08-24T00:00:00.000000Z")
 d.update(kw)
 if "operation" in kw and "classification" not in kw:d["classification"]=cls(proposed_operation_sha256=kw["operation"].proposed_operation_sha256)
 return d
def test_p01_hashes_captured():
 r=attest(**base_kwargs());assert r.record.result in (Result.ALLOW,Result.APPROVAL_REQUIRED,Result.DENY,Result.INCOMPLETE);assert all(getattr(r.record,n) is False for n in ("capability_certified","capability_available","approval_granted","current_authority_resolved","execution_ready"));assert r.record.authority_delta==0
def test_p02_informational_allow_vs_consequence_approval():
 _op=op();r=attest(**base_kwargs(operation=_op,classification=cls(proposed_operation_sha256=_op.proposed_operation_sha256)));assert r.result is Result.ALLOW
 _cls=cls(proposed_operation_sha256=_op.proposed_operation_sha256,consequence_class="EXTERNAL_COMMUNICATION",approval_requirement="EXPLICIT_APPROVAL_REQUIRED")
 r2=attest(**base_kwargs(operation=_op,classification=_cls,mission_consequence_ceiling="EXTERNAL_COMMUNICATION"));assert r2.result is Result.APPROVAL_REQUIRED and r2.record.approval_required
def test_p03_scope_conflict_deny():
 r=attest(**base_kwargs(mission_allowed=("other",)));assert r.result is Result.DENY and r.record.primary_reason_code=="OPERATION_OUTSIDE_EFFECTIVE_MISSION_SCOPE"
def test_p04_authority_evidence_required_denies():
 p=base_policies();p[5]=pol(category="EVIDENCE",policy_id="p_ev",effect="ALLOW",required_evidence=("AUTHORITY_EVIDENCE",));r=attest(**base_kwargs(policies=p));assert r.result is Result.DENY and r.record.primary_reason_code=="REQUIRED_EVIDENCE_CLASS_MISSING"
def test_p05_child_exceeds_budget():
 r=attest(**base_kwargs(operation=op(requested_side_effect_count=1)));assert r.result is Result.DENY and "SIDE_EFFECT_CEILING_EXCEEDED" in r.record.ordered_reason_codes
def test_p06_authority_conversion_denied():
 from dataclasses import replace as rp
 r=attest(**base_kwargs())
 with __import__("pytest").raises(ValueError):rp(r.record,capability_certified=True)
 with __import__("pytest").raises(ValueError):rp(r.record,approval_granted=True)
 with __import__("pytest").raises(ValueError):rp(r.record,current_authority_resolved=True)
def test_p07_deterministic():
 a=attest(**base_kwargs());b=attest(**base_kwargs(policies=list(reversed(base_policies()))));assert a.record.policy_decision_sha256==b.record.policy_decision_sha256
def test_consequence_direct_identity():
 for c in Consequence:
  i=interpret("m",c.value,0);assert i.i6_ceiling==c.value and i.basis_code=="DIRECT_GOVERNANCE_CLASS_IDENTITY"
def test_consequence_e0_legacy():
 i=interpret("m","E0",0);assert i.i6_ceiling=="READ_ONLY" and i.basis_code=="LEGACY_E0_ZERO_WRITE"
def test_consequence_e0_nonzero_denied():
 import pytest
 with pytest.raises(ValueError):interpret("m","E0",1)
def test_consequence_unknown_incomplete():
 i=interpret("m","UNKNOWN",0);assert i is None
def test_consequence_no_case_variation():
 assert interpret("m","e0",0) is None;assert interpret("m","E01",0) is None;assert interpret("m","0",0) is None;assert interpret("m","E0 ",0) is None;assert interpret("m","read_only",0) is None
def test_deny_plus_allow_is_deny():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p_d",effect="DENY");r=attest(**base_kwargs(policies=p));assert r.result is Result.DENY
def test_deny_plus_approval_is_deny():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p_d",effect="DENY");p[1]=pol(category="DATA",policy_id="p_a",effect="APPROVAL_REQUIRED");r=attest(**base_kwargs(policies=p));assert r.result is Result.DENY
def test_allow_plus_approval_is_approval():
 p=base_policies();p[1]=pol(category="DATA",policy_id="p_a",effect="APPROVAL_REQUIRED");r=attest(**base_kwargs(policies=p));assert r.result is Result.APPROVAL_REQUIRED
def test_mission_narrows_policy():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p_MISSION",effect="ALLOW",allowed_operations=("other",));r=attest(**base_kwargs(mission_allowed=("query",),policies=p));assert r.result is Result.DENY
def test_budget_at_ceiling_passes():
 r=attest(**base_kwargs(operation=op(requested_tokens=100),mission_token_ceiling=100));assert r.result is Result.ALLOW
def test_budget_above_ceiling_denied():
 r=attest(**base_kwargs(operation=op(requested_tokens=101),mission_token_ceiling=100));assert r.result is Result.DENY and "TOKEN_CEILING_EXCEEDED" in r.record.ordered_reason_codes
def test_policy_ceiling_lower_controls():
 p=base_policies();p[0]=pol(category="MISSION",policy_id="p1",effect="ALLOW",max_tokens=50);r=attest(**base_kwargs(operation=op(requested_tokens=60),mission_token_ceiling=100,policies=p));assert r.result is Result.DENY
def test_outcome_record_types():
 a=attest(**base_kwargs());assert isinstance(a.record,PolicyDecision)
 d=attest(**base_kwargs(mission_allowed=("other",)));assert isinstance(d.record,PolicyDenial)
 from dataclasses import replace as rp
 p=base_policies();p[1]=pol(category="DATA",policy_id="p_a",effect="APPROVAL_REQUIRED");ap=attest(**base_kwargs(policies=p));assert isinstance(ap.record,PolicyDecision)
 inc=attest(**base_kwargs(upstream_complete=False));assert isinstance(inc.record,PolicyIncomplete)
def test_no_authority_evidence_unrequired():
 r=attest(**base_kwargs());assert r.record.authority_observation is Observation.NOT_PROVIDED and r.result is Result.ALLOW
def test_expired_evidence_not_required():
 _op=op();a=AuthorityEvidence(schema_version=SCHEMA['authority-evidence'],program_id="SP",gate_id="I6",mission_id="m1",bound_operation_sha256=_op.proposed_operation_sha256,valid_from="2020-01-01T00:00:00.000000Z",valid_until="2025-01-01T00:00:00.000000Z");r=attest(**base_kwargs(operation=_op,authority_evidence=a));assert r.record.authority_observation is Observation.EXPIRED and r.result is Result.ALLOW
def test_capability_permitted_not_certified():
 r=attest(**base_kwargs());assert r.record.capability_policy_status=="PERMITTED" and r.record.capability_certified is False and r.record.capability_available is False
def test_approval_required_not_granted():
 p=base_policies();p[1]=pol(category="DATA",policy_id="p_a",effect="APPROVAL_REQUIRED");r=attest(**base_kwargs(policies=p));assert r.record.approval_required and not r.record.approval_granted
def test_missing_upstream_is_incomplete():
 r=attest(**base_kwargs(upstream_complete=False));assert r.result is Result.INCOMPLETE and isinstance(r.record,PolicyIncomplete)
def test_consequence_ceiling_exceeded():
 _op=op();_cls=cls(proposed_operation_sha256=_op.proposed_operation_sha256,consequence_class="FINANCIAL",approval_requirement="EXPLICIT_APPROVAL_REQUIRED");r=attest(**base_kwargs(operation=_op,classification=_cls,mission_consequence_ceiling="EXTERNAL_COMMUNICATION"));assert r.result is Result.DENY and "CONSEQUENCE_CEILING_EXCEEDED" in r.record.ordered_reason_codes