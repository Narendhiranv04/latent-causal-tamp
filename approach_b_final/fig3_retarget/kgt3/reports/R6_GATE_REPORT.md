# LEGOLAS R5.1–R6: consolidated development report at the R6 gate

**Branch:** `naren/rss27-fig3-retarget-home` (unmerged)
**Commits:** from `85708dcda2` (R5.0 approval) to this report's commit

**Controlling documents** (all committed before the outcomes they govern):
- `LEGOLAS_R5_R8_completion_plan.md` (owner);
- `kgt3/R5_PREREG.json`;
- `reports/R5_3_RULES.md` with Addendum A (cVAE recovery) and Addendum B (S2 correction);
- `reports/R5_R6_ALLOCATION_REQUEST.md`.

**Status.**
- Everything here is **development evidence** on exposed DEV roots or newly constructed development families. It is not confirmation.
- There was no protected TEST or release_v2 access (not even metadata) and no K > 5 experiment.
- No production artefact was modified.
- All trained models are development checkpoints. Final models will be trained cleanly in R7.

## Gate classification

| Domain × method | Status | Evidence |
|---|---|---|
| **3D Fig. 3A (REC-ORDERED)** | **DEV_PHYSICALLY_DEMONSTRATED** | 11/20 strict success. 9 with more than 3 actions (6 with 4, 3 with 5). Committed non-oracle plans; replay-verified. |
| **3D Fig. 3B (GA)** | **DEV_PHYSICALLY_DEMONSTRATED** | 12/20 strict success, all with more than 3 actions (7 with 4, 5 with 5). EXACT on 14/20 roots, BOUNDED elsewhere. |
| **2D Fig. 3A (REC-ORDERED)** | **DEV_IMPLEMENTED; physically BLOCKED** under the preregistered configuration | 0/20 dense, 0/12 demonstration. Only one *post-hoc* (S0) 5-action success, which does not count. |
| **2D Fig. 3B (GA)** | **DEV_IMPLEMENTED; physically BLOCKED** | 0/20 dense, 0/12 demonstration, 0/12 post-hoc. |

**2D blockers, measured separately:**
1. **Selection / terminal-Y extrapolation.** The preregistered S2 rule (τ_E from K ≤ 3 successes) commits 1–2-action plans that execute but never restore the target.
2. **Teacher decidability.** 40–50% UNRESOLVED on dense roots and 8–9/12 on long plans in 9–13-object scenes. The mechanism is online-planner incompleteness, not budget; the teacher contract and budgets were not changed.
3. **Placement proposals.** Frozen cVAE recursive-union recall is 0.31 vs 0.57 for uniform exploration. The bounded recovery failed (0.20–0.25).

Local executability (X) is **not** the 2D blocker: G1 VAL AUROC 0.98 and matched-order concordance 0.96.

## 1. Implementation changes and regression tests

| Change | Why | Test |
|---|---|---|
| **R5.0 (audited and fixed earlier; `R5_0_AUDIT.md`)** | | |
| Budget stops keep completed incumbents | Timeouts discarded all candidates | `test_timeout_midway_keeps_completed_incumbent` |
| Floor inside the single deadline and timing | Fallback cost was excluded | `test_floor_inside_deadline_and_no_budget_left` |
| One absolute deadline for REC / GA | Split budgets | – |
| Empty pool → ABSTAIN | Crash risk | `test_empty_candidates_abstain` |
| H = 5 both domains | 2D used 6 | `test_r5_rows.py` |
| **R5.1 budget amendment (owner request)** | | |
| Declared selection reserve (5 s, 64 X / 8 Y readouts) spent **inside** the total caps; caps are never lifted | Selection previously lifted caps | `test_cap_stop_then_selection_is_uncapped_and_counted` (now asserts selection ≤ reserve and total ≤ cap) |
| Search deadline = t_end − reserve; deadline checked before every model batch (`Scores.need`) and every GA assignment | The test found overruns of a whole 256-assignment block | `test_search_deadline_reserves_selection_time` |
| TIMEOUT_NO_INCUMBENT distinct from ABSTAIN; `budget_stop`, `deadline_overrun_s`, `cap_overrun`, `floor_counters`, `search` / `select` / `floor` wall times reported | Outcome distinguishability | `test_timeout_without_incumbent_is_distinct_from_abstain` |
| **R5.2 / R5.3 options (all default-off; production behaviour unchanged)** | | |
| `xlearn` A / M / G fresh X heads, ORDINV / UNCOUPLED / DIRECT controls, Y bitwise assert | Controlled ablation | `ysha` assert in every run |
| Temperature calibration wrapper (a / T, (a + w) / T) | R5.3 | – |
| Proposal modes TOP8 / ANC64 / UNIF (opt-in) | R5.3 | – |
| S2 selection (Addendum B: full-energy statistic) | R5.3 | `test_s2_rule_*`, `test_s2_energy_statistic_respects_terminal_y` |
| Recursive admission margin / eta (`recursive.admits`) | R5.3 | `test_admission_rules_default_unchanged_and_margins` |
| Defects found and fixed during R5 | empty-X replay batch (no grad), DIRECT validation metric, `taskset` CPU list, snapshot link of the isolated cVAE root | – |

