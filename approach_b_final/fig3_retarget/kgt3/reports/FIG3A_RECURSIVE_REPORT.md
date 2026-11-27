# FIG3A — recursive retargeting with ordered chunks (REC-ORDERED)

**Status:**
- **Implemented and unit-tested.** Audited for privileged inputs (P0).
- **Run model-only** on the exposed DEV panels for computational accounting.
- **Not physically deployed.** Both domains stopped at the P2 fresh gate (DATA_LIMITED), so P3 and P5 never authorized physical evaluation.
- **No deployable K > 3 success claim is made.**

## Implementation (`../planners.py` `rec`, reusing `../../recursive.py`)

1. **Seeds.** Original-task ordered seeds of size ≤ 3 come from the released task-conditioned cVAE (D4) and the coupled p11. There are 8 seeds plus the unchanged K ≤ 3 production candidate; low-X seeds are not discarded.
2. **Retargeting.** Every seed action is retargeted, in learned order, on its branch-local hypothetical pre-action scene (`views.rebase`, temporary task = object → destination). The original target, ancestors, placed objects and reserved destinations are protected.
3. **Enabling chunks.** The same sampler and X/Y model score ordered enabling chunks of 1–3 actions by temporary p11.
   - Admission: temporary Y must beat the no-op.
   - The no-insertion sibling is always kept.
   - One extra admitted high-temporary-Y / low-X repair per action (`ylowx_extra`) keeps low-X enablers available for recursion.
   - No oracle-derived edges.
4. **Recursion and insertion.** Recursion runs on new enablers with insertion before the parent, and edges are learned (PREREQ / LOCAL / SEED).
   - Caps: expansion depth 3, 96 expansions, 256 temporary readouts, 4 variants per action.
   - The scene is rebased per branch.
5. **Final composition.** Chunk boundaries of the **fixed recursive order** are chosen by prefix DP (`compose.fixed_order_dp`; has_multi for length > 3). Each chunk is scored by marginal X in its own anchored scene, and global original-task Y is scored once at the endpoint. Temporary scores are not multiplied in. λ = 0; no displacement tie-break.
6. **Selection.** Production NOOP gate, then argmin E over candidates plus the production floor; ABSTAIN if none. One plan per root and arm.

**Controls.**
- **REC-REORDER (hybrid):** grouped subset DP restricted to the candidate's learned PREREQ + LOCAL edges.
- **FLAT-INSERT:** original-task insertion without retargeting, same final scoring.

## Model-only accounting (exposed DEV panels; predictions NOT verified; `p4/p4_model_only_{2d,3d}.jsonl`)

| | 2D (30 certified K4–6, frozen F0) | 3D (20 witnessed L4–5, M1ft O2 s0, not gate-passed) |
|---|---|---|
| REC-ORDERED decisions | 30 REPAIR | 20 REPAIR |
| Selected length > 3 / with a multi-action chunk | 19 / 30 | 8 / 18 |
| Selected lengths | 3: 11, 5: 4, 6: 15 | 3: 12, 4: 4, 5: 4 |
| Production floor selected | 0 | 0 |
| Recursion levels reached (seed level 1; expansion cap 3) | 4 on 18 roots, 3 on 12 | 4 on 15 roots, 3 on 5 |
| Admitted enabling repairs / extra high-Y-low-X repairs | 4,965 / 1,655 | 1,573 / 291 |
| Candidate pool (median per root) | 20 | 30.5 |
| Selected set equals the witness assignment | **0 / 30** | **0 / 20** |
| Wall time, median / max (cap 180 s) | 12.5 / 28.0 s | 1.6 / 3.2 s |
| Budget stops | 0 | 0 |

- **REC-REORDER:** same pools; length > 3 on 19 (2D) and 9 (3D) roots.
- **FLAT-INSERT:** length > 3 on 14 (2D) and 12 (3D) roots.
- **Witness sets:** no arm selected the witness assignment on any root.

## What this does and does not show

- **Shown.** The recursion runs within budget in both domains. It inserts learned enablers before parents at depth up to the cap and composes long ordered plans with multi-action chunks. No physical module is ever called (P0).
- **Not shown.** Whether any of these plans executes. In P2 the X model failed or was DATA_LIMITED on multi-action ranking at reached intermediate states. In P1 the learned orders ranked the verified witness order poorly (2D quantile 0.82). So no long REC-ORDERED plan should be expected to verify at a useful rate.
- **No comparison claims.** No REC-ORDERED vs FLAT-INSERT comparison was run physically, so there is no architectural claim.

## Figure

`figures/KGT3_P4_planners.png`:
- (a) wall time;
- (b) share of selected plans longer than 3 actions (model-only);
- (c) Fig. 3B funnel.
