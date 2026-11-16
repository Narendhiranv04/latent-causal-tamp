"""Recompute descriptive archive statistics using frozen replay rows; no tuning."""
import collections
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
# Run from validation source checkout; --evidence path defaults to gvlab archive.
sys.path.insert(0,str(HERE.parents[1]))
import evaluate as EV


def root_ci(rows,seed=20261116):
    by=collections.defaultdict(list)
    for r in rows:
        if r['masks']['eval_task']:
            by[r['root_id']].append(float(r.get('verified')==1 and r['status']=='REPAIR'))
    values=np.array([np.mean(v) for v in by.values()]);rng=np.random.default_rng(seed)
    boot=[values[rng.integers(len(values),size=len(values))].mean() for _ in range(10000)]
    return {'mean':float(values.mean()),'ci95':list(np.percentile(boot,[2.5,97.5])), 'n_independent_roots':len(by),
            'n_prediction_trials':sum(map(len,by.values())),'resampling':'root; seed means within root'}


def analyze(evidence,out):
    report={}
    for dom in ['2d','3d']:
        arms={p.stem.removeprefix(f'replay_{dom}_'):[json.loads(x) for x in p.read_text().splitlines()]
              for p in evidence.glob(f'replay_{dom}_*.jsonl')}
        primary=arms['p2_q2_primary']
        paired={'p2_value_minus_no_value':EV.paired_root_bootstrap_ci(primary,arms['p2_only'],B_boot=10000,seed=20261116,require_same_seeds=True),
                'round1_all_minus_successful_seed0':EV.paired_root_bootstrap_ci([r for r in arms['p1_q1'] if r['seed']==0],arms['p1_succ_only_q1'],B_boot=10000,seed=20261116,require_same_seeds=True)}
        report[dom]={'arms':{k:{'metrics':EV.compute_benchmark_metrics(v),'root_ci':root_ci(v)} for k,v in arms.items()},
                    'paired':paired,'note':'Historical replay; TEST already exposed; no architecture/threshold chosen here'}
    out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,default=Path('/scratch/nav/disco_grid/validation_v2/evidence'))
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();analyze(a.evidence,a.out)
