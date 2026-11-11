# 0043 — P15: Validated D-Guided Rearrangement, Similarity-Indexed Motion Alternatives, and B Calibration Closure

**Binding scientific and implementation contract for Claude Opus 5.5 High**  
**Project:** `Narendhiranv04/latent-causal-tamp`  
**Verified predecessor:** P14 `cbd5d9b1509fcfdad733545b7d0e9cba4181ee4f`  
**Scope:** 2D only. This is a correctness-first **D rearrangement** phase, with a strictly bounded, separate **B evaluation** workstream.  
**Non-goal:** Do not try to manufacture positive results for D, B, or any factor. Do not begin the 3D port, dummy-variable method, or a learned destination/ordering/trajectory network.

## 0. Central question, success definition, and scientific positioning

Our task is **not** simply to identify objects near the target. The complete system must determine whether the original target task is infeasible; identify potentially contributing obstacles; choose a physically executable sequence of obstacle displacements and destination slots; and confirm that the original target pick/place task has become feasible and can be executed. Multiple grasp/motion possibilities and alternate sufficient clearing sets can exist.

The intended architecture remains:

1. **Learned, unchanged-scope D** estimates original/temporary-target pick-and-place feasibility and probabilities that pool objects participate in sufficient clearing sets. Its training labels refer to the **union of members of inclusion-minimal sufficient parking-map clearing subsets**, not universal necessity. It does **not** learn destination selection, motion planning, obstacle movement order, or travel.
2. **Non-learned scene-similarity index** retrieves previously witnessed robot motions for a proposed object/source/destination move. A 3×3 and 4×4 local scene descriptor, global categorical occupancy, actual robot state, object/geometric/grasp compatibility and multiple motion modes inform retrieval; exact certifiers decide whether a candidate motion is reusable. A lookup miss is not physical infeasibility.
3. **Non-learned joint search** explores relocation object, destination and *motion-mode* choices in hypothetical intermediate scenes. Occupied slots are updated after every hypothetical move, including freed source slots. Optimize lexicographically `(number of physical relocations, total measured robot joint travel)` with **no subjective risk term**.
4. **Physical verification and replay** certify every selected relocation, transition and the final target task. A zero-move solution is always tested first, to avoid disturbing already-feasible scenes.

**Primary scientific hypothesis:** At fixed candidate actions, simulator/certifier rules, motion-index experiences, certification and computational budgets, can learned D-guided expansion identify executable rearrangements with better success/efficiency than geometry-based guidance? Measure the *incremental effect of learning*, not simply whether search infrastructure works.

**Scientific honesty:** If geometry, uninformed or oracle guidance does as well, or D's retargeted predictions remain poor, the conclusion is negative/inconclusive. Do not rename that a win. Similarity-indexed trajectory retrieval, lazy evaluation and lexicographic search are established algorithmic ideas; do not claim them as a new learning contribution.

### 0.1 P14 facts to preserve and correct

- P14 engineering: 6,032 provenance-backed relocation traces; 4,838 indexed after excluding P13 blind roots; 278 absolute source–destination keys; approximately 805 reported swept modes; 166/276 (60.1%) candidate-pair index coverage. 150/150 sampled original-scene replays certified.
- Current D3: six roots common to five guidance variants; D 4/6, others 3/6; exact paired p=1.0. No established D advantage. One extra D success depended on exhausting planner budgets in the other methods.
- Current `p14_d_search._move` returns the **first certified witness** for each object/destination and does not preserve alternate ending configurations; therefore global minimum travel over indexed modes is **not** established.
- `p14_d_search._target` collapses non-verified planner outcomes to `None`; planner unknown is not a certificate. The `depth_exhaustive` flag therefore cannot be read as physical proof that all shorter plans fail.
- The object candidate list comes from existing `ORDERED_TEACHER` sequences; each object can be moved at most once; slots are restricted; search is depth-bounded. That is a restricted graph, not global rearrangement optimality.
- `root_variant()` changes target index/flags but retains `R.goal` and existing visual/scene features. The physical arbitrary-target probe used a different placement goal. The 45.7% agreement is a failure of the **current interface**, not proof that D cannot generalize to arbitrary targets.
- Existing `unnecessary_moves` actually counts moves outside the **original** blocker union; these are not equivalent to redundant moves.
- `lookup_candidates()` ranks similar contexts but has no learned/validated minimum similarity threshold; similarity can increase speed, not certify feasibility. The most popular swept mode is only a rank prior, never a safe intersection/majority-mask substitute.
- P14-B: P13 success 0.734 is correct, but historical B advantages were mostly admission-threshold effects. Thresholds matched on validation achieved **different** admissions on test (e.g. B 83.5%, B-F4/F5spm 90.2%); label/ranking and admission need separate attribution. No fresh B retraining is approved inside the core D study.

Every P10–P14 experiment artifact, frozen checkpoint, historical report and manifest is **read-only**. Produce P15-specific versioned corrections or analyses; never silently rewrite earlier conclusions.

## 1. Engineering constraints and repository discipline

