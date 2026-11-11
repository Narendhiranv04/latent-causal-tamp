# P8 — Decisive Coupling, Repair Selection, and Matched Planning Evaluation

**Status:** Prospective, executable implementation-and-experiment contract for Claude Opus 5.5 High. **No P8 experiments have been run by the author of this document.**

**Starting repository state:** P7a committed `bc20227`, P7b committed `1154314` (as reported by the project operator). Verify actual HEAD, branch, remote and working tree; do not presume these hashes match until checked.

**Authoritative scientific reference:** `latent_causal_tamp_methodology_v1_7.md` (science) and `latent_causal_tamp_implementation_guide_v1_9.md` (engineering), as amended by versioned, implemented, audited P4–P7 operational and architecture contracts. Historical reports are **evidence**, not an invitation to rewrite those contracts. Source reports:

- `responses-phases/0022_P7a_representation_and_optimization.md`
- `responses-phases/0023_P7b_diverse_roots_training_execution.md`
- P6 report 0021 and P5 report 0020 for regression provenance.

**Authorization boundary:** P8a and P8b, then **conditionally** P8c and P8d when their gates pass. All numerical ceilings below are explicit maxima. No unbudgeted reruns, G5/G6 release, 3D, hardware, new oracle semantics, or changes to the `2D-ABC-OPNEG-v1` teacher policy. A negative scientific result is an acceptable completion, not grounds for inventing another architecture.

---

## 0. What we actually know, and what P8 must resolve

### 0.1 Findings from P7 (do not reinterpret)

P7a repaired real implementation errors in the new `ABC7_V1` model: (i) scene edits scarcely changed pooled representations in P6; (ii) alleged scene beliefs depended on the scored repair; (iii) omission–repair pair potentials were missing as distinct factors; (iv) the joint-pool loss dwarfed other loss components. P7a introduced edit-specific object channels, root-consistent scene beliefs, explicit omission pair terms and root-wise loss normalization, and passed mathematical, tiny overfit, and regression checks. B's legacy-scene effect error fell dramatically, but those P6 roots all exhibited the same `κ=+1` motif and could not validate compositional generalization.

P7b collected 48 new roots spanning six predeclared families (complementary, redundant, irrelevant, order, motion barrier, alternatives); 971 planned queries yielded **269 VERIFIED, 368 CERTIFIED, 125 BUDGET_INFEASIBLE, 8 UNKNOWN and 201 NOT_RUN**. Thus **762 decided**. It collected `κ` roots +1 (16), 0 (7), −1 (5); 19/28 of these κ outcomes rely on operational place-side negatives, not proof. Only 17 decided same-endpoint order contrasts and 12 one-shot test scenes were available.

On fresh sealed-test roots: A feasibility accuracy 0.890, AUROC 0.963; B 0.833, 0.926; C 0.833, 0.917; **B-no-coupling** 0.897, 0.953; supervised non-energy S (one seed) 0.897, 0.966. Coupled B predicted +1 too broadly, while the uncoupled B predominantly missed complementary (+1) interactions. B had the best individual scene-effect MAE (0.220) but **not convincing κ generalization**. The 48 new independent one-shot simulator executions were: A 6/12, B 6/12, C 7/12, uniform 6/12. No learned winner. A/B's 4,000-step chains mixed poorly despite detailed balance (TV ~0.67/0.66 vs exact), and C clipped gradients very frequently (~89–99%). Two references failed under motion-planning limits; some incomplete root catalogues were induced by expensive searches. All these observations must be reflected in P8's baselines and accounting.

**Important logical point:** predicting a nonzero signed interaction

\[\kappa_{I,J}=y_{I\cup J}-y_I-y_J+y_0\]

**does not itself demonstrate a learned joint coupling.** A factorized predictor of four marginal intervention outcomes can produce the same κ. We need matched predictive or decision-theoretic comparisons with and without cross-outcome factors, ideally under limited outcome supervision and/or a separate *explicitly labelled offline conditional-evidence diagnostic*. That latter diagnostic is **not deployable counterfactual oracle access**.

### 0.2 Primary questions, in order

1. **P8a: Does generic joint coupling add information?** Compare `B-full`, `B-structured` (scene/omission structured pairs retained; generic coupling removed), `B-none` (all cross-outcome interactions removed), and a parameter-/input-/supervision-matched **factorized-outcome** non-energy model. Repeat relevant `C-full` vs `C-structured`, plus A/S references if affordable. Is improvement root-general, rather than tied to the dominant sign or a larger network?
2. **P8b: Are poor decisions caused by calibration/thresholding, candidate generation, ranking, or insufficient motion-verifier budget?** Measure the whole funnel. Fix demonstrable decision-path bugs and compare legitimate alternatives without relaxing one-shot execution semantics.
3. **P8c: Can a relatively small, targeted, predeclared **κ-balanced** collection produce genuinely informative, independently rooted evidence without expensive missingness and static-screen shortcuts?** Preserve labels and failures exactly.
4. **P8d: Do models select useful *physically executable* repairs under matched compute against uniform, S, and a strong **geometry + complete motion search** baseline?** Use *fresh* sealed roots, actual independent simulator execution, and sensible confidence/abstention accounting.

### 0.3 What counts as a useful outcome

A **positive** P8 outcome is evidence of improvement on root-held-out **selected-and-executed** repair success, reliability, or a rigorously defined conditional-outcome prediction task, under fair budgets. A **negative** P8 outcome is a reproduced, fair result that a simpler model or nonlearned planner wins, documented well enough to simplify the methodology. Software correctness alone is an **engineering PASS**, not proof that explicit causal coupling helps. Do not design a new network to force a positive finding.

---

## 1. Physical semantics and nonnegotiable invariants

