# 0045 — P17: Complete 2D Methodology, Correctness and Prospective Evidence for B and D

**Binding implementation and experiment contract for Claude Opus 5.5 High**  
**Project:** `Narendhiranv04/latent-causal-tamp`  
**Starting reference:** P16 final `bd9a2e88ff1dbd390616f7a42179c14f69d6780a`  
**Scope:** **2D ONLY.** No 3D simulator, 3D robot, 3D certifier, 3D training, 3D benchmarks, or new 3D migration documentation. The already existing P16 3D specification is historical context only.  
**Method tracks:** Evidence-based lean **B** (complete ordered-repair outcome learning, with isolated generic-coupling experimental arm) and pairless **D** (initial/arbitrary-target feasibility + scoped blocker-union probabilities, with non-learned, physically verified joint rearrangement search). A, C/LC, SF, full historical B/D, geometry, uniform and oracle are controls.  
**Acceptance philosophy:** Implement **both** methods to a rigorously defined *complete finite 2D domain* and evaluate them fairly. **Do not demand positive paper claims as an implementation gate.** Preserve negative findings. Do not silently redefine a model or label to obtain better results.

---

## 0. Authority, audit requirements and immutable scientific judgments

### 0.1 Read and reconcile first; source-of-truth order

1. Existing project methodology/implementation: `latent_causal_tamp_methodology_v1_8.md`, `latent_causal_tamp_implementation_guide_v2_0.md` (if actually in repository), and earlier documents for provenance; the old F1–F5 specification is *historical intent*, not permission to reinstate rejected factors.
2. `instruction-phase-md/0044_P16_Dual_Track_B_and_D_Methodology_Completion_Contract.md`, P16 reports `responses-phases/0082_*` to `0089_*`, `responses-phases/P16_B_AND_D_SCIENTIFIC_DECISION.md`; inspect `runs/p16/P16_FINAL_MANIFEST.json`, `P16_PREREG.json`, original sealed execution/labels, `B_TEST.json`, `D_TEST.json`, root-level records, checkpoint and policy hashes.
3. Read corrected P12–P15 conclusions: P12 0053–0058 and P12 decision; P13 0059–0066 and decision; P14 0067–0072 and decision; P15 0073–0081 and decision. Record exact resolved errata, not initial inconsistent versions. Previous P10–P11 method development remains archived.
4. Read real source: `p16_common.py`, `p16_motion.py`, `p16_b.py`, `p16_d.py`, `p16_eval.py`, `d_blockers.py`, `abc7_models.py`, `abc8.py`, `unique_factor.py`, `unique_factor_keyed.py`, `joint_likelihood.py`, `p15_retarget.py`, `p15_lookup.py`, `p15_search.py`, `p14_sweep_index.py`, `motion.py`, `geometry.py`, `skill.py`, `ordered.py`, certificates and `tests/test_p16.py`.
5. **Authority:** actual physical witness + scoped sound certificate > preregistered experiment and raw results > later validated errata > preliminary narratives > conceptual documents. If instructions clash with implementation, write a specific discrepancy and resolution in P17 reports. Never alter archived results to make them consistent.

### 0.2 Preserve the established component verdicts

- **B keep:** frozen mask-pooled DINOv2-small inputs and trainable projection, scene/physical-query unary logits, physical-query *keying*, F2 order-sensitive representation, explicit empty repair, analytic static check. These are methodological defaults, though the observed magnitude of their benefits remains cohort-specific.
- **B remove from lean default:** learned F1 static head, F3 scene pair, F4 omission pair, combined F5 (generic+HO), learned J. The higher-order F5q remains deferred. Omission queries themselves may still exist, but without an F4 pair factor.
- **B generic-only F5 (`LB+G`):** P16 showed **new positive one-cohort evidence** on the same trained data and three seeds: 0.652 strict success versus LB 0.509, with most improvement in initially feasible roots. **Treat as a supported experimental arm needing independent replication and attribution**; do not assert that the generic factor directly changes the original-scene marginal at inference.
- **B historical facts:** the P16 calibrated LB+G did not convincingly beat ALWAYS_EMPTY on the test mixture (0.652 versus 0.643). The prior P13 admission effect remains valid. P16 no-op improvement versus frozen K-B changes both data and architecture. F2 was supported by targeted earlier mechanisms, but P16's natural-heavy endpoint did not resolve an order-on advantage.
- **D keep:** feasibility prediction, *pairless* blocker-union prediction, analytically distinct conditional and feasibility-gated marginals, full model as frozen paired comparator only. A blocker **union is not a set of all required actions**. NO_CLEARING_SET_WITHIN_POOL / INCOMPLETE / NON_MONOTONE / UNKNOWN do not receive confident all-zero mask supervision.
- **D historical facts:** P15 D/geometry 27/32 each, P16 21/21 each with only 4/24 DENSE roots. Learned D guide has **no demonstrated outcome or ≥20% effort advantage**; calibrated recursion used only feasibility, not validated recursive blocker marginals. P16 D retrain did not establish better AUROC than frozen pairless.
- **Shared keep:** deterministic node-budgeted physically certified planner, fixed-base real trajectory witness library, local 3×3/4×4 plus global similarity, multiple motion modes, planned alternate transits, full robot and carried-object continuous sweep certification, independent replay, scene-only candidate generation, bounded finite-graph lexicographic `(N_relocations, joint_travel)`, tri-state UNKNOWN not infeasible.
- **Corrected history:** P12 κ seed-mean estimand; F3 mean CI includes zero; F5spm removes generic+HO; P13 separately trained parameter-matched ablations; P14 validated coverage is not equal test coverage; P15 bootstrap [0,0] is not an equivalence CI; J sign/travel corrected; P16 D NO_CLEARING_SET masking.

### 0.3 History, repo and user data safety

