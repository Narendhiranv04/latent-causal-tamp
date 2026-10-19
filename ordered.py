"""INITIAL_SCENE_ORDERED_ONE_SHOT_V2 evidence, cost and one-shot execution checks
(Methodology v1.6 §4, §8, §10, §12; Guide v1.8 §3, §7, §9). G4D migration.

Teacher path (privileged, offline): `teach_sequence` restarts from the immutable
initial state, verifies exactly the proposed order (verify.plan_fixed_order), stores
the FIRST complete relocation witness and its normalized joint travel before looking
at the target, then evaluates the target once from that witness's achieved state.
Evidence keeps separate status fields and explicit scopes: a failed trajectory is
never an order-wide negative, a witness labels only its own order.

Primary path: `primary_v2` runs evaluate.primary_episode with the fixed-order planner
(no reordering, frozen pool, at most one target call after the repair completes) and
`episode_audit` re-checks the boundary, order, joint continuity and target start.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

import certificates as cert
import data
import evaluate as ev
import geometry as ge
import motion as mo
import proposals as pr
import sequences as sq
import skill as sk
import verify as vf

NOT_RUN, NOT_AUTHORIZED = "NOT_RUN", "NOT_AUTHORIZED"


# ------------------------------------------------------------------ cost (first relocation witness)
def joint_travel(robot, records: list) -> dict:
    """J(w) = sum over consecutive waypoints of sum_j |dq_j| / (q_max_j - q_min_j) over every
    relocation record in order: pregrasp, approach, closure, carry, release, retreat and
    the transitions between relocations. Gripper aperture is excluded. The backend's
    segments are joint-linear between waypoints inside the finite limits [-pi, pi], so
    the differences are the actual unwrapped motion (no wrap shortcut can exist; a large
    certified step is real travel). A waypoint outside the limits or a discontinuous
    transition (next record not starting at the previous end in q and gap) makes the
    label unavailable."""
    rng = np.array([hi - lo for lo, hi in robot.limits], float)
    problems, per_record, per_phase = [], [], {}
    if not np.all(np.isfinite(rng)) or np.any(rng <= 0):
        problems.append("joint range not finite and nonzero")
    for k, arr in enumerate(records):
        q = np.asarray(arr["q"], float)
        d = np.abs(np.diff(q, axis=0))
        if not all(ge.within_limits(robot, x) for x in q):
            problems.append(f"record {k}: waypoint outside the joint limits (unwrapped path not established)")
        if k and not (np.array_equal(np.asarray(records[k - 1]["q"])[-1], q[0]) and records[k - 1]["gap"][-1] == arr["gap"][0]):
            problems.append(f"record {k}: does not start where record {k - 1} ended")
        seg = (d / rng).sum(axis=1)
        per_record.append(float(seg.sum()))
        for ph, v in zip(arr["phase"], seg):
            per_phase[str(ph)] = per_phase.get(str(ph), 0.0) + float(v)
    return {"J": None if problems else float(sum(per_record)), "per_record": per_record, "per_phase": per_phase,
            "problems": problems, "available": not problems, "joint_ranges_rad": rng.tolist()}


def cost_record(robot, v2: dict, s0: vf.RepairState, att: vf.Attempt | None, robot_hash: str) -> dict:
    """Cost label of the declared first-witness policy. Empty sequence: exactly 0. No
    complete relocation witness: no label (never a large or zero placeholder)."""
    base = {"policy": v2["cost"]["policy"], "backend": v2["cost"]["relocation_backend"],
            "start_q": list(s0.q), "start_gap": s0.gap}
    if att is None or att.status != vf.RELOCATED:
        return {**base, "label_available": False, "J": None, "reason": "NO_COMPLETE_RELOCATION_WITNESS"}
    arrs = [r.traj.arrays() for r in att.skills]
    jt = joint_travel(robot, arrs)
    starts = not arrs or (np.array_equal(arrs[0]["q"][0], np.asarray(s0.q)) and arrs[0]["gap"][0] == s0.gap)
    ok = jt["available"] and starts
    end = vf.final_state(s0, att)
    return {**base, "label_available": ok, "J": (0.0 if not arrs else jt["J"]) if ok else None,
            "reason": "OK" if ok else "; ".join(jt["problems"] + ([] if starts else ["first record not at S0"])),
            "witness_hash": ev.witness_hash(s0, att, robot_hash), "end_q": list(end.q), "end_gap": end.gap,
            "waypoints": int(sum(len(a["q"]) for a in arrs)), "per_record": jt["per_record"],
            "per_phase": jt["per_phase"], "joint_ranges_rad": jt["joint_ranges_rad"]}


# ------------------------------------------------------------------ certificate producers (checked in certificates.py)
def first_screen(robot, scene, oid: str, cell: int, cfg: dict):
    """(stage, family size) if `oid` moved first from `scene` to `cell` is excluded by a
    definite pose-only screen over the declared grasp family, else None."""
    p = sk.params(cfg)
    o, n = scene.get(oid), len(sk.directions(p))
    picks = sk.screen_pick(robot, mo.checkers(robot, scene, oid, None, None, p["delta"], p["eps"]), o.xy_m, o.radius_m, p)
    if not any(c.stage == "OK" for c in picks):
        return ("PICK", n) if all(c.certified for c in picks) else None
    dest, local = scene.lattice.center(cell), (robot.grasp_x, 0.0)
    ck = mo.checkers(robot, scene, oid, dest, local, p["delta"], p["eps"])
    places = sk.screen_place(robot, ck, dest, local, 2 * o.radius_m, p)
    ok = not any(c.stage == "OK" for c in places) and all(c.certified for c in places)
    return ("PLACE", n) if ok else None


def certificates_for(robot, cfg: dict, scene, learner: dict, seq) -> list:
    """Candidate negative records for one ordered proposal, each with its scope and the
    independent checker's verdict. Producers propose; only accepted records count."""
    cells, act = sq.assignment(seq), learner["action"]
    scope = cert.certificate_scope(scene, learner, cells)
    recs = []
    if pr.static_endpoints(scene, cells, act["target_id"], cfg)["status"] == mo.INVALID:
        recs.append({**scope, "kind": "STATIC_ENDPOINT_INVALID"})
    else:
        occ = pr.goal_blockers(scene, cells, act, cfg)
        if occ:
            recs.append({**scope, "kind": "GOAL_OVERLAP", "obstacles": occ})
        kept = replace(scene, objects=tuple(o for o in scene.objects if o.id not in cells))   # staying objects only
        pick = sk.pick_certificate(robot, kept, act["target_id"], cfg)
        if pick is not None and pick.status == sk.INFEASIBLE:
            recs.append({**scope, "kind": "TARGET_PICK", "removed": sorted(cells), "candidates": len(pick.picks)})
        screens = {o: first_screen(robot, scene, o, d, cfg) for o, d in seq}
        if seq and all(screens.values()):
            recs.append({**scope, "kind": "FIRST_MOVER", "movers": {o: {"stage": s, "candidates": n}
                                                                   for o, (s, n) in screens.items()}})
        if seq and screens[seq[0][0]]:
            s, n = screens[seq[0][0]]
            recs.append({**scope, "kind": "ORDER_FIRST_ACTION", "sequence": [list(a) for a in seq], "stage": s,
                         "candidates": n})
    out = []
    for r in recs:
        ok, why = cert.check(robot, scene, learner, cells, r, cfg)
        out.append({**r, "scope": cert.CERTIFICATE_SCOPE[r["kind"]], "checker_accepted": ok, "checker_reasons": why})
    return out


