"""One explicitly authorized VAL→selection-freeze→TEST DISCO release.

All candidate checkpoints/root lists/predictions exist before permission. The
approved matrix contains all three preregistered eta branches; only VAL chooses
one per domain. TEST outcomes are never opened by the selection function.
"""
import argparse, hashlib, importlib, json, os, sys, time
from pathlib import Path
CAPS={'2d':{'val':3600,'test':10800},'3d':{'val':7200,'test':21600}}
ETAS=(0.,.08,.15)


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def request(preparation,engine,out):
    manifest=read(preparation/'manifest.json')
    for name,item in manifest['sets'].items():
        if sha(preparation/name)!=item['sha256']:raise ValueError('Candidate matrix changed')
    env=dict(id='V15-F25-v1',status='REQUESTED_NOT_AUTHORIZED',scope='DISCO_RELEASE_EVALUATION',host='gvlab',workers=1,cpu_threads=1,gpu=False,
        authorization_text=None,approved_phases=['val','test'],preparation=str(preparation),engine=str(engine),preparation_sha256=sha(preparation/'manifest.json'),
        checkpoint_manifest_sha256=sha(preparation/'checkpoint_manifest.json'),runner_sha256=sha(__file__),candidate_sets=manifest['sets'],
        ceilings=CAPS,units='seconds per domain and phase, CPU and active wall; all attempts and parent overhead charged',
        disk_gib=10,ram_gib=4,query_wall_s={'2d':60,'3d':120},trial_wall_s={'2d':300,'3d':600},
        global_adapter_call_ceiling=5523,
        roots_per_domain={'val':15,'test':25},final_model_seeds=[0,1,2],validation_model_seeds=[0],
        selection='VAL O0_P2Q2 task success, then verified K0 NOOP, then explicit NONE abstention; residual ties smaller eta. Apply common selected eta to all Q arms and O0/O1 closed-loop.',
        interpretation='Exploratory held-out cohorts; no untouched confirmation attested; fixed-root denominators retain every unresolved/unexecuted trial',
        exclusions='No competing method, no new training, no additional machine or GPU. TEST starts only after selection freeze and required VAL coverage.',
        cancellation='Identity-scoped child/session watchdog and parent-death guard; per-query durable evidence; no automatic ambiguous restart')
    Path(out).write_text(json.dumps(env,indent=2)+'\n');return env


def validate(envelope):
    if envelope.get('status')!='APPROVED' or envelope.get('scope')!='DISCO_RELEASE_EVALUATION' or not envelope.get('authorization_text'):raise PermissionError('Explicit V15-F25 approval required; TRAIN approval is insufficient')
    if envelope.get('host')!='gvlab' or envelope.get('workers')!=1 or envelope.get('gpu') is not False or envelope.get('cpu_threads')!=1:raise PermissionError('Unauthorized host/resources')
    if not 0<envelope.get('global_adapter_call_ceiling',0)<=5523:raise PermissionError('Unauthorized physical-call ceiling')
    if not set(envelope['approved_phases'])<=set(('val','test')):raise PermissionError('Unknown phase')
    for dom in CAPS:
        for phase,maximum in CAPS[dom].items():
            if not 0<envelope['ceilings'][dom][phase]<=maximum:raise PermissionError('Altered approved ceiling')
    prep=Path(envelope['preparation']);engine=Path(envelope['engine'])
    if sha(__file__)!=envelope['runner_sha256'] or sha(prep/'manifest.json')!=envelope['preparation_sha256'] or sha(prep/'checkpoint_manifest.json')!=envelope['checkpoint_manifest_sha256']:raise ValueError('Frozen release inputs changed')
    for name,item in envelope['candidate_sets'].items():
        if sha(prep/name)!=item['sha256']:raise ValueError('Frozen candidates changed')
    for model in read(prep/'checkpoint_manifest.json'):
        for kind in ('policy','value'):
            if model.get(kind) and sha(model[kind])!=model[kind+'_sha256']:raise ValueError('Checkpoint changed since freeze')
    for name,digest in read(prep/'manifest.json')['source_sha256'].items():
        if sha(engine/name)!=digest:raise ValueError('Physical/inference engine changed since candidate freeze')
    return prep,engine


