# Remaining 3D (root -> seqs) after pooling: pre-run caches + all V3.1-4 3D results (laptop, gvlab, girish); greedy split by host throughput.
# usage: rebalance3d.py OUTDIR NEW_RESULTS_FILES(comma) host:rate[,host:rate...]
import json, sys, glob, collections
out, news, rates = sys.argv[1], sys.argv[2].split(','), dict((h, float(r)) for h, r in (x.split(':') for x in sys.argv[3].split(',')))
have = set()
for p in open('/home/naren/abf_v314_verify/caches_3d.txt').read().strip().split(',') + news:
    for l in open(p):
        try:
            v = json.loads(l); have |= {(v['root'], json.dumps(r['seq'])) for r in v['results']}
        except Exception: pass
want = collections.defaultdict(set)
for fn in glob.glob('/home/naren/abf_v314_verify/runs/slim_test/3d/*.jsonl'):
    for l in open(fn):
        r = json.loads(l)
        if r['selected_ordered_seq'] and (r['root_id'], json.dumps(r['selected_ordered_seq'])) not in have:
            want[r['root_id']].add(json.dumps(r['selected_ordered_seq']))
load = {h: 0.0 for h in rates}; assign = {h: [] for h in rates}
for k in sorted(want, key=lambda k: -len(want[k])):
    h = min(rates, key=lambda h: (load[h] + len(want[k])) / rates[h]); assign[h].append(k); load[h] += len(want[k])
print('remaining 3D roots', len(want), 'queries', sum(map(len, want.values())))
for h in rates:
    with open(f'{out}/assign3d_{h}.jsonl', 'w') as f:
        for k in sorted(assign[h]):
            for s in sorted(want[k]): f.write(json.dumps({'root_id': k, 'selected_ordered_seq': json.loads(s), 'decision': 'REPAIR'}) + '\n')
    print(h, 'roots', len(assign[h]), 'queries', int(load[h]), 'est min %.0f' % (load[h] / rates[h]))
