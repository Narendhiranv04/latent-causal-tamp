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
    import time
    fz0, base = TR.f0("3d")
    fz0.net = base.to("cuda").eval(); fz0.reset(); fz0.caps = {}
    out = {}
    for rid in sorted(rows):
        A = orc[rid]["assignment"]
        t0 = time.perf_counter()
        T = OD.Table(fz, rows[rid], A)
        E, o, p = OD.dp(T, lam=OD.LAM)
        dp_s = time.perf_counter() - t0
        E0, o0, p0 = OD.dp(T, lam=0.0)
        T0 = OD.Table(fz0, rows[rid], A)
        rng = random.Random(hashlib.sha256(f"R3.4|{rid}".encode()).hexdigest())
        ro = [list(a) for a in T.A]; rng.shuffle(ro)
        rb = OD.best_partition_for(T, ro)
        out[rid] = {"assignment": A, "S-DP": {"order": o, "partition": list(p), "E": E}, "S-DP0": {"order": o0, "partition": list(p0), "E": E0},
                    "RANDOM": {"order": ro, "partition": list(rb[1]), "E": rb[0]}, "F0-DP": orc[rid]["A-DP"],
                    "orders_scored": len(list(itertools.permutations(A))), "model": f"{arm}_s{seed}", "dp_s": round(dp_s, 3),
                    "ranked": OD.all_orders(T), "ranked_F0": OD.all_orders(T0),           # witness-order rank = evaluator analysis only
                    "chunk_px": {a: _chunk_px(T, out_o, out_p) for a, (out_o, out_p) in (("S-DP", (o, p)), ("RANDOM", (ro, rb[1])))},
                    "chunk_px_F0": _chunk_px(T0, orc[rid]["A-DP"]["order"], orc[rid]["A-DP"]["partition"])}
        print(rid, out[rid]["S-DP"], flush=True)
    O4.mkdir(parents=True, exist_ok=True)
    (O4 / "plans_3d.json").write_text(json.dumps(out, indent=1))


def r24_runs():
    """Exact R2.4 X_CHUNKED + endpoint-Y runs on DEV_ORDER_3D (r24/jobs_24_3d.json + phys_24_3d.jsonl), keyed like jobs24.archive."""
    J = json.loads((C.FIG3 / "r24" / "jobs_24_3d.json").read_text())
    J = J if isinstance(J, list) else [x for v in J.values() for x in v]
    R = {json.loads(l)["key"]: json.loads(l) for l in open(C.FIG3 / "r24" / "phys_24_3d.jsonl")}
    out = {}
    for j in J:
        r = R.get(j["key"])
        if not r or r.get("censored") or r.get("error") or j.get("cells0") or not j.get("y"):
            continue
        X, Y = r.get("X") or {}, r.get("Y") or {}
        out[(j["root_id"], J24.nk(j["order"]), J24.nk(j["bounds"]))] = {"x": X.get("x"), "y": Y.get("y"), "src": "R2.4:" + j["key"], "phase": str(X.get("phase") or ""),
                                                                         "teacher_status": X.get("status"), "replay": (r.get("REPLAY") or {}).get("replay")}
    return out


def _chunk_px(T, order, part):
    S, out, i = set(), [], 0
    for g in part:
        out.append(T.get(S, order[i:i + g])["px"]); S |= {tuple(a) for a in order[i:i + g]}; i += g
    return out


