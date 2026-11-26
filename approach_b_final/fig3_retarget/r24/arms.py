#!/usr/bin/env python3
"""R2.4 model-side planners (PUBLIC rows + frozen bundle; the oracle planner additionally reads ONE private unordered assignment per root).

R2.4A oracle ordering (3D K4/K5 exposed roots; assignment given, witness ORDER hidden):
  A-DP      exact joint order + partition DP (order.dp, LAM per return)          A-DP0   same, LAM = 0 (model-only sensitivity)
  A-PRE     DP restricted to linear extensions of model-discovered pairwise prerequisite edges (order.pair_edges; retargeting inside A)
  logged: every order's best partition + E (witness-order rank), local chunk readouts, Y_global vs Y_rebased of the endpoint.
R2.4B deployment arms (no private data).  One shared discovery run per root (recursive.discover, R-FIG3 semantics, BOUNDED EXHAUSTIVE local
groups up to CFG24.exhaustive_max_groups ordered groups per expansion; any remaining staged-beam fallback is counted):
  R-FIG3-X   action SETS of the recursion pool, each re-ordered by the joint order/partition DP (free permutations)
  R-FIG3-XP  same, DP restricted to the candidate's own PREREQ + LOCAL edges (prerequisite-constrained)
  R-FIG3-XC  composed order kept, best partition only (attribution: re-ordering vs composition)
  GA-INIT    global assignment search over the INITIAL D4 at S0, then the DP
  GA-UNION   global assignment search over the UNION of refreshed proposals produced by the discovery run, then the DP
Set score (all arms): m <= 3 also offers the single chunk exact p11 at S0 (every permitted order); multi-chunk E = DP + -log Y(set), Y =
Y_global (original-root edit node; declared primary) -- the rebased endpoint Y is logged on identical endpoints (never used to choose).
Assignment search: per size k, exhaustive over legal k-sets when the count <= ASSIGN_EXH, else every one-action extension of the top
ASSIGN_BEAM size-(k-1) sets by Y_global (declared truncation, counted); shortlist = top PER_SIZE sets per size by Y_global.  Selection: RK.select
(production NOOP gate at S0, argmin E with fixed tie-breaks).
    python arms.py oracle DOM ROSTER PRIVATE_DIR OUT.json
    python arms.py deploy DOM ROSTER OUT.jsonl"""
from __future__ import annotations

import itertools, json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import construct as CO  # noqa: E402
import order as OD  # noqa: E402
import rank as RK  # noqa: E402
import recursive as RC  # noqa: E402
import views as V  # noqa: E402
from models import CapReached  # noqa: E402

CFG24 = {"exhaustive_max_groups": 50000, "x_unique": 1_500_000, "y_unique": 600_000, "wall_s": 180.0}
ASSIGN_EXH, ASSIGN_BEAM, PER_SIZE = 150_000, 256, 4
DEPLOY = ["R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC", "GA-INIT", "GA-UNION"]


def _elem(sizes, k):
    e = [1] + [0] * k
    for s in sizes:
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * s
    return e[k]


def enum_sets(fz, row0, D, m_max, log):
    """Legal assignments of size 1..m_max over proposal dict D, scored by Y_global (exhaustive per size when affordable, else beam)."""
    D = {o: sorted(set(v)) for o, v in D.items() if v}
    acts = sorted((o, d) for o, v in D.items() for d in v)
    sizes = [len(v) for v in D.values()]
    out, prev = {}, None
    for k in range(1, m_max + 1):
        if k > len(D):
            break
        if _elem(sizes, k) <= ASSIGN_EXH:
            cand = [tuple(sorted(A)) for A in CO.assignments(D, k)]
            mode = "exhaustive"
        else:
            seen = {}
            for S in prev:
                ob, ds = {o for o, _ in S}, {d for _, d in S}
                for a in acts:
                    if a[0] not in ob and a[1] not in ds:
                        seen.setdefault(tuple(sorted(S + (a,))), None)
            cand, mode = list(seen), "beam"
        cand = [A for A in cand if V.legal_seq(row0, [list(a) for a in A], m_max)]
        ys = fz.y_global(row0, [list(map(list, A)) for A in cand]) if cand else []
        sc = sorted(zip(cand, ys), key=lambda t: (-t[1], json.dumps(t[0])))
        log["assign"].append({"k": k, "mode": mode, "count_upper": _elem(sizes, k), "scored": len(cand), "kept": min(len(sc), ASSIGN_BEAM)})
        for A, y in sc:
            out[A] = y
        prev = [A for A, _ in sc[:ASSIGN_BEAM]]
        if not prev:
            break
    return out


def shortlist(scored):
    by = {}
    for A, y in scored.items():
        by.setdefault(len(A), []).append((A, y))
    return [A for k in sorted(by) for A, _ in sorted(by[k], key=lambda t: (-t[1], json.dumps(t[0])))[:PER_SIZE]]


