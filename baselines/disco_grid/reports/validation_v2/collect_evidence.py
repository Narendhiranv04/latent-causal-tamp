import sys,pathlib,json,collections,time,hashlib,importlib.util,os
b=pathlib.Path('/scratch/nav/disco_grid/validation_v2');code=b/'code_final/baselines/disco_grid';sys.path.insert(0,str(code))
import data as D,env as E,policy as P,distill as DS,evaluate as V
import numpy as np,torch
torch.set_num_threads(1)
for script,out in [('analyze_archive.py','archive_statistics.json'),('build_pairing.py','paired_root_manifest.json')]:
 path=code/'reports/validation_v2'/script;spec=importlib.util.spec_from_file_location(script[:-3],path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 (mod.analyze if script.startswith('analyze') else mod.build)(b/'evidence',b/'evidence'/out)
training={}
for dom in ['2d','3d']:
 p=b/f'ablations_{dom}_r1/results.json'
 training[dom]=json.loads(p.read_text()) if p.exists() else {'status':'NOT_AVAILABLE'}
(b/'evidence/new_training.json').write_text(json.dumps(training,indent=2))
cal={}
for dom in ['2d','3d']:
 ck=D.DISCO_ROOT/f'runs/distill/{dom}/r2_s0/value.pt';model,meta=DS.load_value_checkpoint(ck,'cpu')
 examples=[]
 for row in D.load_snapshot_rows(dom,'val'):
  y=next((a['y'] for a in row['labels']['Y'] if not a['edit']),None)
  if y not in (0,1):continue
  obs=V.initial_observation_from_row(row,dom);tok,mask,ctx,_=P.extract_scene_object_tokens(dom,obs,meta['scalers'])
  with torch.no_grad():q=float(model.predict_q(torch.tensor(tok[None]),torch.tensor(mask[None]),torch.tensor(ctx[None]),torch.tensor([P.MAXOBJ[dom]]),torch.tensor([model.N]))[0])
  examples.append({'root_id':row['root_id'],'family_id':D.root_family_key(row),'split':'val','seed':0,'q_stop':q,'z_stop':int(y)})
 result=V.fit_root_stop_calibration(examples)
 result.update(checkpoint=str(ck),checkpoint_sha256=D.sha256_file(ck),n_examples=len(examples),n_positive=sum(r['z_stop'] for r in examples),adopted_as_default=False,physical_queries=0)
 cal[dom]=result
 (b/f'evidence/stop_calibration_{dom}_val.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in examples))
 print(dom,'calibration',len(examples),result['audit_raw'],result['audit_calibrated'],flush=True)
(b/'evidence/stop_calibration.json').write_text(json.dumps(cal,indent=2))
# Structured compact fresh parity record; raw original output remains untouched on host.
parity=json.loads((b/'evidence/physical_parity.json').read_text())
for item in parity['records']:
 item['result']={k:v for k,v in item['result'].items() if k not in ('step_results','stop_result')}
parity['scope']='4 complete-sequence replays; exact physical calls inside archived string traces not reconstructed'
(b/'evidence/physical_parity_compact.json').write_text(json.dumps(parity,indent=2))
print('training runs',{d:len(r.get('runs',[])) for d,r in training.items()},flush=True)