- Start by checking `git status --porcelain`, `git rev-parse HEAD`, `git rev-parse origin/main`, actual hashes of `P14_FINAL_MANIFEST.json`, `P14_PREREG.json`, P14 index, P14 model snapshots and all P14 search/eval files. Fetch origin before making claims about remote equality. Document any dirty user files. Do not stage/delete the user's two root PDFs or other unrequested modifications.
- Read the source implementations **before editing**: `p14_sweep_index.py`, `p14_d_search.py`, `p14_eval.py`, `p14_audit.py`, `d_blockers.py`, `abc_models.py` (`Root.numeric`, context), `learn_data.py` (`root_record`, image/anchor semantics), `motion.py` (`check_record`, `certify_trajectory`), `geometry.py`, `skill.py`, `p10b_dataset.py` (`d_labels`), `p13_pipeline.py` and `p13_scenes.py`. Check the actual `config.toml` and trajectory saving routines.
- P15 is a **small extension**: prefer updating P14-owned modules in clean, reviewable commits, but preserve old behavior and P14 results through explicit versioned entry points. If this would alter historical replay unexpectedly, add a minimal `p15_*` module rather than invasive changes. Target **3–5 short new modules, preferably under approximately 350 lines each**, plus a test file and reporting script. An oversize file requires justification. No framework explosion.
- Version all schemas (`P15_*_V1`), lock random seeds and settings, emit deterministic run IDs, include unique root/query identity, code/checkpoint/index hash, robot/scene/goal hashes, split, method and resource accounting for every result. Use robust resume support; never overwrite a completed episode.
- Distinguish three evidence grades: sound `CERTIFIED_INFEASIBLE` for its precise declared claim; `VERIFIED_FEASIBLE` motion witness; and `UNKNOWN`/`UNRESOLVED`/`BUDGET_INFEASIBLE`/`NO_LIBRARY_WITNESS`. Do not combine the latter with certified physical impossibility.
- No teacher/planner calls during D **prediction**. Planning for on-demand edge/goal verification is permitted and metered separately. Do not train/calibrate with evaluation-root labels.
- Preserve P14's strict fixed-base motion-reuse rule: use the **same absolute source/destination cells** and robot-compatible motion; a matching relative displacement at other absolute cells does **not** justify applying a shifted joint trajectory.

## 2. Stage P15-0 — source audit, error inventory and reproducibility

**Deliverable:** `responses-phases/0073_P15_0_P14_Source_And_Evidence_Audit.md`, `runs/p15/P15_0_GATE.json`.

Build a source-to-claim matrix of every P14 issue above. Check the replayed witness count and exact placement consistency; verified vs unknown statuses; stated average CPU; existing index provenance and held-out exclusion. Recompute five-method P14 D3 table and P14 matched-admission table using stored JSON, including the 6 common root IDs. Verify that historical artifacts are byte-for-byte unchanged via hashes and that the checked-out source matches commit `cbd5d9b…` before proceeding.

**Gate 0:** No silent numerical disagreement and no dirty user-file loss. If unexpected deviations exist, stop or isolate and report them.

## 3. Stage P15-1 — correct D's arbitrary-target interface *before retraining*

**Deliverable:** `responses-phases/0074_P15_1_Target_Goal_Conditioning_And_Recursive_D_Probe.md`; source/tests and `runs/p15/retarget/` evidence.

### 3.1 Query semantics must match the actual physical action

For a hypothetical scene state `S_k`, current robot joint configuration `q_k`, a target object `o`, and a declared placement goal `g_o`, the D query must represent the **same full pick–carry–place–retreat task** as the physical teacher/probe. The earlier P14 comparison used D with the original `R.goal` while the physical planner tested a newly selected destination. That is not a matched test.

Implement a **single validated scene-to-D-input builder** using the existing appearance anchor and feature encoding. It must reconstruct, not partially patch, at least:

- object positions/footprints, object presence, movability, target-role flags;
- selected `tid`, `goal_xy`, target-relative geometric features and their numeric normalization;
- current `robot_q`, recomputed `robot_fk_joints`, robot base/context values;
- visual tokens or anchored image features appropriate to the changed scene/target/goal; explicitly inspect whether the existing rendered channels/markers encode target identity and destination. If labels/semantics in visual features cannot be regenerated faithfully, mark the query unsupported rather than pretending the old visual tokens are unchanged. Cache only when scene+target+goal+robot+render context genuinely match.

Inspect `abc_models.Root.numeric` and D's `forward` to verify exactly which fields actually drive predictions. Assert `target_id != original_t0` changes all intended channels, and that changing `goal` changes `R.goal`, `R.ctx` and numerical features. Preserve object ordering/IDs and pool indexing. Avoid treating the moved obstacle itself as a blocker. For a relocation search query, include the intended slot, or explicitly distinguish a **pure pick accessibility** question from the *full placement feasibility* label: do not compare them as if identical.

### 3.2 Tests and measurement

