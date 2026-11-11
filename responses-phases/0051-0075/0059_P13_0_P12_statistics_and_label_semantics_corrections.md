# 0059 — P13-0: P12 statistics and label-semantics corrections (versioned addendum)

**Previous turn sync:** P12 final `021cd00461bfb346053c991303385a9e467769f5` (local = origin/main verified at start).

**Actual result.**
- **Gate:** `runs/p13/P13_0_GATE.json` → **PASS**.
- **Scope:** all corrections are read-only regenerations from the frozen P12 predictions and sealed labels. No fitting, label edits, teacher calls or writes to P10–P12 artifacts. Total ledger cost: 6.9 CPU-s.
- **F3, corrected to the preregistered estimand:** Δ −0.057 [−0.099, −0.016], raw p 0.025, **Holm p 0.0496**. Still a significant reversal (B-F3 more accurate), but the evidence is weaker than P12's published p 0.0118.
- **F5s:** NOT_CONFIRMED (Holm p 0.082).
- **The constant κ̂ = 0 control beats every frozen model** (MAE 0.092 vs B 0.366). On these families, no model's κ predictions carry useful interaction information.

## 1. κ estimand (`runs/p13/p13_0/KAPPA_CORRECTED.json`, `p13_factors.kappa_correction`)

- **What P12 preregistered:** the error of the seed-mean prediction, e = |κ̂ − κ| with κ̂ = (1/3) Σₛ (pₛ(A+B) − pₛ(A) − pₛ(B) + pₛ(∅)).
- **What P12 computed:** the mean over seeds of |κ̂ₛ − κ|. This is never smaller than the preregistered error.
- **Check:** the published statistic is reproduced exactly (both primary tests, to 1e-12).
- **Cohort:** 65 proof-grounded four-tuples, κ = 0: 59, +1: 4, −1: 2.
- **Truth patterns** (y₀ yA yB yAB): 0011 ×32, 0101 ×27, 0001 ×4, 0111 ×2.

**Primary tests.** Positive Δ means full B is better.

| test | estimand | mean Δ | 95 % CI | B / ablation better | raw p | Holm p | d | verdict |
|---|---|---|---|---|---|---|---|---|
| F3 | **preregistered (seed-mean)** | **−0.057** | [−0.099, −0.016] | 23 / 42 | 0.025 | **0.0496** | −0.34 | SIGNIFICANT_REVERSAL |
| F5s | **preregistered (seed-mean)** | −0.046 | [−0.130, 0.042] | 25 / 40 | 0.082 | 0.082 | −0.13 | NOT_CONFIRMED |
| F3 | published (seed-wise) | −0.074 | [−0.112, −0.032] | 21 / 44 | 0.0059 | 0.0118 | −0.44 | SIGNIFICANT_REVERSAL |
| F5s | published (seed-wise) | −0.027 | [−0.109, 0.058] | 30 / 35 | 0.62 | 0.62 | −0.08 | NOT_CONFIRMED |

**Why the verdict is unchanged but weaker.** Averaging seeds cancels part of each model's spurious κ̂, and the cancellation is larger for B than for B-F3. B's MAE falls from 0.404 to 0.366, against B-F3 from 0.331 to 0.309.

**Per-family Δ (preregistered):**
- F3: X −0.040, Y −0.069.
- F5s: X +0.136, Y −0.175.

**MAE by true κ (preregistered estimand):**

| model | all | κ = −1 (2) | κ = 0 (59) | κ = +1 (4) | predicts \|κ̂\| ≥ 0.5 when κ = 0 |
|---|---|---|---|---|---|
| **constant 0** | **0.092** | 1.000 | **0.000** | 1.000 | 0 % |
| SF | 0.208 | 0.217 | 0.166 | 0.823 | 5.1 % |
| B-F5q | 0.240 | 0.158 | 0.190 | 1.009 | 8.5 % |
| B-F3 | 0.309 | 0.360 | 0.265 | 0.944 | 13.6 % |
| B-F5s | 0.321 | 0.083 | 0.251 | 1.468 | 18.6 % |
| keyed C | 0.343 | 0.405 | 0.307 | 0.843 | 22.0 % |
| **keyed B** | 0.366 | 0.400 | 0.335 | **0.810** | 20.3 % |
| A | 0.421 | 0.143 | 0.348 | 1.633 | 22.0 % |
| B-V0 | 0.641 | — | — | — | 66.1 % |

- **B vs constant 0:** −0.274 [−0.344, −0.199]; the constant is better on 59 of 65 roots.
- **B vs SF:** −0.159 [−0.208, −0.112]; SF is better on 55 of 65.
- **Where B does best:** it has the lowest error on the 4 κ = +1 roots (descriptive, n = 4). No model gets close to κ = +1 there.
- **Threshold:** the |κ̂| ≥ 0.5 cut is nearest-integer rounding of κ ∈ {−1, 0, 1}. It was not tuned.

