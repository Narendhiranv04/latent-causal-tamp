# 0030 — P9-L2: matched saved-data comparison of the exact joint objective against the P8 multi-loss

**Actual result.** Training ran under one frozen plan (`runs/p9/L2_plan.json`, `sha256:65a5f238…`), entirely on saved data:
- **Runs:** 27 guarded runs = 18 mandatory (B-full, B-structured, B-quadratic, C-full, A, SF × seeds 0–2), plus B-none × 3 and certified-only label sensitivity (B-full, SF × 3).
- **Comparator:** the 21 unchanged P8c multi-loss checkpoints, evaluated by the same code; they reproduce their published metrics exactly.
- **Compute:** **4,000.9 / 8,000 CPU-s** aggregate, failed attempts included. 0 teacher calls, 0 new roots, 0 episodes.

**Engineering gate:** `runs/p9/P9_L2_GATE.json` → **PASS** (12/12). This is *not* a claim of scientific superiority.

**Scientific summary.** Everything below is on 12 P8c validation roots and the 24 disclosed P8c test roots (12 obstructed, 12 single-bit originally-feasible). It is **not** a fresh holdout.
- **Objective.**
  - The exact joint objective lowers disclosed-test **exact root NLL** for every arm (e.g., B-full 3.19 → 1.22, B-structured 3.85 → 2.02, SF 2.33 → 1.61). That is the quantity it optimizes.
  - **Validation** root NLL is unchanged or slightly worse (B-full +0.055 [+0.006, +0.112]).
  - **Neutral calibrated repair metrics are mixed:** B-structured, A and SF improve; B-full, B-quadratic and C-full lose 1–4 accuracy points.
  - It removes every false-feasible empty repair (P8 B-structured: 3.0 per seed).
- **Coupling.**
  - Generic coupling lowers root NLL against structured factors on both splits (validation −0.37 [−0.74, −0.09], test −0.81 [−1.58, −0.29]) and makes scene → repair conditionals informative (task d 0.83 → 0.21).
  - But **no arm predicts the (operational) κ = +1 roots once the explicit P8 effect loss is gone**.
  - The factorized SF control has the **best** scene-bit and hidden-scene-completion NLL on the disclosed test.
- **Structured `z0–zS` pair: unidentifiable from the saved data.** No saved root has both scene edits and a feasible original task.

Previous turn sync: `f9a6de0695d83699a2115d4898e5c78063852073`. L0 and L1 gates PASS (reports 0028, 0029).

## 1. Protocol (frozen in `L2_plan.json` before any training)

- **Data:** `runs/p8/c_training/dataset.pt`.
  - Train: 178 roots (P8c train + all P4–P7 history).
  - Validation: 12 P8c roots, used for every choice.
  - Disclosed P8c test (`dataset_sealed.pt`, 24 roots): a legacy diagnostic, never used for any choice.
- **Matching.** `torch.manual_seed(seed)` precedes `abc8.build(arm)`, and the κ-balanced `RootSampler(train, 12, seed)` is used. Each ABC9 run therefore has **the same initialization and the same 200 minibatches of 12 roots** as the P8c run of that arm and seed. AdamW, lr 1e-3, wd 1e-4.
- **Objective (B/C):** `mean_roots(−log P(D_c))` (exact, equality-aware; report 0029) + 1.0 · static BCE + 1.0 · log-Huber witnessed J.
  - **A / SF:** the factorized root likelihood over the same distinct observed queries + the same two auxiliaries.
  - **Not used:** no task, scene, omission, effect or κ BCE / MSE, and no pool term.
- **Selection:** best validation root NLL, checked every 20 updates. Temperature and threshold come from validation only (P8 rules).
- **Clip, one value for all arms.** The predeclared rule `max(5, ceil(median unclipped norm))` was applied to the single sanity trial (B-full seed 0, 60 unclipped updates, 46.2 CPU-s, train + validation only). The median was 9.2, giving **clip = 10**. P8 used per-arm clip 1 or 5 and pool weights 0.25 or 0.5.
- **Two prediction modes** for every model, new and legacy:
  - **per-candidate:** the ABC7 single-repair marginal (the P8 convention);
  - **root model:** the equality-aware marginal over the frozen catalogue (identical for A / SF).
  - Tables below use the root model unless marked.

