"""Sole command dispatcher (Guide v1.6 §1). Never imported by other modules.

Active commands: scene (G0). Later commands are added only in their stage.

    python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np
import PIL
from PIL import Image

import scene as sc
import viz


def load_fixture(path: str, case: str) -> dict:
    fixtures = json.loads(Path(path).read_text())["fixtures"]
    if case not in fixtures:
        raise SystemExit(f"unknown case {case!r}; known: {sorted(fixtures)}")
    return fixtures[case]


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True))


def scene_checks(cfg: dict, fx: dict, s: sc.Scene, inst: np.ndarray, out: Path) -> dict:
    """Run-time evidence recorded in result.json (pytest holds the full gate)."""
    rebuilt = sc.make_scene(cfg, fx["root_id"], fx["variant_id"], fx["seed"])
    permuted = sc.Scene(**{**s.__dict__, "objects": tuple(reversed(s.objects))})
    gaps = [math.dist(a.xy_m, b.xy_m) - a.radius_m - b.radius_m for a, b in combinations(s.objects, 2)]
    res = viz.raster_geometry(s, cfg["render"]["image_px"])[2]
    areas = np.bincount(inst.ravel(), minlength=len(s.objects) + 1)[1:] * res ** 2
    analytic = math.pi * cfg["suite"]["obstacle_radius_m"] ** 2
    x0, x1, y0, y1 = viz.shapes_extent(viz.robot_shapes(s, cfg))
    xl, yl = cfg["render"]["overview_xlim_m"], cfg["render"]["overview_ylim_m"]
    return {
        "rebuild_same_hash": sc.scene_hash(rebuilt) == sc.scene_hash(s),
        "json_roundtrip_same_hash": sc.scene_hash(sc.load_scene_json(out / "scene.json"))
        == sc.scene_hash(s),
        "permuted_input_same_hash": sc.scene_hash(permuted) == sc.scene_hash(s),
        "distinct_cells": len(sc.occupancy(s)) == len(s.objects),
        "min_surface_gap_m": float(min(gaps)),
        "min_surface_gap_meets_margin": bool(min(gaps) >= cfg["suite"]["margin_m"]),
        "mask_area_max_rel_error": float(np.max(np.abs(areas - analytic)) / analytic),
        "robot_drawing_within_axes": bool(xl[0] <= x0 and x1 <= xl[1] and yl[0] <= y0 and y1 <= yl[1]),
    }


def cmd_scene(args) -> int:
    cfg = sc.load_config(args.config)
    fx = load_fixture(args.fixtures, args.case)
    s = sc.make_scene(cfg, fx["root_id"], fx["variant_id"], fx["seed"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chash, shash, rhash = sc.config_hash(cfg), sc.scene_hash(s), s.robot_profile_hash

    _write_json(out / "config.json", {"config_hash": chash, "config": cfg})
    sc.save_scene_json(s, out / "scene.json")
    rgb, inst, ids = viz.render_observation(s, cfg["render"]["image_px"])
    Image.fromarray(rgb).save(out / "observation.png")
    np.savez_compressed(out / "arrays.npz", **sc.scene_arrays(s), observation_rgb=rgb,
                        instance_mask=inst, instance_ids=np.array(ids, dtype="U16"))

    checks = scene_checks(cfg, fx, s, inst, out)
    passed = all(v for k, v in checks.items() if isinstance(v, bool))
    notes = [f"scene_hash {shash}", f"config_hash {chash}",
             f"robot_profile_hash {rhash} (PROVISIONAL, untested)",
             f"gamma_0 hash: none (no target action before G1)  |  motion scope: NONE  |  "
             f"gripper: open g={s.robot.gripper_gap_m} m, m={s.robot.attachment}  |  moved history H=[]",
             f"{len(s.objects)} objects ({cfg['suite']['num_obstacles']} obstacles + "
             f"{cfg['suite']['num_targets']} target) on {len(s.legal_cells)} legal cells, "
             f"domain {s.domain_policy}, seed {fx['seed']}"]
    fig = viz.overview_figure(s, cfg, (rgb, inst, ids), notes)
    fig.savefig(out / "overview.png", dpi=120)

    obstacles = [o.id for o in s.objects if o.kind == "obstacle"]
    sizes = [sc.candidate_map(s, i).size - 1 for i in obstacles]
    with open(out / "metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "unit"])
        w.writerows([["num_objects", len(s.objects), "count"], ["num_obstacles", len(obstacles), "count"],
                     ["occupied_cells", len(sc.occupancy(s)), "count"],
                     ["free_cells", len(s.legal_cells) - len(sc.occupancy(s)), "count"],
                     ["candidates_per_obstacle_min", min(sizes), "count"],
                     ["candidates_per_obstacle_max", max(sizes), "count"],
                     ["min_surface_gap", checks["min_surface_gap_m"], "m"],
                     ["required_pair_clearance_margin", cfg["suite"]["margin_m"], "m"],
                     ["mask_area_max_rel_error", checks["mask_area_max_rel_error"], "ratio"]])

    _write_json(out / "result.json", {
        "stage": "G0", "fixture": args.case, "gate_checks_passed": passed, "checks": checks,
        "root_family_id": s.root_id, "variant_id": s.variant_id, "scene_hash": shash,
        "config_hash": chash, "robot_profile_hash": rhash, "robot_profile_status": "PROVISIONAL",
        "domain_policy": s.domain_policy, "margin_policy": cfg["suite"]["margin_policy"],
        "query_status": None, "verification_scope": "NONE", "target_hash": None,
        "robot_pose_status": "SCHEMATIC_NOT_RUN", "moved_history": [],
        "target_replay_status": "NOT_ATTEMPTED", "simulation_replay_status": "NOT_RUN",
        "physical_execution_status": "NOT_RUN",
        "note": "No action query exists at G0; three-valued query status begins at G2."})

    files = sorted(p.name for p in out.iterdir() if p.name != "manifest.json")
    _write_json(out / "manifest.json", {
        "command": sys.argv, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seeds": {"root": fx["seed"]}, "config_hash": chash, "scene_hash": shash,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "matplotlib": matplotlib.__version__, "pillow": PIL.__version__,
                     "platform": platform.platform()},
        "files": {n: "sha256:" + hashlib.sha256((out / n).read_bytes()).hexdigest() for n in files}})
    print(json.dumps({"out": str(out), "gate_checks_passed": passed, "scene_hash": shash}))
    return 0 if passed else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Latent causal TAMP stage runner")
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("scene", help="G0: build, snapshot and render a fixture scene")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--case", required=True)
    q.add_argument("--out", required=True)
    q.set_defaults(func=cmd_scene)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
