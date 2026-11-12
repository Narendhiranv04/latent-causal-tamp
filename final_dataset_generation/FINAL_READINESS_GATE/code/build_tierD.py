#!/usr/bin/env python3
"""Tier D replay items: every R2_FRESH_LEGACY_RELOCATION_FAILURE row and every R1_GVLAB_XY3D_V3 positive (X = 1 rows, Y = 1 endpoints) of the selected
K2/K3 rows not already in tiers A/B (rpl3d_items.json); all are RERUN (finalized teacher, fresh process) + REPLAY.
  build_tierD.py OUT.json"""
import collections as C, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.argv = [sys.argv[0], str(H.parent / "work/_tmp_ab.json"), "150"] + sys.argv[1:]
out = sys.argv[3]
sys.argv = sys.argv[:3]
exec(open(H / "build_rpl3d.py").read().split("if len(sys.argv) > 3:")[0])      # reuse the loaders / helpers (no writes before this point)
ab = json.loads((H.parent / "work/rpl3d_items.json").read_text())
inab = {(i["root_id"], q["qid"]) for i in ab for q in i["queries"]}
tD = C.defaultdict(dict)
for l in sel_rows:
    p = l["x_provenance"]
    qid = "X_SEL_" + okey(l["relocations"])
    if (l["root_id"], qid) in inab:
        continue
    if p.startswith("R2") or (p.startswith("R1") and l["x"] == 1):
        tD[l["root_id"]][qid] = xq(l, "D_RERUN_REPLAY")
for rid in by_root:
    y, w = y_sel(rid)
    if w is None and y == 1 and (rid, "Y_SEL") not in inab:
        tD[rid]["Y_SEL"] = {"q": "Y", "row_kind": "SELECTED_ASSIGNMENT_ORDER", "K": by_root[rid][0]["K"], "split": by_root[rid][0]["split"],
                            "cells": cells_of(rid, by_root[rid][0]["relocations"]), "label_y": y, "witnesses": None,
                            "y_provenance": by_root[rid][0]["y_provenance"], "tags": ["D_RERUN_REPLAY"]}
itd = [{"key": f"RPD_{rid}", "root_id": rid, "path": str(rpath(rid)), "root_sha256": sel[rid].get("root_sha256"),
        "queries": [dict(q, qid=qid) for qid, q in sorted(qs.items())]} for rid, qs in sorted(tD.items()) if qs]
Path(out).write_text(json.dumps(itd))
qd = [q for i in itd for q in i["queries"]]
print("TIER D roots", len(itd), "queries", len(qd), C.Counter((q["q"], q.get("x_provenance", q.get("y_provenance", "")).split("(")[0], q.get("label_x", q.get("label_y"))) for q in qd))
