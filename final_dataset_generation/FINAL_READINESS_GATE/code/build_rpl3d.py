#!/usr/bin/env python3
"""Replay items for rpl3d.py from FINAL_3D_DATASET_V4 (label manifest + selection manifest) and the final3d_v4 work files (Y witnesses,
resolved exactly as make_final3d.py resolves them).  Strata (written into every query as "tags"):
  M_OMISSION13   every OMISSION_YNEG row with Y = 1 (13 roots), their omission Y, a LEGACY diagnostic of each shortened order, and ALL selected
                 rows + selected Y of those 13 roots (superset of "every selected row affected by a confirmed inconsistency").
  M_SELY0        both selected roots whose finalized Y = 0 (all their orders + Y).
  S_SEL          stratified sample of SELECTED_ASSIGNMENT_ORDER rows: >= quota per (K, split, X, Y), (K3 finalized-X strength, split),
                 (X provenance, X), (failure phase), (source family, K), then a seeded random fill; Y of every sampled root.
  S_OM           stratified sample of OMISSION_YNEG rows by (K, split, X, Y) + their omission Y.
  build_rpl3d.py OUT_ITEMS.json [N_FILL]"""
import collections as C, json, random, sys
from pathlib import Path

H = Path(__file__).resolve().parent
G = H.parent.parent
PKG, W = G / "FINAL_3D_DATASET_V4", G / "final3d_v4/work"
SRC = Path("/home/naren/Desktop/rss3d_final_src")


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def okey(order):
    return "".join(o[-1] for o, _ in order)


labels = json.loads((PKG / "FINAL_3D_XY_LABEL_MANIFEST.json").read_text())["rows"]
sel = {r["root_id"]: r for r in json.loads((PKG / "FINAL_3D_SELECTION_MANIFEST.json").read_text())["rows"]}
res, items_w = {}, {}
for f in ("k2_xy_yneg.jsonl", "xy_final_laptop.jsonl", "xy_final_gvlab.jsonl", "xy_assist_laptop.jsonl", "es_verify.jsonl"):
    for r in jl(W / f):
        res[r["key"]] = r
for f in ("xy_items.json", "yneg_items.json", "xy_shortcut_audit.json", "xy_items_k2.json", "yneg_items_k2.json"):
    if (W / f).exists():
        for i in json.loads((W / f).read_text()):
            items_w[i["key"]] = i
reuse = json.loads((W / "xy_reuse.json").read_text())
ycache = {}
for k, r in res.items():
    it = items_w.get(k)
    if r.get("y") and it and it.get("y_key") and r["y"].get("y") in (0, 1):
        ycache.setdefault(it["y_key"], {"y": r["y"]["y"], "witnesses": r["y"].get("witnesses"), "status": r["y"].get("status")})


def rpath(rid):
    p = Path(sel[rid]["path"])
    return p if p.is_absolute() else SRC / p


def cells_of(rid, relocs):
    rec = json.loads(rpath(rid).read_text())
    return {**{k: list(v) for k, v in rec["initial_cells"].items()}, **{o: list(d) for o, d in relocs}}


def y_sel(rid):
    ru = reuse.get(rid, {})
    if ru.get("y"):
        return ru["y"]["y"], None                                   # R1: no stored Y witness -> RERUN
    yc = ycache[ru["y_key"]]
    return yc["y"], yc["witnesses"] or []


def y_om(rid):
    r, it = res.get(f"YN_{rid}"), items_w[f"YN_{rid}"]
    if r and r.get("y") and r["y"].get("y") in (0, 1):
        return r["y"]["y"], r["y"].get("witnesses") or []
    yc = ycache[it["y_key"]]
    return yc["y"], yc["witnesses"] or []


def xq(l, tag):
    return {"q": "X", "row_kind": l["row_kind"], "K": l["K"], "split": l["split"], "order": l["relocations"], "label_x": l["x"],
            "label_phase": l.get("x_phase"), "x_provenance": l["x_provenance"], "label_y": l["y"],
            "witnesses": l.get("x_witnesses") if l["x_provenance"].startswith("FIN3D") else None, "tags": [tag]}


