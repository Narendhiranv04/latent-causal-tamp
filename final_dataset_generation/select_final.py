#!/usr/bin/env python3
"""Deterministic final selection (versioned, never overwrites the originals) + integrity audit for the 2D and 3D target-task datasets.

Rules
- Originals are immutable archives; the new selection is a manifest that swaps some independent K2/K3 roots for new dependent roots.
- A new root built from a selected parent (re-parking: SAME layout) REPLACES that parent: never both in one selection.
- A new root built from a K1 parent (chain: parent layout + added objects) keeps the K1 parent; it inherits the parent's split.
- K3 picks favour strength: 1/6 > 2/6 > 3/6 > 4/6 > 5/6, ties by a fixed hash.  K-class quotas are preserved exactly.
- Every accepted root needs all orders evaluated (2 / 6), a present root file, and every success witness file on disk.
- Splits: new roots inherit the split of their parent's lineage group; no root is ever moved between splits."""
import hashlib, json, math, os, sys
from collections import Counter, defaultdict
from pathlib import Path

H = Path(__file__).resolve().parent
OUT = H / "FINAL_DATASET_SELECTION_MANIFESTS"
OUT.mkdir(exist_ok=True)
hh = lambda s: hashlib.sha256(s.encode()).hexdigest()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def new_roots(stores):
    """accepted roots from per-host stores: {root_id: (record, store_dir)}"""
    out = {}
    for st in stores:
        for f in sorted((st / "roots").glob("*.json")):
            r = json.loads(f.read_text())
            if "permutations" not in r:
                continue
            rid = r["ids"]["root_id"]
            assert rid not in out, f"duplicate new root id {rid}"
            out[rid] = (r, st)
    return out


def wit_ok(rec, st, extra_dirs=()):
    for p in rec["permutations"]:
        if p["y"] == 1:
            for w in p.get("witnesses") or []:
                if not any((d / "witnesses" / w[:2] / f"{w}.npz").exists() for d in (st, *extra_dirs)):
                    return False
    return True


def strength(r):
    return f"{r['n_success']}/{r['n_orders']}"


def pick(dom, quota, ratio, orig_rows, new, split_of, parent_of_new, extra_wit):
    """orig_rows: {rid: {K, order_class, n_success, ...}} of the published selection.  Returns the manifest rows."""
    sel = dict(orig_rows)
    report = {}
    used_parents = set()
    for K in ("2", "3"):
        q = sum(1 for r in orig_rows.values() if r["K"] == K)
        dep0 = [r for r in orig_rows.values() if r["K"] == K and r["order_class"] == "ORDER_DEPENDENT"]
        ind0 = [r for r in orig_rows.values() if r["K"] == K and r["order_class"] == "ORDER_INDEPENDENT"]
        need_dep = math.ceil(ratio * q)
        need_new = max(0, need_dep - len(dep0))
        max_new = len(ind0) - (q - need_dep)                    # every new root costs one independent slot
        cands = []
        for rid, (r, st) in new.items():
            if str(r["verified_K"]) != K or r["order_class"] != "ORDER_DEPENDENT" or len(r["permutations"]) != math.factorial(int(K)):
                continue
            if any(p["y"] not in (0, 1) for p in r["permutations"]) or not wit_ok(r, st, extra_wit):
                continue
            par = r["construction"]["parent_root_id"]
            same_layout = r["construction"].get("same_layout_as_parent", False) or r["construction"]["method"].endswith("repark") \
                or "repark" in r["construction"]["method"]
            cands.append((r["n_success"], 0 if (same_layout and par in orig_rows) else 1, hh(rid), rid, par, same_layout))
        cands.sort()                                            # strongest first; replacements of selected parents before others
        chosen, removed = [], set()
        for ns, _, _, rid, par, same in cands:
            if len(chosen) >= min(need_new, max_new):
                break
            if same and par in orig_rows:
                if par in removed or orig_rows[par]["order_class"] != "ORDER_INDEPENDENT":
                    continue
                removed.add(par)
            elif same and par in used_parents:
                continue
            used_parents.add(par)
            chosen.append(rid)
        # remaining independent removals (children not replacing a selected parent) by fixed hash
        extra_rm = len(chosen) - len(removed)
        pool = sorted((r["root_id"] for r in ind0 if r["root_id"] not in removed), key=lambda x: hh("drop" + x))
        removed |= set(pool[:extra_rm])
        for x in removed:
            sel.pop(x)
        for rid in chosen:
            r, st = new[rid]
            sel[rid] = {"root_id": rid, "K": K, "order_class": "ORDER_DEPENDENT", "n_success": r["n_success"], "n_orders": r["n_orders"],
                        "source": "NEW_DEPENDENCE_SEEKING", "host_store": str(st), "parent_root_id": r["construction"]["parent_root_id"],
                        "method": r["construction"]["method"], "split": split_of(r["construction"]["parent_root_id"])}
        d = [r for r in sel.values() if r["K"] == K and r["order_class"] == "ORDER_DEPENDENT"]
        report[f"K{K}"] = {"quota": q, "target_dependent": need_dep, "original_dependent": len(dep0), "original_independent": len(ind0),
                           "new_candidates": len(cands), "new_selected": len(chosen), "independent_removed": len(removed),
                           "final_dependent": len(d), "final_independent": sum(1 for r in sel.values() if r["K"] == K and r["order_class"] == "ORDER_INDEPENDENT"),
                           "final_dependent_pct": round(100 * len(d) / q, 2), "deficit": max(0, need_dep - len(d)),
                           "strength_final": dict(sorted(Counter(f"{r['n_success']}/{math.factorial(int(K))}" for r in sel.values() if r["K"] == K).items())),
                           "strength_new_selected": dict(sorted(Counter(f"{new[x][0]['n_success']}/{math.factorial(int(K))}" for x in chosen).items())),
                           "strength_new_candidates": dict(sorted(Counter(f"{c[0]}/{math.factorial(int(K))}" for c in cands).items()))}
    return sel, report


