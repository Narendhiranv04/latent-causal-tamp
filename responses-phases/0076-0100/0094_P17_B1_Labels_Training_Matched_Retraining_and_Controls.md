# 0094 — P17-B1: full existential labels, converged matched retraining, controls and calibrated policies

**Actual result**
- **Labels.** 326 development and calibration roots were labelled with the existential protocol (`P17_EXISTENTIAL_V1`). This includes full ordered-repair labels for every P16 train / dev / val / calib root, closing P16's "lattice-only" gap, plus 113 p17train and 61 p17calib roots. Cost: 87.8 CPU-h, mean 969 CPU-s per root.
- **Training.** 8 arms × 3 seeds were trained to convergence with validation early stopping. Every run stopped early (patience 15 evaluations), and its best checkpoint was restored.
- **Policies.** Every learned arm received a no-op-first policy calibrated on p17calib only (51 decided originals).
- **Freeze.** Everything above was frozen in `runs/p17/PREREG.json` (commit `f22a444`) before any p17test label or execution existed.

## 1. Labels (development / calibration evidence only)

**Decided originals:** 101 feasible, 175 infeasible, 50 UNKNOWN (UNKNOWN is never used as 0).

| length | VERIFIED | CERTIFIED (motion-independent) | UNKNOWN |
|---|---|---|---|
| 1 | 731 | 310 | 891 |
| 2 | 1,154 | 291 | 1,163 |
| 3 | 530 | 153 | 621 |
| 4 | 389 | 121 | 468 |

- 3- and 4-move sequences are supervised in both directions: 919 positives and 274 negatives. The data are therefore not dominated by 1–2-move tasks.
- Missingness is substantial at every length (35–48 % UNKNOWN). Those queries are marginalized, never treated as negative.

**Original status by family** (feasible / infeasible / unknown):
- DENSE 21 / 34 / 10
- NAT 78 / 30 / 37
- REACH 2 / 17 / 3
- each P13 grammar family 0 / 11–13 / 0

The natural NAT stream is kept unbalanced.

**Proposal recall** (`runs/p17/shared/PROPOSAL_RECALL_w0.json`): 6 small scenes, the B generator's full domain enumerated (≤ 2 moves, or ≤ 3 with two movers), and every sequence verified.
- The capped catalogue (caps 1 / 6 / 8 / 4 / 3) contains **10–33 %** of certified solutions.
- It contains **a minimal-length certified solution in 6 / 6** scenes.
- The corrected D search found a plan of the exhaustive minimal length in 6 / 6.
- On one 3-move-capable scene the catalogue holds 0 / 5 certified 3-move solutions.

**Limitation (declared):** B sees a stride-sampled fraction of long repairs. No claim of complete 4-move coverage is made.

## 2. Matched retraining

All arms share:
- the same `TRAIN.pt`: 440 P13 train roots (protocol-tagged) + 244 P17-labelled roots; validation 74 P13 + 21 P16-val;
- the optimizer (AdamW 1e-3, batch 12, clip 10);
- the early-stopping rule;
- seeds 0–2;
- the execution verifier.

| arm | params | val root NLL (s0 / s1 / s2) | best update (s0 / s1 / s2) |
|---|---|---|---|
| **LB** (production) | 467,365 | 2.307 / 2.266 / 2.022 | 340 / 540 / 940 |
| **LB+G** (generic coupling) | 516,774 | 1.799 / 1.998 / 1.851 | 620 / 500 / 520 |
| LB-W (parameter-matched, no coupling) | 516,901 | 2.416 / 2.408 / 2.202 | 340 / 540 / 740 |
| FULLB (full keyed B, same data) | 698,154 | 1.474 / 1.676 / 1.764 | 840 / 400 / 420 |
| LB-F2 (order-invariant) | 368,549 | 3.099 / 2.871 / 3.184 | 180 / 800 / 400 |
| LC (GRU order) | 484,133 | 2.094 / 1.996 / 2.415 | 980 / 1,240 / 960 |
| A | 450,596 | 2.438 / 2.018 / 2.331 | 620 / 900 / 740 |
| SF | 351,396 | 2.600 / 3.008 / 2.839 | 1,340 / 280 / 600 |

**Joint-likelihood ordering:** FULLB < LB+G < LC ≈ LB < LB-W < SF < LB-F2.
- The parameter-matched non-coupled LB-W is *worse* than LB.
- Therefore LB+G's lower joint NLL is not explained by parameter count.
- Joint NLL rewards modelling dependencies between queries, so it is not a decision metric. Decision effects are evaluated prospectively in 0097.

**Learning curves:** `visualizations/p17/b/P17_B_learning_curves.png`. Validation NLL is noisy (12-root batches, 95 validation roots), so the restored best checkpoint is used.

## 3. Calibrated deployable policies (`runs/p17/b/POLICIES.json`, p17calib only)

| arm | t0 | t | calibration-split correct |
|---|---|---|---|
| LB | 0.74 | 0.80 | 0.765 |
| LB+G | 0.90 | 0.74 | 0.784 |
| LB+G\|nocpl (inference toggle) | 0.47 | 0.77 | 0.784 |
| LB-W | 0.90 | 0.80 | 0.765 |
| FULLB | 0.81 | 0.86 | 0.765 |
| LB-F2 / LC / A / SF | 0.15 / 0.22 / 0.71 / 0.89 | 0.71 / 0.92 / 0.71 / 0.29 | 0.745 / 0.784 / 0.745 / 0.745 |
| P13 K-B / K-C / A / SF / B-F2 | — | — | 0.725 / 0.784 / 0.765 / 0.765 / 0.725 |

- These are in-sample calibration numbers (51 roots), not evidence.
- Swapped-threshold arms (`LB+G@LB`, `LB@LB+G`) and TOP-3 verify-then-next arms (`LB#top3`, `LB+G#top3`) are frozen as separate conditions.

## 4. B-CORRECT gate (method correctness)

All of the following pass (`tests/test_p17.py` 26 tests + `tests/test_p16.py` 17 tests):
- LB exact factorization (brute force);
- UNKNOWN marginalized;
- keyed identity;
- F2 order sensitivity;
- layout of 4-move / repeat / omission aliasing;
- LB+G has `cpl` but no F3 / F4 / higher-order terms;
- LB-W parameter-matched (Δ = 127 parameters);
- inference-only coupling toggle keeps the weights and **P(z0)** exactly invariant while repair marginals change;
- finite gradients under early stopping;
- the fast scorer equals `p9_l3.root_eval9` marginals to < 1e-12;
- existential labels (0091);
- empty-sequence certificate scope.

**Correction made before the freeze:** for the empty sequence, a q-dependent certificate at q0 refutes the only realization and is now CERTIFIED. No label changes, because originals are labelled through the goal check.