- Confirm local and remote HEAD and current working tree; preserve user-unrelated edits and the previously deleted root PDFs. Do not reset, clean, stage or overwrite unrelated files.
- Generate Git blob / SHA-256 audit of all historical `runs/p10`–`runs/p16`, `visualizations/p10`–`visualizations/p16`, reports through 0089, and their frozen checkpoints; historical byte differences must stay **zero**. Historical source modules can be patched only with a strong need and a new isolated regression; *prefer versioned P17 code*.
- P17 artifacts live in new `runs/p17/`, `responses-phases/0090_*` onward, and `visualizations/p17/`; P17 instructions under `instruction-phase-md/0045_*`. Explicitly record migration versus reusable old entry points.
- Write one machine-readable source-to-equation-to-label-to-evaluation trace for both tracks and a historical verdict lock. No hidden `ORDERED_TEACHER`, labels, parking assignments or family predicates in runtime generation.

**Gate P17-0:** full source audit, historical-hash check, tests/replays, explicit task and two-model declarations, actual starting SHA.

---

## 1. Precisely define what "complete in 2D" means

This phase **does not** claim completeness over infinite continuous robotics states. It completes the declared, finite, executable **2D domain** and supplies automated tests + independently certified examples across its intended logical mechanisms.

**Physical task:** Given one initial 2D robot+scene observation, `S0`, robot configuration `q0`, target object `T`, goal `g`, declared fixed/movable objects, supported grasp/placing options and a strict physical certification protocol, decide whether zero moves suffices or select verified corrective relocations ending in the target action. All candidate generation depends only on scene/task and allowed geometry; physical labels remain offline teacher evidence.

**Complete domain conditions (declare numerically after DEV pilot):**

1. B and D both accept scene-only initial information and target/goal/q, with the **same shared action-space definition**. No privileged teacher ordered sequence, clearing-set, label, oracle solution or test outcome in their production paths.
2. Zero-move, single, 2-, 3- and 4-move ordered corrective sequences supported; B must **score** the declared sequences, including repeated moves; D must search them. At least one mechanically verified repeated-object and one order-dependent slot-conflict example is required.
3. Destinations are **not** fixed to one parking slot per object: support multiple verified static-valid slots, dynamic freed source positions, finite buffer reuse, scene-state update after each hypothetically executed relocation, different robot end configurations, and at least two independently witnessed alternatives for the same source/destination when they exist. A candidate that leaves a slot occupied excludes an incompatible later assignment.
4. All accepted complete trajectories include approach, grasp, transfer, placement, release, retreat, and final target retrieval/placement; measured joint travel includes any start transit and final task. Start with no-op check. The chosen sequence is independently replay-certified.
5. Motion/planning status semantics are explicit: `VERIFIED`, scoped `CERTIFIED_INFEASIBLE`, `STATIC_INVALID`, `UNKNOWN_<reason>`. A missing motion witness, expired node budget or impossible-to-verify edge is **not** a proven physical negative.
6. Search proofs are scoped to a fully enumerated and **fully adjudicated finite action/motion graph**. If the explored graph has any unresolved edge capable of affecting the optimum, report verified best-known and lower bounds, not minimum.
7. Each of the required 2D mechanisms (section 5) must have **at least one independent real physical witness of its claimed property**, a deliberately adversarial control, and a visualization. If a mechanism cannot be constructed after systematic geometry-first attempts, mark the implementation completion `BLOCKED` for that mechanism, not `PASS`.
8. Train on sufficient distinct physical examples and verify generalization on root/fingerprint-disjoint new scenes. Keep performance and correct implementation as different assessments: `METHOD_CORRECT`, `METHOD_INCOMPLETE`, `CLAIM_SUPPORTED`, `NEGATIVE`, `UNDERPOWERED`.

**No 3D** even if 2D completes early. Do not add MuJoCo/Panda, modify P16 3D spec or deliver a P17 3D plan. P17 final is a **2D completion decision only**.

---

## 2. P17-1: fix physical-search correctness FIRST

### 2.1 D dominance-key defect — hard fail until fixed

`p16_common.search()` forbids moving the same object consecutively (`o != last`), yet its dominance key is just `(occupancy, rounded q)` and **omits the last moved object**. Two equal occupancy+q states with different `last` can have different legal next actions. Also inspect per-object move counters, attachment/gripper configuration, the remaining relocation-depth budget and any path/history-dependent restrictions.

Implement a formal state:

`SearchState = {object_poses, robot_q, gripper/attachment_if_applicable, last_moved_if_rule_active, per_object_move_counts, depth, query_contract}`.

- State equivalence / dominance must be defined against **future legal action set** and cost. Include `last` in key if the restriction stays. If removing a consecutive-move rule, show why doing so retains valid model semantics and guards cycles differently.
- `counts` alone may be necessary as a resource vector, but two states with equal geometry and q and different count vectors cannot be merged unless a proof ensures the dominating state permits a superset of future moves with no worse remaining budget; same for `last` and attachment.
- Float rounding of joint configuration for caching must not silently merge configurations with different collision/grasp outcomes. Use explicit tolerance boundaries and a conservative equivalence test; store exact query/fingerprint in certificates.
- Prevent unsound pruning of the only valid repeated-move path. Add adversarial tests with equal `(occupancy,q)` but different `last`, and identical geometry but different counts/attachment. Compare against an exhaustive tiny-state enumerator (or unit-test oracle) to validate travel optimality and minimum moves. Also test a 2D scene that physically **requires** moving the same object twice.

### 2.2 Optimality and UNKNOWN accounting

