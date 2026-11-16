"""Scientific figures from frozen archive rows, actual scenes and physical trees.

Run on gvlab with --evidence and --out. Dashed arrows are proposed cell edits,
never depicted as robot trajectories. 3D is explicitly a shelf projection.
"""
import argparse
import collections
import dataclasses
import json
import math
from pathlib import Path
import pickle
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np
import data as D
import env as E
import mcts as M
import policy as P
import distill as DS

plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})


def export(fig,out,name):
    fig.savefig(out/f'{name}.png',dpi=220,bbox_inches='tight')
    fig.savefig(out/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)


def arm(ax,q,base,style='k-',label=None):
    theta=np.cumsum(q);length=np.array([.42,.34,.20])
    pos=np.vstack([base,np.asarray(base)+np.cumsum(np.column_stack([length*np.cos(theta),length*np.sin(theta)]),axis=0)])
    ax.plot(pos[:,0],pos[:,1],style,lw=3,marker='o',ms=3,label=label)


def scene(ax,row,pred,caption):
    inp=row['inputs'];dom=row['domain'].lower();pitch=.08 if dom=='2d' else .075
    for d in inp['legal_cells']:
        x,y=inp['cell_xy'][str(d)];ax.plot(x,y,'.',c='.88',ms=2)
    for i,(oid,xy,a) in enumerate(zip(inp['ids'],inp['xy0'],inp['attrs'])):
        col='#db6656' if i==inp['tid'] else '#5b88b3'
        if dom=='2d':ax.add_patch(Circle(xy[:2],float(a[0]),color=col,alpha=.8))
        else:
            # Teacher size = box half-width / cylinder radius (metres).
            size=float(a[2])
            if a[0]:ax.add_patch(Rectangle((xy[0]-size,xy[1]-size),2*size,2*size,color=col,alpha=.8))
            else:ax.add_patch(Circle(xy[:2],size,color=col,alpha=.8))
        ax.text(xy[0],xy[1],oid,ha='center',va='center',fontsize=6)
    gx,gy=inp['goal'][:2];ax.plot(gx,gy,'*',c='#be3424',ms=12)
    if dom=='2d':arm(ax,inp['q_ref'],inp['base'][:2],label='root q_ref')
    for k,(o,d) in enumerate(pred.get('seq') or []):
        src=inp['xy0'][o][:2];dst=inp['cell_xy'][str(d)][:2]
        ax.annotate('',xy=dst,xytext=src,arrowprops={'arrowstyle':'->','ls':'--','color':'#d58b14'})
        ax.text(dst[0],dst[1],str(k+1),color='#744000',fontsize=8)
    ax.set_aspect('equal');ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    ax.set_title(caption+'\n'+row['root_id'],fontsize=8)
    ax.set_xlabel(f"x (m) | proposed {pred.get('seq')}\nX={pred.get('x')} Y={pred.get('y')} phase={pred.get('failed_phase')}\n"+
            ('full 3R root pose; arrows are cell proposals' if dom=='2d' else 'canonical footprint projection; full 3D arm NOT_AVAILABLE'),fontsize=7)


