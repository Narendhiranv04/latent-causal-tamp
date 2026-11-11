# 0033 — P9-L3b: matched saved-data comparison, P9 PoE vs unique-factor root model

**Actual result.** The comparison ran under one frozen plan (`runs/p9/l3/l3b/L3B_plan.json`, `sha256:3b4913e7…`, written before the first update), entirely on saved data:
- **Trained:** 12 mandatory runs — unique-factor B-full, B-structured, geometry-only B-full and C-full × seeds 0–2, matched 200 updates — plus the optional matched **400-update pair** (unique and PoE B-full × 3 seeds, both from scratch).
- **Comparators (not retrained):** 15 P9-L2 checkpoints (PoE B-full / B-structured / C-full, SF, A × 3 seeds), evaluated by the same code.
- **Compute:** **4,630 / 8,000 CPU-s** for all of L3a + L3b, failed attempts and regression included. **0** teacher, IK or planner calls.

**Engineering gate:** `runs/p9/l3/L3B_GATE.json` → **PASS** (12/12). Every trained unique model is invariant to duplication, permutation and disconnected candidates (≤ 1.4e-14); every PoE model is not (0.11–0.15).

**Scientific outcome.** The validation contrasts are predeclared; the disclosed test is a legacy diagnostic and never selects.
- **Predictive parity between formulations at matched training.**
  - Validation root NLL, unique − PoE: B-full +0.046 [−0.050, +0.175]; B-structured +0.003 [−0.102, +0.119]; C-full −0.064 [−0.169, +0.011]. At 400 updates: +0.001 [−0.027, +0.025].
  - Neutral calibrated metrics move in both directions.
  - **No predictive reason to prefer either formulation.** The difference is semantic: only the unique-factor model satisfies the mandatory catalogue invariances.
- **Within the unique formulation**, generic coupling (B-full − B-structured −0.33 [−0.66, −0.07]) and joint vs factorized (B-full − SF −0.52 [−1.12, −0.12]) are favoured on validation. But **95 % of B-full's validation NLL comes from 3 roots**.

Previous turn sync: `4be6d803bbfcff693b8055eb4e2e25707a8da4ee`. Gates L3a-0 and L3a-1 PASS (reports 0031, 0032).

## 1. Protocol

- **Data:** P8c learner view, `dataset.pt` (sha256 recorded in the plan).
  - 178 training roots; 12 validation roots (all choices); 24 disclosed-test roots (diagnostic only).
  - All decided labels: VERIFIED 1, CERTIFIED 0, OPNEG-v1 BUDGET_INFEASIBLE 0; UNKNOWN and NOT_RUN missing. Root key lists are frozen in the plan.
- **Matching (identical to P9-L2 PoE runs):**
  - `torch.manual_seed(seed)` before `build`;
  - `abc8.RootSampler(train, 12, seed)`;
  - AdamW lr 1e-3, wd 1e-4; clip 10; 200 updates;
  - best validation root NLL of the model's **own** likelihood every 20 updates;
  - temperature and threshold from validation only.
- **Objective:** `mean_roots(−log P_U(D_c)) + 1·static BCE + 1·log-Huber witnessed J`, the same auxiliaries as P9-L2.
- **Same initialization and batches** as the PoE run of the same arm and seed. The exception is geometry-only (`ModelBC7(vision=False)`, no 384→32 projection: 685,834 vs 698,154 parameters), so its random initialization differs.
- **Evaluation (`p9_l3.evaluate9`).** Every quantity comes from the model's own joint (PoE, unique or factorized), in three labelled outputs:
  - **root prior:** repair, scene and omission marginals, calibration, funnel, κ;
  - **per-candidate:** the P8 convention;
  - **offline oracle-revealed conditionals** of the own root model, plus the **legacy per-candidate conditionals** reported separately.

## 2. Own exact root likelihood (mean ± sd over 3 seeds; lower is better)

| arm | validation root NLL | per observed query | disclosed-test root NLL | test: catalogue roots | test: single-bit roots |
|---|---|---|---|---|---|
| PoE-B-full | 0.243 ± 0.09 | 0.061 | 1.218 ± 0.26 | 2.422 | 0.013 |
| **U-B-full** | 0.289 ± 0.14 | 0.072 | 1.129 ± 0.07 | 2.251 | 0.006 |
| PoE-B-structured | 0.615 ± 0.04 | 0.154 | 2.024 ± 0.43 | 3.831 | 0.216 |
| **U-B-structured** | 0.618 ± 0.08 | 0.154 | 2.148 ± 0.29 | 4.100 | 0.197 |
| PoE-C-full | 0.286 ± 0.04 | 0.072 | 1.134 ± 0.31 | 2.237 | 0.031 |
| **U-C-full** | **0.223 ± 0.09** | 0.056 | 1.284 ± 0.28 | 2.553 | 0.016 |
| **U-B-full-geo** | 0.666 ± 0.13 | 0.167 | **0.917 ± 0.04** | 1.626 | 0.207 |
| SF | 0.806 ± 0.13 | 0.201 | 1.608 ± 0.31 | 2.789 | 0.427 |
| A | 0.886 ± 0.12 | 0.222 | 2.021 ± 0.19 | 3.539 | 0.502 |
| PoE-B-full, 400 updates | 0.064 ± 0.01 | 0.016 | **0.620 ± 0.10** | 1.234 | 0.005 |
| U-B-full, 400 updates | 0.065 ± 0.01 | 0.016 | 1.481 ± 0.68 | 2.916 | 0.045 |

