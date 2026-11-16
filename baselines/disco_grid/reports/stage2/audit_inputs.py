"""Entire-input checksum/lineage audit and non-inferential old interruption quarantine."""
import collections, datetime, hashlib, json, os, pathlib, sys
HERE=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
import data as D, collect as C, policy as P
OUT=pathlib.Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
def digest(p):return D.sha256_file(p)
base=D.DISCO_ROOT/'validation_v2'
old=base/'pilot_3d_k3_seed20261116'
rawfiles={str(p.relative_to(old)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(old.rglob('*')) if p.is_file()}
ledger={'root_id':'D3H_GVLAB_366ce85b50','status':'QUARANTINED_UNRECOVERABLE','iteration_marker':(old/'D3H_GVLAB_366ce85b50/IN_FLIGHT').read_text(),'adapter_calls':None,'cpu_s':None,'wall_limit_s':300,'watchdog_grace_s':5,'query_identity':None,'result_recovery':'No journal, checkpoint, returned result or saved parent state. Witness files alone cannot establish call identity, execution acceptance, q continuity, or Z.','attempts':[{'identity':None,'classification':'UNRECOVERABLE','charged_before_dispatch':None,'actual_adapter_invocations':None,'in_flight':True}],'raw_artifacts':rawfiles,'automatic_resume':'REFUSED; diagnostic rerun must have a new attempt identity'}
(OUT/'interruption_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
audit={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':{p.name:digest(p) for p in HERE.glob('*.py')},'snapshots':{str(s):D.verify_snapshot_lock(s) for s in [D.BASE_SNAP,D.V2_SNAP]},'domains':{}}
for dom in ['2d','3d']:
 rows=D.load_snapshot_rows(dom); counts=collections.Counter((r['split'],str(r['K_legacy'])) for r in rows)
 audit['domains'][dom]={'n_roots':len(rows),'split_K':{'|'.join(k):v for k,v in counts.items()},'families':dict(collections.Counter(r['split'] for r in {D.root_family_key(r):r for r in rows}.values())),'hygiene':D.check_split_hygiene(rows),'data_sha256':digest(D.BASE_SNAP/f'data{dom}.jsonl'),'teacher_sources':C.teacher_sources(dom),'task_dims':{s:P.task_dim(dom,s) for s in [P.O0,P.O1]}}
ref=json.loads((HERE/'reports/validation_v2/archive_replay.json').read_text()); teachers=json.loads((HERE/'reports/validation_v2/teacher_sources.json').read_text()); hashes={}
for d in ref.values():hashes.update(d['checkpoint_sha256'])
for d in teachers.values():hashes.update(d)
audit['preservation']={p:digest(p)==sha for p,sha in hashes.items()}
assert all(audit['preservation'].values())
assert all(s['all_ok'] for s in audit['snapshots'].values())
assert all(not v for d in audit['domains'].values() for k,v in d['hygiene'].items() if k.endswith('conflicts'))
# All numerical legacy JSON is parsed, recursively finite-checked and retained by hash.
legacy={}
for name in ['artifact_inventory','archive_replay','resolved_config','new_training','training_pilots','physical_parity','stop_calibration','release_verification']:
 p=HERE/'reports/validation_v2'/f'{name}.json';obj=json.loads(p.read_text()); scalars=collections.Counter()
 def walk(x):
  if isinstance(x,dict):
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
  else:
   scalars[type(x).__name__]+=1
   if isinstance(x,float):assert __import__('math').isfinite(x)
 walk(obj);legacy[name]={'sha256':digest(p),'scalar_counts':dict(scalars)}
audit['legacy_full_parse']=legacy
(OUT/'input_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('preserved',len(hashes),'split/teacher/lock audits passed; old 3D count remains UNKNOWN')
