# FIG3B — global assignment first, then variable ordered-chunk composition (GA)

**Status:**
- **Implemented and unit-tested.** Audited for privileged inputs (P0).
- **Run model-only** on the exposed DEV panels.
- **Not physically deployed.** P2 was DATA_LIMITED in both domains.
- **No deployable K > 3 success claim is made.**

## Implementation (`../planners.py` `ga`, `../compose.py`)

1. **Initial pool.** Proposals come from the released task-conditioned cVAE (rule S1, D4). Complete legal assignments of sizes 1..H (H = 6 in 2D, 5 in 3D) are formed with distinct objects and destinations, none reusing an initially occupied cell or the goal. Primary GA uses no retargeting, witness or recursive union.
2. **EXACT vs BOUNDED,** fixed per root by the declared envelope:
   - **EXACT** when every size satisfies e_k ≤ 150,000 and the request estimate is ≤ 1.2 M. Then every complete assignment is streamed, gets Y_global once, and gets the grouped subset DP.
   - **BOUNDED** otherwise. Each size enumerates if e_k ≤ 150,000, else extends the retained size k−1 sets. It keeps ≤ 256 per size: 96 by top Y_global, 96 by the lowest first ordered-pair X energy at S0, and 64 object-set-diverse. Counts and truncation are logged.
3. **Grouped subset DP** (`compose.grouped_dp`). State (U, has_multi). At each step choose an unordered chunk B ⊆ A \ U of size 1–3 and batch-score its 1, 2 or 6 internal permutations in the canonical scene after U. Only the best permutation propagates; scores are cached by (placed set, ordered chunk).
   - Energy: sum of −log marginal pX, plus −log Y_global at the complete endpoint. No intermediate Y gate; λ = 0.
   - Tested exact against brute force and against the historical `order.dp`; no m! materialisation.
4. **Selection.** Same rule as Fig. 3A, including the K ≤ 3 production floor.
5. **GA-YONLY control.** The historical Y-only top-4 per size over the same candidate domain, then the same DP.

## Model-only accounting (exposed DEV panels; predictions NOT verified)

| | 2D (30, frozen F0) | 3D (20, M1ft O2 s0) |
|---|---|---|
| Mode | **BOUNDED on 30/30** (dense N 14–20 → e_k far above the envelope) | **EXACT on 14/20**, BOUNDED on 6/20 |
| Unique X scores per root (median) | 0.30 M | 0.07 M |
| Wall time, median / max (cap 180 s) | 49.9 / 75.3 s | 19.0 / 110.2 s |
| Selected length > 3 / multi-action chunk | 25 / 29 (production floor on 1) | 18 / 20 |
| **Witness assignment inside the initial D4 pool** (evaluator only) | **0 / 30** | **2 / 20** |
| Witness assignment DP-optimized (retained) | 0 / 30 | 1 / 20 |
| Selected = witness assignment | 0 / 30 | 0 / 20 |
| GA-YONLY: selected length > 3 | 24 / 30 | 11 / 20 |

## What this does and does not show

- **Exact enumeration works where the pool is small.** In 3D, complete exhaustive enumeration with the exact learned-energy DP finished on 14 of 20 roots within 180 s. The Y-only top-4 bottleneck is removed from the primary method.
  - Exactness holds for the learned energy over the declared pool only, never for physical feasibility or minimality.
- **Proposal coverage, not retention, binds first in this regime.** The witness assignment lies in the initial D4 pool on **0/30** 2D roots and **2/20** 3D roots (R2.4 reported 2/20 for 3D). So GA over the initial pool cannot rediscover the known long repairs on these panels, whatever the X model or retention policy.
  - Other valid assignments may exist; coverage of the witness set is a diagnostic, not proof of infeasibility.
  - A refreshed or recursive proposal union (GA-UNION) is the only route to wider coverage under the frozen sampler. It is a separately labelled hybrid and was not run here.
- **No physical evidence.** There is no physical GA result and no GA vs GA-YONLY claim.

## Figure

`figures/KGT3_P4_planners.png`, panel (c): the assignment funnel.