def select_eta(val_jobs,outcomes):
    if any(j['split']!='val' for j in val_jobs):raise ValueError('Selection must only read VAL jobs')
    expected={j['id']:j for j in val_jobs};lookup={}
    for row in outcomes:
        if row['job_id'] not in expected or row['job_id'] in lookup:raise ValueError('Unexpected/duplicate VAL result')
        lookup[row['job_id']]=row
    selected={};scores={}
    for dom in ('2d','3d'):
        domain_scores=[]
        for eta in ETAS:
            jobs=[j for j in val_jobs if j['domain']==dom and j['arm']=='O0_P2Q2' and j['rule']['abstain_eta']==eta]
            tasks=[j for j in jobs if str(j['K_legacy']) in ('1','2','3')];k0=[j for j in jobs if str(j['K_legacy'])=='0'];none=[j for j in jobs if str(j['K_legacy'])=='NONE']
            if not tasks or not k0 or not none:raise ValueError('Missing preregistered VAL strata')
            task=sum(lookup.get(j['id'],{}).get('verified')==1 for j in tasks)/len(tasks)
            noop=sum(lookup.get(j['id'],{}).get('verified')==1 and lookup[j['id']].get('status')=='NOOP' for j in k0)/len(k0)
            abstain=sum(lookup.get(j['id'],{}).get('status')=='ABSTAIN' for j in none)/len(none)
            def physically_decided(job):
                result=lookup.get(job['id'],{})
                return result.get('verified') in (0,1) and result.get('status')!='ABSTAIN'
            known=sum(physically_decided(j) for j in tasks)
            coverage={}
            for arm in ('O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2'):
                arm_jobs=[j for j in val_jobs if j['domain']==dom and j['arm']==arm and j['rule']['abstain_eta']==eta and str(j['K_legacy']) in ('1','2','3')]
                coverage[arm]=dict(expected=len(arm_jobs),known=sum(physically_decided(j) for j in arm_jobs))
            eligible=all(c['expected']>0 and c['known']*2>=c['expected'] for c in coverage.values())
            domain_scores.append(dict(eta=eta,eligible=eligible,protocol_coverage=coverage,task_success=task,verified_noop_K0=noop,explicit_abstention_NONE=abstain,n_task_trials=len(tasks),n_task_outcomes_known=known))
        # At least half the raw-Q task trials must have real decided outcomes.
        if not domain_scores[0]['eligible']:raise RuntimeError(f'{dom} VAL evidence gate: insufficient decided raw-Q task coverage')
        best=max([r for r in domain_scores if r['eligible']],key=lambda r:(r['task_success'],r['verified_noop_K0'],r['explicit_abstention_NONE'],-r['eta']))
        selected[dom]=best['eta'];scores[dom]=domain_scores
    return dict(selected_eta=selected,validation_scores=scores,criterion='fixed lexicographic VAL rule; unknowns retained as not verified successful, not physical negatives')


