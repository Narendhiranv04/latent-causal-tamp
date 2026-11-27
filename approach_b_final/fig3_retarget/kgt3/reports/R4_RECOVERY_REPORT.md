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

## Summary

| Question | Answer (development evidence) |
|---|---|
| Primary 3D bottleneck | **Execution ordering** (with a weak X model) and **over-long selection**. Coverage is secondary and teacher reliability is acceptable. With the correct assignment, F0 orders succeed on 2/20 vs G1s 11/20 (witness 18/20). Chunk boundaries do not matter (R4.2). The long energy favours longer plans (R4.0). |
| Primary 2D bottleneck | **Learned proposal distribution and teacher decidability.** Witness destinations sit in the cVAE tail (R4.1). Dense-scene online-planner incompleteness produces UNKNOWN (R4.3, R4.5 pilot). No 2D ordering model exists (F0 concordance 0.49). |
| Does the frozen GNN give physical ordering benefit? | **Yes, in 3D.** G1s vs F0 9–0 (p = 0.004) with the assignment given; concordance 0.81 on 28 new families (F0 0.55); end-to-end Fig. 3A / 3B with G1s 10 and 9/20 vs flat 3/20. |
| Can the frozen cVAE be recovered by wider proposals? | **3D:** partly (witness-set coverage 2 → 15/20), but exact Fig. 3B search over the widened initial pool is unaffordable (≥ 1e8 readouts). **2D:** no. |
| Are Fig. 3A and 3B viable? | **3D: yes, both.** 10/20 and 9/20 physically verified end-to-end repairs, 8 and 9 of them longer than 3 actions, vs 3/20 flat (p ≤ 0.03), on exposed roots. **2D: NOT_READY.** |

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

**Long-plan energy bias** (`r4/audit_length.json`; corrected P4 rerun, model-only):

| | Median best E by assignment size (1 → max) | −log Y_global (1 → max) | X sum F (m ≥ 4) | Argmin size |
|---|---|---|---|---|
| 2D (F0, 30 roots, H 6) | 5.92, 3.70, 1.51, 0.93, 0.78, 0.68 | 5.91 → 0.11 | 0.59–0.63 | 6: 15, 5: 9, 4: 3, 3: 3 |
| 3D (O2, 20 roots, H 5) | 4.93, 1.22, 0.30, 0.14, 0.12 | 4.92 → 0.01 | 0.06–0.09 | 4: 11, 5: 8, 3: 1 |

- **Direction of the bias.** The energy does **not** favour short plans. E never increases with size on any root (0/30, 0/20), and the argmin is usually at or near the maximum length.
- **Cause.** The frozen Y_global keeps rising as more objects are moved, while the summed marginal-X cost of long plans stays near 0. Nothing penalises unnecessary relocations, and selected long plans also use more chunks than needed (m = 6 with 4–5 chunks where 2 suffice).
- **Consequence.** The long objective is **length-biased toward over-long repairs**. No normalisation coefficient was introduced (per instruction). Calibrating X on long chunks, or a length prior learned from verified minimal repairs, is the evidence-backed fix.
- **Accounting after the corrections.** Median per root:
  - **3D:** GA EXACT and exhausted on 14/20. Requested 1.0e5, unique model evaluations 7.0e4, cache hits 4.4e4, 3.1e3 batches, 2.3e5 DP lookups (theoretical unshared 3.4e6), 18.7 s wall (max 115.5 s).
  - **2D:** BOUNDED on 30/30. Unique evaluations 3.0e5, 68 s wall (max 95 s).
- **Change against the KGT3 P4 plans** (from the K ≤ 3 energy fix and the removed tie-break): 1/20 3D GA plans changed and 4/20 REC-ORDERED.

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

## R4.4 3D deeper intermediate-state supervision and temporary-target pilot (`r4/d3d/`, `figures/R4_4_deep3d.png`)

**Construction.** Fresh families (sealed roster of 40, none consumed by KGT3), built with the unchanged fin3d probes:
- **Level 2:** B is blocked by a BIG obstacle E; E → pE plans; B plans once E is parked.
- **Level 3:** a second BIG obstacle F blocks E → pE; F → pF plans; E plans once F is parked.
- **Prefixes:** irrelevant ordinary relocations Z1 and Z2.

Yield: **34/40** families (19 level 3, 15 level 2; 6 had no verified level 2), using 501 probes and 1.54 CPU-h.

