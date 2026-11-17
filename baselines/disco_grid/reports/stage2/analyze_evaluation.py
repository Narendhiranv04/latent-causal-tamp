"""Regenerate standalone DISCO metrics from frozen jobs and actual outcome rows."""
import argparse, collections, csv, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import data as D, evaluate as EV, journal as J
import numpy as np


def read(p):return json.loads(p.read_text())


def analyze(release,out):
    out.mkdir(parents=True,exist_ok=True);groups={};row_sources={};jobs_all=[];observed_all=[];predictions=[];verifications=[];metrics={};flat=[]
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
            for job in jobs:
                eta=job['rule']['abstain_eta'];key=(phase,dom,job['protocol'],job['arm'],eta)
                groups.setdefault(key,dict(jobs=[],rows=[]));groups[key]['jobs'].append(job)
                row=lookup.get(job['id'])
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
            n_novel_verified_repairs_NONE=sum(r.get('verified')==1 for r in none),
            execution_failure_at_target_feasible_endpoint=sum(r.get('x')==0 and r.get('y')==1 for r in rows),
            failure_phases=dict(collections.Counter(r.get('failed_phase') or ('verified' if r.get('verified')==1 else r['status']) for r in rows)),
            failure_kinds=dict(collections.Counter(r.get('failure_kind') or 'NONE' for r in rows)),
            latency_ms=dict(n=len(latency),median=float(np.median(latency)) if latency else None,p95=float(np.percentile(latency,95)) if latency else None),
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
                    paired[f'{phase}|{dom}|{a}_minus_{b}|eta{ka[4]}']=EV.paired_frozen_root_metrics(aa,bb,roots,seeds=seeds)
    J.atomic_json(out/'FINAL_METRICS.json',dict(metrics=metrics,paired=paired,source_hashes=row_sources,interpretation='Frozen-root intention-to-evaluate; not-run and unresolved are not physical negative labels'))
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
