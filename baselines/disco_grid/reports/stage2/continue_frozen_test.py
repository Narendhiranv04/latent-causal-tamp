"""Continue only never-attempted TEST jobs; preserve VAL selection and costs."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import collect as C, data as D, journal as J, parallel_eval as POOL


def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]


def remaining_jobs(jobs,observed):
    ids=[r['job_id'] for r in observed]
    if len(set(ids))!=len(ids) or not set(ids)<={j['id'] for j in jobs}:
        raise ValueError('Unexpected or duplicated prior outcomes')
    return [j for j in jobs if j['id'] not in set(ids)]


def run(prior,out):
    start=time.monotonic();cpu_start=time.process_time()
    C.require_headroom();C.execution_host('girish-laptop')
    authorization=read(os.environ['DISCO_EXECUTION_AUTHORIZATION'])
    if authorization['scope']!='DISCO_RELEASE_RESERVED_CORES_AMENDMENT':raise PermissionError('Reserved-core amendment required')
    old=read(prior/'COMPLETE.json');envelope=read(prior/'APPROVED_ENVELOPE.json')
    extension=envelope.get('completion_extension')
    if extension:
        approval=read(extension['approval_path'])
        if (approval.get('status')!='APPROVED' or approval.get('scope')!='DISCO_ONLY_FROZEN_2D_TEST_CPU_EXTENSION'
                or not approval.get('authorization_text') or D.sha256_file(extension['approval_path'])!=extension['approval_sha256']
                or approval['additional_cpu_s']!=43200 or approval['additional_active_wall_s']!=18000
                or approval['maximum_additional_adapter_calls']!=370 or approval['remaining_trials']!=113):
            raise PermissionError('Invalid frozen 2D extension approval')
        if (envelope['ceilings']['2d']['test']!=extension['initial_cpu_s']+43200
                or envelope['wall_ceilings']['2d']['test']!=extension['initial_active_wall_s']+18000
                or envelope['ceilings']['3d']['test']!=21600):
            raise PermissionError('CPU/wall extension does not match explicit approval')
    prep=Path(envelope['preparation']);engine=HERE.parents[1]
    for name,digest in read(prep/'manifest.json')['source_sha256'].items():
        if name not in ('collect.py','physical_eval.py') and D.sha256_file(engine/name)!=digest:
            raise ValueError('Frozen scientific module changed: '+name)
    for model in read(prep/'checkpoint_manifest.json'):
        for kind in ('policy','value'):
            if model.get(kind) and D.sha256_file(model[kind])!=model[kind+'_sha256']:raise ValueError('Checkpoint changed')
    for name,item in envelope['candidate_sets'].items():
        if D.sha256_file(prep/name)!=item['sha256']:raise ValueError('Frozen candidates changed')
    freeze=read(prior/'SELECTION_FREEZE.json')
    all_test=[j for domain in ('2d','3d') for j in read(prior/f'test_{domain}_jobs.json')['jobs']]
    if {j['id'] for j in all_test}!=set(freeze['selected_test_job_ids']):raise ValueError('Selection identity changed')
    # Audit the previous pool's completed ledgers, including cancelled attempts.
    for phase in ('val','test'):
        for domain in ('2d','3d'):
            directory=prior/f'{phase}_{domain}'
            jobs=read(prior/f'{phase}_{domain}_jobs.json')['jobs'];observed=rows(directory/'outcomes.jsonl')
            remaining_jobs(jobs,observed)
            dirs={p.name.split('_',1)[1]:p for p in directory.iterdir() if p.is_dir() and (p/'job.json').exists()}
            if set(dirs)!={r['job_id'] for r in observed}:raise ValueError('Unpublished physical attempt; reconcile before continuing')
            if any(read(p/'ACCOUNTING.json')['in_flight_reservations'] for p in [prior/f'{phase}_{domain}_pool_fragment'] if p.exists()):
                raise ValueError('Prior in-flight reservation')
            account=read(directory/'ACCOUNTING.json')
            actual_calls=sum(e['event']=='started' for p in dirs.values() for e in J.read_events(p))
            if actual_calls!=account['adapter_calls']:raise ValueError('Prior query ledger mismatch')
    out.mkdir(parents=True,exist_ok=False)
    J.atomic_json(out/'APPROVED_ENVELOPE.json',dict(envelope,workers=authorization['workers'],engine=str(engine),
        parallel_authorization=authorization,prior_release=str(prior),source_commit=os.environ['DISCO_SOURCE_COMMIT']))
    for name in ('SELECTION_FREEZE.json','HOST_MIGRATION.json','ORIGINAL_TRANSFER_INDEX.json','PARALLEL_HANDOFF.json'):
        if (prior/name).exists():J.atomic_bytes(out/name,(prior/name).read_bytes())
    if extension:J.atomic_json(out/'COMPLETION_EXTENSION.json',extension)
    J.atomic_json(out/'RESERVED_CORES_HANDOFF.json',dict(prior_release=str(prior),prior_complete_sha256=D.sha256_file(prior/'COMPLETE.json'),
        authorization=authorization,affinity=sorted(os.sched_getaffinity(0)),
        semantics='Never-attempted frozen TEST identities only. No re-selection, no retry of unresolved or cancelled attempts.'))
    for domain in ('2d','3d'):
        for name in (f'val_{domain}',f'val_{domain}_jobs.json'):(out/name).symlink_to(prior/name,target_is_directory=(prior/name).is_dir())
    calls=old['global_adapter_calls'];fresh_accounts=[];own_phase_cpu=0.
    prior_shared=max(0.,old['total_cpu_s']-sum(a['cpu_s'] for a in old['phase_accounting']))
    for domain in ('2d','3d'):
        key=f'test_{domain}';jobs=read(prior/f'{key}_jobs.json')['jobs'];observed=rows(prior/key/'outcomes.jsonl')
        pending=remaining_jobs(jobs,observed);charge=read(prior/key/'ACCOUNTING.json')
        if extension and domain=='2d' and not {j['id'] for j in pending}<=set(extension['job_ids']):
            raise ValueError('2D extension contains an unapproved trial identity')
        J.atomic_json(out/f'{key}_jobs.json',dict(jobs=jobs))
        path=out/f'{key}_remaining_jobs.json';J.atomic_json(path,dict(jobs=pending))
        cap=envelope['ceilings'][domain]['test'];wall_cap=envelope.get('wall_ceilings',envelope['ceilings'])[domain]['test'];allowance=30+prior_shared
        sub=dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',authorization_text=authorization['authorization_text'],
            host='girish-laptop',workers=authorization['workers'],gpu=False,split='test',jobs_sha256=D.sha256_file(path),
            cpu_s=max(0.,cap-charge['cpu_s']-allowance),active_wall_s=max(0.,wall_cap-charge['active_wall_s']-30),
            adapter_calls=5523-calls,disk_gib=8.)
        if extension:
            sub.update(disk_gib=2.,cumulative_disk_root=extension['cumulative_disk_root'])
            if domain=='2d':sub['adapter_calls']=min(sub['adapter_calls'],max(0,extension['initial_adapter_calls']+370-charge['adapter_calls']))
        ep=out/f'{key}_envelope.json';J.atomic_json(ep,sub)
        fragment=out/f'{key}_pool_fragment';phase_cpu=time.process_time();POOL.run(path,ep,fragment)
        own_phase_cpu+=time.process_time()-phase_cpu
        account=read(fragment/'ACCOUNTING.json');fresh_accounts.append(account);calls+=account['adapter_calls']
        combined=out/key;combined.mkdir();positions={j['id']:i for i,j in enumerate(jobs)}
        for i,j in enumerate(jobs):
            p=prior/key/f'{i:04d}_{j["id"]}'
            if p.exists():(combined/p.name).symlink_to(p,target_is_directory=True)
        for i,j in enumerate(pending):
            p=fragment/f'{i:04d}_{j["id"]}'
            if p.exists():(combined/f'{positions[j["id"]]:04d}_{j["id"]}').symlink_to(p,target_is_directory=True)
        merged=observed+rows(fragment/'outcomes.jsonl');merged.sort(key=lambda r:positions[r['job_id']])
        J.atomic_bytes(combined/'outcomes.jsonl',''.join(json.dumps(r)+'\n' for r in merged).encode())
        total={k:charge[k]+account[k] for k in ('cpu_s','active_wall_s','adapter_calls','worker_cpu_s','controller_cpu_s','worker_wall_s')}
        total.update(n_attempted=len(merged),n_frozen_jobs=len(jobs),n_not_run=len(jobs)-len(merged),workers=authorization['workers'],
            prior_charge=charge,new_pool_charge=account,cpu_accounting_kind='MEASURED_SUPERVISORS_AND_REAPED_CHILDREN')
        if total['cpu_s']>cap or total['active_wall_s']>wall_cap:raise RuntimeError('Approved phase ceiling exceeded')
        if extension and domain=='2d' and total['adapter_calls']>extension['initial_adapter_calls']+370:
            raise RuntimeError('Approved 2D extension query ceiling exceeded')
        J.atomic_json(combined/'ACCOUNTING.json',total)
    J.atomic_json(out/'COMPLETE.json',dict(selected_eta=freeze['selected_eta'],workers=authorization['workers'],
        phase_accounting=[read(out/f'{phase}_{domain}/ACCOUNTING.json') for phase in ('val','test') for domain in ('2d','3d')],
        total_cpu_s=old['total_cpu_s']+sum(a['cpu_s'] for a in fresh_accounts)+time.process_time()-cpu_start-own_phase_cpu,
        total_wall_s=old['total_wall_s']+time.monotonic()-start,global_adapter_calls=calls,
        cpu_accounting_kind='PRESERVED_PRIOR_BOUNDS_PLUS_MEASURED_CONTINUATION',
        scope='Original 5523-call ceiling and frozen TEST selection/no-retry preserved; CPU/wall limits include the explicit frozen-2D amendment where recorded'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('prior',type=Path);p.add_argument('out',type=Path)
    args=p.parse_args();run(args.prior,args.out)