def score_set(fz, row0, A, before=(), fixed_order=None, deadline=None):
    """-> candidate dict (seq, E, partition, ...) for one set; m <= 3 adds the single-chunk exact p11 at S0 over permitted orders."""
    if deadline and time.perf_counter() > deadline:
        raise TimeoutError("hard deadline")
    A = sorted(OD._t(A)); m = len(A)
    T = OD.Table(fz, row0, A)
    yg = fz.y_global(row0, [list(map(list, A))])[0]
    cands = []
    orders = [fixed_order] if fixed_order else [list(map(list, o)) for o in itertools.permutations(A) if not before or OD._ok(set(), o, OD._pred(before))]
    if m <= 3 and orders:
        sc = fz.score(row0, orders)
        for o, x in zip(orders, sc):
            cands.append((-math.log(max(OD.EPS, x["p11"])), 1, o, [m]))
    if m >= 2:
        if fixed_order:
            r = OD.best_partition_for(T, fixed_order, min_chunks=2)
            if r:
                cands.append((r[0] - math.log(max(OD.EPS, yg)), len(r[1]), fixed_order, list(r[1])))
        else:
            r = OD.dp(T, before=before, min_chunks=2)
            if r:
                cands.append((r[0] - math.log(max(OD.EPS, yg)), len(r[2]), r[1], r[2]))
    if not cands:
        return None
    E, n, o, p = min(cands, key=lambda t: (round(t[0], 12), t[1], json.dumps(t[2])))
    return {"seq": o, "E": E, "partition": p, "y_global": yg, "set": [list(a) for a in A], "scenes": T.scenes}


def _select(fz, row0, rule, cands, t0, extra):
    pick, why, noop = RK.select(row0, [c for c in cands if c], fz, rule)
    dec = "NOOP" if why == "NOOP_GATE" else ("REPAIR" if pick else "ABSTAIN")
    top = sorted([c for c in cands if c], key=lambda c: (round(c["E"], 12), len(c["seq"])))[:40]
    return {"decision": dec, "seq": pick["seq"] if pick else None, "partition": pick["partition"] if pick else None, "E": pick["E"] if pick else None,
            "y_global": pick["y_global"] if pick else None, "p_noop": noop, "n_cands": len([c for c in cands if c]),
            "top": [{k: c[k] for k in ("seq", "E", "partition", "y_global")} for c in top], "rank_s": round(time.perf_counter() - t0, 3), **extra}


def _fresh(fz, t_disc):
    """Per-arm ranking: empty X/Y readout caches (proposal cache kept: the discovery output), own deadline = wall - discovery time."""
    fz._x.clear(); fz._y.clear()
    fz.c = {k: 0 for k in fz.c}                                   # per-arm counters and caps (ranking stage)
    t = time.perf_counter()
    return t, None, t + CFG24["wall_s"] - t_disc


def _delta(fz, c0):
    return dict(fz.c)


def deploy_root(fz, row0, rule):
    """All R2.4B arms for one root from one discovery run (+ GA-INIT from S0 only).  Counters are logged per stage."""
    out = {}
    m_max = RC.CFG["m_max"][row0["domain"]]
    # GA-INIT (no discovery)
    fz.reset(); fz.caps = {"x_unique": CFG24["x_unique"], "y_unique": CFG24["y_unique"]}
    t0 = time.perf_counter(); dl = t0 + CFG24["wall_s"]
    log = {"assign": []}
    D0 = {o: v for o, v in fz.proposals(row0, V.eligible(row0)).items() if v}
    stop = None
    try:
        sc = enum_sets(fz, row0, D0, m_max, log)
        cands = [score_set(fz, row0, A, deadline=dl) for A in shortlist(sc)]
    except (TimeoutError, CapReached) as e:
        cands, stop = [], f"{type(e).__name__}:{e}"
    out["GA-INIT"] = _select(fz, row0, rule, cands, t0, {"latency_s": round(time.perf_counter() - t0, 3), "cap_stop": stop, "counters": dict(fz.c),
                                                         "assign_log": log["assign"], "pool_actions": sorted([o, d] for o, v in D0.items() for d in v)})
    # shared discovery (R-FIG3 recursion with bounded exhaustive local groups)
    t1 = time.perf_counter()
    ctx, pool, tree, dstop = RC.discover(fz, row0, "R-FIG3", CFG24)             # resets fz (caches + counters)
    t_disc = time.perf_counter() - t1
    disc_c = {**ctx.n, **fz.c}
    union = {}
    for Dp in fz._p.values():
        for o, ds in Dp.items():
            union.setdefault(int(o), set()).update(int(d) for d in ds)
    el = set(V.eligible(row0))
    union = {o: sorted(v) for o, v in union.items() if o in el and v}
    common = {"discovery_s": round(t_disc, 3), "discovery_stop": dstop, "discovery_counters": disc_c, "pool": len(pool),
              "union_actions": sorted([o, d] for o, v in union.items() for d in v)}
    sets = {}
    for P, E, sd in pool.values():
        sets.setdefault(tuple(sorted(OD._t(P))), []).append((P, E))
    for arm in ("R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC"):
        t2, c0, dl = _fresh(fz, t_disc)
        stop, cands = None, []
        try:
            for A, lst in sorted(sets.items()):
                if arm == "R-FIG3-X":
                    cands.append(score_set(fz, row0, A, deadline=dl))
                else:
                    for P, E in lst:
                        if arm == "R-FIG3-XP":
                            keys = {V.key(row0, a): OD._t([a])[0] for a in P}
                            bef = [(keys[x], keys[y]) for x, y, k in E if k in ("PREREQ", "LOCAL") and x in keys and y in keys]
                            cands.append(score_set(fz, row0, A, before=bef, deadline=dl))
                        else:
                            cands.append(score_set(fz, row0, A, fixed_order=[list(a) for a in P], deadline=dl))
        except (TimeoutError, CapReached) as e:
            stop = f"{type(e).__name__}:{e}"
        out[arm] = _select(fz, row0, rule, cands, t2, {"latency_s": round(t_disc + time.perf_counter() - t2, 3), "cap_stop": stop or dstop,
                                                       "counters": _delta(fz, c0), "n_sets": len(sets), **common})
    t2, c0, dl = _fresh(fz, t_disc)
    stop, log, cands, sc = None, {"assign": []}, [], {}
    try:
        sc = enum_sets(fz, row0, union, m_max, log)
        cands = [score_set(fz, row0, A, deadline=dl) for A in shortlist(sc)]
    except (TimeoutError, CapReached) as e:
        stop = f"{type(e).__name__}:{e}"
    out["GA-UNION"] = _select(fz, row0, rule, cands, t2, {"latency_s": round(t_disc + time.perf_counter() - t2, 3), "cap_stop": stop or dstop,
                                                          "counters": _delta(fz, c0), "assign_log": log["assign"], **common})
    out["_ga_union_sets"] = [[list(map(list, A)), y] for A, y in sorted(sc.items(), key=lambda t: -t[1])[:300]] if not stop else []
    out["_tree"] = tree
    return out


