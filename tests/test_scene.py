"""G0 acceptance tests: scene records, lattice/raster conventions, snapshots."""
import copy
import json
import math
import subprocess
import sys
import tomllib
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cf  # noqa: E402
import geometry  # noqa: E402
import scene as sc  # noqa: E402
import viz  # noqa: E402

FIXTURE = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]["G0_ILLUSTRATIVE"]


@pytest.fixture(scope="module")
def raw():
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


@pytest.fixture(scope="module")
def cfg(raw):
    return cf.validate_config(raw)


@pytest.fixture(scope="module")
def scene(cfg):
    return sc.make_scene(cfg, FIXTURE["root_id"], FIXTURE["variant_id"], FIXTURE["seed"])


def _bad(raw, edit):
    bad = copy.deepcopy(raw)
    edit(bad)
    with pytest.raises(cf.ConfigError):
        cf.validate_config(bad)


# ---------------------------------------------------------------- config
def test_unknown_missing_and_mistyped_config_keys_fail(raw):
    _bad(raw, lambda c: c["suite"].update(typo_key=1))
    _bad(raw, lambda c: c.update(planner2d={"seed": 41}))       # section of a later stage
    _bad(raw, lambda c: c["arm2d"].pop("q_home_rad"))
    _bad(raw, lambda c: c["suite"].update(rows="8"))
    _bad(raw, lambda c: c["arm2d"].update(link_lengths_m=[0.4, 0.3]))


def test_physically_inconsistent_config_fails(raw):
    _bad(raw, lambda c: c["suite"].update(pitch_m=0.05))           # 0.05 < 2r + delta = 0.053
    _bad(raw, lambda c: c["suite"].update(domain_policy="RESTRICTED"))
    _bad(raw, lambda c: c["suite"].update(num_obstacles=64))       # 64 + 1 target > 64 cells
    _bad(raw, lambda c: c["gripper2d"].update(open_gap_m=0.040))   # narrower than 2r


def test_config_hash_is_stable_and_sensitive(raw, cfg):
    assert cf.config_hash(cf.validate_config(copy.deepcopy(raw))) == cf.config_hash(cfg)
    changed = copy.deepcopy(raw)
    changed["suite"]["margin_m"] = 0.006
    assert cf.config_hash(cf.validate_config(changed)) != cf.config_hash(cfg)


# ---------------------------------------------------------------- lattice
def test_row_to_world_convention(scene):
    lat = scene.lattice
    assert lat.center(lat.cell_id(0, 0)) == pytest.approx((0.04, 0.04))
    assert lat.center(lat.cell_id(7, 0)) == pytest.approx((0.04, 0.60))   # row grows with +y
    assert lat.center(lat.cell_id(0, 7)) == pytest.approx((0.60, 0.04))   # column grows with +x
    assert lat.cell_id(3, 5) == 29 and lat.rc(29) == (3, 5)
    centers = {lat.center(c) for c in range(lat.n_cells)}
    assert len(centers) == 64                                              # no duplicate cells


def test_generated_scene_is_distinct_and_nonpenetrating(cfg, scene):
    assert len(scene.objects) == 36 and len(sc.occupancy(scene)) == 36
    for a, b in combinations(scene.objects, 2):
        gap = math.dist(a.xy_m, b.xy_m) - a.radius_m - b.radius_m
        assert gap >= cfg["suite"]["margin_m"]


# ---------------------------------------------------------------- determinism
def test_same_seed_same_hash_different_seed_differs(cfg, scene):
    again = sc.make_scene(cfg, FIXTURE["root_id"], FIXTURE["variant_id"], FIXTURE["seed"])
    other = sc.make_scene(cfg, FIXTURE["root_id"], FIXTURE["variant_id"], FIXTURE["seed"] + 1)
    assert again == scene and sc.scene_hash(again) == sc.scene_hash(scene)
    assert sc.scene_hash(other) != sc.scene_hash(scene)


