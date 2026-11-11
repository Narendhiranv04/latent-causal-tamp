# 0042 — P14: Scientific Repair of P13 + D-Guided Joint Rearrangement with Similarity-Retrieved Swept Volumes

**Binding implementation/research contract for Claude Opus 5.5 High.**

**Base repository:** `Narendhiranv04/latent-causal-tamp`; expected base commit `99bccf7cbc57feb6150d0d50062548af4d3eebe1`. Verify HEAD, origin, dirty files and archived result hashes first; do not assume they match. **Stay in 2D.** Do not port to 3D, introduce dummy variables, or train a D destination model.

**Primary scientific purpose:** Correct P13's identifiable evaluation/reporting issues, explain and attempt to remedy original-feasibility/natural-mix failures with a leaner appropriately calibrated B, and determine which factor effects are real versus admission-threshold artifacts. **Sidecar engineering/research purpose:** implement a modular, non-learned D-guided rearrangement planner whose candidate motions come from a scene-similarity indexed library of **real witnessed swept-volume trajectories**, plus a safe online-planning fallback. The planner jointly chooses order and all destination slots and optimizes **minimum number of relocations, then minimum measured travel**. Demonstrate the added value, if any, of D versus geometry with exactly the same search and lookup.

## 0. Non-negotiable scientific conclusions already known

1. P13 passed reported engineering gates and archived `430/430` tests and `6/6` historical replays. Its freeze commit was `c9756294beed243b16210fde29519de5eb7db395` and blind-label hash commit `4da8ca297072bda01a21a131d047c01f8472d8f9`. **Preserve every P10–P13 artifact and report unchanged.** Corrections must be versioned P14 addenda.
2. P13 strict TOP1 success on 129 executable roots: keyed B `.734`, A `.558`, C `.579`, SF `.318`, geometry `.612`, separately planner-assisted G+M `.783`; on 48 natural-stream roots B `.5625` vs geometry `.625`. The aggregate B advantage over geometry is heavily concentrated in ORD_CHAIN/OMIT_OPT; avoid claiming broad geometric superiority.
3. P12 complete 80-root execution: geometry `.8375` > B `.6292`. This failure of distribution transfer remains binding.
4. P13 F2/order supported. F3 offers no demonstrated beneficial mean effect (point estimate `−.02247` nats, bootstrap CI `[−.06375,.01470]`; Holm sign-test p `.030` favors removing it); do **not** describe the mean harm as established by the CI. F4 omission log-loss gain `.014` nats below the prereg `.05` threshold and large natural loss; F4 execution gain is entangled with abstentions. F5's primary ablation B-F5spm removes **generic coupling plus higher order**, not generic-only coupling. It helps on mechanism-conditioned challenge but harms natural mix (`B joint4 NLL 2.537` versus B-F5spm `1.397`). F5q triple-only finding is exploratory.
5. D's output is initial-target feasibility plus a **union of members in inclusion-minimal sufficient clearing sets** relative to a fixed parking-map intervention lattice. It **does not** predict destinations, order, access paths, minimal move count or the unique set of required obstacles. D-pairless is a valid simpler control. On 119 matched P13 infeasible roots D blocker F1 `.892`, D-pairless `.880`, geometry `.824`, B-derived `.866`; D's pairwise improvement is not significant. On 166 decided originals only 27 are feasible: B feasible recall `19/27`, D `23/27`, A `24/27`.
6. The severe palette recolor effect and mild photometric controls are established as different transformations; don't conflate them. The current analytic static veto fired zero times, and F1's fourth ordering key was never reached.
7. Offline `SCENE_TARGET_ONLY` counterfactual tests and actual executable ordered relocations are different. A hypothetical static scene edit being feasible does **not** prove its relocation can physically be executed.

## 1. Work boundaries and organization

Use two clearly separated subtracks, with independent artifacts and results:

