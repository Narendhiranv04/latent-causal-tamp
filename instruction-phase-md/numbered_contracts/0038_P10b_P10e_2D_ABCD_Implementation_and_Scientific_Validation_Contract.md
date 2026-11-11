# 0038 — 2D Research Completion: A/B/C Scientific Validation + Minimal D Blocker Model

**Execution contract v1.0 | Applies after P10a | Research-first, 2D-only**  
**Repository:** `Narendhiranv04/latent-causal-tamp`. Verified P10a result commit `dd12f0ce354c16e2525f88805cf2a8b5e811aadf`, predecessor prediction-freeze `3afa81c2f8804fc1a8d11e08e2b3f010286fc784`. Check live `HEAD`/`origin/main` and ancestry before touching anything. **Never reset, overwrite, or stage unrelated/user files.**  
**Instruction location:** `instruction-phase-md/0038_P10b_P10e_2D_ABCD_Implementation_and_Scientific_Validation_Contract.md`.  
**Research priority:** Finish the highest-quality, honest, reproducible **2D** scientific evaluation feasible within bounded resources; compare **A/B/C** on physical long-horizon repairs; add **D only for initial target-feasibility and causal-blocker detection**. Neither good results nor B/C superiority are predetermined. Gate PASS and a publishable scientific conclusion are different things.

## 0. Read and preserve the existing science

Read, in full, Methodology v1.8, Implementation Guide v2.0, P8c/P8d, P9 reports 0031–0036, `P9_2D_FREEZE_DECISION.md`, `runs/p9/2d_freeze_manifest.json`, `P10_TARGETED_CAUSAL_EVIDENCE_PILOT_PROPOSAL.md`, `responses-phases/0037_P10_0_validation_readiness_and_training_protocol.md`, `responses-phases/0038_P10a_constructibility_and_label_provenance.md`, `responses-phases/P10a_NEXT_DECISION.md`, both P10 gates and their source-linked artifacts. Inspect source and manifests, not prose alone: `abc7_models.py`, `abc7_train.py`, `abc8.py`, `unique_factor*.py`, `joint_likelihood.py`, `p10_{protocol,prereg,scenes,collect,eval,viz}.py`, `evaluate.py`, `ordered.py`, `p8_select.py`, `config_v2_r4.toml`, teacher/proposal/checker modules and tests.

**Baseline facts to retain:** P10-0 trained keyed B, keyed C, A and SF for 400 updates × 3 seeds on legacy data; 392/392 tests and 6/6 replays passed. P10a independently obtained proof-grounded H1 complementarity, H2 redundancy/neutrality, H3 same-endpoint reverse-order differences, H4 omission decisions and H5 feasible-original/harmful-edit examples. H7 edit-vs-executable mismatch and H8 obstructed constructor-disjoint example **were NOT realized**. P10a frozen A/B/C/SF models failed H1/H3 on two adaptive roots per mechanism, while B/C performed worse than factorized models on new geometry. **These pilot roots are disclosed development evidence, never a fresh blind test or independent proof of model superiority.**

### 0.1 Immutable approach definitions

- **A / LOCAL-SEQUENCE:** shared scene/object encoder, ordered repair tokens and GRU, independent task/scene scores, documented factorized supervised training. It does **not** use B/C's joint repair-outcome likelihood.
- **B / JOINT-CAUSAL-EBM:** frozen physically keyed `ABC9K_KEYED_V1` conditional Boltzmann outcome graph, prefix/predecessor representation of ordered repair.
- **C / HYBRID-JOINT:** **same** physically keyed graph and factors as B; substitutes the GRU order encoder for B's predecessor interaction, not an additional GRU on top.
- **SF:** factorized supervised control; retain as a serious baseline.
- **B/C F1–F5:** F1 static endpoint supervision, F2 ordered repair success, F3 scene edits and scene interactions, F4 full/omitted repair relations, F5 generic pairwise and higher-order scene–repair/omission interactions. F1 and learned travel J stay **outside** normalized joint outcome likelihood. Physical query identities are canonical; no duplicate factor on re-listing.
- **D / new:** one **small conditional Boltzmann blocker predictor** that predicts **whether the original target-retrieval task is feasible** and **which scene objects causally block it under a specified intervention protocol**. **Stop there.** D must NOT generate places, choose relocation order, recursively move blockers, evaluate obstacle destinations, execute repairs, or use the planner at inference. Do not fold D into A/B/C or modify their factor graph.