- Synthetic unit tests: target swaps, goal swaps, robot-q changes, object relocations, image/anchor changes, cache-key stability and double-computation equality to the original target query.
- DEV matched-query physical probes: use the identical frozen seed, scene, target object, destination, starting q and full physical action on both sides. Record VERIFIED, sound CERTIFIED and UNKNOWN separately. Do not report binary accuracy on UNKNOWN or conflate `BUDGET` with infeasible. Test multiple destination slots and independent families/roots; target approximately 40–60 decided probes, subject to preregistered cap; stratify by physically feasible/infeasible and feasible-original controls. Use paired old-interface-vs-corrected-interface accuracy, NLL/Brier/AUROC (if class diversity) and uncertainty by independent root, not pooled highly correlated query count. Count physical calls and data coverage.
- If transfer still fails, **do not automatically start retraining**. Diagnose training target-role distribution, arbitrary-object semantics, D's candidate pool and whether the supervision is target-specific. A separately gated small D arbitrary-target retrain is authorized only after a verified failure with the corrected interface and an agreed preregistered protocol in this contract (below). The learned outputs remain feasibility and blocker-union prediction; no learned destination or order policy.

**Retarget gate:** Only turn on recursive D expansion priority if the corrected interface is meaningfully predictive on physically decided temporary-target queries; an indicative acceptance threshold is balanced accuracy ≥0.70 and feasible recall ≥0.70, with sufficient per-class roots. These are **engineering-use thresholds**, not evidence of generalization or a significance claim. If it fails, retain D's original-target guidance but disable/ablate recursive queries. Geometry-only recursion is an allowed control.

### 3.3 Optional bounded retrain, only if necessary

If corrected frozen D fails, run **at most one** clearly separated three-seed small retrain of D and a matched D-pairless control on *training-only* scene/goal retargeted examples; use exact prior architecture if possible, feasible-original and blocked controls, and exact verification/certificates. Do not reinterpret operational negatives as proof. Freeze a separate retargeted evaluation roster and model predictions before its labels; withhold a positive claim if the frozen test cannot be populated. Cap training and teacher work as in §10; if projected cost would exceed the cap, do not force it. Keep frozen P13 D as the primary reference; treat retargeted D as a **new** model with clearly separated data and comparison.

## 4. Stage P15-2 — strengthen similarity-indexed multimodal motion evidence

**Deliverable:** `responses-phases/0075_P15_2_Scene_Similarity_Sweep_Transfer_And_Motion_Modes.md`, frozen versioned index/config and `/runs/p15/lookup/`.

### 4.1 Data/evidence boundaries

Use P14's real `relocation.npz` with provenance, physical robot geometry and scene-at-relocation reconstruction. Confirm `q`, gripper opening, all phases, attachment, `held_local`, released pose, original-source scene and certification. Never fabricate a sweep from source/destination cells. Index held-out split exclusions must be enforced by **root, geometry fingerprint and trajectory lineage**, including alternate aliases/episodes; audit repeated near-identical appearances and per-source support. A record from the same physical root across arms/seeds counts as **one independent support**, not several.

### 4.2 Hard compatibility versus soft similarity

Use a two-stage retriever:

1. **Hard safety/kinematic compatibility:** same absolute (source,destination), compatible footprint, object shape/kind/grasp-offset class where physically relevant, correct robot/base geometry, attachment metadata and reconstructed goal/placement, and valid starting-q transit. The old implementation hard-filters radius but stores `kind` and `held_local`; audit whether these should be hard filters or verified equivalent classes. Do not eliminate valid motions merely on arbitrary visualization labels. Recorded `q_start/q_end` must be preserved.
2. **Soft scene similarity:** source+destination 3×3 and anchored 4×4 categorical windows, plus full 8×8 occupancy. Explicitly handle off-board, fixed obstacles, movable objects, target identity and empty-space dominance. Compare local-only, global-only and combined; consider occupied-cell-weighted similarity as a *DEV-only* candidate alternative. Version and freeze chosen weight/thresholds **before** evaluation. Compare exact-score ranking, thresholded lookup and no-threshold lookup; threshold controls **cost**, not whether the motion is physically possible.

Groups of similar swept volumes must be based on an explicit recorded motion signature, using IoU overlap of conservative per-phase sweeps (or documented whole-path IoU) and final robot pose to avoid merging incompatible endings. Explain that greedy IoU grouping is order-dependent and test invariance/sensitivity to witness record permutation or replace with deterministic canonical clustering. Record **independent root support** and raw count separately.

### 4.3 Non-interchangeability of motion modes

Maintain **multiple separately certified trajectories** for the same source/destination. Rank by independent support, similarity and measured travel, but do not discard a rare one after the popular mode certifies. Cache successful adaptations only after physical certification; never add blind-evaluation witnesses to an evaluation index. The conservative per-phase sampled swept grid is a screening/indexing feature; it does not prove clearance or infeasibility. Exact trajectory certification remains mandatory after a successful start-transit check.

Generate matched trajectory-transfer benchmarks from held-out **different-root** scenes for the same absolute move; evaluate: `top1_certifies`, `any_topK_certifies`, attempts/certifier calls, first-certified cost, best-certified cost, rare-mode rescue, online fallback, CPU and precision of similarity ranking. Include cases where endpoints are free but robot links collide midway, where the popular mode collides but a rare mode is valid, and where the new starting robot q cannot transit to the recorded q_start. The rare-mode case must be a **real certified counterfactual witness** if claiming observed transfer, not only a mocked unit test. If none exists, explicitly label the real-world frequency unmeasured.

**Lookup gate:** meaningful held-out retrieval statistics and exact safety tests pass. A similarity cutoff is accepted only if it improves certification cost/precision without unacceptable loss of verified-available motions, with fallback counted honestly. Index build cost reported separately from online query cost.

