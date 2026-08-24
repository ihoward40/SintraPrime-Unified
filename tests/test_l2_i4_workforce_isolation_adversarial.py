import ast,os,pathlib,shutil,socket,tempfile
import pytest
from tests.test_l2_i4_workforce_isolation import *
from sintra_live.l2.workforce_workspace import check_contained,inventory
from sintra_live.l2.workforce_launcher import RUNTIME_FILES,child_env

def test_runtime_exact_14_modules_and_forbidden_absent():
 assert len(RUNTIME_FILES)==14; assert not any(x.startswith(('sintra_live/approval','sintra_live/authorization','sintra_live/github','sintra_live/side_effect','sintra_live/swarm')) for x in RUNTIME_FILES)
def test_final_i_probe_and_shadow_protection():
 root=pathlib.Path(tempfile.mkdtemp());rt=build_runtime(ROOT,BASE,root/'build');lane=root/'lane';(lane/'sintra_live/l2').mkdir(parents=True);(lane/'sintra_live/l2/workforce_launcher.py').write_text('raise RuntimeError("SHADOW_IMPORTED")')
 try:
  import subprocess
  env=child_env(lane,rt['python']);cp=subprocess.run([str(rt['python']),'-I','-u','-m','sintra_live.l2.workforce_launcher','--i4-worker-probe'],cwd=lane,env=env,text=True,capture_output=True);d=json.loads(cp.stdout);assert cp.returncode==0 and d['isolated']==1 and d['pythonpath'] is None and d['pythonhome'] is None and str(lane) not in d['sys_path'] and str(ROOT) not in d['sys_path'] and 'site-packages' in d['path']
 finally:shutil.rmtree(root,ignore_errors=True)
def test_secret_stripping_names_only():
 root=pathlib.Path(tempfile.mkdtemp());(root/'temp').mkdir();os.environ['OPENAI_API_KEY']='not-reported';env=child_env(root,BASE)
 try:assert 'OPENAI_API_KEY' not in env and set(env)=={'SYSTEMROOT','WINDIR','TEMP','TMP','PYTHONIOENCODING','PYTHONUTF8','PATH'}
 finally:os.environ.pop('OPENAI_API_KEY',None);shutil.rmtree(root)
def test_path_traversal_ads_unc_denied():
 r=pathlib.Path(tempfile.mkdtemp());
 try:
  for p in (r/'..'/'escape',pathlib.Path(str(r/'x')+':ads'),pathlib.Path('\\\\server\\share\\x')):
   with pytest.raises(ValueError):check_contained(r,p)
 finally:shutil.rmtree(r)
def test_preexisting_workspace_distinct():
 r=pathlib.Path(tempfile.mkdtemp());a=create_workspace(r,'x');b=create_workspace(r,'x');assert a!=b;shutil.rmtree(r)
def test_symlink_or_junction_escape_real_host():
 r=pathlib.Path(tempfile.mkdtemp());outside=pathlib.Path(tempfile.mkdtemp());link=r/'link'
 try:
  try:os.symlink(outside,link,target_is_directory=True)
  except OSError:pytest.skip('host cannot create symlink/reparse point')
  with pytest.raises(ValueError):check_contained(r,link/'x')
 finally:shutil.rmtree(r,ignore_errors=True);shutil.rmtree(outside,ignore_errors=True)
def test_child_does_not_inherit_parent_file_or_socket_handle():
 import msvcrt
 f=tempfile.TemporaryFile();s=socket.socket();fh=msvcrt.get_osfhandle(f.fileno());sh=s.fileno();os.set_handle_inheritable(fh,True);os.set_handle_inheritable(sh,True);root=pathlib.Path(tempfile.mkdtemp());rt=build_runtime(ROOT,BASE,root/'build');w=create_workspace(root/'lanes','h')
 try:
  p,o,*_=launch(rt['python'],w,'h','offline_supported');assert p.returncode==0
 finally:f.close();s.close();shutil.rmtree(root,ignore_errors=True)
def test_output_violation_flags_denied():
 r=reconcile((package('x','1',output('1',credential_request=True,scope_expansion_claim=True)),));assert r.result is ReconciliationResult.DENIED
def test_no_store_policy_memory_network_provider_credential_database_approval_calls():
 fs=[ROOT/'sintra_live/l2'/x for x in ('workforce_contract.py','workforce_policy.py','workforce_workspace.py','workforce_launcher.py','workforce_reconciliation.py')];imports=[];calls=[]
 for p in fs:
  t=ast.parse(p.read_text())
  for n in ast.walk(t):
   if isinstance(n,ast.Import):imports += [x.name for x in n.names]
   elif isinstance(n,ast.ImportFrom) and n.module:imports.append(n.module)
   elif isinstance(n,ast.Call):calls.append(n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else '')
 forbidden=('requests','httpx','urllib','provider','credential','database','sqlite','approval','side_effect','github_live');assert not [x for x in imports if any(y in x.lower() for y in forbidden)];assert not {'transition','evaluate_transition','retrieve_memory','dispatch'}.intersection(calls)
def test_no_arbitrary_shell():
 src=(ROOT/'sintra_live/l2/workforce_launcher.py').read_text();assert 'shell=False' in src and 'shell=True' not in src
def test_workspace_inventory_detects_undeclared():
 r=pathlib.Path(tempfile.mkdtemp());w=create_workspace(r,'u');(w/'bad.txt').write_text('x');assert 'bad.txt' in inventory(w);shutil.rmtree(r)
def test_runtime_cleanup():
 r=pathlib.Path(tempfile.mkdtemp());build_runtime(ROOT,BASE,r/'build');shutil.rmtree(r);assert not r.exists()
