"""G2 acceptance tests: frozen action, one-edit interventions, fixed-action oracle."""
import json
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
import interventions as iv  # noqa: E402
import motion as mo  # noqa: E402
import scene as sc  # noqa: E402
import skill as sk  # noqa: E402

FX = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]


@pytest.fixture(scope="module")
def cfg():
    return cf.load_config(ROOT / "config.toml")


@pytest.fixture(scope="module")
def robot(cfg):
    return ge.make_robot(cfg)


@pytest.fixture(scope="module")
def d2(cfg, robot):
    """The D2 reference: planned with its six background obstacles present, frozen."""
    fx = FX["G2_D2"]
    scene = sc.place_scene(cfg, fx["root_id"], "ref", [fx["tasks"][0][0]], fx["obstacle_cells"])
    res = sk.plan_skill(robot, scene, "t0", fx["tasks"][0][1], cfg, "G2_D2")
    assert res.status == sk.VERIFIED
    return scene, iv.freeze(robot, cfg, scene, "t0", res.traj.arrays())


def snap(robot, cfg, frozen, parent, name, edit):
    child = iv.apply_edit(parent.scene, edit, name, cfg["suite"]["margin_m"])
    return iv.evaluate(robot, cfg, frozen, iv.Snapshot(name, parent.variant, edit, child))


@pytest.fixture(scope="module")
def lineage(cfg, robot, d2):
    """ref -> A (o05 -> 50) -> A+B (o02 -> 57) -> A out -> B out, as recorded in runs/g2_interventions."""
    scene, fr = d2
    ref = iv.evaluate(robot, cfg, fr, iv.Snapshot("ref", None, None, scene))
    a = snap(robot, cfg, fr, ref, "block_a", iv.Edit("RELOCATE", "o05", 49, 50))
    ab = snap(robot, cfg, fr, a, "block_ab", iv.Edit("RELOCATE", "o02", 40, 57))
    ca = snap(robot, cfg, fr, ab, "clear_a", iv.Edit("RELOCATE", "o05", 50, 41))
    cab = snap(robot, cfg, fr, ca, "clear_ab", iv.Edit("RELOCATE", "o02", 57, 49))
    return ref, a, ab, ca, cab


# ---------------------------------------------------------------- frozen identity
def test_frozen_hash_invariance_and_tamper_detection(cfg, robot, d2, lineage):
    scene, fr = d2
    fr.verify()
    assert {s.scene.root_id for s in lineage} == {scene.root_id}
    q = fr.arrays["q"].copy()
    q[-1] += 1e-6                                           # only the final return-home waypoint differs
    replanned = iv.FrozenAction(fr.target_id, {**fr.arrays, "q": q}, fr.reference_scene_hash,
                                fr.robot_profile_hash, fr.action_hash)
    with pytest.raises(ValueError):                         # silently replanned gamma_0
        iv.evaluate(robot, cfg, replanned, iv.Snapshot("x", None, None, scene))
    rehashed = replace(fr, reference_scene_hash=sc.scene_hash(lineage[2].scene))
    with pytest.raises(ValueError):                         # descendant scene substituted into the identity
        rehashed.verify()