All learned predictors see only observations/features, target/goal/robot `q0` and explicitly proposed actions/edits as applicable. Allowed visual input: existing frozen mask-pooled DINOv2-small features plus object geometry; optional visual-zero ablation. Never leak outcomes, certificates, privileged collision/swept-volume labels, planned paths, or constructor acceptance flags into learner features.

## 1. End-state acceptance criteria (must test, not promise)

**Engineering completion:** deterministic reproducible data generation/training/inference/selection; unit and physical-fixture regression; 3-seed A/B/C/SF and D training; all declared computational limits respected; zero IK/planner/teacher calls for learned scoring; sound label provenance; visualizations for each studied mechanism, difficult 3–4-relocation scenes and every major failure; full reproducible code/checkpoint/manifest suite.

**Scientific completion:** independent-root, sealed-holdout comparisons of A/B/C/SF on (i) target and ordered-repair feasibility, (ii) H1–H5 physical interventions and omissions, (iii) multi-relocation repair feasibility/selection, (iv) length extrapolation, (v) strict TOP1 executed success versus G+M and geometry-only, (vi) factor-wise retrained ablations and statistical uncertainty. For D: independent-ground-truth **initial retrieval feasibility** and **object blocker attribution** versus simple non-Boltzmann and counterfactual baselines, with exact cardinality/false attribution analysis. Report *insufficiently identified/underpowered* endpoints plainly. A failed hypothesis is a legitimate final outcome.

**No false claims:** A sound negative requires an independent scope-correct certificate; timeouts only yield operational BUDGET or UNKNOWN. A successful `zS[I]` hypothetical edit is NOT proof that the actual corresponding relocation can be executed. A four-move successful witness is NOT proof that fewer moves are impossible. No fabricated trajectories, labels, unseen-success claims or hidden fallbacks.

## 2. Physical 2D scope and long-horizon tasks

Keep the existing fixed-base finite-width 3R arm, joint restrictions, complete collision bodies, 48-grasp family, 8×8 support grid (pitch 0.08 m), 0.024 m discs, 0.005 m clearance, robot start `q0`, one target and goal with SAFE_RETREAT. Preserve `config_v2_r4.toml`'s **current maximum 4 distinct relocations**. Do not quietly claim five- or six-move physical demonstrations on an unmodified four-move teacher or evaluator. A separately labelled **5+ stretch diagnostic** is permitted only if its exact physical validity, bounded complexity and configuration changes are first audited and preregistered; omit it rather than destabilize A/B/C.

Required root families and contrasts:

1. **H1 true complementarity** (κ = +1): both edits jointly enable retrieval; neither alone does. Complete proof-grounded 4-tuple `y0,yA,yB,yAB` with 0/1 scope-correct evidence.
2. **H2 redundancy and neutral controls**: κ = −1 and 0 under equally rigorous 4-tuples.
3. **H3 order sensitivity**: same initial scene, robot `q0`, movers, destinations and final arrangement; `(A,B)` VERIFIED while `(B,A)` CERTIFIED, or reverse. Include **three- and four-move permutations** with independently decided contrasting orders, not mere random permutations without counterfactual evidence.
4. **H4 necessity/redundancy**: completed full repair plus separately decided leave-one-out sequences from the **original state**, including nontrivial omitted early/middle/late actions. Avoid only trivially irrelevant far-object omissions.
5. **H5 originally feasible** retrieval and harmful/neutral edits (identifies `z0–zS`; checks unnecessary relocations and false-empty).
6. **H6 destinations/travel/static**: same object with multiple destination candidates; distinguish static validity, target reachability, physical carry success and observed travel J.
7. **H7** edit-only succeeds / executable relocation fails: **development first** and accept as a realized mechanism only if teacher actually establishes disagreement. Never invent a place-side certificate.
8. **H8** genuinely obstructed swept/carry/arm-body family independent of pose-screen-based acceptance. **Development first**; must show original task is genuinely infeasible and an actionable witness or sound mechanism-specific pair exists. Never call a feasible original an obstruction.
9. **H9** visual nuisance controls: fixed exact physical geometry/outcomes, changed appearance/masks-verified inputs; separate true generalization from color/template memorization.
10. **H10 long repairs:** physically witnessed **three- and four-distinct-object** relocation sequences, competing shorter and reversed sequences, genuinely changed intermediate accessibility, and misleading plausible relocation candidates. At least one family where order determines outcome; at least one where a superficially useful move makes later repair impossible. Record actual supported lengths rather than intent.

Keep each root an independent physical family/seed. All its order variants, omissions, edited scenes, color variants and reference scenes remain in one split. Constructor targeting and pilot mechanics are disclosed; blindness requires roots and labels not inspected for training/tuning. **Constructor-disjoint** and **unseen-length** are different axes: test each and their intersection when feasible. Do not confuse #objects in scene with minimum necessary #relocations.

