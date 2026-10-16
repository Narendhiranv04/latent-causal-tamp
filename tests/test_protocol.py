"""G3.5 contract tests (G3_5 instruction §9): INITIAL_SCENE_ONE_SHOT_V1 needs no frozen
path, privileged fields cannot reach learner inputs, no target feedback before commit
or between relocations, achieved-state target start, evidence kept separate."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cases  # noqa: E402
import config as cf  # noqa: E402
import data  # noqa: E402
import evaluate as ev  # noqa: E402
import geometry as ge  # noqa: E402
import interventions as iv  # noqa: E402
import motion as mo  # noqa: E402
import skill as sk  # noqa: E402
import proposals as pr  # noqa: E402
import verify as vf  # noqa: E402
from scene import scene_hash  # noqa: E402

FX = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


def query_of(cfg, name, oracle=None):
    fx = FX[name]
    scene, prov = cases.build_scene(cfg, fx)
    return scene, data.make_query(cfg, name, scene, fx["action"]["target"], fx["action"]["goal_cell"],
                                  prov if oracle is None else oracle)


class Spy:
    """Target callback recording the trace length at each call; returns `status`."""
    def __init__(self, trace, status):
        self.calls, self.trace, self.status = [], trace, status

    def __call__(self, state, key):
        self.calls.append((len(self.trace.events), state))
        return {"status": self.status, "reason": "SPY", "result": None}


def run_primary(robot, cfg, scene, query, ranked, status):
    trace = ev.Trace(query["query_id"])
    spy = Spy(trace, status)
    return ev.primary_episode(robot, cfg, query, scene, ranked, spy, cf.robot_profile_hash(cfg), trace), spy


def test_new_protocol_query_needs_no_reference_path(cfg, robot):
    scene, q = query_of(cfg, "G35_R2_GOAL", oracle={})
    assert set(q) == {"protocol", "query_id", "learner", "labels", "oracle_only", "hashes"}
    blob = json.dumps(q["learner"])
    for word in ("gamma", "envelope", "trajectory", "action_hash", "root_id", "reference"):
        assert word not in blob
    ranked = pr.rank_proposals(data.initial_scene(q), q["learner"]["action"], FX["G35_R2_GOAL"]["candidates"], cfg)
    assert ranked and ranked[0]["cells"] == {"o03": 60}        # all-stay screened out: goal provably occupied
    bad = copy.deepcopy(cf.load_config(ROOT / "config.toml"))
    for sec, key, val in (("protocol", "target_reference_required", True), ("protocol", "target_calls_between_relocations", 1),
                          ("protocol", "proposal_observation", "REFRESH"), ("target_evaluation", "start_state", "HOME")):
        c = copy.deepcopy(bad)
        c[sec][key] = val
        with pytest.raises(cf.ConfigError):
            cf.validate_config(c)


def test_privileged_fields_cannot_change_learner_inputs_or_proposals(cfg):
    scene, q = query_of(cfg, "G35_R1_D1BLOCK")
    assert cases.poison_check(q, 64)["tensors_unchanged_after_poison_and_delete"]
    poisoned = {**q, "oracle_only": {"reference_action_hash": "x", "blockers": ["o02"], "root_id": "leak"}}
    cands = FX["G35_R1_D1BLOCK"]["candidates"]
    assert pr.rank_proposals(data.initial_scene(q), q["learner"]["action"], cands, cfg) == \
        pr.rank_proposals(data.initial_scene(poisoned), poisoned["learner"]["action"], cands, cfg)
    goal2 = data.make_query(cfg, "g", scene, "t0", 46, {})
    assert goal2["hashes"]["action_context"] != q["hashes"]["action_context"]
    assert goal2["hashes"]["observation"] == q["hashes"]["observation"]
    assert not np.array_equal(data.learner_tensors(goal2, 64)["goal_xy"], data.learner_tensors(q, 64)["goal_xy"])


def test_no_target_call_before_commit_or_between_moves_and_no_retry(cfg, robot):
    """Two viable candidates; the spy target fails. One call, after COMMIT and after the
    last RELOCATE; no STATIC_CHECK/REPAIR_PLAN/COMMIT after it (no fallback)."""
    scene, q = query_of(cfg, "G35_R2_GOAL", oracle={})
    ranked = [{"label": "a", "cells": {"o03": 60}}, {"label": "b", "cells": {"o03": 38}}]
    out, spy = run_primary(robot, cfg, scene, q, ranked, sk.UNRESOLVED)
    kinds = [e["kind"] for e in out["trace"].events]
    assert len(spy.calls) == 1 and out["outcome"] == "TARGET_UNRESOLVED"
    at = spy.calls[0][0]
    assert kinds[:at].count("COMMIT") == 1 and "TARGET_EVALUATE" == kinds[at - 1]
    assert max(i for i, k in enumerate(kinds) if k == "RELOCATE") < at
    assert not {"STATIC_CHECK", "REPAIR_PLAN", "COMMIT", "PROPOSE"} & set(kinds[at:])
    assert kinds.count("COMMIT") == 1 and [t["rank"] for t in out["tried"]] == [0]


def test_target_starts_at_actual_last_relocation_state(cfg, robot):
    """End-to-end real planning: relocation o03 60 then the complete target skill."""
    scene, q = query_of(cfg, "G35_R2_GOAL", oracle={})
    act = q["learner"]["action"]
    out = ev.primary_episode(robot, cfg, q, scene, [{"label": "a", "cells": {"o03": 60}}],
                             lambda s, k: ev.evaluate_target(robot, cfg, s, act, k), cf.robot_profile_hash(cfg))
    assert out["outcome"] == "SUCCESS" and out["target"]["goal_reached"]
    st, arr = out["achieved"], out["target"]["result"].traj.arrays()
    assert np.array_equal(arr["q"][0], np.asarray(st.q)) and arr["gap"][0] == st.gap == robot.open_gap
    assert not np.allclose(st.q, robot.q_home)                          # really the retreat end, not home
    w = out["commit"]["attempt"]
    assert str(w.skills[-1].traj.arrays()["phase"][-1]) == "retreat"     # no connector to a reference start
    assert st.moved == ("o03",) and out["trace"].events[-1]["outcome"] == "SUCCESS"
    assert scene_hash(scene) == scene_hash(cases.build_scene(cfg, FX["G35_R2_GOAL"])[0])   # live S0 untouched


def test_static_validity_and_timeouts_never_become_labels(cfg, robot):
    scene, q = query_of(cfg, "G35_R1_D1BLOCK")
    stub = lambda s, k: {"status": sk.UNRESOLVED, "reason": "PLANNER_BUDGET", "result": None}   # noqa: E731
    row = ev.audit_candidate(robot, cfg, q, scene, {"label": "all-stay", "cells": {}}, stub, "t")
    assert row["static"]["status"] == mo.VALID and row["status"] == sk.UNRESOLVED and row["certificate"] is None
    s4, q4 = query_of(cfg, "G35_R4_ACCESS")
    stuck = ev.audit_candidate(robot, cfg, q4, s4, {"label": "o00 first", "cells": {"o00": 29}}, stub, "t4")
    assert stuck["static"]["status"] == mo.VALID and stuck["status"] != sk.VERIFIED   # no relocation witness
    r = {"audit": [row], "primary": {"outcome": "TARGET_UNRESOLVED"}, "bound": pr.action_lower_bound(scene, q["learner"]["action"], cfg, set())}
    b = cases.bounds(r)
    assert (b["lower_bound"], b["upper_bound"], b["minimality"]) == (0, None, "MINIMUM_UNRESOLVED")


def test_frozen_blocker_count_is_not_a_new_lower_bound(cfg, robot):
    scene, q = query_of(cfg, "G35_R1_D1BLOCK")
    frozen, _ = iv.load_archived("runs/g2_interventions", "G2_D1")
    snap = iv.evaluate(robot, cfg, frozen, iv.Snapshot("x", None, None, scene))
    assert snap.F == mo.INVALID                                         # the frozen path is blocked by o02 ...
    assert pr.action_lower_bound(scene, q["learner"]["action"], cfg, set())["lower_bound"] == 0   # ... LB stays 0
    s2, q2 = query_of(cfg, "G35_R2_GOAL")
    assert pr.action_lower_bound(s2, q2["learner"]["action"], cfg, set())["lower_bound"] == 1
    s4, q4 = query_of(cfg, "G35_R4_ACCESS")
    cert = sk.pick_certificate(robot, s4, "o00", cfg)
    assert cert is not None and cert.status == sk.INFEASIBLE
    assert pr.action_lower_bound(s4, q4["learner"]["action"], cfg, {"o00"})["lower_bound"] == 2


def test_rejected_order_does_not_exclude_the_assignment(cfg, robot):
    scene, q = query_of(cfg, "G35_R4_ACCESS")
    ok = lambda s, k: {"status": sk.VERIFIED, "reason": "STUB", "result": None}    # noqa: E731
    row = ev.audit_candidate(robot, cfg, q, scene, {"label": "x", "cells": {"o00": 29, "o01": 18}}, ok, "r4")
    first, last = row["orders"][0]["attempt"], row["orders"][-1]["attempt"]
    assert first.order[0][0] == "o00" and first.stop == 0 and first.skills[0].reason == "NO_PICK_CANDIDATE"
    assert last.order[0][0] == "o01" and last.status == vf.RELOCATED and row["status"] == sk.VERIFIED
    assert row["certificate"] is None
    single = ev.audit_candidate(robot, cfg, q, scene, {"label": "y", "cells": {"o00": 29}}, ok, "r4s")
    assert single["goal_blockers"] == [] and single["status"] == sk.INFEASIBLE      # o00 alone cannot move first
    assert single["certificate"] == "FIRST_MOVER_POSE_ONLY_SCREEN_IN_S0"
    unknown = lambda s, k: {"status": sk.UNRESOLVED, "reason": "STUB", "result": None}    # noqa: E731
    both = ev.audit_candidate(robot, cfg, q, scene, {"label": "z", "cells": {"o00": 29, "o01": 18}}, unknown, "r4u")
    assert both["status"] == sk.UNRESOLVED and both["certificate"] is None   # o01 can move first: no certificate


def test_move_once_history_and_clone_isolation(cfg, robot):
    scene, q = query_of(cfg, "G35_R2_GOAL", oracle={})
    s0, before = ev.start(scene, q), scene_hash(scene)
    att = vf.realize(robot, vf.repair_cfg(cfg), s0, (("o03", 60), ("o03", 38)), {}, "mo")
    assert att.stop == 1 and att.skills[1].reason == "MOVE_ONCE_VIOLATION" and att.states[0].moved == ("o03",)
    assert scene_hash(s0.scene) == before and s0.moved == ()
    used = {"plans": 0}
    plan = vf.plan_repair(robot, cfg, s0, {}, "empty", used)
    assert plan["witness"].status == vf.RELOCATED and plan["witness"].states == [] and used["plans"] == 0


def test_frozen_control_semantics_unchanged(cfg, robot):
    """Legacy execute still ends at gamma_0's exact start; the new mode ends at retreat."""
    frozen, snaps = iv.load_archived("runs/g2_interventions", "G2_D1")
    s0 = vf.start_state(snaps["block_a"], frozen, "legacy")
    att = vf.execute(robot, vf.repair_cfg(cfg), frozen, s0, 0, 1, (("o02", 43),), {}, "legacy")
    assert att.status == vf.EXECUTABLE
    assert np.array_equal(att.skills[-1].traj.arrays()["q"][-1], frozen.arrays["q"][0])
    frozen.verify()
    new = vf.realize(robot, vf.repair_cfg(cfg), s0, (("o02", 43),), {}, "new")
    assert new.status == vf.RELOCATED and str(new.skills[-1].traj.arrays()["phase"][-1]) == "retreat"