**Execution incidents (all charged; nothing hidden).**
1. **Missing directory.** The first launch trained and checkpointed five seed-0 runs but could not write their result JSON (`runs/p9/l2/runs/` did not exist). 668.6 CPU-s were charged, plus a 70 CPU-s upper bound for a sixth job stopped without a guard record. The deterministic runs were repeated after the fix.
2. **Legacy evaluation key error.** The legacy evaluation first failed on a results key (P8c stores configurations under `configs`); ten fast failed attempts (31.8 CPU-s) are charged.
3. **Gate criterion corrected.** My first gate criterion ("every B/C factor gets a nonzero gradient on *every* update") failed only for the `z0–zS` pair (§4). It was replaced by "in the graph every update and nonzero on ≥ 90 % of updates". The strict result (`False`) and per-factor zero-update counts stay in the gate file.
4. **`p9_run.py` source hash.** Aggregation and gate functions were added to `p9_run.py` while training ran. Each job imports the file fresh, but the training code path was unchanged, so the per-run source hash of `p9_run.py` varies across runs.

## 2. Exact root likelihood (mean ± sd over 3 seeds; lower is better)

| arm | validation P8 | validation ABC9 | disclosed test P8 | disclosed test ABC9 |
|---|---|---|---|---|
| B-full | **0.188 ± 0.05** | 0.243 ± 0.09 | 3.185 ± 0.23 | 1.218 ± 0.26 |
| B-quadratic | 0.233 ± 0.10 | 0.246 ± 0.09 | 3.780 ± 0.20 | 1.545 ± 0.12 |
| B-structured | 0.847 ± 0.09 | 0.615 ± 0.04 | 3.849 ± 0.25 | 2.024 ± 0.43 |
| B-none | 0.614 ± 0.18 | 0.796 ± 0.05 | 2.924 ± 0.41 | 2.444 ± 0.57 |
| C-full | 0.317 ± 0.29 | 0.286 ± 0.04 | 3.045 ± 0.99 | **1.134 ± 0.31** |
| A | 0.829 ± 0.05 | 0.886 ± 0.12 | 2.360 ± 0.34 | 2.021 ± 0.19 |
| SF | 0.793 ± 0.25 | 0.806 ± 0.13 | 2.327 ± 0.47 | 1.608 ± 0.31 |

**Objective contrasts** (ABC9 − P8, same arm; seed-averaged per root; root-cluster bootstrap 95 % CI):

| arm | validation | test |
|---|---|---|
| B-full | +0.055 [+0.006, +0.112] | −1.97 [−4.36, +0.03] |
| B-quadratic | +0.013 | **−2.23 [−5.08, −0.12]** |
| B-structured | −0.233 | **−1.83 [−3.69, −0.30]** |
| C-full | −0.031 | **−1.91 [−4.16, −0.09]** |
| B-none | **+0.182 [+0.057, +0.316]** | −0.48 |
| A | +0.057 | −0.34 |
| SF | +0.013 | −0.72 |

Intervals not shown include 0. The disclosed-test gain is concentrated in over-confident P8 errors on reused queries and on combined outcomes. P8 was not trained on this quantity.

## 3. Neutral metrics (disclosed test, calibrated, root model; P8 → ABC9; seed mean)

