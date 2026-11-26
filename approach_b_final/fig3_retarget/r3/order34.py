#!/usr/bin/env python3
"""R3.4 physical order recovery on DEV_ORDER_3D (20 exposed K4/K5 roots; the R2.4 known UNORDERED assignment; witness order hidden).
Arms (preregistered R3_PREREG.json R3_4):  S-DP = selected scaling model + exact subset DP (order.dp, LAM = -log 0.92 as R2.4);
RANDOM = permutation from sha256('R3.4|' + root) with the selected model's best partition for that order; F0-DP = archived R2.4 A-DP
(same chunked mode, exact jobs reused); WITNESS = archived R2.4 witness split (upper reference).  lambda = 0 logged offline only.
Physical: X_CHUNKED with endpoint Y (t0, goal), independent replay; exact archived (root, ordered names, bounds) labels reused (jobs24.archive).
    python order34.py plan ARM SEED      (GPU) -> O/r34/plans_3d.json
    python order34.py jobs CAP                 -> O/r34/jobs_34_3d.json (+ SEAL), selection_34_3d.json
    python order34.py analyze                  -> O/r34/R3_4_3d.json"""
from __future__ import annotations

import hashlib, itertools, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C = K.C
sys.path.insert(0, str(HERE.parent / "r24"))
import order as OD  # noqa: E402
import jobs24 as J24  # noqa: E402

O4 = K.O / "r34"


def plan(arm, seed):
    import train as TR
    fz, net = TR.load("3d", arm, seed)
    fz.net = net; fz.reset(); fz.caps = {}
    orc = json.loads((C.FIG3 / "r24" / "oracle_3d.json").read_text())
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    out = {}
    for rid in sorted(rows):
        A = orc[rid]["assignment"]
        T = OD.Table(fz, rows[rid], A)
        E, o, p = OD.dp(T, lam=OD.LAM)
        E0, o0, p0 = OD.dp(T, lam=0.0)
        rng = random.Random(hashlib.sha256(f"R3.4|{rid}".encode()).hexdigest())
        ro = [list(a) for a in T.A]; rng.shuffle(ro)
        rb = OD.best_partition_for(T, ro)
        out[rid] = {"assignment": A, "S-DP": {"order": o, "partition": list(p), "E": E}, "S-DP0": {"order": o0, "partition": list(p0), "E": E0},
                    "RANDOM": {"order": ro, "partition": list(rb[1]), "E": rb[0]}, "F0-DP": orc[rid]["A-DP"],
                    "orders_scored": len(list(itertools.permutations(A))), "model": f"{arm}_s{seed}"}
        print(rid, out[rid]["S-DP"], flush=True)
    O4.mkdir(parents=True, exist_ok=True)
    (O4 / "plans_3d.json").write_text(json.dumps(out, indent=1))


def jobs(cap):
    P = json.loads((O4 / "plans_3d.json").read_text())
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    A = J24.archive("3d", rows)
    seen, units, jb, sel = {}, 0, [], []
    for arm in ("S-DP", "RANDOM", "F0-DP"):
        for rid in sorted(P, key=lambda r: hashlib.sha256(f"R3.4|{r}".encode()).hexdigest()):
            p = P[rid][arm]; ids = rows[rid]["inputs"]["ids"]; b = J24.bounds(p["partition"])
            k = (rid, json.dumps(p["order"]), json.dumps(b))
            if k in seen:
                sel.append({"key": list(k), "arm": arm, "status": "SAME_AS", "same_as": seen[k]}); continue
            seen[k] = arm
            hit = J24.lookup("3d", A, rid, ids, p["order"], b)
            if hit:
                sel.append({"key": list(k), "arm": arm, "status": "REUSED", **hit}); continue
            if arm == "F0-DP" or units + 1 > int(cap):
                sel.append({"key": list(k), "arm": arm, "status": "NOT_RUN_BUDGET" if arm != "F0-DP" else "F0_ARCHIVE_MISSING"}); continue
            units += 1
            key = f"R34|{rid[-22:]}|{json.dumps(p['order'])}|{json.dumps(b)}"
            rp = C.NW / "k45/cohort/roots" / f"{rid}.json"
            jb.append({"key": key, "root_id": rid, "path": str(rp), "kind": "X_CHUNKED", "order": J24.names("3d", ids, p["order"]), "bounds": b,
                       "y": {"target": "t0", "goal": json.loads(rp.read_text())["goal"]}})
            sel.append({"key": list(k), "arm": arm, "status": "QUEUED", "job": key})
    jf = O4 / "jobs_34_3d.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = O4 / "selection_34_3d.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (O4 / (f.name + ".SEAL")).write_text(K.sha(f))
    import collections
    print(json.dumps({"queued": len(jb), "by": collections.Counter((s["arm"], s["status"]) for s in sel)}, default=str))


def analyze():
    from scipy.stats import binomtest
    P = json.loads((O4 / "plans_3d.json").read_text())
    sel = json.loads((O4 / "selection_34_3d.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(O4 / "phys_34_3d.jsonl")} if (O4 / "phys_34_3d.jsonl").exists() else {}
    res = {}
    for s in sel:
        if s["status"] == "SAME_AS":
            continue
        if s["status"] == "QUEUED":
            r = R.get(s["job"], {})
            x, y = (r.get("X") or {}).get("x"), (r.get("Y") or {}).get("y")
            ok = x == 1 and y == 1 and (r.get("REPLAY") or {}).get("replay") == 1
            res[tuple(s["key"])] = {"x": x, "y": y, "succ": ok if x is not None else None, "phase": (r.get("X") or {}).get("phase")}
        elif s["status"] == "REUSED":
            res[tuple(s["key"])] = {"x": s["x"], "y": s["y"], "succ": s["x"] == 1 and s["y"] == 1, "phase": s.get("phase")}
    arms = {}
    for arm in ("S-DP", "RANDOM", "F0-DP", "S-DP0"):
        per = {}
        for rid, p in P.items():
            b = J24.bounds(p[arm]["partition"])
            per[rid] = res.get((rid, json.dumps(p[arm]["order"]), json.dumps(b)), {"succ": None})
        arms[arm] = {"verified": sum(v["succ"] is True for v in per.values()), "decided": sum(v["succ"] is not None for v in per.values()), "per_root": per}
    s, f = arms["S-DP"]["per_root"], arms["F0-DP"]["per_root"]
    gain = sum(s[r]["succ"] is True and f[r]["succ"] is False for r in P); loss = sum(s[r]["succ"] is False and f[r]["succ"] is True for r in P)
    p = binomtest(gain, gain + loss, 0.5, alternative="greater").pvalue if gain + loss else None
    v = arms["S-DP"]["verified"]
    dec = "RECOVERED" if v >= 14 else "PARTIAL" if v >= 10 else "NOT_RECOVERED"
    out = {"arms": {a: {k: x for k, x in d.items() if k != "per_root"} for a, d in arms.items()}, "per_root": {a: d["per_root"] for a, d in arms.items()},
           "paired_S_vs_F0": {"gain": gain, "loss": loss, "net": gain - loss, "mcnemar_one_sided_p": p}, "count_band": dec,
           "material_gain": gain - loss >= 5 and p is not None and p < 0.05}
    (O4 / "R3_4_3d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("arms", "paired_S_vs_F0", "count_band", "material_gain")}, default=str))


if __name__ == "__main__":
    {"plan": lambda: plan(*sys.argv[2:4]), "jobs": lambda: jobs(sys.argv[2]), "analyze": analyze}[sys.argv[1]]()
