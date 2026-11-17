"""Verify a prospective data-control correction changes no other frozen jobs."""
import argparse, hashlib, json
from pathlib import Path


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(previous,current,out):
    old=read(previous/'manifest.json');new=read(current/'manifest.json')
    if old['cohorts_sha256']!=new['cohorts_sha256']:raise ValueError('Root registry changed')
    checks=changed_controls=0
    for name in old['sets']:
        before=read(previous/name)['jobs'];after=read(current/name)['jobs']
        def identity(job):return (job['domain'],job['arm'],job['root_id'],job['seed'],job['rule']['abstain_eta'])
        aa={identity(j):j for j in before};bb={identity(j):j for j in after}
        if len(aa)!=len(before) or len(bb)!=len(after) or aa.keys()!=bb.keys():raise ValueError('Trial matrix changed')
        for key,first in aa.items():
            second=bb[key]
            if first['domain']=='3d' and first['arm']=='O0_P2_clean_onlyQ2':
                if first['policy_sha256']==second['policy_sha256']:raise ValueError('Coverage control not replaced')
                changed_controls+=1;continue
            for field in ('id','policy_sha256','value_sha256','root_sha256','input_sha256','protocol','schema','physics_seed','rule','teacher_sources'):
                if first.get(field)!=second.get(field):raise ValueError('Non-control job changed: '+str(key)+' '+field)
            for field in ('status','seq','m','observation_schema','selection_physical_counters','selection_trace'):
                if first.get('prediction',{}).get(field)!=second.get('prediction',{}).get(field):raise ValueError('Non-control prediction changed: '+str(key)+' '+field)
            checks+=1
    registry=read(current/'checkpoint_manifest.json')
    for entry in registry:
        if entry['domain']!='3d' or entry['arm']!='O0_P2_clean_onlyQ2':continue
        control=Path(entry['policy']).parent;primary=control.parent.parent/'3d_P2Q2_knownprefix'/control.name
        cc=read(control/'resolved_config.json');pc=read(primary/'resolved_config.json')
        # Same initialization, optimization and engine; only current supervision differs.
        if {k:v for k,v in cc.items() if k!='dataset_sha256'}!={k:v for k,v in pc.items() if k!='dataset_sha256'}:raise ValueError('Data control has unmatched trainer settings')
        if read(control/'distill_report.json')['n_trees']!=31:raise ValueError('Expected 31 clean 3D root-rounds')
    result=dict(status='PASS',non_control_job_checks=checks,replaced_3d_control_jobs=changed_controls,
        previous_manifest_sha256=sha(previous/'manifest.json'),current_manifest_sha256=sha(current/'manifest.json'),script_sha256=sha(Path(__file__)),
        physical_queries=0,heldout_outcomes_used=False,unchanged='primary models, other ablations, roots, rules, common physical seeds and model-only decisions; latency excluded',
        change='3D current-P2 data control uses 31 clean trees and matched P1 initialization; original pooled run included the recovered R0 prefix')
    with out.open('x') as file:json.dump(result,file,indent=2);file.write('\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('previous',type=Path);parser.add_argument('current',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();print(json.dumps(audit(args.previous,args.current,args.out),indent=2))
