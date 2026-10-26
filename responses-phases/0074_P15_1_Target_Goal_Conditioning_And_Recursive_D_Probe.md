# 0074 — P15-1: target / goal conditioning and the recursive-D probe

**Actual result.**
- **Gate:** `runs/p15/P15_1_GATE.json` → **PASS** (engineering).
- **Builder:** a single scene → D-input builder (`p15_retarget.build_record`) re-runs the **training pipeline** for arbitrary (state, target, goal, robot q) queries. It reproduces stored training inputs **exactly** (every channel differs by 0.0).
- **Matched DEV probes:** 176, of which 157 decided. They show that frozen D **ranks** temporary-target feasibility almost perfectly (AUROC 1.000 on original-state probes) but is **severely under-confident**: feasible recall 0.17–0.35 at 0.5.
- **Recalibration** (DEV-only scalar bias + temperature) passes the engineering gate under **root-split cross-validation**: balanced accuracy **0.924** [0.87, 0.99]; feasible recall 0.949; infeasible recall 0.90.
- **Recursion** is enabled with the recalibrated probability. The optional retrain is not run.
- **Spend:** `retarget_probe` 384 / 8,000 CPU-s.

## 1. The corrected builder

`retarget_scene` sets the state's object cells, gives the queried object the target role (kind `target`; the former target becomes an obstacle) and puts the robot at the current q. `build_record` then calls:

```
data.make_query(cfg, key, scene, target_id, goal_cell, {}, "SAFE_RETREAT", PROTOCOL_V2)
  -> data.appearance_anchor -> data.learner_tensors_v2 -> learn_data.visual_features (DINOv2, mask-pooled)
```

**Field audit** (`abc_models.Root`, `Root.numeric`, `ModelD.forward`): D reads
- `object_xy`, `object_radius`;
- `is_active_target` → `tid` and the target-relative features;
- `is_obstacle`;
- `goal_xy` → goal-relative features and the context;
- `robot_q`, `robot_fk_joints` → base and context;
- `visual`.

**The renderer draws identical cylinders, with no target, goal or robot**, so the visual tokens encode object positions only.

**Checks on a DEV root:**

| change | channels that change |
|---|---|
| original query rebuilt | none: all channels equal to the stored record (max \|Δ\| = 0.0) |
| target swap | `is_active_target`, `is_obstacle` only |
| goal swap | `goal_xy` only |
| q change | `robot_q`, `robot_fk_joints` only |
| relocation | `object_xy` and `visual` (re-rendered) |

**What P14's `root_variant` got wrong:** it kept the original `goal_xy`, and in moved states it also kept **stale visual tokens**.

**Pool rule:** the queried object is never in its own blocker pool (`d_predict`).

## 2. Matched physical probes (DEV roots only)

The probe asks **the same task** as the D query: pick object o from q and place it at goal cell g (`skill.plan_skill`, up to 3 state-keyed attempts).
- **CERTIFIED** only from checker-accepted sound certificates for exactly this task (`ordered.certificates_for` plus the sector certificate with o as the moved object).
- **UNKNOWN** otherwise; never scored as a negative.

**Original-state probes** (`PROBES.json`): every movable obstacle of 26 DEV roots, 2 destination slots each; 116 probes: 83 VERIFIED, 20 CERTIFIED, 13 UNKNOWN; **103 decided**.

| interface | balanced accuracy (root CI) | feasible recall | infeasible recall | AUROC | Brier | NLL |
|---|---|---|---|---|---|---|
| P14 `root_variant` (old) | 0.584 [0.52, 0.63] | 0.169 | 1.000 | 0.998 | 0.618 | 5.95 |
| corrected builder | 0.584 [0.52, 0.63] | 0.169 | 1.000 | **1.000** | 0.604 | 5.71 |

**Intermediate-state probes** (`PROBES_INTERMEDIATE.json`):
- **State:** after the first relocation of a VERIFIED ≥ 2-move DEV teacher sequence, with poses and robot q from the recorded witness end.
- **Query:** the next mover at its actual destination.
- **Counts:** 60 probes: 54 VERIFIED, 6 UNKNOWN (no negatives).

| interface | feasible recall | Brier | NLL |
|---|---|---|---|
| old (stale visual tokens, original goal) | 0.204 | 0.683 | 6.94 |
| **corrected** (re-rendered state, actual goal) | **0.352** | **0.528** | **5.37** |

## 3. Diagnosis and the gate

**Diagnosis:**
- D was trained only with the catalogue target in the target role. With an obstacle as target, its logits are shifted far negative (fitted bias −20.0 on the logit scale), yet its **ordering is preserved** (AUROC ≈ 1).
- The P14 failure was mostly a **calibration shift plus stale inputs**, not an absence of signal.

**DEV-only recalibration** (`RECALIBRATION.json`):
- **Model:** p′ = σ((logit p − b) / T).
- **Validation:** root-split 2-fold cross-validation over the 157 decided probes on 36 roots; fitted on one half of the roots and scored on the other.

| metric (cross-validated) | value |
|---|---|
| balanced accuracy | **0.924** [0.871, 0.989] |
| feasible recall | 0.949 |
| infeasible recall | 0.900 |
| AUROC | 0.922 |
| Brier | 0.048 |
| NLL | 0.37 |

**Fit on all DEV probes** (used downstream): b = −19.98, T = 0.762.

**Gate:**
- raw corrected D: **FAIL** (feasible recall 0.169);
- recalibrated corrected D: **PASS** (≥ 0.70 / ≥ 0.70).

**Decision:** recursive D priority is enabled, using the **recalibrated** temporary-target feasibility. The optional D retrain is **not** run; a calibration sufficed.

**Limits:**
- Only temporary-target **feasibility** was validated. D's temporary-target **blocker marginals** have no physical ground truth here, so their use in recursion is unvalidated, and recursion also runs as a geometry-recursion control.
- The DEV probes involve no evaluation roots.
- These are engineering-use thresholds, not a generalization claim.
