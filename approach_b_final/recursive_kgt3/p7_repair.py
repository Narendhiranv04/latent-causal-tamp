#!/usr/bin/env python3
"""P7A — PUBLIC bounded candidate repair (reports/p7/P7A_PLAN.md is the frozen specification).  For a base endpoint (assignment A from the
sealed P4 pools) search over ordered plans that may (i) execute required moves with their own or adjusted destinations, (ii) insert
enabling moves of PUBLIC SUSPECTS (objects near pending sources/destinations, the target or the goal; 2 levels), (iii) drop required moves
(replacement at the 12-move cap), (iv) rebuild from a target-near core.  Inputs: public DEV scene, frozen cVAE proposals at S0, frozen
temporary-target y_hat (step score, soft), frozen endpoint y_hat.  Never reads kill tables, teacher rows, witnesses or certified K.
  step cost   -log max(eps, phi);  phi = sqrt(phi_G * phi_Y)  (mode P; ablations G / Y)
              phi_G = exp(-0.5 (occupied 8-neighbours of source + of destination))   HAND-DESIGNED public clearance heuristic
              phi_Y = frozen y_hat of temporary task (o -> d) in Edit(S0, plan), robot at q_ref    LEARNED (frozen) prediction
  shortlist   (amendment A1) per layer, children pre-ranked by free public geometry (parent cost - log phi_G(step) + h); top S = 32 get the
              counted step score phi; the rest are pruned (same rule for every arm)
  beam order  path cost + h,  h = sum over pending of -log phi_G(current cells)  (public, free; logged as geometry evals, not charged)
  final       path - log phi(T0 -> G0 | final) - log y_end(final assignment)        all scores are predictions/heuristics, never gates
    python p7_repair.py run ENDPOINTS.jsonl DEV_PUBLIC OUT.jsonl [--arms FULL,DEST_ONLY,...] [--device cuda]"""
import hashlib, json, math, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CFG = {"B": 8, "layers": 24, "cap": 12, "k_s": 6, "k_cvae": 4, "k_park": 4, "eps": 1e-4, "lam_d": 1.0, "PHI_MAX": 2000, "Y_MAX": 300, "keep": 5, "S": 32}
ARMS = {"FULL": dict(en=1, dr=1, de=1, rb=1), "DEST_ONLY": dict(en=0, dr=0, de=1, rb=0), "OBJSET_ONLY": dict(en=1, dr=1, de=0, rb=0),
        "FLAT": dict(flat=1), "RANDOM": dict(en=1, dr=1, de=1, rb=1, rnd=1), "FULL_phiG": dict(en=1, dr=1, de=1, rb=1, mode="G"),
        "FULL_phiY": dict(en=1, dr=1, de=1, rb=1, mode="Y"),
        "DIAG_NODROP": dict(en=1, dr=0, de=1, rb=1)}       # POST-HOC diagnostic (after the A2 gate); not a pre-registered arm, not eligible for P7B


def jl(p):
    return [json.loads(l) for l in open(p)]


def _seed(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:12], 16)