- Use existing exact **fixed-base 2D 3R articulated robot**, all full-width links/fingers/base, rigid object attachments, joint limits, collision clearances and **48 declared grasps**. No circle-only translation or teleportation can count as a robot repair.
- Resting destinations: 8×8 grid, pitch 0.08 m, identical disc radius 0.024 m, single 0.005 m clearance unless an explicitly separate future version; the joint trajectories and carried-object paths are continuous.
- Canonical repair `r=((i1,k1),...,(im,km))`, **0≤m≤4**, move-once distinct non-target objects, no stays/padding as separate proposals, explicit ordered intermediate object poses. Never silently reorder, reroute the chosen object sequence or reset arm state to home between moves.
- A successful queried repair includes witnessed pick → carry → place → release → retreat **for every action**, followed by the target action from actual achieved state and **GOAL_AND_SAFE_RETREAT**. A successful original task uses the empty repair.
- A `scene edit` only changes predeclared object poses in the hypothetical **initial** scene; original robot q/gripper/attachment and appearance anchor are unchanged. Scene-edit verdict is target-only and does **not** prove the robot can implement that edit.
- Omission `r\A` removes the designated action(s) and recomputes all remaining ideal prefixes; omitted objects remain in the scene at stay. Label with an **independent** oracle result, not inferred from the successful full-plan trajectory.
- Physical status is `VERIFIED_FEASIBLE` (complete independently checked witness), `CERTIFIED_INFEASIBLE` (sound stated-scope certificate), `BUDGET_INFEASIBLE` (all required allowed seeded planner calls finish on clean terminal failures under **unchanged OPNEG-v1**), `UNKNOWN`, `NOT_RUN`, or error. Only the first three are supervised decisions under the existing operational policy. Budget negatives are **not mathematical impossibility proofs**; report results both with and without them.
- A7 place-side certificate **remains disabled**. Do not enable based only on 2 mm tolerance, static goal-center collision or planner failure; a separate independent soundness proof would require new authorization. LINK0_SECTOR_PICK and other existing certificates retain their audited scopes.
- All models use the same initial information: frozen DINOv2-small mask-pooled appearance; supplied object geometry/poses, q0/FK, target and goal; legal candidate domain. **Forbidden:** true future trajectories, teacher outcomes, cause certificates, oracle collision distances, post-intervention screenshots, teacher seeds/grasp paths, root IDs, family ID, split, privileged role flags derived from ground truth, target task outcome. Counterfactual geometry obtained by applying an explicitly declared pose edit to the original structural scene is allowed.
- Retain primary models: A local unary/pair + GRU + travel head; B explicit joint z with prefix order; C explicit z with GRU, no duplicated prefix order. Candidate-selection displacement and learned first-witness joint travel remain **separate** from the B/C feasibility factors.
- Two metrics must always remain distinct: a) probability the *original target* succeeds after a **fixed-robot hypothetical pose edit**; b) probability the **ordered robot relocation + target** succeeds. Do not train on one and report the other as interchangeable.

---

## 2. Read-only repository and evidence audit (mandatory first)

Before edits:

1. Inspect HEAD/remote/dirty state; list relevant Python modules/tests, plans, manifests, configs, report 0022/0023, `ABC7_V1`, `Z_LAYOUT_V3_R4`, sampler and `ordered.primary_v2` executor. Do not invent filenames; adapt this document's suggested responsibilities to the actual repository.
2. Verify the **316/316** reported P7 final test baseline and **6/6** archived replays if executable under a guard. Verify evidence hashes without rewriting P4–P7 records. The 2 tracked root-PDF deletions and user's untracked instructions remain untouched.
3. Recompute **only from saved records** P7 status totals, split lineage counts, κ sign coverage with proof-vs-operational scopes, scene/omission masks, order pair counts, 48 episode denominators, and one-shot status breakdown. Flag mismatches as data-integrity errors, not convenient rounding.
4. Trace code path from edited-scene input to scene logits to root-level `P_S(z_scene|c0)`; from repair-specific tokens to `P_Q(z_repair,z_omit | z_scene,r)`; and from their normalized energies to marginal repair energy, first-witness J predictor and proposed/selected repair. Produce a two-page (maximum) parameter/gradient graph and tensor shape audit.
5. Verify `full`, `quadratic`, `structured`, `none` coupling semantics **by direct module traversal, autograd and controlled value tests**. In particular, `structured` must keep scene and omission structural pairs while removing only generic coupling; `none` must remove all cross-outcome interactions. The existing P7b reported `B-no-coupling` is the `none` branch, **not** a clean test of generic φ_couple alone.
6. Record whether P7's root-conditioned chain normalization makes `P(z_scene|c0)` insensitive to the generic scene↔repair coupling **by construction**. If so, an improvement to root-level κ from that coupling is impossible without changing that factorization. Do not pretend that a constrained graph can express a prohibited effect. The desired semantics may support *conditional repair* gains even if it cannot change unconditional scene marginals. **Diagnose before editing.**
7. Write `runs/p8/audit/analysis.md`, `factor_mapping.json`, `replay_audit.json`, `data_coverage.csv`, `baseline_status.json`. The report must distinguish observations from hypotheses and show exact results under archived model versions.

**Audit gate:** All input/output scopes consistent, reproducibility checks complete or an explained BLOCKED status. Abort any training or collection if historical evidence changed or if the teacher/robot contracts cannot be reconstructed.

---

## 3. P8a — Decisive joint-coupling experiment (no new teacher calls)

### 3.1 Scientific estimands, not just scoreboards

Define **three separately reported tasks**:

**(i) Unconditional intervention prediction (deployment-input-only):** for an initial scene `c0`, predeclared eligible edit I, predict `p_S(I)=P(Y_I=1|c0,I)` without true edited outcome observations. Score BCE/NLL, Brier, ECE, balanced κ sign and κ MAE over complete roots, macro averaged by root and separately by observed κ sign. A, B, C and S/factorized baselines must all receive edit-specific geometry. Correctly note that **a factorized model can produce nonzero κ**. This tests *representation and optimization*, not automatically generic coupling.

