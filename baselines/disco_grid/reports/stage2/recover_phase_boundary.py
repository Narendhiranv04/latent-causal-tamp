"""Audit a stopped between-phase handoff into a new metadata-only release.

Accept only a completed, published 2D fragment and a demonstrably unstarted 3D
pool. Preserve the stopped release. Missing final parent CPU is charged with an
affinity-wide elapsed upper bound, never guessed as an exact measurement.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import time
import monitor_frozen_evaluation as M


def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]


def recover(partial,launch_path,out,execute=False):
    start=time.process_time();partial=Path(partial);out=Path(out);launch=M.read(launch_path)
    if M.alive(launch):raise RuntimeError('Original process still active')
    if (partial/'COMPLETE.json').exists():raise ValueError('Release already has a completed ledger')
    if (partial/'test_3d_pool_fragment').exists():raise ValueError('3D dispatch may have started; requires a different audit')
    envelope=M.read(partial/'APPROVED_ENVELOPE.json');prior=Path(envelope['prior_release'])
    old=M.read(prior/'COMPLETE.json');fragment=partial/'test_2d_pool_fragment'
    fresh=M.read(fragment/'ACCOUNTING.json')
    if fresh['in_flight_reservations']:raise ValueError('Unreaped reservations')
    if not (fragment/'COMPLETE.json').exists():raise ValueError('2D pool did not close')
    current=M.read(partial/'test_2d/ACCOUNTING.json');observed=rows(partial/'test_2d/outcomes.jsonl')
    jobs=M.read(partial/'test_2d_jobs.json')['jobs'];ids={j['id'] for j in jobs}
    if len({r['job_id'] for r in observed})!=len(observed) or not {r['job_id'] for r in observed}<=ids:
        raise ValueError('Invalid published attempt identities')
    dirs=[p for p in (partial/'test_2d').iterdir() if p.is_dir() and (p/'job.json').exists()]
    if {M.read(p/'job.json')['id'] for p in dirs}!={r['job_id'] for r in observed}:raise ValueError('Unpublished attempt directory')
    calls=0
    # Empty/cache-only directories legitimately have no query journal.
    for p in dirs:
        if (p/'queries.jsonl').exists():calls+=sum(e['event']=='started' for e in rows(p/'queries.jsonl'))
    if calls!=current['adapter_calls'] or current['n_attempted']!=len(observed):raise ValueError('Query/count ledger mismatch')
    if M.read(partial/'test_3d_jobs.json')!=M.read(prior/'test_3d_jobs.json'):raise ValueError('Frozen 3D jobs changed')
    if M.digest(partial/'SELECTION_FREEZE.json')!=M.digest(prior/'SELECTION_FREEZE.json'):raise ValueError('VAL freeze changed')
    supervisors=[M.read(p) for p in fragment.glob('*/SUPERVISOR_COMPLETE.json')]
    child_cpu=sum(a['physical_child_cpu_s'] for a in supervisors);supervisor_cpu=sum(a['supervisor_cpu_s'] for a in supervisors)
    if abs(child_cpu-fresh['worker_cpu_s'])>.001:raise ValueError('Reaped child CPU mismatch')
    command=launch['command'];affinity=command[command.index('-c')+1]
    cpus=set()
    for span in affinity.split(','):
        ends=list(map(int,span.split('-')));cpus.update(range(ends[0],ends[-1]+1))
    if cpus!=set(range(22)):raise ValueError('Expected recorded two-core-excluded affinity')
    boot=next(int(s.split()[1]) for s in Path('/proc/stat').read_text().splitlines() if s.startswith('btime '))
    ticks=int(launch['proc_stat'].rpartition(')')[2].split()[19]);began=boot+ticks/os.sysconf('SC_CLK_TCK')
    log=Path(launch['log']);elapsed=max(fresh['active_wall_s'],log.stat().st_mtime-began)+5
    if elapsed>fresh['active_wall_s']+60:raise ValueError('Clock/elapsed evidence inconsistent; no automatic cost guess')
    # This deliberately loose bound covers every allowed controller CPU, even
    # if an imported runtime used more than one thread. Retain measured child
    # and supervisor costs in addition, never call the result exact CPU time.
    parent_upper=elapsed*len(cpus)
    phase_parent=max(0.,fresh['controller_cpu_s']-supervisor_cpu)
    extra=max(0.,parent_upper-phase_parent)
    adjusted=copy.deepcopy(current);adjusted['cpu_s']+=extra;adjusted['controller_cpu_s']+=extra
    adjusted['active_wall_s']+=max(0.,elapsed-fresh['active_wall_s'])
    adjusted.update(cpu_accounting_kind='CONSERVATIVE_AFFINITY_WIDE_PARENT_ELAPSED_BOUND',
        exact_final_parent_cpu_s=None,additional_controller_upper_charge_s=extra)
    if adjusted['cpu_s']>envelope['ceilings']['2d']['test'] or adjusted['active_wall_s']>envelope['wall_ceilings']['2d']['test']:
        raise ValueError('Conservative recovery charge exceeds existing approval')
    proof=dict(partial=str(partial),original_launch=str(launch_path),physical_queries=0,
        published_2d_attempts=len(observed),new_fragment_attempts=fresh['n_attempted'],adapter_calls=calls,
        no_3d_pool_directory=True,original_error_log_sha256=M.digest(log),
        source_accounting_sha256=M.digest(partial/'test_2d/ACCOUNTING.json'),
        exact_new_child_cpu_s=child_cpu,exact_new_supervisor_cpu_s=supervisor_cpu,
        parent_elapsed_upper_s=elapsed,parent_affinity_cpus=sorted(cpus),parent_cpu_upper_s=parent_upper,
        additional_controller_upper_charge_s=extra,adjusted_2d_cpu_s=adjusted['cpu_s'],
        recovery_cpu_s=time.process_time()-start,scope='Metadata-only audited reconstruction; no retry, new outcome or archive overwrite')
    if not execute:return proof
    out.mkdir(exist_ok=False)
    for name in ('APPROVED_ENVELOPE.json','SELECTION_FREEZE.json','HOST_MIGRATION.json','ORIGINAL_TRANSFER_INDEX.json','PARALLEL_HANDOFF.json','COMPLETION_EXTENSION.json','RESERVED_CORES_HANDOFF.json'):
        if (partial/name).exists():M.write(out/name,M.read(partial/name))
    for phase in ('val','test'):
        for domain in ('2d','3d'):
            key=f'{phase}_{domain}';source=partial if (partial/f'{key}_jobs.json').exists() else prior
            (out/f'{key}_jobs.json').symlink_to((source/f'{key}_jobs.json').resolve())
            if key=='test_2d':continue
            source=partial/key if (partial/key).exists() else prior/key
            (out/key).symlink_to(source.resolve(),target_is_directory=True)
    combined=out/'test_2d';combined.mkdir()
    for p in dirs:(combined/p.name).symlink_to(p.resolve(),target_is_directory=True)
    (combined/'outcomes.jsonl').write_bytes((partial/'test_2d/outcomes.jsonl').read_bytes())
    M.write(combined/'ACCOUNTING.json',adjusted);M.write(out/'PHASE_BOUNDARY_RECOVERY.json',proof)
    accounts=[M.read(out/f'{p}_{d}/ACCOUNTING.json') for p in ('val','test') for d in ('2d','3d')]
    M.write(out/'COMPLETE.json',dict(selected_eta=M.read(out/'SELECTION_FREEZE.json')['selected_eta'],workers=3,
        phase_accounting=accounts,total_cpu_s=old['total_cpu_s']+fresh['cpu_s']+extra,
        total_wall_s=old['total_wall_s']+elapsed,global_adapter_calls=sum(a['adapter_calls'] for a in accounts),
        cpu_accounting_kind='PRESERVED_PRIOR_BOUNDS_PLUS_AFFINITY_WIDE_RECOVERY_BOUND',metadata_recovered=True,
        scope='No new physics; interrupted release preserved; published 2D proof and untouched 3D prior reconciled'))
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('partial',type=Path);p.add_argument('launch',type=Path);p.add_argument('out',type=Path);p.add_argument('--execute',action='store_true')
    a=p.parse_args();print(json.dumps(recover(a.partial,a.launch,a.out,a.execute),indent=2))
