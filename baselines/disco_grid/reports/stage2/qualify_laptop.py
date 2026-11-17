"""Check migrated inputs and frozen model decisions without physical execution."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import collect as C, data as D, evaluate as EV, physical_eval as PE


def qualify(rootfs,out):
    start=time.monotonic();cpu=time.process_time()
    C.execution_host('girish-laptop');C.require_headroom()
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise PermissionError('CPU only')
    import torch, mujoco
    torch.set_num_threads(1)
    if torch.__version__!='2.5.1+cpu' or mujoco.__version__!='3.16.0':raise ValueError('Unqualified library version')
    spec=__import__('importlib.util',fromlist=['util']).spec_from_file_location('laptop_paths',HERE/'continue_physical_laptop.py')
    module=__import__('importlib.util',fromlist=['util']).module_from_spec(spec);spec.loader.exec_module(module)
    prep=rootfs/'scratch/nav/disco_grid/stage2/campaigns/E16_v1_20261117/evaluation_preparation_v3'
    jobs=[]
    for p in sorted(prep.glob('*eta*.json')):jobs.extend(json.loads(p.read_text())['jobs'])
    rows={d:{r['root_id']:r for r in D.load_snapshot_rows(d)} for d in ('2d','3d')}
    checked_roots=set();teachers={};models={};cases=[];chosen={}
    for job in jobs:
        key=(job['domain'],job['root_id'])
        if key not in checked_roots:
            row=rows[key[0]][key[1]]
            if C.input_hash(row)!=job['input_sha256'] or D.sha256_file(D.raw_root_path(*key))!=job['root_sha256']:
                raise ValueError('Migrated root mismatch: '+str(key))
            checked_roots.add(key)
        teachers.update(job['teacher_sources'])
        for kind in ('policy','value'):
            if job.get(kind):models[job[kind]]=job[kind+'_sha256']
        if (job['protocol']=='open_loop' and not job.get('diagnostic_only') and
                job['rule']['abstain_eta']==0. and str(job['K_legacy'])=='1'):
            modelkey=(job['domain'],job['policy_sha256'],job.get('value_sha256'),job['mode'])
            chosen.setdefault(modelkey,job)
    for path,digest in {**teachers,**models}.items():
        if D.sha256_file(module.relocated(path,rootfs))!=digest:raise ValueError('Migrated source/model mismatch: '+path)
    for job in chosen.values():
        local=module.relocated(job,rootfs);proposal=PE.load_proposal(local)
        pred=EV.predict_open_loop_sequence(rows[job['domain']][job['root_id']],job['domain'],proposal,
            B_test=job['B'],use_value=job['use_value'],rule=job['rule'],seed=job['seed'])
        if any(pred['selection_physical_counters'].values()):raise ValueError('Qualification called physics')
        if any(pred.get(k)!=job['prediction'].get(k) for k in ('seq','status','m')):
            # Lists and tuples represent the same discrete frozen actions.
            if (json.dumps(pred.get('seq'))!=json.dumps(job['prediction'].get('seq')) or
                    pred['status']!=job['prediction']['status'] or pred.get('m')!=job['prediction'].get('m')):
                raise ValueError('Frozen model decision differs on laptop: '+job['id'])
        cases.append(dict(job_id=job['id'],domain=job['domain'],arm=job['arm'],seed=job['seed'],
            policy_sha256=job['policy_sha256'],value_sha256=job.get('value_sha256'),
            matched=True,seq=pred['seq'],status=pred['status'],selection_physical_counters=pred['selection_physical_counters']))
        if time.process_time()-cpu>120 or time.monotonic()-start>180:raise RuntimeError('Qualification cost ceiling')
    result=dict(status='PASS',roots=len(checked_roots),teacher_files=len(teachers),model_files=len(models),
        model_decision_cases=cases,torch=torch.__version__,mujoco=mujoco.__version__,
        cpu_s=time.process_time()-cpu,wall_s=time.monotonic()-start,physical_queries=0,
        source_commit=os.environ.get('DISCO_SOURCE_COMMIT'),
        scope='Hash-identical inputs/weights/teachers and nonphysical prediction parity; not physical task success or TEST model selection')
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rootfs',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();r=qualify(args.rootfs,args.out)
    print(json.dumps({k:v for k,v in r.items() if k!='model_decision_cases'},indent=2))