## 5. Stage P15-3 — correct the joint search state, transition semantics and optimality

**Deliverable:** `responses-phases/0076_P15_3_TriState_Multimodal_Lexicographic_Search.md` and `/runs/p15/search/` proofs/counterexamples.

### 5.1 Explicit result statuses

Implement explicit enum-like status fields, never a binary `None` for both failure and unknown:

- `VERIFIED`: a continuous collision-certified action witness in the current state.
- `CERTIFIED_INFEASIBLE`: a **sound, scoped** impossibility certificate, with certificate type and quantification domain.
- `UNKNOWN_PLANNER`, `UNKNOWN_BUDGET`, `UNKNOWN_NO_LIBRARY_WITNESS`, `UNKNOWN_TRANSIT` / `UNRESOLVED`: no physical impossibility established. An unavailable straight transit is a failure **of that particular transit**, not of all possible transits to that witness start.
- `STATIC_INVALID`: a sound occupancy/support impossibility of that proposed **destination**, never a claim that all destinations fail.

Keep unknown statistics separately for each edge and goal. Preserve the exact teacher label from the original full task when available, but **do not use it to bypass blind planning**. `UNKNOWN` must not silently enter the negative class in search or evaluation. A planner negative can be `CERTIFIED` only if `skill` returns a sound certificate matching this action, not merely `INFEASIBLE` from its finite search protocol. Audit `skill`/`teacher` statuses explicitly.

### 5.2 Complete search state and candidate actions

A state is `(object -> exact pose/cell including fixed objects, current robot q, gripper/attachment state, active goal)`. A transition is `(object, slot, grasp/relative mode, exact certified witness including a certified transit)` with resulting state `S', q'`. The lookup is a **multi-edge provider**, not a single best edge. Keep multiple distinct `q'` outcomes. For a fully sampled finite candidate graph, accept non-dominated states: with the same exact occupancy, same compatible joint state and same remaining allowed moves, keep only the one with no worse travel; otherwise retain the alternatives. An epsilon/rounded-q merge may support speed, but cannot support a proof of exact optimum unless equivalence is certified.

- Always evaluate the **original no-move task** first.
- Enumerate current free destinations; moving object A to s1 occupies s1, frees A's old slot, and changes every following collision check. Never simultaneously assign the same occupied slot to another object. Two destinations overlapping in robot/object footprints must be excluded.
- Search movable objects from the declared action domain, not only whatever happened to appear in `ORDERED_TEACHER` tokens, when implementing a genuinely **recursive** search. If the budget only permits the original restricted catalogue, preserve it as a separate `CATALOGUE_RESTRICTED` baseline and do not claim unrestricted recursion. Test extra enabling-object discovery.
- The default can remain **move-once** with at most three relocations for a bounded pilot, but record this as an action-space restriction. A test for situations requiring moving an object twice must show the restricted graph is incomplete. Consider an optional expanded graph as a separate arm; do not silently change all methods' search spaces mid-experiment.
- `D` and its variants may **reorder** candidate expansions but must not suppress any valid branch based on an uncertain probability. Geometry, uninformed and oracle use the identical candidate graph, index, online planner, motion verification and budgets. D cannot see hidden teacher labels. The oracle must be labelled as **oracle original blocker union only**; add a small oracle precedence/plan guide only when a physically validated plan is available and keep it distinct.
- Planner seeds must be hashes of exact `(scene/object poses, current q, target, goal, destination, grasp/mode, planner params, robot)` with no method/call-counter dependence. Cache keys must include all those inputs. Check that old/potentially censored results don't get reused when the per-query budget changes.

### 5.3 Lexicographic optimization without false proofs

Objective:

\[
\operatorname*{lexmin}_{\pi\in\mathcal P}
\left( N_{\rm reloc}(\pi),\,J(\pi)\right),\quad
J(\pi)=\sum_{\text{certified transits, relocations, goal}} J_{\rm joint}(\text{trajectory}).
\]

`J_joint` must be the same measurable unit and implementation for every method, including transits, approach, carry, place, retreat and the *final target* path. No subjective risk term. If the target may be feasible with zero moves, zero wins even over short relocation paths. Between one-move plans, compare all certified variants and terminal-q-dependent target trajectories, not just one preferred motion.

Use iterative deepening by physical move count plus a **priority queue/branch-and-bound over verified edges** at each depth, or another correct finite-graph lexicographic search. Log complete graph counts and choice dominance. The first feasible plan does NOT establish minimum travel. Explore all remaining potentially better travel alternatives unless a mathematically sound lower bound allows pruning. Nonnegative travel permits pruning when current travel already exceeds the incumbent, subject to accounting for admissible bounds and exact state equivalence.

**Separate two completeness flags:**

1. `search_enumeration_complete`: all permitted states, slots, motion candidates and goal-test branches under the **declared graph** have been visited or validly pruned.
2. `all_shorter_depths_physically_decided`: every potentially successful shorter-length edge/goal was either VERIFIED in a way considered by the search or excluded by a **sound certificate**, not merely unsuccessful stochastic planning.

