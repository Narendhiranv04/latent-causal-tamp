#!/usr/bin/env python3
"""V3.4 P4 ground truth: eval_noop = (K0 root and teacher Y(empty) == 1) from the unchanged-teacher cache; Y(empty) missing/UNKNOWN -> None
(excluded from the NOOP denominator, reported).  v34_gt.py PRIVATE_IN CACHE_DIR DOM PRIVATE_OUT"""
import collections, json, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
import benchmark as BM
pin, cache, dom, pout = sys.argv[1:5]
L, _ = BM.cache_labels(cache, dom)
c = collections.Counter()
with open(pout, "w") as f:
    for e in map(json.loads, open(pin)):
        if e["K"] == "0":
            x, y = L.get((e["root_id"], "[]"), (None, None))
            e["masks"]["eval_noop"] = None if y is None else bool(y == 1)
            e["y_empty"] = y
            c["k0_y1" if y == 1 else "k0_y0" if y == 0 else "k0_unknown"] += 1
        else:
            e["masks"]["eval_noop"] = False
        f.write(json.dumps(e) + "\n")
print(json.dumps({"dom": dom, **c}))