- Iterative deepening is acceptable, but branch-and-bound/dominance and terminal-state pruning must preserve lexicographic optimality. A lower-travel prefix cannot dominate if it has fewer future actions available; if path-dependent robot-state variables are omitted from the search key, fix them.
- Every candidate edge return is a structured `Status` with a set of witnessed outcomes, scoped certificates and unresolved/unexplored alternatives. If a candidate's first witness fails but others are unknown, the edge outcome cannot be promoted to certified infeasible.
- Distinguish `enumeration_complete`, `all_applicable_edges_decided`, `minimum_moves_proven`, `minimum_travel_proven`, and `best_verified_within_budget`. A planner/lookup budget censor remains UNKNOWN in proof provenance.
- Retain all distinct certified terminal robot configurations relevant to downstream feasibility. Do not prematurely discard longer first motions if they lead to better global travel or make downstream actions possible. An option may be removed only with a justified dominance relation.
- Track exact objective across all phases (transit, grasp, carry, release, retreat, target). If lower-bound travel pruning is used, justify admissibility.

### 2.3 Replace B's greedy complete-repair verifier with existential motion realization

`p16_common.verify_sequence()` chooses `best_edge(outs)` for each relocation, i.e. the least travel **locally**. This can falsely label a feasible action sequence UNKNOWN/failed if a longer first motion enables later moves.

Implement `verify_ordered_sequence_existential(scene, q0, ordered_actions, physical_provider, per_sequence_budgets)`:

1. **Hold the ordered object/destination action list fixed.** This remains B's supervision/query definition, not a learned relocation policy or an unconstrained D search.
2. For each action, enumerate all certified motion-witness alternatives (distinct terminal q, grasp/attachment metadata). Keep separate successor states and measured travel. Try alternate start transits and bounded online fallback when the library lacks a valid witness.
3. Continue through the entire sequence and target action, with updated occupancy and robot configuration. Return `VERIFIED` and one certified minimum-travel witness **over adjudicated finite alternatives**, or best certified witness with incomplete-travel-optimality flag.
4. Only declare an ordered sequence impossible when a **sound applicable certificate** establishes that claim at the relevant step for all admissible alternatives within the explicitly certified scope; otherwise return `UNKNOWN` with failure provenance. If some branch succeeds, the sequence is VERIFIED even if other branches unresolved.
5. Keep predecessor/retreat and all trajectory record continuity in replay. Avoid B training-label leakage: truth is generated by this new physical verifier, predictions cannot influence the labels.
6. Use `verify_sequence_greedy_P16` as a frozen retrospective baseline, not the new ground truth.

**Mandatory adversarial example:** two valid first-action modes lead to distinct terminal q; only the costlier first move allows the second action and final target. Greedy verifier fails, existential verifier succeeds with certified full replay. Include an equally important example where no motion works yet the outcome remains UNKNOWN rather than a false negative.

### 2.4 Determinism, witness/provenance and cap policy

- Preserve P16's seeded node-budgeted deterministic planner. Test 5 repeats including parallel load on representative dense/repeat/slot-conflict roots; same status, hash, q_end, move count, travel and work counters. Re-check under replay after any change to state keys or certifiers.
- Shared exact cache keys must include full query contract, goal, current q, occupancy, grasp/mode, planner profile, numerical tolerances and budgets. Cache certified witnesses and sound certificates, never universalize UNKNOWN to persistent infeasibility.
- Similarity lookup remains retrieval-prior, never a motion feasibility certificate. Use all motion alternatives under declared cap, track mode support from independent roots and report transfer/rare-mode rescue. A failure of straight transit invokes a certified alternate transit, not an object-slot rejection.
- **User authorizes exceeding old aggregate CPU ceilings**: do **not** stop the P17 roster because some inherited cap was reached. Retain bounded deterministic **per-query work budgets** for scientific comparability, external watchdogs for safety, and a continuously written CPU/wall/storage ledger. Use per-root checkpoints/resume and resource estimates, not arbitrary aggregate cap-induced subset selection. Never create unbounded searches or run out of disk unchecked; only seek user authorization if truly new hardware/resource expenses are required.

**Gate P17-1:** adversarial dominance and existential verifier tests, deterministic replay, 2D physically realized counterexamples, all historical regressions unchanged.

---

## 3. P17-2: one shared scene-only 2D action/candidate interface

- `Task`: initial observed geometry, robot state, target and goal, fixed structures, gripper, allowed discrete 2D relocations. `State`: current poses and robot q, plus attachment/last/count history when relevant.
- `enumerate_movers`: every declared movable non-target object; configurable cap but **record omissions and run a widening test**. Do not pick only nearest 3 just because historical `catalogue` did.
- `enumerate_slots(state, obj)`: multiple empty supported placements computed **after every hypothetical move**, with static clearance and target/goal corridors, plus freed sources and buffers. Include a broadened geometric search to prevent the heuristic from wrongly deleting all valid placements. Widen according to deterministic policy, not model predictions. Query original geometry before all moves.
- `enumerate_ordered_repairs(Task, max_moves, per_object, slot_width, search_budget)`: **model-agnostic, deterministic** generator for B/A/C and direct baselines. It should generate 0/1/2/3/4-move candidate sequences from the same scene/action set used by D. It must avoid teacher-labelled solutions and physical-success oracle filtering; **cheap analytic statics** may be shared and declared. D's planner can explore lazily; B's proposal catalogue can use bounded lazy/beam enumeration for complexity, but count discarded candidates and publish coverage vs an exhaustive tiny-scene oracle. If an upper length is missing from B training/evaluation, make that explicit instead of silently claiming long horizon.
- Provide `compare_action_domain(B,D)` on small scenes: same legal mover/destination opportunities; explain different candidate-evaluation protocols, and ensure neither method receives verified winning sequences while the other does not.
- Preserve physical-query keying: query ID encodes initial scene fingerprint, target/goal, robot start, full ordered `(object,destination)` sequence, and verification/label protocol. Same physical sequence referenced as an omission equals one variable. Omitted action must recompute intermediate poses; it cannot reuse previous final pose blindly. Duplicate candidates must not alter root-scene marginals.
- Separate **initial-feasibility test** from physical search. A candidate never becomes labelled feasible because its final static arrangement looks feasible without executable relocation witnesses.

