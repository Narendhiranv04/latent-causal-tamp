# R2.1 (3D): is the frozen X/Y scorer the bottleneck? Exact labels, with the cVAE and search bypassed

**Data and setup.**
- **Labels:** the exact-label pool from R2.0, held-out part only: VAL plus TRAIN-cache labels that are not in the training snapshot. That is 7,554 decided local (m ≤ 3) X·Y pairs and 6,892 Y labels.
- **Model:** the frozen bundle (D s0 scorer, S1 cVAE), running on the RTX 5090.
- **Statistics:** family-cluster bootstrap 95 % CIs. "mf" = mixed families.
- **Data:** JSON in `R2_1_model_only_3d.json` (aggregates) and `R2_phys_3d.json` (matched-N, omission). Figures: `figures/R2_1_scorer_3d.png`, `R2_1_matchedN_3d.png`, `R2_1_retarget.png`, `R2_1_rebase.png`.

## Established (pre-registered rule met)

1. **SCORER_SIGNAL.**
   - Held-out p11 vs X·Y: AUROC **0.871 [0.854, 0.889]**.
   - Within-root top-1 verified rate **0.788 vs random 0.525**: +0.263 [0.221, 0.304], 153 mixed families.
2. **H_m, sequence length degrades discrimination.**
   - AUROC m = 1 **0.969**, m = 2 0.848, m = 3 0.841. m3 − m1 = **−0.128 [−0.159, −0.093]**.
   - On the K4/K5 cohort (out of distribution, archived exact labels, continuous mode), direct long-sequence p11 is near chance: AUROC **0.55 [0.39, 0.70]** (m = 4: 0.52, m = 5: 0.66; 12 mixed roots).
   - pX vs X on that cohort: 0.60 [0.43, 0.75].
   - **Reading:** scoring long sequences directly is unreliable; local chunks of m ≤ 3 are where the model has signal.
3. **H_h: the representation matters, a little.** On identical endpoints, Y_rebased (fresh-root no-op) vs Y_global (original root plus edits):
   - AUROC 0.935 vs 0.949, difference **−0.014 [−0.022, −0.006]**.
   - Rebased is better calibrated (ECE 0.043 vs 0.065).
   - By h: h = 2 shows the largest loss (0.886 vs 0.924).
4. **RETARGET_SIGNAL (C3b, 22 blocked temporary tasks, TT_ADAPTER_V1 labels; restricted candidate sets, so this is a diagnostic only).**
   - Within-context concordance of ΔpY (enabling vs non-enabling) **0.893 [0.825, 0.960]**.
   - Top-1 p11 is a verified enabler in **15/21** (0.71) vs random 0.19.
   - Retargeting the **scorer** context is essential: Y_τ AUROC **0.817 [0.711, 0.908]** retargeted vs **0.377** with the original-task context (difference +0.44 [0.36, 0.52]).
5. **H_T: temporary tasks are scored worse than original tasks.**
   - Y_τ AUROC upper CI 0.908 < lower CI 0.958 of the original-task one-edit pY (0.974).
   - Y_τ is also miscalibrated: ECE 0.18; mean p 0.41 vs prevalence 0.25.
6. **The admission rule discards real enablers.** Relative temporary-pY admission (`beats_empty`):
   - drops **29/139 enabling groups (21 %)**, including **17/93 verified enablers**;
   - admits 55/389 non-enabling groups (14 %).
7. **H_C, staged beam (diagnostic run forcing staging):** the exhaustive top-1 group is retained by the staged beam in:

   | N bin | Retained | Median exhaustive groups | Staging active by default? |
   |---|---|---|---|
   | 1–3 | 100 % | — | no |
   | 4–5 | 43 % | 836 | no |
   | 6–7 | 24 % | 3,352 | no |
   | 8–13 | **10 %** | 15,928 | **yes** |

   At default settings, staging switches on only above 4,096 groups, so it affects only the highest-N 3D roots.

## Not established

- **H_N: object count, natural panel, inside support.**
  - AUROC by N bin: 1–3 0.860, 4–5 0.843, 6–7 0.864, 8–13 0.939 (8 mixed families).
  - Highest qualifying bin (6–7) − lowest (1–3) = **+0.004 [−0.046, +0.060]**.
  - Within-root top-1 gain is positive in every bin (+0.22 to +0.28).
- **H_N: matched add-distractor panel** (8 families; +3 / +6; 14 variants built; 5 unsupported because the 6×6 shelf lacked qualifying cells; RNG floor 3/3 unchanged).
  - **Labels change:** adding bodies changed the teacher's labels in 3/7 (+3) and 4/4 (+6) variants. The repair endpoint became infeasible.
  - **The model tracked those changes.** pY of changed endpoints fell to 0.016–0.13. Pooled within-level Y AUROC is 0.95 (original), 0.93 (+3) and 1.0 (+6).
  - **Unchanged-label subset (+3, n = 4):** discrimination rep > neg and rep > noop **4/4 preserved**. Mean Δp11 −0.10 (range −0.19 to +0.02).
  - **Reading:** this is consistent with label-tracking, **not** with a cardinality failure. With n this small the result is not a proof.

## Hypotheses only (not supported by these data)

- **A pure object-count shortcut in 3D.** TRAIN N ≥ 9 is 100 % NONE, but the matched variants at N 9–11 are still ranked correctly (only 6 scored variants).
- **Omission (34 new or reused exact Y_τ labels on 17 examples).**
  - Leaving one action out of the verified two-action enabling set breaks the parent in only 18/34 cases. 16/17 examples contain a redundant action.
  - The model's pY of the kept action vs Y_τ: AUROC 0.86.
  - **Reading:** enabling groups in C3b are usually one necessary move plus one redundant move.

## Implication for the >K3 failure in 3D

- **What the evidence points to:** the problem is **not** object count. It is:
  1. scoring long sequences directly (out of distribution in m);
  2. weaker and miscalibrated temporary-task Y;
  3. admission discarding real enablers;
  4. at high N only, staged-beam candidate loss.
- **What is fine:** the local m ≤ 3 scorer with a retargeted context is strong.
- **Consequence:** this favours the R1 design of retargeting plus chunked local scoring over direct long scoring. R2.3 tests that.