# ------------------------------------------------------------------ offline teacher for one ordered proposal
def teach_sequence(robot, cfg: dict, v2: dict, query: dict, scene, seq, target_eval, key: str, robot_hash: str) -> dict:
    """Evidence for one canonical sequence from the immutable initial state. The relocation
    witness and its cost are stored before the target is examined; the target is
    evaluated once from that witness's achieved state, and skipped (NOT_RUN) when an
    accepted certificate already covers this order."""
    seq = sq.canonical(seq)
    why = sq.validate_sequence(scene, query["learner"]["action"], seq, v2["proposal"]["move_cap"])
    if why:
        raise ValueError(f"not a canonical V2 sequence: {why}")
    learner, s0 = query["learner"], ev.start(scene, query)
    certs = certificates_for(robot, cfg, scene, learner, seq)
    evidence = [{"kind": "certificate", "validated": c["checker_accepted"], "certificate": c["kind"], "scope": c["scope"],
                 "source": "teacher"} for c in certs]
    static = pr.static_endpoints(scene, sq.assignment(seq), learner["action"]["target_id"], cfg)["status"]
    rec = {"sequence": [list(a) for a in seq], "assignment": sq.assignment(seq), "moved": len(seq), "static_status": static,
           "certificates": certs, "relocation_attempt_status": NOT_RUN, "target_attempt_status": NOT_RUN,
           "simulation_status": NOT_RUN, "hardware_status": NOT_AUTHORIZED, "cost": None, "relocation": None,
           "target": None, "target_start_matches_achieved": None}
    first_blocked = any(c["kind"] in ("ORDER_FIRST_ACTION", "STATIC_ENDPOINT_INVALID") and c["checker_accepted"]
                        for c in certs)
    if static == mo.VALID and not first_blocked:
        plan = vf.plan_fixed_order(robot, cfg, s0, seq, f"{key}/reloc", {"plans": 0})
        att = plan["attempts"][0] if plan["attempts"] else None
        rec["relocation_attempt_status"] = vf.RELOCATED if plan["witness"] else data.UNKNOWN
        rec["relocation"] = {"stop": plan["stop"], "policy": plan["policy"], "relocation_plans": plan["relocation_plans"],
                             "failed_action": att and att.stop, "reason": att and att.reason}
        rec["cost"] = cost_record(robot, v2, s0, plan["witness"], robot_hash)
        rec["_attempt"] = att
        if not plan["witness"]:
            evidence.append({"kind": "order_attempt", "scope": data.TRAJECTORY, "source": "teacher",
                             "status": att.status if att else "RELOCATION_BUDGET"})
        elif not any(c["checker_accepted"] for c in certs):
            achieved = vf.final_state(s0, plan["witness"])
            t = target_eval(achieved, f"{key}/target")
            rec["target"], rec["target_attempt_status"] = t, t["status"]
            arr = t.get("result") and t["result"].traj is not None and t["result"].traj.arrays()
            rec["target_start_matches_achieved"] = bool(arr) and bool(np.array_equal(arr["q"][0], np.asarray(achieved.q))
                                                                     and arr["gap"][0] == achieved.gap)
            if t["status"] == ev.VALID and rec["target_start_matches_achieved"]:
                evidence.append({"kind": "complete_witness", "scope": data.ORDER, "source": "teacher"})
    rec["aggregate"] = data.ordered_aggregate(evidence)
    rec["ordered_feasibility_status"] = rec["aggregate"]["label"]
    rec["evidence"] = evidence
    return rec