**Gate P17-2:** teacher-deletion test, test on 4 movers and several destinations each, multi-move coverage, identity/invariance tests, adversarial cases for dynamic freed source and conflicting slot placement.

---

## 4. P17-3: finish physically realized 2D logical mechanism families

Build from physics and geometry, with no model-dependent acceptance and with careful status evidence. Use constructor diversity, stochastic unfiltered scenes and mechanism-enriched strata, all recorded separately. **A successful constructor must provide a physical witness and a counterfactual contrast**, not just assign a family tag.

| Family | Required physical contrast and proof/witness |
|---|---|
| M0 Feasible original with decoys | Verified original target; no relocation necessary; at least one plausible-looking but redundant obstacle nearby |
| M1 Single blocker | Original target negative under scoped certificate; verified one-move repair; alternate destinations available |
| M2 Complementary blockers | Neither one alone is sufficient; a particular pair clears target (with full intervention lattice decided) |
| M3 Alternative clearing sets | `A` OR `B` sufficient; union differs from intersection, and moving both is redundant |
| M4 Ordered access chain | Correct order succeeds; reversed order is accepted certified impossible or physically demonstrated failing under declared action protocol, not merely timeout |
| M5 Intermediate swept obstruction | Candidate endpoints are free, but moving object to one slot blocks the **later full robot-link/carried-object sweep**; alternate slot yields verified overall plan |
| M6 Joint slot assignment | Naïvely assigning two movers to a single slot fails; joint distinct-slot assignment succeeds, with appropriate occupancy updates |
| M7 Buffer reuse / repeated object | At least one physically VERIFIED `A->u, B->v, A->w` or equivalent, with a **finite-domain proof** that no allowed no-repeat solution achieves the goal under the same permitted slots/modes; do not call it globally necessary |
| M8 Longer repair | Verified >=3 and >=4 relocation tasks, independently replayed, and at least one explicit no-op baseline |
| M9 Difficult negatives/UNKNOWN | Sound certificate scope contrasted with budget-exhausted unknown on similar geometry; model never trains UNKNOWN as 0 |

P16 physically realized 8/10 previous families in its 12-root DEV pilot; the missing ones included a later swept obstruction and repeat-move necessity. **These are hard P17 gates**, not optional tags.

For each family save: actual scene initial/intermediate states, robotic q, object poses, goal, accepted and rejected sequences, exact status and certificate scope, physical witness files and independent replay hash, scene fingerprint, constructor attempts/acceptance statistics. Test random-unfiltered strata separately so 'mechanism' performance is not presented as natural-scene generalization. Do not make a test set by filtering for B/D success. Keep the benchmark mechanism tags *post-hoc from physics*.

**Gate P17-3:** full mechanism-coverage matrix, real 2D rendered visuals, physically replayed GIFs for M4–M8, all historical claims preserved.

---

## 5. P17-B — complete and scientifically isolate the learned B approach

### 5.1 Model definition and retained/deferred factors

**Lean B default:** DINOv2 vision with trainable projection + numeric scene/context; keyed unique physical-query ontology; scene/no-op unaries; F2 order-sensitive predecessor representation; candidate ordered repair success logits; exact factorized Bernoulli normalization; analytic static checks. Do not train static F1, scene-pair F3, omission-pair F4, generic+HO combined F5 or J in the default; keep F5q deferred.

**Generic-only B (`LB+G`):** isolate the exact generic-only pair term without F3/F4/HO, with validated exact root graph and normalized `P_S(z_S) P_Q(x|z_S)` (or equivalent exact keyed representation). Avoid silently changing scene marginals when adding a repair-only conditional factor. Keep this as a *replication and mechanism-identification arm*, not an automatic default.

**Historical full keyed B:** retrain on the **same new data**, with same evaluation pipeline, explicitly as a **comparator**, not because the old factors were resurrected. Pairless D / B names must not be confused. Also include new LB-F2, lean C (GRU), A, optionally SF; equal data, common seeds and declared capacity controls where interpretation depends on parameter count. Retain frozen P13 K-B as a historical comparator.

### 5.2 B must handle complete longer repair sequences and multiple destinations

- Generate from the shared *scene-only* multi-slot domain (section 3), including empty and 1–4 relocations, changed intermediate occupancy, possible object repeats and alternative last robot q (physical witness search). B's input must encode **object identity/geometry, destination slot, actual prefix scene and action order**; check that same endpoints with reversed order can score differently and that changing destination while holding object fixed changes the query.
- Physically supervise each ordered sequence with the **existential full-sequence verifier**, not the old greedy mode; no labels from endpoint-only checks masquerading as physically executed repair success. Keep original P13 labels as a separately tagged historical protocol; they are not interchangeable if query realization semantics changed.
- Explicit candidate budgets: the full combinatorial domain is huge; use a deterministic proposal/enumeration scheme unrelated to teacher outcomes, count omissions and compute **proposal recall** of certified solutions on small exhaustive scenes. If B never sees certain 3/4-move repairs at training, report that as a limitation; do not claim complete 4-move capability merely because the GRU/prefix code accepts four tokens.
- Preserve a strict TOP1 proposal protocol and an optional TOP-k verify-then-next protocol as different conditions. Track whether a no-op was chosen without physical verification; a 'safe verification-first gate' must separately count the physical cost of verifying the original target and be given to every baseline.

### 5.3 Labelling and data collection: finish rather than silently downgrade

