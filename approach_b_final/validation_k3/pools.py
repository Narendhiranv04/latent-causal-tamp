#!/usr/bin/env python3
"""Teacher-free pool diagnostics from the multipass records (B1, D ranking, A5 ranking; frozen labels only for known successes).
    python pools.py SPLIT DOM   -> $K3V/runs/out/pools/{SPLIT}_{DOM}.json
Per scorer: p_noop by root class (K0 / K1-3 / NONE), p_best (argmax repair) by class, registered-rule decision mix by class, and the rank of the
best KNOWN successful sequence (snapshot X = 1, Y = 1 labels; counted strictly-higher + ties, i.e. pessimistic rank) among all M4 candidates."""
import collections, json, sys

import numpy as np

import vk
import queries as QU
import rules as RU


def main(split, dom):
    M = QU.mp(split, dom)
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_{split}_{dom}.jsonl")}
    cls = {rid: ("K0" if e["K"] == "0" else "NONE" if e["K"] == "NONE" else "K123") for rid, e in priv.items()}
    nets = sorted(next(iter(M.values()))["p_noop"])
    out = {"p_noop": {}, "p_best": {}, "decisions_registered": {}, "known_rank": {}, "n_cand": {}}
    q = lambda v: [round(float(x), 4) for x in np.percentile(v, [5, 25, 50, 75, 95])] if len(v) else None  # noqa: E731
    for n in nets:
        for c in ("K0", "K123", "NONE"):
            pn = [M[r]["p_noop"][n] for r in M if cls[r] == c]
            pb = [M[r]["variants"][f"{n}:p11"]["p"] for r in M if cls[r] == c and f"{n}:p11" in M[r]["variants"]]
            out["p_noop"][f"{n}|{c}"] = {"n": len(pn), "mean": float(np.mean(pn)), "q05_25_50_75_95": q(pn), "frac_ge_0.5": float(np.mean(np.array(pn) >= 0.5))}
            out["p_best"][f"{n}|{c}"] = {"n": len(pb), "mean": float(np.mean(pb)) if pb else None, "q05_25_50_75_95": q(pb), "frac_ge_0.3": float(np.mean(np.array(pb) >= 0.3)) if pb else None}
            D = collections.Counter("ABSTAIN" if (d := RU.decide(M[r], f"{n}:p11", *RU.REG)) is None else "NOOP" if d == [] else "REPAIR" for r in M if cls[r] == c)
            out["decisions_registered"][f"{n}|{c}"] = dict(D)
    for vn in sorted({v for r in M.values() for v in r["variants"]}):
        ranks = []
        for r in M.values():
            k = r["variants"].get(vn, {}).get("known")
            if k and cls[r["root_id"]] == "K123":
                ranks.append(1 + k["n_higher"] + max(0, k["n_equal"]))
        ranks = np.array(ranks)
        out["known_rank"][vn] = {"roots": len(ranks), "hit@1": float((ranks <= 1).mean()) if len(ranks) else None, "hit@10": float((ranks <= 10).mean()) if len(ranks) else None,
                                 "hit@100": float((ranks <= 100).mean()) if len(ranks) else None, "median_rank": float(np.median(ranks)) if len(ranks) else None}
    nc = [r["n_cand"] for r in M.values()]
    out["n_cand"] = {"mean": float(np.mean(nc)), "q05_25_50_75_95": q(nc)}
    out["w_pool_FULL_s0"] = {"w_mean": float(np.mean([r["w_pool_FULL_s0"]["w_mean"] for r in M.values() if r["n_cand"]])),
                             "absdp_mean": float(np.mean([r["w_pool_FULL_s0"]["absdp_mean"] for r in M.values() if r["n_cand"]]))}
    vk.wjson(vk.OUT / "pools" / f"{split}_{dom}.json", out)
    for k in ("p_noop", "p_best", "decisions_registered"):
        for kk, v in out[k].items():
            if kk.split("|")[0] in ("FULL_s0", "E_s0", "DIRECT_s0"):
                print(k, kk, v)
    for kk, v in out["known_rank"].items():
        if kk.startswith(("FULL_s0", "E_s0", "DIRECT_s0")):
            print("rank", kk, v)
    print(out["n_cand"], out["w_pool_FULL_s0"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