**Tests:** **58 pass on gvlab2**: 30 R4 / R5 unit tests, 20 KGT3, 6 real-row contract tests, 2 learn. 50 of them also run locally.

**Leakage safeguards (R5.0 PASS, unchanged since):** the import guard poisons 23 physical modules, sentinel evaluator fields were never read, and plans are invariant to metadata stripping and root-ID renaming. Every planner reads only `{ids, xy0, cells0, attrs, tid, goal, goal_cell, base, ctx, legal_cells, q_ref, cell_xy}`.

## 2. R5.1 local supervision

**Collected** (sealed rosters before outcomes; unchanged teachers and budgets; fresh cache per query):

| | 2D (BXY, full articulated planar arm) | 3D (SHELF66V3) |
|---|---|---|
| Families attempted | 70 (`R5.1-2D-F000..069`) | 60 fresh families (KGT3 and R4.4 excluded) |
| Dependencies constructed | 68 (37 two-level, 31 three-level) | 49 (28 two-level, 21 three-level); 11 had no verified level 2 |
| Teacher queries / jobs | 1,775 queries (853 SUCCESS, 565 CERTIFIED, 357 UNRESOLVED) | 888 probes + 887 jobs (X: 218 SUCCESS, 401 certified, 104 budget, 1 operational; Y interventions: 37 / 103 / 23) |
| New strict labels after a preceding relocation | h1 g3 **+66 / −42**; h2 g2 **+62 / −19**; h2 g3 present | h1 g2 +51 / −59; h1 g3 +12 / −51; h2 +11 / −49; h3 +2 / −4 |
| Physical CPU | 4.09 CPU-h | 2.36 (construction) + 4.36 (jobs) CPU-h |

**How the 2D gaps were filled.** The 2D intermediate states come from verified relocations of each family's own cage walls, with no added bodies. These prefixes precede matched permutations of the dependency chunk. A long rollout only supplies the starting state; **every supervised sequence is a chunk ≤ 3** (asserted in `xlearn.build`).

**Label policy.**
- ADDITIONAL supervision is strict: replayed positives and certified negatives only.
- UNRESOLVED, budget-relative (NO_PLAN_FOUND) and operational outcomes are kept as such and never used as negatives.
- The original v32 replay keeps its historical contract.
- Historical R3.1 / KGT3 labels were audited under their own contract. Strict filtering dropped:
  - R3.1 3D: 99 budget-relative negatives and 124 un-replayed or uncertified "positive prefixes";
  - KGT3 3D: 51 budget and 8 operational negatives;
  - KGT3 2D: 644 UNKNOWN runs (`r5/xl/data_*.json` `audit`).

**Splits.**
- Family-level VAL assignment for new families, fixed before outcomes: `sha256('R5.1-split|' + family) < 0.40`.
- R3.1, KGT3 (except the 2D GATE), R4.3 and R4.4 are TRAIN only.
- 2D VAL also uses the KGT3 P2 2D GATE families, which no model had read before (disclosed).
- The demonstration families (`R6-2D-DEMO*`) and every R4.2 / R4.5 / coh2d DEV root are excluded from training and selection.
- The family-disjointness assert passed.

| VAL support (preregistered minima) | 2D | 3D |
|---|---|---|
| VAL families (≥ 20) | **101** | **26** |
| VAL matched discordant groups (≥ 30) | **70** | **64** |
| VAL families with h ≥ 1 multi-action labels (≥ 10) | **79** | **24** |
| TRAIN families | 136 | 269 |
| Minima met | yes | yes |

No further targeted collection was needed.

## 3. R5.2 controlled X learning

**Protocol.**
- **Fixed:** Y path and cVAE frozen (bitwise-asserted every run); fresh X initialisation; original observed-data likelihood with unknown X / Y marginalised; family-balanced local sampling with original replay batches; no O2 ranking loss; no history or provenance features.
- **Recipe check** (seed 0, + strict local data):
  - lr 1e-3 beat 1e-4 for every representation in both domains;
  - the 1e-4 MLP did not converge in 60 epochs (best epoch 59), confirming the owner's warning;
  - every chosen-recipe run converged before its cap except one DIRECT control seed (3D s1, epoch 59; control only).
- **Selection:** VAL family NLL only; the simplest representation within max(seed spread, 0.005) of the best.

**VAL family NLL (two seeds), chosen recipe lr 1e-3:**

| | A0 | A1 | M0 | M1 | G0 | **G1** |
|---|---|---|---|---|---|---|
| 2D | 0.450 / 0.467 | 0.423 / 0.418 | 0.440 / 0.470 | 0.416 / 0.333 | 0.357 / 0.366 | **0.264 / 0.227** |
| 3D | 0.679 / 0.683 | 0.570 / 0.591 | 0.616 / 0.595 | 0.578 / 0.381 | 0.583 / 0.598 | **0.230 / 0.243** |

