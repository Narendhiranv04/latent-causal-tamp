"""Continue the frozen release after an explicitly requested host change.

No model/benchmark/decision changes. Finished and interrupted gvlab trials are
retained without retry; all their query intents and reaped costs are charged.
Only file locations and the recorded host guard are amended.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import collect as C, data as D, journal as J, physical_eval as PE


def read(p):return json.loads(Path(p).read_text())
def sha(p):return D.sha256_file(p)


def relocated(value,rootfs):
    if isinstance(value,str) and value.startswith(('/scratch/nav/','/home/nav/')):
        return str(rootfs/value.lstrip('/'))
    if isinstance(value,list):return [relocated(x,rootfs) for x in value]
    if isinstance(value,dict):return {relocated(k,rootfs):relocated(v,rootfs) for k,v in value.items()}
    return value


def load_selection():
    spec=importlib.util.spec_from_file_location('frozen_selection',HERE/'release_evaluation.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.select_eta


def previous_cost(prior,launch):
    directory=prior/'val_2d';accounts=[];calls=0
    for trial in directory.iterdir():
        if not trial.is_dir():continue
        if (trial/'WATCHDOG_ACCOUNTING.json').exists():accounts.append(read(trial/'WATCHDOG_ACCOUNTING.json'))
        calls+=sum(e['event']=='started' for e in J.read_events(trial))
    start=datetime.datetime.fromisoformat(read(launch)['utc']).timestamp()
    end=max(a['wall_time_end'] for a in accounts)
    elapsed=end-start;child=sum(a['reaped_child_cpu_s'] for a in accounts)
    # The detached controller's final CPU is not recoverable after its exit.
    # Charge its entire elapsed interval as CPU, on top of exact reaped worker
    # CPU, rather than invent a small controller estimate. One-thread execution
    # was enforced by the environment and recorded process identities.
    return dict(cpu_s=child+elapsed,worker_cpu_s=child,controller_cpu_s=elapsed,
        worker_wall_s=sum(a['wall_s'] for a in accounts),active_wall_s=elapsed,
        adapter_calls=calls,cpu_accounting_kind='CONSERVATIVE_CONTROLLER_ELAPSED_UPPER_BOUND',
        exact_final_controller_cpu_s=None,attempts=len(accounts),
        scope='All original gvlab attempts, including user-cancelled final trial; detached controller CPU charged at elapsed-wall upper bound')


def run(rootfs,out):
    cpu_start=time.process_time();wall_start=time.monotonic()
    host=C.execution_host('girish-laptop');C.require_headroom()
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise PermissionError('CPU-only continuation')
    audit=read(rootfs.parent/'MIGRATION_HASH_AUDIT.json')
    if audit['status']!='PASS':raise ValueError('Migration byte audit failed')
    original=rootfs/'scratch/nav/disco_grid/stage2'
    prior=original/'releases/V15_F25_v1_20261117'
    prep=original/'campaigns/E16_v1_20261117/evaluation_preparation_v3'
    approved=read(prior/'APPROVED_ENVELOPE.json')
    if approved['status']!='APPROVED' or approved['global_adapter_call_ceiling']!=5523:raise PermissionError('Original approval missing')
    old_sources=read(prep/'manifest.json')['source_sha256']
    engine=HERE.parents[1]
    for name,digest in old_sources.items():
        if name not in ('collect.py','physical_eval.py') and sha(engine/name)!=digest:
            raise ValueError('Non-host scientific source changed: '+name)
    for model in read(prep/'checkpoint_manifest.json'):
        for kind in ('policy','value'):
            if model.get(kind) and sha(relocated(model[kind],rootfs))!=model[kind+'_sha256']:
                raise ValueError('Frozen model changed')
    for name,item in approved['candidate_sets'].items():
        if sha(prep/name)!=item['sha256']:raise ValueError('Original frozen matrix changed')
    prior_charge=previous_cost(prior,original/'evidence/V15_F25_v1_20261117_LAUNCH.json')
    out.mkdir(parents=True,exist_ok=False)
    execution_prep=out/'execution_preparation';execution_prep.mkdir()
    registry=relocated(read(prep/'checkpoint_manifest.json'),rootfs)
    J.atomic_json(execution_prep/'checkpoint_manifest.json',registry)
    candidate_sets={}
    for name,item in approved['candidate_sets'].items():
        matrix=read(prep/name);mapped=relocated(matrix,rootfs)
        if [j['id'] for j in matrix['jobs']]!=[j['id'] for j in mapped['jobs']]:raise ValueError('Relocation changed job IDs')
        J.atomic_json(execution_prep/name,mapped)
        candidate_sets[name]=dict(item,sha256=sha(execution_prep/name),original_sha256=item['sha256'])
    current_sources={name:sha(engine/name) for name in old_sources}
    manifest=dict(read(prep/'manifest.json'),source_commit=os.environ['DISCO_SOURCE_COMMIT'],
        source_sha256=current_sources,sets=candidate_sets,original_preparation_sha256=approved['preparation_sha256'])
    J.atomic_json(execution_prep/'manifest.json',manifest)
    envelope=dict(approved,host=host['alias'],engine=str(engine),
        preparation=str(execution_prep),preparation_sha256=sha(execution_prep/'manifest.json'),
        checkpoint_manifest_sha256=sha(execution_prep/'checkpoint_manifest.json'),
        original_checkpoint_manifest_sha256=approved['checkpoint_manifest_sha256'],candidate_sets=candidate_sets,
        host_amendment=read(Path(os.environ['DISCO_EXECUTION_AUTHORIZATION'])),
        host_amendment_sha256=sha(os.environ['DISCO_EXECUTION_AUTHORIZATION']),
        original_preparation=str(prep),prior_attempt_charge=prior_charge,
        scientific_source_sha256=current_sources,
        original_frozen_preparation_sha256=approved['preparation_sha256'])
    # Keep original engine/model hashes alongside relocated execution paths.
    J.atomic_json(out/'APPROVED_ENVELOPE.json',envelope)
    J.atomic_json(out/'HOST_MIGRATION.json',dict(byte_audit=audit,prior_charge=prior_charge,
        original_release=str(prior),source_commit=os.environ['DISCO_SOURCE_COMMIT'],
        original_source_sha256=old_sources,new_source_sha256=envelope['scientific_source_sha256'],
        interpretation='Only host guard and file bindings amended. Prior failures, timeouts and cancellation are retained without retry. TEST outcomes never select the model.'))
    J.atomic_json(out/'ORIGINAL_TRANSFER_INDEX.json',read(original/'evidence/GIRISH_MIGRATION_TRANSFER_v1.json'))
    phase_costs=[]
    setup_cpu=time.process_time()-cpu_start;setup_wall=time.monotonic()-wall_start
    if max(setup_cpu,setup_wall)>25:raise RuntimeError('Continuation setup exceeded fixed 30-second bookkeeping reserve')
    def execute(phase,dom,jobs):
        original_jobs=jobs;jobs=relocated(jobs,rootfs)
        assert [j['id'] for j in jobs]==[j['id'] for j in original_jobs]
        J.atomic_json(out/f'{phase}_{dom}_jobs.json',dict(jobs=jobs))
        combined=out/f'{phase}_{dom}';combined.mkdir()
        old_rows=[];old_attempted=set();old=prior_charge if (phase,dom)==('val','2d') else dict(cpu_s=0.,worker_cpu_s=0.,controller_cpu_s=0.,worker_wall_s=0.,active_wall_s=0.,adapter_calls=0)
        if old['adapter_calls']:
            old_rows=[relocated(json.loads(s),rootfs) for s in (prior/'val_2d/outcomes.jsonl').read_text().splitlines()]
            lookup={r['job_id']:r for r in old_rows}
            for i,job in enumerate(jobs):
                source=prior/'val_2d'/f'{i:04d}_{job["id"]}'
                if not source.exists():continue
                old_attempted.add(job['id']);(combined/source.name).symlink_to(source,target_is_directory=True)
                if job['id'] not in lookup:
                    # An administrative host cancellation is not a new physical
                    # failure or a license to retry this benchmark trial.
                    row={k:job[k] for k in ('root_id','domain','seed','arm','protocol','K_legacy','family_id')}
                    row.update(job_id=job['id'],status='UNRESOLVED',verified=None,x=None,y=None,
                        failure_kind='USER_HOST_CHANGE_CANCELLED',evidence=str(source),execution_host='gvlab')
                    old_rows.append(row)
            for row in old_rows:row['execution_host']='gvlab'
        remaining=[j for j in jobs if j['id'] not in old_attempted]
        charged_before=sum(x['adapter_calls'] for x in phase_costs)+old['adapter_calls']
        budget=approved['ceilings'][dom][phase]
        cpu_left=budget-old['cpu_s']-30
        wall_left=budget-old['active_wall_s']-30
        if min(cpu_left,wall_left)<=0:raise RuntimeError('Prior attempts exhausted approved phase ceiling')
        path=out/f'{phase}_{dom}_remaining_jobs.json';J.atomic_json(path,dict(jobs=remaining))
        sub=dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',authorization_text=envelope['host_amendment']['authorization_text'],
            jobs_sha256=sha(path),host=host['alias'],workers=1,gpu=False,split=phase,
            cpu_s=cpu_left,active_wall_s=wall_left,adapter_calls=5523-charged_before,disk_gib=9.)
        ep=out/f'{phase}_{dom}_envelope.json';J.atomic_json(ep,sub)
        fragment=out/f'{phase}_{dom}_girish_fragment'
        try:
            PE.run(path,ep,fragment)
        finally:
            rows=[json.loads(s) for s in (fragment/'outcomes.jsonl').read_text().splitlines()] if (fragment/'outcomes.jsonl').exists() else []
            for row in rows:row['execution_host']='girish-laptop'
            positions={j['id']:i for i,j in enumerate(jobs)}
            for i,job in enumerate(remaining):
                source=fragment/f'{i:04d}_{job["id"]}'
                if source.exists():(combined/f'{positions[job["id"]]:04d}_{job["id"]}').symlink_to(source,target_is_directory=True)
            all_rows=sorted(old_rows+rows,key=lambda r:positions[r['job_id']])
            J.atomic_bytes(combined/'outcomes.jsonl',''.join(json.dumps(r)+'\n' for r in all_rows).encode())
            new=read(fragment/'ACCOUNTING.json')
            account={k:old.get(k,0)+new[k] for k in ('cpu_s','worker_cpu_s','controller_cpu_s','worker_wall_s','active_wall_s','adapter_calls')}
            account.update(n_frozen_jobs=len(jobs),n_attempted=len(all_rows),n_not_run=len(jobs)-len(all_rows),
                cpu_accounting_kind=old.get('cpu_accounting_kind','MEASURED'),fragments=[dict(host='gvlab',accounting=old),dict(host='girish-laptop',accounting=new)])
            J.atomic_json(combined/'ACCOUNTING.json',account);phase_costs.append(account)
        return all_rows
    val_jobs=[]
    for eta in (0.,.08,.15):val_jobs.extend(read(prep/f'val_eta{eta:g}.json')['jobs'])
    val_rows=[]
    for dom in ('2d','3d'):val_rows.extend(execute('val',dom,[j for j in val_jobs if j['domain']==dom]))
    selection=load_selection()(val_jobs,val_rows)
    test_jobs=[]
    for dom,eta in selection['selected_eta'].items():
        test_jobs.extend(j for j in read(prep/f'test_eta{eta:g}.json')['jobs'] if j['domain']==dom)
        if eta!=0.:test_jobs.extend(j for j in read(prep/'test_eta0.json')['jobs'] if j['domain']==dom and j.get('diagnostic_only'))
    J.atomic_json(out/'SELECTION_FREEZE.json',dict(selection,selected_test_job_ids=[j['id'] for j in test_jobs],
        candidate_sets=candidate_sets,checkpoint_manifest_sha256=envelope['checkpoint_manifest_sha256'],
        validation_evidence_sha256={d:sha(out/f'val_{d}/outcomes.jsonl') for d in ('2d','3d')},
        no_retry=True,confirmation_status='EXPLORATORY; external historical exposure not fully attested'))
    for dom in ('2d','3d'):execute('test',dom,[j for j in test_jobs if j['domain']==dom])
    # The controller and environment migration overhead are separate records;
    # phase CPU includes exact workers and the conservative cancelled-controller
    # charge. Do not disguise that upper bound as an exact grand total.
    new_phase_controller=sum(x['fragments'][1]['accounting']['controller_cpu_s'] for x in phase_costs)
    J.atomic_json(out/'COMPLETE.json',dict(selection,phase_accounting=phase_costs,
        total_cpu_s=sum(x['cpu_s'] for x in phase_costs)+time.process_time()-cpu_start-new_phase_controller,
        total_wall_s=prior_charge['active_wall_s']+time.monotonic()-wall_start,
        continuation_controller_cpu_s=time.process_time()-cpu_start,
        continuation_wall_s=time.monotonic()-wall_start,cpu_accounting_kind='CONSERVATIVE_GVLAB_CONTROLLER_UPPER_BOUND',
        scope='Same V15-F25-v1 physical envelope across both machines; all gvlab attempts retained/charged, no retries, no model selection from TEST'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rootfs',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();run(args.rootfs,args.out)
