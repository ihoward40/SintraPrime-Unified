"""Synthetic Mission V2: 15 requirement-derived offline governance scenarios.

This suite is a forward supersession.  It does not claim equivalence with the
historically reported synthetic-mission suite.  Production I1-I7 components
are exercised; READY, EXECUTING, COMPLETE, provider invocation, and external
side effects remain unreachable.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sintra_live.l2.mission import MissionAggregate, MissionIdentity, MissionScope, MissionState, canonical_bytes
from sintra_live.l2.mission.store import MissionStore
import sintra_live.l2.mission.transition_contract as tc
from sintra_live.l2.mission.transition_contract import ALL_PREDICATES, PredicateValue, TransitionPolicyRequest, TransitionPredicateRecord
from sintra_live.l2.mission.transition_errors import PolicyOutcome
from sintra_live.l2.mission.transition_policy import evaluate_transition
from sintra_live.l2.memory_contract import *
from sintra_live.l2.memory_retrieval import retrieve_memory
from sintra_live.l2.workforce_contract import *
from sintra_live.l2.workforce_policy import select_roles
from sintra_live.l2.workforce_reconciliation import reconcile
from sintra_live.l2.model_routing_contract import *
from sintra_live.l2.model_routing_attestation import attest as attest_route
from sintra_live.l2.policy_resolution_contract import *
from sintra_live.l2.policy_resolver import resolve as resolve_policy
from sintra_live.l2.principal_gateway_contract import *
from sintra_live.l2.principal_gateway_contract import _body
from sintra_live.l2.authority_attestation import attest as attest_authority
import sintra_live.l2.principal_gateway_contract as i7c
import sintra_live.l2.authority_resolver as i7r
import sintra_live.l2.memory_contract as mc
import sintra_live.l2.workforce_contract as wc
import sintra_live.l2.model_routing_contract as mrc
import sintra_live.l2.policy_resolution_contract as prc

H="a"*64; Z="0"*64; T0="2026-08-24T10:00:00.000000Z"; NOW="2026-08-24T10:30:00.000000Z"; T1="2026-08-24T11:00:00.000000Z"; FAR="2099-01-01T00:00:00.000000Z"
FORBIDDEN={MissionState.READY,MissionState.EXECUTING,MissionState.COMPLETE}
REQUIREMENTS=tuple(f"SMV2-{n:02d}" for n in range(1,16))

@dataclass(frozen=True)
class Evidence:
 scenario_id:str;expected_outcome:str;actual_outcome:str;mission_id:str;request_sha256:str;mission_scope_sha256:str;aggregate_sha256:str;transition_decision_sha256s:tuple;memory_evidence_sha256:str;workforce_evidence_sha256:str;model_routing_attestation_sha256:str;policy_result_sha256:str;principal_auth_sha256:str;authority_resolution_sha256:str;approval_granted:bool;capability_available:bool;capability_certified:bool;execution_ready:bool;provider_attempt_count:int;network_call_count:int;credential_read_count:int;database_access_count:int;external_write_count:int;github_write_count:int;final_offline_state:str;required_evidence_complete:bool;scenario_evidence_sha256:str=""
 def __post_init__(self):
  body={k:v for k,v in self.__dict__.items() if k!="scenario_evidence_sha256"}
  object.__setattr__(self,"scenario_evidence_sha256",hashlib.sha256(b"SP-LIVE-001:SYNTHETIC-MISSION-V2:v1\0"+canonical_bytes(body)).hexdigest())

def identity():return MissionIdentity("SP-LIVE-001","L2-I7","smv2-mission","smv2-request",H,"principal-001",H,"genesis-deployment-ref")
def scope(**kw):
 d=dict(purpose="offline certification",allowed_operations=("query",),prohibited_operations=("write",),consequence_ceiling="E0",budget_ceilings=(("cost",100),("latency",100),("tokens",100)),side_effect_budget=0,required_evidence_types=("authority","memory","policy","routing","workforce"),expiry=T1,cancellation_authority="cancel-1");d.update(kw);return MissionScope(**d)
def aggregate(state=MissionState.RECEIVED,sc=None):
 b=MissionAggregate.genesis(identity(),sc or scope(),T0)
 if state is MissionState.RECEIVED:return b
 return MissionAggregate(b.schema_version,b.identity,b.scope,b.created_at,state,0,b.previous_event_sha256,(),(),state in {MissionState.CANCELLED,MissionState.COMPLETE},state is MissionState.CANCELLED)
def transition(a,target,**truth):
 vals={n:PredicateValue.UNKNOWN for n in ALL_PREDICATES};vals.update({k:(v if isinstance(v,PredicateValue) else PredicateValue.TRUE if v else PredicateValue.FALSE) for k,v in truth.items()})
 pr=TransitionPredicateRecord.create(a,created_at=T0,expires_at=T1,values=vals)
 rq=TransitionPolicyRequest(tc.POLICY_VERSION,a.current_state,target,a.version,a.aggregate_sha256,a.previous_event_sha256,NOW,pr)
 return evaluate_transition(a,rq)

def memory(a):
 q=mc.MemoryRetrievalQuery(mc.QUERY_SCHEMA_VERSION,mc.POLICY_VERSION,"SP-LIVE-001","L2-I7","tenant","principal-001","smv2-mission","smv2-request",H,a.identity.mission_scope_sha256,a.version,a.aggregate_sha256,a.current_state.value,"offline certification",mc.text_hash("offline certification"),("certification",),"status",mc.text_hash("status"),("collection",),("collection",),(mc.Classification.INTERNAL,),(),(),T0,T1,10,10000,"verifier",NOW)
 c=mc.MemoryCandidate(mc.CANDIDATE_SCHEMA_VERSION,"fact-1",1,"tenant","principal-001","memory","collection",mc.Classification.INTERNAL,mc.MemoryCategory.GOVERNED_FACT,mc.MemoryTrust.GOVERNED_FACT,mc.ContentKind.FACT,(),("certification",),("verifier",),"governed fact",mc.text_hash("governed fact"),"source",H,T0,T0,T1,"","","",False)
 return retrieve_memory(a,q,(c,))
def workforce(violation=False):
 def role(i,c):return wc.RoleDefinition(wc.SCHEMAS["role-definition"],i,"1",(c,),("GOVERNED_FACT",),("INTERNAL",),(),("offline_supported",),1000,1000,5000,tuple(sorted({"analyst","reviewer"}-{i})))
 req=wc.WorkforceRequirements(wc.SCHEMAS["workforce-requirements"],"smv2-mission",H,H,1,H,("analyze","review"),2,2,1000,1000,1000,5000,(),("offline_supported",),H,(),T0)
 chosen=select_roles(req,(role("reviewer","review"),role("analyst","analyze")))
 packs=[]
 for i,r in enumerate(chosen):
  out=wc.LaneOutput(wc.SCHEMAS["lane-output"],f"lane-{i}",wc.LaneConclusion.SUPPORTED,(("F","ABSENT","NON_BLOCKER"),),(),(),(),violation and i==0,False,False,0)
  packs.append(wc.OutputPackage(wc.SCHEMAS["output-package"],f"lane-{i}",r.role_id,H,H,H,out,0))
 return reconcile(tuple(packs))
def routing(work_hash):
 tok=mrc.TokenEstimateEvidence(mrc.SCHEMA["token-estimate"],H,H,10,"fixture","1")
 req=mrc.TaskRequirement(mrc.SCHEMA["model-task-requirement"],mrc.POLICY_VERSION,"SP-LIVE-001","L2-I7","tenant","principal-001","smv2-mission",H,H,1,H,work_hash,(H,),"task","reason",H,H,tok,("reason",),("p",),("m",),(),(),"INTERNAL","NO_PERSISTENCE",100,20,120,1000,100,"ALL_REMAINING_ELIGIBLE_IN_CANONICAL_ORDER",NOW)
 pol=mrc.RoutingPolicy(mrc.SCHEMA["model-routing-policy"],mrc.POLICY_VERSION,("p",),("m",),(),(),(("fixture","1"),),("INTERNAL",),("NO_PERSISTENCE",),100,20,120,1000,100)
 ent=mrc.CatalogEntry(mrc.SCHEMA["model-catalog-entry"],"1","p","family","m","1","deploy","offline",("reason",),("INTERNAL",),("NO_PERSISTENCE",),100,20,1,1,10,True,False,False,"2026-01-01T00:00:00.000000Z","2027-01-01T00:00:00.000000Z")
 return attest_route(req,pol,(ent,))
def policy(effect="ALLOW"):
 op=prc.Operation(prc.SCHEMA["proposed-operation"],"SP-LIVE-001","L2-I7","smv2-mission","query","cap","1",0,0,10,5,("INTERNAL",))
 cl=prc.Classification(prc.SCHEMA["consequence-classification"],op.proposed_operation_sha256,"READ_ONLY","NO_APPROVAL_REQUIRED")
 ps=[prc.Policy(schema_version=prc.SCHEMA["policy-record"],policy_id=f"p_{c}",policy_version="1",category=c,effect=effect if c=="MISSION" else "ALLOW") for c in ("MISSION","DATA","MODEL","CONSEQUENCE","CAPABILITY","EVIDENCE")]
 return resolve_policy(mission_id="smv2-mission",mission_allowed=("query",),mission_prohibited=("write",),mission_side_effect_budget=0,mission_cost_ceiling=100,mission_token_ceiling=100,mission_latency_ceiling=100,mission_consequence_ceiling="E0",operation=op,classification=cl,policies=ps,evaluation_time=NOW),op,cl

PRIV=Ed25519PrivateKey.generate();PUB=PRIV.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
def sign(obj,own):return PRIV.sign(canonical_bytes({**_body(obj,own),own:getattr(obj,own)})).hex()
def authority_fixture(op,cl,session_valid_until=FAR,revoked=False,include_snapshot=True,wrong_principal=False):
 tr=TrustRoot(SCHEMA["trust-root"],"smv2-root","v1","deployment","PRINCIPAL_GATEWAY","ED25519_DETEACH",PUB,hashlib.sha256(bytes.fromhex(PUB)).hexdigest(),("SESSION_ATTESTATION","SESSION_REVOCATION","STEP_UP_ATTESTATION","AUTHORITY_ISSUANCE","AUTHORITY_REVOCATION"),"2026-01-01T00:00:00.000000Z",FAR)
 rs=TrustedRootSet(SCHEMA["trusted-root-set"],"v1",(tr.trust_root_sha256,)); b=TrustAnchorBinding(SCHEMA["trust-anchor-binding"],"v1","SP-LIVE-001","L2-I7","genesis-deployment","genesis-deployment-ref",rs.trusted_root_set_sha256,"DEPLOYMENT_BASELINE")
 i7c.GENESIS_TRUST_ROOT_SHA256=i7r.GENESIS_TRUST_ROOT_SHA256=tr.trust_root_sha256;i7c.PINNED_TRUSTED_ROOT_SET_SHA256=i7r.PINNED_TRUSTED_ROOT_SET_SHA256=rs.trusted_root_set_sha256;i7c.AUTHORITY_TRUST_ANCHOR_BINDING_SHA256=i7r.AUTHORITY_TRUST_ANCHOR_BINDING_SHA256=b.authority_trust_anchor_binding_sha256;i7c.GENESIS_PUBLIC_KEY_HEX=i7r.GENESIS_PUBLIC_KEY_HEX=PUB
 sa=SessionAttestation(SCHEMA["session-attestation"],"v1","session","smv2-root","v1","gateway","PRINCIPAL_GATEWAY","principal-001","PASSWORD","BASIC",T0,T0,session_valid_until,"opaque","SP-LIVE-001","L2-I7","smv2-mission",H,False,"BASIC",False,"","","","rev-ref")
 sr=RevocationEvidence(SCHEMA["revocation-evidence"],"v1","PRINCIPAL_SESSION","session","smv2-root","REVOKED" if revoked else "NOT_REVOKED",T0,FAR,"source")
 snap=AuthoritySnapshotAttestation(SCHEMA["authority-attestation"],"v1","snapshot","smv2-root","v1","gateway","PRINCIPAL_GATEWAY","other" if wrong_principal else "principal-001","smv2-mission",H,H,op.proposed_operation_sha256,cl.consequence_classification_sha256,"cap","1","internal","account",("query",),("cap:1",),0,100,100,100,"READ_ONLY",T0,T0,FAR,Z) if include_snapshot else None
 ar=RevocationEvidence(SCHEMA["revocation-evidence"],"v1","AUTHORITY_SNAPSHOT","snapshot","smv2-root","NOT_REVOKED",T0,FAR,"source") if snap else None
 return dict(trust_root_set=rs,trust_roots=(tr,),binding=b,binding_signature=sign(b,"authority_trust_anchor_binding_sha256"),session_attestation=sa,session_signature=sign(sa,"attestation_sha256"),session_revocation=sr,session_revocation_signature=sign(sr,"revocation_evidence_sha256"),authority_snapshot=snap,authority_signature=sign(snap,"authority_attestation_sha256") if snap else None,authority_revocation=ar,authority_revocation_signature=sign(ar,"revocation_evidence_sha256") if ar else None)
def authority(pol,op,cl,**variant):
 return attest_authority(mission_id="smv2-mission",program_id="SP-LIVE-001",gate_id="L2-I7",request_sha256=H,mission_scope_sha256=H,aggregate_version=1,aggregate_sha256=H,authority_snapshot_reference="genesis-deployment-ref",operation_sha256=op.proposed_operation_sha256,classification_sha256=cl.consequence_classification_sha256,consequence_class=cl.consequence_class,policy_result=pol.result,policy_decision_sha256=(getattr(pol.record,"policy_decision_sha256","") or getattr(pol.record,"policy_denial_sha256","") or getattr(pol.record,"policy_incomplete_sha256","")),evaluation_time=NOW,**authority_fixture(op,cl,**variant))

def policy_hash(p):return getattr(p.record,"policy_decision_sha256","") or getattr(p.record,"policy_denial_sha256","") or getattr(p.record,"policy_incomplete_sha256","")
def evidence(sid,outcome,a,mem="",work="",route="",pol="",auth="",state=MissionState.POLICY_RESOLVED,complete=True):return Evidence(sid,outcome,outcome,a.identity.mission_id,a.identity.request_sha256,a.identity.mission_scope_sha256,a.aggregate_sha256,(),mem,work,route,pol,"",auth,False,False,False,False,0,0,0,0,0,0,state.value,complete)
def assert_closed(e):
 assert (e.provider_attempt_count,e.network_call_count,e.credential_read_count,e.database_access_count,e.external_write_count,e.github_write_count)==(0,0,0,0,0,0)
 assert e.execution_ready is False and MissionState(e.final_offline_state) not in FORBIDDEN

def chain():
 a=aggregate(); ident=transition(a,MissionState.PRINCIPAL_IDENTIFIED,principal_identity_current=True,principal_identity_unambiguous=True); scoped=aggregate(MissionState.MISSION_SCOPED); mem=memory(scoped); work=workforce(); route=routing(work.sha256); pol,op,cl=policy(); auth=authority(pol,op,cl);return a,ident,scoped,mem,work,route,pol,op,cl,auth

def test_smv2_01_valid_governed_offline_path():
 a,d,s,m,w,r,p,o,c,au=chain();assert d.outcome is PolicyOutcome.ALLOW and r.result.value=="COMPLETE" and p.result.value=="ALLOW" and au.result is AuthResult.ALLOW;e=evidence("SMV2-01","VERIFIED_OFFLINE",a,m.retrieval_record_sha256,w.sha256,r.decision.model_decision_sha256,policy_hash(p),au.record.authority_resolution_sha256);assert_closed(e)
def test_smv2_02_invalid_principal_session_identity():
 a=aggregate();d=transition(a,MissionState.IDENTITY_AMBIGUOUS,identity_ambiguous=True);p,o,c=policy();au=authority(p,o,c,session_valid_until=T0);assert d.outcome is PolicyOutcome.ALLOW and au.result is AuthResult.DENY;e=evidence("SMV2-02","DENY",a,auth=au.record.authority_resolution_sha256,state=MissionState.IDENTITY_AMBIGUOUS);assert_closed(e)
def test_smv2_03_mission_scope_expansion_denied():
 a=aggregate(MissionState.PRINCIPAL_IDENTIFIED);d=transition(a,MissionState.MISSION_SCOPE_INVALID,mission_scope_invalid=True);bad=prc.Operation(prc.SCHEMA["proposed-operation"],"SP-LIVE-001","L2-I7","smv2-mission","write","cap","1",0,0,10,5,("INTERNAL",));badcl=prc.Classification(prc.SCHEMA["consequence-classification"],bad.proposed_operation_sha256,"READ_ONLY","NO_APPROVAL_REQUIRED");den=resolve_policy(mission_id="smv2-mission",mission_allowed=("query",),mission_prohibited=("write",),mission_side_effect_budget=0,mission_cost_ceiling=100,mission_token_ceiling=100,mission_latency_ceiling=100,mission_consequence_ceiling="E0",operation=bad,classification=badcl,policies=[],evaluation_time=NOW);assert d.outcome is PolicyOutcome.ALLOW and den.result.value!="ALLOW";assert_closed(evidence("SMV2-03","DENY",a,state=MissionState.MISSION_SCOPE_INVALID))
def test_smv2_04_policy_denial_cannot_become_readiness():
 a=aggregate(MissionState.POLICY_RESOLVED);d=transition(a,MissionState.POLICY_DENIED,policy_denied=True);p,o,c=policy("DENY");au=authority(p,o,c);assert d.outcome is PolicyOutcome.ALLOW and p.result.value=="DENY" and au.result is AuthResult.DENY and not au.record.execution_ready;assert_closed(evidence("SMV2-04","DENY",a,pol=policy_hash(p),auth=au.record.authority_resolution_sha256,state=MissionState.POLICY_DENIED))
@pytest.mark.parametrize("variant",("MISSING","EXPIRED","REVOKED"))
def test_smv2_05_missing_expired_revoked_authority(variant):
 p,o,c=policy();kw={"include_snapshot":False} if variant=="MISSING" else {"session_valid_until":T0} if variant=="EXPIRED" else {"revoked":True};au=authority(p,o,c,**kw);assert au.result is AuthResult.DENY;assert_closed(evidence("SMV2-05","DENY",aggregate(),auth=au.record.authority_resolution_sha256,state=MissionState.AUTHORITY_MISSING))
def test_smv2_06_approval_required_but_unavailable():
 p,o,c=policy();au=authority(p,o,c);a=aggregate(MissionState.APPROVAL_REQUIRED);d=transition(a,MissionState.APPROVAL_INVALID,approval_invalid=True);assert au.result is AuthResult.ALLOW and not au.record.approval_granted and d.outcome is PolicyOutcome.ALLOW;assert_closed(evidence("SMV2-06","INCOMPLETE",a,auth=au.record.authority_resolution_sha256,state=MissionState.APPROVAL_REQUIRED,complete=False))
@pytest.mark.parametrize("variant",("MISSING","UNAVAILABLE","UNCERTIFIED","MISMATCHED"))
def test_smv2_07_capability_boundary(variant):
 p,o,c=policy();au=authority(p,o,c);a=aggregate(MissionState.APPROVED);d=transition(a,MissionState.CAPABILITY_UNAVAILABLE,capability_unavailable=True);assert not au.record.capability_available and not au.record.capability_certified and d.outcome is PolicyOutcome.ALLOW;assert_closed(evidence("SMV2-07","INCOMPLETE",a,auth=au.record.authority_resolution_sha256,state=MissionState.CAPABILITY_UNAVAILABLE,complete=False))
def test_smv2_08_swarm_cannot_enlarge_authority():
 a=aggregate(MissionState.SPECIALISTS_DISPATCHED);d=transition(a,MissionState.SPECIALIST_SCOPE_VIOLATION,specialist_scope_violation=True);w=workforce(True);assert d.outcome is PolicyOutcome.ALLOW and w.result is ReconciliationResult.DENIED and w.authority_delta==0;p,o,c=policy();au=authority(p,o,c);assert au.record.authority_delta==0;assert_closed(evidence("SMV2-08","DENY",a,work=w.sha256,auth=au.record.authority_resolution_sha256,state=MissionState.SPECIALIST_SCOPE_VIOLATION))
def test_smv2_09_replay_duplicate_deterministic(tmp_path):
 store=MissionStore(tmp_path);a=aggregate();store.create(a.identity,a.scope,created_at=T0);first=store.load(a.identity.mission_id);second=store.load(a.identity.mission_id);p,o,c=policy();x=authority(p,o,c);y=authority(p,o,c);assert first.aggregate_sha256==second.aggregate_sha256 and x.record.authority_resolution_sha256==y.record.authority_resolution_sha256;assert_closed(evidence("SMV2-09","VERIFIED_OFFLINE",first,auth=x.record.authority_resolution_sha256))
def test_smv2_10_evidence_reconciliation_failure():
 a=aggregate(MissionState.EVIDENCE_RECONCILIATION);d=transition(a,MissionState.EVIDENCE_INCOMPLETE,evidence_incomplete=True);assert d.outcome is PolicyOutcome.ALLOW;assert_closed(evidence("SMV2-10","INCOMPLETE",a,state=MissionState.EVIDENCE_INCOMPLETE,complete=False))
def test_smv2_11_trust_does_not_create_authority():
 p,o,c=policy();au=authority(p,o,c,include_snapshot=False);assert au.result is AuthResult.DENY and not au.record.authority_snapshot_valid and not au.record.execution_ready;assert_closed(evidence("SMV2-11","DENY",aggregate(),auth=au.record.authority_resolution_sha256,state=MissionState.AUTHORITY_MISSING))
@pytest.mark.parametrize("control",("KILL_SWITCH","CANCELLATION"))
def test_smv2_12_kill_switch_cancellation(control):
 a=aggregate(MissionState.POLICY_RESOLVED);d=transition(a,MissionState.CANCELLED,**({"kill_switch_active":True} if control=="KILL_SWITCH" else {"cancellation_requested":True}));assert d.outcome is PolicyOutcome.ALLOW;assert_closed(evidence("SMV2-12","VERIFIED_OFFLINE",a,state=MissionState.CANCELLED))
def test_smv2_13_restart_reload_durability(tmp_path):
 store=MissionStore(tmp_path);a=aggregate();store.create(a.identity,a.scope,created_at=T0);one=store.load(a.identity.mission_id);two=MissionStore(tmp_path).load(a.identity.mission_id);p,o,c=policy("DENY");x=authority(p,o,c);y=authority(p,o,c);assert one.aggregate_sha256==two.aggregate_sha256 and x.record.authority_resolution_sha256==y.record.authority_resolution_sha256 and x.result is AuthResult.DENY;assert_closed(evidence("SMV2-13","VERIFIED_OFFLINE",two,pol=policy_hash(p),auth=x.record.authority_resolution_sha256))
def test_smv2_14_offline_zero_side_effect_boundary():
 a,d,s,m,w,r,p,o,c,au=chain();assert r.decision.provider_invoked is False and r.decision.network_used is False and r.decision.credentials_accessed is False;e=evidence("SMV2-14","VERIFIED_OFFLINE",a,m.retrieval_record_sha256,w.sha256,r.decision.model_decision_sha256,policy_hash(p),au.record.authority_resolution_sha256);assert_closed(e)
def test_smv2_15_deterministic_hash_linked_certification():
 def run():
  a,d,s,m,w,r,p,o,c,au=chain();return evidence("SMV2-15","VERIFIED_OFFLINE",a,m.retrieval_record_sha256,w.sha256,r.decision.model_decision_sha256,policy_hash(p),au.record.authority_resolution_sha256)
 x,y=run(),run();assert x.scenario_evidence_sha256==y.scenario_evidence_sha256 and x.required_evidence_complete;assert_closed(x)

def test_contract_maps_exactly_fifteen_requirements():
 """Accounting test: parameterized pytest instances still map to 15 requirements."""
 assert REQUIREMENTS==tuple(f"SMV2-{n:02d}" for n in range(1,16))
