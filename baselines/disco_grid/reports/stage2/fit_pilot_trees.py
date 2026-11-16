"""Fixed-schedule diagnostic fits on completed new TRAIN trees, never final models."""
import argparse, json, os, resource, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import data as D, collect as C, distill as DS, policy as P

def run(dom,out):
    C.require_headroom()
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU only')
    os.nice(10)
    import torch;torch.set_num_threads(1)
    out.mkdir(parents=True,exist_ok=False)
    planned={};trees=[];excluded=[]
    for manifest in sorted((D.DISCO_ROOT/'stage2/trees').glob('pilot_*/manifest.json')):
        m=json.loads(manifest.read_text())
        if m['domain']!=dom:continue
        for root in m['roots']:
            rid=root['root_id'];planned[rid]=root
            td=manifest.parent/rid
            if not td.exists():continue
            if (td/'IN_FLIGHT').exists() or not (td/'checkpoint.pkl').exists():excluded.append(dict(root_id=rid,reason='quarantined incomplete tree',path=str(td)));continue
            trees.append(td)
    if not trees:raise ValueError('No completed physical trees')
    scalers=json.loads((D.ABF_ROOT/f'data/q2_{dom}/scalers.json').read_text())
    manifest=dict(domain=dom,scope='DIAGNOSTIC P1/Q1 on pilot TRAIN evidence; not final, no held-out task evaluation',
        source_commit=os.environ['DISCO_SOURCE_COMMIT'],epochs=45,seeds=[0,1,2],batch_size=64,lr=.001,
        source_sha256={p.name:D.sha256_file(p) for p in HERE.glob('*.py')},
        planned_roots=list(planned.values()),excluded_incomplete=excluded,
        trees=[dict(path=str(t),checkpoint_sha256=D.sha256_file(t/'checkpoint.pkl'),journal_sha256=D.sha256_file(t/'queries.jsonl')) for t in trees])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    reports=[];start=time.monotonic();cpu=time.process_time()
    for schema,mode in [(P.O0,'all_feasible'),(P.O0,'successful_only'),(P.O1,'all_feasible')]:
        extracted=DS.extract_dataset_from_tree_dirs(trees,dom,scalers,observation_schema=schema,edges_mode=mode)
        counts={}
        for kind in ['policy_dst_rows','policy_obj_rows','value_rows']:
            from collections import Counter
            counts[kind]=dict(Counter(f"{r['root_id']}|K{r['K_legacy']}|depth{r['depth']}|STOP{r.get('is_stop',False)}" for r in extracted[kind]))
        (out/f'coverage_{schema}_{mode}.json').write_text(json.dumps(counts,indent=2))
        for seed in [0,1,2]:
            C.require_headroom()
            rep=DS.distill_policy_and_value(dom,extracted,D.DISCO_ROOT/f'runs/p0/{dom}/s{seed}/model.pt',
                round_name='stage2_pilot_P1Q1',seed=seed,epochs=45,batch_size=64,device='cpu',
                out_dir=out/f'{schema}_{mode}_s{seed}',checkpoint_rule='fixed_epochs')
            rep.update(policy_sha256=D.sha256_file(rep['policy_ckpt']),value_sha256=D.sha256_file(rep['value_ckpt']) if rep['value_ckpt'] else None)
            reports.append(rep)
            (out/'results.json').write_text(json.dumps(dict(runs=reports,wall_s=time.monotonic()-start,cpu_s=time.process_time()-cpu,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_physical_calls=0),indent=2))
    # Q rows and schedule are identical between policy-edge controls.
    for seed in [0,1,2]:
        a=DS.load_value_checkpoint(out/f'{P.O0}_all_feasible_s{seed}/value.pt','cpu')[0]
        b=DS.load_value_checkpoint(out/f'{P.O0}_successful_only_s{seed}/value.pt','cpu')[0]
        if any(not torch.equal(v,b.state_dict()[k]) for k,v in a.state_dict().items()):raise RuntimeError('Policy-only control changed Q training')
    return dict(fits=len(reports),roots=len(trees),scope=manifest['scope'])
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--domain',choices=['2d','3d'],required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();print(json.dumps(run(v.domain,v.out)))