**Minimum-length truth:** For each root, label `verified_witness_length = k` from the actual returned execution. Label `minimum_required = k` **only relative to a frozen, explicitly exhaustive finite repair catalogue** if *every* shorter candidate is decided infeasible with correctly scoped evidence; distinguish sound vs operational negatives. Otherwise `minimality = UNKNOWN` and report relative-to-catalogue best known witness. Never certify a global minimum from finite non-exhaustive testing.

## 3. D: smallest valid learned baseline (NO placement/recursion)

### 3.1 Output and meaning

At inference, input `(S_0, robot q0, target T, goal)` and a pool `O={o1,...,on}` of potentially movable objects. Return:
- `p_feasible = P(y0=1 | S0,T,q0,goal)` for **initial target retrieval plus SAFE_RETREAT**;
- `p_blocker[i]` for each observed candidate object; a ranked set with threshold fixed on validation;
- optionally a joint blocker-set MAP (small N) and calibrated uncertainty.

A **blocker** means membership in a *proven inclusion-minimal sufficient clearing set* under a **predeclared hypothetical object-pose edit map**. For a root choose deterministic, statically valid *parking poses* `h_i` solely to define counterfactual target-only scenes; do NOT learn, optimize, execute or rank these poses. Ask teacher whether the **target-only** task from unchanged `q0` is feasible in scene `S_I` with exactly the objects in subset `I` moved to their frozen `h_i`. This is scientific label generation only; it is not a physical relocation. Prefer 2–4 movable candidates so `2^n` small (4 → 16). For >4, define an explicitly bounded partial-label regime; do not pretend full enumeration.

For root with **original `y0=0`**, a subset `M` is an inclusion-minimal sufficient clearing set if `y_M=1` is VERIFIED and **every proper subset `J⊂M`** is **soundly decided 0** (CERTIFIED; operational evidence separately stratified). Multiple minimal sets may exist. Define `b_i=1` when `i` belongs to **at least one** proven inclusion-minimal sufficient clearing set **and completeness of the set family has been checked**. This is an *alternative-solution participation* label, **not** a claim that i is individually indispensable across all solutions. Separately report intersection of all minimal sets as `necessary_i` where complete. For `y0=1`, the labelled blocker set is empty. For `y0=0` and exhaustive soundly decided subsets with no successful clearing set, use `NO_CLEARING_SET_WITHIN_POOL` (blocker mask all zero **only within this scope**, not global intrinsic unreachability). If labels are incomplete, contradictory, depend on unsafe invalid parking edits, or the full minimal-set family is not established, mark the ambiguous blocker bits/entire mask **UNKNOWN** and train D's feasibility term only. Report mask-label yield; never treat unknown as absent or convert a planner budget timeout into an exact blocker label.

**Counterfactual comparability:** The parking map must be frozen without teacher outcomes, and each predicted scene edit must have a one-to-one identity with the labelled intervention. Do not assume removing an object from the world is equivalent to moving it to a grid pose. If a parked object creates a new obstruction, record it; do not silently assume monotonicity. Reject it for simple clearing-set attribution or retain as a separately labelled non-monotone analysis, not as a fake positive.

### 3.2 Minimal conditional Boltzmann model

Keep one shared object encoder already available (DINOv2 features + geometry), target token and robot/goal context; **one small feasibility head** and **one simple conditional Boltzmann blocker head**, no graph neural network, GRU, Slot Attention, value iteration, decoder, generated poses, hierarchical training or search network.

Let `u = f_theta(S0,T,q0,goal)` and per-object `a_i`, optional symmetric pair scores `w_ij` from compact MLPs over the shared features. Define:

`P_D(y0=1,b=0 | S)=sigmoid(u)`;

`P_D(y0=0,b | S)=[1-sigmoid(u)] * exp( sum_i a_i b_i + sum_{i<j} w_ij b_i b_j ) / Z_B(S)`;

`Z_B(S)=sum_{b in {0,1}^n} exp( sum_i a_i b_i + sum_{i<j} w_ij b_i b_j )`.

This is one conditional model (not separate stages of reasoning); blocker variables are meaningful conditional on infeasibility and zero when y0=1. Empty blocker set is allowed for inaccessible scenes with no clearing set in the candidate pool. For n≤4 or n≤6, perform stable exact logsumexp enumeration; fail closed on cap and report coverage (never silently subsample combinations). At runtime return `sigmoid(u)` and blocker marginals `P_D(b_i=1 | y0=0,S)`, plus optional unconditional `(1-p_feasible)*marginal`. State which is thresholded. Permute object order and require identical probabilities after inverse permutation; mask pads and exclude fixed non-movable bodies as blocker candidates (they remain geometry context).

