#!/usr/bin/env python3
"""P7A-R — PUBLIC bounded repair search (specification: reports/p7ar/P7AR_PREREG.md, sections 2-5; constants below are the frozen values).
Directional access proxy (hand-designed heuristic): base-facing corridors CC(x,u), access a = max_u exp(-#objects in corridor);
potential Phi = sum of clipped -log access over pending moves + the target's pick/goal access.  Transitions EXEC / DEST / ENABLE / INSERT /
SUB (atomic replacement only at the 12-move cap, never cheaper than executing the replaced move); NO ordinary deletion.  Frozen models:
temporary-target y_hat as a within-parent percentile rank (FULL-R only), endpoint y_hat as a within-root percentile in the final score.
Never reads kill tables, teacher rows, witnesses, certified K or labels.
    python p7ar_repair.py run ENDPOINTS.jsonl ROOTS_PUBLIC.jsonl OUT.jsonl [--device cuda]"""
import hashlib, json, math, random, sys, time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CFG = {"B": 8, "layers": 24, "cap": 12, "k_e": 6, "q_park": 2, "q_ins": 6, "q_sub_e": 3, "q_sub_r": 2, "q_flat": 48, "Gamma": 4.0, "lam_e": 0.3,
       "lam_sub": 0.3, "w_TR": 1.0, "lam_Y": 0.5, "lam_end": 1.0, "len_corr": 2.0, "half_w": 0.75, "thetas": (-60, -30, 0, 30, 60),
       "MODEL_MAX": 6000, "YEND_MAX": 200, "GEO_MAX": 3_000_000, "keep": 5}
ARMS = {"DEST_ONLY": dict(dest=3), "FULL_R": dict(dest=1, en=1), "FULL_R_GEOM": dict(dest=1, en=1, geom=1),
        "FLAT_STRONG": dict(flat=1), "RANDOM_MATCHED": dict(dest=1, en=1, rnd=1)}


def jl(p):
    return [json.loads(l) for l in open(p)]


def _seed(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:12], 16)


class Geo:
    """Public geometry: corridor cell-sets CC[x] (one frozenset per base-facing direction), access, legality.  CC is injectable (tests)."""
    def __init__(s, row0, cfg=CFG, CC=None):
        inp = row0["inputs"]; s.cfg = cfg
        s.xy = {int(k): v for k, v in inp["cell_xy"].items()}; s.c0 = [int(c) for c in inp["cells0"]]
        s.T0, s.G0 = int(inp["tid"]), int(inp["goal_cell"]); s.S0 = set(s.c0); s.legal = set(int(c) for c in inp["legal_cells"])
        s.fixed = {i for i, a in enumerate(inp["attrs"]) if a[3]}; s.p = abs(s.xy[1][0] - s.xy[0][0]); s.n = 0
        s.CC = CC if CC is not None else {x: s._corridors(x, inp["base"]) for x in s.xy}

    def _corridors(s, x, base):
        X = s.xy[x]; v = (base[0] - X[0], base[1] - X[1]); L = math.hypot(*v) or 1.0; out = []
        for th in s.cfg["thetas"]:
            t = math.radians(th); u = ((v[0] * math.cos(t) - v[1] * math.sin(t)) / L, (v[0] * math.sin(t) + v[1] * math.cos(t)) / L)
            cs = frozenset(y for y, Y in s.xy.items() if y != x and 0 < (Y[0] - X[0]) * u[0] + (Y[1] - X[1]) * u[1] <= s.cfg["len_corr"] * s.p + 1e-9
                           and abs((Y[0] - X[0]) * u[1] - (Y[1] - X[1]) * u[0]) <= s.cfg["half_w"] * s.p + 1e-9)
            out.append(cs)
        return out

    def a(s, x, occ):
        s.n += 1
        return max(math.exp(-len(cc & occ)) for cc in s.CC[x]) if s.CC[x] else 1.0

    def term(s, v):
        return min(s.cfg["Gamma"], -math.log(max(v, 1e-12)))

    def acc(s, c, o, d):
        occ = set(c) - {c[o]}
        return s.a(c[o], occ) * s.a(d, occ)

    def accT(s, c, drop=None):
        occ = set(c) - {c[s.T0]} - ({c[drop]} if drop is not None else set())
        return s.a(c[s.T0], occ) * s.a(s.G0, occ)

    def phi(s, c, R, flat=False):
        return s.term(s.accT(c)) + (0.0 if flat else sum(s.term(s.acc(c, o, d)) for o, d in R))

    def legal_dest(s, c, d, reserved):
        return d in s.legal and d not in s.S0 and d != s.G0 and d not in c and d not in reserved


