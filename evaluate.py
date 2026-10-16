"""INITIAL_SCENE_ONE_SHOT_V1: post-commit target evaluation, the primary episode with
its commitment boundary, and the separate offline case audit (Methodology v1.5 §2,
§9; Guide v1.7 §3-4).

The target evaluator is injected only into `primary_episode` after COMMIT and into
the privileged `audit_candidate` teacher path. Proposal ranking (solve.py) and
relocation planning (verify.py) never import this module.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import motion as mo
import skill as sk
import solve
import verify as vf
from config import stable_hash
from scene import scene_hash

VALID, INVALID, UNRESOLVED = sk.VERIFIED, sk.INFEASIBLE, sk.UNRESOLVED      # evidence words (spec §3)


@dataclass
class Trace:
    """Ordered events: PROPOSE, STATIC_CHECK, REPAIR_PLAN, COMMIT, RELOCATE, REOBSERVE,
    TARGET_EVALUATE, FINISH or ABORT, each with its component and state hash."""
    episode: str
    events: list = field(default_factory=list)
    t0: float = field(default_factory=time.perf_counter)

    def emit(self, kind: str, component: str, state, **info):
        self.events.append({"i": len(self.events), "kind": kind, "component": component,
                            "state_hash": state if isinstance(state, str) else scene_hash(state),
                            "t_s": round(time.perf_counter() - self.t0, 3), **info})


def evaluate_target(robot, cfg, state: vf.RepairState, action: dict, key: str) -> dict:
    """Plan the complete target skill afresh from the final achieved state: its joints,
    gripper gap, attachment (free after every verified retreat) and object poses. One
    call is one skill query with the declared internal schedule (skill2d budgets,
    planner caps). Goal achieved = placement within the goal tolerance."""
    t = time.perf_counter()
    if state.gap != robot.open_gap:
        return {"status": UNRESOLVED, "reason": "START_GRIPPER_OUT_OF_SKILL_SCOPE", "result": None, "seconds": 0.0}
    final = "home" if cfg["target_evaluation"]["final_connector"] == "HOME" else None
    res = sk.plan_skill(robot, state.scene, action["target_id"], action["goal_cell"], cfg, key, q_start=state.q,
                        q_goal=final)
    reached = res.status == VALID and res.place_error_m <= action["goal_tolerance_m"]
    return {"status": res.status if reached or res.status != VALID else UNRESOLVED, "reason": res.reason,
            "result": res, "goal_reached": bool(reached), "place_error_m": res.place_error_m,
            "start": {"q": list(state.q), "gripper_gap_m": state.gap, "attachment": "free"},
            "wall_clock_dependent": any(p.wall_clock_cut for _, p in res.plans), "seconds": round(time.perf_counter() - t, 2)}


def start(scene, query: dict) -> vf.RepairState:
    return vf.RepairState(scene, tuple(scene.robot.q_rad), scene.robot.gripper_gap_m, (), query["query_id"],
                          query["hashes"]["action_context"])


def witness_hash(s0: vf.RepairState, att: vf.Attempt, robot_hash: str) -> str:
    before = [s0] + att.states[:-1]
    return stable_hash([mo.trajectory_hash(r.traj.arrays(), o, scene_hash(b.scene), robot_hash)
                        for (o, _), r, b in zip(att.order, att.skills, before)])


def primary_episode(robot, cfg, query: dict, scene, ranked: list, target_eval, robot_hash: str,
                    trace: Trace | None = None) -> dict:
    """PROPOSE -> per candidate STATIC_CHECK, REPAIR_PLAN (clones) -> COMMIT the first
    relocation witness -> RELOCATE/REOBSERVE (replay on a clone, abort on deviation) ->
    one TARGET_EVALUATE from the achieved state -> FINISH. No candidate is tried after
    the commitment, whatever the target outcome."""
    tr, s0, act = trace or Trace(query["query_id"]), start(scene, query), query["learner"]["action"]
    obs = query["hashes"]["observation"]
    phash = stable_hash({"observation": obs, "action": query["hashes"]["action_context"],
                         "ranked": [[c["label"], sorted((o, solve.json_key(d)) for o, d in c["cells"].items())]
                                    for c in ranked]})
    tr.emit("PROPOSE", "proposal", obs, candidates=len(ranked), proposal_hash=phash)
    used, tried, commit = {"plans": 0}, [], None
    for rank, cand in enumerate(ranked):
        st = solve.static_endpoints(scene, cand["cells"], act["target_id"], cfg)
        tr.emit("STATIC_CHECK", "static_screen", scene, rank=rank, status=st["status"])
        row = {"rank": rank, "label": cand["label"], "cells": cand["cells"], "static": st, "plan": None}
        tried.append(row)
        if st["status"] != mo.VALID:
            continue
        plan = vf.plan_repair(robot, cfg, s0, cand["cells"], f"{query['query_id']}/primary/c{rank}", used)
        row["plan"] = plan
        tr.emit("REPAIR_PLAN", "relocation_planner", scene, rank=rank, orders=len(plan["attempts"]),
                relocation_plans=plan["relocation_plans"], stop=plan["stop"])
        if plan["witness"]:
            w = plan["witness"]
            commit = {"rank": rank, "label": cand["label"], "cells": cand["cells"], "order": [list(m) for m in w.order],
                      "witness_hash": witness_hash(s0, w, robot_hash), "proposal_hash": phash,
                      "source_observation_hash": obs, "attempt": w}
            tr.emit("COMMIT", "commitment", scene, rank=rank, witness_hash=commit["witness_hash"])
            break
        if plan["stop"] == "RELOCATION_BUDGET":
            break
    out = {"trace": tr, "tried": tried, "commit": commit, "target": None, "achieved": None}
    if commit is None:
        tr.emit("FINISH", "episode", scene, outcome="NO_REPAIR_WITNESS_WITHIN_BUDGET")
        return {**out, "outcome": "NO_REPAIR_WITNESS_WITHIN_BUDGET"}
    state, w = s0, commit["attempt"]
    for (oid, cell), res, nxt in zip(w.order, w.skills, w.states):       # execute = replay on a clone of S0
        ok = vf.replay_step(robot, cfg, state, oid, res, nxt)
        tr.emit("RELOCATE", "executor", state.scene, object=oid, cell=cell, certified=ok)
        tr.emit("REOBSERVE", "executor", nxt.scene, matches_commitment=ok)
        if not ok:
            tr.emit("ABORT", "episode", nxt.scene, reason="ACHIEVED_STATE_DEVIATES_FROM_COMMITMENT")
            return {**out, "outcome": "ABORTED"}
        state = nxt
    out["achieved"] = state
    tr.emit("TARGET_EVALUATE", "target_evaluator", state.scene, start_q=list(state.q), start_gap=state.gap)
    out["target"] = target_eval(state, f"{query['query_id']}/primary/target")
    outcome = "SUCCESS" if out["target"]["status"] == VALID else f"TARGET_{out['target']['status']}"
    tr.emit("FINISH", "episode", state.scene, outcome=outcome, target_reason=out["target"]["reason"])
    return {**out, "outcome": outcome}


def audit_candidate(robot, cfg, query: dict, scene, cand: dict, target_eval, key: str) -> dict:
    """OFFLINE_CASE_AUDIT (privileged teacher path; never feeds a primary episode). Static
    check, then non-dominated orders with their own memo and budget until the first
    complete relocation sequence, then one target evaluation from that order's own
    achieved state. Complete-assignment status: VERIFIED_FEASIBLE with a witness;
    CERTIFIED_INFEASIBLE only with a sound certificate; otherwise UNRESOLVED."""
    act, cells = query["learner"]["action"], cand["cells"]
    st = solve.static_endpoints(scene, cells, act["target_id"], cfg)
    row = {"label": cand["label"], "cells": cells, "moved": len(cells), "static": st, "orders": [],
           "goal_blockers": [], "certificate": None, "status": UNRESOLVED, "unknown_reason": None}
    if st["status"] != mo.VALID:
        row.update(status=INVALID if st["status"] == mo.INVALID else UNRESOLVED,
                   certificate="STATIC_ENDPOINT_INVALID" if st["status"] == mo.INVALID else None,
                   unknown_reason=None if st["status"] == mo.INVALID else "STATIC_GRAY_BAND")
        return row
    row["goal_blockers"] = solve.goal_blockers(scene, cells, act, cfg)
    s0 = start(scene, query)
    plan = vf.plan_repair(robot, cfg, s0, cells, key, {"plans": 0})
    for att in plan["attempts"]:                        # only the last can be a complete relocation
        o = {"attempt": att, "target": None}
        row["orders"].append(o)
        if att.status == vf.RELOCATED:
            o["target"] = target_eval(vf.final_state(s0, att), f"{key}/target")
            row["status"] = VALID if o["target"]["status"] == VALID else UNRESOLVED
    row["pruned_orders"], row["plan_stop"] = plan["pruned_orders"], plan["stop"]
    first = {a.order[0][0]: a for a in plan["attempts"] if a.stop == 0}
    pose_only = all(m in first and first[m].skills[0].status == INVALID
                    and first[m].skills[0].reason in ("NO_PICK_CANDIDATE", "NO_PLACE_CANDIDATE") for m in cells)
    if row["status"] == VALID:
        return row
    if row["goal_blockers"]:
        row.update(status=INVALID, certificate=f"GOAL_OVERLAP:{','.join(row['goal_blockers'])}")
    elif cells and pose_only:
        row.update(status=INVALID, certificate="FIRST_MOVER_POSE_ONLY_SCREEN_IN_S0")
    else:
        last = row["orders"][-1] if row["orders"] else None
        row["unknown_reason"] = (f"TARGET_{last['target']['status']}:{last['target']['reason']}" if last and last["target"]
                                 else f"RELOCATION_ORDERS:{plan['stop']}")
    return row
