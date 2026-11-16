# remaining 2D (root -> seqs) per host shard at this moment: initial want (slim files minus pre-run caches) minus roots finished in this run
import json, sys, hashlib, glob, collections
caches = open('/home/naren/abf_v314_verify/caches_2d.txt').read().strip().split(',')
have = set()
for p in caches:
    for i, l in enumerate(open(p)):
        if p.endswith('abf_v31_lapverify/runs/verify_2d.jsonl') and i >= 1235: break
        v = json.loads(l); have |= {(v['root'], json.dumps(r['seq'])) for r in v['results']}
want = collections.defaultdict(set)
for fn in glob.glob('/home/naren/abf_v314_verify/runs/slim_test/2d/*.jsonl'):
    for l in open(fn):
        r = json.loads(l)
        if r['selected_ordered_seq'] and (r['root_id'], json.dumps(r['selected_ordered_seq'])) not in have:
            want[r['root_id']].add(json.dumps(r['selected_ordered_seq']))
done = set()
for p in sys.argv[1:]:
    for l in open(p):
        try: done.add(json.loads(l)['root'])
        except Exception: pass
h = lambda k: int(hashlib.sha256(k.encode()).hexdigest(), 16) % 20
out = {}
for host, sh in (('lap', set(range(11))), ('gv', set(range(11, 20)))):
    rem = sorted(k for k in want if h(k) in sh and k not in done)
    out[host] = {k: sorted(want[k]) for k in rem}
    print(host, 'total', sum(len(v) for k, v in want.items() if h(k) in sh), 'remaining roots', len(rem), 'queries', sum(len(want[k]) for k in rem))
json.dump(out, open(sys.argv[0].replace('remaining2d.py', 'remaining2d.json'), 'w'))
