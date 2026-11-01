"""BXY-P16 hard-scene development generator BXY_GEN_V21 (access closure), outcome-blind catalogue with prefix-complete query design,
bounded development waves, collection and data-readiness summary. Development namespace only; no confirmatory cohort is generated here.

Why V2 (P15) was easy: its blockers sat on ONE nominal target sweep, while the planar 3R side-grasp skill (skill.py) offers 24 approach
directions x 2 elbows for the pick and for the place; the teacher simply used another mode. V2.1 closes modes analytically.

Access-closure geometry (geometry only, never a teacher label): for a disc grasped at cell c, `pick_map(c)` lists the declared grasp
candidates that pass skill.screen_pick in the otherwise empty board and, for each, the cells whose disc kills it (grasp pose, 6 cm approach
line or closure collides, whole arm included). `place_map(g)` is the same for skill.screen_place of T at goal g. A screen over several discs
fails iff one disc fails it (union; re-checked on the populated scene by the real screen before a root is accepted). For a pick candidate i
and a place candidate j the movable discs in M_pick[i] u M_place[j] must all leave (a fixed disc there rules the pair out), and each must
itself be pickable when it leaves (`removal_order`: greedy over pick_map of its cell). K_geom = the fewest such removals over all (i, j) --
an ANALYTIC NECESSARY-CONDITION intent, not a verified K: transit / carry are planned by the teacher, which may still fail.
Mechanisms: open / near_closed (K0, few open modes and a harmful cell whose occupation closes them), pick, place, mixed, nested (an
intended remover is itself closed in S0: forced order), goal_occupant. Construction keeps P15's single target-only reference planner call
(the task is solvable on the empty board) and never plans a populated scene.
    python3 bxy_p16.py maps | generate <wave> | freeze <wave> | authorize <wave> | collect <wave> | worker <wave> <root> | summarize <wave>"""
from __future__ import annotations

import collections
import itertools
import json
import math
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

import bd_2d
import bd_core as bc
import bxy_data as bd
import bxy_f1 as F1
import bxy_p15 as P15
import bxy_pmin as PM
import bxy_teacher as T

OUT = Path("runs/approach_b/bxy_p16_v1")
GEN = "BXY_GEN_V21"
NS = {"dev": "bxyg21dev"}                                   # development only; a confirmatory namespace is never generated in P16
MECH = ("open", "near_closed", "pick", "place", "mixed", "nested", "goal_occupant")
MAX_CANDS, MAX_QUERIES = 16, 44
LIMITS = {"cpu_s": 24000.0, "root_cpu_s": 800.0, "workers": 4, "wall_s": 14400.0, "roots": 120, "min_allow": 30.0}
HARM_OPEN = 4                                               # near_closed: at most this many open pick (or place) candidates in S0


