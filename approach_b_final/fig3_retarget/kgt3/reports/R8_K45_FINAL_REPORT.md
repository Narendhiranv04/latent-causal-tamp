# R8C: 3D recursive (Fig. 3A) and global (Fig. 3B) composition on the sealed independent cohort

**Cohort.** The 99 sealed R8B roots (68 with L_ref 4, 31 with L_ref 5); see `R8_K45_DATASET_REPORT.md`.

**Configuration.** The R6 3D configuration, frozen before any outcome. The only change is the clean R7 models (`R7_FREEZE.md`):
- raw X, S0 selection;
- admission A1 with m = 0.10;
- GA with S1 top-4 proposals; REC with ANC64 proposals;
- exact / bounded GA, has_multi;
- H = 5;
- **180 s deadline including floor and selection**.

The floor uses the final model. B0 stays the production model.

**Protocol.**
- One sealed plan per root and method, with no retries.
- Verification: X_CHUNKED + endpoint Y + continuous replay.
- Unresolved outcomes count as *not verified*, never as certified failures.
- Shorter valid repairs count as successes and are reported separately.

**Runs.** 449 physical jobs (main) and 194 (control), both COMPLETE; 4.8 + 2.0 CPU-h. Generators were drained, so the timed arms ran on clean CPUs.

## Main result (compact table: Original / Recursive / Global)

| Method | Verified success | Wilson 95% |
|---|---|---|
| Original final model, H ≤ 3 (H3) | 23/99 | 16.0–32.5% |
| **Recursive, Fig. 3A (REC, H ≤ 5)** | **59/99** | 49.7–68.7% |
| **Global, Fig. 3B (GA, H ≤ 5)** | **64/99** | 54.8–73.4% |

Either REC or GA succeeds on **77/99** roots.

## Full table

| Method | Success | Long (4–5) successes | Shorter than L_ref | L_ref 4 | L_ref 5 | Plan s mean / median / p90 | Deadline stops |
|---|---|---|---|---|---|---|---|
| B0 production (H ≤ 3) | 8/99 | 0 | 8 | 7/68 | 1/31 | 0.2 / 0.2 / 0.5 | 0 |
| H3 final model (H ≤ 3) | 23/99 | 0 | 23 | 19/68 | 4/31 | 0.2 / 0.1 / 0.5 | 0 |
| Flat insertion (H ≤ 5) | 48/99 | 34 | 17 | 40/68 | 8/31 | 5.9 / 4.8 / 12.0 | 0 |
| **REC (Fig. 3A)** | **59/99** | 47 | 14 | 44/68 | 15/31 | 7.8 / 6.7 / 15.0 | 0 |
| **GA (Fig. 3B)** | **64/99** | 60 | 6 | 51/68 | 13/31 | 83.8 / 80.2 / 175.0 | 20 |
| REC, original-data-only GNN X | 14/99 | 9 | 6 | 12/68 | 2/31 | 8.3 / 7.0 / 15.9 | 0 |
| GA, original-data-only GNN X | 8/99 | 7 | 1 | 6/68 | 2/31 | 84.9 / 82.2 / 175.0 | 20 |

**Paired comparisons** (two-sided sign test):

| Comparison | Wins – losses | p |
|---|---|---|
| REC vs H3 | 38 – 2 | 1.5e-9 |
| GA vs H3 | 45 – 4 | 8.2e-10 |
| GA vs FLAT | 29 – 13 | .02 |
| REC vs FLAT | 25 – 14 | .11 |
| REC vs GA | 13 – 18 | .47 |
| H3 vs B0 | 18 – 3 | .0015 |

**Unverified outcomes per arm** (BUDGET_NO_PLAN / OPERATIONAL_FAILURE / CERTIFIED_INFEASIBLE counted over each arm's jobs):

| Arm | BUDGET_NO_PLAN | OPERATIONAL_FAILURE | CERTIFIED_INFEASIBLE |
|---|---|---|---|
| REC | 14 | 4 | 14 |
| GA | 8 | 5 | 14 |
| FLAT | 18 | 2 | 12 |

## Readings (supported by this cohort; no causal or universality claim)

1. **Composition beyond three actions is demonstrated on independent roots.**
   - REC and GA verify 4–5-action repairs on 47 and 60 roots respectively.
   - The K ≤ 3 model alone solves 23 roots, all with ≤ 3 actions, shorter than L_ref.
2. **Global (GA) and recursive (REC) are statistically indistinguishable here** (13 vs 18 discordant wins).
   - GA is better on L_ref 4 (51 vs 44); REC is better on L_ref 5 (15 vs 13).
   - GA costs about 10× the planning time and hit the 180 s deadline on 20/99 roots.
3. **Strict local supervision is necessary for composition.** With the same seed, base and cVAE, but the X head trained on original data only, success falls to 14 (REC) and 8 (GA).
4. **Planners rarely reproduce the reference repair.** Mean witness-action recall is 0.13 (REC) and 0.20 (GA). Successes are mostly *different* valid repairs, which matters because L_ref is not a certified minimum.

**Visual evidence** (`reports/final/gifs/`): actual MuJoCo re-executions of the stored teacher witnesses of the sealed plans, not re-planned.
- REC and GA verified 4- and 5-action successes;
- one failure each (ending on a captioned still);
- one root where REC and GA both verify different 5-action plans, with FLAT and H3 shown on the same root.

**Development check** (20 exposed DEV roots, never pooled): B0 2, H3 4, FLAT 9, REC 14, GA 10. Figure: `reports/final/figures/d_composition3d.png`.
