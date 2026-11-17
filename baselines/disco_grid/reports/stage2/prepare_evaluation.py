"""Freeze actual models and prediction-only VAL/TEST candidate matrices.

No physical teacher calls. TEST candidates cover the preregistered admission
rules, before any TEST outcomes. A separate release envelope authorizes VAL and
one VAL-selected TEST branch, avoiding an additional permission interruption.
"""
import argparse, copy, hashlib, json, os, resource, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import collect as C, data as D, distill as DS, env as E, evaluate as EV, journal as J, physical_eval as PE, policy as P
RULE=dict(noop_q_gate=.55,stop_q_margin=.02,abstain_eta=0.,policy_stop_thresh=.45,stop_q_min=.35,noop_pol_gate=.5)
ETAS=(0.,.08,.15)


def read(p):return json.loads(p.read_text())


def root_order(roots):
    by={k:sorted([r for r in roots if str(r['K_legacy'])==k],key=lambda r:r['root_id']) for k in ('0','1','2','3','NONE')}
    return [by[k][i] for i in range(max(map(len,by.values()))) for k in by if i<len(by[k])]


def job_identity(job):
    keys=('domain','arm','seed','policy_sha256','value_sha256','schema','root_id','root_sha256','input_sha256','protocol','physics_seed')
    return hashlib.sha256(json.dumps(dict({k:job.get(k) for k in keys},rule=job['rule']),sort_keys=True).encode()).hexdigest()[:20]


def model_configs(campaign,dom):
    tr=campaign/'training';p1=tr/f'{dom}_P1Q1';clean=tr/f'{dom}_P2Q2';known=tr/f'{dom}_P2Q2_knownprefix'
    p2=known if any(campaign.glob(f'known_prefix_fit*/{dom}_COMPLETE.json')) else clean
    if not (p1/'COMPLETE.json').exists() or not (p2/'COMPLETE.json').exists():raise ValueError('Missing completed full iterative cycle')
    return dict(O0_P0=(None,P.O0,False,'p0'),O0_P1=(p1,P.O0,False,'distilled'),O0_P1Q1=(p1,P.O0,True,'distilled'),
        O0_P2=(p2,P.O0,False,'distilled'),O0_P2Q2=(p2,P.O0,True,'distilled'),O0_P2_success_onlyQ2=(p2,P.O0,True,'distilled'),
        O0_P1_success_onlyQ1=(p1,P.O0,True,'distilled'),O0_P2_clean_onlyQ2=(clean,P.O0,True,'distilled'),O0_closed_P2Q2=(p2,P.O0,True,'distilled'),O1_closed_P2Q2=(p2,P.O1,True,'distilled'))


