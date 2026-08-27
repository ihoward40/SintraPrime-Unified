"""Immutable L2-I6 policy-resolution contracts; policy evidence never grants authority."""
from __future__ import annotations
import hashlib,re
from dataclasses import asdict,dataclass,field,replace
from enum import Enum
from typing import Any,Tuple
from sintra_live.l2.mission.model import canonical_bytes
MAX=2**63-1; RESOLVER_VERSION="sp-live-001-l2-i6-policy-resolver-v1"
SCHEMA={x:f"sp-live-001-l2-i6-{x}-v1" for x in ("proposed-operation","consequence-interpretation","consequence-classification","authority-evidence","policy-record","policy-set","policy-evaluation","policy-decision","policy-denial","policy-incomplete")}
DOMAIN={x:f"SP-LIVE-001:L2:I6:{x.upper()}:v1\0".encode() for x in ("proposed-operation","consequence-interpretation","consequence-classification","authority-evidence","policy-record","policy-set","policy-evaluation","policy-decision","policy-denial","policy-incomplete")}
class Result(str,Enum):ALLOW="ALLOW";DENY="DENY";APPROVAL_REQUIRED="APPROVAL_REQUIRED";INCOMPLETE="INCOMPLETE"
class Consequence(str,Enum):READ_ONLY="READ_ONLY";REVERSIBLE_INTERNAL="REVERSIBLE_INTERNAL";SCOPED_WRITE="SCOPED_WRITE";EXTERNAL_COMMUNICATION="EXTERNAL_COMMUNICATION";FINANCIAL="FINANCIAL";PRODUCTION="PRODUCTION";LEGAL="LEGAL";SECURITY_SENSITIVE="SECURITY_SENSITIVE";GOVERNANCE_PROTECTED="GOVERNANCE_PROTECTED"
ORDER=tuple(x.value for x in Consequence)
class Observation(str,Enum):NOT_PROVIDED="NOT_PROVIDED";STRUCTURALLY_VALID="STRUCTURALLY_VALID";NOT_YET_VALID="NOT_YET_VALID";EXPIRED="EXPIRED";REVOKED="REVOKED"
def iv(x):
 if isinstance(x,bool) or not isinstance(x,int) or not 0<=x<=MAX:raise ValueError("INVALID_INTEGER")
 return x
def ss(x):
 x=tuple(x)
 if x!=tuple(sorted(set(x))):raise ValueError("NONCANONICAL_INPUT")
 return x
