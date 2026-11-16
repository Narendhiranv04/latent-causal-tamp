"""Exhaustive-inference host parity: for every root in the host file, every M and all 72 rules, the selected sequence must equal the reference
(V3.2-A laptop) record, and its p11 must agree within TOL; also n_scored / counts / known-success-in-pool.  usage: ex_parity.py REF.jsonl HOST.jsonl"""
import json, sys
TOL = 1e-4
ref = {json.loads(l)["root_id"]: json.loads(l) for l in open(sys.argv[1])}
n = same = 0; dp = 0.0; bad = []
for l in open(sys.argv[2]):
    h = json.loads(l); r = ref[h["root_id"]]
    for M in h["per_M"]:
        a, b = r["per_M"][M], h["per_M"][M]
        assert a["counts_by_K"] == b["counts_by_K"] and a["n_scored"] == b["n_scored"] and a["known_success_in_pool"] == b["known_success_in_pool"], h["root_id"]
        for x, y in zip(a["decisions"], b["decisions"]):
            n += 1
            sx, sy = (None if x is None else x["seq"]), (None if y is None else y["seq"])
            if sx == sy:
                same += 1
                if x is not None and y is not None:
                    dp = max(dp, abs(x["p11"] - y["p11"]))
            else:
                bad.append((h["root_id"], M, sx, sy))
print(json.dumps({"roots": sum(1 for _ in open(sys.argv[2])), "decisions": n, "identical": same, "max_abs_dp11": dp, "mismatch": bad[:5],
                  "status": "PASS" if same == n and dp < TOL else "FAIL"}))
