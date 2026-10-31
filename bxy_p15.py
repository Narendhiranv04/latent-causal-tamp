"""BXY-P15 outcome-blind harder-scene generator (BXY_GEN_V2), outcome-blind candidate catalogue, frozen pilot design, bounded pilot teacher
collection, and the frozen confirmatory-cohort plan (never generated here).

Scene construction (deterministic from (namespace, wave, slot)): source / goal / start pose as BD_GEN_V1 (bd_2d), then ONE reference planner
call on the target-only scene (bd_2d.t_goal, the unchanged Y teacher) gives the nominal target sweep. Intended blockers are drawn from the
sweep's mechanism pools (grasp / place / transfer), fixed structures off the sweep next to the anchors, distractors from role pools, and an
optional order trap (a distractor on a blocker's natural parking cell). No populated scene is ever planned during construction (no witness
chasing, no K selection, no rejection by any label): a root is rejected only for a geometric reason or an unverified target-only reference.
Candidate catalogue (outcome-blind, geometry only): per movable object the nearest parking cells off the sweep, an incorrect placement
inside the sweep, the free off-sweep cell nearest the q_ref arm footprint (connector-to-q_ref corridor), the cell of another movable object
(occupied destination); the phenomena are drained round-robin so each is represented under the per-root cap;
single moves, ordered pairs of sweep-relevant objects in both orders, the occupied-destination pair in both orders, the full relevant set
in two orders. Query design = P-min PMIN_DEV_MATCHED classes (y0, complete X / Y, reversal X, single-action omission X / Y) with F1.
Namespaces: pilot (development only) and confirm (reserved; generate() refuses it in this gate). Root / family ids are disjoint from BD_GEN_V1.
    python3 bxy_p15.py generate | freeze | authorize | collect | worker <root> | summarize"""
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
import bxy_pmin as PM
import bxy_teacher as T

OUT = Path("runs/approach_b/bxy_p15_v1")
GEN = "BXY_GEN_V2"
NS = {"pilot": "bxyg2pilot", "confirm": "bxyg2confirm"}
FACTORS = {"K_intent": [0, 1, 2, 3, 4], "mechanism": ["grasp", "place", "transfer", "mixed"], "distractors": ["0", "1-2", "3-4"],
           "distractor_role": ["near_T", "near_goal", "near_path", "far"], "source": ["near", "mid", "far"],
           "displacement": ["short", "medium", "long"], "trap": ["none", "occupied_destination"], "start_pose": ["home", "nonhome"]}
PILOT_K = {0: 3, 1: 5, 2: 8, 3: 8, 4: 6}                       # 30 pilot slots, K_intent emphasis on 2-4 (construction intent, not verified K)
MAX_CANDS, MAX_QUERIES = 12, 36
PILOT_LIMITS = {"cpu_s": 8000.0, "root_cpu_s": 800.0, "workers": 4, "wall_s": 7200.0, "min_allow": 30.0}
CONFIRM_PLAN = {"roots": 360, "K_intent": {0: 40, 1: 40, 2: 50, 3: 50, 4: 180}}       # set from the pilot construction realization only


# ------------------------------------------------------------------ ids and specs
def ids(ns, wave, slot, spec) -> dict:
    seed = int(bc.sha([GEN, NS[ns], wave, slot])[:8], 16)
    fam = "fam2-" + bc.sha([GEN, ns, {k: spec[k] for k in FACTORS}])[:10]
    G = bd_2d.env()
    return {"root_id": f"2d-{NS[ns]}-w{wave:04d}-s{slot:03d}", "parent_family_id": fam, "construction_seed": seed, "variant_id": "orig",
            "generator_version": GEN, "namespace": ns, "config_hash": G["config_hash"], "teacher_version": bd_2d.TEACHER_VERSION,
            "robot_protocol": G["protocol"], "label_protocol": bc.LABEL_PROTOCOL}