# ------------------------------------------------------------------ V2 primary episode
def fixed_order_planner(robot, cfg, s0, cand, key, used):
    return vf.plan_fixed_order(robot, cfg, s0, cand["sequence"], key, used)


def primary_v2(robot, cfg, query: dict, scene, ranked: list, target_eval, robot_hash: str, trace=None, executor=None):
    """One-shot V2 episode over a frozen ranked pool (sequences.rank_sequences)."""
    cands = [{**r, "cells": dict(r["assignment"])} for r in ranked]
    out = ev.primary_episode(robot, cfg, query, scene, cands, target_eval, robot_hash, trace, executor,
                             planner=fixed_order_planner)
    out["audit"] = episode_audit(out, ev.start(scene, query), ranked)
    return out


def episode_audit(out: dict, s0: vf.RepairState, ranked: list) -> dict:
    """Boundary, order, continuity and target-start checks recomputed from the episode."""
    ev_ = out["trace"].events
    kinds = [e["kind"] for e in ev_]
    t = [i for i, k in enumerate(kinds) if k == "TARGET_EVALUATE"]
    c = kinds.index("COMMIT") if "COMMIT" in kinds else None
    r = [i for i, k in enumerate(kinds) if k == "RELOCATE"]
    w = out["commit"] and out["commit"]["attempt"]
    order_ok = w is None or [list(m) for m in w.order] == [list(a) for a in ranked[out["commit"]["rank"]]["sequence"]]
    cont, prev = True, (np.asarray(s0.q), s0.gap)
    for res in (w.skills if w else []):
        a = res.traj.arrays()
        cont &= bool(np.array_equal(a["q"][0], prev[0]) and a["gap"][0] == prev[1])
        prev = (a["q"][-1], a["gap"][-1])
    tgt, ach = out["target"], out["achieved"]
    start_ok = None
    if tgt is not None and ach is not None:
        arr = tgt.get("result") and tgt["result"].traj is not None and tgt["result"].traj.arrays()
        start_ok = bool(np.array_equal(np.asarray(ach.q), prev[0]) and ach.gap == prev[1]) and (
            not arr or bool(np.array_equal(arr["q"][0], np.asarray(ach.q)) and arr["gap"][0] == ach.gap))
    return {"target_calls": len(t), "calls_before_commit": sum(c is None or i < c for i in t),
            "calls_before_last_relocation": sum(bool(r) and i < max(r) for i in t),
            "calls_after_abort": sum("ABORT" in kinds[:i] for i in t), "commits": kinds.count("COMMIT"),
            "committed_order_equals_proposed": bool(order_ok), "joint_continuity": bool(cont),
            "target_start_equals_achieved": start_ok,
            "reobserve": [{k: e.get(k) for k in ("object", "commanded_xy", "achieved_xy", "q", "gap", "attachment", "moved",
                                                 "matches_commitment")} for e in ev_ if e["kind"] == "REOBSERVE"],
            "boundary_ok": len(t) <= 1 and (not t or (c is not None and t[0] > c and (not r or t[0] > max(r))))}