Publish `MIN_MOVES_WITHIN_FULLY_ADJUDICATED_FINITE_GRAPH` only if both apply (for lower depths). Publish `MIN_TRAVEL_WITHIN_FULLY_ADJUDICATED_FINITE_GRAPH` only if the chosen depth is completely searched over its **actual available motion alternatives and terminal robot states**, with valid cost bounds. Otherwise: `BEST_VERIFIED_WITHIN_BUDGET` plus list of unresolved edges/roots; a plan may be valid without being optimal. These claims never imply global continuous-space TAMP optimality.

Allow continued search after first witness only if budget permits, with resumable frontier. Do not trade away correct label semantics to meet a CPU cap. The main report must show separately: task success, minimum-move proof coverage, minimum-travel proof coverage, and budget truncation.

### 5.4 Unit/integration adversarial tests (must pass)

Build small source-backed or physically certified cases; mocked toy graphs test algorithm invariants but do **not** count as physical evidence.

1. Already-feasible original → zero relocations, no needless moves, no D-induced veto.
2. Equal source/destination and two certified swept modes, frequent one longer → cheaper one chosen when both are in graph.
3. Mode A has shorter immediate motion but bad terminal q, mode B leads to shorter **whole plan** → B wins.
4. Popular mode collides while rare recorded mode certifies → rare remains available.
5. UNKNOWN shorter path and VERIFIED longer path → longer plan may be returned, **never** labelled minimum-move-proven.
6. UNKNOWN target check at depth0 and verified one-move plan → valid plan, zero-move optimality **not proven**.
7. A occupying s1 prohibits B→s1; after A moves again, s1 may become free in the expanded graph.
8. Distinct object IDs in identical cells/pose labels do not poison memo or cached teacher evidence.
9. One object requiring two moves is impossible under move-once and is correctly reported as excluded by that restricted action domain.
10. Same state reached at different costs: safe dominance only when full physical state and remaining possibilities are equal.
11. Geometry oracle and D modes see identical physically available edge sets; guidance alters order only.
12. Budget/resume reconstructs exactly the same frontier and goal/edge outcome accounting.

### 5.5 The `unnecessary_moves` erratum

Rename existing metric to `moves_outside_original_blocker_union`. It is not the count of unnecessary actions. A moved member of the blocker union can be redundant when alternative minimal clearing sets exist; an out-of-union object can be necessary to make another obstruction movable. For true `extra_moves_vs_optimum`, compute only on physically exhaustively adjudicated cases:

\[N_{\rm extra}=N_{\rm found}-N_{\rm min,verified}\]

and mark it UNKNOWN when no optimum is certified. Report object-level precision/recall separately; no blanket zero-unnecessary-moves claim based only on union membership.

**Search gate:** All failure/unknown semantics, mode/state optimality examples and replay checks pass. Any finding based on a truncated or censored graph remains `BEST_VERIFIED`, not optimum.

## 6. Stage P15-4 — decouple the search efficiency question from D diagnosis

**Deliverable:** `responses-phases/0077_P15_4_Diagnosis_vs_Geometry_Search_Ablation_Design.md` plus frozen hypothesis/roster files.

Implement the same search solver with guidance policies:

- `D_frozen`: original-target D with correct current-scene inputs; recursive temporary-target priority **only** if P15-1 gate passes.
- `D_pairless`: matched D-pairless with the same retargeting policy.
- `Geometry_same_gate`: a **common original-feasibility gate** for all guides followed by geometry blocker priorities. This isolates blocker ranking from feasibility-gate superiority. Also report existing raw geometry un-gated comparator separately.
- `Uniform`/uninformed: deterministic tie-break with no learned guidance.
- `Oracle_union`: teacher-labelled original blocker union, declared nondeployable; does not know correct moves, destinations or order. A tiny `Oracle_plan` diagnostic may be added only on independently physically verified plans; do not equate union labels with optimal sequences.
- Optional `D_without_recursion` and `D_retargeted` when P15-1 actually supports them. No new learned motion/destination policy.

Report **two fair budgets**: (a) identical physical check/online-planner/goal-check counts and action space; (b) equal total **CPU or wall** allowance **including D inference and index lookup**. Normalize implementation overhead. D consuming +40 CPU-s/root must count against real end-to-end efficiency. If D improves success only because it is allowed more CPU, do not call it a fair advantage. Report success-vs-CPU and success-vs-planner-calls anytime curves, expansion ordering diagnostics, and *oracle–geometry* parity/non-parity.

**Very important:** Guide value is largest when budget truncates the search; for fully exhaustive exact finite graphs, all sound guidance orderings should converge to the same optimal plan. Therefore measure both bounded-budget solved rate and complete-graph optimality, never claim guidance improves a globally optimal exhaustive answer.

### 6.1 Explicit comparison protocol

