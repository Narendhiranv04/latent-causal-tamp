# 0048 — P11-3: physically executed length extrapolation (short-trained models on 3- / 4-move roots)

**Actual result** (POST-HOC / SUPPLEMENTARY on the disclosed 65 P10b blind roots).
- **Gate:** `runs/p11/length/P11_LENGTH_GATE.json` → **PASS**.
- **Protocol:** the ≤ 2-move-trained A / B / C / SF checkpoints (3 seeds, frozen before the P10d unsealing) were physically executed under strict TOP1_COMMIT, using their **unchanged frozen choices**.
- **Episodes:** 162 distinct (root, repair) episodes. 103 are byte-identical in identity to P10d episodes and reused; **59 are new** (188 CPU-s).
- **Finding:** **execution-level length extrapolation largely fails.**
  - Short-trained B succeeds on 0.15 of 3-move and 0.22 of 4-move roots, against 0.52 / 0.78 for full-trained B. The difference on H10 roots is −0.46 [−0.63, −0.28], with 1 vs 14 roots favouring short / full.
  - The prediction-level extrapolation reported in 0043 (order / omission accuracy 1.00 for short B) therefore does **not** translate into executed long repairs.

## 1. Protocol

- **Manifest:** `runs/p11/length/LENGTH_MANIFEST.json` (`sha256:4d86bacb…`), committed (`6fdd6ca`) before any new episode. It records:
  - checkpoint hashes;
  - the unchanged frozen choices;
  - one episode per (root, repair) with the P10d seed namespace (identity verified against P10d jobs for every reused key);
  - the 180 CPU-s / 600 s cap, no fallback, SAFE_RETREAT.
- **Calibration caveat:** the frozen short-regime τ / thresholds were selected on the **full** validation set, which includes ≥ 3-move roots. As a sensitivity check, the models were recalibrated on the ≤ 2-move validation subset only (26 roots, deterministic rule, no outcome use). B's choices were identical, C changed slightly, and A became worse.
- **Minimality:** catalogue-relative.
  - H10_4: SOUND on 5 of 9 blind roots, OPERATIONAL otherwise.
  - H10_3: OPERATIONAL on all (the middle omission is a BUDGET negative).

## 2. Executed TOP1 success (seed mean per root; abstain = failure)

| arm | 1–2-move families (47 roots) | H10_3 (9) | H10_4 (9) | H10_4 SOUND (5) | all (65) |
|---|---|---|---|---|---|
| **full B** | 0.745 | **0.519** | **0.778** | 0.800 | 0.718 |
| **short B** (frozen) | 0.787 | 0.148 | 0.222 | 0.267 | 0.621 |
| full C | 0.752 | 0.481 | 0.778 | 0.800 | 0.718 |
| short C | 0.667 | 0.074 | 0.593 | 0.667 | 0.574 |
| full A | 0.660 | 0.037 | 0.741 | 0.733 | 0.585 |
| short A | 0.738 | 0.000 | 0.519 | 0.533 | 0.605 |
| full SF | 0.532 | 0.000 | 0.000 | 0.000 | 0.385 |
| short SF | 0.631 | 0.000 | 0.000 | 0.000 | 0.456 |

Short-validation recalibration: B unchanged; C 0.074 / 0.593; A 0.000 / 0.259.

**Paired contrasts on the 18 H10 roots:**

| contrast | difference | 95 % CI | roots (a / b better) | p |
|---|---|---|---|---|
| short − full, B | −0.463 | [−0.630, −0.278] | 1 / 14 | 0.001 |
| short − full, C | −0.296 | [−0.407, −0.185] | — | 0.0005 |
| short − full, A | −0.130 | [−0.204, −0.056] | — | 0.016 |
| short − full, SF | 0 | — | — | — |
| short B − short A | −0.074 | [−0.241, 0.074] | — | ns |
| short B − short C | −0.148 | [−0.296, 0.000] | — | ns |
| short B − short SF | +0.185 | [0.093, 0.296] | — | 0.008 |

**Outcome classes of short B** (195 choices): 121 SUCCESS, 34 ABSTAIN, 14 TARGET_CERTIFIED_INFEASIBLE, 12 NO_REPAIR_WITNESS, 5 TARGET_UNRESOLVED, 9 CENSORED. Most H10 failures are abstentions or shorter, infeasible choices: models never trained on 3- / 4-move repairs rarely admit them.

**Reading.**
- On 1–2-move families, short training does not hurt (short B 0.787 vs full B 0.745).
- Physically executed 3- / 4-move repairs require training data containing them. B's long-repair advantage is a **trained** capability, not a demonstrated length generalization.

**Figures** (`visualizations/p11/`; real recorded traces only):
- `P11_length_executed.png`
- `P11_short_trained_long_success.gif`: a recorded short-B 3-move success
- `P11_short_trained_long_failures.png`: committed repair and recorded outcome; no motion drawn
