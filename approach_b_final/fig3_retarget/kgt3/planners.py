"""KGT3 deployable Fig. 3 planners + the isolated assignment-given diagnostic (FIG3_KGT3_PREREG P3 / P4).  Public row + learned models only:
the released task-conditioned cVAE (fz.proposals), the coupled X/Y scorer (fz.score / y_global / p_noop; F0 or a scaling checkpoint via
fz.net), views.rebase (hypothetical pose edits, temporary tasks) and the monotone grammar.  No physical module is imported here (tested).

Arms (one sealed plan per root and arm):
  REC-ORDERED  Fig. 3A: recursive.discover (R-FIG3: ordered seeds <= 3 from the released sampler + p11, every action retargeted on its
               branch-local pre-action scene, ordered enabling chunks 1..3 by temporary p11, recursion, insertion before the parent) with
               the scaling option ylowx_extra = 1 (one extra admitted high-temporary-Y repair per action); the recursive ORDER is kept and
               only the chunk boundaries are optimized (compose.fixed_order_dp, has_multi for length > 3).
  REC-REORDER  hybrid control: the same pool, grouped subset DP restricted to the candidate's learned PREREQ + LOCAL edges.
  FLAT-INSERT  control: recursive.discover F-FLAT (original-task insertion, no retargeting), same final scoring.
  GA-EXACT / GA-BOUNDED   Fig. 3B: complete legal assignments over the INITIAL D4 pool for sizes 1..H; global Y once per assignment; every
               (exact) or every retained (bounded) assignment gets the grouped subset DP (chunk membership, internal order, sizes).
  GA-YONLY     control: the same candidate domain, historical Y-only top-4 per size, same DP.
Final energy: m <= 3 single chunk = -log p11 (exact coupled joint); otherwise sum of -log marginal pX of the anchored chunks - log Y_global.
Selection: production NOOP gate on p_noop(S0); candidates = the arm's candidates + the production K <= 3 floor (rank.b0 with the PRODUCTION
F0 scorer and rules, re-scored as one chunk under the arm's model); argmin (round(E, 12), length, chunks, canonical JSON); ABSTAIN if none."""
from __future__ import annotations

import hashlib, itertools, json, math, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import compose as CP  # noqa: E402
import construct as CO  # noqa: E402
import rank as RK  # noqa: E402
import recursive as RC  # noqa: E402
import views as V  # noqa: E402
from models import CapReached  # noqa: E402

CFG = {"H": {"2d": 5, "3d": 5}, "wall_s": 180.0,   # R5: H = 5 in both domains (KGT3 / R4 used 2d: 6)
       "x_unique": 1_500_000, "y_unique": 600_000, "assign_per_size": 150_000,
       "exact_x_est": 1_200_000, "retain": {"y": 96, "x": 96, "div": 64}, "yonly": 4, "rule": {"noop_gate": 0.5, "eta": 0.3},
       "select_reserve": {"wall_s": 5.0, "x_unique": 64, "y_unique": 8},     # R5.1: declared bounded selection reserve (inside the totals)
       "rec": {"n_seeds": 8, "variants_per_action": 4, "depth": 3, "repair_expansions": 96, "temp_readouts": 256, "repairs_per_action": 2,
               "ylowx_extra": 1, "exhaustive_max_groups": 50000}}


class Budget:
    """R5.0: one absolute deadline (cfg['t_end'], perf_counter) shared by floor, proposal, scoring, composition and selection; else wall_s
    from now."""
    def __init__(self, cfg):
        self.t_end = cfg.get("t_end") or time.perf_counter() + cfg["wall_s"]

    def left(self):
        return self.t_end - time.perf_counter()

    def tick(self):
        if time.perf_counter() > self.t_end:
            raise TimeoutError("hard deadline")


def elem(sizes, k):
    e = [1] + [0] * k
    for s in sizes:
        for j in range(k, 0, -1):
            e[j] += e[j - 1] * s
    return e[k]