(A = original ordered X modules re-initialised; M = query-relative MLP; G = query-relative GNN; 0 = original replay only; 1 = + strict local.)

**Selected:** **G (query-relative GNN) in both domains.** The margin over M (2D 0.129, 3D 0.244 in seed-mean NLL) is 3.5× and 19× the selection tolerance. The checkpoint was chosen by VAL NLL: 2D `2d_G1_hi_base_s1`, 3D `3d_G1_hi_base_s0`. Additional strict local supervision is necessary: G0 → G1 drops NLL from 0.36 → 0.25 (2D) and 0.59 → 0.24 (3D).

**Selected-model VAL metrics:**

| | AUROC | AUPRC | ECE | Matched-order concordance (all / h ≥ 1) | h ≥ 1 multi-action AUROC |
|---|---|---|---|---|---|
| 2D | 0.979 | 0.985 | 0.039 | 0.962 / 0.897 | 0.929 |
| 3D | 0.966 | 0.959 | 0.034 | 0.977 / 0.941 | 0.956 |

For comparison, the best A1 has concordance 0.64 (2D) and 0.89 (3D); the best M1 has 0.90 and 0.94.

**Controls** (on G1, two seeds):

| Control | 2D VAL NLL | 3D VAL NLL | Reading |
|---|---|---|---|
| Order-invariant (actions canonically sorted) | 0.301 / 0.313 | 0.454 / 0.468 | **Ordering is essential**; concordance 0.5 by construction |
| Uncoupled (w = 0) | 0.275 / 0.206 | 0.233 / 0.211 | **No established coupling effect on local X** (within seed spread), consistent with the K3 ablation |
| Direct short-sequence success (BCE on observed replay success) | K ≤ 3 success AUROC 0.83 / 0.85 vs coupled G1 0.77 / 0.79 | 0.90 / 0.92 vs 0.92 / 0.92 | Competitive on short success ranking, but it **yields no marginal X**, so it cannot drive the long composition. No long-horizon direct supervision was invented. |

**K ≤ 3 regression** (original VAL roots): G1 short-success AUROC is 2D 0.77–0.79 and 3D 0.92, against 0.73–0.79 and 0.86–0.87 for the A heads. Y is identical. The production artefacts are untouched; R6 B0 uses them.

**Physical ordering diagnostic** (R4.2 protocol: 20 exposed 3D roots, witness assignment given, one sealed order + partition per arm; 46 new runs, 68 exact reuses; 0.50 CPU-h):

| Arm | Strict success | First action correct | Physical concordance (95 pairs) | Paired vs F0 |
|---|---|---|---|---|
| **G1 (selected)** | **15/20** | 13 | **0.97** | 13–0 (p = 0.0002) |
| M1 | 12/20 | 11 | 0.77 | 11–1 |
| A1 | 6/20 | 5 | 0.59 | 4–0 |
| F0 (production) | 2/20 | 3 | 0.36 | – |
| RANDOM / WITNESS | 3 / 18 | – | – | – |

The local NLL ranking (G < M < A) reproduces exactly in physical ordering. The GNN improvement over the earlier R3 G1s (11/20) comes with the strict expanded local data.

## 4. R5.3 energy, calibration, proposals and admission

All of this is model-only on the DEV roots for the selected X. The rules were committed before any of these numbers (`R5_3_RULES.md`).

**Calibration.**
- 2D: temperature T = 0.753 is **adopted**; VAL NLL 0.2271 → 0.2213.
- 3D: T = 0.949 is not adopted (Δ < 0.005).
- Both models are already well calibrated (ECE about 0.035–0.04). The reliability diagrams (`R5_2_xlearning.png` d / h) show mild **under**-prediction in the mid range. Calibration rescales a and a + w jointly, so marginal pX and p11 are recomputed consistently.

**Energy by length** (`R5_3_scoring.png` a / e; `r53/length_*`):
- **2D:** best E is non-increasing in assignment size on **95%** of DEV roots. The selected G1 still prefers over-long plans: −log Y_global falls from 5.7 to 0.1 while the composed X cost stays below about 0.4.
- **3D:** non-increasing on only **45%** of roots, so the R4.0 over-long bias (audited with O2) **does not hold for G1**.
- **`has_multi`:** the constraint binds (changes the optimum) on 20/40 (2D) and 19/37 (3D) long assignments. It remains the primary policy, and the all-singleton-inclusive objective is recorded as a named diagnostic.
- **Terminal Y on 4–5 edits** is an extrapolation of a Y trained on ≤ 3 edits. It is monotone in the number of moved objects, which is the source of the 2D length bias.

