"""Faithful Fig. 3(a) recursive retargeting (R-FIG3) and matched controls in ONE harness (plan §3, amendment R1a).

R-FIG3  seeds = diverse original-task ordered hypotheses (length 3 first when legal, then 2 and 1), ranked by frozen p11 at S0 (no eta).
        EVERY action a = (A, d) of every seed is retargeted on its exact hypothetical pre-action scene to the temporary task "pick A, place
        at d" (frozen task-conditioned cVAE + frozen coupled X/Y).  Local repairs = the empty repair (always kept) and the best ordered
        enabling groups of length 1..3 by temporary p11.  Each NEWLY INTRODUCED enabler is retargeted again (repeat on new actions; branch-
        local ancestor stack; depth cap).  Prerequisites are inserted immediately before their parent; edges are stable action keys:
        PREREQ (enabler -> parent), LOCAL (consecutive enablers of one group), SEED (consecutive seed actions).
R-GATED identical, but a non-empty repair is only proposed when pY_temp < 0.5 or (lowest action of the seed and pY_temp < 0.9) (legacy B4).
F-FLAT  identical seeds and budgets, no retargeting: original-task local groups (1..3, requeried top-4 on the rebased scene) are inserted at
        every position before a seed action (flat beam over original-task proposals).
R-TOPO  (ranking option) relaxes only SEED edges: every linear extension that keeps PREREQ + LOCAL edges.
Variant scores (beam bookkeeping only, never the final rank) are cumulative products: empty sibling = temporary no-op pY of the action as
is; repaired = temporary pY of the parent after the group x the enablers' own variant scores (an enabler's X-infeasibility is scored where
its own recursion resolves it, not twice).
Ranking: rank.best_partition (DP over 1-3 chunks, E_home with Y_global; single chunk m <= 3 = exact p11).  One hard deadline covers
proposal, recursion and ranking.  Variants are kept by local score plus object-set diversity (never by insertion count, R0 issue 6) and the
empty sibling is always kept; the candidate pool is not pruned by global Y (R0 issue 7)."""
from __future__ import annotations

import itertools, json, math, time

import construct as CO
import rank as RK
import views as V
from models import CapReached

CFG = {"m_max": {"2d": 6, "3d": 5}, "n_seeds": 8, "repairs_per_action": 2, "variants_per_action": 4, "depth": 3, "temp_readouts": 256,
       "repair_expansions": 96, "repair_expansions_per_seed": 24, "exhaustive_max_groups": 4096, "admit": "beats_empty", "wall_s": 180.0, "x_unique": 100_000,
       "y_unique": 100_000, "beam": 8}
# admit = "beats_empty": every action is retargeted (temporary readout + local proposals + scoring), and a NON-EMPTY local repair (ranked
#   by temporary p11) is admitted only if its frozen temporary pY (the parent's feasibility after the group) exceeds the temporary no-op
#   pY of the same view -- the model's own "does this group unblock the parent?" vs doing nothing; no fixed threshold.  The enabler's own
#   X-infeasibility is NOT used for admission: resolving it is the job of the recursion on that enabler.  admit = "all": the top repairs_per_action groups are always admitted (budget-hungry; diagnostic).


class Ctx:
    def __init__(self, fz, row0, arm, cfg=None):
        self.fz, self.row0, self.arm = fz, row0, arm
        self.cfg = {**CFG, **(cfg or {})}
        self.m_max = self.cfg["m_max"][row0["domain"]] if isinstance(self.cfg["m_max"], dict) else self.cfg["m_max"]
        self.t_end = time.perf_counter() + self.cfg["wall_s"]
        self.n = {"temp_readouts": 0, "repair_expansions": 0, "retargeted_actions": 0, "empty_kept": 0, "nonempty_repairs": 0, "cap_hits": {},
                  "no_room": 0, "cycle_rejects": 0, "max_depth": 0, "not_admitted": 0, "staged_calls": 0}
        self.seed_exp = 0
        self._yt, self.tree = {}, []
        fz.caps = {"x_unique": self.cfg["x_unique"], "y_unique": self.cfg["y_unique"]}

    def tick(self):
        if time.perf_counter() > self.t_end:
            raise TimeoutError("hard deadline")

    def cap(self, k):
        self.n["cap_hits"][k] = self.n["cap_hits"].get(k, 0) + 1

    def ytemp(self, T):
        """Counted unique temporary no-op readout (R0 issue 2: repeated (scene, task, reservations) is a cache hit, never re-counted)."""
        k = V.skey(T)
        if k not in self._yt:
            if self.n["temp_readouts"] >= self.cfg["temp_readouts"]:
                self.cap("temp_readouts"); return None
            self.n["temp_readouts"] += 1
            self._yt[k] = self.fz.p_noop(T)
        return self._yt[k]


