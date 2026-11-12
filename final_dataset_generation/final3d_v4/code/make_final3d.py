#!/usr/bin/env python3
"""Builds the FINAL_3D_DATASET_V4 package (9 deliverables) from the final selection, the finalized X/Y + Y-negative results, the
fresh-env classification, generation / hard-order ledgers and the witness stores.  Read-only on every input; never touches V2 / V3, the
2D dataset or the placement datasets.   make_final3d.py"""
import glob, hashlib, json, shutil, statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent; V4 = H.parent; W = V4 / "work"; G = V4.parent; B = G.parent
PKG = G / "FINAL_3D_DATASET_V4"
SRC = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
GVPFX = "/home/nav/approachb_final_gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass/raw/roots/"
TARGET = {1: 214, 2: 184, 3: 92, 4: 61, 5: 31, 6: 30}
S6 = range(1, 7)


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def okey(order):
    return "".join(o[-1] for o, _ in order)


def rehash(p):
    z = np.load(p, allow_pickle=False)
    h = hashlib.sha256()
    for k in sorted(z.files):
        v = np.ascontiguousarray(np.asarray(z[k]))
        h.update(f"{k}|{v.dtype.str}|{v.shape}".encode()); h.update(v.tobytes())
    return h.hexdigest()[:24]


def dist(xs, rng=S6):
    c = Counter(xs)
    return {f"{s}/6": c.get(s, 0) for s in rng}


def table(rows, cols):
    s = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in rows:
        s += "| " + " | ".join(str(x) for x in r) + " |\n"
    return s


