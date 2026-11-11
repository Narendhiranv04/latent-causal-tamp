#!/usr/bin/env python3
"""K3 strength selection V3 (hard-order challenge view) -- one assignment per K3 layout, never overwriting V2.

Per K3 layout of the V2 selection (2D 1,150; 3D the 357 published): candidates = every fully-resolved, teacher-verified K3 assignment of that
layout (original root, DEPSEEK V1 children, HARDK3 children).  Exactly one is chosen per layout (no layout is counted twice; alternative
parkings of one layout are lineage siblings, never extra scenes).  The choice is an optimal assignment (scipy linear_sum_assignment) of
layouts to target slots T[s] with lexicographic weights: the 6/6 control quota first (protected), then 1/6 > 2/6 > 3/6 > 4/6 > 5/6;
layouts beyond the targets keep their strongest available assignment (overflow, reported).  Ties: fewer changed destinations, then hash.
K0 / K1 / K2 / NONE rows are copied unchanged from V2.  Splits: inherited from the layout (unchanged).

  select_k3.py 2d|3d"""
import glob, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

H = Path(__file__).resolve().parent
G = H.parent
B = G.parent
dom = sys.argv[1]
TARGET = {"2d": {1: 403, 2: 345, 3: 172, 4: 115, 5: 57, 6: 58}, "3d": {1: 125, 2: 107, 3: 54, 4: 36, 5: 18, 6: 17}}[dom]   # 3D: 612-target scaled to 357
TARGET_FULL_3D = {1: 214, 2: 184, 3: 92, 4: 61, 5: 31, 6: 30}
W = {6: 10 ** 7, 1: 10 ** 6, 2: 10 ** 5, 3: 10 ** 4, 4: 10 ** 3, 5: 10 ** 2}
v2 = json.loads((G / "FINAL_DATASET_SELECTION_MANIFESTS" / f"{dom.upper()}_SELECTION_V2.json").read_text())
rows = v2["rows"]
k3 = [r for r in rows if r["K"] == "3"]
lay = {}
for r in k3:
    L = r["root_id"] if r["source"] == "ORIGINAL_SELECTED" else (r["parent_root_id"] if r.get("method") in ("repark2d", "depseek3d_repark") else r["root_id"])
    lay[L] = r
