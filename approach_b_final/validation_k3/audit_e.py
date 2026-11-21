#!/usr/bin/env python3
"""Experiment E (teacher-free audit of the remaining ablation arms) from sealed predictions, node dumps and checkpoints.
    python audit_e.py SPLIT DOM   -> $K3V/runs/out/audit_e/{SPLIT}_{DOM}.json"""
import collections, json, sys

import numpy as np
import torch

import vk

PRED = vk.K3A / "runs/predictions"


def P(arm, split, dom):
    return {r["root_id"]: r for r in vk.jl(PRED / arm / f"{split}_{dom}.jsonl")}


def nparams(path, kind):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    return int(sum(v.numel() for v in ck["state"].values()))


def main(split, dom):
    out = {}
    full, uni, m1, c1 = P("FULL_s0", split, dom), P("UNIFORM4_r0", split, dom), P("M1", split, dom), P("C1_r0", split, dom)
    snap = {r["root_id"]: r for r in vk.rows(dom, split)}
    import search as S
    # E2 Uniform4: per-object legality, distinctness, count parity with FULL, candidate counts
    bad, cnt_eq, cnt_tot, nfull, nuni = 0, 0, 0, [], []
    for rid, u in uni.items():
        root = S.Root(snap[rid], dom)
        legal = set(root.legal_dests(root.cells0))
        for o, ds in u["proposals"].items():
            bad += (len(set(ds)) != len(ds)) or any(d not in legal for d in ds) or len(ds) != min(4, len(legal))
            cnt_tot += 1; cnt_eq += len(ds) == len(full[rid]["proposals"].get(o, []))
        assert set(u["proposals"]) == set(full[rid]["proposals"]), rid
        nfull.append(full[rid]["n_scored"]); nuni.append(u["n_scored"])
    out["E2_uniform4"] = {"objects": cnt_tot, "illegal_or_dup_or_wrong_count": bad, "same_count_as_FULL": cnt_eq, "same_object_set_as_FULL": True,
                          "n_scored_mean": {"FULL": float(np.mean(nfull)), "UNIFORM4": float(np.mean(nuni))},
                          "FULL_dest_overlap_across_objects": float(np.mean([1 - len({d for v in f["proposals"].values() for d in v[:4]}) / max(1, sum(len(v[:4]) for v in f["proposals"].values())) for f in full.values()])),
                          "UNIFORM4_dest_overlap_across_objects": float(np.mean([1 - len({d for v in f["proposals"].values() for d in v}) / max(1, sum(len(v) for v in f["proposals"].values())) for f in uni.values()]))}
    # E4 M1: top-1 of the identical frozen proposal ranking (prefix of FULL), same scorer
    pre = sum(all(v == full[rid]["proposals"][o][:1] for o, v in m["proposals"].items()) for rid, m in m1.items())
    out["E4_M1"] = {"roots": len(m1), "proposals_are_FULL_top1_prefix": pre, "scorer_same_as_FULL": len({m["scorer_sha256"] for m in m1.values()} | {f["scorer_sha256"] for f in full.values()}) == 1,
                    "n_scored_mean": float(np.mean([m["n_scored"] for m in m1.values()]))}
    # E5 C1: one label-blind candidate from the FULL M4 pool, one scorer call (+ no-op)
    inpool = 0
    for rid, c in c1.items():
        s = c.get("c1_candidate")
        if s:
            inpool += all(d in full[rid]["proposals"].get(str(o), []) for o, d in s)
    out["E5_C1"] = {"roots": len(c1), "with_candidate": sum(bool(c.get("c1_candidate")) for c in c1.values()), "candidate_in_FULL_pool": inpool,
                    "n_scored": dict(collections.Counter(c["n_scored"] for c in c1.values())), "scorer_evals": dict(collections.Counter(c["scorer_evals"] for c in c1.values())),
                    "decisions": dict(collections.Counter(c["decision"] for c in c1.values()))}
    # E3 TaskFM: parameters, sampling budget, quantization support, latency vs FULL
    fm = P("TASKFM_s0", split, dom)
    out["E3_taskfm"] = {"params_taskfm": nparams(vk.K3A / "runs/training/taskfm" / dom / "taskfm_s0" / "model.pt", "fm"), "params_cvae": nparams(vk.BUNDLE / dom / "sampler.pt", "cvae"),
                        "sampler_evals_per_root_mean": {"TASKFM": float(np.mean([r["sampler_evals"] for r in fm.values()])), "FULL": float(np.mean([r["sampler_evals"] for r in full.values()]))},
                        "contexts_hist_support_lt_M": int(sum(r.get("hist_support_lt_M", 0) for r in fm.values())),
                        "proposal_latency_s_mean": {"TASKFM": float(np.mean([r["timing_s"]["proposal"] for r in fm.values()])), "FULL": float(np.mean([r["timing_s"]["proposal"] for r in full.values()]))},
                        "training": json.loads((vk.K3A / "runs/training/taskfm" / dom / "taskfm_s0" / "curve.json").read_text())["steps"]}
    # E1 G: permutation invariance on labeled nodes (a and p11 identical within an endpoint), Y shared
    X = [r for r in vk.jl(vk.OUT / "nodes" / f"{dom}_{split}_G_s0.jsonl") if r["node"] == "X"]
    g = collections.defaultdict(list)
    for r in X:
        g[(r["root"], r["s"])].append((r["a"], r["b"]))
    out["E1_G"] = {"multi_order_endpoints": sum(len(v) > 1 for v in g.values()),
                   "max_within_endpoint_range_a": float(max((max(a for a, _ in v) - min(a for a, _ in v)) for v in g.values() if len(v) > 1)),
                   "max_within_endpoint_range_b": float(max((max(b for _, b in v) - min(b for _, b in v)) for v in g.values() if len(v) > 1))}
    vk.wjson(vk.OUT / "audit_e" / f"{split}_{dom}.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