- P14's 24-root roster is **previously seen**: six roots already have outcomes. Re-running it after changing the search algorithm is a **retrospective/exploratory correction**, *not* new prospective confirmation under the unchanged P14 preregistration. Record all 24 root IDs and overlaps.
- Only a **new, independently sampled and preregistered** test roster whose results have not been inspected can support a new confirmatory P15 claim. Use mixed feasible-originals, one-blocker, complementary two-blocker, order-dependent and alternative-minimal-set cases. Freeze selection rules and scene grammar *before* physical evaluation; don't cherry-pick based on D's predictions. Mechanism-conditioned and unconditioned distributions must be reported separately.
- For fresh holdouts, avoid index leakage by root, geometry hash and trajectory lineage. Freeze train/dev/test splits, index, modes, D/checkpoints, threshold and exact algorithms plus budgets **before** test teacher labels / motion outcomes. Push preregistration and frozen model decisions to origin; hash-commit sealed labels before unseal, where applicable. If constructing new scenes requires costly planning, use non-model geometric screens in DEV only and freeze screens before holdout.
- Do **not** call `N=24` automatically decisive. Calculate exact paired sign-test power for plausible discordant-root counts. A 1/0 discordance gives p=1 even at N=24 if the other 23 are ties. Report CIs and the number of informative pairs; stop at `UNDERPOWERED` if necessary, not because results are negative.
- Predefine primary endpoint **paired strict physical task success** (independent replay confirmed, unknown/budget counted unsuccessful but stratified). Secondary: success-versus-budget, node expansions, expensive planner calls, goal checks, D calls, CPU+wall, moves, travel on both-solved roots, extra moves only where optimality proven, coverage of sound certificates, proven minimum-move/travel flags, and root-level uncertainty. Do not condition the primary on successful roots.
- No adaptive stop based on observed p-values; resource-only stop is permitted with outcome-blind root order. Preregister multiple-testing family; if more than one primary guide contrast is introduced, correct it (Holm). Cluster uncertainty at root; seeds sharing a root are correlated. A non-significant result does not establish equivalence.

**D comparison gate:** If cost model from independent DEV runs predicts inability to complete the frozen roster within the declared CPU cap, either (i) request no user action but reduce to an explicitly descriptive, fixed pilot and stop, or (ii) revise the prospective protocol *before outcomes are collected*, make a new prereg and call it a new study. Never silently shorten a confirmatory roster after seeing results.

## 7. Stage P15-5 — run controlled D vs geometry benchmark

**Deliverable:** `responses-phases/0078_P15_5_D_Rearrangement_Benchmark_And_Anytime_Performance.md`, full run ledgers, plots and physical-case figures.

### 7.1 First: close previous 24 roots without overclaiming

After P15-1 through P15-3 correctness fixes, rerun the same 24 P14 roster roots with **all baseline methods, all fields reset, equal budgets and physical verification**. Explicitly call this a P15-algorithm retrospective benchmark, not a continuation of an unchanged P14 estimand. Do not reuse its six old outcomes as if newly blind. Budget planning must use observed 135–176 CPU-s/root from P14 and the larger cost of multimodal branching; forecast with a small independent DEV pilot and record a hard cap.

The method comparison must use an identical initial scene, candidate slots, indexed motion library and online planner, and count D inference. Report rerun differences from the old P14 six-root evidence with changed semantics.

### 7.2 Then: prospective confirmation if and only if the resource gate supports it

Build and freeze a **new** root roster with at least 24 independent roots, preferably 32 (a mixed family cohort and a mechanism-conditioned cohort, each with feasible controls). Include physically decided original tasks and sufficiently many multi-object cases. Root diversity and proof-grounded interactions take priority over a larger but trivial one-move count. Root labels and true minimal clearing sets may be UNKNOWN; report coverage rather than silently replacing roots. Avoid training/evaluation overlap with the lookup. A larger study is permitted only after measured cost projection fits §10; if not, publish the exploratory 24-root results and stop P15 with an explicit underpowered verdict.

For a novel blinded cohort, freeze the scene generators, roster, supporting certificates, candidate slots and possible actions, index, D models, D interface version, guidance, motion budgets and analysis prior to label acquisition. Independent teacher/certifier decides labels with provenance; planner censored cases are not negative proofs.

### 7.3 Required figures and analyses

- Visualize initial scene, D-vs-geometry blocker scores and optional false-feasible/false-infeasible diagnoses, the retrieved ranked swept-mode alternatives, source/goal-local context, occupancy updates after each hypothetical step, certified robot-body swept regions and actual joint-space trajectories, final retrieved target, and how the chosen order/destinations differ by guide.
- Animate only actual replay-certified joint sequences; if a method fails, show **why** (lookup uncovered, failed start transit, physical collision, candidate exhausted, target unknown, budget depleted) without inventing successful motions.
- Plot root-paired success-versus-budget curves, runtime/expansions breakdown, index topK certification curves, and lexicographic travel/move outcomes on co-solved scenes. Mark all budget-truncated and UNKNOWN states.
- Include a small list of cases in which D is *better*, D is *worse*, and both tie; if no such case exists, don't fabricate it. For every divergent root, state the actual reason and whether guidance truly changed expansion order before online budgets were used.

## 8. Stage P15-6 — lookup ablations and generalization tests

**Deliverable:** `responses-phases/0079_P15_6_Local_Global_Modal_Similarity_Ablations.md`.

At identical search/physical-check budgets (and with time separately metered), compare:

1. `combined` 3×3/4×4 + global, multimodal;
2. local-only;
3. global-only;
4. combined with held-out calibrated minimum scene-similarity threshold;
5. modal-top1 (known possibly incomplete);
6. all individual witnessed trajectories versus representative modes (to quantify clustering loss);
7. online-only, no lookup;
8. optionally a wider compatible-index catalogue to test whether index coverage is the main bottleneck, only if a DEV-only expansion can be frozen without leakage.

