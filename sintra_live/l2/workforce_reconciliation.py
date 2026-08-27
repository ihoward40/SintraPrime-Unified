"""Pure deterministic I4 specialist output reconciliation."""
from .workforce_contract import *
def reconcile(packages):
 ordered=sorted(packages,key=lambda p:(p.role_id,p.lane_id,p.sha256));hashes=tuple(sorted(p.sha256 for p in ordered))
 if any(p.output.self_authorization_claim or p.output.scope_expansion_claim or p.output.credential_request for p in ordered):return Reconciliation(SCHEMAS['reconciliation'],hashes,ReconciliationResult.DENIED,LaneConclusion.INCOMPLETE,'SPECIALIST_VIOLATION',(),0)
 if any(p.output.conclusion is LaneConclusion.INCOMPLETE for p in ordered):return Reconciliation(SCHEMAS['reconciliation'],hashes,ReconciliationResult.INCOMPLETE,LaneConclusion.INCOMPLETE,'REQUIRED_LANE_INCOMPLETE',(),0)
 assertions={}
 blocker=False
 for p in ordered:
  for fid,assertion,severity in p.output.findings:
   assertions.setdefault(fid,set()).add(assertion);blocker|=assertion=='PRESENT' and severity=='BLOCKER'
 conflicts=tuple(sorted(k for k,v in assertions.items() if {'PRESENT','ABSENT'}<=v))
 if blocker:return Reconciliation(SCHEMAS['reconciliation'],hashes,ReconciliationResult.COMPLETE,LaneConclusion.NOT_SUPPORTED,'BLOCKER_PRESENT',conflicts,0)
 conclusions={p.output.conclusion for p in ordered}
 if conflicts or len(conclusions)>1:return Reconciliation(SCHEMAS['reconciliation'],hashes,ReconciliationResult.INCOMPLETE,LaneConclusion.INCOMPLETE,'MATERIAL_SPECIALIST_DISAGREEMENT',conflicts,0)
 conclusion=next(iter(conclusions));return Reconciliation(SCHEMAS['reconciliation'],hashes,ReconciliationResult.COMPLETE,conclusion,conclusion.value,(),0)