| arm | accuracy | AUROC | repair NLL | ECE | scene-bit NLL | κ macro MAE | conditional d (scene → zR) |
|---|---|---|---|---|---|---|---|
| B-full | 0.890 → 0.846 | 0.951 → 0.946 | 0.97 → 1.12 | 0.115 → 0.144 | 0.495 → 0.528 | 0.466 → 0.685 | 0.83 → **0.21** |
| B-quadratic | 0.886 → 0.860 | 0.945 → 0.942 | 0.86 → 1.31 | 0.105 → 0.146 | 0.568 → 0.511 | 0.521 → 0.659 | 0.95 → 0.31 |
| B-structured | 0.789 → **0.890** | 0.875 → 0.944 | 1.14 → 0.75 | 0.171 → 0.110 | 0.576 → 0.466 | 0.619 → 0.613 | 0.99 → 0.60 |
| B-none | 0.851 → 0.842 | 0.920 → 0.927 | 1.25 → 0.85 | 0.148 → 0.148 | 0.552 → 0.623 | 0.635 → 0.657 | 0.84 → 0.62 |
| C-full | 0.882 → 0.868 | 0.943 → **0.959** | 0.97 → 1.03 | 0.112 → 0.132 | 0.491 → 0.469 | 0.522 → 0.624 | 0.83 → 0.24 |
| A | 0.825 → 0.825 | 0.891 → 0.908 | 0.91 → 0.65 | 0.159 → 0.149 | 0.590 → 0.477 | 0.539 → 0.701 | 0.90 → 0.65 |
| SF | 0.838 → 0.811 | 0.898 → 0.925 | 0.89 → **0.47** | 0.147 → 0.129 | 0.565 → **0.364** | 0.479 → 0.577 | 0.81 → 0.44 |

**Reading the table.**
- **Per-candidate (P8-convention) metrics for comparison:** ABC9 B-full 0.860 / 0.938 / 0.79; P8 B-full (published) 0.882 / 0.953 / 0.87.
- **Calibration is weakly determined.** Temperatures reach the grid edge 0.25 for most B/C models (12 validation roots), as in P8.
- **Hidden-scene completion (tasks a / b, offline oracle-revealed):**

  | arm | P8 | ABC9 |
  |---|---|---|
  | SF | 0.62 / 0.95 | **0.39 / 0.30** (marginals) |
  | B-structured | 0.56 / 0.67 | 0.58 / 0.72 |
  | B-full | 0.95 / 1.03 | 0.83 / 0.97 |

  Coupled scene blocks are near-perfect on validation (B-full 0.12 / 0.03) but over-confident on the disclosed test.

**κ by observed sign** (sign accuracy, seed mean). The test roots split 2 / 3 / 2 for −1 / 0 / +1. Both **+1 roots rely on a BUDGET_INFEASIBLE `zS[A]` label (operational, OPNEG-v1)**; the −1 and 0 roots are certified or witnessed throughout.

| arm | −1 | 0 | +1 |
|---|---|---|---|
| P8 B-full | 0.50 | 0.44 | **0.67** |
| P8 C-full | 0.50 | 0.78 | **0.67** |
| P8 B-quadratic | 0.50 | 0.67 | 0.50 |
| every ABC9 arm | 0.33–0.67 | 0.56–1.00 | **0.00** |

**Restricted-catalogue selection** (disclosed test, 12 obstructed roots, 7 with a VERIFIED candidate; saved records; per seed: success / abstain / false-feasible empty):

| arm | P8 | ABC9 |
|---|---|---|
| B-full | 5.0 / 2.7 / 0 | 6.0 / 1.7 / 0 |
| B-quadratic | 6.0 / 3.0 / 0 | 6.0 / 1.7 / 0 |
| B-structured | 5.0 / 1.3 / **3.0** | **6.7** / 2.0 / 0 |
| B-none | 5.3 / 4.3 / 0 | 4.7 / 4.0 / 0 |
| C-full | 6.7 / 1.7 / 0 | 5.7 / 1.0 / 0 |
| A | 4.0 / 4.0 / 0.7 | 6.0 / 4.0 / 0 |
| SF | 2.7 / 6.3 / 0 | 4.3 / 3.7 / 0 |

## 4. Factor contrasts under the new objective (exact root NLL, ABC9 only; negative favours the first)