Loss on labelled roots: `L_D = BCE(sigmoid(u), y0) + lambda_B * 1_{y0=0,blocker_mask_fully_decided} * [-log P_D(b_GT | y0=0,S)]`. Choose `lambda_B`, optimizer, temperature/threshold and early stopping **using train/validation only**, with a small predeclared grid; report sensitivity. Incomplete blocker masks are ignored for the blocker loss rather than assigned zeros; allow exact marginal likelihood over admissible partial masks only if minimal/simple and validated, not mandatory. With confirmed alternative minimal sets, train the **defined union participation mask** and separately report the alternative sets for physical interpretation. No extra auxiliary tasks.

**Mandatory controls:** (i) same backbone with blocker pair terms `w_ij=0` retrained (independent Bernoulli blocker baseline); (ii) simple geometry-only blocker proximity/occlusion ranking with fixed nonlearned rules; (iii) if feasible, A/B/C/SF counterfactual scene-score-derived blocker attribution using **the exact same parking poses and restricted subset catalogue**; do not claim they natively output blocker labels. If the joint models cannot exactly represent a required subset catalogue within `MAX_SCOPE=16`, report **UNSUPPORTED/ABSTAIN** and coverage. Do not secretly split the joint model into smaller inconsistent graphs or substitute unary probabilities while calling them full joint B/C attribution. A precisely labelled auxiliary single-edit score is permitted only as a separate, weaker attribution baseline. **No A/B/C factor-graph redesign to accommodate D's evaluation.**

### 3.3 Fair D evaluation

Primary: initial target feasibility AUROC/AUPRC, balanced accuracy, Brier, NLL, ECE, false feasible/false infeasible; **per-object blocker precision/recall/F1**, macro by root, exact blocker-set accuracy, Jaccard, top-k recall, blocker cardinality error and false attribution for already-feasible roots. Report mask GT completeness/yield, intrinsic-unreachable-in-pool cases and alternative minimal-set ambiguity. Report confidence intervals clustered by root and separate 1-, 2-, 3-, 4-blocker strata; keep D's **n ≤ small enumerated cap** visible. For difficult multi-blocker scenes include certificates/witnesses for all decisive subsets. Compare D's feasibility output against A/B/C/SF original-task `z0` probabilities on exactly matched roots, calibrated on same validation partition.

**Scope fence for D:** no `MOVE(A,d)` inference, no placement direction, no destination enumeration algorithm beyond the **fixed training-label parking map**, no recursive inference, no obstacle-execution order, no target-after-sequential-relocations test, **no D execution score**. Add `D_DESTINATION_AND_RECURSION_DEFERRED.md` containing only the open research question and a brief interface contract, NOT implementation.

## 4. Experimental design, comparisons and statistical integrity

### 4.1 Data partitions and material requirements

Preregister root IDs, family, constructor version/seed, q0, goals, object counts, mover sets, candidate destinations, appearance group, query catalogue, treatment order, safe parking edits for D, label source and physical teacher policy **before collecting teacher labels**. Do not put past adaptive P10a roots in sealed validation/test; they may be **training/dev only** and must remain labelled disclosed. P8c disclosed test remains descriptive. Split by independent lineage and near-duplicate geometric fingerprint; certify no train/test shape/seed lineage collision.

**Target** (adjust downward with transparent UNDERPOWERED result if physical cases/budget fail): about **180 new independent roots** in stages; illustrative `80 train / 35 validation / 65 sealed blind`, with H1/H3/H4 and 3-/4-move cases deliberately covered. Holdout should aim **≥10–15 independent fully decided roots** per central mechanism/length category, not simply that many query lines. Declare minimum decided-root counts and effect-size targets using P10a pilot variance, and note where real power requires 15–20+ blind independent roots *per* mechanism. Exact count can be changed **only prior to labels/split freezing**; don't adapt blind holdout sizes based on results. For the first 40 new roots perform a constructibility/label-yield gate; only then expand. No deceptive claim that 180 roots automatically establishes generalization.