**Root-cluster contrasts** (seed-averaged per-root difference, bootstrap 95 % CI; negative favours the first):

| contrast | validation (12 roots, predeclared) | disclosed test (24 roots, diagnostic) |
|---|---|---|
| formulation B-full: unique − PoE | +0.046 [−0.050, +0.175] | −0.089 [−0.351, +0.205] |
| formulation B-structured: unique − PoE | +0.003 [−0.102, +0.119] | +0.125 [−0.283, +0.602] |
| formulation C-full: unique − PoE | −0.064 [−0.169, +0.011] | +0.150 [−0.045, +0.380] |
| 400 updates, B-full: unique − PoE | +0.001 [−0.027, +0.025] | **+0.861 [+0.048, +1.957]** |
| generic coupling (unique): full − structured | **−0.328 [−0.663, −0.074]** | **−1.020 [−2.102, −0.251]** |
| joint vs factorized: U-B-full − SF | **−0.516 [−1.118, −0.116]** | **−0.479 [−0.926, −0.076]** |
| U-B-structured − SF | −0.188 [−0.504, +0.069] | +0.540 [−0.252, +1.797] |
| appearance: DINOv2 + geometry − geometry-only | −0.377 [−0.884, +0.048] | +0.212 [−0.206, +0.703] |
| order: C (GRU) − B (prefix) | −0.067 [−0.169, +0.015] | +0.155 [−0.185, +0.554] |

## 3. Neutral metrics (root prior, calibrated on validation; disclosed test; seed mean)

| arm | val repair NLL | test accuracy | test AUROC | test repair NLL | test ECE | test success / abstain / false-empty (of 12) | κ sign acc. −1 / 0 / +1 (n = 2 / 3 / 2) | test κ MAE |
|---|---|---|---|---|---|---|---|---|
| PoE-B-full | 0.006 | 0.846 | 0.946 | 1.115 | 0.144 | 6.0 / 1.7 / 0 | 0.33 / 0.56 / 0.00 | 0.685 |
| U-B-full | 0.046 | 0.864 | 0.951 | **0.759** | 0.123 | 5.7 / 1.0 / 0 | 0.50 / 0.56 / 0.00 | 0.658 |
| PoE-B-structured | 0.034 | **0.890** | 0.944 | 0.752 | 0.110 | **6.7** / 2.0 / 0 | 0.50 / 1.00 / 0.00 | 0.613 |
| U-B-structured | 0.004 | 0.868 | 0.915 | 1.137 | 0.128 | 5.0 / 1.7 / 0 | 0.50 / 1.00 / 0.00 | 0.635 |
| PoE-C-full | 0.032 | 0.868 | **0.959** | 1.026 | 0.132 | 5.7 / 1.0 / 0 | 0.67 / 0.67 / 0.00 | 0.624 |
| U-C-full | 0.004 | 0.851 | 0.936 | 1.316 | 0.145 | 6.0 / 1.3 / 0 | 0.50 / 0.56 / 0.17 | 0.649 |
| U-B-full-geo | 0.239 | 0.868 | 0.940 | **0.368** | **0.099** | 6.0 / **0.3** / 0 | **0.83 / 0.67 / 0.67** | **0.407** |
| SF | 0.148 | 0.811 | 0.925 | 0.473 | 0.129 | 4.3 / 3.7 / 0 | 0.50 / 1.00 / 0.00 | 0.577 |
| A | 0.139 | 0.825 | 0.908 | 0.650 | 0.149 | 6.0 / 4.0 / 0 | 0.50 / 0.78 / 0.00 | 0.701 |
| PoE-B-full, 400 updates | 0.000 | 0.890 | 0.980 | 0.522 | 0.100 | 5.7 / 1.0 / 0 | 0.67 / 0.44 / 0.83 | 0.362 |
| U-B-full, 400 updates | 0.000 | 0.873 | 0.954 | 1.077 | 0.122 | 6.0 / 1.7 / 0 | 0.50 / 0.44 / 0.83 | 0.464 |

