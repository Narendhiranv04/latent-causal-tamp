"""Plot only measured standalone DISCO release metrics; no teacher/model loads."""
import argparse, hashlib, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def plot(metrics_path,out):
    data=json.loads(metrics_path.read_text());out.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    colors=['#3875a8','#d18029','#31816a'];arms=['O0_P2Q2','O0_closed_P2Q2','O1_closed_P2Q2'];names=['O0 open loop','O0 closed loop','O1 closed loop'];sources=[]
    def save(fig,name):
        for ext in ('png','svg'):
            path=out/f'{name}.{ext}';fig.savefig(path,dpi=200,bbox_inches='tight');sources.append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        plt.close(fig)
    def entry(dom,arm):
        items=[(k,v) for k,v in data['metrics'].items() if k.split('|')[0:2]==['test',dom] and k.split('|')[3]==arm]
        if len(items)>1:raise ValueError('More than one TEST threshold: do not silently select by outcome')
        return items[0][1] if items else None
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,dom in zip(axes,('2d','3d')):
        for index,(arm,name,color) in enumerate(zip(arms,names,colors)):
            item=entry(dom,arm)
            if item is None:continue
            for col,k in enumerate(('1','2','3')):
                value=item['by_K'][k]
                if value['success_rate'] is None:continue
                position=col+(index-1)*.25;rate=value['success_rate']*100;lo,hi=np.array(value['ci95'])*100
                ax.bar(position,rate,.23,color=color,label=name if col==0 else None,
                    hatch='//' if value['status']=='PARTIAL' else None,alpha=.85)
                ax.errorbar(position,rate,yerr=[[max(0.,rate-lo)],[max(0.,hi-rate)]],fmt='none',ecolor=color,capsize=3)
                ax.text(position,rate+3,f"{value['n_verified_success']}/{value['n_expected_predictions']}",ha='center',fontsize=6,rotation=90)
        primary=entry(dom,arms[0]);overall=primary['overall'] if primary else None
        root_note=f" | {overall['n_roots']} roots, {overall['n_expected_predictions']//overall['n_roots']} model seeds" if overall and overall['n_roots'] else ' | NOT_RUN'
        ax.set_xticks(range(3),['K1','K2','K3']);ax.set_title(dom.upper()+root_note);ax.set_ylim(0,115);ax.set_ylabel('Verified task success (%)');ax.legend(fontsize=7)
    fig.suptitle('Exploratory held-out DISCO evaluation | fixed root/seed denominators\n95% root-family bootstrap intervals; hatching denotes unresolved/unexecuted outcomes',fontsize=10)
    fig.tight_layout();save(fig,'heldout_success_by_K')
    comparisons=[('O0_P2Q2_minus_O0_P2','Q2 on − off'),('O0_P2Q2_minus_O0_P2_success_onlyQ2','All feasible − successful-only P2'),
        ('O0_P2Q2_minus_O0_P2_clean_onlyQ2','Certified-prefix − clean-only data'),('O1_closed_P2Q2_minus_O0_closed_P2Q2','Observed joints: O1 − O0 closed loop'),
        ('O0_P2Q2_minus_O0_P1Q1','P2/Q2 − P1/Q1'),('O0_P2Q2_minus_O0_P0','P2/Q2 − P0')]
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,dom in zip(axes,('2d','3d')):
        for index,(comparison,label) in enumerate(comparisons):
            items=[v for k,v in data['paired'].items() if k.startswith(f'test|{dom}|{comparison}|')]
            if not items:continue
            if len(items)!=1:raise ValueError('Ambiguous paired TEST selection')
            item=items[0]
            if item.get('delta') is None:continue
            delta=item['delta']*100;lo,hi=np.array(item['ci95'])*100
            ax.errorbar(delta,index,xerr=[[max(0.,delta-lo)],[max(0.,hi-delta)]],fmt='o',color='#3875a8',capsize=3)
        ax.axvline(0,color='gray',lw=.8);ax.set_title(dom.upper());ax.set_yticks(range(len(comparisons)),[v for k,v in comparisons]);ax.set_xlabel('Task-success difference (percentage points)')
    axes[0].invert_yaxis()
    fig.suptitle('Paired DISCO ablations on the same K1–K3 roots\n95% root-family bootstrap intervals; secondary evolution/data arms use common model seed 0',fontsize=10)
    fig.tight_layout();save(fig,'paired_disco_ablations')
    (out/'figure_sources.json').write_text(json.dumps(dict(metrics_path=str(metrics_path),metrics_sha256=hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
        interpretation='Observed frozen TEST cohorts only; unknowns retained, not certified negatives',figures=sources),indent=2)+'\n')
    return sources


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('metrics',type=Path);parser.add_argument('out',type=Path);args=parser.parse_args();plot(args.metrics,args.out)