class Repair:
    """One arm on one endpoint.  phiY(plan, o, d) / yend(list of move lists) / cvae {obj: [dests]} are injected (frozen or mock)."""
    def __init__(s, row0, phiY, yend, cvae, arm, cfg=CFG, mode=None):
        inp = row0["inputs"]; s.row0, s.cfg, s.a = row0, cfg, {"mode": "P", **ARMS[arm]}; s.arm = arm
        if mode:
            s.a["mode"] = mode
        s.xy = {int(k): v for k, v in inp["cell_xy"].items()}; s.c0 = [int(c) for c in inp["cells0"]]
        s.T0, s.G0 = int(inp["tid"]), int(inp["goal_cell"]); s.S0 = set(s.c0); s.legal = set(int(c) for c in inp["legal_cells"])
        s.fixed = {i for i, a in enumerate(inp["attrs"]) if a[3]}; s.pitch = abs(s.xy[1][0] - s.xy[0][0])
        s.nb = {c: {x for x in s.xy if x != c and math.dist(s.xy[x], s.xy[c]) <= 1.5 * s.pitch + 1e-9} for c in s.xy}
        s.phiY, s.yend, s.cvae = phiY, yend, cvae
        s.used = {"phi": 0, "y": 0, "geo": 0}; s.cache, s.ycache = {}, {}; s.prop_objs, s.prop_dests = set(), set()

    # ------------------------------------------------------------------ public geometry
    def cells(s, plan):
        c = list(s.c0)
        for o, d in plan:
            c[o] = d
        return c

    def occ_nb(s, cells, cell, excl):
        return sum(1 for i, x in enumerate(cells) if i != excl and x in s.nb[cell])

    def phiG(s, cells, o, d):
        s.used["geo"] += 1
        return math.exp(-0.5 * (s.occ_nb(cells, cells[o], o) + s.occ_nb(cells, d, o)))

    def legal_dest(s, cells, d, reserved):
        return d in s.legal and d not in s.S0 and d != s.G0 and d not in cells and d not in reserved

    def anchors(s, cells, pend):
        return [cells[o] for o, _ in pend] + [d for _, d in pend] + [cells[s.T0], s.G0]

    def movable(s, used):
        return [i for i in range(len(s.c0)) if i != s.T0 and i not in s.fixed and i not in used]

    def suspects(s, cells, pend, used, key):
        mv = s.movable(used)
        if s.a.get("rnd"):
            return sorted(random.Random(_seed("RS", s.row0["root_id"], key)).sample(mv, min(s.cfg["k_s"], len(mv))))
        A = s.anchors(cells, pend)
        dist = lambda i, P: min(math.dist(s.xy[cells[i]], s.xy[p]) for p in P)  # noqa: E731
        L1 = [i for i in mv if cells[i] in set().union(*(s.nb[a] for a in A))]
        L2 = [i for i in mv if i not in L1 and L1 and cells[i] in set().union(*(s.nb[cells[j]] for j in L1))]
        out = sorted(L1, key=lambda i: (dist(i, A), i)) + sorted(L2, key=lambda i: (dist(i, [cells[j] for j in L1]), i))
        return out[:s.cfg["k_s"]]

    def parking(s, cells, e, A, reserved, key):
        free = [d for d in sorted(s.legal) if s.legal_dest(cells, d, reserved)]
        if s.a.get("rnd"):
            return sorted(random.Random(_seed("RP", s.row0["root_id"], key, e)).sample(free, min(s.cfg["k_cvae"] + s.cfg["k_park"], len(free))))
        cv = [d for d in s.cvae.get(e, [])[:s.cfg["k_cvae"]] if d in free]
        pk = sorted((d for d in free if d not in cv), key=lambda d: (s.occ_nb(cells, d, e), -min(math.dist(s.xy[d], s.xy[a]) for a in A), d))
        return cv + pk[:s.cfg["k_park"]]

    # ------------------------------------------------------------------ scores (counted)
    def phi(s, plan, cells, o, d):
        k = (frozenset(plan), o, d)
        if k not in s.cache:
            s.used["phi"] += 1
            g = s.phiG(cells, o, d) if s.a["mode"] in "PG" else 1.0
            y = s.phiY(plan, o, d) if s.a["mode"] in "PY" else 1.0
            s.cache[k] = math.sqrt(g * y) if s.a["mode"] == "P" else (g if s.a["mode"] == "G" else y)
        return s.cache[k]

    def ye(s, assigns):
        todo = [a for a in {frozenset(x) for x in assigns} if a not in s.ycache]
        if todo:
            s.used["y"] += len(todo)
            for a, v in zip(todo, s.yend([sorted(a) for a in todo])):
                s.ycache[a] = v
        return [s.ycache[frozenset(x)] for x in assigns]

    def nll(s, p):
        return -math.log(max(s.cfg["eps"], p))

    def ok(s):
        return s.used["phi"] < s.cfg["PHI_MAX"] and s.used["y"] < s.cfg["Y_MAX"]

    # ------------------------------------------------------------------ search
    def h(s, cells, pend):
        return sum(s.nll(s.phiG(cells, o, d)) for o, d in pend) if not s.a.get("flat") else s.nll(s.phiG(cells, s.T0, s.G0))

    def search(s, pend0):
        cfg, a = s.cfg, s.a
        start = ((), tuple(sorted(pend0)), ())
        beam, complete, stop = [(0.0, start)], {}, "BEAM_EMPTY"
        for layer in range(cfg["layers"]):
            nxt, pre_k = {}, {}
            for cost, (plan, pend, drop) in beam:
                cells = s.cells(plan); used = {o for o, _ in plan + pend + drop}; reserved = {d for _, d in pend}
                key = (tuple(sorted(plan)), pend, drop); A = s.anchors(cells, pend); ex = []
                if len(plan) < cfg["cap"]:
                    for o, d0 in pend:
                        ds = [d0] + (s.parking(cells, o, A, reserved - {d0}, key) if a.get("de") else [])
                        ex += [((o, d), (o, d0)) for d in dict.fromkeys(ds) if d == d0 or s.legal_dest(cells, d, reserved)]
                    if a.get("en") or a.get("flat"):
                        cand = s.movable(used) if a.get("flat") else s.suspects(cells, pend, used, key)
                        for e in cand:
                            s.prop_objs.add(e)
                            ex += [((e, p), None) for p in s.parking(cells, e, A, reserved, key)]
                if a.get("dr"):
                    ex += [(None, r) for r in pend]
                for mv, r in ex:                                   # free public pre-score (geometry only): child path proxy + h
                    if mv is None:
                        st = (plan, tuple(x for x in pend if x != r), tuple(sorted(drop + (r,)))); g = cost + cfg["lam_d"]
                    else:
                        s.prop_dests.add(mv[1]); g = cost + s.nll(s.phiG(cells, *mv))
                        st = (plan + (mv,), tuple(x for x in pend if x != r) if r else pend, drop)
                    k = (frozenset(st[0]), st[1], st[2]); pre = g + s.h(s.cells(st[0]), st[1])
                    if k not in pre_k or (pre, st) < pre_k[k][:2]:
                        pre_k[k] = (pre, st, cost, plan, cells, mv, r, pend)
            short = sorted(pre_k.values(), key=lambda t: (t[0], t[1]))[: cfg["S"]]      # amendment A1: shortlist gets the counted score
            for pre, st, cost, plan, cells, mv, r, pend in short:
                if not s.ok():
                    stop = "BUDGET"; break
                if mv is None:                                       # drop: replacement / redundancy, priced by frozen endpoint y_hat
                    full = list(plan) + list(pend); y0, y1 = s.ye([full, [x for x in full if x != r]])
                    c = cost + cfg["lam_d"] + max(0.0, math.log(max(cfg["eps"], y0)) - math.log(max(cfg["eps"], y1)))
                else:
                    c = cost + s.nll(s.phi(plan, cells, *mv))
                k = (frozenset(st[0]), st[1], st[2])
                if k not in nxt or (c, st) < (nxt[k][0], nxt[k][1]):
                    nxt[k] = (c, st)
            ranked = sorted(nxt.values(), key=lambda t: (t[0] + s.h(s.cells(t[1][0]), t[1][1]), t[1]))
            for c, st in ranked:
                if st[0] and (a.get("flat") or not st[1]):
                    complete[(frozenset(st[0]), st[2])] = min(complete.get((frozenset(st[0]), st[2]), (1e18, None)), (c, st))
            beam = [(c, st) for c, st in ranked if st[1] or a.get("flat")][:cfg["B"]]
            if stop == "BUDGET" or not beam:
                break
        else:
            stop = "LAYERS"
        return list(complete.values()), stop

    def final(s, cands):
        out = []
        for c, (plan, pend, drop) in sorted(cands, key=lambda t: (t[0] + s.h(s.cells(t[1][0]), t[1][1]), t[1]))[: 4 * s.cfg["keep"]]:
            cells = s.cells(plan)
            pf = s.phi(plan, cells, s.T0, s.G0) if s.used["phi"] < s.cfg["PHI_MAX"] + 4 * s.cfg["keep"] else None
            y = s.ye([list(plan)])[0] if s.used["y"] < s.cfg["Y_MAX"] + 4 * s.cfg["keep"] else None
            F = c + (s.nll(pf) if pf is not None else 0) + (s.nll(y) if y is not None else 0)
            out.append({"plan": [list(m) for m in plan], "dropped": [list(m) for m in drop], "path": c, "phi_final": pf, "y_end": y, "F": F})
        return sorted(out, key=lambda r: (r["F"], json.dumps(r["plan"])))[: s.cfg["keep"]]

    def run(s, A):
        A = [tuple(map(int, m)) for m in A]
        cands, stop = s.search(A if not s.a.get("flat") else [])
        rebuilt = False
        if not cands and s.a.get("rb") and s.ok():
            near = s.nb[s.c0[s.T0]] | s.nb[s.G0]
            core = [m for m in A if s.c0[m[0]] in near] or sorted(A, key=lambda m: min(math.dist(s.xy[s.c0[m[0]]], s.xy[x]) for x in (s.c0[s.T0], s.G0)))[:3]
            cands, stop = s.search(core); rebuilt = True
        top = s.final(cands)
        orig = {o: d for o, d in A}
        for t in top:
            t["added"] = [m for m in t["plan"] if m[0] not in orig]; t["dest_changed"] = [m for m in t["plan"] if m[0] in orig and orig[m[0]] != m[1]]
        cells0 = list(s.c0)
        return {"top": top, "stop": stop, "rebuilt": rebuilt, "used": dict(s.used), "n_complete": len(cands),
                "suspects_S0": s.suspects(cells0, A, set(o for o, _ in A), "S0") if not s.a.get("flat") else [],
                "proposed_objects": sorted(s.prop_objs), "proposed_dests": sorted(s.prop_dests)}