cands = defaultdict(list)          # layout -> [(ns, n_changed, root_id, source, store, method, xy_ok)]
def _jl(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []
CONS = {r["root_id"]: r["consistent"] for r in _jl(H / "consistency2d.jsonl")}           # 2D fresh-cache gate (hardk3 roots)
XY = {r["root_id"]: r for r in _jl(H / f"xy{dom}_all.jsonl") if "error" not in r}       # finalized X/Y check
def xy_ok(rid, ns):                # X contrast reproduces the legacy strength and Y (target from q_ref) succeeds
    r = XY.get(rid)
    return bool(r) and r.get("x_n_success") == ns and (r.get("y") or {}).get("y") == 1
excluded = Counter()
C3 = {r["root_id"]: r.get("consistent") for r in _jl(H / "consistency3d.jsonl")}       # 3D fresh-env gate for pre-hardk3 (V1) children
def v1_3d_ok(rid, meth):
    if dom != "3d" or not str(meth or "").startswith("depseek3d"):
        return True
    if C3.get(rid) is True:
        return True
    excluded["3D_V1_CHILD_FRESH_ENV_" + ("FAIL" if rid in C3 else "UNCHECKED")] += 1
    return False
src = B / ("order_classification_2d/per_scene_six_permutation_outcomes.jsonl" if dom == "2d" else "order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl")
for l in open(src):
    r = json.loads(l)
    if r["root_id"] in lay and r.get("permutations") and all(p["y"] in (0, 1) for p in r["permutations"]) and len(r["permutations"]) == 6:
        ns0 = sum(p["y"] for p in r["permutations"])
        cands[r["root_id"]].append((ns0, 0, r["root_id"], "ORIGINAL", None, None, xy_ok(r["root_id"], ns0)))
for L, r in lay.items():                                  # non-same-layout V2 K3 rows (3D chain child) are their own layout
    if r["source"] != "ORIGINAL_SELECTED" and L == r["root_id"] and v1_3d_ok(r["root_id"], r.get("method")):
        cands[L].append((r["n_success"], 1, r["root_id"], r["source"], r.get("host_store"), r.get("method"), xy_ok(r["root_id"], r["n_success"])))
stores = ([G / "d2/store", H / "d2/store", H / "d2_gvlab/store"] if dom == "2d" else      # smoke stores are never selected
          [G / "d3_gvlab/store", G / "d3_blackwell/store", G / "d3_laptop/store", H / "d3/store"])
for st in stores:
    for f in sorted((st / "roots").glob("*.json")):
        r = json.loads(f.read_text())
        c = r.get("construction", {})
        L = c.get("layout_root_id") or c.get("parent_root_id")
        if r.get("verified_K") != 3 or L not in lay or not c.get("same_layout_as_parent") or len(r.get("permutations", [])) != 6:
            continue
        if any(p["y"] not in (0, 1) for p in r["permutations"]) or r["n_success"] < 1:
            continue
        rid = r["ids"]["root_id"]
        if c.get("method", "").startswith("hardk3"):            # fail-closed teacher-consistency gates
            if dom == "2d" and CONS.get(rid) is not True:
                excluded["2D_CONSISTENCY_" + ("FAIL" if rid in CONS else "UNCHECKED")] += 1
                continue
            if dom == "3d" and r.get("teacher_vs_fresh_env") != "ALL_TEACHER_ORDERS_REPRODUCED":
                excluded["3D_TEACHER_VS_FRESH_ENV_MISSING"] += 1
                continue
        if not v1_3d_ok(rid, c.get("method")):
            continue
        nch = len(c.get("changed_destinations") or [c.get("changed_destination")])
        src_tag = "NEW_HARD_ORDER" if c.get("method", "").startswith("hardk3") else "NEW_DEPENDENCE_SEEKING"
        cands[L].append((r["n_success"], nch, rid, src_tag, str(st), c.get("method"), xy_ok(rid, r["n_success"])))
Ls = sorted(lay)
assert all(cands[L] for L in Ls), "layout without a candidate"
for L in Ls:                                               # duplicate assignments are impossible by root id; keep the first per strength
    best = {}
    for c in sorted(cands[L], key=lambda c: (c[0], not c[6], c[1], hashlib.sha256(c[2].encode()).hexdigest())):
        best.setdefault(c[0], c)
    cands[L] = sorted(best.values())
slots = [s for s in range(1, 7) for _ in range(TARGET[s])]
n = len(Ls)
BIG = 10 ** 12
cost = np.full((n, len(slots) + 6 * n), BIG, dtype=np.float64)
for i, L in enumerate(Ls):
    have = {c[0]: c for c in cands[L]}
    for j, s in enumerate(slots):
        if s in have:
            cost[i, j] = -W[s] + have[s][1] - 5 * have[s][6]
    for s in have:                                          # overflow: keep the strongest available (tiny preference for low ns)
        cost[i, len(slots) + (s - 1) * n:len(slots) + s * n] = s
r_, c_ = linear_sum_assignment(cost)
assert (cost[r_, c_] < BIG).all()
chosen = {}
for i, j in zip(r_, c_):
    s = slots[j] if j < len(slots) else (j - len(slots)) // n + 1
    chosen[Ls[i]] = {c[0]: c for c in cands[Ls[i]]}[s]
out_rows, dist = [], Counter()
for r in rows:
    if r["K"] != "3":
        out_rows.append(r)
for L in Ls:
    ns, nch, rid, srct, st, meth, xyk = chosen[L]
    dist[ns] += 1
    out_rows.append({"root_id": rid, "K": "3", "order_class": "ORDER_DEPENDENT" if ns < 6 else "ORDER_INDEPENDENT", "n_success": ns, "n_orders": 6,
                     "source": "ORIGINAL_SELECTED" if srct == "ORIGINAL" else srct, "layout_root_id": L, "host_store": st, "method": meth,
                     "split": lay[L]["split"], "xy_verified_same_strength": xyk,
                     "xy_checked": rid in XY, "alternatives_available": sorted(c[0] for c in cands[L])})
avail = Counter(s for L in Ls for s in {c[0] for c in cands[L]})
res = {"version": f"{dom.upper()}_K3_STRENGTH_SELECTION_V3", "baseline_kept": f"{dom.upper()}_SELECTION_V2 (unchanged file)",
       "rule": __doc__.split("\n\n")[1], "targets": TARGET, "selected_distribution": {f"{s}/6": dist[s] for s in range(1, 7)},
       "deficit_vs_target": {f"{s}/6": TARGET[s] - dist[s] for s in range(1, 7)},
       "layouts_with_option": {f"{s}/6": avail[s] for s in range(1, 7)}, "n_layouts": n, "excluded_by_gates": dict(excluded),
       "xy_checked_selected": sum(1 for L in Ls if chosen[L][2] in XY), "xy_verified_selected": sum(1 for L in Ls if chosen[L][6]), "rows": out_rows}
if dom == "3d":
    res["targets_full_612"] = TARGET_FULL_3D
    res["note"] = "published 357 K3 layouts only; the teammate's 255 unpublished K3 roots are not counted until published and verified"
p = H / f"{dom.upper()}_K3_STRENGTH_SELECTION_V3.json"
p.write_text(json.dumps(res, indent=0))
print(dom, "selected", dict(sorted(dist.items())), "deficit", res["deficit_vs_target"], "avail", dict(sorted(avail.items())),
      "excluded", dict(excluded), "rows", len(out_rows), Counter(r["source"] for r in out_rows if r["K"] == "3"))