def long_energy(T, fz, row0, seq, part, F):
    """-> E, y_global for an ordered plan whose chunk sum F is known."""
    yg = fz.y_global(row0, [seq])[0]
    return F - math.log(max(CP.EPS, yg)), yg


def short_options(fz, row0, orders):
    """Single-chunk exact p11 at S0 for m <= 3 (each permitted order)."""
    if not orders:
        return []
    return [{"seq": o, "partition": [len(o)], "E": -math.log(max(CP.EPS, x["p11"])), "kind": "p11_single", "p11": x["p11"]}
            for o, x in zip(orders, fz.score(row0, orders))]


def cand_of(seq, part, E, **kw):
    return {"seq": [list(map(int, a)) for a in seq], "partition": list(part), "E": E, **kw}


def ckey(c):
    return (round(c["E"], 12), len(c["seq"]), len(c["partition"]), json.dumps(c["seq"]))


# ------------------------------------------------------------------------------------------------ Fig. 3B: global assignments
def ga(fz, row0, mode, cfg=None, log=None, sink=None):
    """mode: AUTO (EXACT when the declared envelope fits, else BOUNDED) | YONLY.  -> candidates, info.
    sink (R5.0): {'cands': [], 'info': {}} filled progressively so a budget stop keeps every COMPLETED size's incumbent."""
    cfg = {**CFG, **(cfg or {})}
    sink = sink if sink is not None else {"cands": [], "info": {}}
    H = cfg["H"][row0["domain"]]
    B = Budget(cfg)
    el = V.eligible(row0)
    D = {o: sorted(set(v)) for o, v in fz.proposals(row0, el).items() if v}
    D = {o: [d for d in v if V.legal_seq(row0, [[o, d]], H)] for o, v in D.items()}
    D = {o: v for o, v in D.items() if v}
    sizes = [len(v) for v in D.values()]
    ub = {k: elem(sizes, k) for k in range(1, H + 1)}
    est_x = CP.distinct_requests(ub)                 # R4.0: distinct (U, ordered chunk) readouts under set-keyed caching (the envelope quantity)
    theo = sum(ub[k] * CP.nx(k) for k in range(4, H + 1))  # R4.0: unshared DP lookups N_X(k) per long assignment (k <= 3 = one p11 per order)
    exact = mode != "YONLY" and all(v <= cfg["assign_per_size"] for v in ub.values()) and est_x <= cfg["exact_x_est"]
    info = {"mode": "EXACT" if exact else ("YONLY" if mode == "YONLY" else "BOUNDED"), "D4": {str(o): v for o, v in D.items()},
            "assign_upper_bound": ub, "est_distinct_x": est_x, "est_theoretical_dp_lookups": theo, "per_size": {}, "by_size": {}, "exhausted": False}
    sink["info"] = info
    T = CP.Scores(fz, row0, V.rebase, tick=B.tick)
    info["scores_ref"] = T
    pair_px = None
    cands, prev = sink["cands"], []
    for k in range(1, H + 1):
        B.tick()
        if k > len(D):
            break
        if ub[k] <= cfg["assign_per_size"]:
            pool = [tuple(sorted(A)) for A in CO.assignments(D, k)]
            gen = "enumerated"
        else:                                                           # declared beam extension of the retained size k-1 sets
            acts = sorted((o, d) for o, v in D.items() for d in v)
            pool = sorted({tuple(sorted(A + (a,))) for A in prev for a in acts if a[0] not in {x[0] for x in A} and a[1] not in {x[1] for x in A}})
            gen = "beam_extension"
        yg = dict(zip(pool, fz.y_global(row0, [list(map(list, A)) for A in pool]))) if pool else {}
        if exact:
            keep, why = pool, "exact"
        elif mode == "YONLY":
            keep = sorted(pool, key=lambda A: (-yg[A], A))[:cfg["yonly"]]; why = "yonly_top4"
            prev = sorted(pool, key=lambda A: (-yg[A], A))[:256]
        else:
            if pair_px is None:                                           # first ordered chunk proxy: every ordered pair / single of the pool at S0
                acts = sorted((o, d) for o, v in D.items() for d in v)
                req = [(frozenset(), (a,)) for a in acts] + [(frozenset(), (a, b)) for a in acts for b in acts if a[0] != b[0] and a[1] != b[1]]
                T.need(req); pair_px = True
            def xproxy(A):
                c = [T.cost((), (a, b)) for a in A for b in A if a != b] if len(A) >= 2 else [T.cost((), (A[0],))]
                return min(c)
            q = cfg["retain"]
            byY = sorted(pool, key=lambda A: (-yg[A], A))
            byX = sorted(pool, key=lambda A: (xproxy(A), A))
            keep = list(dict.fromkeys(byY[:q["y"]] + byX[:q["x"]]))
            seen = {tuple(sorted(o for o, _ in A)) for A in keep}
            for A in sorted(pool, key=lambda A: (hashlib.sha256(json.dumps(A).encode()).hexdigest())):
                if len(keep) >= q["y"] + q["x"] + q["div"]:
                    break
                s = tuple(sorted(o for o, _ in A))
                if s not in seen:
                    keep.append(A); seen.add(s)
            prev = keep; why = "bounded_union_y_x_div"
        if exact:
            prev = pool
        info["per_size"][k] = {"generated": len(pool), "generation": gen, "kept": len(keep), "retention": why}
        best_k = None
        for i in range(0, len(keep), 256):                               # streamed blocks: requests -> batched scores -> exact DP per assignment
            B.tick()
            blk = keep[i:i + 256]
            if k > 3:
                T.need({r for A in blk for r in CP.requests(A)})
            for A in blk:
                B.tick()                                                  # R5.1: deadline checked per assignment (bounded overrun: one model batch)
                if k <= 3:                                                # R4.0: K <= 3 keeps the exact joint p11 of one chunk (no marginal competitor)
                    for c in short_options(fz, row0, [list(map(list, o)) for o in itertools.permutations(A)]):
                        c.update(set=[list(a) for a in A], y_global=yg[A], n_chunks=1)
                        if best_k is None or ckey(c) < ckey(best_k):
                            best_k = c
                    continue
                T.dp_lookups += CP.nx(k)                                  # R4.0: theoretical DP reads (cost lookups) actually performed
                r = CP.grouped_dp(T, A)
                if r:
                    F, o, p = r
                    c = cand_of(o, p, F - math.log(max(CP.EPS, yg[A])), kind="ga_dp", y_global=yg[A], set=[list(a) for a in A], F=F, n_chunks=len(p))
                    if best_k is None or ckey(c) < ckey(best_k):
                        best_k = c
        if best_k:
            cands.append(best_k)                                         # only the per-size argmin can win the global argmin
            info["by_size"][k] = {"E": best_k["E"], "y_global": best_k.get("y_global"), "F": best_k.get("F"), "n_chunks": len(best_k["partition"])}
        info["per_size"][k]["dp_optimized"] = len(keep)
        if not exact:                                                    # evaluator-side coverage audit only (never read by the planner)
            info.setdefault("retained", {})[k] = [[list(a) for a in A] for A in keep]
    info["exhausted"] = bool(exact)                                     # reached only when every size was completed (timeouts raise before)
    info["scores"] = {**T.n, "dp_lookups": T.dp_lookups}
    info.pop("scores_ref", None)
    return cands, info