class Search:
    def __init__(s, row0, arm, phiY=None, cvae=None, cfg=CFG, geo=None):
        s.g, s.cfg, s.a, s.arm, s.row0 = geo or Geo(row0, cfg), cfg, ARMS[arm], arm, row0
        s.phiY, s.cvae = phiY, cvae or {}
        s.ycache, s.used, s.stop = {}, {"model": 0, "geo": 0, "expansions": 0, "layers": 0}, "BEAM_EMPTY"
        s.fun = {k: set() for k in ("suspect", "generated", "scored", "survivor", "complete")}; s.fun_n = defaultdict(int); s.sub_log = []

    def cells(s, plan):
        c = list(s.g.c0)
        for o, d in plan:
            c[o] = d
        return c

    def anchors(s, c, R):
        return [(c[o], {o}) for o, _ in R] + [(d, {o}) for o, d in R] + [(c[s.g.T0], {s.g.T0}), (s.g.G0, {s.g.T0})]

    def eligible(s, used):
        return [i for i in range(len(s.g.c0)) if i != s.g.T0 and i not in s.g.fixed and i not in used]

    def suspects(s, c, R, used, key):
        el = set(s.eligible(used))
        if s.a.get("rnd"):
            return sorted(random.Random(_seed("P7AR", "RANDOM", s.row0["root_id"], key, "S")).sample(sorted(el), min(s.cfg["k_e"], len(el))))
        where = {x: i for i, x in enumerate(c)}

        def hits(anch):
            cnt = defaultdict(int)
            for x, ex in anch:
                for cc in s.g.CC[x]:
                    for y in cc:
                        j = where.get(y)
                        if j is not None and j in el and j not in ex:
                            cnt[j] += 1
            return cnt
        L1 = hits(s.anchors(c, R)); L2 = hits([(c[j], {j}) for j in L1])
        out = sorted(L1, key=lambda j: (-L1[j], j)) + sorted((j for j in L2 if j not in L1), key=lambda j: (-L2[j], j))
        return out[: s.cfg["k_e"]]

    def places(s, c, e, R, reserved, key):
        free = [d for d in sorted(s.g.legal) if s.g.legal_dest(c, d, reserved)]
        if s.a.get("rnd"):
            return sorted(random.Random(_seed("P7AR", "RANDOM", s.row0["root_id"], key, e)).sample(free, min(4, len(free))))
        cv = [d for d in s.cvae.get(e, [])[:2] if d in free]
        sets = [cc for x, _ in s.anchors(c, R) for cc in s.g.CC[x]]
        A = [x for x, _ in s.anchors(c, R)]
        pk = sorted((d for d in free if d not in cv), key=lambda d: (sum(d in cc for cc in sets), -min(math.dist(s.g.xy[d], s.g.xy[x]) for x in A), d))
        return cv + pk[:2]

    def yt(s, plan, o, d):
        k = (frozenset(plan), o, d)
        if k not in s.ycache:
            s.used["model"] += 1; s.ycache[k] = s.phiY(plan, o, d)
        return s.ycache[k]

    def kids(s, plan, R):
        """All children of one parent under the frozen per-family quotas (no global shortlist).  -> list of dicts."""
        cfg, a, g = s.cfg, s.a, s.g
        c = s.cells(plan); used = {o for o, _ in plan} | {o for o, _ in R}; reserved = {d for _, d in R}
        key = (tuple(sorted(plan)), tuple(sorted(R))); out = []; n = len(plan) + len(R)
        if a.get("flat"):
            if len(plan) < s.m:
                cand = []
                for e in s.eligible(used):
                    for p in s.places(c, e, R, reserved, key):
                        c2 = list(c); c2[e] = p
                        cand.append((g.term(g.acc(c, e, p)) + g.phi(c2, (), True) - g.phi(c, (), True), e, p))
                for _, e, p in sorted(cand)[: cfg["q_flat"]]:
                    out.append({"fam": "FLAT", "mv": (e, p), "rem": None, "ins": None, "x": 0.0}); s.fun_n["generated"] += 1
            return out, c
        for o, d0 in sorted(R):
            out.append({"fam": "EXEC", "mv": (o, d0), "rem": (o, d0), "ins": None, "x": 0.0})
            alts = [p for p in s.places(c, o, R, reserved - {d0}, key) if p != d0 and g.legal_dest(c, p, reserved)][: a.get("dest", 0)]
            out += [{"fam": "DEST", "mv": (o, p), "rem": (o, d0), "ins": None, "x": 0.0} for p in alts]
        if a.get("en"):
            sus = s.suspects(c, R, used, key); s.fun["suspect"] |= set(sus)
            en = [(e, p) for e in sus for p in s.places(c, e, R, reserved, key)[: cfg["q_park"]]]
            s.fun["generated"] |= {e for e, _ in en}; s.fun_n["generated"] += len(en)
            if n + 1 <= cfg["cap"]:
                out += [{"fam": "ENABLE", "mv": m, "rem": None, "ins": None, "x": cfg["lam_e"]} for m in en]
                for e in sus[: cfg["q_ins"]]:
                    ps = s.places(c, e, R, reserved, key)
                    if ps:
                        out.append({"fam": "INSERT", "mv": None, "rem": None, "ins": (e, ps[0]), "x": cfg["lam_e"]})
            elif R:                                                 # atomic substitution at the cap
                gain = []
                for e, p in en:
                    c2 = list(c); c2[e] = p; gain.append((g.phi(c2, R) - g.phi(c, R), e, p))
                rs = sorted(R, key=lambda r: (g.term(g.accT(c)) - g.term(g.accT(c, drop=r[0])), r))[: cfg["q_sub_r"]]
                for _, e, p in sorted(gain)[: cfg["q_sub_e"]]:
                    for r in rs:
                        tr = g.term(g.accT(c)) - g.term(g.accT(c, drop=r[0]))
                        out.append({"fam": "SUB", "mv": (e, p), "rem": r, "ins": None, "TR": tr,
                                    "x": cfg["lam_e"] + g.term(g.acc(c, *r)) + cfg["lam_sub"] + cfg["w_TR"] * tr})
        return out, c

    def search(s, R0, m):
        cfg, g = s.cfg, s.g; s.m = m
        beam, complete = [(0.0, ((), frozenset() if s.a.get("flat") else frozenset(R0)))], {}
        for layer in range(cfg["layers"]):
            nxt = {}; s.used["layers"] = layer + 1
            for gc, (plan, R) in beam:
                K, c = s.kids(plan, R); s.used["expansions"] += len(K)
                mv = [k for k in K if k["mv"]]
                if not s.a.get("geom") and mv:
                    if s.used["model"] + len(mv) > cfg["MODEL_MAX"]:
                        s.stop = "BUDGET_MODEL"; break
                    ys = [s.yt(plan, *k["mv"]) for k in mv]; srt = sorted(ys)
                    for k, y in zip(mv, ys):                         # within-parent percentile, ties averaged, in (0, 1]
                        lo = srt.index(y); hi = len(srt) - srt[::-1].index(y); k["rho"] = (lo + hi + 1) / 2 / len(srt)
                for k in K:
                    if k["fam"] in ("ENABLE", "SUB", "INSERT", "FLAT"):
                        s.fun["scored"].add((k["mv"] or k["ins"])[0])
                    dg = k["x"] + (g.term(g.acc(c, *k["mv"])) + (0 if s.a.get("geom") else cfg["lam_Y"] * (1 - k.get("rho", 1.0))) if k["mv"] else 0.0)
                    p2 = plan + ((k["mv"],) if k["mv"] else ())
                    R2 = (R - {k["rem"]} if k["rem"] else R) | ({k["ins"]} if k["ins"] else frozenset())
                    st = (p2, frozenset(R2)); kk = (frozenset(p2), st[1])
                    if kk not in nxt or (gc + dg, repr(st)) < (nxt[kk][0], repr(nxt[kk][1])):
                        nxt[kk] = (gc + dg, st, k)
                if g.n > cfg["GEO_MAX"]:
                    s.stop = "BUDGET_GEO"; break
            ranked = sorted(nxt.values(), key=lambda t: (t[0] + g.phi(s.cells(t[1][0]), t[1][1], s.a.get("flat")), repr(t[1])))
            for gc, st, k in ranked:
                done = (len(st[0]) == m) if s.a.get("flat") else (not st[1] and st[0])
                if done:
                    complete[frozenset(st[0])] = min(complete.get(frozenset(st[0]), (1e18, None)), (gc, st), key=lambda t: (t[0], repr(t[1])))
                if k["fam"] == "SUB":
                    s.sub_log.append({"enabler": list(k["mv"]), "replaced": list(k["rem"]), "TR": round(k["TR"], 4)})
            beam = [(gc, st) for gc, st, k in ranked if not ((len(st[0]) == m) if s.a.get("flat") else (not st[1] and st[0]))][: cfg["B"]]
            anchor_objs = {o for o, _ in R0}
            for gc, (plan, R) in beam:
                s.fun["survivor"] |= {o for o, _ in plan if o not in anchor_objs} | {o for o, _ in R if o not in anchor_objs}
            if s.stop.startswith("BUDGET") or not beam:
                break
        else:
            s.stop = "LAYERS"
        s.used["geo"] = g.n
        out = []
        for gc, (plan, R) in sorted(complete.values(), key=lambda t: (t[0] + g.term(g.accT(s.cells(t[1][0]))), repr(t[1])))[: cfg["keep"]]:
            out.append({"plan": [list(x) for x in plan], "g": gc, "termT": g.term(g.accT(s.cells(plan)))})
        anchor_objs = {o for o, _ in R0}
        for t in sorted(complete.values(), key=lambda t: repr(t[1])):
            s.fun["complete"] |= {o for o, _ in t[1][0] if o not in anchor_objs}
        return out


