# 0050 — P11-5: D versus A / B / C / SF — initial infeasibility and blocker identity

**Scope.** All numbers are regenerated in `runs/p11/d_compare/D_VS_ABC_p10b.json` from the frozen P10d snapshot and the adjudicated, unsealed P10b blind roots. They are POST-HOC relative to P10d's preregistration. Units are independent roots, with seed means per root and 95 % root-bootstrap CIs.

**Coverage:** **no constructor-disjoint holdout exists** (P11-4 blocked), so there is no second cohort. D pools have ≤ 4 objects; the exact-enumeration cap is 6. D is limited to feasibility and blocker identity; it does no movement, destinations, recursion or execution.

## 1. Initial target-retrieval feasibility (identical cohort)

**Cohort:** N = **64** blind roots with a decided original-task label. One root is excluded because its original was UNKNOWN, and no root is missing a prediction.
- 4 feasible (VERIFIED witness) vs **60 infeasible** (CERTIFIED). Infeasible prevalence is 0.94.
- Threshold: p(feasible) ≥ 0.5.

| arm | accuracy | balanced acc. | TP / TN / FP / FN | feasible recall | infeasible recall | AUROC | NLL | Brier | ECE (10 bins) |
|---|---|---|---|---|---|---|---|---|---|
| **D** | **1.000** | **1.000** | 4 / 60 / 0 / 0 | 1.00 | 1.00 | 1.000 | **0.0049** | 0.0002 | 0.005 |
| D-pairless | 1.000 | 1.000 | 4 / 60 / 0 / 0 | 1.00 | 1.00 | 1.000 | 0.0062 | 0.0005 | 0.006 |
| SF | 1.000 | 1.000 | 4 / 60 / 0 / 0 | 1.00 | 1.00 | 1.000 | 0.0474 | 0.0081 | 0.043 |
| keyed B | 0.984 | 0.875 | 3 / 60 / 0 / 1 | 0.75 | 1.00 | 1.000 | 0.0221 | 0.0081 | 0.014 |
| keyed C | 0.984 | 0.875 | 3 / 60 / 0 / 1 | 0.75 | 1.00 | 0.988 | 0.0585 | 0.0156 | 0.019 |
| A | 0.984 | 0.875 | 3 / 60 / 0 / 1 | 0.75 | 1.00 | 0.996 | 0.0481 | 0.0124 | 0.028 |

- **Seed variability (accuracy per seed):**
  - D 1.0 / 1.0 / 1.0;
  - B 1.0 / 0.984 / 0.984;
  - SF 0.984 / 1.0 / 0.922.
- **Caveat:** with only 4 feasible roots, feasible recall and AUROC rest on 4 positives. D and D-pairless are calibrated best (lowest NLL), but the differences are not statistically resolvable.

## 2. Blocker identity (all complete masks)

**GT definition:** the union of members of all inclusion-minimal sufficient clearing sets, under the frozen parking map, among the declared movable pool.
- **Complete masks:** **60** (39 proof-grounded, 21 operational).
- **Excluded:** 4 INCOMPLETE, 1 UNKNOWN original.
- **Alternative-set roots:** 4 have alternative minimal sets, so the union is not the same as the necessary intersection. D is trained on the union only; **no necessity-head claim is made.**

Values are per-object metrics, macro by root (micro F1 in its own column).

| stratum | N | D F1 [CI] | D prec / rec / exact | D-pairless F1 [CI] | D-pairless prec / rec / exact | geometry F1 | geometry exact |
|---|---|---|---|---|---|---|---|
| all | 60 | 0.872 [0.830, 0.910] | 0.944 / 0.853 / 0.578 | 0.882 [0.827, 0.928] | 0.942 / 0.884 / 0.667 | 0.797 [0.733, 0.861] | 0.533 |
| proof-grounded | 39 | **0.932** [0.877, 0.972] | 0.915 / 0.974 / 0.829 | 0.889 [0.803, 0.960] | 0.910 / 0.932 / 0.803 | 0.906 [0.821, 0.974] | 0.821 |
| operational | 21 | 0.761 [0.717, 0.803] | 1.000 / 0.627 / 0.111 | **0.869** [0.832, 0.903] | 1.000 / 0.795 / 0.413 | 0.595 [0.563, 0.627] | 0.000 |
| 0 blockers | 4 | 1.000 | — | 1.000 | — | 0.500 | — |
| 1 blocker | 20 | 0.878 | — | 0.783 | — | **0.950** | — |
| 2 blockers | 18 | 0.975 | — | **0.981** | — | 0.907 | — |
| 3 blockers (operational) | 9 | 0.800 | — | **0.896** | — | 0.500 | — |
| 4 blockers (operational) | 9 | 0.667 | — | **0.834** | — | 0.667 | — |

