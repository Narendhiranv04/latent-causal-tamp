# R3.3A — Targeted 3D validation extension

**Contract:** `../R3_PREREG_ADDENDUM_A2.json`, sealed and pushed in `d56e1253b5` before any outcome. **Code:** `../data.py` (`build33a`, `DenseScene`) and `../evaluate.py` (`gate33a`).

**Checkpoints:** frozen, with no training. G1s s0 (`6dae59fd97cb5cd3`) is the primary candidate and M1s s0 (`bb8373a0260dd40c`) the architecture control. All results are development evidence.

## Decision

**R3.3A did not pass. Under the pre-registered rule, R3.4 is NOT_AUTHORIZED, so 3D stops here.**

| Component (pre-registered) | Result | Pass |
|---|---|---|
| POOLED support: mixed families h0 / h ≥ 1 (≥ 10 each) | 46 / 15 | yes |
| POOLED h ≥ 1 AUROC ≥ 0.75, lower CI ≥ 0.60 | 0.914 [0.849, 0.972] | yes |
| POOLED paired h ≥ 1 ΔAUROC vs F0, CI > 0 | +0.088 [0.006, 0.163], 44 families | yes |
| POOLED first-relocation FPR drop ≥ 0.15 (each model's own TPR-0.80 threshold) | 0.255 → 0.092 (25/98 → 9/98), drop 0.163 | yes |
| Guard: NEW panel alone, paired h ≥ 1 ΔAUROC point estimate > 0 | **−0.020** [−0.155, 0.081], 19 families | **no** |
| Guard: NEW panel alone, FPR drop point estimate > 0 | 0.250 → 0.096 | yes |

- **Why the guard exists.** It was pre-registered because the original VAL_SCALE panel was used for G1s early stopping and seed selection.
- **Failed component.** Only that guard fails, so the failure counts as "narrow".
- **DIAGNOSTIC_ONLY R3.4 not authorized.** That route also needed NEW_DENSE alone to show a positive paired h ≥ 1 gain with ≥ 10 mixed families. It has **2** mixed families, with Δ −0.045 [−0.28, 0.11].
- **Original VAL_SCALE gate.** Still FAILED (af45f538c3). It is not re-interpreted.

The pooled pass is carried by the original VAL_SCALE. The new family-independent labels do **not** reproduce the h ≥ 1 gain. They **do** reproduce the h0 / first-relocation gain:

| NEW panel (19–27 independent families) | F0 | G1s s0 | Paired Δ (95 % CI) |
|---|---|---|---|
| h0 AUROC | 0.840 | 0.943 | +0.103 [0.028, 0.172] |
| first relocations (h0, m1) AUROC | 0.804 | 0.940 | +0.136 [0.042, 0.234] |
| first-relocation FPR at own TPR-0.80 threshold | 13/52 | 5/52 | – |
| h ≥ 1 AUROC | 0.857 | 0.838 | −0.020 [−0.155, 0.081] |

## 1. Sealed collection (A2)

- **Families.** 27 new clean original-VAL families: not in any R3.1 scene, no DEV lineage, no physical exposure, N 5–9. They were taken in the pre-registered priority order. Strata alternated DENSE, DENSE, ORD.
- **ORD stratum.** 8 families, 56 jobs, using the unchanged R3.1 templates T1–T7: 6 S0 scenes and 2 HYPSTART scenes.
- **DENSE stratum.** 19 families, 139 jobs. Each scene is a static enabler-chain start built from learner-visible cells only, with no teacher, model score or label involved:
  - pivot M: a target-adjacent body;
  - E1: one or two bodies moved next to M;
  - E2: one body moved next to E1.
- **DENSE templates.** D1 [M], D2 [E1 | M], D3 [E2 | E1], D4 [E2 | E1 M], D5 [E1 M], D6 [M E1] (matched permutation), D7 [R | M] (non-enabling control), D8 [E1 | M→dM2] (changed destination).
- **Skipped.** One family failed DENSE construction; two families closed their strata at the cap.
- **No model-based selection.** No example was selected by G1s or M1s predictions.
- **Density.** Checked before any outcome. Mean occupied 8-neighbours per object: DENSE 2.49, ORD 1.59, the 20 K4/K5 DEV roots 1.63. Target neighbours: 2.16 / 1.88 / 2.25. The DENSE starts are at least as crowded as the K4/K5 regime at cell level.
- **Cost.** 195 jobs, 0.76 CPU-h. There were 0 errors, 0 censored jobs, 0 retries and 0 UNKNOWN outcomes.
- **Teacher outcomes.** 33 VERIFIED; 161 "no feasible side grasp" (relocation 0: 106, 1: 50, 2: 4, 3: 1); 1 EXECUTION_NOT_VERIFIED.
- **Labels.** 245 exact labels:

| Stratum | h0 positive / negative | h ≥ 1 positive / negative |
|---|---|---|
| ORD | 28 / 28 | 4 / 13 |
| DENSE | 43 / 96 | 8 / 25 |

**What the DENSE layouts did.** They blocked far more than intended:

| Outcome | Count |
|---|---|
| Pivot blocked at the start (D1) | 11/19 |
| Enabler E1 itself executable (D2 h0) | 6/19 |
| Pivot executable after E1 was moved (where both were observed) | 1/5 |
| Matched permutations D5/D6 | both fail 17/19, discordant 2/19 |

Consequences:
- Most h ≥ 1 chunks are unobserved, because the prefix failed. That is why DENSE h ≥ 1 has only 2 mixed families.
- The design yields many blocked first grasps but almost no verified enabler → pivot chains.
- Static cell adjacency over-constrains side grasps compared with the teacher-constructed K4/K5 chains, which were verified pick-by-pick.

## 2. Results by panel (marginal pX; family-cluster 95 % CI)

| Panel | Model | n (pos) | AUROC | AUPRC | NLL | Brier | ECE | h0 AUROC (mixed fams) | h ≥ 1 AUROC (mixed fams) | first-reloc. FPR @TPR0.8 (achieved TPR) | FPR / TPR @0.5 | FPR @ ORIG-frozen threshold (TPR) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORIG VAL_SCALE | F0 | 242 (124) | 0.859 | 0.867 | 0.752 | 0.218 | 0.219 | 0.866 (23) | 0.826 [0.73, 0.91] (10) | 0.217 (0.805) | 0.80 / 0.99 | 0.217 (0.805) |
| | G1s | | 0.937 | 0.933 | 0.342 | 0.101 | 0.042 | 0.931 | 0.948 [0.88, 0.99] | 0.087 (0.805) | 0.22 / 0.94 | 0.087 |
| | M1s | | 0.920 | 0.927 | 0.371 | 0.116 | 0.059 | 0.918 | 0.912 | 0.174 | 0.22 / 0.89 | 0.174 |
| NEW ORD | F0 | 71 (31) | 0.851 | 0.766 | 0.852 | 0.226 | 0.232 | 0.797 (7) | 1.000 (3) | 0.333 (0.826) | 1.00 / 0.96 | 0.267 (0.78) |
| | G1s | | 0.956 | 0.946 | 0.285 | 0.087 | 0.084 | 0.945 | 1.000 | 0.067 (0.826) | 0.20 / 0.91 | 0.133 (0.83) |
| | M1s | | 0.951 | 0.944 | 0.279 | 0.084 | 0.105 | 0.937 | 0.962 | 0.133 | 0.27 / 1.00 | 0.200 |
| NEW DENSE | F0 | 134 (36) | 0.833 | 0.691 | 1.050 | 0.331 | 0.396 | 0.849 (16) | 0.780 [0.67, 0.96] (2) | 0.216 (0.808) | 0.92 / 0.96 | 0.189 (0.58) |
| | G1s | | 0.897 | 0.817 | 0.373 | 0.110 | 0.091 | 0.934 | 0.735 [0.52, 0.99] | 0.054 (0.808) | 0.11 / 0.89 | 0.054 (0.73) |
| | M1s | | 0.887 | 0.793 | 0.381 | 0.119 | 0.116 | 0.906 | 0.820 | 0.243 | 0.14 / 0.77 | 0.081 |
| NEW (ORD + DENSE) | F0 | 205 (67) | 0.846 | 0.721 | 0.982 | 0.295 | 0.328 | 0.840 (23) | 0.857 [0.77, 0.97] (5) | 0.250 (0.816) | 0.94 / 0.96 | 0.212 (0.67) |
| | G1s | | 0.926 | 0.885 | 0.342 | 0.102 | 0.069 | 0.943 | 0.838 [0.69, 1.00] | 0.096 (0.816) | 0.13 / 0.90 | 0.077 (0.78) |
| | M1s | | 0.917 | 0.863 | 0.345 | 0.107 | 0.075 | 0.925 | 0.879 | 0.115 | 0.17 / 0.88 | 0.115 |
| POOLED | F0 | 447 (191) | 0.853 | 0.812 | 0.857 | 0.253 | 0.260 | 0.857 (46) | 0.826 [0.75, 0.90] (15) | 0.255 (0.802) | 0.88 / 0.98 | 0.214 (0.76) |
| | G1s | | 0.936 | 0.918 | 0.342 | 0.102 | 0.049 | 0.940 | 0.914 [0.85, 0.97] | 0.092 (0.802) | 0.17 / 0.92 | 0.082 (0.79) |
| | M1s | | 0.922 | 0.904 | 0.359 | 0.112 | 0.065 | 0.926 | 0.899 | 0.143 | 0.19 / 0.89 | 0.143 |

**Strata, POOLED** (G1s vs F0 AUROC):

| Stratum | F0 | G1s | Paired Δ (95 % CI) |
|---|---|---|---|
| h0, m1 | 0.840 | 0.932 | +0.092 [0.031, 0.152] |
| h0, m2–3 | 0.842 | 0.914 | – |
| h ≥ 1, m1 | 0.837 | 0.913 | +0.077 [−0.04, 0.18] |
| h ≥ 1, m2–3 | 0.795 | 0.905 | – |
| S0 start, h0 | 0.810 | 0.911 | – |
| static start (HYPSTART / DENSE), h0 | 0.894 | 0.950 | – |
| physically reached h ≥ 1, from S0 starts | 0.854 | 0.959 | – |
| physically reached h ≥ 1, from static starts | 0.775 | 0.826 (4 mixed families) | – |

**NEW panel h ≥ 1 by stratum.** Multi-action intermediate chunks at h ≥ 1 have **0** mixed families on the NEW panel, so there is no new evidence on them.

**Matched permutation concordance** (G1s vs F0), with very few discordant groups:

| Panel | F0 | G1s | Discordant groups |
|---|---|---|---|
| POOLED | 0.50 | 0.67 | 6 |
| NEW | 0.50 | 0.75 | 4 |

**MLP control.** M1s s0 behaves like G1s: NEW h ≥ 1 paired Δ +0.022 [−0.064, 0.104]. Graph structure remains not separable from the query-relative geometry features.

**Interpretation**
- **Where the improvement holds.** It replicates on new independent families at h0, especially first grasps: false positives at the model's own threshold fall from 13/52 to 5/52, and in DENSE scenes from 8/37 to 2/37.
- **Calibration.** It improves across all panels: NEW ECE goes from 0.33 to 0.07.
- **Where it does not.** The h ≥ 1 improvement is not replicated. The new h ≥ 1 panel is small (50 labels, 5 mixed families) and its point estimate is slightly negative. Most DENSE h ≥ 1 states were never reached.
- **Status.** Whether better first-grasp discrimination transfers to ordering was not tested, because R3.4 was not authorized.

## 3. Process incident (disclosed)

1. **Premature evaluation.** At 00:41 IST the R3.3A labels and gate were computed while the 195-job run was still in progress. A completion message for the run arrived early; I acted on it without checking the job count. That partial evaluation covered 144 labels, roughly 114 of 195 jobs. It returned R3_3A_PASS and was committed and pushed as `9a538428e2`.
2. **Unauthorized dispatch.** R3.4 FORMAL (39 queued jobs) and the K≤3 regression (60 jobs) were sealed (`df1e611f09`) and dispatched on the strength of that partial evaluation.
3. **Detection.** While writing this report, a label audit found 81 jobs with no labels. The run log confirms completion only after the evaluation (`P3D_DONE`, 195 jobs, 2,734.8 CPU-s).
4. **Correction.** Labels and gate were recomputed on all 195 jobs. The pre-registered rule gives **NOT_AUTHORIZED**.
5. **Stop.** The R3.4 and regression workers were stopped by PID at 00:46 IST.
6. **Completed before the stop:**

| Run | Jobs completed | CPU-h | Outcome file (sha16) |
|---|---|---|---|
| R3.4 | 20 | 0.197 | `0e1ea152f2c1caaa` |
| K≤3 regression | 29 | 0.151 | `f4933b3f3210df76` |

   Up to 10 in-flight jobs were killed without results; their CPU is not recorded and is estimated at ≤ 0.2 CPU-h.
7. **Quarantine.** Both outcome files and their logs are moved **unopened and write-protected** to gvlab2 `fig3/r3/QUARANTINE_unauthorized/`. They are **not analysed and not reported**. Whether to discard them or open them as owner-authorized diagnostics is an owner decision.
8. **What stays in the repository.**
   - The partial files are kept as `r33a/PARTIAL_*` for transparency. They must not be used.
   - The sealed R3.4 / regression manifests in `r34/` and `regr/` stay committed but are void.
   - The usage is charged to the R3.4 and regression reserves in the ledger.

## Figure

`figures/R3_3A_validation.png`:
- (a, b) AUROC by panel at h0 and h ≥ 1 for F0, G1s and M1s, with family-cluster CIs and mixed-family support.
- (c) First-relocation false positives.
- (d) F0 vs G1s pX on every NEW_DENSE label.
- (e–h) Actual R3.3A scenes with teacher outcomes:
  - a DENSE blocked first grasp: F0 1.00, G1s 0.16;
  - a physically reached h = 1 negative: F0 0.97, G1s 0.03;
  - a discordant D5/D6 matched permutation. G1s barely separates the executable enabler-first order (0.07) from the failing pivot-first order (0.06); F0 ranks them the wrong way (0.20 vs 0.26).

Reproduce (gvlab2):
```
$PYG data.py build33a 60 140
physical3d.py work jobs_33a_3d.json phys_33a_3d.jsonl 10 12 200 4.0
$PYG data.py labels 3d 33a
$PYG evaluate.py gate33a G1s 0 M1s 0
```
