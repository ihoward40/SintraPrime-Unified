"""Windows fail-closed disposable lane workspace containment."""
from __future__ import annotations
import hashlib,os,pathlib,shutil,stat,uuid
REPARSE=0x400
def _raw_bad(s):
 return '\x00' in s or s.startswith(('\\\\','//','\\\\?\\','\\\\.\\')) or '..' in pathlib.PurePath(s).parts or (':' in s[2:] if len(s)>=2 and s[1]==':' else ':' in s)
def check_contained(root,target,must_exist=False):
 rs=str(root);ts=str(target)
 if not os.path.isabs(rs) or not os.path.isabs(ts) or _raw_bad(ts):raise ValueError('unsafe path')
 rr=os.path.normcase(os.path.realpath(rs));rt=os.path.normcase(os.path.realpath(ts))
 if os.path.commonpath([rr,rt])!=rr or rr==rt:raise ValueError('escape')
 cur=pathlib.Path(rr)
 for part in pathlib.Path(rt).relative_to(cur).parts:
  cur=cur/part
  if cur.exists() or cur.is_symlink():
   st=os.lstat(cur)
   if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&REPARSE:raise ValueError('reparse')
 if must_exist and not os.path.exists(rt):raise ValueError('missing')
 return pathlib.Path(rt)
def create_workspace(root,lane_id):
 root=pathlib.Path(root).resolve();root.mkdir(parents=True,exist_ok=True);p=root/f'lane-{lane_id}-{uuid.uuid4().hex}'
 if p.exists():raise ValueError('preexisting')
 p.mkdir();check_contained(root,p,True);(p/'temp').mkdir();check_contained(root,p/'temp',True);return p
def inventory(path):return tuple(sorted(str(x.relative_to(path)).replace('\\','/') for x in pathlib.Path(path).rglob('*')))
def workspace_hash(path):return hashlib.sha256('\n'.join(inventory(path)).encode()).hexdigest()
def cleanup(path):
 try:shutil.rmtree(path);return 'PASS'
 except Exception:return 'FAIL'
