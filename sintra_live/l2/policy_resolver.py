"""Pure deterministic L2-I6 policy resolver."""
from .policy_resolution_contract import *
CATS=("MISSION","DATA","MODEL","CONSEQUENCE","CAPABILITY","EVIDENCE")
def interpret(mission_id,value,side_effect_budget):
 if value=="E0":
  if side_effect_budget!=0:raise ValueError("INCONSISTENT_CONSEQUENCE_INTERPRETATION")
  return ConsequenceInterpretation(SCHEMA['consequence-interpretation'],"sp-live-001-l2-i6-consequence-interpretation-v1",mission_id,value,"READ_ONLY","LEGACY_E0_ZERO_WRITE")
 if value in ORDER:return ConsequenceInterpretation(SCHEMA['consequence-interpretation'],"sp-live-001-l2-i6-consequence-interpretation-v1",mission_id,value,value,"DIRECT_GOVERNANCE_CLASS_IDENTITY")
 return None
def policy_set_hash(policies):
 p=sorted(policies,key=lambda x:(CATS.index(x.category),*x.identity()[1:],x.policy_record_sha256));ids=[x.identity() for x in p];hs=[x.policy_record_sha256 for x in p]
 if len(ids)!=len(set(ids)):raise ValueError("DUPLICATE_POLICY_IDENTITY")
 if len(hs)!=len(set(hs)):raise ValueError("DUPLICATE_POLICY_HASH")
 return hr(DOMAIN['policy-set'],hs)
def observe(a,evaluation_time,operation):
 if a is None:return Observation.NOT_PROVIDED
 if (a.program_id,a.gate_id,a.mission_id,a.bound_operation_sha256)!=(operation.program_id,operation.gate_id,operation.mission_id,operation.proposed_operation_sha256):raise ValueError("AUTHORITY_EVIDENCE_BINDING_INVALID")
 if a.revoked:return Observation.REVOKED
 if evaluation_time<a.valid_from:return Observation.NOT_YET_VALID
 if evaluation_time>=a.valid_until:return Observation.EXPIRED
 return Observation.STRUCTURALLY_VALID
def resolve(*,mission_id,mission_allowed,mission_prohibited,mission_side_effect_budget,mission_cost_ceiling,mission_token_ceiling,mission_latency_ceiling,mission_consequence_ceiling,operation,classification,policies,evaluation_time,authority_evidence=None,upstream_complete=True):
 ts(evaluation_time)
 if not upstream_complete:return incomplete(operation,None,classification,"","REQUIRED_UPSTREAM_EVIDENCE_MISSING",("UPSTREAM",))
 interp=interpret(mission_id,mission_consequence_ceiling,mission_side_effect_budget)
 if interp is None:return incomplete(operation,None,classification,"","CONSEQUENCE_INTERPRETATION_UNAVAILABLE",("CONSEQUENCE_INTERPRETATION",))
 if operation.mission_id!=mission_id or classification.proposed_operation_sha256!=operation.proposed_operation_sha256:return deny(operation,interp,classification,"","HASH_MISMATCH")
 try:psh=policy_set_hash(policies);obs=observe(authority_evidence,evaluation_time,operation)
 except ValueError as x:return deny(operation,interp,classification,"",str(x))
 applicable=[];ev=[]
 for p in sorted(policies,key=lambda x:(CATS.index(x.category),x.policy_id,x.policy_version,x.policy_record_sha256)):
  if not p.valid_from<=evaluation_time<p.valid_until:return deny(operation,interp,classification,psh,"POLICY_EXPIRED")
  app=not p.applicable_operations or operation.operation_type in p.applicable_operations
  e=Evaluation(SCHEMA['policy-evaluation'],p.policy_record_sha256,app,p.effect,())
  ev.append(e)
  if app:applicable.append(p)
 if set(p.category for p in policies)!=set(CATS):return incomplete(operation,interp,classification,psh,"REQUIRED_POLICY_CATEGORY_MISSING",("POLICY_CATEGORY",),ev,obs,authority_evidence)
 if any(not any(p.category==c and (not p.applicable_operations or operation.operation_type in p.applicable_operations) for p in policies) for c in CATS):return incomplete(operation,interp,classification,psh,"NO_APPLICABLE_POLICY_FOR_REQUIRED_CATEGORY",("APPLICABLE_POLICY",),ev,obs,authority_evidence)
 allowed=set(mission_allowed)
 for p in applicable:
  if p.allowed_operations:allowed &= set(p.allowed_operations)
 prohibited=set(mission_prohibited)
 for p in applicable:prohibited |= set(p.prohibited_operations)
 reasons=[]
 if operation.operation_type not in allowed or operation.operation_type in prohibited:reasons.append("OPERATION_OUTSIDE_EFFECTIVE_MISSION_SCOPE")
 se=min([mission_side_effect_budget]+[p.max_side_effects for p in applicable]);co=min([mission_cost_ceiling]+[p.max_cost for p in applicable]);to=min([mission_token_ceiling]+[p.max_tokens for p in applicable]);la=min([mission_latency_ceiling]+[p.max_latency_ms for p in applicable]);cc=min([ORDER.index(interp.i6_ceiling)]+[ORDER.index(p.max_consequence) for p in applicable]);ceil=ORDER[cc]
 if operation.requested_side_effect_count>se:reasons.append("SIDE_EFFECT_CEILING_EXCEEDED")
 if operation.requested_cost>co:reasons.append("COST_CEILING_EXCEEDED")
 if operation.requested_tokens>to:reasons.append("TOKEN_CEILING_EXCEEDED")
 if operation.requested_latency_ms>la:reasons.append("LATENCY_CEILING_EXCEEDED")
 if ORDER.index(classification.consequence_class)>cc:reasons.append("CONSEQUENCE_CEILING_EXCEEDED")
 cap=f"{operation.capability_id}:{operation.capability_version}"
 for p in applicable:
  if p.allowed_capabilities and cap not in p.allowed_capabilities:reasons.append("CAPABILITY_POLICY_PROHIBITED")
  if cap in p.prohibited_capabilities:reasons.append("CAPABILITY_POLICY_PROHIBITED")
  if set(operation.data_classifications)&set(p.prohibited_operations):reasons.append("DATA_CLASSIFICATION_PROHIBITED")
 required=set().union(*(set(p.required_evidence) for p in applicable))
 if "AUTHORITY_EVIDENCE" in required and obs is not Observation.STRUCTURALLY_VALID:reasons.append({Observation.NOT_PROVIDED:"REQUIRED_EVIDENCE_CLASS_MISSING",Observation.EXPIRED:"REQUIRED_EVIDENCE_EXPIRED",Observation.REVOKED:"REQUIRED_EVIDENCE_REVOKED",Observation.NOT_YET_VALID:"REQUIRED_EVIDENCE_NOT_YET_VALID"}[obs])
 if classification.approval_requirement=="PROHIBITED":reasons.append("CONSEQUENCE_CEILING_EXCEEDED")
 if any(p.effect=="DENY" for p in applicable):reasons.append("POLICY_EXPLICIT_DENY")
 ctx=(tuple(ev),obs,authority_evidence,se,co,to,la,ceil,evaluation_time)
 if reasons:return deny(operation,interp,classification,psh,*reasons,ctx=ctx)
 approval=classification.approval_requirement=="EXPLICIT_APPROVAL_REQUIRED" or any(p.effect=="APPROVAL_REQUIRED" for p in applicable)
 return decision(operation,interp,classification,psh,approval,ctx)
