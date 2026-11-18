# NOR-Grid: adapted Ren & Qureshi (ICRA 2024) OSNet + RPNet baseline

**NOR-Grid** adapts *Neural Rearrangement Planning for Object Retrieval from Confined Spaces Perceivable by Robot's In-hand RGB-D Sensor* (Ren & Qureshi, ICRA 2024, arXiv:2402.06976) to the Approach B K ≤ 3 target-repair benchmark.
- **It is not:** an exact reproduction of the paper, or Tang & Sukhatme's SORC.
- **Fidelity and every adaptation:** `reports/METHOD_SWITCH_AND_FIDELITY.md`.
- **Contract:** `../../neural_object_retrieval_plan.md`.

**Mechanism.**
- **OSNet:** MLP tokens → Transformer → blocking distribution over objects (MSE).
- **RPNet:** encoder over robot, goal, target and region tokens; decoder queries = region + selected object; outputs a cost per region (MSE).
- **Labels:** TRAIN-only collision-ignorant reference paths from the unchanged planners (`homotopy.py`).
- **Termination:** the separately labelled **OSRP-openloop-adapter** STOP head (BCE on decided endpoint Y), calibrated on decided VAL Y.
- **Inference:** one-shot, open-loop, at most 3 hypothetical OSNet → RPNet steps, then NOOP / REPAIR / ABSTAIN, sealed before the unchanged physical X/Y teachers verify it.

**Compute.** Laptop only (CPU and RTX 5060). Artifacts live in `~/sorc_grid/` (labels, tensors, models, eval).

| Step | Command (from this directory) |
|---|---|
| Tests | `python3 -m pytest -q tests` |
| TRAIN labels | `ABF_ROOT=~/abf_v3_laptop/root ~/abf_v3_laptop/env2d/bin/python homotopy.py 2d train ~/sorc_grid/labels/homotopy_2d_train.jsonl 3500 W` (3D: `env3d`, `3d … 1766 W`) |
| Tensors → train → calibrate → predict → seal | `./pipeline.sh` |
| Physical verification (sealed files only) | `./eval.sh DOM PRED.jsonl WORKERS CPU0`; queue: `./eval_queue.sh DOM W CPU0` |
| Analysis | `python3 analyze.py ~/sorc_grid/eval/ANALYSIS.json` |
| Figures | `python3 figs.py labels …` / `python3 figs.py policy …` |
| Freeze | `python3 freeze.py reports/NOR_FREEZE_MANIFEST.json` |

The results are in `reports/NEURAL_OBJECT_RETRIEVAL_BASELINE_REPORT.md`.
