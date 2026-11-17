"""Read-only, standard-library campaign coverage/cost report; no teacher/model calls."""
import argparse, collections, csv, hashlib, json
from pathlib import Path

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def summarize(root,out):
    manifest=read(root/'manifest.json');records=[];inputs={}
    for dom in ('2d','3d'):
        for rnd in range(2):
            for r in manifest['cohorts']['domains'][dom]['train_roots']:
                td=root/f'trees/{dom}/R{rnd}'/r['root_id'];state=td/r['root_id']
                events=[]
                if (state/'queries.jsonl').exists():
                    events=[json.loads(s) for s in (state/'queries.jsonl').read_text().splitlines()];inputs[str(state/'queries.jsonl')]=sha(state/'queries.jsonl')
                starts=[e for e in events if e['event']=='started'];ends=[e for e in events if e['event']=='finished']
                accounts=[read(p) for p in td.glob('attempts/*/WATCHDOG_ACCOUNTING.json')]
                status=read(td/'ATTEMPT_COMPLETE.json')['status'] if (td/'ATTEMPT_COMPLETE.json').exists() else 'IN_PROGRESS' if td.exists() else 'NOT_RUN'
                tree=read(state/'tree.json') if (state/'tree.json').exists() else {};nodes=tree.get('nodes',[])
                if tree:inputs[str(state/'tree.json')]=sha(state/'tree.json')
                feasible=[n for n in nodes if n['node_id']>0 and not n['is_stop_node']]
                phases={k:sum((e.get('accounting') or {}).get(k,0) or 0 for e in ends) for k in ('transition_planner_calls','connector_calls','y_calls','y_cache_hits')}
                row=dict(domain=dom,round=f'R{rnd}',root_id=r['root_id'],family_id=r['family_id'],K=r['K_legacy'],status=status,
                    charged_adapter_intents=len(starts),returned_adapter_queries=len(ends),unreturned_adapter_queries=len(starts)-len(ends),
                    returned_feasible_transitions=sum(e['kind']=='transition' and e['status']=='EXECUTED' for e in ends),
                    cpu_s=sum(a['reaped_child_cpu_s'] for a in accounts) if accounts else None,
                    wall_s=sum(a['wall_s'] for a in accounts) if accounts else None,
                    checkpoint_feasible_edges=len(feasible),checkpoint_depth_counts=dict(collections.Counter(n['depth'] for n in feasible)),
                    checkpoint_terminal_counts=dict(collections.Counter(f"depth{len(n['prefix'])}|Z{n['terminal_z']}" for n in nodes if n['stop_evaluated'])),
                    returned_terminal_outcomes=dict(collections.Counter(f"depth{e['depth']}|Z{(e.get('raw_teacher_outcome') or {}).get('z_outcome') if e['status']=='DECIDED' else 'UNRESOLVED'}" for e in ends if e['kind']=='terminal')),
                    checkpoint_summary=tree.get('summary'),phases=phases,watchdog_reasons=[a['reason'] for a in accounts],
                    checkpoint_sha256=sha(state/'checkpoint.pkl') if (state/'checkpoint.pkl').exists() else None)
                records.append(row)
    fits=[]
    for p in root.glob('training/*/*/distill_report.json'):
        rep=read(p);fits.append(dict(path=str(p),sha256=sha(p),domain=rep['domain'],round=rep['round'],seed=rep['seed'],schema=rep['observation_schema'],completed_epochs=rep['completed_epochs'],edges_mode=rep['edges_mode']))
    totals={dom:dict(planned_root_rounds=32,n_attempted=sum(x['status']!='NOT_RUN' for x in records if x['domain']==dom),
        n_clean=sum(x['status']=='COMPLETED' for x in records if x['domain']==dom),
        n_quarantined=sum(x['status']=='QUARANTINED_UNRESOLVED' for x in records if x['domain']==dom),
        charged_intents=sum(x['charged_adapter_intents'] for x in records if x['domain']==dom),
        returned_queries=sum(x['returned_adapter_queries'] for x in records if x['domain']==dom),
        cpu_s=sum(x['cpu_s'] or 0 for x in records if x['domain']==dom),wall_s=sum(x['wall_s'] or 0 for x in records if x['domain']==dom)) for dom in ('2d','3d')}
    report=dict(source=str(root),source_commit=manifest['source_commit'],scope='TRAIN collection and fits; no held-out task results',
        totals=totals,records=records,fits=fits,source_hashes=inputs,controller_complete=(root/'CONTROLLER_COMPLETE.json').exists(),
        physical_task_evaluation='NOT_RUN')
    out.mkdir(parents=True,exist_ok=True);(out/'training_coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    keys=['domain','round','root_id','family_id','K','status','charged_adapter_intents','returned_adapter_queries','unreturned_adapter_queries','returned_feasible_transitions','cpu_s','wall_s','checkpoint_feasible_edges']
    with (out/'training_coverage.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(records)
    print(json.dumps(dict(totals=totals,fits=len(fits),controller_complete=report['controller_complete']),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();summarize(a.root,a.out)
