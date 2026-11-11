# 0097 — P17-B2: prospective B evaluation (no-op, repair, admission, verification-first, coupling attribution)

**Actual result** (p17test, frozen and unsealed; 140 decided originals: 75 feasible, 65 infeasible; 34 UNKNOWN originals excluded from strict metrics)
- **Primary contrast, LB vs ALWAYS_EMPTY:** strict TOP1 0.479 vs 0.536. Discordant roots split 31 : 39, p = 0.40, CI of the difference [−0.17, +0.06]. **Production lean B is not better than doing nothing.**
- **VERIFY_FIRST is best:** strict TOP1 0.850, with 75 / 75 correct no-ops and 44 / 65 verified repairs. It beats LB 56 : 4 (Holm p = 1e-11) and costs about 330 s of virtual CPU per root.
- **Generic coupling did not replicate.** LB+G scores 0.350, against 0.479 for LB (3 : 21, Holm p = 0.0025). The deficit is a **threshold-calibration failure, not a scoring failure** (§3).
- **Every learned arm stays below verify-first.** The best learned arms are LC (0.657) and P13:SF (0.657), and neither beats ALWAYS_EMPTY by a pre-registered margin.

## 1. Per-arm outcomes (`runs/p17/eval/P17_PROSPECTIVE.json` → `b.analysis.per_arm`; figure `visualizations/p17/b/P17_B_test.png`)

| arm | strict TOP1 | correct no-op / 75 | unnecessary relocation | repair verified / 65 | wrong no-op | admission precision | no-op κ |
|---|---|---|---|---|---|---|---|
| **verify_first** | **0.850** | 75 | 0 | 44 | 0 | 0.68 | — |
| LC | 0.657 | 62 | 12 | 30 | 5 | 0.68 | 0.74 |
| P13:SF | 0.657 | 68 | 6 | 24 | 10 | 0.53 | 0.76 |
| LB-F2 | 0.607 | 65 | 9 | 20 | 8 | 0.58 | 0.74 |
| FULLB | 0.593 | 52 | 21 | 31 | 4 | 0.63 | 0.62 |
| LB+G\|nocpl | 0.593 | 55 | 16 | 28 | 4 | 0.64 | 0.66 |
| P13:A | 0.579 | 47 | 25 | 34 | 4 | 0.68 | 0.55 |
| LB#top3 | 0.571 | 36 | 36 | 44 | 0 | 0.93 | 0.46 |
| P13:K-C | 0.564 | 52 | 20 | 27 | 5 | 0.62 | 0.61 |
| empty_always | 0.536 | 75 | 0 | 0 | 65 | — | 0 |
| A (retrained) | 0.514 | 45 | 27 | 27 | 2 | 0.61 | 0.55 |
| **LB** | **0.479** | 36 | 36 | 31 | 2 | 0.69 | 0.43 |
| LB+G@LB | 0.457 | 40 | 33 | 24 | 2 | 0.55 | 0.49 |
| LB-W | 0.400 | 24 | 48 | 32 | 1 | 0.73 | 0.29 |
| SF | 0.371 | 28 | 46 | 24 | 0 | 0.60 | 0.36 |
| **LB+G** | **0.350** | 23 | 50 | 26 | 0 | 0.63 | 0.29 |
| geometry | 0.264 | 7 | 63 | 30 | 0 | 0.58 | 0.09 |
| random | 0.157 | 3 | 72 | 19 | 1 | 0.51 | 0.02 |

Omitted rows: P13:K-B (0.514), P13:B-F2 (0.557) and LB+G#top3 (0.464).

**Strict TOP1** means one of two things:
- a correct no-op, where EMPTY is chosen and the original target is VERIFIED; or
- a strict repair success, where the chosen repair is existentially VERIFIED and its replay is CLEAR.

## 2. Pre-registered secondary contrasts (strict TOP1, exact sign test, Holm over the family)

| contrast | a only : b only | Holm p |
|---|---|---|
| LB vs verify_first | 4 : 56 | 1.4e-11 |
| LB+G vs LB | 3 : 21 | 0.0025 |
| LB+G vs LB+G\|nocpl | 3 : 37 | 2.6e-7 |
| LB+G vs LB+G@LB (same scores, LB thresholds) | 2 : 17 | 0.0058 |
| LB+G vs LB-W (parameter-matched) | 5 : 12 | 0.43 |
| LB vs FULLB | 7 : 23 | 0.026 |
| LB vs LB-F2 (order-invariant) | 13 : 31 | 0.038 |
| LB vs LC | 1 : 26 | 5e-6 |
| LB vs A | 4 : 9 | 0.53 |
| LB vs SF | 19 : 4 | 0.018 |
| LB vs P13:K-B | 11 : 16 | 0.53 |
| LB+G vs ALWAYS_EMPTY | 26 : 52 | 0.026 |
| LB vs geometry | 40 : 10 | 0.0003 |
| LB#top3 vs LB | 13 : 0 | 0.0024 |
| LB#top3 vs verify_first | 6 : 45 | 2.6e-7 |

