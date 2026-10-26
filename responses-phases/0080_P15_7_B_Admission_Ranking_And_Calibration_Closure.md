# 0080 — P15-7: B admission, ranking and calibration closure (secondary; saved data only)

**Actual result**
- **Data:** saved P13 frozen test predictions (`runs/p13/holdout/PREDICTIONS_FROZEN.json`), P13 teacher labels (VERIFIED / CERTIFIED only), P14 validation rows and P14 matched-admission / natural diagnostics.
- **Spend:** **no training, no new labels**. `b_diag` 3.1 / 3,000 CPU-s.
- **Output:** `runs/p15/B/B_CLOSURE.json` (`p15_bench.b_closure`).
- **Gate:** `runs/p15/P15_7_GATE.json` → **PASS (closure)**. B's extra factors show **no deployment contribution under fair admission**. Ranking evidence favours keyed B over the F2 and SF arms only.

## 1. Admission: validation-matched is not test-matched (terminology corrected)

- All arms were matched on **validation** coverage (≈ 0.694), not on test admission.
- Test-admission denominators: the 129 executed roots (P14 `MATCHED_ADMISSION.json`).

| arm | val coverage (matched) | **test admission** | executed success (lower bound) | historical thr: val cov / test adm |
|---|---|---|---|---|
| K-B | 0.694 | **0.835** | 0.731 | 0.694 / 0.835 |
| A | 0.694 | 0.827 | 0.731 | 0.509 / 0.620 |
| K-C | 0.694 | 0.860 | 0.731 | 0.532 / 0.672 |
| SF | 0.694 | 0.889 | 0.649 | 0.275 / 0.346 |
| B-F2 | 0.698 | **0.910** | 0.664 | 0.257 / 0.341 |
| B-F3pm | 0.694 | 0.891 | 0.744 | 0.658 / 0.835 |
| B-F4 | 0.694 | **0.902** | 0.734 | 0.450 / 0.605 |
| B-F5spm | 0.694 | **0.902** | 0.742 | 0.365 / 0.540 |
| B-F5qpm | 0.698 | 0.925 | 0.736 | 0.554 / 0.734 |
| B-U | 0.694 | 0.894 | 0.770 | 0.482 / 0.589 |
| B-V0 | 0.694 | 0.889 | 0.690 | 0.613 / 0.796 |
| B-F1off | 0.694 | 0.912 | 0.760 | 0.644 / 0.866 |

**Reading.** At equal validation coverage, the ablations admit **7–9 pp more** test roots than K-B. Differences in conditional success therefore mix admission with ranking. The next section separates the two.

## 2. Common-candidate ranking (admission removed; UNKNOWN candidates censored)

**Set-up:**
- **Roots:** all 169 test roots have an **identical candidate set across every arm and seed** (common-scoreable).
  - 110 roots have ≥ 1 decided-feasible candidate.
  - 83 roots have both decided-feasible and decided-infeasible candidates (within-root AUROC).
- **Ranking:** candidates sorted by u (feasibility logit).
- **Censoring:** UNKNOWN candidates are skipped, never treated as negatives, and are counted when ranked ahead of the first feasible one.

| ranking | first-feasible rank (decided) | top-1 decided-feasible | top-1 UNKNOWN (censored) | within-root AUROC (83) |
|---|---|---|---|---|
| **K-B** | **1.024** | 0.930 | 0.055 | **0.972** |
| A | 1.027 | 0.915 | 0.076 | 0.970 |
| B-F1off | 1.033 | 0.930 | 0.048 | 0.970 |
| B-F3pm | 1.033 | 0.939 | 0.045 | 0.968 |
| B-F4 | 1.042 | 0.921 | 0.052 | 0.965 |
| K-C | 1.039 | 0.939 | 0.042 | 0.963 |
| B-V0 | 1.033 | 0.888 | 0.100 | 0.963 |
| B-U | 1.030 | 0.930 | 0.052 | 0.957 |
| B-F5spm | 1.048 | 0.921 | 0.055 | 0.949 |
| B-F5qpm | 1.042 | 0.909 | 0.061 | 0.949 |
| SF | 1.139 | 0.794 | 0.088 | 0.899 |
| B-F2 | 1.185 | 0.791 | 0.042 | 0.893 |
| baseline: fewest moves | 2.327 | 0.245 | 0.036 | 0.164 |
| baseline: random (expected) | 1.735 | 0.596 | — | — |
| oracle | 1.000 | 1.000 | — | 1.000 |