- **P14-A: corrective evaluation + natural-mix calibration and minimal-B diagnosis**. Priority; do not spend the bulk budget on another broad factor training campaign.
- **P14-D: retrieval-based D-guided rearrangement**. Implement as a sidecar, preserving D's learned task. No learned similarity encoder, destination head, order head or new Boltzmann energies. Reuse the existing robot, data, physics and episode APIs; do not mutate A/B/C/D mathematical definitions as a shortcut.

Prefer ≤4 small purpose-specific Python modules rather than monolithic 600–800-line files. Suggested root-level files only if existing ones cannot be cleanly extended: `p14_audit.py` (existing-artifact evaluations), `p14_sweep_index.py` (trajectory evidence, descriptors, retrieval, collision filter), `p14_d_search.py` (joint search and integration), `p14_eval.py` (frozen comparison, metrics and plotting) plus `tests/test_p14.py`. Reuse existing modules for training/teacher; do not clone the simulator, redefine a second robot model, introduce gratuitous nested folders or exceed ~350 lines/module without a written exception. Artifacts in `runs/p14/{audit,calibration,lookup,search,eval,guards}`; reports `responses-phases/0067_...` onward; figures `visualizations/p14/`. Put a compact pre-stage decision `runs/p14/P14_PREREG.json` and separate hash manifests for the P14-A and P14-D controls.

## 2. P14-A0 — audit and versioned corrections: ZERO new physical labels

Read and verify original P13 source/JSON, not merely summary tables:

- `p13_factors.py` (notably `_paired`, `targeted`, `d13`, `f1_and_j`), `p13_execution.py`, `p13_pipeline.py`, P13 `PREREG` and addendum; old files stay immutable.
- **Travel-head sign:** historical `F1_J.json` teacher-labelled success is `J .83618` vs `noJ .81766`, so `J−noJ = +.01852`, even though stored field `B_success_J_minus_noJ` has `.mean_delta = −.01852`. Create corrected P14 version and add a regression test guarding sign orientation. Distinguish target teacher-labelled choice accuracy from physically executed success.
- **J regret:** `f1_and_j` restricts the travel metric to *verified feasible* alternatives before picking by J, and `shuffledJ` samples feasible alternatives. This is an oracle-filtered diagnostic, **not** the deployed travel regret. Report it as such; if possible, compute true frozen-choice travel on comparable **selected verified** candidates, coverage and failures separately; never impute travel of an infeasible or unattempted action.
- **Execution ledger discrepancy:** reported outcome histogram 295 successes / 51 no-witness versus final eight `runs/p13/p13_5/episodes/w*/ledger.json` files containing **301 SUCCESS, 52 NO_REPAIR_WITNESS_WITHIN_BUDGET, 34 UNRESOLVED_CENSORED, 28 TARGET_CERTIFIED_INFEASIBLE, 13 TARGET_UNRESOLVED = 428**. Reconstruct by unique episode identity, continuation records, excluded/duplicate jobs, and report-generation times; determine why the old narrative differs. Independently regenerate all per-arm root success numbers with abstentions as failures. Do not assert the aggregate `0.734` is wrong unless recomputation proves it.
- **F3:** show both directional sign-test p and bootstrap confidence interval for the mean; effect below `.05` nats. **F5:** rename primary claim to combined generic+HO block; do not claim generic-only benefit. **F4:** distinguish change in admission, conditional candidate ranking, and physical success.
- **Keying:** `unique_factor_keyed` enforces one canonical variable per actual physical query. Unkeyed NLL improvement is *not* proof of duplicate/re-listing consistency; retain keyed as correctness reference. Add exact duplicate query/permutation tests, and report prediction-vs-catalogue-invariance separately.
- **D:** preserve matched lattice semantics and no-predicted-clearing-set as a miss. Present conditional truth-known infeasible blocker F1 separately from full feasibility-gated blocker inference. Union-of-minimal-sets is not universal necessity.
- **Compute ledger:** `min(guard CPU, wall)` under the thread-parent bug is an upper bound for a single-threaded child, *not* an exact measurement. Present a bounded/estimated count, preserve raw readings, and stop calling it verified exact CPU-s.

Pass gate only with corrected P14 JSON, code unit tests, clear unmodified historical file hashes and updated reports. No fresh physical testing is required for these corrections.

