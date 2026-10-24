# 0055 — P12-4: prospective F3 / F5 tests on the novel holdout

**Actual result.**
- **Gate:** `runs/p12/P12_4_GATE.json`.
- **Neither primary hypothesis is confirmed. F3 is significantly reversed:** the retrained model *without* the scene-pair factor predicts κ better than full keyed B on the novel families.
- **Absolute adequacy** of κ prediction is poor for every arm.

## 1. Primary tests (preregistered; 65 proof-grounded roots; Holm over 2)

Δ = |κ̂_ablation − κ| − |κ̂_B − κ| per root, seed-mean marginals; positive means full B is better.

| test | mean Δ | 95 % CI | full B / ablation better (ties) | raw p (two-sided sign) | Holm p | effect size d | status |
|---|---|---|---|---|---|---|---|
| **F3**: B vs B-F3 | **−0.0735** | [−0.112, −0.032] | 21 / 44 (0) | 0.0059 | **0.0118** | −0.44 | **NOT_CONFIRMED (significant reversal)** |
| **F5**: B vs B-F5s | −0.0266 | [−0.109, +0.058] | 30 / 35 (0) | 0.620 | 0.620 | −0.08 | NOT_CONFIRMED |

**Per-family mean Δ:**
- F3: X −0.062, Y −0.082.
- F5s: X **+0.175**, Y **−0.170**. The F5s effect is strongly family-dependent.

**Per-seed full-B-better root counts:**
- F3: 35 / 26 / 16 (of 65);
- F5s: 23 / 38 / 30.

## 2. Absolute predictive adequacy (same 65 roots)

| arm | mean \|κ̂ − κ\| | four-bit scene NLL |
|---|---|---|
| SF | **0.219** | 0.994 |
| B-F5q | 0.272 | 0.552 |
| B-F3 | 0.331 | 0.439 |
| B-F5s | 0.377 | 0.802 |
| **keyed B** | 0.404 | 0.482 |
| C | 0.406 | 0.509 |
| B-U | 0.418 | **0.433** |
| A | 0.421 | 0.834 |
| B-V0 | 0.673 | 0.632 |

**By κ class** (descriptive):

| class | B | B-F3 | B-F5s | SF |
|---|---|---|---|---|
| κ = +1 (4 roots) | **0.81** | 0.94 | 1.47 | 0.82 |
| κ = 0 (59 roots) | 0.377 | 0.288 | 0.314 | 0.179 |
| κ = −1 (2 roots) | 0.40 | 0.36 | 0.08 | 0.22 |

**Reading.**
- On the no-interaction roots that dominate the novel cohort, the joint coupling in B **creates spurious interaction** (κ̂ ≠ 0). Removing F3, or the HO residual (F5q), reduces that error.
- On the four genuinely complementary roots, full B has the lowest error, consistent with P10's direction, but it is still far from correct (κ̂ ≈ 0.2 against κ = 1). With n = 4 this is descriptive only.
- **Conclusion:** the factors' complexity is not justified by prospective κ accuracy on these families.

## 3. Secondary ablations (same metric; Holm across the secondary family)

| arm | mean Δ | 95 % CI | raw p | Holm (secondary) | reading |
|---|---|---|---|---|---|
| B-F5q (HO only) | −0.132 | [−0.184, −0.078] | 1.6e-5 | 1e-4 | removing HO **helps** |
| SF | −0.185 | [−0.238, −0.136] | 1.2e-8 | < 1e-6 | factorized SF better than B |
| B-V0 | +0.269 | [0.184, 0.348] | 6e-8 | < 1e-6 | DINOv2 helps |
| B-F4 | +0.053 | [0.011, 0.098] | 0.082 | 0.41 | n.s. |
| B-F2 | +0.008 | — | 1.0 | — | n.s. |
| B-U | +0.014 | — | 0.62 | — | n.s. |
| C | +0.002 | — | 0.62 | — | n.s. |
| A | +0.017 | — | 0.80 | — | n.s. |

**Capacity:** the ablations have fewer parameters (−49k to −132k), so lower complexity coincides with better κ accuracy here.

**Order and omission endpoints (secondary; `ORDER_OMISSION.json`).**

*Order:* 206 decided same-endpoint reversed-order pairs exist (110 proof-grounded); 18 roots have proof-grounded pairs scored by every arm.

| arm | accuracy | mean margin |
|---|---|---|
| A | **0.983** | 0.45 |
| B-U | 0.958 | — |
| B-F3 / B-F4 | 0.932 | — |
| keyed B | 0.916 | 0.126 |
| keyed C | 0.887 | 0.201 |
| SF | 0.598 | — |
| **B-F2 (order-invariant)** | **0.459** | — |

| contrast | difference | 95 % CI | roots a / b better | sign p |
|---|---|---|---|---|
| B − F2 | +0.458 | — | 18 / 0 | — |
| B − A | **−0.067** | [−0.104, −0.030] | 1 / 12 | 0.003 |
| C − B, accuracy | −0.029 | — | — | 0.77 (n.s.) |
| C − B, margin | +0.075 | [0.027, 0.119] | — | 0.031 |

*Omission necessity:* 76 roots, 1,470 decided omissions. All arms sit at 0.56–0.69: B 0.675, SF 0.679, A 0.652, C 0.564. B − SF −0.003 (n.s.); B − F4 +0.013 (n.s.).

**Reading.** The order factor remains necessary (F2 collapses), but A, not B, chooses order best on the novel families. Omission prediction is weak for every arm.

**Artifacts:** `runs/p12/p12_4/FACTOR_TESTS.json`, `visualizations/p12/P12_factor_ablation.png`.
