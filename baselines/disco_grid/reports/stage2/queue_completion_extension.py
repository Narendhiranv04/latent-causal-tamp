"""Queue the explicitly approved frozen 2D extension after existing physics.

Only metadata is amended: original evidence remains read-only through symlinks.
The existing continuation engine validates models, sources, journals and quotas.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import time
import monitor_frozen_evaluation as M


def prepare(prior,request_path,approval_path,out):
    prior=Path(prior);request=M.read(request_path);approval=M.read(approval_path)
    if (approval.get('status')!='APPROVED' or approval.get('scope')!='DISCO_ONLY_FROZEN_2D_TEST_CPU_EXTENSION'
            or not approval.get('authorization_text') or approval.get('request_sha256')!=M.digest(request_path)):
        raise PermissionError('Exact approved request required')
    expected=dict(additional_cpu_s=43200,additional_active_wall_s=18000,maximum_additional_adapter_calls=370,
        remaining_trials=113,workers=3,host='girish-laptop',gpu=False,ram_gib=4,new_disk_gib=2,
        reserved_physical_cores=2,global_adapter_call_ceiling=5523,query_wall_s=60,trial_wall_s=300)
    for key,value in expected.items():
        request_key='global_adapter_ceiling_unchanged' if key=='global_adapter_call_ceiling' else key
        if approval.get(key)!=value or request.get(request_key)!=value:raise PermissionError('Approval limits differ: '+key)
    jobs=M.read(prior/'test_2d_jobs.json')['jobs']
    observed=[json.loads(s) for s in (prior/'test_2d/outcomes.jsonl').read_text().splitlines()]
    seen=[r['job_id'] for r in observed]
    if len(set(seen))!=len(seen):raise ValueError('Duplicate prior attempts')
    pending=[j for j in jobs if j['id'] not in set(seen)];registry={j['id']:j for j in request['jobs']}
    if len(registry)!=113 or {j['id'] for j in pending}!=set(registry):raise ValueError('Frozen pending trial registry changed')
    for job in pending:
        digest=__import__('hashlib').sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
        if digest!=registry[job['id']]['job_sha256']:raise ValueError('Frozen job bytes changed')
        if job['domain']!='2d' or job['query_wall_s']!=60 or job['trial_wall_s']!=300:raise ValueError('Teacher budget changed')
    if sum(j['adapter_call_cap'] for j in pending)!=370:raise ValueError('Physical-query cap changed')
    envelope=copy.deepcopy(M.read(prior/'APPROVED_ENVELOPE.json'))
    if envelope['global_adapter_call_ceiling']!=5523 or envelope['ceilings']['3d']['test']!=21600:
        raise PermissionError('Original aggregate/3D ceiling changed')
    charge=M.read(prior/'test_2d/ACCOUNTING.json')
    envelope['wall_ceilings']=copy.deepcopy(envelope.get('wall_ceilings',envelope['ceilings']))
    envelope['ceilings']['2d']['test']=charge['cpu_s']+43200
    envelope['wall_ceilings']['2d']['test']=charge['active_wall_s']+18000
    extension=dict(approval_path=str(Path(approval_path).resolve()),approval_sha256=M.digest(approval_path),
        request_path=str(Path(request_path).resolve()),request_sha256=M.digest(request_path),
        initial_cpu_s=charge['cpu_s'],initial_active_wall_s=charge['active_wall_s'],initial_adapter_calls=charge['adapter_calls'],
        job_ids=[j['id'] for j in pending],cumulative_disk_root=str(Path(out).parent.resolve()),
        original_release=str(prior.resolve()),original_complete_sha256=M.digest(prior/'COMPLETE.json'),
        original_selection_freeze_sha256=M.digest(prior/'SELECTION_FREEZE.json'),approval=approval)
    envelope['completion_extension']=extension
    out=Path(out);out.mkdir(exist_ok=False)
    for name in ('COMPLETE.json','SELECTION_FREEZE.json','HOST_MIGRATION.json','ORIGINAL_TRANSFER_INDEX.json','PARALLEL_HANDOFF.json'):
        if (prior/name).exists():(out/name).symlink_to((prior/name).resolve())
    for phase in ('val','test'):
        for domain in ('2d','3d'):
            for name in (f'{phase}_{domain}',f'{phase}_{domain}_jobs.json'):
                (out/name).symlink_to((prior/name).resolve(),target_is_directory=(prior/name).is_dir())
    M.write(out/'APPROVED_ENVELOPE.json',envelope);M.write(out/'COMPLETION_EXTENSION.json',extension)
    return extension


def run(config_path,state):
    config=M.read(config_path);state=Path(state);state.mkdir(exist_ok=False);started=time.monotonic();cpu_start=time.process_time()
    def status(value,**kw):M.write(state/'STATUS.json',dict(status=value,**kw))
    try:
        upstream=Path(config['upstream_monitor'])
        while not (upstream/'FINAL.json').exists():
            if (upstream/'ERROR.json').exists():raise RuntimeError('Upstream stopped for audit: '+str(upstream/'ERROR.json'))
            if not M.alive(M.read(config['upstream_launch'])):raise RuntimeError('Upstream monitor exited without terminal evidence')
            if time.monotonic()-started>21600:raise RuntimeError('Bounded upstream observation exhausted')
            status('QUEUED_BEHIND_3D',upstream=str(upstream));time.sleep(30)
        prior=Path(M.read(upstream/'FINAL.json')['current_release'])
        root=Path(config['extension_root']);root.mkdir(exist_ok=False)
        view=root/'approved_prior_view';prepare(prior,config['request'],config['approval'],view)
        # Recheck sustained spare capacity without changing the engine guards.
        stable=0;began=time.monotonic()
        while stable<3:
            h=M.headroom(config['disco_root']);stable=stable+1 if h['load1']<=18 and h['ram_available']>=8*2**30 and h['disk_free']>=20*2**30 else 0
            status('WAITING_HEADROOM',headroom=h,stable_samples=stable)
            if time.monotonic()-began>18000:raise RuntimeError('Extension headroom wait exhausted; no physical launch')
            time.sleep(30)
        engine=Path(config['engine']);physical_template=list(config['physical_template']);physical_template[-3]=str(engine/'reports/stage2/continue_frozen_test.py')
        target=root/'release_initial';cmd=physical_template;cmd[-2:]=[str(view),str(target)]
        with (state/'physical_initial.log').open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        launch=dict(pid=p.pid,proc_stat=Path(f'/proc/{p.pid}/stat').read_text(),command=cmd,output=str(target),log=str(state/'physical_initial.log'),source_commit=config['source_commit'])
        lp=state/'physical_initial_launch.json';M.write(lp,launch)
        report=root/'report_initial';cmd=list(config['report_template']);cmd[-4]=str(engine/'reports/stage2/finish_physical_release.py');cmd[-3]=str(lp);cmd[-2]=str(report)
        with (state/'report_initial.log').open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        rp=state/'report_initial_launch.json';M.write(rp,dict(pid=p.pid,proc_stat=Path(f'/proc/{p.pid}/stat').read_text(),command=cmd))
        mc=dict(initial_launch=str(lp),initial_report_launch=str(rp),initial_report=str(report),initial_version='v200',
            version_base=200,run_prefix='completion_continuation',report_base=str(root),disco_root=config['disco_root'],
            max_elapsed_s=18000,max_continuations=6,poll_s=30,physical_source_commit=config['source_commit'])
        mp=state/'monitor_config.json';M.write(mp,mc);status('MONITORED_EXTENSION_RUNNING',release=str(target))
        M.run(mp,state/'monitor')
        # One terminal pointer lets the existing publication observer transfer
        # final combined 2D/3D evidence without modifying an earlier package.
        final=M.read(state/'monitor/FINAL.json');final['queue_cpu_note']='Queue uses metadata/idle observation only; physical and monitor costs have separate ledgers.'
        account=dict(queue_and_nested_monitor_cpu_s=time.process_time()-cpu_start,
            elapsed_wall_including_idle_observation_s=time.monotonic()-started,
            note='CPU includes the nested monitor; do not add its separate monitor CPU a second time. Child physics/reporting CPU is recorded separately. Wall overlaps child phases and must not be summed.')
        M.write(Path(final['report'])/'COMPLETION_QUEUE_ACCOUNTING.json',account)
        M.write(state/'FINAL.json',final);status('FINAL_WITH_LIMITATIONS',report=final['report'])
    except BaseException as exc:
        M.write(state/'ERROR.json',dict(status='STOPPED_NEEDS_AUDIT',error=repr(exc)));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('config',type=Path);p.add_argument('state',type=Path)
    a=p.parse_args();run(a.config,a.state)
