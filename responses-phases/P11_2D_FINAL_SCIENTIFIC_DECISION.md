# P11 — 2D final scientific decision

**Overall status: PARTIAL** (engineering PASS).
- Keyed B is the strongest **learned** repair-execution method on the P10b benchmark.
- D is the best initial-infeasibility and blocker-identification method on matched cohorts.
- Length generalization of execution, appearance robustness and constructor-disjoint generalization are **not** established.

**Stage gates:**

| stage | gate |
|---|---|
| P11-0 audit | PASS |
| P11-1 H9 | PASS |
| P11-2 components | PASS |
| P11-3 length | PASS |
| P11-4 new holdout | **BLOCKED** |
| P11-5 D comparison | done |
| P11-6 regression | 407 / 407 + 6 / 6 |

## Direct answers

1. **Do the P10 B > A / SF strict TOP1 and complementarity results survive code-level reconstruction?**
   - **Yes.** Both reproduce exactly from code and recorded evidence (0045):
     - B 0.718 vs SF 0.385, +0.333 [0.226, 0.441], raw p 1.9e-6, **Holm p 7.8e-6**;
     - B vs A on H1 κ error, 0.014 vs 0.277, raw p 0.0039, **Holm p 0.0117**.
   - P3 (order, Holm p 1.0) and P4 (omission, Holm p 0.60) remain unsupported.
   - The blind evaluation recomputes bit-identically, and the 255 episodes map to all 975 arm × seed choices.
2. **What does the correctly evaluated H9 two-palette experiment show? Did the overwrite exist?**
   - **The overwrite existed**: P2 overwrote P1 in the snapshot.
   - Corrected (both palettes, 100 roots, per-root), keyed B's predictions shift by 0.248 [0.216, 0.282], its TOP1 changes on **77 %** of roots, and κ̂ moves by 0.62 on H1 roots. Every DINOv2 arm is appearance-sensitive; visual-zero gives exactly 0.
   - P10e's 0.165 reproduces as the P2-only, query-pooled value.
3. **Does F1 add independent value? Does J change decisions, and is its cost prediction useful?**
   - **F1:** a matched λ_static = 0 retrain shows the static head learns static validity only when supervised (AUROC 0.78 vs 0.56). No benefit for repair selection is identified (TOP1 −0.031 [−0.103, 0.041]); the H1 sensitivity is exploratory.
   - **J:** predicts witnessed travel (Spearman 0.71–0.79) but rarely decides a choice (tie-break on 6–20 / 65 roots) and does not change success. It is **not practically identified**.
4. **Which of F2, F3, F4, F5-generic, F5-HO and DINOv2 improve held-out outcomes?**
   - Surviving family-wise (32-test Holm) correction: **F2 order** (order −0.72) and **DINOv2** (NLL +0.089 without it).
   - **F3, F5-generic, F5-HO:** consistent H1 effects (9 / 9 roots) that cannot survive correction with 9 roots, so UNDERPOWERED.
   - **F4:** not beneficial.
   - **Why a null is not redundancy:** with 9–26 roots, shared encoders and fixed constructor families, a null result is not proof of redundancy elsewhere.
5. **Do short-trained models physically execute 3- / 4-move repairs?**
   - Mostly **no**. Short-trained B: 0.15 (3-move) and 0.22 (4-move), against 0.52 / 0.78 for full-trained B (−0.46 [−0.63, −0.28]).
   - Prediction-level extrapolation did not transfer to execution.
   - Minimality is catalogue-relative: H10_4 SOUND on 5 of 9 blind roots, H10_3 OPERATIONAL.
6. **Does a new 2D constructor family support generalization?**
   - **Not evaluated (BLOCKED).** The non-adaptive new families produced mostly feasible originals (statically obstructed: 3 / 40 and 7 / 39).
   - Making them hard would require adaptive selection, and the cost was about 3× the cap.
   - External generalization remains **open**.
7. **Best approach per task (separate rankings):**
   - **Repair execution:** keyed B (= C) > A > geometry > SF among learned / analytic methods; planner-assisted G+M is still higher (0.831).
   - **Initial infeasibility:** D ≈ D-pairless ≈ SF (all 64 / 64; D has the lowest NLL, 0.0049) > A = B = C (each misses 1 of 4 feasible roots). Not statistically resolvable with 4 positives.
   - **Blocker identity:** D on proof-grounded masks (0.932) and on the matched cohort (0.939). D-pairless is better on operational corridor masks.
8. **Remaining limitations:**
   - 2D simulator only, with one robot and one grasp family.
   - Adaptive P10b constructor families; generalization beyond them is not evaluated.
   - Blind results are now disclosed, so every P11 analysis is post-hoc.
   - Small mechanism strata (H1: 9 roots).
   - Certificate scopes: pick-side, plus assignment-scoped FIRST_MOVER; operational BUDGET labels.
   - Appearance fragility.
   - Long repairs require long training data.
   - G+M advantage, at about equal CPU per success.
   - No hardware and no 3D.
   - D is limited to feasibility and blocker identity; destinations and recursion are not implemented.

**Commit:** P11 artifacts are pushed to `origin/main`; the final SHA is in the chat reply.
