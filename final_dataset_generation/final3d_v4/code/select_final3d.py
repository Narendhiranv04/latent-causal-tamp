#!/usr/bin/env python3
"""FINAL_3D_SELECTION_V4: the 2,500-scene 3D main selection (NONE 408, K0 511, K1 357, K2 612, K3 612); K4 archived separately.

* NONE / K0 / K1 / K2: the published selection (rss-ebm-infeasibility @ yadu/dataset-3d fb1120a30, selected.json) verbatim, frozen.
* K3 layouts: the 517 published K3 layouts + exactly 95 NEW layouts.  New layouts come only from (a) the published run's DEPENDENT scenes
  with verified K = 3 (raw/, not counted by the published independent-moves rule; admitted here under the order-dependence contract) and
  (b) layouts generated locally by the published generator (K3 requests only, namespace lap4).  A new layout is eligible only when its
  6 orders were all evaluated in a fresh env with >= 1 success and every non-target object passed the published no-fixed-object rule
  (none_dense.pickable_alone).  The 95 are the eligible new layouts with the strongest available order dependence (min n_success), then
  DEPENDENT before generated, then hash.
* One assignment per K3 layout: the original (strength = FRESH-env 6-order outcome), a DEPSEEK V1 re-parking child (fresh-env gate
  passed), a HARDK3 V3 child (gvlab, fresh-env gate) or a HARDK3 V4 child (laptop, fresh-env gate).  Chosen by an optimal assignment
  (scipy linear_sum_assignment) to target slots 1/6..6/6 = 214/184/92/61/31/30 (35/30/15/10/5/5 % of 612) with lexicographic weights:
  6/6 control quota protected, then 1/6 > 2/6 > 3/6 > 4/6 > 5/6; layouts beyond the targets keep their strongest assignment.
  Ties: assignment already finalized-X/Y-verified at its strength, fewer changed destinations, hash.
* Splits: the frozen first-cohort split manifest (SHELF66V3 placement extension) for every root it covers; every other root by
  SHELF66V3_PLACE_SPLIT_EXTENSION_V1 (union-find over the manifest groups + parent_family_id + identical layout; inherit; new groups
  by the V1 rule sha256("SHELF66V3_PLACE_ROSTER_V1|split|min root") < 0.70 train, < 0.85 val, else test).  Re-parked assignments share
  their layout's split.
  select_final3d.py OUT.json"""
import glob, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

H = Path(__file__).resolve().parent; V4 = H.parent; W = V4 / "work"; G = V4.parent; B = G.parent
SRC = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
SPLITF = Path("/home/naren/Desktop/rss-3d-relocations/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v3/frozen/"
              "split_manifest_first_cohort.json")
GEN = V4 / "gen_k3"
TARGET = {1: 214, 2: 184, 3: 92, 4: 61, 5: 31, 6: 30}
WGT = {6: 10 ** 7, 1: 10 ** 6, 2: 10 ** 5, 3: 10 ** 4, 4: 10 ** 3, 5: 10 ** 2}
N_NEW = 95


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hh(s):
    return hashlib.sha256(s.encode()).hexdigest()


def okey(order):
    return json.dumps([[o, list(d)] for o, d in order])


