"""G4C-D2-P3a: LINK0_SECTOR_PICK_V1 producer/checker. Synthetic geometry, counterexamples,
tampering, scope, fail-closed boundaries, saved-positive noncontradiction and zero-call
guards. No planner, skill, target or relocation call is allowed (guards raise)."""
import copy
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import geometry as ge  # noqa: E402
import sector_cert as scp  # noqa: E402
import sector_check as sc  # noqa: E402
import skill as sk  # noqa: E402
from scene import Obj, place_scene  # noqa: E402

CFG = cf.load_config(ROOT / "config.toml")
ROBOT = ge.make_robot(CFG)


@pytest.fixture(autouse=True)
def guards(monkeypatch):
    calls, ops = scp.guard_and_count(monkeypatch.setattr)
    yield calls, ops
    assert not any(calls.values()), calls


def _src(s, scope="CONTROL_FIXED_START", moved="t0", seq=(), kind="CONTROL", h=None):
    return {"scene": s, "scope": scope, "moved": moved, "sequence": list(seq), "kind": kind, "expected_hash": h}


def _run(s, scope="CONTROL_FIXED_START", **k):
    rec = scp.produce(ROBOT, CFG, s, k.get("moved", "t0"), scope, list(k.get("seq", ())), 7)
    return rec, sc.check(ROBOT, CFG, rec, _src(s, scope, **k))


@pytest.fixture(scope="module")
def blocked():
    return place_scene(CFG, "syn", "v", [7], [42])   # barrier 19.4 deg, rho 0.361 m; proof needs sector AND in-sector screens


def test_fixture_certifies_with_every_candidate_proved(blocked, guards):
    rec, chk = _run(blocked)
    assert rec["claim"] == chk["verdict"] == "CERTIFIED_INFEASIBLE" and chk["reasons"] == [] and all(chk["excluded"])
    assert len(rec["candidates"]) == 48 and {b[0] for b in rec["barriers"]} == {"o00"}
    assert rec["place_sector_diag"]["released"] is False and guards[1]["screen_pick"] == 2   # producer + checker
    open_ = place_scene(CFG, "syn", "v", [15], [42])
    assert _run(open_)[1]["verdict"] == "UNKNOWN"                   # some candidate in the sector passes / unproved


def _moved_obstacle(s, rho):
    a = math.radians(24.8)
    xy = (ROBOT.base[0] + rho * math.cos(a), ROBOT.base[1] + rho * math.sin(a))
    return replace(s, objects=tuple(Obj(x.id, x.kind, x.radius_m, xy, None) if x.id == "o00" else x for x in s.objects))


def test_annulus_boundary_fails_closed(blocked):
    k = sc.constants(ROBOT, CFG)
    r0 = k["L1"] + max(k["w0_half"], k["housing_r"]) + 0.024 + k["delta"] - k["eps"]
    assert abs(r0 - 0.4608) < 1e-12
    for rho, barrier in ((r0 + 0.004, False), (r0 - 0.004, True), (r0 - 0.5 * sc.TAU, False), (r0, False)):
        s = _moved_obstacle(blocked, rho)
        bars, _ = sc.sector(ROBOT, CFG, s, s.robot.q_rad[0])
        assert bool(bars) is barrier and bool(scp._sector(ROBOT, CFG, s, s.robot.q_rad[0])[0]) is barrier
    assert _run(_moved_obstacle(blocked, 0.465))[1]["verdict"] == "UNKNOWN"   # C7: rho 0.465 m is no premise


def test_two_sided_sector_and_start_on_barrier(blocked):
    s = place_scene(CFG, "syn", "v", [7], [41, 56])          # barriers at 24.8 and 57.3 deg around... q0 = 90 deg
    _, (lo, hi) = sc.sector(ROBOT, CFG, s, s.robot.q_rad[0])
    assert math.isclose(math.degrees(lo), 57.3, abs_tol=0.1) and math.isclose(hi, ROBOT.limits[0][1])
    _, (lo, hi) = sc.sector(ROBOT, CFG, s, math.radians(40.0))   # start between them: both sides bounded
    assert math.isclose(math.degrees(lo), 24.8, abs_tol=0.1) and math.isclose(math.degrees(hi), 57.3, abs_tol=0.1)
    with pytest.raises(ValueError):
        sc.sector(ROBOT, CFG, s, math.atan2(s.get("o00").xy_m[1] - ROBOT.base[1], s.get("o00").xy_m[0] - ROBOT.base[0]))


