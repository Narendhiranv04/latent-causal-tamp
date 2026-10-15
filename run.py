"""Sole command dispatcher (Guide v1.6 §1). Never imported by other modules.

Active commands: scene (G0), check and replay (G1). Later commands arrive with their stage.

    python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
    python run.py check --config config.toml --out runs/g1_robot
    python run.py replay --run runs/g1_robot
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from multiprocessing import Pool
from pathlib import Path

import matplotlib
import numpy as np
import PIL
from PIL import Image

import diagnostics as dg
import figures as fig
import geometry as ge
import motion as mo
import scene as sc
import skill as sk
import viz


def load_fixture(path: str, case: str) -> dict:
    fixtures = sc.validate_fixtures(json.loads(Path(path).read_text())["fixtures"])
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
    x0, x1, y0, y1 = viz.robot_extent(ge.make_robot(cfg), s.robot.q_rad, s.robot.gripper_gap_m)
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

    _write_manifest(out, {"root": fx["seed"]}, chash, {"scene_hash": shash})
    print(json.dumps({"out": str(out), "gate_checks_passed": passed, "scene_hash": shash}))
    return 0 if passed else 1


def _write_manifest(out: Path, seeds: dict, chash: str, extra: dict) -> None:
    files = sorted(p.name for p in out.iterdir() if p.name != "manifest.json")
    _write_json(out / "manifest.json", {
        "command": sys.argv, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seeds": seeds, "config_hash": chash, **extra,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "matplotlib": matplotlib.__version__, "pillow": PIL.__version__,
                     "platform": platform.platform()},
        "files": {n: "sha256:" + hashlib.sha256((out / n).read_bytes()).hexdigest() for n in files}})


# ------------------------------------------------------------------ G1
def task_scene(cfg: dict, fx: dict, task_id: str, src: int) -> sc.Scene:
    """Seeded fixtures reuse their generated scene; designated ones put t0 at src."""
    if "seed" in fx:
        s = sc.make_scene(cfg, fx["root_id"], "ref", fx["seed"])
        if s.get("t0").cell != src:
            raise SystemExit(f"{task_id}: fixture target rests at {s.get('t0').cell}, not {src}")
        return s
    return sc.place_scene(cfg, fx["root_id"], task_id, [src], fx["obstacle_cells"])


def run_task(job):
    """Pool worker: plan one six-phase skill (independent per-query seeds)."""
    cfg, fx, task_id, src, dst = job
    s = task_scene(cfg, fx, task_id, src)
    t0 = time.time()
    res = sk.plan_skill(ge.make_robot(cfg), s, "t0", dst, cfg, task_id)
    return task_id, s, res, time.time() - t0


def g1_jobs(cfg: dict, fixtures: dict) -> list:
    jobs = []
    for case, fx in fixtures.items():
        if fx["stage"] != "G1":
            continue
        if fx.get("audit"):
            n = cfg["suite"]["rows"] * cfg["suite"]["cols"]
            jobs += [(cfg, fx, f"audit_c{c:02d}", c, n - 1 - c) for c in range(n)]
        jobs += [(cfg, fx, f"{case}_t{i}", a, b) for i, (a, b) in enumerate(fx["tasks"])]
    return jobs


def home_check(cfg: dict) -> dict:
    """Old provisional vs current home against every one of the 64 cells occupied."""
    robot = ge.make_robot(cfg)
    full = sc.place_scene(cfg, "root_full", "all_cells", [], list(range(64)))
    ck = ge.Checker(robot, ge.make_world(full), cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"])
    out = {}
    for name, q in (("provisional_q0", (0.0, 0.0, 0.0)), ("home", robot.q_home)):
        d = ck.distances(q, robot.open_gap)
        k = int(np.argmin(d - ck.clear_thr))
        out[name] = {"q": list(q), "status": ck.status_at(q, robot.open_gap).status,
                     "closest_pair": ck.labels[k], "distance_m": float(d[k])}
    return out


def cmd_check(args) -> int:
    cfg = sc.load_config(args.config)
    fixtures = sc.validate_fixtures(json.loads(Path(args.fixtures).read_text())["fixtures"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot, chash, rhash = ge.make_robot(cfg), sc.config_hash(cfg), sc.robot_profile_hash(cfg)
    with Pool(args.workers) as pool:
        done = {tid: (s, res, secs) for tid, s, res, secs in pool.imap_unordered(run_task, g1_jobs(cfg, fixtures))}
    tasks, arrays, scenes = {}, {}, {}
    for tid in sorted(done):
        s, res, secs = done[tid]
        tasks[tid] = {**sk.summary(res, sc.scene_hash(s), rhash), "seconds": round(secs, 1),
                      "scene_hash": sc.scene_hash(s), "root_id": s.root_id}
        scenes[tid] = sc.scene_to_dict(s)
        if res.traj is not None:
            arrays.update({f"{tid}__{k}": v for k, v in res.traj.arrays().items()})
    if not args.no_figures:
        fig.g1_figures(out, robot, cfg, fixtures, done)
    f = dg.ik_tracking_figure(robot, cfg, dg.ik_examples(robot, cfg, done))
    f.savefig(out / "ik_tracking.png", dpi=90)
    extent = traj_extent(robot, done)
    xl, yl = cfg["render"]["overview_xlim_m"], cfg["render"]["overview_ylim_m"]
    nominal = "G1_S1_t%d" % fixtures["G1_S1"]["tasks"].index(fixtures["G1_S1"]["nominal_task"])
    audit = [t for k, t in tasks.items() if k.startswith("audit_")]
    corners = {k: t["status"] for k, t in tasks.items() if k.startswith(("G1_D0", "G1_S1")) and k != nominal}
    gate = {"home_clear_of_all_64_cells": home_check(cfg)["home"]["status"] == ge.CLEAR,
            "all_64_cells_verified_obstacle_free": all(t["status"] == sk.VERIFIED for t in audit),
            "corner_tasks_verified_D0_and_S1": all(v == sk.VERIFIED for v in corners.values()),
            "nominal_skill_verified": tasks[nominal]["status"] == sk.VERIFIED,
            "robot_frames_within_fixed_axes": bool(xl[0] <= extent[0] and extent[1] <= xl[1]
                                                   and yl[0] <= extent[2] and extent[3] <= yl[1])}
    sc.save_scene_json(sc.scene_from_dict(scenes[nominal]), out / "scene.json")
    _write_json(out / "scenes.json", scenes)
    np.savez_compressed(out / "arrays.npz", **arrays)
    _write_json(out / "config.json", {"config_hash": chash, "config": cfg})
    counts = {st: sum(t["status"] == st for t in audit) for st in (sk.VERIFIED, sk.INFEASIBLE, sk.UNRESOLVED)}
    _write_json(out / "result.json", {
        "stage": "G1", "gate_checks_passed": all(gate.values()), "gate": gate, "home_check": home_check(cfg),
        "config_hash": chash, "robot_profile_hash": rhash, "robot_profile_status": "TESTED_G1",
        "nominal_task": nominal, "nominal_action_hash": tasks[nominal]["action_hash"],
        "audit_counts": counts, "robot_extent_m": extent, "tasks": tasks,
        "wall_clock_dependent_tasks": sorted(k for k, t in tasks.items() if t["wall_clock_dependent"]),
        "target_replay_status": "KINEMATIC_REPLAY_CERTIFIED (see replay)", "simulation_replay_status": "NOT_RUN",
        "physical_execution_status": "NOT_RUN"})
    with open(out / "metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "status", "reason", "waypoints", "seconds"])
        w.writerows([[k, t["status"], t["reason"], t["waypoints"], t["seconds"]] for k, t in tasks.items()])
    _write_manifest(out, {"planner_base": cfg["planner2d"]["seed"], "per_query": "crc32(task/connector)"},
                    chash, {"nominal_action_hash": tasks[nominal]["action_hash"]})
    print(json.dumps({"out": str(out), "gate": gate, "audit_counts": counts}))
    return 0 if all(gate.values()) else 1


def traj_extent(robot, done) -> list[float]:
    """Bounding box of every body over every recorded waypoint and figure sample."""
    boxes = [viz.robot_extent(robot, q, g) for _, res, _ in done.values() if res.traj is not None
             for q, g, _ in mo.samples(res.traj.arrays(), 120)]
    boxes.append(viz.robot_extent(robot, robot.q_home, robot.open_gap))
    b = np.array(boxes)
    return [float(b[:, 0].min()), float(b[:, 1].max()), float(b[:, 2].min()), float(b[:, 3].max())]


def cmd_replay(args) -> int:
    """Re-certify every stored trajectory from the run's own files and hashes."""
    run = Path(args.run)
    cfg = sc.validate_config(json.loads((run / "config.json").read_text())["config"])
    scenes, result = json.loads((run / "scenes.json").read_text()), json.loads((run / "result.json").read_text())
    robot, rhash = ge.make_robot(cfg), sc.robot_profile_hash(cfg)
    delta, eps, evals = cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"], cfg["geometry"]["certify_max_evals"]
    data, report = np.load(run / "arrays.npz", allow_pickle=False), {}
    for tid in sorted({k.split("__")[0] for k in data.files}):
        arr = {k.split("__")[1]: data[k] for k in data.files if k.startswith(tid + "__")}
        s = sc.scene_from_dict(scenes[tid])
        verdicts = mo.certify_trajectory(robot, s, "t0", arr, delta, eps, evals)
        h = mo.trajectory_hash(arr, "t0", sc.scene_hash(s), rhash)
        report[tid] = {"segments": len(verdicts), "all_certified": all(v.status == ge.CLEAR for v in verdicts),
                       "hash_matches_record": h == result["tasks"][tid]["action_hash"]}
    ok = all(r["all_certified"] and r["hash_matches_record"] for r in report.values())
    out = Path(args.report) if args.report else run / "replay.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, {"replay_passed": ok, "run": str(run), "trajectories": report})
    print(json.dumps({"replay_passed": ok, "trajectories": len(report)}))
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Latent causal TAMP stage runner")
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("scene", help="G0: build, snapshot and render a fixture scene")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--case", required=True)
    q.add_argument("--out", required=True)
    q.set_defaults(func=cmd_scene)
    q = sub.add_parser("check", help="G1: robot audit, corner/nominal/clutter skills, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.add_argument("--workers", type=int, default=16)
    q.add_argument("--no-figures", action="store_true", help="re-certification run: skip the G1 figure set")
    q.set_defaults(func=cmd_check)
    q = sub.add_parser("replay", help="G1: independently re-certify a run's stored trajectories")
    q.add_argument("--run", required=True)
    q.add_argument("--report", help="where to write the replay record (default: <run>/replay.json)")
    q.set_defaults(func=cmd_replay)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
