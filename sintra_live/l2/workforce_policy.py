"""Deterministic role selection and mechanical memory minimization."""
from itertools import combinations
from .workforce_contract import *

def select_roles(req,roles):
 eligible=[]
 for r in roles:
  if not set(r.permitted_tool_ids)<=set(req.permitted_tool_ids):continue
  if not set(r.permitted_callable_ids)<=set(req.permitted_callable_ids):continue
  if r.maximum_input_bytes>req.per_lane_input_bytes or r.maximum_output_bytes>req.per_lane_output_bytes or r.maximum_wall_time_ms>req.per_lane_wall_time_ms:continue
  eligible.append(r)
 valid=[]
 for n in range(req.minimum_independent_roles,min(req.maximum_lanes,len(eligible))+1):
  for subset in combinations(sorted(eligible,key=lambda x:(x.role_id,x.role_version,x.sha256)),n):
   if not set(req.required_capabilities)<=set().union(*(set(x.capabilities) for x in subset)):continue
   if any(b.role_id not in a.independent_from_role_ids or a.role_id not in b.independent_from_role_ids for i,a in enumerate(subset) for b in subset[i+1:]):continue
   excess=sum(len(set(x.capabilities)-set(req.required_capabilities)) for x in subset); tools=sum(len(x.permitted_tool_ids) for x in subset)
   valid.append(((n,excess,tools,tuple((x.role_id,x.role_version,x.sha256) for x in subset)),subset))
 if not valid:return None
 return min(valid,key=lambda x:x[0])[1]
def project_memory(role,selected_items,required_hashes):
 by={x.selected_item_sha256:x for x in selected_items}; out=[]
 for h in sorted_unique(required_hashes):
  x=by.get(h)
  if x is None:raise ValueError("required memory missing")
  if x.memory_category not in role.permitted_memory_categories or x.classification not in role.permitted_classifications or x.consumer_role_basis!=role.role_id:raise ValueError("memory not permitted")
  out.append(x)
 return tuple(out)