def make(campaign,cohorts_path,out):
    C.require_headroom()
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU only')
    import torch;torch.set_num_threads(1)
    start=time.monotonic();cpu=time.process_time();out.mkdir(parents=True,exist_ok=False)
    cohorts=read(cohorts_path);rows={d:{r['root_id']:r for r in D.load_snapshot_rows(d)} for d in ('2d','3d')}
    models={};configs={d:model_configs(campaign,d) for d in ('2d','3d')}
    registry=[];loaded={}
    for dom in configs:
        for arm,(fit,schema,q,mode) in configs[dom].items():
            for seed in (0,1,2):
                folder=fit/f'{schema}_{"successful_only" if "success_only" in arm else "all_feasible"}_s{seed}' if fit else None
                pp=folder/'policy.pt' if fit else D.DISCO_ROOT/f'runs/p0/{dom}/s{seed}/model.pt';vp=folder/'value.pt' if q else None
                entry=dict(domain=dom,arm=arm,seed=seed,policy=str(pp),policy_sha256=D.sha256_file(pp),value=str(vp) if vp else None,
                    value_sha256=D.sha256_file(vp) if vp else None,schema=schema,use_value=q,mode=mode)
                ck=torch.load(pp,map_location='cpu',weights_only=False)
                if ck['domain']!=dom or ck.get('observation_schema',P.O0)!=schema or ck.get('seed',seed)!=seed:raise ValueError('Checkpoint metadata differs from declared model')
                if any(not torch.isfinite(v).all() for v in ck['state_dict'].values()):raise ValueError('Nonfinite checkpoint parameters')
                entry['checkpoint_metadata']={k:ck.get(k) for k in ('seed','epoch','hidden','round','observation_schema','obj_trained')}
                entry['parameter_l2']=float(torch.sqrt(sum(v.float().square().sum() for v in ck['state_dict'].values())))
                if vp:
                    vc=torch.load(vp,map_location='cpu',weights_only=False)
                    if vc['domain']!=dom or vc.get('observation_schema',P.O0)!=schema or vc.get('seed',seed)!=seed:raise ValueError('Value metadata mismatch')
                    if any(not torch.isfinite(v).all() for v in vc['state_dict'].values()):raise ValueError('Nonfinite value parameters')
                registry.append(entry);models[(dom,arm,seed)]=entry
    J.atomic_json(out/'checkpoint_manifest.json',registry)
    original_selector=EV.select_action_model_only
    def predict(row,entry,rule):
        modelkey=(entry['policy'],entry['value'])
        if modelkey not in loaded:loaded[modelkey]=PE.load_proposal(entry)
        w=loaded[modelkey];trace=[]
        def capture(obs,*args,**kw):
            decision=original_selector(obs,*args,**kw)
            trace.append(PE.plain(dict(observation_hash=obs.obs_hash(),remaining_steps=obs.remaining_steps,cells=obs.cells,moved_mask=obs.moved_mask,
                q_visible=obs.q_t_optional is not None,is_predicted_edit=obs.is_predicted_edit,decision=decision)))
            return decision
        EV.select_action_model_only=capture;pf=w.policy_forward_passes;vf=w.value_forward_passes
        try:pred=EV.predict_open_loop_sequence(row,entry['domain'],w,B_test=16 if entry['domain']=='2d' else 12,use_value=entry['use_value'],rule=rule,seed=entry['seed'])
        finally:EV.select_action_model_only=original_selector
        if any(pred['selection_physical_counters'].values()):raise ValueError('Selection oracle violation')
        pred.update(selection_trace=trace,policy_forward_passes=w.policy_forward_passes-pf,value_forward_passes=w.value_forward_passes-vf)
        return PE.plain(pred)
    sources={p.name:D.sha256_file(p) for p in HERE.glob('*.py')};all_sets={}
    for split,network_seeds in [('val',(0,)),('test',(0,1,2))]:
        for eta in ETAS:
            jobs=[];roots_manifest={}
            for dom in ('2d','3d'):
                roots=cohorts['domains'][dom]['validation_roots' if split=='val' else 'exploratory_test_roots'];roots_manifest[dom]=roots
                # Primary protocols precede diagnostics and secondary ablations.
                arms=['O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2','O0_P2','O0_P2_success_onlyQ2','O0_P0','O0_P1','O0_P1Q1','O0_P1_success_onlyQ1','O0_P2_clean_onlyQ2']
                for arm in arms:
                    if split=='val' and eta!=0. and arm not in ('O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2'):continue
                    for r in root_order(roots):
                        row=rows[dom][r['root_id']]
                        if row['split']!=split or C.input_hash(row)!=r['input_sha256']:raise ValueError('Frozen root/cohort mismatch')
                        arm_seeds=network_seeds if split=='val' or arm in ('O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2','O0_P2','O0_P2_success_onlyQ2') else (0,)
                        for seed in arm_seeds:
                            e=models[(dom,arm,seed)];rule=dict(RULE,abstain_eta=eta);protocol='closed_loop' if 'closed' in arm else 'open_loop'
                            job=dict(e,root_id=r['root_id'],root_sha256=r['root_sha256'],input_sha256=r['input_sha256'],family_id=r['family_id'],
                                K_legacy=r['K_legacy'],split=split,physics_seed=0,protocol=protocol,B=16 if dom=='2d' else 12,rule=rule,
                                teacher_sources=cohorts['domains'][dom]['teacher_source_sha256'],query_wall_s=60 if dom=='2d' else 120,trial_wall_s=300 if dom=='2d' else 600,
                                adapter_call_cap=5,confirmation_status=cohorts['domains'][dom]['confirmation_status'])
                            if protocol=='open_loop':
                                job['prediction']=predict(row,e,rule);job['adapter_call_cap']=len(job['prediction']['seq'])+1 if job['prediction']['seq'] is not None else 1
                            job['id']=job_identity(job);jobs.append(job)
                            if time.process_time()-cpu>120 or time.monotonic()-start>180:raise RuntimeError('Prediction preparation budget exhausted')
                # Root STOP probes provide independently verified diagnostic labels.
                for r in (root_order(roots) if eta==0. else []):
                    e=models[(dom,'O0_P2Q2',0)];row=rows[dom][r['root_id']]
                    pred=dict(root_id=r['root_id'],domain=dom,split=split,K_legacy=r['K_legacy'],seed=0,status='NOOP',seq=[],m=0,
                        protocol='open_loop',latency_ms=0.,selection_physical_counters={k:0 for k in ('physical_transition_calls','teacher_X_calls','teacher_Y_calls','simulator_initializations','MCTS_calls')},
                        diagnostic_only=True,selection_source='predeclared original-target STOP probe, not a learned policy decision')
                    job=dict(e,arm='root_stop_diagnostic',root_id=r['root_id'],root_sha256=r['root_sha256'],input_sha256=r['input_sha256'],family_id=r['family_id'],
                        K_legacy=r['K_legacy'],split=split,physics_seed=0,protocol='open_loop',B=0,rule=RULE,teacher_sources=cohorts['domains'][dom]['teacher_source_sha256'],
                        query_wall_s=60 if dom=='2d' else 120,trial_wall_s=300 if dom=='2d' else 600,adapter_call_cap=1,prediction=pred,diagnostic_only=True)
                    job['id']=job_identity(job);jobs.append(job)
            name=f'{split}_eta{eta:g}.json';J.atomic_json(out/name,dict(jobs=jobs,roots=roots_manifest,rule=dict(RULE,abstain_eta=eta),
                status='PREPARED_NOT_AUTHORIZED',prediction_source_sha256=sources,model_seeds=list(network_seeds)))
            all_sets[name]=dict(sha256=D.sha256_file(out/name),jobs=len(jobs),maximum_uncached_adapter_calls=sum(j['adapter_call_cap'] for j in jobs if not(j['protocol']=='open_loop' and j['prediction']['status']=='ABSTAIN')))
    # Verify common-random-number candidate matching for the Q intervention.
    for name in all_sets:
        jobs=read(out/name)['jobs'];base=read(out/(name.split('_eta')[0]+'_eta0.json'))['jobs'];by={(j['domain'],j['root_id'],j['seed'],j['arm']):j for j in base}
        for j in jobs:
            if j['arm']!='O0_P2Q2':continue
            other=by[(j['domain'],j['root_id'],j['seed'],'O0_P2')]
            a={t['observation_hash']:t for t in j['prediction']['selection_trace']};b={t['observation_hash']:t for t in other['prediction']['selection_trace']}
            for key in a.keys()&b.keys():
                if a[key]['decision'].get('candidates')!=b[key]['decision'].get('candidates'):raise ValueError('Q ablation changed shared-observation candidate list')
    J.atomic_json(out/'manifest.json',dict(sets=all_sets,checkpoint_manifest_sha256=D.sha256_file(out/'checkpoint_manifest.json'),cohorts_sha256=D.sha256_file(cohorts_path),
        cpu_s=time.process_time()-cpu,wall_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,physical_queries=0,
        primary_model_rule='Known-prefix P2 when fully certified and fitted; otherwise completed clean-only P2. Fixed before VAL.',
        selection_rule='Choose eta by VAL seed-0 O0 open-loop task success, then K0 verified NOOP, then explicit NONE abstention; remaining ties smaller eta. Same eta used by all Q arms and both closed-loop schemas.',
        test_outcomes_opened=False,source_commit=os.environ['DISCO_SOURCE_COMMIT'],source_sha256=sources))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--cohorts',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.campaign,a.cohorts,a.out)
