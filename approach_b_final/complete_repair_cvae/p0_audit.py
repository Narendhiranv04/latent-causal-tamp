#!/usr/bin/env python3
"""P0 audit (plan.md 6 P0): provenance, TRAIN/VAL corpus audit, root-label audit, cohort roster (pre-registered, by stable hash), parity roster.

    python p0_audit.py provenance      -> reports/P0_PROVENANCE.json
    python p0_audit.py data            -> reports/P0_DATA.json (+ figures via viz.py p0)
    python p0_audit.py roster          -> $CR_PRIV/cohort_{dom}.jsonl (private: K per root) + reports/P0_COHORT.json (ids, counts, hashes)
    python p0_audit.py parity_ids      -> reports/P0_PARITY_IDS.json (VAL roots by hash per legacy-K stratum; for infer.py parity)

Reads TRAIN/VAL labels (allowed) and the V3.4 PRIVATE_INDEX K / family metadata (roster selection only).  Never reads held-out outcomes."""
from __future__ import annotations

import collections, json, os, platform, subprocess, sys
from pathlib import Path

import data as D

REP = D.HERE / "reports"
SALT = "CRCVAE_COHORT_V1"
V34 = D.H / "abf_v34"
CAP = {"1": 50, "2": 50, "3": 50, "0": 30, "NONE": 30}
FROZEN_SRC = ["contracts.py", "placement.py", "search.py", "xy.py", "construct.py", "exhaustive.py", "benchmark.py", "evaluate.py",
              "scripts/v32b_phys.py", "teacher2d.py"]
TEACHER_SRC = {"3d_fin3d": D.H / "abf_v3_laptop/gen/final3d_v4/code/fin3d.py", "3d_perm3d": D.H / "abf_v3_laptop/gen/final3d_v4/code/perm3d.py",
               "3d_bwlphys": D.H / "abf_v3_laptop/gen/final3d_v4/code/bwlphys.py", "2d_teacher2d_runtime": D.H / "abf_v3_laptop/root/code/teacher2d.py"}


def git(*a):
    return subprocess.run(["git", *a], cwd=D.HERE, capture_output=True, text=True).stdout.strip()


def wj(name, obj):
    REP.mkdir(parents=True, exist_ok=True)
    (REP / name).write_text(json.dumps(obj, indent=1, default=str))


