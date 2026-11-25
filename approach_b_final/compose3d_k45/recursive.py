"""B4: bounded Fig. 3(a) recursive task retargeting + enabling-action insertion, then B3-style ranking (plan.md 5, B4).

Beam over global hypothetical prefixes.  For a prefix P: original-target local hypotheses u (<= 3 moves, top-4 requeried on S_P, ranked by
pX(u | S_P) * Y_global(P + u); low-Y partials kept).  For each pending action a = (A, d) of u, in order: retarget the EXACT pre-action scene
to the temporary task "pick A from its current cell, place it at d" (all objects encoded; original target, goal, pending objects and their
destinations reserved).  pY_temp = the frozen no-op probability of that retargeted root (a learned proxy, not proof).  If pY_temp < 0.5, or
a is the hypothesis' lowest-pY_temp action and pY_temp < 0.9, enabling repairs e (<= min(3, room)) are proposed ON THE TEMPORARY TASK
(top-4 requery, ranked by temporary p11); an enabling action that itself looks blocked is retargeted again (depth <= 2, cycle guard).
An insertion is kept if pY_temp after e >= 0.5, or improved by >= 0.10 (labelled RELAXED); the no-insertion sibling is always kept.
Inserted actions precede their parent (dependency edges).  Final ranking: every candidate over its dependency-respecting orders only;
m <= 3 -> frozen p11 at S0, m > 3 -> H over the declared two-group splits.  No teacher, no physical feedback."""
from __future__ import annotations

import itertools, json, math, time

import scene as SC
import compose as CP
from models import CapReached

T_LOW, T_LOWEST, T_GAIN = 0.5, 0.9, 0.10
PROBE_CAP, READ_CAP, DEPTH, KEEP_ENABLE, KEEP_VARIANTS = 32, 64, 2, 2, 4


class Ctx:
    def __init__(self, fz, row0, t_end):
        self.fz, self.row0, self.t_end = fz, row0, t_end
        self.n = {"temp_probes": 0, "temp_readouts": 0, "insert_attempts": 0, "insert_accepted": 0, "insert_relaxed": 0, "max_depth": 0, "cycle_blocked": 0}
        self.seen = set()

    def tick(self):
        if time.perf_counter() > self.t_end:
            raise TimeoutError("wall")

    def py_temp(self, seq, a, reserved):
        """Frozen no-op probability of the retargeted pre-action scene (temporary task A -> d)."""
        if self.n["temp_readouts"] >= READ_CAP:
            self.n["readout_cap_hit"] = self.n.get("readout_cap_hit", 0) + 1
            return None                                                     # cap: no retargeting decision (flat continuation)
        self.n["temp_readouts"] += 1
        return self.fz.p_noop(SC.rebase(self.row0, seq, task=a, reserved=reserved))


def enabling(cx, seq, a, pending, room):
    """Top enabling groups for temporary task a at the scene after `seq` (ranked by temporary p11; diverse by object set)."""
    if cx.n["temp_probes"] >= PROBE_CAP:
        cx.n["probe_cap_hit"] = cx.n.get("probe_cap_hit", 0) + 1
        return []
    cx.n["temp_probes"] += 1
    reserved = [d for _, d in pending]
    T = SC.rebase(cx.row0, seq, task=a, reserved=reserved)
    el = SC.eligible(cx.row0, used=[o for o, _ in seq], pending=[o for o, _ in pending], task_obj=a[0])
    D = cx.fz.proposals(T, el)
    gs = [[list(x) for x in p] for k in range(1, min(3, room) + 1) for A in CP.assignments(D, k) for p in itertools.permutations(A)]
    gs = [g for g in gs if SC.legal_seq(cx.row0, seq + g + pending, SC.MAX_LEN) and all(d != a[1] for _, d in g)]
    if not gs:
        return []
    sc = cx.fz.score(T, gs)
    order = sorted(zip(gs, sc), key=lambda t: (-t[1]["p11"], len(t[0]), json.dumps(t[0])))
    out, per = [], set()
    for g, x in order:
        s = tuple(sorted(o for o, _ in g))
        if s not in per:
            out.append((g, x["p11"])); per.add(s)
        if len(out) == KEEP_ENABLE:
            break
    return out


def insert(cx, seq, edges, a, pending, depth, lowest=False):
    """Variants (seq', edges', info) that end with action a placed after `seq`, with or without an inserted enabling group."""
    cx.tick()
    reserved = [d for _, d in pending]
    key = (json.dumps(seq), json.dumps(a), json.dumps(sorted(reserved)))
    if key in cx.seen:
        cx.n["cycle_blocked"] += 1
        return [(seq + [a], edges, {"action": a, "py_temp": None, "inserted": None, "cycle": True})], None
    cx.seen.add(key)
    py0 = cx.py_temp(seq, a, reserved)
    out = [(seq + [a], edges, {"action": a, "py_temp": py0, "inserted": None})]                 # the no-insertion sibling, always kept
    room = SC.MAX_LEN - len(seq) - 1 - len(pending)
    need = py0 is not None and (py0 < T_LOW or (lowest and py0 < T_LOWEST))
    if not need or room <= 0 or depth > DEPTH:
        return out, py0
    cx.n["max_depth"] = max(cx.n["max_depth"], depth)
    for g, p_e in enabling(cx, seq, a, pending, room):
        cx.n["insert_attempts"] += 1
        cur, ed = list(seq), list(edges)
        for b in g:                                                                        # nested retargeting of a blocked enabler
            vs, _ = insert(cx, cur, ed, b, [a] + pending, depth + 1)
            v = max(vs, key=lambda t: (t[2]["inserted"] is not None, -len(t[0])))
            cur, ed = v[0], v[1] + [(len(v[0]) - 1, "PARENT", a)]
        if len(cur) + 1 + len(pending) > SC.MAX_LEN:
            continue
        py1 = cx.py_temp(cur, a, reserved)
        if py1 is not None and (py1 >= T_LOW or py1 - py0 >= T_GAIN):
            cx.n["insert_accepted"] += 1; cx.n["insert_relaxed"] += py1 < T_LOW
            new_idx = list(range(len(seq), len(cur)))
            out.append((cur + [a], ed + [(i, "BEFORE", len(cur)) for i in new_idx],
                        {"action": a, "py_temp": py0, "py_temp_after": py1, "inserted": cur[len(seq):], "relaxed": py1 < T_LOW, "depth": depth, "p11_enable": p_e}))
    return out, py0


