"""Immutable, canonical L2-I5 offline model-routing records."""
from __future__ import annotations
import hashlib,re,unicodedata
from dataclasses import dataclass,fields
from enum import Enum
from typing import Any,Mapping,Tuple
from sintra_live.l2.mission.model import canonical_bytes
MAX_INT=2**63-1
POLICY_VERSION="sp-live-001-l2-i5-routing-policy-v1"
SCHEMA={n:f"sp-live-001-l2-i5-{n}-v1" for n in ("token-estimate","model-task-requirement","model-catalog-entry","model-catalog-set","model-routing-policy","candidate-evaluation","model-decision","routing-denial","routing-incomplete")}
DOMAIN={n:f"SP-LIVE-001:L2:I5:{n}:v1\0".encode() for n in ("MODEL-TOKEN-ESTIMATE","MODEL-TASK-REQUIREMENT","MODEL-CATALOG-ENTRY","MODEL-CATALOG-SET","MODEL-ROUTING-POLICY","CANDIDATE-EVALUATION","MODEL-DECISION","ROUTING-DENIAL","ROUTING-INCOMPLETE")}
class PrivacyLevel(str,Enum):PUBLIC="PUBLIC";INTERNAL="INTERNAL";CONFIDENTIAL="CONFIDENTIAL";RESTRICTED="RESTRICTED"
class DataPolicy(str,Enum):NO_PERSISTENCE="NO_PERSISTENCE";TRANSIENT_PROCESSING="TRANSIENT_PROCESSING";RETENTION_ALLOWED="RETENTION_ALLOWED"
class Result(str,Enum):COMPLETE="COMPLETE";INCOMPLETE="INCOMPLETE";DENIED="DENIED"
def _v(x):
 if isinstance(x,Enum):return x.value
 if isinstance(x,tuple):return [_v(y) for y in x]
 if hasattr(x,"to_dict"):return x.to_dict()
 return x
def _body(x):return {f.name:_v(getattr(x,f.name)) for f in fields(x) if not f.name.endswith("sha256") or f.name in ("task_prompt_sha256","context_manifest_sha256","request_sha256","mission_scope_sha256","aggregate_sha256","workforce_reconciliation_sha256","routing_policy_sha256","model_catalog_set_sha256","catalog_entry_sha256","requirement_sha256","token_estimate_evidence_sha256")}
def hash_record(domain,body):return hashlib.sha256(domain+canonical_bytes(body)).hexdigest()
def integer(x):
 if isinstance(x,bool) or not isinstance(x,int) or x<0 or x>MAX_INT:raise ValueError("INVALID_INTEGER")
 return x
def sset(x):
 t=tuple(x)
 if t!=tuple(sorted(set(t))):raise ValueError("NONCANONICAL_SET")
 return t
def text(x):
 if not isinstance(x,str) or not x or unicodedata.normalize("NFC",x)!=x:raise ValueError("INVALID_TEXT")
 return x
