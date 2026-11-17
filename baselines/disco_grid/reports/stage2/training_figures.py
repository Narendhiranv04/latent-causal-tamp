"""Regenerate TRAIN diagnostics from archived JSON, without loading a teacher.

These are data/optimization diagnostics, never held-out performance curves.
Resource rows are separate accounting layers: do not sum controller totals and
their contained child rows. Interrupted attempts remain in the censoring ledger.
"""
import argparse, collections, csv, hashlib, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def build(campaign,coverage_path,out):
    out.mkdir(parents=True,exist_ok=False)
    coverage=read(coverage_path);records=coverage['records'];sources={str(coverage_path):sha(coverage_path)}
    curves=[];fit_summaries=[];resources=[];censored=[];depths=[]
    for path in sorted(campaign.glob('training/*/*/distill_report.json')):
        report=read(path);sources[str(path)]=sha(path)
        ident=dict(domain=report['domain'],fit=path.parent.parent.name,schema=report['observation_schema'],
            edges_mode=report['edges_mode'],seed=report['seed'])
        fit_summaries.append(dict(ident,n_trees=report['n_trees'],trees_with_solution=report['n_trees_with_solution'],
            physical_calls_in_data=report['total_sim_calls'],obj_rows=report['n_policy_obj_rows'],destination_rows=report['n_policy_dst_rows'],value_rows=report['n_value_rows'],
            epochs=report['completed_epochs'],report_sha256=sha(path),dataset_sha256=report['hyperparameters']['dataset_sha256']))
        # "val_*" in legacy report fields can monitor the very same TRAIN rows.
        # Export train_* only; do not relabel these diagnostics benchmark VAL.
        for kind in ('policy','value'):
            for item in report[kind+'_curve']:
                curves.append(dict(ident,kind=kind,epoch=item['epoch']+1,**{k:v for k,v in item.items() if k.startswith('train_')}))
    for path in sorted(campaign.glob('**/WATCHDOG_ACCOUNTING.json')):
        info=read(path);sources[str(path)]=sha(path)
        resources.append(dict(layer='reaped_child_attempt',path=str(path),cpu_s=info.get('reaped_child_cpu_s'),
            wall_s=info.get('wall_s'),peak_rss_kib=info.get('peak_rss_kib'),reason=info.get('reason'),sha256=sha(path)))
    for row in records:
        if row['status']!='COMPLETED' or row['unreturned_adapter_queries'] or row.get('returned_unresolved_queries',0):
            censored.append({k:row.get(k) for k in ('domain','round','root_id','family_id','K','status','charged_adapter_intents','returned_adapter_queries','unreturned_adapter_queries','returned_unresolved_queries','cpu_s','wall_s')})
        for depth,count in row['checkpoint_depth_counts'].items():
            depths.append(dict(domain=row['domain'],round=row['round'],root_id=row['root_id'],K=row['K'],status=row['status'],depth=int(depth),feasible_edges=count,
                interpretation='latest completed iteration checkpoint; interrupted tail excluded'))
    csv_write(out/'TRAINING_LOSS.csv',curves);csv_write(out/'DISTILLATION_COVERAGE.csv',fit_summaries)
    csv_write(out/'SEARCH_DEPTH.csv',depths);csv_write(out/'CENSORING_LEDGER.csv',censored);csv_write(out/'RESOURCE_ACCOUNTING.csv',resources)
    csv_write(out/'SEARCH_COVERAGE.csv',[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in records])
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    figure_paths=[]
    def save(fig,name):
        for ext in ('png','svg'):
            path=out/f'{name}.{ext}';fig.savefig(path,dpi=200,bbox_inches='tight');figure_paths.append(path)
        plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,6),sharex=True)
    for i,dom in enumerate(('2d','3d')):
        for fit_tag,color in [('P1Q1','#3875a8'),('P2Q2','#d18029'),('P2Q2_knownprefix','#31816a')]:
            subset=[r for r in curves if r['domain']==dom and r['fit']==f'{dom}_{fit_tag}' and r['schema']=='o0_v1' and r['edges_mode']=='all_feasible']
            for col,(kind,field) in enumerate((('policy','train_obj_ce'),('value','train_weighted_bce'))):
                series=[[r for r in subset if r['kind']==kind and r['seed']==s] for s in (0,1,2)]
                if not all(series):continue
                common=sorted(set.intersection(*({r['epoch'] for r in seq} for seq in series)))
                values=np.array([[next(r[field] for r in seq if r['epoch']==epoch) for epoch in common] for seq in series],dtype=float)
                axes[i,col].plot(common,values.mean(0),color=color,label=fit_tag)
                axes[i,col].fill_between(common,values.min(0),values.max(0),color=color,alpha=.14)
                axes[i,col].set_title(f'{dom.upper()} | '+('policy object/STOP NLL' if col==0 else 'weighted Q BCE'))
                axes[i,col].set_xlabel('TRAIN epoch');axes[i,col].set_ylabel('TRAIN loss');axes[i,col].legend(fontsize=7)
    fig.suptitle('Optimization diagnostics: O0 all-feasible, mean/range of three model seeds\nNo held-out task-success claim',fontsize=10);fig.tight_layout();save(fig,'train_loss_diagnostics')
    fig,axes=plt.subplots(1,2,figsize=(9,3.5))
    for ax,dom in zip(axes,('2d','3d')):
        x=np.arange(3)
        for j,rnd in enumerate(('R0','R1')):
            counts=[sum(r['feasible_edges'] for r in depths if r['domain']==dom and r['round']==rnd and r['depth']==d) for d in (1,2,3)]
            ax.bar(x+(j-.5)*.35,counts,.35,label=rnd)
        ax.set_xticks(x,['1','2','3']);ax.set_xlabel('Executed relocation depth');ax.set_ylabel('Feasible edges in completed checkpoints');ax.set_title(dom.upper());ax.legend()
    fig.suptitle('Physical TRAIN search coverage; incomplete iteration tails excluded',fontsize=10);fig.tight_layout();save(fig,'mcts_depth_coverage')
    fig,axes=plt.subplots(1,2,figsize=(9,3.5))
    for ax,dom in zip(axes,('2d','3d')):
        subset=[r for r in records if r['domain']==dom];positions=np.arange(len(subset))
        returned=np.array([r['returned_adapter_queries'] for r in subset]);missing=np.array([r['unreturned_adapter_queries'] for r in subset])
        ax.bar(positions,returned,label='Returned (includes unresolved)');ax.bar(positions,missing,bottom=returned,label='Unreturned',color='#ba4c48')
        ax.axvline(15.5,color='gray',lw=.8);ax.set_xlabel('Frozen root-round order: R0 then R1');ax.set_ylabel('Charged adapter intents');ax.set_title(dom.upper());ax.legend(fontsize=7)
    fig.suptitle('All attempted queries stay in the cost ledger',fontsize=10);fig.tight_layout();save(fig,'mcts_query_accounting')
    manifest=dict(scope='TRAIN-only diagnostics; no physical dispatch; no model selection',source_hashes=sources,
        source_campaign=str(campaign),figures={p.name:sha(p) for p in figure_paths},
        limitations=['Root-count/search-budget task-success learning curves NOT_RUN: only E16 rung executed.',
            'Checkpoint depth totals include quarantined completed checkpoints; use certified-prefix provenance to establish fitting eligibility.',
            'Child cost rows omit controller costs; combine only using cumulative campaign accounting, never sum nested ledgers.',
            'Training losses do not demonstrate held-out improvement.'])
    (out/'figure_sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return dict(fits=len(fit_summaries),curve_rows=len(curves),figures=len(figure_paths),censored_root_rounds=len(censored))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('campaign',type=Path);parser.add_argument('coverage',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();print(json.dumps(build(args.campaign,args.coverage,args.out),indent=2))
