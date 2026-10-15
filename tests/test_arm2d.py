"""G1 acceptance tests: 3R kinematics, collision bodies, certification, six-phase skill."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import geometry as ge  # noqa: E402
import motion as mo  # noqa: E402
import planner as pn  # noqa: E402
import scene as sc  # noqa: E402
import skill as sk  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return sc.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


def world(cfg, discs):
    """Checker world with discs given as world (x, y) centres (radius r)."""
    s = sc.place_scene(cfg, "root_t", "v", [], [])
    r = cfg["suite"]["obstacle_radius_m"]
    return ge.make_world(s, extra=[(f"o{i:02d}", tuple(xy), r) for i, xy in enumerate(discs)])


def checker(cfg, robot, discs, **kw):
    return ge.Checker(robot, world(cfg, discs), cfg["suite"]["margin_m"],
                      cfg["geometry"]["numeric_margin_band_m"], **kw)


# ---------------------------------------------------------------- kinematics
def test_fk_ik_round_trip_both_branches(robot):
    rng = np.random.default_rng(1)
    for _ in range(500):
        q = rng.uniform(-3.0, 3.0, 3)
        joints, theta = ge.fk(robot, q)
        sols = ge.ik(robot, joints[3], theta[2])
        assert {b for b, _ in sols} == {1, -1}                      # interior: two elbows
        best = min(np.max(np.abs(ge.wrap(p - q))) for _, p in sols)
        assert best < 1e-9
        for b, p in sols:
            j2, t2 = ge.fk(robot, p)
            assert np.allclose(j2[3], joints[3], atol=1e-12) and math.isclose(
                float(ge.wrap(t2[2] - theta[2])), 0.0, abs_tol=1e-12)
            assert np.sign(p[1]) == b


def test_ik_limits_wrapping_and_unreachable(robot):
    assert ge.ik(robot, (1.5, 0.3), 0.0) == []                       # beyond reach
    for b, q in ge.ik(robot, (0.3, 0.3), 2.5):
        assert ge.within_limits(robot, q) and np.all(np.abs(q) <= math.pi)


# ---------------------------------------------------------------- gripper
@pytest.mark.parametrize("gap", [0.070, 0.048])
def test_gripper_connected_and_aperture(robot, gap):
    b = ge.bodies(robot, (0.4, -0.9, 0.7), gap)
    assert ge.core_distance(b["rail"][0], b["finger_l"][0]) == 0.0  # fingers mounted on rail
    assert ge.core_distance(b["rail"][0], b["finger_r"][0]) == 0.0
    assert math.isclose(ge.core_distance(b["finger_l"][0], b["finger_r"][0]), gap, abs_tol=1e-12)
    ys = [ge.tool_local(robot, (0.4, -0.9, 0.7), v)[1] for v in b["rail"][0]]
    assert math.isclose(max(ys) - min(ys), robot.open_gap + 2 * robot.finger_t, abs_tol=1e-12)


def test_closure_stops_at_contact_without_penetration(cfg, robot):
    obj = np.array([0.30, 0.20])
    q = sk._ik(robot, obj, (robot.grasp_x, 0.0), 0.4)[1]
    touch = checker(cfg, robot, [obj], contact="o00")
    assert ge.certify(touch, q, q, robot.open_gap, 2 * 0.024, 4000).status == ge.CLEAR
    squeeze = ge.certify(touch, q, q, robot.open_gap, robot.closed_gap, 4000)
    assert squeeze.status == ge.COLLISION and squeeze.pair.startswith("finger")
    no_touch = checker(cfg, robot, [obj])                              # contact not scheduled
    assert ge.certify(no_touch, q, q, robot.open_gap, 0.048, 4000).status == ge.COLLISION


# ---------------------------------------------------------------- collisions
def test_self_collision_detected(cfg, robot):
    v = checker(cfg, robot, []).status_at((0.0, 3.1, 0.0), robot.open_gap)   # link 1 folded back
    a, b = v.pair.split("|")
    assert v.status == ge.COLLISION and {a, b} <= set(ge.ROBOT_BODIES)
    assert frozenset((a, b)) not in robot.excluded
    assert checker(cfg, robot, []).status_at(robot.q_home, robot.open_gap).status == ge.CLEAR


def test_world_collision_margin_and_gray_band(cfg, robot):
    q, r, w0 = (0.0, 0.0, 0.0), 0.024, robot.widths[0] / 2
    hit = checker(cfg, robot, [(0.1, 0.32)]).status_at(q, robot.open_gap)
    assert hit.status == ge.COLLISION and hit.pair == "link0|o00"
    at_delta = 0.32 + w0 + r + cfg["suite"]["margin_m"]
    assert checker(cfg, robot, [(0.1, at_delta)]).status_at(q, robot.open_gap).status == ge.UNRESOLVED
    assert checker(cfg, robot, [(0.1, at_delta + 0.001)]).status_at(q, robot.open_gap).status == ge.CLEAR


def test_swept_collision_between_clear_endpoints(cfg, robot):
    ck = checker(cfg, robot, [(0.16, 0.32)])                          # on link 0's axis at angle 0
    qa, qb = np.array([0.3, 0.0, 0.0]), np.array([-0.3, 0.0, 0.0])
    assert ck.status_at(qa, robot.open_gap).status == ge.CLEAR
    assert ck.status_at(qb, robot.open_gap).status == ge.CLEAR
    v = ge.certify(ck, qa, qb, robot.open_gap, robot.open_gap, 4000)
    assert v.status == ge.COLLISION and 0 < v.s < 1 and v.pair.startswith("link0")


def test_lipschitz_bound_is_sound(cfg, robot, monkeypatch):
    monkeypatch.setattr(ge.Checker, "EXACT_BELOW_M", math.inf)         # exact distances only
    ck = checker(cfg, robot, [(0.3, 0.2), (0.5, 0.45)], held=("t", 0.024, (robot.grasp_x, 0.0)))
    rng = np.random.default_rng(2)
    for trial in range(12):                                           # joints and finger travel
        qa, qb = rng.uniform(-2.5, 2.5, 3), rng.uniform(-2.5, 2.5, 3)
        ga, gb = (0.048, 0.070) if trial % 2 else (0.060, 0.060)
        s = np.linspace(0, 1, 801)
        d = np.array([ck.distances(qa + t * (qb - qa), ga + t * (gb - ga)) for t in s])
        slope = np.max(np.abs(np.diff(d, axis=0)), axis=0) / (s[1] - s[0])
        assert np.all(slope <= ck.lipschitz(qb - qa, gb - ga) * (1 + 1e-6) + 1e-9)


# ---------------------------------------------------------------- planning
def test_link0_sweep_certificate_and_unresolved_budget(cfg, robot):
    ck = checker(cfg, robot, [(0.10, 0.20)])                          # 0.27 m from base, angle -0.46
    qa, qb = np.array([0.5, 0.0, 0.0]), np.array([-1.2, 0.3, 0.0])
    pl = pn.plan(ck, qa, qb, robot.open_gap, cfg["planner2d"], 4000, "t")
    assert pl.status == ge.COLLISION and pl.reason == "LINK0_SWEEP:link0|o00"
    far = checker(cfg, robot, [(0.50, 0.32)])                         # beyond L1: no certificate
    qa, qb = np.array([0.3, 0.0, 0.0]), np.array([-0.3, 0.0, 0.0])
    tiny = {**cfg["planner2d"], "max_nodes": 2}                       # budget spent at once
    pl = pn.plan(far, qa, qb, robot.open_gap, tiny, 4000, "t")
    assert pl.direct.status == ge.COLLISION
    assert pl.status == ge.UNRESOLVED and pl.reason == "BUDGET_EXHAUSTED"  # never "infeasible"


def test_home_clear_of_every_cell_and_q0_rejected(cfg, robot):
    full = sc.place_scene(cfg, "r", "v", [], list(range(64)))
    ck = ge.Checker(robot, ge.make_world(full), cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"])
    assert ck.status_at(robot.q_home, robot.open_gap).status == ge.CLEAR
    v = ck.status_at((0.0, 0.0, 0.0), robot.open_gap)
    assert v.status == ge.COLLISION and v.pair == "housing1|o27" and v.distance < cfg["suite"]["margin_m"]


@pytest.mark.parametrize("cell", [0, 7, 56, 63])
def test_every_corner_has_certified_grasp_candidates(cfg, robot, cell):
    s = sc.place_scene(cfg, "r", "v", [cell], [])
    p = sk.params(cfg)
    ck = mo.checkers(robot, s, "t0", None, None, p["delta"], p["eps"])
    picks = sk.screen_pick(robot, ck, s.get("t0").xy_m, 0.024, p)
    assert sum(c.stage == "OK" for c in picks) >= 4


# ---------------------------------------------------------------- full skill
@pytest.fixture(scope="module")
def corner_skill(cfg, robot):
    s = sc.place_scene(cfg, "root_d0", "t", [0], [])
    return s, sk.plan_skill(robot, s, "t0", 7, cfg, "test/corner")


def test_six_phase_corner_skill_verified_and_replays(cfg, robot, corner_skill):
    s, res = corner_skill
    assert res.status == sk.VERIFIED and res.place_error_m <= cfg["gripper2d"]["release_xy_tolerance_m"]
    arr = res.traj.arrays()
    order = [p for i, p in enumerate(arr["phase"]) if i == 0 or p != arr["phase"][i - 1]]
    assert order == list(mo.PHASES)
    assert np.allclose(arr["q"][0], robot.q_home) and np.allclose(arr["q"][-1], robot.q_home)
    p = sk.params(cfg)
    verdicts = mo.certify_trajectory(robot, s, "t0", arr, p["delta"], p["eps"], p["evals"])
    assert all(v.status == ge.CLEAR for v in verdicts)


def test_attachment_continuity(robot, corner_skill):
    s, res = corner_skill
    arr = res.traj.arrays()
    ph, q = arr["phase"], arr["q"]
    first, last = np.flatnonzero(ph == "carry")[[0, -1]]
    assert np.allclose(ge.tool_point(robot, q[first], arr["held_local"]), s.get("t0").xy_m, atol=1e-12)
    assert np.allclose(ge.tool_point(robot, q[last + 1], arr["held_local"]), arr["place_xy"], atol=1e-12)
    assert abs(arr["held_local"][1]) < 1e-12 and math.isclose(arr["held_local"][0], robot.grasp_x)


def test_skill_is_deterministic(cfg, robot, corner_skill):
    s, res = corner_skill
    again = sk.plan_skill(robot, s, "t0", 7, cfg, "test/corner")
    h = lambda r: mo.trajectory_hash(r.traj.arrays(), "t0", sc.scene_hash(s), sc.robot_profile_hash(cfg))  # noqa: E731
    assert h(again) == h(res)


def test_sweep_certificate_band_is_sound(cfg, robot):
    """A disc just beyond L1 (inside L1 + housing_r + r + delta) is certified, and with
    q1 aimed at it every (q2, q3) is a definite collision: no path can avoid it."""
    rho, alpha = robot.lengths[0] + 0.03, 0.35
    xy = np.asarray(robot.base) + rho * np.array([math.cos(alpha), math.sin(alpha)])
    ck = checker(cfg, robot, [xy])
    pl = pn.plan(ck, np.array([1.2, 0.0, 0.0]), np.array([-0.5, 0.0, 0.0]), robot.open_gap,
                 cfg["planner2d"], 4000, "t")
    assert pl.status == ge.COLLISION and pl.reason == "LINK0_SWEEP:housing1|o00"
    rng = np.random.default_rng(3)
    for q23 in rng.uniform(-3.1, 3.1, (200, 2)):
        assert ck.status_at((alpha, *q23), robot.open_gap).status == ge.COLLISION
    far = checker(cfg, robot, [np.asarray(robot.base) + 0.47 * np.array([math.cos(alpha), math.sin(alpha)])])
    assert pn.link0_sweep_blocker(far, np.array([1.2, 0, 0]), np.array([-0.5, 0, 0])) is None


def test_interrupted_connect_never_joins_uncertified_edges(cfg, robot):
    """Regression: a budget hit in the middle of CONNECT must not splice the trees."""
    ck = checker(cfg, robot, [(0.50, 0.32)])                          # beyond L1: no certificate
    qa, qb = np.array([0.6, 0.0, 0.0]), np.array([-0.6, 0.0, 0.0])
    certified = lambda pl: all(ge.certify(ck, a, b, robot.open_gap, robot.open_gap, 4000).status  # noqa: E731
                               == ge.CLEAR for a, b in zip(pl.path[:-1], pl.path[1:]))
    for budget in range(4, 41):                                       # budget lands mid-CONNECT
        pl = pn.plan(ck, qa, qb, robot.open_gap, {**cfg["planner2d"], "max_nodes": budget}, 4000, "join")
        assert pl.direct.status == ge.COLLISION
        assert pl.status == ge.UNRESOLVED or certified(pl)
    full = pn.plan(ck, qa, qb, robot.open_gap, cfg["planner2d"], 4000, "join")
    assert full.status == ge.CLEAR and certified(full)