sel_rows = [l for l in labels if l["row_kind"] == "SELECTED_ASSIGNMENT_ORDER"]
om_rows = [l for l in labels if l["row_kind"] == "OMISSION_YNEG"]
by_root = C.defaultdict(list)
for l in sel_rows:
    by_root[l["root_id"]].append(l)
strength = {rid: sum(x["x"] for x in ls) for rid, ls in by_root.items()}
queries = C.defaultdict(dict)                                       # rid -> {qid: query}


def add(rid, qid, q):
    if qid in queries[rid]:
        queries[rid][qid]["tags"] = sorted(set(queries[rid][qid]["tags"]) | set(q["tags"]))
    else:
        queries[rid][qid] = q


def add_sel_y(rid, tag):
    y, w = y_sel(rid)
    relocs = by_root[rid][0]["relocations"]
    add(rid, "Y_SEL", {"q": "Y", "row_kind": "SELECTED_ASSIGNMENT_ORDER", "K": by_root[rid][0]["K"], "split": by_root[rid][0]["split"],
                       "cells": cells_of(rid, relocs), "label_y": y, "witnesses": w,
                       "y_provenance": by_root[rid][0]["y_provenance"], "tags": [tag]})


def add_sel_x(l, tag):
    add(l["root_id"], "X_SEL_" + okey(l["relocations"]), xq(l, tag))


def add_om(l, tag, legacy=False):
    rid = l["root_id"]
    add(rid, "X_OM_" + okey(l["relocations"]), xq(l, tag))
    y, w = y_om(rid)
    add(rid, "Y_OM", {"q": "Y", "row_kind": "OMISSION_YNEG", "K": l["K"], "split": l["split"], "cells": cells_of(rid, l["relocations"]),
                      "label_y": y, "witnesses": w, "omitted": l["omitted"], "tags": [tag]})
    if legacy:
        add(rid, "L_OM_" + okey(l["relocations"]), {"q": "LEGACY", "order": l["relocations"], "omitted": l["omitted"], "tags": [tag]})


om13 = sorted({l["root_id"] for l in om_rows if l["y"] == 1})
for l in om_rows:
    if l["root_id"] in om13:
        add_om(l, "M_OMISSION13", legacy=True)
for rid in om13:
    for l in by_root[rid]:
        add_sel_x(l, "M_OMISSION13")
    add_sel_y(rid, "M_OMISSION13")
sely0 = sorted({l["root_id"] for l in sel_rows if l["y"] == 0})
for rid in sely0:
    for l in by_root[rid]:
        add_sel_x(l, "M_SELY0")
    add_sel_y(rid, "M_SELY0")

rng = random.Random(20261112)
pool = [l for l in sel_rows if l["root_id"] not in set(om13) | set(sely0)]
rng.shuffle(pool)
fam = lambda l: sel[l["root_id"]]["source"]
pcls = lambda l: "none" if l["x"] == 1 else (l.get("x_phase") or "?")
prov = lambda l: l["x_provenance"].split("(")[0]
dims = [(lambda l: ("KSXY", l["K"], l["split"], l["x"], l["y"]), 8),
        (lambda l: ("STR", strength[l["root_id"]], l["split"]) if l["K"] == "3" else None, 6),
        (lambda l: ("PROV", prov(l), l["x"]), 12),
        (lambda l: ("PHASE", l["K"], pcls(l)), 10),
        (lambda l: ("FAM", fam(l), l["K"]), 6)]
picked, cnt = [], C.Counter()
for l in pool:
    keys = [(f(l), q) for f, q in dims if f(l) is not None]
    if any(cnt[k] < q for k, q in keys):
        picked.append(l)
        for k, _ in keys:
            cnt[k] += 1
