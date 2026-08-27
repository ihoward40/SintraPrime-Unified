"""Pure deterministic L2-I5 model candidate evaluation and selection."""
from __future__ import annotations
from .model_routing_contract import *
REASONS=("PROVIDER_NOT_ALLOWED","PROVIDER_PROHIBITED","MODEL_NOT_ALLOWED","MODEL_PROHIBITED","REQUIRED_CAPABILITY_MISSING","PRIVACY_LEVEL_NOT_SUPPORTED","DATA_POLICY_NOT_SUPPORTED","INPUT_TOKEN_LIMIT_EXCEEDED","OUTPUT_TOKEN_LIMIT_EXCEEDED","TOTAL_TOKEN_LIMIT_EXCEEDED","ESTIMATED_COST_LIMIT_EXCEEDED","ESTIMATED_LATENCY_LIMIT_EXCEEDED","CATALOG_ENTRY_NOT_YET_VALID","CATALOG_ENTRY_EXPIRED","OFFLINE_ROUTING_NOT_SUPPORTED","NETWORK_REQUIRED","CREDENTIALS_REQUIRED")
def checked_mul(a,b):
 integer(a);integer(b)
 if a and b>MAX_INT//a:raise ValueError("INTEGER_OVERFLOW")
 return a*b
def checked_add(a,b):
 integer(a);integer(b)
 if a>MAX_INT-b:raise ValueError("INTEGER_OVERFLOW")
 return a+b
def catalog_hash(entries):
 ordered=sorted(entries,key=lambda x:(*x.identity(),x.catalog_entry_sha256));ids=[x.identity() for x in ordered]
 if len(ids)!=len(set(ids)):raise ValueError("DUPLICATE_MODEL_IDENTITY")
 hs=[x.catalog_entry_sha256 for x in ordered]
 if len(hs)!=len(set(hs)):raise ValueError("DUPLICATE_CATALOG_ENTRY_HASH")
 return hash_record(DOMAIN["MODEL-CATALOG-SET"],hs)
def evaluate(req,policy,catalog_set_sha256,e):
 token=req.token_estimate_evidence
 if token is None:raise ValueError("TOKEN_ESTIMATE_EVIDENCE_MISSING")
 inp=token.input_token_estimate;out=req.maximum_output_tokens;total=checked_add(inp,out);ic=checked_mul(inp,e.cost_microunits_per_input_token);oc=checked_mul(out,e.cost_microunits_per_output_token);cost=checked_add(ic,oc)
 max_in=min(policy.maximum_input_tokens,req.maximum_input_tokens,e.maximum_input_tokens);max_out=min(policy.maximum_output_tokens,req.maximum_output_tokens,e.maximum_output_tokens);max_total=min(policy.maximum_total_tokens,req.maximum_total_tokens);max_cost=min(policy.maximum_cost_microunits,req.maximum_estimated_cost_microunits);max_latency=min(policy.maximum_latency_ms,req.maximum_estimated_latency_ms)
 checks={"provider_allowlist":not policy.allowed_provider_ids or e.provider_id in policy.allowed_provider_ids,"provider_denylist":e.provider_id not in set(policy.prohibited_provider_ids)|set(req.prohibited_provider_ids),"model_allowlist":not policy.allowed_model_ids or e.model_id in policy.allowed_model_ids,"model_denylist":e.model_id not in set(policy.prohibited_model_ids)|set(req.prohibited_model_ids),"capability":set(req.required_capabilities)<=set(e.capabilities),"privacy":req.required_privacy_level in e.supported_privacy_levels,"data_policy":req.required_data_policy in e.supported_data_policies,"input_token":inp<=max_in,"output_token":out<=max_out,"total_token":total<=max_total,"cost":cost<=max_cost,"latency":e.estimated_latency_ms<=max_latency,"not_yet_valid":req.evaluation_time>=e.valid_from,"expired":req.evaluation_time<e.valid_until,"offline_only":e.supports_offline_routing_only,"network":not e.requires_network,"credential":not e.requires_credentials}
 names=("provider_allowlist","provider_denylist","model_allowlist","model_denylist","capability","privacy","data_policy","input_token","output_token","total_token","cost","latency","not_yet_valid","expired","offline_only","network","credential");failed=tuple(REASONS[i] for i,n in enumerate(names) if not checks[n]);pairs=tuple((n,"PASS" if checks[n] else "FAIL") for n in names)
 return CandidateEvaluation(SCHEMA["candidate-evaluation"],req.requirement_sha256,policy.policy_sha256,catalog_set_sha256,e.catalog_entry_sha256,e.identity(),pairs,ic,oc,cost,total,len(set(e.capabilities)-set(req.required_capabilities)),not failed,failed)
def order_key(pair):
 e,c=pair;return (c.excess_capability_count,c.estimated_total_cost_microunits,e.estimated_latency_ms,c.estimated_total_tokens,*e.identity(),e.catalog_entry_sha256)
def route(req,policy,entries):
 if req.token_estimate_evidence is None:return RoutingOutcome(Result.INCOMPLETE,"TOKEN_ESTIMATE_EVIDENCE_MISSING",None,())
 if (req.token_estimate_evidence.input_token_estimator_id,req.token_estimate_evidence.input_token_estimator_version) not in policy.permitted_token_estimators:return RoutingOutcome(Result.DENIED,"TOKEN_ESTIMATOR_NOT_ALLOWED",None,())
 try:ch=catalog_hash(entries);ev=tuple(evaluate(req,policy,ch,e) for e in sorted(entries,key=lambda x:(*x.identity(),x.catalog_entry_sha256)))
 except ValueError as x:return RoutingOutcome(Result.DENIED,str(x),None,())
 eligible=sorted(((e,c) for e,c in zip(sorted(entries,key=lambda x:(*x.identity(),x.catalog_entry_sha256)),ev) if c.eligible),key=order_key)
 if not eligible:return RoutingOutcome(Result.DENIED,"NO_POLICY_ELIGIBLE_MODEL",None,ev)
 selected,ce=eligible[0];fallback=eligible[1:];decision=ModelDecision(SCHEMA["model-decision"],Result.COMPLETE,req.requirement_sha256,policy.policy_sha256,ch,tuple(c.evaluation_sha256 for c in ev),selected.identity(),selected.catalog_entry_sha256,tuple(e.identity() for e,c in fallback),tuple(e.catalog_entry_sha256 for e,c in fallback),req.token_estimate_evidence.input_token_estimate,req.maximum_output_tokens,ce.estimated_total_tokens,ce.estimated_total_cost_microunits,selected.estimated_latency_ms)
 return RoutingOutcome(Result.COMPLETE,"CANONICAL_FIRST_POLICY_ELIGIBLE_CANDIDATE",decision,ev)