# ---------------------------------------------------------------- edits
def test_one_edit_invariants_and_forbidden_edits(cfg, robot, d2, lineage):
    scene, fr = d2
    delta = cfg["suite"]["margin_m"]
    ref, a = lineage[0], lineage[1]
    assert [o.id for o in a.scene.objects] == [o.id for o in ref.scene.objects]
    assert sum(x != y for x, y in zip(ref.scene.objects, a.scene.objects)) == 1
    assert a.scene.robot == ref.scene.robot and a.scene.legal_cells == ref.scene.legal_cells
    extra = replace(a.scene, objects=a.scene.objects + (sc.Obj("z99", "obstacle", 0.024, scene.lattice.center(2), 2),))
    with pytest.raises(ValueError):                         # inserting a new obstacle
        iv.audit_edit(ref.scene, extra, a.edit, delta)
    two = iv.apply_edit(a.scene, iv.Edit("RELOCATE", "o00", 4, 3), "two", delta)
    with pytest.raises(ValueError):                         # two objects changed on one edge
        iv.audit_edit(ref.scene, two, a.edit, delta)
    with pytest.raises(ValueError):                         # destination occupied
        iv.apply_edit(scene, iv.Edit("RELOCATE", "o00", 4, 15), "x", delta)
    with pytest.raises(ValueError):                         # the target is not an intervention object
        iv.apply_edit(scene, iv.Edit("RELOCATE", "t0", 26, 2), "x", delta)
    with pytest.raises(ValueError):                         # a diagnostic edit cannot claim robot execution
        iv.apply_edit(scene, iv.Edit("RELOCATE", "o00", 4, 3, robot_executed=True), "x", delta)
    back = iv.apply_edit(a.scene, iv.Edit("RELOCATE", "o05", 50, 49), "back", delta)
    assert sc.scene_hash(back) == sc.scene_hash(scene)      # undoing the edit reproduces the reference


def test_support_vacancy_and_pair_validity(cfg, lineage):
    for s in lineage:
        assert s.present_state == mo.VALID
        assert len(sc.occupancy(s.scene)) == len(s.scene.objects)
        assert all(iv.support_status(s.scene, o) == mo.VALID for o in s.scene.objects)
    status, gap = iv.pair_status(lineage[2].scene, cfg["suite"]["margin_m"], 0.0)
    assert status == mo.VALID and gap == pytest.approx(0.08 - 0.048)


# ---------------------------------------------------------------- oracle and attribution
def test_blocker_detected_on_full_body_sweep(lineage):
    a = lineage[1]
    chk = a.checks["o05"]
    assert chk.status == mo.INVALID and chk.first["kind"] == "ROBOT_BODY" and chk.first["body"] == "link2"
    assert a.F == mo.INVALID and a.whole_replay == mo.INVALID      # independent whole-scene replay agrees
    assert all(c.status == mo.VALID for i, c in a.checks.items() if i != "o05")


def test_per_id_conflict_cancels_while_global_failure_stays(cfg, lineage):
    ref, a, ab, ca, cab = lineage
    delta = cfg["suite"]["margin_m"]
    assert ab.F == mo.INVALID and iv.contributions(ab, delta)["o02"]["c"] == 1
    eff = iv.edge_effect(ab, ca, delta)
    assert ca.F == mo.INVALID and eff["Delta_I"] == 0 and eff["d_I"]["o05"] == -1
    assert iv.contributions(ca, delta)["o02"]["c"] == 1
    assert cab.F == mo.VALID and iv.edge_effect(ca, cab, delta)["Delta_I"] == 1
    assert all(s.F == s.whole_replay for s in lineage)


def test_removal_differs_from_relocation_but_both_clear_own_conflict(cfg, robot, d2, lineage):
    _, fr = d2
    ab = lineage[2]
    removed = snap(robot, cfg, fr, ab, "remove_a", iv.Edit("REMOVE", "o05", 50))
    assert "o05" not in {o.id for o in removed.scene.objects} and removed.F == mo.INVALID
    eff = iv.edge_effect(ab, removed, cfg["suite"]["margin_m"])
    assert eff["d_I"]["o05"] == -1 and eff["Delta_I"] == 0           # absent object contributes 0


def test_unrelated_edit_leaves_outcome_unchanged(cfg, robot, d2, lineage):
    _, fr = d2
    for parent in (lineage[0], lineage[2]):
        child = snap(robot, cfg, fr, parent, "unrelated", iv.Edit("RELOCATE", "o00", 4, 3))
        eff = iv.edge_effect(parent, child, cfg["suite"]["margin_m"])
        assert eff["Delta_I"] == 0 and not any(eff["d_I"].values()) and child.F == parent.F


