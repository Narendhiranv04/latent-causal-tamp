#!/usr/bin/env python3
"""V3.2 exhaustive top-M feasibility audit (read-only; no training, no teachers, no test outcomes).

    propose   frozen V3 task cVAE (q2init_all, S1 = top-M of the 64-draw MC marginal, V3 per-root CUDA generator seeding) -> deterministic
              top-6 destinations per eligible movable object, TRAIN + VALIDATION, seeds 0-2 (top-4 / top-5 are prefixes: same draws)
    count     exact K1 / K2 / K3 ordered-sequence counts (all permutations, pairwise-distinct destinations, inclusion-exclusion; nothing
              materialized, no B cap) for M = 4, 5, 6 + known-assignment ingredient recall from existing labels; CPU pool
    bench     scorer throughput of the frozen V3 D on the local GPU (inference only) for the feasibility estimate
Environment: ABF_ROOT, V3OUT (frozen copies), V3_TASK_STAGE=v3_3."""
from __future__ import annotations

import collections, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ABF, V3 = Path(os.environ["ABF_ROOT"]), Path(os.environ["V3OUT"])
OUT = V3 / "v32"
SNAP = ABF / "snapshot/abf_v3_e8a496bc66266fca"          # V3 snapshot: base + V2 + V3-4 labels on TRAIN; validation rows = base
MS = (4, 5, 6)


def rows_of(dom, split):
    return [r for r in map(json.loads, open(SNAP / f"data{dom}.jsonl")) if r["split"] == split]


def propose():
    import torch
    import construct as CO
    import search as S
    OUT.mkdir(parents=True, exist_ok=True)
    for dom in ("2d", "3d"):
        for seed in (0, 1, 2):
            samp = CO.make_sampler(dom, "task:q2init_all", seed, CO.RULES["S1"])
            fo = OUT / f"proposals_{dom}_s{seed}.jsonl"
            t0 = time.time()
            with open(fo, "w") as f:
                for split in ("train", "val"):
                    for r in rows_of(dom, split):
                        root = S.Root(r, dom)
                        gen = torch.Generator(device=samp.dev).manual_seed(seed)       # = construct.run_root (one generator per root)
                        D = samp.propose_many(root, root.cells0, list(root.movable), 6, gen) if root.movable else {}
                        f.write(json.dumps({"root_id": r["root_id"], "split": split, "K": r["K_legacy"], "n_movable": len(root.movable),
                                            "n_free_legal": len(root.legal_dests(root.cells0)), "D6": {str(o): [int(d) for d in v] for o, v in D.items()}}) + "\n")
            print(json.dumps({"dom": dom, "seed": seed, "out": str(fo), "s": round(time.time() - t0, 1)}), flush=True)