def run(envelope_path,out):
    run_cpu=time.process_time();run_wall=time.monotonic()
    envelope=read(envelope_path);prep,engine=validate(envelope)
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise PermissionError('CPU only')
    sys.path.insert(0,str(engine));PE=importlib.import_module('physical_eval');J=PE.J;C=PE.C
    C.require_headroom();out.mkdir(parents=True,exist_ok=False)
    J.atomic_json(out/'APPROVED_ENVELOPE.json',envelope)
    # All VAL candidates, only one eventual TEST branch per domain.
    val_jobs=[]
    for eta in ETAS:val_jobs.extend(read(prep/f'val_eta{eta:g}.json')['jobs'])
    if len({j['id'] for j in val_jobs})!=len(val_jobs):raise ValueError('Duplicate VAL job identity')
    outcomes=[];phase_costs=[]
    def execute(phase,dom,jobs):
        path=out/f'{phase}_{dom}_jobs.json';J.atomic_json(path,dict(jobs=jobs))
        budget=envelope['ceilings'][dom][phase]-30
        shared_cpu=time.process_time()-run_cpu-sum(x.get('controller_cpu_s',0) for x in phase_costs)
        shared_wall=time.monotonic()-run_wall-sum(x.get('active_wall_s',0) for x in phase_costs)
        if max(shared_cpu,shared_wall)>50:raise RuntimeError('RELEASE_BOOKKEEPING_RESERVE_EXHAUSTED')
        used=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        remaining_disk=envelope['disk_gib']-used/2**30
        if remaining_disk<=0:raise RuntimeError('RELEASE_DISK_LIMIT')
        sub=dict(status='APPROVED',scope='DISCO_PHYSICAL_EVALUATION',authorization_text=envelope['authorization_text'],
            jobs_sha256=sha(path),host='gvlab',workers=1,gpu=False,split=phase,cpu_s=budget,active_wall_s=budget,
            adapter_calls=min(envelope['global_adapter_call_ceiling']-sum(x['adapter_calls'] for x in phase_costs),sum(j['adapter_call_cap'] for j in jobs if not(j['protocol']=='open_loop' and j['prediction']['status']=='ABSTAIN'))),disk_gib=remaining_disk)
        ep=out/f'{phase}_{dom}_envelope.json';J.atomic_json(ep,sub)
        PE.run(path,ep,out/f'{phase}_{dom}')
        p=out/f'{phase}_{dom}/outcomes.jsonl'
        rows=[json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
        phase_costs.append(read(out/f'{phase}_{dom}/ACCOUNTING.json'))
        return rows
    if 'val' not in envelope['approved_phases']:raise PermissionError('VAL selection evidence required before TEST')
    for dom in ('2d','3d'):outcomes.extend(execute('val',dom,[j for j in val_jobs if j['domain']==dom]))
    selection=select_eta(val_jobs,outcomes)
    test_jobs=[]
    for dom,eta in selection['selected_eta'].items():
        test_jobs.extend([j for j in read(prep/f'test_eta{eta:g}.json')['jobs'] if j['domain']==dom])
        if eta!=0.:test_jobs.extend([j for j in read(prep/'test_eta0.json')['jobs'] if j['domain']==dom and j.get('diagnostic_only')])
    J.atomic_json(out/'SELECTION_FREEZE.json',dict(selection,checkpoint_manifest_sha256=envelope['checkpoint_manifest_sha256'],
        candidate_sets=envelope['candidate_sets'],selected_test_job_ids=[j['id'] for j in test_jobs],approved_envelope_sha256=sha(out/'APPROVED_ENVELOPE.json'),
        validation_evidence_sha256={str(out/f'val_{d}/outcomes.jsonl'):sha(out/f'val_{d}/outcomes.jsonl') for d in ('2d','3d')},
        source_sha256=read(prep/'manifest.json')['source_sha256'],no_retry=True,confirmation_status='EXPLORATORY; external historical exposure not fully attested'))
    if 'test' not in envelope['approved_phases']:
        J.atomic_json(out/'VAL_COMPLETE_TEST_NOT_AUTHORIZED.json',selection);return
    for dom in ('2d','3d'):execute('test',dom,[j for j in test_jobs if j['domain']==dom])
    J.atomic_json(out/'COMPLETE.json',dict(selection,phase_accounting=phase_costs,total_cpu_s=sum(x.get('worker_cpu_s',0) for x in phase_costs)+time.process_time()-run_cpu,total_wall_s=time.monotonic()-run_wall,scope='DISCO-only physical release; regenerate final metrics from frozen jobs and outcomes'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',action='store_true');p.add_argument('--preparation',type=Path);p.add_argument('--engine',type=Path);p.add_argument('--envelope',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args()
    if a.request:request(a.preparation,a.engine,a.envelope)
    else:run(a.envelope,a.out)