def test_object_permutation_changes_neither_physics_nor_plot(cfg, scene):
    order = np.random.default_rng(0).permutation(len(scene.objects))
    permuted = sc.Scene(**{**scene.__dict__, "objects": tuple(scene.objects[i] for i in order)})
    assert permuted == scene and sc.scene_hash(permuted) == sc.scene_hash(scene)
    assert sc.occupancy(permuted) == sc.occupancy(scene)
    px = cfg["render"]["image_px"]
    obs_a, obs_b = viz.render_observation(scene, px), viz.render_observation(permuted, px)
    assert all(np.array_equal(a, b) for a, b in zip(obs_a[:2], obs_b[:2])) and obs_a[2] == obs_b[2]
    fig_a = viz.overview_figure(scene, cfg, obs_a, ["n"])
    fig_b = viz.overview_figure(permuted, cfg, obs_b, ["n"])
    assert np.array_equal(viz.figure_rgba(fig_a), viz.figure_rgba(fig_b))


# ---------------------------------------------------------------- raster
def test_raster_transform_and_row_reversal(cfg, scene):
    px = cfg["render"]["image_px"]
    h, w, res = viz.raster_geometry(scene, px)
    assert (h, w) == (320, 320) and res == pytest.approx(0.002)
    u, v = viz.world_to_pixel(0.04, 0.60, scene, px)          # cell (7, 0): back-left
    assert u < w / 4 and v < h / 4                            # appears top-left in the image
    x, y = viz.pixel_to_world(*viz.world_to_pixel(0.123, 0.456, scene, px), scene, px)
    assert (x, y) == pytest.approx((0.123, 0.456))
    rgb, inst, ids = viz.render_observation(scene, px)
    for k, obj_id in enumerate(ids, start=1):                  # mask centroid == world centre
        vv, uu = np.nonzero(inst == k)
        assert viz.pixel_to_world(uu.mean(), vv.mean(), scene, px) == pytest.approx(
            scene.get(obj_id).xy_m, abs=res / 2)


def test_mask_area_and_equal_aspect(cfg, scene):
    px = cfg["render"]["image_px"]
    _, inst, ids = viz.render_observation(scene, px)
    res = viz.raster_geometry(scene, px)[2]
    areas = np.bincount(inst.ravel(), minlength=len(ids) + 1)[1:] * res ** 2
    assert np.allclose(areas, math.pi * cfg["suite"]["obstacle_radius_m"] ** 2, rtol=0.03)
    fig = viz.overview_figure(scene, cfg, viz.render_observation(scene, px), ["n"])
    world_axes = [fig.axes[0], fig.axes[1], fig.axes[3]]
    assert all(ax.get_aspect() == 1.0 for ax in world_axes)


def test_robot_drawing_inside_fixed_axes(cfg, scene):
    robot = geometry.make_robot(cfg)
    x0, x1, y0, y1 = viz.robot_extent(robot, scene.robot.q_rad, scene.robot.gripper_gap_m)
    (xl0, xl1), (yl0, yl1) = cfg["render"]["overview_xlim_m"], cfg["render"]["overview_ylim_m"]
    assert xl0 <= x0 and x1 <= xl1 and yl0 <= y0 and y1 <= yl1
    names = [n for n, _ in viz.robot_outlines(robot, scene.robot.q_rad, scene.robot.gripper_gap_m)]
    assert {"finger_l", "finger_r", "palm", "rail", "housing1", "housing2"} <= set(names)


# ---------------------------------------------------------------- candidates
def test_candidate_map_stay_zero_and_no_clone(scene):
    cmap = sc.candidate_map(scene, "o00")
    o = scene.get("o00")
    target_cell = scene.get("t0").cell
    assert cmap.cell_of(0) is None and cmap.stay_xy_m == o.xy_m
    assert cmap.size == 63 and o.cell not in cmap.cells and target_cell not in cmap.cells
    assert cmap.cells != tuple(range(1, 63))                     # per-object k != global cell ID
    ghost = sc.substitute_pose(scene, "o00", cmap.cell_of(5))
    assert [g.id for g in ghost.objects] == [s.id for s in scene.objects]
    assert ghost.get("o00").cell == cmap.cell_of(5) and o.cell not in sc.occupancy(ghost)
    assert all(g == s for g, s in zip(ghost.objects, scene.objects) if g.id != "o00")
    assert (ghost.robot, ghost.legal_cells) == (scene.robot, scene.legal_cells)
    with pytest.raises(ValueError):
        sc.candidate_map(scene, "t0")                            # targets are never relocated


