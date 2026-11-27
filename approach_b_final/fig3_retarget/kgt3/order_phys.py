#!/usr/bin/env python3
"""R4.2 physical known-assignment order recovery, 3D (NEW DEVELOPMENT DIAGNOSTIC; not P2 reopening, not the P3 confirmation gate).
Panel: the 20 exposed 3D DEV witness roots (r23 roster; R2.4 known unordered assignment = the witness SET, order hidden).
Arms, one sealed (order, partition) per root before any outcome, no replacement:
  F0 / M1s / G1s / O2   learned X (frozen production F0, R3 query-relative MLP / GNN, KGT3 M1ft_O2_s0) + compose.grouped_dp (lambda 0,
                        has_multi for m > 3, R4.0 energy); identical candidate grammar (every order x every chunking of the given set).
  RANDOM                order from sha256('KGT3-P3|' + root), partition = F0 fixed-order DP (declared).
  WITNESS               verified witness order (privileged; positive control), partition = F0 fixed-order DP (declared).
Partition study (fixed order, chunk boundaries varied): WITNESS order and G1s order x {all singletons, F0-DP partition, front-loaded max
chunks, back-loaded max chunks}; isolates ordering vs boundary vs connector failures.
Physical: X_CHUNKED + endpoint Y (t0, goal) + independent replay (physical3d.py, unchanged teacher / budgets).  Exact archived
(root, ordered names, bounds) outcomes are REUSED (R2.4 archive; quarantined R3.4 runs only as labelled reuse).
    $PYG order_phys.py plan            -> O/kgt3/r4/order3d/plans.json (+ SEAL)
    python order_phys.py jobs CAP      -> jobs.json (+ SEAL), selection.json
    python order_phys.py analyze       -> R4_2_order3d.json"""
from __future__ import annotations

import collections, hashlib, itertools, json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
C = K.C
OD = C.FIG3 / "kgt3" / "r4" / "order3d"
SPECS = {"F0": "F0", "M1s": "M1s_s0", "G1s": "G1s_s0", "O2": "M1ft_O2_s0"}
ARMS = ("F0", "M1s", "G1s", "O2", "RANDOM", "WITNESS")


def bounds(part):
    s, out = 0, []
    for g in part:
        s += g; out.append(s)
    return out


def front(m):
    p = []
    while m > 0:
        p.append(min(3, m)); m -= p[-1]
    return p


def plan():
    import compose as CP
    import learn as LN
    import p3 as P3
    import planners as PL
    import views as V
    pan = P3.panel("3d")
    M = {}
    for a, spec in SPECS.items():
        fz, net = LN.load("3d", spec); fz.net = net; fz.reset(); fz.caps = {}
        M[a] = fz
    out = {}
    for rid, row, A, W, meta in pan:
        r0 = {"root_id": row["root_id"], "domain": row["domain"], "inputs": row["inputs"]}
        A = sorted(tuple(map(int, a)) for a in A); W = [tuple(map(int, a)) for a in W]
        assert sorted(W) == A, rid
        rec = {"meta": {k: v for k, v in meta.items() if k != "hist"}, "assignment": [list(a) for a in A], "arms": {}, "rank": {}, "cost": {}}
        for a, fz in M.items():
            fz.reset()
            t0 = time.perf_counter()
            s = PL.assignment_given(fz, r0, A, witness=W if a == "F0" else None)
            if str(fz.dev).startswith("cuda"):
                fz.torch.cuda.synchronize()
            rec["cost"][a] = {"wall_s": round(time.perf_counter() - t0, 3), **s["scores"], **{k: fz.c[k] for k in ("x_unique", "y_unique", "batches", "cache_hits")}}
            rec["arms"][a] = {k: s["SEL-DP"][k] for k in ("order", "partition", "E", "chunk_px")}
            if a == "F0":
                rec["arms"]["RANDOM"] = {k: s["RANDOM"][k] for k in ("order", "partition", "E", "chunk_px")}
                rec["arms"]["WITNESS"] = {k: s["WITNESS"][k] for k in ("order", "partition", "E", "chunk_px")}
            # evaluator analysis only: energy of EVERY order of the set (best admissible partition) under this model
            T = CP.Scores(fz, r0, V.rebase); T.need(CP.requests(A))
            E = sorted(((CP.fixed_order_dp(T, list(o))[0], list(map(list, o))) for o in itertools.permutations(A)), key=lambda t: (round(t[0], 12), json.dumps(t[1])))
            wr = next(i for i, (_, o) in enumerate(E) if [tuple(x) for x in o] == W)
            rec["rank"][a] = {"witness_rank": wr, "n_orders": len(E), "quantile": wr / max(1, len(E) - 1), "first_action_ok": rec["arms"][a]["order"][0] == list(W[0]),
                              "F_by_order": {json.dumps(o): F for F, o in E}}
        out[rid] = rec
        print(rid, {a: (v["order"], v["partition"]) for a, v in rec["arms"].items()}, {a: r["witness_rank"] for a, r in rec["rank"].items()}, flush=True)
    OD.mkdir(parents=True, exist_ok=True)
    pf = OD / "plans.json"; pf.write_text(json.dumps(out, indent=1))
    (OD / "plans.json.SEAL").write_text(GD.sha(pf))


