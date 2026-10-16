"""G4A checks (instruction §11): certificate soundness, end policy, abort, automatic
candidates (allowlist, goal sensitivity, permutation), labels and masks, panels,
primary independence from the teacher, and the run.py split."""
import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import audit  # noqa: E402
import config as cf  # noqa: E402
import controls  # noqa: E402
import data  # noqa: E402
import evaluate as ev  # noqa: E402
import geometry as ge  # noqa: E402
import proposals as pr  # noqa: E402
import run  # noqa: E402
import skill as sk  # noqa: E402
from scene import place_scene  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


@pytest.fixture(scope="module")
def suite(robot, cfg):
    return controls.certificate_suite(robot, cfg)


def test_certificate_checker_accepts_sound_and_rejects_broken_premises(suite):
    bad = [c for c in suite if not c["as_expected"]]
    assert not bad, bad
    names = {c["case"]: c["accepted"] for c in suite}
    for case in ("stale object ID", "stale goal (action changed after production)", "contact rule altered: pushing allowed",
                 "altered radius after production", "assignment changed after production", "premise removed: no blocker named"):
        assert names[case] is False                                          # stale scope / removed premise
    assert names["goal occupied exactly (R2 all-stay)"] and names["R4 bound 2 (occupant o00 + pick certificate)"]
    assert all(c["accepted"] for c in suite if c["case"].startswith("G3.5"))  # archived proofs re-audited


def test_occupancy_proof_cannot_certify_a_region_with_an_alternative(cfg, suite):
    names = {c["case"]: c["accepted"] for c in suite}
    assert not names["goal region with a free escape pose"] and not names["goal tolerance 10 mm reaches a clear placement"]
    assert names["close to margin, clearance 4.0 mm < delta - eps"] and not names["close to margin, clearance 4.9 mm in the gray band"]
    s = place_scene(cfg, "x", "v", [18], [3, 13, 50, 45])
    act = data.make_query(cfg, "x", s, "t0", 45, {}, "SAFE_RETREAT")["learner"]["action"]
    assert pr.goal_blockers(s, {}, act, cfg) == ["o03"]
    esc = {**act, "goal_alternatives_xy": [list(s.lattice.center(47))]}
    assert pr.goal_blockers(s, {}, esc, cfg) == [] and pr.action_lower_bound(s, esc, cfg, set())["lower_bound"] == 0


def test_first_mover_proof_covers_every_mover_and_grasp(suite, robot, cfg):
    import certificates as cert
    s4 = place_scene(cfg, "c_r4", "initial", [20], [28, 27, 31, 58, 63])
    L4 = data.make_query(cfg, "c", s4, "t0", 28, {}, "SAFE_RETREAT")["learner"]
    two, n = {"o00": 29, "o01": 18}, len(sk.directions(sk.params(cfg)))
    omitted = {**cert.certificate_scope(s4, L4, two), "kind": "FIRST_MOVER", "movers": {"o00": {"stage": "PICK", "candidates": n}}}
    ok, why = cert.check(robot, s4, L4, two, omitted, cfg)                  # o01 not even listed as a mover
    assert not ok and any("do not cover every selected object" in w for w in why)
    names = {c["case"]: c for c in suite}
    assert not names["a selected object (o01) can go first"]["accepted"]
    assert not names["one declared grasp omitted from the record"]["accepted"]
    assert not names["start-dependent connector failure offered"]["accepted"]
    assert not names["planner timeout offered as a certificate"]["accepted"]
    assert not names["grasp family narrowed (12 directions) under the same record"]["accepted"]


def _r2(cfg):
    s = place_scene(cfg, "x", "v", [18], [3, 13, 50, 45])
    return s, data.make_query(cfg, "x", s, "t0", 45, {}, "SAFE_RETREAT")


