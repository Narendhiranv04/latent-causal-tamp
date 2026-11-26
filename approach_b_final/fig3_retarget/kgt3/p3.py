#!/usr/bin/env python3
"""KGT3 P3 physical order recovery GIVEN the unordered assignment (ORACLE_DIAGNOSTIC; FIG3_KGT3_PREREG P3).  Runs only after guard.authorize
on the domain's P2 gate decision (P2_GATE == PASS).
Arms: SEL-DP (selected X, grouped DP, lambda 0, has_multi), F0-NEW (frozen F0, same objective), HIST (archived learned order: 2D R3.4D FX-DP,
3D R2.4 A-DP; no rerun), RANDOM (sha256('KGT3-P3|' + root) order + best admissible partition, selected X), WITNESS (privileged order + best
admissible partition, selected X).  One sealed plan per root and arm; exact archive reuse only for identical (root, order, bounds) and contract.
    $PYG p3.py plan DOM SPEC      -> O/kgt3/p3/plans_DOM.json (+ SEAL)
    python p3.py jobs DOM CAP     -> O/kgt3/p3/jobs_DOM.json (+ SEAL), selection_DOM.json
    python p3.py analyze DOM      -> O/kgt3/p3/P3_DOM.json + guard decision p3_DOM.json"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
C = K.C
O3 = C.FIG3 / "kgt3" / "p3"
ARMS = ("SEL-DP", "F0-NEW", "RANDOM", "WITNESS")


def panel(dom):
    if dom == "2d":
        R = {json.loads(l)["root_id"]: json.loads(l) for l in open(K.O / "coh2d" / "rows.jsonl")}
        P = json.loads((K.O / "coh2d" / "plans.json").read_text())
        return [(rid, R[rid], P[rid]["assignment"], P[rid]["WITNESS"]["order"], {"K": P[rid]["K"], "N": P[rid]["N"], "path": R[rid]["path"]}) for rid in sorted(P)]
    R = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
    orc = json.loads((C.FIG3 / "r24" / "oracle_3d.json").read_text())
    out = []
    for rid in sorted(R):
        p = C.NW / "k45/cohort/roots" / f"{rid}.json"
        rec = json.loads(p.read_text()); ids = R[rid]["inputs"]["ids"]
        W = [[ids.index(o), int(d[0]) * 6 + int(d[1])] for o, d in rec["k45"]["witness"]["order"]]
        out.append((rid, R[rid], orc[rid]["assignment"], W, {"K": len(W), "N": len(ids), "path": str(p), "goal": rec["goal"], "hist": orc[rid]["A-DP"]}))
    return out


def plan(dom, spec):
    import time
    import learn as LN
    import planners as PL
    GD.authorize(C.FIG3 / "kgt3" / f"gate_{dom}.json", "P2_GATE", "PASS")
    fz, net = LN.load(dom, spec)
    fz0, base = LN.load(dom, "F0")
    fz.net = net; fz.reset(); fz.caps = {}
    fz0.net = base; fz0.reset(); fz0.caps = {}
    out = {}
    for rid, row, A, W, meta in panel(dom):
        t0 = time.perf_counter()
        s = PL.assignment_given(fz, row, A, witness=W)
        f = PL.assignment_given(fz0, row, A)
        out[rid] = {"meta": {k: v for k, v in meta.items() if k != "hist"}, "SEL-DP": s["SEL-DP"], "RANDOM": s["RANDOM"], "WITNESS": s["WITNESS"],
                    "F0-NEW": f["SEL-DP"], "y_global_sel": s["y_global"], "wall_s": round(time.perf_counter() - t0, 3), "spec": spec}
        print(rid, out[rid]["SEL-DP"]["order"], out[rid]["SEL-DP"]["partition"], flush=True)
    O3.mkdir(parents=True, exist_ok=True)
    pf = O3 / f"plans_{dom}.json"; pf.write_text(json.dumps(out, indent=1))
    (O3 / f"plans_{dom}.json.SEAL").write_text(GD.sha(pf))


def bounds(part):
    s, out = 0, []
    for g in part:
        s += g; out.append(s)
    return out


def archive(dom):
    """Exact (root, ordered actions, bounds) -> outcome from earlier runs with the same contract (endpoint Y + replay)."""
    A = {}
    if dom == "2d":
        jobs = json.loads((K.O / "coh2d" / "jobs.json").read_text())
        R = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / "coh2d" / "phys.jsonl")}
        for j in jobs:
            r = R.get(j["key"]); X = (r or {}).get("X") or {}
            if r and not r.get("error"):
                A[(j["root_id"], json.dumps(j["seq_idx"]), json.dumps(j["bounds"]))] = {"x": None if str(X.get("teacher_status", "")).startswith("UNKNOWN") else X.get("x"),
                                                                                         "replay": X.get("independent_replay"), "src": "R3.4D:" + j["key"], "phase": X.get("failed_phase")}
    else:
        import order34 as O34
        for (rid, o, b), v in O34.r24_runs().items():
            A[(rid, o, b)] = v
    return A


def y2d():
    """2D endpoint Y per cohort root (identical endpoint for every arm; measured once in R3.4D)."""
    jobs = json.loads((K.O / "coh2d" / "jobs.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / "coh2d" / "phys.jsonl")}
    return {j["root_id"]: (R[j["key"]].get("Y") or {}).get("y") for j in jobs if j["y_endpoint"]}


def jobs(dom, cap):
    GD.authorize(C.FIG3 / "kgt3" / f"gate_{dom}.json", "P2_GATE", "PASS")
    P = json.loads((O3 / f"plans_{dom}.json").read_text())
    pan = {rid: (row, meta) for rid, row, _, _, meta in panel(dom)}
    A = archive(dom)
    import jobs24 as J24
    seen, jb, sel = {}, [], []
    for arm in ARMS:
        for rid in sorted(P, key=lambda r: hashlib.sha256(f"KGT3-P3|{r}".encode()).hexdigest()):
            p = P[rid][arm]; row, meta = pan[rid]; ids = row["inputs"]["ids"]; b = bounds(p["partition"])
            if dom == "2d":
                k = (rid, json.dumps(p["order"]), json.dumps(b))
            else:
                k = (rid, J24.nk(J24.names("3d", ids, p["order"])), J24.nk(b))
            if k in seen:
                sel.append({"key": list(k), "arm": arm, "status": "SAME_AS", "same_as": seen[k]}); continue
            seen[k] = arm
            if k in A:
                sel.append({"key": list(k), "arm": arm, "status": "REUSED", **A[k]}); continue
            if len(jb) + 1 > int(cap):
                sel.append({"key": list(k), "arm": arm, "status": "NOT_RUN_BUDGET"}); continue
            key = f"KGT3-P3|{dom}|{rid}|{arm}|{json.dumps(p['order'])}|{json.dumps(b)}"
            if dom == "2d":
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "geom": "original", "kind": "X_CHUNKED",
                           "seq": [[ids[o], int(d)] for o, d in p["order"]], "seq_idx": p["order"], "bounds": b, "y_endpoint": False})
            else:
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "kind": "X_CHUNKED", "order": J24.names("3d", ids, p["order"]),
                           "bounds": b, "y": {"target": "t0", "goal": meta["goal"]}})
            sel.append({"key": list(k), "arm": arm, "status": "QUEUED", "job": key})
    jf = O3 / f"jobs_{dom}.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = O3 / f"selection_{dom}.json"; sf.write_text(json.dumps(sel, indent=1))
    GD.seal(jf); (O3 / f"selection_{dom}.json.SEAL").write_text(GD.sha(sf))
    print(json.dumps({"queued": len(jb), "by": collections.Counter(f"{s['arm']}:{s['status']}" for s in sel)}))


def analyze(dom):
    from scipy.stats import binomtest
    jf, rf = O3 / f"jobs_{dom}.json", O3 / f"phys_{dom}.jsonl"
    c = GD.complete(jf, rf)
    if c["status"] != "COMPLETE":
        raise SystemExit(f"INCOMPLETE {c}")
    P = json.loads((O3 / f"plans_{dom}.json").read_text())
    sel = json.loads((O3 / f"selection_{dom}.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(rf)}
    Y = y2d() if dom == "2d" else {}
    res = {}
    for s in sel:
        k = tuple(s["key"])
        if s["status"] == "QUEUED":
            r = R[s["job"]]; X = r.get("X") or {}
            if dom == "2d":
                unk = str(X.get("teacher_status", "")).startswith("UNKNOWN")
                x = None if unk else X.get("x"); y = Y.get(k[0])
                res[k] = {"succ": None if x is None else bool(x == 1 and X.get("independent_replay") and y == 1), "phase": X.get("failed_phase"), "status": X.get("teacher_status")}
            else:
                x, y = X.get("x"), (r.get("Y") or {}).get("y")
                res[k] = {"succ": None if x is None else bool(x == 1 and y == 1 and (r.get("REPLAY") or {}).get("replay") == 1), "phase": X.get("phase"), "status": X.get("status")}
        elif s["status"] == "REUSED":
            if dom == "2d":
                y = Y.get(k[0]); res[k] = {"succ": None if s["x"] is None else bool(s["x"] == 1 and s.get("replay") and y == 1), "phase": s.get("phase"), "src": s.get("src")}
            else:
                res[k] = {"succ": bool(s["x"] == 1 and s["y"] == 1 and s.get("replay", 1) == 1), "phase": s.get("phase"), "src": s.get("src")}
    import jobs24 as J24
    pan = {rid: (row, meta) for rid, row, _, _, meta in panel(dom)}
    per = collections.defaultdict(dict)
    for rid in P:
        row, meta = pan[rid]; ids = row["inputs"]["ids"]
        for arm in ARMS:
            p = P[rid][arm]; b = bounds(p["partition"])
            k = (rid, json.dumps(p["order"]), json.dumps(b)) if dom == "2d" else (rid, J24.nk(J24.names("3d", ids, p["order"])), J24.nk(b))
            per[rid][arm] = {**res.get(k, {"succ": None, "status": "NOT_RUN"}), "partition": p["partition"], "order": p["order"]}
        if dom == "2d":
            hist = json.loads((K.O / "coh2d" / "R3_4D_2d.json").read_text())["per_root"][rid]["FX-DP"]
            per[rid]["HIST"] = {"succ": hist["succ"], "status": hist.get("status")}
        else:
            h = pan[rid][1]["hist"]; kk = (rid, J24.nk(J24.names("3d", ids, h["order"])), J24.nk(bounds(h["partition"])))
            a = archive(dom).get(kk)
            per[rid]["HIST"] = {"succ": bool(a and a["x"] == 1 and a["y"] == 1 and a.get("replay", 1) == 1) if a else None}
    n = len(P)
    strict = {a: sum(per[r][a]["succ"] is True for r in P) for a in ARMS + ("HIST",)}

    def mc(a, b):
        g = sum(per[r][a]["succ"] is True and per[r][b]["succ"] is not True for r in P); l = sum(per[r][a]["succ"] is not True and per[r][b]["succ"] is True for r in P)
        return {"gain": g, "loss": l, "p_one_sided": binomtest(g, g + l, 0.5, alternative="greater").pvalue if g + l else None}
    thr = 21 if dom == "2d" else 14
    vh, vr = mc("SEL-DP", "HIST"), mc("SEL-DP", "RANDOM")
    dec = {"strict": strict, "decided": {a: sum(per[r][a]["succ"] is not None for r in P) for a in ARMS + ("HIST",)}, "n": n, "vs_HIST": vh, "vs_RANDOM": vr,
           "vs_F0NEW": mc("SEL-DP", "F0-NEW"), "witness_protocol_ok": strict["WITNESS"] >= 0.8 * n}
    passed = strict["SEL-DP"] >= thr and vh["gain"] - vh["loss"] >= 5 and vh["p_one_sided"] is not None and vh["p_one_sided"] < 0.05 and vr["gain"] > vr["loss"] and dec["witness_protocol_ok"]
    dec["P3_GATE"] = "PASS" if passed else ("PARTIAL" if strict["SEL-DP"] >= 0.5 * n else "NOT_RECOVERED")
    out = {"decision": dec, "per_root": per, "completion": c}
    (O3 / f"P3_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    GD.decide(C.FIG3 / "kgt3" / f"p3_{dom}.json", {"P3_GATE": dec["P3_GATE"]}, [jf, rf, O3 / f"plans_{dom}.json", O3 / f"P3_{dom}.json", Path(__file__)], manifests=[(jf, rf)])
    print(json.dumps(dec, default=str))


if __name__ == "__main__":
    a = sys.argv[1]
    {"plan": lambda: plan(sys.argv[2], sys.argv[3]), "jobs": lambda: jobs(sys.argv[2], sys.argv[3]), "analyze": lambda: analyze(sys.argv[2])}[a]()
