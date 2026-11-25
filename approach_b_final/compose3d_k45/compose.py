"""B0-B3 and the shared candidate / composition helpers (plan.md 5).  Planner-only: public rows + the frozen bundle.

B0  EXACT4 K<=3 (frozen p11, frozen selector)            B1  shared D4 pool + Y-shortlisted long sets, every order, direct p11 (OOD)
B2  greedy sequential groups <=3 on rebased scenes        B3  shared shortlist, every order x declared two-group split, chunk score H
H(r, pi) = log max(eps, Y_global(E)) + sum_j log max(eps, pX(c_j | S_{j-1}))   (ranking heuristic; m <= 3 keeps exact p11)."""
from __future__ import annotations

import itertools, json, math, time

import scene as SC
from models import CapReached

EPS = 1e-8
BUDGET = {"x_unique": 100_000, "y_unique": 100_000, "wall_s": 180.0, "L": 32, "per_set_first_pass": 2, "local_top": 6, "beam": 6}


def assignments(D, k):
    import construct as CO
    return list(CO.assignments({o: v for o, v in D.items() if v}, k))


def choose(row0, cands, rule):
    """Frozen selector semantics (search_sets.choose / xy.choose): cands[0] = no-op; gate on its p; admission p >= eta (no-op included);
    argmin (round(-log p, 12), m, displacement, signature).  Long candidates carry p = exp(H) (declared heuristic admission)."""
    noop = cands[0]
    if noop["p"] >= rule["noop_gate"]:
        return noop, "NOOP_GATE"
    pool = [c for c in cands if c["p"] >= rule["eta"]]
    if not pool:
        best = max(cands[1:], key=lambda c: c["p"], default=None)
        return None, f"ABSTAIN(best_p={best['p']:.3g})" if best else "ABSTAIN(empty)"
    key = lambda c: (round(-math.log(max(c["p"], 1e-12)), 12), len(c["seq"]), round(SC.displacement(row0, c["seq"]), 9), json.dumps(c["seq"]))  # noqa: E731
    return min(pool, key=key), "SELECTED"


def plan_out(arm, row0, pick, why, extra, fz, t0):
    seq = None if pick is None else pick["seq"]
    dec = "ABSTAIN" if pick is None else "NOOP" if not seq else "REPAIR"
    return {"root_id": row0["root_id"], "arm": arm, "decision": dec, "seq": seq if dec == "REPAIR" else None,
            "partition": pick.get("partition") if pick else None, "score": pick["p"] if pick else None, "score_kind": pick.get("kind") if pick else None,
            "stop": why, "counters": dict(fz.c), "wall_s": round(time.perf_counter() - t0, 4), **extra}


# ------------------------------------------------------------------------------------------------------------- short pool (B0)
def short_candidates(fz, row0, D, kmax=3):
    seqs = [[list(a) for a in p] for k in range(1, kmax + 1) for A in assignments(D, k) for p in itertools.permutations(A)]
    sc = fz.score(row0, [[]] + seqs)
    return [{"seq": [], "p": sc[0]["p11"], "kind": "noop"}] + [{"seq": s, "p": x["p11"], "kind": "p11", "partition": [len(s)]} for s, x in zip(seqs, sc[1:])]


def b0(fz, row0, rule):
    t0 = time.perf_counter()
    D = fz.proposals(row0, SC.eligible(row0))
    c = short_candidates(fz, row0, D)
    pick, why = choose(row0, c, rule)
    return plan_out("B0", row0, pick, why, {"n_candidates": len(c) - 1, "D4": {str(o): v for o, v in D.items()}}, fz, t0)