**Selection.** By rule:
- 2D uses **S2**: the shortest reliable candidate, else argmin E.
- 3D uses **S0**: the original argmin E.
- **Addendum B (disclosed specification correction, before any R6 2D plan).** The S2 statistic as first written was X-only and **degenerated to 1-relocation plans on 40/40 roots**. It was corrected to the full energy E with τ_E = 2.43, the 95th percentile of −log p11 over 719 observed original K ≤ 3 VAL successes. Sanity check (model-only): S0 picks 5, 5, 5, 5, 4; S2 picks 4, 4, 3, 3, 2.

**Recursive admission** (paired physical temporary-target labels; same families in every denominator; VAL = R5.1 VAL families):

| 3D rule (VAL) | True admission (useful enablers) | False admission (irrelevant / harmful) |
|---|---|---|
| A0 `beats_empty` | 0.89 (17/19) | **0.56** (19/34) |
| A1 m = 0.05 | 0.74 | 0.35 |
| **A1 m = 0.10 (chosen)** | **0.68** | **0.21** |
| A1 m = 0.20 | 0.58 | 0.15 |
| A2 (m = 0, + p11 ≥ 0.3) | 0.53 | 0.06 |

- **3D:** no margin met both targets (true ≥ 0.80, false ≤ 0.20), so the error-minimising m = 0.1 was chosen. A2 lowers false admission further but costs more than 0.05 of true admission, so it was not adopted. TRAIN and EXPOSED (R4.4) show the same pattern.
- **2D:** only useful-enabler labels exist (cage probes). A0 true admission is 1.00 on VAL (22/22), and the 3D margin would cost 0.14, so **A0 is kept**. 2D false admission is **not measurable** with the current data.

**Proposal coverage** (witness-action recall on DEV; the witness is one valid repair, not necessarily the only one):

| Mode | 3D GA pool | 3D REC union | 2D GA pool | 2D REC union | 3D REC median wall |
|---|---|---|---|---|---|
| S1 top-4 (production) | 0.51 | 0.83 | 0.04 | 0.17 | 2.3 s |
| TOP8 | 0.61 | 0.87 | 0.05 | 0.19 | 7.9 s |
| **ANC64** (REC local resampling) | 0.61 | **0.90** | 0.07 | **0.31** | 7.1 s |
| UNIF (labelled exploration control) | 0.55 | 0.95 | 0.18 | 0.57 | 9.4 s |

- **Chosen:** GA keeps S1 in both domains (TOP8 drops the 3D exact envelope from 14/20 to 3/20 roots). REC uses ANC64 in both.
- **2D cVAE recovery (Addendum A, conditionally authorised experiment).** It was triggered because the best frozen REC recall was 0.31 < 0.5, and the *uniform* control reached 0.57, more than the learned sampler. The recovery used the original staged recipe from fresh initialisation in an isolated root: Q2 placement pretraining, then `q2init_all` task fine-tuning.
  - R-ORIG (original data): REC recall **0.20**.
  - R-LOCAL (+ 152 verified local single-action repairs from TRAIN families): **0.24**.
  - Frozen production sampler: 0.31.
  - **Not adopted** (the adoption bar was +0.10). Retraining alone loses coverage, and 152 local examples next to 6,317 original ones do not move the learned distribution toward the parking cells that 2D repairs need. **2D proposal coverage remains an unresolved limitation of the learned sampler.**

**Frozen R6 configuration** (`r5/r6/config.json`):

| | Model | Selection | Admission | GA pool | REC proposals |
|---|---|---|---|---|---|
| 2D | `2d_G1_hi_base_s1` (T = 0.753) | S2, τ_E = 2.429 | A0 | S1 | ANC64 |
| 3D | `3d_G1_hi_base_s0` (raw) | S0 | A1, m = 0.1 | S1 | ANC64 |

## 5. R6 physical development evaluation

### 3D (20 exposed DEV roots, L_ref 4 / 5; `r5/r6/R6_3d.json`, `figures/R6_3d.png`)

**Protocol.**
- One committed plan per root and arm, sealed (`plans_3d.jsonl.SEAL`) before any teacher query.
- Unchanged teacher with X_CHUNKED (q_ref connectors at every chunk boundary) + endpoint Y + independent continuous replay.
- No retries or replacement. Exact archived outcomes are reused only for identical (root, ordered names, bounds) keys.
- 63 new runs, 0.72 CPU-h.

