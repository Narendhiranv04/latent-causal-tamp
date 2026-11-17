"""Regenerate standalone DISCO metrics from frozen jobs and actual outcome rows."""
import argparse, collections, csv, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import data as D, evaluate as EV, journal as J
import numpy as np


def read(p):return json.loads(p.read_text())


def write_csv(path,rows,empty_columns=('status',)):
    keys=list(dict.fromkeys(key for row in rows for key in row)) or list(empty_columns)
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def paired_evidence(a,b,roots,seeds,bootstrap=10000):
    result=EV.paired_frozen_root_metrics(a,b,roots,seeds=seeds,bootstrap=bootstrap)
    decided=any(r.get('verified') in (0,1) or r.get('status')=='ABSTAIN' for r in a+b)
    if not decided:
        result.update(status='UNRESOLVED' if a or b else 'NOT_RUN',delta=None,ci95=None)
    else:
        result['status']='PARTIAL' if result['unknown_pair_trials'] else 'MEASURED'
    return result


def root_stop_diagnostics(jobs,observed):
    """Raw root STOP Q versus separate original-target physical probes.

    No calibration fitting, no labels imputed from legacy K, no counterfactual
    continuation labels. Keep one seed-0 prediction per arm/root at raw eta=0 on
    VAL and the frozen selected eta on TEST. Forced STOP scores are not Q outputs.
    """
    lookup={r['job_id']:r for r in observed};labels={};examples=[]
    for job in jobs:
        row=lookup.get(job['id'],{})
        if job.get('diagnostic_only') and row.get('verified') in (0,1):
            labels[(job['split'],job['domain'],job['root_id'])]=int(row['verified'])
    for job in jobs:
        if job.get('diagnostic_only') or job['seed']!=0 or not job.get('use_value'):continue
        if job['split']=='val' and job['rule']['abstain_eta']!=0.:continue
        key=(job['split'],job['domain'],job['root_id'])
        if key not in labels:continue
        row=lookup.get(job['id'],{});trace=job.get('prediction',{}).get('selection_trace')
        if trace is None:
            path=Path(row.get('execution_evidence',{}).get('directory',''))/'selection_trace.json'
            trace=read(path) if path.is_file() else []
        if not trace:continue
        decision=trace[0]['decision']
        if not decision.get('n_candidates') or 'best_reloc_score' not in decision:continue
        if not np.isfinite(decision['stop_score']) or not 0<=decision['stop_score']<=1:raise ValueError('Invalid raw STOP probability')
        examples.append(dict(phase=job['split'],domain=job['domain'],arm=job['arm'],root_id=job['root_id'],
            family_id=job['family_id'],q_stop=float(decision['stop_score']),label=labels[key],selected_stop=decision['selected']=='STOP'))
    groups={}
    for row in examples:groups.setdefault((row['phase'],row['domain'],row['arm']),[]).append(row)
    summaries={}
    for key,rows in groups.items():
        q=np.clip([r['q_stop'] for r in rows],1e-7,1-1e-7);y=np.array([r['label'] for r in rows]);selected=np.array([r['selected_stop'] for r in rows])
        bins=[]
        for lo,hi in zip(np.linspace(0,1,6)[:-1],np.linspace(0,1,6)[1:]):
            mask=(q>=lo)&(q<hi if hi<1 else q<=hi)
            bins.append(dict(low=lo,high=hi,n=int(mask.sum()),mean_q=float(q[mask].mean()) if mask.any() else None,positive_fraction=float(y[mask].mean()) if mask.any() else None))
        summaries['|'.join(key)]=dict(n=len(rows),n_positive=int(y.sum()),brier=float(np.mean((q-y)**2)),
            nll=float(np.mean(-y*np.log(q)-(1-y)*np.log1p(-q))),
            stop_precision=float(y[selected].mean()) if selected.any() else None,
            stop_recall=float(selected[y==1].mean()) if (y==1).any() else None,bins=bins)
    return dict(examples=examples,summaries=summaries,interpretation='Independent root STOP probes only; descriptive small-sample raw-Q diagnostics, no fitted calibration and no continuation-value truth claim')


