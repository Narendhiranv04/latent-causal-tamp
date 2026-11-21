#!/usr/bin/env python3
"""P0: source and result audit of the completed K<=3 ablation (read-only).  Re-derives the pooled paired physical table from the sealed
result files, checks seals / checkpoint pins / candidate pools / cluster ids, per-seed and per-K stability, and the teacher status behind
every physical failure of the selected repairs.     python p0_audit.py   -> $K3V/runs/out/p0/P0_AUDIT.json"""
import collections, json, re

import numpy as np

import vk

ARMS = {"E": ("E_s{}", "FULL_s{}", 3), "G": ("G_s{}", "FULL_s{}", 3), "DIRECT": ("DIRECT_s{}", "FULL_s{}", 3), "DREFIT": ("DREFIT_s{}", "FULL_s{}", 3),
        "UNIFORM4": ("UNIFORM4_r{}", "FULL_s0", 3), "TASKFM": ("TASKFM_s{}", "FULL_s0", 3), "NOTASK": ("NOTASK_s{}", "FULL_s0", 3), "M1": ("M1", "FULL_s0", 1),
        "C1": ("C1_r{}", "FULL_s0", 3)}
VER, PRED = vk.K3A / "runs/verification", vk.K3A / "runs/predictions"


def res(split, arm, dom):
    return {x["root_id"]: x for x in vk.jl(VER / split / f"results_{arm}_{dom}.jsonl")}


def task(x):
    return None if not x["masks"].get("eval_task") or x["outcome"] == "UNKNOWN" else float(x["outcome"] == "SUCCESS")


def pooled(split, dom, fam, lin):
    a, ref, n = ARMS[fam]
    per, perK, seeds = collections.defaultdict(list), {}, {}
    for k in range(n):
        A, R = res(split, a.format(k), dom), res(split, ref.format(k), dom)
        d = {rid: task(x) - task(R[rid]) for rid, x in A.items() if task(x) is not None and rid in R and task(R[rid]) is not None}
        seeds[a.format(k)] = {"n": len(d), "diff": round(100 * float(np.mean(list(d.values()))), 2)}
        for rid, v in d.items():
            per[rid].append(v); perK[rid] = A[rid]["K"]
    rids = sorted(per)
    v = [float(np.mean(per[r])) for r in rids]
    grp_res = [res(split, ref.format(0), dom)[r]["group"] for r in rids]
    out = {"n_roots": len(rids), "pooled_group_results": vk.cluster_boot(v, grp_res), "pooled_layout_root_id": vk.cluster_boot(v, [lin[r] for r in rids]),
           "pooled_root_iid": vk.cluster_boot(v, rids), "per_seed": seeds}
    out["by_K"] = {K: vk.cluster_boot([x for x, r in zip(v, rids) if perK[r] == K], [lin[r] for r in rids if perK[r] == K]) for K in ("1", "2", "3")}
    return out


def main():
    A = {"seals": {}, "pins": {}, "groups": {}, "pooled": {}, "fail_status": {}, "pool_hash": {}}
    for f in sorted(PRED.glob("*/*.jsonl")):                                   # seals
        s = f.with_name(f.name + ".SEAL.json")
        if s.exists():
            A["seals"][f"{f.parent.name}/{f.name}"] = json.loads(s.read_text())["sha256"] == vk.sha(f)
    A["seals_all_ok"] = all(A["seals"].values()); A["n_sealed"] = len(A["seals"])
    proto = (vk.HERE.parent / "config/final_protocol.yaml").read_text()          # frozen checkpoint pins
    for dom in ("2d", "3d"):
        for s in (0, 1, 2):
            h = vk.sha(vk.ckpt(f"FULL_s{s}", dom))
            A["pins"][f"{dom}_scorer_s{s}"] = h in proto
        A["pins"][f"{dom}_sampler"] = vk.sha(vk.BUNDLE / dom / "sampler.pt") in proto
    for split in ("val", "test"):
        for dom in ("2d", "3d"):
            lin = vk.lineage(dom, split)
            R = res(split, "FULL_s0", dom)
            same = sum(R[r]["group"] == lin[r] for r in R)
            A["groups"][f"{split}_{dom}"] = {"roots": len(R), "group_eq_layout_root_id": same, "n_groups": len({x["group"] for x in R.values()}),
                                             "n_layout_root_ids": len({lin[r] for r in R}), "group_eq_root_id": sum(R[r]["group"] == r for r in R)}
            for fam in ARMS:
                A["pooled"][f"{fam}|{split}|{dom}"] = pooled(split, dom, fam, lin)
            pools = {}                                                           # identical candidate pools for scorer arms
            for arm in ("FULL_s0", "E_s0", "G_s0", "DIRECT_s0", "DREFIT_s0", "M1", "C1_r0"):
                pools[arm] = {r["root_id"]: r["pool_hash"] for r in vk.jl(PRED / arm / f"{split}_{dom}.jsonl")}
            A["pool_hash"][f"{split}_{dom}"] = {a: sum(pools[a][r] == pools["FULL_s0"][r] for r in pools["FULL_s0"]) for a in pools}
            cache = {}                                                           # teacher status behind selected-repair failures
            for l in open(vk.K3A / "runs/verifier_cache" / f"verify_{dom}.jsonl"):
                v = json.loads(l)
                for x in v["results"]:
                    cache[(v["root"], json.dumps(x["seq"]))] = ((x["x"] or {}).get("status"), (x["y"] or {}).get("status"))
            for arm in ("FULL_s0", "E_s0", "G_s0", "DIRECT_s0", "UNIFORM4_r0", "TASKFM_s0", "M1", "C1_r0"):
                C = collections.Counter()
                for x in res(split, arm, dom).values():
                    if x["decision"] == "REPAIR" and x["outcome"] in ("FAIL_X", "FAIL_Y"):
                        xs, ys = cache.get((x["root_id"], json.dumps(x["seq"])), (None, None))
                        C[f"{x['outcome']}:{ys if x['outcome'] == 'FAIL_Y' else xs}"] += 1
                A["fail_status"][f"{arm}|{split}|{dom}"] = dict(C.most_common())
    rep = json.loads((vk.HERE.parent / "ablations_k3/reports/tables/pooled_paired_task.json").read_text()) if (vk.HERE.parent / "ablations_k3/reports/tables/pooled_paired_task.json").exists() else None
    A["reported_pooled"] = rep
    vk.wjson(vk.OUT / "p0/P0_AUDIT.json", A)
    print(json.dumps({k: A[k] for k in ("seals_all_ok", "n_sealed", "pins", "groups", "pool_hash")}, indent=1))
    for k, v in A["pooled"].items():
        print(k, "grp", v["pooled_group_results"], "lin", v["pooled_layout_root_id"], "iid", v["pooled_root_iid"], {s: x["diff"] for s, x in v["per_seed"].items()}, "K", v["by_K"])
    for k, v in A["fail_status"].items():
        print(k, v)


if __name__ == "__main__":
    main()
