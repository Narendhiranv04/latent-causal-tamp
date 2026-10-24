# 0052 — P12-0: scope, source audit and preregistration draft

**Actual result.**
- **Gate:** `runs/p12/P12_0_GATE.json` → **PASS**.
- **Repository:** HEAD = origin/main = `b5d3f85`. The only tracked changes are the user's two PDF deletions, which are never staged.
- **Frozen evidence:**
  - the frozen P10d prediction snapshot hash verifies;
  - all **33** full-regime checkpoints (A, keyed B, keyed C, SF, B-F2, B-F3, B-F4, B-F5s, B-F5q, B-V0, B-U × 3 seeds) match their stored SHA-256 and their frozen snapshot calibration (`runs/p12/p12_0/AUDIT.json`).
- **Draft preregistration:** `runs/p12/p12_0/PREREG_DRAFT.json`. The final preregistration is frozen in P12-2, before any confirmation label.

## 1. Fixed questions

**Primary (confirmatory only on a new, prediction-frozen holdout):**

| test | comparison | per-root statistic |
|---|---|---|
| **F3** | full keyed B vs retrained **B-F3** (scene pair removed) | Δ_F3 = \|κ̂_{B-F3} − κ\| − \|κ̂_B − κ\|; positive = full B better |
| **F5** | full keyed B vs retrained **B-F5s** (generic coupling *plus* higher-order removed together) | same statistic |

- **κ̂:** the same combination of frozen, seed-mean model marginals as κ.
- **What F5 tests:** the combined factor block. B-F5q (HO only) is secondary.
- **Statistics:** exact two-sided sign test with ties removed. Holm over these **two** tests only, α = 0.05. Paired root-cluster bootstrap 95 % CI.
- **Cohort:** every new root whose four fixed-q0 edit outcomes (original, A, B, A+B) are all VERIFIED or CERTIFIED, **whatever κ turns out to be**. κ class is reported, never used to include or exclude a root.
- **Narrow family:** the two-test Holm family is legitimate only for the new frozen holdout. It is not applied retroactively to the P11 nine-root data.

**Secondary (declared):**
- B-F5q, B-F2, B-F4, B-V0, B-U, A, C and SF on the same metric (exploratory family, Holm-adjusted);
- scene binary NLL and calibration;
- same-endpoint order choice and margin;
- omission necessity on verified full repairs;
- strict TOP1 executed success (A / B / C / SF / geometry), with G+M reported as a separate planner-assisted protocol;
- D feasibility and blockers on complete, physically identical masks.

## 2. Power / sensitivity (planning only; source = disclosed P11 data, POST-HOC)

| per-root deltas from P11 (9 roots) | values |
|---|---|
| B-F3 | 0.034, 0.371, 0.003, 0.090, 0.132, 0.368, 0.198, 0.010, 0.079 (all positive) |
| B-F5s | 0.079, 0.116, 0.141, 0.066, 0.089, 0.170, 0.074, 0.095, 0.060 (all positive) |

Power of the sign test at the first Holm level (0.025):

| scenario | N = 16 | N = 24 | N = 32 | N = 40 |
|---|---|---|---|---|
| observed effects (bootstrapped) | 1.00 | 1.00 | 1.00 | 1.00 |
| pessimistic: effects halved, 25 % of roots reversed | 0.68 | 0.87–0.88 | 0.94–0.95 | 0.98 |

- **Target:** ≥ 24 proof-grounded four-tuples, aiming for ≥ 32, within ≤ 80 new roots in batches of ≤ 20.
- **Minimal meaningful effect:** mean κ-error reduction ≥ 0.05 with a majority of roots favouring full B.
- **Stopping:** fixed roster and budget only, never on p-values.

## 3. Frozen models

| arm | params |
|---|---|
| keyed B | 698,154 |
| B-F3 | 648,745 |
| B-F5s | 566,183 |
| B-F5q | 615,592 |
| B-F2 | 599,338 |
| B-F4 | 648,745 |
| C | 714,922 |
| A | 450,596 |
| SF | 351,396 |

- **Capacity confound:** the ablations have fewer parameters than B. This is recorded as a limitation, not adjusted.
- **Calibration:** the P10d snapshot τ / threshold per checkpoint, used unchanged. There is no retraining or recalibration on P12 data.
- **D:** λ_B = 2.0 for both D variants; thresholds 0.3 (D) and 0.4 (D-pairless).
