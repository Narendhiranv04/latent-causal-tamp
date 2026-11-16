"""Continue only untouched roots of a frozen pilot after a quarantined sibling.

Never resume or repeat an ambiguous query. Inherit the unused original aggregate
wall/call envelope and exact root list/proposal/source, preserving parent bytes.
"""
import argparse, copy, json, pathlib

def freeze(parent,out):
    p=pathlib.Path(parent);out=pathlib.Path(out);m=json.loads((p/'manifest.json').read_text())
    import hashlib
    unstarted=[r for r in m['roots'] if not (p/r['root_id']).exists()]
    if not unstarted:raise ValueError('No untouched predeclared roots')
    costs=list(p.glob('attempts/*/WATCHDOG_ACCOUNTING.json'))
    if not costs:raise ValueError('Missing parent accounting; cannot infer unused time')
    used=sum(json.loads(q.read_text())['wall_s'] for q in costs)
    new=copy.deepcopy(m);new.update(roots=unstarted,wall_envelope_s=m['wall_envelope_s']-used,
        aggregate_adapter_call_ceiling=len(unstarted)*m['per_tree']['max_sim_calls'],
        continuation_parent=str(p),parent_manifest_sha256=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest(),
        continuation_rule='only original untouched roots; ambiguous sibling remains quarantined')
    if new['wall_envelope_s']<=new['query_wall_s']:raise ValueError('Insufficient original envelope remaining')
    out.mkdir(parents=True,exist_ok=False);(out/'manifest.json').write_text(json.dumps(new,indent=2)+'\n')
    print([r['root_id'] for r in unstarted],new['wall_envelope_s'])
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('parent');a.add_argument('out');v=a.parse_args();freeze(v.parent,v.out)