def main():
    PKG.mkdir(exist_ok=True)
    sel = json.loads((W / "FINAL_3D_SELECTION_V4.json").read_text())
    rows = sel["rows"]
    k3 = [r for r in rows if r["K"] == "3"]
    k2 = [r for r in rows if r["K"] == "2"]
    # ------------------------------------------------------------------ X/Y results
    files = {"k2_xy_yneg.jsonl": "LAPTOP", "xy_final_laptop.jsonl": "LAPTOP", "xy_final_gvlab.jsonl": "GVLAB", "xy_assist_laptop.jsonl": "LAPTOP", "es_verify.jsonl": "LAPTOP"}
    res, host_of = {}, {}
    for f, host in files.items():
        for r in jl(W / f):
            res[r["key"]] = r; host_of[r["key"]] = host
    items = {i["key"]: i for f in ("xy_items.json", "yneg_items.json", "xy_shortcut_audit.json", "xy_items_k2.json", "yneg_items_k2.json")
             if (W / f).exists() for i in json.loads((W / f).read_text())}
    reuse = json.loads((W / "xy_reuse.json").read_text())
    ycache = {}
    for k, r in res.items():
        it = items.get(k)
        if r.get("y") and it and it.get("y_key") and r["y"].get("y") in (0, 1):
            ycache.setdefault(it["y_key"], {"y": r["y"]["y"], "status": r["y"].get("status"), "witnesses": r["y"].get("witnesses"),
                                            "provenance": f"FIN3D_Y_{host_of[k]}", "computed_by": k})
    labels, cover = [], Counter()
    xstr = {}
    for row in rows:
        if row["K"] not in ("2", "3"):
            continue
        rid = row["root_id"]
        ru = reuse.get(rid, {"orders": {}})
        r = res.get(f"XY_{rid}", {})
        comp = {okey(x["order"]): x for x in r.get("x", [])}
        if ru.get("y"):
            y = {"y": ru["y"]["y"], "provenance": ru["y"]["provenance"]}
        else:
            yc = ycache.get(ru.get("y_key"))
            y = {"y": yc["y"], "provenance": yc["provenance"] + ("" if yc["computed_by"] == f"XY_{rid}" else "_SHARED_ENDPOINT_CACHE"),
                 "witnesses": yc.get("witnesses")} if yc else {"y": None, "provenance": "MISSING"}
        leg = {okey(x["order"]): x.get("y") for x in row.get("legacy_orders") or []}
        xs = []
        for lo in row.get("legacy_orders") or []:
            k = okey(lo["order"])
            if k in ru["orders"]:
                o = ru["orders"][k]; x = {"x": o["x"], "x_phase": o.get("phase"), "x_provenance": o["provenance"]}
            elif k in comp:
                c = comp[k]
                x = {"x": c.get("x") if c.get("resolution") == "EVALUATED" else None, "x_phase": c.get("phase"),
                     "x_provenance": f"FIN3D_X_{host_of[f'XY_{rid}']}" if c.get("resolution") == "EVALUATED" else f"MISSING_{c.get('resolution')}",
                     "x_witnesses": c.get("witnesses")}
            else:
                x = {"x": None, "x_phase": None, "x_provenance": "MISSING"}
            xs.append(x["x"])
            labels.append({"row_kind": "SELECTED_ASSIGNMENT_ORDER", "root_id": rid, "K": row["K"], "split": row["split"], "layout_root_id": row["layout_root_id"],
                           "order": [o for o, _ in lo["order"]], "relocations": lo["order"], **x, "y": y["y"], "y_provenance": y["provenance"],
                           "legacy_y": leg.get(k)})
        full = all(v in (0, 1) for v in xs) and y["y"] in (0, 1)
        cover["finalized" if full else "incomplete"] += 1
        if full:
            xstr[rid] = (row["K"], sum(xs), y["y"])
    # ---- Y-negatives: omission endpoints
    for row in rows:
        if row["K"] not in ("2", "3"):
            continue
        rid = row["root_id"]
        it, r = items.get(f"YN_{rid}"), res.get(f"YN_{rid}")
        if not it:
            continue
        if r and r.get("y") and r["y"].get("y") in (0, 1):
            y = {"y": r["y"]["y"], "provenance": f"FIN3D_Y_{host_of[f'YN_{rid}']}"}
        else:
            yc = ycache.get(it.get("y_key"))
            y = {"y": yc["y"], "provenance": yc["provenance"] + "_SHARED_ENDPOINT_CACHE"} if yc else {"y": None, "provenance": "MISSING"}
        comp = {okey(x["order"]): x for x in (r or {}).get("x", [])}
        for q in it["x_orders"]:
            c = comp.get(okey(q))
            x = c.get("x") if c and c.get("resolution") == "EVALUATED" else None
            labels.append({"row_kind": "OMISSION_YNEG", "root_id": rid, "K": row["K"], "split": row["split"], "layout_root_id": row["layout_root_id"],
                           "omitted": it["omitted"], "order": [o for o, _ in q], "relocations": q, "x": x, "x_phase": c.get("phase") if c else None,
                           "x_provenance": f"FIN3D_X_{host_of[f'YN_{rid}']}" if x is not None else "MISSING", "x_witnesses": c.get("witnesses") if c else None,
                           "y": y["y"], "y_provenance": y["provenance"]})
    # ---- Y-negatives: empty corrective sequence (original scene), teacher T-direct check + fresh verification sample
    es_ver = {r["root_id"]: r for r in jl(W / "es_verify.jsonl")}
    for row in rows:
        if row["K"] not in ("NONE", "1", "2", "3"):
            continue
        L = row["layout_root_id"]
        v = es_ver.get(L)
        labels.append({"row_kind": "EMPTY_SEQUENCE_YNEG", "root_id": L, "K": row["K"], "split": row["split"], "layout_root_id": L, "order": [],
                       "relocations": [], "x": 1, "x_provenance": "EMPTY_SEQUENCE(no relocation; robot already at q_ref)", "y": 0,
                       "y_provenance": "TEACHER_ORIGINAL_T_DIRECT_CHECK(verified_K>=1 or certified NONE)" +
                                       (f"; FRESH_VERIFIED y={v['y']['y']}" if v and v.get('y') else ""),
                       "fresh_verified_y": v["y"]["y"] if v and v.get("y") else None})
    # ------------------------------------------------------------------ shortcut audit
    aud = Counter(); aud_bad = []
    for k, it in items.items():
        if not k.startswith("A_"):
            continue
        r = res.get(k)
        if not r:
            aud["not_run"] += 1; continue
        x = r["x"][0]
        okk = x.get("x") == 0 and x.get("phase") == it["expect_phase"]
        aud["agree" if okk else "disagree"] += 1
        if not okk:
            aud_bad.append({"key": k, "expected": it["expect_phase"], "got": {"x": x.get("x"), "phase": x.get("phase")}})
    # ------------------------------------------------------------------ summaries
    kinds = Counter((l["row_kind"], l["x"], l["y"]) for l in labels)
    xy_tab = {kind: {f"X={a},Y={b}": kinds.get((kind, a, b), 0) for a in (0, 1) for b in (0, 1)} | {"missing": sum(v for (kk, a, b), v in kinds.items() if kk == kind and (a is None or b is None))}
              for kind in ("SELECTED_ASSIGNMENT_ORDER", "OMISSION_YNEG", "EMPTY_SEQUENCE_YNEG")}
    k3_x = dist([v[1] for rid, v in xstr.items() if v[0] == "3"], range(0, 7))
    k3_leg = dist([r["legacy_n_success"] for r in k3])
    conf = Counter((r["legacy_n_success"], xstr[r["root_id"]][1]) for r in k3 if r["root_id"] in xstr)
    k2_x = Counter(v[1] for v in xstr.values() if v[0] == "2")
    k2_leg = Counter(r.get("legacy_n_success") for r in k2)
    y_sel = Counter(v[2] for v in xstr.values())
    # ------------------------------------------------------------------ integrity
    integ = {}
    pub = json.loads((SRC / "selected.json").read_text())["selected"]
    pins = json.loads((H / "pins_v4_all.json").read_text())
    ids = [r["root_id"] for r in rows]
    integ["n_rows"] = len(rows)
    integ["class_counts"] = dict(Counter(r["K"] for r in rows))
    integ["class_counts_ok"] = integ["class_counts"] == {"NONE": 408, "0": 511, "1": 357, "2": 612, "3": 612}
    integ["root_ids_unique"] = len(set(ids)) == len(ids)
    integ["k3_layouts_unique"] = len({r["layout_root_id"] for r in k3}) == len(k3)
    integ["frozen_classes_equal_published"] = all(sorted(r["root_id"] for r in rows if r["K"] == k) == sorted(pub[k]) for k in ("NONE", "0", "1", "2"))
    integ["published_k3_layouts_all_present"] = set(pub["3"]) <= {r["layout_root_id"] for r in k3}
    integ["k4_not_in_main"] = not (set(pub.get("4", [])) & set(ids))
    bad = Counter()
    for r in rows:
        p = Path(r["path"]) if Path(r["path"]).is_absolute() else Path("/home/naren/Desktop/rss3d_final_src") / r["path"]
        if not p.exists():
            bad["file_missing"] += 1; continue
        if sha(p) != r["root_sha256"]:
            bad["root_sha256_mismatch"] += 1
        if r["K"] == "3" and r["source"] not in ("PUBLISHED_ORIGINAL", "PUBLISHED_RUN_DEPENDENT_K3", "GENERATED_V4_K3"):
            c = json.loads(p.read_text())["construction"]
            if (c.get("layout_root_id") or c.get("parent_root_id")) != r["layout_root_id"] or not c.get("same_layout_as_parent"):
                bad["lineage_layout_mismatch"] += 1
            if c.get("parent_sha256") != pins.get(r["layout_root_id"]):
                bad["parent_sha256_mismatch"] += 1
        if r["K"] in ("NONE", "0", "1", "2") or r["source"] == "PUBLISHED_ORIGINAL":
            if r["root_id"] in pins and pins[r["root_id"]] != r["root_sha256"]:
                bad["published_root_changed"] += 1
    integ["row_file_and_lineage_failures"] = dict(bad)
    sm = json.loads(Path("/home/naren/Desktop/rss-3d-relocations/gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/production_v3/frozen/"
                         "split_manifest_first_cohort.json").read_text())["split"]
    integ["split_conflicts_with_frozen_manifest"] = sum(1 for r in rows if r["layout_root_id"] in sm and sm[r["layout_root_id"]] != r["split"])
    # witnesses: selected non-published K3 roots (their own store) + X/Y label witnesses (work/store, work/store_gvlab)
    wc = Counter()
    for r in k3:
        if r["source"] == "PUBLISHED_ORIGINAL":
            continue
        p = Path(r["path"]); st = p.parent.parent
        rec = json.loads(p.read_text())
        wids = {w for b in rec["labels"]["B"] for w in (b.get("witnesses") or [])} | {w for q in rec.get("permutations", []) for w in (q.get("witnesses") or [])}
        for w in wids:
            f = st / "witnesses" / w[:2] / f"{w}.npz"
            wc["root:" + ("missing" if not f.exists() else "ok" if rehash(f) == w else "hash_mismatch")] += 1
    stores = [W / "store", W / "store_gvlab", G / "k3_hard/d3/store"]
    def find_w(w):
        for st in stores:
            f = st / "witnesses" / w[:2] / f"{w}.npz"
            if f.exists():
                return f
    seen = set()
    for l in labels:
        for w in (l.get("x_witnesses") or []):
            if w in seen:
                continue
            seen.add(w)
            f = find_w(w)
            wc["xy:" + ("missing" if f is None else "ok" if rehash(f) == w else "hash_mismatch")] += 1
    integ["witness_check"] = dict(wc)
    v2 = G / "FINAL_DATASET_SELECTION_MANIFESTS"
    sums = dict(l.split()[::-1] for l in open(v2 / "SHA256SUMS") if l.strip())
    integ["2d_and_v2_selection_files_unchanged"] = all(sha(v2 / n) == h for n, h in sums.items() if (v2 / n).exists())
    integ["v3_k3_package_unchanged"] = all(sha(G / "k3_hard/K3_HARD_ORDER_V1" / l.split()[1]) == l.split()[0]
                                           for l in open(G / "k3_hard/K3_HARD_ORDER_V1/SHA256SUMS") if l.strip())
    integ["training_started"] = False
    # ------------------------------------------------------------------ resources
    def cpu(f, key="cpu_s"):
        return round(sum(r.get(key, 0) or 0 for r in jl(f)) / 3600, 1)
    def cpu_orders(f):
        return round(sum(o.get("cpu_s", 0) for r in jl(f) for o in r.get("orders", [])) / 3600, 1)
    def cpu_xy(f):
        return round(sum((x.get("cpu_s") or 0) for r in jl(f) for x in r.get("x", [])) / 3600 + sum((r.get("y") or {}).get("cpu_s", 0) or 0 for r in jl(f)) / 3600, 1)
    gen_wall = {g: round(sum((r.get("wall_s") or 0) for r in jl(V4 / g / "raw/ledger.jsonl")[4071:]) / 3600, 1) for g in ("gen_k3", "gen_k3b", "gen_k3g")}
    resources = {"limits": {"laptop": "<= 27 workers (of 32 logical CPUs)", "gvlab": "<= 16 workers (of 24), >= 3 free, from 2026-11-11 21:01 IST (user approval)"},
                 "stage1_fresh_legacy_cpu_h_laptop": cpu_orders(W / "stage1_legacy.jsonl"), "stage1_fixed_object_cpu_h_laptop": cpu(W / "stage1_fixed.jsonl"),
                 "generation_worker_wall_h": {"laptop_lap4": gen_wall["gen_k3"], "laptop_lap5": gen_wall["gen_k3b"], "gvlab_srv5": gen_wall["gen_k3g"]},
                 "generated_checks_cpu_h_laptop": round(cpu_orders(W / "gen_legacy.jsonl") + cpu(W / "gen_fixed.jsonl"), 1),
                 "hard_order_cpu_h": {"laptop": cpu(V4 / "hard/ledger.jsonl"), "gvlab": cpu(V4 / "hard_gvlab/ledger.jsonl")},
                 "xy_and_yneg_cpu_h": {"laptop": round(cpu_xy(W / "k2_xy_yneg.jsonl") + cpu_xy(W / "xy_final_laptop.jsonl") + cpu_xy(W / "xy_assist_laptop.jsonl") + cpu_xy(W / "es_verify.jsonl"), 1),
                                       "gvlab": cpu_xy(W / "xy_final_gvlab.jsonl")}}
    # ------------------------------------------------------------------ copy new roots, write manifests
    (PKG / "roots_new").mkdir(exist_ok=True)
    for r in k3:
        if r["source"] != "PUBLISHED_ORIGINAL" and not r["path"].startswith(str(SRC)):
            shutil.copy(r["path"], PKG / "roots_new" / Path(r["path"]).name)
    gen_layouts = [r for r in k3 if r["layout_origin"] == "GENERATED_V4_K3"]
    for r in gen_layouts:
        for g in ("gen_k3", "gen_k3b", "gen_k3g"):
            p = V4 / g / "raw/roots" / f"{r['layout_root_id']}.json"
            if p.exists():
                shutil.copy(p, PKG / "roots_new" / p.name)
    (PKG / "FINAL_3D_SELECTION_MANIFEST.json").write_text(json.dumps(sel, indent=0))
    n_fin = cover["finalized"]
    lab = {"version": "FINAL_3D_XY_LABELS_V4", "definitions": {
        "X": "the order's relocations executed exactly as bd_3dt.teach.seq (fresh env, carried arm state, same checks) WITHOUT the target step, then "
             "CONNECTOR_TO_QREADY_V1 (plan_free_move to q_ref = q_ready, RRT 5000 seed 0, execute, open gripper, |q - q_ref| <= 0.02, nothing pushed, "
             "every object in its endpoint cell, no contact)",
        "Y": "BD3DS66_Y_PLAN_V1: the endpoint scene settled at q_ref, bd_3dt.query(t0 -> goal), executed with seq's target checks (one Y per endpoint)",
        "legacy_y": "full-task label: relocations then T planned from the ACHIEVED arm pose (perm3d.seq, fresh env)",
        "provenance": {"R1_GVLAB_XY3D_V3": "gvlab xy3d result for HARDK3 V3 roots (laptop/gvlab parity 3/3 roots identical)",
                       "R2_FRESH_LEGACY_RELOCATION_FAILURE": "X = 0 at relocation j because the fresh-env legacy run of the same order failed at relocation j "
                                                             "(identical code path; 728/728 on V3 roots; shortcut audit in FINAL_3D_XY_FINALIZATION_REPORT)",
                       "FIN3D_X_* / FIN3D_Y_*": "computed in this run (laptop or gvlab; parity 48/48 legacy orders identical incl. witness ids)",
                       "_SHARED_ENDPOINT_CACHE": "Y of an identical endpoint (same objects, cells, goal) computed once and shared"}},
           "counts": {"rows": len(labels), "by_kind_xy": xy_tab}, "rows": labels}
    (PKG / "FINAL_3D_XY_LABEL_MANIFEST.json").write_text(json.dumps(lab))
    st = {"k3_legacy_selected": k3_leg, "k3_x_selected": k3_x, "k3_natural": sel["k3_natural_distribution"], "legacy_vs_x": {f"{a}->{b}": v for (a, b), v in sorted(conf.items())},
          "k2_legacy": {f"{k}/2": v for k, v in sorted(k2_leg.items(), key=str)}, "k2_x": {f"{k}/2": v for k, v in sorted(k2_x.items())},
          "y_selected_endpoints": dict(y_sel), "xy_tab": xy_tab, "cover": dict(cover), "shortcut_audit": dict(aud), "shortcut_audit_disagreements": aud_bad,
          "integrity": integ, "resources": resources}
    (PKG / "final3d_raw_stats.json").write_text(json.dumps(st, indent=1, default=str))
    integ_ok = (integ["class_counts_ok"] and integ["root_ids_unique"] and integ["k3_layouts_unique"] and integ["frozen_classes_equal_published"]
                and integ["published_k3_layouts_all_present"] and integ["k4_not_in_main"] and not integ["row_file_and_lineage_failures"]
                and integ["split_conflicts_with_frozen_manifest"] == 0 and not any("missing" in k or "mismatch" in k for k in wc)
                and integ["2d_and_v2_selection_files_unchanged"] and integ["v3_k3_package_unchanged"])
    k3d = sel["k3_selected_distribution"]
    defi = {f"{s}/6": TARGET[s] - k3d[f"{s}/6"] for s in S6 if TARGET[s] > k3d[f"{s}/6"]}
    rd = {"stage": "FINAL 3D V4 dataset package; STOPPED BEFORE TRAINING", "training_started": False,
          "status": ("TRAINING_READY_PENDING_APPROVAL" if integ_ok and n_fin == len(k2) + len(k3) else
                     "TRAINING_READY_WITH_CAVEATS_PENDING_APPROVAL" if integ_ok else "BLOCKED_INTEGRITY"),
          "main_count": len(rows), "class_counts": integ["class_counts"], "k4_archived": len(pub.get("4", [])),
          "k3_strength_selected_legacy": k3d, "k3_strength_targets": {f"{s}/6": TARGET[s] for s in S6}, "k3_strength_deficits": defi,
          "k3_strength_finalized_x": k3_x, "k2_k3_rows_fully_finalized_xy": n_fin, "k2_k3_rows_total": len(k2) + len(k3),
          "rows_legacy_only": {"K0": 511, "K1": 357, "NONE": 408, "K2_K3_incomplete": cover["incomplete"]},
          "y_negative_labels": {k: v["X=0,Y=0"] + v["X=1,Y=0"] for k, v in xy_tab.items()}, "xy_combinations": xy_tab,
          "integrity_ok": integ_ok, "integrity": integ, "shortcut_audit": dict(aud),
          "caveats": ["50 K3 layouts are published-run DEPENDENT scenes (excluded by the published independent-moves rule; admitted under the order-"
                      "dependence contract); 45 K3 layouts were generated locally with the unmodified published generator (namespaces lap4 / lap5 / srv5)",
                      "K3 hard-order view: 1/6 is near target but 2/6 and 3/6 are short; 5/6 and 6/6 exceed target because many layouts have no stronger verified assignment",
                      "the K3 selection uses re-parked (hard-order / dependence-seeking) assignments for many layouts; the natural (original) assignment of every layout is kept for the natural-distribution view",
                      "3D X/Y labels are teacher passes (fresh env) without an independent replay process",
                      "EMPTY_SEQUENCE Y-negatives reuse the teacher's original T-direct check (fresh-verified on a sample)",
                      "the gvlab hard-order pass was time-boxed (05:45 IST); 2 in-flight jobs were stopped (MISSING, not failure)",
                      f"{len({l['root_id'] for l in labels if l['row_kind'] == 'OMISSION_YNEG' and l['y'] == 1})} selected rows have an omission endpoint with Y = 1 "
                      "(a shorter repair is feasible from q_ref, i.e. minimal K under the finalized protocol may be lower); listed in the Y-negative report",
                      f"{y_sel.get(0, 0)} selected K2/K3 rows have endpoint Y = 0 from q_ref although their legacy full-task label succeeds (target only "
                      "feasible from the carried arm pose); kept with their finalized labels"]}
    (PKG / "FINAL_3D_DATASET_READINESS.json").write_text(json.dumps(rd, indent=1))
    # ------------------------------------------------------------------ markdown reports
    R = []
    R.append("# FINAL 3D main dataset (V4)\n\nShelf 6×6 open-sided, xArm7, without home position, no overpass. Source: `rss-ebm-infeasibility` @ "
             "`yadu/dataset-3d` fb1120a30 (published selection: NONE 408, K0 511, K1 357, K2 612, K3 517, K4 9 archived).\n\n")
    R.append("## Final counts (exactly 2,500 main scenes; K4 archived separately)\n\n" + table([[k, v] for k, v in integ["class_counts"].items()], ["class", "scenes"]))
    R.append("\n## Where the 95 additional K3 scenes come from\n\n" + table([[k, v] for k, v in sel["k3_layout_origin"].items()], ["layout origin", "K3 layouts"]) +
             "\n- PUBLISHED_RUN_DEPENDENT_K3: teacher-verified K = 3 scenes of the published run that the published independent-moves rule did not count "
             "(a relocation needs another one first). Every one passed the published no-fixed-object rule and has >= 1 successful order in a fresh env.\n"
             "- GENERATED_V4_K3: new layouts from the unmodified published generator (`run_shelf66_full.py`, K3 requests only) run locally "
             "(laptop lap4 / lap5, gvlab srv5); all passed the same checks.\n")
    R.append("\n## Selection rule\n\n```\n" + sel["rule"] + "\n```\n")
    R.append("\n## K3 source of the selected assignment\n\n" + table([[k, v] for k, v in sel["k3_source_mix"].items()], ["source", "rows"]))
    R.append("\n## Splits\n\n" + table([[k, v.get("train", 0), v.get("val", 0), v.get("test", 0)] for k, v in sel["split_counts"].items()], ["class", "train", "val", "test"]) +
             f"\nNew roots: {sel['split_rule_stats']['inherited_from_manifest_groups']} inherited through manifest groups, {sel['split_rule_stats']['fresh_groups']} new groups by the V1 hash rule; "
             f"conflicts with the frozen manifest: {integ['split_conflicts_with_frozen_manifest']}.\n")
    R.append("\n## Views\n\n- **Hard-order challenge view:** the selected K3 assignment of each layout (`rows`).\n- **Natural-distribution view:** the original "
             "assignment of the same layouts (`natural_assignment` per row; test-split rows give the natural holdout).\n")
    R.append("\n## Training readiness\n\n" + f"**{rd['status']}** (integrity ok: {integ_ok}). No training was started.\n\nCaveats:\n" + "".join(f"- {c}\n" for c in rd["caveats"]))
    (PKG / "FINAL_3D_MAIN_DATASET_REPORT.md").write_text("".join(R))
    S = ["# FINAL 3D K3 order-strength report\n\nStrength = successful orders of the 6 orderings of one K3 assignment, executed sequentially in a FRESH "
         "MuJoCo env (carried arm state, no reset; target planned from the achieved pose = legacy full-task strength). Finalized-X strength = orders whose "
         "relocations + connector to q_ref succeed.\n\n"]
    S.append(table([[f"{s}/6", sel["k3_natural_distribution"].get(f"{s}/6", 0), k3d[f"{s}/6"], TARGET[s], k3_x.get(f"{s}/6", 0)] for s in S6] +
                   [["0/6", sel["k3_natural_distribution"].get("0/6", 0), 0, 0, k3_x.get("0/6", 0)]],
                   ["strength", "natural (original assignment)", "selected (hard-order view, legacy)", "target", "selected, finalized X"]))
    S.append("\nLegacy -> finalized-X strength of the selected K3 rows:\n\n" + table([[k, v] for k, v in st["legacy_vs_x"].items()], ["legacy->X", "rows"]))
    S.append(f"\nPublished K3 originals whose teacher label disagreed with the fresh env on >= 1 order: {sel['stats'].get('original_teacher_fresh_disagree', 0)} "
             "(fresh-env strength used).\n\nNew-layout pool: " + json.dumps(Counter((x['origin'], x['chosen']) for x in sel['new_layout_pool']).most_common(), default=str) + "\n")
    (PKG / "FINAL_3D_K3_STRENGTH_REPORT.md").write_text("".join(S))
    X = ["# FINAL 3D finalized X/Y report\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in lab["definitions"].items() if k != "provenance") + "\n\n"]
    X.append(f"Selected K2 + K3 rows fully finalized (every order X and the endpoint Y resolved): **{n_fin} / {len(k2) + len(k3)}**.\n\n")
    X.append(table([[k, v.get('X=1,Y=1', 0), v.get('X=0,Y=1', 0), v.get('X=1,Y=0', 0), v.get('X=0,Y=0', 0), v.get('missing', 0)] for k, v in xy_tab.items()],
                   ["row kind", "X1 Y1", "X0 Y1", "X1 Y0", "X0 Y0", "missing"]))
    X.append("\nProvenance of X labels (selected assignment orders):\n\n" + table([[k, v] for k, v in Counter(l['x_provenance'] for l in labels if l['row_kind'] == 'SELECTED_ASSIGNMENT_ORDER').most_common()], ["provenance", "orders"]))
    X.append("\nProvenance of Y labels (selected rows):\n\n" + table([[k, v] for k, v in Counter(l['y_provenance'] for l in labels if l['row_kind'] == 'SELECTED_ASSIGNMENT_ORDER' and l['order']).most_common()], ["provenance", "orders"]))
    X.append(f"\nShortcut audit (R2 orders re-executed in full): {dict(aud)}; disagreements: {aud_bad}\n")
    X.append("\nK2 legacy strength " + json.dumps(st['k2_legacy']) + "; K2 finalized-X strength " + json.dumps(st['k2_x']) + "\n")
    (PKG / "FINAL_3D_XY_FINALIZATION_REPORT.md").write_text("".join(X))
    Y = ["# FINAL 3D Y-negative collection report\n\nAll Y-negatives come from EXISTING selected scenes / assignments (no new scenes):\n\n"
         "- **OMISSION_YNEG:** each selected K2 / K3 assignment with one mover omitted (sha256 choice); X for every order of the remaining movers, Y at "
         "that endpoint (minimality predicts Y = 0; Y = 1 would expose a shorter repair).\n- **EMPTY_SEQUENCE_YNEG:** the original scene of every selected "
         "K1 / K2 / K3 / NONE scene (no relocation): T from q_ref is infeasible by the teacher's original check / the NONE certificate; fresh-verified on a sample.\n\n"]
    Y.append(table([[k, v.get('X=1,Y=1', 0), v.get('X=0,Y=1', 0), v.get('X=1,Y=0', 0), v.get('X=0,Y=0', 0), v.get('missing', 0)] for k, v in xy_tab.items()],
                   ["row kind", "X1 Y1", "X0 Y1", "X1 Y0", "X0 Y0", "missing"]))
    tot = Counter(l["y"] for l in labels)
    Y.append(f"\nAll label rows: Y=1 {tot[1]}, Y=0 {tot[0]}, missing {tot[None]} (Y=0 share {tot[0] / max(1, tot[0] + tot[1]):.1%}; "
             f"excluding empty-sequence rows {(tot[0] - xy_tab['EMPTY_SEQUENCE_YNEG']['X=1,Y=0']) / max(1, tot[0] + tot[1] - sum(xy_tab['EMPTY_SEQUENCE_YNEG'][c] for c in ('X=1,Y=0','X=1,Y=1','X=0,Y=0','X=0,Y=1'))):.1%}).\n")
    esv = Counter(v["y"]["y"] for v in es_ver.values() if v.get("y"))
    Y.append(f"\nEmpty-sequence fresh verification sample: {dict(esv)} (expected all 0).\n")
    omy1 = sorted({l["root_id"] for l in labels if l["row_kind"] == "OMISSION_YNEG" and l["y"] == 1})
    Y.append(f"\nOmission endpoints with Y = 1 (a shorter repair exists from q_ref; reported, not hidden): {len(omy1)} roots {omy1[:20]}\n")
    (PKG / "FINAL_3D_Y_NEGATIVE_COLLECTION_REPORT.md").write_text("".join(Y))
    I = ["# FINAL 3D integrity and resource report\n\n## Integrity\n\n```\n" + json.dumps(integ, indent=1) + "\n```\n\n## Resources\n\n```\n" +
         json.dumps(resources, indent=1) + "\n```\n\nParity: laptop vs earlier gvlab evidence 24/24 legacy orders and 3/3 X/Y roots identical; gvlab vs laptop "
         "48/48 fresh-env orders identical (incl. witness ids) before gvlab was used (from 2026-11-11 21:01 IST, user-approved, <= 16 workers).\n"]
    (PKG / "FINAL_3D_INTEGRITY_AND_RESOURCE_REPORT.md").write_text("".join(I))
    with open(PKG / "SHA256SUMS", "w") as f:
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and p.name != "SHA256SUMS":
                f.write(f"{sha(p)}  {p.relative_to(PKG)}\n")
    print(json.dumps({"status": rd["status"], "integrity_ok": integ_ok, "finalized": n_fin, "xy_tab": xy_tab, "k3_x": k3_x, "integ": integ}, default=str)[:3000])


if __name__ == "__main__":
    main()