def main():
    sel = json.loads((SRC / "selected.json").read_text())["selected"]
    pins = json.loads((H / "pins_fb1120a30.json").read_text())
    led = jl(SRC / "raw/ledger.jsonl")
    dep_ids = sorted(r["root_id"] for r in led if r.get("observed") == "DEPENDENT" and r.get("verified_K") == 3)
    cls = {c["root_id"]: c for c in jl(B / "order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")}
    leg = {}
    for f in [W / "stage1_legacy.jsonl"] + sorted(W.glob("gen_legacy*.jsonl")):
        for r in jl(f):
            leg.setdefault(r["root_id"], {}).update({okey(o["order"]): o for o in r["orders"]})
    fixed = {r["root_id"]: r for f in [W / "stage1_fixed.jsonl"] + sorted(W.glob("gen_fixed*.jsonl")) for r in jl(f)}
    gen_ids = sorted({r["root_id"] for f in sorted(W.glob("gen_legacy*.jsonl")) for r in jl(f)})
    xy = {r["root_id"]: r for r in jl(G / "k3_hard/xy3d_all.jsonl") if "error" not in r}
    xy.update({r["root_id"]: r for r in jl(W / "xy_rows_v4_summary.jsonl")})
    stats = Counter()

    def path_of(rid):
        for p in [SRC / "raw/roots" / f"{rid}.json"] + [V4 / g / "raw/roots" / f"{rid}.json" for g in ("gen_k3", "gen_k3b", "gen_k3g")]:
            if p.exists():
                return p
        raise FileNotFoundError(rid)

    # ---------------- original K3 candidates (fresh-env strength) + teacher consistency
    def original(rid):
        rec = json.loads(path_of(rid).read_text())
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        import itertools
        fresh = {okey(p["order"]): p for p in (cls.get(rid, {}).get("permutations") or []) if p["source"] == "new"}
        fresh.update(leg.get(rid, {}))
        perms, dis = [], []
        hist = {okey(b["sequence"]): b["y"] for b in rec["labels"]["B"]}
        for q in itertools.permutations([[o, list(d)] for o, d in mini["sequence"]]):
            k = okey(q)
            f = fresh.get(k)
            if f is None or f.get("y") not in (0, 1):
                return None, {"reason": "ORDER_NOT_FRESH_RESOLVED", "order": k}
            perms.append({"order": list(q), "y": f["y"], "failed_step": f.get("failed_step"), "source": "fresh_env"})
            if k in hist and hist[k] != f["y"]:
                dis.append({"order": [o for o, _ in q], "teacher_y": hist[k], "fresh_y": f["y"]})
        return {"perms": perms, "ns": sum(p["y"] for p in perms), "teacher_fresh_disagreements": dis, "assign": mini["sequence"]}, None

    cands = defaultdict(list)       # layout -> candidate dicts
    layouts = {}                    # layout -> origin
    for rid in sel["3"]:
        layouts[rid] = "PUBLISHED_K3"
    new_pool = []
    for rid, origin in [(r, "PUBLISHED_RUN_DEPENDENT_K3") for r in dep_ids] + [(r, "GENERATED_V4_K3") for r in gen_ids]:
        fx = fixed.get(rid)
        if not fx or fx.get("resolution") != "EVALUATED" or fx.get("fixed_objects"):
            stats[f"new_excluded_fixed_or_unchecked:{origin}"] += 1
            continue
        new_pool.append((rid, origin))
    orig_info = {}
    for rid in list(layouts) + [r for r, _ in new_pool]:
        o, err = original(rid)
        if o is None:
            stats["original_unresolved"] += 1
            orig_info[rid] = err
            continue
        orig_info[rid] = o
        if o["teacher_fresh_disagreements"]:
            stats["original_teacher_fresh_disagree"] += 1
        if o["ns"] >= 1:
            cands[rid].append({"root_id": rid, "ns": o["ns"], "nch": 0, "source": "ORIGINAL", "method": None, "path": str(path_of(rid)),
                               "perms": o["perms"]})
        else:
            stats["original_zero_success_fresh"] += 1
    # ---------------- children (same layout)
    c3 = {r["root_id"]: r.get("consistent") for r in jl(G / "k3_hard/consistency3d.jsonl")}
    stores = [(G / "d3_gvlab/store", "NEW_DEPENDENCE_SEEKING_V1"), (G / "d3_blackwell/store", "NEW_DEPENDENCE_SEEKING_V1"),
              (G / "d3_laptop/store", "NEW_DEPENDENCE_SEEKING_V1"), (G / "k3_hard/d3/store", "NEW_HARD_ORDER_V3"), (V4 / "hard/store", "NEW_HARD_ORDER_V4"),
              (V4 / "hard_gvlab/store", "NEW_HARD_ORDER_V4")]
    for st, tag in stores:
        for f in sorted((st / "roots").glob("*.json")):
            r = json.loads(f.read_text())
            c = r.get("construction", {})
            L = c.get("layout_root_id") or c.get("parent_root_id")
            if L not in cands and L not in layouts and L not in dict(new_pool):
                continue
            if r.get("verified_K") != 3 or not c.get("same_layout_as_parent") or len(r.get("permutations", [])) != 6:
                continue
            if any(p["y"] not in (0, 1) for p in r["permutations"]) or r["n_success"] < 1:
                continue
            rid = r["ids"]["root_id"]
            if tag.startswith("NEW_HARD") and r.get("teacher_vs_fresh_env") != "ALL_TEACHER_ORDERS_REPRODUCED":
                stats["child_excluded_no_fresh_gate"] += 1; continue
            if tag.startswith("NEW_DEP") and c3.get(rid) is not True:
                stats["child_excluded_v1_fresh_gate"] += 1; continue
            if c.get("parent_sha256") != pins.get(L) and c.get("parent_sha256") != sha(path_of(L)):
                stats["child_excluded_parent_sha"] += 1; continue
            if c.get("destinations_free_distinct_in_original") is not True:
                stats["child_excluded_dest_cert"] += 1; continue
            nch = len(c.get("changed_destinations") or [c.get("changed_destination")])
            cands[L].append({"root_id": rid, "ns": r["n_success"], "nch": nch, "source": tag, "method": c.get("method"), "path": str(f),
                             "perms": [{"order": p["order"], "y": p["y"], "failed_step": p.get("failed_step"), "source": p.get("source")}
                                       for p in r["permutations"]]})
    # ---------------- the 95 new layouts
    elig = [(rid, origin) for rid, origin in new_pool if cands.get(rid)]
    elig.sort(key=lambda x: (min(c["ns"] for c in cands[x[0]]), x[1] != "PUBLISHED_RUN_DEPENDENT_K3", hh(x[0])))
    chosen_new = elig[:N_NEW]
    for rid, origin in chosen_new:
        layouts[rid] = origin
    stats["new_eligible"] = len(elig)
    stats["new_chosen"] = len(chosen_new)
    # ---------------- per-strength best candidate per layout + optimal assignment
    Ls = sorted(layouts)
    missing = [L for L in Ls if not cands.get(L)]
    assert not missing, f"K3 layouts without a valid candidate: {missing[:5]}"

    def xy_ok(c):
        x = xy.get(c["root_id"])
        return bool(x) and x.get("x_n_success") == c["ns"] and (x.get("y") or {}).get("y") == 1
    best = {}
    for L in Ls:
        b = {}
        for c in sorted(cands[L], key=lambda c: (c["ns"], not xy_ok(c), c["nch"], hh(c["root_id"]))):
            b.setdefault(c["ns"], c)
        best[L] = b
    slots = [s for s in range(1, 7) for _ in range(TARGET[s])]
    n = len(Ls)
    BIG = 1e12
    cost = np.full((n, len(slots) + 6 * n), BIG)
    for i, L in enumerate(Ls):
        for j, s in enumerate(slots):
            if s in best[L]:
                cost[i, j] = -WGT[s] + best[L][s]["nch"] - 5 * xy_ok(best[L][s])
        for s in best[L]:
            cost[i, len(slots) + (s - 1) * n:len(slots) + s * n] = s
    ri, ci = linear_sum_assignment(cost)
    assert (cost[ri, ci] < BIG).all()
    pick = {}
    for i, j in zip(ri, ci):
        s = slots[j] if j < len(slots) else (j - len(slots)) // n + 1
        pick[Ls[i]] = best[Ls[i]][s]
    # ---------------- splits
    sm = json.loads(SPLITF.read_text())
    old_split, old_groups = sm["split"], list(sm["groups"].values())
    main_roots = {}
    for k in ("NONE", "0", "1", "2"):
        sub = "raw_none" if k == "NONE" else "raw"
        for rid in sel[k]:
            main_roots[rid] = (k, SRC / sub / "roots" / f"{rid}.json")
    for L in Ls:
        main_roots[L] = ("3", path_of(L))
    recs = {rid: json.loads(p.read_text()) for rid, (k, p) in main_roots.items()}
    items = sorted(set(main_roots) | set(old_split))
    par = {r: r for r in items}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x

    def union(rs):
        for r in rs[1:]:
            par[find(r)] = find(rs[0])
    for g in old_groups:
        union([r for r in g if r in par])
    by = defaultdict(list)
    for rid, rec in recs.items():
        by[("fam", rec["ids"]["parent_family_id"])].append(rid)
        lay = json.dumps([sorted((o["id"], o["shape"], round(o["size"], 6), round(o["height"], 6)) for o in rec["objects"]),
                          sorted((k, tuple(v)) for k, v in rec["initial_cells"].items())], default=list)
        by[("layout", hh(lay))].append(rid)
    for rs in by.values():
        union(rs)
    groups = defaultdict(list)
    for r in items:
        groups[find(r)].append(r)
    split, conflicts, inherited, fresh_g = {}, [], 0, 0
    for g in groups.values():
        olds = {old_split[r] for r in g if r in old_split}
        if len(olds) > 1:
            conflicts.append(g); continue
        if olds:
            s_ = olds.pop(); inherited += sum(1 for r in g if r not in old_split)
        else:
            x = int(hh("|".join(("SHELF66V3_PLACE_ROSTER_V1", "split", min(g)))) [:15], 16) / 16 ** 15
            s_ = "train" if x < 0.70 else "val" if x < 0.85 else "test"; fresh_g += 1
        for r in g:
            split[r] = s_
    assert not conflicts, f"SPLIT_CONFLICT {conflicts[:2]}"
    assert all(split[r] == old_split[r] for r in old_split if r in split)
    # ---------------- rows
    k2leg = {}
    for rid in sel["2"]:
        rec = recs[rid]
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        import itertools
        fresh = {okey(p["order"]): p for p in (cls.get(rid, {}).get("permutations") or []) if p["source"] == "new"}
        fresh.update(leg.get(rid, {}))
        hist = {okey(b["sequence"]): b["y"] for b in rec["labels"]["B"]}
        ps = []
        for q in itertools.permutations([[o, list(d)] for o, d in mini["sequence"]]):
            f = fresh.get(okey(q))
            ps.append({"order": list(q), "y": None if f is None else f.get("y"), "failed_step": None if f is None else f.get("failed_step"),
                       "teacher_y": hist.get(okey(q))})
        k2leg[rid] = ps
    rows = []
    for k in ("NONE", "0", "1", "2"):
        for rid in sel[k]:
            p = main_roots[rid][1]
            row = {"root_id": rid, "K": k, "layout_root_id": rid, "source": "PUBLISHED_ORIGINAL", "split": split[rid],
                   "path": str(p.relative_to(SRC.parent.parent.parent)), "root_sha256": sha(p)}
            if k == "2":
                ps = k2leg[rid]
                row.update(legacy_orders=ps, legacy_n_success=None if any(x["y"] is None for x in ps) else sum(x["y"] for x in ps), n_orders=2)
            rows.append(row)
    for L in Ls:
        c = pick[L]
        p = Path(c["path"])
        oi = orig_info.get(L) if isinstance(orig_info.get(L), dict) and "ns" in orig_info.get(L, {}) else None
        rows.append({"root_id": c["root_id"], "K": "3", "layout_root_id": L, "layout_origin": layouts[L],
                     "source": c["source"] if c["source"] != "ORIGINAL" else ("PUBLISHED_ORIGINAL" if layouts[L] == "PUBLISHED_K3" else layouts[L]),
                     "method": c["method"], "split": split[L], "legacy_n_success": c["ns"], "n_orders": 6, "n_changed_destinations": c["nch"],
                     "legacy_orders": c["perms"], "path": str(p), "root_sha256": sha(p),
                     "natural_assignment": {"root_id": L, "legacy_n_success": oi["ns"] if oi else None,
                                            "teacher_fresh_disagreements": oi["teacher_fresh_disagreements"] if oi else None},
                     "alternatives_available": sorted(best[L])})
    k3 = [r for r in rows if r["K"] == "3"]
    out = {"version": "FINAL_3D_SELECTION_V4", "source": {"repo": "Narendhiranv04/rss-ebm-infeasibility", "branch": "yadu/dataset-3d",
                                                          "commit": "fb1120a30ab1be2ede6e0e4c585a93f0aacdb907",
                                                          "selected_json_sha256": sha(SRC / "selected.json")},
           "rule": __doc__, "targets_k3": TARGET, "counts": dict(Counter(r["K"] for r in rows)), "n_rows": len(rows),
           "k3_selected_distribution": {f"{s}/6": sum(1 for r in k3 if r["legacy_n_success"] == s) for s in range(1, 7)},
           "k3_natural_distribution": {f"{s}/6": sum(1 for r in k3 if (r["natural_assignment"]["legacy_n_success"] == s)) for s in range(0, 7)},
           "k3_source_mix": dict(Counter(r["source"] for r in k3)), "k3_layout_origin": dict(Counter(r["layout_origin"] for r in k3)),
           "split_counts": {k: dict(Counter(r["split"] for r in rows if r["K"] == k)) for k in ("NONE", "0", "1", "2", "3")},
           "split_rule_stats": {"inherited_from_manifest_groups": inherited, "fresh_groups": fresh_g},
           "stats": dict(stats), "new_layout_pool": [{"root_id": r, "origin": o, "min_ns": min(c["ns"] for c in cands[r]) if cands.get(r) else None,
                                                      "chosen": r in layouts} for r, o in new_pool],
           "k4_archived": {"ids": sel.get("4", []), "note": "K4 ordered scenes, archived separately, not in the 2,500 main total"},
           "rows": rows}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=0))
    print(out["counts"], out["n_rows"], out["k3_selected_distribution"], out["k3_source_mix"], out["k3_layout_origin"], dict(stats))


if __name__ == "__main__":
    main()