def ts(x):
 if not isinstance(x,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z",x):raise ValueError("INVALID_TIME")
 return x
def body(x,own):
 d=asdict(x);d.pop(own,None)
 for k,v in tuple(d.items()):
  if isinstance(v,Enum):d[k]=v.value
 return d
def hr(domain,d):return hashlib.sha256(domain+canonical_bytes(d)).hexdigest()
def seal(x,own,key):
 h=hr(DOMAIN[key],body(x,own));old=getattr(x,own)
 if old and old!=h:raise ValueError("HASH_MISMATCH")
 object.__setattr__(x,own,h)
@dataclass(frozen=True)
class Operation:
 schema_version:str;program_id:str;gate_id:str;mission_id:str;operation_type:str;capability_id:str;capability_version:str;requested_side_effect_count:int;requested_cost:int;requested_tokens:int;requested_latency_ms:int;data_classifications:Tuple[str,...];proposed_operation_sha256:str=""
 def __post_init__(self):
  for n in ("requested_side_effect_count","requested_cost","requested_tokens","requested_latency_ms"):iv(getattr(self,n))
  object.__setattr__(self,"data_classifications",ss(self.data_classifications));seal(self,"proposed_operation_sha256","proposed-operation")
@dataclass(frozen=True)
class ConsequenceInterpretation:
 schema_version:str;mapping_version:str;mission_id:str;i1_value:str;i6_ceiling:str;basis_code:str;authority_delta:int=0;consequence_interpretation_sha256:str=""
 def __post_init__(self):
  if self.authority_delta or self.i6_ceiling not in ORDER:raise ValueError("AUTHORITY_DELTA_NONZERO")
  seal(self,"consequence_interpretation_sha256","consequence-interpretation")
@dataclass(frozen=True)
class Classification:
 schema_version:str;proposed_operation_sha256:str;consequence_class:str;approval_requirement:str;authority_delta:int=0;consequence_classification_sha256:str=""
 def __post_init__(self):
  if self.consequence_class not in ORDER or self.approval_requirement not in ("NO_APPROVAL_REQUIRED","EXPLICIT_APPROVAL_REQUIRED","PROHIBITED") or self.authority_delta:raise ValueError("CLASSIFICATION_INVALID")
  seal(self,"consequence_classification_sha256","consequence-classification")
@dataclass(frozen=True)
class AuthorityEvidence:
 schema_version:str;program_id:str;gate_id:str;mission_id:str;bound_operation_sha256:str;valid_from:str;valid_until:str;revoked:bool=False;authority_evidence_sha256:str=""
 def __post_init__(self):
  ts(self.valid_from);ts(self.valid_until)
  if self.valid_from>=self.valid_until:raise ValueError("INVALID_TIME")
  seal(self,"authority_evidence_sha256","authority-evidence")
@dataclass(frozen=True)
class Policy:
 schema_version:str;policy_id:str;policy_version:str;category:str;effect:str;applicable_operations:Tuple[str,...]=();allowed_operations:Tuple[str,...]=();prohibited_operations:Tuple[str,...]=();allowed_capabilities:Tuple[str,...]=();prohibited_capabilities:Tuple[str,...]=();required_evidence:Tuple[str,...]=();max_side_effects:int=MAX;max_cost:int=MAX;max_tokens:int=MAX;max_latency_ms:int=MAX;max_consequence:str="GOVERNANCE_PROTECTED";valid_from:str="2020-01-01T00:00:00.000000Z";valid_until:str="2099-01-01T00:00:00.000000Z";authority_delta:int=0;policy_record_sha256:str=""
 def __post_init__(self):
  if self.category not in ("MISSION","DATA","MODEL","CONSEQUENCE","CAPABILITY","EVIDENCE") or self.effect not in ("ALLOW","DENY","APPROVAL_REQUIRED") or self.authority_delta or self.max_consequence not in ORDER:raise ValueError("POLICY_INVALID")
  for n in ("applicable_operations","allowed_operations","prohibited_operations","allowed_capabilities","prohibited_capabilities","required_evidence"):object.__setattr__(self,n,ss(getattr(self,n)))
  for n in ("max_side_effects","max_cost","max_tokens","max_latency_ms"):iv(getattr(self,n))
  ts(self.valid_from);ts(self.valid_until);seal(self,"policy_record_sha256","policy-record")
 def identity(self):return (self.category,self.policy_id,self.policy_version)
@dataclass(frozen=True)
class Evaluation:
 schema_version:str;policy_record_sha256:str;applicable:bool;effect:str;reason_codes:Tuple[str,...];policy_evaluation_sha256:str=""
 def __post_init__(self):seal(self,"policy_evaluation_sha256","policy-evaluation")
@dataclass(frozen=True)
class OutcomeBase:
 schema_version:str;resolver_version:str;result:Result;primary_reason_code:str;ordered_reason_codes:Tuple[str,...];operation_sha256:str;interpretation_sha256:str;classification_sha256:str;policy_set_sha256:str;evaluation_sha256s:Tuple[str,...];evaluation_time:str;authority_observation:Observation;authority_evidence_sha256:str|None;approval_required:bool;capability_policy_status:str;effective_side_effect_ceiling:int;effective_cost_ceiling:int;effective_token_ceiling:int;effective_latency_ceiling_ms:int;effective_consequence_ceiling:str;capability_certified:bool=False;capability_available:bool=False;approval_granted:bool=False;current_authority_resolved:bool=False;execution_ready:bool=False;authority_delta:int=0
 def check(self):
  if any((self.capability_certified,self.capability_available,self.approval_granted,self.current_authority_resolved,self.execution_ready)) or self.authority_delta:raise ValueError("POLICY_AUTHORITY_EXPANSION")
@dataclass(frozen=True)
class PolicyDecision(OutcomeBase):
 policy_decision_sha256:str=""
 def __post_init__(self):
  self.check()
  if self.result not in (Result.ALLOW,Result.APPROVAL_REQUIRED):raise ValueError("OUTCOME_RECORD_TYPE_MISMATCH")
  seal(self,"policy_decision_sha256","policy-decision")
@dataclass(frozen=True)
class PolicyDenial(OutcomeBase):
 policy_denial_sha256:str=""
 def __post_init__(self):
  self.check()
  if self.result is not Result.DENY:raise ValueError("OUTCOME_RECORD_TYPE_MISMATCH")
  seal(self,"policy_denial_sha256","policy-denial")
@dataclass(frozen=True)
class PolicyIncomplete(OutcomeBase):
 missing_evidence:Tuple[str,...]=();unavailable_conclusions:Tuple[str,...]=();policy_incomplete_sha256:str=""
 def __post_init__(self):
  self.check()
  if self.result is not Result.INCOMPLETE or not (self.missing_evidence or self.unavailable_conclusions):raise ValueError("OUTCOME_RECORD_TYPE_MISMATCH")
  seal(self,"policy_incomplete_sha256","policy-incomplete")
@dataclass(frozen=True)
class Resolution:
 result:Result;record:PolicyDecision|PolicyDenial|PolicyIncomplete;evaluations:Tuple[Evaluation,...]
