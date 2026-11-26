#!/usr/bin/env python3
"""R3.4D 2D certified long-repair ORDER-RECOVERY PILOT (addendum A2; DIAGNOSTIC: the 2D local-X support gate is unresolved).
Cohort = the sealed DEV_ORDER_2D (r31/DEV_ORDER_2D_cohort.json, 30 CERTIFIED_MIN_K roots, 10 per K in {4, 5, 6}); reserve roots never used.
Given the known relocation ASSIGNMENT (sorted; the verified order and every teacher outcome are hidden from the planner), the frozen 2D F0
scorer orders and partitions it (r24.order: exact subset DP, chunk 1-3, marginal pX on canonical prefix scenes, LAM = -log 0.92):
  FX-DP     argmin E over all orders x partitions
  RANDOM    permutation from sha256('R3.4D|' + root) + the frozen-X best partition for that order (matched partition semantics)
  WITNESS   privileged verified order + the frozen-X best partition for it (same chunk-boundary protocol; upper reference)
Physical: physical2d X_CHUNKED (relocation primitives of BXY_X_TEACHER_V1, connector to q_ref at every declared boundary, independent replay).
Every arm reaches the SAME endpoint (same assignment), so endpoint Y is measured once per root (on the first queued job of the root).
Success = X = 1 (replayed) and Y = 1.  UNKNOWN (planner / transit) stays UNKNOWN: strict all-root success counts it as failure; decided-only drops it.
    $PY2D coh2d.py prep               -> O/coh2d/{recs/*.json, rows.jsonl}      (k3scale witness.rec_of + contracts.view2d)
    $PYG  coh2d.py plan               -> O/coh2d/plans.json (+ SEAL)            (frozen 2D bundle; no teacher)
    python coh2d.py jobs CAP          -> O/coh2d/jobs.json (+ SEAL), selection.json
    python coh2d.py analyze           -> O/coh2d/R3_4D_2d.json"""
from __future__ import annotations

import collections, hashlib, json, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C = K.C
O2 = K.O / "coh2d"
COH = HERE / "reports" / "r31" / "DEV_ORDER_2D_cohort.json"
ARMS = ("FX-DP", "RANDOM", "WITNESS")


def cohort():
    return json.loads(COH.read_text())["cohort"]


