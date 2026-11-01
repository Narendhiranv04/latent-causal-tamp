# 0128 — BXY-P21: retraining the existing Approach B models with the K3/K4 development data (exploratory)

Date: 2026-11-01. Gate: BXY-P21, run as the contract's **bounded exploratory analysis** because P20 returned K3 at LIMITED level and K4
below threshold (0127 §6, recorded before any P21 step).
- Design `85fc31d2…`, committed `dd3fdb46` before any optimizer step.
- Authorization `9cfee5be`.
- 90 / 90 runs done, every one on its first attempt.
- **49,411 / 65,000 CPU-s, 12,799 / 30,000 s wall**; max run 736 CPU-s against the 2,000 cap.

## Result

1. **The model family is unchanged.**
   - The same six P17 arms (`bxy_p17.Model`, losses, GEO2, SYM, rule grid), trained on 398 development roots: P-min 197, P15 28, V2.1 87,
     K34 86.
   - 5 family-grouped folds × 3 seeds, out-of-fold, with fold-specific inner rules.
2. **The X/Y model still clearly beats the unchanged baseline:**
   - P1 D vs B (outcome-blind, OB) **+0.233 [+0.171, +0.298]**, with unnecessary repairs −0.073 → IMPROVES_WITHIN_GUARDRAIL;
   - on K34 alone, +0.284 [+0.194, +0.378].
3. **P17's "superior to DIRECT" does not replicate with the K3/K4 data:**
   - P2 D vs DIRECT-GEO (OB) is +0.031 [−0.002, +0.064], unnecessary −0.053 [−0.133, +0.027];
   - on K34 alone, −0.005 [−0.041, +0.032];
   - DIRECT-GEO improved from 0.149 (P17) to 0.258 with the new data.
   - **The whole-system advantage over a geometry-informed direct predictor is therefore not established.**
4. **The quadratic coupling still adds nothing:** P3 D vs E +0.002 [−0.027, +0.031]; joint NLL +0.03 [−0.23, +0.29].
5. **Order-aware F2 matters, now on hard scenes:**
   - P5 D vs the capacity-matched order-invariant G: order concordance **+0.32 [+0.23, +0.39]** (OB) and **+0.39 [+0.31, +0.46]** (K34);
   - corrective success +0.053 [+0.016, +0.096] (OB);
   - pre-registered **H4 (D vs G on repairable K3/K4 roots): +0.222 [+0.048, +0.413], n = 21, unnecessary +0.02 → criterion met
     (exploratory).**
6. **K3/K4 hypotheses H1–H3 are not met:** D vs DIRECT 0.000 [−0.127, +0.111]; E vs DIRECT −0.032; D vs E +0.032 (n = 21 repairable
   K3/K4 roots).

| Arm (OB = P15 + V21 + K34: 150 infeasible, 63 with a verified repair) | success (infeasible) | success (verified repair available) | unnecessary (feasible) | harmful unnecessary | Y0 AUROC | edit sign 1→0 | order (P17 metric) |
|---|---|---|---|---|---|---|---|
| A DIRECT-GEO | 0.258 | 0.614 | 0.193 | 0.027 | 0.942 | — | — |
| B XYQ-BASE | 0.056 | 0.132 | 0.213 | 0.107 | 0.885 | 0.26 | 0.74 |
| C XYQ-GEO-CON | 0.273 | 0.651 | 0.193 | 0.020 | 0.947 | 0.90 | 0.87 |
| **D XYQ-GEO-SYM** | **0.289** | **0.688** | 0.140 | 0.007 | 0.949 | 0.94 | 0.83 |
| E XY-UNC-SA-GEO-SYM | 0.287 | 0.683 | 0.160 | 0.007 | 0.952 | 0.96 | 0.81 |
| G XYQ-GEO-SYM-ORDINV | 0.236 | 0.561 | 0.120 | 0.013 | 0.953 | 0.94 | 0.52 |

References on the same roots:

| Reference | Success (infeasible) | Unnecessary repairs |
|---|---|---|
| analytic access | 0.207 | 0.000 |
| shortest | 0.080 | 0.98 |
| no-op | 0 | 0 |
| verify-first ceiling | 0.420 | — |

**P18 pooled rule on the same OOF scores (read-only diagnostic, not an ensemble estimate):**