| contrast | validation (12 roots) | disclosed test (24 roots) |
|---|---|---|
| generic coupling: B-full − B-structured | **−0.37 [−0.74, −0.09]** | **−0.81 [−1.58, −0.29]** |
| higher-order: B-full − B-quadratic | −0.003 [−0.06, +0.05] | −0.33 [−0.91, −0.01] |
| structured pairs: B-structured − B-none | **−0.18 [−0.32, −0.06]** | −0.42 [−1.15, +0.07] |
| joint vs factorized: B-full − SF | **−0.56 [−1.16, −0.19]** | −0.39 [−1.04, +0.21] |
| B-structured − SF | −0.19 [−0.47, +0.06] | +0.42 [−0.33, +1.56] |
| order representation: C-full − B-full | +0.04 [−0.00, +0.10] | −0.08 [−0.28, +0.07] |
| A − SF | +0.08 | +0.41 |

**Gradient health** (per-factor-family norms over 200 updates; seed mean):
- **B-full:** generic pairs 6.1, higher-order 3.5, sequence 2.8, zR–zO pair 2.0, scene unary 0.83, **z0–zS pair 0.029**, static 0.056, travel 0.089.
- **B-structured:** sequence 3.6, zR–zO pair 3.3, scene unary 0.53, **z0–zS pair 0.034**.
- **The z0–zS pair is the only factor with exact-zero updates** (1–16 of 200, in the full / quadratic / C arms). The mechanism:
  - its energy `W·z0·zS[I]` acts only when `z0 = 1`;
  - **all 93 decided roots with scene edits have `z0 = 0`, and all 86 feasible originals have no edits**;
  - so the factor is **not identifiable from the saved evidence**.
- **Clipping (not comparable across objectives):** clipped fraction 0.53 (B-full / C-full) to 0.68 (B-none) at clip 10. P8 clipped 0.53–0.95 at clip 1 / 5. Median pre-clip norms are 10.6–16.0 (ABC9) vs 3.9–7.5 (P8), because a root NLL is a sum over a root's observed bits.
- **Training length:** the best validation update was 200 in 12 of 21 primary runs. Matched 200-update training is likely under-converged for both objectives.

**Proof-only label sensitivity** (BUDGET_INFEASIBLE labels dropped in training; evaluated on all decided labels):
- **B-full:** validation root NLL 0.243 → 0.301; test 1.22 → 1.51; test accuracy 0.846 → 0.860; abstentions 1.7 → 0. Selection success 6.0 → 5.3.
- **SF:** worse throughout (validation root NLL 0.81 → 1.46; test 1.61 → 2.27).
- **Conclusion:** operational negatives help the likelihood fit on this distribution. This is not evidence that they are proofs.

## 5. Figures (`visualizations/p9/`, SHA-256 in `index.json`)

- `P9_L2_nll_vs_legacy.png`: exact root NLL and calibrated NLLs per arm and seed.
- `P9_L2_gradient_health.png`: per-factor gradient trajectories; median pre-clip norms.
- `P9_L2_predictions_selection.png`:
  - (a) reliability, seed 0;
  - (b) selection funnel;
  - (c) root-cluster contrasts.

## 6. Artifacts and accounting

- **Plan and status:** `runs/p9/l2/{L2_plan.json, sanity.json, run_status.json}`.
- **Runs:** `runs/p9/l2/runs/<arm>#s<seed>[#certified_only].json`, containing:
  - the per-update history (losses, gradient norms by module, clipping);
  - the source hashes, dataset hash and plan hash;
  - the full evaluation (both modes, funnel rows, per-root NLL).
- **Comparator and summary:** `runs/p9/l2/legacy_eval.json` (the P8 comparator), `runs/p9/l2/summary.json`.
- **Ledger:** `runs/p9/l2/guards/` (every attempt, including failures).
- **Checkpoints:** `runs/p9/l2/ckpt/` (27; seed 0 committed, all hashed in `checkpoint_manifest.json`).
- **Compute:** 4,000.9 CPU-s aggregate (≤ 8,000), 4,008.7 s wall (≤ 18,000). Largest job 167.9 CPU-s (≤ 1,800). One trainer process at a time.