# ------------------------------------------------------------------------------------------------ Fig. 3A: recursive retargeting
def rec(fz, row0, arm, cfg=None, sink=None):
    cfg = {**CFG, **(cfg or {})}
    sink = sink if sink is not None else {"cands": [], "info": {}}
    H = cfg["H"][row0["domain"]]
    B = Budget(cfg)
    rc = {**cfg["rec"], "m_max": H, "wall_s": max(0.0, B.left()) * 0.6, "x_unique": cfg["x_unique"], "y_unique": cfg["y_unique"], "disp_tiebreak": False}
    ctx, pool, tree, stop = RC.discover(fz, row0, "F-FLAT" if arm == "FLAT-INSERT" else "R-FIG3", rc)
    fz.caps = {"x_unique": cfg["x_unique"], "y_unique": cfg["y_unique"]}
    T = CP.Scores(fz, row0, V.rebase, tick=B.tick)
    info = {"pool": len(pool), "stop": stop, "counters": dict(ctx.n), "tree": tree, "scores_ref": T}
    sink["info"] = info
    cands = sink["cands"]
    for kk, (P, E, sd) in sorted(pool.items()):
        B.tick()
        acts = [tuple(map(int, a)) for a in P]
        if len(P) <= 3:                                                  # R4.0: K <= 3 = exact joint p11 of one chunk only
            orders = [list(map(list, P))] if arm != "REC-REORDER" else [list(map(list, q)) for q in itertools.permutations(acts)]
            cands += [dict(c, seed=sd, n_inserted=len(P) - len(sd)) for c in short_options(fz, row0, orders)]
            continue
        if arm == "REC-REORDER":
            idx = {V.key(row0, a): a for a in acts}
            before = [(idx[x], idx[y]) for x, y, k in E if k in ("PREREQ", "LOCAL") and x in idx and y in idx]
            T.need(CP.requests(acts, before))
            r = CP.grouped_dp(T, acts, before=before)
        else:
            T.need(CP.fixed_requests(acts))
            r = CP.fixed_order_dp(T, acts)
        if r:
            F, o, p = r
            Eh, yg = long_energy(T, fz, row0, o, p, F)
            cands.append(cand_of(o, p, Eh, kind="rec_dp", y_global=yg, seed=sd, n_inserted=len(P) - len(sd), edges=sorted(map(list, E)), F=F, n_chunks=len(p)))
    info["scores"] = dict(T.n); info.pop("scores_ref", None)
    return cands, info


