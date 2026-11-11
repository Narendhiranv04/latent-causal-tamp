# 0058 — P12-7: independent 2D generalization and the scientific verdict

**Bottom line.**
- **Repair selection:** on genuinely new, independently constructed and prediction-locked 2D scene families, keyed B's advantage **does not generalize**. In executed strict TOP1, B ≈ A ≈ C ≈ SF, and a simple analytic geometry proposer beats all of them.
- **Joint factors:** the prospective test does not support them. F3 is **significantly reversed** (removing it improves κ accuracy) and F5 is null.
- **What still holds:** the order factor remains necessary for order discrimination, and DINOv2 input helps fit. Realistic appearance changes are tolerated when masks are fixed.
- **D:** feasibility is near-perfect on P10b. On the new families it is beaten by the geometry heuristic for blocker identity, although its pair term helps there.

## 1. Evidence-to-claim matrix (new holdout = 80 roots, locked at `caa49df` before labels)

| claim | P10 / P11 (disclosed benchmark) | P12 (novel, prospective) | status |
|---|---|---|---|
| B > SF executed TOP1 | 0.718 vs 0.385 (Holm 7.8e-6) | 0.633 vs 0.565, +0.068 [−0.007, 0.143], n.s. (49 roots) | **does not generalize** |
| B > A executed TOP1 | +0.133 | +0.007 [−0.068, 0.082] | **does not generalize** |
| B > geometry-only | +0.272 | **−0.163** [−0.265, −0.054], p 0.0015 | **reversed** |
| B vs planner-assisted G+M | G+M 0.831 > B | G+M 0.571 (X family 0.20) vs B 0.633, n.s. | inconclusive (protocols differ) |
| F3 improves κ accuracy (preregistered all-κ proof-grounded cohort) | 9 / 9 roots, family-Holm 0.117 | Δ −0.0735 [−0.112, −0.032], Holm p 0.0118 (65 roots) | **refuted on these families** |
| F3 on H1-like complementary (κ = +1) four-tuples | 9 / 9 roots | 4 roots only (target ≥ 12): B 0.81 vs B-F3 0.94 | **UNDERPOWERED** (descriptive favours B) |
| F5 (generic + HO) improves κ accuracy | 9 / 9, underpowered | Δ −0.027 [−0.109, 0.058], Holm 0.62 | **not confirmed** |
| HO residual improves κ accuracy | exploratory | B-F5q better: −0.132 [−0.184, −0.078] | **reversed** |
| order factor (F2) needed | order −0.72 | B − F2 +0.458 (18 / 0 roots) | **supported** |
| C better than B on order | no | accuracy n.s.; margin +0.075 (p 0.03) | weak / exploratory |
| B best order chooser | ceiling | A 0.983 > B 0.916 (p 0.003) | **not supported** |
| omission necessity | B ≈ SF | all arms 0.56–0.69 | weak for every arm |
| DINOv2 helps | NLL +0.089 without | κ error +0.269 without | **supported** |
| appearance robustness (masks fixed) | severe remap: TOP1 changes 77 % | realistic: TOP1 changes 4–11 % | supported for mild changes only |
| D feasibility | 64 / 64 (4 feasible) | 0 feasible roots, so not evaluable; D false-feasible 3 / 80 | supported on P10b only |
| D blocker identity | infeasible-only F1 0.863 | 0.752 < geometry 0.850 | heuristic better |
| D pair term | not beneficial | +0.154 [0.103, 0.209] vs pairless | **positive on new families (exploratory)** |
| physical length extrapolation | fails (0048) | new families are mostly 1-move repairs (64 / 80) | not testable here |

## 2. Why the joint factors do not pay off on novel scenes

- **The novel cohort is dominated by κ = 0** (59 / 65): exactly one edit suffices.
- **Spurious interaction:** B's joint coupling produces κ̂ ≠ 0 on these roots (B mean |κ̂ − κ| 0.377 on κ = 0, against SF 0.179).
- **Where full B does best:** on the four genuinely complementary roots, full B has the lowest error (0.81, against B-F3 0.94 and B-F5s 1.47). This matches the P10 direction, but it is n = 4 and B's absolute error stays large.
- **Interpretation:** the factors encode a prior toward interaction learned from the P10b H1 / H10 families, and that prior does not transfer.

## 3. Engineering and integrity

- **Preregistration:** `PREREG.json` was frozen before labels. Predictions were frozen with 0 physical calls and pushed (`caa49df`). Labels were hash-committed (`a2d7833`) before unsealing.
- **Stopping and model use:** no outcome-based stopping or selection, and no retraining or recalibration.
- **Tests:** full regression 407 / 407 passed, 6 / 6 replays exit 0 (627.7 / 2,000 CPU-s; 681 fixture planner calls counted separately in `runs/p12/regression/calls.json`). The 6 new P12 tests (`tests/test_p12.py`) pass separately; that file was added after the regression collection began.
- **Budgets:**

  | category | used / cap (CPU-s) |
  |---|---|
  | audit | 1,582 / 4,000 |
  | dev | 4,985 / 5,000 |
  | teacher | 26,025 / 40,000 |
  | execution | 11,902 / 12,000 |
  | secondary | 562 / 5,000 |
  | regression | 628 / 2,000 |

  Execution is **PARTIAL**: 49 / 80 roots, with coverage fixed by the frozen order.
- **Disclosed issues:**
  - per-batch execution caps were set too low, then an ordered continuation was run;
  - one CPU-censored job build;
  - one killed launch lasting under a minute;
  - 0055 first wrongly called the order / omission endpoints not evaluable; this was corrected before commit.

## 4. Claims approved for a talk or paper

**Approved:**
- On the P10b constructor families, keyed B outperforms A, SF and a geometry rule in strict one-shot execution.
- On two independently constructed, prediction-locked 2D families, this advantage disappears, and on the preregistered all-κ cohort (91 % κ = 0) the joint scene-pair factor F3 *reduces* interaction-prediction accuracy. The complementary-only question stays open (4 roots).
- The order factor is necessary for order discrimination.
- DINOv2 helps fit, and predictions are stable to mild photometric change when masks are fixed.

**Not approved:**
- generalization of B's superiority;
- necessity of F3 / F5;
- C over B;
- length generalization;
- D blocker superiority over a geometric heuristic;
- any 3D or hardware claim.