## 3. P14-A1 — diagnosis of the natural/mixed distribution

Analyze frozen P13 predictions for the whole natural stream and separately the 45 decided original-feasibility labels. Report balanced accuracy, feasible recall, infeasible recall, Brier, binary NLL, reliability bins with honest small-N uncertainty, and joint four-bit NLL stratified by outcome pattern (`1111`, single-blocker patterns, joint clearing patterns). A natural cohort with mostly feasible originals is **not equivalent** to real-world prevalence; call it the synthetic unconditioned stream.

Analyze K-B, K-C, A, SF, B-F3pm, B-F4, B-F5spm, B-F5qpm, B-U, D and D-pairless. Explain whether errors reflect ranking, threshold/admission, or probabilities. Do not refit calibrators/thresholds on P13 natural blind roots; all P13 results remain test, with exploratory post-hoc diagnostics labelled as such.

**Matched admission/selection comparison:** for every arm, report (i) coverage fraction / abstention, (ii) success conditional on attempting a repair, (iii) root success under historical chosen thresholds, (iv) full coverage–risk/accuracy curves from **frozen scores**, (v) validation-derived common admission coverage or a common fixed false-admission constraint, and (vi) effect of J as second tie-break independently from admission. Do not match thresholds on blind labels. If a reported counterfactual choice lacks physical execution, mark success UNKNOWN or execute via separately budgeted prospective protocol; never recycle a different episode as an outcome.

Mathematically distinguish **generic pairwise F5**, **higher-order HO**, **F3**, **F4**, and the scene unary. Generic-only isolation means zero/remove `cpl` (including scene-scene, scene-query and omit-omit uses), while preserving the architecture and HO path; match capacity and optimization, and test normalization/inference. The already tested B-F5spm is combined removal. Identify what can be established with existing checkpoints, and if additional retraining is necessary, do it only with a declared 3-seed matched protocol and within the capped gate.

**Possible repair of the problem:** create a separate small fresh TRAIN/VALIDATION set with realistic mixtures of feasible-original scenes and hard intervention cases. Set sampling proportions *before* model fitting; use validation-only calibration (e.g. scalar temperature / bias / prior-correction as appropriate). A small set of three predefined settings (full B, lean B without F3/HO, no-coupling B) is preferable to blind model-search. To establish success, construct **new** held-out natural-like and mechanism-disjoint scenes, and freeze all model checkpoints, chosen thresholds, predeclared stats and predictions **before** new physical labels. If budget/constructibility is inadequate, mark the correction exploratory and do not reclassify P13's reused test roots as new confirmation.

A 3D port is NOT authorized. Do not force all factors to become significant. Declare the primary criterion before the new test: initial feasible-original recall and non-unnecessary-relocation rate must not deteriorate; natural-mix joint/individual predictive fit should improve without unacceptable drop in executed task success; assess cause rather than just report scalar improvements.

## 4. P14-D0 — motion-evidence provenance audit (a mandatory STOP gate)

The similarity lookup must **not invent a trajectory** or infer a swept volume merely from its source/destination endpoints.