def archive():
    """Exact (root, ordered names, bounds) -> outcome from earlier X_CHUNKED + endpoint-Y runs with the same teacher contract."""
    import jobs24 as J24
    A = {}
    srcs = [(C.FIG3 / "r24" / "jobs_24_3d.json", C.FIG3 / "r24" / "phys_24_3d.jsonl", "R2.4"),
            (C.FIG3 / "r3" / "r34" / "jobs_34_3d.json", C.FIG3 / "r3" / "QUARANTINE_unauthorized" / "phys_34_3d.jsonl", "R3.4-QUARANTINED-DIAGNOSTIC")]
    for jf, rf, tag in srcs:
        J = json.loads(jf.read_text()); J = J if isinstance(J, list) else [x for v in J.values() for x in v]
        R = {json.loads(l)["key"]: json.loads(l) for l in open(rf)}
        for j in J:
            r = R.get(j["key"])
            if not r or r.get("censored") or r.get("error") or j.get("cells0") or not j.get("y") or j.get("kind") != "X_CHUNKED":
                continue
            k = (j["root_id"], J24.nk(j["order"]), J24.nk(j["bounds"]))
            A.setdefault(k, {"rec": r, "src": f"{tag}:{j['key']}"})
    return A


def jobs(cap):
    import jobs24 as J24
    import p3 as P3
    P = json.loads((OD / "plans.json").read_text())
    if GD.sha(OD / "plans.json") != (OD / "plans.json.SEAL").read_text().strip():
        raise SystemExit("plans not sealed")
    pan = {rid: (row, meta) for rid, row, _, _, meta in P3.panel("3d")}
    A = archive()
    items = []
    for rid in sorted(P, key=lambda r: hashlib.sha256(f"R4.2|{r}".encode()).hexdigest()):
        for arm in ARMS:
            p = P[rid]["arms"][arm]; items.append((rid, arm, "main", p["order"], p["partition"]))
    for rid in sorted(P, key=lambda r: hashlib.sha256(f"R4.2|{r}".encode()).hexdigest()):  # partition study (after every main job)
        m = len(P[rid]["assignment"])
        for base in ("WITNESS", "G1s"):
            o = P[rid]["arms"][base]["order"]
            for tag, part in (("singletons", [1] * m), ("dp", P[rid]["arms"]["F0" if base == "WITNESS" else "G1s"]["partition"]), ("front", front(m)), ("back", front(m)[::-1])):
                items.append((rid, f"{base}:{tag}", "partition", o, part))
    seen, jb, sel = {}, [], []
    for rid, arm, study, order, part in items:
        row, meta = pan[rid]; ids = row["inputs"]["ids"]; b = bounds(part)
        names = J24.names("3d", ids, order)
        k = (rid, J24.nk(names), J24.nk(b))
        base = {"root_id": rid, "arm": arm, "study": study, "order": order, "partition": part}
        if k in seen:
            sel.append({**base, "status": "SAME_AS", "same_as": seen[k]}); continue
        key = f"R4.2|3d|{rid}|{json.dumps(order)}|{json.dumps(b)}"
        seen[k] = key
        if k in A:
            sel.append({**base, "status": "REUSED", "job": key, "src": A[k]["src"]}); continue
        if len(jb) + 1 > int(cap):
            sel.append({**base, "status": "NOT_RUN_BUDGET", "job": key}); continue
        jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "kind": "X_CHUNKED", "order": names, "bounds": b, "y": {"target": "t0", "goal": meta["goal"]}})
        sel.append({**base, "status": "QUEUED", "job": key})
    jf = OD / "jobs.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = OD / "selection.json"; sf.write_text(json.dumps(sel, indent=1))
    GD.seal(jf); (OD / "selection.json.SEAL").write_text(GD.sha(sf))
    print(json.dumps({"queued": len(jb), "by": collections.Counter(f"{s['study']}:{s['status']}" for s in sel)}))


