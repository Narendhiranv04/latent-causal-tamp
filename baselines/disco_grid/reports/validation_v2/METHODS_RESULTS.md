# DISCO-Grid (adapted): methods and measured pilot results

We adapt DISCO’s training-time progressive-widening UCB search and feasible-edge policy/value distillation to categorical object–destination decisions. The benchmark uses a fixed-base planar 3R robot on an 8×8 lattice (0.08 m pitch; 48 side-grasp candidates) and xArm7 in a 6×6 confined shelf (0.075 m pitch; 32 side-grasp candidates). Original object geometry, fixed/movable flags, target task and physical teachers remain fixed. Up to three non-target, move-once relocations may use originally empty supported cells without destination reuse. Physical state carries joints and attachments through moves; stopping verifies the terminal q_ref connector (X) and independent target execution in the canonical edited endpoint (Y).

The historical O0 model encodes structured scene/goal/mask context but omits achieved intermediate joints. Its primary open-loop rollout performs only predicted cell edits before committing one plan; independent final verification incurs physical cost. A separately versioned O1 model includes actual observed joint sin/cos and visibility masks in both categorical policy branches and action-conditioned continuation Q. O1 is restricted to physically observed closed-loop states.

Search uses UCB C1.5 and widening k2,alpha.3. Executed feasible transitions supervise policy; visited decided descendant-leaf success fractions supervise weighted BCE Q, with log(1+n) evidence weights. STOP has decided positive/negative value labels and successful policy demonstrations. New extraction counts a cached STOP once. Historical trees are small: 24 2D /12 3D TRAIN roots and 171/48 R0 feasible edges; there are no 3D depth3 feasible edges in either historical round.

## Historical primary O0 open-loop pilot, recalculated

| Domain | Overall roots | Task roots | Success / prediction trials | Root-mean success | 95% root bootstrap CI |
|---|---:|---:|---|---:|---|
| 2D | 75 | 45 | 11/135 (3 fixed network seeds) | 8.15% | [3.70, 14.07]% |
| 3D | 30 | 18 | 15/54 (3 fixed network seeds) | 27.78% | [11.11, 46.30]% |

The resampling unit is the physical root, with fixed-model seed means within root (10,000 resamples; seed 20261116). These are exposed historical TEST cohorts, not new confirmation sets.

| Paired historical contrast | 2D delta [95% CI], points | 3D delta [95% CI], points |
|---|---|---|
| P2+Q2 − P2, seeds 0/1/2 | -2.22 [-7.41, +2.96] | +7.41 [-5.56, +20.37] |
| Round1 all-feasible − successful-only, seed 0 only | +0.00 [-6.67, +6.67] | +11.11 [+0.00, +27.78] |

Neither value contrast establishes superiority. The correctly matched historical seed 0 round 1 comparison is +11.11 points in 3D with a CI including zero; this differs from both the unequal-seed24.07−16.67=7.40-point aggregate and the invalid prior P2-vs-round 1 significance claim. Newly completed three-seed controls have not undergone new physical task evaluation.

## Validation STOP calibration (diagnostic only)

An optional regularized affine-logit root-STOP calibration was fitted on one validation-family half and audited on the other. Checkpoints were frozen; no TEST outcome selected parameters or architecture.

| Domain | VAL decided roots | Fit / audit roots | Audit raw NLL → calibrated NLL | Brier → calibrated Brier |
|---|---:|---|---|---|
| 2D | 751 | 387 / 364 | 0.5285 → 0.3413 | 0.1590 → 0.1115 |
| 3D | 364 | 170 / 194 | 0.5247 → 0.4556 | 0.1779 → 0.1421 |

This is probability calibration on root terminal labels, not measured repair improvement. The optional rule is not adopted as the primary selector. Intermediate STOP and continuation calibration remain unresolved.

All new computation used gvlab CPU with one thread per process and no GPU allocation. Ten original lightweight tests and 35 final validation/regression tests passed; fresh physical order parity was 4/4. Frozen archive replay reproduced315 primary predictions exactly. Eighteen new matched round 1 training runs completed on the historical trees; they establish implementation compatibility, not stronger task performance. An independent 2D K3 root yielded 8 feasible edges / 16 calls and no solution; a 3D pilot was stopped at its wall limit with an unresolved in-flight query.

The limited independent-root coverage, expensive3D search, absent physical O1 evaluation, exposed TEST data, missing paired Approach B weight/provenance records, and unmeasured peak-resource/partial-query accounting preclude a publication claim of a fully strengthened baseline or cross-method superiority. No causal advantage is assigned to any Approach B factor.