**Physical jobs** (626, sealed, complete, 2.99 CPU-h):

| Kind | SUCCESS | CERTIFIED_INFEASIBLE | BUDGET_NO_PLAN | Operational |
|---|---|---|---|---|
| X runs | 164 (all replayed) | 263 | 85 | 1 |
| Y interventions | 26 | 69 | 18 | – |

**Decided chunk labels by preceding relocations** (+ positive: replayed or executed prefix; − certified):

| | chunk 1 | chunk 2 | chunk 3 |
|---|---|---|---|
| 0 preceding | +205 / −41 | +59 / −55 | +24 / −74 |
| 1 preceding | +25 / −0 | **+39 / −38** | **+12 / −29** |
| 2 preceding | +4 / −4 | +5 / −7 | +1 / −11 |
| 3 preceding | – | +4 / −4 | – |

**Matched discordant groups** (same scene, endpoint and bounds; SUCCESS vs certified): 84 in total. By template:

| Template | Groups |
|---|---|
| h0 g2 | 26 |
| h0 g3 | 14 |
| h1 g2 | 26 |
| h1 g3 (incl. 1 [A] \| [B, C, D]) | 9 |
| h2 g2 | 4 |
| h2 g3 | 1 |
| h3 g2 | 4 |
| [A, B] \| [C, D, E] | 0 |

- **Coverage is now adequate** at one preceding relocation (2- and 3-action chunks).
- **Coverage is thin** at h ≥ 2. Only 5 families had two plannable irrelevant prefixes Z1 and Z2, so h2/h3 support is 5–9 groups.

**Frozen X models on these never-seen families** (model-only, 28 families, 84 groups; `rank_models.json`):

| Model | Concordance [95% CI] | h0 | h1 | h2 (n = 5) | h3 (n = 4) |
|---|---|---|---|---|---|
| F0 | 0.55 [0.39, 0.70] | 0.58 | 0.67 | 0.40 | 0.00 |
| M1s | 0.77 [0.63, 0.88] | 0.73 | 0.91 | 1.00 | 0.50 |
| **G1s** | **0.81 [0.67, 0.91]** | 0.82 | 0.91 | 1.00 | 0.50 |
| O2 | 0.72 [0.58, 0.85] | 0.74 | 0.84 | 0.60 | 0.50 |

This is independent of the exposed R4.2 panel, and it reproduces the same ordering of models.

**Physical temporary-target interventions** (temporary target B → pB):

| Intervention | Verified | Certified infeasible | Budget-relative |
|---|---|---|---|
| Baseline (E at x) | 1/34 | 27 | 6 |
| Beneficial (E parked) | **23/34** | 6 | 5 |
| Irrelevant (Z1 moved) | 1/26 | 21 | 4 |
| Harmful (E parked, F moved onto x) | 1/19 | 15 | 3 |

**Frozen-model Fig. 3A assumptions** (model-only, 82 physically verified E-enables-B families: 34 from R4.4 and 48 from KGT3 P2):

| Assumption | Result |
|---|---|
| Frozen Y_temp(B) rises after moving E | 77/82 (median +0.42) |
| Task-conditioned cVAE proposes E as a mover | 82/82 |
| E's constructed destination is in its top-4 | 13/82 (rank ≥ 12 for 54) |
| Recursive admission accepts E → pE | 76/82 |
| Recursive admission accepts some proposed E move | 81/82 |
| Irrelevant Z1 move admitted | **18/53** |
| Other proposed actions admitted | **33%** |

**Reading.**
- **Temporary-target scoring.** It is good at detecting the true enabler: the frozen Y recognises the physical feasibility change, and admission accepts the enabler in 93% of families.
- **Admission false positives.** It is poor at rejecting non-enablers: about a third of irrelevant actions are admitted, whereas physically only 1/26 irrelevant interventions helped. These false positives bloat the Fig. 3A pool and feed the length bias.
- **Proposals.** Exact enabler-destination recall is low (13/82), but almost any proposed E destination is admitted (81/82), so this does not bind in 3D.

## R4.5 End-to-end development smoke (`r4/smoke/`, `figures/R4_5_smoke.png`, GIFs)

**Configuration.** The rule was preregistered before the R4.2 outcomes: the 3D X model is the learned arm with the best R4.2 success, which is **G1s**.

