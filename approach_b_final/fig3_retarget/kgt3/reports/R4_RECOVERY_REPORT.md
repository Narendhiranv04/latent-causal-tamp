# FIG3 K > 3 recovery (R4): consolidated report

**Branch:** `naren/rss27-fig3-retarget-home` (not merged)
**Start commit:** `219c735c33`
**Final commit:** see the last commit on the branch (this report's commit)
**Controlling preregistration:** `../R4_PREREG.json`, committed before any R4 outcome, plus the R4.5 addendum, committed before the R4.2 outcomes.

## Status

All R4 numbers are **development evidence**. They come from exposed DEV panels or from newly constructed families.

- The P2 DATA_LIMITED decisions stand. Nothing here reopens P2, and nothing here is the P3 or P5 confirmation gate.
- There was no protected TEST access, no release_v2 access, and no cVAE or X/Y retraining.
- The K ≤ 3 production bundle, sampler, Y pathway, teacher contracts and per-query budgets are unchanged.

@@SUMMARY@@

## R4.0 Implementation and evidence-accounting corrections

| Issue | Correction | Regression test |
|---|---|---|
| Complexity claim | N_X(m) = Σ_g g!·C(m,g)·2^(m−g), so N_X(8) = 15,360. The "1,800" in the parity audit was wrong; the code and its test always used 15,360. The parity-audit row is corrected and the correction is disclosed there. | `test_nx_formula_and_requests` |
| Exhaustive-search estimator | Fields renamed. `est_distinct_x` counts set-keyed cached readouts (the envelope quantity, unchanged decisions). `est_theoretical_dp_lookups` = Σ_k e_k·N_X(k). Measured fields: `requested`, `cache_hits`, `x_unique` (actual model evaluations), `batches`, `dp_lookups`, wall. | `test_distinct_requests_equals_union_over_pool`, `test_long_assignments_use_marginal_composition_and_accounting` |
| EXACT label | `exhausted = true` only when every size was completed; timeouts raise before it is set. | same |
| K ≤ 3 energy | K ≤ 3 assignments are scored only by the exact joint p11 of one chunk, in GA, REC and assignment_given. The marginal-composition competitor is removed. Long plans keep the chunkwise marginal-X + terminal-Y objective. | `test_short_assignments_use_exact_joint_p11_only` |
| Displacement tie-break | `recursive.seeds` gains `disp_tiebreak`. The historical default is True; the scaling path passes False. The production floor (`rank.b0`) is unchanged. | `test_rec_passes_no_displacement_tiebreak`, `test_seed_tiebreak_ignores_displacement_when_disabled` |
| Guard | A record without a terminal X/Y value is NO_OUTCOME and never terminal. `decide(required=…, stage_dir=…, once=…)` refuses missing metrics, unbound sealed manifests and a second gate opening. | `test_guard_*` |
| Evidence taxonomy | `guard.outcome` classifies results as SUCCESS, CERTIFIED_INFEASIBLE, BUDGET_NO_PLAN (budget-relative, not a certificate), OPERATIONAL_FAILURE, UNRESOLVED, CENSORED, ERROR or NO_OUTCOME. | `test_outcome_taxonomy` (10 cases) |
| Latent bug | `Scores.cost` failed on list-valued prefixes in `assignment_given` chunk_px. P3 never ran, so no result was affected. | `test_assignment_given_long_reports_chunk_px` |

**Tests.** 43 pass on gvlab2: 20 historical KGT3 tests, 2 learn tests and 21 new R4 tests (`tests/test_r4.py`).

**3D label audit** (`r4/audit_labels.json`):

- **Positives:**
  - all 352 successful P2 3D runs were independently replayed, giving 406 replayed positive chunk labels;
  - 42 positives are executed prefix chunks of runs that failed later, and these were never replayed.
- **Negatives:** of 173 counted negatives, 114 are certified, 51 are BUDGET_NO_PLAN and 8 are OPERATIONAL_FAILURE.
- **Strict labels** (replayed positives only, certified negatives only) change the 3D GATE support from 9/22/22 to 8/16/16. This is descriptive; the P2 decision stands.

@@LENGTH@@

## R4.1 Frozen-cVAE proposal coverage (model-only; `r4/cover/`, `figures/R4_1_coverage.png`)

**Method.**
- The production S1 marginal was reproduced exactly: parity with D4 on 20/20 3D and 30/30 2D roots.
- No assignment optimization was run.
- The witness is used only by the evaluator. It is one valid repair, not necessarily the only one.

**Results:**

| Proposal arm | 3D witness action recall | 3D complete witness set | 2D witness action recall | 2D complete witness set |
|---|---|---|---|---|
| TOP4 (production D4) | 0.51 | 2/20 | 0.03 | 0/30 |
| TOP6 | 0.56 | 2/20 | 0.03 | 0/30 |
| TOP8 | 0.61 | 3/20 | 0.04 | 0/30 |
| TOP12 | 0.73 | 7/20 | 0.09 | 0/30 |
| ANC16 / 64 / 256 / 1024 (ancestral latent draws per object) | 0.59 / 0.68 / 0.86 / 0.90 | 1 / 3 / 11 / 15 | 0.09 / 0.25 / 0.47 / 0.73 | 0 / 0 / 4 / 11 |
| FULL legal set (upper bound) | 1.00 | 20/20 | 1.00 | 30/30 |
| Fig. 3A recursive proposal union (separate) | 0.78 | 7/20 | 0.12 | 0/30 |
| Fig. 3A candidate pool (actions / exact set) | 0.50 | 0/20 | 0.01 | 0/30 |

**Failure taxonomy.**
- No witness object was ever unproposed: every eligible object receives proposals.
- No destination had zero mass, and nothing was dropped by the grammar.
- Every miss is a destination that was **sampled but truncated** (top-k) or **not drawn** (ancestral).

**Rank of the witness destination in the S0 marginal:**
- **3D:** rank 0 for 24 of 90 actions, rank ≤ 3 for 46, rank ≥ 12 for 24.
- **2D:** rank ≥ 12 for **137 of 150** actions, and typically 17–30 of roughly 30 legal cells.
- **After the witness prefix (oracle diagnostic):** the 2D ranks are equally poor, so 2D is not an intermediate-state effect.

**Cost.**
- Neural inference is negligible (about 5 ms per root).
- Composition cost explodes with proposal width. Median distinct readouts for an exact Fig. 3B search:
  - 3D: TOP4 7.0e5 (EXACT on 14/20), TOP12 1.4e8 (3/20), ANC1024 1.1e9 (0/20);
  - 2D: 5.5e9 even at TOP4 (0/30).
- 3D TOP4 complete-set coverage by N: N5 1/3, N6 0/6, N7 0/5, N8 1/5, N9 0/1. TOP12 action recall is 1.00 at N5 and 0.55–0.78 at N6–N9. 2D roots all have N 14–20 (TOP12 recall ≤ 0.17).

**Reading.**
- **3D.** The frozen cVAE's distribution contains the witness destinations at moderate rank, so wider proposals recover coverage (15/20 at ANC1024). But Fig. 3B's exact search over a widened initial pool is unaffordable. Proposal width and composition cost must be traded explicitly, for example by recursive or local resampling, which is a Fig. 3A property.
- **2D.** The learned distribution itself is the limit. Witness destinations sit in the tail of the marginal in both the initial and the witness-prefix scenes. Increasing diversity under the frozen 2D cVAE does not recover the known long repairs at any affordable budget.

## R4.2 3D physical known-assignment order recovery (new development diagnostic; `r4/order3d/`, `figures/R4_2_order3d.png`)

**Protocol.** These are the 20 exposed 3D DEV witness roots. No independent verified K > 3 3D cohort exists outside this panel.

- Every arm received the same unordered witness assignment, with the order hidden. Composition used `compose.grouped_dp` (λ = 0, has_multi, R4.0 energy).
- **One sealed (order, partition) per arm and root** was committed before any job, with no post-failure replacement.
- Success requires X = 1 (every relocation and boundary connector), endpoint Y = 1 and independent replay = 1.
- There were 205 new runs (2.59 CPU-h); 26 exact archived outcomes were reused.

| Arm | Strict success | First action = witness | Median witness-order rank quantile (all m! orders) | Failure outcomes | New / reused runs |
|---|---|---|---|---|---|
| F0 (production X) | **2/20** | 3 | 0.30 | 15 certified, 3 budget | 9 / 11 |
| M1s (query-relative MLP) | **10/20** | 8 | 0.14 | 7 certified, 3 budget | 15 / 5 |
| **G1s (query-relative GNN)** | **11/20** | 9 | 0.17 | 5 certified, 4 budget | 11 / 9 |
| O2 (KGT3 P2-trained M1) | 6/20 | 6 | 0.23 | 11 certified, 3 budget | 18 / 2 |
| RANDOM | 3/20 | – | – | 14 certified, 3 budget | 20 / 0 |
| WITNESS order (positive control) | 18/20 | – | – | 2 operational | 20 / 0 |

**Paired comparisons** (exact two-sided sign test):

| Comparison | Gain–loss | p |
|---|---|---|
| G1s vs F0 | 9–0 | 0.004 |
| G1s vs RANDOM | 8–0 | 0.008 |
| M1s vs F0 | 9–1 | 0.02 |
| O2 vs F0 | 4–0 | 0.13 |
| F0 vs RANDOM | 2–3 | 1.0 |

**Physical concordance** covers 84 executed order pairs with different decided outcomes on the same set: G1s **0.75**, M1s 0.63, O2 0.60, F0 **0.40** (anti-concordant).

**Reuse disclosure.** G1s is 8/11 on new runs and 3/9 on exact reuses of the quarantined R3.4 runs (used here only as labelled reuse). Excluding every quarantined outcome, G1s ≥ 8/20 vs F0 2/20.

**Partition study** (same fixed order, chunk boundaries varied):

| Order | All singletons | Model-DP | Front-loaded 3-chunks | Back-loaded 3-chunks |
|---|---|---|---|---|
| G1s | 11 | 11 | 11 | 11 |
| Witness | 16 | 17 | 19 | 18 |

- Under the G1s order, every root has the same outcome under all four chunkings.
- Under the witness order, 16 roots succeed under all four. Connector failures: 1 run in the main panel.
- **Long-horizon 3D failures with the correct assignment are ordering failures, not chunk-boundary or q_ref-connector failures.**

**Compute.** Median model-only ordering cost is 0.2–0.3 s and 480 unique X readouts per root. Median physical verification is about 30–40 s CPU per run.

**Reading.**
- The frozen query-relative GNN gives a large, physically measured ordering benefit over the production X (+9 roots, 0 losses). Its offline local metrics (P2 GATE AUROC 0.69, concordance 0.77) did translate into planning utility.
- The KGT3 P2 fine-tuning (O2) **reduced** physical ordering success relative to its own initialisation (M1s 10 → O2 6). That training is not a recovery path as run.
- These are 20 exposed roots: development evidence, not confirmation.

## R4.3 2D teacher audit and witness-first dependency construction (`r4/b2d/`, `figures/R4_3_build2d.png`, GIFs)

### Audit of the 644 unresolved P2 queries (`audit_unknown.json`)

**Static kill-table class of the failed relocation:**

| Outcome | Statically free | Pick statically blocked | Place statically blocked | Boundary |
|---|---|---|---|---|
| UNRESOLVED | **541** | 37 | 13 | 53 (transit) |
| CERTIFIED_INFEASIBLE | 0 | 230 | 40 | – |

- **Dominant mechanism.** Online skill-planner failure on relocations whose pick and place are statically available in dense scenes (N 14–20). These runs fail fast: median 5.5 CPU-s, with `goal_plans` and motion checks unspent. This is planner incompleteness, not budget exhaustion.
- **Re-query sample (40 unresolved relocations, unchanged budgets).** 21/40 return a skill-planner status of CERTIFIED_INFEASIBLE internally. The teacher checker does not accept these as certificates (ORDER_FIRST_ACTION / STATIC_ENDPOINT_INVALID), so they stay UNKNOWN_PLANNER. The other 19 are genuinely unresolved.
- **Teacher-path finding.** `y_temp`'s certificate routine (`p15_retarget.certified`) returned UNKNOWN on statically caged objects, where the X teacher's `edges()` certificates decide. The construction therefore probes with the X teacher. This is disclosed: smoke families R4.3-SMOKE0–8 used 157 CPU-s.

### Witness-first construction

- **Physics.** Full articulated 3R planar arm through the unchanged BXY primitives; fresh cache and unchanged budget per query; disc sizes unchanged.
- **Why cages.** A single neighbouring disc never blocks the planar arm (SMOKE0: four obstructor cells, all VERIFIED). Dependencies are therefore built as **static cages**: walls ranked by the MINK kill table, with E the wall whose removal restores a grasp.
- **What counts.** Every block must be CERTIFIED_INFEASIBLE by the teacher, and every free move VERIFIED with independent replay.

| | Count |
|---|---|
| Families attempted (sealed roster) | 60 |
| Verified E-enables-B (level ≥ 2) | **55** |
| Verified F → E → B (level 3) | **35** |
| Teacher queries | 1,159 (492 SUCCESS, 492 CERTIFIED_INFEASIBLE, 175 UNRESOLVED; 0 errors / censored) |
| Decided matched-order groups (identical destination assignment, SUCCESS vs certified negative) | **134** (110 two-action, 24 three-action) + 16 with nuisance |
| Groups containing an unresolved order | 51 (nuisance 31, L3 partitions 15, L3 permutations 5) |
| CPU | **1.34 CPU-h** (cap 12) |

**Level-2 attempt failures** (an attempt is retried with a new layout): no verified B relocation 19, B not free after E 12, no static cage 5, B not certified blocked 3, no verified E relocation 1.

**Level-3 failures:** no verified F relocation or E not free after F 16, E not certified blocked by F 3, no cage 1.

**Decided chunk labels by preceding relocations** (+ replayed or executed prefix, − certified):

| | chunk 1 | chunk 2 | chunk 3 |
|---|---|---|---|
| 0 preceding | +125 / −55 | +99 / −77 (9 unresolved) | +31 / −222 (27 unresolved) |
| 1 preceding | +90 / −0 | +24 / −6 (5 unresolved) | – |
| 2 preceding | +48 / −12 (10 unresolved) | – | – |

**Nuisance after the dependency.** Three distant discs added after the dependency was established:
- verified order: 16 succeed, 8 certified infeasible, 31 unresolved;
- B-first order: 55/55 certified infeasible.

Density reintroduces unresolved teacher outcomes even far from the chain.

**Frozen 2D F0 on the decided contrasts** (model-only, m ≤ 3, so the energy is the exact joint p11):
- Concordance is **0.49 [0.37, 0.60]** over 55 families and 150 groups; marginal pX gives 0.48.
- The frozen 2D X model does not rank enabling orders. No 2D query-relative ordering model exists.

**Reading.**
- The 2D teacher is reliable on sparse, constructed dependency scenes: certified negatives and replayed positives at about 85% decidability. It is unreliable in dense generator scenes because of online-planner incompleteness.
- A small, reproducible certified dependency collection now exists: 55 families, with level-3 and h ≥ 1 coverage. It is not yet large enough for training, and h ≥ 1 three-action chunks are not yet covered.

@@R44@@

@@R45@@

@@ANSWERS@@