## 3. Where B loses: the no-op threshold, not the scores

**Offline label-scored metrics** (2,181 decided queries, 1,695 positive; `b.offline`):

| arm | AUROC | ECE | z0 Brier | within-root rank AUC |
|---|---|---|---|---|
| LB | 0.966 | 0.051 | 0.129 | 0.77 |
| LB+G | 0.964 | 0.027 | 0.119 | 0.80 |
| FULLB | 0.964 | 0.023 | 0.084 | 0.81 |
| LC | 0.966 | 0.042 | 0.135 | 0.77 |
| A | 0.971 | 0.049 | 0.104 | 0.79 |

- **Constant-prevalence z0 baseline:** Brier 0.249.
- **Learned scores are informative and roughly calibrated.** Every arm's z0 Brier beats the constant baseline.
- **The deployable no-op policy is the weak link.** The (t0, t) policies were fitted on only 51 decided p17calib roots and transfer poorly. LB chose a repair on 36 / 75 feasible originals; LB+G, with t0 = 0.90, on 50 / 75.

**Coupling attribution.**
- P(z0) is invariant to the coupling. This is tested: `test_coupling_off_is_inference_only_and_keeps_original_marginal`.
- So the no-op gap between LB+G and LB+G\|nocpl (0 : 32) comes **entirely from their different calibrated thresholds** (t0 = 0.90 vs 0.47), not from the coupling.
- Under LB's thresholds, LB+G's own scores reach 0.457 (LB+G@LB).
- With the coupling switched off at inference, the repair marginals degrade: AUROC 0.908, ECE 0.276.
- **Conclusion:** generic coupling improves joint likelihood and offline repair calibration, but **gives no prospective decision benefit**. P16's +16 roots for LB+G is not replicated.

## 4. Repair and admission (decided infeasible originals)

- **Repair success on 65 roots:** verify_first and LB#top3 44, P13:A 34, LB-W 32, LB / FULLB 31, LC 30, LB+G 26.
- **TOP-3 verify-then-next** turns LB's admitted list into verify_first-level repair (44 / 65; LB#top3 vs LB 13 : 0) at about 3 charged verifications. It keeps LB's no-op errors.
- **Equal-coverage admission** (each arm admits its top-scored repair on the top-c fraction of 65 roots; verified / admitted):

| arm | c = 0.3 | c = 0.5 | all |
|---|---|---|---|
| LB | 18 / 20 | 26 / 32 | 40 / 65 |
| LC | 17 / 20 | 26 / 32 | 39 / 65 |
| LB+G | 16 / 20 | 23 / 32 | 35 / 65 |
| A | 17 / 20 | 23 / 32 | 36 / 65 |

  UNKNOWN repairs are not counted as verified.
- **Reversed-order pairs:** all 7 certified reversed-order pairs are ranked correctly by every ordered arm. The order-invariant LB-F2 ranks them at 0.5.

## 5. Strata and cost

- **NATURAL** (75 decided; 55 feasible):

| LB | LB+G | ALWAYS_EMPTY | verify_first |
|---|---|---|---|
| 0.493 | 0.347 | 0.733 | 0.973 |

  LB vs ALWAYS_EMPTY is 8 : 26 (p = 0.003): **worse than doing nothing on natural scenes.**
- **CONSTRUCTED** (65 decided; 45 infeasible):

| LB | LC | ALWAYS_EMPTY | verify_first |
|---|---|---|---|
| 0.462 | 0.600 | 0.308 | 0.708 |

  LB vs ALWAYS_EMPTY is 23 : 13 (p = 0.13).
- **REACH** (14 decided): LB 0.00, verify_first 0.21. These are hard reachability failures that no catalogue repair fixes.
- **Physical calls per root:**
  - verify_first: 107 motion checks, 3.2 goal plans, 2.7 online moves;
  - LB: 8 motion checks (one existential verification of its chosen query).
  - B's advantage is cost, not accuracy.

## 6. Verdict for B (contract §10)

- **Implementation complete:** keyed exact LB, 0–4 ordered actions with multiple destinations, existential labels and execution, converged matched retraining with 3 seeds, and calibrated policies. No-op, repair, admission, calibration and baselines are all reported. No open correctness defect.
- **METHOD_B_2D_COMPLETE.**
- **Scientific result: negative.**
  - Production LB does not beat ALWAYS_EMPTY.
  - It is dominated by VERIFY_FIRST.
  - The P16 coupling gain does not replicate.
- **Declared limitation:** the capped catalogue holds 10–33 % of certified solutions (0094 §1).
