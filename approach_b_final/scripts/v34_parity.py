#!/usr/bin/env python3
"""V3.4 P1 parity: portable benchmark.py predictions vs the archived V3.3 exhaustive records (same bundle models) or vs another prediction file.
    v34_parity.py PRED REF [OUT_JSON]     REF = V3.3 slim record (.jsonl.gz, fields D6 / decision_frozen_rule) or a benchmark prediction file
Compares, per root: top-M proposals per object, the decision kind and the selected ordered sequence; reports max |p11| difference."""
import gzip, json, sys


def load(p):
    op = gzip.open if p.endswith(".gz") else open
    return {r["root_id"]: r for r in map(json.loads, op(p, "rt"))}


def norm(r):
    if "decision_frozen_rule" in r:                                       # V3.3 record
        d = r["decision_frozen_rule"]
        seq = None if d is None else d["seq"]
        return {k: v[:4] for k, v in r["D6"].items()}, seq, None if d is None else d["p11"], r["p_noop"]
    seq = None if r["decision"] == "ABSTAIN" else [[m["object_index"], m["destination_cell"]] for m in r["moves"]]
    return r["proposals"], seq, r["score_p11"], r["p_noop"]


A, B = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(A) & set(B))
res = {"n_pred": len(A), "n_ref": len(B), "n_common": len(common), "proposals_equal": 0, "decision_equal": 0, "max_abs_dp11": 0.0,
       "max_abs_dpnoop": 0.0, "mismatch": []}
for k in common:
    pa, sa, qa, na = norm(A[k])
    pb, sb, qb, nb = norm(B[k])
    res["proposals_equal"] += pa == pb
    res["decision_equal"] += sa == sb
    if qa is not None and qb is not None and sa == sb:
        res["max_abs_dp11"] = max(res["max_abs_dp11"], abs(qa - qb))
    res["max_abs_dpnoop"] = max(res["max_abs_dpnoop"], abs(na - nb))
    if sa != sb or pa != pb:
        res["mismatch"].append({"root": k, "proposals_equal": pa == pb, "a": sa, "b": sb, "p11": [qa, qb]})
print(json.dumps({k: v for k, v in res.items() if k != "mismatch"} | {"n_mismatch": len(res["mismatch"]), "first": res["mismatch"][:3]}))
if len(sys.argv) > 3:
    json.dump(res, open(sys.argv[3], "w"), indent=1)
