#!/usr/bin/env python3
"""Hard-order (HARDK3_3D_V1) jobs for K3 layouts that have no hard-order search yet: the 50 DEPENDENT verified-K3 candidates, the 160
K3 layouts published after snapshot A, and (when given) locally generated K3 layouts.  Start = the layout's original assignment with its
FRESH-env 6-order outcomes (stage-1 legacy results); layouts already at 1/6 or with an unresolved order get no job.
Order: DEPENDENT / generated first (they are new scenes), then published by start strength 3, 4, 5, 2, 6 (V3 yield order), then hash.
  build_hard.py OUT.json [GENERATED_LEGACY.jsonl ...]"""
import hashlib, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent; W = H.parent / "work"
SRC = Path("/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass")
old = json.loads((H.parent.parent / "snapshot_a_root_sha256.json").read_text())
items = {i["key"]: i for i in json.loads((W / "stage1_legacy.json").read_text())}
res = [json.loads(l) for f in [W / "stage1_legacy.jsonl"] + [Path(x) for x in sys.argv[2:]] for l in open(f)]
fixed = {json.loads(l)["root_id"]: json.loads(l) for f in [W / "stage1_fixed.jsonl"] + [Path(x).with_name(Path(x).name.replace("legacy", "fixed")) for x in sys.argv[2:]]
         if f.exists() for l in open(f)}
jobs = []
for r in res:
    rid = r["root_id"]
    origin = items[r["key"]]["origin"] if r["key"] in items else "GENERATED_K3"
    if origin == "PUBLISHED_K2" or (origin == "PUBLISHED_K3" and rid in old):
        continue
    if origin != "PUBLISHED_K3" and (fixed.get(rid, {}).get("fixed_objects") != [] or fixed.get(rid, {}).get("resolution") != "EVALUATED"):
        continue
    o = r["orders"]
    if len(o) != 6 or any(x.get("resolution") != "EVALUATED" for x in o):
        continue
    ns = sum(x["y"] for x in o)
    if ns <= 1:
        continue
    assign = sorted([od[0], list(od[1])] for od in o[0]["order"])
    jobs.append({"job_id": f"HJ3d_v4_{rid}", "layout": rid, "origin": origin, "start_id": rid, "start_ns": ns, "start_assign": assign,
                 "start_succ": [[od[0] for od in x["order"]] for x in o if x["y"] == 1],
                 "known_keys": [json.dumps(sorted([a, list(d)] for a, d in assign))], "variant": "v4"})
pri = {3: 0, 4: 1, 5: 2, 2: 3, 6: 4}
jobs.sort(key=lambda j: (j["origin"] == "PUBLISHED_K3", pri[j["start_ns"]], hashlib.sha256(j["layout"].encode()).hexdigest()))
Path(sys.argv[1]).write_text(json.dumps(jobs))
import collections as C
print("jobs", len(jobs), C.Counter((j["origin"], j["start_ns"]) for j in jobs))