def local_groups(ctx, T, P, protect, pending, room, task_dest=None, exhaustive=False):
    """Ordered groups of 1..min(3, room) from top-4 proposals on view T (its own task), legal globally with P + pending.
    Exhaustive when the ordered-group count is <= exhaustive_max_groups; otherwise a STAGED beam on view T (all singletons scored; pairs =
    both orders of top-`beam` singletons; triples = top-`beam` pairs extended by a top singleton at any of the 3 positions), counted in
    ctx.n['staged_calls'] (declared approximation; never silent)."""
    row0 = ctx.row0
    el = V.eligible(row0, used=[o for o, _ in P], pending=[o for o, _ in pending], protect=protect)
    D = {o: v for o, v in ctx.fz.proposals(T, el).items() if v}
    ok = lambda g: (task_dest is None or all(d != task_dest for _, d in g)) and V.legal_seq(row0, P + g + pending, ctx.m_max)  # noqa: E731
    out, big = [], False
    for k in range(1, min(3, room) + 1):
        for A in CO.assignments(D, k):
            for p in itertools.permutations(A):
                g = [list(x) for x in p]
                if ok(g):
                    out.append(g)
                    if not exhaustive and len(out) > ctx.cfg["exhaustive_max_groups"]:
                        big = True; break
            if big:
                break
        if big:
            break
    if not big:
        return out
    ctx.n["staged_calls"] += 1
    B = ctx.cfg["beam"]
    singles = [[[o, d]] for o, ds in sorted(D.items()) for d in ds if ok([[o, d]])]
    top = lambda gs: [g for g, _ in sorted(zip(gs, ctx.fz.score(T, gs)), key=lambda t: (-t[1]["p11"], json.dumps(t[0])))[:B]] if gs else []  # noqa: E731
    s1 = top(singles)
    out = list(singles)
    if room >= 2:
        pairs = [g for a in s1 for b in s1 for g in ([a[0], b[0]],) if a[0][0] != b[0][0] and a[0][1] != b[0][1] and ok(g)]
        out += pairs
        if room >= 3:
            tri = {json.dumps(g): g for pr in top(pairs) for a in s1 for i in range(3) for g in (pr[:i] + a + pr[i:],)
                   if a[0][0] not in {x[0] for x in pr} and a[0][1] not in {x[1] for x in pr} and ok(g)}
            out += list(tri.values())
    return out