**(ii) Offline conditional-completion diagnostic (joint modeling only):** Given **explicitly revealed ground-truth outcome bits from the same root**, estimate held-out outcome bits `P(z_hidden|c0,r,z_revealed)` using exact conditioning for B/C. This is **an offline scientific probe**, never a robot-inference input. Predeclare reveal masks that are shared across arms and root splits, e.g. (a) reveal `z0, zS[A]` and predict `zS[B],zS[AB]`; (b) reveal both singletons, predict joint; (c) reveal `zR` and one genuine omission, predict other omitted outcomes. Only use eligible fully decided outcome sets, record per-task denominators and avoid always revealing a label that trivially gives away its target. Evaluate per-hidden-bit NLL/Brier and calibration; root-macro average with bootstrap intervals. Compare `B-full` vs `B-structured` vs `B-none` vs a **factorized** outcome predictor that ignores other revealed bits, with identical direct edit features. If conditional evidence is not available at deployment, any gain is **not an autonomous recourse improvement claim**.

**(iii) Repair prediction/selection from original input alone:** learn scores for canonical 0–4-move repairs and compare feasibility NLL/Brier/AUROC, same-endpoint order ranking, first positive rank, cost MAE and restricted-catalogue selection success/abstention. Absolutely no revealed z bits on this path. This is the primary route to later executed improvement.

### 3.2 Correct probabilistic graph comparison

Use `ABC7_V1` as frozen scientific base; introduce **`ABC8_DIAG_V1`** only if code fixes or controlled diagnostic heads require changes. Produce factor graph truth table for each version and a parametric graph diagram (PNG/SVG made programmatically, not invented as observed results):

- `B-full`: static + prefix sequence + scene unary/structured relationships + omission unary/structured relationships + generic quadratic and optional higher-order joint coupling.
- `B-structured`: **identical** static/sequence/scene/omission functions, but **generic** coupling off; maintain structured scene and omission pairs.
- `B-quadratic`: same as full with higher-order residual off.
- `B-none`: **all cross-outcome interactions disabled**, including structured pairs; keep direct per-edit and per-omission unary predictions.
- `S-factorized`: non-energy DeepSets/permutation-invariant edit-specific outcome predictor and repair feasibility head, trained with equivalent outcome masks, root counts and total supervision. Parameter-match to B where practicable, and report unavoidable parameter differences.
- `C-full` vs `C-structured` as secondary matched GRU tests; A as direct-local reference. Preserve a named original S implementation; do not silently rename it to a new control.

The model's **outcome layout**, active masks, variable-dimension reference measure, exact 512-state upper bound, scene edit root consistency, omission-prefix semantics, and `P_S`/`P_Q` normalization **must stay mathematical invariants**. Model changes cannot retroactively reinterpret old checkpoint keys. If a factorization inherently blocks a proposed type of coupling, keep the legitimate hypothesis (e.g. conditional dependence) and label the unidentifiable one accordingly rather than silently restructuring B.

**Critical tests (at least):**

1. With exactly identical direct logits but different cross terms, demonstrate the expected changes (or forced invariances) in unconditional scene marginals, conditional scene predictions, repair marginals and total ranking. Record derivative/zero-gradient assertions, not just a screenshot.
2. For true `none` modes, verify a product-of-marginals conditional joint within numerical tolerance on a deliberately nondegenerate fixture. For `structured`, verify that toggling an explicit omission pair changes a relevant conditional outcome even with generic coupling off.
3. Exact partition normalization and 2^K enumeration for K=4,…,9 (max 512); independent brute-force `logsumexp`, finite-difference gradients and inactive-slot invariance. Verify cardinality-reference correction makes equal raw per-state energies produce equal *marginal* repair energies across K but does not erase genuine distributional differences.
4. Scene prediction invariance to candidate `r` (<1e−10), identity/distinctness of the three edit vectors, object-ID permutation symmetry, order-swap difference, no GRU in B and no duplicate prefix factor in C.
5. Explicit omitted-action outcomes: query/position IDs unaliased, omitted object physically remains at its initial pose until any non-omitted action; zR↔zO structural pair present in `structured`.
6. Gradient-reachability test for **each named factor** in each relevant objective; explain any zero-by-architecture gradients. No fake cross-effects through tensors accidentally containing future labels.
7. Differential result on three **independent** synthetic roots with κ −1/0/+1 **and** a held-out compositional fixture, not only ability to overfit three roots. Synthetic success is a unit/capacity test, not a science result.
8. Test that all four comparator arms receive identical input fields and label masks; if unmatched, do not attribute differences to coupling.

### 3.3 Data and supervision regime

- **No new root collection in P8a.** Use P4–P7 saved development roots and labels. Previously inspected P6/P7 test sets are **legacy diagnostics**, not fresh tests. Never let downstream threshold/model decisions be described as independent on them.
- Create a **balanced-by-root** training sampler and report actual decided label masks and proof-vs-operational sources by κ sign. Do not simply duplicate +1 examples and declare balancing; use inverse-frequency weights within a clip or a fixed root sampler. Report both naturally weighted and root-balanced evaluation.
- Two **matched supervision regimes** on identical roots: `FULL_DECIDED` (all actual decided auxiliary outcomes available), `SPARSE_AUX` (e.g. predeclared 50% of auxiliary scene/omission labels hidden **for training only**, with independent hash-based masks and identical hides for every architecture). Do not hide task labels unless a separate ablation. A held-out auxiliary label is not used in training energy, any BCE, pool target, or data-derived feature. Crucially, a pool is eligible only if all fields required by that pool objective remain observed after masking; never fabricate completion.
- In `SPARSE_AUX`, the count of surviving fully decided B/C pools may shrink sharply. Report exact counts; if insufficient, mark the joint likelihood term **N/A** rather than claiming an ablation failure.
- Use existing `2D-ABC-OPNEG-v1`: proof-grounded metrics as primary where enough complete roots exist; operational negatives separate; full-vs-certified-only sensitivity. No `UNKNOWN`, `NOT_RUN` or censoring converted into negatives. Root scenes, not individual actions, are bootstrap units.
- For identical training sizes, compare 3 fixed optimizer seeds per **primary** B-full/B-structured/B-none/S-factorized and, if budget allows, C-full/C-structured and A. Record parameter counts, epochs, gradient updates, CPU/wall, clipping, best validation checkpoint and thresholds. Comparison with matched **updates** as well as matched **CPU** is required in diagnostics; not feasible to equalize both exactly, so report the tradeoff and never hide it.