def main2d():
    P2 = H.parent / "order_classification_2d"
    rows = {}
    for l in open(P2 / "per_scene_six_permutation_outcomes.jsonl"):
        r = json.loads(l)
        rows[r["root_id"]] = {"root_id": r["root_id"], "K": r["K"], "order_class": r["order_class"], "n_success": r.get("n_success"),
                              "n_orders": r.get("n_perms"), "source": "ORIGINAL_SELECTED", "split": r.get("split"), "source_sha256": r["source_sha256"]}
    split = {x["root_id"]: x["split"] for x in json.loads(Path(
        "/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_relocations_v1/launch_ready_2d_v2/split_manifest.json").read_text())["roots"]}
    for r in rows.values():
        r["split"] = split.get(r["root_id"])
    new = new_roots([H / "d2/store"])
    sp = lambda par: split.get(par) or ("train" if int(hh("split2d" + par)[:4], 16) % 100 < 70 else "val" if int(hh("split2d" + par)[:4], 16) % 100 < 85 else "test")
    sel, rep = pick("2D", None, 0.60, rows, new, sp, None, ())
    return sel, rep, new


def main3d():
    P3 = H.parent / "order_classification_3d"
    rows = {}
    for l in open(P3 / "3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl"):
        r = json.loads(l)
        if r["K"] == "4":
            continue                                          # K4 archived separately, never in the main selection
        rows[r["root_id"]] = {"root_id": r["root_id"], "K": r["K"], "order_class": r["order_class"], "n_success": r.get("n_success"),
                              "n_orders": r.get("n_perms"), "source": "ORIGINAL_SELECTED", "split": r.get("split"), "source_sha256": r["source_sha256"]}
    split = {k: v for k, v in json.loads(Path("/home/naren/Desktop/rss-3d-relocations/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/"
                                              "production_v3/frozen/split_manifest_first_cohort.json").read_text())["split"].items()}
    stores = [H / "d3_gvlab/store", H / "d3_blackwell/store", H / "d3_laptop/store"]
    new = new_roots([s for s in stores if s.exists()])
    src = Path("/home/naren/Desktop/boltzmann_lfd/order_classification_3d/src_8fe96075/gh-yadu-iiith/shelf_6x6_open_sides/"
               "dataset_bd_classquota_without_home_position_no_overpass")
    sp = lambda par: split.get(par) or ("train" if int(hh("split3d" + par)[:4], 16) % 100 < 70 else "val" if int(hh("split3d" + par)[:4], 16) % 100 < 85 else "test")
    sel, rep = pick("3D", None, float(os.environ.get("RATIO_3D", "0.70")), rows, new, sp, None, (src / "raw",))
    return sel, rep, new


if __name__ == "__main__":
    res = {}
    for dom, fn in (("2D", main2d), ("3D", main3d)):
        sel, rep, new = fn()
        assert len({r["root_id"] for r in sel.values()}) == len(sel)
        m = OUT / f"{dom}_SELECTION_V2.json"
        m.write_text(json.dumps({"version": f"{dom}_TARGET_TASK_SELECTION_V2_DEPENDENCE", "rows": sorted(sel.values(), key=lambda r: (r["K"], r["root_id"]))}, indent=0))
        res[dom] = {"report": rep, "classes": dict(Counter(r["K"] for r in sel.values())), "total": len(sel),
                    "splits_new": dict(Counter(f"K{r['K']}|{r['split']}" for r in sel.values() if r["source"] != "ORIGINAL_SELECTED")),
                    "new_roots_accepted": len(new), "new_dependent_by_K": dict(Counter(str(r["verified_K"]) for r, _ in new.values() if r["order_class"] == "ORDER_DEPENDENT")),
                    "manifest": m.name, "manifest_sha256": sha(m)}
    (OUT / "SELECTION_SUMMARY.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