- Proposals are the frozen released D4. The common `planners.CFG` budget (180 s wall) applies to every arm.
- Planners received only public rows: no assignment, order, object identities or K.
- One plan per planner and root was committed and sealed before any job.
- Physical success requires X = 1, endpoint Y = 1 and independent replay.

**3D (20 exposed DEV roots; 60 new runs, 0.54 CPU-h):**

| Planner | Repair committed | X = 1 | Y = 1 | Full success | Success with > 3 actions | Witness-action recall | Witness set chosen | Planning (median) | Verification (median) |
|---|---|---|---|---|---|---|---|---|---|
| Flat-search control (FLAT-INSERT) | 20 | 5 | 13 | **3** | 2 | 0.10 | 0 | 1.5 s | 28 s |
| **Fig. 3A REC-ORDERED** | 20 | 11 | 15 | **10** | **8** | 0.13 | 0 | 2.8 s | 34 s |
| **Fig. 3B GA** (EXACT 14, BOUNDED 6) | 20 | 10 | 15 | **9** | **9** | 0.15 | 0 | 33 s | 34 s |
| B0 (K ≤ 3 production) | 17 | 4 | 9 | 2 | 0 | 0.14 | 0 | – | 23 s |

**Paired comparisons** (exact sign test):

| Comparison | Gain–loss | p |
|---|---|---|
| Fig. 3A vs flat | 7–0 | 0.016 |
| Fig. 3B vs flat | 6–0 | 0.03 |
| Fig. 3A vs B0 | 8–0 | 0.008 |
| Fig. 3B vs B0 | 7–0 | 0.016 |
| Fig. 3A vs Fig. 3B | 3–2 | n.s. |

- **Union.** At least one Fig. 3 planner succeeds on **12/20** roots.
- **Witness.** No successful plan equals the witness set. The planners found other physically verified long repairs, consistent with R4.1's note that the witness is one repair among several.
- **Failure profile.**
  - **Fig. 3A:** 4 certified-infeasible X, 5 budget-relative X, 1 X-success / Y-failure.
  - **Fig. 3B:** 5 certified X, 5 budget X, 1 X-success / Y-failure.
  - **Shared:** on 3 roots all three planners fail on budget-relative (NO_PLAN_FOUND) relocations.
- **Caveat.** These are exposed development roots and G1s was selected on R4.2 over the same roots. This is a smoke test, not confirmation. Repairs may be longer than necessary (see the length bias): 8 of Fig. 3B's selected plans are 5 actions long.

**2D: NOT_READY** (`R4_5_2d_NOT_READY.json`). By the preregistered pilot rule, 7/10 pilot runs were UNRESOLVED (6 UNKNOWN_PLANNER, 1 UNKNOWN_TRANSIT), 3 were certified infeasible and 0 succeeded. The remaining 64 sealed jobs were not run.

Three independent reasons:
1. the dense 2D DEV roots exceed the teacher's decidability (R4.3 audit);
2. the frozen 2D cVAE does not cover the known repairs (R4.1);
3. no 2D X model ranks enabling orders (F0 concordance 0.49).

## Answers to the required questions

1. **Commits** (`git log 219c735c33..HEAD`):

   | Commit | Content |
   |---|---|
   | `7d359c32ed` | R4.0 + preregistration |
   | `2786b06730` | R4.2 sealed plans / manifest |
   | `1bd77c5f81` | code + sealed R4.3 / R4.4 rosters |
   | `0c0337827d` | R4.1 |
   | `c439d26a07` | R4.5 addendum |
   | `be915f54b7` | R4.2 results |
   | `b48285d660` | R4.3 |
   | `dd54bac27a` | R4.4 / R4.5 manifests |
   | `1969ef4519` | R4.5 |
   | final commit | R4.4 results + this report |

2. **Corrections and regressions.** See R4.0. 43 tests pass.
3. **Numerical results.** See sections R4.1–R4.5.
4. **Physical evidence and visualisations.** Figures are under `reports/figures/`:
   - `R4_1_coverage.png`, `R4_2_order3d.png`, `R4_3_build2d.png`, `R4_4_deep3d.png`, `R4_5_smoke.png` (Fig. 3A / 3B funnels), `R4_compute.png`.
   - GIFs are in `reports/figures/gifs/`, all actual logged runs:
     - **3D**, MuJoCo re-execution of stored teacher witnesses:
       - R4.2 G1s success vs F0 failure vs witness on one root;
       - R4.5 Fig. 3A and Fig. 3B long successes and the flat failure.
     - **2D**, certified articulated-arm joint records: R4.3 F → E → B as one chunk and as three chunks (success) vs B, E, F and E, F, B (certified failures).
   - Raw records are under `reports/r4/*/` (manifests, seals, results, per-root analyses).
