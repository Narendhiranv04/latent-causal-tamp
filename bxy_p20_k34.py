"""BXY-P20 K3/K4 development generator (BXY_GEN_K34), outcome-blind catalogue with K4-capable query design, bounded waves, collection,
summary and readiness. Development namespace bxyg34dev only. Implements runs/approach_b/bxy_p19_v1/P20_PLAN.json.

Families (all geometry-only; no populated-scene motion planning, no teacher call during construction):
  local_mixed   distributed closure: every declared T-pick mode covered >= Kp times and every T-place mode >= Kg times by movable blockers
                drawn from LOCAL pools (Chebyshev <= 2 of the source / goal), by seeded greedy covering; the EXACT order-free bound over all
                finite mode pairs (bxy_p16.requirements) must equal K and the real-screen certificate K_cert must equal K
  local_pick    the same with the whole K on the pick side
  v21b_*        P16 V21B construction (bxy_p16._construct_once + validate, REV['wB']) -- a second, non-local geometry family / controls
Acceptance (local families): the order-free lower bound K_LB == K_intent; K_cert == K_intent (real screens: every (K-1)-subset of the
movable discs removed leaves the T pick or place certified closed -- a sound necessity bound); an intended removal order in which every
blocker's pick screen is open (>= 2 modes) in its ideal predecessor scene with no analytic edge certificate; a short-carry parking cell
(Chebyshev <= 2, arm-comfortable first) with >= 3 open place modes off the reopened T modes' kill cells; after the full repair >= 3 / >= 3
open T modes and no analytic certificate.
    python3 bxy_p20_k34.py generate <wave> [workers] | audit <wave> | freeze <wave> | authorize <wave> | collect <wave> | worker <wave> <root>
                          | summarize <wave> | readiness <waves...>"""
from __future__ import annotations

import collections
import itertools
import json
import math
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import numpy as np

import bd_2d
import bd_core as bc
import bxy_data as bd
import bxy_f1 as F1
import bxy_p15 as P15
import bxy_p16 as G
import bxy_p19_audit as A
import bxy_pmin as PM
import bxy_teacher as T

OUT = Path("runs/approach_b/bxy_p20_v1")
GEN = "BXY_GEN_K34"
GEN_WAVE = {"k1": GEN, "k2": "BXY_GEN_K34B", "k3": "BXY_GEN_K34C"}
REV34 = {"k1": {}, "k2": {"step_sector_certificate": True, "step_min_pick": 3}, "k3": {"step_sector_certificate": True, "step_min_pick": 3, "min_row": 3, "blocker_min_row": 2}}
LINK0_M = 0.46                                              # cells nearer the base than this lie in the link-0 sweep annulus (k1 diagnosis)
NS = "bxyg34dev"
MAX_CANDS, MAX_QUERIES = 24, 60
LIMITS = {"cpu_s": 60000.0, "root_cpu_s": 1400.0, "workers": 4, "wall_s": 28800.0, "roots": 150, "min_allow": 30.0}
LOCAL_R, PF, MAX_FIXED_SIDE = 3, 0.6, 4                     # walled niche: fixed discs close most modes, movables cover the corridor K times
COMFORT_M = 0.62                                            # arm-comfortable cells: centre within this distance of the base (P19 §1.2)
WAVES = {"k3": [("local_mixed", 4, 25), ("local_pick", 4, 5), ("local_mixed", 3, 12), ("local_pick", 3, 5), ("local_mixed", 2, 3), ("v21b_near_closed", 0, 5)],
         "k2": [("local_mixed", 4, 20), ("local_pick", 4, 6), ("local_mixed", 3, 10), ("local_pick", 3, 6), ("local_mixed", 2, 4), ("v21b_nested", 3, 3),
               ("v21b_near_closed", 0, 6)],
         "k1": [("local_mixed", 4, 12), ("local_mixed", 3, 10), ("local_pick", 3, 4), ("local_mixed", 2, 4), ("local_pick", 1, 4), ("v21b_near_closed", 0, 6)]}
READINESS = {"verified_K3": 20, "verified_K4": 20, "mechanisms_each": 2, "strict_order_K34": 10, "harmful": 10, "neutral": 10}
LIMITED = {"verified_K3": 12, "verified_K4": 10}


@contextmanager
def p16_paths():
    """Run bxy_p16 wave helpers (results / roots / summaries / worker) against the P20 run tree."""
    old = G.OUT
    G.OUT = OUT
    try:
        yield
    finally:
        G.OUT = old


def comfort(c) -> float:
    return math.dist(G._xy(c), tuple(bd_2d.env()["robot"].base))