# ------------------------------------------------------------------------------------------------ selection
def select(fz, row0, cands, floor, rule):
    """Production NOOP gate, then argmin E over the arm's candidates + the production K <= 3 floor (re-scored under the arm's model)."""
    noop = fz.p_noop(row0)
    if noop >= rule["noop_gate"]:
        return None, "NOOP", noop
    pool = [c for c in cands if c and c["seq"]]
    if floor and floor.get("seq"):
        x = fz.score(row0, [floor["seq"]])[0]
        pool.append({"seq": floor["seq"], "partition": [len(floor["seq"])], "E": -math.log(max(CP.EPS, x["p11"])), "kind": "production_floor"})
    if not pool:
        return None, "ABSTAIN", noop
    tau = rule.get("S2_tau")
    if tau is not None:                                                   # R5.3 S2: reliability-threshold shortest (tau from local VAL only)
        for c in pool:
            if rule.get("S2_stat") == "E":                                # Addendum B: reliability = full energy (X chunks + terminal Y)
                c["rel"] = c["E"]
            elif c.get("F") is None or len(c["seq"]) <= 3:
                c["rel"] = -math.log(max(CP.EPS, fz.score(row0, [c["seq"]])[0]["px"]))
            else:
                c["rel"] = c["F"]
        ok = [c for c in pool if c["rel"] <= tau]
        if ok:
            return min(ok, key=lambda c: (len(c["seq"]),) + ckey(c)), "SELECTED_S2", noop
    return min(pool, key=ckey), "SELECTED", noop


