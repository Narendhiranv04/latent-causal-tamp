# 0043 — P10d: blind predictions and physically executed TOP1 on 65 sealed 2D roots

**Actual result.**
- **Protocol:** predictions, calibration and selection rules were frozen and pushed (`162338e`, snapshot `sha256:52a2d278…`) before unsealing. Blind outcomes were then scored offline, and every arm's single TOP1 choice was physically executed once with no fallback: **255 distinct episodes covering 975 arm × seed choices**.
- **Two of the four Holm-corrected primaries are confirmed for keyed B:**
  - **P1, executed TOP1 success:** B **71.8 %** vs SF **38.5 %** (+33 points [23, 44], Holm p = 8e-6). Also +13 points vs A and +27 vs geometry-only.
  - **P2, H1 complementarity κ error:** B 0.014 vs A 0.277 (Holm p = 0.012; 9 / 9 roots).
- **Not confirmed:**
  - **P3, order:** every main arm is at ceiling, so C = B.
  - **P4, omission:** B 0.93 vs SF 0.90, Holm p = 0.60.
- **C vs B:** C never beats B. Execution success is identical, and per-root NLL is slightly worse for C.
- **Planner-assisted G+M** (83.1 %) still beats B (−11 points [−24, +2]; better on 24 roots vs 8), at the cost of planner calls on up to 5 candidates.

Gates: `runs/p10d/P10D_GATE.json` PASS; P10c gate `runs/p10c/P10C_GATE.json` PASS. All numbers are in `runs/p10d/BLIND_EVAL.json` and `runs/p10d/P1_TOP1.json`.

## 1. Blind set

- **Roots:** 65 independent sealed roots.

  | family | roots |
  |---|---|
  | H1 | 9 |
  | H2a | 5 |
  | H2b | 4 |
  | H3 | 9 |
  | H4 | 7 |
  | H5 | 5 |
  | H7 | 4 |
  | H8 | 4 |
  | H10_3 | 9 |
  | H10_4 | 9 |

- **Outcomes:** 771 adjudicated queries: 211 VERIFIED, 415 CERTIFIED, 125 BUDGET, 20 UNKNOWN.
- **Per-arm values:** the seed mean per root; CIs are paired root-cluster bootstrap (2,000 resamples); p-values are exact sign tests on roots.

## 2. P1 — strict TOP1_COMMIT executed success (primary)

| arm | success | mean CPU / episode (s) | moves on success |
|---|---|---|---|
| **keyed B** | **0.718** | 20.0 | 1.99 |
| **keyed C** | **0.718** | 21.6 | 1.97 |
| A | 0.585 | 20.6 | 1.86 |
| SF | 0.385 | 20.0 | 1.20 |
| geometry-only (analytic, no IK) | 0.446 | 13.7 | 1.34 |
| uniform | 0.338 | 9.0 | 1.68 |
| G+M (planner-assisted, ≤ 5 candidates) | 0.831 | 15.7 | 1.89 |

**Contrasts:**

| contrast | difference | 95 % CI | roots a better / b better | p |
|---|---|---|---|---|
| B − SF | **+0.333** | [0.226, 0.441] | 32 / 4 | 2e-6 (Holm 8e-6) |
| B − A | +0.133 | [0.077, 0.195] | 18 / 1 | 1e-4 |
| B − geometry | +0.272 | [0.128, 0.405] | 28 / 8 | 0.001 |
| B − uniform | +0.379 | [0.241, 0.508] | 32 / 7 | 1e-4 |
| C − B | 0.000 | [−0.041, 0.041] | 6 / 6 | — |
| B − G+M | −0.113 | [−0.236, 0.021] | 8 / 24 | 0.007 |

- **Episode outcomes:** 147 SUCCESS, 58 NO_REPAIR_WITNESS_WITHIN_BUDGET, 33 TARGET_CERTIFIED_INFEASIBLE, 8 TARGET_UNRESOLVED, 9 UNRESOLVED_CENSORED (180 CPU-s episode cap).
- **Abstentions (count as failures):** SF 89, A 59, B 30, C 26 out of 195 choices each.

**By family and length** (seed-mean success; `runs/p10d/P1_BY_FAMILY.json`):

| | B | C | A | SF | geometry | G+M |
|---|---|---|---|---|---|---|
| 1–2-move families | 0.745 | 0.752 | 0.660 | 0.532 | 0.617 | 0.809 |
| H10_3 (3 moves) | **0.519** | 0.481 | 0.037 | 0.000 | 0.000 | 0.889 |
| H10_4 (4 moves) | **0.778** | 0.778 | 0.741 | 0.000 | 0.000 | 0.889 |
| H1 complementarity | 1.00 | 1.00 | 1.00 | 0.52 | 0.56 | 0.44 |
| H3 order | 0.67 | 0.74 | 0.44 | 0.07 | 0.00 | 0.89 |
| H7 edit vs executable | **0.00** | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |

- **H7 is a failure mode of every learned arm.** All learned arms abstain on all 4 H7 roots; their predictions for the alternative destination M* stay below the admission threshold. Geometry-only and G+M succeed on 4 / 4.
- **Length.** Executed success **does not collapse with length for B / C**: 0.75 → 0.52 (3 moves) → 0.78 (4 moves). It does collapse for SF and geometry (0) and for A on 3-move roots (0.04).

