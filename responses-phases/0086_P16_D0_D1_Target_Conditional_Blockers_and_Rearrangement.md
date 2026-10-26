# 0086 — P16-D0/D1: target-conditional blockers, label semantics and the scene-only rearrangement system

**Scope.** This report covers D's mathematics, the label-semantics correction, temporary-target validation, retraining, and the completed non-learned optimiser. Prospective comparisons are in 0088.

## 1. The learned method (`d_blockers.ModelD`, checked against the source)

- **Feasibility head:** P_φ(y0 = 1 | S, T, g, q) = σ(u_φ), where u = feas(pool-token summary, target token, context).
- **Pairless blocker distribution (default, `pair=False`):**
  P_φ(b | S, T, g, q, y0 = 0) = exp(Σ_i a_i b_i) / Π_i (1 + e^{a_i}).
  This is exactly independent Bernoullis σ(a_i) (test `test_d_pairless_conditional_vs_gated_marginals`). **No inter-blocker coupling is claimed.**
- **Paired control (frozen P13 D):** adds ½ Σ_{i,j} w_ij b_i b_j, with w symmetric and a zero diagonal, and exact enumeration over 2^|M| states with |M| ≤ 6 (`blocker_logp`). The test shows the pair term changes the marginals.
- **Loss:** BCE(σ(u), y0) + λ_B · 1[y0 = 0, mask defined, proof-grounded] · (−log P_φ(b | y0 = 0)), with λ_B = 2.0 (the P13 pairless choice).
- **Inference** reports both quantities separately (`d_blockers.predict`):
  - the conditional marginal P(b_i = 1 | y0 = 0);
  - the feasibility-gated (1 − P(y0 = 1)) · P(b_i = 1 | y0 = 0), which the search guide uses as its score.

## 2. Label semantics (corrected in P16; tests `test_d_*`)

| lattice outcome (`d_blockers.minimal_sets` on the scene-only lattice) | P13 training | **P16 training** |
|---|---|---|
| FEASIBLE_ORIGINAL | y0 = 1, no blocker term | same |
| MINIMAL_SETS, proof-grounded | union mask | same; the **necessary** intersection is reported separately |
| MINIMAL_SETS, operational | excluded | excluded |
| **NO_CLEARING_SET_WITHIN_POOL** | trained as an **all-zero mask** when proof-grounded (P13 train 2, validation 1) | **no blocker term** (y0 only). DENSE 10000 shows why: parking at the lattice slot never clears, yet a 1-move plan to another slot does |
| INCOMPLETE / NON_MONOTONE / UNKNOWN original | no blocker term / skipped | same |

Union vs necessary on DEV:
- **PR_SIDES 17000:** union [1,1], necessary [0,0] (A or B suffices).
- **TRI_OR 19000:** union [1,1,1], necessary [0,0,1].
- **ORD_CHAIN 13000:** union = necessary = [1,1].

## 3. Arbitrary-target inputs and temporary-target validation

- **Inputs:** every query (scene, temporary target o, destination, current q) rebuilds the target role, goal, q and the DINOv2 view through the training pipeline (`p15_retarget.retarget_scene` / `build_record`; exact reproduction verified in P15-1).
- **Temporary-target lattice** (`p16_d.temp_lattice`): for each pool object o (destination = its scene-only parking slot) and each subset U of the other pool objects parked, the physical status of the move o → slot from q0 is adjudicated.
  - The union of minimal clearing subsets is the **temporary-target blocker label**.
  - UNKNOWN gives an incomplete lattice and no label.
  - (A first run compared against the teacher vocabulary instead of the physics vocabulary and returned all-UNKNOWN. It was detected, voided in `void_temp_v1`, fixed and re-run.)
- **Recursion policy:** recursion uses only the P15 DEV-recalibrated temporary-target **feasibility** (deferring an object whose recalibrated feasibility to its first slot is < 0.5). Temporary-target blocker **marginals are never used** by any guide; they are evaluated separately below.

## 4. Completed non-learned optimiser (shared by every guide)

- **Movers:** every movable non-fixed object (scene-only, cap 6). Hidden enabling objects are eligible because nothing is filtered by any label.
- **Destinations:** recomputed on every hypothetical state; freed source cells are eligible.
- **Edges:** up to 3 certified library modes with distinct terminal q (local 3×3 / 4×4 + global similarity ranking, absolute-source / destination fixed-base filter, footprint).
  - Every reuse is re-certified in the current scene.
  - A failed straight start-transit triggers a bounded certified RRT transit (8 per root), else `UNKNOWN_TRANSIT`.
  - If no mode certifies, the deterministic online planner runs (6 per root).
- **Search:** iterative deepening to 4 relocations, repeats ≤ 2 per object (never consecutively), dominance on (occupancy, q) against ≤ counts and ≤ travel, travel branch-and-bound, node cap 500, lexicographic (moves, measured joint travel).
  - Claims are only `MIN_MOVES…` / `MIN_MOVES_AND_MIN_TRAVEL_WITHIN_FULLY_ADJUDICATED_FINITE_GRAPH` when every shallower (and same-depth) pass was enumerated completely with all outcomes decided.
- **Guides only reorder candidates; none prunes:**

| guide | definition |
|---|---|
| Dp16 / Dp16-norec | P16-retrained pairless (corrected labels), ± feasibility-only recursion |
| Dp | frozen P13 pairless |
| D | frozen P13 paired |
| geometry / geometry-norec | analytic heuristic on updated positions, ± geometric recursion |
| uniform | catalogue order |
| oracle | original scene-only lattice union (scope-limited, after unsealing) |

- **Shared cache:** all guides on a root use one exact cache with virtual accounting (0083 §1). Budgets and CPU are therefore identical to separate runs, while physical work is computed once.
