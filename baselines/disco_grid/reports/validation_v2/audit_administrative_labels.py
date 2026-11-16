import json,pickle,sys,pathlib,collections
b=pathlib.Path('/scratch/nav/disco_grid/validation_v2');sys.path.insert(0,str(b/'code/baselines/disco_grid'))
import mcts,env
out={}
for p in pathlib.Path('/scratch/nav/disco_grid/trees').glob('*/*/*/nodes.pkl'):
 with p.open('rb') as f:nodes=pickle.load(f)
 bad=[{'node_id':n.node_id,'failure_kind':n.stop_result.failure_kind,'phase':n.stop_result.failed_phase,'connector':n.stop_result.connector_status,'y':n.stop_result.y_status} for n in nodes if n.stop_result and (n.stop_result.failure_kind=='TIMEOUT' or 'BUDGET' in n.stop_result.connector_status or 'BUDGET' in n.stop_result.y_status)]
 if bad: out[str(p)]=bad
p=b/'pilot_2d_k3_seed20261116'
for q in p.glob('*/tree.json'):
 d=json.loads(q.read_text());print('pilotfailures',[e for e in d['edge_logs'] if e['status']!='EXECUTED'])
(b/'evidence/administrative_label_audit.json').write_text(json.dumps(out,indent=2))
print('affected historical trees',len(out),'stop queries',sum(map(len,out.values())))
