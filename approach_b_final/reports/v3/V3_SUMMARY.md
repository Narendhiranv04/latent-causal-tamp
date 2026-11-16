# Approach B V3: summary (task-aware candidate sets + coupled Boltzmann selection)

**Contract:** `docs/PLAN_V3_2026-11-15.md`. **Branch:** `naren/approach-b-v3`.

**Execution hosts:**
- gvlab2: GPU (RTX 5090) and CPU.
- Laptop and gvlab: CPU teacher hosts, authorised by the user on 2026-11-16, with parity-checked teachers.

**Method.** Original scene → **one** pass of a repair-trained, goal-conditioned cVAE (M = 4 destinations per object) → every legal ordered repair of length 1–3 (B = 4,096) → coupled F2 / F3 / F5 Boltzmann scoring (retrained on candidate-matched physical labels) → **one** repair, NO-OP or ABSTAIN → independent physical verification.
- No hypothetical re-querying.
- No planner calls inside inference.
- No retries.

| Phase | Commit | Key result |
|---|---|---|
| V3-0 audit | `fc6c570eab` | All verified successful assignments satisfy the V3 grammar. The base snapshot has 1 assignment per root (2D 1,881 / 3D 1,127). Splits are clean. |
| V3-1 direct constructor | `3027da5b45`, `fd5dd6d6a5` | With the frozen V2 models, direct ≈ iterative in 3D, −7 to −10 points in 2D: proposal coverage of 3.5 % vs 21 % |
| V3-2 / V3-3 samplers, task cVAE | `9e95e5c97e` | Sampling rules barely matter for the Q2 cVAE. The repair-trained cVAE raises ingredient recall at M = 4 from 2 → 29 % (2D) and 4 → 59 % (3D), and 3D top-1 by +13 points with the old scorer. NONE abstention collapses (scorer shift). |
| V3-4 matched labels | `36a370d9ab` | 5,458 new TRAIN labels. The V2 scorer is overconfident on the new candidates: 2D ECE 0.40. |
| V3-5 retrained scorer, rule | `da9ce55f4e` | Held-out NLL 0.92 → 0.47 (2D) and 0.73 → 0.51 (3D). Rule: gate 0.5, η 0.3, α = β = γ = 0. |
| V3-6 final test | this commit | **2D 43.6 % vs V2 iterative 25.6 % (+18.0 [+14.6, +21.4]); 3D 77.3 % vs 52.4 % (+24.9 [+20.1, +29.3])**. Both learned components are needed. Coupling gives no measurable gain. Order modelling is needed in 3D. |

**Not done or not claimed:**
- V3-7: no dataset extension.
- V3-8: optional items not needed.
- Test-split exposure from V1 / V2 (no fresh cohort).
- No travel benefit (γ = 0).
- No universal infeasibility claim for NONE.
- External 3D baselines remain deferred.