def _xy(c):
    return ((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08)


# ------------------------------------------------------------------ analytic access geometry (cached; CPU recorded)
def _scene(cells, q0=(math.pi / 2,) * 3, rid="geom"):
    """cells: [t0 cell, obstacle cells...] -> Scene with t0 first."""
    from scene import place_scene
    G = bd_2d.env()
    s = place_scene(G["cfg"], rid, "orig", [cells[0]], list(cells[1:]))
    return replace(s, robot=replace(s.robot, q_rad=tuple(q0)))


def screen(kind, s, oid="t0", dest=None) -> list:
    """Indices (into skill.directions) of declared candidates passing the analytic pick / place screen for object oid in scene s."""
    import motion as mo
    import skill as sk
    G = bd_2d.env()
    rob, p = G["robot"], sk.params(G["cfg"])
    o = s.get(oid)
    if kind == "pick":
        ck = mo.checkers(rob, s, oid, None, None, p["delta"], p["eps"])
        cs = sk.screen_pick(rob, ck, o.xy_m, o.radius_m, p)
    else:
        d, local = s.lattice.center(dest), (rob.grasp_x, 0.0)
        ck = mo.checkers(rob, s, oid, d, local, p["delta"], p["eps"])
        cs = sk.screen_place(rob, ck, d, local, 2 * o.radius_m, p)
    return [i for i, c in enumerate(cs) if c.stage == "OK"]


_MAPS = {}


def _maps_file():
    return OUT / "geometry" / "ACCESS_MAPS.json"


def _load_maps():
    if not _MAPS and _maps_file().exists():
        _MAPS.update(json.loads(_maps_file().read_text())["maps"])
    return _MAPS


def access_map(kind, c) -> dict:
    """{"open": [cand], "kill": {cand: [cells]}, "cpu_s"} for a disc picked at c (kind pick) or T placed at goal c (kind place)."""
    M, key = _load_maps(), f"{kind}:{c}"
    if key in M:
        return M[key]
    t0 = time.process_time()
    base = screen(kind, _scene([c]), dest=c if kind == "place" else None)
    kill = {i: [] for i in base}
    for x in range(64) if base else ():                                       # no open candidate: nothing to kill
        if x == c:
            continue
        ok = set(screen(kind, _scene([c, x]), dest=c if kind == "place" else None))
        for i in base:
            if i not in ok:
                kill[i].append(x)
    M[key] = {"open": base, "kill": {str(i): v for i, v in kill.items()}, "cpu_s": round(time.process_time() - t0, 3)}
    return M[key]


def _one_map(key):
    kind, c = key.split(":")
    return key, access_map(kind, int(c))


def precompute(workers=4) -> dict:
    """Every pick map (64 cells) and every place map (valid goal cells), 4 single-thread processes; CPU recorded per map."""
    import multiprocessing as mp
    _load_maps()
    keys = [k for k in [f"pick:{c}" for c in range(64)] + [f"place:{c}" for c in bd_2d.env()["valid"]] if k not in _MAPS]
    with mp.get_context("fork").Pool(workers) as pool:
        for k, v in pool.imap_unordered(_one_map, keys):
            _MAPS[k] = v
    save_maps()
    return {"maps": len(_MAPS), "cpu_s": round(sum(v["cpu_s"] for v in _MAPS.values()), 1)}


def save_maps():
    _maps_file().parent.mkdir(parents=True, exist_ok=True)
    G = bd_2d.env()
    _maps_file().write_text(json.dumps({"version": "BXY_P16_ACCESS_MAPS_V1", "config_hash": G["config_hash"], "skill": G["cfg"]["skill2d"],
                                        "maps": dict(sorted(_MAPS.items()))}, sort_keys=True))


def open_after(km, occ) -> list:
    occ = set(occ)
    return [int(i) for i, ks in km["kill"].items() if not occ.intersection(ks)]


def removal_order(movable, fixed, src, remove, park=None):
    """Greedy analytic order in which the discs `remove` can each be picked (pick_map of their cell open given every other disc: T at src,
    the fixed discs, movables not yet removed, and already removed discs at their parking cells if given). None if stuck."""
    left, done, cells = list(remove), [], dict(movable)
    while left:
        occ = lambda o: {src, *fixed, *(cells[p] for p in cells if p != o)}  # noqa: E731
        ok = [o for o in sorted(left, key=lambda o: (math.dist(_xy(cells[o]), _xy(src)) * -1, o)) if open_after(access_map("pick", cells[o]), occ(o))]
        if not ok:
            return None
        o = ok[0]
        done.append(o)
        left.remove(o)
        cells[o] = park[o] if park and o in park else -1 - len(done)          # removed disc: off the board unless its parking is known
        cells = {p: v for p, v in cells.items() if v >= 0}
    return done


def requirements(movable, fixed, src, goal):
    """[(cost, i, j, remove_set)] over finite (pick i, place j) options: movables in M_pick[i] u M_place[j] (+ a goal occupant)."""
    kp, kg = access_map("pick", src), access_map("place", goal)
    F, inv = set(fixed), collections.defaultdict(set)
    for o, c in movable.items():
        inv[c].add(o)
    occ_goal = {o for o, c in movable.items() if c == goal}
    if goal in F:
        return []
    out = []
    pj = {j: set(ks) for j, ks in kg["kill"].items() if not F.intersection(ks)}
    for i, ks in kp["kill"].items():
        if F.intersection(ks):
            continue
        for j, kj in pj.items():
            rem = {o for c in set(ks) | kj for o in inv.get(c, ())} | occ_goal
            out.append((len(rem), int(i), int(j), frozenset(rem)))
    return sorted(out, key=lambda r: (r[0], r[1], r[2], sorted(r[3])))


def k_geom(movable, fixed, src, goal):
    """(K_geom, best options [(i, j, remove, order)], forced) -- the fewest analytic removals with a feasible greedy removal order."""
    best, seen = None, set()
    for cost, i, j, rem in requirements(movable, fixed, src, goal):
        if best is not None and cost > best[0]:
            break
        if rem in seen:
            continue
        seen.add(rem)
        order = removal_order(movable, fixed, src, rem)
        if order is None:
            continue
        if best is None:
            best = (cost, [])
        best[1].append((i, j, rem, order))
    if best is None:
        return None, [], False
    occ = {src, *fixed, *movable.values()}
    forced = any(not open_after(access_map("pick", movable[o]), occ - {movable[o]}) for _, _, rem, _ in best[1] for o in rem)
    return best[0], best[1], forced


# ------------------------------------------------------------------ construction (deterministic from (namespace, wave, slot))
def ids(wave, slot, spec) -> dict:
    seed = int(bc.sha([GEN, NS["dev"], wave, slot])[:8], 16)
    G = bd_2d.env()
    return {"root_id": f"2d-{NS['dev']}-{wave}-s{slot:03d}", "parent_family_id": "fam21-" + bc.sha([GEN, wave, slot, spec])[:10],
            "construction_seed": seed, "variant_id": "orig", "generator_version": GEN, "namespace": "dev", "wave": wave,
            "config_hash": G["config_hash"], "teacher_version": bd_2d.TEACHER_VERSION, "robot_protocol": G["protocol"], "label_protocol": bc.LABEL_PROTOCOL}


def _close(rng, km, occupied, excl, K, fixed, movable, pf, max_fixed):
    """Greedy: raise the movable coverage of every finite candidate of km to >= K (a fixed disc makes a candidate infinite)."""
    while True:
        F, B = set(fixed), set(movable)
        cov = {i: (math.inf if F.intersection(ks) else len(B.intersection(ks))) for i, ks in km["kill"].items()}
        fin = [i for i, v in cov.items() if v < math.inf]
        if not fin:
            return False
        lo = min(cov[i] for i in fin)
        if lo >= K:
            return True
        i = sorted((i for i in fin if cov[i] == lo), key=lambda i: int(i))[int(rng.integers(0, sum(cov[i] == lo for i in fin)))]
        opts = sorted(set(km["kill"][i]) - set(occupied) - set(excl) - F - B)
        if not opts:
            return False
        c = int(rng.choice(opts))
        if lo == 0 and len(fixed) < max_fixed and len(fin) > 1 and rng.random() < pf:
            fixed.append(c)
        else:
            movable.append(c)


def construct(spec, idd, store_out=None, tries=400) -> dict:
    """One root (BD_GEN_V1 / P15 record schema, so the unchanged teacher and F1 apply). Raises bd_2d.Reject(reason)."""
    import p14_sweep_index as sx
    import p6_scenes as p6
    from scene import place_scene, scene_to_dict
    G = bd_2d.env()
    cfg, robot, rid = G["cfg"], G["robot"], idd["root_id"]
    rng = np.random.default_rng(idd["construction_seed"])
    t0 = time.process_time()
    K, mech = spec["K_intent"], spec["mechanism"]
    lo, hi = bd_2d.DISP[spec["displacement"]]
    for attempt in range(8):                                                    # task draws (src, goal, q0) with an open empty-board task
        src = int(rng.choice([x for x in G["region"][spec["source"]] if any(lo <= bd_2d.cheb(c, x) <= hi for c in G["valid"])]))
        goal = int(rng.choice([c for c in G["valid"] if lo <= bd_2d.cheb(c, src) <= hi]))
        stratum = "S0" if spec["start_pose"] == "home" else str(rng.choice(["S1", "S2", "S3"]))
        q0 = tuple(p6.STRATA[stratum])
        if access_map("pick", src)["open"] and access_map("place", goal)["open"]:
            break
    else:
        raise bd_2d.Reject("NO_OPEN_EMPTY_BOARD_TASK")
    excl = {src, goal} | P15.footprint(q0)
    kp, kg = access_map("pick", src), access_map("place", goal)
    plan = None
    for t in range(tries):
        fixed, mov = [], []
        if mech in ("pick", "nested", "mixed"):
            ok = _close(rng, kp, [], excl, K if mech != "mixed" else max(1, K // 2), fixed, mov, 0.35, 3)
        elif mech == "place":
            ok = _close(rng, kg, [], excl, K, fixed, mov, 0.35, 3)
        elif mech == "goal_occupant":
            mov.append(goal)
            ok = K == 1 or _close(rng, kp, [goal], excl, K - 1, fixed, mov, 0.35, 3)
        else:
            ok = True
        if ok and mech == "mixed":
            ok = _close(rng, kg, fixed + mov, excl, K - max(1, K // 2), fixed, mov, 0.35, 3)
        if not ok:
            continue
        if mech in ("open", "near_closed"):                                      # K0: a partial ring that leaves few open modes
            kind = "pick" if rng.random() < 0.6 else "place"
            km = kp if kind == "pick" else kg
            pool = sorted({x for ks in km["kill"].values() for x in ks} - excl)
            n = int(rng.integers(2, 5)) if mech == "near_closed" else int(rng.integers(0, 3))
            for c in rng.permutation(pool):
                if len(mov) >= n:
                    break
                trial = mov + [int(c)]
                if open_after(km, {*trial, *fixed}):
                    mov.append(int(c))
        movable = {f"b{i}": c for i, c in enumerate(mov)}
        kk, opts, forced = k_geom(movable, fixed, src, goal)
        if kk is None or kk != K or (mech == "nested" and not forced) or len(mov) > bc.MAX_MOVABLE:
            continue
        harm = harmful_cells(movable, fixed, src, goal, excl)
        if mech == "near_closed" and not harm:
            continue
        plan = (fixed, movable, opts, forced, harm, t)
        break
    if plan is None:
        raise bd_2d.Reject(f"NO_ANALYTIC_LAYOUT:{mech}:K{K}")
    fixed, movable, opts, forced, harm, t_used = plan
    empty = place_scene(cfg, rid, "empty", [src], [])
    empty = replace(empty, robot=replace(empty.robot, q_rad=q0))
    st, a, _ = bd_2d.t_goal({"scene": scene_to_dict(empty), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": rid + ":ref"}, {}, {"t0": src},
                            np.asarray(q0, float))
    if st != "VERIFIED":
        raise bd_2d.Reject(f"T_NOT_VERIFIED_IN_TARGET_ONLY_SCENE:{st}")
    sw = sx.swept_cells(robot, cfg, a)
    occ = {src, goal, *fixed, *movable.values()}
    lo_d, hi_d = bc.N_DISTRACT[spec["distractors"]]
    nd = min(int(rng.integers(lo_d, hi_d + 1)), bc.MAX_MOVABLE - len(movable))
    need = {c for _, _, rem, _ in opts for o in rem for c in [movable[o]]}
    kill_best = {x for i, j, _, _ in opts for x in kp["kill"][str(i)] + kg["kill"][str(j)]}
    neutral = sorted(c for c in range(64) if c not in occ and c not in excl and c not in kill_best)
    dis = [int(x) for x in rng.choice(neutral, min(nd, len(neutral)), replace=False)] if nd and neutral else []
    if mech in ("open", "near_closed") and not dis and neutral:
        dis = [int(rng.choice(neutral))]                                          # a movable distractor that can make the harmful edit
    cells = list(movable.values()) + dis + fixed
    s = place_scene(cfg, rid, "orig", [src], cells)
    s = replace(s, robot=replace(s.robot, q_rad=q0))
    allids = [o.id for o in s.objects if o.id != "t0"]
    nb, ndis = len(movable), len(dis)
    name = dict(zip(movable, allids[:nb]))
    mov_ids, fixed_ids = allids[:nb + ndis], allids[nb + ndis:]
    c0 = {o.id: o.cell for o in s.objects}
    # real screens on the populated scene (the union model must hold)
    sp, sg = screen("pick", s), screen("place", s, dest=goal)
    if mech in ("pick", "nested", "mixed", "goal_occupant") and sp and mech != "goal_occupant":
        raise bd_2d.Reject("UNION_MISMATCH:pick_open_in_S0")
    if mech in ("place", "mixed") and sg:
        raise bd_2d.Reject("UNION_MISMATCH:place_open_in_S0")
    if mech in ("open", "near_closed") and not (sp and sg):
        raise bd_2d.Reject("UNION_MISMATCH:K0_closed_in_S0")
    roles = {i: ("intended_blocker" if i in name.values() and c0[i] in need else "nonintended_ring" if i in name.values() else "distractor")
             for i in mov_ids}
    best = [{"pick": i, "place": j, "remove": sorted(name[o] for o in rem), "order": [name[o] for o in order]} for i, j, rem, order in opts]
    return {"ids": idd, "domain": bd_2d.DOMAIN, "generator": GEN, "spec": spec, "scene": scene_to_dict(s), "goal_cell": goal, "start_stratum": stratum,
            "q0": list(q0), "q_ref": list(q0), "roles": roles, "fixed_ids": fixed_ids, "intended_blockers": sorted({o for b in best for o in b["remove"]}),
            "construction": {"K_geom": K, "forced_order": forced, "options": best, "harmful_cells": harm, "neutral_cells": neutral,
                             "S0_open": {"pick": len(sp), "place": len(sg)}, "layout_draw": t_used, "q_ref_footprint": sorted(P15.footprint(q0)),
                             "reference_sweep": {k: sorted(v) for k, v in sw.items()}, "reference_planner_calls": 1,
                             "construction_cpu_s": round(time.process_time() - t0, 3),
                             "reference_witness": T.wid({k: np.asarray(v) for k, v in a.items()}, store_out)},
            "budget": {"per_query": bd_2d.QB}}


def harmful_cells(movable, fixed, src, goal, excl) -> list:
    """Free cells whose single occupation closes every open pick or every open place candidate of T (analytic)."""
    occ = {src, *fixed, *movable.values()}
    out = []
    for kind, c in (("pick", src), ("place", goal)):
        km = access_map(kind, c)
        op = open_after(km, occ)
        if not op or len(op) > HARM_OPEN * 2:
            continue
        common = set.intersection(*(set(km["kill"][str(i)]) for i in op))
        out += [{"cell": x, "closes": kind} for x in sorted(common - occ - set(excl))]
    return out



# ------------------------------------------------------------------ outcome-blind catalogue and prefix-complete query design
def _ideal_scene(rec, cells):
    from scene import scene_from_dict
    s0 = scene_from_dict(rec["scene"])
    objs = tuple(replace(o, cell=cells[o.id], xy_m=s0.lattice.center(cells[o.id])) for o in s0.objects)
    return replace(s0, objects=objs)


def parking(rec, o, cells, avoid, n=2) -> list:
    """Up to n free cells for object o, nearest first, off every avoided cell / q_ref footprint / T source and goal, whose analytic place
    screen for o is open in the ideal scene `cells` (geometry only)."""
    c0, src, goal = cells[o], bd.cells0(rec)["t0"], rec["goal_cell"]
    bad = set(avoid) | set(rec["construction"]["q_ref_footprint"]) | {src, goal} | set(cells.values())
    out = []
    for d in sorted((d for d in range(64) if d not in bad), key=lambda d: (math.dist(_xy(d), _xy(c0)), d)):
        if screen("place", _ideal_scene(rec, cells), oid=o, dest=d):
            out.append(d)
            if len(out) >= n:
                break
    return out


def candidates(rec) -> list:
    """[(seq, kind)] in fixed priority order; deterministic from geometry and construction intent; no teacher outcome is read."""
    c0, C = bd.cells0(rec), rec["construction"]
    src, goal = c0["t0"], rec["goal_cell"]
    kp, kg = access_map("pick", src), access_map("place", goal)
    mov = sorted(rec["roles"])
    dis = [o for o in mov if rec["roles"][o] == "distractor"]
    out = []
    add = lambda seq, kind: out.append(([(o, int(d)) for o, d in seq], kind)) if seq and all(d is not None for _, d in seq) else None  # noqa: E731
    neutral = [d for d in C["neutral_cells"] if d not in c0.values()]
    if C["options"] and C["options"][0]["order"]:                               # K_geom >= 1: an intended repair exists
        opt = C["options"][0]
        avoid = set(kp["kill"][str(opt["pick"])]) | set(kg["kill"][str(opt["place"])])
        cells, park = dict(c0), {}
        for o in opt["order"]:                                                    # sequential parking in the intended order
            ps = parking(rec, o, cells, avoid, 1)
            park[o] = ps[0] if ps else None
            if park[o] is not None:
                cells[o] = park[o]
        ordr = [(o, park[o]) for o in opt["order"]]
        m = len(ordr)
        add(ordr, "repair")
        if m >= 2:
            add(ordr[::-1], "repair_reversed")
        for t in range(1, m):
            add(ordr[:t], f"prefix_{t}")
        for t in range(m - 1 if m >= 2 else 0):                                  # omission of the last action = prefix m-1 (shared)
            add([a for i, a in enumerate(ordr) if i != t], f"omission_{t}")
        if m >= 3:
            add([ordr[1], ordr[0]] + ordr[2:], "repair_swap12")
        wrong = sorted((d for d in avoid if d not in c0.values() and d not in (src, goal) and d not in park.values()
                        and d not in C["q_ref_footprint"]), key=lambda d: (math.dist(_xy(d), _xy(c0[ordr[-1][0]])), d))
        if wrong:
            add(ordr[:-1] + [(ordr[-1][0], wrong[0])], "repair_wrong_destination")
        alt = next((b for b in C["options"][1:] if set(b["remove"]) != set(opt["remove"])), None)
        if alt:
            cells2, alt_seq = dict(c0), []
            av2 = set(kp["kill"][str(alt["pick"])]) | set(kg["kill"][str(alt["place"])])
            for o in alt["order"]:
                ps = parking(rec, o, cells2, av2, 1)
                alt_seq.append((o, ps[0] if ps else None))
                if ps:
                    cells2[o] = ps[0]
            add(alt_seq, "alternative_repair")
        for o, d in ordr if m >= 2 else []:
            add([(o, d)], "single_partial")
        if dis:
            pd = parking(rec, dis[0], cells, avoid, 1)
            add(ordr + [(dis[0], pd[0] if pd else None)], "repair_plus_unnecessary")
            if wrong:
                add(ordr + [(dis[0], wrong[0])], "repair_then_harmful")
        if m >= 2:                                                               # interference: A parked on B's pick-kill cell first
            A, B = ordr[0][0], ordr[1][0]
            kB = access_map("pick", c0[B])["kill"]
            hit = sorted({x for ks in kB.values() for x in ks} - avoid - set(c0.values()) - {src, goal} - set(C["q_ref_footprint"]) - set(park.values()),
                         key=lambda d: (math.dist(_xy(d), _xy(c0[A])), d))
            if hit:
                add([(A, hit[0]), (B, park[B])], "interference_blocking_order")
                add([(B, park[B]), (A, hit[0])], "interference_safe_order")
    harm = [h["cell"] for h in C["harmful_cells"] if h["cell"] not in c0.values()]
    movers = dis + [o for o in mov if rec["roles"][o] == "nonintended_ring"] + ([o for o in mov if o not in dis] if not C["K_geom"] else [])
    for o in list(dict.fromkeys(movers))[:2]:
        if harm:
            add([(o, harm[0])], "harmful_edit")
        nn = [d for d in neutral if screen("place", _ideal_scene(rec, c0), oid=o, dest=d)][:1]
        add([(o, nn[0] if nn else None)], "neutral_edit")
    if len(movers) >= 2 and len(neutral) >= 2:
        a_, b_ = list(dict.fromkeys(movers))[:2]
        add([(a_, neutral[0]), (b_, neutral[1])], "neutral_pair")
        add([(b_, neutral[1]), (a_, neutral[0])], "neutral_pair_reversed")
    foot = C["q_ref_footprint"]
    if foot and mov:
        corr = min((d for d in neutral), key=lambda d: (min(math.dist(_xy(d), _xy(f)) for f in foot), d), default=None)
        add([(mov[0], corr)], "qref_corridor_destination")
    seen, uniq = set(), []
    for seq, kind in out:
        sg = bd.sig(seq)
        if sg not in seen and len({o for o, _ in seq}) == len(seq) and len(seq) + 1 <= bc.MAX_ACTIONS:
            seen.add(sg)
            uniq.append((seq, kind))
    return uniq


def root_design(k, rec) -> dict:
    """y0 + X and Y of every catalogue candidate (each candidate is a stopping prefix: X includes the connector to q_ref), in catalogue
    priority order, truncated deterministically at MAX_CANDS candidates / MAX_QUERIES queries. Prefixes and omissions are themselves
    candidates (prefix-complete supervision of the intended repair); Y keys dedupe shared endpoints exactly."""
    Q, bad, cat = {}, {}, []
    PM._add(Q, bad, k, rec, "y", [], "y0")
    for seq, kind in candidates(rec):
        if len(cat) >= MAX_CANDS:
            break
        tq, tb = json.loads(json.dumps(Q)), json.loads(json.dumps(bad))
        PM._add(tq, tb, k, rec, "x", seq, kind)
        PM._add(tq, tb, k, rec, "y", seq, kind)
        if len(tq) > MAX_QUERIES:
            continue
        Q, bad = tq, tb
        f = F1.screen(rec, seq)
        cat.append({"seq": [list(a) for a in seq], "kind": kind, "sig": bd.sig(seq), "f1_complete_ok": f["complete_ok"], "f1_x_ok": f["x_ok"], "f1_y_ok": f["y_ok"]})
    return {"catalogue": cat, "queries": dict(sorted(Q.items())), "f1_screened": dict(sorted(bad.items()))}



# ------------------------------------------------------------------ development waves: generate, freeze, authorize, collect, summarize
WAVES = {"wA": {0: [("open", 3), ("near_closed", 7)], 1: [("pick", 2), ("place", 2), ("goal_occupant", 2)],
                2: [("pick", 2), ("nested", 3), ("mixed", 2), ("place", 1)], 3: [("pick", 2), ("nested", 3), ("mixed", 2)],
                4: [("pick", 2), ("nested", 2), ("mixed", 1)]}}


def specs(wave) -> list:
    out, i = [], 0
    for K, mechs in sorted(WAVES[wave].items()):
        for mech, n in mechs:
            for _ in range(n):
                sp = {"K_intent": K, "mechanism": mech, "displacement": ("short", "medium", "long")[(2 * i) % 3], "source": ("near", "mid", "far")[(i + 1) % 3],
                      "start_pose": ("home", "nonhome")[(i // 2) % 2], "distractors": ("0", "1-2", "3-4")[(5 * i + 1) % 3]}
                if mech in ("open", "near_closed") and sp["distractors"] == "0":
                    sp["distractors"] = "1-2"
                out.append(sp)
                i += 1
    return out


def wdir(wave) -> Path:
    return OUT / wave


def roots_of(wave) -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted((wdir(wave) / "roots").glob("*.json"))}


def generate(wave) -> dict:
    if wave not in WAVES:
        raise PermissionError(f"unknown development wave {wave}")
    d = wdir(wave)
    if (d / "DESIGN.json").exists():
        raise FileExistsError("wave already frozen")
    (d / "roots").mkdir(parents=True, exist_ok=True)
    attempts = []
    for slot, sp_ in enumerate(specs(wave)):
        idd = ids(wave, slot, sp_)
        row = {"slot": slot, "spec": sp_, "root_id": idd["root_id"], "family": idd["parent_family_id"], "seed": idd["construction_seed"]}
        t0 = time.process_time()
        try:
            rec = construct(sp_, idd, d)
            dd = root_design(idd["root_id"], rec)
        except bd_2d.Reject as e:
            attempts.append(row | {"accepted": False, "reject": str(e), "cpu_s": round(time.process_time() - t0, 3)})
            continue
        rec["catalogue_v21"], rec["design_v21"] = dd["catalogue"], {"queries": dd["queries"], "f1_screened": dd["f1_screened"]}
        (d / "roots" / f"{idd['root_id']}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
        attempts.append(row | {"accepted": True, "cpu_s": round(time.process_time() - t0, 3), "candidates": len(dd["catalogue"]), "queries": len(dd["queries"]),
                               "kinds": [c["kind"] for c in dd["catalogue"]], "K_geom": rec["construction"]["K_geom"], "forced": rec["construction"]["forced_order"]})
    save_maps()
    man = {"generator": GEN, "wave": wave, "attempts": attempts, "accepted": sum(a["accepted"] for a in attempts),
           "construction_cpu_s": round(sum(a["cpu_s"] for a in attempts), 3), "t": time.time()}
    (d / "GENERATION.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


def freeze(wave) -> str:
    d = wdir(wave)
    R = roots_of(wave)
    D = {"version": f"BXY_P16_DESIGN_{wave}", "generator": GEN, "teacher_hash": T.teacher_hash(), "teacher_policy": T.TEACHER, "f1": F1.VERSION,
         "per_query_budget": bd_2d.QB, "max_cands": MAX_CANDS, "max_queries": MAX_QUERIES, "root_order": sorted(R),
         "roots": {k: {"record_sha256": bc.sha(r), "catalogue": r["catalogue_v21"], "queries": r["design_v21"]["queries"]} for k, r in R.items()},
         "generation_sha256": PM.sha_file(d / "GENERATION.json"), "access_maps_sha256": PM.sha_file(_maps_file()), "generator_sha256": PM.sha_file("bxy_p16.py")}
    f, txt = d / "DESIGN.json", json.dumps(D, indent=1, sort_keys=True)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("wave design already frozen with different content")
    if (d / "results").exists() and any((d / "results").iterdir()):
        raise RuntimeError("teacher results exist: a design must be frozen before any query")
    f.write_text(txt)
    return PM.sha_file(f)


def spent() -> dict:
    """P16 aggregate accounting across waves: access-map CPU, construction CPU of every attempted slot, worker CPU, collection wall."""
    maps = sum(v["cpu_s"] for v in _load_maps().values())
    cons, coll, wall, roots = 0.0, 0.0, 0.0, 0
    for g in sorted(OUT.glob("w*/GENERATION*.json")):            # superseded pre-freeze generations count too
        cons += json.loads(g.read_text())["construction_cpu_s"]
    for g in sorted(OUT.glob("w*/PRELABEL_AUDIT.json")):         # geometry audits count as construction
        cons += json.loads(g.read_text())["cpu_s"]
    for led in sorted(OUT.glob("w*/LEDGER.jsonl")):
        ev = [json.loads(x) for x in led.read_text().splitlines() if x.strip()]
        coll += sum(e["cpu_s"] for e in ev if e["event"] == "finish")
        st = [e["t"] for e in ev]
        wall += (max(st) - min(st)) if st else 0.0
        roots += len({e["root"] for e in ev if e["event"] == "start"})
    mw = json.loads((OUT / "geometry" / "MAPS_WALL.json").read_text())["wall_s"] if (OUT / "geometry" / "MAPS_WALL.json").exists() else 0.0
    return {"maps_cpu_s": round(maps, 1), "construction_cpu_s": round(cons, 1), "collection_cpu_s": round(coll, 1),
            "total_cpu_s": round(maps + cons + coll, 1), "collection_wall_s": round(wall, 1), "maps_wall_s": mw, "total_wall_s": round(wall + mw, 1),
            "labelled_roots_started": roots}


def authorize(wave) -> dict:
    d = wdir(wave)
    f = d / "AUTHORIZATION.json"
    if f.exists():
        raise FileExistsError(str(f))
    sp = spent()
    a = {"gate": "BXY-P16", "wave": wave, "scope": "development teacher labelling of the frozen wave design only (namespace bxyg21dev)",
         "limits_total": LIMITS, "spent_before": sp, "cpu_left": round(LIMITS["cpu_s"] - sp["total_cpu_s"], 1), "wall_left": round(LIMITS["wall_s"] - sp["total_wall_s"], 1),
         "roots_left": LIMITS["roots"] - sp["labelled_roots_started"], "design_sha256": PM.sha_file(d / "DESIGN.json"), "runner_sha256": PM.sha_file("bxy_p16.py"),
         "teacher_hash": T.teacher_hash(), "per_query_budget": bd_2d.QB, "authorized": True, "created_at": time.time(),
         "authorized_by": "user execution contract BXY-P16..P18 (2026-11-01) section F: 24,000 CPU-s, 800 CPU-s / root, 4 workers, 14,400 s wall, <= 120 roots"}
    if a["roots_left"] < len(json.loads((d / "DESIGN.json").read_text())["root_order"]):
        raise PermissionError("wave would exceed the 120-root ceiling")
    f.write_text(json.dumps(a, indent=1, sort_keys=True))
    return a


def worklist(D) -> dict:
    return {k: [dict(q, key=key) for key, q in sorted(D["roots"][k]["queries"].items(), key=lambda kv: (kv[1]["side"], kv[0]))] for k in D["root_order"]}


def worker(wave, k) -> None:
    import bxy_pmin_collect as PC
    d = wdir(wave)
    D = json.loads((d / "DESIGN.json").read_text())
    rec = roots_of(wave)[k]
    if bc.sha(rec) != D["roots"][k]["record_sha256"]:
        raise RuntimeError(f"{k}: record differs from the frozen design")
    E, cache, rd = T.env(), {}, d / "results" / k
    rd.mkdir(parents=True, exist_ok=True)
    for i, q in enumerate(worklist(D)[k]):
        f = rd / f"{i:04d}.{q['side']}.json"
        if f.exists():
            continue
        m = rd / f"{i:04d}.{q['side']}.inprogress"
        PC.jw(m, {"started": time.time(), "key": q["key"]})
        seq = [tuple(a) for a in q["seq"]]
        row = T.x_query(E, k, rec, seq, cache, d) if q["side"] == "x" else PM.y_query_counted(E, k, rec, seq, cache, d, None)
        if row.get(f"{q['side']}_key") != q["key"]:
            row = {"root": k, "attempted": True, "observed": False, "y": None, "teacher_status": "IDENTITY_MISMATCH", "got": row.get(f"{q['side']}_key")}
        PC.jw(f, row | {"item": i, "side": q["side"], "design_key": q["key"], "classes": q["classes"], "teacher_hash": T.teacher_hash(), "runner": GEN})
        m.unlink()


def collect(wave) -> dict:
    import bxy_pmin_collect as PC
    d = wdir(wave)
    a = json.loads((d / "AUTHORIZATION.json").read_text())
    if a["design_sha256"] != PM.sha_file(d / "DESIGN.json") or a["runner_sha256"] != PM.sha_file("bxy_p16.py") or a["teacher_hash"] != T.teacher_hash():
        raise PermissionError("wave authorization drift")
    if bd_2d.QB != PC.QB:
        raise PermissionError("per-query budget differs from P-min")
    sp = spent()
    L = {"cpu_s": LIMITS["cpu_s"] - sp["total_cpu_s"], "root_cpu_s": LIMITS["root_cpu_s"], "workers": LIMITS["workers"],
         "wall_s": LIMITS["wall_s"] - sp["total_wall_s"], "min_allow": LIMITS["min_allow"]}
    D = json.loads((d / "DESIGN.json").read_text())
    return PC.supervise(d, roots=D["root_order"], limits=L, cmd=lambda k: [sys.executable, "bxy_p16.py", "worker", wave, k], est=None,
                        ramp=((0, 2), (2, 4)), gates=True)



# ------------------------------------------------------------------ realized outcomes and the data-readiness gate (frozen before any label)
READINESS = {"labelled_roots": 60, "infeasible_roots": 20, "verified_K_ge2_roots": 12, "discordant_pairs": 4, "discordant_pair_roots": 3,
             "harmful_contrast_roots": 12}


def results(wave, k) -> dict:
    rd = wdir(wave) / "results" / k
    return {r["design_key"]: r for r in (json.loads(f.read_text()) for f in sorted(rd.glob("*.json")))} if rd.exists() else {}


def root_summary(wave, k, rec, D) -> dict:
    res = results(wave, k)
    y = lambda key: (res.get(key) or {}).get("y")  # noqa: E731
    y0 = y(T.ykey(k, rec, []))
    rows = []
    for c in D["roots"][k]["catalogue"]:
        seq = [tuple(a) for a in c["seq"]]
        xr, yr = res.get(T.xkey(k, rec, seq)) or {}, res.get(T.ykey(k, rec, seq)) or {}
        rows.append({"kind": c["kind"], "sig": c["sig"], "m": len(seq), "f1": c["f1_complete_ok"], "x_ok": c["f1_x_ok"], "x": xr.get("y"), "y": yr.get("y"),
                     "endpoint": T.ykey(k, rec, seq), "x_neg": xr.get("negative_kind"), "x_phase": xr.get("failed_phase"), "x_status": xr.get("teacher_status"),
                     "y_neg": yr.get("negative_kind"), "y_status": yr.get("teacher_status")})
    ver = [r for r in rows if r["f1"] and r["x"] == 1 and r["y"] == 1]
    vk = "UNOBSERVED_Y0" if y0 is None else 0 if y0 == 1 else (min(r["m"] for r in ver) if ver else None)
    by_end = collections.defaultdict(list)
    for r in rows:
        if r["m"] >= 2 and r["x_ok"] and r["x"] is not None:
            by_end[r["endpoint"]].append(r)
    disc = [{"endpoint": e, "orders": [(r["sig"], r["x"], r["x_neg"], r["x_phase"]) for r in g]} for e, g in by_end.items() if len({r["x"] for r in g}) > 1]
    harm = [r for r in rows if y0 == 1 and r["m"] >= 1 and r["y"] == 0]
    cells = collections.Counter(f"{r['x']}{r['y']}" for r in rows if r["x"] is not None and r["y"] is not None)
    rep = next((r for r in rows if r["kind"] == "repair"), None)
    pref = [r for r in rows if r["kind"].startswith("prefix_")]
    status = collections.Counter((r.get("teacher_status") or "NONE") for r in res.values())
    return {"root": k, "spec": rec["spec"], "K_geom": rec["construction"]["K_geom"], "forced_order": rec["construction"]["forced_order"],
            "queries": len(D["roots"][k]["queries"]), "results": len(res), "censored": status.get("CENSORED", 0), "y0": y0, "verified_K": vk,
            "verified_repairs": len(ver), "verified_kinds": sorted({r["kind"] for r in ver}), "cells": dict(cells), "discordant": disc,
            "harmful": [(r["kind"], r["sig"], r["y_neg"]) for r in harm], "connector_failures": sum(1 for r in res.values() if r.get("side") == "x" and
                                                                                               str(r.get("failed_phase") or "").startswith("connector")),
            "repair": {"x": rep["x"], "y": rep["y"], "m": rep["m"], "prefix_y": [p["y"] for p in sorted(pref, key=lambda p: p["m"])],
                       "prefix_x": [p["x"] for p in sorted(pref, key=lambda p: p["m"])]} if rep else None,
            "cpu_s": round(sum((r.get("process_cpu_s") or 0.0) for r in res.values()), 1),
            "x_neg": dict(collections.Counter(r.get("negative_kind") for r in res.values() if r.get("side") == "x" and r.get("y") == 0)),
            "y_neg": dict(collections.Counter(r.get("negative_kind") for r in res.values() if r.get("side") == "y" and r.get("y") == 0)),
            "statuses": dict(status), "rows": rows}


def summarize(wave) -> dict:
    d = wdir(wave)
    D = json.loads((d / "DESIGN.json").read_text())
    R = roots_of(wave)
    rows = [root_summary(wave, k, R[k], D) for k in D["root_order"]]
    gen = json.loads((d / "GENERATION.json").read_text())
    by = lambda f: {str(v): dict(collections.Counter(str(r["verified_K"]) for r in rows if r["spec"][f] == v)) for v in sorted({r["spec"][f] for r in rows}, key=str)}  # noqa: E731
    return {"wave": wave, "roots": len(rows), "attempted_slots": len(gen["attempts"]), "rejected": [a for a in gen["attempts"] if not a["accepted"]],
            "verified_K": dict(collections.Counter(str(r["verified_K"]) for r in rows)), "by_K_intent": by("K_intent"), "by_mechanism": by("mechanism"),
            "K_geom_vs_verified": dict(collections.Counter(f"{r['K_geom']}->{r['verified_K']}" for r in rows)), "spent": spent(), "rows": rows}


def readiness(waves) -> dict:
    """Totals over the collected development waves vs the frozen READINESS targets (engineering criteria, not outcomes to fabricate)."""
    rows = [r for w in waves for r in json.loads((wdir(w) / "SUMMARY.json").read_text())["rows"] if r["results"]]
    tot = {"labelled_roots": len(rows), "infeasible_roots": sum(r["y0"] == 0 for r in rows),
           "verified_K_ge2_roots": sum(isinstance(r["verified_K"], int) and r["verified_K"] >= 2 for r in rows),
           "discordant_pairs": sum(len(r["discordant"]) for r in rows), "discordant_pair_roots": sum(bool(r["discordant"]) for r in rows),
           "harmful_contrast_roots": sum(bool(r["harmful"]) for r in rows)}
    ok = {k: tot[k] >= v for k, v in READINESS.items()}
    return {"targets": READINESS, "totals": tot, "met": ok, "decision": "DATA_READY" if all(ok.values()) else "DATA_READINESS_FAILED", "waves": list(waves)}



def prelabel_audit(wave) -> dict:
    """Geometry-only checks of every accepted root before any label: real pick / place screens of T in S0, after each intended prefix and
    after the full intended repair (ideal object scenes); for every same-endpoint order pair the analytic pick screen of each step's object
    in its ideal predecessor scene (a closed first-step pick is an independently reproducible order certificate candidate)."""
    out = {}
    for k, rec in roots_of(wave).items():
        c0, goal = bd.cells0(rec), rec["goal_cell"]
        row = {"K_geom": rec["construction"]["K_geom"], "mechanism": rec["spec"]["mechanism"], "S0": rec["construction"]["S0_open"], "candidates": {}}
        for c in rec["catalogue_v21"]:
            cells, steps = dict(c0), []
            for o, d in c["seq"]:
                steps.append(len(screen("pick", _ideal_scene(rec, cells), oid=o)))
                cells[o] = int(d)
            sc = _ideal_scene(rec, cells) if c["f1_y_ok"] else None
            row["candidates"][c["sig"]] = {"kind": c["kind"], "step_pick_open": steps,
                                           "T_pick_open": len(screen("pick", sc)) if sc else None, "T_place_open": len(screen("place", sc, dest=goal)) if sc else None}
        out[k] = row
    return out


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    cmd = sys.argv[1]
    if cmd == "maps":
        print(json.dumps(precompute()))
    elif cmd == "generate":
        print(json.dumps({k: v for k, v in generate(sys.argv[2]).items() if k != "attempts"}))
    elif cmd == "freeze":
        print(freeze(sys.argv[2]))
    elif cmd == "authorize":
        print(json.dumps(authorize(sys.argv[2]), indent=1))
    elif cmd == "collect":
        print(json.dumps(collect(sys.argv[2]), indent=1, default=str))
    elif cmd == "audit":
        t0 = time.process_time()
        au = prelabel_audit(sys.argv[2])
        (wdir(sys.argv[2]) / "PRELABEL_AUDIT.json").write_text(json.dumps({"cpu_s": round(time.process_time() - t0, 1), "roots": au}, indent=1, sort_keys=True))
        print(len(au))
    elif cmd == "summarize":
        sm = summarize(sys.argv[2])
        (wdir(sys.argv[2]) / "SUMMARY.json").write_text(json.dumps(sm, indent=1, sort_keys=True, default=str))
        print(json.dumps({k: v for k, v in sm.items() if k != "rows"}, default=str))
    elif cmd == "readiness":
        rd = readiness(sys.argv[2:])
        (OUT / "READINESS.json").write_text(json.dumps(rd, indent=1, sort_keys=True))
        print(json.dumps(rd))
    elif cmd == "worker":
        worker(sys.argv[2], sys.argv[3])