def ids(wave, slot, spec) -> dict:
    E = bd_2d.env()
    return {"root_id": f"2d-{NS}-{wave}-s{slot:03d}", "parent_family_id": "fam34-" + bc.sha([GEN, wave, slot, spec])[:10],
            "construction_seed": int(bc.sha([GEN, NS, wave, slot])[:8], 16), "variant_id": "orig", "generator_version": GEN_WAVE.get(wave, GEN), "namespace": "dev",
            "wave": wave, "config_hash": E["config_hash"], "teacher_version": bd_2d.TEACHER_VERSION, "robot_protocol": E["protocol"],
            "label_protocol": bc.LABEL_PROTOCOL}


# ------------------------------------------------------------------ exact local side closure (finite mode abstraction, bitmasks)
def _masks(km) -> list:
    return [sum(1 << x for x in ks) for ks in km["kill"].values()]


def side_closures(km, pool, k_side, max_fixed=1) -> list:
    """Every (F, M) with F a subset of pool, |F| <= max_fixed, M a subset of pool \\ F, |M| = k_side, such that every declared mode is killed by F
    or covered >= k_side times by M, and min coverage over the fixed-free modes == k_side (exact, union model)."""
    ms, out = _masks(km), []
    pool = sorted(pool)
    for nf in range(max_fixed + 1):
        for F in itertools.combinations(pool, nf):
            fm = sum(1 << x for x in F)
            free = [m for m in ms if not m & fm]
            if not free:
                continue
            for M in itertools.combinations([c for c in pool if c not in F], k_side):
                mm = sum(1 << x for x in M)
                cov = [bin(m & mm).count("1") for m in free]
                if min(cov) == k_side:
                    out.append((list(F), list(M)))
    return out


