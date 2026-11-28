#!/usr/bin/env python3
"""MCTS_PROTOCOL_FREEZE.json writer / checker (gvlab2).
    $PYG freeze.py write TUNING_RESULT.json OUT.json     (after the DEV tuning; before any BENCH_COMP planning)
    $PYG freeze.py check FREEZE.json                      (plan_eval.sh guard: code, model and roster sha256 must match, else exit 1)"""
from __future__ import annotations

import hashlib, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
CODE = KG.parent.parent                                                   # approach_b_final
NW = Path("/home/projects/long-horizon/naren_workspace")
R7 = NW / "fig3/final/r7/runs"
ROSTER = NW / "r10/comp/PUBLIC_bench_comp_3d.jsonl"
ROSTER_SHA = "9e8d6a7e44abb05a50a1208c4f1ec2c979212f14e8ed8f2070d0249dc75da058"
CODE_FILES = ["fig3_retarget/kgt3/mcts_poc/mcts_ga.py", "fig3_retarget/kgt3/mcts_poc/anytime.py", "fig3_retarget/kgt3/mcts_poc/evaljobs.py",
              "fig3_retarget/kgt3/mcts_poc/analyze.py", "fig3_retarget/kgt3/planners.py", "fig3_retarget/kgt3/compose.py", "fig3_retarget/kgt3/r6.py",
              "fig3_retarget/kgt3/r53.py", "fig3_retarget/kgt3/learn.py", "fig3_retarget/recursive.py",
              "fig3_retarget/rank.py", "fig3_retarget/models.py", "fig3_retarget/views.py", "construct.py", "fig3_retarget/physical3d.py",
              "fig3_retarget/kgt3/reports/final/r8c_config.json"]
MODELS = {"X_3d_G1_hi_base_s2": R7 / "xl/ckpt/3d_G1_hi_base_s2/model.pt", "XY_base_D_s2": R7 / "xy/p2_3d/D_s2/model.pt",
          "cVAE_q2init_all_s1": R7 / "r7_task/3d/q2init_all_s1/model.pt"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(tuning, out):
    T = json.loads(Path(tuning).read_text())
    assert sha(ROSTER) == ROSTER_SHA, "public roster sha mismatch"
    cfg = json.loads((KG / "reports/final/r8c_config.json").read_text())["3d"]
    assert sha(MODELS["X_3d_G1_hi_base_s2"]) == cfg["checkpoint_sha256"] and sha(MODELS["cVAE_q2init_all_s1"]) == cfg["cvae_sha256"], "R9 checkpoint mismatch"
    bundle = Path(os.environ.get("FIG3_BUNDLE", ""))
    fr = {"label": "GA-MCTS proof-of-concept protocol freeze (development-only tuning on the 20 exposed DEV roots; written before any BENCH_COMP planning)",
          "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "roster": {"file": str(ROSTER), "sha256": ROSTER_SHA, "n_roots": sum(1 for _ in open(ROSTER)), "content": "the 99 BENCH_COMP_3D roots, public rows only (= sealed R8B public roster)",
                     "planner_input": "public rows only via r6.public_roots('r10comp'); the private index is read only by the evaluator AFTER plans are sealed"},
          "arms": {"H3": "rank.b0 rule with the final model (R8C H3), r6.py plan", "REC": "REC-ORDERED (Fig. 3A), r6.py plan, R8C config",
                   "GA": "planners.ga AUTO (Fig. 3B), anytime trajectory; the 180 s point is planners.plan unchanged",
                   "GA-MCTS": "mcts_ga.plan (planners.plan with mcts_ga.search swapped in), anytime trajectory"},
          "mcts_config": {**T["selected_mcfg"], "seed": None}, "mcts_config_id": T["selected"], "tuning": {"rule": T["rule"], "tied": T["tied"], "configs": T["configs"]},
          "seeds": {"predeclared": [0, 1, 2], "primary": 0, "note": "GA is deterministic (one trajectory); seeds 1/2 are GA-MCTS robustness only"},
          "budgets_s": [5, 10, 20, 30, 60, 180], "horizon_s": 180, "anytime_select_reserve_s": 0.5,
          "planner_config": {"file": "reports/final/r8c_config.json", "3d": cfg, "R6_FLOOR": "final", "deadline": "180 s end-to-end (floor + search + selection; 5 s selection reserve)"},
          "models_sha256": {k: sha(p) for k, p in MODELS.items()}, "bundle": {"FIG3_BUNDLE": str(bundle), "files_sha256": {f.name: sha(f) for f in sorted(bundle.glob("*")) if f.is_file()} if bundle.is_dir() else None},
          "code_sha256": {f: sha(CODE / f) for f in CODE_FILES},
          "verification": {"contract": "unchanged fig3_retarget/physical3d.py work: X_CHUNKED + endpoint Y + continuous replay (R8C contract), W workers, 4, cap 5000, 150.0 s",
                           "dedup": "exact (root, ordered object names, chunk bounds) across methods / budgets / seeds -> one job",
                           "reuse": "sealed R8C records naren_workspace/fig3/final/{r8c,r8c_ctrl}/{jobs,phys}_r8b* when root, ordered names, bounds AND scene path match (r6.archive_r10)",
                           "success": "X == 1 and Y == 1 and replay == 1; unresolved = not verified (never certified failure)"},
          "analysis": {"primary": "verified success, GA-MCTS seed 0 vs GA, at EACH predeclared budget (5/10/20/30/60/180 s), exact two-sided sign test, Holm over the six budgets; 95% CI by family bootstrap (2,000 resamples, seed 0; family = private r10_family/r10_template if present else root)",
                       "secondary": ["learned energy of the selected plan and regret vs per-root best", "time to first / final incumbent", "long (4-5) repair success",
                                     "seed robustness (seeds 1, 2)", "H3 / REC reference rows", "deadline overruns", "normalized area under the success-vs-log-budget curve"],
                       "no_retrospective_budget_choice": True},
          "compute_expectation": "exclusive GPU window (CUDA 0), 4 shards x 2 CPUs; timing claims valid only under that window"}
    Path(out).write_text(json.dumps(fr, indent=1, default=str))
    print(json.dumps({k: fr[k] for k in ("mcts_config", "mcts_config_id", "seeds", "budgets_s")}, indent=1))


def check(fp):
    fr = json.loads(Path(fp).read_text())
    bad = [f for f, h in fr["code_sha256"].items() if sha(CODE / f) != h] + [k for k, h in fr["models_sha256"].items() if sha(MODELS[k]) != h]
    if sha(fr["roster"]["file"]) != fr["roster"]["sha256"]:
        bad.append("roster")
    print(json.dumps({"freeze_ok": not bad, "mismatch": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    {"write": lambda: write(sys.argv[2], sys.argv[3]), "check": lambda: check(sys.argv[2])}[sys.argv[1]]()