def timestamp(x):
 if not isinstance(x,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z",x):raise ValueError("INVALID_TIME")
 return x
@dataclass(frozen=True)
class TokenEstimateEvidence:
 schema_version:str;task_prompt_sha256:str;context_manifest_sha256:str;input_token_estimate:int;input_token_estimator_id:str;input_token_estimator_version:str;input_token_estimate_sha256:str=""
 def __post_init__(self):
  integer(self.input_token_estimate);text(self.input_token_estimator_id);text(self.input_token_estimator_version);h=hash_record(DOMAIN["MODEL-TOKEN-ESTIMATE"],_body(self));
  if self.input_token_estimate_sha256 and self.input_token_estimate_sha256!=h:raise ValueError("TOKEN_ESTIMATE_EVIDENCE_INVALID")
  object.__setattr__(self,"input_token_estimate_sha256",h)
 def to_dict(self):return {**_body(self),"input_token_estimate_sha256":self.input_token_estimate_sha256}
@dataclass(frozen=True)
class CatalogEntry:
 schema_version:str;catalog_entry_version:str;provider_id:str;provider_family:str;model_id:str;model_version:str;deployment_id:str;endpoint_class:str;capabilities:Tuple[str,...];supported_privacy_levels:Tuple[str,...];supported_data_policies:Tuple[str,...];maximum_input_tokens:int;maximum_output_tokens:int;cost_microunits_per_input_token:int;cost_microunits_per_output_token:int;estimated_latency_ms:int;supports_offline_routing_only:bool;requires_credentials:bool;requires_network:bool;valid_from:str;valid_until:str;catalog_entry_sha256:str=""
 def __post_init__(self):
  for n in ("provider_id","provider_family","model_id","model_version","deployment_id","endpoint_class"):text(getattr(self,n))
  for n in ("capabilities","supported_privacy_levels","supported_data_policies"):object.__setattr__(self,n,sset(getattr(self,n)))
  for n in ("maximum_input_tokens","maximum_output_tokens","cost_microunits_per_input_token","cost_microunits_per_output_token","estimated_latency_ms"):integer(getattr(self,n))
  timestamp(self.valid_from);timestamp(self.valid_until)
  if self.valid_from>=self.valid_until:raise ValueError("INVALID_TIME_INTERVAL")
  h=hash_record(DOMAIN["MODEL-CATALOG-ENTRY"],_body(self));object.__setattr__(self,"catalog_entry_sha256",h)
 def identity(self):return (self.provider_id,self.model_id,self.model_version,self.deployment_id)
 def to_dict(self):return {**_body(self),"catalog_entry_sha256":self.catalog_entry_sha256}
@dataclass(frozen=True)
class RoutingPolicy:
 schema_version:str;policy_version:str;allowed_provider_ids:Tuple[str,...];allowed_model_ids:Tuple[str,...];prohibited_provider_ids:Tuple[str,...];prohibited_model_ids:Tuple[str,...];permitted_token_estimators:Tuple[Tuple[str,str],...];permitted_privacy_levels:Tuple[str,...];permitted_data_policies:Tuple[str,...];maximum_input_tokens:int;maximum_output_tokens:int;maximum_total_tokens:int;maximum_cost_microunits:int;maximum_latency_ms:int;require_offline_routing_only:bool=True;prohibit_network_required_models:bool=True;prohibit_credential_required_models:bool=True;fallback_policy:str="ALL_REMAINING_ELIGIBLE_IN_CANONICAL_ORDER";drift_policy:str="FAIL_CLOSED";authority_delta:int=0;policy_sha256:str=""
 def __post_init__(self):
  for n in ("allowed_provider_ids","allowed_model_ids","prohibited_provider_ids","prohibited_model_ids","permitted_token_estimators","permitted_privacy_levels","permitted_data_policies"):object.__setattr__(self,n,sset(getattr(self,n)))
  for n in ("maximum_input_tokens","maximum_output_tokens","maximum_total_tokens","maximum_cost_microunits","maximum_latency_ms"):integer(getattr(self,n))
  if self.authority_delta!=0 or self.policy_version!=POLICY_VERSION:raise ValueError("POLICY")
  object.__setattr__(self,"policy_sha256",hash_record(DOMAIN["MODEL-ROUTING-POLICY"],_body(self)))
 def to_dict(self):return {**_body(self),"policy_sha256":self.policy_sha256}
@dataclass(frozen=True)
class TaskRequirement:
 schema_version:str;routing_policy_version:str;program_id:str;gate_id:str;tenant_id:str;principal_identity_reference:str;mission_id:str;request_sha256:str;mission_scope_sha256:str;aggregate_version:int;aggregate_sha256:str;workforce_reconciliation_sha256:str;ordered_specialist_output_package_sha256s:Tuple[str,...];task_id:str;task_type:str;task_prompt_sha256:str;context_manifest_sha256:str;token_estimate_evidence:TokenEstimateEvidence|None;required_capabilities:Tuple[str,...];allowed_provider_ids:Tuple[str,...];allowed_model_ids:Tuple[str,...];prohibited_provider_ids:Tuple[str,...];prohibited_model_ids:Tuple[str,...];required_privacy_level:str;required_data_policy:str;maximum_input_tokens:int;maximum_output_tokens:int;maximum_total_tokens:int;maximum_estimated_cost_microunits:int;maximum_estimated_latency_ms:int;fallback_policy:str;evaluation_time:str;requirement_sha256:str=""
 def __post_init__(self):
  for n in ("ordered_specialist_output_package_sha256s","required_capabilities","allowed_provider_ids","allowed_model_ids","prohibited_provider_ids","prohibited_model_ids"):object.__setattr__(self,n,sset(getattr(self,n)))
  for n in ("aggregate_version","maximum_input_tokens","maximum_output_tokens","maximum_total_tokens","maximum_estimated_cost_microunits","maximum_estimated_latency_ms"):integer(getattr(self,n))
  timestamp(self.evaluation_time);object.__setattr__(self,"requirement_sha256",hash_record(DOMAIN["MODEL-TASK-REQUIREMENT"],_body(self)))
 def to_dict(self):return {**_body(self),"requirement_sha256":self.requirement_sha256}
@dataclass(frozen=True)
class CandidateEvaluation:
 schema_version:str;requirement_sha256:str;routing_policy_sha256:str;model_catalog_set_sha256:str;catalog_entry_sha256:str;identity_key:Tuple[str,...];checks:Tuple[Tuple[str,str],...];estimated_input_cost_microunits:int;estimated_output_cost_microunits:int;estimated_total_cost_microunits:int;estimated_total_tokens:int;excess_capability_count:int;eligible:bool;exclusion_reason_codes:Tuple[str,...];evaluation_sha256:str=""
 def __post_init__(self):object.__setattr__(self,"evaluation_sha256",hash_record(DOMAIN["CANDIDATE-EVALUATION"],_body(self)))
 def to_dict(self):return {**_body(self),"evaluation_sha256":self.evaluation_sha256}
@dataclass(frozen=True)
class ModelDecision:
 schema_version:str;result:Result;requirement_sha256:str;routing_policy_sha256:str;model_catalog_set_sha256:str;ordered_candidate_evaluation_sha256s:Tuple[str,...];selected_identity_key:Tuple[str,...];selected_catalog_entry_sha256:str;fallback_identity_keys:Tuple[Tuple[str,...],...];fallback_catalog_entry_sha256s:Tuple[str,...];input_token_estimate:int;maximum_output_tokens:int;estimated_total_tokens:int;estimated_total_cost_microunits:int;estimated_latency_ms:int;provider_invoked:bool=False;provider_receipt_sha256:None=None;provider_response_sha256:None=None;provider_session_id:None=None;provider_request_id:None=None;model_output_sha256:None=None;network_used:bool=False;credentials_accessed:bool=False;authority_delta:int=0;model_decision_sha256:str=""
 def __post_init__(self):
  if self.provider_invoked or self.network_used or self.credentials_accessed or self.authority_delta!=0 or any(getattr(self,n) is not None for n in ("provider_receipt_sha256","provider_response_sha256","provider_session_id","provider_request_id","model_output_sha256")):raise ValueError("AUTHORITY_EXPANSION")
  object.__setattr__(self,"model_decision_sha256",hash_record(DOMAIN["MODEL-DECISION"],_body(self)))
 def to_dict(self):return {**_body(self),"model_decision_sha256":self.model_decision_sha256}
@dataclass(frozen=True)
class RoutingOutcome:
 result:Result;reason_code:str;decision:ModelDecision|None;evaluations:Tuple[CandidateEvaluation,...]
