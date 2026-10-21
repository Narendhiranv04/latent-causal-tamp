# A7 place-side certificate — read-only soundness audit (P7, before any P7b teacher call)

**Decision: A7 stays DISABLED.** Place-side negatives remain `BUDGET_INFEASIBLE` (operational, policy-relative) and are
reported separately from certified negatives.

## What a sound place-side certificate would have to prove

For the target held after **any** of the 48 declared grasps (each fixes a held-object offset `held_local`), **every**
declared place candidate (48 approach directions × branches) at **every** admissible goal pose is excluded, for a
fixed, correctly identified start of the place phase.

## Why the existing evidence does not suffice

1. **Goal tolerance (the A7 issue, report 0017 §6.3, C4).** The skill places at the exact goal-cell centre, but the
   success predicate accepts the object within `release_xy_tolerance_m = 0.002` m. `geometry.Checker` returns a
   COLLISION verdict without a penetration depth, so a definite collision at the exact centre does not exclude a clear
   placement up to 2 mm away.
2. **The tolerance does not translate rigidly into the arm.** A 2 mm target shift changes the place configuration
   through closed-form IK, so links move by an amount bounded by the IK sensitivity, not by 2 mm. A robust proof
   needs a signed-distance margin plus an IK-sensitivity bound per candidate; neither exists in the pinned code.
3. **Grasp-place coupling.** The place screen is evaluated per pick candidate's `held_local`. The teacher's
   `PLACE_SCREEN_EXHAUSTED_CERTIFIED` terminal shows that every *screened* combination failed definitely at the exact
   centre, not that the full grasp × place × 2 mm family fails.
4. **No independent checker.** Unlike `LINK0_SECTOR_PICK_V1` (separate producer and checker, `sector_check.py`), no
   independent place-side checker exists, and no witness replay has been run against near-boundary counterexamples.

## What would be required (not authorized in P7; needs a new versioned decision)

A depth-carrying distance query, a per-candidate IK Lipschitz bound over the 2 mm disc, an independent checker, replay
of all recorded place witnesses (no contradiction allowed), and a near-boundary perturbation test. Alternatively the
user may accept the declared exact-centre skill as the certificate scope (as A1 did for the pick side). That is a
scope decision, not a proof, and is left to the user.

## Consequence for P7b

Every place-side negative (P6 F2/F3/F4-style) is `BUDGET_INFEASIBLE`; every κ or effect that uses one is flagged
`operational`. Construction still predicts these negatives with the pose-only place screen, as an intent predicate,
never as a label.
