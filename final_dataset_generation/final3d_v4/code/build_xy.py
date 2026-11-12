#!/usr/bin/env python3
"""Finalized X/Y work for the FINAL_3D_SELECTION_V4 K2 / K3 rows, and the Y-negative (omission) work, from EXISTING selected assignments.

X per order of the selected assignment (K3: 6, K2: 2); Y once per endpoint (shared by the orders of one assignment; cached by endpoint).
Reuse (never re-labelled, provenance recorded):
  R1  gvlab xy3d results for HARDK3 V3 roots (laptop/gvlab parity: 3/3 roots identical on every X order and Y);
  R2  X = 0 at relocation j when a FRESH-env legacy evaluation of the same order failed at relocation j (identical relocation code path;
      728/728 agreement on the V3 roots); a random 5 % of these orders is re-executed in full as an audit (SHORTCUT_AUDIT items).
Y-negatives (OMISSION_V1): for every selected K3 row, omit one mover (sha256(root|omit) picks it); X for BOTH orders of the two remaining
movers, Y at that endpoint.  For every selected K2 row, omit one mover; X for the remaining one, Y at that endpoint.
  build_xy.py SELECTION.json"""
import hashlib, itertools, json, random, sys
from pathlib import Path

H = Path(__file__).resolve().parent; W = H.parent / "work"; G = H.parent.parent


def hh(s):
    return hashlib.sha256(s.encode()).hexdigest()


def ykey(rec, cells):
    return hh(json.dumps([sorted((o["id"], o["shape"], round(o["size"], 6), round(o["height"], 6)) for o in rec["objects"]),
                          sorted((k, list(v)) for k, v in cells.items()), list(rec["goal"])]))


def okeys(order):
    return "".join(o[-1] for o, _ in order)


sel = json.loads(Path(sys.argv[1]).read_text())
gx = {json.loads(l)["root_id"]: json.loads(l) for l in open(G / "k3_hard/xy3d_all.jsonl")}
rng = random.Random(20261111)
xy_items, yneg_items, reuse, audit = [], [], {}, []
yseen = {}
for row in sel["rows"]:
    if row["K"] not in ("2", "3"):
        continue
    p = Path(row["path"]) if Path(row["path"]).is_absolute() else Path("/home/naren/Desktop/rss3d_final_src") / row["path"]
    rec = json.loads(p.read_text())
    rid = rec["ids"]["root_id"]
    mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
    assign = [[o, list(d)] for o, d in mini["sequence"]]
    cells = {**rec["initial_cells"], **{o: d for o, d in assign}}
    leg = {okeys(x["order"]): x for x in row.get("legacy_orders") or []}
    ent = {"root_id": rid, "K": row["K"], "orders": {}, "y": None}
    x_orders = []
    for q in itertools.permutations(assign):
        k = okeys(q)
        if rid in gx and k in gx[rid]["x"]:
            ent["orders"][k] = {"x": gx[rid]["x"][k]["x"], "phase": gx[rid]["x"][k].get("phase"), "provenance": "R1_GVLAB_XY3D_V3"}
            continue
        lg = leg.get(k)
        fresh = lg and lg.get("source") in ("fresh_env", "audit", "new") and lg.get("y") == 0 and isinstance(lg.get("failed_step"), int)
        if fresh:
            ent["orders"][k] = {"x": 0, "phase": f"relocation:{lg['failed_step']}", "provenance": "R2_FRESH_LEGACY_RELOCATION_FAILURE"}
            if rng.random() < 0.05:
                audit.append({"key": f"A_{rid}_{k}", "path": str(p), "x_orders": [list(q)], "y": None, "expect_phase": f"relocation:{lg['failed_step']}"})
            continue
        x_orders.append(list(q))
    if rid in gx:
        ent["y"] = {"y": gx[rid]["y"]["y"], "provenance": "R1_GVLAB_XY3D_V3"}
    yk = ykey(rec, cells)
    need_y = ent["y"] is None and yk not in yseen
    if ent["y"] is None:
        ent["y_key"] = yk
        yseen.setdefault(yk, rid)
    reuse[rid] = ent
    if x_orders or need_y:
        xy_items.append({"key": f"XY_{rid}", "path": str(p), "x_orders": x_orders, "y": {"cells": cells} if need_y else None, "y_key": yk})
    # ---- omission Y-negatives
    movers = sorted(o for o, _ in assign)
    om = movers[int(hh(rid + "|omit")[:8], 16) % len(movers)]
    rest = [a for a in assign if a[0] != om]
    cells_o = {**rec["initial_cells"], **{o: d for o, d in rest}}
    yko = ykey(rec, cells_o)
    yneg_items.append({"key": f"YN_{rid}", "path": str(p), "root_id": rid, "K": row["K"], "omitted": om,
                       "x_orders": [list(q) for q in itertools.permutations(rest)], "y": {"cells": cells_o} if yko not in yseen else None, "y_key": yko})
    yseen.setdefault(yko, rid)
(W / "xy_items.json").write_text(json.dumps(xy_items)); (W / "yneg_items.json").write_text(json.dumps(yneg_items))
(W / "xy_reuse.json").write_text(json.dumps(reuse)); (W / "xy_shortcut_audit.json").write_text(json.dumps(audit))
print("xy items", len(xy_items), "x orders to run", sum(len(i["x_orders"]) for i in xy_items), "y to run", sum(1 for i in xy_items if i["y"]),
      "| reused orders", sum(1 for e in reuse.values() for o in e["orders"].values()),
      "| yneg items", len(yneg_items), "x", sum(len(i["x_orders"]) for i in yneg_items), "y", sum(1 for i in yneg_items if i["y"]), "| shortcut audit", len(audit))