## 3. Mechanism endpoints on blind outcomes (prediction only)

| endpoint | B | C | A | SF | primary contrast |
|---|---|---|---|---|---|
| **H1** \|κ̂ − κ\| (9 proof-grounded roots) | **0.014** | 0.057 | 0.277 | 0.312 | B − A: +0.262 [0.224, 0.307], 9 / 0 roots, Holm p 0.012 |
| **Order** (26 roots: H3 + H10 permutations) | 1.000 | 1.000 | 1.000 | 0.987 | C − B: 0.000 (ceiling) |
| **Omission necessity** (52 roots) | 0.929 | 0.926 | 0.926 | 0.897 | B − SF: +0.032 [−0.003, 0.067], Holm p 0.60 |
| Per-root NLL (65 roots, lower better) | **0.234** | 0.269 | 0.281 | 0.367 | B − A: −0.047 [−0.082, −0.016]; B − SF: −0.133 [−0.179, −0.087] |

**Common per-event metrics** (589 decided blind outcomes modelled by A / B / C / SF, × 3 seeds = 1,767 rows):

| arm | accuracy | AUROC | NLL | ECE |
|---|---|---|---|---|
| B | 0.909 | 0.972 | 0.211 | 0.035 |
| C | 0.894 | 0.960 | 0.239 | 0.030 |
| A | 0.887 | 0.955 | 0.259 | 0.041 |
| SF | 0.852 | 0.917 | 0.344 | 0.040 |

**Length extrapolation** (trained on ≤ 2-move data only, scored on blind 3- / 4-move H10 roots):

| arm | omission | order | NLL |
|---|---|---|---|
| B | **1.00** | **1.00** | 0.48 |
| C | 1.00 | 0.83 | 0.64 |
| A | 0.67 | 0.83 | **0.42** |
| SF | 0.77 | 0.76 | 0.54 |

Full-data training improves every arm, with B best at NLL 0.043.

**H9 appearance.** Recolouring the observation, with identical geometry, moves predictions by a mean absolute 0.14–0.17 for every DINOv2 arm. Visual-zero moves 0 by construction. These are **not appearance-invariant** predictions.

## 4. D on blind roots

- **Masks:** 60 / 65 complete; 39 proof-grounded.

  | true blockers | roots |
  |---|---|
  | 0 | 4 |
  | 1 | 20 |
  | 2 | 18 |
  | 3 | 9 (operational H10 corridor masks) |
  | 4 | 9 (operational H10 corridor masks) |

- **Feasibility:** D predicts initial feasibility **perfectly** (64 roots: accuracy 1.0, AUROC 1.0, NLL 0.005). D-pairless NLL is 0.006. A / B / C / SF z0 reach 0.984–1.0 accuracy with NLL 0.022–0.058.
- **Blocker attribution (per-object F1, macro by root):**

  | method | F1 | exact set |
  |---|---|---|
  | D | 0.872 | 0.578 |
  | D-pairless | 0.882 | 0.667 |
  | geometry heuristic | 0.797 | 0.533 |

  - **Primary, D vs D-pairless:** −0.010 [−0.046, +0.038]. D-pairless is better on 19 roots vs 6. **The pairwise blocker term is not supported.**
  - **D vs heuristic:** +0.075 [0.007, 0.142].
  - **By number of true blockers:**

    | true blockers | D | D-pairless | heuristic |
    |---|---|---|---|
    | 1 | 0.88 | 0.78 | 0.95 |
    | 2 | 0.98 | 0.98 | 0.91 |
    | 3 | 0.80 | 0.90 | 0.50 |
    | 4 | 0.67 | 0.83 | 0.67 |

- **Faithful B / C counterfactual attribution** (supported on 33 / 60 roots, where the pool is the two edit roles with identical parking edits; 27 UNSUPPORTED):

  | method | F1 |
  |---|---|
  | D | 0.94 |
  | heuristic | 0.93 |
  | D-pairless | 0.92 |
  | B, C | 0.86 |
  | SF | 0.84 |
  | A | 0.80 |

## 5. Compute and integrity

| category | used / cap (CPU-s) | notes |
|---|---|---|
| execution | 3,346 / 15,000 | |
| teacher | 14,769 / 24,000 | |
| evaluation | 1,042 / 5,000 | |
| training | true 21,858 (17,258 confirmatory + 4,600 preliminary) | cap lifted |

- **0 physical calls** in any learned prediction.
- **Process note.** One serial episode job was stopped and replaced by four per-batch workers (one ledger per batch). Its roughly 2 minutes of CPU has no guard record, and its in-flight episode was re-run deterministically.

**Figures** (`visualizations/p10b/`):
- `P10_TOP1_executed.png`
- `P10_TOP1_executed_successes.gif`: recorded keyed-B TOP1 executions on blind 4-move, 3-move, H1 and H3 roots
- `P10_TOP1_failures.png`
- `P10_blind_endpoints.png`
- `P10_D_blind.png`
- `P10_length_extrapolation.png`