def jobs(cap, label="FORMAL"):
    P = json.loads((O4 / "plans_3d.json").read_text())
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    A = J24.archive("3d", rows)
    A.update(r24_runs())                                               # R2.4's own executed runs (the archived A-DP arm lives here)
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
            key = f"{'R34' if label == 'FORMAL' else 'R34DX'}|{rid[-22:]}|{json.dumps(p['order'])}|{json.dumps(b)}"
            rp = C.NW / "k45/cohort/roots" / f"{rid}.json"
            jb.append({"key": key, "root_id": rid, "path": str(rp), "kind": "X_CHUNKED", "order": J24.names("3d", ids, p["order"]), "bounds": b,
                       "y": {"target": "t0", "goal": json.loads(rp.read_text())["goal"]}})
            sel.append({"key": list(k), "arm": arm, "status": "QUEUED", "job": key, "label": label})
    jf = O4 / "jobs_34_3d.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = O4 / "selection_34_3d.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (O4 / (f.name + ".SEAL")).write_text(K.sha(f))
    import collections
    print(json.dumps({"queued": len(jb), "by": collections.Counter(f"{s['arm']}:{s['status']}" for s in sel)}))


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
            res[tuple(s["key"])] = {"x": x, "y": y, "succ": ok if x is not None else None, "phase": (r.get("X") or {}).get("phase"),
                                    "status": (r.get("X") or {}).get("status"), "cpu_s": r.get("cpu_s"), "src": "R3.4"}
        elif s["status"] == "REUSED":
            res[tuple(s["key"])] = {"x": s["x"], "y": s["y"], "succ": s["x"] == 1 and s["y"] == 1 and s.get("replay", 1) == 1, "phase": s.get("phase"),
                                    "status": s.get("teacher_status"), "src": s.get("src")}
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    wit = {}
    for rid in P:                                                     # evaluator only: the verified witness order of the K45 record
        rec = json.loads((C.NW / "k45/cohort/roots" / f"{rid}.json").read_text()); ids = rows[rid]["inputs"]["ids"]
        wit[rid] = [[ids.index(o), int(d[0]) * 6 + int(d[1])] for o, d in rec["k45"]["witness"]["order"]]
    arms = {}
    for arm in ("S-DP", "RANDOM", "F0-DP", "S-DP0"):
        per = {}
        for rid, p in P.items():
            b = J24.bounds(p[arm]["partition"])
            per[rid] = dict(res.get((rid, json.dumps(p[arm]["order"]), json.dumps(b)), {"succ": None}))
            ph = str(per[rid].get("phase") or "")
            per[rid].update(partition=p[arm]["partition"], returns=len(p[arm]["partition"]) - 1, order=p[arm]["order"],
                            fail_at=int(ph.split(":")[1]) if ph.startswith("relocation:") else None, fail_kind=ph.split(":")[0] or None,
                            exact_witness=p[arm]["order"] == wit[rid])
        for rid in P:
            if arm in ("S-DP", "F0-DP"):
                rk = P[rid]["ranked" if arm == "S-DP" else "ranked_F0"]
                per[rid]["witness_rank"] = [1 + next(i for i, r in enumerate(rk) if r["order"] == wit[rid]), len(rk)]
        arms[arm] = {"verified": sum(v["succ"] is True for v in per.values()), "decided": sum(v["succ"] is not None for v in per.values()), "per_root": per}
    s, f = arms["S-DP"]["per_root"], arms["F0-DP"]["per_root"]
    gain = sum(s[r]["succ"] is True and f[r]["succ"] is False for r in P); loss = sum(s[r]["succ"] is False and f[r]["succ"] is True for r in P)
    p = binomtest(gain, gain + loss, 0.5, alternative="greater").pvalue if gain + loss else None
    v = arms["S-DP"]["verified"]
    dec = "RECOVERED" if v >= 14 else "PARTIAL" if v >= 10 else "NOT_RECOVERED"
    rnd = arms["RANDOM"]["per_root"]
    g2 = sum(s[r]["succ"] is True and rnd[r]["succ"] is False for r in P); l2 = sum(s[r]["succ"] is False and rnd[r]["succ"] is True for r in P)
    label = next((x.get("label") for x in sel if x.get("label")), "FORMAL")
    out = {"label": label, "arms": {a: {k: x for k, x in d.items() if k != "per_root"} for a, d in arms.items()}, "per_root": {a: d["per_root"] for a, d in arms.items()},
           "paired_S_vs_RANDOM": {"gain": g2, "loss": l2, "mcnemar_one_sided_p": binomtest(g2, g2 + l2, 0.5, alternative="greater").pvalue if g2 + l2 else None},
           "plan_s": {r: P[r]["dp_s"] for r in P},
           "paired_S_vs_F0": {"gain": gain, "loss": loss, "net": gain - loss, "mcnemar_one_sided_p": p}, "count_band": dec,
           "material_gain": gain - loss >= 5 and p is not None and p < 0.05}
    (O4 / "R3_4_3d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("arms", "paired_S_vs_F0", "count_band", "material_gain")}, default=str))


if __name__ == "__main__":
    {"plan": lambda: plan(*sys.argv[2:4]), "jobs": lambda: jobs(*sys.argv[2:4]), "analyze": analyze}[sys.argv[1]]()
