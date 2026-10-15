"""G3 executable-repair tests: real 3R relocations from the achieved state, move-once
history, exact gamma_0 start, unchanged frozen action, bounds that never over-claim."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import geometry as ge  # noqa: E402
import interventions as iv  # noqa: E402
import motion as mo  # noqa: E402
import skill as sk  # noqa: E402
import solve  # noqa: E402
import verify as vf  # noqa: E402

FX = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


def prepared(robot, cfg, name):
    frozen, ref, scene, _ = vf.blocked_state(robot, cfg, name, FX[name])
    status = solve.cell_status(robot, cfg, frozen, scene)
    terminal = solve.a0(scene, solve.domains(scene, "ALL_SUPPORTED"), status, cfg["repair2d"]["k_best"],
                        cfg["suite"]["margin_m"])
    return frozen, ref, scene, status, terminal


@pytest.fixture(scope="module")
def d1(robot, cfg):
    """Archived G2 D1 blocked state (o02 blocks the frozen action), searched once."""
    frozen, ref, scene, status, terminal = prepared(robot, cfg, "G3_D1")
    before = {k: v.copy() for k, v in frozen.arrays.items()}
    return frozen, ref, scene, status, terminal, vf.search(robot, cfg, frozen, scene, terminal, "test_d1"), before


@pytest.fixture(scope="module")
def d3(robot, cfg):
    frozen, ref, scene, status, terminal = prepared(robot, cfg, "G3_D3")
    return frozen, scene, terminal, vf.search(robot, cfg, frozen, scene, terminal, "test_d3")


def test_one_relocation_continues_from_the_achieved_state(cfg, robot, d1):
    frozen, _, scene, status, terminal, _, _ = d1
    s0 = vf.start_state(scene, frozen, "t")
    oid, cell = solve.moves_of(scene, terminal["assignments"][0]["cells"])[0]
    res, s1 = vf.relocate(robot, vf.repair_cfg(cfg), s0, oid, cell, "unit")
    assert res.status == sk.VERIFIED and s1.moved == (oid,)
    arr = res.traj.arrays()
    assert np.array_equal(arr["q"][0], np.asarray(s0.q))                       # planned from the actual state
    assert s1.q == tuple(arr["q"][-1]) and s1.gap == float(arr["gap"][-1])     # next state = achieved end
    assert s1.scene.get(oid).xy_m == tuple(arr["place_xy"]) and s1.scene.get(oid).cell == cell
    assert all(o == scene.get(o.id) for o in s1.scene.objects if o.id != oid)  # nothing else moved
    assert all(v.status == ge.CLEAR for v in mo.certify_trajectory(robot, scene, oid, arr, *iv._params(cfg)))
    again, s2 = vf.relocate(robot, cfg, s1, oid, 50 if cell != 50 else 43, "unit2")   # move-once history
    assert s2 is None and again.reason == "MOVE_ONCE_VIOLATION" and again.status == sk.INFEASIBLE


def test_d1_minimum_certified_with_exact_gamma0_start_and_replay(cfg, robot, d1):
    frozen, ref, scene, _, terminal, out, before = d1
    w = out["witness"]
    assert out["status"] == vf.EXECUTABLE and out["lower_bound"] == out["upper_bound"] == 1
    assert out["minimality"] == "MINIMUM_CERTIFIED" and w.cost == len(w.order) == 1
    assert np.array_equal(w.skills[-1].traj.arrays()["q"][-1], frozen.arrays["q"][0])   # exact gamma_0 start
    assert w.final.F == mo.VALID and w.final.whole_replay == mo.VALID
    frozen.verify()                                                            # gamma_0 never replanned
    assert all(np.array_equal(before[k], frozen.arrays[k]) for k in before)
    assert w.states[-1].scene.get("t0") == scene.get("t0") == ref.get("t0")
    s0 = vf.start_state(scene, frozen, "t")
    assert vf.replay_repair(robot, cfg, frozen, s0, w)["replay_passed"]


def test_replay_rejects_tampered_episodes(cfg, robot, d1):
    frozen, _, scene, _, _, out, _ = d1
    w, s0 = out["witness"], vf.start_state(scene, frozen, "t")
    oid = w.order[0][0]
    moved_obj = replace(w.states[0].scene.get(oid), xy_m=(0.5, 0.5), cell=None)
    bad_scene = replace(w.states[0].scene, objects=tuple(moved_obj if o.id == oid else o for o in w.states[0].scene.objects))
    for bad in (replace(w, states=[replace(w.states[0], scene=bad_scene)]),          # achieved pose differs
                replace(w, states=[replace(w.states[0], moved=())]),                   # history dropped
                replace(w, states=[replace(w.states[0], q=tuple(np.add(w.states[0].q, 1e-3)))]),  # q != record end
                replace(w, states=[replace(w.states[0], gap=w.states[0].gap / 2)])):    # gripper != record end
        assert not vf.replay_repair(robot, cfg, frozen, s0, bad)["replay_passed"]
    other = iv.FrozenAction(frozen.target_id, {**frozen.arrays, "q": frozen.arrays["q"] + 1e-3},
                            frozen.reference_scene_hash, frozen.robot_profile_hash, frozen.action_hash)
    with pytest.raises(ValueError):
        vf.replay_repair(robot, cfg, other, s0, w)                             # a different gamma_0


def test_failed_order_keeps_first_offence_and_is_not_a_proof(cfg, robot, d1):
    """Occupied preferred destination on D1: o02 into o03's cell. The o02-first order
    fails at its first relocation (destination occupied); o03-first executes. The
    verified cost (2) exceeds the lower bound (1), so it is not claimed minimal."""
    frozen, _, scene, status, _, _, _ = d1
    dom = solve.domains(scene, "ALL_SUPPORTED")
    plan = solve.forced(scene, dom, status, "o02", scene.get("o03").cell)
    terminal = {"lower_bound": 1, "hall": None, "assignments": [plan]}
    out = vf.search(robot, cfg, frozen, scene, terminal, "test_forced")
    first, last = out["attempts"][0], out["attempts"][-1]
    assert first.order[0][0] == "o02" and first.stop == 0 and first.states == []
    assert first.status == vf.UNRESOLVED and first.reason.startswith(f"o02->{scene.get('o03').cell}")
    assert first.skills[0].status == sk.INFEASIBLE
    assert last.order[0][0] == "o03" and last.status == vf.EXECUTABLE
    assert out["upper_bound"] == 2 and out["lower_bound"] == 1 and out["minimality"] == "MINIMUM_UNRESOLVED"


def test_bounds_and_budget_never_overclaim(cfg, robot, d1):
    frozen, _, scene, _, terminal, _, _ = d1
    none = vf.search(robot, cfg, frozen, scene, {"lower_bound": 1, "hall": None, "assignments": []}, "t")
    assert (none["status"], none["upper_bound"], none["minimality"]) == (vf.UNRESOLVED, None, "MINIMUM_UNRESOLVED")
    hall = vf.search(robot, cfg, frozen, scene, {"lower_bound": None, "hall": {"objects": ["o02"]}, "assignments": []}, "t")
    assert (hall["status"], hall["minimality"]) == (vf.TERMINAL_INFEASIBLE, "NOT_APPLICABLE")
    occupied = {"cost": 1, "cells": {**terminal["assignments"][0]["cells"], "o02": scene.get("o03").cell}}
    tight = {**cfg, "repair2d": {**cfg["repair2d"], "max_relocations": 1}}
    out = vf.search(robot, tight, frozen, scene, {**terminal, "assignments": [occupied] + terminal["assignments"]}, "t")
    assert out["stop_reason"] == "RELOCATION_BUDGET" and out["status"] == vf.UNRESOLVED
    assert out["upper_bound"] is None and out["minimality"] == "MINIMUM_UNRESOLVED"


def test_d3_order_decides_access(cfg, robot, d3):
    """Same terminal assignment, two orders: the blocked-access order fails at its first
    pick, the other executes. Minimum certified from the A0 bound."""
    frozen, scene, terminal, out = d3
    w = out["witness"]
    assert out["status"] == vf.EXECUTABLE and out["minimality"] == "MINIMUM_CERTIFIED" and out["upper_bound"] == 2
    same = [a for a in out["attempts"] if set(a.order) == set(w.order) and a.order != w.order]
    assert same and same[0].status == vf.UNRESOLVED and same[0].stop == 0
    assert w.states[0].moved == (w.order[0][0],) and w.states[1].moved == tuple(o for o, _ in w.order)
    assert np.array_equal(w.skills[1].traj.arrays()["q"][0], np.asarray(w.states[0].q))   # state continuity
    s0 = vf.start_state(scene, frozen, "t")
    assert vf.replay_repair(robot, cfg, frozen, s0, w)["replay_passed"]
    mid = replace(w, states=[replace(w.states[0], gap=w.states[0].gap / 2), w.states[1]])   # mid-episode gripper
    assert not vf.replay_repair(robot, cfg, frozen, s0, mid)["replay_passed"]


def test_dominated_orders_are_pruned_not_counted(cfg):
    memo = {((("a", 1),), False): (None, None)}                  # 'a first' already failed
    pruned = []
    got = list(vf.fresh_orders([("a", 1), ("b", 2), ("c", 3)], memo, 10, pruned))
    assert len(got) == 4 and all(o[0][0] != "a" for o in got) and len(pruned) == 2
    assert len(list(vf.fresh_orders([("a", 1), ("b", 2), ("c", 3)], {}, 3, []))) == 3


def test_a0_terminal_valid_agrees_with_the_original_terminal_oracle(cfg, robot, d1):
    """A0's certified assignments, placed by substitution (terminal check only, no
    motion), satisfy the full G2 fixed-action oracle; the blocked source is INVALID."""
    frozen, _, scene, status, terminal, _, _ = d1
    assert status[scene.get("o02").cell] == mo.INVALID and scene.get("t0").cell not in status
    for a in terminal["assignments"][:3]:
        objs = tuple(replace(o, xy_m=scene.lattice.center(a["cells"][o.id]), cell=a["cells"][o.id])
                     if o.id in a["cells"] else o for o in scene.objects)
        snap = iv.evaluate(robot, cfg, frozen, iv.Snapshot("a0", None, None, replace(scene, objects=objs)))
        assert snap.F == mo.VALID and snap.whole_replay == mo.VALID


def test_relocation_planning_is_deterministic(cfg, robot, d1):
    frozen, _, scene, _, terminal, _, _ = d1
    s0 = vf.start_state(scene, frozen, "t")
    oid, cell = solve.moves_of(scene, terminal["assignments"][0]["cells"])[0]
    a, _ = vf.relocate(robot, vf.repair_cfg(cfg), s0, oid, cell, "det")
    b, _ = vf.relocate(robot, vf.repair_cfg(cfg), s0, oid, cell, "det")
    assert a.status == b.status == sk.VERIFIED
    assert all(np.array_equal(a.traj.arrays()[k], b.traj.arrays()[k]) for k in a.traj.arrays())