def commit(cands, yend, cfg=CFG, learned=True):
    """Root-level one-shot commitment over pooled candidates: F = g + termT + lam_end (1 - rho_end) (rho_end = within-root percentile)."""
    if not cands:
        return None
    if learned:
        ys = yend([c["plan"] for c in cands]); srt = sorted(ys)
        for c, y in zip(cands, ys):
            lo = srt.index(y); hi = len(srt) - srt[::-1].index(y); c["y_end"] = y; c["rho_end"] = (lo + hi + 1) / 2 / len(srt)
    for c in cands:
        c["F"] = c["g"] + c["termT"] + (cfg["lam_end"] * (1 - c["rho_end"]) if learned else 0.0)
    return min(cands, key=lambda c: (c["F"], json.dumps(c["plan"])))


def run_root(row0, endpoints, phiY, yend, cvae, arms, cfg=CFG):
    """All arms on one root (1-2 public endpoints).  Returns per-arm committed plan, per-endpoint top-5, stats, funnel, SUB log."""
    out = {}
    for arm in arms:
        t0, pool, per = time.time(), [], []
        for e in endpoints:
            A = [tuple(map(int, m)) for m in json.loads(e["endpoint_signature"])]
            S = Search(row0, arm, phiY, cvae, cfg); top = S.search(A, len(A))
            for t in top:
                t["endpoint_signature"] = e["endpoint_signature"]; t["novel"] = [m for m in t["plan"] if m[0] not in {o for o, _ in A}]
            pool += top
            per.append({"endpoint_signature": e["endpoint_signature"], "top": top, "stop": S.stop, "used": S.used, "sub_log": S.sub_log[:50],
                        "funnel": {k: sorted(v) for k, v in S.fun.items()} | {"generated_actions": S.fun_n["generated"]}})
        com = commit([dict(t) for t in pool], yend, cfg, learned=not ARMS[arm].get("geom"))
        out[arm] = {"committed": com, "per_endpoint": per, "wall_s": round(time.time() - t0, 2)}
    return out


