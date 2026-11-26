#!/usr/bin/env python3
"""R2.0 audit (evaluator side, read-only; gvlab2).  Distinguishes N (all scene objects incl. target / fixed), m (ordered local sequence length),
K (certified minimum, only where certified), L (proposed / witness length) and h (prior hypothetical edits).

1. TRAIN / VAL distributions per domain from the TRAINING snapshot (V3.2 abf_v32_fb0eef4f5ff433ee: the bundle's train_snapshot) and the
   V3.4 snapshot (abf_9de85710c2a7103f: VAL); TEST rows are skipped by split BEFORE their labels are parsed (counted only).
2. Exact-compatible label pool for R2.1: snapshot X / Y labels + unchanged-teacher verifier caches (evaluate._verify_job, same BXY / FIN3D
   contracts), restricted to TRAIN / VAL roots; TEST and ~TT~ roots excluded; conflicts between sources counted, never resolved silently.
3. Development material N (3D K4/K5 cohort, C3b examples); release_v2 NOT opened (N from its committed report only).
    python audit.py OUT_DIR"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

NW = Path("/home/projects/long-horizon/naren_workspace")
SNAP_TRAIN = NW / "k3abl/abf/snapshot/abf_v32_fb0eef4f5ff433ee"
SNAP_V34 = NW / "k3abl/abf/snapshot/abf_9de85710c2a7103f"
CACHES = {"2d": [NW / p for p in ("k3val/runs/verifier_cache/verify_2d.jsonl", "k3abl/runs/verifier_cache/verify_2d.jsonl", "xy_repair_ranking/cache/verify_2d.jsonl",
                                  "full_domain_sets/cache/verify_2d.jsonl", "mcts_sets/cache/verify_2d.jsonl", "disco_final/disco_teach/cache/verify_2d.jsonl",
                                  "disco_final/ab/out/cache/verify_2d.jsonl")],
          "3d": [NW / p for p in ("k3val/runs/verifier_cache/verify_3d.jsonl", "k3abl/runs/verifier_cache/verify_3d.jsonl", "disco_final/disco_teach/cache/verify_3d.jsonl")]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(snap, dom, keep=("train", "val")):
    """Yield non-TEST rows; TEST lines are counted from the split field only."""
    n_test = 0
    for line in open(snap / f"data{dom}.jsonl"):
        i = line.find('"split": "')
        sp = line[i + 10:i + 10 + line[i + 10:].find('"')]
        if sp not in keep:
            n_test += sp == "test"
            continue
        yield json.loads(line)
    rows.n_test = n_test


def nfix(r, dom):
    return sum(1 for a in r["inputs"]["attrs"] if dom == "2d" and a[3] > 0.5)


def qtiles(v):
    v = sorted(v)
    q = lambda p: v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))]  # noqa: E731
    return {"n": len(v), "min": v[0], "q05": q(.05), "q25": q(.25), "q50": q(.5), "q75": q(.75), "q95": q(.95), "max": v[-1]} if v else {"n": 0}


def dist(snap, dom, split):
    R = [r for r in rows(snap, dom, (split,))]
    N = [len(r["inputs"]["ids"]) for r in R]
    byN = collections.defaultdict(lambda: {"roots": 0, "fixed": 0, "x_by_m": collections.Counter(), "x1_by_m": collections.Counter(),
                                           "y_by_e": collections.Counter(), "y1_by_e": collections.Counter(), "K": collections.Counter(), "families": set()})
    for r in R:
        n = len(r["inputs"]["ids"]); b = byN[n]
        b["roots"] += 1; b["fixed"] += nfix(r, dom); b["K"][r["K_legacy"]] += 1; b["families"].add(r["parent_family_id"])
        for q in r["labels"]["X"]:
            if q["x"] in (0, 1):
                b["x_by_m"][len(q["seq"])] += 1; b["x1_by_m"][len(q["seq"])] += q["x"]
        for y in r["labels"]["Y"]:
            if y["y"] in (0, 1):
                b["y_by_e"][len(y["edit"])] += 1; b["y1_by_e"][len(y["edit"])] += y["y"]
    out = {"roots": len(R), "families": len({r["parent_family_id"] for r in R}), "N": qtiles(N), "N_hist": dict(sorted(collections.Counter(N).items())),
           "fixed_per_root": qtiles([nfix(r, dom) for r in R]), "movable_per_root": qtiles([len(r["inputs"]["ids"]) - 1 - nfix(r, dom) for r in R]),
           "K_legacy": dict(collections.Counter(r["K_legacy"] for r in R)), "byN": {}}
    for n, b in sorted(byN.items()):
        out["byN"][n] = {"roots": b["roots"], "families": len(b["families"]), "fixed_mean": round(b["fixed"] / b["roots"], 2), "K": dict(b["K"]),
                         "X_by_m": {m: [b["x_by_m"][m], b["x1_by_m"][m]] for m in sorted(b["x_by_m"])},
                         "Y_by_edit": {e: [b["y_by_e"][e], b["y1_by_e"][e]] for e in sorted(b["y_by_e"])}}
    tot = lambda key, sub: {m: sum(v[key].get(m, [0, 0])[sub] for v in out["byN"].values()) for m in sorted({m for v in out["byN"].values() for m in v[key]})}  # noqa: E731
    out["X_total_by_m"] = {m: [tot("X_by_m", 0)[m], tot("X_by_m", 1)[m]] for m in tot("X_by_m", 0)}
    out["Y_total_by_edit"] = {e: [tot("Y_by_edit", 0)[e], tot("Y_by_edit", 1)[e]] for e in tot("Y_by_edit", 0)}
    out["test_rows_skipped"] = rows.n_test
    return out, R


def pool(dom, split_of, nobj):
    """Exact-compatible label pool (TRAIN/VAL roots only): X keyed (root, ordered seq), Y keyed (root, sorted endpoint)."""
    X, Y, conf, src, skipped = {}, {}, collections.Counter(), collections.Counter(), collections.Counter()

    def add(tab, k, v, s):
        if k in tab and tab[k]["v"] != v:
            conf[s] += 1; tab[k].setdefault("conflict", []).append([s, v]); return
        tab.setdefault(k, {"v": v, "src": s})
    for f in CACHES[dom]:
        if not f.exists():
            continue
        for line in open(f):
            r = json.loads(line)
            rid = r["root"]
            if "~" in rid or split_of.get(rid) not in ("train", "val"):
                skipped["test_or_unknown_or_tt" if "~" not in rid else "tt"] += 1; continue
            for q in r["results"]:
                seq = tuple(tuple(map(int, a)) for a in q["seq"])
                x = (q.get("x") or {}).get("x"); y = (q.get("y") or {}).get("y")
                xs = (q.get("x") or {}).get("status")
                if seq and x in (0, 1):
                    add(X, (rid, seq), (x, xs if x == 0 else "VERIFIED"), f.parent.parent.parent.name); src["X:" + f.parent.parent.parent.name] += 1
                if y in (0, 1):
                    add(Y, (rid, tuple(sorted(seq))), y, f.parent.parent.parent.name); src["Y:" + f.parent.parent.parent.name] += 1
    return X, Y, conf, src, skipped


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rep = {"snapshots": {"train_snapshot": str(SNAP_TRAIN), "train_lock_sha256": sha(SNAP_TRAIN / "data_snapshot.lock.json"),
                         "v34_snapshot": str(SNAP_V34), "v34_lock_sha256": sha(SNAP_V34 / "data_snapshot.lock.json")}, "domains": {}}
    for dom in ("2d", "3d"):
        tr, Rtr = dist(SNAP_TRAIN, dom, "train")
        va, Rva = dist(SNAP_V34, dom, "val")
        split_of = {}
        for snap in (SNAP_TRAIN, SNAP_V34):
            for line in open(snap / f"data{dom}.jsonl"):
                i = line.find('"root_id": "'); rid = line[i + 12:i + 12 + line[i + 12:].find('"')]
                j = line.find('"split": "'); sp = line[j + 10:j + 10 + line[j + 10:].find('"')]
                split_of[rid] = "test" if "test" in (sp, split_of.get(rid)) else sp
        nobj = {r["root_id"]: len(r["inputs"]["ids"]) for r in Rtr + Rva}
        X, Y, conf, src, skipped = pool(dom, split_of, nobj)
        # snapshot labels join the pool (TRAIN labels = fit reference; VAL labels = held-out reference)
        for r in Rtr + Rva:
            for q in r["labels"]["X"]:
                if q["x"] in (0, 1):
                    k = (r["root_id"], tuple(tuple(map(int, a)) for a in q["seq"]))
                    if k in X and X[k]["v"][0] != q["x"]:
                        conf["snapshot_vs_cache_X"] += 1
                    X.setdefault(k, {"v": (q["x"], q.get("x_phase") or "VERIFIED"), "src": "snapshot"})
            for y in r["labels"]["Y"]:
                if y["y"] in (0, 1):
                    k = (r["root_id"], tuple(sorted(tuple(map(int, a)) for a in y["edit"])))
                    if k in Y and Y[k]["v"] != y["y"]:
                        conf["snapshot_vs_cache_Y"] += 1
                    Y.setdefault(k, {"v": y["y"], "src": "snapshot"})
        lab = collections.Counter()
        for (rid, seq), v in X.items():
            lab[("X", split_of[rid], len(seq), v["v"][0])] += 1
        for (rid, e), v in Y.items():
            lab[("Y", split_of[rid], len(e), v["v"])] += 1
        rep["domains"][dom] = {"train": tr, "val": va, "pool": {"X_unique": len(X), "Y_unique": len(Y), "conflicts": dict(conf), "sources": dict(src),
                                                               "skipped_cache_roots": dict(skipped),
                                                               "by_split_len_label": {"|".join(map(str, k)): v for k, v in sorted(lab.items())}}}
        with open(out / f"pool_{dom}.jsonl", "w") as f:                         # PRIVATE label pool (not committed)
            for (rid, seq), v in sorted(X.items()):
                f.write(json.dumps({"t": "X", "root": rid, "split": split_of[rid], "N": nobj.get(rid), "seq": seq, "x": v["v"][0], "status": v["v"][1],
                                    "src": v["src"], "conflict": v.get("conflict")}) + "\n")
            for (rid, e), v in sorted(Y.items()):
                f.write(json.dumps({"t": "Y", "root": rid, "split": split_of[rid], "N": nobj.get(rid), "edit": e, "y": v["v"], "src": v["src"],
                                    "conflict": v.get("conflict")}) + "\n")
    # development material
    dev = {}
    pub = NW / "fig3/runs/PUBLIC.jsonl"
    if pub.exists():
        dev["3d_k45_cohort"] = qtiles([len(json.loads(l)["inputs"]["ids"]) for l in open(pub)])
    ex = NW / "k3val/runs/out/ttarget"
    for dom in ("2d", "3d"):
        p = ex / f"EXAMPLES_{dom}_b.json"
        if p.exists():
            E = json.loads(p.read_text())
            vr = {json.loads(l)["root_id"]: len(json.loads(l)["inputs"]["ids"]) for l in open(SNAP_V34 / f"data{dom}.jsonl") if '"split": "val"' in l}
            dev[f"{dom}_c3b"] = qtiles([vr[e["root_id"]] for e in E if e["root_id"] in vr])
    dev["2d_release_v2"] = "NOT OPENED (protected); committed scaling2d report: 23 scenes up to 27-28 objects (K12)"
    rep["development_material_N"] = dev
    (out / "R2_0_inventory.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({d: {"train_N": v["train"]["N"], "val_N": v["val"]["N"], "pool": {k: v["pool"][k] for k in ("X_unique", "Y_unique", "conflicts")}}
                      for d, v in rep["domains"].items()}, indent=1, default=str))
    print(json.dumps(dev, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
