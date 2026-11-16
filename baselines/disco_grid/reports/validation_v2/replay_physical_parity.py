import json,sys,time,dataclasses,pathlib,os
base=pathlib.Path('/scratch/nav/disco_grid/validation_v2')
sys.path.insert(0,str(base/'code/baselines/disco_grid'))
import env as E, data as D, evaluate as V
from collect import require_headroom
reference=json.loads((base/'original/baselines/disco_grid/reports/d1_parity_audit.json').read_text())
records=[];t0=time.time();cpu0=time.process_time()
for dom in ['2d','3d']:
 require_headroom()
 # First stored K2 order pair, selected by archive order, not model performance.
 cases=next(v for v in reference['sample_traces'][dom].values() if len(v)>1 and v[0]['stratum']=='K2')[:2]
 env=E.RepairEnv(dom,witness_dir=base/'parity_witnesses'/dom)
 for case in cases:
  start=time.time()
  with V.time_limit(max(1,600-(time.time()-t0))):
   result=env.execute_complete_sequence(case['root_id'],[tuple(x) for x in case['seq']],evaluate_y_on_x_fail=True)
  records.append({'domain':dom,'case':case,'result':result,'wall_s':time.time()-start,
                  'agree':(result['x']==case['expected_x'] and result['y']==case['expected_y'])})
  (base/'evidence/physical_parity.json').write_text(json.dumps({'records':records,'wall_s':time.time()-t0,'cpu_s':time.process_time()-cpu0,'adapter_complete_sequence_calls':len(records)},indent=2,default=str))
  print(dom,case['root_id'],case['seq'],result['x'],result['y'],records[-1]['agree'],flush=True)
