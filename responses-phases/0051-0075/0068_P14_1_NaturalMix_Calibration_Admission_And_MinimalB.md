# 0068 — P14-A1: natural-mix calibration, admission-matched selection and the minimal-B diagnosis

**Previous turn sync:** P14-A0 pushed as `b3b5be63496025ca8a445b84b90ad1e4765db426`.

**Status: EXPLORATORY.** Everything here is post-hoc on frozen P13 predictions. No calibrator or threshold was fitted on P13 blind labels. Matched thresholds come from validation-only re-inference with the frozen P13 checkpoints (`VALIDATION_ROWS.json`). Any counterfactual choice that P13 had not executed was **physically executed** under the identical strict-TOP1 protocol and episode identity before being scored: 74 episodes (`CF_JOBS.json`), plus 3 resumed after the per-worker cap. Nothing is imputed.

**Gate:** `runs/p14/P14_A1_GATE.json` → **PASS** (diagnostics). The fresh confirmatory repair cohort is **not** run in this stage; see §5.

**Spend:** `a_diagnostics` 1,864 / 3,000 CPU-s.

## 1. The natural ("synthetic unconditioned") stream: 45 decided originals, 27 feasible

This stream is a synthetic unconditioned generator, **not** real-world prevalence.

| model | AUROC | feasible recall @ 0.5 | infeasible recall | balanced accuracy | Brier | NLL | mean P(feasible) on feasible originals | TOP1 = empty repair on feasible originals |
|---|---|---|---|---|---|---|---|---|
| **keyed B** | 0.881 | **0.704** | 0.778 | 0.741 | 0.148 | 0.452 | **0.682** | **0.543** |
| C | 0.866 | 0.815 | 0.778 | 0.796 | 0.147 | 0.457 | 0.775 | 0.630 |
| A | 0.889 | 0.889 | 0.778 | **0.833** | **0.134** | **0.416** | 0.757 | 0.420 |
| SF | 0.891 | 0.852 | 0.722 | 0.787 | 0.137 | 0.433 | 0.751 | 0.272 |
| B-F3pm | 0.893 | 0.741 | 0.778 | 0.759 | 0.149 | 0.477 | 0.650 | 0.556 |
| B-F4 | 0.864 | 0.926 | 0.611 | 0.769 | 0.159 | 0.475 | 0.831 | 0.580 |
| B-F5spm (combined generic + HO removed) | 0.891 | 0.926 | 0.556 | 0.741 | 0.144 | 0.420 | 0.824 | 0.617 |
| B-F5qpm | 0.809 | 0.815 | 0.611 | 0.713 | 0.175 | 0.529 | 0.771 | 0.617 |
| B-U | 0.879 | 0.926 | 0.667 | 0.796 | 0.142 | 0.450 | 0.797 | 0.321 |
| D | 0.874 | 0.852 | 0.722 | 0.787 | 0.142 | 0.481 | 0.778 | — |
| D-pairless | 0.862 | 0.889 | 0.722 | 0.806 | 0.148 | 0.512 | 0.829 | — |

**Keyed B reliability (5 bins; Wilson 95 % CIs):**

| P(feasible) bin | n | mean P | observed rate | 95 % CI |
|---|---|---|---|---|
| 0.0–0.2 | 11 | 0.09 | 0.18 | [0.05, 0.48] |
| 0.2–0.4 | 4 | 0.27 | 0.25 | — |
| 0.4–0.6 | 10 | 0.48 | 0.60 | — |
| 0.6–0.8 | 8 | 0.72 | 0.75 | — |
| 0.8–1.0 | 12 | 0.89 | 1.00 | [0.76, 1.00] |

The bins are small and the intervals wide, but they point to systematic **under**-prediction of feasibility.

**Joint four-bit NLL by outcome pattern (natural):**

| pattern | n | B | B-F5spm | A | B-U | SF |
|---|---|---|---|---|---|---|
| **1111** (feasible original, every edit feasible) | 24 | **2.34** | 1.13 | 1.59 | 1.31 | 1.98 |
| 0011 | 3 | 3.04 | 3.06 | 2.58 | 2.63 | 3.25 |
| 0111 | 1 | 7.21 | 4.19 | 2.70 | 4.93 | 3.02 |
| 0000 | 1 | 1.15 | 0.03 | 0.01 | 0.15 | 0.01 |

**Reading:**
- **Ranking is not the problem:** AUROC is 0.86–0.89 for every model.
- **B's failure is probabilistic:** it shifts P(feasible) down on feasible originals (mean 0.68), and its coupled P_S assigns low probability to the all-feasible pattern.
- **Behavioural cost:** on feasible originals, B's TOP1 picks the empty repair only 54 % of the time. The rest are unnecessary relocations or abstentions.
- **On the mechanism challenge set,** every original is infeasible and every model is near-perfect (infeasible recall 0.99–1.00).

## 2. Admission versus conditional selection quality (129 executable roots; corrected from 0067)

**At P13's historical thresholds:**
- B attempts 0.835 of choices with 0.879 success when it attempts, so root success is 0.734.
- A: 0.620 × 0.900 = 0.558.
- SF: 0.346 × 0.918 = 0.318.

B's historical advantage is coverage, not conditional accuracy.