def test_gray_band_in_sector_candidate_blocks_the_certificate(blocked, monkeypatch):
    rec, _ = _run(blocked)
    only = [i for i, c in enumerate(rec["candidates"]) if c["excluded_by"] and all(e.startswith("DEFINITE") for e in c["excluded_by"])]
    assert only, "fixture needs an in-sector candidate excluded only by a definite screen"
    real = sk.screen_pick

    def gray(*a, **k):
        out = real(*a, **k)
        out[only[0]].certified = False                     # the same rejection, now in the gray band
        return out
    monkeypatch.setattr(sk, "screen_pick", gray)
    rec2, chk2 = _run(blocked)
    assert rec2["claim"] == chk2["verdict"] == "UNKNOWN" and chk2["unexcluded"] == [only[0]]
    forged = copy.deepcopy(rec2)
    forged["candidates"][only[0]]["excluded_by"] = rec["candidates"][only[0]]["excluded_by"]
    forged["claim"] = "CERTIFIED_INFEASIBLE"
    chk3 = sc.check(ROBOT, CFG, forged, _src(blocked))
    assert not chk3["accepted"] and any("does not hold" in r for r in chk3["reasons"])


def _tamper(rec, how):
    r = copy.deepcopy(rec)
    c = r["candidates"]
    if how == "drop":
        c.pop()
    elif how == "duplicate":
        c[1] = copy.deepcopy(c[0])
    elif how == "reorder":
        c[0], c[1] = c[1], c[0]
    elif how == "branch":
        c[3]["branch"] = -c[3]["branch"]
    elif how == "phi":
        c[3]["phi"] += 1e-6
    elif how == "ik_q":
        k = next(i for i, x in enumerate(c) if x["q"] is not None)
        c[k]["q"][0] += 1e-6
    elif how == "nominal_path_pseudo_proof":
        k = next(i for i, x in enumerate(c) if x["excluded_by"])
        c[k]["excluded_by"] = ["NOMINAL_PATH_COLLISION"]
    elif how == "place_screen_reason":
        k = next(i for i, x in enumerate(c) if x["excluded_by"])
        c[k]["excluded_by"] = ["DEFINITE_PLACE_SCREEN"]
    elif how == "false_sector":
        k = next(i for i, x in enumerate(c) if x["excluded_by"] and "SECTOR" not in x["excluded_by"] and x["q"] is not None)
        c[k]["excluded_by"] = ["SECTOR"]
    elif how == "screen_record":
        c[5]["screen"]["certified"] = not c[5]["screen"]["certified"]
    elif how == "start_q":
        r["start"]["q"][1] += 1e-3
    elif how == "gap":
        r["start"]["gap"] = 0.05
    elif how == "attachment":
        r["start"]["attachment"] = "held"
    elif how == "world":
        r["world"] = r["world"][1:]
    elif how == "scene_hash":
        r["scene_hash"] = "sha256:0"
    elif how == "profile":
        r["profile"]["robot_profile_hash"] = "sha256:0"
    elif how == "collision_policy":
        r["constants"]["delta"] = 0.004
    elif how == "barriers":
        r["barriers"] = []
    elif how == "sector":
        r["sector"][0] -= 0.1
    elif how == "version":
        r["version"] = "LINK0_SECTOR_PICK_V0"
    elif how == "scope":
        r["query"]["scope"] = "ORIGINAL_TARGET"
    return r


@pytest.mark.parametrize("how", ["drop", "duplicate", "reorder", "branch", "phi", "ik_q", "nominal_path_pseudo_proof",
                                 "place_screen_reason", "false_sector", "screen_record", "start_q", "gap", "attachment", "world",
                                 "scene_hash", "profile", "collision_policy", "barriers", "sector", "version", "scope"])
def test_checker_refuses_tampered_records(blocked, how):
    rec, chk = _run(blocked)
    assert chk["accepted"]
    bad = sc.check(ROBOT, CFG, _tamper(rec, how), _src(blocked))
    assert not bad["accepted"] and bad["reasons"], how


