# 0063 — P13-4: blind physical labels and factor utility (preregistered tests)

**Previous turn sync:**
- freeze `c9756294beed243b16210fde29519de5eb7db395`: predictions, models, execution plan and addendum, pushed before any blind label;
- label hash commit `4da8ca297072bda01a21a131d047c01f8472d8f9`: 170 sealed root files, pushed before `UNSEALED`.

**Actual result.**
- **Gate:** `runs/p13/P13_4_GATE.json` → **PASS** (engineering).
- **Blind labels:** 170 roots, 1,282 queries, none missing. Statuses: 539 VERIFIED, 548 CERTIFIED, 109 BUDGET (operational), 63 UNKNOWN, 23 NOT_RUN. Teacher total 59,278 / 65,000 CPU-s.
- **Two natural batches hit the 4,000 CPU-s job cap.** They resumed within the remaining budget; the one query interrupted at the cap is NOT_RUN and was never repeated.
- **Preregistered primaries** (blind challenge set; Holm over 4; positive Δ = full keyed B better):

| test | contrast | cohort | mean Δ | 95 % CI | B / off better (ties) | raw p | Holm p | min. effect | safety harm | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **H_F2** | B vs B-F2 (order accuracy) | 34 roots / 39 pairs | **+0.779** | [0.647, 0.897] | 28 / 0 (6) | 7.5e-9 | **3e-8** | 0.10 | none (natural: 2 roots, n.s.) | **SUPPORTED_CONDITIONAL** |
| **H_F5** | B vs B-F5spm (joint four-bit log-loss) | 62 four-tuples | **+0.175** | [0.115, 0.245] | 52 / 10 | 5.7e-8 | **1.7e-7** | 0.05 | **natural joint log-loss −1.14** [−1.53, −0.73], p 1e-4 | **NOT SUPPORTED** (challenge-only benefit; natural-mix harm) |
| **H_F4** | B vs B-F4 (omission log-loss) | 60 roots / 262 omissions | +0.014 | [0.005, 0.025] | 42 / 18 | 0.0027 | 0.0053 | 0.05 | natural omission log-loss −0.61 [−0.86, −0.40], p < 1e-4 | **NO_DEMONSTRATED_BENEFIT** (below the minimal effect; natural harm) |
| **H_F3** | B vs B-F3pm (joint four-bit log-loss) | 62 four-tuples | −0.023 | [−0.064, 0.015] | 22 / 40 | 0.030 | 0.030 | 0.05 | κ = +1 error −0.010, p 0.035 | **HARMFUL** by the rule (sign-test reversal); practically negligible |

**The cohorts are exactly the preregistered ones:**
- **four-tuples:** 62 on the challenge set (κ: +1 = 33, 0 = 17, −1 = 12) and 29 natural (κ 0 = 28, −1 = 1; 24 of these are feasible originals, pattern 1111);
- **order:** 39 reversed-order pairs on 36 roots;
- **omissions:** 262, of which 82 necessary and 180 optional, on 92 roots;
- **triples:** 21 complete lattices (Δ = +1: 11, Δ = 0: 10).

## 1. Absolute performance (seed-mean marginals; challenge / natural)

| arm | joint four-bit log-loss | κ MAE | order accuracy | omission log-loss | triple Δ error | triple joint 8-bit |
|---|---|---|---|---|---|---|
| **K-B** | 0.157 / 2.54 | 0.103 / 0.435 | 1.00 / 1.00 | **0.026** / 1.05 | 0.076 | 0.147 |
| K-C | 0.163 / 2.46 | 0.101 / 0.437 | 1.00 / 1.00 | 0.028 / 0.96 | **0.024** | **0.050** |
| B-F3pm | **0.135** / 2.46 | 0.091 / 0.435 | 1.00 / 1.00 | 0.035 / 1.13 | 0.055 | 0.086 |
| B-F5spm | 0.332 / 1.40 | 0.192 / 0.297 | 1.00 / 0.50 | 0.038 / 0.38 | 0.251 | 0.495 |
| B-F5qpm | 0.164 / 2.13 | 0.094 / 0.398 | 1.00 / 0.50 | 0.055 / 0.50 | 0.093 | 0.207 |
| B-F2 | 0.178 / 1.92 | 0.105 / 0.438 | **0.22** / 0.50 | 0.068 / 1.03 | 0.071 | 0.120 |
| B-F4 | 0.254 / 1.52 | 0.145 / 0.378 | 1.00 / 0.50 | 0.040 / 0.44 | 0.136 | 0.385 |
| B-U | **0.125** / 1.53 | **0.081** / 0.345 | 1.00 / 0.00 | 0.036 / 0.58 | 0.080 | 0.109 |
| B-V0 | 0.351 / 3.66 | 0.171 / 0.611 | 1.00 / 1.00 | 0.145 / 1.28 | 0.128 | 0.179 |
| B-F5s (1 seed) | 0.252 / **0.85** | 0.136 / 0.190 | 0.99 / 1.00 | 0.039 / **0.31** | 0.169 | 0.242 |
| A | 0.437 / 1.68 | 0.262 / 0.260 | 1.00 / 0.50 | 0.056 / 0.71 | 0.177 | 0.390 |
| SF | 0.318 / 2.08 | 0.180 / 0.345 | 0.65 / 0.50 | 0.075 / 0.73 | 0.195 | 0.416 |
| constant κ̂ = 0 | — | 0.726 / **0.034** | — | — | — | — |