def test_target_success_requires_safe_retreat_and_home_is_optional(cfg, robot, monkeypatch):
    s, q = _r2(cfg)
    act = q["learner"]["action"]
    st = ev.start(s, q)
    res, nxt = __import__("verify").relocate(robot, cfg, st, "o03", 60, "t")
    t = ev.evaluate_target(robot, cfg, nxt, act, "t/target")
    assert t["complete_target_status"] == sk.VERIFIED and t["goal_achieved"] and t["safe_retreat_status"] == sk.VERIFIED
    assert str(t["result"].traj.arrays()["phase"][-1]) == "retreat"
    monkeypatch.setattr(ev, "home_diagnostic", lambda *a, **k: {"status": sk.UNRESOLVED, "reason": "FORCED", "path": None})
    t2 = ev.evaluate_target(robot, cfg, nxt, act, "t/target")
    assert t2["home_return_status"] == sk.UNRESOLVED and t2["complete_target_status"] == sk.VERIFIED    # HOME never erases
    real = sk.plan_skill

    def truncated(*a, **k):                    # a record cut before its retreat must not count as success
        r = real(*a, **k)
        if r.traj is not None:                          # drop the trailing retreat segments (phase labels segments)
            n = sum(p == "retreat" for p in r.traj.phase)
            r.traj.q, r.traj.gap, r.traj.phase = r.traj.q[:-n], r.traj.gap[:-n], r.traj.phase[:-n]
        return r
    monkeypatch.setattr(sk, "plan_skill", truncated)
    t3 = ev.evaluate_target(robot, cfg, nxt, act, "t/target")
    assert t3["safe_retreat_status"] != sk.VERIFIED and t3["complete_target_status"] != sk.VERIFIED


def test_injected_deviation_aborts_without_forbidden_calls(robot, cfg):
    for f in controls.fault_injection(robot, cfg):
        if "within" in f["case"]:
            assert f["outcome"] == "SUCCESS" and f["target_calls"] == 1 and f["target_start_carries_observed_o01"]
        else:
            assert f["outcome"] == "ABORTED" and f["relocations_executed"] == 1 and f["target_calls"] == 0
            assert f["proposals"] == 1 and f["commits"] == 1 and f["events"][-1] == "ABORT"


def test_generator_uses_only_allowlisted_inputs_and_is_goal_sensitive(cfg):
    plan = json.loads((ROOT / "runs/g4a_evidence_audit/g4a_plan.json").read_text())
    q = plan["queries"][2]
    scene, query = audit.query_of(cfg, q)
    act = query["learner"]["action"]
    base = pr.generate_candidates(data.initial_scene(query), act, cfg)
    poisoned = {**query, "oracle_only": {"root_id": "LEAK", "stratum": "X", "blockers": ["o00"], "reference": "gamma"}}
    deleted = {k: v for k, v in query.items() if k != "oracle_only"}
    for qq in (poisoned, deleted):
        assert pr.generate_candidates(data.initial_scene(qq), qq["learner"]["action"], cfg) == base
    other = data.make_query(cfg, "g", scene, "t0", next(c for c in range(64) if c not in {o.cell for o in scene.objects}),
                            {}, "SAFE_RETREAT")
    assert pr.generate_candidates(data.initial_scene(other), other["learner"]["action"], cfg)["candidates"] != base["candidates"]


def test_generator_permutation_maps_to_the_same_physical_assignments(cfg):
    s = place_scene(cfg, "p", "v", [18], [45, 44, 37, 13, 60, 3])
    act = data.make_query(cfg, "p", s, "t0", 45, {}, "SAFE_RETREAT")["learner"]["action"]
    ids = [o.id for o in s.objects if o.kind == "obstacle"]
    perm = dict(zip(ids, reversed(ids)))                                    # relabel obstacles
    s2 = replace(s, objects=tuple(replace(o, id=perm.get(o.id, o.id)) for o in s.objects))

    def physical(scene, gen):
        return sorted(tuple(sorted((scene.get(o).cell, d) for o, d in c["cells"].items())) for c in gen["candidates"])
    g1, g2 = pr.generate_candidates(s, act, cfg), pr.generate_candidates(s2, act, cfg)
    assert physical(s, g1) == physical(s2, g2) and g1["geometry_seed"] == g2["geometry_seed"]


def test_label_masks_aggregation_and_contradiction():
    P, N, U = data.POSITIVE, data.NEGATIVE, data.UNKNOWN
    assert data.aggregate([{"kind": "order_attempt", "status": "UNRESOLVED", "source": "x"}])["label"] == U
    assert data.aggregate([{"kind": "certificate", "validated": False, "certificate": "GOAL_OVERLAP", "source": "x"}])["label"] == U
    assert data.aggregate([{"kind": "complete_witness", "source": "a"}])["label"] == P
    assert data.aggregate([{"kind": "complete_witness", "source": "a"},
                           {"kind": "certificate", "validated": True, "certificate": "FIRST_MOVER", "source": "b"}])["label"] \
        == data.CONTRADICTION
    m = data.label_masks([P, N, U, P])
    assert m["y"].tolist() == [1, 0, 0, 1] and m["binary_mask"].tolist() == [True, True, False, True]
    assert m["joint_pool_mask"].tolist() == [True, True, False, True]
    assert not data.label_masks([P, U])["joint_pool_mask"].any()                    # no mixed pool -> no joint term
    with pytest.raises(ValueError):
        data.label_masks([P, data.CONTRADICTION])