def provenance():
    import torch
    man = json.loads((D.BUNDLE / "MANIFEST.json").read_text())
    files = {n: {"manifest": h, "actual": D.sha(D.BUNDLE / n), "ok": D.sha(D.BUNDLE / n) == h} for n, h in man["files"].items()}
    ck = {d: torch.load(D.BUNDLE / d / "sampler.pt", map_location="cpu", weights_only=False) for d in ("2d", "3d")}
    xy = {d: torch.load(D.BUNDLE / d / "scorer_s0.pt", map_location="cpu", weights_only=False) for d in ("2d", "3d")}
    out = {"head": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
           "base": {"sha": "87ebf65d245dd9368397bf3577c9ff164cff619b", "branch": "naren/rss27-xy-repair-ranking", "remote_verified": True},
           "plan_sha256": D.sha(D.HERE / "plan.md"), "starting_prompt_sha256": D.sha(D.HERE / "starting_prompt.md"),
           "bundle": {"path": str(D.BUNDLE), "manifest_sha256": D.sha(D.BUNDLE / "MANIFEST.json"), "config": man["config"], "files": files,
                      "all_files_ok": all(f["ok"] for f in files.values())},
           "sampler": {d: {"variant": ck[d].get("variant"), "cfg": ck[d]["cfg"], "step": ck[d].get("step"), "prov": ck[d].get("prov"),
                           "tdim": ck[d]["tdim"], "grid": ck[d]["grid"]} for d in ck},
           "scorer_s0": {d: {k: xy[d].get(k) for k in ("arm", "seed", "epoch", "snapshot", "cfg") if k in xy[d]} for d in xy},
           "snapshots": {"train": {"path": str(D.TRAIN_SNAP), **{f"data{d}.jsonl": D.sha(D.TRAIN_SNAP / f"data{d}.jsonl") for d in ("2d", "3d")}},
                         "val": {"path": str(D.VAL_SNAP), **{f"data{d}.jsonl": D.sha(D.VAL_SNAP / f"data{d}.jsonl") for d in ("2d", "3d")}}},
           "frozen_source_sha256": {f: D.sha(D.ABF / f) for f in FROZEN_SRC},
           "teacher_runtime": {"host": platform.node(), "envs": {"2d": str(D.H / "abf_v3_laptop/env2d"), "3d": str(D.H / "abf_v3_laptop/env3d")},
                               "source_sha256": {k: D.sha(p) for k, p in TEACHER_SRC.items() if p.exists()},
                               "missing": [k for k, p in TEACHER_SRC.items() if not p.exists()]},
           "cohort_v34": {"private_index": str(V34 / "final/PRIVATE_INDEX.jsonl"), "sha256": D.sha(V34 / "final/PRIVATE_INDEX.jsonl"),
                          "sealed_predictions": {p: D.sha(V34 / p) for p in ("batchA/pred_2d.jsonl", "batchA/pred_3d.jsonl", "batchB/pred_2d.jsonl", "batchB/pred_3d.jsonl")},
                          "seals": {p: json.loads((V34 / (p + ".SEAL.json")).read_text()) for p in ("batchA/pred_2d.jsonl", "batchA/pred_3d.jsonl", "batchB/pred_2d.jsonl", "batchB/pred_3d.jsonl")}},
           "environment": {"python": sys.executable, "torch": torch.__version__, "cuda": torch.cuda.is_available(),
                           "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "host": platform.node(), "nproc": os.cpu_count()}}
    wj("P0_PROVENANCE.json", out)
    print(json.dumps({"bundle_ok": out["bundle"]["all_files_ok"], "head": out["head"]}))


def layout_fp(row):
    inp = row["inputs"]
    return json.dumps([sorted(int(c) for i, c in enumerate(inp["cells0"]) if i != inp["tid"]), int(inp["cells0"][inp["tid"]]), int(inp["goal_cell"])])


def data_audit():
    rep = {}
    for dom in ("2d", "3d"):
        R = {}
        fps = collections.defaultdict(set)
        for split, snap in (("train", D.TRAIN_SNAP), ("val", D.VAL_SNAP)):
            rr, triples, labels = D.supervision(dom, snap, split)
            for r in rr:
                fps[layout_fp(r)].add(split)
            byK = collections.defaultdict(collections.Counter)
            wsum = collections.defaultdict(float)
            for i, s, w in triples:
                wsum[i] += w
            for i, r in enumerate(rr):
                vo = D.verified_orders(r)
                K = r["K_legacy"]
                c = byK[K]
                c["roots"] += 1
                c["roots_with_repair"] += bool(vo)
                c["assignments"] += len(vo)
                c["orders"] += sum(len(v) for v in vo.values())
                for k, v in vo.items():
                    sz = len(json.loads(v[0]))
                    c[f"assign_size{sz}"] += 1
                    c[f"orders_size{sz}"] += len(v)
                    c[f"assign_size{sz}_orders{len(v)}"] += 1
                c["label_" + ("MASKED" if labels[i] < 0 else D.CLASSES[labels[i]])] += 1
            mins = collections.Counter()
            for i, r in enumerate(rr):
                vo = D.verified_orders(r)
                if r["K_legacy"] in ("1", "2", "3"):
                    m = min((len(json.loads(v[0])) for v in vo.values()), default=None)
                    mins[f"K{r['K_legacy']}|" + ("none" if m is None else "min<K" if m < int(r["K_legacy"]) else "min=K" if m == int(r["K_legacy"]) else "min>K")] += 1
            R[split] = {"roots": len(rr), "triples": len(triples), "raw_x1y1_orders": len(triples),
                        "roots_with_repair": len(wsum), "actions_released_corpus": sum(len(json.loads(v[0])) for r in rr for v in D.verified_orders(r).values()),
                        "root_weight_sum_minmax": [min(wsum.values()), max(wsum.values())] if wsum else None,
                        "by_K": {k: dict(v) for k, v in sorted(byK.items())}, "legacy_K_vs_min_verified": dict(sorted(mins.items())),
                        "labels": {"MASKED" if k < 0 else D.CLASSES[k]: v for k, v in collections.Counter(labels).items()},
                        "families": len({r["parent_family_id"] for r in rr})}
        fam = collections.defaultdict(set)
        for split, snap in (("train", D.TRAIN_SNAP), ("val", D.VAL_SNAP)):
            for r in D.rows(dom, snap, split):
                fam[r["parent_family_id"]].add(split)
        R["split_integrity"] = {"family_in_both": sum(len(v) > 1 for v in fam.values()), "layout_fp_in_both": sum(len(v) > 1 for v in fps.values())}
        R["released_sampler_parity"] = {"released_train_roots": D.json.loads((D.H / f"abf_v33/models/expanded/{dom}/scratch_all_s0/curve.json").read_text())["train_roots"],
                                        "released_train_examples": D.json.loads((D.H / f"abf_v33/models/expanded/{dom}/scratch_all_s0/curve.json").read_text())["train_examples"],
                                        "ours_train_roots": R["train"]["roots_with_repair"], "ours_train_actions": R["train"]["actions_released_corpus"]}
        R["released_sampler_parity"]["equal"] = (R["released_sampler_parity"]["released_train_roots"] == R["train"]["roots_with_repair"] and
                                                 R["released_sampler_parity"]["released_train_examples"] == R["train"]["actions_released_corpus"])
        rep[dom] = R
    wj("P0_DATA.json", rep)
    print(json.dumps({d: {"parity": rep[d]["released_sampler_parity"], "integrity": rep[d]["split_integrity"]} for d in rep}))


def roster():
    """Pre-registered locked-cohort roster: per domain and private stratum, stable hash order sha256(SALT|root) with family coverage first
    (one root per parent family until exhausted), cap CAP[K].  No outcome or prediction is read."""
    P = [json.loads(l) for l in open(V34 / "final/PRIVATE_INDEX.jsonl")]
    pub = {}
    for b in ("batchA", "batchB"):
        for d in ("2d", "3d"):
            for r in map(json.loads, open(V34 / b / f"public_{d}.jsonl")):
                pub[r["root_id"]] = (b, D.sha(V34 / b / f"public_{d}.jsonl"))
    out = {"salt": SALT, "caps": CAP, "source_index_sha256": D.sha(V34 / "final/PRIVATE_INDEX.jsonl"), "domains": {}}
    D.PRIV.mkdir(parents=True, exist_ok=True)
    for dom in ("2d", "3d"):
        sel = []
        for K, cap in CAP.items():
            pool = sorted((e for e in P if e["domain"] == dom and e["K"] == K), key=lambda e: D.stratum_hash(SALT, e["root_id"]))
            seen, first, rest = set(), [], []
            for e in pool:
                (rest if e["parent_family_id"] in seen else first).append(e)
                seen.add(e["parent_family_id"])
            sel += [{**e, "stratum": K, "batch": pub[e["root_id"]][0]} for e in (first + rest)[:cap]]
        assert all(e["root_id"] in pub for e in sel)
        with open(D.PRIV / f"cohort_{dom}.jsonl", "w") as f:
            for e in sorted(sel, key=lambda e: e["root_id"]):
                f.write(json.dumps(e) + "\n")
        c = collections.Counter(e["stratum"] for e in sel)
        out["domains"][dom] = {"n": len(sel), "by_stratum": dict(c), "available": dict(collections.Counter(e["K"] for e in P if e["domain"] == dom)),
                               "families": len({e["parent_family_id"] for e in sel}), "batches": dict(collections.Counter(e["batch"] for e in sel)),
                               "root_ids_sorted": sorted(e["root_id"] for e in sel), "private_file_sha256": D.sha(D.PRIV / f"cohort_{dom}.jsonl")}
    wj("P0_COHORT.json", out)
    print(json.dumps({d: {k: v for k, v in x.items() if k != "root_ids_sorted"} for d, x in out["domains"].items()}))


def parity_ids(per=4):
    arch = {d: {json.loads(l)["root_id"] for l in open(V34 / f"parity/pred_val_{d}_gpu.jsonl")} for d in ("2d", "3d")}
    out = {}
    for dom in ("2d", "3d"):
        rr = [r for r in D.rows(dom, D.VAL_SNAP, "val") if r["root_id"] in arch[dom]]
        ids = []
        for K in ("0", "1", "2", "3", "NONE"):
            ids += sorted((r["root_id"] for r in rr if r["K_legacy"] == K), key=lambda x: D.stratum_hash("CRCVAE_PARITY_V1", x))[:per]
        out[dom] = ids
    wj("P0_PARITY_IDS.json", out)
    print(json.dumps({d: len(v) for d, v in out.items()}))


if __name__ == "__main__":
    {"provenance": provenance, "data": data_audit, "roster": roster, "parity_ids": parity_ids}[sys.argv[1]]()
