#!/usr/bin/env python3
"""R2.4 presealed physical selection (evaluator side; label-blind to NEW outcomes).  Unique (root, ordered sequence, bounds) plans in the
preregistered tier priority; exact archived labels always reused (no budget); <= CAP new units (3D: 1 per job, 2D: 2 queries per job).
    python jobs24.py build DOM CAP"""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2")]
import common as C  # noqa: E402
import labels as LB  # noqa: E402

O = C.FIG3 / "r24"
PRIO = {"3d": ["A-DP", "R-FIG3-X", "GA-UNION", "GA-INIT", "R-FIG3-XP", "A-PRE", "R-FIG3-XC"], "2d": ["R-FIG3-X", "GA-UNION", "GA-INIT", "R-FIG3-XP", "R-FIG3-XC"]}


def bounds(part):
    out, s = [], 0
    for g in part:
        s += g; out.append(s)
    return out


def names(dom, ids, seq):
    return [[ids[int(o)], int(d) if dom == "2d" else [int(d) // 6, int(d) % 6]] for o, d in seq]


def nk(x):
    return json.dumps(x).replace(" ", "")


def archive(dom, rows):
    """Exact archived (root, ordered names, bounds) -> outcome, from every non-TEST Fig.3 / K45 teacher run with an endpoint t0 Y."""
    A = {}
    for jf, rf, tag in LB.sources(dom):
        if not Path(jf).exists():
            continue
        J, R = LB._load(jf, rf)
        for j in J:
            r = R.get(j["key"])
            if not r or r.get("censored") or r.get("error") or j.get("kind", "X_CHUNKED") != "X_CHUNKED" or j.get("cells0") or j.get("fixture"):
                continue
            if not (j.get("y") or j.get("y_endpoint") or j.get("y_cells")):
                continue
            if j.get("y") and j["y"].get("target", "t0") != "t0":
                continue
            rid = LB.rid_of(dom, j)
            X, Y = r.get("X") or {}, r.get("Y") or {}
            A[(rid, nk(j.get("order") or j.get("seq")), nk(j["bounds"]))] = {"x": X.get("x"), "y": Y.get("y"), "src": tag + ":" + j["key"],
                                                                                "phase": str(X.get("phase") or X.get("failed_phase") or ""),
                                                                                "teacher_status": X.get("teacher_status") or X.get("status")}
    if dom == "2d":                                                       # continuous single chunk: pool x_query (== x_chunked(bounds={m})) + Y
        X, Y = {}, {}
        for e in C.pool(dom):
            if e["t"] == "X":
                X[(e["root"], json.dumps([list(map(int, a)) for a in e["seq"]]))] = e["x"]
            else:
                Y[(e["root"], json.dumps(sorted([list(map(int, a)) for a in e["edit"]])))] = e["y"]
        A["_pool"] = (X, Y)
    return A


def plans(dom):
    P = []
    if dom == "3d" and (O / "oracle_3d.json").exists():
        for rid, r in json.loads((O / "oracle_3d.json").read_text()).items():
            for arm in ("A-DP", "A-PRE"):
                P.append({"root_id": rid, "arm": arm, "decision": "REPAIR", "seq": r[arm]["order"], "partition": r[arm]["partition"]})
    for l in open(O / f"deploy_{dom}.jsonl"):
        r = json.loads(l)
        for arm in ("R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC", "GA-INIT", "GA-UNION"):
            P.append({"root_id": r["root_id"], "arm": arm, "decision": r[arm]["decision"], "seq": r[arm]["seq"], "partition": r[arm]["partition"]})
    return P


def lookup(dom, A, rid, ids, seq, b):
    k = (rid, nk(names(dom, ids, seq)), nk(b))
    if k in A:
        return A[k]
    if dom == "2d" and b == [len(seq)]:
        X, Y = A["_pool"]
        x = X.get((rid, json.dumps([list(map(int, a)) for a in seq])))
        y = Y.get((rid, json.dumps(sorted([list(map(int, a)) for a in seq]))))
        if x is not None and y is not None:
            return {"x": x, "y": y, "src": "pool x_query + Y", "phase": "", "teacher_status": None}
    return None


def build(dom, cap):
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / f"roster_{dom}.jsonl")}
    A = archive(dom, rows)
    P = [p for p in plans(dom) if p["arm"] in PRIO[dom]]
    order = sorted(P, key=lambda p: (PRIO[dom].index(p["arm"]), C.h("R2_4|" + p["root_id"])))
    seen, units, jobs, sel = {}, 0, [], []
    for p in order:
        if not p["seq"]:
            continue
        ids = rows[p["root_id"]]["inputs"]["ids"]
        b = bounds(p["partition"])
        k = (p["root_id"], json.dumps(p["seq"]), json.dumps(b))
        if k in seen:
            continue
        seen[k] = 1
        hit = lookup(dom, A, p["root_id"], ids, p["seq"], b)
        if hit:
            sel.append({"key": list(k), "first_arm": p["arm"], "status": "REUSED", **hit}); continue
        cost = 1 if dom == "3d" else 2
        if units + cost > int(cap):
            sel.append({"key": list(k), "first_arm": p["arm"], "status": "NOT_RUN_BUDGET"}); continue
        units += cost
        key = f"R24|{p['root_id'][-22:]}|{json.dumps(p['seq'])}|{json.dumps(b)}"
        if dom == "3d":
            rp = C.NW / "k45/cohort/roots" / f"{p['root_id']}.json"
            jobs.append({"key": key, "root_id": p["root_id"], "path": str(rp), "kind": "X_CHUNKED", "order": names(dom, ids, p["seq"]), "bounds": b,
                         "y": {"target": "t0", "goal": json.loads(rp.read_text())["goal"]}})
        else:
            path, geom = C.raw_path(dom, p["root_id"])
            jobs.append({"key": key, "root_id": p["root_id"], "path": path, "geom": geom, "kind": "X_CHUNKED", "seq": names(dom, ids, p["seq"]), "bounds": b, "y_endpoint": True})
        sel.append({"key": list(k), "first_arm": p["arm"], "status": "QUEUED", "job": key})
    jf = O / f"jobs_24_{dom}.json"; jf.write_text(json.dumps(jobs, indent=1))
    sf = O / f"selection_24_{dom}.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (O / (f.name + ".SEAL")).write_text(hashlib.sha256(f.read_bytes()).hexdigest())
    print(json.dumps({"dom": dom, "unique_plans": len(sel), "reused": sum(s["status"] == "REUSED" for s in sel), "queued_jobs": len(jobs), "units": units,
                      "not_run_budget": sum(s["status"] == "NOT_RUN_BUDGET" for s in sel),
                      "by_first_arm": {a: [sum(s["first_arm"] == a and s["status"] == st for s in sel) for st in ("REUSED", "QUEUED", "NOT_RUN_BUDGET")] for a in PRIO[dom]},
                      "seal": {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16] for f in (jf, sf)}}))


if __name__ == "__main__":
    build(sys.argv[2], sys.argv[3])
