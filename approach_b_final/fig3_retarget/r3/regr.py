#!/usr/bin/env python3
"""R3 physical K<=3 regression (R3_PREREG R3_2.k3_regression.physical; addendum A2): released EXACT4 selector (rank.b0: D4 cVAE proposals at
S0, every legal set of <= 3 x every order, p11, NOOP gate 0.5, eta 0.3, frozen tie-break) run with the production F0 scorer and with the
selected scaling scorer (same cVAE proposals, same rule).  Panel = NATURAL_VAL roots (original v32 VAL, families without any DEV / diagnostic
exposure).  Roots whose decision or sequence is unchanged have identical physical outcomes by construction (deterministic teacher).
Changed roots (sha256('R3.REGR|' + root) order) are verified for BOTH arms: exact reuse of an original v32 label (continuous X of that
sequence == chunked bounds [m], R3.0 TRN parity 8/8, and the endpoint Y label) or of an archived exact Fig.3 run; otherwise one new job
(X_CHUNKED bounds [m] + endpoint Y + independent replay).  Cap 60 jobs / 3 CPU-h; a root is queued only if all its jobs fit.
Success: REPAIR -> X = 1 and Y = 1;  NOOP -> Y(empty) = 1 (v32 label);  ABSTAIN -> 0 (task not achieved).
    $PYG regr.py select ARM SEED     -> O/regr/select.json (+ SEAL)
    python regr.py jobs CAP          -> O/regr/jobs.json (+ SEAL), selection.json
    python regr.py analyze           -> O/regr/REGR_3d.json"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C = K.C
OR = K.O / "regr"
RULE = {"noop_gate": 0.5, "eta": 0.3}


def panel():
    lin = json.loads((K.O / "lineage_3d.json").read_text())
    diag = set(lin["diag_fams"])
    rows = C.snapshot_rows("3d", splits=("val",), snap=C.SNAP_TRAIN)
    return {r: x for r, x in sorted(rows.items()) if x["parent_family_id"] not in diag}


def select(arm, seed):
    import rank
    import train as TR
    rows = panel()
    fz, net = TR.load("3d", arm, seed)
    out = {}
    for tag in ("F0", f"{arm}_s{seed}"):
        prop = dict(fz._p)
        fz.net = fz.scor.net if tag == "F0" else net                 # F0 = the production bundle scorer itself
        fz.reset(); fz._p = prop; fz.caps = {}
        for rid, r in rows.items():
            d = rank.b0(fz, r, RULE)
            out.setdefault(rid, {})[tag] = {"decision": d["decision"], "seq": d["seq"], "score": d["score"]}
    for rid, v in out.items():
        a, b = v["F0"], v[f"{arm}_s{seed}"]
        v["changed"] = (a["decision"], a["seq"]) != (b["decision"], b["seq"])
    OR.mkdir(parents=True, exist_ok=True)
    f = OR / "select.json"; f.write_text(json.dumps({"model": f"{arm}_s{seed}", "rule": RULE, "roots": out}, indent=1))
    (OR / "select.json.SEAL").write_text(K.sha(f))
    print(json.dumps({"roots": len(out), "changed": sum(v["changed"] for v in out.values()),
                      "decisions": {t: collections.Counter(v[t]["decision"] for v in out.values()) for t in ("F0", f"{arm}_s{seed}")}}))


def _v32(row, seq):
    xs = [q["x"] for q in row["labels"]["X"] if [list(map(int, a)) for a in q["seq"]] == [list(map(int, a)) for a in seq]]
    ys = [q["y"] for q in row["labels"]["Y"] if sorted(map(tuple, map(lambda a: tuple(map(int, a)), q["edit"]))) == sorted(tuple(map(int, a)) for a in seq)]
    return (xs[0], ys[0]) if xs and ys else None


def jobs(cap):
    sys.path.insert(0, str(HERE.parent / "r24"))
    import data as DA
    import jobs24 as J24
    S = json.loads((OR / "select.json").read_text())
    rows = panel(); paths = DA.raw_paths("3d")
    A = J24.archive("3d", rows)
    tags = list(next(iter(S["roots"].values())).keys())[:2]
    ch = sorted([r for r, v in S["roots"].items() if v["changed"]], key=lambda r: hashlib.sha256(f"R3.REGR|{r}".encode()).hexdigest())
    jb, sel = [], []
    for rid in ch:
        need, plan = [], []
        for t in tags:
            d = S["roots"][rid][t]
            if d["decision"] != "REPAIR":
                plan.append({"root_id": rid, "arm": t, "status": d["decision"]}); continue
            seq = d["seq"]; ids = rows[rid]["inputs"]["ids"]
            v = _v32(rows[rid], seq)
            if v:
                plan.append({"root_id": rid, "arm": t, "status": "REUSED_V32", "x": v[0], "y": v[1]}); continue
            hit = J24.lookup("3d", A, rid, ids, seq, [len(seq)])
            if hit:
                plan.append({"root_id": rid, "arm": t, "status": "REUSED", **hit}); continue
            key = f"REGR|{rid}|{json.dumps(seq)}"
            if key not in {j["key"] for j in need}:
                rec = json.loads(Path(paths[rid]).read_text())
                need.append({"key": key, "root_id": rid, "path": paths[rid], "kind": "X_CHUNKED", "order": J24.names("3d", ids, seq), "bounds": [len(seq)],
                             "y": {"target": "t0", "goal": rec["goal"]}})
            plan.append({"root_id": rid, "arm": t, "status": "QUEUED", "job": key})
        if len(jb) + len(need) > int(cap):
            sel += [{**p, "status": "NOT_RUN_BUDGET"} if p["status"] == "QUEUED" else p for p in plan]; continue
        jb += need; sel += plan
    jf = OR / "jobs.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = OR / "selection.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (OR / (f.name + ".SEAL")).write_text(K.sha(f))
    print(json.dumps({"changed_roots": len(ch), "jobs": len(jb), "by": collections.Counter(f"{p['arm']}:{p['status']}" for p in sel)}))


def analyze():
    from scipy.stats import binomtest
    S = json.loads((OR / "select.json").read_text())
    sel = json.loads((OR / "selection.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(OR / "phys.jsonl")} if (OR / "phys.jsonl").exists() else {}
    rows = panel()
    tags = list(next(iter(S["roots"].values())).keys())[:2]
    y0 = {rid: next((q["y"] for q in r["labels"]["Y"] if not q["edit"]), None) for rid, r in rows.items()}
    per = collections.defaultdict(dict)
    for p in sel:
        st = p["status"]
        if st == "QUEUED":
            r = R.get(p["job"], {})
            x, y = (r.get("X") or {}).get("x"), (r.get("Y") or {}).get("y")
            s = None if x is None else bool(x == 1 and y == 1 and (r.get("REPLAY") or {}).get("replay") == 1)
        elif st in ("REUSED_V32", "REUSED"):
            s = p["x"] == 1 and p["y"] == 1
        elif st == "NOOP":
            s = None if y0[p["root_id"]] is None else y0[p["root_id"]] == 1
        elif st == "ABSTAIN":
            s = False
        else:
            s = None
        per[p["root_id"]][p["arm"]] = {"status": st, "succ": s}
    a, b = tags
    done = [r for r in per if all(per[r].get(t, {}).get("succ") is not None for t in tags)]
    g = sum(per[r][b]["succ"] and not per[r][a]["succ"] for r in done); l = sum(per[r][a]["succ"] and not per[r][b]["succ"] for r in done)
    n = len(S["roots"]); nc = sum(v["changed"] for v in S["roots"].values())
    import numpy as np
    rng = np.random.default_rng(0)
    d = np.array([int(per[r][b]["succ"]) - int(per[r][a]["succ"]) for r in done], float)
    # changed roots are verified in sha256 order (a hash-random subset when the cap binds): panel delta = (changed / panel) x mean subset delta
    est = lambda x: nc / n * x.mean() if len(x) else 0.0  # noqa: E731
    boot = [est(rng.choice(d, len(d))) for _ in range(4000)] if len(d) else [0.0]
    out = {"panel_roots": n, "changed": nc, "verified_changed": len(done), "unverified_changed": nc - len(done),
           "gain": g, "loss": l, "subset_mean_delta": float(d.mean()) if len(d) else None, "delta_success_pp_panel": 100 * est(d),
           "ci95_pp": [100 * float(np.percentile(boot, 2.5)), 100 * float(np.percentile(boot, 97.5))],
           "mcnemar_two_sided_p": binomtest(g, g + l, 0.5).pvalue if g + l else None,
           "noninferior_5pp": bool(len(d) >= 10 and np.percentile(boot, 2.5) > -0.05),
           "per_root": per, "jobs": len(R), "cpu_h": sum(r.get("cpu_s", 0) for r in R.values()) / 3600}
    (OR / "REGR_3d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "per_root"}, default=str))


if __name__ == "__main__":
    {"select": lambda: select(*sys.argv[2:4]), "jobs": lambda: jobs(sys.argv[2]), "analyze": analyze}[sys.argv[1]]()