| Arm | Success / unnecessary |
|---|---|
| D | 0.296 / 0.153 |
| E | 0.291 / 0.207 |
| A | 0.262 / 0.207 |

## K-stratified held-out selection (K34 roots, OOF seed means)

| Verified K (independent roots) | A DIRECT-GEO | B | C | **D** | E | G (order-invariant) |
|---|---|---|---|---|---|---|
| K1 (6) | 0.67 | 0.11 | 0.50 | 0.61 | 0.61 | 0.67 |
| K2 (5) | 0.60 | 0.20 | 0.67 | 0.60 | 0.60 | 0.40 |
| **K3 (14), exploratory** | 0.79 | 0.07 | 0.74 | 0.74 | 0.71 | 0.60 |
| **K4 (7), descriptive only** | 0.86 | 0.00 | 0.86 | **0.95** | 0.90 | 0.57 |

- **These strata are conditioned on availability.** Every verified-K root has a verified repair in its catalogue: the curriculum
  subset, not the generator distribution. The unconditional rates are in the table above.
- **Interpretation:**
  - On held-out K3/K4 scenes, every GEO2 model usually selects a physically verified multi-move repair, with the correct order and
    destinations.
  - The order-invariant control fails much more often on K4 (0.57 vs 0.95). That is the expected signature of order-sensitive physical
    execution.
  - **With n = 7 K4 roots this is a description, not a "learned K4" claim** (figure 05: D's and DIRECT's choices on four held-out K4
    roots vs the verified, certified-necessary repair).

## Strict permutation order (K34 roots; same action multiset, same endpoint, both F1-admissible, X discordant)

| Arm | all (309 pair × seeds, 33 roots) | certified failing order (93) |
|---|---|---|
| D | 0.93 | 1.00 |
| C | 0.92 | 1.00 |
| E | 0.92 | 1.00 |
| B | 0.77 | 0.78 |
| G | 0.50 (ties by construction) | 0.50 |

## What the evidence supports

- **Supported (development):**
  - learning from X/Y labels with GEO2 + SYM vastly outperforms the unchanged X/Y model;
  - order-aware F2 is needed for order-sensitive multi-move repairs;
  - models select verified K3 repairs on held-out roots at about 0.7–0.8 when one exists.
- **Not supported:**
  - superiority of the X/Y factorization over a geometry-informed DIRECT predictor (P17's gate does not replicate);
  - any benefit of the quadratic coupling.
- **Not testable here:** K4 learning (n = 7).

## Figures ([visualizations/approach_b/bxy_p21_v1/](../visualizations/approach_b/bxy_p21_v1/))

| Figure | Content |
|---|---|
| 01 | success (unconditional ○ / availability-conditioned △) vs unnecessary repairs, with references, for OB / K34 / P-min |
| 02_success_by_K | K1–K4 strata with n (K3 exploratory, K4 descriptive) |
| 03_k34_hypotheses | H1–H4 paired CIs |
| 04_strict_order_K34 | strict order concordance |
| 05_k4_heldout_gallery | held-out K4 roots: D vs DIRECT choices and the verified repair with replayed witnesses |
| 02_paired_contrasts, 03_representation, 04_calibration, 06_decision_categories, 08_travel_matched | P17-style panels on the P21 runs |

## Files

- **Code:**
  - [bxy_p21_k34.py](../bxy_p21_k34.py) — design, reusing the P17 arms;
  - [bxy_p21_run.py](../bxy_p21_run.py) — a copy of the P17 runner;
  - [bxy_p21_eval.py](../bxy_p21_eval.py);
  - [bxy_p21_viz.py](../bxy_p21_viz.py).
- **Artifacts:**
  - [EVALUATION_P21.json](../runs/approach_b/bxy_p21_v1/EVALUATION_P21.json);
  - per-run RESULT / predictions / history files with hashes; checkpoints are git-ignored, and P22 makes a second copy;
  - INPUTS_K34.pt (sha `54ce801d…`).
- **Regression:** see the next section.

## Regression

Recorded in `runs/approach_b/bxy_p21_v1/regression/`:
- full suite: **716 passed, 1 skipped**;
- six archived replays: exit 0;
- hash guard: clean.

STOP (gate P21).