### 3.4 Optimization controls

- Preserve P7a root-wise term normalization; measure raw and scaled loss magnitudes, and per-term preclip gradient norms. Clip and `λ_pool` candidates are **predeclared**, tuned only on development validation, with stable budget. Suggested small grid: clip {1,5} × pool {0.25,0.5}. Do not expand this post hoc. Reject NaN/Inf immediately.
- No adding learned attention, trajectory predictors, auxiliary teacher models or new latent causes. One bounded edit-feature or factor bug fix is allowed if supported by a failing test; version it and retain the previous model as control.
- If C remains >80% clipped at chosen hyperparameters, report this as **optimization-limited**; do not describe lower test accuracy as evidence against recurrence without the matched-update sensitivity check.
- Temperature calibration on development validation only. Do not calibrate each root using its hidden teacher results.
- Use the historical evidence to choose the *scientific test design*, not to claim fresh transfer.

### 3.5 P8a exit criteria

Engineering PASS requires (a) exact mathematical and factor-scope tests, (b) full regression and six replays, (c) comparable three-seed runs or explicitly declared cap-limited partials, (d) factorized-control comparison, (e) matched full/structured/none results, (f) **separate unconditional and offline conditional** evaluations, (g) honest interaction sign and missingness tables. **No mandatory accuracy improvement**: B-full losing cleanly is a meaningful result.

Deliver `runs/p8/a/` logs/configs/models, `responses-phases/0024_P8a_joint_coupling_decisive_audit.md`, PNG/GIF diagnostics, and a machine-readable `P8A_GATE.json` containing per-check PASS/FAIL/NOT_RUN, CPU, cap, hashes and scientific outcome. **STOP P8 here** if the mathematical invariants or leakage tests fail; otherwise continue to P8b even if coupling loses.

---

## 4. P8b — Repair selection, verifier fairness and sampler diagnostics (no new teacher calls)

### 4.1 Decompose failure sources, in order

On existing P7 legacy development/diagnostic roots **without any new teacher calls** measure for each model and each selected candidate:

- Original task status/predicted `p0`; false-feasible empty-repair choices, stratified by certificate vs operational label.
- Candidate-generation coverage: fraction of roots whose frozen catalogue contains ≥1 VERIFIED repair; if none, **selection cannot possibly succeed**, regardless of energy.
- Learned ranking quality: first VERIFIED rank, ordered same-endpoint pair ranking (with denominators), calibration and NLL conditional on candidate length m=0..4, and per-move false-positive rate.
- Selection filter: count passing p threshold and exact static screens; how often predicted feasible shorter candidates preempt verified longer candidates; how often false negatives cause abstention.
- Relocation verifier: which ranked candidates have complete relocation witnesses and how many actual independent calls/CPU nodes/time are spent to find one; **this is different from target execution success**.
- Commit/target: once a relocation witness is committed, exactly one target attempt and safe retreat, no alternate target-plan retry or post-feedback reranking.
- Selection optimality: compare chosen repair length with **minimum known VERIFIED candidate length within the frozen evaluated catalogue**; separately label roots where candidate pool incomplete. No globally shortest claim.

Report a **root-by-root decision funnel CSV** with stages candidate exists → scored → threshold admitted → motion witness → committed → target attempt → GOAL_AND_SAFE_RETREAT, and status denominators including abstain, failure and censoring. Use saved teacher data only for *offline assessment*, not to construct rankings.

### 4.2 Calibration/threshold sweep with frozen candidate domain

- Retain the methodology's lexicographic selection (admitted predicted-feasible candidates: **fewest moved objects, least predicted first-witness J, least analytic displacement, lowest feasibility energy**, deterministic tie break). Do **not** quietly replace it with a soft weighted move cost that can permit extra moves solely for convenience.
- Compare current validation-calibrated `p≥0.5` against a **small frozen threshold family** {0.5,0.7,0.85,0.95}, with a separate **abstain/no-safe-prediction** outcome. Candidate screening and action budget must match. Do not claim arbitrary thresholds guarantee safety. Selection threshold should be selected from **development validation** using declared lexicographic criterion: (1) lower false-feasible `r=∅` rate on known-negative initial tasks; (2) higher eligible-root successful *offline* repair fraction (count abstain as failure); (3) smaller predicted verified move count / J conditional on success. Report coverage/abstention and secondary thresholds even if no threshold dominates.
- If no threshold improves the primary success/abstention tradeoff, retain 0.5 and document. A successful 0-move query should still be considered whenever its calibrated p clears the same threshold.
- Optional lightweight seed-ensemble disagreement can be displayed, but if used for selection it must be treated as an independently named, budget-charged variant and chosen on validation only; do not silently mix seed-0 and 3-seed results.

### 4.3 Sampler correctness versus useful mixing

