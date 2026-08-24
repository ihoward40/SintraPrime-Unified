"""Fixed child entrypoint and disposable minimal-runtime launcher for I4."""
from __future__ import annotations
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile,threading,time,zipfile
from .workforce_contract import *
RUNTIME_FILES=('sintra_live/__init__.py','sintra_live/l2/__init__.py','sintra_live/l2/memory_contract.py','sintra_live/l2/mission/__init__.py','sintra_live/l2/mission/errors.py','sintra_live/l2/mission/model.py','sintra_live/l2/mission/state.py','sintra_live/l2/mission/transition_contract.py','sintra_live/l2/mission/transition_errors.py','sintra_live/l2/workforce_contract.py','sintra_live/l2/workforce_launcher.py','sintra_live/l2/workforce_policy.py','sintra_live/l2/workforce_reconciliation.py','sintra_live/l2/workforce_workspace.py')
CALLABLES=('offline_supported','offline_not_supported','offline_incomplete','offline_violation')
def _fixture(name,lane):
 flags={'self_authorization_claim':False,'scope_expansion_claim':False,'credential_request':False}; conclusion={'offline_supported':'SUPPORTED','offline_not_supported':'NOT_SUPPORTED','offline_incomplete':'INCOMPLETE','offline_violation':'SUPPORTED'}[name]
 if name=='offline_violation':flags={'self_authorization_claim':True,'scope_expansion_claim':True,'credential_request':True}
 return {'schema_version':SCHEMAS['lane-output'],'lane_id':lane,'conclusion':conclusion,'findings':[['FINDING','PRESENT','NON_BLOCKER']], 'assumptions':[],'uncertainties':[],'followups':[],**flags,'authority_delta':0}
def worker():
 if sys.argv[1:] not in (['--i4-worker'],['--i4-worker-probe']):raise SystemExit(64)
 if sys.argv[1:]==['--i4-worker-probe']:
  p=pathlib.Path(__file__);print(json.dumps({'isolated':sys.flags.isolated,'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sys_path':sys.path,'pythonpath':os.getenv('PYTHONPATH'),'pythonhome':os.getenv('PYTHONHOME')},sort_keys=True));return
 d=json.loads(sys.stdin.buffer.read().decode()); name=d['callable_id']
 if name not in CALLABLES:raise SystemExit(65)
 print(json.dumps(_fixture(name,d['lane_id']),sort_keys=True,separators=(',',':')))
def module_manifest(root):
 root=pathlib.Path(root);return {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in RUNTIME_FILES}
def build_runtime(repo_root,base_python,out):
 repo=pathlib.Path(repo_root);out=pathlib.Path(out);stage=out/'stage';wheel=out/'sintralive_i4_runtime-0.1.0-py3-none-any.whl';venv=out/'runtime'
 for f in RUNTIME_FILES:
  p=stage/f;p.parent.mkdir(parents=True,exist_ok=True)
  if f=='sintra_live/__init__.py' and not (repo/f).exists():p.write_text('')
  elif f=='sintra_live/l2/mission/__init__.py':p.write_text('"""Minimal I4 runtime mission package."""\n')
  else:shutil.copyfile(repo/f,p)
 manifest=module_manifest(stage);msha=dh(DOMAINS['runtime-module-manifest'],manifest);wheel.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(wheel,'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(RUNTIME_FILES):z.write(stage/f,f)
  di='sintralive_i4_runtime-0.1.0.dist-info';z.writestr(di+'/METADATA','Metadata-Version: 2.1\nName: sintralive-i4-runtime\nVersion: 0.1.0\n');z.writestr(di+'/WHEEL','Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
 subprocess.run([str(base_python),'-m','venv','--without-pip',str(venv)],check=True);sp=venv/'Lib/site-packages'
 with zipfile.ZipFile(wheel) as z:z.extractall(sp)
 installed=module_manifest(sp)
 if installed!=manifest:raise RuntimeError('runtime manifest')
 return {'python':venv/'Scripts/python.exe','wheel':wheel,'manifest_sha256':msha,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'worker_sha256':manifest['sintra_live/l2/workforce_launcher.py'],'stage':stage,'venv':venv}
def child_env(workspace,python_exe):
 # The venv interpreter needs the base Python DLL and standard-library runtime
 # directories on Windows.  This fixed minimum contains no repository/tool path.
 base=pathlib.Path(sys.base_prefix)
 path_parts=(pathlib.Path(python_exe).parent,base,base/'DLLs',base/'Scripts',pathlib.Path(os.environ.get('SYSTEMROOT',r'C:\\Windows'))/'System32')
 env={'SYSTEMROOT':os.environ.get('SYSTEMROOT',''),'WINDIR':os.environ.get('WINDIR',''),'TEMP':str(pathlib.Path(workspace)/'temp'),'TMP':str(pathlib.Path(workspace)/'temp'),'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','PATH':os.pathsep.join(str(x) for x in path_parts)}
 return env
def launch(runtime_python,workspace,lane_id,callable_id,input_budget=65536,output_budget=65536,stderr_budget=8192,timeout_ms=5000):
 data=json.dumps({'lane_id':lane_id,'callable_id':callable_id},sort_keys=True,separators=(',',':')).encode();
 if len(data)>input_budget:raise ValueError('input budget')
 start=time.monotonic_ns();p=subprocess.Popen([str(runtime_python),'-I','-u','-m','sintra_live.l2.workforce_launcher','--i4-worker'],cwd=workspace,env=child_env(workspace,runtime_python),shell=False,close_fds=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:out,err=p.communicate(data,timeout=timeout_ms/1000);timed=False
 except subprocess.TimeoutExpired:p.terminate();timed=True;out,err=p.communicate(timeout=2)
 if len(out)>output_budget or len(err)>stderr_budget:raise ValueError('pipe budget')
 parsed=json.loads(out) if p.returncode==0 and not timed else None
 return p,parsed,out,err,timed,time.monotonic_ns()-start
if __name__=='__main__':worker()
