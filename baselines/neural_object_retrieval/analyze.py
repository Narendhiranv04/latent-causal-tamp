#!/usr/bin/env python3
"""NOR-Grid P5 analysis: per-variant metrics (benchmark.summarize), seed average, and PAIRED root-level contrasts with a stratified
evaluation-group (layout lineage) bootstrap (2000 resamples, seed 0): NOR primary vs Approach B (full VALIDATION) and each ablation vs the
primary on the registered VALSUB roots.  Task = verified X=1 & Y=1 on K1-K3 roots; UNKNOWN never counts as failure (excluded pairwise).

    analyze.py OUT_JSON"""
import collections, json, sys
from pathlib import Path

import numpy as np

E = Path.home() / "sorc_grid/eval"
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parents[1] / "approach_b_final"))
import benchmark as BM  # noqa: E402


def res(path):
    return {r["root_id"]: r for r in map(json.loads, open(path))} if Path(path).exists() else None


def task_vals(R, roots=None):
    out = {}
    for k, r in R.items():
        if (roots is None or k in roots) and r["masks"].get("eval_task") and r["outcome"] != "UNKNOWN" and not r["outcome"].startswith("MISSING"):
            out[k] = float(r["outcome"] == "SUCCESS")
    return out


def paired(A, B, ref, n=2000, seed=0):
    """mean(A - B) over shared task roots; bootstrap = resample layout groups within K strata."""
    keys = sorted(set(A) & set(B))
    if not keys:
        return None
    strata = collections.defaultdict(lambda: collections.defaultdict(list))
    for k in keys:
        strata[ref[k]["K"]][ref[k]["group"]].append(A[k] - B[k])
    G = {s: list(g.values()) for s, g in strata.items()}
    pt = float(np.mean([A[k] - B[k] for k in keys]))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        v = []
        for s, gs in G.items():
            for i in rng.integers(0, len(gs), len(gs)):
                v += gs[i]
        bs.append(np.mean(v))
    return {"n": len(keys), "diff_pp": round(100 * pt, 2), "ci95": [round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)]}


def main(out):
    P = E / "pred"
    report = {"summaries": {}, "paired": {}, "seed_mean": {}}
    files = sorted(P.glob("*_results.jsonl")) + sorted((E / "comparators").glob("*_results.jsonl"))
    S = BM.summarize(None, str(Path(out).with_suffix(".summaries.json")), [str(f) for f in files])
    report["summaries"] = S
    for d in ("2d", "3d"):
        prim = res(P / f"{d}_full_s0_full_results.jsonl")
        ab = res(E / "comparators" / f"{d}_approachB_final_results.jsonl")
        sub = {json.loads(l)["root_id"] for l in open(E / f"private_valsub_{d}.jsonl")}
        seeds = [res(P / f"{d}_full_s{s}_full_results.jsonl") for s in (0, 1, 2)]
        if all(seeds):
            per = {}
            for k in prim:
                v = [task_vals(s).get(k) for s in seeds]
                if all(x is not None for x in v):
                    per[k] = float(np.mean(v))
            report["seed_mean"][d] = {"task_pp": round(100 * float(np.mean(list(per.values()))), 2), "n": len(per),
                                      "per_seed_task_pp": [round(100 * float(np.mean(list(task_vals(s).values()))), 2) for s in seeds]}
            report["paired"][f"{d}: NOR seed-mean - ApproachB"] = paired(per, task_vals(ab), prim)
        report["paired"][f"{d}: NOR s0 - ApproachB"] = paired(task_vals(prim), task_vals(ab), prim)
        for v in ("full_s0_osnet_only", "full_s0_rpnet_only", "full_s0_both_analytic", "nogoal_s0_full", "full_s0_no_stop"):
            a = res(P / f"{d}_{v}__valsub_results.jsonl")
            if a:
                report["paired"][f"{d}: {v} - NOR s0 (VALSUB)"] = paired(task_vals(a), task_vals(prim, sub), prim)
    Path(out).write_text(json.dumps(report, indent=1))
    for k, v in report["paired"].items():
        print(k.ljust(48), v)
    print(json.dumps(report["seed_mean"]))


if __name__ == "__main__":
    main(sys.argv[1])
