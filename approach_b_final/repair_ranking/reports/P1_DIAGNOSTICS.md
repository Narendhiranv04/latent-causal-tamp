# P1: diagnosis of the frozen X/Y scorer (no new queries)

**Inputs:**
- **Scorer:** frozen arm D seed 0 (`scorer_s0.pt`), read out through `rr.readout`: b, a, w, pY, pX1, pX0, marginal pX, p11.
- **VAL labels:** exact-contract teacher caches (k3abl, k3val, mcts, fds); 5,408 decided-or-partial K ≤ 2 legal sequences on 751 roots.
- **TRAIN labels:** the original finalized snapshot labels (in-sample).

**Metrics:** within-root ranking is computed per root and then averaged over roots, with 95 % family-cluster bootstrap intervals (4,000 resamples). Z is the logical conjunction: 1 iff X = Y = 1 verified, 0 if either is soundly 0.

**Status:** this is development evidence on exposed VAL. The scorer's checkpoint was early-stopped on VAL NLL.

**Selection bias:** the labelled candidates are those that earlier methods chose to verify, not random draws. Tail candidates entered the caches mostly as EXACT_FULL or search picks, so they are already high-scoring. Cross-tier comparisons are therefore diagnostic, not causal. P3 adds score-independent random sets to address this.

## 1. Calibration (`P1_CALIBRATION.json`, `figures/p1_calibration_ranking.png`)

| VAL K1/K2 (exact contract) | n | AUROC | slope | FP rate at p ≥ 0.9 |
|---|---|---|---|---|
| pY vs Y (unique endpoints) | 3,312 | 0.854 | 0.73 | 6.5 % |
| marginal pX vs X | 4,008 | 0.757 | 0.52 | 7.5 % |
| **pX1 vs X given Y = 1** | 2,522 | **0.714** | **0.41** | 8.3 % |
| pX0 vs X given Y = 0 | 540 | 0.833 | 0.74 | 2.0 % |
| **p11 vs Z** | 3,240 | **0.798** | 0.68 | **14.0 %** |
| p11 vs Z on TRAIN (in-sample) | 8,685 | 0.941 | 1.10 | 3.6 % |

- **Large generalization gap.** On its TRAIN labels the scorer is well calibrated, with slope 1.10. On VAL it is over-confident, with slope 0.68 and 14 % false positives at p11 ≥ 0.9.
- **Over-confidence rises with destination rank.** The calibration intercept is −0.33 for ranks 1–4, −0.86 for ranks 7–12 and −1.30 for ranks above 12. At p11 ≥ 0.9, the false-positive rate is 11.8 % (ranks 1–4) against 17.9 % (above 12).
- **High-confidence errors split between both factors.** Of the 397 decided failures with p11 ≥ 0.8, 206 failed Y and 156 failed X with Y = 1; the median predicted pY and pX1 for these were 0.95 and 0.98.

## 2. Ranking within a root (`P1_RANKING.json`)

These are the 165 K1/K2 VAL roots that have both a verified success and a verified failure among their labelled candidates.

| Score used to rank | Concordance [95 % CI] | Known-candidate top-1 |
|---|---|---|
| **frozen p11** | **0.718 [0.669, 0.762]** | 0.733 |
| pY only | 0.706 [0.656, 0.752] | 0.733 |
| **pX1 only** | **0.451 [0.403, 0.499]** | 0.406 |
| cVAE prior only (mean log prior) | 0.513 [0.474, 0.556] | 0.570 |
| random | 0.480 | 0.649 |

Top-1 is the share of these roots where the top-scored labelled candidate is a verified success.

- **Almost all of the scorer's within-root ranking comes from the endpoint head, pY.** The conditional execution head pX1 ranks verified successes *below* failures within a root (CI below 0.5), even though it is globally informative (AUROC 0.71).
- **The prior alone carries no within-root ranking signal.**
- **By pair kind:**
  - Disjoint object sets: 0.74.
  - Omission or addition: 0.84.
  - **Same objects, different destinations: 0.48** (66 roots, 751 pairs). The scorer cannot tell good from bad destinations for a fixed object set, which is exactly the decision expanded destination search depends on.
  - Same set, other order: only 2 decided pairs, too few to evaluate.
- **By rank tier** (`figures/p1_tier_pair_concordance.png`):
  - When the success uses ranks 1–4 and the failure uses ranks 7–12 / 5–6 / beyond 12, concordance is 0.18 / 0.13 / 0.28. When the tiers are reversed, it is 0.96–0.98.
  - The scorer systematically scores sets with off-top-4 destinations above top-4 sets, whatever the outcome.
  - That is consistent with the EXACT_FULL losses (all off-top-4), but it is partly a selection effect, because tail candidates are cached EXACT_FULL / search winners.

## 3. Recall and decision decomposition (`P1_FAILURES.json`)

- **Coverage (lower bound):** 222 of the 240 K1/K2 VAL roots have a known verified K ≤ 2 success. On 219 of them, a known success lies inside the D4 pool. Only 3 roots have known successes off D4 only.
- **Positive rates by tier:** among decided labelled candidates, positive rates are 66 % (ranks 1–4), 83 % (5–6), 75 % (7–12) and 73 % (above 12). These are selection-biased.
- **EXACT4 re-run on all 240 K1/K2 VAL roots** (identical frozen rule; decided labels only):

  | Primary category | Roots |
  |---|---|
  | SUCCESS | 145 |
  | unresolved (no decided label for the pick) | 58 |
  | **ranking failure** (a verified success in D4 scored lower): 12 FAIL_X, 9 FAIL_Y | **21** |
  | NOOP although a scored known success existed (gate) | 7 |
  | known success only outside D4 (pool-miss candidate) | 2 |
  | failure with no known witness | 7 |
  | order failure (other order of the same set verified) | 0 |

  EXACT6 is similar: 141 SUCCESS, 25 ranking failures, 7 gate.

## Conclusion and gate

- **Gate: PASS. Proceed to P2 and P3.**
  - Strict same-root Z+/Z− pairs exist on 165 VAL roots (89 in DEV_CAL, 76 in DEV_AUDIT) and on about 1,700 TRAIN roots.
  - Gate/admission errors are minor (7 roots), so P2 focuses on ranking, not the gate.
- **Errors are dominated by ranking, not recall.** Within ranking:
  - **(i)** The pX1 head anti-ranks within a root.
  - **(ii)** The scorer cannot separate destinations for a fixed object set.
  - **(iii)** Probabilities for off-top-4 sets are inflated, by tier.
- **Hypothesis status:**
  - H1 (misranking dominates) is supported.
  - H2 (errors concentrate in rank strata) is supported, with a selection-bias caveat.
  - The training-support audit (P0) shows the tail is labelled but under-represented relative to legal support. The VAL/TRAIN gap points to generalization failure, not missing support alone.
- **No causal blocker claims are made.**