- P16 had 37 P16-train and 16 P16-val roots with **lattice-only** labels; on existing known splits, collect their full ordered-repair labels where physically adjudicable, recording query-protocol version, chosen destination catalogue and exact verifier version. Use these to improve training/diagnostics as *development* evidence only, not fresh blind confirmation.
- Increase deliberately **decided original-feasible** and **decided original-infeasible** train/calibration examples from independent geometry fingerprints and diverse families; preserve a truly natural/unfiltered stream without artificially balancing its evaluation prevalence. For training, sampling/weighting may balance classes, with calibrated deployment-prior accounting.
- Add 3–4-move order/destination examples, positive and negative when soundly decided; do not disproportionately train one-/two-move tasks. Avoid using fragile planning failures as negative labels. Unknown query statuses may be marginalised/ignored, but count missingness by mechanism and candidate length.
- Train enough epochs/updates for convergence, with validation early stopping, learning curves and gradient checks. P16 400-step checkpoints often peaked at the final step. Use independent seeds (minimum three, preferably five when variance warrants). Record learning rates/schedules, root-level effective sample counts, per-family feasible prevalence, loss by supervised endpoint.
- A full-B retrain **must use matched new data, common candidate catalogue, optimizer/checkpoint protocol, calibrated policy and execution verifier**. This isolates architecture/data better than comparing new lean B only to frozen P13 B.

### 5.4 B factor attribution — required exact comparisons

Test these distinct questions, not one ambiguous "coupling helps" statistic:

1. **Architecture vs data:** full keyed B retrained on the new data vs lean B retrained on the same data; frozen full K-B is historical descriptive only.
2. **Training benefit of generic factor:** independent matched LB and LB+G retraining on identical roots/labels and comparable optimization; each checkpoint family has a fresh held-out cohort.
3. **Inference-only dependence:** for each trained LB+G checkpoint, compute exact marginals with generic term normally active, then with that term set to zero at inference with *weights frozen*; distinguish prediction effects on **repair marginals** from the root original-feasibility marginal which, under root-consistent normalized conditional factors, should be invariant for fixed weights if F3 absent.
4. **Common-policy control:** frozen per-model scores with common `t0,t`, swapped `t0/t` policies, and equal admission/coverage curves; do not tune thresholds on test. Report ROC/PR, Brier, ECE/reliability, NLL, within-root candidate ranking, and no-op/repair outcomes separately.
5. **Capacity control:** if LB+G has ~49k more parameters, include a parameter-matched widened noncoupled LB variant and demonstrate a meaningful exact-complexity/matched training comparison. It is not sufficient to claim a pairwise *mechanism* from a general increase in parameters.
6. **Factor ontology:** prove keyed invariance when duplicate physical query appears as separate proposal/omission; correct shared root-scene marginals and equality constraints. Compare with unkeyed only as the archived invalid-invariance control.
7. **Order effect:** evaluate certified reversed-order physical pairs and ≥3-move access chains (same endpoints where feasible). Compare LB-F2 and LC; no universal GRU vs prefix claim unless supported.

### 5.5 B deployable no-op and repair policy

- The policy's goal is not merely high no-op recall. It must also avoid false-empty calls on infeasible originals **and retain high repair success**.
- Report separate `no_op_correct / feasible`, `unnecessary_moves / feasible`, `false_empty / infeasible`, `repair_verified / infeasible`, `abstentions`, `UNKNOWN/decided`, physical query/trajectory calls and computation time. Match candidate sets and verification budgets.
- Independently compare: ALWAYS_EMPTY, learned LB, LB+G, LC, A, full retrained B, frozen B, geometry-static selector, random, **verify-original-first + common non-learned repair search**. For the verification-first method, count its initial physical verification queries and online planning cost; give the learned method access to the same budget. This strong baseline must not silently be given a physical oracle for free.
- Optimize threshold on independent calibration split only; quantify policy sensitivity to feasible-scene prevalence. Use stratified/weighted measures for per-class performance and report the naturally occurring mixture without replacing it by a balanced metric. One coarse calibration grid and 30 originals is not sufficient for a broad generalization claim.
- Include a *false-action safety check*: if the original target is already VERIFIED, physically executing a needless repair is penalized in the strict metric (as in P16). However distinguish a correct safe physical verification from a learned no-op decision.

**Gate B-CORRECT:** exact math/keying/masking, gradients, 1–4 actions, multi-slot/repeat, witnessed-label protocol and existential verifier all pass. **Gate B-EVIDENCE:** all predeclared cohorts executed and analyses complete; if LB+G loses, record negative without blocking correctness.

---

## 6. P17-D — complete blocker learning, recursive tests and joint search

### 6.1 Keep exact learning scope and label semantics

- Model Dp: `p_f=σ(u)`, conditional pairless blocker union probabilities `P(b|y0=0)=∏ Bernoulli(σ(a_i))`; feasibility BCE plus masked blocker NLL, root/class split, trainable visual projection but frozen DINOv2. No learned ordering, destination, trajectory, search heuristic cost or arbitrary third policy head. Retain frozen full D and frozen Dp for comparison; do not reinstate D pair term as default.
- The original union label is defined **only relative to an intervention lattice** and a declared candidate pool/destination protocol; it is not global necessity or a set of actions that must all be done. Preserve fixed-parking labels as `PARKING_LATTICE_V1` and, if expanding intervention semantics, create **separately named new multi-destination labels**, never silently relabel old records.
- If using multiple destinations in offline labels, define a mathematically unambiguous quantity, e.g. a subset is existentially sufficient if an admissible static-valid assignment of that subset to declared buffer poses makes the *original target* physically verified feasible in the resulting edited scene. Negative only when every declared admissible assignment is adjudicated by a sound scoped negative; otherwise UNKNOWN. This is not proof those relocations themselves are executable. Record all admissible assignments and scope.
- A no-clearing-set or incomplete lattice **never becomes an all-zero blocker union**. If true membership is not identifiable within the finite tested intervention protocol, omit blocker loss but retain feasible-original supervision when decided.
- Evaluate conditional blocker F1, exact union set, individual-object precision/recall, feasible-original gate, necessary-set semantics, alternative minimal sets and incomplete-label rates. Report denominators and mechanism strata. Do not inflate accuracy through repeated identical masks or trivial all-positive masks.

### 6.2 Arbitrary-target and recursive blocker identification

