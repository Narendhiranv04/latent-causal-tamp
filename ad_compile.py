"""Approach D G2a: OFFLINE motion compiler and compiled-template catalog (approachD_G2_offline_only_instructions_v1_1 §2, §6 G2a).

Runs before inference and may use IK, IK-tracked lines and the certified planner (skill / motion / planner). A template is a complete
home -> home record (pregrasp, approach, close/attach, carry, release, retreat, return_home) for one ABSOLUTE (src, dst) pair, compiled in
a generic fixture that holds nothing but the moved disc (no root, split or scene geometry) and validated there by the independent replay
certifier. Origins:
  EXACT_CELL_WITNESS  a stored witness at the same cells, completed with offline home connectors (its own path is kept verbatim);
  BASE_ROTATION       a stored witness rotated about the base (q1 + psi); exact only when one psi maps BOTH endpoints. On this lattice no
                      valid-cell pair has such a partner (audit), so it is exercised on a controlled off-lattice fixture only;
  FAMILY_RETARGET     a G1 relative-family mode: its seed's pick / place elbow branches and base-rotated grasp directions, snapped to the
                      declared grasp set and realised at the new cells with offline IK, certified lines and connectors;
  DIRECT_OFFLINE      the declared grasp set in the planner's own preference order ('order') or spread over branch classes ('spread'),
                      no relative seed: the unseeded baselines;
  ENTRY               root start q -> home, nothing held (the canonical-home contract's precompiled entry actions).
Every attempt is binary (compiled 1 / 0); a 0 keeps negative_kind and termination as metadata, never a third label, never a proof that
no motion exists. Selection of which mode templates to try at runtime belongs to G1 retrieval (ad_runtime), not to this module."""
from __future__ import annotations

import collections
import copy
import hashlib
import json
import math
import os
import platform
import time
from pathlib import Path

import numpy as np

import config as cf
import geometry as ge
import motion as mo
import planner as pn
import skill as sk
from scene import place_scene

VERSION, OUT = "AD_COMPILER_V1", Path("runs/approach_d/g2a")
KEYS = {"version", "fixture", "contract", "budget_id", "planner_max_nodes", "templates_per_mode", "direct_k", "max_grasp_shift_deg"}
NEG = ("CERTIFIED", "TIMEOUT", "NO_PLAN_FOUND", "OTHER_FAILURE")


def ccfg(path="approach_d.toml") -> dict:
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["compiler"]
    if set(c) != KEYS or c["version"] != VERSION or c["contract"] != "Q_HOME" or c["fixture"] != "GENERIC_EMPTY_WORKSPACE":
        raise ValueError(f"invalid [compiler]: {sorted(set(c) ^ KEYS)}")
    return c


def setup(c=None):
    """config.toml (unchanged) with the declared compile budget: node budgets decide, no wall-clock adjudication (deterministic)."""
    c = c or ccfg()
    cfg = copy.deepcopy(cf.load_config("config.toml"))
    cfg["planner2d"]["max_nodes"], cfg["planner2d"]["max_wall_seconds"] = c["planner_max_nodes"], 1e9
    return cfg, ge.make_robot(cfg), sk.params(cfg)


def fixture(cfg, src=None):
    """Generic compile fixture: the moved disc at src (t0) and nothing else; robot at home."""
    return place_scene(cfg, "ad_fixture", "empty" if src is None else f"c{src:02d}", [] if src is None else [src], [])


def grasp(a) -> tuple:
    """((pick phi, pick branch), (place phi, place branch)) of a stored record: tool axis q1+q2+q3 and elbow sign at close and release."""
    ph, q = [str(x) for x in a["phase"]], np.asarray(a["q"], float)
    return tuple((float(np.sum(q[ph.index(n)]) % (2 * math.pi)), int(np.sign(q[ph.index(n)][1]))) for n in ("close_attach", "release"))