def plan(fz, row0, arm, floor, cfg=None):
    """One sealed plan for (root, arm) under ONE deadline and ONE readout budget (R5.0 / R5.1 amendment).
    floor: a callable floor(deadline) -> {"seq", "counters"} run INSIDE the timed region (production K <= 3 reference; its wall and readouts are
    reported and included in the totals), or a precomputed dict (historical R4 callers; NOT in this plan's timing; flagged floor_external).
    Search (proposal, recursion, scoring, composition) runs under deadline t_end - reserve.wall_s and caps x/y_unique - reserve; the declared
    selection reserve (p_noop, floor re-scoring) is spent inside the TOTAL caps (never lifted).  Budget stop (TimeoutError / CapReached): every
    COMPLETED candidate is kept (GA: completed sizes only, mode *_TIMEOUT, exhausted = False; REC: candidates ranked so far).
    decision: REPAIR | NOOP | ABSTAIN (search finished or incumbents exist, none admissible) | TIMEOUT_NO_INCUMBENT (budget stop, nothing to select)
    | SELECTION_BUDGET_EXCEEDED (reserve insufficient: best completed candidate by E without re-scoring; never expected)."""
    cfg = {**CFG, **(cfg or {})}
    rs = cfg["select_reserve"]
    t0 = time.perf_counter()
    t_end = cfg.get("t_end") or t0 + cfg["wall_s"]
    caps = {"x_unique": cfg["x_unique"], "y_unique": cfg["y_unique"]}
    scfg = {**cfg, "t_end": t_end - rs["wall_s"], "x_unique": caps["x_unique"] - rs["x_unique"], "y_unique": caps["y_unique"] - rs["y_unique"]}
    fz.reset(); fz.caps = {"x_unique": scfg["x_unique"], "y_unique": scfg["y_unique"]}
    floor_wall, floor_ctr, floor_external = None, None, not callable(floor) and floor is not None
    if callable(floor):
        tf = time.perf_counter()
        floor = floor(scfg["t_end"])
        floor_wall = round(time.perf_counter() - tf, 3)
        floor_ctr = (floor or {}).pop("counters", None) if isinstance(floor, dict) else None
    stop, sink = None, {"cands": [], "info": {}}
    try:
        if time.perf_counter() >= scfg["t_end"]:
            raise TimeoutError("no search budget left after floor")
        if arm in ("GA", "GA-YONLY"):
            cands, info = ga(fz, row0, "YONLY" if arm == "GA-YONLY" else "AUTO", scfg, sink=sink)
        else:
            cands, info = rec(fz, row0, arm, scfg, sink=sink)
    except (TimeoutError, CapReached) as e:
        stop = f"{type(e).__name__}:{e}"
        cands, info = list(sink["cands"]), dict(sink["info"])
        T = info.pop("scores_ref", None)
        if T is not None:
            info["scores"] = {**T.n, "dp_lookups": getattr(T, "dp_lookups", 0)}
        if info.get("mode") in ("EXACT", "BOUNDED"):
            info["mode"] = info["mode"] + "_TIMEOUT"
        info["exhausted"] = False
    t_search = time.perf_counter()
    pre = dict(fz.c)
    fz.caps = dict(caps)                                                  # selection spends the declared reserve inside the TOTAL caps
    try:
        pick, why, noop = select(fz, row0, cands, floor, cfg["rule"])
    except CapReached:
        pool = [c for c in cands if c and c["seq"]]
        pick, why, noop = (min(pool, key=ckey) if pool else None), "SELECTION_BUDGET_EXCEEDED", None
    if str(fz.dev).startswith("cuda"):
        fz.torch.cuda.synchronize()
    t1 = time.perf_counter()
    H = cfg["H"][row0["domain"]]
    total = round(t1 - t0, 3)
    if why == "NOOP":
        dec = "NOOP"
    elif why == "SELECTION_BUDGET_EXCEEDED":
        dec = "SELECTION_BUDGET_EXCEEDED"
    elif pick:
        dec = "REPAIR"
    else:
        dec = "TIMEOUT_NO_INCUMBENT" if stop and not cands and not (floor and floor.get("seq")) else "ABSTAIN"
    out = {"root_id": row0["root_id"], "arm": arm if arm != "GA" else f"GA-{info.get('mode', 'NA')}", "decision": dec,
           "seq": pick["seq"] if pick else None, "partition": pick["partition"] if pick else None, "E": pick["E"] if pick else None,
           "kind": pick["kind"] if pick else None, "p_noop": noop, "n_candidates": len(cands), "long": bool(pick and len(pick["seq"]) > 3),
           "multi_chunk": bool(pick and max(pick["partition"]) >= 2), "H": H, "stop": stop, "budget_stop": bool(stop),
           "info": {k: v for k, v in info.items() if k != "tree"}, "tree": info.get("tree"), "counters": dict(fz.c),
           "selection_readouts": {k: fz.c[k] - pre.get(k, 0) for k in fz.c}, "floor_counters": floor_ctr, "floor_external": floor_external,
           "caps": caps, "reserve": rs, "wall_s": total, "floor_wall_s": floor_wall, "search_wall_s": round(t_search - t0 - (floor_wall or 0.0), 3),
           "select_wall_s": round(t1 - t_search, 3), "deadline_overrun_s": round(max(0.0, t1 - t_end), 3),
           "cap_overrun": {k: max(0, fz.c.get(k, 0) - caps[k]) for k in caps}, "incumbent_from_stop": bool(stop and pick)}
    out["arm_wall_s"] = round(total - (floor_wall or 0.0), 3)
    if pick and pick["kind"] == "production_floor":
        out["note"] = "unchanged K<=3 production floor selected (short selection, not a long repair)"
    return out


