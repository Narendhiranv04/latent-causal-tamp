#!/usr/bin/env python3
"""R8A analysis: per-arm task / NOOP / ABSTAIN rates on the V3.4 cohort and paired comparisons vs FINAL (task roots; sign test; group-cluster
bootstrap 95% CI of the difference, 2,000 resamples, seed 0).  PROD = the sealed V3.4 production predictions (reference).
    python r8a_analyze.py RESULTS_DIR OUT.json"""
import collections, json, math, sys
from pathlib import Path
import numpy as np


def load(d, arm, dom):
    p = Path(d) / f"results_{arm}_{dom}.jsonl"
    return {r["root_id"]: r for r in map(json.loads, open(p))} if p.exists() else None


def sign(g, l):
    n = g + l
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(g, l) + 1)) / 2 ** n) if n else None


def main(d, out):
    arms = sorted({p.name[8:].rsplit("_", 1)[0] for p in Path(d).glob("results_*_*d.jsonl")})
    res = {}
    for dom in ("3d", "2d"):
        F = load(d, "FINAL", dom)
        task = sorted(r for r, x in F.items() if x["masks"]["eval_task"])
        grp = {r: F[r]["group"] for r in task}
        G = sorted(set(grp.values())); gi = {g: [r for r in task if grp[r] == g] for g in G}
        rng = np.random.default_rng(0); B = [rng.choice(len(G), len(G)) for _ in range(2000)]
        sF = {r: F[r]["outcome"] == "SUCCESS" for r in task}
        res[dom] = {}
        for arm in arms:
            A = load(d, arm, dom)
            if A is None:
                continue
            sA = {r: A[r]["outcome"] == "SUCCESS" for r in task}
            k0 = [r for r, x in A.items() if x["masks"]["eval_noop"]]; nn = [r for r, x in A.items() if x["masks"]["eval_abstain"]]
            g = sum(sA[r] and not sF[r] for r in task); l = sum(sF[r] and not sA[r] for r in task)
            diff = []
            for b in B:
                rr = [r for j in b for r in gi[G[j]]]
                diff.append(100 * (np.mean([sA[r] for r in rr]) - np.mean([sF[r] for r in rr])))
            res[dom][arm] = {"task": 100 * np.mean([sA[r] for r in task]), "n_task": len(task),
                             "task_by_K": {k: 100 * np.mean([sA[r] for r in task if A[r]["K"] == k]) for k in ("1", "2", "3")},
                             "noop": 100 * np.mean([A[r]["outcome"] == "NOOP" for r in k0]) if k0 else None,
                             "abstain": 100 * np.mean([A[r]["outcome"] == "ABSTAIN" for r in nn]) if nn else None,
                             "outcomes": dict(collections.Counter(x["outcome"] for x in A.values())),
                             "unknown": sum(x["outcome"] == "UNKNOWN" for x in A.values()),
                             "vs_FINAL": {"gain": g, "loss": l, "p_sign": sign(g, l), "diff_pp": 100 * (np.mean([sA[r] for r in task]) - np.mean([sF[r] for r in task])),
                                          "ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]}}
    Path(out).write_text(json.dumps(res, indent=1, default=float))
    for dom in res:
        print("==", dom)
        for arm, v in sorted(res[dom].items(), key=lambda kv: -kv[1]["task"]):
            c = v["vs_FINAL"]
            print(f"{arm:30s} {v['task']:5.1f}  d={c['diff_pp']:+5.1f} [{c['ci95'][0]:+5.1f},{c['ci95'][1]:+5.1f}] g/l {c['gain']}/{c['loss']} p={c['p_sign'] if c['p_sign'] is None else round(c['p_sign'],4)}  noop {v['noop'] and round(v['noop'],1)} abst {v['abstain'] and round(v['abstain'],1)}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