def frozen_fns(M, row0):
    import data as DA
    T0 = int(row0["inputs"]["tid"])
    phiY = lambda plan, o, d: M.ytask(DA.HypoRoot(row0, [list(m) for m in plan]) if o == T0 else DA.HypoRoot(row0, [list(m) for m in plan], task=(o, d)))  # noqa: E731
    yend = lambda seqs: M.y_end(row0, seqs)  # noqa: E731
    return phiY, yend, M.propose(DA.HypoRoot(row0))


def run(endpoints, dev_public, out, arms, device="cuda"):
    import models as MD
    import data as DA
    pub = {r["root_id"]: r for r in jl(dev_public)}; E = jl(endpoints); M = MD.Frozen(device)
    DA.install_guard([HERE, HERE.parent, Path(out).parent, Path(endpoints).parent, Path(dev_public).parent, Path(sys.executable).resolve().parents[1]])
    done = {(r["root_id"], r["endpoint_signature"]) for r in jl(out)} if Path(out).exists() else set()      # resumable per endpoint
    with open(out, "a") as f:
        for e in E:
            if (e["root_id"], e["endpoint_signature"]) in done:
                continue
            row0 = pub[e["root_id"]]; A = json.loads(e["endpoint_signature"]); phiY, yend, cvae = frozen_fns(M, row0)
            rec = {k: e[k] for k in e if k != "src_order"} | {"m": len(A), "arms": {}, "cvae_S0": {str(k): v for k, v in cvae.items()}}
            rec["arms"]["ORIG"] = {"top": [{"plan": e["src_order"], "dropped": [], "added": [], "dest_changed": [], "y_end": yend([e["src_order"]])[0]}],
                                   "used": {"phi": 0, "y": 1, "geo": 0}}
            for arm in arms:
                t0, c0 = time.time(), dict(M.c)
                r = Repair(row0, phiY, yend, cvae, arm).run(A)
                r["frozen_calls"] = {k: M.c.get(k, 0) - c0.get(k, 0) for k in M.c}; r["wall_s"] = round(time.time() - t0, 2)
                for t in r["top"]:
                    assert DA.check_sequence(row0, t["plan"]) is None and len(t["plan"]) <= CFG["cap"]
                rec["arms"][arm] = r
            f.write(json.dumps(rec) + "\n"); f.flush()
            for c in ("_sc", "_yend"):
                getattr(M, c).clear()
    print(json.dumps({"endpoints": len(E), "out": str(out)}))


if __name__ == "__main__":
    a = sys.argv[1:]
    arms = a[a.index("--arms") + 1].split(",") if "--arms" in a else [k for k in ARMS]
    dev = a[a.index("--device") + 1] if "--device" in a else "cuda"
    if a[0] == "run":
        run(a[1], a[2], a[3], arms, dev)
