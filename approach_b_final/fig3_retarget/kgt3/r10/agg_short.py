#!/usr/bin/env python3
"""R10.8 short-horizon aggregation from raw per-root verification results (verify.py evaluate output) -> registry cells + paired statistics.
Metrics per (domain, track in TEST_SHORT / BENCH_SHORT / UNION, arm):
  task_itt   K1-K3 roots (eval_task mask): SUCCESS / all eligible (UNKNOWN = not verified)      [primary]
  task_known same with UNKNOWN removed from the denominator                                     [sensitivity]
  noop       K0 roots (eval_noop): NOOP / eligible;  abstain  NONE roots (eval_abstain): ABSTAIN / eligible
  K1 / K2 / K3 / K12 task, attempted-repair outcomes (SUCCESS / FAIL_X / FAIL_Y / UNKNOWN), executed lengths
Paired vs FINAL on task_itt: exact two-sided sign test over discordant roots; 95% CI of the difference by cluster bootstrap over template families
(original split unit; physical family when no template), 2,000 resamples, seed 0; Holm within the predeclared family per domain and track.
    python3 agg_short.py K3EVAL_DIR ARMS_JSON OUT.json"""
import collections, hashlib, json, math, sys
from pathlib import Path

import numpy as np

FAMILIES = {"ablation": ["B0", "UNCOUPLED", "ORDINV", "DIRECT", "UNIFORM4", "TASKFM", "NOTASK", "M1", "C1"], "yonly": ["YONLY", "YONLY_CAL"],
            "generative": ["CR", "CRXY", "FC4"], "representation": ["REP_A1", "REP_M1", "REP_G0"], "seeds": ["FINAL_X0", "FINAL_X1", "FINAL_X2", "SEED0", "SEED1", "SEED2"],
            "baselines": ["BL_em4m", "BL_mosegman", "BL_msmcts", "BL_disco_s0", "BL_disco_s1", "BL_disco_s2", "BL_nor", "BL_reap"]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sign_p(w, l):
    n = w + l
    if n == 0:
        return 1.0
    k = min(w, l)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def boot_diff(clusters, n=2000, seed=0):
    """clusters: [(cluster, [(a, b)])] -> 95% CI (pp) of mean(b) - mean(a) resampling clusters."""
    g = np.random.default_rng(seed)
    keys = list(range(len(clusters)))
    arr = [np.array(v, float) for _, v in clusters]
    def est(ix):
        s = np.concatenate([arr[i] for i in ix]); return 100 * (s[:, 1].mean() - s[:, 0].mean())
    bs = [est(g.integers(0, len(keys), len(keys))) for _ in range(n)]
    return [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]


def metrics(rows):
    out = {}
    T = [r for r in rows if r["masks"].get("eval_task")]
    out["task_itt"] = [sum(r["outcome"] == "SUCCESS" for r in T), len(T)]
    Tk = [r for r in T if r["outcome"] != "UNKNOWN"]
    out["task_known"] = [sum(r["outcome"] == "SUCCESS" for r in Tk), len(Tk)]
    for K in ("1", "2", "3"):
        TK = [r for r in T if str(r["K"]) == K]
        out[f"task_K{K}"] = [sum(r["outcome"] == "SUCCESS" for r in TK), len(TK)]
    T12 = [r for r in T if str(r["K"]) in ("1", "2")]
    out["task_K12"] = [sum(r["outcome"] == "SUCCESS" for r in T12), len(T12)]
    N = [r for r in rows if r["masks"].get("eval_noop")]
    out["noop"] = [sum(r["outcome"] == "NOOP" for r in N), len(N)]
    A = [r for r in rows if r["masks"].get("eval_abstain")]
    out["abstain"] = [sum(r["outcome"] == "ABSTAIN" for r in A), len(A)]
    att = [r for r in rows if r["decision"] == "REPAIR"]
    out["attempted"] = dict(collections.Counter(r["outcome"] for r in att)) | {"n": len(att)}
    out["exec_len"] = dict(collections.Counter(str(len(r["seq"] or [])) for r in rows if r["outcome"] == "SUCCESS"))
    out["unknown"] = sum(r["outcome"] == "UNKNOWN" for r in rows)
    out["outcomes"] = dict(collections.Counter(r["outcome"] for r in rows))
    return out


def main(k3, arms_json, out):
    k3 = Path(k3); arms = json.loads(Path(arms_json).read_text())
    ver = k3 / "runs/verification/r10u"
    reg, stats = [], {}
    for dom, alist in arms.items():
        P = {json.loads(l)["root_id"]: json.loads(l) for l in open(k3 / f"runs/public/private_r10u_{dom}.jsonl")}
        res = {}
        for a in alist:
            f = ver / f"results_{a}_{dom}.jsonl"
            if f.exists():
                res[a] = {json.loads(l)["root_id"]: json.loads(l) for l in open(f)}
                assert set(res[a]) == set(P), (a, dom, "denominator differs from the roster")
        for track in ("TEST_SHORT", "BENCH_SHORT", "UNION"):
            ids = [r for r in P if track == "UNION" or P[r]["r10_track"] == track]
            for a, R in res.items():
                m = metrics([R[i] for i in ids])
                fs = ver / f"results_{a}_{dom}.jsonl"
                files = k3 / "runs/predictions" / a / f"files_{dom}.json"
                reg.append({"release": "LEGOLAS_FINAL_v1", "domain": dom, "track": track, "arm": a, "roster": "r10u", "n_roots": len(ids),
                            "roster_private_sha256": sha(k3 / f"runs/public/private_r10u_{dom}.jsonl"), "results_file": str(fs), "results_sha256": sha(fs),
                            "model_files": json.loads(files.read_text()) if files.exists() else None, "metrics": m})
            if "FINAL" not in res:
                continue
            for fam, members in FAMILIES.items():
                rows, ps = [], []
                for a in members:
                    if a not in res:
                        continue
                    T = [i for i in ids if P[i]["masks"].get("eval_task")]
                    pairs = [(float(res["FINAL"][i]["outcome"] == "SUCCESS"), float(res[a][i]["outcome"] == "SUCCESS")) for i in T]
                    w = sum(1 for x, y in pairs if y > x); l = sum(1 for x, y in pairs if y < x)
                    cl = collections.defaultdict(list)
                    for i, pr in zip(T, pairs):
                        cl[P[i].get("r10_template") or P[i]["r10_family"]].append(pr)
                    d = 100 * (np.mean([y for _, y in pairs]) - np.mean([x for x, _ in pairs])) if pairs else None
                    rows.append({"arm": a, "n": len(pairs), "delta_pp": None if d is None else round(float(d), 2), "ci95": boot_diff(list(cl.items())) if pairs else None,
                                 "wins_vs_final": w, "losses_vs_final": l, "p_sign": sign_p(w, l), "clusters": len(cl)})
                    ps.append(rows[-1]["p_sign"])
                for r, p in zip(rows, holm(ps)):
                    r["p_holm"] = p
                stats[f"{dom}|{track}|{fam}"] = rows
    Path(out).write_text(json.dumps({"registry": reg, "paired_vs_final": stats}, indent=1))
    print(json.dumps({"cells": len(reg), "families": len(stats)}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