- For `(state S_k, current q, temporary target object o, intended destination d)`, rebuild object roles, goal, numeric context and DINOv2 features; ensure D's target query refers to the same *pick/place goal* the physical checker tests.
- **Critical P16 defect:** `p16_d.Guide` loads the **same** `runs/p15/retarget/RECALIBRATION.json` coefficients for frozen paired D, frozen pairless D and newly trained Dp16. Fit/save **separate calibration parameters per checkpoint family/ensemble**, on root-disjoint development/calibration physical probes. Apply only each model's own calibration. Prefer a hierarchical/stratified reliability analysis if data permit, with honest uncertainty.
- Collect enough **decided temporary-target blocker lattices**, including nontrivial infeasible temporary targets, to evaluate blocker marginals; P16 had only 2 defined masks. Modify physical construction/robot/grasp difficulty based on geometry-first mechanisms, *not model predictions*. Include intermediate states after certified relocations, not just original snapshots.
- Test recursion at three scopes: (a) raw/recalibrated temporary-target feasibility; (b) blocker identity for a temporary target; (c) end-to-end search with each of (a) and (a+b). **Do not enable recursive blocker marginals as production guidance until (b) is independently validated.** Keep an experimental arm to measure whether (b) helps or harms.
- In all search uses, D only **reorders**, never hard-prunes based on uncertain predictions. Alternative sufficient clearing sets remain alternatives; D cannot force moving the entire union.

### 6.3 Complete the D rearrangement planner

- Use the corrected finite search of section 2, dynamic multiple slots of section 3, physically verified witnesses and independent replay. Include depth 0–4, at least one forced repeat-move case, and verify a widened (rather than nearest-only) object/slot domain on tiny scenes against exhaustive enumeration.
- Jointly optimize **which objects**, **how many**, **in what order**, **to which dynamically available slots**, and **which motion-mode/robot-end-configuration alternatives** with lexicographic `(moves, measured joint travel)`; no subjective risk cost and no learned placement/order policy.
- Maintain finite-state admissibility and status completeness; a plan can be found without optimality proof. Track virtual CPU, actual CPU, planner calls, search nodes, witness-hit rate, rare-mode rescues, unknown edges, candidate omission and per-root minimum proof flags.
- Geometry baseline: same action graph, same exact checker, same budgets. Uniform and frozen D/Dp comparators; full/nondeployable blocker-union oracle **mandatory**, and optional stronger finite-graph oracle lower bound on small scenes. Avoid attributing speed to learned D if provider budgets differ.
- **Use meaningful anytime budgets**: 10/25/50/100/200/500 nodes plus a per-query motion-call cap; compare success-versus-effort curves. Because P15/P16 guides often expand the same first moves, report actual guide disagreement rate and rank correlation, including D vs geometry score overlap. A high blocker F1 cannot imply planning gain if the guide orders candidates nearly identically.

### 6.4 Mandatory full P16 continuation and truly new test

1. **Retrospective completion:** complete **all 48 frozen P16 D test roots**, especially **the remaining 20 DENSE roots** (only 4/24 were previously covered), with the newly corrected implementation and all guides including oracle; version label `P17_REANALYSIS_OF_P16_ROOTS` because code and design have been revised after their outcomes became known. Do not call this prospective replication.
2. **Fully rerun** the initial 21 roots with the corrected state key / scorer / calibrations as applicable so every arm uses one comparable corrected algorithm. Preserve the original P16 records untouched. If additional oracle labels require post-unseal use, record that as retrospective baseline evidence.
3. Run a **fresh independently frozen** prospective DENSE-heavy and mechanism-mixed cohort after development is frozen, with enough physically difficult/branching roots and feasible-original controls. Physics-only difficulty strata can be defined on DEV and predeclared; **do not select test roots by whether D or geometry wins**. If no oracle advantage in fresh tests, report that as informative negative evidence, not permission to discard the oracle.
4. Endpoints: `D_vs_geometry` paired success and bounded effort, min-move proof coverage, travel, search expansion, relevant unknowns, D-vs-geometry first-move disagreements, oracle headroom, recursive ablations. All models' inference CPU belongs in comparisons.

**Gate D-CORRECT:** finite-state/search/UNKNOWN proof tests, multiple motions, recursive interface/calibration, physical mechanisms and replay pass. **Gate D-EVIDENCE:** complete 48-root retrospective roster including oracle and new prospective D cohort with documented root-level statistical uncertainty. Neither requires D to outperform geometry.

---

## 7. Experiment design, statistical integrity and what counts as a valid proof

### 7.1 Split ontology

- Historic P10–P16 data and P16 test scenes, all scenes used to debug P17, and pilot runs are **development/retrospective** evidence only after design inspection.
- Fresh P17 prospective test must be root-disjoint, scene-geometry-fingerprint-disjoint and trajectory-provenance-disjoint from train/val/calib and lookup index. Include near-duplicate adjacency and transformed-scene checks where possible.
- Models/weights, all thresholds, motion-profile/version, certifier, source hash, candidate generator, role retargeting, benchmark roster, primary hypotheses, comparisons, outcome definitions and exact inference modes frozen **before any test label/physical outcome is inspected**. Handle required amendments like P15/P16: void affected outputs, push amendment before rerun, distinguish confirmatory from exploratory if unblinding occurred.
- Positive teacher outcomes require full physical witness and replay; scoped negative certificates require producer/checker. UNKNOWN and NOT_RUN are explicit, never 0. Label all outcomes with versioned physical query protocol, including existential-vs-greedy B labels.
- The new prospective test is **not** an endless search for a favourable split; predefine eligible scenes independent of B/D outputs and report all exclusions and unknowns. Keep a natural/unfiltered stream as well as mechanism-enriched benchmark.

### 7.2 Two independent scientific hypotheses, plus method-correctness gates

