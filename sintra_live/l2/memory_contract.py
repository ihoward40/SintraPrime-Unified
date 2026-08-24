"""Immutable canonical contracts for L2-I3 governed memory retrieval."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, fields
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Mapping, Tuple
from sintra_live.l2.mission import canonical_bytes

QUERY_SCHEMA_VERSION="sp-live-001-l2-i3-memory-query-v1"
CANDIDATE_SCHEMA_VERSION="sp-live-001-l2-i3-memory-candidate-v1"
SELECTED_SCHEMA_VERSION="sp-live-001-l2-i3-selected-item-v1"
EXCLUSION_SCHEMA_VERSION="sp-live-001-l2-i3-exclusion-v1"
CONFLICT_SCHEMA_VERSION="sp-live-001-l2-i3-conflict-v1"
RECORD_SCHEMA_VERSION="sp-live-001-l2-i3-retrieval-record-v1"
POLICY_VERSION="sp-live-001-l2-i3-retrieval-policy-v1"
QUERY_DOMAIN=b"SP-LIVE-001:L2:I3:MEMORY-QUERY:v1\0"; CANDIDATE_DOMAIN=b"SP-LIVE-001:L2:I3:MEMORY-CANDIDATE:v1\0"
CANDIDATE_SET_DOMAIN=b"SP-LIVE-001:L2:I3:CANDIDATE-SET:v1\0"; SELECTED_DOMAIN=b"SP-LIVE-001:L2:I3:SELECTED-ITEM:v1\0"
EXCLUSION_DOMAIN=b"SP-LIVE-001:L2:I3:EXCLUSION:v1\0"; CONFLICT_DOMAIN=b"SP-LIVE-001:L2:I3:CONFLICT:v1\0"
RECORD_DOMAIN=b"SP-LIVE-001:L2:I3:RETRIEVAL-RECORD:v1\0"
SHA=lambda b: hashlib.sha256(b).hexdigest()
class MemoryCategory(str,Enum): GOVERNED_FACT="GOVERNED_FACT"; PRINCIPAL_PREFERENCE="PRINCIPAL_PREFERENCE"; WORKING_CONTEXT="WORKING_CONTEXT"; EXTERNAL_CONTEXT="EXTERNAL_CONTEXT"; HISTORICAL_APPROVAL="HISTORICAL_APPROVAL"
class MemoryTrust(str,Enum): GOVERNED_FACT="GOVERNED_FACT"; PRINCIPAL_PREFERENCE="PRINCIPAL_PREFERENCE"; WORKING_CONTEXT="WORKING_CONTEXT"; UNTRUSTED_EXTERNAL="UNTRUSTED_EXTERNAL"
class Classification(str,Enum): PUBLIC="PUBLIC"; INTERNAL="INTERNAL"; CONFIDENTIAL="CONFIDENTIAL"; RESTRICTED="RESTRICTED"
class ContentKind(str,Enum): FACT="FACT"; PREFERENCE="PREFERENCE"; HISTORICAL_APPROVAL="HISTORICAL_APPROVAL"; INSTRUCTION="INSTRUCTION"; UNTRUSTED_TEXT="UNTRUSTED_TEXT"
class InstructionCategory(str,Enum):
 SCOPE_EXPANSION="SCOPE_EXPANSION"; TOOL_EXPANSION="TOOL_EXPANSION"; AUTHORITY_CLAIM="AUTHORITY_CLAIM"; APPROVAL_BYPASS="APPROVAL_BYPASS"; DESTINATION_CHANGE="DESTINATION_CHANGE"; BUDGET_CHANGE="BUDGET_CHANGE"; CAPABILITY_SELECTION="CAPABILITY_SELECTION"; CREDENTIAL_REQUEST="CREDENTIAL_REQUEST"; EXECUTION_REQUEST="EXECUTION_REQUEST"; POLICY_BYPASS="POLICY_BYPASS"
class RetrievalResult(str,Enum): COMPLETE="COMPLETE"; INCOMPLETE="INCOMPLETE"; DENIED="DENIED"

def text_hash(s:str)->str: return SHA(s.encode("utf-8"))
def domain_hash(domain:bytes,body:Mapping[str,Any])->str: return SHA(domain+canonical_bytes(body))
def _time(v:str):
 if not isinstance(v,str) or len(v)!=27 or not v.endswith("Z"): raise ValueError("noncanonical time")
 return datetime.strptime(v,"%Y-%m-%dT%H:%M:%S.%fZ")
def _sorted(values):
 t=tuple(values)
 if t!=tuple(sorted(set(t))): raise ValueError("array must be sorted unique")
 return t
def _body(obj,skip):
 d={}
 for f in fields(obj):
  if f.name==skip: continue
  v=getattr(obj,f.name)
  if isinstance(v,Enum): v=v.value
  elif isinstance(v,tuple): v=[x.value if isinstance(x,Enum) else x.to_dict() if hasattr(x,"to_dict") else x for x in v]
  d[f.name]=v
 return d

@dataclass(frozen=True)
class MemoryRetrievalQuery:
 schema_version:str; retrieval_policy_version:str; program_id:str; gate_id:str; tenant_id:str; principal_identity_reference:str; mission_id:str; request_id:str; request_sha256:str; mission_scope_sha256:str; aggregate_version:int; aggregate_sha256:str; aggregate_state:str; purpose:str; purpose_sha256:str; purpose_tags:Tuple[str,...]; query_text:str; query_sha256:str; allowed_collection_ids:Tuple[str,...]; cross_mission_allowed_collection_ids:Tuple[str,...]; allowed_classifications:Tuple[Classification,...]; required_memory_categories:Tuple[MemoryCategory,...]; required_trust_levels:Tuple[MemoryTrust,...]; temporal_horizon_start:str; temporal_horizon_end:str; maximum_item_count:int; maximum_total_bytes:int; intended_consumer_role:str; evaluation_time:str; query_record_sha256:str=""
 def __post_init__(self):
  if self.schema_version!=QUERY_SCHEMA_VERSION or self.retrieval_policy_version!=POLICY_VERSION: raise ValueError("schema")
  for n in ("purpose_tags","allowed_collection_ids","cross_mission_allowed_collection_ids","allowed_classifications","required_memory_categories","required_trust_levels"): object.__setattr__(self,n,_sorted(getattr(self,n)))
  if not self.purpose_tags or not self.allowed_collection_ids or not self.allowed_classifications: raise ValueError("empty allowlist")
  if not set(self.cross_mission_allowed_collection_ids)<=set(self.allowed_collection_ids): raise ValueError("cross mission subset")
  if text_hash(self.purpose)!=self.purpose_sha256 or text_hash(self.query_text)!=self.query_sha256: raise ValueError("text hash")
  _time(self.temporal_horizon_start); _time(self.temporal_horizon_end); _time(self.evaluation_time)
  if self.temporal_horizon_start>=self.temporal_horizon_end or self.maximum_item_count<1 or self.maximum_total_bytes<1: raise ValueError("limits")
  h=domain_hash(QUERY_DOMAIN,self.body());
  if self.query_record_sha256 and self.query_record_sha256!=h: raise ValueError("query hash")
  object.__setattr__(self,"query_record_sha256",h)
 def body(self): return _body(self,"query_record_sha256")
 def to_dict(self): return {**self.body(),"query_record_sha256":self.query_record_sha256}

@dataclass(frozen=True)
class MemoryCandidate:
 schema_version:str; memory_item_id:str; version:int; tenant_id:str; principal_identity_reference:str; source_mission_id:str; collection_id:str; classification:Classification; memory_category:MemoryCategory; trust_label:MemoryTrust; content_kind:ContentKind; instruction_categories:Tuple[InstructionCategory,...]; purpose_tags:Tuple[str,...]; consumer_roles:Tuple[str,...]; content:str; content_sha256:str; source_reference:str; source_sha256:str; created_at:str; valid_from:str; valid_until:str; supersedes_item_id:str; superseded_by_item_id:str; contradiction_group_id:str; is_governance_memory:bool; candidate_record_sha256:str=""
 def __post_init__(self):
  if self.schema_version!=CANDIDATE_SCHEMA_VERSION or isinstance(self.version,bool) or self.version<0: raise ValueError("candidate schema")
  for n in ("instruction_categories","purpose_tags","consumer_roles"): object.__setattr__(self,n,_sorted(getattr(self,n)))
  if (self.content_kind is ContentKind.INSTRUCTION) != bool(self.instruction_categories): raise ValueError("instruction metadata")
  compat={MemoryCategory.GOVERNED_FACT:{MemoryTrust.GOVERNED_FACT},MemoryCategory.PRINCIPAL_PREFERENCE:{MemoryTrust.PRINCIPAL_PREFERENCE},MemoryCategory.WORKING_CONTEXT:{MemoryTrust.WORKING_CONTEXT,MemoryTrust.GOVERNED_FACT},MemoryCategory.EXTERNAL_CONTEXT:{MemoryTrust.UNTRUSTED_EXTERNAL,MemoryTrust.WORKING_CONTEXT},MemoryCategory.HISTORICAL_APPROVAL:{MemoryTrust.GOVERNED_FACT}}
  if self.trust_label not in compat[self.memory_category]: raise ValueError("category trust")
  if self.memory_category is MemoryCategory.HISTORICAL_APPROVAL and self.content_kind is not ContentKind.HISTORICAL_APPROVAL: raise ValueError("approval representation")
  if self.content_kind is ContentKind.UNTRUSTED_TEXT and (self.memory_category is not MemoryCategory.EXTERNAL_CONTEXT or self.trust_label is not MemoryTrust.UNTRUSTED_EXTERNAL): raise ValueError("untrusted representation")
  if text_hash(self.content)!=self.content_sha256: raise ValueError("content hash")
  for v in (self.created_at,self.valid_from,self.valid_until): _time(v)
  h=domain_hash(CANDIDATE_DOMAIN,self.body());
  if self.candidate_record_sha256 and self.candidate_record_sha256!=h: raise ValueError("candidate hash")
  object.__setattr__(self,"candidate_record_sha256",h)
 def body(self): return _body(self,"candidate_record_sha256")
 def to_dict(self): return {**self.body(),"candidate_record_sha256":self.candidate_record_sha256}

@dataclass(frozen=True)
class SelectedItem:
 schema_version:str; memory_item_id:str; version:int; collection_id:str; classification:str; memory_category:str; trust_label:str; content:str; content_sha256:str; source_reference:str; source_sha256:str; valid_from:str; valid_until:str; purpose_match_basis:str; consumer_role_basis:str; presentation_only:bool; prior_approval_history_only:bool; selected_item_sha256:str=""
 def __post_init__(self): object.__setattr__(self,"selected_item_sha256",domain_hash(SELECTED_DOMAIN,self.body()))
 def body(self): return _body(self,"selected_item_sha256")
 def to_dict(self): return {**self.body(),"selected_item_sha256":self.selected_item_sha256}
@dataclass(frozen=True)
class Exclusion:
 schema_version:str; memory_item_id:str; version:int; disposition:str; reason_code:str; candidate_record_sha256:str; instruction_categories:Tuple[str,...]=(); exclusion_sha256:str=""
 def __post_init__(self): object.__setattr__(self,"instruction_categories",_sorted(self.instruction_categories)); object.__setattr__(self,"exclusion_sha256",domain_hash(EXCLUSION_DOMAIN,self.body()))
 def body(self): return _body(self,"exclusion_sha256")
 def to_dict(self): return {**self.body(),"exclusion_sha256":self.exclusion_sha256}
@dataclass(frozen=True)
class Conflict:
 schema_version:str; contradiction_group_id:str; participant_hashes:Tuple[str,...]; reason_code:str; conflict_sha256:str=""
 def __post_init__(self): object.__setattr__(self,"participant_hashes",_sorted(self.participant_hashes)); object.__setattr__(self,"conflict_sha256",domain_hash(CONFLICT_DOMAIN,self.body()))
 def body(self): return _body(self,"conflict_sha256")
 def to_dict(self): return {**self.body(),"conflict_sha256":self.conflict_sha256}
@dataclass(frozen=True)
class MemoryRetrievalRecord:
 schema_version:str; retrieval_policy_version:str; mission_id:str; request_sha256:str; mission_scope_sha256:str; aggregate_version:int; aggregate_sha256:str; tenant_id:str; principal_identity_reference:str; purpose_sha256:str; purpose_tags:Tuple[str,...]; query_sha256:str; query_record_sha256:str; allowed_collection_ids:Tuple[str,...]; cross_mission_allowed_collection_ids:Tuple[str,...]; allowed_classifications:Tuple[str,...]; required_memory_categories:Tuple[str,...]; required_trust_levels:Tuple[str,...]; temporal_horizon_start:str; temporal_horizon_end:str; maximum_item_count:int; maximum_total_bytes:int; intended_consumer_role:str; candidate_set_sha256:str; evaluation_time:str; evaluated_candidate_count:int; selected_items:Tuple[SelectedItem,...]; excluded_items:Tuple[Exclusion,...]; quarantined_items:Tuple[Exclusion,...]; conflict_records:Tuple[Conflict,...]; selected_item_count:int; selected_total_bytes:int; result:RetrievalResult; reason_code:str; authority_delta:int=0; retrieval_record_sha256:str=""
 def __post_init__(self):
  if self.authority_delta!=0: raise ValueError("authority delta")
  object.__setattr__(self,"retrieval_record_sha256",domain_hash(RECORD_DOMAIN,self.body()))
 def body(self): return _body(self,"retrieval_record_sha256")
 def to_dict(self): return {**self.body(),"retrieval_record_sha256":self.retrieval_record_sha256}

def candidate_set_hash(candidates):
 ordered=sorted(candidates,key=lambda c:(c.memory_item_id,c.version,c.candidate_record_sha256)); keys=[(c.memory_item_id,c.version) for c in ordered]; hashes=[c.candidate_record_sha256 for c in ordered]
 if len(keys)!=len(set(keys)) or len(hashes)!=len(set(hashes)): raise ValueError("duplicate candidate")
 return domain_hash(CANDIDATE_SET_DOMAIN,{"candidate_hashes":hashes})
