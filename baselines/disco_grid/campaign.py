"""Execute an explicitly approved, frozen two-round TRAIN envelope, one CPU job at a time.

Existing collect.py host/root guards remain enforced. This controller adds
aggregate permission, CPU/wall/disk accounting; it never evaluates TEST.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, multiprocessing as mp, os, sys, time, resource
from pathlib import Path
CONTROLLER_START=time.monotonic()
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import collect as C, data as D, distill as DS, journal as J, policy as P


def jsonread(p):return json.loads(Path(p).read_text())


def accounting(out,domain=None,training=False):
    pattern='training/*/attempts/*/WATCHDOG_ACCOUNTING.json' if training else f'trees/{domain}/*/*/attempts/*/WATCHDOG_ACCOUNTING.json'
    files=sorted(out.glob(pattern));cpu=wall=0.
    for p in files:
        x=jsonread(p);cpu+=x['reaped_child_cpu_s'];wall+=x['wall_s']
    return dict(cpu_s=cpu,wall_s=wall,jobs=len(files))


def validate_authorization(envelope,cohort_path):
    if envelope.get('id')!='E16-v1' or envelope.get('status')!='APPROVED' or envelope.get('authorization',{}).get('text')!='Authorize E16-v1 for both domains':
        raise PermissionError('Explicit approved E16-v1 envelope required')
    expected={'2d':(16,2,32,1024,14400,14400,60,900),'3d':(16,2,16,512,28800,28800,120,900)}
    keys=('independent_train_roots','rounds','per_root_adapter_cap','aggregate_adapter_cap','aggregate_cpu_s','active_wall_s','query_wall_s','root_wall_s')
    for dom,limits in expected.items():
        if tuple(envelope['domains'][dom][k] for k in keys)!=limits:raise PermissionError('Altered approved limits')
    if tuple(envelope[k] for k in ('host','workers','cpu_threads','nice','gpu_hours','ram_ceiling_gib','new_disk_ceiling_gib'))!=('gvlab',1,1,10,0,4,10):raise PermissionError('Altered resource authorization')
    neural=envelope['neural_training']
    if (neural['model_seeds'],neural['epochs'],neural['cpu_s_cap'],neural['wall_s_cap'],neural['gpu'])!=([0,1,2],45,1800,1800,False):raise PermissionError('Altered fit limits')
    if D.sha256_file(cohort_path)!=envelope['cohort_manifest_sha256']:raise ValueError('Frozen cohort checksum mismatch')


def charged_calls(out,dom):
    return sum(e['event']=='started' for p in (out/f'trees/{dom}').glob('*/*/*/queries.jsonl') for e in J.read_events(p.parent))


def controller_overhead(out):
    # Reserve a conservative 60 seconds in EACH envelope for this shared controller.
    # Job wall is already charged separately; wall gaps and controller CPU are measured.
    ident=jsonread(out/'CONTROLLER.json')
    jobs=sum(accounting(out,d)['wall_s'] for d in ('2d','3d'))+accounting(out,training=True)['wall_s']
    pending=list(out.glob('trees/*/*/*/attempts/*/START.json'))+list(out.glob('training/*/attempts/*/START.json'))
    active=sum(max(0.,time.monotonic()-jsonread(p)['monotonic_start']) for p in pending if not (p.parent/'WATCHDOG_ACCOUNTING.json').exists())
    return dict(wall_s=max(0.,time.monotonic()-ident['monotonic_start']-jobs-active),cpu_s=time.process_time()-ident['cpu_start'])


def checked_resources(out,envelope):
    r=C.require_headroom()
    size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if size>envelope['new_disk_ceiling_gib']*2**30:raise RuntimeError('CAMPAIGN_DISK_LIMIT')
    if (out/'CONTROLLER.json').exists():
        overhead=controller_overhead(out)
        J.atomic_json(out/'CONTROLLER_OVERHEAD.json',overhead)
        if max(overhead.values())>=55:raise RuntimeError('CONTROLLER_RESERVED_BUDGET_EXHAUSTED')
    return r


def fit_worker(dom,root,out,round_index):
    J.die_with_parent(root['controller_pid']);os.setsid();os.nice(10)
    import torch;torch.set_num_threads(1)
    streams=root['streams'];previous=root.get('previous')
    scalers=jsonread(D.ABF_ROOT/f'data/q2_{dom}/scalers.json');reports=[]
    for schema,mode in [(P.O0,'all_feasible'),(P.O1,'all_feasible'),(P.O0,'successful_only')]:
        datasets=[DS.extract_dataset_from_tree_dirs([Path(t) for t in stream],dom,scalers,tree_round=i+1,
            observation_schema=schema,edges_mode=mode) for i,stream in enumerate(streams)]
        extracted=datasets[0] if len(datasets)==1 else DS.merge_extracted_datasets(datasets)
        for seed in [0,1,2]:
            C.require_headroom()
            dest=out/f'{schema}_{mode}_s{seed}'
            if (dest/'distill_report.json').exists() and jsonread(dest/'distill_report.json')['completed_epochs']==45:
                reports.append(jsonread(dest/'distill_report.json'));continue
            pp=Path(previous)/f'{schema}_all_feasible_s{seed}/policy.pt' if previous else D.DISCO_ROOT/f'runs/p0/{dom}/s{seed}/model.pt'
            vp=Path(previous)/f'{schema}_all_feasible_s{seed}/value.pt' if previous else None
            result=DS.distill_policy_and_value(dom,extracted,pp,init_value_ckpt=vp,round_name=f'E16_P{round_index+1}Q{round_index+1}',
                seed=seed,epochs=45,batch_size=64,lr=.001,device='cpu',out_dir=dest,checkpoint_rule='fixed_epochs',resume=(dest/'trainer.pt').exists())
            reports.append(result)
            J.atomic_json(out/'results.json',dict(domain=dom,round=round_index+1,scope='TRAIN fits, not physical task evaluation',runs=reports))
    J.atomic_json(out/'COMPLETE.json',dict(fits=len(reports),checkpoint_sha256={str(p):D.sha256_file(p) for p in out.glob('*/*.pt')}))


def dispatch_fit(dom,out,streams,previous,envelope,campaign_root):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'COMPLETE.json').exists():return
    totals=accounting(campaign_root,training=True);cfg=envelope['neural_training']
    wall=cfg['wall_s_cap']-totals['wall_s']-65;cpu=cfg['cpu_s_cap']-totals['cpu_s']-65
    if min(wall,cpu)<=0:raise RuntimeError('NEURAL_AGGREGATE_BUDGET_EXHAUSTED')
    attempts=out/'attempts';attempts.mkdir(exist_ok=True)
    for a in attempts.iterdir():
        if not (a/'WATCHDOG_ACCOUNTING.json').exists():raise RuntimeError('Unknown fit attempt accounting; reconcile')
    attempt=attempts/f'{len(list(attempts.iterdir())):03d}';attempt.mkdir()
    J.atomic_json(attempt/'START.json',dict(controller=J.process_identity(),wall_s=wall,cpu_s=cpu,monotonic_start=time.monotonic()))
    worker=mp.get_context('spawn').Process(target=fit_worker,args=(dom,dict(streams=streams,previous=str(previous) if previous else None,controller_pid=os.getpid()),out,len(streams)-1))
    worker.start()
    cancelled=J.wait_for_child(worker,wall,directory=attempt,cpu_seconds=cpu,rss_limit_kib=(envelope['ram_ceiling_gib']-1)*2**20,
        resource_check=lambda:checked_resources(campaign_root,envelope))
    if cancelled or worker.exitcode or not (out/'COMPLETE.json').exists():raise RuntimeError('FIT_INCOMPLETE; exact trainer checkpoints preserved')


def tree_manifest(dom,root,policy,value,round_index,envelope,cohorts,source_commit,wall,cpu,campaign_root):
    cfg=envelope['domains'][dom];scalers=D.ABF_ROOT/f'data/q2_{dom}/scalers.json'
    cohort_seed=cohorts['domains'][dom]['search_seed_schedule'][round_index]
    search_seed=int(hashlib.sha256(f'E16-v1|{dom}|{round_index}|{root["root_id"]}|{cohort_seed}'.encode()).hexdigest()[:8],16)%(2**31-1)
    return dict(version=3,domain=dom,roots=[root],source_commit=source_commit,
        runtime_versions={n:__import__('importlib.metadata',fromlist=['version']).version(n) for n in ('torch','numpy','mujoco')},
        permission_envelope='E16-v1 APPROVED',cohort_seed=cohort_seed,search_seed=search_seed,network_initialization_seed=0,
        proposal_mode='distilled' if value else 'p0',observation_schema=P.O0,
        policy_checkpoint=str(policy),policy_sha256=D.sha256_file(policy),value_checkpoint=str(value) if value else None,value_sha256=D.sha256_file(value) if value else None,
        scalers=str(scalers),scalers_sha256=D.sha256_file(scalers),snapshot_lock_sha256=D.sha256_file(D.BASE_SNAP/'data_snapshot.lock.json'),
        source_sha256={p.name:D.sha256_file(p) for p in HERE.glob('*.py')},teacher_source_sha256=C.teacher_sources(dom),
        host_allowlist=['gvlab'],workers=1,threads=1,gpu=False,wall_envelope_s=wall,cpu_envelope_s=cpu,
        rss_limit_kib=(envelope['ram_ceiling_gib']-1)*2**20,disk_budget_root=str(campaign_root),disk_budget_bytes=envelope['new_disk_ceiling_gib']*2**30,
        query_wall_s=cfg['query_wall_s'],aggregate_adapter_call_ceiling=cfg['per_root_adapter_cap'],
        per_tree=dict(iterations=12,max_sim_calls=cfg['per_root_adapter_cap'],expansion_budget_B=2,C=1.5,k=2.,alpha=.3,max_depth=3,reward_mode='geometric'))


def run(envelope_path,cohort_path,out):
    envelope=jsonread(envelope_path);cohorts=jsonread(cohort_path)
    validate_authorization(envelope,cohort_path)
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU only')
    source_commit=os.environ['DISCO_SOURCE_COMMIT'];out=out.resolve()
    if not out.is_relative_to((D.DISCO_ROOT/'stage2').resolve()):raise ValueError('New Stage 2 output required')
    out.mkdir(parents=True,exist_ok=True);checked_resources(out,envelope)
    identity=dict(source_commit=source_commit,source_sha256={p.name:D.sha256_file(p) for p in HERE.glob('*.py')},envelope=envelope,cohorts=cohorts)
    if (out/'manifest.json').exists():
        if jsonread(out/'manifest.json')!=identity:raise ValueError('Campaign resume source/config mismatch')
    else:J.atomic_json(out/'manifest.json',identity)
    with (out/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'CONTROLLER.json').exists():raise RuntimeError('Controller restart requires reconciliation of overhead; no silent reset')
        J.atomic_json(out/'CONTROLLER.json',dict(J.process_identity(),monotonic_start=CONTROLLER_START,cpu_start=0.))
        for dom in ['2d','3d']:
            try:
                streams=[];previous=None;cfg=envelope['domains'][dom]
                roots=cohorts['domains'][dom]['train_roots']
                if len(roots)!=cfg['independent_train_roots'] or len(set(r['family_id'] for r in roots))!=len(roots):raise ValueError('Independent root quota mismatch')
                for rnd in range(2):
                    clean=[];round_rows=[]
                    for root in roots:
                        checked_resources(out,envelope)
                        td=out/f'trees/{dom}/R{rnd}'/root['root_id']
                        if (td/'ATTEMPT_COMPLETE.json').exists():
                            status=jsonread(td/'ATTEMPT_COMPLETE.json')
                        else:
                            totals=accounting(out,dom)
                            wall=min(cfg['root_wall_s'],cfg['active_wall_s']-totals['wall_s']-65)
                            cpu=cfg['aggregate_cpu_s']-totals['cpu_s']-65
                            if charged_calls(out,dom)+cfg['per_root_adapter_cap']>cfg['aggregate_adapter_cap']:raise RuntimeError('AGGREGATE_CALL_CAP')
                            if wall<cfg['query_wall_s'] or cpu<=0:raise RuntimeError('COLLECTION_AGGREGATE_BUDGET_EXHAUSTED')
                            if td.exists():raise RuntimeError(f'Unreconciled controller interruption: {td}')
                            td.mkdir(parents=True)
                            policy=previous/f'{P.O0}_all_feasible_s0/policy.pt' if previous else D.DISCO_ROOT/f'runs/p0/{dom}/s0/model.pt'
                            value=previous/f'{P.O0}_all_feasible_s0/value.pt' if previous else None
                            m=tree_manifest(dom,root,policy,value,rnd,envelope,cohorts,source_commit,wall,cpu,out)
                            J.atomic_json(td/'manifest.json',m)
                            print(dom,'R'+str(rnd),root['root_id'],'START',flush=True)
                            C.execute(td)
                            state_dir=td/root['root_id'];is_clean=(state_dir/'checkpoint.pkl').exists() and not (state_dir/'IN_FLIGHT').exists()
                            status=dict(root_id=root['root_id'],split='train',K_legacy=root['K_legacy'],family_id=root['family_id'],
                                clean=is_clean,tree=str(state_dir),cancellation=jsonread(td/'BLOCKED_WALL_LIMIT.json') if (td/'BLOCKED_WALL_LIMIT.json').exists() else None,status='COMPLETED' if is_clean else 'QUARANTINED_UNRESOLVED')
                            J.atomic_json(td/'ATTEMPT_COMPLETE.json',status)
                        round_rows.append(status)
                        if status['clean']:clean.append(status['tree'])
                        J.atomic_json(out/f'coverage_{dom}_R{rnd}.json',round_rows)
                        print(dom,'R'+str(rnd),root['root_id'],status['status'],accounting(out,dom),flush=True)
                    if not clean:raise RuntimeError('NO_COMPLETED_PHYSICAL_TREES')
                    streams.append(clean)
                    fit=out/f'training/{dom}_P{rnd+1}Q{rnd+1}'
                    dispatch_fit(dom,fit,streams,previous,envelope,out);previous=fit
                J.atomic_json(out/f'{dom}_TRAINING_COMPLETE.json',dict(selected_checkpoint_rule='fixed epochs, no TEST selection',rounds=2,
                    final_fit=str(previous),physical_task_evaluation='NOT_RUN',accounting=accounting(out,dom)))
            except Exception as err:
                J.atomic_json(out/f'{dom}_BLOCKED.json',dict(error=type(err).__name__,reason=str(err),accounting=accounting(out,dom)))
                print(dom,'BLOCKED',str(err),flush=True)
        J.atomic_json(out/'CONTROLLER_COMPLETE.json',dict(physical_task_evaluation='NOT_RUN',neural_accounting=accounting(out,training=True),controller_overhead=controller_overhead(out)))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--envelope',type=Path,required=True);a.add_argument('--cohorts',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();run(v.envelope,v.cohorts,v.out)