**B primary research question:** Does LB+G (generic-only coupling) improve correct no-op/verified repair decisions under a single fixed prospective protocol compared with lean LB and a retrained full-B control, and does any improvement persist when threshold/capacity/training-inference effects are controlled? Always report ALWAYS_EMPTY and verify-first geometry. The *method* may pass with no improvement.

**D primary research question:** On branch-heavy physically verified 2D rearrangements, does D's learned blocker guidance improve bounded-budget task success or reduce physical motion-planning effort compared with geometry/uniform under identical search and motion provider? Is there even headroom for an original-blocker-union oracle? The *method* may pass with no improvement.

**Mechanism correctness** is independently evaluated for order reversal, alternative clearing sets, coupling, scene/repair distinction, no-op, chain, intermediate swept collision, slot conflict and necessary repeated moves. A demonstration of a mechanism is not by itself evidence of broad generalization.

### 7.3 Statistics

- Unit of independence = initial root/scene fingerprint, not individual trajectories, candidates, repairs or three training seeds. Cluster bootstrap at root; if family-wise correlations occur, report family-stratified results, not only naive root intervals.
- Predesign primary/secondary contrast family, desired minimally important effect and realistic power based on pilot discordance (or credible upper bounds). Use paired tests (exact sign/McNemar for binary), confidence intervals appropriate to zero discordance (not spuriously `[0,0]` equivalence), multiple-test adjustment for secondary families. For efficiency include paired CPU/planner-call/node distributions and uncertainty, not only average speed.
- Always compare **candidate admission**, **conditional selection quality** and **physical execution** separately. With trainable coupling, evaluate joint log-loss, no-op Brier, κ including constant-zero baseline and scoped physical outcomes; do not claim causal identification from an energy interaction alone.
- For B include original feasible/infeasible count, no-op recall, false no-op, unnecessary moves, abstentions, repair success on infeasible, robust mixture-weighted strict success and original-prevalence curves. For D include F1/mask/provenance completeness, task success, moves/travel, actual and virtual CPU, physical checks, oracle advantage and guide disagreements.
- Reports must distinguish architecture-specific effect, calibration/policy effect, data-distribution effect, and physical-verification effect. An LB+G trained-model improvement is not automatically direct test-time generic coupling action on `P(z0)`.

---

## 8. Execution discipline: finish the roster, no inherited aggregate budget cutoffs

**The user's latest instruction explicitly permits spending beyond historical CPU caps to finish the 2D work.** Do not request authorization just to pass a previously arbitrary **CPU-seconds total**; those are no longer P17 hard ceilings. This does **not** license uncontrolled processes, hardware purchases, indefinite loops or changing physically meaningful per-query evaluation limits.

- Perform a documented small pilot to estimate CPU per *family*, not just easy feasible originals; forecast complete training/teacher/retrospective/prospective/ablation spend with margins. Report actual costs as they accrue, no need to stop after 21/48 because an old total cap ran out.
- Work in **small resumable checkpoints**: per root, per model/seed, per trial; flush atomically and hash; maintain ledger for started/completed/UNKNOWN/cancelled/killed. A root in progress when a process ends must be resumable or explicitly reported.
- Limit concurrency based on physical cores/memory and provider determinism; avoid oversubscription and self-`pkill`. Explicit process IDs and ownership tags, no pattern-killing broad system shells. Do not allow simultaneous jobs to circumvent per-query limits.
- **Keep deterministic per-query node/collision/lookup/goal limits fixed for all methods**, and evaluate a larger common budget as a separate declared condition if informative. For a query that remains UNKNOWN at the chosen limit, increasing its limit requires a **new protocol version** and a corresponding fairness rerun for all arms.
- Do not silently replace full sequence labels by cheaper lattice-only labels, skip difficult DENSE scenes, or drop oracle to save CPU. If hardware/physical process genuinely cannot finish, report exact blocker; do not claim completion.
- Preserve rollback to last committed gate and all cancellation logs. Stage commits with expected hashes; push and verify remote SHA after each major gate. Do not promise unattended/asynchronous future completion beyond the current execution environment.

---

## 9. Code structure: minimal, testable modules, no giant new orchestration file

Reuse `p16_*` and `p15_*` interfaces selectively; **do not edit historical data**. Version new source only where necessary. Preferred P17 additions, adapting to avoid duplication:

```
p17_search.py        # dominance/UNKNOWN/finite optimality corrections (can be thin wrapper)
p17_verify.py        # fixed-sequence existential physical realization
p17_domain.py        # scene-only multi-slot, variable-length candidate generation
p17_b.py             # B longer-sequence records, lean/generic/full controls, training
p17_d.py             # D target calibration, label protocols and search guides
p17_eval.py          # lightweight CLI/stage orchestration, NOT 1000-line monolith
tests/test_p17.py    # adversarial math + physics + all key gates
runs/p17/{audit,shared,mechanisms,b,d,tests}/...
responses-phases/0090_...md ...
visualizations/p17/{mechanisms,b,d}/...
```

Aim for <300–350 meaningful lines per new Python module. Split `p17_eval.py` by true responsibility rather than introducing one >1000-line file; do not add dozens of tiny utilities. Prefer central shared `Status`, `PhysicalQuery`, `SearchState`, `Witness` contracts with explicit field validators and serialization.

**Tests / stress cases (must-have):**