- Revalidate detailed balance, stationary normalization, proposal symmetry/asymmetry corrections, and z-marginal cardinality for G4B on repaired models. **Detailed balance is necessary but insufficient**.
- On at least **three** finite development candidate pools (easy, medium, 4-move/large), compute exactly normalized proposal probabilities **if computationally feasible**. For each sampler, use predeclared chain budgets of 4,000 and 16,000 steps, ≥4 seeded chains, log lag autocorrelation/ESS, mode occupancy, top-k candidate discovery, empirical TV to exact π when exact π exists, effective scoring/proposal CPU and wall. The 16k budget is diagnostic only, not a free inference advantage.
- Validate and account for the fact that adding analytic displacement and learned J changes the sampling distribution, but not the feasibility energy's intended probability semantics.
- Define a **deterministic bounded-pool fallback** for serious mixing failure: enumerate/score the same canonical candidate pool (or a predeclared deterministic beam if full pool too large), and sort by the same gated lexicographic selector. Charge every score and model call; do not implicitly use teacher outcomes. Compare sampler vs deterministic ranking on **equal** model-evaluation and wall/CPU budgets. The fallback is a benchmark variant, not a fabricated new scientific model.
- A long Markov chain with TV ~0.67 should not be reported as delivering representative Boltzmann samples. If exact stationary diagnostics remain bad, **retire the sampling claim at that runtime** and default to deterministic bounded search for P8d, declaring it in the frozen plan.

### 4.4 Strong baseline specification

Implement or inspect a **geometry + full-motion** (G+M) baseline, with no training and **no future teacher verdict**:

1. Receives exact same initial geometric/robot inputs and canonical candidate domain available to A/B/C, optionally ranks by independently deterministic accessible static checks, fewer moves, support/collision eligibility, analytic object displacement and deterministic robot-proximity heuristic.
2. May perform permitted **complete 3R relocation motion planning**, including grasp/transport/place/retreat and all initial q continuity, to find a relocation witness for ranked candidates. Every planner call, node limit and CPU use is charged against the **same total execution envelope** as learned arms. This baseline is not allowed to query the target's eventual result for many repairs before committing. It can screen placements pre-commit but not run multiple target attempts.
3. If the same pose screen **generated** a scenario, report potential constructor-alignment advantage; do not present those screens as a privileged outcome oracle. A geometry-only screen alone is **not** a full physical repair-success baseline.
4. One declared stochastic uniform-rank baseline U over identical candidates and executable query budget; predeclare hash-based seeds. Existing S non-energy scorer is mandatory too.
5. All baselines get the same data-independent universe, top-k allowances, call accounting, no fallback after committed target failure, and complete denominator.

### 4.5 P8b exit criteria

PASS requires a reproducible root-level failure funnel, genuine repaired/no-repair calibration evaluation with abstentions, sampler mixing report/fallback decision, and tested, no-leak full G+M baseline runnable under `ordered.primary_v2`. It **does not** require models to beat uniform. No new teacher calls or hidden test use. Save `runs/p8/b/`, `responses-phases/0025_P8b_selection_sampler_and_baselines.md`, machine-readable `P8B_GATE.json`, and GIF of identical candidate sets / rankings with no invented robot paths.

If same-budget baseline cannot be implemented or full one-shot boundary fails, STOP before P8c; fix only the identified engineering defect inside cap.

---

## 5. P8c — Small targeted collection, only after P8a/P8b PASS

**Rationale:** Old P7 test roots have been examined. Fresh evidence must be independently rooted and pre-split, with a narrower, label-efficient catalogue. This is a **targeted 36-root pilot (not broad scaling)** to compare κ signs and selectivity. Each sign is a *construction intent*, never automatically a label.

### 5.1 Frozen root and split plan

- **36 new independent 2D roots**, 12 per κ construction intent: `K_PLUS` complementary, `K_MINUS` redundant, `K_ZERO` irrelevant/additive. Cross these with more than one physical layout/robot q stratum and target/goal location. Include up to four obstacle moves within the same cap, with some alternative feasible lengths and same-endpoint orders if physically constructible.
- For **each intent family**, assign **6 train, 2 validation, 4 sealed test** roots **before construction/outcomes**: overall 18/6/12. The 12 sealed roots must remain fully inaccessible to training, threshold fitting, dataset adjustments and queries for signs/counts until checkpoints, rankings, baselines and evaluation scripts are frozen and checksummed.
- Make physical motifs varied, not just rigid translations of identical adjacent-neighbor discs. Preserve identical discs and the validated scene robot contract; vary relative offsets, accessible sides, target/goal, q0 strata, more than one independent nuisance/occluder arrangement, and whether scene edit shifts alter later carry/approach/retreat reachability. Reject constructions statically **before** teacher labels where required; log every attempt. Do not select successful κ roots after viewing outcomes or silently discard failed-intent constructions.
- Do **not** pass family/sign-intent, root/seed/split, construction fingerprints or teacher status to any model. Hold original appearance anchor unchanged across edits. Make render overlays clearly mark original vs hypothetical.

### 5.2 Query catalogue and why it's different

- Freeze **at most 20 unique teacher queries/root**, **720 planned query maximum**, before any teacher call. Query identities include exactly the executed ordered proposal, and fixed-robot edit IDs; avoid duplicated aliases in z-layout. Static-invalid endpoint checks are logged separately and use no teacher calls.
- **Essential precedence:** (1) reference, original empty-repair; (2) A, B and A+B scene edits + one nuisance if eligible; (3) one primary complete repair and at least one designed alternative of different move count (where possible); (4) same-endpoint swap and leave-one-out omission closure for the primary (up to four omissions); (5) optional alternate destinations / longer variants. The exact per-family graph and list must be frozen; mandatory prerequisite labels before low-priority, expensive optional candidates whenever permissible.
- Use an **outcome-blind deterministic priority function** (predeclared query type, static screen/certificate result, cheap analytic costs and fixed ID tiebreak), to make cheapest/essential-first ordering reproducible. **Do not prioritize using learned model probabilities or teacher outcomes**. Admit only catalogue queries under unchanged `2D-ABC-OPNEG-v1`; the planner's 3 seeds, budgets and terminal requirements stay identical. Never convert a not-attempted query or censored attempt to BUDGET.
- Compare ability to close complete B/C outcome pools and κ tuples against P7's `201 NOT_RUN / 971 planned`, with status-aware accounting. Require full trace of every per-root root/batch/aggregate cap and the reason for each `NOT_RUN`.
- Important: A claimed `κ` requires all four relevant scene edit statuses decided with the same fixed robot state and eligible edits. A *proof-grounded κ* requires evidence sound at the scope of each relevant outcome. Otherwise it is **operational κ**, not geometrically certified. Treat `UNKNOWN` as missing, not 0.
- Include direct controls for original-task success and same-scene **0-move alternative grasp/path success** when the independent planner finds one; don't artificially force every root to require relocation. Catalogues should contain alternatives at different move lengths and destination choices, but only report observed decided ones.

