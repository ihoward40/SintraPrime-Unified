"""Pure deterministic L2-I3 memory candidate policy."""
from __future__ import annotations
from .memory_contract import *
TRUST_RANK={MemoryTrust.GOVERNED_FACT:1,MemoryTrust.PRINCIPAL_PREFERENCE:2,MemoryTrust.WORKING_CONTEXT:3,MemoryTrust.UNTRUSTED_EXTERNAL:4}
def disposition(query,c):
 if c.tenant_id!=query.tenant_id:return "TENANT_MISMATCH"
 if c.principal_identity_reference!=query.principal_identity_reference:return "PRINCIPAL_MISMATCH"
 if c.collection_id not in query.allowed_collection_ids:return "COLLECTION_NOT_ALLOWED"
 if c.classification not in query.allowed_classifications:return "CLASSIFICATION_NOT_ALLOWED"
 if query.intended_consumer_role not in c.consumer_roles:return "CONSUMER_ROLE_NOT_ALLOWED"
 if not set(query.purpose_tags)&set(c.purpose_tags): return "CROSS_MISSION_PURPOSE_MISMATCH" if c.source_mission_id!=query.mission_id else "PURPOSE_MISMATCH"
 if c.source_mission_id!=query.mission_id and c.collection_id not in query.cross_mission_allowed_collection_ids:return "CROSS_MISSION_NOT_ALLOWED"
 if not (query.temporal_horizon_start<=c.created_at<query.temporal_horizon_end):return "OUTSIDE_HORIZON"
 if not (c.valid_from<=query.evaluation_time<c.valid_until):return "NOT_CURRENT"
 if query.required_trust_levels and c.trust_label not in query.required_trust_levels:return "TRUST_NOT_ALLOWED"
 if c.content_kind is ContentKind.INSTRUCTION:return "DATA_ONLY_INSTRUCTION"
 return "ELIGIBLE"
def selection_key(c):return (TRUST_RANK[c.trust_label],-c.version,"".join(chr(0x10ffff-ord(x)) for x in c.created_at),c.memory_item_id,c.candidate_record_sha256)