def main(evidence,out):
    out.mkdir(parents=True,exist_ok=True)
    stats=json.loads((evidence/'archive_statistics.json').read_text())
    training=json.loads((evidence/'new_training.json').read_text())
    cal=json.loads((evidence/'stop_calibration.json').read_text())
    rows={dom:{r['root_id']:r for r in D.load_snapshot_rows(dom)} for dom in ['2d','3d']}
    predictions={dom:[json.loads(x) for x in (evidence/f'replay_{dom}_p2_q2_primary.jsonl').read_text().splitlines()] for dom in ['2d','3d']}
    names=['uniform_no_q','p0_only','p1_q1','p2_only','p2_q2_primary'];labels=['Uniform','P0','P1+Q1','P2','P2+Q2']
    fig,axs=plt.subplots(1,2,figsize=(10,3.6))
    for ax,dom in zip(axs,['2d','3d']):
        means=np.array([stats[dom]['arms'][n]['root_ci']['mean'] for n in names])*100
        ci=np.array([stats[dom]['arms'][n]['root_ci']['ci95'] for n in names])*100
        ax.errorbar(np.arange(len(names)),means,yerr=np.array([means-ci[:,0],ci[:,1]-means]),fmt='o',capsize=4,color='#356f9d')
        ax.set_xticks(np.arange(len(names)),labels,rotation=25);ax.set_ylim(0,60);ax.set_ylabel('verified task success (%)')
        ax.set_title(f"{dom.upper()} archive: {45 if dom=='2d' else 18} task roots; root bootstrap 95% CI")
    fig.suptitle('Historical pilot only; training seeds averaged within each physical root')
    fig.tight_layout();export(fig,out,'archive_success_root_ci')
    fig,axs=plt.subplots(1,2,figsize=(9,3.3))
    for ax,key,title in zip(axs,['p2_value_minus_no_value','round1_all_minus_successful_seed0'],['Value minus no value (3 seeds)','Round-1 all-feasible minus successful-only (seed 0)']):
        for i,dom in enumerate(['2d','3d']):
            item=stats[dom]['paired'][key];d=item['delta']*100;lo,hi=np.array(item['ci95'])*100
            ax.errorbar(d,i,xerr=[[d-lo],[hi-d]],fmt='o',capsize=4)
        ax.axvline(0,c='.6',lw=1);ax.set_yticks([0,1],['2D','3D']);ax.set_xlabel('paired task-success difference (percentage points)');ax.set_title(title,fontsize=9)
    fig.tight_layout();export(fig,out,'corrected_ablation_differences')
    fig,axs=plt.subplots(2,2,figsize=(9,6))
    for i,dom in enumerate(['2d','3d']):
        for schema,mode,color in [('o0_v1','all_feasible','#356f9d'),('o0_v1','successful_only','#d18b26'),('o1_qt_v1','all_feasible','#3c9369')]:
            runs=[r for r in training[dom]['runs'] if r['observation_schema']==schema and r['edges_mode']==mode]
            for j,(field,curve) in enumerate([('train_dst_ce','policy_curve'),('train_weighted_bce','value_curve')]):
                values=np.array([[e[field] for e in r[curve]] for r in runs]);ep=np.arange(values.shape[1])+1
                axs[i,j].plot(ep,values.mean(0),label=f'{schema} {mode}',color=color)
                axs[i,j].fill_between(ep,values.min(0),values.max(0),color=color,alpha=.15)
                axs[i,j].set_title(f'{dom.upper()} {field}');axs[i,j].set_xlabel('fixed training epoch')
    axs[0,0].legend(fontsize=6);fig.suptitle('New matched training on historical round-0 trees; shading=min–max 3 seeds\nTraining diagnostics, not held-out physical success',fontsize=10)
    fig.tight_layout(rect=[0,0,1,.92]);export(fig,out,'matched_training_curves')
    fig,axs=plt.subplots(1,2,figsize=(9,3.5))
    for ax,dom in zip(axs,['2d','3d']):
        attempted=collections.Counter();feasible=collections.Counter()
        for p in (D.DISCO_ROOT/'trees'/dom/'r0_p0_pw_geom').glob('*/tree.json'):
            for e in json.loads(p.read_text())['edge_logs']:
                attempted[e['depth']]+=1;feasible[e['depth']]+=int(e['status']=='EXECUTED')
        ax.bar([1,2,3],[feasible[d] for d in [1,2,3]],label='feasible')
        ax.bar([1,2,3],[attempted[d]-feasible[d] for d in [1,2,3]],bottom=[feasible[d] for d in [1,2,3]],label='failed/unresolved',color='.75')
        ax.set_xticks([1,2,3]);ax.set_xlabel('relocation depth');ax.set_ylabel('physical transition attempts');ax.set_title(f'{dom.upper()} archived round 0')
        for d in [1,2,3]:ax.text(d,attempted[d]+1,f'{feasible[d]}/{attempted[d]}',ha='center',fontsize=8)
    axs[0].legend(fontsize=7);fig.tight_layout();export(fig,out,'physical_edge_coverage')
    fig,axs=plt.subplots(1,2,figsize=(9,3.4))
    for ax,dom in zip(axs,['2d','3d']):
        examples=[json.loads(x) for x in (evidence/f'stop_calibration_{dom}_val.jsonl').read_text().splitlines()]
        held=[r for r in examples if r['family_id'] in cal[dom]['audit_family_ids']]
        raw=np.array([r['q_stop'] for r in held]);truth=np.array([r['z_stop'] for r in held]);rule=cal[dom]['rule']
        adjusted=1/(1+np.exp(-(np.log(np.clip(raw,1e-6,1-1e-6)/(1-np.clip(raw,1e-6,1-1e-6)))/rule['root_stop_temperature']+rule['root_stop_bias'])))
        for q,label in [(raw,'raw Q'),(adjusted,'VAL affine-logit adaptation')]:
            xs=[];ys=[]
            for lo,hi in zip(np.linspace(0,1,7)[:-1],np.linspace(0,1,7)[1:]):
                mask=(q>=lo)&(q<=hi if hi==1 else q<hi)
                if mask.any():xs.append(q[mask].mean());ys.append(truth[mask].mean())
            ax.plot(xs,ys,'o-',label=label)
        ax.plot([0,1],[0,1],':',c='.5');ax.set(xlim=(0,1),ylim=(0,1),xlabel='predicted root STOP success',ylabel='observed Y0 success',title=f'{dom.upper()} VAL audit families (n={len(held)})')
    axs[0].legend(fontsize=6);fig.suptitle('Calibration diagnostic only: no new task-success or TEST claim',fontsize=10);fig.tight_layout();export(fig,out,'stop_calibration')
    cases=[]
    def choose(dom,predicate,title):
        match=next((p for p in predictions[dom] if predicate(p)),None)
        if match:cases.append((dom,match,title))
    choose('2d',lambda p:p['K_legacy']=='0' and p['status']!='NOOP','K0 STOP miss')
    choose('2d',lambda p:p['K_legacy']=='1' and p['verified']==1,'K1 independently verified success')
    choose('2d',lambda p:p['K_legacy']=='2' and p['verified']==0,'K2 failed proposed repair')
    choose('2d',lambda p:p['K_legacy']=='3' and p['verified']==0,'K3 failed proposed repair')
    choose('2d',lambda p:p['K_legacy']=='NONE' and p['status']=='ABSTAIN','Legacy NONE explicit abstention')
    choose('3d',lambda p:p.get('failure_kind')=='GRASP_FAILED' or str(p.get('failed_phase')).startswith('connector'),'3D failed grasp / connector')
    fig,axs=plt.subplots(2,3,figsize=(13,9),layout='constrained');registry=[]
    for ax,(dom,pred,title) in zip(axs.flat,cases):
        row=rows[dom][pred['root_id']];scene(ax,row,pred,title)
        registry.append({'case':title,'domain':dom,'root_id':row['root_id'],'root_sha256':row['root_sha256'],'prediction':pred,'verification':'archived independent verifier; not re-executed for this plot'})
    for ax in list(axs.flat)[len(cases):]:ax.text(.2,.5,'NOT_AVAILABLE');ax.axis('off')
    export(fig,out,'actual_scene_cases')
    parity=json.loads((evidence/'physical_parity_compact.json').read_text())
    order_cases=[r for r in parity['records'] if r['domain']=='2d']
    if len(order_cases)==2:
        fig,axs=plt.subplots(1,2,figsize=(10,5),layout='constrained')
        for ax,item in zip(axs,order_cases):
            case=item['case'];result=item['result'];pred={'seq':case['seq'],**result}
            scene(ax,rows['2d'][case['root_id']],pred,'Fresh physical order replay: '+('success' if result['z']==1 else 'failure'))
        export(fig,out,'verified_order_pair')
    # Same geometry: achieved q before a successful verified STOP vs its accepted q_ref connector endpoint.
    for path in sorted((D.DISCO_ROOT/'trees/2d/r0_p0_pw_geom').glob('*/nodes.pkl')):
        with path.open('rb') as f:nodes=pickle.load(f)
        node=next((n for n in nodes if n.depth>0 and not n.is_stop_node and n.stop_result and n.stop_result.x_terminal==1),None)
        if node is None:continue
        st=E.RepairEnv.restore(node.state_blob);row=rows['2d'][st.root_id];inp=row['inputs']
        if np.allclose(st.q_t,inp['q_ref']):continue
        fig,axs=plt.subplots(1,2,figsize=(8,4))
        for ax,q,title in zip(axs,[st.q_t,inp['q_ref']],['achieved q_t before STOP','accepted terminal connector q_ref']):
            for oid,c,a in zip(inp['ids'],st.cells,inp['attrs']):
                x,y=inp['cell_xy'][str(c)];ax.add_patch(Circle((x,y),float(a[0]),color='#5b88b3',alpha=.7));ax.text(x,y,oid,fontsize=6)
            arm(ax,q,inp['base'][:2]);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
        fig.suptitle(f'{st.root_id}: identical endpoint cells, differing physically verified robot context\nStatic configurations, not a trajectory interpolation',fontsize=9)
        fig.tight_layout();export(fig,out,'same_geometry_different_q')
        registry.append({'case':'same geometry differing q','root_id':st.root_id,'tree':str(path),'state_hash':st.state_hash(),'q_t':st.q_t,'q_ref':inp['q_ref'],'cells':st.cells,'connector_witness':node.stop_result.witness_connector})
        break
    (out/'case_registry.json').write_text(json.dumps(registry,indent=2))
    fig,ax=plt.subplots(figsize=(11,3));ax.axis('off')
    texts=[(.1,.68,'TRAIN roots only\nphysical MCTS (UCB + PW)'),(.4,.68,'all feasible edges → categorical policy\ndecided leaves → Q(h,a)'),(.72,.68,'O0 open-loop: predicted cell edits\nzero selection physical calls'),(.93,.68,'one committed\nX + canonical Y'),(.49,.15,'Separate O1 closed-loop: execute chosen move → observe achieved joints → next policy/Q query')]
    for x,y,t in texts:ax.text(x,y,t,ha='center',va='center',bbox={'boxstyle':'round,pad=.5','facecolor':'#eaf0f5','edgecolor':'#356f9d'},fontsize=8)
    for a,c in [(.22,.29),(.54,.60),(.84,.87)]:ax.annotate('',xy=(c,.68),xytext=(a,.68),arrowprops={'arrowstyle':'->'})
    ax.set_title('DISCO-Grid (adapted): discrete object–destination policies; fixed benchmark grasps',fontsize=11)
    export(fig,out,'method_diagram')
    (out/'source_manifest.json').write_text(json.dumps({'source_runs':['D0-D8 archive','validation_v2/ablations_2d_r1','validation_v2/ablations_3d_r1'],'script_sha256':D.sha256_file(__file__),'notes':['No independent-root performance learning curve: NOT_RUN','3D full-arm trajectory rendering: NOT_AVAILABLE','O1 closed-loop success: NOT_RUN']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.evidence,a.out)