Readouts: independently grounded top1/topK transfer success, real rare-mode rescue, collision certification calls, time per query, online fallbacks, solved roots, move count, travel and global success. **Coverage must be separated from precision:** 60% index match coverage does not mean 60% reusable trajectories. Cache/index construction CPU reported as amortized break-even analysis over query count, not hidden.

Keep modes and candidate slots aligned; if one ablation changes the number of available edges, describe it as a resource/coverage ablation and do not interpret downstream success differences as solely better similarity scoring.

## 9. Stage P15-7 — B evaluation closure, no unjustified retraining

**Deliverable:** `responses-phases/0080_P15_7_B_Admission_Ranking_And_Calibration_Closure.md` and `runs/p15/B/`.

This is **secondary**. Preserve P13 and P14 checkpoints and choices. Do not run the ~45k-CPU teacher cohort from P14 under the D budget. Only use saved labels and any existing independent public/new holdout genuinely suitable for separate analysis; if data aren't sufficient, say so.

1. Correct terminology everywhere: B, A, C, F3-off, F4-off and F5(combined)-off were matched by **validation** admission, not exact held-out admission (P14 test admission B 0.835, F4/F5spm 0.902, B-F2 0.910). Report both validation and test admissions.
2. Factor admission vs candidate ranking using **common-scoreable root/candidate sets**: full candidate-score permutations, top-k or first-feasible rank among physically adjudicated candidates, baseline oracle lower/upper bounds and abstention/coverage-risk curves. Handle unknown candidates as censored, not negative. A model may perform similarly in conditional success because it selected easier attempted roots; avoid unpaired comparisons as proof of equal ranking.
3. Evaluate original-feasible zero-move selection separately: feasible recall, zero-move chosen, unnecessary relocation/abstain, Brier/NLL, per-bin reliability with root CIs, as well as mixed-distribution joint four-bit NLL and original-infeasible retrieval. Test whether validation-only monotone calibration (temperature **plus bias**, optionally isotonic with enough validation data) changes decisions under frozen candidate rankings; don't fit to test labels.
4. Compare a lean, no-F3/no-F4/no-HO **inference configuration** only when the exact architecture and checkpoints support it; do not call turning off learned modules post hoc equivalent to matched retraining. A generic-only F5 ablation is still **not experimentally established** without training.
5. Maintain keyed query ontology as a correctness invariant unless an alternative proves exact listing/omission equivalence. DINOv2 is an input representation, not evidence of geometric causal understanding by itself.
6. If the conclusion remains that B's extra factors have no deployment contribution under fair admission, report that; no sweeping claim that full B outperforms geometry or is 3D-ready.

**Do not start a fresh B retrain in P15.** Deliver a *separate costed, preregisterable P16 proposal* if future B confirmation remains worthwhile. This avoids consuming resources necessary to evaluate D.

## 10. Resource ceilings, stage stops and statistics

These are upper bounds, **not targets**. Report `process_time`/process-tree CPU honestly; account for model inference, certifier, teacher, index-building and regression separately. Never repair an overcount with unvalidated arithmetic. Use guarded jobs, root-level checkpointing, outcome-blind order and auditable stdout/return codes.

| Category | CPU-s hard cap | Notes |
|---|---:|---|
| Source audit + correctness tests | 3,000 | P15-0/1 static tests, old artifact reconciliation |
| Arbitrary-target physical interface probes | 8,000 | DEV only first; no retarget-train until gate |
| Optional D/D-pairless retarget training | 10,000 | Only if P15-1 fails and prospective supervised data can be collected fairly |
| Optional retargeted training teacher labels | 15,000 | Must be separate from blinded evaluation labels |
| Index transfer and ablation development | 6,000 | Real trajectory certifications and offline replays |
| Search correctness development | 8,000 | Multi-mode, finite-graph toy proofs, physical regressions |
| Old 24-root retrospective D benchmark | 27,000 | Budget reviewed from observed DEV cost before launch; all five guidance arms |
| **Fresh prospective D benchmark** | **38,000** | Conditional on cost/power gate; no significance-driven stopping |
| Lookup ablations and supplementary runs | 12,000 | Conditional on D core completion; keep separate |
| B saved-data diagnostics | 3,000 | No new teacher labels or retraining |
| Regression, replay and manifest | 3,000 | All historical + new tests and six replay fixtures |

These ceilings authorize **bounded** work after each stage gate; a budget-forecast stop is a valid `PARTIAL/BLOCKED` scientific outcome, not a failure of integrity. Do not take CPU from one category to silently exceed another. For the fresh benchmark, make a resource forecast using independent DEV roots with confidence bounds, and design around **both** counts-based and wall/CPU fairness. If the optional retrain would be underpowered or the teacher labels incomplete, do not launch it. Training/relabeling does not guarantee arbitrary-target transfer.

