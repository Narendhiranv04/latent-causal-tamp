#!/usr/bin/env python3
"""Planner-only inference: PUBLIC root rows + a scorer checkpoint -> one decision per root and arm.  No K, label, mask, cache, teacher or
witness is read here (tested).  Arms reuse the completed study's frozen constructors and parameters (full_domain_sets.fsearch, P2_FROZEN_PARAMS).
    python run_eval.py predict PUBLIC.jsonl CKPT OUT.jsonl ARM[@B],...     (B = ordered-evaluation budget; exact arms take none)
    python run_eval.py live PUBLIC.jsonl CKPT OUT.json ARM[@B],... N        (CUDA-synchronized timing, warm-up + median of 3)"""
from __future__ import annotations

import json, os, statistics, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (str(HERE.parent), str(HERE.parent / "full_domain_sets")):
    if p not in sys.path:
        sys.path.insert(0, p)
BUNDLE = Path(os.environ.get("RR_BUNDLE", Path.home() / "abf_v34/approach_b_bundle"))
FP = json.loads((HERE.parent / "full_domain_sets/reports/P2_FROZEN_PARAMS.json").read_text())
RULE = {"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def models(ckpt, device="cuda"):
    import benchmark as BM
    import search as S
    samp, _, man = BM.load_bundle(BUNDLE, "2d", device, 0)                 # frozen sampler (hash-checked); scorer replaced by ckpt
    assert man["config"]["rule"] == RULE
    return samp, S.Scorer(str(ckpt), device=device)


def parse(arms):
    out = []
    for a in arms.split(","):
        name, _, b = a.partition("@")
        out.append((name, int(b) if b else None))
    return out


def decide(row, samp, scor, arms, seed=0, sync=None):
    import domain as DM
    import fsearch as FS
    import search as S
    root = S.Root(row, "2d")
    t0 = time.perf_counter(); raw, D6, _ = DM.cvae_raw(root, samp, 0, 64)
    sync and sync(); t_prior = time.perf_counter() - t0
    doms = {}
    res = []
    for arm, B in arms:
        p = dict(FP.get(arm) or {}); e = p.pop("eps", 0.25)
        for k in (e, 1.0):
            doms.setdefault(k, DM.Domain(raw, D6, k))
        t1 = time.perf_counter()
        x = FS.run_arm(arm, doms[e], lambda q: scor.score(root, q), B, RULE, row["root_id"], seed, root.displacement, p, doms[1.0])
        sync and sync()
        res.append({"arm": arm, "budget": B, "decision": x["decision"], "seq": x["seq"], "p11": x.get("p11"), "scored": x.get("scored"),
                    "pick_stratum": x.get("pick_stratum"), "pick_max_rank": x.get("pick_max_rank"), "wall_s": round(time.perf_counter() - t1, 5)})
    return {"root_id": row["root_id"], "t_prior_s": round(t_prior, 5), "results": res, "proposals": {str(o): v[:4] for o, v in D6.items()}}


def predict(pub, ckpt, out, arms):
    samp, scor = models(ckpt)
    rows = [json.loads(l) for l in open(pub)]
    done = {json.loads(l)["root_id"] for l in open(out)} if Path(out).exists() else set()
    with open(out, "a") as f:
        for r in rows:
            if r["root_id"] not in done:
                f.write(json.dumps(decide(r, samp, scor, parse(arms))) + "\n"); f.flush()


def bench_format(rec, arm, budget, public_row):
    """One sealed benchmark prediction row (benchmark.validate / need / evaluate schema)."""
    x = next(y for y in rec["results"] if y["arm"] == arm and y["budget"] == budget)
    ids = public_row["inputs"]["ids"]
    moves = [{"object_id": ids[o], "object_index": int(o), "destination_cell": int(d)} for o, d in (x["seq"] or [])] if x["decision"] == "REPAIR" else []
    return {"root_id": rec["root_id"], "domain": "2d", "decision": x["decision"], "moves": moves, "score_p11": x["p11"], "arm": arm, "budget": budget}


def live(pub, ckpt, out, arms, n):
    import torch
    samp, scor = models(ckpt)
    rows = [json.loads(l) for l in open(pub)][:int(n)]
    sync = torch.cuda.synchronize; A = parse(arms); rec = []
    for r in rows:
        decide(r, samp, scor, A)                                                # warm-up
        reps = [decide(r, samp, scor, A, sync=sync) for _ in range(3)]
        rec.append({"root_id": r["root_id"], "t_prior_s": statistics.median(x["t_prior_s"] for x in reps),
                    "arms": {f"{a}@{b}": {"wall_s": statistics.median(x["results"][i]["wall_s"] for x in reps), "decision": reps[0]["results"][i]["decision"],
                                          "seq": reps[0]["results"][i]["seq"], "scored": reps[0]["results"][i]["scored"]} for i, (a, b) in enumerate(A)}})
    summ = {}
    for k in rec[0]["arms"]:
        e2e = sorted(x["t_prior_s"] + x["arms"][k]["wall_s"] for x in rec)
        summ[k] = {"median_end_to_end_s": statistics.median(e2e), "p90_s": e2e[int(0.9 * (len(e2e) - 1))], "median_scored": statistics.median(x["arms"][k]["scored"] or 0 for x in rec)}
    Path(out).write_text(json.dumps({"ckpt": str(ckpt), "n": len(rec), "device": torch.cuda.get_device_name(0), "summary": summ, "per_root": rec}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "predict":
        predict(*sys.argv[2:6])
    elif cmd == "live":
        live(*sys.argv[2:7])