| Arm | Strict success [Wilson 95%] | > 3 actions (L4 / L5) | X / Y / replay = 1 | Certified / budget / operational / no-repair | L_pred histogram | Planning wall median / p90 / mean (s) | Verification wall (median) | Budget stops | New / reused runs |
|---|---|---|---|---|---|---|---|---|---|
| B0 historical K≤3 (production F0) | **2/20** [0.03, 0.30] | 0 (0 / 0) | 4 / 9 / 2 | 7 / 6 / 0 / 3 | {'0': 3, '2': 2, '3': 15} | 0.2 / 0.5 / 0.2 | 22.6 s | 0 | 0 / 17 |
| H3 selected G1, K≤3 rule | **4/20** [0.08, 0.42] | 0 (0 / 0) | 7 / 7 / 4 | 5 / 4 / 0 / 4 | {'0': 4, '2': 1, '3': 15} | 0.2 / 0.4 / 0.2 | 29.0 s | 0 | 12 / 4 |
| Flat search H5 | **6/20** [0.15, 0.52] | 5 (4 / 1) | 8 / 15 / 6 | 1 / 11 / 0 / 0 | {'2': 1, '3': 6, '4': 9, '5': 4} | 4.8 / 9.9 / 5.4 | 38.0 s | 0 | 19 / 1 |
| **Fig. 3A REC-ORDERED H5** | **11/20** [0.34, 0.74] | 9 (6 / 3) | 11 / 19 / 11 | 0 / 9 / 0 / 0 | {'2': 1, '3': 3, '4': 6, '5': 10} | 5.5 / 10.0 / 5.6 | 35.4 s | 0 | 19 / 1 |
| **Fig. 3B GA H5** | **12/20** [0.39, 0.78] | 12 (7 / 5) | 13 / 17 / 12 | 2 / 5 / 0 / 0 | {'4': 13, '5': 7} | 21.4 / 133.0 / 45.2 | 39.6 s | 0 | 18 / 2 |

**Paired (exact sign test):**

| Comparison | Gain–loss | p |
|---|---|---|
| REC vs flat | 5–0 | 0.062 |
| GA vs flat | 6–0 | 0.031 |
| REC vs GA | 4–5 | n.s. |
| REC vs H3 | 7–0 | 0.016 |
| GA vs H3 | 9–1 | 0.021 |
| H3 vs B0 | 2–0 | 0.50 |

At least one Fig. 3 planner succeeds on **16/20**.

**By reference length** (success / roots):
- REC: {'4': [8, 10], '5': [3, 10]}
- GA: {'4': [6, 10], '5': [6, 10]}
- flat: {'4': [4, 10], '5': [2, 10]}

**Reading.**
- Both compositional planners physically demonstrate replay-verified 4- and 5-action repairs from committed, non-oracle plans.
- Each clearly exceeds the same model restricted to H ≤ 3 (horizon effect isolated: REC 7–0, GA 9–1) and the flat H5 control (REC 5–0, GA 6–0).
- REC vs GA is not distinguishable (4–5).
- **Every remaining REC failure is budget-relative** (NO_PLAN_FOUND at relocation). GA has 5 budget-relative and 2 certified failures. The residual 3D gap therefore lies largely in the teacher's per-query planning budget and executable placements, not certified infeasibility.
- Fig. 3A is about 4× cheaper to plan than Fig. 3B (median 5.5 s vs 21 s; GA p90 133 s, with EXACT on 14/20 and BOUNDED elsewhere).
- No committed plan is the known witness assignment set.
- Repairs are not claimed minimal. A long executed repair does not prove a long repair was required.
- **Earlier anchors on the same roots:** R4.5 REC 10, GA 9 (R3 G1s, KGT3 objective); now REC 11, GA 12 with the clean-recipe development G1, the R5 budget fixes and the R5.3 rules.

### 2D: dense DEV panel (20 coh2d roots with L_ref 4–5, N 14–20; `R6_2d.json`)

**Pilot (preregistered stop: more than 50% UNRESOLVED in 10 jobs):** 5 UNRESOLVED / 4 CERTIFIED / 1 VERIFIED, i.e. exactly 50%. This is **not above** the threshold, so the full panel was evaluated by rule.

| Arm | Strict success | X / Y / replay = 1 | Unresolved / certified / no-repair | L_pred | Planning median / p90 (s) |
|---|---|---|---|---|---|
| B0 | 0/20 | 0 / 3 / 0 | 3 / 7 / 10 | {'0': 10, '3': 10} | 5.3 / 6.5 |
| H3 | 0/20 | 0 / 0 / 0 | 7 / 2 / 11 | {'0': 11, '3': 9} | 6.8 / 8.2 |
| flat H5 | 0/20 | 1 / 0 / 1 | 10 / 6 / 3 | {'0': 3, '1': 1, '2': 5, '3': 7, '4': 4} | 68.1 / 91.1 |
| Fig. 3A REC | 0/20 | 1 / 0 / 1 | 9 / 7 / 3 | {'0': 3, '1': 1, '2': 5, '3': 7, '4': 1, '5': 3} | 71.4 / 104.0 |
| Fig. 3B GA | 0/20 | 4 / 1 / 4 | 9 / 7 / 0 | {'2': 6, '3': 10, '4': 4} | 53.7 / 100.6 |

### 2D: held-out moderate-density demonstration roots (12; N 9–13; L_ref 4 ×9, 5 ×3; `R6_2d_demo.json`)

These roots are never used for training or selection, and are never pooled with the dense panel.

