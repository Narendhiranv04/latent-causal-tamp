# R2.1 (2D): is the frozen X/Y scorer the bottleneck? Exact labels, with the cVAE and search bypassed

**Data and setup.**
- **Labels:** the exact-label pool from R2.0, held-out part only: VAL plus TRAIN-cache labels. That is 21,548 decided local (m ≤ 3) X·Y pairs and 19,995 Y labels.
- **Model:** the frozen bundle, running on the RTX 5090.
- **Statistics:** family-cluster bootstrap 95 % CIs.
- **Data:** JSON in `R2_1_model_only_2d.json` and `R2_phys_2d.json`. Figures: `figures/R2_1_scorer_2d.png`, `R2_1_matchedN_2d.png`, `R2_1_retarget.png`, `R2_1_rebase.png`.

## Established

1. **SCORER_SIGNAL (weaker than 3D).**
   - Held-out p11 vs X·Y AUROC **0.789 [0.775, 0.802]**; ECE 0.17.
   - Within-root top-1 verified 0.662 vs random 0.476: **+0.186 [0.161, 0.210]**, 713 mixed families.
   - The TRAIN fit reference is 0.89–0.92, so there is a clear generalization gap.
2. **H_m.** AUROC m = 1 **0.852**, m = 2 0.777, m = 3 0.764. m3 − m1 = **−0.088 [−0.115, −0.061]**.
3. **H_h: rebasing hurts in 2D.**
   - Y_rebased vs Y_global on identical endpoints: AUROC 0.818 vs 0.865, difference **−0.047 [−0.060, −0.035]**.
   - Rebased Y is **severely under-confident**: mean p 0.16 vs prevalence 0.56; ECE 0.40 vs 0.13.
   - **Why it matters:** R1's chunk costs and temporary tasks are computed on rebased views, so 2D home-anchored energies inherit this bias.
4. **RETARGET_SIGNAL (C3b, 49 examples, 39 blocked; TT_ADAPTER_V1 labels; restricted candidates).**
   - ΔpY concordance **0.703 [0.621, 0.792]**.
   - Top-1 p11 is a verified enabler in **37/48** (0.77) vs random 0.34.
   - Scorer retargeting helps: Y_τ AUROC **0.692 [0.616, 0.764]** vs 0.585 with the original context (+0.107 [0.019, 0.198]).
5. **H_T.** Y_τ AUROC upper CI 0.764 < lower CI 0.870 of the original-task one-edit pY (0.890). Y_τ is miscalibrated: ECE 0.19; mean p 0.26 vs prevalence 0.43.
6. **Admission is not a filter in 2D.**
   - `beats_empty` admits **605/608 non-enabling groups (99.5 %)** and discards 5/476 enabling groups.
   - **Why:** the blocked temporary no-op pY is about 0, so any group raises pY.
   - In the omission panel it admitted all 18 omissions that break the parent.
7. **H_C, staged beam: this is the operating regime in 2D.** The exhaustive top-1 group is retained in:

   | N bin | Retained | Median exhaustive groups |
   |---|---|---|
   | 1–5 | 90 % | 348 |
   | 6–10 | 30 % | 13.6k |
   | 11–15 | 15 % | 62k |
   | 16–20 | **4 %** | 169k |

   Staging is active whenever there are more than 4,096 groups, i.e. typically N ≥ 6. Recursive repair generation in 2D therefore **almost never sees the model's own best local group** at mid and high N. The production B0 enumerates EXACT4 exhaustively and is unaffected.

## Object count (H_N): split verdict

- **Natural panel, N ≤ 15: NOT ESTABLISHED.**
  - AUROC 1–5 0.771, 6–10 0.731, 11–15 0.751. Difference 11–15 − 1–5 = **−0.020 [−0.073, +0.031]**.
  - Top-1 gain is positive in every populated bin.
- **Natural panel, N 16–20: UNIDENTIFIABLE.**
  - There are **0 feasible labels** in held-out data, mirroring TRAIN (R2.0: every N ≥ 16 root is NONE).
  - The model predicts mean p11 0.009 there.
- **Matched add-distractor panel (10 families; +4 / +8; 20 variants; 92 queries; RNG floor 3/3).**
  - **Labels:** adding bodies far from task cells changed teacher labels in **8/10 (+4) and 9/10 (+8)** families. Repair X fell 10 → 3 → 1 and repair Y fell 10 → 4 → 3. The failures are mostly UNKNOWN_PLANNER, with 2 certified infeasible.
  - **Consequence:** the planar arm's free space genuinely shrinks, so a label-preserving matched panel was **not achievable** in 2D.
  - **The model shifts every prediction downward with N.** Mean pY of teacher-feasible endpoints falls **0.75 → 0.31 → 0.33**, and of infeasible ones 0.20 → 0.08 → 0.004.
  - **Ranking within each level survives, with few positives:** AUROC 0.91 / 0.81 / 0.84, on 10 / 4 / 3 positives.
  - **False negatives at high N:** feasible repair endpoints at N = 15 and N = 19 receive pY 0.12, 0.086 and 0.001.
- **Reading:**
  - **Supported as a hypothesis**, not established: a **label-support shortcut** at high N in 2D, where more objects means lower pY regardless of the specific scene, consistent with TRAIN having no feasible N ≥ 16 example.
  - **Not supported:** a pure representation-capacity failure, since ranking survives. The evidence cannot separate the two cleanly because the teacher's labels also move.

## Implication for the >K3 failure in 2D

- **The several limitations act together:**
  1. weaker local scoring (0.79);
  2. rebased views that are badly under-confident;
  3. temporary-task Y that is weak and miscalibrated;
  4. an admission rule that never rejects;
  5. a staged beam that discards the model's best groups at N ≥ 6;
  6. for N ≥ 16, no positive supervision at all.
- **Object count alone is not shown to be the cause.** Its effect is confounded with the training-label support.