def test_seed_panel_holds_state_and_budget_fixed(cfg, monkeypatch):
    s, q = _r2(cfg)
    plan_q = {"query_id": "x", "root_id": "x", "stratum": "S", "seed": 0, "scene": __import__("scene").scene_to_dict(s),
              "goal_cell": 45, "hashes": q["hashes"]}
    monkeypatch.setattr(audit, "query_of", lambda c, qq: (s, {**q, "query_id": "x"}))
    seen = []

    def spy(robot, c, state, act, key):
        seen.append((state, json.dumps(c, sort_keys=True), key, act.get("end_policy")))
        return {"status": sk.UNRESOLVED, "reason": "SPY", "result": None, "seconds": 0.0}
    monkeypatch.setattr(ev, "evaluate_target", spy)
    st = ev.start(s, q)
    out = audit.seed_case((cfg, {"query_id": "x", "cells": {}, "keys": [f"k{i}" for i in range(5)]}, plan_q, st))
    runs = [x for x in seen if x[3] == "SAFE_RETREAT"]
    assert len(runs) == 5 and all(x[0] is st for x in runs) and len({x[1] for x in runs}) == 1
    assert len({x[2] for x in runs}) == 5 and len(out["runs"]) == 5 and out["home_required"]["status"] == sk.UNRESOLVED


def test_primary_never_adopts_the_teachers_candidate(cfg, robot):
    s, q = _r2(cfg)
    ranked = [{"label": "a", "cells": {"o03": 60}}, {"label": "b", "cells": {"o03": 38}}]

    def target(state, key):                            # primary's own choice fails; the teacher's alternative succeeds
        return {"status": sk.UNRESOLVED if "primary" in key else sk.VERIFIED, "reason": "STUB", "result": None}
    teacher = ev.audit_candidate(robot, cfg, q, s, ranked[1], target, "x/audit/b")
    out = ev.primary_episode(robot, cfg, q, s, ranked, target, cf.robot_profile_hash(cfg))
    kinds = [e["kind"] for e in out["trace"].events]
    assert teacher["status"] == sk.VERIFIED and out["commit"]["label"] == "a" and kinds.count("COMMIT") == 1
    assert out["outcome"] == "TARGET_UNRESOLVED" and kinds.count("TARGET_EVALUATE") == 1


def test_run_split_keeps_cli_and_replay(tmp_path):
    import argparse
    seen = {}
    real = argparse.ArgumentParser.parse_args

    def capture(self, argv=None, namespace=None):
        a = real(self, argv, namespace)
        seen["func"] = a.func
        raise SystemExit(0)
    for argv, owner in ((["scene", "--case", "G0_ILLUSTRATIVE", "--out", "x"], "viz"), (["check", "--out", "x"], "figures"),
                        (["intervene", "--out", "x"], "intervention_figures"), (["solve", "--out", "x"], "assignment_figures"),
                        (["case-analysis", "--out", "x"], "case_figures"), (["g4a-audit", "--out", "x"], "audit"),
                        (["replay", "--run", "x"], "run")):
        argparse.ArgumentParser.parse_args = capture
        try:
            with pytest.raises(SystemExit):
                run.main(argv)
        finally:
            argparse.ArgumentParser.parse_args = real
        assert seen["func"].__module__ == owner
    for arch in ("g2_interventions", "g3_5_initial_scene"):       # archives predating G4A config sections / keys
        assert run.main(["replay", "--run", str(ROOT / "runs" / arch), "--report", str(tmp_path / f"{arch}.json")]) == 0
        assert json.loads((tmp_path / f"{arch}.json").read_text())["replay_passed"]
    assert json.loads((tmp_path / "g3_5_initial_scene.json").read_text())["config_keys_filled_from_current"] == {
        "target_evaluation": ["end_policy", "home_return_diagnostic"]}