def repairs(ctx, T, P, a, pending, protect, room, y0):
    """Best non-empty enabling groups for temporary task a on T, ranked by temporary p11 (diverse by object set); admission per CFG."""
    if ctx.n["repair_expansions"] >= ctx.cfg["repair_expansions"]:
        ctx.cap("repair_expansions"); return []
    if ctx.seed_exp >= ctx.cfg["repair_expansions_per_seed"]:
        ctx.cap("repair_expansions_per_seed"); return []
    ctx.n["repair_expansions"] += 1; ctx.seed_exp += 1
    gs = local_groups(ctx, T, P, protect, [a] + pending, room, task_dest=a[1])
    if not gs:
        return []
    sc = ctx.fz.score(T, gs)
    order = sorted(zip(gs, sc), key=lambda t: (-t[1]["p11"], len(t[0]), json.dumps(t[0])))
    out, seen = [], set()
    for g, x in order:
        if ctx.cfg["admit"] == "beats_empty" and ctx.arm != "R-GATED" and not x["py"] > y0:       # R-GATED keeps the legacy gate only
            ctx.n["not_admitted"] += 1
            continue
        s = tuple(sorted(o for o, _ in g))
        if s not in seen:
            out.append((g, x["p11"], x["py"])); seen.add(s)
        if len(out) == ctx.cfg["repairs_per_action"]:
            break
    extra = ctx.cfg.get("ylowx_extra", 0)            # KGT3 scaling option (default 0 = historical behaviour): admitted high-temporary-Y repairs
    if extra:                                        # that ranked low by temporary p11 (low X) are kept for recursive enabling
        for g, x in sorted(zip(gs, sc), key=lambda t: (-t[1]["py"], len(t[0]), json.dumps(t[0]))):
            s = tuple(sorted(o for o, _ in g))
            if extra and s not in seen and x["py"] > y0:
                out.append((g, x["p11"], x["py"])); seen.add(s); extra -= 1
                ctx.n["ylowx_extra"] = ctx.n.get("ylowx_extra", 0) + 1
    return out


def place(ctx, P, E, a, pending, depth, ancestors, node):
    """Variants (P', E', local score) that end with action a; prerequisites recursively inserted immediately before a."""
    ctx.tick()
    row0 = ctx.row0
    ka = V.key(row0, a)
    rec = {"action": ka, "depth": depth, "children": [], "y_temp": None, "repairs": []}
    node["children"].append(rec)
    if int(a[0]) in [int(o) for o, _ in ancestors]:
        ctx.n["cycle_rejects"] += 1; rec["why"] = "cycle"; return []
    T = V.rebase(row0, P, task=a, reserved=[d for _, d in pending] + [d for _, d in ancestors])
    yt = ctx.ytemp(T)
    rec["y_temp"] = yt
    ctx.n["retargeted_actions"] += 1
    ctx.n["max_depth"] = max(ctx.n["max_depth"], depth)
    out = [(P + [a], E, yt if yt is not None else 0.0)]
    ctx.n["empty_kept"] += 1
    room = ctx.m_max - len(P) - 1 - len(pending)
    gate = ctx.arm == "R-GATED" and not (yt is not None and (yt < 0.5 or (node.get("lowest") == ka and yt < 0.9)))
    if gate or yt is None or depth > ctx.cfg["depth"]:
        rec["why"] = "gated" if gate else ("readout_cap" if yt is None else "depth_cap")
        return out
    if room <= 0:
        ctx.n["no_room"] += 1; rec["why"] = "no_room"; return out
    protect = [o for o, _ in ancestors] + [a[0]]
    for g, pg, pyg in repairs(ctx, T, P, a, pending, protect, room, yt):
        ctx.n["nonempty_repairs"] += 1
        rr = {"group": [V.key(row0, e) for e in g], "p11_temp": pg, "py_temp": pyg, "children": []}
        rec["repairs"].append(rr)
        vs = [(list(P), set(E), 1.0)]
        for i, e in enumerate(g):
            nv = []
            for Pv, Ev, sv in vs:
                for P2, E2, _s in place(ctx, Pv, Ev, e, g[i + 1:] + [a] + pending, depth + 1, ancestors + [a], rr):
                    E3 = set(E2) | {(V.key(row0, e), ka, "PREREQ")} | ({(V.key(row0, g[i - 1]), V.key(row0, e), "LOCAL")} if i else set())
                    nv.append((P2, E3, sv * _s))
            vs = keep(ctx, nv)
        for Pv, Ev, sv in vs:
            if len(Pv) + 1 + len(pending) <= ctx.m_max and V.legal_seq(row0, Pv + [a] + pending, ctx.m_max):
                out.append((Pv + [a], Ev, pyg * sv))
    return keep(ctx, out, force_first=True)


