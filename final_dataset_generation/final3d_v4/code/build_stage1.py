#!/usr/bin/env python3
"""Stage 1 work lists: fresh-env legacy orders for every K3 candidate layout (517 published + 50 DEPENDENT verified-K3) and every
published K2 (612), skipping orders that already have FRESH-env results (laptop classification 'new' perms); fixed-object check
for the 50 DEPENDENT candidates.  Writes work/stage1_legacy.json, work/stage1_fixed.json, work/intake.json."""
import itertools, json, hashlib
from pathlib import Path
H = Path(__file__).resolve().parent; W = H.parent / "work"; G = H.parent.parent; B = G.parent
SRC = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
sel = json.loads((SRC / "selected.json").read_text())["selected"]
led = [json.loads(l) for l in open(SRC / "raw/ledger.jsonl")]
dep = sorted(r["root_id"] for r in led if r.get("observed") == "DEPENDENT" and r.get("verified_K") == 3)
cls = {c["root_id"]: c for c in map(json.loads, open(B / "order_classification_3d/3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl"))}
items, fixed = [], []
def add(rid, K, origin):
    p = SRC / "raw/roots" / f"{rid}.json"
    r = json.loads(p.read_text())
    mini = next(b for b in r["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
    assert len(mini["sequence"]) == K, (rid, K)
    fresh = {json.dumps(pp["order"]) for pp in (cls.get(rid, {}).get("permutations") or []) if pp["source"] == "new"}
    orders = [list(map(list, q)) for q in itertools.permutations([[o, list(d)] for o, d in mini["sequence"]])]
    need = [o for o in orders if json.dumps(o) not in fresh]
    if need:
        items.append({"key": f"L_{rid}", "path": str(p), "orders": need, "K": K, "origin": origin})
for rid in dep:
    add(rid, 3, "DEPENDENT_K3"); fixed.append({"key": f"F_{rid}", "path": str(SRC / "raw/roots" / f"{rid}.json")})
for rid in sel["3"]:
    add(rid, 3, "PUBLISHED_K3")
for rid in sel["2"]:
    add(rid, 2, "PUBLISHED_K2")
pri = {"DEPENDENT_K3": 0, "PUBLISHED_K3": 1, "PUBLISHED_K2": 2}
items.sort(key=lambda x: (pri[x["origin"]], -len(x["orders"]), x["key"]))
(W / "stage1_legacy.json").write_text(json.dumps(items)); (W / "stage1_fixed.json").write_text(json.dumps(fixed))
print(len(items), "roots", sum(len(i["orders"]) for i in items), "orders", {o: sum(1 for i in items if i["origin"] == o) for o in pri}, "fixed", len(fixed))