def test_privileged_diagnostics_are_never_executed_repairs(cfg, robot, d2, lineage):
    _, fr = d2
    summary = iv.family_summary({"status": "OK", "frozen": fr, "snaps": list(lineage), "scene": lineage[0].scene,
                                 "plan": sk.SkillResult(sk.VERIFIED, "x")}, cfg)
    assert summary["executed_repairs"] == 0 and summary["moved_history"] == []
    assert all(x["edit"] is None or (x["edit"]["role"] == iv.DIAGNOSTIC and not x["edit"]["robot_executed"])
               for x in summary["nodes"])
    assert all(s.scene.robot == lineage[0].scene.robot for s in lineage)
    assert {x["action_hash_used"] for x in summary["nodes"]} == {fr.action_hash}
    gates = iv.family_gates({**summary, "nodes": summary["nodes"]}, 2)
    assert gates["partial_correction_keeps_failure"] and gates["oracle_agrees_with_whole_scene_replay"]


# ---------------------------------------------------------------- synthetic static actions
def static_action(robot, phases, place=(0.6, 0.6)):
    """A recorded action that holds the robot at home: exact, inspectable clearances."""
    n = len(phases) + 1
    return {"q": np.tile(robot.q_home, (n, 1)), "gap": np.full(n, robot.open_gap), "phase": np.array(phases),
            "attached": np.array([mo.CONTEXT[p][0] == "held" for p in phases]),
            "held_local": np.array([robot.grasp_x, 0.0]), "place_xy": np.array(place)}


def check(cfg, robot, arrays, xy, target=("t0", (0.3, 0.3), 0.024), evals=4000):
    return mo.object_check(robot, arrays, target, ("o00", xy, 0.024), (0.64, 0.64),
                           cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"], evals)


def test_margin_boundary_and_gray_band(cfg, robot):
    """Disc beside the base disc (radius 0.018) at clearance delta -+ 2 eps and exactly delta."""
    delta, eps = cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"]
    arr = static_action(robot, ["pregrasp"])
    base = np.asarray(robot.base)
    at = lambda d: tuple(base - np.array([robot.base_r + 0.024 + d, 0.0]))  # noqa: E731
    assert check(cfg, robot, arr, at(delta + 2 * eps)).status == mo.VALID
    assert check(cfg, robot, arr, at(delta)).status == mo.UNRESOLVED            # gray band is never proof
    bad = check(cfg, robot, arr, at(delta - 2 * eps))
    assert bad.status == mo.INVALID and bad.first["body"] == "base"
    assert mo._conjoin([mo.VALID, mo.UNRESOLVED]) == mo.UNRESOLVED
    assert mo._conjoin([mo.UNRESOLVED, mo.INVALID]) == mo.INVALID and mo._conjoin([]) == mo.VALID


def test_contact_kinds_resting_carried_and_placed_target(cfg, robot):
    arr = static_action(robot, ["pregrasp", "carry", "release"], place=(0.55, 0.05))
    held = ge.tool_point(robot, robot.q_home, arr["held_local"])
    assert check(cfg, robot, arr, (0.3, 0.3 + 0.05)).first["kind"] == "RESTING_TARGET"
    assert check(cfg, robot, arr, tuple(held + np.array([0.0, -0.05]))).first["kind"] == "CARRIED_TARGET"
    placed = check(cfg, robot, arr, (0.55, 0.10))
    assert placed.first["kind"] == "PLACED_TARGET" and placed.first["phase"] == "release"
    assert check(cfg, robot, arr, (0.60, 0.40)).status == mo.VALID


def test_budget_exhaustion_is_unresolved_not_proof(cfg, robot):
    """A moving segment that needs subdivision, certified with a 2-evaluation budget."""
    arr = static_action(robot, ["pregrasp"])
    arr["q"] = np.array([robot.q_home, np.asarray(robot.q_home) + np.array([-0.6, 0.0, 0.0])])
    near = tuple(np.asarray(robot.base) + 0.52 * np.array([math.cos(1.27), math.sin(1.27)]))  # 45 mm clear
    full, tiny = check(cfg, robot, arr, near), check(cfg, robot, arr, near, evals=2)
    assert full.status == mo.VALID and full.evals > 2              # needed subdivision to prove clearance
    assert tiny.status == mo.UNRESOLVED                            # same truth, budget spent: not proof