def run(endpoints, roots_public, out, device="cuda"):
    import models as MD
    import data as DA
    from p7_repair import frozen_fns
    pub = {r["root_id"]: r for r in jl(roots_public)}; E = defaultdict(list)
    for e in jl(endpoints):
        E[e["root_id"]].append(e)
    M = MD.Frozen(device)
    DA.install_guard([HERE, HERE.parent, Path(out).parent, Path(endpoints).parent, Path(roots_public).parent, Path(sys.executable).resolve().parents[1]])
    done = {json.loads(l)["root_id"] for l in open(out)} if Path(out).exists() else set()
    with open(out, "a") as f:
        for rid in sorted(E):
            if rid in done:
                continue
            row0 = pub[rid]; eps = sorted(E[rid], key=lambda e: e["rank_public"]); phiY, yend, cvae = frozen_fns(M, row0)
            c0 = dict(M.c); res = run_root(row0, eps, phiY, yend, cvae, list(ARMS))
            orig = eps[0]
            res["ORIG"] = {"committed": {"plan": orig["src_order"], "endpoint_signature": orig["endpoint_signature"], "novel": [],
                                         "y_end": yend([orig["src_order"]])[0]}, "per_endpoint": [], "wall_s": 0.0}
            for arm, v in res.items():
                if v["committed"]:
                    assert DA.check_sequence(row0, v["committed"]["plan"]) is None and len(v["committed"]["plan"]) <= CFG["cap"]
            f.write(json.dumps({"root_id": rid, "endpoints": [e["endpoint_signature"] for e in eps], "arms": res,
                                "frozen_calls": {k: M.c.get(k, 0) - c0.get(k, 0) for k in M.c},
                                "cvae_S0": {str(k): v for k, v in cvae.items()}}) + "\n"); f.flush()
            for c in ("_sc", "_yend"):
                getattr(M, c).clear()
    print(json.dumps({"roots": len(E), "out": str(out)}))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "run":
        run(a[1], a[2], a[3], a[a.index("--device") + 1] if "--device" in a else "cuda")