- Last-mover dominance counterexample; action-count budget and attachment distinct; correct minimum-move/travel claims against an exhaustive tiny-state oracle; feasibility UNKNOWN poisoning prevention; alternate q-ending modes retained; no accidental unsafe pruning; cycles and repeated relocation.
- Exact physical sequence witness existence vs greedy failure; physical unknown alternatives and certificate scope; start-transit alternate RRT; mid-sweep collision; carried-object collision; trajectory continuity and deterministic replay.
- Scene-only API with teacher/candidate metadata deleted; multi-slot availability and freed-source reuse; unambiguous goal/original no-op; fixed obstacle exclusion; catalogue provenance and exhaustion/omission count.
- B factorized exact normalization, keyed query/omission equality, duplicate catalogue invariance, F2 order effect, generic-only joint normalized probability, frozen-weight coupling-off control, parameter-matched baseline, original `P(z0)` invariance when only cross-block couplings change, masked labels, NLL gradients finite, long-horizon 3/4 move conditioning.
- D union≠necessary, no-clearing not zero mask, multi-destination vs single-parking label version, arbitrary target visual and numeric rebinding, model-specific calibration, recursive blocker physical label, original-feasible correctness, conditional/unconditional marginals, pairless normalization, oracle guide scope.
- Leakage by root, fingerprint, source trajectory and parent scene; hash-commit before unseal; seed-independent trajectory replay; no test thresholds used in calibration; cancelled-job accounting and checkpoint resumption.

### Required visual outputs

Provide direct 2D physical outputs after the main gates: one multi-panel scene of each mechanism initial/intermediate/final occupancy, link+carried-object true swept trajectories, successful/failed alternative destinations, a repeated-object example with every actual waypoint, B score/calibration/no-op and rank breakdown, D union/necessary/recursive target and guide trace, plotted search cost curves. **GIFs/videos use only verified trajectory records**; explanatory nonphysical arrows must be labelled as schematic.

---

## 10. Mandatory stages and final deliverables

Each stage must have a gate file, report, code/data hashes, regression subset and visual evidence when applicable. Suggested stage sequence (report IDs allocated after 0089; adapt names but keep one-to-one mapping):

| Stage | Report | Deliverable / stop gate |
|---|---|---|
| P17-0 Audit | `0090_P17_0_...md` | Immutable history, source/decision map, starting SHA |
| P17-1 Physical correctness | `0091_P17_1_...md` | Fixed D dominance, existential B verifier, UNKNOWN/optimality, replay |
| P17-2 Shared domain | `0092_P17_2_...md` | Multi-slot scene-only B/D candidate API, long sequences |
| P17-3 Mechanics | `0093_P17_3_...md` | All required 2D physically realized mechanisms + counterfactuals |
| P17-B1 Training | `0094_P17_B1_...md` | Full B labels, convergence, matched retraining/ablations, controls |
| P17-D1 Diagnosis | `0095_P17_D1_...md` | Multi-target and per-model calibrated feasibility / scoped blocker masks |
| P17-4 Frozen test | `0096_P17_4_...md` | New frozen splits, prospective label custody and entire roster completed |
| P17-B2 Evaluation | `0097_P17_B2_...md` | No-op, strict and verification-first B evaluation, factor attribution |
| P17-D2 Evaluation | `0098_P17_D2_...md` | Completed P16 48/48 retrospective including oracle; new prospective D + proof coverage |
| P17-5 Final closure | `0099_P17_5_...md` | Both methodologies' correctness/claim verdicts and remaining 2D limitations |

Also supply:

- `responses-phases/P17_COMPLETE_2D_B_AND_D_SCIENTIFIC_DECISION.md` with clear separation of **implemented**, **verified**, **empirically supported**, **negative**, and **unresolved**.
- `runs/p17/P17_FINAL_MANIFEST.json` with stage gates, source/hash data, previous-history check, model checkpoints, splits, full root counts per family, missing/UNKNOWN counts, proofs, provenance, physical planner profiles, CPU/wall/memory usage, records of cancellations, and paired statistical contrasts.
- `runs/p17/P17_IMPLEMENTATION_MAP.md` explaining exactly which functions are production B, experimental LB+G, historical full B, pairless D, recursive D, and shared motion/search; explicit formulas and which weights get gradients.
- Small comprehensible visualizations and deterministic certified GIFs from actual replayed motions.
- All historical tests plus six historical replays and all new tests passing. If historical tests need compatibility shims, document rather than mutate archived results.
- Incremental commits and final verified local/remote SHA. Leave unrelated working-tree changes alone.

### Final success/failure determination

**METHOD_B_2D_COMPLETE** only if: math/keyed semantics and training labels correct; zero-move/1–4 ordered actions and multiple destinations implemented; existential verifier used; full training and held-out execution conducted; calibrated false-empty/no-op and repair outcomes and baselines all reported; no unclosed correctness defect.

**METHOD_D_2D_COMPLETE** only if: initial/temporary target interfaces correct with per-model calibration; blocker label scope and uncertainty correct; scene-only dynamic destination/order/mode/repeat search mathematically correct; all mechanism gates physically realized, oracle and DENSE cohort completed; independent replay and finite-proof semantics valid; no unclosed correctness defect.

**P17_2D_COMPLETE** only when **both method gates pass** and all mandatory test rosters are executed. It may *still* conclude no scientific advantage for one/both methods. A negative result must not force a method to be removed or resurrect a rejected factor.

If methods are technically correct but still cannot attain a result for a declared cohort because a physical primitive is genuinely unavailable, mark **PARTIAL/BLOCKED with precise root IDs, reasons and noninvented evidence**. Do not pretend the next step is 3D. No 3D work under this contract.

### Final Claude response format

Provide concise but numerical: source and SHA; audited history; precisely what changed in physics / B / D; all 2D mechanism coverage; B dataset/seed/training NLL and no-op/repair results vs LB+G/full retrain/ALWAYS_EMPTY/verified geometry; coupling attribution incl inference-only toggle; D temporary-target feasibility/mask sample sizes, each guide's full P16 and fresh prospective results incl oracle, speed/optimality/UNKNOWN; CPU/wall, all report/figure locations, test/replay totals, final commit. Explicitly state which 2D claims remain negative or underpowered and what—not another unspecified phase—prevents technical closure.

**Direct instruction:** finish both complete 2D methodologies and experiments first. Do not start 3D. Do not stop a primary frozen roster merely because an outdated total CPU cap would have been exceeded.