# ------------------------------------------------------------------------------------------------ P3 isolated assignment-given diagnostic
def assignment_given(fz, row0, A, witness=None, lam=0.0):
    """ORACLE_DIAGNOSTIC (never a deployment arm): the unordered assignment A is supplied (sorted, order hidden).  -> plans for
    SEL-DP (grouped DP, has_multi for |A| > 3), RANDOM (sha256('KGT3-P3|' + root) order + best admissible partition) and, when the
    evaluator passes the witness order, WITNESS (best admissible partition of that order)."""
    A = sorted(CP._t(A))
    rng = random.Random(hashlib.sha256(f"KGT3-P3|{row0['root_id']}".encode()).hexdigest())
    if len(A) <= 3:                                                      # R4.0: K <= 3 = one chunk scored by the exact joint p11
        ro = list(A); rng.shuffle(ro)
        ps = [list(map(list, o)) for o in itertools.permutations(A)]
        sc = {json.dumps(o): x["p11"] for o, x in zip(ps, fz.score(row0, ps))}
        mk = lambda o: {"order": [list(map(int, a)) for a in o], "partition": [len(o)], "F": None, "E": -math.log(max(CP.EPS, sc[json.dumps([list(map(int, a)) for a in o])])), "kind": "p11_single"}  # noqa: E731
        out = {"SEL-DP": mk(min(ps, key=lambda o: (-sc[json.dumps(o)], json.dumps(o)))), "RANDOM": mk(ro)}
        if witness is not None:
            out["WITNESS"] = mk(witness)
        return {**out, "y_global": fz.y_global(row0, [list(map(list, A))])[0], "scores": {"p11_orders": len(ps)}}
    T = CP.Scores(fz, row0, V.rebase)
    T.need(CP.requests(A))
    yg = fz.y_global(row0, [list(map(list, A))])[0]
    out = {}
    r = CP.grouped_dp(T, A, lam=lam)
    out["SEL-DP"] = {"order": r[1], "partition": r[2], "F": r[0]} if r else None
    ro = list(A); rng.shuffle(ro)
    r = CP.fixed_order_dp(T, ro, lam=lam)
    out["RANDOM"] = {"order": r[1], "partition": r[2], "F": r[0]} if r else None
    if witness is not None:
        r = CP.fixed_order_dp(T, [tuple(map(int, a)) for a in witness], lam=lam)
        out["WITNESS"] = {"order": r[1], "partition": r[2], "F": r[0]} if r else None
    for v in out.values():
        if v:
            v["E"] = v["F"] - math.log(max(CP.EPS, yg))
            v["chunk_px"] = []
            i = 0
            for g in v["partition"]:
                v["chunk_px"].append(math.exp(-T.cost(v["order"][:i], v["order"][i:i + g]))); i += g
    out["y_global"] = yg; out["scores"] = dict(T.n)
    return out