# ------------------------------------------------------------------------------------------------------------- shared long shortlist (B1 / B3)
def shared_shortlist(fz, row0, D):
    """Original-root D4 endpoints of length 4 and 5 (complete if they fit the endpoint cap, else a deterministic hash-stratified sample),
    ranked by Y_global; shortlist L per length with object-set diversity (<= 2 per object set first pass, then fill)."""
    import hashlib
    nat = {k: len(assignments(D, k)) for k in range(1, 6)}
    room = BUDGET["y_unique"] - fz.c["y_unique"]
    out, cov = {}, {}
    for k in (4, 5):
        A = assignments(D, k)
        quota = max(0, room // 2)
        if len(A) > quota:
            A = sorted(A, key=lambda a: hashlib.sha256(json.dumps(a).encode()).hexdigest())[:quota]
        cov[k] = {"natural": nat[k], "scored": len(A), "complete": len(A) == nat[k]}
        if not A:
            out[k] = []; continue
        y = fz.y_global(row0, A)
        order = sorted(zip(A, y), key=lambda t: (-t[1], json.dumps(t[0])))
        pick, per = [], {}
        for a, yy in order:
            s = tuple(sorted(o for o, _ in a))
            if per.get(s, 0) < BUDGET["per_set_first_pass"]:
                pick.append((a, yy)); per[s] = per.get(s, 0) + 1
            if len(pick) == BUDGET["L"]:
                break
        for a, yy in order:
            if len(pick) == BUDGET["L"]:
                break
            if (a, yy) not in pick:
                pick.append((a, yy))
        out[k] = pick
    return out, {"natural_endpoints": nat, "long_coverage": cov}


def b1(fz, row0, rule, D, short, sl):
    t0 = time.perf_counter()
    cands = list(short)
    for k in (4, 5):
        for a, _ in sl[k]:
            orders = [[list(x) for x in p] for p in itertools.permutations(a)]
            sc = fz.score(row0, orders)
            cands += [{"seq": s, "p": x["p11"], "kind": "p11_direct_long", "partition": [len(s)]} for s, x in zip(orders, sc)]
    pick, why = choose(row0, cands, rule)
    return plan_out("B1", row0, pick, why, {"n_candidates": len(cands) - 1}, fz, t0)


def chunk_score(fz, row0, seq, part, yg):
    """log H for one ordered sequence and partition (original task on every rebased prefix scene; inactive objects stay encoded)."""
    lh, prefix, px = math.log(max(EPS, yg)), [], []
    for g in SC.groups(seq, part):
        x = fz.score(SC.rebase(row0, prefix), [g])[0]["px"]
        px.append(x); lh += math.log(max(EPS, x)); prefix = prefix + g
    return lh, px


def best_composition(fz, row0, a, yg, orders=None, t_end=None):
    best = None
    for p in (orders if orders is not None else itertools.permutations(a)):
        seq = [list(x) for x in p]
        for part in SC.splits(len(seq)):
            if t_end and time.perf_counter() > t_end:
                raise TimeoutError
            lh, px = chunk_score(fz, row0, seq, part, yg)
            k = (lh, -len(part), json.dumps(seq), part)
            if best is None or k > best[0]:
                best = (k, {"seq": seq, "p": math.exp(lh), "logH": lh, "kind": "H", "partition": list(part), "px": px, "y_global": yg})
    return best[1] if best else None


def b3(fz, row0, rule, D, short, sl):
    t0 = time.perf_counter(); t_end = t0 + BUDGET["wall_s"]
    cands, stop = list(short), None
    try:
        for k in (4, 5):
            for a, yg in sl[k]:
                c = best_composition(fz, row0, a, yg, t_end=t_end)
                if c:
                    cands.append(c)
    except (TimeoutError, CapReached) as e:
        stop = f"CAP:{type(e).__name__}:{e}"
    pick, why = choose(row0, cands, rule)
    return plan_out("B3", row0, pick, why, {"n_candidates": len(cands) - 1, "cap_stop": stop}, fz, t0)


# ------------------------------------------------------------------------------------------------------------- B2 greedy sequential
def local_groups(fz, row0, prefix, maxk):
    S = SC.rebase(row0, prefix)
    D = fz.proposals(S, SC.eligible(row0, used=[o for o, _ in prefix]))
    gs = [[list(x) for x in p] for k in range(1, maxk + 1) for A in assignments(D, k) for p in itertools.permutations(A)]
    gs = [g for g in gs if SC.legal_seq(row0, prefix + g)]
    if not gs:
        return S, []
    px = fz.score(S, gs)
    yg = fz.y_global(row0, [prefix + g for g in gs])
    return S, [{"g": g, "px": x["px"], "p11_local": x["p11"], "y_global": y, "local": x["px"] * y} for g, x, y in zip(gs, px, yg)]


def b2(fz, row0, rule):
    t0 = time.perf_counter(); t_end = t0 + BUDGET["wall_s"]
    prefix, parts, trace, stop = [], [], [], None
    noop = fz.score(row0, [[]])[0]["p11"]
    cands = [{"seq": [], "p": noop, "kind": "noop"}]
    try:
        while len(prefix) < SC.MAX_LEN and len(parts) < 5 and time.perf_counter() < t_end:
            S, gs = local_groups(fz, row0, prefix, min(3, SC.MAX_LEN - len(prefix)))
            if not gs:
                stop = "NO_LOCAL_GROUP"; break
            best = max(gs, key=lambda x: (x["local"], -len(x["g"]), [-v for a in x["g"] for v in a]))
            prefix, parts = prefix + best["g"], parts + [len(best["g"])]
            trace.append({"group": best["g"], "px": best["px"], "y_global": best["y_global"], "n_local": len(gs)})
            seq = [list(x) for x in prefix]
            if len(seq) <= 3:
                cands.append({"seq": seq, "p": fz.score(row0, [seq])[0]["p11"], "kind": "p11", "partition": list(parts)})
            else:
                yg = fz.y_global(row0, [seq])[0]
                lh = math.log(max(EPS, yg)) + sum(math.log(max(EPS, t["px"])) for t in trace)
                cands.append({"seq": seq, "p": math.exp(lh), "logH": lh, "kind": "H_actual_partition", "partition": list(parts), "y_global": yg})
    except CapReached as e:
        stop = f"CAP:{e}"
    pick, why = choose(row0, cands, rule)
    return plan_out("B2", row0, pick, why, {"n_candidates": len(cands) - 1, "greedy_trace": trace, "cap_stop": stop or ("WALL" if time.perf_counter() >= t_end else None)}, fz, t0)