| Arm | Strict success | X / Y / replay = 1 | Unresolved / certified / no-repair | L_pred | Planning median / p90 (s) |
|---|---|---|---|---|---|
| B0 | 0/12 | 5 / 0 / 5 | 3 / 4 / 0 | {'2': 5, '3': 7} | 2.0 / 2.2 |
| H3 | 0/12 | 6 / 0 / 6 | 6 / 0 / 0 | {'1': 2, '2': 3, '3': 7} | 2.3 / 2.5 |
| flat H5 | 0/12 | 4 / 0 / 4 | 8 / 0 / 0 | {'1': 6, '2': 6} | 32.9 / 42.5 |
| Fig. 3A REC | 0/12 | 4 / 0 / 4 | 8 / 0 / 0 | {'1': 6, '2': 6} | 38.4 / 47.0 |
| Fig. 3B GA | 0/12 | 6 / 0 / 6 | 5 / 1 / 0 | {'1': 6, '2': 6} | 85.9 / 94.4 |

**Reading (primary, preregistered).**
- 2D is **not physically demonstrated**: 0/20 and 0/12 for every arm.
- **Demonstration roots.** Under the frozen 2D configuration (S2 shortest-reliable with τ_E from K ≤ 3 successes), **every committed plan has 1–2 relocations**, although every root's verified reference repair needs 4–5. The short plans often execute (X = 1 on 4–6 roots) but never restore the target (Y = 0 throughout). The frozen 2D Y and calibrated X give p11 ≥ 0.09 to short repairs that are physically insufficient, so the K ≤ 3-derived threshold is too permissive for 2D.
- **Dense panel.** Teacher decidability dominates: 9–10 UNRESOLVED per long arm, plus certified-infeasible plans, on top of proposal coverage (REC-union recall 0.31).
- **The three 2D bottlenecks, measured separately:**
  1. Teacher decidability: UNRESOLVED 40–50% in dense scenes; the dominant mechanism is online-planner incompleteness, not budget (R4.3 audit).
  2. Local executability: solved at the local level (G1 VAL AUROC 0.98, concordance 0.96).
  3. Placement proposals: the frozen cVAE recalls only 0.31 of reference actions; uniform exploration reaches 0.57; the bounded recovery failed.
- **The selection or Y-extrapolation issue** (short plans with optimistic p11) is a fourth, newly identified blocker.

### 2D post-hoc diagnostic: original S0 selection on the 12 demonstration roots (`r5/r6_posthoc_s0/`; **chosen after observing the R6 2D primary outcomes; not a primary result, never pooled**)

**Purpose.** Separate the selection-rule blocker from the X / Y / teacher / proposal blockers. Configuration is identical to the frozen R6 2D configuration except S0 instead of S2. Plans were sealed before jobs; 52 new runs, 0.17 CPU-h.

| Arm | Strict success | > 3 actions | X / Y / replay = 1 | Unresolved / certified | L_pred |
|---|---|---|---|---|---|
| B0 | 0/12 | 0 | 5 / 0 / 5 | 3 / 4 | {'2': 5, '3': 7} |
| H3 | 0/12 | 0 | 6 / 0 / 6 | 6 / 0 | {'1': 2, '2': 3, '3': 7} |
| flat H5 | 1/12 | 1 | 4 / 1 / 4 | 8 / 0 | {'1': 2, '2': 2, '3': 2, '4': 6} |
| Fig. 3A REC | 1/12 | 1 | 3 / 3 / 3 | 9 / 0 | {'1': 2, '2': 2, '3': 1, '4': 1, '5': 6} |
| Fig. 3B GA | 0/12 | 0 | 4 / 1 / 4 | 8 / 0 | {'1': 2, '2': 1, '4': 5, '5': 4} |

**Reading.**
- With S0 the 2D planners commit long plans: REC 4–5 actions on 7/12 roots, GA on 9/12.
- **Fig. 3A REC produces one replay-verified 5-action repair** on the sparsest root (G032, N = 9); flat succeeds there too with a 4-action plan.
- REC reaches endpoint Y = 1 on 3 roots. The dominant outcome is now **UNRESOLVED (8–9/12): the unchanged 2D teacher cannot decide most long plans in 9–13-object scenes.**
- **2D blocker order is therefore:** selection or Y extrapolation (S2 short plans: target never restored), then teacher decidability for long plans, then proposal coverage.
- This single post-hoc success is not a physical demonstration of 2D.


## 6. Resources

**Machine use.** All compute ran on gvlab2 (48 cores, RTX 5090 32 GB, 125 GB RAM). The local machine was used only for git, figures and reports, because /home there had 1.4 GB free (below the 20 GiB floor) and no GPU was visible. No unrelated process was touched.