**On the mechanism challenge set, every B-family model is accurate:**
- κ MAE ≈ 0.10 against 0.73 for the constant-zero control;
- the false-interaction rate on κ = 0 roots is 0 for B (B-V0 0.35, plain B-F3 0.12);
- order accuracy is 1.00 for every model with order information.

**On the natural mix, every coupled model is badly miscalibrated:**
- B's joint log-loss is 2.54 nats, the plain no-coupling B-F5s 0.85, and the constant κ̂ = 0 control is best on κ;
- the natural cohort is mostly feasible originals (pattern 1111), which the mechanism-heavy training data rarely shows.

## 2. Secondary endpoints (challenge; Holm within the secondary family; natural replication)

| contrast (B vs …) | challenge Δ (CI) | Holm (secondary) | natural Δ (CI) |
|---|---|---|---|
| vision B-V0 (joint4) | **+0.194** [0.070, 0.319] | 0.041 | **+1.12** [0.37, 1.72] |
| keying B-U (joint4) | **−0.032** [−0.054, −0.003] | < 1e-4 | **−1.00** [−1.33, −0.71] |
| F5q (HO), parameter-matched, triple joint 8-bit | **+0.060** [0.040, 0.080] | 0.022 | — |
| F5q (HO), parameter-matched, triple Δ error | +0.018 [−0.003, 0.037] | 1.0 | — |
| F5q (HO), parameter-matched, joint4 | +0.007 [−0.018, 0.034] | 1.0 | −0.41 [−0.84, −0.09] |
| F5s, parameter-matched, triple joint 8-bit | **+0.348** [0.223, 0.492] | < 1e-4 | — |
| F5s, parameter-matched, κ MAE | **+0.090** [0.059, 0.123] | 1e-4 | −0.14 [−0.20, −0.08] |
| F3, parameter-matched, triple joint 8-bit | **−0.062** [−0.098, −0.029] | 0.022 | — |
| F3, parameter-matched, κ MAE | −0.012 [−0.032, 0.006] | 0.57 | 0.000 |
| plain B-F3 / B-F5s / B-F5q (1 seed), joint4 | +0.046 / +0.095 / +0.016 | n.s. | −0.57 / −1.69 / −1.44 |
| A (joint4) | +0.280 [0.211, 0.357] | < 1e-4 | −0.86 [−1.26, −0.47] |
| SF (joint4) | +0.161 [0.112, 0.220] | < 1e-4 | −0.46 [−0.82, −0.18] |
| SF (order) | +0.353 [0.206, 0.500] | 0.008 | — |
| C (joint4) | +0.006 [−0.040, 0.055] | 0.086 | −0.08 |
| constant 0 (κ MAE) | +0.623 [0.505, 0.738] | 0.008 | **−0.40** [−0.48, −0.33] |

**F1 static validity** (676 held-out analytic static checks, 338 invalid; `F1_J.json`):
- **Discrimination:** AUROC is 0.53–0.57 for *every* model, and 0.50 for B-F1off.
- **Calibration:** B log-loss 0.84 vs B-F1off 4.78 (Δ +3.93, p 3e-51).
- **Deployment:** the analytic veto fired on 0 candidates, and the energy key, F1's only TOP1 path, was reached 0 times.
- **Reading:** F1 makes the static head *calibrated* but does **not** discriminate valid from invalid placements on held-out roots. On this lattice, validity just means the destination cell is free, and no near-valid case exists.

**J travel** (admitted, VERIFIED, minimum-move alternatives with witnessed travel; only **15** B roots):

| choice rule | relative travel regret |
|---|---|
| J | 0.210 |
| shuffled J | 0.236 |
| no J | 0.301 |

- **No J − J:** +0.091 [−0.029, 0.252], p 0.77.
- **Success:** J vs no J −0.019 [−0.041, 0.000], p 0.25.
- **Verdict:** UNDERPOWERED. The direction favours J (B-F5spm: 0.071 vs 0.303), but there are too few roots.

## 3. Reading

- **Order information (F2)** is necessary: without it, order accuracy collapses from 1.00 to 0.22. A (GRU) and C are equally perfect, so *some* order representation is required; B's specific predecessor design is not superior to a GRU.
- **The joint coupling (F5)** carries real interaction information: joint log-loss, κ MAE and triple lattices all improve. But on the realistic natural mix the same coupling is much worse. The benefit is **conditional on mechanism-like data** and does not survive the preregistered natural-mix safety rule.
- **F3** (the z₀–z_S scene pair) is not useful. Parameter-matched removal is slightly *better* on joint log-loss and on triples. This replicates P12's reversal.
- **F4** gives a statistically real but practically tiny gain on challenge omissions (0.014 nats) and a large natural-mix loss.
- **The higher-order residual** helps triple joint likelihood (+0.06 nats, secondary) but not Δ error or pair endpoints.
- **DINOv2 vision** helps on both streams. **Keying** does not help: unkeyed B-U is better on both streams.

**Limitation:** the challenge set is a mechanism-conditioned case-control (κ follows the family). Its effects measure what the models learned from matching mechanisms, not population accuracy. The natural stream is small (29 four-tuples, 2 order roots, 13 infeasible D lattices) and dominated by feasible originals.