# ------------------------------------------------------------------ construction
def _task(rng, spec, rev=None):
    E = bd_2d.env()
    import p6_scenes as p6
    mr = (rev or {}).get("min_row", 0)
    good = [c for c in E["valid"] if comfort(c) <= (COMFORT_M if not mr else 0.75) and c // 8 >= mr and G.access_map("pick", c)["open"] and G.access_map("place", c)["open"]]
    for _ in range(50):
        src = int(rng.choice(good))
        far = [c for c in good if 2 <= bd_2d.cheb(c, src) <= 4]
        if far:
            goal = int(rng.choice(far))
            stratum = "S0" if spec["start_pose"] == "home" else str(rng.choice(["S1", "S2", "S3"]))
            return src, goal, stratum, tuple(p6.STRATA[stratum])
    raise bd_2d.Reject("NO_COMFORTABLE_TASK")


def _niche_side(rng, km, k, excl, occupied, max_fixed=6, walls=(), forbid=frozenset(), local=None):
    """Doorway construction on one side (pick or place): a doorway D of 3-6 declared modes (a seed mode and its angular neighbours) stays the
    only fixed-free set; fixed walls are chosen only from cells that kill modes OUTSIDE D and no mode in D (greedy set cover); the k movable
    blockers lie in the intersection of D's kill sets, so every doorway mode is covered exactly k times (union model)."""
    import skill as sk
    dirs = sk.directions(sk.params(bd_2d.env()["cfg"]))
    kill_all = {i: set(km["kill"][i]) for i in km["kill"]}
    modes = [i for i in km["kill"] if not set(walls) & kill_all[i]]   # modes already killed by the other side's walls stay killed
    kill = {i: kill_all[i] for i in modes}
    for _ in range(120):
        if len(modes) < 3:
            break
        seed = modes[int(rng.integers(0, len(modes)))]
        phi0 = dirs[int(seed)][0]
        width = float(rng.choice([0.27, 0.53, 0.8]))                  # +-15, 30, 45 degrees
        D = [i for i in modes if abs(math.remainder(dirs[int(i)][0] - phi0, 2 * math.pi)) <= width]
        if len(D) < 3:
            continue
        core = set.intersection(*(kill[i] for i in D)) - excl - occupied - forbid
        if local is not None:
            core &= local
        if len(core) < k:
            continue
        inside = set().union(*(kill[i] for i in D))
        allowed = set().union(*(kill[i] for i in modes if i not in D)) - inside - excl - occupied - core - forbid
        if local is not None:
            allowed &= local
        todo, fixed = [i for i in modes if i not in D], []
        while todo and len(fixed) < max_fixed:
            gain = {c: sum(c in kill[i] for i in todo) for c in allowed - set(fixed)}
            if not gain or max(gain.values()) == 0:
                break
            top = max(gain.values())
            c = sorted(c for c, g in gain.items() if g == top)[int(rng.integers(0, sum(g == top for g in gain.values())))]
            fixed.append(c)
            todo = [i for i in todo if c not in kill[i]]
        if todo:
            continue
        mov = sorted(core, key=lambda c: (comfort(c) > COMFORT_M, comfort(c), c))
        pick = [int(x) for x in rng.choice(mov[:max(k, min(len(mov), k + 2))], k, replace=False)]
        return fixed, pick, D, inside
    raise bd_2d.Reject("NO_DOORWAY")


def _local_layout(rng, spec, src, goal, excl, rev=None):
    """Doorway closure of the T pick (Kp blockers) and the T place (Kg blockers); acceptance needs the exact order-free bound
    (bxy_p16.requirements) == K and the real-screen certificate K_cert == K."""
    K, fam = spec["K_intent"], spec["family"]
    kp_, kg_ = G.access_map("pick", src), G.access_map("place", goal)
    split = [(K, 0)] if fam == "local_pick" else ([(a, K - a) for a in range(1, K) if a <= 3 and K - a <= 3] or [(K, 0)])
    kp, kg = split[int(rng.integers(0, len(split)))]
    fixed, mov, inside = [], [], set()
    md = (rev or {}).get("min_base_dist")
    loc = lambda c: {x for x in range(64) if comfort(x) >= md} if md else None  # noqa: E731
    if kp:
        f, m, _, inside = _niche_side(rng, kp_, kp, excl, set(), local=loc(src))
        fixed, mov = fixed + f, mov + m
    if kg:                                       # place walls / blockers never touch the pick doorway; pick walls already killing place modes count
        f, m, _, _ = _niche_side(rng, kg_, kg, excl, set(fixed) | set(mov), walls=fixed, forbid=frozenset(inside), local=loc(goal))
        fixed, mov = fixed + f, mov + m
    if len(mov) > bc.MAX_MOVABLE:
        raise bd_2d.Reject("TOO_MANY_MOVABLES")
    return fixed, mov, (kp, kg)


def _intended(rec, opt, kp_, kg_, rev=None):
    """Validated intended relocation sequence for option `opt` (geometry only) or (None, reason)."""
    c0 = bd.cells0(rec)
    avoid = set(kp_["kill"][str(opt["pick"])]) | set(kg_["kill"][str(opt["place"])])
    cells, seq = dict(c0), []
    remaining = list(opt["remove"])
    if any(c0[o] // 8 < (rev or {}).get("blocker_min_row", 0) for o in remaining):
        return None, "BLOCKER_IN_BOTTOM_ROWS"
    while remaining:                                                  # choose the next blocker whose pick is open, most open first
        best = None
        for o in sorted(remaining):
            n = len(G.screen("pick", G._ideal_scene(rec, cells), oid=o))
            if n >= (rev or {}).get("step_min_pick", 2) and (best is None or n > best[1]):
                best = (o, n)
        if best is None:
            return None, "STEP_PICK_CLOSED"
        o = best[0]
        bad = avoid | set(rec["construction"]["q_ref_footprint"]) | {c0["t0"], rec["goal_cell"]} | set(cells.values())
        opts = sorted((d for d in range(64) if d not in bad and bd_2d.cheb(d, cells[o]) <= 2 and d // 8 >= (rev or {}).get("min_row", 0)),
                      key=lambda d: (comfort(d) > COMFORT_M, bd_2d.cheb(d, cells[o]), comfort(d), d))
        park = next((d for d in opts if len(G.screen("place", G._ideal_scene(rec, cells), oid=o, dest=d)) >= 3), None)
        if park is None:
            return None, "NO_SHORT_PARKING"
        if G.edge_certified(rec, cells, o, park):
            return None, "STEP_CERTIFIED"
        if (rev or {}).get("step_sector_certificate") and _obj_certified(rec, cells, o, park):
            return None, "STEP_SECTOR_CERTIFIED"
        seq.append((o, park))
        cells[o] = park
        remaining.remove(o)
    sc = G._ideal_scene(rec, cells)
    if len(G.screen("pick", sc)) < 3 or len(G.screen("place", sc, dest=rec["goal_cell"])) < 3:
        return None, "REOPEN_TOO_NARROW"
    if G.certified(rec, cells):
        return None, "REPAIR_CERTIFIED"
    return seq, None


def _obj_certified(rec, cells, o, dest) -> list:
    """The teacher's analytic certificate checker (p15_retarget.certified: ordered.certificates_for + link-0 sector) for picking object o and
    placing it at dest, robot at q_ref in the ideal scene `cells` (geometry only; an empty list is not a feasibility claim)."""
    import p15_retarget as pr
    E = bd_2d.env()
    return pr.certified(E["cfg"], E["robot"], G._ideal_scene(rec, cells), o, int(dest))


def construct_local(spec, idd, store_out, rng, tries=None) -> dict:
    import p14_sweep_index as sx
    from scene import place_scene, scene_to_dict
    E = bd_2d.env()
    cfg, robot, rid, K = E["cfg"], E["robot"], idd["root_id"], spec["K_intent"]
    rejects = collections.Counter()
    for t in range(tries or (60 if K >= 4 else 30)):
        try:
            src, goal, stratum, q0 = _task(rng, spec, REV34.get(idd["wave"]))
            excl = {src, goal} | P15.footprint(q0)
            fixed, mov, split = _local_layout(rng, spec, src, goal, excl, REV34.get(idd["wave"]))
        except bd_2d.Reject as e:
            rejects[str(e).split(":")[0]] += 1
            continue
        movable = {f"b{i}": c for i, c in enumerate(mov)}
        lb = G.requirements(movable, fixed, src, goal)
        if not lb or lb[0][0] != K:
            rejects["LB_MISMATCH"] += 1
            continue
        kp_, kg_ = G.access_map("pick", src), G.access_map("place", goal)
        occ = {src, goal, *fixed, *mov}
        kill_any = {x for i, j, _, _ in [(r[1], r[2], 0, 0) for r in lb if r[0] == K] for x in kp_["kill"][str(i)] + kg_["kill"][str(j)]}
        neutral = sorted(c for c in range(64) if c not in occ and c not in excl and c not in kill_any and comfort(c) <= 0.75)
        nd = int(rng.integers(0, 3)) if spec.get("distractors", True) else 0
        dis = [int(x) for x in rng.choice(neutral, min(nd, len(neutral)), replace=False)] if nd and neutral else []
        s = place_scene(cfg, rid, "orig", [src], mov + dis + fixed)
        s = replace(s, robot=replace(s.robot, q_rad=q0))
        allids = [o.id for o in s.objects if o.id != "t0"]
        name = dict(zip(movable, allids[:len(mov)]))
        mov_ids, fixed_ids = allids[:len(mov) + len(dis)], allids[len(mov) + len(dis):]
        rec = {"ids": idd, "domain": bd_2d.DOMAIN, "generator": GEN_WAVE.get(idd["wave"], GEN), "spec": spec, "scene": scene_to_dict(s), "goal_cell": goal, "start_stratum": stratum,
               "q0": list(q0), "q_ref": list(q0), "roles": {i: ("intended_blocker" if i in name.values() else "distractor") for i in mov_ids},
               "fixed_ids": fixed_ids, "construction": {"q_ref_footprint": sorted(P15.footprint(q0)), "harmful_cells": [], "neutral_cells": neutral}}
        kc, _ = A.k_cert(rec, K)
        if kc != K:
            rejects[f"K_CERT_{kc}"] += 1
            continue
        opts = [{"pick": i, "place": j, "remove": sorted(name[o] for o in rem)} for c_, i, j, rem in lb if c_ == K]
        seq, why = None, None
        for opt in opts[:6]:
            seq, why = _intended(rec, opt, kp_, kg_, REV34.get(idd["wave"]))
            if seq:
                break
        if not seq:
            rejects[why or "NO_OPTION"] += 1
            continue
        empty = place_scene(cfg, rid, "empty", [src], [])
        empty = replace(empty, robot=replace(empty.robot, q_rad=q0))
        st, a, _ = bd_2d.t_goal({"scene": scene_to_dict(empty), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": rid + ":ref"}, {}, {"t0": src},
                                np.asarray(q0, float))
        if st != "VERIFIED":
            rejects["T_NOT_VERIFIED_EMPTY_BOARD"] += 1
            continue
        sw = sx.swept_cells(robot, cfg, a)
        rec["construction"] |= {"family": spec["family"], "K_geom": K, "K_LB": K, "K_cert": kc, "split_pick_place": list(split), "forced_order": False,
                                "options": [dict(opts[0], order=[o for o, _ in seq])], "intended": [list(x) for x in seq],
                                "S0_open": {"pick": len(G.screen("pick", s)), "place": len(G.screen("place", s, dest=goal))},
                                "layout_try": t, "rejects": dict(rejects), "reference_sweep": {k: sorted(v) for k, v in sw.items()},
                                "reference_witness": T.wid({k: np.asarray(v) for k, v in a.items()}, store_out), "reference_planner_calls": 1}
        rec["intended_blockers"] = sorted(o for o, _ in seq)
        return rec
    raise bd_2d.Reject(f"NO_VALID_LAYOUT:{dict(rejects)}")


def construct_v21b(spec, idd, store_out, rng) -> dict:
    """Second geometry family / controls: the P16 V21B construction and validation, with this root's own seed and namespace."""
    rev = G.REV["wB"]
    mech = spec["family"].split("_", 1)[1]
    sp = {"K_intent": spec["K_intent"], "mechanism": mech, "displacement": spec["displacement"], "source": spec["source"],
          "start_pose": spec["start_pose"], "distractors": "1-2"}
    rejects = collections.Counter()
    for _ in range(rev["layouts"]):
        try:
            rec = G._construct_once(sp, idd, store_out, 400, rng)
        except bd_2d.Reject as e:
            rejects[str(e).split(":")[0]] += 1
            continue
        why = G.validate(rec, rev)
        if why is None:
            rec["generator"], rec["spec"] = GEN, spec
            kc, _ = A.k_cert(rec, max(spec["K_intent"], 1)) if spec["K_intent"] else (0, 0)
            rec["construction"] |= {"family": spec["family"], "K_cert": kc, "rejects": dict(rejects)}
            return rec
        rejects[why] += 1
    raise bd_2d.Reject(f"NO_VALID_LAYOUT:{dict(rejects)}")


def construct(spec, idd, store_out=None) -> dict:
    rng = np.random.default_rng(idd["construction_seed"])
    return (construct_v21b if spec["family"].startswith("v21b_") else construct_local)(spec, idd, store_out, rng)


# ------------------------------------------------------------------ outcome-blind catalogue (K4-capable)
def candidates(rec) -> list:
    c0, C = bd.cells0(rec), rec["construction"]
    if "intended" not in C:                                          # V21B family: the P16 catalogue unchanged
        return G.candidates(rec)
    seq = [(o, int(d)) for o, d in C["intended"]]
    m, src, goal = len(seq), c0["t0"], rec["goal_cell"]
    out = []
    add = lambda s, kind: out.append(([(o, int(d)) for o, d in s], kind)) if s and all(d is not None for _, d in s) else None  # noqa: E731
    add(seq, "repair")
    kp_, kg_ = G.access_map("pick", src), G.access_map("place", goal)
    opt = C["options"][0]
    avoid = set(kp_["kill"][str(opt["pick"])]) | set(kg_["kill"][str(opt["place"])])
    taken = set(c0.values()) | {d for _, d in seq} | set(C["q_ref_footprint"]) | {src, goal} | avoid
    alt = []
    for o, d in seq:                                                  # parking variant: second short-carry cell per blocker
        nxt = sorted((x for x in range(64) if x not in taken and bd_2d.cheb(x, c0[o]) <= 2), key=lambda x: (bd_2d.cheb(x, c0[o]), comfort(x), x))
        alt.append((o, nxt[0] if nxt else d))
        if nxt:
            taken.add(nxt[0])
    add(alt, "repair_park_variant")
    if m >= 2:
        add(seq[::-1], "repair_reversed")
        perms = [list(p) for p in itertools.permutations(seq) if list(p) not in (seq, seq[::-1])]
        for p in perms[:2]:
            add(p, "repair_permutation")
    for t in range(1, m):
        add(seq[:t], f"prefix_{t}")
    for t in range(m - 1 if m >= 2 else 0):
        add([a for i, a in enumerate(seq) if i != t], f"omission_{t}")
    for o, d in seq if m >= 2 else []:
        add([(o, d)], "single_partial")
    wrong = sorted((x for x in avoid if x not in c0.values() and x not in (src, goal) and x not in {d for _, d in seq}
                    and x not in C["q_ref_footprint"]), key=lambda x: (math.dist(G._xy(x), G._xy(c0[seq[-1][0]])), x))
    if wrong:
        add(seq[:-1] + [(seq[-1][0], wrong[0])], "repair_wrong_destination")
    dis = [o for o in sorted(rec["roles"]) if rec["roles"][o] == "distractor"]
    neutral = [x for x in C["neutral_cells"] if x not in c0.values() and x not in {d for _, d in seq}]
    if dis and neutral:
        add(seq + [(dis[0], neutral[0])], "repair_plus_unnecessary")
        add([(dis[0], neutral[0])], "neutral_edit")
        if wrong:
            add(seq + [(dis[0], wrong[0])], "repair_then_harmful")
    if m >= 2:                                                        # interference: first blocker parked on the second's pick-kill cell
        a_, b_ = seq[0][0], seq[1][0]
        kB = G.access_map("pick", c0[b_])["kill"]
        hit = sorted({x for ks in kB.values() for x in ks} - avoid - set(c0.values()) - {src, goal} - set(C["q_ref_footprint"]) - {d for _, d in seq},
                     key=lambda x: (math.dist(G._xy(x), G._xy(c0[a_])), x))
        if hit:
            add([(a_, hit[0]), (b_, seq[1][1])], "interference_blocking_order")
            add([(b_, seq[1][1]), (a_, hit[0])], "interference_safe_order")
    seen, uniq = set(), []
    for s, kind in out:
        sg = bd.sig(s)
        if sg not in seen and len({o for o, _ in s}) == len(s) and len(s) + 1 <= bc.MAX_ACTIONS:
            seen.add(sg)
            uniq.append((s, kind))
    return uniq


def root_design(k, rec) -> dict:
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


# ------------------------------------------------------------------ waves
def specs(wave) -> list:
    out, i = [], 0
    for fam, K, n in WAVES[wave]:
        for _ in range(n):
            out.append({"family": fam, "K_intent": K, "mechanism": fam, "start_pose": ("home", "nonhome")[(i // 2) % 2],
                        "displacement": ("short", "medium", "long")[(2 * i) % 3], "source": ("near", "mid", "far")[(i + 1) % 3], "distractors": True})
            i += 1
    return out


def wdir(wave) -> Path:
    return OUT / wave


def roots_of(wave) -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted((wdir(wave) / "roots").glob("*.json"))}


def _slot(args):
    wave, slot, sp_ = args
    idd = ids(wave, slot, sp_)
    row = {"slot": slot, "spec": sp_, "root_id": idd["root_id"], "family": idd["parent_family_id"], "seed": idd["construction_seed"]}
    t0 = time.process_time()
    try:
        rec = construct(sp_, idd, wdir(wave))
        dd = root_design(idd["root_id"], rec)
    except bd_2d.Reject as e:
        return row | {"accepted": False, "reject": str(e)[:400], "cpu_s": round(time.process_time() - t0, 3)}, None
    rec["catalogue_v21"], rec["design_v21"] = dd["catalogue"], {"queries": dd["queries"], "f1_screened": dd["f1_screened"]}
    return row | {"accepted": True, "cpu_s": round(time.process_time() - t0, 3), "candidates": len(dd["catalogue"]), "queries": len(dd["queries"]),
                  "kinds": [c["kind"] for c in dd["catalogue"]], "K_cert": rec["construction"].get("K_cert")}, rec


def generate(wave, workers=4) -> dict:
    import multiprocessing as mp
    if wave not in WAVES:
        raise PermissionError(f"unknown P20 development wave {wave}")
    d = wdir(wave)
    if (d / "DESIGN.json").exists():
        raise FileExistsError("wave already frozen")
    (d / "roots").mkdir(parents=True, exist_ok=True)
    w0, jobs = time.time(), [(wave, s, sp) for s, sp in enumerate(specs(wave))]
    G._load_maps()
    with mp.get_context("fork").Pool(workers) as pool:
        res = pool.map(_slot, jobs, chunksize=1)
    attempts = []
    for row, rec in res:
        attempts.append(row)
        if rec is not None:
            (d / "roots" / f"{row['root_id']}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    man = {"generator": GEN_WAVE.get(wave, GEN), "wave": wave, "attempts": attempts, "accepted": sum(a["accepted"] for a in attempts), "workers": workers,
           "construction_cpu_s": round(sum(a["cpu_s"] for a in attempts), 3), "t": time.time(), "wall_s": round(time.time() - w0, 1)}
    (d / "GENERATION.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


def freeze(wave) -> str:
    d = wdir(wave)
    R = roots_of(wave)
    D = {"version": f"BXY_P20_DESIGN_{wave}", "generator": GEN, "teacher_hash": T.teacher_hash(), "teacher_policy": T.TEACHER, "f1": F1.VERSION,
         "per_query_budget": bd_2d.QB, "max_cands": MAX_CANDS, "max_queries": MAX_QUERIES, "root_order": sorted(R),
         "roots": {k: {"record_sha256": bc.sha(r), "catalogue": r["catalogue_v21"], "queries": r["design_v21"]["queries"]} for k, r in R.items()},
         "generation_sha256": PM.sha_file(d / "GENERATION.json"), "access_maps_sha256": PM.sha_file(G._maps_file()), "generator_sha256": PM.sha_file("bxy_p20_k34.py")}
    f, txt = d / "DESIGN.json", json.dumps(D, indent=1, sort_keys=True)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("wave design already frozen with different content")
    if (d / "results").exists() and any((d / "results").iterdir()):
        raise RuntimeError("teacher results exist: a design must be frozen before any query")
    f.write_text(txt)
    return PM.sha_file(f)


def spent() -> dict:
    cons, coll, wall, roots = 0.0, 0.0, 0.0, 0
    for g in sorted(OUT.glob("k*/GENERATION*.json")):
        x = json.loads(g.read_text())
        cons += x["construction_cpu_s"]
        wall += x.get("wall_s", 0.0)
    for g in sorted(OUT.glob("k*/PRELABEL_AUDIT.json")):
        x = json.loads(g.read_text())
        cons += x["cpu_s"]
        wall += x.get("wall_s", x["cpu_s"])
    for led in sorted(OUT.glob("k*/LEDGER.jsonl")):
        ev = [json.loads(x) for x in led.read_text().splitlines() if x.strip()]
        coll += sum(e["cpu_s"] for e in ev if e["event"] == "finish")
        st = [e["t"] for e in ev]
        wall += (max(st) - min(st)) if st else 0.0
        roots += len({e["root"] for e in ev if e["event"] == "start"})
    extra = json.loads((OUT / "EXTRA_CPU.json").read_text()) if (OUT / "EXTRA_CPU.json").exists() else []
    xc, xw = sum(e["cpu_s"] for e in extra), sum(e["wall_s"] for e in extra)
    return {"construction_cpu_s": round(cons, 1), "collection_cpu_s": round(coll, 1), "extra_cpu_s": round(xc, 1),
            "total_cpu_s": round(cons + coll + xc, 1), "total_wall_s": round(wall + xw, 1), "labelled_roots_started": roots}


def authorize(wave) -> dict:
    d = wdir(wave)
    f = d / "AUTHORIZATION.json"
    if f.exists():
        raise FileExistsError(str(f))
    sp = spent()
    a = {"gate": "BXY-P20", "wave": wave, "scope": "development teacher labelling of the frozen wave design only (namespace bxyg34dev)",
         "limits_total": LIMITS, "spent_before": sp, "cpu_left": round(LIMITS["cpu_s"] - sp["total_cpu_s"], 1), "wall_left": round(LIMITS["wall_s"] - sp["total_wall_s"], 1),
         "roots_left": LIMITS["roots"] - sp["labelled_roots_started"], "design_sha256": PM.sha_file(d / "DESIGN.json"), "runner_sha256": PM.sha_file("bxy_p20_k34.py"),
         "teacher_hash": T.teacher_hash(), "per_query_budget": bd_2d.QB, "authorized": True, "created_at": time.time(),
         "authorized_by": "user execution contract BXY-P19..P22 (2026-11-01): P20 60,000 CPU-s, 28,800 s wall, <= 4 workers, <= 150 roots, <= 1,400 CPU-s / root"}
    if a["roots_left"] < len(json.loads((d / "DESIGN.json").read_text())["root_order"]):
        raise PermissionError("wave would exceed the 150-root ceiling")
    f.write_text(json.dumps(a, indent=1, sort_keys=True))
    return a


def worker(wave, k) -> None:
    with p16_paths():
        G.worker(wave, k)


def collect(wave) -> dict:
    import bxy_pmin_collect as PC
    d = wdir(wave)
    a = json.loads((d / "AUTHORIZATION.json").read_text())
    if a["design_sha256"] != PM.sha_file(d / "DESIGN.json") or a["runner_sha256"] != PM.sha_file("bxy_p20_k34.py") or a["teacher_hash"] != T.teacher_hash():
        raise PermissionError("wave authorization drift")
    if bd_2d.QB != PC.QB:
        raise PermissionError("per-query budget differs from P-min")
    sp = spent()
    L = {"cpu_s": LIMITS["cpu_s"] - sp["total_cpu_s"], "root_cpu_s": LIMITS["root_cpu_s"], "workers": LIMITS["workers"],
         "wall_s": LIMITS["wall_s"] - sp["total_wall_s"], "min_allow": LIMITS["min_allow"]}
    D = json.loads((d / "DESIGN.json").read_text())
    return PC.supervise(d, roots=D["root_order"], limits=L, cmd=lambda k: [sys.executable, "bxy_p20_k34.py", "worker", wave, k], est=None,
                        ramp=((0, 2), (2, 4)), gates=True)


def summarize(wave) -> dict:
    with p16_paths():
        sm = G.summarize(wave)
    R = roots_of(wave)
    for r in sm["rows"]:
        C = R[r["root"]]["construction"]
        r["K_cert"], r["family"] = C.get("K_cert"), C.get("family")
        short = [x for x in r["rows"] if x["f1"] and isinstance(r["verified_K"], int) and 0 < x["m"] < r["verified_K"]]
        r["shorter_undecided"] = sum(1 for x in short if x["x"] is None or x["y"] is None)
        r["verified_K_claim"] = r["verified_K"] if isinstance(r["verified_K"], int) and r["shorter_undecided"] == 0 else None
        strict = []
        for dsc in r["discordant"]:
            seqs = [[(a.split(">")[0], int(a.split(">")[1])) for a in o[0].split(".")] for o in dsc["orders"]]
            if all(sorted(s) == sorted(seqs[0]) and len(s) == len(seqs[0]) for s in seqs):
                strict.append(dsc)
        r["strict_discordant"] = strict
        r["neutral_ok"] = any(x["kind"] == "neutral_edit" and x["y"] is not None and x["y"] == r["y0"] for x in r["rows"])
    sm["spent_p20"] = spent()
    return sm


def readiness(waves) -> dict:
    rows = [r for w in waves for r in json.loads((wdir(w) / "SUMMARY.json").read_text())["rows"] if r["results"]]
    vk = lambda K: [r for r in rows if r["verified_K_claim"] == K]  # noqa: E731
    k3, k4 = vk(3), vk(4)
    tot = {"verified_K3": len(k3), "verified_K4": len(k4), "K3_mechanisms": len({r["family"] for r in k3}), "K4_mechanisms": len({r["family"] for r in k4}),
           "verified_K3_cert": sum(r["K_cert"] == 3 for r in k3), "verified_K4_cert": sum(r["K_cert"] == 4 for r in k4),
           "strict_order_K34": sum(len(r["strict_discordant"]) for r in rows if (r["K_geom"] or 0) >= 3),
           "harmful": sum(bool(r["harmful"]) for r in rows), "neutral": sum(r["neutral_ok"] for r in rows), "labelled_roots": len(rows)}
    ready = (tot["verified_K3"] >= READINESS["verified_K3"] and tot["verified_K4"] >= READINESS["verified_K4"] and tot["K3_mechanisms"] >= 2
             and tot["K4_mechanisms"] >= 2 and tot["strict_order_K34"] >= READINESS["strict_order_K34"] and tot["harmful"] >= READINESS["harmful"]
             and tot["neutral"] >= READINESS["neutral"])
    limited = tot["verified_K3"] >= LIMITED["verified_K3"] and tot["verified_K4"] >= LIMITED["verified_K4"]
    dec = "K34_DATA_READY" if ready else "K34_LIMITED_DATA" if limited else ("K4_PHYSICAL_DATA_NOT_ESTABLISHED" if tot["verified_K4"] < LIMITED["verified_K4"] else "K34_LIMITED_DATA_K3_SHORT")
    return {"targets": READINESS, "limited": LIMITED, "totals": tot, "decision": dec, "waves": list(waves)}


def prelabel_audit(wave) -> dict:
    with p16_paths():
        return G.prelabel_audit(wave)


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    cmd = sys.argv[1]
    if cmd == "generate":
        print(json.dumps({k: v for k, v in generate(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4).items() if k != "attempts"}))
    elif cmd == "audit":
        t0, w0 = time.process_time(), time.time()
        au = prelabel_audit(sys.argv[2])
        (wdir(sys.argv[2]) / "PRELABEL_AUDIT.json").write_text(json.dumps({"cpu_s": round(time.process_time() - t0, 1), "wall_s": round(time.time() - w0, 1), "roots": au}, indent=1, sort_keys=True))
        print(len(au))
    elif cmd == "freeze":
        print(freeze(sys.argv[2]))
    elif cmd == "authorize":
        print(json.dumps(authorize(sys.argv[2]), indent=1))
    elif cmd == "collect":
        print(json.dumps(collect(sys.argv[2]), indent=1, default=str))
    elif cmd == "worker":
        worker(sys.argv[2], sys.argv[3])
    elif cmd == "summarize":
        sm = summarize(sys.argv[2])
        (wdir(sys.argv[2]) / "SUMMARY.json").write_text(json.dumps(sm, indent=1, sort_keys=True, default=str))
        print(json.dumps({k: v for k, v in sm.items() if k != "rows"}, default=str)[:3000])
    elif cmd == "readiness":
        rd = readiness(sys.argv[2:])
        (OUT / "READINESS.json").write_text(json.dumps(rd, indent=1, sort_keys=True))
        print(json.dumps(rd))
