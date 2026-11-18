"""Aggregate independently verified VAL summaries (benchmark.py summarize) per DISCO arm: mean +- sd over seeds."""
import json, glob, os, re, sys, statistics as st, collections
src = sys.argv[1]; G = collections.defaultdict(list)
for f in sorted(glob.glob(f'{src}/results*/SUMMARY_pred_*.json')):
    s = list(json.load(open(f)).values())[0]; name = os.path.basename(f)[len('SUMMARY_pred_'):-5]
    arm, seed = re.match(r'(.*)_s(\d)$', name).groups()
    G[arm].append(dict(seed=int(seed), n=s['n_roots'], task=s['task']['rate_ci'][0], task_ci=s['task']['rate_ci'][1:], by_K={k: v['rate_ci'][0] for k, v in s['task_by_K'].items()},
                       noop=s['noop']['rate_ci'][0], abstain=s['abstain']['rate_ci'][0], outcomes=s['outcomes'],
                       unknown=s['task']['unknown'] + s['noop']['unknown'] + s['abstain']['unknown'], latency_p50=s['latency_s']['p50']))
out = {}
for arm, v in sorted(G.items()):
    m = lambda k: round(st.mean(x[k] for x in v), 2); sd = lambda k: round(st.stdev(x[k] for x in v), 2) if len(v) > 1 else None
    out[arm] = dict(seeds=sorted(x['seed'] for x in v), n=v[0]['n'], task_mean=m('task'), task_sd=sd('task'), noop_mean=m('noop'), abstain_mean=m('abstain'),
                    unknown=sum(x['unknown'] for x in v), per_seed=v)
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print('| arm | seeds | Task % mean (sd) | K1 / K2 / K3 (seed mean) | NOOP % | ABSTAIN % | UNKNOWN |'); print('|---|---|---|---|---|---|---|')
for arm, a in out.items():
    ks = ' / '.join(f"{st.mean(x['by_K'].get(k, 0) for x in a['per_seed']):.1f}" for k in ('1', '2', '3'))
    print(f"| {arm} | {len(a['seeds'])} | {a['task_mean']:.1f}" + (f" ({a['task_sd']:.1f})" if a['task_sd'] is not None else '') + f" | {ks} | {a['noop_mean']:.1f} | {a['abstain_mean']:.1f} | {a['unknown']} |")
