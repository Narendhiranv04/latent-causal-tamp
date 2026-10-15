"""Sole command dispatcher (Guide v1.6 §1). Never imported by other modules.

Active commands: scene (G0), check and replay (G1), intervene (G2), solve (G3). Later commands arrive with their stage.

    python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
    python run.py check --config config.toml --out runs/g1_robot
    python run.py replay --run runs/g1_robot
    python run.py intervene --config config.toml --out runs/g2_interventions
    python run.py solve --config config.toml --out runs/g3_repairs
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
from multiprocessing import Pool
from pathlib import Path

import matplotlib
import numpy as np
import PIL
import scipy
from PIL import Image

import assignment_figures as afig
import config as cf
import diagnostics as dg
import figures as fig
import geometry as ge
import intervention_figures as ifig
import interventions as iv
import motion as mo
import scene as sc
import skill as sk
import verify as vf
import viz


def load_fixture(path: str, case: str) -> dict:
    fixtures = cf.validate_fixtures(json.loads(Path(path).read_text())["fixtures"])
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
    cfg = cf.load_config(args.config)
    fx = load_fixture(args.fixtures, args.case)
    s = sc.make_scene(cfg, fx["root_id"], fx["variant_id"], fx["seed"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chash, shash, rhash = cf.config_hash(cfg), sc.scene_hash(s), s.robot_profile_hash

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
def cmd_check(args) -> int:
    cfg = cf.load_config(args.config)
    fixtures = cf.validate_fixtures(json.loads(Path(args.fixtures).read_text())["fixtures"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot, chash, rhash = ge.make_robot(cfg), cf.config_hash(cfg), cf.robot_profile_hash(cfg)
    with Pool(args.workers) as pool:
        done = {tid: (s, res, secs) for tid, s, res, secs in pool.imap_unordered(sk.run_task, sk.g1_jobs(cfg, fixtures))}
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
    gate = {"home_clear_of_all_64_cells": sk.home_check(cfg)["home"]["status"] == ge.CLEAR,
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
        "stage": "G1", "gate_checks_passed": all(gate.values()), "gate": gate, "home_check": sk.home_check(cfg),
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


# ------------------------------------------------------------------ G2
def run_family(job):
    """Pool worker: plan, freeze and intervene on one G2 fixture."""
    cfg, name, fx = job
    return iv.reference_family(ge.make_robot(cfg), cfg, name, fx)


def cmd_intervene(args) -> int:
    cfg = cf.load_config(args.config)
    fixtures = cf.validate_fixtures(json.loads(Path(args.fixtures).read_text())["fixtures"])
    g2 = {k: fx for k, fx in fixtures.items() if fx["stage"] == "G2"}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot, chash = ge.make_robot(cfg), cf.config_hash(cfg)
    with Pool(len(g2)) as pool:
        fams = {f["name"]: f for f in pool.imap_unordered(run_family, [(cfg, k, fx) for k, fx in g2.items()])}
    families, gates, tasks, scenes, arrays = {}, {}, {}, {}, {}
    for name in sorted(fams):
        f = fams[name]
        families[name] = iv.family_summary(f, cfg)
        gates[name] = iv.family_gates(families[name], g2[name]["blockers"])
        if f["frozen"] is not None:              # replay-compatible: <name>__q etc. + scenes[name]
            tasks[name] = {"action_hash": f["frozen"].action_hash}
            scenes[name] = sc.scene_to_dict(f["scene"])
            arrays.update({f"{name}__{k}": v for k, v in f["frozen"].arrays.items()})
        for s in f["snaps"]:
            scenes[f"{name}/{s.variant}"] = sc.scene_to_dict(s.scene)
            Image.fromarray(viz.render_observation(s.scene, cfg["render"]["image_px"])[0]).save(
                out / f"obs_{name}_{s.variant}.png")             # clean learner observation, no overlays
    ifig.g2_figures(out, robot, cfg, fams)
    ok = all(g and all(g.values()) for g in gates.values())
    _write_json(out / "config.json", {"config_hash": chash, "config": cfg})
    _write_json(out / "scenes.json", scenes)
    np.savez_compressed(out / "arrays.npz", **arrays)
    _write_json(out / "result.json", {
        "stage": "G2", "gate_checks_passed": ok, "gates": gates, "families": families, "tasks": tasks,
        "config_hash": chash, "robot_profile_hash": cf.robot_profile_hash(cfg),
        "verification_scope": "FIXED_ACTION_KINEMATIC_REPLAY (privileged diagnostic edits; no corrective motion)",
        "simulation_replay_status": "NOT_RUN", "physical_execution_status": "NOT_RUN"})
    with open(out / "metrics.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "variant", "parent", "edit", "F_fixed", "whole_scene_replay", "Delta_I", "c", "oracle_evals"])
        w.writerows([[n, x["variant"], x["parent"], x["edit"] and f"{x['edit']['kind']} {x['edit']['obj_id']}",
                      x["F_fixed"], x["whole_scene_replay"], x.get("Delta_I"),
                      " ".join(f"{i}={c['c']}" for i, c in x["contributions"].items()), x["oracle_evals"]]
                     for n, fam in families.items() for x in fam["nodes"]])
    _write_manifest(out, {"planner_base": cfg["planner2d"]["seed"], "per_query": "crc32(task/connector)"}, chash,
                    {"families": {n: f["frozen"] for n, f in families.items()}})
    print(json.dumps({"out": str(out), "gates": gates}))
    return 0 if ok else 1


# ------------------------------------------------------------------ G3
def run_repair(job):
    """Pool worker: A0 terminal problem, executable repair search and replay for one G3 fixture."""
    cfg, name, fx = job
    try:
        return name, vf.run_fixture(ge.make_robot(cfg), cfg, name, fx)
    except iv.FixtureUnavailable as e:
        return name, {"name": name, "unavailable": f"CONSTRUCTION_UNAVAILABLE: {e}"}


def cmd_solve(args) -> int:
    cfg = cf.load_config(args.config)
    fixtures = cf.validate_fixtures(json.loads(Path(args.fixtures).read_text())["fixtures"])
    g3 = {k: fx for k, fx in fixtures.items() if fx["stage"] == "G3"}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot, chash, rhash = ge.make_robot(cfg), cf.config_hash(cfg), cf.robot_profile_hash(cfg)
    with Pool(len(g3)) as pool:
        res = dict(pool.imap_unordered(run_repair, [(cfg, k, fx) for k, fx in g3.items()]))
    records, tasks, scenes, arrays = vf.archive(res, rhash)
    afig.g3_figures(out, robot, cfg, res)
    rows = afig.summary_rows(res)
    ok = all(r["replay"]["replay_passed"] for r in res.values() if r.get("replay"))
    _write_json(out / "config.json", {"config_hash": chash, "config": cfg})
    _write_json(out / "scenes.json", scenes)
    np.savez_compressed(out / "arrays.npz", **arrays)
    _write_json(out / "result.json", {
        "stage": "G3", "gate_checks_passed": ok, "fixtures": records, "tasks": tasks, "summary": rows,
        "config_hash": chash, "robot_profile_hash": rhash,
        "solver": {"matching": "scipy.optimize.linear_sum_assignment", "k_best": "Murty partitioning (solve.kbest)",
                   "scipy": scipy.__version__},
        "verification_scope": "KINEMATIC_3R_RELOCATIONS_AND_FIXED_GAMMA0_REPLAY (no dynamics, no simulation)",
        "simulation_replay_status": "NOT_RUN", "physical_execution_status": "NOT_RUN"})
    with open(out / "metrics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, ["fixture", "domain", "|D|", "LB", "best verified", "minimality", "status", "stop",
                                "plans", "attempts", "replay"])
        w.writeheader()
        w.writerows(rows)
    _write_manifest(out, {"planner_base": cfg["planner2d"]["seed"], "per_query": "crc32(episode key)"}, chash,
                    {"frozen_actions": {n: r["frozen"].action_hash for n, r in res.items() if "frozen" in r}})
    print(json.dumps({"out": str(out), "replay_passed": ok, "summary": rows}))
    return 0 if ok else 1


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
    archived = json.loads((run / "config.json").read_text())["config"]
    filled = sorted(set(cf.SCHEMA) - set(archived))      # sections introduced after this run; unused by replay
    current = cf.load_config(args.config)
    cfg = cf.validate_config({**{s: current[s] for s in filled}, **archived})
    scenes, result = json.loads((run / "scenes.json").read_text()), json.loads((run / "result.json").read_text())
    robot, rhash = ge.make_robot(cfg), cf.robot_profile_hash(cfg)
    delta, eps, evals = cfg["suite"]["margin_m"], cfg["geometry"]["numeric_margin_band_m"], cfg["geometry"]["certify_max_evals"]
    data, report = np.load(run / "arrays.npz", allow_pickle=False), {}
    for tid in sorted({k.split("__")[0] for k in data.files}):
        arr = {k.split("__")[1]: data[k] for k in data.files if k.startswith(tid + "__")}
        task = result["tasks"][tid]
        s, target = sc.scene_from_dict(scenes[tid]), task.get("target", "t0")
        verdicts = mo.certify_trajectory(robot, s, target, arr, delta, eps, evals)
        bound = sc.scene_from_dict(scenes[task.get("hash_scene", tid)])     # G3: gamma_0 keeps its reference identity
        h = mo.trajectory_hash(arr, target, sc.scene_hash(bound), rhash)
        report[tid] = {"segments": len(verdicts), "all_certified": all(v.status == ge.CLEAR for v in verdicts),
                       "hash_matches_record": h == result["tasks"][tid]["action_hash"]}
    ok = all(r["all_certified"] and r["hash_matches_record"] for r in report.values())
    out = Path(args.report) if args.report else run / "replay.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, {"replay_passed": ok, "run": str(run), "config_sections_filled_from_current": filled,
                      "trajectories": report})
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
    q = sub.add_parser("intervene", help="G2: frozen reference actions, diagnostic interventions, attribution")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.set_defaults(func=cmd_intervene)
    q = sub.add_parser("solve", help="G3: A0 assignment, executable move-once repair search, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.set_defaults(func=cmd_solve)
    q = sub.add_parser("replay", help="G1-G3: independently re-certify a run's stored trajectories")
    q.add_argument("--run", required=True)
    q.add_argument("--report", help="where to write the replay record (default: <run>/replay.json)")
    q.add_argument("--config", default="config.toml", help="only for config sections the run predates")
    q.set_defaults(func=cmd_replay)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