def keep(ctx, vs, force_first=False):
    """Bounded variant list: optional forced first (empty sibling), then by local score with object-set diversity; never by insert count."""
    if not vs:
        return []
    head = [vs[0]] if force_first else []
    rest = sorted(vs[1:] if force_first else vs, key=lambda v: (-v[2], len(v[0]), json.dumps(v[0])))
    out, seen = list(head), {tuple(sorted(o for o, _ in head[0][0]))} if head else set()
    for v in rest:
        s = tuple(sorted(o for o, _ in v[0]))
        if s not in seen or len(out) < ctx.cfg["variants_per_action"] // 2:
            out.append(v); seen.add(s)
        if len(out) >= ctx.cfg["variants_per_action"]:
            break
    return out


def seeds(ctx):
    """Diverse original-task ordered hypotheses (length 3 first when legal, then 2, 1), frozen p11 at S0 (no eta gate).  The B0 (EXACT4)
    argmax is always added as a seed, so every long arm's pool contains B0's candidate and its single-chunk E = -log p11 (K <= 3 floor)."""
    row0 = ctx.row0
    gs = local_groups(ctx, row0, [], [], [], 3, exhaustive=True)     # S0 seeds: always the full EXACT4 set (B0's own candidates)
    sc = ctx.fz.score(row0, gs)
    out = []
    for L in (3, 2, 1):
        cand = sorted(((g, x["p11"]) for g, x in zip(gs, sc) if len(g) == L), key=lambda t: (-t[1], json.dumps(t[0])))
        seen = set()
        for g, p in cand:
            s = tuple(sorted(o for o, _ in g))
            if s in seen:
                continue
            out.append((g, p)); seen.add(s)
            if len([x for x in out if len(x[0]) == L]) >= (ctx.cfg["n_seeds"] // 2 if L == 3 else ctx.cfg["n_seeds"] // 4):
                break
    out = out[:ctx.cfg["n_seeds"]]
    if gs:
        b = min(zip(gs, sc), key=lambda t: (round(-math.log(max(t[1]["p11"], 1e-12)), 12), len(t[0]), round(V.displacement(row0, t[0]), 9), json.dumps(t[0])))
        if all(g != b[0] for g, _ in out):
            out.append((b[0], b[1]["p11"]))
    return out


def flat(ctx, seed):
    """F-FLAT: no retargeting; original-task local groups (requeried on the rebased scene) inserted before each seed action (beam)."""
    row0 = ctx.row0
    vs = [([], set(), 1.0)]
    for i, a in enumerate(seed):
        nv = []
        for P, E, s in vs:
            pending = seed[i + 1:]
            nv.append((P + [a], set(E), s))
            room = ctx.m_max - len(P) - 1 - len(pending)
            if room <= 0 or ctx.n["repair_expansions"] >= ctx.cfg["repair_expansions"]:
                continue
            ctx.n["repair_expansions"] += 1
            S = V.rebase(row0, P, reserved=[d for _, d in [a] + pending])
            gs = local_groups(ctx, S, P, [a[0]], [a] + pending, room)
            if not gs:
                continue
            px = ctx.fz.score(S, gs)
            for g, x in sorted(zip(gs, px), key=lambda t: (-t[1]["px"], json.dumps(t[0])))[:ctx.cfg["repairs_per_action"]]:
                if V.legal_seq(row0, P + g + [a] + pending, ctx.m_max):
                    nv.append((P + g + [a], set(E) | {(V.key(row0, e), V.key(row0, a), "FLAT_BEFORE") for e in g}, s * x["px"]))
        vs = keep(ctx, nv, force_first=True)
    return vs


def topo_orders(row0, seq, E, limit=24):
    """Linear extensions keeping PREREQ + LOCAL edges (SEED / FLAT edges relaxed); validated, cycle-free; composed order first."""
    keys = [V.key(row0, a) for a in seq]
    cons = {(x, y) for x, y, k in E if k in ("PREREQ", "LOCAL") and x in keys and y in keys}
    out = [seq]
    for p in itertools.permutations(range(len(seq))):
        if len(out) >= limit:
            break
        pos = {keys[j]: i for i, j in enumerate(p)}
        if all(pos[x] < pos[y] for x, y in cons):
            cand = [seq[j] for j in p]
            if cand != seq:
                out.append(cand)
    return out


def valid_dag(row0, seq, E):
    keys = [V.key(row0, a) for a in seq]
    pos = {k: i for i, k in enumerate(keys)}
    return all(pos[x] < pos[y] for x, y, k in E if x in pos and y in pos)


def discover(fz, row0, arm, cfg=None):
    """Seeds + retargeting / flat insertion -> (ctx, pool {json(seq): (seq, edges, seed)}, tree, stop).  No ranking (R2.4 reuses the pool)."""
    fz.reset()
    ctx = Ctx(fz, row0, "R-FIG3" if arm == "R-TOPO" else arm, cfg)
    root = {"action": "ROOT", "children": []}
    pool, stop = {}, None
    try:
        for g, p in seeds(ctx):
            ctx.tick()
            sn = {"seed": [V.key(row0, a) for a in g], "p11_seed": p, "children": []}
            ctx.seed_exp = 0
            root["children"].append(sn)
            if arm == "F-FLAT":
                vs = flat(ctx, g)
            else:
                lowest = None
                if arm == "R-GATED":
                    yl = [(ctx.ytemp(V.rebase(row0, g[:i], task=a, reserved=[d for _, d in g[i + 1:]])), V.key(row0, a)) for i, a in enumerate(g)]
                    yl = [t for t in yl if t[0] is not None]
                    lowest = min(yl)[1] if yl else None
                sn["lowest"] = lowest
                vs = [([], set(), 1.0)]
                for i, a in enumerate(g):
                    nv = []
                    for P, E, s in vs:
                        for P2, E2, s2 in place(ctx, P, E, a, g[i + 1:], 1, [], sn):
                            nv.append((P2, set(E2) | ({(V.key(row0, g[i - 1]), V.key(row0, a), "SEED")} if i else set()), s * s2))
                    vs = keep(ctx, nv, force_first=True)
            for P, E, _ in vs:
                if P and V.legal_seq(row0, P, ctx.m_max) and valid_dag(row0, P, E):
                    pool.setdefault(json.dumps(P), (P, E, sn["seed"]))
    except (TimeoutError, CapReached) as e:
        stop = f"{type(e).__name__}:{e}"
    return ctx, pool, root, stop


def plan(fz, row0, rule, arm, cfg=None):
    t0 = time.perf_counter()
    ctx, pool, root, stop = discover(fz, row0, arm, cfg)
    cands = []
    try:
        for kk, (P, E, sd) in sorted(pool.items()):
            ctx.tick()
            orders = topo_orders(row0, P, E) if arm == "R-TOPO" else [P]
            best = None
            for o in orders:
                Eh, part, px, yf = RK.best_partition(fz, row0, o)
                c = {"seq": o, "E": Eh, "partition": list(part), "px": px, "y_final": yf, "edges": sorted(map(list, E)), "seed": sd,
                     "n_inserted": len(o) - len([1 for x in o if V.key(row0, x) in [tuple(s) for s in sd]])}
                if best is None or (round(c["E"], 12), len(c["partition"])) < (round(best["E"], 12), len(best["partition"])):
                    best = c
            cands.append(best)
    except (TimeoutError, CapReached) as e:
        stop = (stop or "") + f"|RANK:{type(e).__name__}"
    pick, why, noop = RK.select(row0, cands, fz, rule)
    dec = "NOOP" if why == "NOOP_GATE" else ("REPAIR" if pick else "ABSTAIN")
    return {"root_id": row0["root_id"], "arm": arm, "decision": dec, "seq": pick["seq"] if pick else None, "partition": pick["partition"] if pick else None,
            "E": pick["E"] if pick else None, "edges": pick["edges"] if pick else None, "n_inserted": pick["n_inserted"] if pick else None,
            "p_noop": noop, "stop": why, "cap_stop": stop, "pool": len(pool), "counters": {**ctx.n, **fz.c}, "tree": root,
            "wall_s": round(time.perf_counter() - t0, 3), "m_max": ctx.m_max}