def prep():
    sys.path.insert(0, os.environ.get("K3SCALE", str(C.NW / "k3scale")))
    import witness as W
    import contracts as CT
    (O2 / "recs").mkdir(parents=True, exist_ok=True)
    rows = []
    for L in cohort():
        rec, ids = W.rec_of({"cells0": L["cells0"], "goal_cell": L["goal_cell"], "root_id": L["root_id"]}, "original")
        p = O2 / "recs" / f"{L['root_id']}.json"; p.write_text(json.dumps(rec))
        inp = CT.view2d(rec)
        assert dict(zip(inp["ids"], inp["cells0"])) == dict(zip(ids, L["cells0"])), L["root_id"]      # same bodies by name (record order differs)
        rows.append({"root_id": L["root_id"], "domain": "2d", "parent_family_id": L["root_id"], "inputs": inp, "path": str(p), "geom": "original"})
    with open(O2 / "rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("PREP", len(rows))


def rows_():
    return {json.loads(l)["root_id"]: json.loads(l) for l in open(O2 / "rows.jsonl")}


def idx(row, seq):
    ids = row["inputs"]["ids"]
    return [[ids.index(o), int(d)] for o, d in seq]


def plan():
    sys.path.insert(0, str(HERE.parent / "r24"))
    import order as OD
    from models import Frozen
    fz = Frozen("2d"); fz.caps = {}
    R = rows_()
    out = {}
    for L in cohort():
        rid = L["root_id"]; row = R[rid]
        W = idx(row, L["witness"])
        A = sorted(W)                                              # the planner sees the UNORDERED assignment only
        t0 = time.perf_counter()
        T = OD.Table(fz, row, A)
        E, o, p = OD.dp(T, lam=OD.LAM)
        dp_s = time.perf_counter() - t0
        rng = random.Random(hashlib.sha256(f"R3.4D|{rid}".encode()).hexdigest())
        ro = [list(a) for a in T.A]; rng.shuffle(ro)
        rE, rp = OD.best_partition_for(T, ro)
        wE, wp = OD.best_partition_for(T, W)                       # privileged reference (evaluator supplies the order)
        ranked = OD.all_orders(T)                                  # every order with its best partition (rank of the witness = analysis only)
        out[rid] = {"K": L["L"], "N": L["N"], "assignment": A, "FX-DP": {"order": o, "partition": list(p), "E": E},
                    "RANDOM": {"order": ro, "partition": list(rp), "E": rE}, "WITNESS": {"order": W, "partition": list(wp), "E": wE},
                    "witness_rank": 1 + next(i for i, r in enumerate(ranked) if r["order"] == W), "n_orders": len(ranked),
                    "chunk_px": {a: [T.get(set(map(tuple, out_o[:s])), out_o[s:s + g])["px"] for s, g in _starts(out_p)]
                                 for a, (out_o, out_p) in (("FX-DP", (o, p)), ("RANDOM", (ro, rp)), ("WITNESS", (W, wp)))},
                    "dp_s": round(dp_s, 3), "scenes_scored": T.scenes}
        print(rid, L["L"], out[rid]["FX-DP"], "witness_rank", out[rid]["witness_rank"], "/", len(ranked), flush=True)
    O2.mkdir(parents=True, exist_ok=True)
    pf = O2 / "plans.json"; pf.write_text(json.dumps(out, indent=1))
    (O2 / "plans.json.SEAL").write_text(K.sha(pf))


def _starts(part):
    s, out = 0, []
    for g in part:
        out.append((s, g)); s += g
    return out


def bounds(part):
    return [s + g for s, g in _starts(part)]


def jobs(cap):
    P = json.loads((O2 / "plans.json").read_text())
    R = rows_()
    seen, jb, sel, yroot = {}, [], [], set()
    for arm in ARMS:
        for rid in sorted(P, key=lambda r: hashlib.sha256(f"R3.4D|{r}".encode()).hexdigest()):
            p = P[rid][arm]; ids = R[rid]["inputs"]["ids"]; b = bounds(p["partition"])
            k = (rid, json.dumps(p["order"]), json.dumps(b))
            if k in seen:
                sel.append({"key": list(k), "arm": arm, "status": "SAME_AS", "same_as": seen[k]}); continue
            seen[k] = arm
            q = 1 + (rid not in yroot)                             # X query (+ the root's single endpoint Y query)
            if sum(1 + bool(j.get("y_endpoint")) for j in jb) + q > int(cap):
                sel.append({"key": list(k), "arm": arm, "status": "NOT_RUN_BUDGET"}); continue
            key = f"R34D|{rid}|{arm}|{json.dumps(p['order'])}|{json.dumps(b)}"
            jb.append({"key": key, "root_id": rid, "arm": arm, "path": R[rid]["path"], "geom": "original", "kind": "X_CHUNKED",
                       "seq": [[ids[o], int(d)] for o, d in p["order"]], "seq_idx": p["order"], "bounds": b, "y_endpoint": rid not in yroot})
            yroot.add(rid)
            sel.append({"key": list(k), "arm": arm, "status": "QUEUED", "job": key})
    O2.mkdir(parents=True, exist_ok=True)
    jf = O2 / "jobs.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = O2 / "selection.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (O2 / (f.name + ".SEAL")).write_text(K.sha(f))
    print(json.dumps({"jobs": len(jb), "queries": sum(1 + bool(j["y_endpoint"]) for j in jb),
                      "by": collections.Counter(f"{s['arm']}:{s['status']}" for s in sel), "seal": K.sha(jf)[:16]}))


def outcome(r):
    """-> x (1 / 0 / None = UNKNOWN), first failing relocation index, status, replay ok."""
    X = r.get("X") or {}
    if r.get("error") or r.get("censored") or not X:
        return {"x": None, "status": "ERROR" if r.get("error") else "NOT_RUN", "fail_at": None, "replay": None}
    st = str(X.get("teacher_status") or "")
    x = X.get("x")
    unk = st.startswith("UNKNOWN")
    ph = str(X.get("failed_phase") or "")
    fa = int(ph.split(":")[1]) if ":" in ph and ph.split(":")[1].isdigit() else None
    rep = X.get("independent_replay")
    rep_ok = None if rep is None else bool(rep.get("ok") if isinstance(rep, dict) else rep)
    return {"x": None if unk else x, "status": st, "phase": ph, "fail_at": fa, "replay": rep_ok, "cpu_s": r.get("cpu_s")}


def analyze():
    P = json.loads((O2 / "plans.json").read_text())
    sel = json.loads((O2 / "selection.json").read_text())
    jb = {j["key"]: j for j in json.loads((O2 / "jobs.json").read_text())}
    R = {json.loads(l)["key"]: json.loads(l) for l in open(O2 / "phys.jsonl")} if (O2 / "phys.jsonl").exists() else {}
    Y = {}
    for k, j in jb.items():
        if j["y_endpoint"] and k in R:
            yy = R[k].get("Y") or {}
            Y[j["root_id"]] = None if str(yy.get("teacher_status", "")).startswith("UNKNOWN") else yy.get("y")
    res = {}
    for s in sel:
        if s["status"] == "QUEUED":
            res[tuple(s["key"])] = outcome(R.get(s["job"], {})) | {"job": s["job"]}      # SAME_AS entries share this key
    per = collections.defaultdict(dict)
    for rid, p in P.items():
        for a in ARMS:
            k = (rid, json.dumps(p[a]["order"]), json.dumps(bounds(p[a]["partition"])))
            o = res.get(k, {"x": None, "status": "NOT_RUN"})
            y = Y.get(rid)
            succ = None if o["x"] is None or (o["x"] == 1 and y is None) else bool(o["x"] == 1 and o.get("replay") is not False and y == 1)
            per[rid][a] = {**o, "y": y, "succ": succ, "partition": p[a]["partition"], "returns": len(p[a]["partition"]) - 1, "order": p[a]["order"],
                           "first_chunk_px": P[rid]["chunk_px"][a][0] if P[rid]["chunk_px"][a] else None}
    from scipy.stats import binomtest
    summ = {}
    strata = {"all": lambda r: True, **{f"K{k}": (lambda r, k=k: P[r]["K"] == k) for k in (4, 5, 6)},
              **{f"N{a}-{b}": (lambda r, a=a, b=b: a <= P[r]["N"] <= b) for a, b in ((14, 16), (17, 18), (19, 20))}}
    for sn, f in strata.items():
        rs = [r for r in P if f(r)]
        summ[sn] = {a: {"n": len(rs), "strict_success": sum(per[r][a]["succ"] is True for r in rs), "decided": sum(per[r][a]["succ"] is not None for r in rs),
                        "unknown": sum(per[r][a]["succ"] is None for r in rs)} for a in ARMS}
    def pair(a, b):
        g = sum(per[r][a]["succ"] is True and per[r][b]["succ"] is not True for r in P)
        l = sum(per[r][a]["succ"] is not True and per[r][b]["succ"] is True for r in P)
        return {"gain": g, "loss": l, "net": g - l, "mcnemar_one_sided_p": binomtest(g, g + l, 0.5, alternative="greater").pvalue if g + l else None}
    fx = summ["all"]["FX-DP"]["strict_success"]; n = len(P)
    out = {"summary": summ, "paired": {"FX-DP_vs_RANDOM": pair("FX-DP", "RANDOM"), "WITNESS_vs_FX-DP": pair("WITNESS", "FX-DP")},
           "reference_bands": {"FX-DP_strict": fx, "n": n, "band": "RECOVERED_REF" if fx >= 0.7 * n else "PARTIAL_REF" if fx >= 0.5 * n else "NOT_RECOVERED_REF",
                               "note": "R3_PREREG R3_4.2d 70 % / 50 % used as DIAGNOSTIC reference only (2D local-X support gate unresolved): no formal gate"},
           "fail_location": {a: collections.Counter(f"{per[r][a]['status']}@{per[r][a].get('phase')}" for r in P if per[r][a]["succ"] is not True) for a in ARMS},
           "witness_rank": {r: [P[r]["witness_rank"], P[r]["n_orders"]] for r in P}, "exact_witness_match": sum(P[r]["FX-DP"]["order"] == P[r]["WITNESS"]["order"] for r in P),
           "endpoint_Y": collections.Counter(str(v) for v in Y.values()), "per_root": per,
           "queries": sum(1 + bool(j["y_endpoint"]) for k, j in jb.items() if k in R), "cpu_h": sum(R[k].get("cpu_s", 0) for k in R) / 3600}
    (O2 / "R3_4D_2d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("paired", "reference_bands", "exact_witness_match", "endpoint_Y", "queries", "cpu_h")}, default=str))
    print(json.dumps(summ["all"]))


if __name__ == "__main__":
    {"prep": prep, "plan": plan, "jobs": lambda: jobs(sys.argv[2]), "analyze": analyze}[sys.argv[1]]()
