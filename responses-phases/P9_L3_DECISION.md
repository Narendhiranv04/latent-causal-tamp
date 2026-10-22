# P9-L3 decision — which joint Boltzmann root formulation to keep

## Decision: **KEEP_UNIQUE** (canonical unique-factor root model, `ABC9U_UNIQUE_V1`), on semantic grounds — with predictive parity, not predictive superiority

**Gates:**

| gate | verdict | basis |
|---|---|---|
| L3a-0 | PASS | integrity, identity, isolation (report 0031) |
| L3a-1 | PASS | exact mathematics; invariances; B-full higher order retained; 375/375 tests (report 0032) |
| L3b | PASS | engineering; matched training; 4,630 / 8,000 CPU-s; 0 teacher, IK or planner calls (report 0033) |

All results are **prediction-only metrics on saved data**. No physical execution was performed; P8d's G+M 9/12 remains the only execution evidence.

## Why the unique-factor model

1. **It satisfies the invariances the factor graph must have; P9 PoE does not.**
   - With identical weights, PoE prior marginals move by up to **0.18** when a candidate is listed twice, and by **0.046** when a one-move repair already present as an omission is also listed as a candidate (no new physical relation).
   - The PoE choice changes on 1–3 of 12 roots under a duplicate.
   - The mechanism is that PoE applies a reused query's outcome unary once per block containing it (742 of 1,265 queries, up to 7×), plus one normalizer per block. In the toy, 0.8 becomes 0.941.
   - The unique model is exactly invariant (≤ 1e-14) in every expected case, for B-full, B-structured, C-full and all 15 trained unique models.
2. **It is the same model wherever PoE is unambiguous.**
   - It is identical to the ABC7 joint for one-repair catalogues and to PoE when no query is shared (≤ 1e-10).
   - It keeps P_S exactly, all five families (including B-full's higher order) and the same three-term objective.
   - It costs the same per root.
3. **Predictively the formulations are indistinguishable at matched training.**
   - Validation root NLL (unique − PoE): B-full +0.05 [−0.05, +0.18], B-structured +0.00, C-full −0.06 [−0.17, +0.01]; 400 updates +0.001 [−0.03, +0.03].
   - Neutral calibrated metrics move both ways by arm.
   - By the predeclared rule (invariances mandatory; prefer the simpler model absent a robust gain), the unique model — fewer factor applications and no `Z_eq` — is kept.

## What this does NOT establish

- **No predictive advantage of the unique model.** The disclosed-test 400-update diagnostic even favours PoE (+0.86 [+0.05, +1.96]). It is high-variance by seed (unique 2.42 / 1.17 / 0.86 vs PoE 0.74 / 0.62 / 0.50), and by contract the disclosed test cannot select. It is a warning to re-check with independent data.
- **No catalogue invariance for genuinely relational additions.** In B-full and C-full, adding an omission query as a complete candidate brings ABC7's role- and context-specific scene–repair couplings for that query, and marginals move by up to 0.31 / 0.51. This is permitted, but it is a real modelling choice.
- **No generalization or execution claim.** Validation has 12 roots, and 3 of them carry 95 % of U-B-full's validation NLL.

## Factor evidence carried forward

| factor | verdict | basis |
|---|---|---|
| F5 generic coupling | **INCONCLUSIVE-positive** | Under the unique model it is favoured on validation (full − structured −0.33 [−0.66, −0.07]) and test; scene → repair conditionals informative (dependence 0.10 vs 0) |
| joint vs factorized | **INCONCLUSIVE-positive** | U-B-full − SF −0.52 [−1.12, −0.12] on validation. But SF and geometry-only B-full are better *calibrated* on the disclosed test, and κ +1 is only predicted after longer training or by geometry-only (policy-relative labels) |
| F3 structured `z0–zS` pair | **BLOCKED** | Unidentifiable from saved data (no root has scene edits and `z0 = 1`); exactly-zero gradients persist in both formulations |
| appearance (DINOv2) | **INCONCLUSIVE** | Geometry-only has worse validation NLL (−0.38 [−0.88, +0.05], favouring DINOv2) but the best test calibration, hidden-scene completion and κ MAE. Capacity and initialization differ, so it is not a clean ablation |
| C order representation, order contrasts, omission necessity | **UNTESTED / N/A** | C-full vs B-full n.s.; no decided same-endpoint order pairs; no omission-only labels in validation or test |

## Recommended next steps (proposal only; nothing authorized or started)

1. **Narrower explicit graph, saved data only.** Add one scene–query coupling per (scene bit, query) instead of per (block, role, context), and compare it with `ABC9U_UNIQUE_V1` on the same plan. This decides whether the remaining alias sensitivity of B-full / C-full is wanted physics or parameterization.
2. **Capacity-matched geometry-only control** (same layer list, zero visual input), plus a larger *validation* set. Twelve roots, three of them dominant, cannot decide equivalence.
3. **Conditional data proposal (requires separate approval and budget):**
   - originally feasible roots *with* scene edits (identifies `z0–zS`);
   - proof-grounded or witnessed κ = +1 (needs the place-side certificate);
   - same-endpoint order swaps from the same q0;
   - independently evaluated omission-only queries;
   - a constructor-disjoint family;
   - then a matched L4 one-shot comparison against G+M.

**STOP.** No L4, 3D, hardware, new teacher queries, data collection or robot episodes.
