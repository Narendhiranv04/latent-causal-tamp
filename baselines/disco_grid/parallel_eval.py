"""Three supervised CPU trials with aggregate reservations and no physical retry.

Each supervisor owns exactly one physical child, so RUSAGE_CHILDREN accounting
cannot double-count siblings. The coordinator reserves CPU and query quotas
before dispatch and releases unused quota only after durable completion.
"""
import fcntl
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import collect as C, data as D, journal as J, physical_eval as PE


def read(path):return json.loads(Path(path).read_text())


def supervise(job,directory,parent_pid,quota,worker_target):
    J.die_with_parent(parent_pid);os.setsid();os.nice(9)
    worker=mp.get_context('spawn').Process(target=worker_target,args=(job,directory,os.getpid()))
    worker.start();error=None
    def resources():
        C.require_headroom()
        if (directory/'CANCEL').exists():raise RuntimeError('Coordinator requested bounded pool stop')
        if time.process_time()>9:raise RuntimeError('Supervisor CPU reserve exhausted')
    try:
        J.wait_for_child(worker,job['trial_wall_s'],directory=directory,query_wall_s=job['query_wall_s'],
            cpu_seconds=quota-20,rss_limit_kib=3*2**20,resource_check=resources)
    except BaseException as exc:error=repr(exc)
    finally:
        account=read(directory/'WATCHDOG_ACCOUNTING.json')
        J.atomic_json(directory/'SUPERVISOR_COMPLETE.json',dict(
            supervisor_cpu_s=time.process_time(),physical_child_cpu_s=account['reaped_child_cpu_s'],
            cpu_s=time.process_time()+account['reaped_child_cpu_s'],reserved_cpu_s=quota,
            parent_identity=J.process_identity(parent_pid),child_account=account,error=error))