**Paired within-root AUROC, K-B minus arm** (83 roots; exact sign test on discordant roots; root bootstrap CI). These 11 comparisons are secondary, so the Bonferroni threshold is 0.0045.

| arm | K-B better / worse | mean diff [95 % CI] | p |
|---|---|---|---|
| B-F2 | 35 / 2 | +0.079 [+0.054, +0.105] | **1e-8** |
| SF | 29 / 4 | +0.072 [+0.045, +0.102] | **1e-5** |
| B-F5spm | 8 / 0 | +0.023 [+0.008, +0.041] | 0.008 (not significant after Bonferroni) |
| B-U | 11 / 2 | +0.014 [+0.004, +0.026] | 0.022 (not significant after Bonferroni) |
| B-V0 | 14 / 3 | +0.009 [−0.015, +0.030] | 0.013 (CI crosses 0) |
| A, B-F1off, B-F3pm, B-F4, K-C, B-F5qpm | ≤ 7 / ≤ 4 | ≤ +0.022, all CIs cross 0 | ≥ 0.34 |

**Reading.**
- Every learned scorer ranks far better than the model-free baselines.
- K-B's ranking advantage is clear only against **F2-off** and **SF**. Against A, K-C, F1-off, F3pm and F4, ranking is indistinguishable.
- The equal-conditional-success results seen earlier are therefore **not** proof of equal ranking. They are mostly admission effects, and the ranking itself is near-saturated for most arms.

## 3. Original-feasible zero-move behaviour (natural stream: 45 roots, 27 feasible originals)

| arm | feasible recall @0.5 | infeasible recall | AUROC | Brier | NLL | **TOP-1 = empty on feasible originals** |
|---|---|---|---|---|---|---|
| K-B | 0.704 | 0.778 | 0.881 | 0.148 | 0.452 | **0.543** |
| A | 0.889 | 0.778 | 0.889 | 0.134 | 0.416 | 0.420 |
| K-C | 0.815 | 0.778 | 0.866 | 0.147 | 0.457 | 0.630 |
| B-F1off | 0.963 | 0.444 | 0.840 | 0.192 | 0.582 | 0.815 |
| B-F5spm | 0.926 | 0.556 | 0.891 | 0.144 | 0.420 | 0.617 |
| SF | 0.852 | 0.722 | 0.891 | 0.137 | 0.433 | 0.272 |
| B-V0 | 0.000 | 1.000 | 0.842 | 0.454 | 1.337 | 0.025 |

- **K-B chooses a relocation or abstains on 46 % of feasible originals.** This is the clearest B deployment defect, and it is a decision-rule / calibration problem rather than a discrimination problem (AUROC 0.88).
- **Blind stream:** 121 roots, 0 feasible originals. Infeasible recall is 0.99–1.00 for every arm, so the stream cannot measure zero-move recall.
- **Per-bin reliability with Wilson CIs** and the mixed-distribution joint four-bit NLL by pattern are in `NATURAL_DIAG.json` (reproduced under `zero_move_original`).
  - Example, natural 1111 pattern (24 roots): K-B NLL 2.34, A 1.59, B-F2 1.58, SF 1.98.
  - Infeasible originals: K-B NLL 0.18–0.19 on patterns 0001 / 0101.

## 4. Validation-only temperature + bias calibration under frozen rankings

**Fit:** p′ = σ(a · u/τ + b), with (a, b) fitted on validation rows only, per arm and seed (≈ 74 roots and ≈ 400 decided candidates each). It is scored on the 169 common test roots.

