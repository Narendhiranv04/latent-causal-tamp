#!/usr/bin/env python3
"""R10.1 independent recount of the R9 R8C composition outcomes from the raw sealed records (gvlab2): seals, job coverage, no retries,
success = X=1 and Y=1 and continuous replay, actual executed lengths; compared with the R9 report numbers.
    python3 audit_r9.py R8C_DIR R8C_CTRL_DIR R8B_PRIVATE OUT.json"""
import collections, hashlib, json, sys
from pathlib import Path
REPORTED = {"main": {"B0": 8, "H3": 23, "FLAT-INSERT": 48, "REC-ORDERED": 59, "GA": 64}, "ctrl": {"REC-ORDERED": 14, "GA": 8},
            "long": {"REC-ORDERED": (32, 15), "GA": (40, 20)}, "jobs": {"main": 449, "ctrl": 194}}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
jl = lambda p: [json.loads(l) for l in open(p)]  # noqa: E731


def count(d, priv):
    d = Path(d)
    seals = {"plans": sha(d / "plans_r8b.jsonl") == (d / "plans_r8b.jsonl.SEAL").read_text().strip(),
             "selection": sha(d / "selection_r8b.json") == (d / "selection_r8b.json.SEAL").read_text().strip()}
    js = (d / "jobs_r8b.json.SEAL").read_text().strip()
    seals["jobs"] = sha(d / "jobs_r8b.json") in js or js.startswith(sha(d / "jobs_r8b.json")[:16]) or json.loads(js).get("sha256") == sha(d / "jobs_r8b.json") if js.startswith("{") else sha(d / "jobs_r8b.json") == js
    jobs = json.loads((d / "jobs_r8b.json").read_text())
    phys = jl(d / "phys_r8b.jsonl")
    keys = collections.Counter(r["key"] for r in phys)
    R = {r["key"]: r for r in phys}
    sel = json.loads((d / "selection_r8b.json").read_text())
    P = {r["root_id"]: r for r in jl(d / "plans_r8b.jsonl")}
    out = {"seals": seals, "n_jobs": len(jobs), "n_phys": len(phys), "duplicate_phys_keys(retries)": sum(v > 1 for v in keys.values()),
           "jobs_without_record": sum(1 for j in jobs if j["key"] not in R), "roots": len(P), "arms": {}}
    per = collections.defaultdict(lambda: collections.Counter())
    for s in sel:
        a = s["arm"]; per[a]["n"] += 1
        p = P[s["root_id"]]["arms"][a]
        assert p["seq"] == s["seq"], "selection differs from sealed plan"
        if s["status"] == "NO_REPAIR":
            per[a]["no_repair"] += 1; continue
        r = R.get(s.get("job"))
        if r is None:
            per[a]["unrun"] += 1; continue
        X, Y = r.get("X") or {}, r.get("Y") or {}
        ok = X.get("x") == 1 and Y.get("y") == 1 and (r.get("REPLAY") or {}).get("replay") == 1
        L = len(s["seq"])
        per[a]["succ"] += ok; per[a][f"succ_L{L}"] += ok
        per[a][f"succ_shorter_than_ref"] += ok and L < priv[s["root_id"]]["L_ref"]
    out["arms"] = {a: dict(c) for a, c in per.items()}
    return out


if __name__ == "__main__":
    priv = {r["root_id"]: r for r in jl(sys.argv[3])}
    res = {"main": count(sys.argv[1], priv), "ctrl": count(sys.argv[2], priv), "reported": REPORTED}
    chk = {f"main:{a}": (res["main"]["arms"].get(a, {}).get("succ"), v) for a, v in REPORTED["main"].items()}
    chk.update({f"ctrl:{a}": (res["ctrl"]["arms"].get(a, {}).get("succ"), v) for a, v in REPORTED["ctrl"].items()})
    chk.update({f"long:{a}": ((res["main"]["arms"][a].get("succ_L4", 0), res["main"]["arms"][a].get("succ_L5", 0)), v) for a, v in REPORTED["long"].items()})
    chk.update({"jobs:main": (res["main"]["n_jobs"], 449), "jobs:ctrl": (res["ctrl"]["n_jobs"], 194)})
    res["check"] = {k: {"recount": list(a) if isinstance(a, tuple) else a, "reported": list(b) if isinstance(b, tuple) else b, "match": tuple(a) == tuple(b) if isinstance(a, tuple) else a == b} for k, (a, b) in chk.items()}
    Path(sys.argv[4]).write_text(json.dumps(res, indent=1))
    print(json.dumps({"seals": [res["main"]["seals"], res["ctrl"]["seals"]], "retries": [res["main"]["duplicate_phys_keys(retries)"], res["ctrl"]["duplicate_phys_keys(retries)"]],
                      "missing": [res["main"]["jobs_without_record"], res["ctrl"]["jobs_without_record"]], "check": res["check"]}, indent=0))