def result(r):
    """-> evidence record of one physical run (R4.0 taxonomy): success needs X = 1, endpoint Y = 1 and independent replay = 1."""
    X, Y, RP = r.get("X") or {}, r.get("Y") or {}, r.get("REPLAY") or {}
    tr = X.get("trace") or []
    nconn = sum(1 for s in tr if s.get("kind") == "connector")
    ph = str(X.get("phase") or "")
    return {"x": X.get("x"), "y": Y.get("y"), "replay": RP.get("replay"), "succ": bool(X.get("x") == 1 and Y.get("y") == 1 and RP.get("replay") == 1),
            "x_outcome": GD.outcome(r, "X"), "y_outcome": GD.outcome(r, "Y") if r.get("Y") else None, "phase": ph or None, "status": X.get("status"),
            "first_failed": int(ph.split(":")[1]) if ph.startswith("relocation") else None, "connector_fail": ph.startswith("boundary"),
            "connectors_ok": nconn, "cpu_s": r.get("cpu_s"), "wall_s": r.get("wall_s"), "y_status": Y.get("status")}


def analyze():
    from scipy.stats import binomtest
    jf, rf = OD / "jobs.json", OD / "phys.jsonl"
    c = GD.complete(jf, rf)
    if c["status"] != "COMPLETE":
        raise SystemExit(f"INCOMPLETE {c}")
    P = json.loads((OD / "plans.json").read_text())
    sel = json.loads((OD / "selection.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(rf)}
    A = archive()
    import jobs24 as J24
    byjob = {}
    for s in sel:
        if s["status"] == "QUEUED":
            byjob[s["job"]] = {**result(R[s["job"]]), "src": "NEW"}
        elif s["status"] == "REUSED":
            k = next(k for k, v in A.items() if v["src"] == s["src"])
            byjob[s["job"]] = {**result(A[k]["rec"]), "src": s["src"]}
    res = collections.defaultdict(dict)
    for s in sel:
        j = s.get("job") or s.get("same_as")
        res[s["root_id"]][s["arm"]] = {**(byjob.get(j) or {"succ": None, "x_outcome": "NOT_RUN"}), "order": s["order"], "partition": s["partition"], "study": s["study"]}
    roots = sorted(P)
    n = len(roots)
    summ = {}
    for arm in ARMS:
        rr = [res[r][arm] for r in roots]
        summ[arm] = {"succ": sum(x["succ"] is True for x in rr), "x": sum(x.get("x") == 1 for x in rr), "y_given_x": sum(x.get("x") == 1 and x.get("y") == 1 for x in rr),
                     "replay_given_xy": sum(x.get("x") == 1 and x.get("y") == 1 and x.get("replay") == 1 for x in rr),
                     "first_failed": dict(collections.Counter(x.get("first_failed") for x in rr if x.get("x") == 0)),
                     "connector_fail": sum(bool(x.get("connector_fail")) for x in rr), "x_outcomes": dict(collections.Counter(x.get("x_outcome") for x in rr)),
                     "new": sum(x.get("src") == "NEW" for x in rr), "reused": sum(str(x.get("src", "")).startswith("R") for x in rr)}
        if arm in SPECS:
            summ[arm]["first_action_ok"] = sum(P[r]["rank"][arm]["first_action_ok"] for r in roots)
            summ[arm]["witness_rank_median_quantile"] = sorted(P[r]["rank"][arm]["quantile"] for r in roots)[n // 2]
            summ[arm]["plan_wall_s_median"] = sorted(P[r]["cost"][arm]["wall_s"] for r in roots)[n // 2]
            summ[arm]["x_unique_median"] = sorted(P[r]["cost"][arm]["x_unique"] for r in roots)[n // 2]

    def mc(a, b):
        g = sum(res[r][a]["succ"] is True and res[r][b]["succ"] is not True for r in roots)
        l = sum(res[r][a]["succ"] is not True and res[r][b]["succ"] is True for r in roots)
        return {"gain": g, "loss": l, "p_two_sided": binomtest(g, g + l, 0.5).pvalue if g + l else None}
    paired = {f"{a}_vs_{b}": mc(a, b) for a in ("G1s", "M1s", "O2") for b in ("F0", "RANDOM")}
    paired["F0_vs_RANDOM"] = mc("F0", "RANDOM")
    # physical concordance: within a root, every pair of distinct executed orders of the same set (any study) with different outcomes
    conc = {}
    for a in SPECS:
        pairs = []
        for r in roots:
            ex = {}
            for arm, v in res[r].items():
                if v.get("succ") is not None and v.get("x_outcome") not in ("UNRESOLVED", "BUDGET_NO_PLAN", "OPERATIONAL_FAILURE"):
                    ex.setdefault(json.dumps(v["order"]), set()).add(bool(v["succ"]))
            ok = {o: s.pop() for o, s in ex.items() if len(s) == 1}
            Fm = P[r]["rank"][a]["F_by_order"]
            pos = [o for o, s in ok.items() if s]; neg = [o for o, s in ok.items() if not s]
            for p in pos:
                for q in neg:
                    pairs.append(1.0 if Fm[p] < Fm[q] else 0.5 if Fm[p] == Fm[q] else 0.0)
        conc[a] = {"pairs": len(pairs), "concordance": sum(pairs) / len(pairs) if pairs else None}
    # partition study: per root, which chunkings of the same fixed order succeed
    part = collections.Counter()
    for r in roots:
        for base in ("WITNESS", "G1s"):
            v = {t: res[r].get(f"{base}:{t}", {}).get("succ") for t in ("singletons", "dp", "front", "back")}
            part[f"{base}:pattern:" + "".join("1" if v[t] else ("0" if v[t] is False else "?") for t in ("singletons", "dp", "front", "back"))] += 1
            for t in v:
                part[f"{base}:{t}:succ"] += v[t] is True
    cpu = sum(R[k].get("cpu_s", 0) for k in R) / 3600
    out = {"n_roots": n, "summary": summ, "paired": paired, "physical_concordance": conc, "partition_study": dict(sorted(part.items())), "per_root": res,
           "completion": c, "cpu_h_new": cpu, "label": "R4.2 DEVELOPMENT DIAGNOSTIC (exposed roots); not P2 reopening, not the P3 confirmation gate"}
    (OD / "R4_2_order3d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_root",)}, default=str)[:4000])


if __name__ == "__main__":
    a = sys.argv[1]
    {"plan": plan, "jobs": lambda: jobs(sys.argv[2]), "analyze": analyze}[a]()