def _ang(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def screens(cfg, robot, p, src, dst):
    """Declared grasp-set screens in the fixture (offline IK): passing picks and places, exactly as skill.plan_skill screens them."""
    s = fixture(cfg, src)
    o, dest = s.get("t0"), s.lattice.center(dst)
    picks = sk.screen_pick(robot, mo.checkers(robot, s, "t0", None, None, p["delta"], p["eps"]), o.xy_m, o.radius_m, p)
    ck = mo.checkers(robot, s, "t0", dest, (robot.grasp_x, 0.0), p["delta"], p["eps"])
    places = sk.screen_place(robot, ck, dest, (robot.grasp_x, 0.0), 2 * o.radius_m, p)
    return s, [c for c in picks if c.stage == "OK"], [c for c in places if c.stage == "OK"], picks + places


def gkey(pick, place):
    return (round(pick.phi, 9), pick.branch, round(place.phi, 9), place.branch)


def direct_pairs(good, goodp, home, k, how="order"):
    """Unseeded baselines over the declared grasp set. 'order': plan_skill's own (pick, place) preference order. 'spread': round-robin over
    (pick branch, place branch) classes in that order, skipping a pair within 30 deg at both ends of one already taken in its class."""
    branches = {c.branch for c in goodp}
    seq = [(a, b) for a in sorted(good, key=lambda c: (c.branch not in branches, np.linalg.norm(c.line[0] - home)))
           for b in sorted(goodp, key=lambda c: (c.branch != a.branch, np.linalg.norm(c.q_end - a.q_end)))]
    if how == "order":
        return seq[:k]
    cls = collections.OrderedDict()
    for a, b in seq:
        cls.setdefault((a.branch, b.branch), []).append((a, b))
    out, taken = [], collections.defaultdict(list)
    while len(out) < k and any(cls.values()):
        for c, pairs in cls.items():
            while pairs:
                a, b = pairs.pop(0)
                if all(_ang(a.phi, x.phi) > math.radians(30) or _ang(b.phi, y.phi) > math.radians(30) for x, y in taken[c]):
                    out.append((a, b))
                    taken[c].append((a, b))
                    break
            if len(out) == k:
                break
    return out


def seeded_pair(good, goodp, seed, psi, max_shift):
    """Snap a seed grasp, rotated by psi about the base, to the declared set on the SAME elbow branch at pick and at place."""
    (pp, pb), (lp, lb) = seed
    a, b = [c for c in good if c.branch == pb], [c for c in goodp if c.branch == lb]
    if not a or not b:
        return None, "SEED_BRANCH_UNAVAILABLE", None
    pick = min(a, key=lambda c: (_ang(c.phi, pp + psi), c.phi))
    place = min(b, key=lambda c: (_ang(c.phi, lp + psi), c.phi))
    shift = (_ang(pick.phi, pp + psi), _ang(place.phi, lp + psi))
    return ((pick, place), None, shift) if max(shift) <= max_shift + 1e-9 else (None, "SEED_GRASP_UNAVAILABLE", shift)


def _neg(plan):
    return "CERTIFIED" if plan.status == ge.COLLISION else "TIMEOUT" if plan.reason.startswith("BUDGET_EXHAUSTED") else "NO_PLAN_FOUND"


def realize(cfg, robot, p, s, dst, pick, place, key):
    """Offline: certified connectors home -> pregrasp and retreat -> home, carry by guide line / pose-space RRT on one branch (else joint
    RRT), then skill._finish's independent replay. -> (arrays | None, termination, negative_kind, plans)."""
    pc, home, gopen, dest = cfg["planner2d"], np.array(robot.q_home), robot.open_gap, s.lattice.center(dst)
    ck0 = mo.checkers(robot, s, "t0", None, None, p["delta"], p["eps"])
    ck = mo.checkers(robot, s, "t0", dest, (robot.grasp_x, 0.0), p["delta"], p["eps"])
    same, plans = pick.branch == place.branch, []
    guide = mo.carry_line(robot, s.get("t0").xy_m, dest, pick.local, pick.phi, place.phi, pick.branch, p["line_step_m"],
                          p["max_ik_jump_rad"])[0] if same else None
    pose = ((*s.get("t0").xy_m, pick.phi), (*dest, place.phi), pick.local, pick.branch, p["line_step_m"], p["max_ik_jump_rad"]) if same else None
    for label, chk, a, b, gap, g, ps in (("pregrasp", ck0[("start", False)], home, pick.line[0], gopen, None, None),
                                         ("carry", ck[("held", False)], pick.q_end, place.q_end, pick.gap, guide, pose),
                                         ("return_home", ck[("placed", False)], place.line[-1], home, gopen, None, None)):
        r = pn.plan(chk, a, b, gap, pc, p["evals"], f"{key}/{label}", True, g, ps)
        plans.append(r)
        if r.status != ge.CLEAR:
            return None, f"CONNECTOR_{label.upper()}:{r.reason}", _neg(r), plans
    res = sk._finish(sk.SkillResult(sk.UNRESOLVED, ""), robot, s, "t0", dest, (plans[0], pick, plans[1], place, plans[2]), cfg)
    if res.status != sk.VERIFIED:
        return None, res.termination, "OTHER_FAILURE", plans
    return res.traj.arrays(), "WITNESS_RECHECKED", None, plans


def complete(cfg, robot, p, s, oid, a, key):
    """Offline: wrap a stored relocation core (kept verbatim) in certified home connectors in fixture s. -> (arrays | None, term, neg)."""
    home, q, gap, ph = np.array(robot.q_home), np.asarray(a["q"], float), np.asarray(a["gap"], float), [str(x) for x in a["phase"]]
    held, place = tuple(np.asarray(a["held_local"], float)), tuple(np.asarray(a["place_xy"], float))
    ck = mo.checkers(robot, s, oid, place, held, p["delta"], p["eps"])
    legs = {}
    for label, chk, x, y, g in (("pregrasp", ck[("start", False)], home, q[0], gap[0]),
                                ("return_home", ck[("placed", False)], q[-1], home, gap[-1])):
        r = None if np.array_equal(x, y) else pn.plan(chk, x, y, g, cfg["planner2d"], p["evals"], f"{key}/{label}", True)
        if r is not None and r.status != ge.CLEAR:
            return None, f"CONNECTOR_{label.upper()}:{r.reason}", _neg(r)
        legs[label] = [] if r is None else r.path[1:]
    t = mo.Trajectory(oid, held_local=held, place_xy=place)
    t.add(home, gap[0], None)
    for w in legs["pregrasp"][:-1]:
        t.add(w, gap[0], "pregrasp")
    for i in range(1, len(q)) if not legs["pregrasp"] else range(len(q)):
        t.add(q[i], gap[i], "pregrasp" if i == 0 else ph[i - 1])
    for w in legs["return_home"]:
        t.add(w, gap[-1], "return_home")
    return t.arrays(), "COMPLETED", None


def rotate(robot, a, psi):
    """Exact base-rotation transfer of a stored record: q1 + psi moves every body (and the held disc) rigidly about the base. None if any
    waypoint leaves the joint limits. The rotated record is still certified in its new scene (the support does not rotate with it)."""
    q = np.array(a["q"], float)
    q[:, 0] += psi
    if not all(ge.within_limits(robot, w) for w in q):
        return None
    b, c, s = np.asarray(robot.base, float), math.cos(psi), math.sin(psi)
    return {**a, "q": q, "place_xy": (np.asarray(a["place_xy"], float) - b) @ np.array([[c, s], [-s, c]]) + b}


def validate(cfg, robot, p, s, oid, a, dst_xy) -> dict:
    """Template acceptance in its compile fixture: record consistency, every segment certified, exact home start and end, placement."""
    home = np.array(robot.q_home)
    try:
        vs = mo.certify_trajectory(robot, s, oid, a, p["delta"], p["eps"], p["evals"])
    except ValueError as e:
        return {"ok": False, "why": f"RECORD:{e}"}
    bad = [v for v in vs if v.status != ge.CLEAR]
    err = float(np.linalg.norm(np.asarray(a["place_xy"]) - np.asarray(dst_xy)))
    ok = not bad and np.array_equal(a["q"][0], home) and np.array_equal(a["q"][-1], home) and err <= p["release_tol"]
    return {"ok": bool(ok), "why": None if ok else (f"SEGMENT:{bad[0].status}:{bad[0].pair}" if bad else "HOME_OR_PLACE"),
            "segments": len(vs), "place_error_m": err}


def sweep(robot, cfg, a) -> dict:
    """Absolute swept cells per phase of the ACTUAL compiled joint path (p14 swept_cells per phase; return_home included)."""
    import p14_sweep_index as sx
    ph, out = [str(x) for x in a["phase"]], {}
    for name in dict.fromkeys(ph):
        i = [k for k, x in enumerate(ph) if x == name]
        sub = {"q": a["q"][i[0]:i[-1] + 2], "gap": a["gap"][i[0]:i[-1] + 2], "phase": np.array(["pregrasp"] * len(i)),
               "attached": a["attached"][i[0]:i[-1] + 1], "held_local": a["held_local"]}
        out[name] = sorted(set().union(*map(set, sx.swept_cells(robot, cfg, sub).values())))
    return out


def tid(a, src, dst) -> str:
    h = hashlib.sha256(f"{VERSION}|{src}|{dst}".encode())
    for k in ("q", "gap"):
        h.update(np.round(np.asarray(a[k], float), 9).tobytes())
    h.update("|".join(map(str, a["phase"])).encode())
    return h.hexdigest()[:16]


HW = {"machine": platform.machine(), "python": platform.python_version(), "cpus": os.cpu_count()}


def record(cfg, robot, origin, kind, src, dst, a, lineage, cpu, extra=None) -> dict:
    import ordered as od
    sw = sweep(robot, cfg, a)
    ph = [str(x) for x in a["phase"]]
    return {"id": tid(a, src, dst), "compiler_version": VERSION, "origin": origin, "kind": kind, "src": src, "dst": dst,
            "radius": cfg["suite"]["obstacle_radius_m"], "object_class": "disc", "fixture": "GENERIC_EMPTY_WORKSPACE", "contract": "Q_HOME",
            "q_start": np.asarray(a["q"][0]).tolist(), "q_end": np.asarray(a["q"][-1]).tolist(),
            "grasp": grasp(a) if "close_attach" in ph else None, "waypoints": len(a["q"]), "phases": dict(collections.Counter(ph)),
            "travel_J": od.joint_travel(robot, [a])["J"], "swept_by_phase": sw, "swept": sorted(set().union(*map(set, sw.values()))),
            "sweep_hash": cf.stable_hash(sw), "lineage": lineage, "compile_cpu_s": cpu, **(extra or {})}


def attempt(origin, src, dst, lineage, ok, term, neg, cpu, tpl_id=None, c=None) -> dict:
    """Binary compile outcome under budget B (AD_BINARY_BUDGET_V1 semantics): 1 = compiled and independently re-certified, else 0."""
    assert ok or neg in NEG
    return {"label_protocol": "AD_BINARY_BUDGET_V1", "origin": origin, "src": src, "dst": dst, "lineage": lineage, "compiled": int(ok),
            "negative_kind": None if ok else neg, "termination_reason": term, "budget_id": (c or {}).get("budget_id", "B_COMPILE_V1"),
            "cpu_s": cpu, "hardware": HW, "template_id": tpl_id}


# ------------------------------------------------------------------ one offline compile job (pool worker; sees cells and seed grasps only)
def compile_job(job) -> dict:
    """job: {src, dst, kind, direct_k, seeds: [{mode, ref, grasp, psi, residual_m, ...}], exact: [{file, index, ...}]}. No scene, root or
    split geometry enters: the fixture is generic and seeds arrive as (grasp, psi) only. -> {'templates': [(row, arrays)], 'attempts'}."""
    import g4d_run as gr
    c = ccfg()
    cfg, robot, p = setup(c)
    src, dst, out, seen = job["src"], job["dst"], {"templates": [], "attempts": []}, {}
    t0 = time.process_time()
    s, good, goodp, allc = screens(cfg, robot, p, src, dst)
    scr_cpu = time.process_time() - t0
    out["screen"] = {"picks_ok": len(good), "places_ok": len(goodp), "rejections": sk.count_reasons(allc), "cpu_s": scr_cpu}

    def emit(origin, lineage, pair=None, core=None):
        c0 = time.process_time()
        if pair is not None and gkey(*pair) in seen:          # identical declared grasp pair -> identical deterministic template
            tpl, neg0 = seen[gkey(*pair)]
            out["attempts"].append(attempt(origin, src, dst, lineage, tpl is not None, "DUPLICATE_OF_COMPILED" if tpl else "DUPLICATE_OF_FAILED",
                                           neg0, 0.0, tpl, c))
            return tpl
        if pair is not None:
            a, term, neg, _ = realize(cfg, robot, p, s, dst, *pair, f"{VERSION}/{src}>{dst}/{gkey(*pair)}")
        else:
            a, term, neg = complete(cfg, robot, p, s, "t0", core, f"{VERSION}/{src}>{dst}/{lineage['witness']}")
        v = validate(cfg, robot, p, s, "t0", a, s.lattice.center(dst)) if a is not None else None
        if a is not None and not v["ok"]:
            a, term, neg = None, f"VALIDATION:{v['why']}", "OTHER_FAILURE"
        cpu = time.process_time() - c0
        row = record(cfg, robot, origin, job["kind"], src, dst, a, lineage, cpu, {"validation": v}) if a is not None else None
        if row is not None:
            row["sweep_cpu_s"] = time.process_time() - c0 - cpu
        if row is not None:
            out["templates"].append((row, a))
        if pair is not None:
            seen[gkey(*pair)] = (row and row["id"], None if row else neg)
        out["attempts"].append(attempt(origin, src, dst, lineage, row is not None, term, neg, cpu, row and row["id"], c))
        return row and row["id"]

    home = np.array(robot.q_home)
    if not good or not goodp:
        cert = all(x.certified for x in allc if x.stage != "OK")
        for how in ("order", "spread"):
            out[f"direct_{how}"] = []
            out["attempts"].append(attempt(f"DIRECT_OFFLINE:{how}", src, dst, {}, False, "NO_PICK_CANDIDATE" if not good else
                                           "NO_PLACE_CANDIDATE", "CERTIFIED" if cert else "NO_PLAN_FOUND", scr_cpu, None, c))
    else:
        for how in ("order", "spread"):
            out[f"direct_{how}"] = [emit(f"DIRECT_OFFLINE:{how}", {"rank": i}, pr) for i, pr in enumerate(direct_pairs(good, goodp, home,
                                                                                                                   job["direct_k"], how))]
    out["modes"] = {}
    for sd in job.get("seeds", []):                           # members in canonical mode order; a mode keeps its first W distinct templates
        if len(out["modes"].get(sd["mode"], [])) >= c["templates_per_mode"]:
            continue
        lin = {k: sd[k] for k in sd if k != "grasp"} | {"seed_grasp": sd["grasp"]}
        pair, why, shift = seeded_pair(good, goodp, sd["grasp"], sd["psi"], math.radians(c["max_grasp_shift_deg"])) if good and goodp \
            else (None, "NO_DECLARED_GRASP", None)
        lin["grasp_shift_rad"] = shift
        if pair is None:
            out["attempts"].append(attempt("FAMILY_RETARGET", src, dst, lin, False, why, "NO_PLAN_FOUND", 0.0, None, c))
            out["modes"].setdefault(sd["mode"], [])
            continue
        lin["snapped_grasp"] = [[pair[0].phi, pair[0].branch], [pair[1].phi, pair[1].branch]]
        t = emit("FAMILY_RETARGET", lin, pair)
        lst = out["modes"].setdefault(sd["mode"], [])
        if t and t not in lst:
            lst.append(t)
    out["exact"] = []
    for ex in job.get("exact", []):
        core = gr._arrays(Path(ex["file"]))[ex["index"]]
        out["exact"].append(emit("EXACT_CELL_WITNESS", {"witness": f"{ex['file']}#{ex['index']}", **ex}, core=core))
    return out


def compile_entries(strata) -> dict:
    """ENTRY templates: each declared root start q -> home in the empty workspace (nothing held, open gripper), certified offline."""
    c = ccfg()
    cfg, robot, p = setup(c)
    s, home, out = fixture(cfg), np.array(robot.q_home), {"templates": [], "attempts": []}
    ck = ge.Checker(robot, ge.make_world(s), p["delta"], p["eps"])
    for name, q in strata.items():
        c0, q = time.process_time(), np.asarray(q, float)
        if np.array_equal(q, home):
            continue
        r = pn.plan(ck, q, home, robot.open_gap, cfg["planner2d"], p["evals"], f"{VERSION}/entry/{name}", True)
        cpu = time.process_time() - c0
        if r.status != ge.CLEAR:
            out["attempts"].append(attempt("ENTRY", None, None, {"stratum": name}, False, r.reason, _neg(r), cpu, None, c))
            continue
        path = np.asarray(r.path, float)
        a = {"q": path, "gap": np.full(len(path), robot.open_gap), "phase": np.array(["pregrasp"] * (len(path) - 1)),
             "attached": np.zeros(len(path) - 1, bool), "held_local": np.array([]), "place_xy": np.array([])}
        row = {"id": tid(a, name, "home"), "compiler_version": VERSION, "origin": "ENTRY", "kind": "ENTRY", "stratum": name,
               "q_start": path[0].tolist(), "q_end": path[-1].tolist(), "waypoints": len(path), "method": r.reason, "compile_cpu_s": cpu,
               "fixture": "GENERIC_EMPTY_WORKSPACE", "contract": "Q_HOME"}
        out["templates"].append((row, a))
        out["attempts"].append(attempt("ENTRY", None, None, {"stratum": name}, True, r.reason, None, cpu, row["id"], c))
    return out


def save_catalog(templates, attempts, name="CATALOG") -> dict:
    """CATALOG.json (template rows + execution index (src, dst, radius, q_start) -> ids) and CATALOG_TEMPLATES.npz (frozen arrays)."""
    d = OUT / "catalog"
    d.mkdir(parents=True, exist_ok=True)
    rows, arrs = {}, {}
    for row, a in templates:
        rows.setdefault(row["id"], {k: v for k, v in row.items() if k not in ("arrays", "derivations")})
        for k, v in a.items():
            arrs[f"{row['id']}__{k}"] = np.asarray(v)
    for a in attempts:                                        # every compile path that yields this exact template (lineage is per path)
        if a["compiled"] and a["template_id"] in rows:
            rows[a["template_id"]].setdefault("derivations", []).append({"origin": a["origin"], "lineage": a["lineage"]})
    index = collections.defaultdict(list)
    for r in rows.values():
        if r["kind"] != "ENTRY":
            index[f"{r['src']}>{r['dst']}|{r['radius']}|home"].append(r["id"])
    np.savez_compressed(d / f"{name}_TEMPLATES.npz", **arrs)
    cat = {"version": VERSION, "templates": rows, "execution_index": dict(sorted(index.items())), "attempts": attempts,
           "hash": cf.stable_hash(sorted(rows)), "arrays_sha256": arrays_hash(arrs)}
    cf.write_json(d / f"{name}.json", cat)
    return cat


def arrays_hash(arrs) -> str:
    """Content hash of the frozen arrays (sorted keys, dtype, shape, bytes): independent of npz member order and zip metadata."""
    h = hashlib.sha256()
    for k in sorted(arrs):
        v = np.ascontiguousarray(arrs[k])
        h.update(f"{k}|{v.dtype.str}|{v.shape}".encode())
        h.update(v.tobytes())
    return h.hexdigest()


def load_catalog(name="CATALOG") -> dict:
    """id -> runtime template (row fields + frozen arrays + swept set), as ad_runtime.check consumes it."""
    d = OUT / "catalog"
    cat, z = json.loads((d / f"{name}.json").read_text()), np.load(d / f"{name}_TEMPLATES.npz")
    out = {}
    for i, r in cat["templates"].items():
        a = {k.split("__")[1]: z[k] for k in z.files if k.startswith(f"{i}__")}
        out[i] = {**r, "arrays": a, "q_start": np.asarray(r["q_start"]), "q_end": np.asarray(r["q_end"])}
    return out