### 5.3 Strict budgets and waves

- Root construction and deterministic static admission: **≤800 CPU-s total**, independent of teacher CPU; no planner calls in admission.
- Teacher: **≤12,000 aggregate process-tree CPU-s**, **≤24,000 wall-s**, **1 worker**, **≤650 CPU-s/root**, **≤6,000 CPU-s per 18-root wave**, hard cancellation margin as in existing guard, **≤720 planned queries** and at most the corresponding policy-authorized seed attempts. **Never reuse the unused P7 teacher budget**; P8's numbers are new caps.
- Evaluate wave 1 (18 roots, **6 per intended sign**, of which 3/1/2 are train/validation/test per sign) using **development roots only**; sealed test roots contribute at most status/integrity counters, not sign distributions or tuning. Predeclare this specific per-wave split before labels.
- After wave 1, continue wave 2 only if: all hash/teacher-policy/test invariants hold; **at least one decided κ of each sign in development roots**, at least one fully decided multi-action pool per targeted sign, **at least two roots with different witnessed repair lengths**, and UNRESOLVED+NOT_RUN ≤35% of attempted/planned development queries. Otherwise stop and report `P8C_PARTIAL`, with no post-hoc changes to improve a gate.
- After wave 2: desired coverage **≥4 independent development roots/sign with decided κ**, of which **≥2/sign proof-grounded if physically available**, and ≥8 development roots with ≥2 verified repair lengths. These are *scientific sufficiency goals*, not permission to invent labels; if missed, classify interaction evidence **INSUFFICIENT** and keep test sealed or execute a predeclared diagnostic evaluation with an explicit insufficiency banner, depending on the frozen plan.
- No additional scenes, no third wave, no budget increase automatically. Report proof-only/operational and true verified success separately.

### 5.4 Training protocol for fresh evaluation

- Train once on P8c TRAIN plus separately versioned, historically eligible development roots from P4–P7. Historical test roots are **development-eligible only if already disclosed**, and must be identified by source to prevent calling transfer across them fresh. P8c validation selects early stopping, calibrations and thresholds; do not use its test roots.
- Strict model arms: **A, B-full, B-structured, B-none, C, S-factorized**, plus optional C-structured if feasible within budget. **Three optimizer seeds for all six named primary arms.** Identical inputs/labels/outcome masks wherever defined; frozen root sampler and supervision regimes. Keep reported class/scope balance. No optional arm may steal CPU from required six.
- Freeze configurations from P8a/P8b, with only **predeclared** validation selection. Record matched number of **optimizer updates** in a primary table and measured CPU/wall for every run; also report a budget-matched-CPU sensitivity when supported by saved checkpoints. Do not report matched updates as matched compute.
- Fresh P8c results must report: feasibility NLL/Brier/AUROC, calibration/false-positive empty repairs, macro κ MAE/sign by observed sign and provenance, omission effects, order accuracy/coverage, root-level top-k feasible rank, predicted-vs-measured first-witness J, exact z joint/pool likelihood where complete, `FULL_DECIDED` vs `SPARSE_AUX` diagnostic if resources allow, and selection/abstention. Compute root bootstrap intervals; N/A where denominators insufficient.
- Freeze all models, temperature/threshold, candidate rankings **and any deterministic fallback policy** before opening test labels or performing independent one-shot execution. A hash manifest must confirm timing/order of freeze and unseal.

---

## 6. P8d — Independent matched one-shot simulator test

### 6.1 Competing arms and root denominator

Mandatory **six arms** on exactly the same **12 new sealed P8c test roots**:

1. A local-sequence neural scorer.
2. B-full (generic joint coupling).
3. B-structured (scene/omission structured pairs; generic coupling off).
4. S-factorized non-energy scorer.
5. Uniform seeded candidate ranking.
6. **Geometry + complete 3R relocation search (G+M)**.

**Total planned episodes: 72 = 12 roots × 6 arms**, one frozen seed-0 checkpoint per learned arm for one-shot runs. B-none and C must have complete offline tests; execute them **only if authorized P8d compute remains** after the mandatory six, with distinct supplementary labels (never replace an essential baseline). Three-seed **offline** model results remain mandatory; executing just seed 0 must be acknowledged. Use one predeclared ranking namespace per model and a separate deterministic execution seed namespace per episode; no teacher outcome peeking or hindsight filters.

### 6.2 Match the planner and the commitment boundary exactly

For each episode:

1. See **only initial root c0**, target/goal and legal canonical catalogue, same for all arms. Produce a complete ranked list and checkpoint/model hash **before** any verification call or teacher label unseal.
2. Use static checks, then complete per-candidate 3R relocation planning under the **same per-proposal node limits, number of attempts, total CPU/wall and maximum candidate count** for every arm. **Charge the model's scoring/sampling time** separately and in total. G+M cannot obtain a hidden free motion-search budget; it simply uses the common budget for its ranking/search.
3. `COMMIT` the first relocation witness that passes prescribed precommit admission; execute relocation sequence with achieved-state continuity; after commit run target from achieved state **once** and check SAFE_RETREAT. No target-feedback-driven second attempt, changed order or emergency uncharged reranking.
4. If ranked list contains no admissible proposal, record ABSTAIN; if planning exhausts, record NO_WITNESS/UNKNOWN with exact reason; if episode CPU censored, report CENSORED as a failure in primary denominator but separately. No convenient dropping hard roots.
5. For m=0: commit empty repair and attempt target exactly once. It is not automatically successful because a classifier predicted `p0≥τ`.
6. Replay GIFs only from **new episode-recorded trajectories**. Counterfactual scene edits and proposed-but-not-executed candidates must be static/ghost overlays explicitly labelled.

