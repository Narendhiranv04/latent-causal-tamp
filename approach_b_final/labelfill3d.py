#!/usr/bin/env python3
"""3D label completion (disclosed, protocol-identical): finalized X/Y for the 357 selected 3D K1 roots and finalized Y at the unedited scene of the
511 K0 roots, which FINAL_3D_DATASET_V4 left as legacy-only.  Teacher unchanged: final3d_v4 fin3d.py `xy` mode (X = the minimal assignment's
relocation + CONNECTOR_TO_QREADY_V1; Y = BD3DS66_Y_PLAN_V1 at the endpoint from q_ref), into a separate witness store; then every result is
replayed by FINAL_READINESS_GATE rpl3d.py.  Nothing existing is relabelled.

    python labelfill3d.py items SNAPSHOT_DIR OUT_ITEMS.json        fin3d xy items (paths = verified mirror roots)
    python labelfill3d.py replay-items ITEMS.json FIN3D_OUT.jsonl OUT.json    rpl3d items for the new labels"""
import json, sys
from pathlib import Path

MIR = Path("/scratch/nav/approachb_final/mirror")


def items(snap, out):
    rows = [json.loads(l) for l in open(Path(snap) / "data3d.jsonl")]
    sel = {r["root_id"]: r for r in json.loads((MIR / "boltzmann_lfd/final_dataset_generation/FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json").read_text())["rows"]}
    res = []
    for r in rows:
        if r["K_legacy"] not in ("0", "1"):
            continue
        p = sel[r["root_id"]]["path"]
        path = MIR / "rss3d_final_src" / p
        rec = json.loads(path.read_text())
        cells = {k: list(v) for k, v in rec["initial_cells"].items()}
        if r["K_legacy"] == "1":
            mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
            order = [[o, list(d)] for o, d in mini["sequence"]]
            res.append({"key": f"LF_{r['root_id']}", "path": str(path), "x_orders": [order], "y": {"cells": {**cells, **{o: d for o, d in order}}}, "K": "1"})
        else:
            res.append({"key": f"LF_{r['root_id']}", "path": str(path), "x_orders": [], "y": {"cells": cells}, "K": "0"})
    Path(out).write_text(json.dumps(res))
    print(len(res), sum(1 for i in res if i["K"] == "1"), sum(1 for i in res if i["K"] == "0"))


def replay_items(items_json, fin_out, out):
    path = {i["key"]: i["path"] for i in json.loads(Path(items_json).read_text())}
    res = []
    for l in open(fin_out):
        r = json.loads(l)
        q = []
        for x in r.get("x", []):
            if x.get("resolution") == "EVALUATED":
                q.append({"q": "X", "qid": "X_K1", "row_kind": "LABELFILL_K1", "order": x["order"], "label_x": x["x"], "label_phase": x.get("phase"),
                          "x_provenance": "FIN3D_X_GVLAB_LABELFILL", "witnesses": x.get("witnesses") or [], "tags": ["F_LABELFILL"]})
        y = r.get("y") or {}
        if y.get("resolution") == "EVALUATED":
            q.append({"q": "Y", "qid": "Y_LF", "row_kind": "LABELFILL", "cells": y["cells"], "label_y": y["y"], "witnesses": y.get("witnesses") or [],
                      "tags": ["F_LABELFILL"]})
        res.append({"key": "RPF_" + r["root_id"], "root_id": r["root_id"], "path": path[r["key"]], "queries": q})
    Path(out).write_text(json.dumps(res))
    print(len(res), sum(len(i["queries"]) for i in res))


if __name__ == "__main__":
    {"items": lambda: items(sys.argv[2], sys.argv[3]), "replay-items": lambda: replay_items(sys.argv[2], sys.argv[3], sys.argv[4])}[sys.argv[1]]()
