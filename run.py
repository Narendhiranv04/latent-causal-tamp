"""Sole command dispatcher (Guide v1.7 §1): argument parsing, dispatch and the
cross-stage replay. Never imported by other modules. Each stage's command body lives
with the module that owns that stage (moved here-from at G4A, behaviour unchanged):

    scene (G0)          viz.cmd_scene                 runs/g0_scene
    check (G1)          figures.cmd_check             runs/g1_robot
    intervene (G2)      intervention_figures.cmd_intervene    runs/g2_interventions
    solve (G3)          assignment_figures.cmd_solve  runs/g3_repairs        (FROZEN_CONTROL)
    case-analysis (G3.5) case_figures.cmd_case_analysis runs/g3_5_initial_scene (INITIAL_SCENE_ONE_SHOT_V1)
    g4a-plan, g4a-audit audit.cmd_g4a_plan / cmd_g4a_audit runs/g4a_evidence_audit
    teacher-plan/-run   teacher.cmd_teacher_plan / cmd_teacher_run runs/g4a_teacher_budget_diagnostic (G4A follow-up)
    g4d-plan, g4d-migrate g4d.cmd_g4d_plan / cmd_g4d_migrate runs/g4d_migration (V2 migration; no collection)
    g4d-legacy/-finalize/-run/-judge g4d_gate.*   runs/g4d_evidence (corrections, bounded collection, gate)
    g4b                 g4b.cmd_g4b                   runs/g4b_sampler_exact (exact sampler proof; no planner)
    g4c-plan            g4c.cmd_g4c_plan              runs/g4c_preflight (frozen 20-root plan; no collection)
    g4c-pilot-*         g4c_pilot.*                   runs/g4c_pilot (authorized 5-root pilot: finalize, run, judge)
    g4c-d2-precheck     d2_precheck.run               runs/g4c_d2_precheck (witness-first static precheck; no teacher)
    g4c-d2-poc-*        d2_poc.*                      runs/g4c_d2_poc_s (authorized POC_S: finalize, run, judge)
    replay              run.cmd_replay                any run directory

    python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
    python run.py replay --run runs/g1_robot
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import assignment_figures as afig
import audit
import case_figures as cfig
import config as cf
import figures as fig
import g4d
import g4d_gate
import g4b
import g4c
import g4c_pilot
import d2_poc
import d2_precheck
import geometry as ge
import intervention_figures as ifig
import motion as mo
import scene as sc
import teacher
import viz


def cmd_replay(args) -> int:
    """Re-certify every stored trajectory from the run's own files and hashes."""
    run = Path(args.run)
    archived = json.loads((run / "config.json").read_text())["config"]
    filled = sorted(set(cf.SCHEMA) - set(archived))      # sections introduced after this run; unused by replay
    current = cf.load_config(args.config)
    keys = {s: sorted(set(cf.SCHEMA[s]) - set(archived[s])) for s in archived if set(cf.SCHEMA[s]) - set(archived[s])}
    cfg = cf.validate_config({**{s: current[s] for s in filled},
                              **{s: {**{k: current[s][k] for k in keys.get(s, [])}, **v} for s, v in archived.items()}})
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
    cf.write_json(out, {"replay_passed": ok, "run": str(run), "config_sections_filled_from_current": filled,
                        **({"config_keys_filled_from_current": keys} if keys else {}),
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
    q.set_defaults(func=viz.cmd_scene)
    q = sub.add_parser("check", help="G1: robot audit, corner/nominal/clutter skills, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.add_argument("--workers", type=int, default=16)
    q.add_argument("--no-figures", action="store_true", help="re-certification run: skip the G1 figure set")
    q.set_defaults(func=fig.cmd_check)
    q = sub.add_parser("intervene", help="G2: frozen reference actions, diagnostic interventions, attribution")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.set_defaults(func=ifig.cmd_intervene)
    q = sub.add_parser("solve", help="G3: A0 assignment, executable move-once repair search, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.set_defaults(func=afig.cmd_solve)
    q = sub.add_parser("case-analysis", help="G3.5: R0-R6 one-shot initial-scene protocol cases, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--fixtures", default="fixtures.json")
    q.add_argument("--out", required=True)
    q.set_defaults(func=cfig.cmd_case_analysis)
    q = sub.add_parser("g4a-plan", help="G4A: freeze roots, automatic candidates, panels and budgets (no outcomes)")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--out", required=True)
    q.set_defaults(func=audit.cmd_g4a_plan)
    q = sub.add_parser("g4a-audit", help="G4A: primary episodes, first-pass teacher audit, panels, controls, figures")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--out", required=True, help="directory holding g4a_plan.json")
    q.add_argument("--limit", type=int, help="pilot: only the first N planned queries")
    q.set_defaults(func=audit.cmd_g4a_audit)
    for name, fn, hlp in (("teacher-plan", teacher.cmd_teacher_plan, "G4A follow-up: freeze the bounded teacher diagnostic"),
                          ("teacher-run", teacher.cmd_teacher_run, "G4A follow-up: guarded teacher-budget evaluations")):
        q = sub.add_parser(name, help=hlp)
        q.add_argument("--config", default="config.toml")
        q.add_argument("--g4a", default="runs/g4a_evidence_audit")
        q.add_argument("--out", required=True)
        q.set_defaults(func=fn)
    for name, fn, hlp in (("g4d-plan", g4d.cmd_g4d_plan, "G4D: freeze the sparse V2 evidence plan (no outcomes, no budget)"),
                          ("g4d-migrate", g4d.cmd_g4d_migrate, "G4D: V1->V2 migration manifest, legacy label scope audit, figures"),
                          ("g4d-legacy", g4d_gate.cmd_g4d_legacy, "G4D: revalidate archived evidence, derived omission pairs"),
                          ("g4d-finalize", g4d_gate.cmd_g4d_finalize, "G4D: final execution plan linked to the pending plan"),
                          ("g4d-run", g4d_gate.cmd_g4d_run, "G4D: guarded, resumable bounded collection"),
                          ("g4d-judge", g4d_gate.cmd_g4d_judge, "G4D: evidence from re-checked checkpoints, gate, figures")):
        q = sub.add_parser(name, help=hlp)
        q.add_argument("--config", default="config.toml")
        q.add_argument("--config-v2", default="config_v2.toml")
        q.add_argument("--out", required=True)
        q.set_defaults(func=fn)
    q = sub.add_parser("g4b", help="G4B: exact Boltzmann sampler certification on finite spaces (no planner calls)")
    q.add_argument("--out", required=True)
    q.set_defaults(func=g4b.cmd_g4b)
    q = sub.add_parser("g4c-plan", help="G4C-P0: freeze the 20-root A/B/C development plan (no teacher/planner calls)")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--config-v2", default="config_v2.toml")
    q.add_argument("--out", required=True)
    q.set_defaults(func=g4c.cmd_g4c_plan)
    for name, fn, hlp in (("g4c-pilot-finalize", g4c_pilot.cmd_g4c_pilot_finalize, "G4C-P1: authorization record + derived pilot plan"),
                          ("g4c-pilot-run", g4c_pilot.cmd_g4c_pilot_run, "G4C-P1: guarded collection of the 59 pilot units"),
                          ("g4c-pilot-judge", g4c_pilot.cmd_g4c_pilot_judge, "G4C-P1: revalidated evidence, judge, figures")):
        q = sub.add_parser(name, help=hlp)
        q.add_argument("--config", default="config.toml")
        q.add_argument("--config-v2", default="config_v2.toml")
        q.add_argument("--instruction", default="instruction-phase-md/G4C_P1_5Root_Pilot_Collection_Instructions.md")
        q.add_argument("--out", required=True)
        q.set_defaults(func=fn)
    q = sub.add_parser("g4c-d2-precheck", help="G4C-D2-P0: static witness-first construction precheck (no teacher calls)")
    q.add_argument("--config", default="config.toml")
    q.add_argument("--out", required=True)
    q.set_defaults(func=d2_precheck.run)
    for name, fn, hlp in (("g4c-d2-poc-finalize", d2_poc.cmd_finalize, "G4C-D2-P1: authorization record + frozen POC_S plan"),
                          ("g4c-d2-poc-run", d2_poc.cmd_run, "G4C-D2-P1: guarded collection (2 fresh bases + 68 units)"),
                          ("g4c-d2-poc-judge", d2_poc.cmd_judge, "G4C-D2-P1: revalidated evidence, Q1-Q6, figures")):
        q = sub.add_parser(name, help=hlp)
        q.add_argument("--config", default="config.toml")
        q.add_argument("--config-v2", default="config_v2.toml")
        q.add_argument("--instruction", default="instruction-phase-md/G4C_D2_P1_Witness_First_POC_S_Instructions.md")
        q.add_argument("--out", required=True)
        q.set_defaults(func=fn)
    q = sub.add_parser("replay", help="G1-G3.5: independently re-certify a run's stored trajectories")
    q.add_argument("--run", required=True)
    q.add_argument("--report", help="where to write the replay record (default: <run>/replay.json)")
    q.add_argument("--config", default="config.toml", help="only for config sections the run predates")
    q.set_defaults(func=cmd_replay)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
