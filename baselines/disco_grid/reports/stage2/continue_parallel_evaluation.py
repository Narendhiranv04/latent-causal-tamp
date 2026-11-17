"""Preserve the serial release, then run its remaining frozen jobs in three slots."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0,str(HERE))
import collect as C, data as D, journal as J, parallel_eval as POOL, physical_eval as PE
import release_evaluation as RELEASE


def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []


def audit_prior(prior,drain):
    records={};completed_controller=0.
    active_phase=drain.get('active_phase') or ('_'.join(Path(drain['trial']).parent.name.split('_')[:2]) if drain.get('trial') else None)
    for phase in ('val_2d','val_3d','test_2d','test_3d'):
        jp=prior/f'{phase}_jobs.json'
        if not jp.exists():continue
        jobs=read(jp)['jobs'];byid={j['id']:j for j in jobs}
        published={r['job_id']:r for r in rows(prior/phase/'outcomes.jsonl')};directories={}
        candidates=[prior/phase]+list(prior.glob(phase+'_*fragment'))
        for parent in candidates:
            if not parent.is_dir():continue
            for d in parent.iterdir():
                if not d.is_dir() or not (d/'job.json').exists():continue
                job=read(d/'job.json');key=job['id'];source=d.resolve()
                if key not in byid:raise ValueError('Unexpected prior job')
                if key in directories and directories[key]!=source:raise ValueError('Duplicate physical attempt identity')
                directories[key]=source
        recovered={};accounts=[];calls=0
        for key,directory in directories.items():
            job=byid[key];account=directory/'WATCHDOG_ACCOUNTING.json'
            if account.exists():accounts.append(read(account))
            calls+=sum(e['event']=='started' for e in J.read_events(directory))
            if key in published:result=published[key]
            elif (directory/'result.json').exists():result=read(directory/'result.json')
            elif (directory/'reconciled_result.json').exists():result=read(directory/'reconciled_result.json')
            else:
                result=PE.reconcile_returned_proof(job,directory)
                if result is None:
                    result={k:job[k] for k in ('root_id','domain','seed','arm','protocol','K_legacy','family_id')}
                    result.update(job_id=key,status='UNRESOLVED',verified=None,x=None,y=None,
                        failure_kind='PARALLEL_HANDOFF_NO_RETURNED_PROOF',evidence=str(directory))
            recovered[key]=dict(result,execution_host=result.get('execution_host','girish-laptop'))
        old=read(prior/phase/'ACCOUNTING.json')
        physical_cpu=sum(a['reaped_child_cpu_s'] for a in accounts)
        if phase!=active_phase:
            if old['adapter_calls']!=calls or abs(old['worker_cpu_s']-physical_cpu)>.001:
                raise ValueError('Completed phase cost ledger mismatch: '+phase)
            completed_controller+=sum(f['accounting']['controller_cpu_s'] for f in old.get('fragments',[]) if f['host']=='girish-laptop')
            cost=old
        else:
            # The detached controller was stopped at an observed CPU reading.
            # Its cleanup duration is a conservative additional one-thread CPU
            # charge. Completed earlier phases retain their existing charges.
            controller=max(0.,drain['controller_final_cpu_upper_bound_s']-completed_controller)
            fragment=prior/(phase+'_girish_fragment')
            elapsed=max(old['active_wall_s'],drain['finished_utc_epoch']-(fragment/'manifest.json').stat().st_mtime)
            cost=dict(cpu_s=physical_cpu+controller,worker_cpu_s=physical_cpu,controller_cpu_s=controller,
                worker_wall_s=sum(a['wall_s'] for a in accounts),active_wall_s=elapsed,
                adapter_calls=calls,cpu_accounting_kind='CONSERVATIVE_OBSERVED_CONTROLLER_DRAIN_BOUND',
                controller_cpu_evidence=drain,exact_final_controller_cpu_s=None)
        cost=dict(cost,n_attempted=len(recovered),n_frozen_jobs=len(jobs),n_not_run=len(jobs)-len(recovered))
        records[phase]=dict(jobs=jobs,rows=recovered,directories={k:str(v) for k,v in directories.items()},cost=cost)
    return records


def run(prior,drain_path,out):
    cpu_start=time.process_time();wall_start=time.monotonic()
    C.require_headroom();C.execution_host('girish-laptop')
    if C.execution_workers()!=3:raise PermissionError('Three-worker amendment required')
    drain=read(drain_path)
    if not drain['physical_children_exited']:raise RuntimeError('Serial children not drained')
    old_envelope=read(prior/'APPROVED_ENVELOPE.json');prep=Path(old_envelope['preparation'])
    old=audit_prior(prior,drain);initial_calls=sum(x['cost']['adapter_calls'] for x in old.values())
    engine=HERE.parents[1];old_source=read(prep/'manifest.json')['source_sha256']
    for name,digest in old_source.items():
        if name not in ('collect.py','physical_eval.py') and D.sha256_file(engine/name)!=digest:
            raise ValueError('Frozen scientific implementation changed: '+name)
    for model in read(prep/'checkpoint_manifest.json'):
        for kind in ('policy','value'):
            if model.get(kind) and D.sha256_file(model[kind])!=model[kind+'_sha256']:raise ValueError('Frozen checkpoint changed')
    for name,item in old_envelope['candidate_sets'].items():
        if D.sha256_file(prep/name)!=item['sha256']:raise ValueError('Frozen candidate file changed')
    out.mkdir(parents=True,exist_ok=False)
    envelope=dict(old_envelope,workers=3,engine=str(engine),
        parallel_authorization=read(os.environ['DISCO_EXECUTION_AUTHORIZATION']),
        prior_release=str(prior),parallel_runner_sha256=D.sha256_file(Path(__file__)),
        pool_sha256=D.sha256_file(engine/'parallel_eval.py'),parallel_source_commit=os.environ['DISCO_SOURCE_COMMIT'])
    J.atomic_json(out/'APPROVED_ENVELOPE.json',envelope)
    J.atomic_json(out/'PARALLEL_HANDOFF.json',dict(drain=drain,prior_charge={k:v['cost'] for k,v in old.items()},
        initial_charged_calls=initial_calls,models_roots_rules_predictions_unchanged=True,
        scientific_source_sha256={name:D.sha256_file(engine/name) for name in old_source},
        scheduling='Three independent supervised trials; frozen job ordering with in-flight exact-sequence deduplication; fixed denominators, no retry'))
    for name in ('HOST_MIGRATION.json','ORIGINAL_TRANSFER_INDEX.json'):
        if (prior/name).exists():J.atomic_json(out/name,read(prior/name))
    new_costs=[];calls=initial_calls
    def execute(phase,domain,jobs):
        nonlocal calls
        key=f'{phase}_{domain}';previous=old.get(key,dict(rows={},directories={},cost={}))
        charge=previous['cost'];combined=out/key;combined.mkdir()
        J.atomic_json(out/f'{key}_jobs.json',dict(jobs=jobs))
        remaining=[j for j in jobs if j['id'] not in previous['rows']]
        path=out/f'{key}_remaining_jobs.json';J.atomic_json(path,dict(jobs=remaining))
        cap=old_envelope['ceilings'][domain][phase]
        cpu=max(0.,cap-charge.get('cpu_s',0)-30);wall=max(0.,cap-charge.get('active_wall_s',0)-30)
        sub=dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',authorization_text=envelope['parallel_authorization']['authorization_text'],
            host='girish-laptop',workers=3,gpu=False,split=phase,jobs_sha256=D.sha256_file(path),
            cpu_s=cpu,active_wall_s=wall,adapter_calls=5523-calls,disk_gib=8.)
        ep=out/f'{key}_envelope.json';J.atomic_json(ep,sub)
        fragment=out/f'{key}_pool_fragment'
        POOL.run(path,ep,fragment)
        fresh=rows(fragment/'outcomes.jsonl');account=read(fragment/'ACCOUNTING.json');new_costs.append(account);calls+=account['adapter_calls']
        positions={j['id']:i for i,j in enumerate(jobs)}
        for job_id,directory in previous['directories'].items():
            (combined/f'{positions[job_id]:04d}_{job_id}').symlink_to(directory,target_is_directory=True)
        for i,j in enumerate(remaining):
            source=fragment/f'{i:04d}_{j["id"]}'
            if source.exists():(combined/f'{positions[j["id"]]:04d}_{j["id"]}').symlink_to(source,target_is_directory=True)
        all_rows=list(previous['rows'].values())+fresh
        all_rows.sort(key=lambda r:positions[r['job_id']])
        J.atomic_bytes(combined/'outcomes.jsonl',''.join(json.dumps(r)+'\n' for r in all_rows).encode())
        total={k:charge.get(k,0)+account[k] for k in ('cpu_s','worker_cpu_s','controller_cpu_s','worker_wall_s','active_wall_s','adapter_calls')}
        total.update(n_attempted=len(all_rows),n_frozen_jobs=len(jobs),n_not_run=len(jobs)-len(all_rows),
            workers=3,prior_charge=charge,new_pool_charge=account,cpu_accounting_kind=charge.get('cpu_accounting_kind','MEASURED_SUPERVISORS_AND_CHILDREN'))
        if max(total['cpu_s'],total['active_wall_s'])>cap:raise RuntimeError('Approved phase ceiling exceeded')
        J.atomic_json(combined/'ACCOUNTING.json',total)
        return all_rows
    val_jobs=[]
    for eta in (0.,.08,.15):val_jobs.extend(read(prep/f'val_eta{eta:g}.json')['jobs'])
    observed=[]
    for domain in ('2d','3d'):observed.extend(execute('val',domain,[j for j in val_jobs if j['domain']==domain]))
    selection=RELEASE.select_eta(val_jobs,observed);test_jobs=[]
    for domain,eta in selection['selected_eta'].items():
        test_jobs.extend(j for j in read(prep/f'test_eta{eta:g}.json')['jobs'] if j['domain']==domain)
        if eta!=0.:test_jobs.extend(j for j in read(prep/'test_eta0.json')['jobs'] if j['domain']==domain and j.get('diagnostic_only'))
    J.atomic_json(out/'SELECTION_FREEZE.json',dict(selection,selected_test_job_ids=[j['id'] for j in test_jobs],
        checkpoint_manifest_sha256=old_envelope['checkpoint_manifest_sha256'],candidate_sets=old_envelope['candidate_sets'],
        validation_evidence_sha256={d:D.sha256_file(out/f'val_{d}/outcomes.jsonl') for d in ('2d','3d')},
        no_retry=True,confirmation_status='EXPLORATORY; external exposure not fully attested'))
    for domain in ('2d','3d'):execute('test',domain,[j for j in test_jobs if j['domain']==domain])
    new_phase_parent=sum(x['controller_cpu_s'] for x in new_costs)
    # new_phase_parent includes supervisor CPU, which is separate from this
    # coordinator. Its exact contribution stays in the phase ledgers.
    own_phase_cpu=sum(max(0.,x['controller_cpu_s']-sum(read(p)['supervisor_cpu_s'] for p in (out/f'{phase}_{domain}_pool_fragment').glob('*/SUPERVISOR_COMPLETE.json'))) for x,(phase,domain) in zip(new_costs,[(p,d) for p in ('val','test') for d in ('2d','3d')]))
    J.atomic_json(out/'COMPLETE.json',dict(selection,workers=3,
        phase_accounting=[read(out/f'{p}_{d}/ACCOUNTING.json') for p in ('val','test') for d in ('2d','3d')],
        total_cpu_s=sum(v['cost']['cpu_s'] for v in old.values())+sum(x['cpu_s'] for x in new_costs)+time.process_time()-cpu_start-own_phase_cpu,
        total_wall_s=sum(v['cost']['active_wall_s'] for v in old.values())+time.monotonic()-wall_start,
        global_adapter_calls=calls,cpu_accounting_kind='PRIOR_CONTROLLER_BOUNDS_PLUS_MEASURED_PARALLEL_COSTS',
        scope='Same approved 5523-call and per-domain CPU/wall ceilings; three workers explicitly authorized; no model or benchmark change'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('prior',type=Path);parser.add_argument('drain',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();run(args.prior,args.drain,args.out)