# ---------------------------------------------------------------- snapshots
def test_json_snapshot_roundtrip_and_tamper_detection(scene, tmp_path):
    path = tmp_path / "scene.json"
    sc.save_scene_json(scene, path)
    loaded = sc.load_scene_json(path)
    assert loaded == scene and sc.scene_hash(loaded) == sc.scene_hash(scene)
    record = json.loads(path.read_text())
    record["scene"]["objects"][0]["xy_m"][0] += 1e-6
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        sc.load_scene_json(path)


def test_npz_snapshot_roundtrip(scene, tmp_path):
    arrays = sc.scene_arrays(scene)
    np.savez_compressed(tmp_path / "a.npz", **arrays)
    with np.load(tmp_path / "a.npz", allow_pickle=False) as back:
        for key, value in arrays.items():
            assert back[key].dtype == value.dtype and np.array_equal(back[key], value)
    for row, obj_id in enumerate(arrays["object_ids"]):
        assert tuple(arrays["object_xy_m"][row]) == scene.get(str(obj_id)).xy_m


# ---------------------------------------------------------------- CLI
def test_cli_scene_run_writes_artifacts(scene, tmp_path):
    out = tmp_path / "run"
    cmd = [sys.executable, "run.py", "scene", "--case", "G0_ILLUSTRATIVE", "--out", str(out)]
    assert subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode == 0
    for name in ["config.json", "scene.json", "result.json", "overview.png", "observation.png",
                 "arrays.npz", "metrics.csv", "manifest.json"]:
        assert (out / name).exists(), name
    result = json.loads((out / "result.json").read_text())
    assert result["gate_checks_passed"] and result["scene_hash"] == sc.scene_hash(scene)
    assert result["robot_pose_status"] == "SCHEMATIC_NOT_RUN" and result["target_hash"] is None


def test_g2_reference_policy_is_enforced():
    dense, sparse = list(range(35)), [3, 11, 40]
    ok = {"a": {"stage": "G2", "reference_policy": "FINAL_DENSE_PLANNED", "benchmark_role": "PRIMARY",
                "obstacle_cells": dense},
          "b": {"stage": "G2", "reference_policy": "SPARSE_SEEDED_REFERENCE", "benchmark_role": "BOOTSTRAP_ONLY"},
          "d": {"stage": "G2", "reference_policy": "FINAL_DEV_SCENE_PLANNED", "benchmark_role": "DEVELOPMENT_ONLY",
                "obstacle_cells": sparse},
          "c": {"stage": "G1"}}
    assert cf.validate_fixtures(ok) is ok
    for bad in ({"stage": "G2"},
                {"stage": "G3", "reference_policy": "SPARSE_SEEDED_REFERENCE", "benchmark_role": "PRIMARY"},
                {"stage": "G2", "reference_policy": "SPARSE_FILL", "benchmark_role": "PRIMARY"},
                {"stage": "G2", "reference_policy": "FINAL_DEV_SCENE_PLANNED", "benchmark_role": "PRIMARY",
                 "obstacle_cells": sparse},                                   # dev scene posing as primary
                {"stage": "G2", "reference_policy": "FINAL_DEV_SCENE_PLANNED", "benchmark_role": "DEVELOPMENT_ONLY",
                 "obstacle_cells": dense},                                    # "dev" scene that is dense
                {"stage": "G2", "reference_policy": "FINAL_DEV_SCENE_PLANNED", "benchmark_role": "DEVELOPMENT_ONLY"},
                {"stage": "G2", "reference_policy": "FINAL_DENSE_PLANNED", "benchmark_role": "PRIMARY",
                 "obstacle_cells": sparse}):                                  # sparse scene posing as dense
        with pytest.raises(cf.ConfigError):
            cf.validate_fixtures({"x": bad})
