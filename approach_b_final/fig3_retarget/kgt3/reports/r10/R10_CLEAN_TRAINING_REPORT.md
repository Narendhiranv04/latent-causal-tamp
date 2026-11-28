# R10.2: clean training lineage and model freeze

Every learned component was retrained **from fresh initialisation on gvlab2** (RTX 5090, envgpu torch 2.9.1+cu130). Training used only the LEGOLAS_FINAL_v1 canonical views:
- snapshot `abf_r10_70e8ec7db1d4c56b`;
- canonical-TRAIN Q2 and its scalers;
- the local-label family split.

The recipes are the frozen R7 ones (`r7.py`, `arms.py`, `complete_repair_cvae/train.py`) with seeds 0, 1, 2. No checkpoint was reused or warm-started.

- **Queue and logs:** `r10/r10q.sh`; job log `training/jobs.jsonl`, 88 jobs with rc 0.
- **Freeze:** `R10_MODEL_FREEZE.json` hashes 90 checkpoints, the packs, the scalers and the release seal.

A first launch was aborted and discarded after the release tests found the Q2 / duplicate-conflict bugs (see `R10_DATASET_RELEASE_REPORT.md`).

## Stages (VAL = canonical VAL only)

**Stage A (cVAE).** Q2 placement pretraining (`placement.fit cvae`), then the task-conditioned `q2init_all` cVAE (fixed production step budget, VAL ELBO), plus the matched no-task control from the same pretraining:

| Domain | Seed 0 | Seed 1 | Seed 2 | No-task s0 / s1 / s2 |
|---|---|---|---|---|
| 3D | 2.0405 | **2.0315** | 2.0344 | 2.111 / 2.094 / 2.177 |
| 2D | 2.7209 | 2.7385 | **2.7153** | 2.725 / 2.738 / 2.704 |

Seed 1 is selected in 3D and seed 2 in 2D (lowest VAL ELBO).

**Stage B (coupled X/Y, arm D).** Original observed-data likelihood. Y and the encoder are frozen afterwards; the Y hash is asserted in every stage-C fit.

| Domain | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| 3D VAL NLL | 1.451 | 1.361 | 1.418 |
| 2D VAL NLL | 1.687 | 1.719 | 1.713 |

**Stage C (fresh X heads).** Trained on frozen stage-B Y with recipe hi: lr 1e-3, ≤ 60 epochs, patience 10, family-balanced, no O2 loss. Data are original replay (3D 1,722 / 2D 3,199 roots) plus strict local labels:

| Domain | TRAIN views | VAL views | VAL families |
|---|---|---|---|
| 3D | 535 | 180 | 87 |
| 2D | 883 | 362 | 101 |

Local-family VAL NLL by seed (s0 / s1 / s2):

| Arm | 3D | 2D |
|---|---|---|
| A0 (ordered X, original data) | .577 / .532 / .532 | .473 / .461 / .472 |
| A1 (ordered X, + local labels) | .475 / .461 / .431 | .441 / .435 / .412 |
| M0 (MLP, original data) | .540 / .528 / .602 | .480 / .485 / .469 |
| M1 (MLP, + local labels) | .347 / .349 / .333 | .425 / .330 / .411 |
| G0 (GNN, original data; the composition G0 control) | .421 / .360 / .435 | .375 / .381 / .367 |
| **G1 (GNN, + local labels)** | **.254 / .257 / .249** | **.235 / .237 / .216** |
| G1 ORDINV | .449 / .451 / .435 | .324 / .309 / .323 |
| G1 UNCOUPLED | .266 / .226 / .247 | .254 / .264 / .232 |
| G1 DIRECT (short-success BCE) | .448 / .387 / .401 | .504 / .478 / .504 |

- **Supervision.** Adding strict local labels improves every representation in both domains.
- **Representation.** G1 has the lowest VAL NLL among the base arms.
- **Coupling.** In 3D, UNCOUPLED's seed mean (.246) is slightly *below* G1's (.253) on VAL NLL; in 2D G1 is lower (.229 vs .250). The R7 report's statement that coupling matters on VAL does not carry over to 3D. Its physical effect is measured in R10.9.
- **Controls.** TaskFM (flow matching, R5 recipe, scratch encoder: no Q2 initialisation, a disclosed supervision difference) and the complete-repair cVAE (CR; output ≤ 3 actions; hyperparameters read from the production sampler config, weights fresh) were trained on the same canonical views.

| Control (s0 / s1 / s2) | 3D | 2D |
|---|---|---|
| TaskFM VAL FM loss | 1.443 / 1.418 / 1.411 | 1.335 / 1.344 / 1.331 |
| CR VAL select | 7.564 / **7.540** / 7.564 | 8.479 / 8.577 / **8.417** |

CR's pick is the lowest VAL select criterion: 3D r10_s1, 2D r10_s2.

## Stage D: selection (predefined VAL rules only; `r7.py select`)

| Domain | X (rule R5.2; seed = lowest VAL) | Temperature (R5.3, adopt iff ΔNLL ≥ .005) | cVAE | Primary spec |
|---|---|---|---|---|
| 3D | G1 s2, .249 | T 1.194, Δ .0031, **not adopted** (raw) | q2init_all s1 | `R7:3d_G1_hi_base_s2` |
| 2D | G1 s2, .216 | T 1.064, Δ .0001, **not adopted** (raw) | q2init_all s2 | `R7:2d_G1_hi_base_s2` |

- **Change from R7.** In 2D the selected seeds differ from R7 (X s0 → s2, cVAE s0 → s2) because the training and validation memberships changed. 3D selects the same seeds as R7.
- **Seed-matched bundle.** In 2D the full seed-matched bundle s2 is the primary bundle (SEED2 is an alias).
- **Single primary bundle.** The selected bundle per domain is used everywhere: short horizon, H3, REC, GA and the floor.
- **Strict loader.** The composition env files (`comp_configs/*.env`) carry the X, cVAE and base sha256 values that the strict loader asserts (`R10_STRICT=1`).

## Reproducibility / parity note

Stage-B 3D seed 0 VAL NLL is 1.451 here, against 1.363 in R7 on Blackwell. The 3D rows are identical, but the canonical snapshot orders rows by root id, which changes the data shuffle. The torch build and GPU also differ. Fits are seed-deterministic given order and device; cross-host and cross-order variation is reported, not tuned away.

## Cost

About 0.6 GPU process-hours and about 1.5 CPU-h for 88 jobs (each 8–250 s).