def test_forged_status_and_changed_source_world_or_start(blocked):
    open_ = place_scene(CFG, "syn", "v", [15], [42])
    rec, _ = _run(open_)
    rec["claim"] = "CERTIFIED_INFEASIBLE"
    assert not sc.check(ROBOT, CFG, rec, _src(open_))["accepted"]
    rec, _ = _run(blocked)
    moved = replace(blocked, objects=tuple(Obj(o.id, o.kind, o.radius_m, blocked.lattice.center(40), 40) if o.id == "o00" else o
                                           for o in blocked.objects))
    started = replace(blocked, robot=replace(blocked.robot, q_rad=(math.pi / 2, math.pi / 2, math.pi / 2 - 0.01)))
    added = place_scene(CFG, "syn", "v", [7], [41, 0])
    for s in (moved, started, added):
        assert not sc.check(ROBOT, CFG, rec, _src(s))["accepted"]


def test_scope_rules(blocked):
    h = sc.scene_hash(blocked)
    rec = scp.produce(ROBOT, CFG, blocked, "t0", "ORIGINAL_TARGET", [], 7)
    assert sc.check(ROBOT, CFG, rec, _src(blocked, "ORIGINAL_TARGET", kind="ORDERED_TEACHER", h=h))["accepted"]
    assert not sc.check(ROBOT, CFG, rec, _src(blocked, "ORIGINAL_TARGET", kind="ORDERED_TEACHER", h="sha256:0"))["accepted"]
    seq_rec = scp.produce(ROBOT, CFG, blocked, "t0", "ORIGINAL_TARGET", [["o00", 40]], 7)
    assert not sc.check(ROBOT, CFG, seq_rec, _src(blocked, "ORIGINAL_TARGET", seq=[["o00", 40]], kind="ORDERED_TEACHER",
                                                  h=h))["accepted"]                # target stage after a relocation
    fa = scp.produce(ROBOT, CFG, blocked, "t0", "FIRST_ACTION_ORDER", [["o00", 40]], 40)
    assert not sc.check(ROBOT, CFG, fa, _src(blocked, "FIRST_ACTION_ORDER", seq=[["o00", 40]], kind="ORDERED_TEACHER",
                                             h=h))["accepted"]                     # moved object is not the first action's
    after = scp.produce(ROBOT, CFG, blocked, "t0", "TARGET_AFTER_RELOCATION", [], 7)
    assert not sc.check(ROBOT, CFG, after, _src(blocked, "TARGET_AFTER_RELOCATION"))["accepted"]
    assert sc.LABEL_SCOPES == {"ORIGINAL_TARGET", "SCENE_TARGET_ONLY", "FIRST_ACTION_ORDER"}   # no ASSIGNMENT scope


def test_joint_wrap_fails_closed(blocked):
    cfg = copy.deepcopy(CFG)
    cfg["arm2d"]["joint_limits_rad"][0] = [-math.pi - 0.1, math.pi + 0.1]
    robot = ge.make_robot(cfg)
    with pytest.raises(ValueError):
        sc.sector(robot, cfg, blocked, blocked.robot.q_rad[0])


def test_independent_ik_matches_geometry_ik_on_the_whole_family():
    for cell in (7, 22, 45, 18, 57):
        anchor = place_scene(CFG, "syn", "v", [cell], []).get("t0").xy_m
        for phi, b in sk.directions(sk.params(CFG)):
            mine = sc._ik(ROBOT, anchor, phi, b)
            theirs = sk._ik(ROBOT, anchor, (ROBOT.grasp_x, 0.0), phi).get(b)
            assert (mine is None) == (theirs is None) and (mine is None or np.allclose(mine, theirs, atol=1e-12))


def test_saved_positive_witnesses_are_not_contradicted_sample():
    ctrls = scp.controls(CFG, ROBOT)
    assert len(ctrls) > 50 and all(c["pick_q"] for c in ctrls)
    for c in ctrls[:: max(1, len(ctrls) // 8)]:
        r = scp.evaluate_control(CFG, ROBOT, c)
        assert r["witness_candidate"] and not r["contradiction"] and not r["checker_reasons"], (c["witnesses"], r)


def test_guards_raise_on_any_oracle_call(guards):
    import planner
    import skill
    with pytest.raises(RuntimeError):
        planner.plan(None, None, None, None, None, None, None)
    with pytest.raises(RuntimeError):
        skill.plan_skill(None, None, None, None, None, None)
    guards[0].clear()                                       # the two deliberate calls above are the test itself
