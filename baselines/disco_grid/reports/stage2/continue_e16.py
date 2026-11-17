"""Explicit continuation after the conservative controller-overhead reserve stops E16.

Original engine/source, frozen roots and per-query/host guards remain unchanged.
Every prior intent, child attempt, and controller CPU/wall cost is charged. The
original controller must have exited cleanly; unresolved roots are never retried.
This corrects the overly small bookkeeping reserve, without increasing ceilings.
"""
import argparse, fcntl, hashlib, importlib, json, os, sys, time
from pathlib import Path


def read(p):return json.loads(Path(p).read_text())


def live_child_cpu():
    children=Path(f'/proc/{os.getpid()}/task/{os.getpid()}/children').read_text().split()
    total=0.
    for pid in children:
        try:
            fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            total+=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
        except (FileNotFoundError,ProcessLookupError):pass
    return total


def charged_totals(costs,overhead):
    return dict(costs,cpu_s=costs['cpu_s']+overhead['cpu_s'],wall_s=costs['wall_s']+overhead['wall_s'],shared_controller_charge=overhead)


def run(engine,out,controller_commit,continuation_id="001",prior_ledger=None,include_r0_prefixes=None):
    began=time.monotonic()
    sys.path.insert(0,str(engine));CA=importlib.import_module('campaign');C=CA.C;D=CA.D;J=CA.J;P=CA.P
    if not (out/'CONTROLLER_COMPLETE.json').exists():raise RuntimeError('Original controller not reconciled/complete')
    original=read(out/'manifest.json');envelope=original['envelope'];cohorts=original['cohorts']
    # Validate immutable original authorization by exact original files and limits.
    ep=engine/'reports/stage2/COMPUTE_ENVELOPE_REQUEST.json';cp=engine/'reports/stage2/cohorts.json'
    CA.validate_authorization(read(ep),cp)
    if read(ep)!=envelope or read(cp)!=cohorts:raise ValueError('Original cohort/envelope mismatch')
    for name,sha in original['source_sha256'].items():
        if D.sha256_file(engine/name)!=sha:raise ValueError('Original engine changed')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU only')
    # No unknown controller/child accounting is silently reset.
    for p in out.glob('trees/*/*/*/attempts/*/START.json'):
        if not (p.parent/'WATCHDOG_ACCOUNTING.json').exists():raise ValueError('Unreconciled child attempt')
    for p in out.glob('training/*/attempts/*/START.json'):
        if not (p.parent/'WATCHDOG_ACCOUNTING.json').exists():raise ValueError('Unreconciled fit attempt')
    ledger=out/f'continuation_{continuation_id}';ledger.mkdir(exist_ok=False)
    J.atomic_json(ledger/'manifest.json',dict(controller_source_commit=controller_commit,controller_sha256=D.sha256_file(__file__),
        original_manifest_sha256=D.sha256_file(out/'manifest.json'),original_engine_commit=original['source_commit'],
        original_controller_complete_sha256=D.sha256_file(out/'CONTROLLER_COMPLETE.json'),prior_ledger=str(prior_ledger) if prior_ledger else None,prior_ledger_sha256=D.sha256_file(prior_ledger) if prior_ledger else None,include_r0_prefixes=str(include_r0_prefixes) if include_r0_prefixes else None,
        reason='Replace fixed 55-second bookkeeping cutoff by measured conservative aggregate charging; no limit increase'))
    prior=read(prior_ledger or out/'CONTROLLER_COMPLETE.json')['controller_overhead'];phase=None
    historical=[out/'CONTROLLER_COMPLETE.json']+list(out.glob('continuation_*/COMPLETE.json'))+list(out.glob('known_prefix_fit*/COMPLETE.json'))
    if prior['cpu_s']+1e-6<max(read(p)['controller_overhead']['cpu_s'] for p in historical):raise ValueError('Prior controller ledger omits charged CPU')
    original_accounting=CA.accounting
    def raw_jobs():return sum(original_accounting(out,d)['wall_s'] for d in ('2d','3d'))+original_accounting(out,training=True)['wall_s']
    jobs_before=raw_jobs()
    def overhead():
        pending=list(out.glob('trees/*/*/*/attempts/*/START.json'))+list(out.glob('training/*/attempts/*/START.json'))
        active=sum(max(0.,time.monotonic()-read(p)['monotonic_start']) for p in pending if not (p.parent/'WATCHDOG_ACCOUNTING.json').exists())
        return dict(cpu_s=prior['cpu_s']+time.process_time(),wall_s=prior['wall_s']+max(0.,time.monotonic()-began-(raw_jobs()-jobs_before)-active))
    def charged(root,domain=None,training=False):
        costs=original_accounting(root,domain,training);oh=overhead()
        # Conservatively charge ALL shared controller work to EACH envelope.
        # It is reported separately and must not be summed as physical CPU cost.
        return charged_totals(costs,oh)
    def resources(root,e):
        try:r=C.require_headroom()
        except RuntimeError as error:
            J.atomic_json(ledger/'RESOURCE_REJECTION.json',dict(phase=phase,error=str(error),resources=C.resources()));raise
        if sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>e['new_disk_ceiling_gib']*2**30:raise RuntimeError('CAMPAIGN_DISK_LIMIT')
        if phase=='training' and charged(out,training=True)['cpu_s']+live_child_cpu()>=e['neural_training']['cpu_s_cap']-6:
            J.atomic_json(ledger/'RESOURCE_REJECTION.json',dict(phase=phase,error='AGGREGATE_FIT_CPU_LIMIT',charged=charged(out,training=True),live_child_cpu=live_child_cpu()));raise RuntimeError('AGGREGATE_FIT_CPU_LIMIT')
        J.atomic_json(ledger/'CONTROLLER_OVERHEAD.json',overhead());return r
    original_headroom=C.manifest_headroom
    def bounded_headroom(m):
        try:r=original_headroom(m)
        except RuntimeError as error:
            J.atomic_json(ledger/'RESOURCE_REJECTION.json',dict(phase='collection',error=str(error),resources=C.resources()));raise
        if charged(out,m['domain'])['cpu_s']+live_child_cpu()>=envelope['domains'][m['domain']]['aggregate_cpu_s']-6:raise RuntimeError('AGGREGATE_COLLECTION_CPU_LIMIT')
        return r
    C.manifest_headroom=bounded_headroom
    CA.accounting=charged;CA.checked_resources=resources
    with (out/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        J.atomic_json(ledger/'CONTROLLER.json',J.process_identity())
        for dom in ('2d','3d'):
            try:
                streams=[];previous=None;cfg=envelope['domains'][dom];roots=cohorts['domains'][dom]['train_roots']
                for rnd in range(2):
                    clean=[];rows=[]
                    for root in roots:
                        resources(out,envelope);td=out/f'trees/{dom}/R{rnd}'/root['root_id']
                        if (td/'ATTEMPT_COMPLETE.json').exists():status=read(td/'ATTEMPT_COMPLETE.json')
                        else:
                            if td.exists():raise RuntimeError(f'Unreconciled tree directory {td}; no automatic retry')
                            totals=charged(out,dom);wall=min(cfg['root_wall_s'],cfg['active_wall_s']-totals['wall_s']-65);cpu=cfg['aggregate_cpu_s']-totals['cpu_s']-65
                            if wall<cfg['query_wall_s'] or cpu<=0:raise RuntimeError('COLLECTION_AGGREGATE_BUDGET_EXHAUSTED')
                            if CA.charged_calls(out,dom)+cfg['per_root_adapter_cap']>cfg['aggregate_adapter_cap']:raise RuntimeError('AGGREGATE_CALL_CAP')
                            td.mkdir(parents=True)
                            policy=previous/f'{P.O0}_all_feasible_s0/policy.pt' if previous else D.DISCO_ROOT/f'runs/p0/{dom}/s0/model.pt'
                            value=previous/f'{P.O0}_all_feasible_s0/value.pt' if previous else None
                            m=CA.tree_manifest(dom,root,policy,value,rnd,envelope,cohorts,original['source_commit'],wall,cpu,out)
                            m['controller_provenance']=dict(commit=controller_commit,sha256=D.sha256_file(__file__))
                            J.atomic_json(td/'manifest.json',m);print(dom,'R'+str(rnd),root['root_id'],'CONTINUE_START',flush=True)
                            C.execute(td)
                            state=td/root['root_id'];ok=(state/'checkpoint.pkl').exists() and not (state/'IN_FLIGHT').exists() and not (state/'ACTIVE_QUERY.json').exists()
                            status=dict(root_id=root['root_id'],split='train',K_legacy=root['K_legacy'],family_id=root['family_id'],clean=ok,tree=str(state),
                                status='COMPLETED' if ok else 'QUARANTINED_UNRESOLVED',cancellation=read(td/'BLOCKED_WALL_LIMIT.json') if (td/'BLOCKED_WALL_LIMIT.json').exists() else None)
                            J.atomic_json(td/'ATTEMPT_COMPLETE.json',status)
                        rows.append(status)
                        if status['clean']:clean.append(status['tree'])
                        J.atomic_json(ledger/f'coverage_{dom}_R{rnd}.json',rows)
                    if dom=='3d' and rnd==0 and include_r0_prefixes:
                        if list((out/'training/3d_P1Q1').glob('*/trainer.pt')):raise RuntimeError('R0 eligibility cannot change after any P1 epoch')
                        recovered=read(include_r0_prefixes)['records']
                        added=[r['destination'] for r in recovered if r['status']=='CERTIFIED_COMPLETED_ITERATION_PREFIX' and Path(r['destination']).parent.parent.name==dom and Path(r['destination']).parent.name=='R0']
                        clean.extend(sorted(added));J.atomic_json(ledger/'3d_R0_FIT_SOURCES.json',dict(trees=clean,added_certified_prefixes=added,physical_queries=0,eligibility_changed_before_any_P1_epoch=True))
                    if not clean:raise RuntimeError('NO_COMPLETED_PHYSICAL_TREES')
                    streams.append(clean);fit=out/f'training/{dom}_P{rnd+1}Q{rnd+1}'
                    phase='training'
                    CA.dispatch_fit(dom,fit,streams,previous,envelope,out);previous=fit
                    phase=None
                J.atomic_json(ledger/f'{dom}_TRAINING_COMPLETE.json',dict(final_fit=str(previous),rounds=2,charged_cost_upper_bound=charged(out,dom),physical_task_evaluation='NOT_RUN'))
            except Exception as error:
                J.atomic_json(ledger/f'{dom}_BLOCKED.json',dict(error=type(error).__name__,reason=str(error),charged_cost_upper_bound=charged(out,dom)))
                print(dom,'BLOCKED',str(error),flush=True)
        J.atomic_json(ledger/'COMPLETE.json',dict(controller_overhead=overhead(),neural_charged_cost_upper_bound=charged(out,training=True)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--controller-commit',required=True);p.add_argument('--continuation-id',default='001');p.add_argument('--prior-ledger',type=Path);p.add_argument('--include-r0-prefixes',type=Path);a=p.parse_args();run(a.engine,a.out,a.controller_commit,a.continuation_id,a.prior_ledger,a.include_r0_prefixes)