5. **Primary bottleneck.**
   - **3D:** execution ranking (order), then the length bias of the long objective and admission false positives. Proposal coverage matters but is not binding for success. Composition and boundaries are not binding.
   - **2D:** learned proposal distribution plus teacher reliability in dense scenes, then execution ranking.
6. **Frozen GNN.** Yes. It gives a large, physically measured ordering benefit in 3D, replicated on independent new families. M1s is close behind; the GNN-vs-MLP difference is not established (11 vs 10; 0.81 vs 0.77).
7. **Frozen cVAE.** 3D: coverage is recoverable by sampling, but only affordably inside a recursive or local scheme. 2D: not recoverable. The distribution itself must change.
8. **Viability.**
   - Fig. 3A and Fig. 3B both remain scientifically viable in 3D: comparable success, Fig. 3A 12× cheaper to plan (2.8 s vs 33 s median).
   - 2D is not yet viable.
9. **What must improve, by measured evidence:**
   - **(a) 3D long-chunk X calibration and a length-aware objective.** Summed marginal X ≈ 0.06–0.09 for 4–5-action plans, so −log Y_global dominates and longer plans are always preferred. Supervision: the R4.4 h ≥ 1 matched chunks plus verified minimal-length repairs.
   - **(b) Temporary-target admission specificity.** Physical irrelevant / harmful labels (R4.4 interventions) for the recursive admission head. 33% false admission vs 4% physical.
   - **(c) 2D.** A query-relative ordering head trained on the certified R4.3 dependency families (134 contrasts; F0 is at chance). A 2D repair-destination proposal model that covers far parking cells (witness destinations at rank ≥ 12). Sparse or moderately dense 2D DEV roots where the teacher decides.
   - **(d) Do not reuse the KGT3 O2 recipe.** It lowered physical ordering (10 → 6) and concordance relative to its M1s initialisation.
10. **Recommended next experiment** (not started).
    - Train the 3D X scaling head (G1s/M1s initialisation, Y frozen) on R4.4 + KGT3 matched chunks with replayed positives and certified negatives only, with a calibrated long-chunk loss.
    - Confirm on a **fresh sealed 3D cohort** constructed like R4.4 (new families, untouched): known-assignment order success and end-to-end Fig. 3A / 3B vs flat, under preregistered criteria.
    - In parallel, scale the 2D witness-first construction to about 300 families with h ≥ 1 three-action chunks before any 2D training.
11. **Compute.** See `r4/R4_LEDGER.json` and `figures/R4_compute.png`.
    - **CPU:** 9.24 CPU-h in total. R4.2 2.59 / 8; R4.3 1.56 / 12; R4.4 4.53 / 12; R4.5 0.56 / 4.
    - **GPU:** wall-clock union of GPU-loaded processes about 1.1 h. Summed process wall about 2.4 h, mostly CPU-bound DP with the GPU largely idle. Under the strict per-process reading this exceeds the 2 GPU-h authorization by about 0.4 h (disclosed).
    - **Wall clock:** about 2 h of the 8 h guard; at most 16 concurrent workers; gvlab2 only; no retries.
12. **Protected data and production.**
    - No protected TEST or release_v2 data (not even metadata) was accessed.
    - The K ≤ 3 production bundle, checkpoints, datasets, sampler, Y pathway, teacher contracts and per-query budgets are untouched, with no retraining.
    - Historical results were not modified: the P2 decisions stand, the one KGT3 report correction is a labelled errata line, and quarantined A2 outcomes were used only as labelled exact reuse.

**Deviations (disclosed).**
- 2D construction probes use the X teacher (single relocation, bounds [1]) instead of `y_temp`, after smoke families showed `y_temp`'s certificate routine cannot certify caged objects.
- 2D obstruction uses static cages (kill-table ranked) because single discs never block the planar arm.
- A PIL symlink path was used for the 3D GIF process (env3d lacks PIL); no environment was modified.
- GIFs are frame-subsampled for size.
- The GPU accounting interpretation is described above.