Primary D hypothesis for a new holdout: paired strict physical success D vs geometry-common-gate, tested at root level with two-sided exact paired sign/McNemar-equivalent test and a root-paired confidence interval. Pre-register alpha=0.05, effect direction and minimum practically meaningful improvement (e.g. 10 percentage points and/or ≥20% fewer planner calls at non-inferior success) **before** seeing labels; account for both if co-primary. All secondary methods/endpoints described as such, with familywise correction if promoted to additional primary. Always report informative discordant pairs and precision/uncertainty. If insufficient root pairs decide the question, status is `UNDERPOWERED`, not equivalence.

A real physical success requires **all** recorded/replayed trajectories independently `CLEAR`, correct object released at the requested destination, target actually retrieved/placed, and correct intermediate scene states. Distinguish simulation rollout from actual hardware (not part of this stage).

## 11. Regression, artifacts, gates and final deliverables

**Required tests** (beyond existing 438/438 and 6/6 archived replays):

- exact source/goal/retargeted D input contract and visual context;
- comparison to same full physical pick-place probe, UNKNOWN accounting and paired scoring;
- nominal/rare/all trajectory modes, collision and q-start transit checks;
- source/destination identity, footprint/grasp shape, per-phase sweep and actual certifier consistency;
- finite graph exhaustive vs physically adjudicated distinction;
- multimodal global travel vs first-certified shortcut;
- goal UNKNOWN propagation and correct zero-move behavior;
- move-once exclusions, extra enabling objects, destination conflicts and freed slots;
- oracle blocker-union semantics; leakage and index root exclusion;
- replay, deterministic state-based seeds and resumable searches;
- similarity ranking vs absolute compatibility and no valid-motion loss without an explicitly labelled threshold/fallback;
- admission/ranking decomposition and no use of blind labels for thresholds;
- all previous historical tests with unchanged fixtures.

**Report sequence, in `responses-phases/`:**

- `0073_P15_0_P14_Source_And_Evidence_Audit.md`
- `0074_P15_1_Target_Goal_Conditioning_And_Recursive_D_Probe.md`
- `0075_P15_2_Scene_Similarity_Sweep_Transfer_And_Motion_Modes.md`
- `0076_P15_3_TriState_Multimodal_Lexicographic_Search.md`
- `0077_P15_4_Diagnosis_vs_Geometry_Search_Ablation_Design.md`
- `0078_P15_5_D_Rearrangement_Benchmark_And_Anytime_Performance.md`
- `0079_P15_6_Local_Global_Modal_Similarity_Ablations.md`
- `0080_P15_7_B_Admission_Ranking_And_Calibration_Closure.md`
- `0081_P15_8_Scientific_Decision_And_3D_Readiness.md`
- `P15_D_REARRANGEMENT_AND_B_CALIBRATION_DECISION.md`

**Required machine-readable artifacts:** `runs/p15/P15_PREREG.json`, each stage's `P15_*_GATE.json`, `P15_CODE_MANIFEST.json`, `P15_FINAL_MANIFEST.json`, source/checkpoint/index hashes, frozen algorithms/rosters, provenance/check certificates, full run logs, budget ledger including killed/unknown jobs, episode/trajectory records, paired statistics, root case taxonomy and results. Save GIFs and scene/trajectory figures under `visualizations/p15/`. A report must state exact underlying JSON paths and commit hashes.

**Workflow:** work gate-by-gate. Push the prereg, source and frozen test choices **before** collecting new blind labels. Keep historical artifacts unchanged and do not force all stages to show positive results. Run full historical tests/replays after final changes. Commit and push completed work, fetch the remote and compare SHAs; list any excluded dirty files.

### Final response must be numerical and decision-oriented

Claude's final reply must include:

1. Verified final commit and what code changed (and what historical files remained untouched).
2. Retargeting: exact matched physical task, total/decided probes, feasible/infeasible/unknown counts, before-vs-after D metrics, and if recursion was enabled, disabled or retrained.
3. Lookup: evidence counts, distinct independent motion modes, indexed/root-leakage exclusions, transfer top1/topK certification, rare-mode rescue, false retrieval and online fallback.
4. Search: verified task successes, tri-state unknown/certificate counts, statuses of minimum-move and minimum-travel claims, number of distinct terminal-q alternatives and branch-and-bound coverage.
5. D vs geometry vs D-pairless vs uninformed vs oracle: **identical-cohort root counts**, paired success/CIs/p, CPU and planner-call differences, solved-root move/travel, D inference cost, budget curves, failures and prospective-vs-retrospective distinction.
6. Lookup ablation results, or clearly BLOCKED where not run. Don't infer the value of a similarity threshold from mocked examples alone.
7. Corrected `moves_outside_original_blocker_union` versus true extra-move metric on proven optima.
8. B's validation/test admission, common-candidate ranking, original-feasible no-move behavior and any validated calibration change, with **no** fictitious lean-B retrain.
9. Actual resources spent vs caps, full regression/replays, figures, report names and explicit scientific verdicts: `SUPPORTED`, `NEGATIVE`, `UNDERPOWERED`, `PARTIAL`, `BLOCKED`, or `NOT_TESTED`.

**Decision rule:** P15 is complete only as an engineering/scientific *audit* when all executed claims are sound and all missing experiments are openly labeled. It need not establish a positive D advantage. Moving to 3D is **not authorized** by this contract; the P15 report can recommend whether that move is warranted.
