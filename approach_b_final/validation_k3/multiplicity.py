#!/usr/bin/env python3
"""Bonferroni-adjusted (36 registered arm x split x domain cells; two-sided alpha 0.05/36 -> 99.86 %) intervals for the pooled paired
task-success differences of the completed ablation (same per-root seed-mean differences and layout-cluster resampling as p0_audit).
    python multiplicity.py   -> $K3V/runs/out/p0/MULTIPLICITY.json"""
import json

import numpy as np

import vk
import p0_audit as P0

A = 0.05 / 36


def main():
    out = {}
    for fam in P0.ARMS:
        for split in ("val", "test"):
            for dom in ("2d", "3d"):
                a, ref, n = P0.ARMS[fam]
                per = {}
                for k in range(n):
                    R0, R1 = P0.res(split, a.format(k), dom), P0.res(split, ref.format(k), dom)
                    for rid, x in R0.items():
                        t0, t1 = P0.task(x), P0.task(R1[rid]) if rid in R1 else None
                        if t0 is not None and t1 is not None:
                            per.setdefault(rid, []).append(t0 - t1)
                rids = sorted(per)
                v = np.array([np.mean(per[r]) for r in rids])
                rng = np.random.default_rng(0)
                bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(20000)]
                out[f"{fam}|{split}|{dom}"] = {"diff": round(100 * v.mean(), 2), "ci95": [round(100 * np.percentile(bs, q), 2) for q in (2.5, 97.5)],
                                              "ci_bonf": [round(100 * np.percentile(bs, q), 2) for q in (100 * A / 2, 100 - 100 * A / 2)]}
    vk.wjson(vk.OUT / "p0/MULTIPLICITY.json", out)
    for k, v in out.items():
        print(k, v["diff"], v["ci95"], v["ci_bonf"], "EXCLUDES0" if v["ci_bonf"][1] < 0 or v["ci_bonf"][0] > 0 else "")


if __name__ == "__main__":
    main()