def b4(fz, row0, rule):
    t0 = time.perf_counter(); cx = Ctx(fz, row0, t0 + CP.BUDGET["wall_s"])
    pool, stop = {}, None
    frontier = [([], [], [])]
    try:
        while frontier:
            nxt = []
            for P, E, tr in frontier:
                room = SC.MAX_LEN - len(P)
                if room <= 0:
                    continue
                S, gs = CP.local_groups(fz, row0, P, min(3, room))
                gs = sorted(gs, key=lambda x: (-x["local"], json.dumps(x["g"])))
                hyps, per = [], {}
                for x in gs:                                                          # diverse local hypotheses (<= 2 per object set)
                    s = tuple(sorted(o for o, _ in x["g"]))
                    if per.get(s, 0) < 2:
                        hyps.append(x); per[s] = per.get(s, 0) + 1
                    if len(hyps) == CP.BUDGET["local_top"]:
                        break
                for h in hyps:
                    vars_ = [(list(P), list(E), list(tr))]
                    u = h["g"]
                    pre = [cx.py_temp(P + u[:i], a, [d for _, d in u[i + 1:]]) for i, a in enumerate(u)]   # plain-path pY_temp (lowest action)
                    known = [(p, i) for i, p in enumerate(pre) if p is not None]
                    low = min(known)[1] if known else None
                    for i, a in enumerate(u):
                        new = []
                        for seq, ed, t in vars_:
                            res, py0 = insert(cx, seq, ed, a, u[i + 1:], 1, lowest=(i == low))
                            new += [(s2, e2, t + [inf]) for s2, e2, inf in res]
                        vars_ = sorted({json.dumps(v[0]): v for v in new}.values(), key=lambda v: (-sum(1 for x in v[2] if x.get("inserted")), json.dumps(v[0])))[:KEEP_VARIANTS]
                    for seq, ed, t in vars_:
                        if not SC.legal_seq(row0, seq):
                            continue
                        k = json.dumps(seq)
                        if k not in pool:
                            pool[k] = {"seq": seq, "edges": ed, "trace": t}
                            if len(seq) < SC.MAX_LEN:
                                nxt.append((seq, ed, t))
            yk = fz.y_global(row0, [s for s, _, _ in nxt]) if nxt else []
            frontier = [v for v, _ in sorted(zip(nxt, yk), key=lambda z: (-z[1], json.dumps(z[0][0])))][:CP.BUDGET["beam"]]
    except (TimeoutError, CapReached) as e:
        stop = f"CAP:{type(e).__name__}:{e}"
    cands = [{"seq": [], "p": fz.score(row0, [[]])[0]["p11"], "kind": "noop"}]
    ranked = 0
    try:
        for k, c in sorted(pool.items()):
            orders = respecting(c["seq"], c["edges"])
            if len(c["seq"]) <= 3:
                sc = fz.score(row0, orders)
                j = max(range(len(orders)), key=lambda i: (sc[i]["p11"], json.dumps(orders[i])))
                cands.append({"seq": orders[j], "p": sc[j]["p11"], "kind": "p11", "partition": [len(orders[j])], "trace": c["trace"], "edges": c["edges"]})
            else:
                yg = fz.y_global(row0, [c["seq"]])[0]
                b = CP.best_composition(fz, row0, c["seq"], yg, orders=[[tuple(x) for x in o] for o in orders], t_end=cx.t_end + 60)
                if b:
                    cands.append({**b, "trace": c["trace"], "edges": c["edges"]})
            ranked += 1
    except (TimeoutError, CapReached) as e:
        stop = (stop or "") + f"|RANK_CAP:{type(e).__name__}"
    pick, why = CP.choose(row0, cands, rule)
    ins = [x for x in (pick or {}).get("trace", []) if x.get("inserted")]
    return CP.plan_out("B4", row0, pick, why, {"n_candidates": len(cands) - 1, "pool": len(pool), "ranked": ranked, "cap_stop": stop, "b4": dict(cx.n),
                                               "pick_insertions": ins, "pick_edges": (pick or {}).get("edges"),
                                               "pool_keys": sorted({json.dumps(sorted(map(list, c["seq"]))) for c in pool.values()})}, fz, t0)


def respecting(seq, edges):
    """All orders of seq's actions in which every inserted enabler precedes its parent (edges recorded at insertion time)."""
    acts = [tuple(a) for a in seq]
    before = set()
    for e in edges:
        if e[1] == "BEFORE":
            before.add((acts[e[0]], acts[e[2]]))
    out = []
    for p in itertools.permutations(acts):
        pos = {a: i for i, a in enumerate(p)}
        if all(pos[x] < pos[y] for x, y in before):
            out.append([list(a) for a in p])
    return out or [[list(a) for a in acts]]