**Label correction.** P12's "four-bit scene NLL" was a **sum of per-variable binary NLLs, not a joint likelihood**. It is re-reported here with seed-mean marginals: B 0.368, B-F3 0.304, SF 0.680, A 0.628. The frozen P12 predictions store marginals only, so a true joint four-bit likelihood cannot be computed from them. P13 must store joint probabilities.

## 2. Strict D / scene-edit correspondence (`D_STRICT_{p10b,holdout}.json`, `p13_factors.d_strict`)

**The check now verified explicitly for every parking subset of the pool:**
- the subset is a frozen catalogue item;
- `d_subset` equals the subset;
- the edit dict equals the root's parking map restricted to that subset, keyed by the same object ids;
- non-empty subsets are fixed-q0 `SCENE_TARGET_ONLY` queries;
- the empty subset is the empty executed repair from q0 (the original task).

**Lattices passing:** P10b 56 / 56 infeasible complete lattices, holdout 64 / 64. Query ids are a deterministic hash of (root, kind, edit), so P12's weaker check selected the same roots. **The matched cohort is unchanged at 33.**

**What changes is the scoring.** A choice where a model predicts no clearing set is now scored as a miss (F1 0) on the common cohort, never as an empty blocker set and never silently dropped.

**P10b, exact common cohort (33 roots, 30 proof-grounded, 3 operational; per-root F1 / exact-set):**

| arm | coverage (3 seeds) | no-clearing-set choices | F1 conservative (33) | exact (33) | F1, all models predict (25) | F1, proof-grounded (30) |
|---|---|---|---|---|---|---|
| D | 33 | — | **0.939** | 0.818 | 0.947 | 0.941 |
| geometry | 33 | — | 0.929 | 0.788 | **0.960** | **0.956** |
| D-pairless | 33 | — | 0.919 | 0.818 | 0.942 | 0.922 |
| keyed C | 33 | 0 | 0.882 | 0.727 | 0.911 | 0.881 |
| keyed B | 33 | 0 | 0.872 | 0.697 | 0.893 | 0.867 |
| SF | 33 | 2 | 0.835 (P12: 0.855) | 0.687 | 0.902 | 0.841 |
| A | 33 | 7 | 0.801 (P12: 0.842) | 0.646 | 0.924 | 0.830 |

**Paired F1, model − D (33 roots):**

| model | difference | 95 % CI | p |
|---|---|---|---|
| B | −0.067 | [−0.131, −0.013] | 0.12 |
| C | −0.057 | [−0.108, −0.013] | 0.065 |
| A | −0.138 | [−0.226, −0.054] | 0.049 |
| geometry | −0.010 | [−0.071, 0.051] | 1.0 |
| D-pairless | −0.020 | [−0.057, 0.013] | 0.69 |

On the 25 roots where every model predicts a set, nothing differs from D significantly.

**Holdout:** the frozen A / B / C / SF predictions never scored the parking subsets containing C, so their exact lattice coverage is **0 / 64**, and matched attribution stays **UNSUPPORTED**. **P13 design consequence:** every new P13 catalogue scores *every* parking subset, so matched attribution is possible.

## 3. P12 execution coverage (`P12_EXEC_COVERAGE.json`, `p13_execution.coverage_diagnosis`)

**Per-batch roots (frozen order):**

| batch | complete | partial | untouched | complete set is a strict prefix |
|---|---|---|---|---|
| 1 | 13 | 0 | 7 | yes |
| 2 | 20 | 0 | 0 | yes |
| 3 | 8 | 0 | 12 | yes |
| 4 | 8 | 0 | 12 | yes |

**Batch CPU:** 2,179, 1,125, 2,091 and 2,087 CPU-s, then the ordered continuation (17 episodes, 1,548 CPU-s).

**Mechanism.**
- Coverage stops where cumulative cost, plus one 180 CPU-s episode reserve, reaches the batch cap.
- Episode cost depends strongly on outcome: censored episodes average 170 CPU-s, failures without a witness 24, successes 15, certified-infeasible targets 2.
- Batch 2 ran few censored episodes and finished all 20 roots.
- **No root's inclusion depends on its own outcome**, only on its position and on the cost (largely censoring) of the earlier roots in its batch.

**Is the covered set balanced on pre-outcome features?** Mostly:
- X share: 0.51 covered vs 0.48 uncovered;
- jobs per root: 5.7 vs 5.5;
- arms abstaining per root: 1.31 vs 2.00, the one imbalance. Uncovered roots have more frozen abstentions, which count as failures for the abstaining models.

**Episode outcomes (all 452 keys):** SUCCESS 175, censored 33, certified-infeasible target 29, no witness 28, unresolved target 15, NOT_RUN_BUDGET 172.

**Disclosed:** one killed launch (< 1 min) has no guard record. Its CPU is not inferred, and nothing it produced is counted. Completing the 31 untouched roots is a separate stage (P13-5, cap 9,000 CPU-s); it is **not** new confirmatory evidence.

## 4. Tests

- `tests/test_p12.py`: 6 / 6 pass.
- The full suite (407) and the six replays run together with the new P13 tests at P13-7.