| arm | T = 1/a (mean) | b | Brier before → after | NLL before → after | empty-candidate feasible recall | choices changed at the historical threshold | label-correct roots |
|---|---|---|---|---|---|---|---|
| K-B | 0.97 | −0.22 | 0.074 → 0.081 | 0.250 → 0.267 | 0.716 → 0.691 | 19 / 507 | 0.552 → 0.542 |
| A | 0.97 | −0.32 | 0.062 → 0.071 | 0.226 → 0.252 | 0.852 → 0.815 | 26 | 0.420 → 0.393 |
| B-F3pm | 0.97 | +0.03 | 0.079 → 0.078 | 0.268 → 0.265 | 0.704 → 0.679 | 48 | 0.535 → 0.564 |
| B-F4 | 1.01 | +0.04 | 0.060 → 0.058 | 0.204 → 0.200 | 0.901 → 0.914 | 11 | 0.396 → 0.394 |
| others | 0.97–1.01 | −0.34 … +0.04 | ±0.01 | ±0.03 | ±0.06 | 6–34 | ±0.04 |

**Reading.**
- The validation-fitted temperatures are ≈ 1 and the biases are small. The frozen models are already near-calibrated on validation.
- On test, recalibration **worsens** NLL in 25 of 36 (arm, seed) cases. That is validation→test shift, not a fixable miscalibration.
- At a validation-coverage-matched threshold, a monotone transform cannot change the ordering. The residual 3–30 changed choices come only from the 0.01 threshold grid.
- **Verdict: no validated calibration benefit. No decision change is adopted.** Isotonic calibration was not attempted: ≈ 400 validation rows per checkpoint, with too few feasible originals (validation has ≈ 6 NAT roots).

**Denominators.** Here, admission and label-correct are computed over all 169 common roots, with abstain counted as not correct. P14's §1 table uses the 129 executed roots. The two are not interchangeable.

## 5. Lean inference configuration

- B-F3pm, B-F5spm and B-F5qpm are **post-hoc inference masks** of trained checkpoints, not matched retrains. Their rows above are therefore inference-configuration evidence only.
- A generic-only F5 remains **NOT experimentally established**.
- The keyed query ontology is kept as a correctness invariant.
- DINOv2 is the input representation and is not, by itself, evidence of geometric causal understanding.

## 6. Verdicts

| question | verdict |
|---|---|
| B extra factors (F3 / F4 / F5) contribute to deployment under fair admission | **NEGATIVE** (indistinguishable ranking; admission differences explain the earlier success gaps) |
| keyed B ranks better than F2-off / SF | **SUPPORTED** (exploratory, Bonferroni-surviving) |
| B handles feasible originals (zero-move) | **NEGATIVE** for K-B (0.543 top-1 empty) |
| validation-only calibration fixes it | **NEGATIVE** (no validated improvement) |
| generic-only F5, lean-B retrain | **NOT_TESTED** (no retrain by contract) |

## 7. P16 proposal (separate, costed, preregisterable; not started)

**Question:** with the decision rule fixed, does a **zero-move-first, validation-calibrated admission** close the feasible-original gap without losing infeasible-original retrieval? And are F3 / F4 / F5 needed when K-B and the ablations are matched on **test-independent admission**?

**Design:**
1. **New prospective cohort.** 120 natural roots (target ≥ 60 feasible originals) plus 48 mechanism-conditioned roots. Seeds are disjoint from P13–P15; the generator and roster are frozen and pushed before labels.
2. **Arms.** K-B and a matched retrain of a lean B (no F3 / F4 / HO), 3 seeds each, same data, same epochs.
   - Admission is matched on a **separate calibration split** (not validation, not test), with the threshold chosen for equal calibration-split coverage.
   - Primary endpoint: paired top-1 label-correct on feasible originals.
   - Secondary: within-root AUROC on common candidates and infeasible-original retrieval.
3. **Statistics.** Exact paired sign test, α = 0.05. Power was simulated for a 46 % → 20 % wrong-choice rate with independent errors: 24 feasible originals → 0.33, 48 → 0.69, **60 → 0.81**.
4. **Cost:**

| item | CPU-s |
|---|---|
| labels (168 roots × ≈ 130, from P13 rates) | ≈ 22 k |
| lean-B training (3 seeds × ≈ 2.5 k) | ≈ 7.5 k |
| records / inference | ≈ 1 k |
| regression | ≈ 1 k |
| **total** | **≈ 31.5 k** |

5. **Stop rule.** If the calibration split has fewer than 12 feasible originals, or the test cohort has fewer than 60, the zero-move endpoint is UNDERPOWERED. No adaptive stopping.

`runs/p15/B/P16_PROPOSAL.json` holds the machine-readable form.