def oracle_root(fz, row0, A):
    """R2.4A: fixed unordered assignment A (indices), witness order hidden."""
    fz.reset(); fz.caps = {}
    t0 = time.perf_counter()
    T = OD.Table(fz, row0, A)
    res = {"assignment": [list(a) for a in T.A]}
    for name, lam in (("A-DP", OD.LAM), ("A-DP0", 0.0)):
        E, o, p = OD.dp(T, lam=lam)
        res[name] = {"order": o, "partition": p, "E": E}
    res["dp_s"] = round(time.perf_counter() - t0, 3)
    edges, deltas = OD.pair_edges(fz, row0, T.A)
    r = OD.dp(T, before=[(a, b) for a, b, _ in edges])
    res["A-PRE"] = {"order": r[1], "partition": r[2], "E": r[0], "edges": edges, "deltas": deltas}
    res["orders"] = OD.all_orders(T)
    res["chunks"] = [{"prefix": OD.canon(S), "chunk": [list(a) for a in C], **{k: x[k] for k in ("px", "p11", "py", "px1", "px0")}} for (S, C), x in T.r.items()]
    res["y_global"] = fz.y_global(row0, [res["assignment"]])[0]
    res["y_rebased"] = fz.p_noop(V.rebase(row0, res["assignment"]))
    res["latency_s"] = round(time.perf_counter() - t0, 3)
    res["counters"] = dict(fz.c); res["scenes"] = T.scenes
    return res


def main():
    from models import Frozen, sync
    cmd, dom, roster = sys.argv[1:4]
    fz = Frozen(dom)
    rule = fz.man["config"]["rule"]
    rows = [json.loads(l) for l in open(roster)]
    if cmd == "oracle":
        priv, out = Path(sys.argv[4]), sys.argv[5]
        res = {}
        for r in rows:
            rec = json.loads((priv / f"{r['root_id']}.json").read_text())
            ids = r["inputs"]["ids"]
            A = sorted([ids.index(o), rc[0] * 6 + rc[1]] for o, rc in rec["k45"]["witness"]["order"])       # unordered; order NOT passed
            sync(fz)
            res[r["root_id"]] = oracle_root(fz, r, A)
            res[r["root_id"]]["device"] = fz.torch.cuda.get_device_name(0)
            print(r["root_id"], res[r["root_id"]]["A-DP"], res[r["root_id"]]["latency_s"], flush=True)
        Path(out).write_text(json.dumps(res))
    else:
        out = sys.argv[4]
        done = {json.loads(l)["root_id"] for l in open(out)} if Path(out).exists() else set()
        with open(out, "a") as f:
            for r in rows:
                if r["root_id"] in done:
                    continue
                sync(fz)
                res = deploy_root(fz, r, rule)
                sync(fz)
                f.write(json.dumps({"root_id": r["root_id"], "device": fz.torch.cuda.get_device_name(0), **res}) + "\n"); f.flush()
                print(r["root_id"][-24:], {a: (res[a]["decision"], res[a]["seq"], res[a]["partition"], res[a]["latency_s"], res[a]["cap_stop"]) for a in DEPLOY}, flush=True)


if __name__ == "__main__":
    main()