def common(operation,interp,classification,psh,ev=(),obs=Observation.NOT_PROVIDED,a=None,se=0,co=0,to=0,la=0,ceil="READ_ONLY",et=""):
 return dict(resolver_version=RESOLVER_VERSION,operation_sha256=operation.proposed_operation_sha256,interpretation_sha256=interp.consequence_interpretation_sha256 if interp else "0"*64,classification_sha256=classification.consequence_classification_sha256,policy_set_sha256=psh,evaluation_sha256s=tuple(x.policy_evaluation_sha256 for x in ev),evaluation_time=et,authority_observation=obs,authority_evidence_sha256=a.authority_evidence_sha256 if a else None,approval_required=False,capability_policy_status="PERMITTED",effective_side_effect_ceiling=se,effective_cost_ceiling=co,effective_token_ceiling=to,effective_latency_ceiling_ms=la,effective_consequence_ceiling=ceil)
def deny(operation,interp,classification,psh,*reasons,ctx=None):
 ev,obs,a,se,co,to,la,ceil,et=ctx or ((),Observation.NOT_PROVIDED,None,0,0,0,0,"READ_ONLY","");r=tuple(dict.fromkeys(reasons));x=PolicyDenial(schema_version=SCHEMA['policy-denial'],result=Result.DENY,primary_reason_code=r[0],ordered_reason_codes=r,**common(operation,interp,classification,psh,ev,obs,a,se,co,to,la,ceil,et));return Resolution(Result.DENY,x,tuple(ev))
def incomplete(operation,interp,classification,psh,reason,missing,ev=(),obs=Observation.NOT_PROVIDED,a=None,et=""):
 x=PolicyIncomplete(schema_version=SCHEMA['policy-incomplete'],result=Result.INCOMPLETE,primary_reason_code=reason,ordered_reason_codes=(reason,),missing_evidence=tuple(missing),**common(operation,interp,classification,psh,ev,obs,a,et=et));return Resolution(Result.INCOMPLETE,x,tuple(ev))
def decision(operation,interp,classification,psh,approval,ctx):
 ev,obs,a,se,co,to,la,ceil,et=ctx;r=Result.APPROVAL_REQUIRED if approval else Result.ALLOW;reason="EXPLICIT_APPROVAL_REQUIRED" if approval else "ALL_APPLICABLE_POLICIES_SATISFIED";d=common(operation,interp,classification,psh,ev,obs,a,se,co,to,la,ceil,et);d['approval_required']=approval;x=PolicyDecision(schema_version=SCHEMA['policy-decision'],result=r,primary_reason_code=reason,ordered_reason_codes=(reason,),**d);return Resolution(r,x,tuple(ev))