| Item | Used | Authorised |
|---|---|---|
| Physical teacher CPU | **15.1 CPU-h** — R5.1 2D 4.09; 3D 2.36 + 4.36; demonstration construction 1.26 + 0.91; smoke tests 0.36; R5.2 ordering 0.50; R6 3D 0.72; R6 2D 0.22 + 0.10; post-hoc 0.17 | 40 |
| Summed GPU process wall | **≈ 6.4 h** (training ≈ 0.6, R5.3 diagnostics ≈ 2.7, recovery and evaluation ≈ 0.8, R6 planning ≈ 2.0, R5.0 audits ≈ 0.5); mostly CPU-bound DP with a GPU model resident | 10 |
| GPU device occupancy (wall-clock union) | ≈ 3.5 h; peak VRAM ≈ 11 GB with 7 concurrent planners | – |
| Peak host RAM | ≈ 23 GB used of 125 GB; no swap pressure; load ≤ 27 of 48 cores | – |
| Wall clock | R5.1 → R6 gate about 3.3 h, plus R5.0 about 0.4 h | 12 h |
| New storage | about 0.25 GB on gvlab2 (`kgt3/r5`, witnesses, cVAE runs) + about 25 MB in git (GIFs about 21 MB); /home free 33 GB | 4 GiB |

**Planning latency** (synchronized, floor and selection included):
- 3D medians: REC 5.5 s and GA 21 s (p90 10 s and 133 s).
- 2D medians: REC 38–71 s and GA 54–86 s (p90 ≤ 105 s). No deadline overruns beyond one model batch were recorded.

**Verification:** median 3D run 30–40 s CPU; 2D 2–30 s.

## 7. Deviations, limitations and unsuccessful experiments

**Deviations (all disclosed in the commit history and here):**
1. **Addendum B: S2 specification correction.** The preregistered S2 used an X-only reliability statistic and degenerated to 1-relocation plans (model-only, before any R6 2D plan). It was corrected to the full energy with τ_E from original K ≤ 3 VAL successes. In R6 2D the corrected rule still commits too-short plans, which is itself a reported negative result.
2. **R6 2D post-hoc S0 diagnostic.** Chosen after observing the 2D primary outcomes, explicitly labelled, and never pooled.
3. **2D demonstration construction.** The first two designs failed in smoke tests (two-wall cages do not exist under the greedy cage; unverified destinations are unresolved). The third design is pick + place cages with verified steps. Yield: 12/100 attempted families.
4. **2D VAL** includes the KGT3 P2 2D GATE families, which no model had read; they are dense generator scenes, a different distribution from the R5.1 constructions.
5. **R5.2 driver bug.** Replay-only batches without X queries had no gradient, which crashed the run. Fixed and resumed; completed runs were reused by name.
6. **The local machine was not used** (storage).
7. **The 2D dense pilot sat exactly at 50% UNRESOLVED.** That is not above the threshold, so the full panel ran.

**Limitations.**
- All evaluation roots are exposed development roots. The 3D DEV panel has been used across R2–R6, including model and configuration selection (R5.3 coverage, length and admission diagnostics ran on it).
- 3D VAL has 26 families. Each configuration had two seeds.
- The X / Y coupling effect is not established.
- The direct-success control cannot be compared on long horizons.
- Admission false-admission rates in 2D are unmeasurable with current labels.
- Terminal Y on 4–5 edits is an extrapolation.
- No minimum-K claims: L_ref is a verified reference length, not K*.

**Unsuccessful experiments, kept:**
- 2D cVAE recovery (not adopted);
- the first S2 definition;
- 2D demonstration designs 1–2;
- R6 2D primary (0/32).

## 8. Recommendation for R7 / R8 (not started; requires owner approval)

**Is additional independent K4/5 evaluation data justified?** Yes, at least for 3D.
- Every current K4/5 evaluation root is exposed. The 20 3D DEV roots were used for model, configuration and planner development from R2 to R6, so they cannot support confirmation.
- 2D should not proceed to a costly independent cohort until its three blockers are addressed.

**Proposed R7 (separate owner approval).**

1. **Frozen design** from the R5 / R6 evidence:
   - query-relative GNN X head (G);
   - original observed-data likelihood with strict local data;
   - Y frozen from a freshly trained base;
   - lr 1e-3, ≤ 60 epochs, patience 10;
   - selection by local VAL NLL;
   - H = 5, `has_multi` primary;
   - 3D S0 selection, A1 admission with m = 0.10, GA S1 top-4 pool, REC ANC64 local resampling;
   - planner budgets unchanged (180 s with floor and selection reserve inside).

2. **2D, before any 2D R7 training,** a bounded 2D development cycle (R6b), owner decision required:
   - (a) the teacher-decidability question (contracts may not change silently: this needs an explicit owner decision on whether a larger online-planner budget or a certified alternative is permissible);
   - (b) a larger local placement corpus for a fresh cVAE (at least about 1,500 verified local repairs from witness-first construction, about 6 CPU-h);
   - (c) S2 / τ redefinition evidence from verified local *long-endpoint-free* data.

   Otherwise R7 / R8 proceed for 3D only, with 2D reported as BLOCKED.