- **Selection:** 7 of the 12 obstructed test roots have a VERIFIED catalogue repair.
- **κ provenance:** both +1 test roots depend on an operational place-side label (report 0030), so +1 predictions are policy-relative, not proof-grounded.
- **Other offline endpoints:** order-swap contrasts and omission necessity have no independently decided same-endpoint pairs, and no omission-only labels exist in validation or test: **N/A**.

**Offline oracle-revealed conditionals** (NLL; never a ranking input). "Own root" means computed from the model's own joint; "legacy" means the per-candidate `p8_eval.conditional`.

| arm | zR given all scene bits (own root) | zO given zR (own root) | mean \|P(zR\|zS=1) − P(zR\|zS=0)\| | legacy d / a / b |
|---|---|---|---|---|
| PoE-B-full | 0.228 | 0.642 | 0.101 | 0.213 / 0.825 / 0.972 |
| U-B-full | 0.206 | 0.590 | 0.103 | 0.217 / 0.737 / 0.844 |
| U-B-structured | 0.760 | 0.611 | 0.000 (no scene–repair edges) | 0.900 / 0.538 / 0.647 |
| U-C-full | 0.245 | 0.674 | 0.095 | 0.302 / 0.954 / 1.288 |
| U-B-full-geo | **0.200** | **0.308** | **0.260** | 0.285 / **0.173 / 0.107** |
| SF | 0.464 | 0.443 | 0 (factorized) | — |

## 4. Training health, invariance and confounds

- **Gradients** (mean per-family norm, seed mean, U-B-full): generic pairs 5.8, HO 4.1, `zR–zO` 2.0, sequence 1.8, scene unary 0.75, **`z0–zS` 0.029** (22 exactly-zero updates of 600), F1 0.053, J 0.087.
  - At 400 updates the `z0–zS` pair is exactly zero on 289 / 1,200 (unique) and 312 / 1,200 (PoE) updates. It remains **unidentifiable** (P9-L2 finding: no root has edits and `z0 = 1`).
  - Clip fractions ≈ 0.52–0.58 for both formulations; geometry-only 0.34. No non-finite loss in any run.
- **Trained-model invariance** (max \|change\|, 6 validation roots):

  | case | unique (all arms) | PoE | related candidate (allowed) |
  |---|---|---|---|
  | exact duplicate | **0** | 0.11–0.15 | — |
  | permutation, disconnected, renamed | ≤ 1.4e-14 | ≤ 1.4e-14 | — |
  | related candidate | — | — | 0.13–0.44 |

  Scene prior unchanged in all cases.
- **Confounds.**
  - *Geometry-only* differs in capacity and initialization, so its contrast is not a pure appearance ablation.
  - *Longer training* changes the picture: both formulations reach validation NLL 0.064, but disclosed-test NLL then diverges (unique 2.42 / 1.17 / 0.86 by seed vs PoE 0.74 / 0.62 / 0.50; seed 0 is extreme, but seed 1 is also worse).
  - *Scene prior* has the same structure (P_S) in both formulations; only trained weights differ.
  - *Concentration:* the 3 worst roots carry **95 %** of U-B-full's validation NLL and 59 % of its test NLL. Validation contrasts are therefore dominated by a few roots, and n = 12 cannot establish equivalence.

## 5. Artifacts and accounting

- **Plan and status:** `runs/p9/l3/l3b/{L3B_plan.json, run_status.json}`.
- **Runs:** `runs/p9/l3/l3b/runs/<arm>#s<seed>[#u400].json`: per-update loss and gradient-by-module, plan hash, checkpoint sha256, full evaluation.
- **Comparators and summary:** `baselines.json` (15 P9-L2 checkpoints re-evaluated), `summary.json`.
- **Checkpoints:** `ckpt/` (seed 0 committed, all hashed in `checkpoint_manifest.json`).
- **Figures** (SHA-256 manifests of inputs):
  - `visualizations/p9/P9_L3b_comparison.png`;
  - `visualizations/p9/P9_L3b_health.png`;
  - factor-graph schematic: `P9_L3a_real_root_factor_graph.png`.
- **Incidents.**
  - The first L3b gate run failed its "historic sources unchanged" check because `p9_viz.py` had been *extended*. It is append-only: 232 lines added, 0 removed. The check now requires exact hashes for every other historic source and zero deleted lines in `p9_viz.py`.
  - Figure titles were shortened and re-rendered. Both incidents are charged.
- **Compute:** L3a + L3b total 4,630 CPU-s and ~4,640 s wall, every job in `runs/p9/l3/guards/`.
- **Calls:** 0 new teacher queries, 0 IK or planner calls in learned training or inference, 0 robot episodes. The historical suite's planner fixtures were counted separately (report 0032).
