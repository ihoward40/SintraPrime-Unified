import hashlib,json,pathlib,shutil,sys,tempfile
import pytest
from sintra_live.l2.workforce_contract import *
from sintra_live.l2.workforce_policy import select_roles
from sintra_live.l2.workforce_launcher import build_runtime,launch
from sintra_live.l2.workforce_workspace import create_workspace,cleanup
from sintra_live.l2.workforce_reconciliation import reconcile
ROOT=pathlib.Path(__file__).parents[1]; BASE=pathlib.Path(r'C:/Users/admin/AppData/Local/Programs/Python/Python311/python.exe')
def role(id,cap):return RoleDefinition(SCHEMAS['role-definition'],id,'1',(cap,),('GOVERNED_FACT',),('INTERNAL',),(),('offline_supported',),1000,1000,5000,tuple(sorted({'analyst','reviewer'}-{id})))
def req():return WorkforceRequirements(SCHEMAS['workforce-requirements'],'m','a'*64,'b'*64,1,'c'*64,('analyze','review'),2,2,1000,1000,1000,5000,(),('offline_supported',),'d'*64,(), '2026-08-24T00:00:00.000000Z')
def output(lane,conclusion=LaneConclusion.SUPPORTED,findings=(('F','PRESENT','NON_BLOCKER'),),**flags):return LaneOutput(SCHEMAS['lane-output'],lane,conclusion,findings,(),(),(),flags.get('self_authorization_claim',False),flags.get('scope_expansion_claim',False),flags.get('credential_request',False),0)
def package(roleid,lane,out):return OutputPackage(SCHEMAS['output-package'],lane,roleid,'a'*64,'b'*64,'c'*64,out,0)
def test_role_selection_deterministic():
 roles=(role('reviewer','review'),role('analyst','analyze'));a=select_roles(req(),roles);b=select_roles(req(),tuple(reversed(roles)));assert [x.role_id for x in a]==[x.role_id for x in b]==['analyst','reviewer']
def test_authority_delta_zero_enforced():
 with pytest.raises(ValueError):WorkforcePlan(SCHEMAS['workforce-plan'],'m','a','b',('x','y'),(),1)
def test_real_windows_children_distinct_workspaces_and_runtime():
 assert sys.platform=='win32'; root=pathlib.Path(tempfile.mkdtemp());rt=build_runtime(ROOT,BASE,root/'build');w1=create_workspace(root/'lanes','a');w2=create_workspace(root/'lanes','b')
 try:
  p1,o1,*_=launch(rt['python'],w1,'a','offline_supported');p2,o2,*_=launch(rt['python'],w2,'b','offline_supported');assert p1.pid!=p2.pid and p1.pid!=__import__('os').getpid() and w1!=w2 and o1['conclusion']=='SUPPORTED';assert len(rt['manifest_sha256'])==64 and len(rt['wheel_sha256'])==64 and len(rt['worker_sha256'])==64
 finally:shutil.rmtree(root,ignore_errors=True)
def test_reconciliation_supported():
 r=reconcile((package('a','1',output('1')),package('b','2',output('2'))));assert r.result is ReconciliationResult.COMPLETE and r.conclusion is LaneConclusion.SUPPORTED
def test_reconciliation_not_supported():
 r=reconcile((package('a','1',output('1',LaneConclusion.NOT_SUPPORTED)),package('b','2',output('2',LaneConclusion.NOT_SUPPORTED))));assert r.conclusion is LaneConclusion.NOT_SUPPORTED
def test_required_lane_incomplete():
 r=reconcile((package('a','1',output('1',LaneConclusion.INCOMPLETE)),));assert r.result is ReconciliationResult.INCOMPLETE
def test_blocker_wins():
 r=reconcile((package('a','1',output('1',findings=(('B','PRESENT','BLOCKER'),))),));assert r.conclusion is LaneConclusion.NOT_SUPPORTED
def test_material_disagreement():
 r=reconcile((package('a','1',output('1')),package('b','2',output('2',LaneConclusion.NOT_SUPPORTED))));assert r.reason=='MATERIAL_SPECIALIST_DISAGREEMENT'
def test_specialist_violation_denied():
 r=reconcile((package('a','1',output('1',self_authorization_claim=True)),));assert r.result is ReconciliationResult.DENIED
def test_acceptance_mapping():assert {f'W-{i:02}' for i in range(1,9)}|{'M-07'}=={'W-01','W-02','W-03','W-04','W-05','W-06','W-07','W-08','M-07'}