n_fill = int(sys.argv[2]) if len(sys.argv) > 2 else 150
rest = [l for l in pool if l not in picked]
picked += rest[:n_fill]
for l in picked:
    add_sel_x(l, "S_SEL")
    add_sel_y(l["root_id"], "S_SEL")
ompool = [l for l in om_rows if l["root_id"] not in om13]
rng.shuffle(ompool)
oc = C.Counter()
for l in ompool:
    k = (l["K"], l["split"], l["x"], l["y"])
    if oc[k] < 5:
        oc[k] += 1
        add_om(l, "S_OM")
if len(sys.argv) > 3:                                               # tier C: every remaining witness-backed label (no reruns)
    tierC = C.defaultdict(dict)
    for l in sel_rows:
        if l["x_provenance"].startswith("FIN3D"):
            qid = "X_SEL_" + okey(l["relocations"])
            if qid not in queries[l["root_id"]]:
                tierC[l["root_id"]][qid] = xq(l, "C_ALL_WITNESSED")
    for rid in by_root:
        y, w = y_sel(rid)
        if w is not None and "Y_SEL" not in queries[rid]:
            tierC[rid]["Y_SEL"] = {"q": "Y", "row_kind": "SELECTED_ASSIGNMENT_ORDER", "K": by_root[rid][0]["K"], "split": by_root[rid][0]["split"],
                                   "cells": cells_of(rid, by_root[rid][0]["relocations"]), "label_y": y, "witnesses": w,
                                   "y_provenance": by_root[rid][0]["y_provenance"], "tags": ["C_ALL_WITNESSED"]}
    for l in om_rows:
        rid = l["root_id"]
        qid = "X_OM_" + okey(l["relocations"])
        if qid not in queries[rid]:
            tierC[rid][qid] = xq(l, "C_ALL_WITNESSED")
        if "Y_OM" not in queries[rid] and "Y_OM" not in tierC[rid]:
            y, w = y_om(rid)
            tierC[rid]["Y_OM"] = {"q": "Y", "row_kind": "OMISSION_YNEG", "K": l["K"], "split": l["split"], "cells": cells_of(rid, l["relocations"]),
                                  "label_y": y, "witnesses": w, "omitted": l["omitted"], "tags": ["C_ALL_WITNESSED"]}
    itc = [{"key": f"RPC_{rid}", "root_id": rid, "path": str(rpath(rid)), "root_sha256": sel[rid].get("root_sha256"),
            "queries": [dict(q, qid=qid) for qid, q in sorted(qs.items())]} for rid, qs in sorted(tierC.items()) if qs]
    Path(sys.argv[3]).write_text(json.dumps(itc))
    qc = [q for it in itc for q in it["queries"]]
    print("TIER C roots", len(itc), "queries", len(qc), C.Counter((q["q"], q["row_kind"], q["label_x"] if q["q"] == "X" else q["label_y"]) for q in qc),
          "reruns", sum(1 for q in qc if q["witnesses"] is None))
items = [{"key": f"RP3_{rid}", "root_id": rid, "path": str(rpath(rid)), "root_sha256": sel[rid].get("root_sha256"),
          "queries": [dict(q, qid=qid) for qid, q in sorted(qs.items())]} for rid, qs in sorted(queries.items()) if qs]
Path(sys.argv[1]).write_text(json.dumps(items))
qs = [q for it in items for q in it["queries"]]
print("roots", len(items), "queries", len(qs), C.Counter((q["q"], q.get("row_kind", "-"), tuple(q["tags"])) for q in qs))
print("rerun X", sum(1 for q in qs if q["q"] == "X" and q["witnesses"] is None), "rerun Y", sum(1 for q in qs if q["q"] == "Y" and q["witnesses"] is None))
print("sample strata covered", len(cnt), "selected rows sampled", len(picked))

# ---- tier D (separate invocation: build_rpl3d.py --tierD OUT): re-run + replay every R2 row and every R1 positive (X = 1 rows, Y = 1 endpoints)
#      not already in tiers A/B, so that no 3D label rests on a legacy-derived substitution and every positive label is physically replayed.
