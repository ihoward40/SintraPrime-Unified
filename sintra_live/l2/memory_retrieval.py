"""Pure, offline, immutable-candidate L2-I3 retrieval."""
from __future__ import annotations
from sintra_live.l2.mission import MissionAggregate, MissionState
from .memory_contract import *
from .memory_policy import disposition,selection_key

def retrieve_memory(aggregate:MissionAggregate,query:MemoryRetrievalQuery,candidates):
 if aggregate.current_state is not MissionState.MISSION_SCOPED or aggregate.terminal or aggregate.cancelled: raise ValueError("aggregate state")
 ident=aggregate.identity
 if (query.program_id,query.gate_id,query.mission_id,query.request_id,query.request_sha256,query.mission_scope_sha256,query.aggregate_version,query.aggregate_sha256,query.principal_identity_reference)!=(ident.program_id,ident.gate_id,ident.mission_id,ident.request_id,ident.request_sha256,ident.mission_scope_sha256,aggregate.version,aggregate.aggregate_sha256,ident.principal_identity_reference):raise ValueError("binding")
 candidates=tuple(candidates); set_hash=candidate_set_hash(candidates)
 excluded=[]; quarantined=[]; eligible=[]; incomplete=[]
 byid={c.memory_item_id:c for c in candidates}
 for c in sorted(candidates,key=lambda x:(x.memory_item_id,x.version,x.candidate_record_sha256)):
  reason=disposition(query,c)
  if reason=="DATA_ONLY_INSTRUCTION":quarantined.append(Exclusion(EXCLUSION_SCHEMA_VERSION,c.memory_item_id,c.version,"QUARANTINED",reason,c.candidate_record_sha256,tuple(x.value for x in c.instruction_categories)))
  elif reason!="ELIGIBLE":excluded.append(Exclusion(EXCLUSION_SCHEMA_VERSION,c.memory_item_id,c.version,"EXCLUDED",reason,c.candidate_record_sha256))
  else:eligible.append(c)
 # exact bidirectional supersession graph
 for c in tuple(eligible):
  if c.superseded_by_item_id:
   nxt=byid.get(c.superseded_by_item_id)
   if not nxt or nxt.supersedes_item_id!=c.memory_item_id: incomplete.append("BROKEN_SUPERSESSION_CHAIN")
   else:
    eligible.remove(c); excluded.append(Exclusion(EXCLUSION_SCHEMA_VERSION,c.memory_item_id,c.version,"EXCLUDED","SUPERSEDED",c.candidate_record_sha256))
  if c.supersedes_item_id:
   prev=byid.get(c.supersedes_item_id)
   if not prev or prev.superseded_by_item_id!=c.memory_item_id: incomplete.append("BROKEN_SUPERSESSION_CHAIN")
 # cycle detection and multiple-current-leaf detection.
 for c in candidates:
  seen=set(); cur=c
  while cur.superseded_by_item_id:
   if cur.memory_item_id in seen: incomplete.append("CYCLIC_SUPERSESSION_CHAIN"); break
   seen.add(cur.memory_item_id); cur=byid.get(cur.superseded_by_item_id)
   if cur is None:break
 successors={}
 for c in candidates:
  if c.supersedes_item_id: successors.setdefault(c.supersedes_item_id,[]).append(c.memory_item_id)
 if any(len(set(ids))>1 for ids in successors.values()): incomplete.append("MULTIPLE_CURRENT_VERSIONS")
 conflicts=[]
 groups={}
 for c in eligible:
  if c.contradiction_group_id:groups.setdefault(c.contradiction_group_id,[]).append(c)
 conflicted=set()
 for gid,items in groups.items():
  if len(items)>=2 and len({x.content_sha256 for x in items})>=2:
   hashes=tuple(sorted(x.candidate_record_sha256 for x in items)); conflicts.append(Conflict(CONFLICT_SCHEMA_VERSION,gid,hashes,"UNRESOLVED_CONTRADICTION")); incomplete.append("UNRESOLVED_CONTRADICTION"); conflicted.update(hashes)
 eligible=[c for c in eligible if c.candidate_record_sha256 not in conflicted]
 selected=[]; total=0
 for c in sorted(eligible,key=selection_key):
  size=len(c.content.encode("utf-8"))
  if len(selected)+1>query.maximum_item_count or total+size>query.maximum_total_bytes:
   excluded.append(Exclusion(EXCLUSION_SCHEMA_VERSION,c.memory_item_id,c.version,"EXCLUDED","RETRIEVAL_BUDGET_LIMIT",c.candidate_record_sha256)); continue
  selected.append(SelectedItem(SELECTED_SCHEMA_VERSION,c.memory_item_id,c.version,c.collection_id,c.classification.value,c.memory_category.value,c.trust_label.value,c.content,c.content_sha256,c.source_reference,c.source_sha256,c.valid_from,c.valid_until,"EXACT_PURPOSE_TAG",query.intended_consumer_role,c.memory_category is MemoryCategory.PRINCIPAL_PREFERENCE,c.memory_category is MemoryCategory.HISTORICAL_APPROVAL)); total+=size
 missing=set(x.value for x in query.required_memory_categories)-{x.memory_category for x in selected}
 if missing: incomplete.append("REQUIRED_MEMORY_MISSING")
 precedence=("BROKEN_SUPERSESSION_CHAIN","CYCLIC_SUPERSESSION_CHAIN","MULTIPLE_CURRENT_VERSIONS","UNRESOLVED_CONTRADICTION","REQUIRED_MEMORY_MISSING")
 reason=next((x for x in precedence if x in incomplete),"COMPLETE" if selected else "NO_MATCHING_MEMORY")
 result=RetrievalResult.INCOMPLETE if incomplete else RetrievalResult.COMPLETE
 return MemoryRetrievalRecord(RECORD_SCHEMA_VERSION,POLICY_VERSION,query.mission_id,query.request_sha256,query.mission_scope_sha256,query.aggregate_version,query.aggregate_sha256,query.tenant_id,query.principal_identity_reference,query.purpose_sha256,query.purpose_tags,query.query_sha256,query.query_record_sha256,query.allowed_collection_ids,query.cross_mission_allowed_collection_ids,tuple(x.value for x in query.allowed_classifications),tuple(x.value for x in query.required_memory_categories),tuple(x.value for x in query.required_trust_levels),query.temporal_horizon_start,query.temporal_horizon_end,query.maximum_item_count,query.maximum_total_bytes,query.intended_consumer_role,set_hash,query.evaluation_time,len(candidates),tuple(selected),tuple(sorted(excluded,key=lambda x:(x.memory_item_id,x.version,x.disposition,x.reason_code,x.candidate_record_sha256))),tuple(sorted(quarantined,key=lambda x:(x.memory_item_id,x.version,x.disposition,x.reason_code,x.candidate_record_sha256))),tuple(sorted(conflicts,key=lambda x:(x.contradiction_group_id,x.conflict_sha256))),len(selected),total,result,reason,0)