def analyze(release,out):
    out.mkdir(parents=True,exist_ok=True);groups={};row_sources={};jobs_all=[];observed_all=[];predictions=[];verifications=[];metrics={};flat=[];costs=[];censoring=[]
    for phase in ('val','test'):
        for dom in ('2d','3d'):
            path=release/f'{phase}_{dom}_jobs.json'
            if not path.exists():continue
            jobs=read(path)['jobs'];expected={j['id']:j for j in jobs};jobs_all.extend(jobs)
            result=release/f'{phase}_{dom}/outcomes.jsonl';rows=[json.loads(s) for s in result.read_text().splitlines()] if result.exists() else []
            lookup={}
            for row in rows:
                if row['job_id'] not in expected or row['job_id'] in lookup:raise ValueError('Unexpected/duplicate physical outcome')
                job=expected[row['job_id']]
                if row['root_id']!=job['root_id'] or row['seed']!=job['seed']:raise ValueError('Outcome/job identity mismatch')
                lookup[row['job_id']]=row;observed_all.append(row)
            account=release/f'{phase}_{dom}/ACCOUNTING.json'
            if account.exists():
                row_sources[str(account)]=D.sha256_file(account)
                costs.append(dict(phase=phase,domain=dom,**read(account)))
            for index,job in enumerate(jobs):
                eta=job['rule']['abstain_eta'];key=(phase,dom,job['protocol'],job['arm'],eta)
                groups.setdefault(key,dict(jobs=[],rows=[]));groups[key]['jobs'].append(job)
                row=lookup.get(job['id'])
                if row is None or row.get('verified') is None:
                    censoring.append(dict(phase=phase,domain=dom,arm=job['arm'],protocol=job['protocol'],root_id=job['root_id'],seed=job['seed'],job_id=job['id'],
                        status=row.get('status') if row else 'NOT_RUN',failure_kind=row.get('failure_kind') if row else None,
                        interpretation='No certified physical negative inferred'))
                if row:
                    directory=release/f'{phase}_{dom}'/f'{index:04d}_{job["id"]}'
                    trace=directory/'selection_trace.json';journal=directory/'queries.jsonl'
                    details=dict(directory=str(directory),selection_trace_sha256=D.sha256_file(trace) if trace.exists() else None,
                        journal_sha256=D.sha256_file(journal) if journal.exists() else None)
                    if journal.exists():
                        events=[json.loads(line) for line in journal.read_text().splitlines()]
                        details.update(attempted_relocations=sum(e['event']=='started' and e['kind']=='transition' for e in events),
                            executed_relocations=sum(e['event']=='finished' and e['kind']=='transition' and e['status']=='EXECUTED' for e in events))
                        row_sources[str(journal)]=D.sha256_file(journal)
                    if trace.exists():row_sources[str(trace)]=D.sha256_file(trace)
                    row['execution_evidence']=details
                if row:groups[key]['rows'].append(row)
                if phase=='test':
                    pred=job.get('prediction') or {k:row.get(k) if row else None for k in ('seq','status','latency_ms','selection_physical_counters')}
                    predictions.append(dict(job_id=job['id'],root_id=job['root_id'],domain=dom,arm=job['arm'],protocol=job['protocol'],seed=job['seed'],schema=job['schema'],prediction=pred,
                        policy_sha256=job['policy_sha256'],value_sha256=job.get('value_sha256'),family_id=job['family_id'],diagnostic_only=job.get('diagnostic_only',False)))
                    value=row if row is not None else dict(job_id=job['id'],root_id=job['root_id'],domain=dom,arm=job['arm'],protocol=job['protocol'],seed=job['seed'],status='NOT_RUN',verified=None,x=None,y=None)
                    verifications.append(value)
            row_sources[str(path)]=D.sha256_file(path)
            if result.exists():row_sources[str(result)]=D.sha256_file(result)
    for key,g in groups.items():
        phase,dom,protocol,arm,eta=key;roots={j['root_id']:dict(root_id=j['root_id'],family_id=j['family_id'],K_legacy=j['K_legacy']) for j in g['jobs']};seeds=sorted({j['seed'] for j in g['jobs']})
        if {(j['root_id'],j['seed']) for j in g['jobs']}!={(r,s) for r in roots for s in seeds}:raise ValueError('Unequal frozen root/seed coverage')
        m=EV.root_level_metrics(g['rows'],list(roots.values()),seeds=seeds);label='|'.join(map(str,key));metrics[label]=m
        byroot={j['root_id']:j['K_legacy'] for j in g['jobs']};rows=g['rows']
        k0=[r for r in rows if str(byroot[r['root_id']])=='0'];none=[r for r in rows if str(byroot[r['root_id']])=='NONE']
        latency=[r.get('latency_ms') for r in rows if r.get('latency_ms') is not None]
        travel=[r['robot_travel_reference']['reference_joint_path_rad'] for r in rows if r.get('verified')==1 and r.get('robot_travel_reference') and r['robot_travel_reference']['reference_joint_path_rad'] is not None]
        m['deployment_diagnostics']=dict(n_expected_K0=sum(str(r['K_legacy'])=='0' for r in roots.values())*len(seeds),
            n_predicted_NOOP_K0=sum(r['status']=='NOOP' for r in k0),n_verified_NOOP_K0=sum(r['status']=='NOOP' and r.get('verified')==1 for r in k0),
            n_unnecessary_relocation_K0=sum(r['status']=='REPAIR' for r in k0),
            n_expected_NONE=sum(str(r['K_legacy'])=='NONE' for r in roots.values())*len(seeds),n_explicit_abstention_NONE=sum(r['status']=='ABSTAIN' for r in none),
            n_novel_verified_repairs_NONE=sum(r.get('verified')==1 and r.get('status')=='REPAIR' for r in none),
            n_verified_original_target_NONE=sum(r.get('verified')==1 and r.get('status')=='NOOP' for r in none),
            predicted_action_counts=dict(collections.Counter(str(len(r['seq'])) if r.get('seq') is not None else r.get('status','UNKNOWN') for r in rows)),
            actual_executed_relocation_counts=dict(collections.Counter(str(r['execution_evidence']['executed_relocations']) for r in rows if 'executed_relocations' in r.get('execution_evidence',{}))),
            execution_failure_at_target_feasible_endpoint=sum(r.get('x')==0 and r.get('y')==1 for r in rows),
            failure_phases=dict(collections.Counter(r.get('failed_phase') or ('verified' if r.get('verified')==1 else r['status']) for r in rows)),
            failure_kinds=dict(collections.Counter(r.get('failure_kind') or 'NONE' for r in rows)),
            latency_ms=dict(n=len(latency),median=float(np.median(latency)) if latency else None,p90=float(np.percentile(latency,90)) if latency else None,p95=float(np.percentile(latency,95)) if latency else None),
            reference_corrective_joint_path_on_success=dict(n=len(travel),mean_rad=float(np.mean(travel)) if travel else None,
                definition='Accepted corrective joint waypoint paths plus certified connector, target Y excluded; actual servo arc not recorded'),
            actual_motion_arc_status='NOT_RECORDED',verification_reuse_predictions=sum(bool(r.get('physical_verification_reuse_from')) for r in rows))
        for stratum,item in [('overall',m['overall']),('tasks_K1_K2_K3',m['tasks_K1_K2_K3'])]+list(m['by_K'].items()):
            flat.append(dict(phase=phase,domain=dom,protocol=protocol,arm=arm,eta=eta,stratum=stratum,model_seeds=','.join(map(str,seeds)),
                status=item['status'],n_roots=item['n_roots'],n_families=item.get('n_families'),n_expected_predictions=item.get('n_expected_predictions'),
                n_success=item.get('n_verified_success'),success_rate=item.get('success_rate'),ci95_low=item['ci95'][0] if item.get('ci95') else None,
                ci95_high=item['ci95'][1] if item.get('ci95') else None,n_unknown=item.get('n_unresolved_or_unexecuted'),n_not_run=item.get('n_not_run')))
    paired={}
    for phase in ('val','test'):
        for dom in ('2d','3d'):
            sub={k:g for k,g in groups.items() if k[:2]==(phase,dom)}
            for a,b in [('O0_P2Q2','O0_P2'),('O0_P2Q2','O0_P2_success_onlyQ2'),('O0_P1Q1','O0_P1_success_onlyQ1'),
                        ('O0_P2Q2','O0_P2_clean_onlyQ2'),('O1_closed_P2Q2','O0_closed_P2Q2'),('O0_P2Q2','O0_P1Q1'),('O0_P2Q2','O0_P0')]:
                for ka,ga in sub.items():
                    if ka[3]!=a:continue
                    candidates=[(kb,gb) for kb,gb in sub.items() if kb[3]==b and kb[4]==ka[4]]
                    if not candidates:continue
                    kb,gb=candidates[0];seeds=sorted({j['seed'] for j in ga['jobs']}&{j['seed'] for j in gb['jobs']});ra={j['root_id']:j for j in ga['jobs']};rb={j['root_id']:j for j in gb['jobs']}
                    roots=[dict(root_id=r,family_id=ra[r]['family_id'],K_legacy=ra[r]['K_legacy']) for r in sorted(ra.keys()&rb.keys()) if str(ra[r]['K_legacy']) in ('1','2','3')]
                    aa=[r for r in ga['rows'] if r['root_id'] in {x['root_id'] for x in roots} and r['seed'] in seeds];bb=[r for r in gb['rows'] if r['root_id'] in {x['root_id'] for x in roots} and r['seed'] in seeds]
                    paired[f'{phase}|{dom}|{a}_minus_{b}|eta{ka[4]}']=paired_evidence(aa,bb,roots,seeds=seeds)
    J.atomic_json(out/'FINAL_METRICS.json',dict(metrics=metrics,paired=paired,source_hashes=row_sources,interpretation='Frozen-root intention-to-evaluate; not-run and unresolved are not physical negative labels'))
    J.atomic_json(out/'ROOT_STOP_DIAGNOSTICS.json',root_stop_diagnostics(jobs_all,observed_all))
    write_csv(out/'RESOURCE_ACCOUNTING.csv',costs,('phase','domain','cpu_s','active_wall_s','adapter_calls'))
    write_csv(out/'CENSORING_LEDGER.csv',censoring,('phase','domain','arm','protocol','root_id','seed','job_id','status','failure_kind','interpretation'))
    write_csv(out/'ABLATIONS.csv',[dict(comparison=name,**{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in item.items()}) for name,item in paired.items()],('comparison','delta','ci95'))
    if flat:
        with (out/'FINAL_METRICS.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    for name,rows in [('final_predictions.jsonl',predictions),('final_verifications.jsonl',verifications)]:J.atomic_bytes(out/name,''.join(json.dumps(r)+'\n' for r in rows).encode())
    J.atomic_json(out/'final_config.json',read(release/'APPROVED_ENVELOPE.json'))
    if (release/'SELECTION_FREEZE.json').exists():J.atomic_json(out/'SELECTION_FREEZE.json',read(release/'SELECTION_FREEZE.json'))
    J.atomic_json(out/'final_root_manifest.json',{phase:{dom:list({j['root_id']:dict(root_id=j['root_id'],family_id=j['family_id'],K_legacy=j['K_legacy'],root_sha256=j['root_sha256'],input_sha256=j['input_sha256']) for j in jobs_all if j['split']==phase and j['domain']==dom}.values()) for dom in ('2d','3d')} for phase in ('val','test')})
    prep=Path(read(release/'APPROVED_ENVELOPE.json')['preparation']);J.atomic_json(out/'final_checkpoints.json',read(prep/'checkpoint_manifest.json'))
    return dict(metric_groups=len(metrics),paired_comparisons=len(paired),test_predictions=len(predictions),observed_test_outcomes=sum(r['status']!='NOT_RUN' for r in verifications))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('release',type=Path);p.add_argument('out',type=Path);a=p.parse_args();print(json.dumps(analyze(a.release,a.out),indent=2))