Two separately identified regimes:
- **Full-data regime:** A/B/C/SF trained on supported 1–4-move evidence, evaluated on independently held-out 3-/4-move and other mechanisms.
- **Length extrapolation regime:** train copies of A/B/C/SF using **only roots and outcomes requiring/proposing up to 2 moves**, then test fixed held-out 3- and 4-move tasks, with the 4-move teacher cap disclosed. The held-out root family and actual minimum-length provenance remain separate. Label `>2` generalization as success only if physical witness/decision supports it. D analog: training labels with ≤2 target blockers, evaluate on complete 3-/4-blocker masks; distinguish object count from true minimal clearing-set size.

Use **same observational inputs** and **identical physical query catalogue** for A/B/C/SF. A/SF have factorized supervision and B/C have exact root NLL, so compare common out-of-sample predicted physical outcomes and execution decisions; report own-training loss separately. Keep B/C model architectures fixed (keyed graph, F1–F5). D has an additional supervised blocker head and its own target-only outcome; do not imply it solves sequence ordering or full TAMP. Baselines include SF, simple supervised factorized scene model, random/uniform, analytic geometry-only, visual-zero, and G+M in execution (planner-assisted).

### 4.2 Confirmatory endpoints and ablations

Preregister one primary comparison per question and control multiplicity (e.g. Holm across 3 primary mechanisms plus TOP1). Track a clear model-family selection rule: first **held-out strict TOP1 physical task success** and paired confidence intervals vs SF/geometry/G+M, then H1 complementarity four-tuple error, H3 proof-grounded ordering, H4 hard omission discrimination, and efficiency/coverage. **Do not choose a winner from P8c in-distribution NLL.** Report B/C vs A/SF regardless of outcome and C-vs-B (is a GRU order encoder useful?) as a distinct comparison. D's blocker attribution is separate primary, compared to independent-Bernoulli D and transparent geometry heuristics; D target feasibility compared to A/B/C on matching initial-task labels.

**Retrained factor ablations** with same data, seeds, update/optimizer tuning budget as parents, not merely zeroing already-trained weights:
- F2 order information (B predecessor, C GRU) vs deliberately order-invariant representation;
- F3 structured scene pair/scene relation; meaningful only where feasible-original edits are present;
- F4 repair–omission pair;
- F5 generic scene–repair/scene–scene couplings and F5 higher-order terms separately;
- F1 learned static predictor vs analytic static screen (not conflated with physical success);
- witnessed-J travel head in repair selection (same candidate catalogue);
- visual-zero versus DINOv2 with matched architecture and held-out appearance;
- B keyed versus historical unique as **secondary ontology/control**, not another redesign.

Do not assert a removed factor mathematically forbids κ, omission dependence or order discrimination. Shared encoders and other factors can sometimes express the same relation. Evaluate **incremental generalization, calibration, task completion and sample efficiency**, plus number of independent roots supporting a conclusion. Include negative/failed ablations and calibration stability. If total ablations exceed caps, prioritize F2 order, F4 omission, F5 generic + HO, and simple D pair-vs-unary; mark lower-priority others NOT_RUN instead of inflating budgets.

**Must show actual complexity:** number of objects, *verified* relocation length, candidate physical outcome variables, scene intervention bits, factor counts, `MAX_SCOPE` peaks, inference wall time, memory and failure/abstention rate. A/B/C exact graph over many candidate repairs may exceed fixed scope 16; fail closed and report coverage. Never discard hard roots without showing denominator. If longer tasks need different candidate partition or expanded cap, version it as an explicit engineering change with regression and do not compare it silently to old results.

**Uncertainty:** paired independent-root bootstrap CIs (not query/bootstrap-as-independent), seeds shown individually, predicted-vs-decided label provenance and operational separately, calibration on validation only, no hidden post-hoc threshold recalibration. Predeclare non-inferiority margins/equivalence testing if wanted; CI crossing zero is **not** proof of equivalence. Avoid overinterpreting p-values on constructed correlated templates; show constructor-family sensitivity and failure maps.

### 4.3 Actual physical execution of A/B/C (D explicitly excluded)

**Primary `TOP1_COMMIT`:** score **all** allowed candidate sequences with A/B/C/SF neural predictor, and deterministic static checks where explicitly permitted; select **one** with the frozen calibrated admission/fewest-moves/J/displacement/energy tie-break. **No planner/IK/teacher call on any other hypothetical candidate.** Attempt planning/execution of that one committed repair and target+SAFE_RETREAT; if it fails, it fails—no fallback. Make failed and abstained outcomes count.

**Secondary `TOP5_PRECOMMIT`:** legacy bounded relocation planning of up to five ranked candidates, commit the first relocation witness and attempt target once. Label **planner-assisted** and account for all planner calls. Do NOT mix TOP5 success with TOP1 success in headline comparisons. Run G+M under its defined planner-assisted baseline and geometry-only TOP1 under its own no-planner-ranking protocol; explain the unequal compute/privileged checking available to G+M. Paired blind roots, same physical world/robot settings, root-level confidence intervals and joint travel/planning CPU/number relocations recorded. D is not an execution arm; it only identifies target blockers.

