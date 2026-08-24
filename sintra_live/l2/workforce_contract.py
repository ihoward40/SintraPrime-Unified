"""Immutable canonical contracts for L2-I4 offline workforce isolation."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Mapping, Tuple
from sintra_live.l2.mission.model import canonical_bytes

POLICY_VERSION="sp-live-001-l2-i4-workforce-policy-v1"
SCHEMAS={n:f"sp-live-001-l2-i4-{n}-v1" for n in ("workforce-requirements","role-definition","workforce-plan","memory-projection","environment-manifest","workspace-identity","specialist-grant","input-manifest","lane-input","lane-output","lane-receipt","output-package","lane-denial","reconciliation")}
DOMAINS={n:f"SP-LIVE-001:L2:I4:{n.upper()}:v1\0".encode() for n in ("workforce-requirements","role-definition","role-catalog-set","callable-registry","workforce-plan","memory-projection","environment-manifest","workspace-identity","specialist-grant","input-manifest","lane-input","lane-output","lane-receipt","output-payload","output-package","lane-denial","reconciliation","worker-source","callable-source","runtime-module-manifest")}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def dh(domain:bytes,body:Mapping[str,Any])->str:return sha(domain+canonical_bytes(body))
def _value(v):
 if isinstance(v,Enum):return v.value
 if isinstance(v,tuple):return [_value(x) for x in v]
 if hasattr(v,"to_dict"):return v.to_dict()
 return v
def body(obj,skip="sha256"):
 return {f.name:_value(getattr(obj,f.name)) for f in fields(obj) if f.name!=skip}
def sorted_unique(xs):
 t=tuple(xs)
 if t!=tuple(sorted(set(t))):raise ValueError("must be sorted and unique")
 return t
class LaneConclusion(str,Enum):SUPPORTED="SUPPORTED";NOT_SUPPORTED="NOT_SUPPORTED";INCOMPLETE="INCOMPLETE"
class ReconciliationResult(str,Enum):COMPLETE="COMPLETE";INCOMPLETE="INCOMPLETE";DENIED="DENIED"
@dataclass(frozen=True)
class RoleDefinition:
 schema_version:str;role_id:str;role_version:str;capabilities:Tuple[str,...];permitted_memory_categories:Tuple[str,...];permitted_classifications:Tuple[str,...];permitted_tool_ids:Tuple[str,...];permitted_callable_ids:Tuple[str,...];maximum_input_bytes:int;maximum_output_bytes:int;maximum_wall_time_ms:int;independent_from_role_ids:Tuple[str,...];sha256:str=""
 def __post_init__(self):
  if self.schema_version!=SCHEMAS["role-definition"]:raise ValueError("schema")
  for n in ("capabilities","permitted_memory_categories","permitted_classifications","permitted_tool_ids","permitted_callable_ids","independent_from_role_ids"):object.__setattr__(self,n,sorted_unique(getattr(self,n)))
  h=dh(DOMAINS["role-definition"],body(self));
  if self.sha256 and self.sha256!=h:raise ValueError("hash")
  object.__setattr__(self,"sha256",h)
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class WorkforceRequirements:
 schema_version:str;mission_id:str;request_sha256:str;scope_sha256:str;aggregate_version:int;aggregate_sha256:str;required_capabilities:Tuple[str,...];minimum_independent_roles:int;maximum_lanes:int;per_lane_input_bytes:int;per_lane_output_bytes:int;per_lane_stderr_bytes:int;per_lane_wall_time_ms:int;permitted_tool_ids:Tuple[str,...];permitted_callable_ids:Tuple[str,...];expected_registry_sha256:str;role_memory_requirements:Tuple[Tuple[str,Tuple[str,...]],...];evaluation_time:str;sha256:str=""
 def __post_init__(self):
  for n in ("required_capabilities","permitted_tool_ids","permitted_callable_ids"):object.__setattr__(self,n,sorted_unique(getattr(self,n)))
  if self.minimum_independent_roles<2 or self.maximum_lanes<self.minimum_independent_roles:raise ValueError("lane limits")
  h=dh(DOMAINS["workforce-requirements"],body(self));object.__setattr__(self,"sha256",h)
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class WorkforcePlan:
 schema_version:str;mission_id:str;requirements_sha256:str;role_catalog_sha256:str;selected_role_ids:Tuple[str,...];rejected_role_ids:Tuple[str,...];authority_delta:int=0;sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0:raise ValueError("authority")
  object.__setattr__(self,"selected_role_ids",sorted_unique(self.selected_role_ids));object.__setattr__(self,"rejected_role_ids",sorted_unique(self.rejected_role_ids));object.__setattr__(self,"sha256",dh(DOMAINS["workforce-plan"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class SpecialistGrant:
 schema_version:str;lane_id:str;mission_id:str;request_sha256:str;scope_sha256:str;aggregate_sha256:str;workforce_plan_sha256:str;role_id:str;role_sha256:str;callable_id:str;memory_hashes:Tuple[str,...];tool_ids:Tuple[str,...];input_budget:int;output_budget:int;stderr_budget:int;wall_time_ms:int;nonce:str;authority_delta:int=0;sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0:raise ValueError("authority")
  object.__setattr__(self,"memory_hashes",sorted_unique(self.memory_hashes));object.__setattr__(self,"tool_ids",sorted_unique(self.tool_ids));object.__setattr__(self,"sha256",dh(DOMAINS["specialist-grant"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class LaneInput:
 schema_version:str;lane_id:str;grant_sha256:str;role_id:str;task:str;memory_items:Tuple[Mapping[str,Any],...];workspace_identity_sha256:str;environment_manifest_sha256:str;sha256:str=""
 def __post_init__(self):object.__setattr__(self,"sha256",dh(DOMAINS["lane-input"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class LaneOutput:
 schema_version:str;lane_id:str;conclusion:LaneConclusion;findings:Tuple[Tuple[str,str,str],...];assumptions:Tuple[str,...]=();uncertainties:Tuple[str,...]=();followups:Tuple[str,...]=();self_authorization_claim:bool=False;scope_expansion_claim:bool=False;credential_request:bool=False;authority_delta:int=0;sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0:raise ValueError("authority")
  for n in ("findings","assumptions","uncertainties","followups"):object.__setattr__(self,n,sorted_unique(getattr(self,n)))
  object.__setattr__(self,"sha256",dh(DOMAINS["lane-output"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class LaneReceipt:
 schema_version:str;lane_id:str;parent_pid:int;child_pid:int;workspace_sha256:str;input_sha256:str;environment_sha256:str;stdout_sha256:str;stderr_sha256:str;exit_code:int;timed_out:bool;crashed:bool;cleanup_result:str;sha256:str=""
 def __post_init__(self):object.__setattr__(self,"sha256",dh(DOMAINS["lane-receipt"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class OutputPackage:
 schema_version:str;lane_id:str;role_id:str;grant_sha256:str;input_sha256:str;receipt_sha256:str;output:LaneOutput;authority_delta:int=0;sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0:raise ValueError("authority")
  object.__setattr__(self,"sha256",dh(DOMAINS["output-package"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}
@dataclass(frozen=True)
class Reconciliation:
 schema_version:str;ordered_package_hashes:Tuple[str,...];result:ReconciliationResult;conclusion:LaneConclusion;reason:str;disagreements:Tuple[str,...];authority_delta:int=0;sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0:raise ValueError("authority")
  object.__setattr__(self,"ordered_package_hashes",sorted_unique(self.ordered_package_hashes));object.__setattr__(self,"disagreements",sorted_unique(self.disagreements));object.__setattr__(self,"sha256",dh(DOMAINS["reconciliation"],body(self)))
 def to_dict(self):return {**body(self),"sha256":self.sha256}

def role_catalog_hash(roles):return dh(DOMAINS["role-catalog-set"],{"role_hashes":[r.sha256 for r in sorted(roles,key=lambda r:(r.role_id,r.role_version,r.sha256))]})
