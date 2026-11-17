"""Expand the planned held-out cohort before any new VAL/TEST outcome is opened.

Keep every original E16 TRAIN root and original planned evaluation root. Add
independent source components by deterministic hash, excluding known own TEST
exposure. This is an evaluation proposal, never execution authorization.
"""
import argparse, copy, json, os, sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(HERE))
import data as D
from freeze_cohorts import select


def expand(original,out):
    src=json.loads(original.read_text());result=copy.deepcopy(src)
    for dom,info in result['domains'].items():
        rows=D.load_snapshot_rows(dom);groups=D.independence_groups(rows)
        for name,split,n in [('validation_roots','val',3),('exploratory_test_roots','test',5)]:
            existing=info[name];excluded={r['family_id'] for r in existing}
            if split=='test':excluded.update(info['known_exposed_test_components'])
            counts={k:n-sum(str(r['K_legacy'])==k for r in existing) for k in ('0','1','2','3','NONE')}
            extra=select(rows,groups,split,{k:v for k,v in counts.items() if v},excluded,f'stage2-final-{split}-v2|{dom}|20261117')
            info[name]=existing+extra
        info['execution_status']='PROPOSED V15-F25-v1; no VAL/TEST execution authorization'
    result.update(parent_cohort_sha256=D.sha256_file(original),source_commit=os.environ['DISCO_SOURCE_COMMIT'],
        reason='Increase independent evaluation roots before opening outcomes; original TRAIN registry and first evaluation roots unchanged',
        benchmark_change=False,validation_roots_per_domain=15,test_roots_per_domain=25)
    with out.open('x') as f:json.dump(result,f,indent=2)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('original',type=Path);p.add_argument('out',type=Path);a=p.parse_args();expand(a.original,a.out)