## 5. Execution stages and bounded authorizations

This contract **authorizes a staged bounded 2D program**, not indefinite autonomous scientific experimentation. An authorized phase may proceed to the next **only if** its scientific gate and resource gate pass. If data cannot support a requested claim or cap is reached, STOP with `BLOCKED`/`UNDERPOWERED` instead of rewriting the hypothesis, manufacturing labels, overspending or claiming completion.

### P10b-0 — Audit, preregistration, generator repair, D technical smoke test

- Verify both P10 commits, all checkpoint hashes, original P10a plan and frozen predictions, label provenance and past gates. Detect remote/source drift and preserve user files. Preserve immutable pilot records.
- Correct the pre-existing mechanism-yield gate: H7 must establish **edit feasible / physical relocation infeasible** with correct provenance; H8 must establish **original infeasible** in a genuinely constructor-disjoint root; an anchor merely *decided* is insufficient.
- Revise H7/H8 constructors using development-only attempts and sound checkers, with **no invented place-side proof**. If not constructible, declare unachieved and don't obstruct meaningful H1–H5/H10 completion.
- Implement minimal D model using a single new `d_blockers.py` (roughly ≤250–300 logical lines) and one compact testing/training driver, reusing project tensor encoding/data loaders. Optional one small helper file only if essential. Do **not** add a forest of folders or a large framework. First test permutations, normalization, gradient correctness, partial labels, alternative minimal sets, no-blocker state, >cap failure and zero planner calls on synthetic roots.
- Fix the P10a physical single-repair H1 root 01 reporting: its `A` **physical repair** was `BUDGET_INFEASIBLE` whereas the scene edit was certified; only the latter supports proof-grounded κ. Verify all other status wording.
- Preregister full benchmark, D blocker-set definition and comparator query interface, root/seed splits, builder constraints, statistical endpoints, learner/hypothesis selection, seed policy, stage caps and original 2D model versions in a hashed manifest, **before** collecting data. Commit+push source, plans and split roster before outcome collection. Present figures for at least one physical H1/H3/H4 and one 3-/4-move candidate design with honest PROPOSED/VERIFIED labels.

**Gate:** read-only audit/replay PASS; D synthetic exactness + simple tests PASS; clear scientific pre-reg; 0 physical calls in D/A/B/C inference; split secrecy and source hashes PASS. Constructor changes do not alter teacher negative semantics. If gate FAIL, STOP.

### P10b-1 — Initial independent 2D constructibility + attribution-data wave

- Collect up to **40 new independent** development/train/validation roots (none from blind sealed). Include proven H1, H3, hard H4 and H10 3-/4-relocation cases; begin D complete-subset blocker GT using fixed parking edits, with explicit exhaustive-decided coverage.
- Freeze candidate catalogues and counterfactual parking poses *before* teacher labels. Ensure teacher query IDs and statuses are genuinely distinct and auditable; cache by exact physical identity and never use model predictions to determine a blind label.
- Report accepted/proposed/rejected roots, yield by mechanism, #3-/4-move VERIFIED, ground-truth blocker sets and completeness, state/action witness trajectories, static checks/certificates, median and 95th-percentile query cost, UNKNOWN/BUDGET. Validate D mask labels from the saved full subset truth by an **independent** enumerator.
- **GO only if:** at least some soundly proved H1/H3, ≥1 physical 3-move AND ≥1 physical 4-move witness **or explicitly separate H10 BLOCKED**, and enough completely decided D masks to justify model training. Declare thresholds exactly *before collection* (proposal: ≥70% decided required contrast queries; ≥50% complete D masks; ≥2 witnessed 3-move and ≥2 witnessed 4-move roots to scale H10). If unmet, revise only development constructors, rerun a **bounded** second development attempt if caps permit, or STOP. Do not contaminate blind holdout.

### P10b-2 — Scaled, sealed physical dataset

- Only after P10b-1 GO: collect remaining independent roots in frozen, outcome-blind order to approach the preregistered total target. Keep physical ground truth and masks sealed for blind roots, with hashes and no training/validation access. The person/script evaluating blind may reveal outcomes **only after** predictions, model/thresholds and execution protocol have been frozen and committed.
- Do not allow acceptance filtering by whether a model is correct, whether a teacher result is convenient, or whether an outcome makes B/C look good. Record all attempted roots and outcome statuses; for certificate-targeted families report selection mechanism.
- Recompute data-yield/power feasibility after each preregistered 40-root batch, using training/development/validation only; do not peek at blind labels. Halt early if unsupported learning claim, cap or physical impossibility warrants it and write a useful partial scientific report.