Micro F1 (all): D 0.837, D-pairless 0.895, geometry 0.768.

**Paired comparisons:**

| contrast | difference | 95 % CI | roots a / b better | sign p |
|---|---|---|---|---|
| D − D-pairless, F1 | −0.010 | [−0.046, +0.038] | 6 / 19 | 0.015 |
| D − D-pairless, exact | −0.089 | [−0.156, −0.017] | 3 / 15 | 0.0075 |
| D − D-pairless, proof-only F1 | +0.043 | [−0.003, +0.100] | 5 / 2 | 0.45 |
| D − D-pairless, 3–4-blocker operational | −0.132 | [−0.165, −0.102] | 0 / 17 | — |
| D − geometry, F1 | +0.075 | [0.007, 0.142] | 19 / 10 | 0.14 |

## 3. Faithfully matched A / B / C / SF counterfactual attribution

**Matching rule:** a root is matched only when:
- D's movable pool is exactly the two edit roles; and
- each parking subset {A}, {B}, {A, B} is the **same physical query** as zS[A], zS[B], zS[A+B]. This is checked by object ids, destinations, edit dictionary and query id; the root and q0 are shared.

**Derived attribution:** predicted subset feasibility (p ≥ 0.5) → minimal predicted-feasible subsets → union mask.

**Cohort:** **matched N = 33** (30 proof-grounded); **unsupported N = 27**. In every unsupported root the pool is not 2 objects, or its parking subsets differ from the zS edits. Unsupported roots receive **no score**.

| arm (same 33 roots) | F1 [CI] | precision | recall | exact |
|---|---|---|---|---|
| **D** | **0.939** [0.902, 0.973] | 0.929 | 0.980 | 0.818 |
| geometry heuristic | 0.929 [0.879, 0.970] | 0.970 | 0.924 | 0.788 |
| D-pairless | 0.919 [0.865, 0.970] | 0.914 | 0.970 | 0.818 |
| keyed C | 0.882 [0.815, 0.943] | 0.879 | 0.924 | 0.727 |
| keyed B | 0.872 [0.801, 0.929] | 0.864 | 0.924 | 0.697 |
| SF | 0.835 [0.744, 0.912] | 0.889 | 0.848 | 0.687 |
| A | 0.801 [0.704, 0.889] | 0.894 | 0.818 | 0.646 |

**D vs each arm on the matched roots (F1):**

| contrast | difference | 95 % CI | roots D / other better | sign p |
|---|---|---|---|---|
| D − A | +0.138 | [0.054, 0.226] | 13 / 4 | 0.049 |
| D − B | +0.067 | [0.013, 0.131] | 11 / 4 | 0.12 |
| D − C | +0.057 | [0.013, 0.108] | — | 0.065 |
| D − SF | +0.104 | [0.034, 0.189] | — | 0.14 |
| D − D-pairless | +0.020 | — | — | 0.69 |
| D − geometry | +0.010 | — | — | 1.0 |

**Definition change disclosed:** this report uses the "minimal predicted-feasible subsets" derivation. That moves P10e's B matched F1 from 0.862 to 0.872, because P10e mapped non-monotone predictions to an empty mask.

## 4. Conclusions

- **Initial infeasibility detection:** D ≈ D-pairless are best calibrated and perfectly accurate on this cohort; SF is also perfect, and A / B / C each miss one of 4 feasible roots. The data cannot rank them statistically (4 positives).
- **Blocker identity:**
  - On proof-grounded masks, D is best (0.932).
  - On operational corridor masks, D-pairless is significantly better.
  - On the matched cohort, D (0.939) ≥ geometry (0.929) ≥ D-pairless ≥ C ≥ B ≥ SF ≥ A, with D significantly above A and with CIs excluding 0 against B and C (sign tests ns).
- **Pairwise Boltzmann term:** **NOT BENEFICIAL / NOT IDENTIFIED.**
  - Overall F1 shows no gain, and exact-set accuracy is worse with the pair term.
  - The only positive direction is the proof-only F1, which is not significant.
  - A CI spanning zero does not show equivalence.

**Figures:** `visualizations/p11/P11_D_vs_ABC.png`, `visualizations/p11/P11_D_attribution_scenes.png`.