3. **Clean training from random initialisation, per domain** (no development checkpoint inheritance):
   - Q2 placement pretraining → `q2init_all` task fine-tuning (production recipe), seeds 0, 1, 2, or keep the released cVAE if the owner prefers to isolate the X change;
   - fresh base XYNet (arm D, original recipe) seeds 0, 1, 2 → freeze its Y;
   - fresh G X head on original + strict local TRAIN (R3.1 / KGT3 / R4.3 / R4.4 / R5.1 TRAIN), with VAL families for selection only, seeds 0, 1, 2;
   - seed and checkpoint chosen by VAL NLL only; temperature on VAL;
   - estimated ≤ 2 GPU-h.

4. **Independent 3D cohort (R8)** with the existing SHELF66V3 K45 generator + witness pipeline on fresh family seeds:
   - target 40 roots (about 20 with L_ref 4 and about 20 with L_ref 5); a certified K* stratum only where a sound lower bound exists;
   - attempted-family budget fixed in advance; rejected families recorded;
   - estimate about 12–18 CPU-h construction;
   - sealed roster quarantined from developers.

5. **R8 evaluation:**
   - arms B0, H3, flat H5, Fig. 3A H5, Fig. 3B H5 on the sealed cohort;
   - one committed plan per root and arm; teacher, replay and budgets unchanged;
   - all-root strict success (UNKNOWN counted as not verified), > 3-action success, L_pred / L_exec, failure taxonomy, latency (median / p90 / mean), search counters, paired sign tests and family-aware intervals;
   - estimated about 2 GPU-h planning + 3–4 CPU-h verification;
   - **protected TEST / release_v2 access only with explicit separate authorisation.**

## 9. Reproducibility

All commands run on gvlab2 with `source $FIG3/env.sh` and `cd $CODE/fig3_retarget/kgt3`.

```
# R5.1 data (sealed rosters)
B2D_OUT=$FIG3/kgt3/r5/b2d B2D_PREFIX=1 $PY2D build2d.py roster 70 R5.1-2D-F && ... build2d.py work 8 2 6.0
D3D_OUT=$FIG3/kgt3/r5/d3d D3D_NS=R5.1 D3D_ZTRY=8 $PY3D deep3d.py construct 8 10 6.0 60 && $PY3D deep3d.py jobs
$PY3D ../physical3d.py work $FIG3/kgt3/r5/d3d/jobs.json $FIG3/kgt3/r5/d3d/phys.jsonl 12 14 900 8.0
B2D_OUT=$FIG3/kgt3/r5/demo2d{,_b} B2D_DEMO=1 $PY2D build2d.py work 8 26 2.5
# R5.2
$FIG3/kgt3/r5/r52.sh 2d ; $FIG3/kgt3/r5/r52.sh 3d          # data -> recipe -> matrix -> select -> controls
ORD_OUT=$FIG3/kgt3/r5/order3d ORD_SPECS=G1new=XL:3d_G1_hi_base_s0,... ORD_PARTITION=0 $PYG order_phys.py plan; $PY3D order_phys.py jobs 100
# R5.3
$PYG r53.py calib 2d 2d_G1_hi_base_s1 ; ... length / admission / proposals ; $PYG r53.py tauE 2d XL:2d_G1_hi_base_s1@T=0.7535 ; $PYG r53.py decide
ABF_ROOT=$FIG3/kgt3/r5/cvae_root V3OUT=$FIG3/kgt3/r5/cvae_runs $PYG cvae_rec.py run
# R6
R6_SHARD=i/n $PYG r6.py plan {3d|2d|2d_demo} $FIG3/kgt3/r5/r6/config.json ; $PY2D r6.py merge POP n ; r6.py jobs POP CAP
$PY{2D,3D} ../physical{2,3}d.py work jobs_POP.json phys_POP.jsonl W CPU_LO MAX MAXH ; $PY2D r6.py analyze POP
python figs.py {r5xl|r53fig|r6fig 3d|r6fig 2d|r6fig 2d_demo}
```

**Artifacts:**
- `kgt3/reports/r5/` (manifests, seals, raw per-root records, selections, configs, curves);
- `kgt3/reports/figures/R5_2_xlearning.png`, `R5_3_scoring.png`, `R6_3d.png`, `R6_2d.png`, `R6_2d_demo.png`;
- GIFs in `kgt3/reports/figures/gifs/` (`R5`/`R6` prefixed), all actual logged teacher records:
  - 3D: MuJoCo re-execution of stored witnesses;
  - 2D: certified joint records drawn with the teacher's robot geometry.

**Checkpoint hashes (development only):**
- 2D `2d_G1_hi_base_s1` sha256 `da3ad74f…`; 3D `3d_G1_hi_base_s0` `ed59aebc…`, in `$FIG3/kgt3/r5/xl/ckpt/` with `curve.json` per run;
- recovery cVAEs in `$FIG3/kgt3/r5/cvae_runs/`.