### P10c — Final comparative training + ablations

- Train A/B/C/SF full-data 3 seeds with identical input and root splits; checkpoint by validation only; report optimizer, hyperparameter search budget, parameter count, steps, gradients, model capacity, calibration, train/validation curves, overfit vs constructor subgroup. Train short-sequence-only variants for extrapolation; do not merely test longer queries with the full-data checkpoint and call it out-of-length training.
- Train D and D-pairless control 3 seeds on **complete, provenance-valid** blocker masks; otherwise feasibility-only terms. Evaluate D blocker probability and uncertainty by number of true blockers; never use model-predicted blocker sets as GT.
- Carry out prioritized B/C factor ablations with complete retraining and same seed protocol. Report actual gains on proof-grounded H1/H3/H4/H5 and long repairs, including if B/C loses to A or SF. Avoid any performance claims from old disclosed P8c test.
- Freeze source/checkpoints, calibration, exact candidate sets, static veto, lengths, all model predictions and experiment scripts before unsealing the blind labels.

### P10d — Blind prediction and physically executed A/B/C

- On independently held-out roots, evaluate common initial-task/repair event NLL, calibration, mechanism-specific truth, κ, same-endpoint order margins, hard omissions, longer sequences, minimality-within-catalogue, D feasibility/blocker sets and every unsupported query. All metrics aggregated by independent root and with CIs.
- Run strict TOP1 physical episodes for A/B/C/SF/geometry and explicitly planner-assisted G+M; optionally secondary TOP5 if budget. Record every attempt and cost, success with SAFE_RETREAT, timing, scope cap failures, abstentions, error causes, trajectory visualization. Do NOT run D execution.
- Perform failure stratification and qualitative animations for representative: successful 3-move; successful 4-move; complementarity; order swap; necessary omission; false-feasible and false-infeasible; apparent negative cured by a different supported candidate. Avoid only showing favorable examples.

### P10e — Model-component proof ledger and final scientific verdict

- For **every** A/B/C module and F1–F5, show: mathematical definition, code path, real-scene factor visualization, test of shape/normalization/gradients/invariance, training signal provenance, factor removal control, performance effect+CI or clear NOT_IDENTIFIABLE/NOT_BENEFICIAL, and inference cost. D gets analogous one-page audit for `u`, blocker unaries, pair scores, exact normalization and independently adjudicated masks.
- Produce a final side-by-side A/B/C/SF evidence matrix: generalization, κ signs, order accuracy, hard omission, 3–4 move repair success, TOP1 executed success, efficiency/cost and failure modes. For D: initial retrieval feasibility plus blocker precision/recall/exact sets versus controls; **D not ranked as a repair planner**.
- Choose the empirically strongest approach(s) by preregistered decision rule. If SF/A wins or B/C contributions are null, state it explicitly; distinguish scientific completion from a positive result. Declare whether evidence supports **correlation**, intervention-conditional physical effects or actual causal mechanism transfer. Avoid claiming a learned SCM where none exists.
- Deliver a professor-ready concise technical summary, failure atlas, equations, best evidence animations, novel contribution statement bounded by actual results, and reproducibility manifest; explain remaining 3D work as FUTURE, not implemented.

## 6. Budgets, stop rules and reproducibility

These are **suggested maximum authorizations for this handoff**, not expenditure targets or guarantees of completion; honor lower previously committed caps within earlier stages. Track **aggregate CPU and wall**, not only per-job, including failed/censored runs and construction. One worker for the physical teacher; independent guarded jobs for learner/figures. The full new program must stop if a cap is exceeded or work cannot finish safely.

| Category | Proposed aggregate new limit | Notes |
|---|---:|---|
| P10b constructor development | **3,000 CPU-s** | Includes failed/rejected trials and revised H7/H8; no secret repeated sweeps |
| P10b teacher, *including* D counterfactual labels | **24,000 CPU-s** | ~180 roots is an aspiration, not a guaranteed throughput; staged 40-root yield gate then bounded waves; count all planner/IK teacher work |
| P10c training, D and prioritized ablations | **24,000 CPU-s** | Includes failed jobs, matched 3 seeds; stop cleanly and mark ablations NOT_RUN if exceeded |
| P10d executed episodes | **15,000 CPU-s** | Strict TOP1 primary; separate TOP5 optional; count all planner steps |
| Regression/visualizations/evaluation | **5,000 CPU-s** | Itemize fixture planner calls separately from learned inference |

