"""Create candidate physical-root pairing; fail closed on missing model provenance.

This does not evaluate either method or treat matching IDs as teacher identity.
Runs on gvlab against the frozen base inputs and archived V3 slim selections.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
import data as D


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build(evidence,out):
    report={'status':'BLOCKED_MODEL_AND_TEACHER_PROVENANCE','protocol':'strict_open_loop_single_commit_no_retry',
            'source_snapshot':str(D.BASE_SNAP),'snapshot_lock_sha256':D.sha256_file(D.BASE_SNAP/'data_snapshot.lock.json'),
            'approach_b_revision':'ede29034b2 (V3); V3.1 is a distinct comparator',
            'blockers':['V3 trained sampler/scorer checkpoint bytes and checksums absent from inventoried gvlab locations',
                        'Slim predictions contain root ID and selected sequence, no scene/robot/teacher hashes',
                        'Nominal V3 snapshot path advertised by DISCO config is absent on gvlab',
                        'V3.1 checkpoint/run provenance must be frozen independently after its live verification finishes'],
            'domains':{}}
    for dom in ['2d','3d']:
        primary=[json.loads(x) for x in (evidence/f'replay_{dom}_p2_q2_primary.jsonl').read_text().splitlines()]
        rows={r['root_id']:r for r in D.load_snapshot_rows(dom,'test')}
        roots=sorted({p['root_id'] for p in primary})
        seeds={}
        for seed in [0,1,2]:
            path=Path(f'/scratch/nav/abf_v3/runs/slim_test/{dom}/v3D_task:q2init_all-S1_M4_B4096_s{seed}_test.jsonl')
            selections=[json.loads(x) for x in path.read_text().splitlines()]
            ids={r['root_id'] for r in selections}
            if len(ids)!=len(selections): raise ValueError('Duplicate V3 root IDs')
            seeds[str(seed)]={'selection_path':str(path),'selection_sha256':D.sha256_file(path),
                              'n_roots':len(ids),'n_shared':len(ids&set(roots)),'n_missing':len(set(roots)-ids),
                              'sampler_checkpoint_sha256':None,'scorer_checkpoint_sha256':None}
        paired=[]
        for rid in roots:
            row=rows[rid];inp=row['inputs'];raw=D.raw_root_path(dom,rid)
            if D.sha256_file(raw)!=row['root_sha256']: raise ValueError('Raw scene hash mismatch')
            paired.append({'root_id':rid,'domain':dom,'split':'test','class':row['K_legacy'],
                    'family_id':D.root_family_key(row),'raw_scene_sha256':row['root_sha256'],
                    'inputs_sha256':digest(inp),'goal_sha256':digest([inp['tid'],inp['goal'],inp['goal_cell']]),
                    'robot_context_sha256':digest([inp['base'],inp['ctx'],inp['q_ref']]),
                    'trial_seeds':[0,1,2],'approach_b_input_hash_attested':False})
        report['domains'][dom]={'roots':paired,'candidate_selections':seeds,
                    'n_candidate_roots':len(paired),'n_task_roots':sum(r['class'] in ['1','2','3'] for r in paired),
                    'physical_verifier':'unchanged original X plus terminal connector; canonical endpoint Y',
                    'paired_results':'NOT_RUN; do not infer from differently sized published aggregates'}
    out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,default=Path('/scratch/nav/disco_grid/validation_v2/evidence'))
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();build(a.evidence,a.out)