Suggested frozen episode resource: **≤180 process-tree CPU-s/episode**, **≤12,000 aggregate CPU-s**, **≤24,000 wall-s**, one worker, **≤5 ranked repair candidates** attempted before commit and the existing verified target-once boundary. If all 72 cannot complete within aggregate cap, stop at first cap, mark remaining `NOT_RUN`, do not cherry-pick. To minimize root/arm-order bias, interleave arms round-robin per root in a predeclared seeded order, record order and charge shared overhead consistently.

### 6.3 Required outcome reports

Primary: **complete GOAL_AND_SAFE_RETREAT success / all 12 eligible test roots**, including aborts, abstentions, censoring; root-paired comparison of each learner against U and G+M; root-cluster bootstrap 95% uncertainty, exact pairwise success discordance counts, Fisher/McNemar-style tests if valid at n=12 (otherwise N/A). Small n = **pilot-level**, not proof of a population advantage.

Secondary: original-0 false-feasible and unnecessary relocations; number of moved distinct objects; **restricted-catalogue** shortest known verified move count and regret; measured *actual episode* first-witness joint travel for successful and attempted repairs; analytic displacement, first successful rank, motion/planner calls/nodes/CPU/wall, safe-retreat failures, target failures after commit, aborted and censored episodes. Report motion costs **conditional on success separately from all-episode aggregates** to avoid cherry-picked low travel. For G+M baseline, count exactly the same total candidate and oracle time as learned arms.

**Paired-run limitation:** Different arms may choose different repairs; matching seeds does not mean the same stochastic trajectory. The counterfactual comparison is across initial-root pairing and equal budgets, not a claim of identical realized robot paths.

### 6.4 Verdict rules (freeze before unseal)

- `P8D_ENGINEERING_PASS`: complete protocol audit, 72 attempted (or fully documented budget-limited partial), hashes, independent witnessed trajectories where success, no post-commit target retry, full source/status ledger.
- `P8_PRIMARY_LEARNED_ADVANTAGE`: only mark **SUPPORTED** when a learned arm improves *paired* full-episode success over both U and G+M on fresh roots, with a positive, uncertainty-aware interval or clear predeclared practical threshold, and without a hidden resource advantage. With 12 roots this will likely be **INCONCLUSIVE**; never force significant claims.
- `P8_GENERIC_COUPLING_VALUE`: **SUPPORTED** only if full B beats **structured B** (same direct features and supervision) on at least one predeclared scientifically relevant fresh outcome/selection endpoint with materially better root-cluster evidence, without worse primary robot success; otherwise **NOT_SUPPORTED** (or `BLOCKED` if insufficient denominators). `B-full > B-none` alone is insufficient attribution to generic coupling, because `none` also removes structured factors.
- `P8_NO_BENEFIT`: if S, A, B-structured or G+M match/beat B-full on the endpoints that matter within cost, recommend **simplify or retire generic coupling** in the next version. A null finding is a scientific conclusion, not permission to train longer until B wins.

---

## 7. Budget ledger — absolute cumulative hard ceilings

| Work package | Teacher CPU | Other process-tree CPU | Wall | Additional constraints |
|---|---:|---:|---:|---|
| P8 read-only audit + full baseline regression | **0** | **1,200** | 2,400 s | 6 historic replays, no edits |
| P8a controlled models + tests | **0** | **7,000** | 14,000 s | ≥3 seeds for primary arms, stop on cap |
| P8b sampler, selection, strong baseline tests | **0** | **3,000** | 6,000 s | No teacher/model-selected new target execution |
| P8c static construction/admission | **0** | **800** | 1,600 s | No planner in admission |
| P8c new teacher collection | **12,000** | Included in teacher budget | **24,000 s** | 36 roots, 720 queries, 650 CPU/root, 6k CPU/wave, 1 worker |
| P8c fresh A/B/S/C training & evaluations | **0** | **11,000** | 22,000 s | Six priority arms ×3 seeds, fixed updates |
| P8d new one-shot episodes | **0** | **12,000** | 24,000 s | 72 planned, ≤180 CPU/episode, 1 worker |
| P8 PNG/GIF and final reports | **0** | **1,800** | 3,600 s | Reuse recorded witnesses only |

All caps apply to **process-tree CPU**, not the sum of user-facing timers. Include initialization, model load, child planners, sampler scoring and checkpointing, as applicable. Never borrow unused time across work packages or replay old collector outputs as fresh execution. Attempt fewer than the maximum when a gate or budget blocks further work; report planned/attempted/decided/unresolved/NOT_RUN separately. Use historical guard infrastructure, no best-effort unguarded high-cost calls. If a stage cannot finish inside its budget, produce a valid `PARTIAL` report and STOP that stage; never quietly add a seed or another wave.

### Exact stage sequence and commits

- **P8 audit / P8a** → tests and mathematical audit → historical matched learning/coupling verdict → `0024_...md`, report/gate commit if clean.
- **P8b** → calibrated decision funnel, sampler, matching G+M and U/S controls → `0025_...md`, gate commit.
- **P8c** only after both gates → frozen root/split/query manifest; 18-root wave 1 gate; 18-root wave 2 if permitted → `0026_...md` and checkpoint hashes.
- **P8d** only when 36-root pilot collected sufficiently for training and intact sealed test → frozen 18+6+12 splits, ranks, thresholds and baseline decisions; unseal/test/one-shot → `0027_...md` and `P8_DECISION.md`.
- Use one small functional module for each genuinely new responsibility (`p8_audit.py`, `p8_train.py`, `p8_select.py`, `p8_scenes.py`, `p8_run.py`, `p8_viz.py` suggested names only). Reuse `abc7_models`, sampler, guard and robot code. Aim ~120–280 logical lines/file; >300 triggers a responsibility review. Do not build new packages, a UI framework, external services or duplicate motion code.
- Source and model checkpoint/config hashes, root and split hashes, outcome-layout and policy versions, exact CLI commands, return codes, tests and archived replays appear in every stage report. Never rewrite `0022` or `0023` or any archived manifest. Commit explicit paths only and push without force only after passing stage gates. Preserve pre-existing PDF deletions/untracked user files.