def owned_rss_kib():
    processes={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            fields=(p/'stat').read_text().rpartition(')')[2].split()
            processes[int(p.name)]=(int(fields[1]),int(fields[21])*os.sysconf('SC_PAGE_SIZE')//1024)
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    owned={os.getpid()}
    while True:
        expanded=owned|{pid for pid,(parent,rss) in processes.items() if parent in owned}
        if expanded==owned:break
        owned=expanded
    return sum(processes[p][1] for p in owned if p in processes)


def reserve_cpu(limit,used,reserved,trial_wall):
    # Twenty seconds cover supervisor CPU, polling and TERM/KILL grace in
    # addition to the physical child's quota. Reservations bound aggregate CPU.
    free=limit-used-reserved-10
    return max(0.,min(trial_wall+20,free))


def disk_bytes(root):
    total=0
    for path in root.rglob('*'):
        try:
            if path.is_file():total+=path.stat().st_size
        except FileNotFoundError:
            # A journal's atomic temporary file may be renamed during a scan.
            # It is present under its destination name on the next guard poll.
            continue
    return total


def run(jobs_path,envelope_path,out,worker_target=PE.trial_worker):
    envelope=read(envelope_path);jobs=PE.validate_execution(jobs_path,envelope)
    slots=envelope['workers']
    if slots not in (3,4):raise PermissionError('Explicit parallel worker amendment required')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise PermissionError('Frozen CPU inference required')
    if not out.resolve().is_relative_to((D.DISCO_ROOT/'stage2').resolve()):raise ValueError('Isolated stage2 output required')
    disk_root=Path(envelope.get('cumulative_disk_root',out)).resolve()
    if not out.resolve().is_relative_to(disk_root) or not disk_root.is_relative_to((D.DISCO_ROOT/'stage2').resolve()):
        raise ValueError('Disk accounting must cover this isolated Stage 2 output')
    C.require_headroom();out.mkdir(parents=True,exist_ok=False)
    source={p.name:D.sha256_file(p) for p in HERE.glob('*.py')}
    J.atomic_json(out/'manifest.json',dict(envelope=envelope,jobs_sha256=D.sha256_file(jobs_path),
        source_commit=os.environ['DISCO_SOURCE_COMMIT'],source_sha256=source,
        scheduling=f'Frozen job order, first dispatchable entry; identical in-flight sequence certificates wait for completion. {slots} slots, one thread each, no retries.'))
    start=time.monotonic();cpu_start=time.process_time();used_cpu=0.;calls=0;worker_cpu=0.;worker_wall=0.
    pending=list(enumerate(jobs));active={};rows={};certificates={};certificate_sources={};peak_rss=0;peak_active=0;stop=None;dispatch=[]
    def save():
        J.atomic_bytes(out/'outcomes.jsonl',''.join(json.dumps(PE.plain(rows[i]))+'\n' for i in sorted(rows)).encode())
        J.atomic_json(out/'ACCOUNTING.json',dict(cpu_s=used_cpu+time.process_time()-cpu_start,
            worker_cpu_s=worker_cpu,controller_cpu_s=used_cpu-worker_cpu+time.process_time()-cpu_start,
            worker_wall_s=worker_wall,active_wall_s=time.monotonic()-start,adapter_calls=calls,
            n_attempted=len(rows),n_frozen_jobs=len(jobs),n_not_run=len(jobs)-len(rows),
            workers=slots,max_concurrent_trials=peak_active,sampled_peak_pool_rss_kib=peak_rss,stop_reason=stop,
            in_flight_reservations=[dict(job_id=a['job']['id'],cpu_s=a['quota'],adapter_calls=a['job']['adapter_call_cap']) for a in active.values()],
            cpu_accounting_kind='MEASURED_SUPERVISORS_AND_REAPED_CHILDREN'))
    def complete(i,res,directory):
        rows[i]=dict(res,execution_host=envelope['host'])
        key=PE.verification_key(jobs[i],source)
        if key and res.get('x') in (0,1) and res.get('y') in (0,1):
            certificates[key]=res
            path=directory/'result.json' if (directory/'result.json').exists() else directory/'reconciled_result.json'
            certificate_sources[key]=dict(job_id=res['job_id'],result=str(path),result_sha256=D.sha256_file(path))
            J.atomic_json(out/'verification_cache_manifest.json',certificate_sources)
        print(len(rows),len(jobs),jobs[i]['domain'],jobs[i]['arm'],jobs[i]['root_id'],res['status'],
            'Z='+str(res.get('verified')),'charged_calls='+str(calls),'active='+str(len(active)),flush=True)
    def harvest():
        nonlocal used_cpu,worker_cpu,worker_wall,calls
        for i,a in list(active.items()):
            process=a['process']
            if process.is_alive():continue
            process.join();directory=a['directory'];path=directory/'SUPERVISOR_COMPLETE.json'
            account=read(path) if path.exists() else dict(cpu_s=a['quota'],physical_child_cpu_s=a['quota'])
            used_cpu+=account['cpu_s'];worker_cpu+=account['physical_child_cpu_s']
            watchdog=read(directory/'WATCHDOG_ACCOUNTING.json') if (directory/'WATCHDOG_ACCOUNTING.json').exists() else {}
            worker_wall+=watchdog.get('wall_s',0.)
            calls+=sum(e['event']=='started' for e in J.read_events(directory))
            if (directory/'result.json').exists():res=read(directory/'result.json')
            else:
                res=PE.reconcile_returned_proof(a['job'],directory)
                if res is None:
                    res={k:a['job'][k] for k in ('root_id','domain','seed','arm','protocol','K_legacy','family_id')}
                    res.update(job_id=a['job']['id'],status='UNRESOLVED',verified=None,x=None,y=None,
                        failure_kind=watchdog.get('reason') or 'SUPERVISOR_ERROR',evidence=str(directory))
                J.atomic_json(directory/'reconciled_result.json',res)
            del active[i];complete(i,res,directory);save()
    with (D.DISCO_ROOT/'active_physical.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            while pending or active:
                harvest()
                peak_rss=max(peak_rss,owned_rss_kib())
                if not stop:
                    try:C.require_headroom()
                    except RuntimeError as exc:stop=str(exc)
                    if peak_rss>=4*2**20:stop='POOL_RAM_LIMIT_4_GIB'
                    if time.monotonic()-start>=envelope['active_wall_s']-10:stop='PHASE_WALL_LIMIT'
                    if disk_bytes(disk_root)>=envelope['disk_gib']*2**30:stop='PHASE_DISK_LIMIT'
                if stop:
                    for a in active.values():J.atomic_bytes(a['directory']/'CANCEL',stop.encode())
                    pending=[]
                else:
                    for i,job in list(pending):
                        key=PE.verification_key(job,source)
                        if key and any(a['key']==key for a in active.values()):continue
                        cheap=key in certificates or job['protocol']=='open_loop' and job['prediction']['status']=='ABSTAIN'
                        if not cheap and len(active)>=slots:continue
                        quota=reserve_cpu(envelope['cpu_s'],used_cpu+time.process_time()-cpu_start,
                            sum(a['quota'] for a in active.values()),job['trial_wall_s'])
                        if not cheap and (quota<job['query_wall_s']+20 or
                                calls+sum(a['job']['adapter_call_cap'] for a in active.values())+job['adapter_call_cap']>envelope['adapter_calls'] or
                                envelope['active_wall_s']-(time.monotonic()-start)<=job['query_wall_s']+10):continue
                        directory=out/f'{i:04d}_{job["id"]}';directory.mkdir();J.atomic_json(directory/'job.json',job)
                        pending.remove((i,job));dispatch.append(job['id']);J.atomic_json(out/'DISPATCH_ORDER.json',dispatch)
                        if key in certificates:
                            cert=certificates[key]
                            res=dict(job['prediction'],**{k:cert[k] for k in ('verified','x','y','failed_phase','failure_kind')},
                                arm=job['arm'],family_id=job['family_id'],job_id=job['id'],physics_seed=job['physics_seed'],
                                adapter_calls=0,physical_phases={},robot_travel_reference=cert.get('robot_travel_reference'),
                                independent_verification=True,physical_verification_reuse_from=cert['job_id'],verification_key=key)
                            J.atomic_json(directory/'result.json',res);complete(i,res,directory);save()
                        elif cheap:
                            res=dict(job['prediction'],verified=0,x=None,y=None,failed_phase='abstain',failure_kind='ABSTAIN',
                                arm=job['arm'],family_id=job['family_id'],job_id=job['id'],adapter_calls=0,
                                physical_phases={},verification_source='explicit_abstention_no_query')
                            J.atomic_json(directory/'result.json',res);complete(i,res,directory);save()
                        else:
                            process=mp.get_context('spawn').Process(target=supervise,args=(job,directory,os.getpid(),quota,worker_target))
                            process.start();active[i]=dict(process=process,job=job,directory=directory,key=key,quota=quota)
                            peak_active=max(peak_active,len(active))
                    if pending and not active:
                        stop='CPU_QUERY_OR_WALL_RESERVATION_LIMIT';pending=[]
                if active:time.sleep(.1)
        finally:
            # Supervisors must reap their own physical child before the pool
            # exits. Never terminate a supervisor first and lose child costs.
            for a in active.values():J.atomic_bytes(a['directory']/'CANCEL',b'Coordinator stopping')
            for a in active.values():a['process'].join(timeout=15)
            harvest()
            save()
            if active:raise RuntimeError('Supervisor did not complete bounded cancellation; no next phase may launch')
    J.atomic_json(out/'COMPLETE.json',dict(status='COMPLETE' if len(rows)==len(jobs) else 'BUDGET_OR_RESOURCE_LIMITED',
        attempted=len(rows),expected=len(jobs),workers=slots,stop_reason=stop))
    return [rows[i] for i in sorted(rows)]