Inspect existing `runs/p10*`, `runs/p11*`, `runs/p12*`, `runs/p13*` episode artifacts and planners: what exactly is logged as a successful witness (robot joint path, gripper state, carried object's poses, collision geometries, grasp/approach/transfer/retreat phases, start and goal)? Check whether the full robot+carried-object swept occupancy can be reconstructed. If not, instrument the existing simulator **on a small development-only trajectory set** and collect new genuine executable motions; report how many records exist and their trace fidelity. Do not fall back to hand-drawn straight-line volumes or sweep fabricated from start/end.

Record for each independent source-scene, robot state and relocation witness:

- immutable episode/root/query IDs, version and train/dev/eval split;
- robot model, fixed base pose, exact joint configuration `q_start`, gripper state, object class/size and grasp mode;
- object source cell and destination cell, **relative displacement** `(Δrow,Δcol)`;
- local occupancy signatures 3×3 and 4×4 centered/anchored deterministically at both source and candidate destination; include fixed vs movable vs free, object sizes, support/boundary clearance and, where represented, target/goal cells;
- global scene occupancy signature and robot/base-frame descriptor, plus approximate route or workspace-region signature;
- verified joint-space trajectory and optional path poses, success status, **phase-specific conservative swept occupancy** of robot links plus carried obstacle, with actual geometry and clearance margin, and verified measured travel cost; cache only truly witnessed paths;
- independent-support ID (unique scene/robot/witness family). Count near-identical replay duplicates as one effective support when ranking a frequent sweep.

In 2D, represent swept occupancy by conservative occupied grid cells or continuous polygons (including link thickness and margin) **per phase**: approach, grasp, lift/transfer if present, placement, release, retreat. Dynamic object occupancy changes per phase; exclude the carried object from the external obstacle check only when appropriate, and still check the robot/gripper/object against the rest of the scene.

**Safety/physics limitation:** a finite sampled sweep is only approximate unless bounds/inflation yield a conservative enclosure of interpolation. Distinguish strict geometric collision checks from discretized screens. Do not claim that no stored witness exists implies no valid motion exists. Always validate proposed motion in the exact current scene and robot state through the actual physics/motion system before committing it.

## 5. P14-D1 — local/global similarity index, retrieved sweep modes

Implement user's requested **deterministic, non-learned two-level similarity lookup**, independent of D training:

1. **Hard compatibility filtering**, BEFORE similarity: robot base and kinematic model; object shape/height/class, grasp mode/gripper; source→destination relative displacement or equivalent validated transform; support compatibility; and relevant robot start/configuration tolerance. A similar 3×3 patch alone does not make a fixed-base manipulator trajectory reusable. Start robot configuration after each hypothetical move must be tracked.
2. **Local scene descriptor:** fixed-shape 3×3 plus anchored 4×4 occupation windows at the moving object source (and destination); categorical occupancy/free/fixed/target/movable channels, local boundaries and clearances; deterministic alignment under the permitted transformation only. Test translation/rotation invariance ONLY where the robot geometry actually permits it; do not rotate/translate joint trajectories blindly.
3. **Global scene descriptor:** entire 2D occupancy/context encoded canonically (at the pilot resolution), plus robot base/workspace and goal context. Use local similarity as primary ranking and global similarity as a qualifier/tie-break or predeclared weighted term; calibrate any weights on DEV only. Support exact-match-only, local-only, global-only and combined retrieval as baselines.
4. For each `(object features, Δslot, robot-context)` retrieve **all eligible witnessed sweeps** meeting chosen thresholds. They may form multiple distinct motion modes. Cluster by swept-mask overlap (e.g. IoU/Jaccard), with separate approach/transfer/retreat checks; rank clusters by **independent supporting scenes, contextual similarity, and measured travel**, not mere number of nearly duplicate episodes. Keep representative *actual witnessed trajectory* per mode and alternatives within mode.
5. **The user's modal/common-volume suggestion is a heuristic, not a sound feasibility criterion.** Rank the best-supported mode first, but do not discard valid rare modes merely because they are not the majority. Never replace all trajectories by the **intersection/common overlap** of their swept volumes; that underestimates actual occupied space and could be unsafe. A conservative per-cluster union can safely screen a cluster but may reject valid alternatives; individual witnessed sweeps are still the decisive candidates. A rare collision-free path can succeed even when the common mode intersects an obstacle.
6. At query time, transform/reproject each compatible stored swept occupancy into the current coordinate frame only when the transformation is kinematically valid; compare each with the **updated hypothetical scene occupancy**. For collisions, filter that witness, then try other modes. No matching record / all records filtered → **UNKNOWN under lookup**, never `CERTIFIED_INFEASIBLE`. A bounded **online motion-planner fallback** may discover a new witness, to be cached only after physical verification with full provenance.

Return `lookup_candidates(object, from_slot, to_slot, scene, q_robot, grasp)` with candidate motion IDs, similarity and independent support, swept-phase masks, provisional travel, reasons for rejection, and fallback status. Add `index_version/hash`, coverage counts and robust duplicate checks. Keep the index a replayable, queryable cache, not a learned predictor.

**Required tests:** translated patches with valid robot-frame compatibility; same local window but incompatible global geometry; same global occupancy but incompatible near-source patch; different start robot q; same Δ but different source reachability; multiple motion modes with a frequent colliding mode and a rare safe mode; incorrect object height/footprint; swept link-body collision despite EE clearance; no-match UNKNOWN; mode tie-breaking and duplicate inflation.

## 6. P14-D2 — joint destination/order search, not sequential greedy commitment

**Do not greedily choose each object's destination as if later obstacles were unchanged.** Maintain a search state:

`state = (physical object-slot occupancy, original target and goal, robot q/gripper/end-effector state, displaced/handled set, dependency stack, current prefix plan)`.

D is called for the original goal and, as needed, recursively for inaccessible candidate obstacles treated as temporary retrieval targets. Treat the user's assumption of arbitrary-target generalization as a **testable integration hypothesis**: check predictions against witnessed/certified arbitrary-object retrieval probes rather than silently assuming verified transfer. D's blocker probabilities guide **expansion order**, NOT certified hard pruning. D predicts the **union of alternative sufficient clearing sets**, so do not automatically move every object in the union; explore subsets and update blocker predictions after hypothetical relocations. Protect against repeated target cycles and state revisits.

At each node, enumerate **all eligible** (object, destination slot, compatible lookup motion) combinations. Apply deterministic static support/nonoverlap tests first; then actual compatible swept-volume checks against the occupancy at that node, including free original source slot and newly occupied destination. Update robot configuration after the proposed executed motion witness. One object's selection of slot 1 excludes other objects from slot 1 **until it is freed**, but their now-empty original cells can become destinations. Enforce trajectories and future actions for their proper intermediate states, not static all-at-once masks.

Compute candidates jointly **before physical execution** by bounded best-first search / lexicographic uniform-cost search on a finite available candidate graph. Optimize exactly:

`min_{verified plan π} (N_relocations(π), J_measured_robot_travel(π))` lexicographically.

- Zero-move case: **always attempt to verify original target goal first** under the stipulated planner protocol (not just D's predicted infeasibility), so no needless rearrangements if the target can already be retrieved.
- Travel is measurable geometric/joint-space path length of approach+carry+place+retreat and between-action transitions, with a fixed predeclared unit and starting robot configuration. No subjective `risk` penalty and no arbitrary `α N + β J` weights.
- A stored trajectory may be a promising witness but is never an unconditional guarantee when reused in a different environment. Revalidate it in exact intermediate state. Bounded planner failures/unknown states must not be treated as sound infeasibility proofs.
- At putative goal, independently verify final **target retrieval (or final pick-and-place goal)** in hypothetical final scene with the actual simulator motion planner. Count a plan as successfully found only with witnessed relocations and witnessed target completion. During actual rollout, execute first validated step, reobserve, check actual state, and replan as needed; distinguish full precommit solution from corrective online replanning.
- Formal optimality is only over a **finite, sufficiently verified candidate graph** if all eligible edges have known nonnegative exact costs and search finishes. If using top-K templates, budgeted online planning or censoring, say **best plan found within explored library and budget**; don't claim global move/travel optimality. Avoid unproven D-derived heuristics in an admissible A* bound. A lexicographic UCS or iterative move-depth with cost-sorted enumeration works for small 2D scenes.
- Search and lookup can be **computationally parallelized** over candidate checks; single-arm physical relocations are sequential. Keep one deterministic serial reference for reproducibility before adding parallel execution of search work.

**Minimal benchmark cases** (real trajectories, not fabricated):

1. target already feasible: zero moves, no hallucinated blockers;
2. one genuine blocker, ≥2 individually feasible destination options, different measured travel;
3. two jointly necessary blockers, destination conflict (both initially prefer same slot);
4. A blocks B's grasp, so B must wait for A; source slots become free and reusable;
5. first destination is geometrically free but its robot sweep obstructs a later pick/place;
6. multiple sufficient clearing subsets (do not move union blindly);
7. rare sweep mode succeeds while modal sweep collides;
8. no analogous library trajectory → fallback online planning or UNKNOWN, not hard infeasible;
9. failure of D's access prediction corrected by physical check and alternate search;
10. pair/triple cases where possible, but do not mislabel minimality from one witness.

Each benchmark scene should visualize input occupancy, D scores for original and recursive targets, ranked lookup hits and swept masks, search-state tree/plan, before/after occupancy, selected destinations, motion witness traces, verified completion and cost decomposition.

## 7. P14-D3 — scientific baselines and unique attribution

**All compared methods must use the exact same scene/target, candidate slots, sweep index, physical planner, search expansion budget, success criterion, initial robot q and trial seeds.** Only guidance changes:

- `D-guided`: D's blocker probabilities and recursive target queries;
- `D-pairless-guided`: same interface;
- `geometry-guided`: non-learned analytic blocker priority;
- `uninformed`: deterministic root-independent priority / fair randomized control;
- `oracle blocker`: labels only for upper-bound evaluation, explicitly not deployable;
- `lookup-only`: same search without model guidance, to measure whether the cache alone explains gains;
- `online-planner-only` versus `similarity lookup + fallback`, to measure lookup's contribution.

Lookup-specific controls must also compare local-only, global-only, combined, majority-top1-only and top-K-modes; count how often modal-only would falsely reject a viable alternative. Don't conflate retrieval of a similar scenario with proof of safe path execution.

Report for every method: target-goal executed success (not scene-edit feasibility), attempted/verified/failed moves, number of unique blockers actually displaced, unnecessary moves, optimal move count **within fully explored certified finite graph if applicable**, total measured robot travel, scene/lookups evaluated, independent sweep candidates, cache hit/miss, fallback and planner call counts, node expansions, wall time and total CPU, abstain/UNKNOWN/censored counts, paired root-level CIs and failure taxonomy. Include feasible-original controls and sources of false-positive blocker diagnoses. Compare the success/compute Pareto frontier with a fixed finite budget. Cache building cost is disclosed separately from amortized query cost. Explicitly isolate the effect of D on search; if D is not better than geometry under identical conditions, report **negative finding**.

**Novelty discipline:** Similarity-indexed experience retrieval, local environment context and trajectory reuse are established motion-planning ideas (FIRE/experience graphs/experience-driven trees). The proposed learned contribution is **D's causal blocker diagnosis and recursive influence on search**, not originality of the lookup or joint slot search. Do not claim novelty of a lookup table alone.

## 8. Leak prevention, evaluation and statistical design

- Declare DEV/learning records and independent blind test scene roots before training/calibration/index tuning. Ensure no identical or nearly identical **trace-producing root** from evaluation is present in the swept index. Disclose exact and approximate duplicate handling. Test roots cannot contribute to similarity index until the blind evaluation finishes, and any online adaptation must be separately labelled.
- Freeze index configuration, similarity weights, retrieval top-K, scene generator/roster, checkpoints, admission thresholds, costs, fallbacks, all model predictions and statistical hypotheses **before** test physical labels/outcomes. Versioned commit and push, then label hash-commit before unseal, as in P13.
- For D retrieval comparisons, teacher/certificate labels are usable in oracle reference only and blind outcome scoring; not for lookup construction, online D inference, search pruning, or priority decisions. Physical collision and motion-planning calls during **search verification** are legal and explicitly logged, but no physical oracle calls during pure D prediction.
- F3/F4/F5 corrective experiments require factor-on/off three-seed matched retraining whenever a new inferential claim is sought. Distinguish exploratory re-analysis of P13 from fresh confirmatory results. Report confidence intervals and tests at root level; don't confuse a sign-test finding with a mean bootstrap CI.
- For identical scene distributions, compare thresholds at matched coverage or matched false-positive admission rates in addition to original validation thresholds. Separate ranking discrimination, calibration, abstention and execution.
- `UNKNOWN`, `NOT_RUN` and `BUDGET` are not certified negative. Explicitly disclose if incomplete proof/witness rates prevent reliable evidence.

## 9. Resource and stop gates

Start with a **low-cost correction + pilot**. Implement expensive gates only if each predecessor passes, using actual per-job CPU guards and immutable ledgers. Default **P14 pilot** ceilings (CPU-seconds; independent categories):

| Category | Hard cap | Stop condition |
|---|---:|---|
| P14-A correction + frozen-only analyses | 2,500 | corrected artifacts or explicit unresolved inconsistency |
| P14-A matched selection/calibration diagnostics | 3,000 | validation-derived protocols and analysis |
| P14-D trajectory evidence audit + index dev | 4,000 | no real trajectory evidence => stop lookup claims and instrument development data |
| P14-D finite joint-search implementation/dev | 5,000 | fails real physics safety checks => do not scale |
| P14-D 2D pilot execution/eval | 8,000 | insufficient witness coverage => PARTIAL |
| Combined regression/replays/viz | 2,000 | no passing regression => engineering blocked |

A fresh confirmatory re-training/label/execution cohort is **conditionally authorized under separate explicit limits only after the pilot**, with a gate documenting feasibility, power and projected cost: training 18,000, teacher 18,000, physical execution 12,000 CPU-s. Never silently aggregate these into the pilot or launch all phases at once. Stop immediately on budget overrun or lack of prospective data. A wall-clock budget is also required per guarded job. No fabricated results, no future/background promises.

## 10. Required artifacts and stopping reports

Generate staged reports, with paths actually created:

- `0067_P14_0_P13_Statistical_And_Execution_Errata.md`: frozen-only fact corrections including J sign, episode ledger reconciliation, F3/F5, coverage, D labels.
- `0068_P14_1_NaturalMix_Calibration_Admission_And_MinimalB.md`: feasible originals, joint likelihood, reliability, threshold-matched ranking, model comparisons; label exploratory versus fresh confirmatory.
- `0069_P14_D0_Swept_Trajectory_Data_Provenance.md`: audit of real logged paths, exact fields present/missing, instrumentation decision and safety.
- `0070_P14_D1_LocalGlobal_Similarity_SweptIndex.md`: 3×3/4×4 local + full-scene, robot hard filters, multimode clusters, genuine stored examples, match and false-rejection tests.
- `0071_P14_D2_Joint_Destination_Search_And_Recursive_D.md`: formal state graph, lex objective, physically verified state transitions, recursive target queries, cycles, test cases, complete traces.
- `0072_P14_D3_D_vs_Geometry_Search_And_Lookup_Ablations.md`: full same-graph baseline table and supported/unsupported findings.
- `P14_SCIENTIFIC_AND_D_REARRANGEMENT_DECISION.md`: B and D genuinely separate; what is learned versus searched; recommend next scientifically defensible experiment, not an automatic 3D port.

Stage JSON gates under `runs/p14/`, final hash manifest, 2D snapshots/swept mask overlays/search-tree visualizations and recorded playback where available, compact unit/integration tests, final complete regression and six replays. No visualization may depict an unexecuted motion as a physical witness. Don't silently modify historical 0059–0066 reports, P12/P13 outputs or model checkpoints.

**Final Claude chat response: print the actual results, not just file names.** Sections must include: P13 errata, corrected admission/calibration comparisons, provenance and count of witnessed sweep library entries, retrieval matching/coverage and multimodal false-negative tests, 2D exact-search tests, physical goal success and lexicographic cost for D/geometry/uninformed/oracle controls, node/planner costs, negative findings and any blocked evidence, test/replay counts, exact final local/remote git SHA and pushed report paths. Give factor-by-factor lean B verdict separately from D system results.

**Success criterion:** Either (A) a scientifically supported improvement of B under realistic feasible/infeasible mixtures and a measurable D-guided rearrangement advantage under equal search budgets, or (B) clear reproducible evidence why those gains do not occur. Scientific validity takes priority over a positive headline.