**Matched admission** (thresholds from validation only; target = keyed B's own validation coverage per seed, 0.69–0.70, or keyed B's validation false-admission rate; executed success over 129 roots, 3 seeds, abstain = failure):

| arm | historical threshold | **coverage-matched** | false-admission-matched |
|---|---|---|---|
| keyed B | 0.734 | 0.731 | 0.762 |
| A | 0.558 | **0.731** | 0.739 |
| C | 0.579 | **0.731** | 0.698 |
| B-F3pm | 0.708 | 0.744 | 0.736 |
| B-F4 | 0.525 | **0.734** | 0.708 |
| B-F5spm | 0.483 | **0.742** | 0.705 |
| B-F5qpm | 0.612 | 0.736 | 0.742 |
| B-U | 0.527 | 0.770 | 0.770 |
| B-F2 | 0.313 | 0.664 | 0.434 |
| SF | 0.318 | 0.649 | 0.465 |

**Paired contrasts, keyed B − arm** (executed success; bootstrap CI; sign p):

| arm | coverage-matched | false-admission-matched |
|---|---|---|
| A | **0.000** [−0.031, 0.034], p 1.0 | +0.023 [−0.003, 0.049], p 0.19 |
| C | **0.000** [−0.034, 0.034], p 0.86 | +0.065 [0.036, 0.098], p 2e-4 |
| B-F3pm | −0.013 [−0.049, 0.021], p 0.86 | +0.026 [0.000, 0.052], p 0.11 |
| B-F4 | **−0.003** [−0.041, 0.036], p 0.71 | +0.054 [0.021, 0.090], p 0.029 |
| B-F5spm | **−0.010** [−0.049, 0.026], p 1.0 | +0.057 [0.021, 0.093], p 0.003 |
| B-F2 | **+0.067** [0.010, 0.124], p 0.011 | +0.328 [0.248, 0.408], p < 1e-4 |
| SF | **+0.083** [0.028, 0.137], p 0.014 | +0.297 [0.230, 0.362], p < 1e-4 |

**Conclusions on the P13 execution claims (exploratory, frozen roots):**
1. Once all arms are held to the **same validation-derived admission coverage**, B's executed advantage over A, C, F3-off, F4-off and F5(combined)-off **disappears**. The P13 differences came from validation-calibrated admission thresholds chosen on a coarse grid {0.5, 0.7, 0.85, 0.95} that left some arms with very low coverage. They do not reflect better candidate ranking.
2. **What survives matching:**
   - order information (F2): +0.067 at matched coverage;
   - B over the factorized SF: +0.083.
3. Under a **false-admission constraint** (equal error tolerance), B keeps a modest advantage over C, F4-off and F5-off (+0.05 to +0.07), but not over A or F3pm.
4. Unkeyed B-U is the highest at matched coverage (0.770, not significant vs B) **but violates catalogue invariance (0067)**.

## 3. J as the second tie-break, separated from admission

Over the same admitted set (0067):
- **Choice correctness:** J − no-J = +0.019 (3 / 0 roots; p 0.25).
- **Witnessed travel:** on the 12 roots where both picks are VERIFIED, J's pick is shorter by 0.14 normalized-joint units, but not significantly (p 0.77).
- **Verdict:** J helps a little and never hurts here; underpowered.

## 4. Factor mathematics: what the existing checkpoints can and cannot establish

| removed block | modules | tested in P13? | what P14 can say |
|---|---|---|---|
| F3 | `pair_scene` (z₀–z_S) | yes (B-F3pm) | no benefit at matched coverage (−0.013) |
| F4 | `pair_omit` | yes (B-F4) | no benefit at matched coverage (−0.003); small benefit under the false-admission constraint |
| **combined F5** | `cpl` **and** `ho_u` / `ho_s` / `ho_q` | yes (B-F5spm) | no executed benefit at matched coverage; +0.175 nats challenge NLL; −1.14 natural |
| HO only | `ho_*` | yes (B-F5qpm) | +0.06 on triple joint likelihood only |
| **generic `cpl` only** (scene–scene, scene–query, omit–omit) with HO kept | `cpl` | **no** | **not establishable without a fresh matched 3-seed retrain** |
| scene unary | `scene` | not ablatable without breaking the model | — |

A generic-only ablation needs a new arm with `cpl` removed and `ho_*` kept, plus a parameter-matched control. It is **not** run here: it belongs to the conditional confirmatory cohort and is gated in §5.

## 5. Repair cohort (natural-mix calibration of a lean B): status

The contract authorizes a fresh training / validation / test cohort with separate caps (training 18,000, teacher 18,000, execution 12,000 CPU-s) **only after the pilot gate**. The proposed design (to be preregistered only if the gate passes):
- training data: P13 train + new natural-like roots with ~50 % feasible originals;
- three predefined settings, 3 seeds each: full B, lean B (no F3 and no HO), and no-coupling B;
- validation-only temperature + bias calibration;
- new held-out natural-like and mechanism-disjoint test roots, frozen before labels;
- primary criterion: feasible-original recall and unnecessary-relocation rate must not get worse, while natural joint / individual fit improves.

Until it runs, **every A1 statement above is exploratory and P13's test roots are not reclassified as new confirmation.**