**No external paid APIs, no hardware, no 3D physics, no 3D perception, no Slot Attention implementation.** Existing frozen DINOv2 embeddings preferred; no new GPU obligation. Do not silently invoke a tool/provider requiring payment. Do not promise full 180-root delivery at the estimated average cost; measure achieved root/contrast counts and either finish within caps or report the scientific blocker.

**Seed policy:** choose a per-query budget consistent with all required seed attempts; unlike P10a, do not assume three 100-s seeds fit inside 120 CPU-s. If prioritizing full seed policies, allocate a higher explicit per-query maximum within aggregate cap; else censor uncompleted runs to UNKNOWN, never operational-negative. Predeclare both options and choose once before new labels; never adjust policy after viewing a candidate's success. Keep OPNEG-v1 source statuses and distinguish a *new* teacher seed-budget version from the original.

**Fail-closed conditions:** hash mismatch, unsafe ID aliasing, nonfinite likelihood/gradient, missing checkpoint or source, outcome leakage, unsound certificate, broken scope-normalization, incorrect brute-force likelihood, unexpected planner-in-inference call, invalid sealed split, unrecorded threshold update, labels changed after freeze, exceeded exact-factor scope, CPU cap exceeded. Fix implementation bugs only in the development branch with explicit versioned re-runs; if confirmatory holdout is compromised, label it disclosed and create a new sealed holdout if budget allows—never quietly recycle it.

## 7. Minimal code structure and validation deliverables

Use existing root modules, not a new package or many subdirectories. Suggested files: `d_blockers.py`, `p10b_dataset.py`, `p10c_train_eval.py`, `p10d_execute.py`, `p10e_report.py`, and `tests/test_d_blockers.py`; adapt existing `p10_*.py` only with small well-tested hooks. Each new source file **target ≤300 logical lines**; prefer extracting small reusable utilities over duplicating large P10 drivers. No unbounded orchestration harness. No deprecated-method rewrite.

**Expected sequential reports**, continuing existing `responses-phases/` numbering:

- `0039_P10b0_source_audit_prereg_and_D_math.md`
- `0040_P10b1_multi_obstacle_and_blocker_GT_pilot.md`
- `0041_P10b2_2D_dataset_split_and_provenance.md`
- `0042_P10c_ABC_SF_D_training_and_ablation_results.md`
- `0043_P10d_blind_predicted_and_executed_2D_results.md`
- `0044_P10e_model_component_proofs_and_scientific_verdict.md`
- `P10_2D_SCIENTIFIC_DECISION.md`
- `D_DESTINATION_AND_RECURSION_DEFERRED.md`

Artifacts: guarded stage gates (`PASS / FAIL / BLOCKED / UNDERPOWERED`), accepted/rejected and missing-case ledgers, root/query/teacher hashes, checkpoint SHA-256, source/version manifest, train/validation/blind sealed hashes, paired root-bootstrap analysis, ablation matrix, object/robot rendering and physical witness GIFs. Every visual is tied to root/query, teacher provenance, source hash; label hypothetical scenes as HYPOTHETICAL, certified failures as CERTIFIED (no fabricated trajectories), operational negatives as BUDGET. Include one clear **3- and 4-relocation frame sequence** if witnessed; if unavailable show the failure-to-construct evidence instead.

**Must end with direct answers**:
1. Are A/B/C actually better than SF, geometry-only and G+M on new long repairs? By how much, at what uncertainty and physical compute?
2. Does C improve over B on genuine paired order contrasts? Does B/C outperform A on complementarity after seeing relevant training data?
3. Which of F1–F5 matters on which independently validated phenomenon? What is still unidentifiable?
4. How does performance/coverage degrade from one/two to three/four required relocations, and where does exact factor inference fail?
5. Does D identify genuine initial blockers, including jointly necessary/alternative minimal sets, better than a pairless or heuristic baseline? How reliable is feasibility prediction?
6. What is still open? Explicitly **D destinations/recursive displacement and all 3D work**, rather than implementing either.

**Completion rule:** A scientifically defensible 2D evaluation is complete only when the claimed mechanisms have independently decided ground truth, matched new-training results, blinded comparisons, appropriate ablations, root-level uncertainty and reproducible executed evidence—or when the final report explicitly establishes which hypotheses were unsupported or underpowered and why. **Do not optimize for a positive B/C result. Optimize for a trustworthy result the professor can scrutinize.**
