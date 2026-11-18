# NOR-Grid data and label audit (local laptop, read-only sources)

Snapshot facts, splits and leakage are in `DATA_AUDIT_P0_paper_agnostic.md` and `dataset_manifest.json`.
- **Splits:** 2D 3,500 / 751 / 749 roots and 3D 1,766 / 364 / 370 (TRAIN / VAL / TEST).
- **Leakage:** 0 families or layouts appear in more than one split.
- **TEST:** outcomes were never opened. The ongoing V3.4 cohort was never touched.

## Supervision present in the snapshots vs constructed here

| Supervision | Present in the snapshots? | Used for | Construction |
|---|---|---|---|
| Path-homotopy blocking counts (OSNet target) | **No** | OSNet MSE | Built TRAIN-only by `homotopy.py` (unchanged planners, collision-ignorant to movable objects) |
| Region cost maps (RPNet target) | **No** | RPNet MSE | Derived from the same reference sweeps (REGION_RULE_V2_MAJORITY) |
| Endpoint Y (target from q_ref) | Yes, deduplicated per endpoint | STOP adapter (BCE); VAL Y only for the temperature | `nor_data.supervision` |
| Ordered X / step phases | Yes | Not used by NOR-Grid (no X head in the paper) | — |
| Q2 placement trials | NOT_LOCAL | Not used | — |

**Nothing was substituted.** No ground-truth blocker IDs, K classes, repair orders or Approach B probabilities were used as homotopy labels.

## Reference paths (TRAIN only)

**Cost:** 16.7 CPU-hours on the laptop CPU, within the declared caps of 15 h (2D) and 12 h (3D). There were 0 errors.

| | 2D (NOR_HOMOTOPY_2D_V1) | 3D (NOR_HOMOTOPY_3D_V1) |
|---|---|---|
| TRAIN roots labelled | 3,500 / 3,500 | 1,766 / 1,766 |
| Verified collision-ignorant reference paths per root | 6 (every root) | mean 4.50 (6: 532, 5: 413, 4: 407, 3: 280, 2: 93, 1: 34, 0: 7) |
| Roots with no verified path (no OSNet/RPNet label; STOP Y still used) | 0 | 7 |
| CPU-s per root (mean) / total | 12.0 / 11.7 h | 10.3 / 5.0 h |
| S0 states with zero blocking objects (OSNet sample masked) | 386 | 97 |

**What the planner checks.**
- **2D:** the unchanged `bd_2d.t_goal` / `plan_skill` (full 3R arm and gripper, declared side-grasp pairs, FAST budget, start at q_ref), run in a scene with only the target and fixed structure. Sweep = `p14_sweep_index.swept_cells`.
- **3D:** the unchanged SHELF66V3 `plan_pick_place` with the scene's grasp poses, in a target-only scene whose arm ceiling is held at the full scene's value. The paths are replayed in the full scene through `_object_hits` plus the carried-footprint rule. Sweep = an exact MuJoCo distance check for a generic column at each cell.

**P2 pilot-gate revision.**
- The region-blocking rule was changed from the union of sweeps to **majority** (swept by ≥ half the paths), after the pilot showed the union blocks 63 of 64 cells in 2D.
- The change was made before any full training. The stored sweeps were not changed.

## Training tensors (`samples.py`)

| | 2D | 3D |
|---|---|---|
| Hypothetical states (S0, label-policy rollout, verified-repair prefixes, endpoint scenes) | 33,922 | 16,069 |
| OSNet samples (states with ≥ 1 blocker) | 17,302 | 9,224 |
| RPNet samples (state, object) | 52,617 | 20,654 |
| STOP: TRAIN endpoint Y / VAL endpoint Y (calibration only) | 18,777 / 1,457 | 7,671 / 751 |
| TRAIN group holdout (early stopping) | 360 roots | 198 roots |

The goal-free ablation tensors (`NOR_GOAL=0`) have identical counts, with every goal-derived feature zeroed.