def specs(k_counts) -> list:
    """Deterministic factor assignment: K_intent by the requested counts, every other factor cycled with co-prime strides; invalid
    distractor levels (K + minimum > MAX_MOVABLE) step down."""
    ks = [k for k, n in sorted(k_counts.items()) for _ in range(n)]
    out = []
    for i, K in enumerate(ks):
        s = {"K_intent": K, "mechanism": FACTORS["mechanism"][(3 * i) % 4], "distractors": FACTORS["distractors"][(5 * i + 1) % 3],
             "distractor_role": FACTORS["distractor_role"][(7 * i + 2) % 4], "source": FACTORS["source"][(i + 1) % 3],
             "displacement": FACTORS["displacement"][(2 * i) % 3], "trap": FACTORS["trap"][i % 2], "start_pose": FACTORS["start_pose"][(i // 2) % 2]}
        while K + bc.N_DISTRACT[s["distractors"]][0] > bc.MAX_MOVABLE:
            s["distractors"] = FACTORS["distractors"][FACTORS["distractors"].index(s["distractors"]) - 1]
        if s["distractors"] == "0":
            s["distractor_role"] = "far"
        out.append(s)
    return out


# ------------------------------------------------------------------ outcome-blind construction
def footprint(q, margin=0.012) -> set:
    """Legal cells whose obstacle disc would touch the arm resting at q (links as capsules, base disc)."""
    import geometry as ge
    G = bd_2d.env()
    rob, r = G["robot"], G["cfg"]["suite"]["obstacle_radius_m"]
    J, _ = ge.fk(rob, q)
    out = set()
    for c in range(64):
        p = np.array(((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08))
        d = [np.linalg.norm(p - np.asarray(rob.base)) - rob.base_r]
        for i in range(3):
            a, b = J[i], J[i + 1]
            t = np.clip((p - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
            d.append(np.linalg.norm(p - (a + t * (b - a))) - rob.widths[i] / 2)
        if min(d) < r + margin:
            out.add(c)
    return out


def construct(spec, idd, store_out=None) -> dict:
    """One root (BD_GEN_V1 record schema, so the unchanged teacher and F1 apply). Raises bd_2d.Reject(reason)."""
    import p14_sweep_index as sx
    import p6_scenes as p6
    from scene import place_scene, scene_to_dict
    G = bd_2d.env()
    cfg, robot, rid = G["cfg"], G["robot"], idd["root_id"]
    rng = np.random.default_rng(idd["construction_seed"])
    t0 = time.process_time()
    lo, hi = bd_2d.DISP[spec["displacement"]]
    srcs = [x for x in G["region"][spec["source"]] if any(lo <= bd_2d.cheb(c, x) <= hi for c in G["valid"])]
    src = int(rng.choice(srcs))
    goal = int(rng.choice([c for c in G["valid"] if lo <= bd_2d.cheb(c, src) <= hi]))
    stratum = "S0" if spec["start_pose"] == "home" else str(rng.choice(["S1", "S2", "S3"]))
    q0 = tuple(p6.STRATA[stratum])
    empty = place_scene(cfg, rid, "empty", [src], [])
    empty = replace(empty, robot=replace(empty.robot, q_rad=q0))
    st, a, _ = bd_2d.t_goal({"scene": scene_to_dict(empty), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": rid + ":ref"}, {}, {"t0": src},
                            np.asarray(q0, float))
    ref_cpu = time.process_time() - t0
    if st != "VERIFIED":
        raise bd_2d.Reject(f"T_NOT_VERIFIED_IN_TARGET_ONLY_SCENE:{st}")
    sw = sx.swept_cells(robot, cfg, a)
    allsw = set().union(*map(set, sw.values()))
    foot = footprint(q0)
    ok = lambda c: c in G["valid"] and c not in (src, goal) and c not in foot  # noqa: E731
    pools = {"grasp": {c for ph in ("pregrasp", "approach", "close_attach") for c in sw[ph] if bd_2d.cheb(c, src) <= 2 and ok(c)},
             "place": {c for ph in ("carry", "release", "retreat") for c in sw[ph] if bd_2d.cheb(c, goal) <= 2 and ok(c)},
             "transfer": {c for ph in ("pregrasp", "carry") for c in sw[ph] if bd_2d.cheb(c, src) >= 2 and bd_2d.cheb(c, goal) >= 2 and ok(c)}}
    K, pick = spec["K_intent"], []
    for j in range(K):
        m = spec["mechanism"] if spec["mechanism"] != "mixed" else ("grasp", "place", "transfer")[j % 3]
        opts = sorted(pools[m] - set(pick)) or sorted(set().union(*pools.values()) - set(pick))
        if not opts:
            raise bd_2d.Reject("MECHANISM_POOL_TOO_SMALL")
        pick.append(int(rng.choice(opts)))
    fixed = []
    if K:
        anchors = {"grasp": [src], "place": [goal], "transfer": [src, goal], "mixed": [src, goal]}[spec["mechanism"]]
        nb = sorted({c for a_ in anchors for c in range(64) if bd_2d.cheb(c, a_) == 1 and c not in (src, goal) and c not in pick and c not in foot})
        off = [c for c in nb if c not in allsw]
        fixed = [int(x) for x in rng.choice(off, min(int(rng.integers(1, 3)), len(off)), replace=False)] if off else []
    lo_d, hi_d = bc.N_DISTRACT[spec["distractors"]]
    nd = min(int(rng.integers(lo_d, hi_d + 1)), bc.MAX_MOVABLE - K - (spec["trap"] != "none"))
    near_sw = {c for c in G["valid"] for s in allsw if bd_2d.cheb(c, s) == 1}
    role = {"near_T": [c for c in G["valid"] if 1 <= bd_2d.cheb(c, src) <= 2 and c not in allsw],
            "near_goal": [c for c in G["valid"] if 1 <= bd_2d.cheb(c, goal) <= 2 and c not in allsw],
            "near_path": [c for c in near_sw if c not in allsw], "far": [c for c in G["valid"] if bd_2d.cheb(c, src) >= 3 and bd_2d.cheb(c, goal) >= 3 and c not in allsw]}
    dpool = sorted({c for c in role[spec["distractor_role"]] if ok(c) and c not in pick and c not in fixed})
    if len(dpool) < min(lo_d, nd):
        raise bd_2d.Reject("DISTRACTOR_ROLE_POOL_TOO_SMALL")
    nd = min(nd, len(dpool))
    dis = [int(x) for x in rng.choice(dpool, nd, replace=False)] if nd else []
    trap = None
    if spec["trap"] == "occupied_destination" and pick:
        occ = set(pick + dis + fixed + [src])
        c0 = pick[0]
        park = sorted((c for c in G["valid"] if ok(c) and c not in occ and c not in allsw), key=lambda c: (math.dist(_xy(c), _xy(c0)), c))
        if not park:
            raise bd_2d.Reject("NO_PARKING_FOR_ORDER_TRAP")
        trap = park[0]
    movers = pick + dis + ([trap] if trap is not None else [])
    s = place_scene(cfg, rid, "orig", [src], movers + fixed)
    s = replace(s, robot=replace(s.robot, q_rad=q0))
    allids = [o.id for o in s.objects if o.id != "t0"]
    mov, fixed_ids = allids[:len(movers)], allids[len(movers):]
    roles = {i: ("intended_blocker" if j < K else "order_trap" if trap is not None and j == len(movers) - 1 else f"distractor:{spec['distractor_role']}")
             for j, i in enumerate(mov)}
    return {"ids": idd, "domain": bd_2d.DOMAIN, "generator": GEN, "spec": spec, "scene": scene_to_dict(s), "goal_cell": goal, "start_stratum": stratum,
            "q0": list(q0), "roles": roles, "fixed_ids": fixed_ids, "intended_blockers": mov[:K],
            "construction": {"reference_sweep": {k: sorted(v) for k, v in sw.items()}, "pools": {k: sorted(v) for k, v in pools.items()},
                             "q_ref_footprint": sorted(foot), "trap_cell": trap, "reference_planner_calls": 1, "reference_cpu_s": round(ref_cpu, 3),
                             "construction_cpu_s": round(time.process_time() - t0, 3),
                             "reference_witness": T.wid({k: np.asarray(v) for k, v in a.items()}, store_out)},
            "budget": {"per_query": bd_2d.QB}}


def _xy(c):
    return ((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08)


# ------------------------------------------------------------------ outcome-blind candidates and query design
def candidates(rec) -> list:
    """Deterministic geometric catalogue [(seq, kind)]: no teacher outcome, label or model score is read."""
    G = bd_2d.env()
    c0, sweep = bd.cells0(rec), set().union(*map(set, rec["construction"]["reference_sweep"].values()))
    src, goal, foot = c0["t0"], rec["goal_cell"], set(rec["construction"]["q_ref_footprint"])
    mov = sorted(rec["roles"])
    occ = set(c0.values())
    near = lambda c, cells: min(cells, key=lambda d: (math.dist(_xy(d), _xy(c)), d)) if cells else None  # noqa: E731
    free = [c for c in G["valid"] if c not in occ and c != goal]
    park_ok = [c for c in free if c not in sweep and c not in foot and bd_2d.cheb(c, src) >= 2 and bd_2d.cheb(c, goal) >= 2]
    rel = sorted((o for o in mov if c0[o] in sweep or any(bd_2d.cheb(c0[o], s) <= 1 for s in sweep)), key=lambda o: (math.dist(_xy(c0[o]), _xy(src)), o))
    anchor = [_xy(c) for c in foot] or [tuple(G["robot"].base)]               # q_ref arm footprint (or the base when it rests off-board)
    qref_dest = min((c for c in free if c not in sweep), key=lambda d: (min(math.dist(_xy(d), a_) for a_ in anchor), d), default=None)
    dest = {}
    for o in mov:
        parks = sorted(park_ok, key=lambda d: (math.dist(_xy(d), _xy(c0[o])), d))[:2]
        dest[o] = {"park1": parks[0] if parks else None, "park2": parks[1] if len(parks) > 1 else None,
                   "wrong": near(c0[o], [c for c in free if c in sweep and c != src]), "qref": qref_dest,
                   "occupied": near(c0[o], [c0[p] for p in mov if p != o])}
    groups = collections.defaultdict(list)                                        # one queue per phenomenon, drained round-robin
    add = lambda g, seq, kind: groups[g].append(([(o, int(d)) for o, d in seq], kind)) if all(d is not None for _, d in seq) else None  # noqa: E731
    for o in rel:
        add("park", [(o, dest[o]["park1"])], "single_park")
        add("incorrect", [(o, dest[o]["wrong"])], "single_incorrect_placement")
        add("connector", [(o, dest[o]["qref"])], "single_qref_corridor_destination")
        p = next((x for x in mov if c0[x] == dest[o]["occupied"]), None)
        if p is not None:
            add("occupied", [(p, dest[p]["park1"]), (o, dest[o]["occupied"])], "occupied_destination_pair")
            add("occupied", [(o, dest[o]["occupied"]), (p, dest[p]["park1"])], "occupied_destination_pair_wrong_order")
    for a_, b_ in itertools.combinations(rel[:4], 2):
        add("pair", [(a_, dest[a_]["park1"]), (b_, dest[b_]["park1"])], "pair_park")
        add("pair", [(b_, dest[b_]["park1"]), (a_, dest[a_]["park1"])], "pair_park_reversed")
    if len(rel) >= 3:
        full = [(o, dest[o]["park1"]) for o in rel[:6]]
        add("full", full, "full_relevant")
        add("full", full[::-1], "full_relevant_reversed")
    for o in mov:
        if o not in rel:
            add("unnecessary", [(o, dest[o]["park1"])], "unnecessary_displacement")
    order = ("park", "pair", "incorrect", "occupied", "full", "connector", "unnecessary")
    out, q = [], {g: list(groups[g]) for g in order}
    while any(q.values()):
        for g in order:
            n = 2 if g in ("pair", "occupied", "full") else 1                   # ordered variants stay together
            out += q[g][:n]
            q[g] = q[g][n:]
    seen, uniq = set(), []
    for seq, kind in out:
        s = bd.sig(seq)
        if s not in seen and len({o for o, _ in seq}) == len(seq) and len(seq) + 1 <= bc.MAX_ACTIONS:
            seen.add(s)
            uniq.append((seq, kind))
    return uniq


def root_design(k, rec) -> dict:
    """P-min PMIN_DEV_MATCHED classes over the outcome-blind catalogue, truncated deterministically (catalogue priority order) so that a root
    never exceeds MAX_CANDS complete candidates or MAX_QUERIES queries."""
    Q, bad, cat = {}, {}, []
    PM._add(Q, bad, k, rec, "y", [], "y0")
    for seq, kind in candidates(rec):
        if len(cat) >= MAX_CANDS:
            break
        trial_Q, trial_bad = json.loads(json.dumps(Q)), json.loads(json.dumps(bad))
        PM._add(trial_Q, trial_bad, k, rec, "x", seq, "complete")
        PM._add(trial_Q, trial_bad, k, rec, "y", seq, "complete")
        if len(seq) >= 2:
            PM._add(trial_Q, trial_bad, k, rec, "x", seq[::-1], "reversal")
            for t in range(len(seq)):
                om = [a for i, a in enumerate(seq) if i != t]
                PM._add(trial_Q, trial_bad, k, rec, "x", om, "omission")
                PM._add(trial_Q, trial_bad, k, rec, "y", om, "omission")
        if len(trial_Q) > MAX_QUERIES:
            continue
        Q, bad = trial_Q, trial_bad
        f = F1.screen(rec, seq)
        cat.append({"seq": [list(a) for a in seq], "kind": kind, "sig": bd.sig(seq), "f1_complete_ok": f["complete_ok"], "f1_x_ok": f["x_ok"], "f1_y_ok": f["y_ok"]})
    return {"catalogue": cat, "queries": dict(sorted(Q.items())), "f1_screened": dict(sorted(bad.items()))}


# ------------------------------------------------------------------ pilot generation, freezing, collection
def generate(ns="pilot", out=OUT) -> dict:
    if ns != "pilot":
        raise PermissionError("only the development pilot namespace may be generated in BXY-P15 (the confirmatory cohort is reserved)")
    out = Path(out)
    (out / "pilot" / "roots").mkdir(parents=True, exist_ok=True)
    attempts = []
    for slot, sp_ in enumerate(specs(PILOT_K)):
        idd = ids(ns, 0, slot, sp_)
        row = {"slot": slot, "spec": sp_, "root_id": idd["root_id"], "family": idd["parent_family_id"], "seed": idd["construction_seed"]}
        t0 = time.process_time()
        try:
            rec = construct(sp_, idd, out / "pilot")
        except bd_2d.Reject as e:
            attempts.append(row | {"accepted": False, "reject": str(e), "cpu_s": round(time.process_time() - t0, 3)})
            continue
        d = root_design(idd["root_id"], rec)
        rec["catalogue_v2"], rec["design_v2"] = d["catalogue"], {"queries": d["queries"], "f1_screened": d["f1_screened"]}
        (out / "pilot" / "roots" / f"{idd['root_id']}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
        attempts.append(row | {"accepted": True, "cpu_s": round(time.process_time() - t0, 3), "candidates": len(d["catalogue"]),
                               "queries": len(d["queries"]), "x": sum(q["side"] == "x" for q in d["queries"].values()),
                               "y": sum(q["side"] == "y" for q in d["queries"].values()), "f1_screened": len(d["f1_screened"])})
    man = {"generator": GEN, "namespace": ns, "attempts": attempts, "accepted": sum(a["accepted"] for a in attempts),
           "construction_cpu_s": round(sum(a["cpu_s"] for a in attempts), 3), "t": time.time()}
    (out / "PILOT_GENERATION.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    return man


def pilot_roots(out=OUT) -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted((Path(out) / "pilot" / "roots").glob("*.json"))}


def freeze(out=OUT) -> str:
    """PILOT_DESIGN.json: every accepted root's record hash, catalogue and query worklist; written once, before any query of it is sent."""
    out = Path(out)
    R = pilot_roots(out)
    D = {"version": "BXY_P15_PILOT_DESIGN_V1", "generator": GEN, "teacher_hash": T.teacher_hash(), "teacher_policy": T.TEACHER, "f1": F1.VERSION,
         "per_query_budget": bd_2d.QB, "classes": "y0 + complete + reversal + omission (P-min PMIN_DEV_MATCHED)", "max_cands": MAX_CANDS,
         "max_queries": MAX_QUERIES, "root_order": sorted(R), "roots": {k: {"record_sha256": bc.sha(r), "catalogue": r["catalogue_v2"],
                                                                             "queries": r["design_v2"]["queries"]} for k, r in R.items()},
         "generation_sha256": PM.sha_file(out / "PILOT_GENERATION.json")}
    f = out / "PILOT_DESIGN.json"
    txt = json.dumps(D, indent=1, sort_keys=True)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("pilot design already frozen with different content")
    if (out / "results").exists() and any((out / "results").iterdir()):
        raise RuntimeError("teacher results exist: the pilot design must be frozen before any query")
    f.write_text(txt)
    return PM.sha_file(f)


def worklist(D) -> dict:
    return {k: [dict(q, key=key) for key, q in sorted(D["roots"][k]["queries"].items(), key=lambda kv: (kv[1]["side"], kv[0]))] for k in D["root_order"]}


def worker(k, out=OUT) -> None:
    import bxy_pmin_collect as PC
    out = Path(out)
    D = json.loads((out / "PILOT_DESIGN.json").read_text())
    rec = pilot_roots(out)[k]
    if bc.sha(rec) != D["roots"][k]["record_sha256"]:
        raise RuntimeError(f"{k}: record differs from the frozen pilot design")
    E, cache, d = T.env(), {}, out / "results" / k
    d.mkdir(parents=True, exist_ok=True)
    for i, q in enumerate(worklist(D)[k]):
        f = d / f"{i:04d}.{q['side']}.json"
        if f.exists():
            continue
        m = d / f"{i:04d}.{q['side']}.inprogress"
        PC.jw(m, {"started": time.time(), "key": q["key"]})
        seq = [tuple(a) for a in q["seq"]]
        row = T.x_query(E, k, rec, seq, cache, out) if q["side"] == "x" else PM.y_query_counted(E, k, rec, seq, cache, out, None)
        if row.get(f"{q['side']}_key") != q["key"]:
            row = {"root": k, "attempted": True, "observed": False, "y": None, "teacher_status": "IDENTITY_MISMATCH", "got": row.get(f"{q['side']}_key")}
        PC.jw(f, row | {"item": i, "side": q["side"], "design_key": q["key"], "classes": q["classes"], "teacher_hash": T.teacher_hash(), "runner": GEN})
        m.unlink()


def authorize(out=OUT) -> dict:
    out = Path(out)
    f = out / "AUTHORIZATION_PILOT.json"
    if f.exists():
        raise FileExistsError(str(f))
    a = {"gate": "BXY-P15", "scope": "optional development-pilot teacher collection of the frozen pilot design only (<= 30 new roots, namespace pilot)",
         "limits": PILOT_LIMITS, "workers": PILOT_LIMITS["workers"], "per_query_budget": bd_2d.QB, "pilot_design_sha256": PM.sha_file(out / "PILOT_DESIGN.json"),
         "generation_construction_cpu_s": json.loads((out / "PILOT_GENERATION.json").read_text())["construction_cpu_s"] + (
             json.loads((out / "SUPERSEDED_GENERATION.json").read_text())["superseded_generation_cpu_s"] if (out / "SUPERSEDED_GENERATION.json").exists() else 0.0),
         "runner_sha256": PM.sha_file("bxy_p15.py"), "teacher_hash": T.teacher_hash(), "authorized": True, "created_at": time.time(),
         "authorized_by": "user execution contract BXY-P13/P14/P15 (2026-11-01): <= 8,000 additional aggregate CPU-s, 4 workers, 7,200 s wall, "
                          "P-min per-query budgets as strict upper bounds"}
    f.write_text(json.dumps(a, indent=1, sort_keys=True))
    return a


def collect(out=OUT) -> dict:
    import bxy_pmin_collect as PC
    out = Path(out)
    a = json.loads((out / "AUTHORIZATION_PILOT.json").read_text())
    if a["pilot_design_sha256"] != PM.sha_file(out / "PILOT_DESIGN.json") or a["runner_sha256"] != PM.sha_file("bxy_p15.py") or a["teacher_hash"] != T.teacher_hash():
        raise PermissionError("pilot authorization drift")
    if bd_2d.QB != PC.QB:
        raise PermissionError("per-query budget differs from P-min")
    L = dict(PILOT_LIMITS)
    L["cpu_s"] = PILOT_LIMITS["cpu_s"] - a["generation_construction_cpu_s"]           # construction reference calls count against the 8,000
    D = json.loads((out / "PILOT_DESIGN.json").read_text())
    return PC.supervise(out, roots=D["root_order"], limits=L, cmd=lambda k: [sys.executable, "bxy_p15.py", "worker", k], est=None,
                        ramp=((0, 2), (2, 4)), gates=True)


def summarize(out=OUT) -> dict:
    """Realized pilot outcomes (development only): per root Y0, verified repairs, verified K (fewest moves among verified complete
    candidates), costs, censoring; per construction factor."""
    out = Path(out)
    D = json.loads((out / "PILOT_DESIGN.json").read_text())
    R = pilot_roots(out)
    gen = json.loads((out / "PILOT_GENERATION.json").read_text())
    rows = []
    for k in D["root_order"]:
        res = {}
        for f in sorted((out / "results" / k).glob("*.json")) if (out / "results" / k).exists() else []:
            r = json.loads(f.read_text())
            res[r["design_key"]] = r
        q = D["roots"][k]["queries"]
        y = lambda key: (res.get(key) or {}).get("y")  # noqa: E731
        y0 = y(T.ykey(k, R[k], []))
        ver = []
        for c in D["roots"][k]["catalogue"]:
            seq = [tuple(a) for a in c["seq"]]
            if c["f1_complete_ok"] and y(T.xkey(k, R[k], seq)) == 1 and y(T.ykey(k, R[k], seq)) == 1:
                ver.append(c)
        status = collections.Counter((r.get("teacher_status") or "NONE") for r in res.values())
        rows.append({"root": k, "spec": R[k]["spec"], "queries": len(q), "results": len(res), "censored": status.get("CENSORED", 0),
                     "not_attempted": len(q) - len(res), "y0": y0, "verified_repairs": len(ver),
                     "verified_K": "UNOBSERVED_Y0" if y0 is None else 0 if y0 == 1 else (min(len(c["seq"]) for c in ver) if ver else None),
                     "kinds_verified": sorted({c["kind"] for c in ver}), "cpu_s": round(sum((r.get("process_cpu_s") or 0.0) for r in res.values()), 1),
                     "x_neg": collections.Counter(r.get("negative_kind") for r in res.values() if r.get("side") == "x" and r.get("y") == 0),
                     "y_neg": collections.Counter(r.get("negative_kind") for r in res.values() if r.get("side") == "y" and r.get("y") == 0),
                     "statuses": dict(status)})
    led = [json.loads(x) for x in (out / "LEDGER.jsonl").read_text().splitlines() if x.strip()] if (out / "LEDGER.jsonl").exists() else []
    fin = [e for e in led if e["event"] == "finish"]
    by = lambda f: {str(v): collections.Counter(str(r["verified_K"]) for r in rows if r["spec"][f] == v) for v in FACTORS[f]}  # noqa: E731
    return {"roots": len(rows), "attempted_slots": len(gen["attempts"]), "rejected": [a for a in gen["attempts"] if not a["accepted"]],
            "verified_K": dict(collections.Counter(str(r["verified_K"]) for r in rows)), "by_K_intent": by("K_intent"), "by_trap": by("trap"),
            "by_mechanism": by("mechanism"), "collection_cpu_s": round(sum(e["cpu_s"] for e in fin), 1), "construction_cpu_s": gen["construction_cpu_s"],
            "worker_exits": dict(collections.Counter(str(e["exit"]) for e in fin)), "rows": rows}


def confirm_plan(pilot: dict | None = None) -> dict:
    """The frozen confirmatory-cohort plan (NOT generated, inspected or evaluated in BXY-P15). Composition is fixed by construction intent and
    namespace seeds; no model output enters it."""
    return {"version": "BXY_P15_CONFIRM_PLAN_V1", "namespace": NS["confirm"], "generator": GEN, "roots": CONFIRM_PLAN["roots"],
            "K_intent": CONFIRM_PLAN["K_intent"], "factor_assignment": "bxy_p15.specs(CONFIRM_PLAN['K_intent']) (deterministic cycling)",
            "waves": "wave 1..; a rejected slot is retried with wave + 1 for the same slot up to 5 times, every attempt recorded; the slot is "
            "dropped (not replaced by a different spec) after 5 rejections", "query_design": "bxy_p15.root_design (outcome-blind catalogue, P-min classes)",
            "teacher": {"hash": T.teacher_hash(), "per_query_budget": bd_2d.QB}, "stop_rule": "fixed root count; no interim look at labels or model outputs",
            "custody": "generated only after every model, rule and metric of the confirmatory analysis is frozen; disjoint from BD_GEN_V1, the 34 "
            "exposed test roots and the pilot namespace; pilot roots never enter it", "precision": "with n_inf initially infeasible roots, a paired "
            "difference of corrective success has 95 % half-width <= 1.96 * 0.5 / sqrt(n_inf) (worst case): n_inf = 150 -> 0.080, 200 -> 0.069",
            "pilot_evidence_used": "construction feasibility, rejection rate, verified-K realization and teacher cost only (no model was run on a pilot root)",
            "pilot_summary": {k: pilot[k] for k in ("roots", "verified_K", "by_K_intent", "collection_cpu_s", "construction_cpu_s")} if pilot else None,
            "expected_from_pilot": expected(pilot) if pilot else None}


def expected(pilot) -> dict:
    """Plan-level expectations from the pilot's per-K_intent realization (development pilot, very small n per level; indicative only)."""
    rate = {}
    for k, c in pilot["by_K_intent"].items():
        n = sum(c.values())
        rate[k] = {"n_pilot": n, "infeasible": (n - c.get("0", 0)) / n, "K>=2": sum(v for kk, v in c.items() if kk.isdigit() and int(kk) >= 2) / n,
                   "no_verified_repair": c.get("None", 0) / n}
    comp = CONFIRM_PLAN["K_intent"]
    exp = {m: sum(comp[int(k)] * r[m] for k, r in rate.items()) for m in ("infeasible", "K>=2", "no_verified_repair")}
    return {"pilot_rates": rate, "expected_counts": exp, "half_width_95_worst_case": 1.96 * 0.5 / max(exp["infeasible"], 1) ** 0.5,
            "cost_cpu_s_per_root_pilot_mean": pilot["collection_cpu_s"] / pilot["roots"]}


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "generate":
        print(json.dumps({k: v for k, v in generate().items() if k != "attempts"}))
    elif cmd == "freeze":
        print(freeze())
    elif cmd == "authorize":
        print(json.dumps(authorize(), indent=1))
    elif cmd == "collect":
        print(json.dumps(collect(), indent=1, default=str))
    elif cmd == "worker":
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        worker(sys.argv[2])
    elif cmd == "plan":
        f = OUT / "CONFIRM_PLAN.json"
        txt = json.dumps(confirm_plan(json.loads((OUT / "PILOT_SUMMARY.json").read_text())), indent=1, sort_keys=True, default=str)
        if f.exists() and f.read_text() != txt:
            raise FileExistsError("confirmatory plan already frozen with different content")
        f.write_text(txt)
        print(PM.sha_file(f))
    elif cmd == "summarize":
        s = summarize()
        (OUT / "PILOT_SUMMARY.json").write_text(json.dumps(s, indent=1, sort_keys=True, default=str))
        print(json.dumps({k: v for k, v in s.items() if k != "rows"}, default=str))
