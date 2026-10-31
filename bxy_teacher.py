"""BXY-P9 connector-aware physical teacher (Approach_B_Final_Methodology_2026-10-31 §2.2, §2.2.1, §5.1; BXY_P9 instructions §C).

X(q), BXY_X_TEACHER_V1: from the stored S0 and q0, every relocation of the ordered prefix is planned by the historical BD2D greedy teacher
  (p16_motion.DetPhysics, no library, P16_FAST profile, bd_2d.QB per-query counts, p16_common.best_edge = cheapest verified mode), the
  achieved joint state carried to the next relocation; then ONE terminal connector q_final -> q_ref in the edited scene with every body
  present (target included), gripper open (bd scene contract: 0.07 m, free), nothing attached: DetPhysics._transit = certified straight
  segment, else one bounded RRT counted under `transit_plans` (both in the motion.checkers ('start', False) world: all objects, no contact
  allowance). X = 1 only if every relocation and the connector are verified AND the independent replay below passes.
Y(S^q), BXY_Y_TEACHER_V1: bd_2d.t_goal (the labels.original / labels.D teacher, same QB) from the SAME fixed q_ref in the hypothetical
  edited scene, whatever X is; Y = 1 only if verified AND independently replayed.
Binary contract: a completed attempted query is 1 or 0 (budget exhaustion included, negative_kind / failed phase kept); malformed queries are
INELIGIBLE (not attempted); administrative kills are written as CENSORED by the pilot supervisor, never 0. Witness arrays are content-
addressed like bd_core.Store.witness; trajectories never enter learner data."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

import bd_2d
import bd_core as bc
import bxy_data as bd

X_VERSION, Y_VERSION = "BXY_X_TEACHER_V1", "BXY_Y_TEACHER_V1"
TOL_Q = 1e-6                                   # continuity / endpoint tolerance (p16_motion.replay's record-continuity tolerance)
TEACHER = {"physics": "p16_motion.DetPhysics(idx=None, transit='planned', transit_nodes=800->FAST 500, profile='fast')",
           "budget_per_query": bd_2d.QB, "edge_choice": "p16_common.best_edge (cheapest verified mode)",
           "connector": "DetPhysics._transit: certified straight segment, else one bounded RRT under transit_plans; motion.checkers ('start', False)",
           "y": "bd_2d.t_goal(task, root cache, edited cells, q_ref)", "cache": "one exact DetPhysics cache per root (bd_2d convention)",
           "replay_tol_q": TOL_Q}
SOURCES = ("bxy_teacher.py", "bd_2d.py", "bd_core.py", "p16_motion.py", "p16_common.py", "p15_search.py", "motion.py", "geometry.py",
           "skill.py", "planner.py", "ordered.py", "config.toml")


def file_sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def teacher_hash() -> str:
    return "sha256:" + hashlib.sha256(json.dumps({"teacher": TEACHER, "x": X_VERSION, "y": Y_VERSION,
                                                  "src": {f: file_sha(f) for f in SOURCES}}, sort_keys=True).encode()).hexdigest()


def env():
    import config as cf
    import geometry as ge
    import skill as sk
    cfg = cf.load_config("config.toml")
    return {"cfg": cfg, "robot": ge.make_robot(cfg), "p": sk.params(cfg)}


def task_of(k, rec) -> dict:
    return {"scene": rec["scene"], "goal_cell": rec["goal_cell"], "fixed_ids": rec["fixed_ids"], "target": "t0", "key": k}


def qref(rec) -> np.ndarray:
    return np.asarray(rec["q0"], float)


def ref_gap(rec) -> float:
    return float(rec["scene"]["robot"]["gripper_gap_m"])


def context(k, rec) -> str:
    """Root / task / reference-state / robot-profile identity carried by every V2 key (no aliasing across them)."""
    return bc.sha([k, rec["goal_cell"], np.round(qref(rec), 12).tolist(), ref_gap(rec), rec["scene"]["robot_profile_hash"]])[:12]


def xkey(k, rec, seq) -> str:
    return f"X2:{k}:{context(k, rec)}:{bd.sig(seq)}"


def ykey(k, rec, seq=None, edit=None) -> str:
    e = bd.endpoint(rec, seq) if edit is None else {o: int(v) for o, v in sorted(edit.items())}
    return f"Y2:{k}:{context(k, rec)}:{bd.sig(sorted(e.items()))}"


def eligible(rec, seq):
    """None if the query is well formed, else the reason (INELIGIBLE: never attempted, never a label)."""
    movable = set(rec["roles"])
    try:
        bc.check_sequence(seq)
    except ValueError as e:
        return str(e)
    if any(o not in movable for o, _ in seq):
        return "moves a non-movable object (target or fixed structure)"
    if len({o for o, _ in seq}) != len(seq):
        return "duplicate relocation of one object"
    if any(int(d) not in rec["scene"]["legal_cells"] for _, d in seq):
        return "destination outside the legal supported cells"
    return None


def wid(arrays, out=None) -> str:
    """Content id exactly as bd_core.Store.witness (written under out/witnesses when out is given)."""
    class _S:
        root = Path(out) if out else None
    if out is None:
        h = hashlib.sha256()
        for k in sorted(arrays):
            v = np.ascontiguousarray(np.asarray(arrays[k]))
            h.update(f"{k}|{v.dtype.str}|{v.shape}".encode())
            h.update(v.tobytes())
        return h.hexdigest()[:24]
    return bc.Store.witness(_S, arrays)


def _phys(k, rec, cache):
    import p16_motion as pm
    return pm.DetPhysics(task_of(k, rec), None, budget=dict(bd_2d.QB), cache=cache)


def _neg(status):
    return bd_2d._neg(status)


# ------------------------------------------------------------------ independent replays
def replay_x(E, rec, seq, records, connector) -> dict:
    """Relocations + connector re-certified from S0 / q0 with motion.certify_trajectory (relocations, in the scene each one faces) and
    geometry.certify on every connector segment in the full ('start', False) world of the edited scene; exact continuity, gap / attachment
    schedule, placement at the requested cells, joint limits and the q_ref endpoint."""
    import geometry as ge
    import motion as mo
    import p16_motion as pm
    phys = pm.DetPhysics(task_of("replay", rec), None, budget=dict(bd_2d.QB))
    robot, p = E["robot"], E["p"]
    cells, q, gap = bd.cells0(rec), qref(rec), ref_gap(rec)
    if len(records) != len(seq):
        return {"ok": False, "why": "record count differs from the prefix"}
    for j, ((o, d), a) in enumerate(zip(seq, records)):
        if np.max(np.abs(np.asarray(a["q"][0], float) - q)) > TOL_Q or abs(float(a["gap"][0]) - gap) > 1e-12:
            return {"ok": False, "why": f"relocation {j}: discontinuous robot state"}
        s = phys.scene(cells, q)
        try:
            v = mo.certify_trajectory(robot, s, o, a, p["delta"], p["eps"], p["evals"])
        except ValueError as e:
            return {"ok": False, "why": f"relocation {j}: invalid record ({e})"}
        if not all(x.status == ge.CLEAR for x in v):
            return {"ok": False, "why": f"relocation {j}: segment not certified clear"}
        if np.linalg.norm(np.asarray(a["place_xy"], float) - np.asarray(s.lattice.center(int(d)))) > 1e-9:
            return {"ok": False, "why": f"relocation {j}: object not placed at the requested cell"}
        if bool(a["attached"][-1]) or str(a["phase"][-1]) != "retreat":
            return {"ok": False, "why": f"relocation {j}: does not end released after a safe retreat"}
        cells, q, gap = {**cells, o: int(d)}, np.asarray(a["q"][-1], float), float(a["gap"][-1])
    c = connector
    cq = np.asarray(c["q"], float)
    if np.max(np.abs(cq[0] - q)) > TOL_Q:
        return {"ok": False, "why": "connector: discontinuous robot state"}
    if any(c["attached"]) or np.asarray(c["held_local"]).size or np.any(np.abs(np.asarray(c["gap"], float) - ref_gap(rec)) > 1e-12) or abs(gap - ref_gap(rec)) > 1e-12:
        return {"ok": False, "why": "connector: gripper not free / open at the reference gap"}
    if not all(ge.within_limits(robot, w) for w in cq):
        return {"ok": False, "why": "connector: waypoint outside joint limits"}
    ck = mo.checkers(robot, phys.scene(cells, q), "t0", None, None, p["delta"], p["eps"])[("start", False)]
    for qa, qb in zip(cq[:-1], cq[1:]):
        if ge.certify(ck, qa, qb, gap, gap, p["evals"]).status != ge.CLEAR:
            return {"ok": False, "why": "connector: segment not certified clear"}
    if ck.status_at(cq[-1], gap).status != ge.CLEAR:
        return {"ok": False, "why": "connector: endpoint not clear"}
    if np.max(np.abs(cq[-1] - qref(rec))) > TOL_Q:
        return {"ok": False, "why": "connector: does not end at q_ref"}
    return {"ok": True, "why": None, "final_cells": cells}


def replay_y(E, rec, seq, a) -> dict:
    """Target record re-certified in the hypothetical edited scene from q_ref; placement at the goal; ends released after retreat."""
    import geometry as ge
    import motion as mo
    import p16_motion as pm
    phys = pm.DetPhysics(task_of("replay", rec), None, budget=dict(bd_2d.QB))
    cells = {**bd.cells0(rec), **bd.endpoint(rec, seq)}
    if np.max(np.abs(np.asarray(a["q"][0], float) - qref(rec))) > TOL_Q or abs(float(a["gap"][0]) - ref_gap(rec)) > 1e-12:
        return {"ok": False, "why": "target record does not start at q_ref with the reference gap"}
    s = phys.scene(cells, qref(rec))
    try:
        v = mo.certify_trajectory(E["robot"], s, "t0", a, E["p"]["delta"], E["p"]["eps"], E["p"]["evals"])
    except ValueError as e:
        return {"ok": False, "why": f"invalid target record ({e})"}
    if not all(x.status == ge.CLEAR for x in v):
        return {"ok": False, "why": "target segment not certified clear"}
    if np.linalg.norm(np.asarray(a["place_xy"], float) - np.asarray(s.lattice.center(rec["goal_cell"]))) > 1e-9:
        return {"ok": False, "why": "target not placed at the goal cell"}
    if bool(a["attached"][-1]) or str(a["phase"][-1]) != "retreat":
        return {"ok": False, "why": "target does not end released after a safe retreat"}
    return {"ok": True, "why": None}


# ------------------------------------------------------------------ queries
def _travel(E, recs):
    import ordered as od
    return od.joint_travel(E["robot"], recs)


def x_query(E, k, rec, seq, cache, out=None, legacy=None) -> dict:
    """One X query (attempted iff eligible). Returns the V2 x_query row; witness arrays in out/witnesses."""
    import geometry as ge
    import motion as mo
    import p15_search as ps
    import p16_common as pc
    seq = [(o, int(d)) for o, d in seq]
    row = {"root": k, "x_key": xkey(k, rec, seq), "x_key_v1": bd.xkey(k, seq), "parent_y_key": ykey(k, rec, seq), "ordered_actions": [list(a) for a in seq],
           "teacher": X_VERSION, "q0": qref(rec).tolist(), "q_ref": qref(rec).tolist()}
    bad = eligible(rec, seq)
    if bad or not seq:
        return row | {"attempted": False, "observed": False, "y": None, "teacher_status": "INELIGIBLE" if bad else "EMPTY_PREFIX_X_IS_1_BY_DEFINITION",
                      "why": bad}
    c0 = time.process_time()
    phys = _phys(k, rec, cache)
    cells, q, recs, steps = bd.cells0(rec), qref(rec), [], []
    fail = None
    for j, (o, d) in enumerate(seq):
        outs = phys.edges(cells, q, o, d)
        e = pc.best_edge(outs)
        if e is None:
            st = outs[0][0] if outs else ps.U_PLAN
            fail = {"teacher_status": st, "negative_kind": _neg(st), "failed_phase": f"relocation:{j}", "detail": str(outs[0][4] if outs else None)[:200]}
            break
        _, rs, q2, J, meta = e
        recs += rs
        steps.append({"object": o, "dest": d, "via": meta.get("via"), "J_record": J, "witness": [wid(a, out) for a in rs]})
        cells, q = {**cells, o: d}, np.asarray(q2, float)
    row |= {"steps": steps, "final_q_before_connector": q.tolist() if fail is None else None}
    conn = None
    if fail is None:
        s = phys.scene(cells, q)
        ck = mo.checkers(E["robot"], s, "t0", None, None, E["p"]["delta"], E["p"]["eps"])[("start", False)]
        gap = ref_gap(rec)
        if ck.status_at(q, gap).status != ge.CLEAR:
            fail = {"teacher_status": "TERMINAL_STATE_NOT_CLEAR", "negative_kind": "CERTIFIED", "failed_phase": "connector:terminal_q"}
        elif ck.status_at(qref(rec), gap).status != ge.CLEAR:
            fail = {"teacher_status": "Q_REF_NOT_CLEAR_IN_EDITED_SCENE", "negative_kind": "CERTIFIED", "failed_phase": "connector:q_ref"}
        else:
            conn, how = phys._transit(s, "t0", q, {"q": [qref(rec)], "gap": [gap]}, ("bxy_connector", ps.state_key(cells, q, ())))
            row["connector_how"] = how
            if conn is None:
                st = ps.U_BUD if phys.used["transit_plans"] >= phys.budget["transit_plans"] else ps.U_TR
                fail = {"teacher_status": st, "negative_kind": _neg(st), "failed_phase": "connector"}
    row |= {"budget_spent": dict(phys.used), "budget": dict(phys.budget), "process_cpu_s": round(time.process_time() - c0, 3),
            "virtual_cpu_s": round(phys.vcpu, 3), "cache_hits": phys.stats.get("cache_hits", 0), "legacy_witness_match": None}
    if legacy is not None and steps:                       # determinism diagnostic against the stored historical relocation witnesses
        mine = [w for st_ in steps for w in st_["witness"]]
        row["legacy_witness_match"] = mine == legacy[:len(mine)]
    if fail is not None:
        return row | {"attempted": True, "observed": True, "y": 0, **fail, "independent_replay": None, "witness_connector": None,
                      "final_q_after_connector": None, "travel_parts": None}
    rep = replay_x(E, rec, seq, recs, conn)
    tj = {"J_move": [_travel(E, [a])["J"] for a in recs], "J_between_actions": [_travel(E, [a])["per_phase"].get("pregrasp", 0.0) for a in recs],
          "J_connector": _travel(E, [conn])["J"], "J_prefix_stitched": _travel(E, recs + [conn])["J"], "note": "J_between_actions = the pregrasp "
          "(free approach from the achieved state) part of each relocation record, already inside J_move"}
    row |= {"witness_relocations": [wid(a, out) for a in recs], "witness_connector": wid(conn, out), "final_q_after_connector": np.asarray(conn["q"][-1]).tolist(),
            "independent_replay": rep["ok"], "replay_why": rep["why"], "travel_parts": tj, "attempted": True, "observed": True}
    if rep["ok"]:
        return row | {"y": 1, "teacher_status": "VERIFIED", "negative_kind": None, "failed_phase": None}
    return row | {"y": 0, "teacher_status": "REPLAY_FAILED", "negative_kind": "OTHER_FAILURE", "failed_phase": "replay"}


def y_query(E, k, rec, seq, cache, out=None, legacy=None) -> dict:
    """One Y query from q_ref in the hypothetical edited scene of the prefix (never from an achieved X state)."""
    seq = [(o, int(d)) for o, d in seq]
    edit = bd.endpoint(rec, seq)
    row = {"root": k, "y_key": ykey(k, rec, seq), "y_key_v1": bd.ykey(k, rec, seq), "hypothetical_poses": edit, "teacher": Y_VERSION,
           "robot_start_q_ref": qref(rec).tolist(), "q_ref_hash": context(k, rec)}
    bad = eligible(rec, seq) if seq else None
    if bad:
        return row | {"attempted": False, "observed": False, "y": None, "teacher_status": "INELIGIBLE", "why": bad}
    c0 = time.process_time()
    st, a, _ = bd_2d.t_goal(task_of(k, rec), cache, {**bd.cells0(rec), **edit}, qref(rec))
    row |= {"process_cpu_s": round(time.process_time() - c0, 3), "attempted": True, "observed": True, "legacy_y": legacy}
    if st != "VERIFIED":
        return row | {"y": 0, "teacher_status": st, "negative_kind": _neg(st), "failed_phase": "target", "target_witness": None,
                      "independent_replay": None, "J_target": None}
    rep = replay_y(E, rec, seq, a)
    row |= {"target_witness": wid(a, out), "independent_replay": rep["ok"], "replay_why": rep["why"], "J_target": _travel(E, [a])["J"]}
    return row | ({"y": 1, "teacher_status": "VERIFIED", "negative_kind": None, "failed_phase": None} if rep["ok"] else
                  {"y": 0, "teacher_status": "REPLAY_FAILED", "negative_kind": "OTHER_FAILURE", "failed_phase": "replay"})


def load_w(out, w) -> dict:
    z = np.load(Path(out) / "witnesses" / w[:2] / f"{w}.npz")
    return {k: z[k] for k in z.files}


def pair(E, xr, yr, out) -> dict:
    """Matched (X, Y) of one prefix: same root / context / endpoint; full joint success needs both replayed witnesses AND exact stitching
    (connector end == target start == q_ref, same gap); J_total over the stitched relocations + connector + target (ordered.joint_travel)."""
    m = xr["parent_y_key"] == yr["y_key"] and xr["root"] == yr["root"]
    res = {"x_key": xr["x_key"], "y_key": yr["y_key"], "matched_protocol": m, "x": xr.get("y"), "y": yr.get("y"), "full_joint_success": None, "J_total": None}
    if not m or xr.get("y") is None or yr.get("y") is None:
        return res
    res["full_joint_success"] = int(xr["y"] == 1 and yr["y"] == 1)
    if res["full_joint_success"]:
        recs = [load_w(out, w) for w in xr["witness_relocations"]] + [load_w(out, xr["witness_connector"]), load_w(out, yr["target_witness"])]
        tv = _travel(E, recs)
        res |= {"J_total": tv["J"], "stitch_problems": tv["problems"], "J_parts_sum": sum(tv["per_record"])}
        if tv["J"] is None:
            res["full_joint_success"] = None                 # stitching failed: not a decided joint witness
    return res
