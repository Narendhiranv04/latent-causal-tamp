"""Frozen original implementation; predictions only; no physical calls."""
import json,sys,time,hashlib,collections,pathlib,os
sys.path.insert(0,'/scratch/nav/disco_grid/validation_v2/original/baselines/disco_grid')
import data as D, policy as P, distill as DS, evaluate as V
out=pathlib.Path('/scratch/nav/disco_grid/validation_v2/evidence');out.mkdir(exist_ok=True)
summary=json.loads(pathlib.Path('/scratch/nav/disco_grid/validation_v2/original/baselines/disco_grid/reports/d6_d7_d8_evaluation_summary.json').read_text())
all_report={}
for dom in ['2d','3d']:
 rows=V.select_eval_cohort(dom,'test',counts_by_k={k:(15 if dom=='2d' else 6) for k in ['0','1','2','3','NONE']})
 cache={}
 cp=D.DISCO_ROOT/'caches'/f'verify_{dom}_test.jsonl'
 for line in cp.open():
  x=json.loads(line)
  for sk,res in x['results'].items(): cache[(x['root_id'],sk)]=res
 configs={'uniform_no_q':(None,None,'uniform',[0]),'p0_only':('runs/p0/{dom}/s{s}/model.pt',None,'p0',[0,1,2]),'p1_only':('runs/distill/{dom}/r1_s{s}/policy.pt',None,'distilled',[0,1,2]),'p1_q1':('runs/distill/{dom}/r1_s{s}/policy.pt','runs/distill/{dom}/r1_s{s}/value.pt','distilled',[0,1,2]),'p2_only':('runs/distill/{dom}/r2_s{s}/policy.pt',None,'distilled',[0,1,2]),'p2_q2_primary':('runs/distill/{dom}/r2_s{s}/policy.pt','runs/distill/{dom}/r2_s{s}/value.pt','distilled',[0,1,2]),'p1_succ_only_q1':('runs/distill/{dom}/r1_succ_only_s0/policy.pt','runs/distill/{dom}/r1_succ_only_s0/value.pt','distilled',[0])}
 arms={};hashes={};t0=time.time()
 for name,(pp,vp,mode,seeds) in configs.items():
  preds=[]
  for seed in seeds:
   pol=val=None
   if pp:
    path=D.DISCO_ROOT/pp.format(dom=dom,s=seed);pol,ck=P.load_policy_checkpoint(path,'cpu');hashes[str(path)]=D.sha256_file(path);scalers=ck['scalers']
   else: scalers=json.loads((D.ABF_ROOT/f'data/q2_{dom}/scalers.json').read_text())
   if vp:
    path=D.DISCO_ROOT/vp.format(dom=dom,s=seed);val,_=DS.load_value_checkpoint(path,'cpu');hashes[str(path)]=D.sha256_file(path)
   w=P.PolicyProposalWrapper(dom,pol,scalers,'cpu',mode,val)
   for row in rows:
    pr=V.predict_open_loop_sequence(row,dom,w,B_test=16 if dom=='2d' else 12,use_value=bool(vp),rule=summary['domains'][dom]['val_rule_tuning']['best_rule'],seed=seed)
    pr['arm']=name
    if pr['status']=='ABSTAIN': pr.update(verified=0,x=None,y=None,verification_source='abstain_no_query')
    else:
     res=cache.get((row['root_id'],json.dumps(pr['seq']))) or V.lookup_existing_snapshot_label(row,pr['seq'])
     if res is None: raise RuntimeError('Missing frozen verification for '+row['root_id']+' '+name)
     pr.update(verified=res['z'],x=res['x'],y=res['y'],failed_phase=res.get('failed_phase'),failure_kind=res.get('failure_kind'),verification_source=res.get('source'))
    preds.append(pr)
  arms[name]=preds
  (out/f'replay_{dom}_{name}.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in preds))
  print(dom,name,len(preds),V.compute_benchmark_metrics(preds)['task_success'],flush=True)
 old=summary['domains'][dom]['open_loop_primary_per_prediction'];new=arms['p2_q2_primary']
 keys=['root_id','seed','seq','status','verified','x','y']
 mismatches=[i for i,(a,b) in enumerate(zip(old,new)) if any(a.get(k)!=b.get(k) for k in keys)]
 all_report[dom]={'n_replayed':sum(map(len,arms.values())),'primary_prediction_replay_count':len(new),'primary_prediction_mismatches':mismatches,'archive_primary_length':len(old),'wall_s':time.time()-t0,'checkpoint_sha256':hashes,'frozen_cache_sha256':D.sha256_file(cp),'metrics':{k:V.compute_benchmark_metrics(v) for k,v in arms.items()},'new_physical_queries':0}
 (out/'archive_replay.json').write_text(json.dumps(all_report,indent=2)+'\n')