def parity():
    """M = 4 prefix of the laptop top-6 vs the proposal sets recorded by V3.1 on gvlab (validation, seed 0)."""
    res = {}
    for dom in ("2d", "3d"):
        ref = {r["root_id"]: r for r in map(json.loads, open(V3.parent / "parity" / f"v3_M4_B128_val_{dom}.jsonl"))}
        same = n = 0
        for p in map(json.loads, open(OUT / f"proposals_{dom}_s0.jsonl")):
            if p["root_id"] in ref:
                n += 1
                mine = sorted([int(o), d] for o, v in p["D6"].items() for d in v[:4])
                same += mine == sorted(ref[p["root_id"]]["proposal_actions"])
        res[dom] = {"roots": n, "identical_M4_proposal_sets": same}
    (OUT / "PARITY_M4.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


_ROWS = {}


def _init(dom):
    _ROWS.clear()
    for split in ("train", "val"):
        for r in rows_of(dom, split):
            _ROWS[r["root_id"]] = r


def _count_one(p):
    import construct as CO
    import contracts as CT
    row = _ROWS[p["root_id"]]
    pa = [A["assignment"] for A in CT.positive_assignments(row).values()] if row["masks"]["eval_task"] or row["split"] == "train" else []
    out = {"root_id": p["root_id"], "split": p["split"], "K": p["K"], "n_movable": p["n_movable"], "n_free_legal": p["n_free_legal"]}
    for M in MS:
        D = {int(o): v[:M] for o, v in p["D6"].items()}
        acts = {(o, d) for o, v in D.items() for d in v}
        n = CO.counts(D)
        out[f"M{M}"] = {"K1": n[0], "K2": n[1], "K3": n[2], "total": sum(n), "unique_actions": len(acts),
                        "recall": (any(all(tuple(a) in acts for a in A) for A in pa) if pa else None)}
    return out


def count(workers=27):
    import multiprocessing as mp
    import numpy as np
    summary = {}
    for dom in ("2d", "3d"):
        for seed in (0, 1, 2):
            props = [json.loads(l) for l in open(OUT / f"proposals_{dom}_s{seed}.jsonl")]
            t0 = time.time()
            with mp.get_context("fork").Pool(workers, initializer=_init, initargs=(dom,)) as pool:
                res = pool.map(_count_one, props, chunksize=16)
            with open(OUT / f"counts_{dom}_s{seed}.jsonl", "w") as f:
                for r in res:
                    f.write(json.dumps(r) + "\n")
            for split in ("train", "val"):
                rs = [r for r in res if r["split"] == split]
                key = f"{dom}|{split}|s{seed}"
                S = {"roots": len(rs), "n_movable": {q: float(np.percentile([r["n_movable"] for r in rs], q)) for q in (50, 90, 99, 100)},
                     "wall_s": round(time.time() - t0, 1)}
                for M in MS:
                    st = {}
                    for k in ("K1", "K2", "K3", "total", "unique_actions"):
                        v = np.array([r[f"M{M}"][k] for r in rs], float)
                        st[k] = {"median": float(np.median(v)), "p90": float(np.percentile(v, 90)), "p99": float(np.percentile(v, 99)),
                                 "max": float(v.max()), "total": float(v.sum())}
                    tot = np.array([r[f"M{M}"]["total"] for r in rs], float)
                    st["share_roots_over_4096"] = float((tot > 4096).mean())
                    st["share_roots_over_65536"] = float((tot > 65536).mean())
                    rec = [r for r in rs if r[f"M{M}"]["recall"] is not None and r["K"] in ("1", "2", "3")]
                    st["recall"] = {"all": float(np.mean([r[f"M{M}"]["recall"] for r in rec])) if rec else None, "n": len(rec),
                                    **{f"K{K}": float(np.mean([r[f"M{M}"]["recall"] for r in rec if r["K"] == K])) for K in "123" if any(r["K"] == K for r in rec)}}
                    S[f"M{M}"] = st
                summary[key] = S
                print(key, json.dumps({f"M{M}": {"total_median": S[f"M{M}"]["total"]["median"], "p99": S[f"M{M}"]["total"]["p99"],
                                                 "max": S[f"M{M}"]["total"]["max"], "recall": S[f"M{M}"]["recall"]["all"]} for M in MS}), flush=True)
    (OUT / "COUNT_SUMMARY.json").write_text(json.dumps(summary, indent=1))


def bench(n_roots=6, per_root=20000):
    """Scorer throughput (frozen V3 D s0, local GPU, inference only): construct + score up to per_root ordered sequences for the largest
    validation roots (M = 6 proposal sets); chunked exactly as construct.run_root (8,192)."""
    import random
    import torch
    import construct as CO
    import search as S
    res = {}
    for dom in ("2d", "3d"):
        sc = S.Scorer(V3 / "v3_5" / f"p2_{dom}" / "D_s0" / "model.pt", None, device="cuda")
        cnt = {r["root_id"]: r for r in map(json.loads, open(OUT / f"counts_{dom}_s0.jsonl")) if r["split"] == "val"}
        props = {p["root_id"]: p for p in map(json.loads, open(OUT / f"proposals_{dom}_s0.jsonl")) if p["split"] == "val"}
        rows = {r["root_id"]: r for r in rows_of(dom, "val")}
        big = sorted(cnt, key=lambda k: -cnt[k]["M6"]["total"])[:n_roots]
        rates, build_rates, peak = [], [], 0
        for rid in big:
            D = {int(o): v for o, v in props[rid]["D6"].items()}
            t0 = time.time()
            seqs = []
            for k in (1, 2, 3):
                for a in CO.assignments(D, k):
                    for perm in __import__("itertools").permutations(a):
                        seqs.append(list(perm))
                        if len(seqs) >= 4 * per_root:
                            break
                    if len(seqs) >= 4 * per_root:
                        break
            build_rates.append(len(seqs) / max(time.time() - t0, 1e-9))
            seqs = random.Random(0).sample(seqs, min(per_root, len(seqs)))
            root = S.Root(rows[rid], dom)
            torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize(); t0 = time.time()
            for i in range(0, len(seqs), 8192):
                sc.score(root, seqs[i:i + 8192])
            torch.cuda.synchronize()
            rates.append(len(seqs) / (time.time() - t0)); peak = max(peak, torch.cuda.max_memory_allocated() / 2 ** 20)
        res[dom] = {"roots": big, "score_seq_per_s_median": float(sorted(rates)[len(rates) // 2]), "score_seq_per_s_all": rates,
                    "build_seq_per_s_median": float(sorted(build_rates)[len(build_rates) // 2]), "gpu_peak_mib_chunk8192": round(peak, 1),
                    "device": torch.cuda.get_device_name(0)}
        print(dom, json.dumps({k: v for k, v in res[dom].items() if k != "roots"}), flush=True)
    (OUT / "BENCH.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "propose":
        propose()
    elif c == "parity":
        parity()
    elif c == "count":
        count(int(sys.argv[2]) if len(sys.argv) > 2 else 27)
    elif c == "bench":
        bench()
    else:
        raise SystemExit(__doc__)