---

## 8. Figure/GIF package — show the *reason* behind each result

All GIFs are required **as diagnostics** and must be browsable under `visualizations/p8/README.md`, with `.sha256` sidecars, consistent color/coordinate convention and a source/checkpoint manifest. Generate a compact index HTML **only if it can be built without an external server**; README + direct GIFs are sufficient.

Mandatory figures/GIFs:

1. `factor_graph_modes.png`: factor nodes, outcome nodes and graph edges for `B-full/B-structured/B-none`; distinguish structured pair potentials from generic coupling; show `J` outside feasibility energy. This is a *diagram*, not a claimed learned graph.
2. `coupling_conditionals.gif`: one real decided root with its true signs and predicted unconditional marginals vs **offline** conditional completions when ground-truth evidence bits are explicitly revealed; prominently mark `ORACLE-REVEALED DIAGNOSTIC, NOT AVAILABLE TO ROBOT`.
3. `kappa_signs.gif`: three observed κ groups, teacher tuple `[y0,yA,yB,yAB]` and predictions of every arm, provenance of each negative; no fabricated κ for missing statuses.
4. `loss_gradient_balance.gif`: factor-wise loss and pre/post-clip norms for matched runs with per-arm steps and CPU; classify clipping-limited C honestly.
5. `empty_repair_false_positive.gif`: identical initial scenes where p0 is wrongly high, candidate ranks, committed decisions vs original certified result. Certified failure has a **static status panel** without imaginary motion.
6. `sampler_mixing.gif`: empirical state-histogram/top-k hit vs exact stationary π where available for 4k/16k steps, and deterministic ranking comparisons with charged calls/CPU; do not confuse detailed balance with mixing.
7. `repair_cost_tradeoff.gif`: alternate **verified** repair lengths from recorded teacher witnesses or new one-shot episodes; show measured first-witness J and object displacement, not invented trajectories.
8. `ABC_S_GM_oneshot.gif`: side-by-side **new recorded P8d robot executions** from exactly the chosen candidate and achieved joint states; labels for abstained, target failure, unknown and budget censored. No trajectory when none recorded.
9. `P8_root_decision_funnel.png` and `P8_paired_success.png`: table/plot of candidate availability → admitted proposals → relocation witnesses → post-commit target outcomes, paired across all arms with full denominators.

Never animate hypothetical obstacle teleportation as if the robot moved it. An intervention visualization is a labelled ghost edit. Certified failures and operational failures get distinct statuses. Executable repairs must use real per-step q/gripper/object arrays (and target + SAFE_RETREAT); any interpolation is only between recorded samples for rendering and must not invent novel paths. If an example is unavailable, record `NOT_AVAILABLE` rather than synthesizing evidence.

---

## 9. Stage reports, reproducibility and falsification output

Each report must begin with a one-paragraph **actual result**, machine-readable gate, exact counts, resource usage vs caps and code revision. Include:

- Repo snapshot hashes; conflict ledger between specification and implementation; what changed/what was intentionally retained.
- Root- and query-level frozen plan, ordered seed/query admission decisions, statuses and scoped certificates, `P8c` holdout hash timestamps.
- Outcome-slot map `z0`, `zS[I]`, `zR`, `zO[t]`, active mask; exact `K≤9`; null/aliases/missing.
- Factor graph/gradient audit and `full/structured/none/quadratic` switch proof, plus conditional vs unconditional estimands.
- Complete loss definitions, normalization, gradients, calibration, masks, gradient clips, matched update counts/CPU, seed variance and ablations.
- All results stratified by independent root and by physical mechanism; teacher scopes, missingness and sample sizes.
- Sampler exact stationarity, finite mixing and useful top-k discovery; deterministic fallback cost.
- G+M and all model one-shot selections/relocations/target outcomes, error categories, counts, qualified minimality, cost/compute distribution, complete denominator.
- Display only grounded GIFs/PNGs and link paths in visualization index.
- A final **support matrix**: H-coupling (conditional), H-interaction (unconditional), H-repair-success, H-minimality-within-catalogue, H-vision, H-sampler, H-geometry-baseline. Every claim must be **SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE / BLOCKED**, with a specific measured basis.

### Final decision memo (mandatory even for null result)

Prepare `responses-phases/P8_DECISION.md` of **at most three pages of dense Markdown** answering:

1. Do we have evidence generic B/C coupling helps **beyond** scene/omission structured factors and feature-matched independent predictors?
2. Is the more complex EBM justified over A, S and G+M by complete one-shot repair success under matched resources?
3. Is the Boltzmann search actually useful at bounded runtime, or should we use deterministic scoring/ranking?
4. Can we substantiate least-required displacement **within a declared finite candidate set**, and what remains unresolved about different possible grasps/paths?
5. Which single architecture should carry forward to **further 2D evaluation** (not automatic 3D), and what precisely would falsify that choice?
6. If none is compelling, name the simplest supported baseline (possibly G+M, S or A), clearly distinguish operational negative evidence and propose the **smallest** next experiment—not another 48-root collection.

**Hard STOP after P8.** No G5/G6 authorization, 3D, real robot/hardware, change in teacher policy, silent new architectures or unconstrained data scaling. If a mandatory gate blocks P8c, deliver the P8a/b results and a complete decision memo explaining that fresh claims remain untested. No fake completed stage or promised later work.
