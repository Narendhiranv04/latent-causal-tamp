import pathlib,sys,json,collections,subprocess
base=pathlib.Path('/scratch/nav/disco_grid/validation_v2')
sys.path.insert(0,str(base/'code/baselines/disco_grid'))
import data as D
out={};trees={}
for dom in ['2d','3d']:
 rows=D.load_snapshot_rows(dom); lookup={r['root_id']:r for r in rows}
 out[dom]={'split_hygiene':D.check_split_hygiene(rows),'split_counts':dict(collections.Counter(r['split'] for r in rows)), 'snapshot_root_sha256':D.sha256_file(D.BASE_SNAP/f'data{dom}.jsonl')}
 for rnd in ['r0_p0_pw_geom','r1_p1q1_pw_geom']:
  roots=[];calls=[];edges=[];depths=collections.Counter();fail=collections.Counter();stops=collections.Counter()
  for p in sorted((D.DISCO_ROOT/'trees'/dom/rnd).glob('*/tree.json')):
   t=json.loads(p.read_text());s=t['summary'];rid=s['root_id'];roots.append({'root_id':rid,'parent_family_id':lookup[rid]['parent_family_id'],'root_sha256':lookup[rid]['root_sha256'],'split':lookup[rid]['split'],'K_legacy':lookup[rid]['K_legacy']});calls.append(s['total_sim_calls']);edges.append(s['feasible_relocation_edges'])
   for n in t['nodes']:
    if n['parent_id'] is not None and not n['is_stop_node']:depths[n['depth']]+=1
    if n['stop_evaluated'] and not n['is_stop_node']:stops[str(n['terminal_z'])]+=1
   for e in t['edge_logs']:
    if e['status']!='EXECUTED':fail[str(e.get('failure_kind'))]+=1
  trees[dom+'/'+rnd]={'roots':roots,'total_calls':sum(calls),'per_tree_calls':calls,'feasible_edges':sum(edges),'depth_feasible_edges':dict(depths),'stop_outcomes':dict(stops),'failed_transition_kinds':dict(fail)}
out['trees']=trees
out['runtime']=subprocess.check_output(['/scratch/nav/disco_grid/venv/bin/python','-c','import sys,torch,mujoco;print(sys.version);print(torch.__version__,torch.version.cuda,mujoco.__version__)'],text=True)
files=[]
for parent,pattern in [(D.DISCO_ROOT/'runs','**/*.pt'),(D.BASE_SNAP,'*lock.json'),(D.V2_SNAP,'*lock.json'),(D.V3_SNAP,'*lock.json'),(D.ABF_ROOT/'teacher2d_wt','config.toml'),(D.ABF_ROOT/'teacher2d_wt','bxy_teacher.py'),(pathlib.Path('/home/nav/approachb_final_gen/final3d_v4/code'),'*.py')]:
 for p in parent.glob(pattern):
  files.append({'path':str(p),'bytes':p.stat().st_size,'sha256':D.sha256_file(p)})
out['files']=files
(base/'evidence/artifact_inventory.json').write_text(json.dumps(out,indent=2)+'\n')
print({k:{'roots':len(v['roots']),'edges':v['feasible_edges'],'calls':v['total_calls']} for k,v in trees.items()})
