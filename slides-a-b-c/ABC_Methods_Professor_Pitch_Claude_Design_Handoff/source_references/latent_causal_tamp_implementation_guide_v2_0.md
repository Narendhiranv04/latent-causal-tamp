---
title: "Latent Causal TAMP"
subtitle: "Implementation & experimental guide v2.0 | post-P8 unified joint Boltzmann learning, minimal code and factor ablations"
author: "Stage-gated implementation contract"
date: "22 October 2026"
lang: en-US
toc: true
numbersections: true
---

> **STATUS: PROPOSED IMPLEMENTATION PLAN—NO CODE OR DATA MODIFIED.** Companion to **Methodology v1.8**. It supersedes Guide **v1.9 for future work** and updates the old G4D-era plan to the *actual completed* P8 baseline. Historical P4–P8 data, results, six archived replays, checkpoints and stage IDs must not be changed. Reported repository: `Narendhiranv04/latent-causal-tamp` at **`f9a6de0`**; new code should be versioned alongside working P8 modules and only applied after an explicit implementation handoff. No automatic teacher collection, large-scale training, 3D or hardware action is authorized by these documentation changes.

> **One-sentence goal.** Implement a clean B/C **factor-graph Boltzmann outcome model** trained primarily with **one masked joint observed-data NLL**, retaining **only necessary** static placement supervision and first-witness travel supervision; test the mathematical semantics and then determine whether each named factor helps on genuine physical infeasibility mechanisms. Keep A, factorized SF, and G+M as mandatory comparators. **Do not force a positive result.**

# 1. What changed since v1.9 and P8

| Item | v1.9 / implemented P8 | v2.0 forward contract |
|:--|:--|:--|
| Status | G4D evidence still blocked in historical guide | **P8 completed**; do not re-run old gates or falsely reset research history |
| A/B/C | A local GRU, B explicit joint outcomes and prefix interactions, C B+GRU | **Same three architecture questions** |
| Five factor families | Static / sequence / scene / omission / coupling | **Same five** with precise variable-node scopes and boundaries |
| Training | Static, task, scene, omission, effect, cost, finite-pool losses; some redundant | Proposed **primary root-level joint evidence NLL** + static BCE + witnessed J regression; optionally separately predeclared selection term |
| Model probability | Exact root scene P_S and conditional repair P_Q in `abc7_models.py` | Keep root consistency; carefully **avoid double-counted root labels and reused query outcomes** |
| Repair score | E_static + T softplus(-logit pR), lexicographic ranking | Explicitly **success-conditioned** candidate score; no claim P(z|r) alone selects repairs |
| Search | P8 switched from mixing-poor sampler to deterministic scoring | **Retain deterministic enumeration** for bounded pools; Boltzmann model need not imply MCMC |
| Evidence | P8 G+M 9/12, B-full 8/12 on same-constructor roots | G+M is strong baseline; independent mechanism test needed for an advantage |
| Tests | Matched full/structured/none; P8 order contrasts absent | Actual **single-factor removals, order-swap fixtures, capacity controls**, and fresh root splits |

**Non-goals:** no new task definition, no learning IK/continuous trajectories, no generative image model, no physical interaction discovery from factor weights, no new causal DAG discovery, no invented proof certificates, no claim of generalization to 3D. The proposed simplified loss is **not yet evaluated** and does not retroactively describe P8's training.

# 2. Source-of-truth and keep-the-code-small rule

Read the actual repo first, then compare to the known `f9a6de0` baseline. Important existing modules and concepts (names verified in prior GitHub review, but inspect the live code before editing):

| Existing file | Role / protection |
|:--|:--|
| `abc_models.py` | Shared geometry, DINOv2 object tokens, local static head and original model behavior; preserve |
| `abc7_models.py` | `ABC7_V1` A/B/C, chain-normalized scene/repair model and four coupling modes; **preserve P8 checkpoint compatibility** |
| `abc8.py` | P8 comparator arm builder, SF, κ sampler and sparse auxiliary masks; preserve |
| `abc7_train.py`, `p8_train.py`, `p8c_train.py` | P8 multi-term training, checkpointing and frozen-ranking behavior; preserve for exact replay |
| `p8_eval.py`, `p8_select.py`, `p8d_run.py` | Matched diagnostics, learned selection and G+M baselines; preserve for comparisons |
| `p8_learn.py`, `p7_learn.py`, `learn_data.py` | Frozen DINOv2 appearance and allowlisted original geometry, label/mask views; keep strict split/source tags |
| `ordered.py`, `p7_oneshot.py`, `sequences.py`, `operational_teacher.py` | **Actual full 3R motion, target one-shot boundary, exact order, evidence scopes**—no change to teacher policy |
| `p8_scenes.py`, `p8_collect.py` | Root constructors/collection controls and legacy P8 data; do not overwrite |

**Repository policy.** Keep the existing root-level minimal architecture; add **at most two or three focused new Python modules plus one test file** for the likelihood/refactor (`joint_likelihood.py`, `abc9_joint.py` if unavoidable, `p9_joint_run.py` only when needed). Prefer extending proven utilities rather than a new nested package tree, a database or copied teacher implementation. Ideal Python module length ~120–280 logical lines; >300 should prompt responsibility review. New documentation belongs in `instruction-phase-md/` if used as an implementation instruction, and numbered results in the existing `responses-phases/` reports scheme. Do not rename or overwrite the actual historical P8 evidence.

**Minimal new version marker:** `ABC9_JOINTNLL_V1`, with migration map `ABC7_V1` → `ABC9_JOINTNLL_V1`. If the new model changes node equality/layout or observation likelihood semantics, **old checkpoint parameter/state compatibility is not presumed**. Persist every new architecture, loss, variable-layout and conditional-normalization version in model artifacts. Train from scratch for fair comparison; do not silently warm-start one arm from an advantaged P8 checkpoint.

# 3. Shared physical robot/data interface: unchanged

**Initial scene:** 2D articulated fixed-base 3R robot, known 8×8 support grid (0.08 m pitch), identical 0.024 m radius discs with validated clearance defaults, tested joint limits and 48 grasp candidates, full fingers/links/attached body, real continuous collision checked motion. Keep exact versioned profile/config and achievement-state replay. The one-shot target includes SAFE_RETREAT, not just reaching the goal. No stationary/teleported object animation counts as execution.

**Repair proposal:** canonical list `[(object_id, legal_destination_id), ...]`, max four distinct mover IDs, original active target excluded. `[]` is an empty repair. Candidate identity includes order and destinations. Displacement and number of unique objects computed exactly, no learned substitute.

**Initial learner inputs (allowlist):** original RGB/GT masks or cached DINOv2 per-object features, known numeric object XY/radius/support and target indicators, original robot `q0`/FK/finger state, goal and candidate ordered high-level sequence. After declared hypothetical edit, recompute only the **specified object geometry/edit channels**; appearance anchor remains from root. Complete teacher trajectories, future joint states, success bits, teacher seeds, root family and privileged geometric oracle distances must never reach `forward()` at inference.

**Teacher record must preserve** `query_id`, `root_id`, fixed robot/anchor hash, canonical action signature, provenance, exact VERIFIED/CERTIFIED/BUDGET_INFEASIBLE/UNKNOWN/NOT_RUN source, proof scope if certified, unit attempts, plan/relocation/target status, and first complete relocation-witness J if present. BUDGET negative is usable as a policy-relative label *only* under `2D-ABC-OPNEG-v1`, with proof-grounded and operational metrics separated. UNKNOWN/NOT_RUN are **never** training zeroes.

# 4. Implement the real factor graph (not just a five-box picture)

## 4.1 Nodes and factor-instance map

**Observed conditioning inputs:** \(c_0\), proposed repair \(r\), canonical scene-edit IDs/destinations and omission definitions. The *random variable circles* are:

- **Root-scoped scene circles:** `z0`, `zS[A]`, `zS[B]`, `zS[A+B]`, and other eligible predeclared edit outcomes.
- **Repair-scoped circles:** `zR[r]` for complete physical repair and `zO[r,t]` for an omitted-action query.

Each circle takes **0 or 1**. Their probabilities come from the **joint Boltzmann distribution**, not extra sigmoid heads acting as a second source of truth. In P8, `z0` and the zero-move `zR` describe the same physical task; treat identity explicitly as a consistency/equality constraint or canonical alias. The same physical omission query reused as another full candidate also denotes the **same factual outcome**, not an independent Bernoulli draw. If this equality cannot be enforced by a small exact implementation, record the limitation and use a properly named **composite** likelihood rather than claiming exact root likelihood.

| Factor family | What the corresponding rectangles touch | Shared feature inputs / learned parameters |
|:--|:--|:--|
| **F1 Static** \(U_i,V_{ij}\) | **Deterministic endpoint object descriptors**, not random z variables | Shared object-local and symmetric pair MLPs; scored once per candidate placement; separately supervised |
| **F2 Sequence** \(\phi_{\rm seq}\) | Unary potential on \(z_R\) conditioned on ordered \(r\) | B: prefix-predecessor MLP; C: GRU over all-object ideal-prefix features |
| **F3 Scene** \(\phi_{\rm scene}\) | Unary on `z0`, `zS[I]`; structured pair `z0`—`zS[I]` | Original/edited geometric tokens, fixed original robot and shared scene features |
| **F4 Omission** \(\phi_{\rm omit}\) | Unary on `zO[r,t]`; structured pair `zR`—`zO[r,t]` | **Newly rebuilt** omitted ordered sequence and full-repair summary |
| **F5 Coupling** \(\phi_{\rm couple}\) | Additional scene-scene, scene-repair, eligible repair-omission or higher-order factors | Same context, typed slot embeddings, no teacher labels during inference |

**Do not confuse these:** static endpoint constraints versus target-only outcome after a hypothetical scene edit; a full physical repair versus a static scene edit; omission feasibility versus exact move count; joint coupling versus a true causal arrow. Coupling must have a properly named `full / quadratic / structured / none` switch—`full` vs `structured` isolates generic coupling, `structured` vs `none` isolates explicit structured pairs, `full` vs `quadratic` isolates higher-order residuals.

## 4.2 Conditional probability blocks

The **supported P7/P8 architecture** already models

\[
P_\theta(z\mid r,c_0)=P^S_\theta(z_S\mid c_0)P^Q_\theta(z_Q\mid z_S,r,c_0).
\]

Maintain root-scoped P_S: same `scene_block` for **every** repair; `scene↔repair` coupling may change P_Q but **cannot change unconditional P_S**. `z` is binary, but returned marginals are continuous probabilities. Factor weights are shared across scenes. The normalizers must use the actual active slots only; for nine active binary fields enumerate 512 assignments with stable `logsumexp`. Reject accidental dense masks with out-of-budget \(2^K\). Every absent/ineligible edit removes a variable rather than assigning its outcome to zero.

**B:** no recurrent GRU; pair/predecessor interaction for sequence order. **C:** replace that sequence encoder with a single GRU (do not simply add GRU to B's order score). **A:** local static + GRU repair logit, no explicit joint z graph. **SF:** independent-outcome sigmoid control using matched scene/repair features and equal label access.

## 4.3 Output APIs and invariants

Keep one small interface, without duplicating entire frameworks:

```python
# Pseudocode / API semantics, not a drop-in patch
scene_block(root, scene_catalogue) -> {
    'scene_slots': ..., 'log_p_scene_states': ..., 'root_hash': ...}
repair_block(root, candidate, z_scene_state) -> {
    'repair_slots': ..., 'log_p_repair_states_given_scene': ...}
observed_root_log_prob(root, observations) -> scalar
marginals(root, candidate, catalogues) -> {
    'p_original': ..., 'p_scene': {...}, 'p_repair': ..., 'p_omission': {...}}
rank_energy(root, candidate, reference_measure) -> scalar
predict_joint_travel(root, candidate) -> nonnegative_float
```

Mandatory invariants:

1. `sum_z exp(logP) = 1` (absolute error ≤ 1e-10 in float64) for every active layout; root-scoped scene marginals identical across repair proposals (≤ 1e-10).
2. No gradient from UNKNOWN, NOT_RUN, ineligible or inapplicable labels; no future oracle information in inference tensors.
3. Permuting object storage order with the same physical signature changes no probability beyond numerical tolerance; changing **action** order may change predicted repair success.
4. Scene A/B/A+B effects use fixed original robot q0 and unchanged appearance anchor. **Omission** removes an action from every rebuilt prefix, not an object from the world.
5. `p_repair([]) == p_original` by construction/canonical event equivalence, within numeric tolerance; no model is permitted to learn mutually incompatible guesses for an identical physical query.
6. Duplicate equivalent full/omitted query IDs are hashed canonically, with labels and evidence scopes matched; contradictory claimed labels are a hard data-integrity failure until adjudicated, not training noise.
7. Constant-energy offsets must cancel from conditional outcome probabilities; an r-only static penalty must not produce a gradient from conditional z-NLL (proof test).
8. Missing active slots do not enlarge partition mass. Add/remove masked dummy z and check all probabilities identical.
9. Joint log probability and all relevant derivatives agree with brute-force enumeration/finite-difference checks on tiny labelled roots.

# 5. The learning objective — simpler *and* mathematically correct

## 5.1 What the 'one primary loss' really means

P8 used up to seven named training terms (`static`, `task`, `scene`, `omit`, `effect`, `cost`, `pool`). **The proposal is to replace the redundant outcome-supervision terms with a *single* primary jointly normalized observed-data likelihood**, while keeping genuinely necessary local targets. There is no rule that five factor families must have five individual losses: all B/C outcome factors get gradients via the **same log probability of observed outcome combinations**.

For root \(c\), define a root scene distribution `logPS[zS]`, and each candidate's repair-conditional `logPQ_r[zS,zQr]`. An observed true/false label restricts its corresponding z dimension; missing observations impose **no restriction**. The exact rootwise evidence is:

\[
\mathcal L_{\rm obs}(c)=-\log\sum_{z_S\text{ consistent with root scene observations}}P_S(z_S)
\prod_{r\in\mathcal C_c}\left[\sum_{z_{Q,r}\text{ consistent with observed repair/omission bits}}P_{Q,r}(z_{Q,r}\mid z_S,r)\right].
\]

This **single root-level negative log probability** handles correlated bits and marginalizes missing labels. It assumes conditional independence of **distinct candidate repair outcome vectors given the shared scene outcomes**. That assumption and duplicate-label handling must be explicitly documented and stress-tested. If repeated physical queries require equality constraints across candidates, either implement their **exact shared-event graph** on tiny domains and a verified scalable algorithm, or fall back to a **de-duplicated composite conditional NLL** with that name. Do not call the latter exact full maximum likelihood. By normalizing/averaging per independent root (not per 512-state joint assignment), large catalogues don't automatically dominate the run.

### Concrete pseudocode for the nonduplicated exact-root case

```python
# PSEUDOCODE: stable double precision; logits/normalizers live on graph
logP_S = model.scene_log_probs(root)  # tensor [2**K_scene]
root_mask = matches(root_observed_scene_bits, scene_assignments)
log_terms = logP_S + where(root_mask, 0.0, -inf)
for repair in root.canonical_repairs:
    logP_Q = model.repair_log_probs(root, repair, scene_assignments)
    # shape [2**K_scene, 2**K_repair], already conditionally normalized
    q_mask = matches(repair.observed_outcome_bits, repair_assignments)
    log_repair_evidence_per_scene = logsumexp(
        where(q_mask, logP_Q, -inf), axis='z_repair')
    log_terms += log_repair_evidence_per_scene
log_likelihood_root = logsumexp(log_terms, axis='z_scene')
loss_joint = mean(-log_likelihood_root for root in minibatch)
```

**Critical safeguards:** no duplicated `z0` observation through an empty repair's `zR` instance; no duplicate `zO` labels charged as independent replicas of another full repair; never require full teacher completion to use partial supervision; never condition deployment on the *observed* scene/repair outcomes. The root query catalogue must be frozen outcome-blind before labels.

## 5.2 The two necessary auxiliaries

**A) Static endpoint label BCE.** Unary/pair static energies depend on proposed coordinates \(r\), not on the outcome configuration z. Therefore they **cancel from \(P(z\mid r,c_0)\)**. Without a dedicated static loss (or a newly designed, explicitly normalized model over repair and validity variables) they receive **no task likelihood gradient**. Train from separately generated analytic support/overlap labels, masked where undecided. If using a hard analytic static screen instead of a learned static energy, label the architecture change and compare fairly.

**B) First-witness joint travel.** Train \(\hat J_\theta(r)\) only if a **complete relocation witness** and an actual unwrapped normalized joint-travel measure exist. No witness → cost label unavailable; never fit J to a candidate's endpoint distance or substitute zero for failed motion. Use \(\log(1+J)\) Huber or a simple declared probabilistic travel likelihood. Define \(\hat J(\varnothing)=0\) exactly.

**Recommended default loss:**

\[
\boxed{\mathcal L=\mathcal L_{\rm joint}^{\rm observed}+\lambda_s\mathcal L_{\rm static}+\lambda_J\mathcal L_{\rm travel}.}
\]

This is **one main outcome-learning loss plus two justified supporting losses**, not five arbitrarily weighted feasibility terms. Do not oversell it as literally one scalar probabilistic training objective for all quantities. Optionally define a predeclared \(\mathcal L_{\rm select}\) for a finite-catalogue selection distribution, but only after proving what observed selection event and teacher sampling policy it corresponds to; compare with/without on validation. Do not automatically add task BCE, scene BCE, omission BCE, effect MSE, κ MSE and pool CE back on top of the primary exact NLL.

## 5.3 Example gradient path (explainability)

Suppose original task fails, individual scene edits A and B fail, edit A+B succeeds, and physical `B→A` repair succeeds. We input only scene/repair descriptions; the *teacher outcome bits* appear **only in likelihood masks**. The model evaluates energies of every admissible scene/repair outcome combination. Log probabilities favoring the wrong combinations incur a higher joint NLL; backpropagation updates shared scene unaries, scene pairs, generic within-scene coupling, sequence factors, repair/scene coupling and omission factors **when those factors influence the observed likelihood**. Because the scene block is root-shared, repeated repairs cannot manufacture multiple observations of `zS[A+B]`.

The model learns **parameterized energy functions** from many roots; it does *not* optimize object destinations with gradient descent. Destination and order are high-level **candidate inputs**; learning adjusts neural weights. At inference, the same weights score unseen candidates. The independent planner handles trajectories and decisions about whether any candidate truly works.

## 5.4 Calibrate, optimize and evaluate fairly

- Default energy temperature for likelihood should be fixed/scoped (e.g. T=1 for learning) unless independently identifiable; tune calibration temperature on development/validation only. Do not compare raw energy magnitudes across differently normalized models.
- Test gradients for every factor, including the sign of BCE for success/failure, appropriate negative/positive logits, all joint factor paths and root marginalization. Report gradient norms, clipping fractions and active observed event counts per root. P8's B-structured and B-none clipping fractions were very high; improve optimizer stability **before** treating full/structured capacity differences as causal evidence.
- Use matched training roots, source/provenance, batch order, optimizer steps, validation selection, seeds and available evidence masks for B/C/SF/A. If model variants have different capacity, add width-matched controls or state the confound. Keep P8 checkpoints frozen for baseline comparison only.
- Compare **legacy P8 multi-loss** versus **new NLL** as a controlled *training-objective* experiment, not a claimed architecture win. P8 test has been disclosed, so treat it as development/legacy; future fresh test must be constructed separately.

# 6. Exact scene changes, omission and order learning: test fixtures

These are **required test questions**, not outcomes to hard-code. Each requires a complete articulated robot scene, eligible query and correct evidence scope. Do not generate desired outcome labels from constructor intent; use teacher status and keep failures/censoring in denominator.

| Fixture | Mechanism; expected diagnostic if constructible | Required evidence / visual |
|:--|:--|:--|
| F0 original feasible | No relocation needed; learner should not invent work | Original target witness, SAFE_RETREAT, move count zero, false-empty controls |
| F1 unary static-invalid | Unsupported/off-workspace destination | Static unary analytic label and learned response |
| F2 pair static-invalid | Individually supported objects overlap at endpoints | Static pair label; omit-pair ablation |
| F3 static-valid/target-blocked | Valid object placements but target grasp/path still blocked | Fixed q0 target-only labels; scene vs static contrast |
| F4 complementary A/B | Each eligible edit alone fails; combined edit succeeds | Four independent target-only labels and status scopes; κ=+1 only when all decided |
| F5 redundant A/B | Either edit alone restores task; joint does too | All four labels; κ=-1 only when valid |
| F6 nuisance/zero | Moving irrelevant object has no measured effect | All four labels; false-positive explanations |
| F7 order swap | Identical final object poses; `A→B` differs from `B→A` | Full witness vs sound order-negative or separately marked policy-relative contrast |
| F8 three-/four-move | Prefix dependence not derivable from final static overlap alone | Real articulated relocation+target witnesses and attempted alternatives |
| F9 omission | Full repair succeeds; an independently evaluated omission removes one action | Reconstructed prefixes and new full teacher query; do not infer from existing trajectory |
| F10 alternative destination | Different placement of mover changes whether another mover is needed | Verified shorter/longer candidates; restricted-catalogue minimality |
| F11 robot-start variation | Same objects/target/goal, different q0 changes access/order | Same-endpoint, fixed q0 per paired comparison; independently decided labels |
| F12 motion-only failure | Static/pose screens admit but joint path or carry conflicts | Proof/witness/operational status; no forged global negative |
| F13 joint-travel inversion | Small endpoint displacement produces longer robot travel than alternative | Two recorded **first relocation witnesses**, measured J |

**Construction independence:** P7 and P8 roots share screen-based construction motifs with G+M. For future scientific test build **a genuinely different constructor family**, audit novelty of physical mechanism and root hashes, and include originally feasible roots. New construction cannot be defined by a hidden teacher success outcome. Candidate pools must contain genuinely competing repairs, not only a predetermined successful `main` sequence. Missing tests are **BLOCKED**, not fabricated positives/negatives.

# 7. Stage gates — minimal work before expensive teacher collection

Do **not** interpret these named stages as authorization to run them now. They are a progression for a later Opus implementation handoff after this report is approved. Each stage produces a machine-readable gate, a human-readable numbered report and a small set of figures or real-motion GIFs. Do not resume obsolete G4D or automatically start old G5/G6 numbers. Prefix new tasks under an **explicit new P9/M-series label** so archived reporting stays unambiguous.

## Gate L0 — Nonmutating repository audit

- Verify actual HEAD/working tree/remote and all relevant P8 report hashes; record current relevant Python module locations, file lengths, test suite, six archived replay hashes and model/checkpoint/config versions.
- Trace `z0`, `zR([])`, omission query IDs, root-scoped scene blocks, current P8 loss and G+M ranking. Detect where physically identical outcomes may appear twice in likelihood factors.
- Verify DINOv2 actually contributes image-derived features to the learner (P8 report's wording calling it wholly symbolic should not be carried forward untested); plan a geometry-only feature ablation.
- Produce `L0_audit.md` and code/graph mapping. **No modifications** until this audit passes.

## Gate L1 — Mathematical/unit-level prototype (zero teacher calls)

1. Implement only the root log-likelihood evaluator, tiny toy root fixtures and an optional versioned model wrapper if essential. Preserve P8 modules intact.
2. Enumerate no more than small root-level scene bits and bounded repairs with explicit equality tests for repeated `z0`/empty and duplicated omission queries.
3. Compare numerical log-likelihood, exact marginals, d/dθ derivatives, finite difference and brute force enumerated joint outcomes. Validate across mixtures of observed, operational, certified and fully missing masks.
4. Test **static cancellation**: adding arbitrary repair-only `E_static` cannot change `P(z|r)` or generate conditional-likelihood gradient. Separately prove static BCE does provide gradient.
5. Test order-permutation sensitivity in representation, scene consistency across r, `zR([])=z0`, optional within-scene pair/HO scopes and inactive-slot invariance.
6. Demonstrate no observed outcome, teacher trajectory or status accidentally appears in model forward input. Fake/test data only, not teacher.
7. Bench root log-evidence for actual bounded P8 pool sizes; abort instead of scaling beyond a declared practical time/memory limit.

**Gate L1 PASS:** exact math and invariants, all source/P8 tests still passing, no new teacher calls, fixed model/noised inputs produce reproducible results. **FAIL/STOP** on duplicate-outcome inconsistency, leakage, false exact-likelihood claim, partition or gradient mismatch. If an exact root-level equality-aware graph is too large, implement explicitly named *de-duplicated composite likelihood* and run a tiny experiment to quantify its difference; do not silently claim equivalence.

## Gate L2 — Matched saved-data optimization experiment (zero new teacher)

- Freeze all historical P4–P8 data. P8 test outcomes are **already disclosed**: this is development-stage training and mathematical diagnosis, never a new sealed test.
- Compare **P8 legacy trainer**, new `joint NLL + static BCE + J` trainer, **B-structured**, **B-quadratic**, **B-full**, **C-full**, **A** and **SF** where feasible; hold input features, binary supervision, root partition, optimizer updates, seeds and inference policy constant. Three seeds per mandatory arm if budget permits; declare numeric compute budget *before running*, otherwise no expensive training.
- Verify loss contributions by factor with freezing/gradient intervention; never claim static updates from pure conditional NLL.
- Report per-root calibration, conditional NLL, κ signs with status source, omission metrics, order contrasts N/A where absent, clipping percentages, runtime and rank outcome. Keep `full` vs `structured` and `quadratic` vs `full` truly separate.
- Compare optional learned static BCE with deterministic analytic screens; preserve sound analytic admissibility in all policy arms.

**Gate L2 PASS:** outcomes trained with one primary mathematical objective, no worse-than-legacy correctness or reproducibility, factor gradients audit, finite CPU, no original P8 regression. **Scientific acceptance separate:** no compelled gain from simplification or coupling.

## Gate L3 — Factor-necessity development ablations (new roots only if explicitly authorized)

Plan an outcome-blind, budgeted independent scene set satisfying F0–F13 coverage, especially **order contrasts absent in P8**, independently decided +/0/- interaction signs, and multiple physically executable alternatives. Split by immutable **reference root before descendants**, preserve construction attempts including failed ones, and preregister all teacher budgets (per query/root/aggregate/wall) and operational policy. Sample sizes and caps are not fabricated by this guide; the user must authorize them in the actual handoff.

**Ablation matrix, minimum:**

| Arm / factor change | What actually gets removed | Evaluation proof needed |
|:--|:--|:--|
| B-full | All allowed factors | Reference B model |
| B-quadratic | Higher-order coupling only | Is HO residual necessary? |
| B-structured | Generic coupling only | Is **generic** outcome dependence valuable? |
| B-none | Both generic and structured pairs | Are structured outcome edges useful at all? |
| B-no-static-unary, B-no-static-pair | One local endpoint family | Static unary/pair errors and effect on executed outcome |
| B-no-order / C-order-invariant | Prefix interaction/GRU order signal | **Decided same endpoints, different orders** |
| B-no-scene-unary, B-no-scene-structured-pair | Separate scene components | Edited target-only outcomes, \(\kappa\) and calibration |
| B-no-omission-unary, B-no-omission-structured-pair | Separate omission components | Full-vs-omission decision and extra moves |
| A, SF, C-full | Reference comparators | Capacity, data, compute, same candidate catalogue |
| G+M, U, optional G+M+learned re-ranker | Nonlearned and hybrid controls | Paired one-shot success, compute, minimum moves |

**Do not mislabel factor deletion:** different parameter count can cause performance change; match widths or at minimum report the confound. Retrain ablated arms under equal root-level supervision and epochs; a no-retrain inference lesion is useful only as an explanatory diagnostic. Ablation may find a factor **redundant**; a rigorous negative result is allowed.

## Gate L4 — One-shot independent execution (requires separate approval)

On untouched constructor-disjoint test roots, freeze calibrated checkpoints, loss hyperparameters, thresholds, candidate pools, ranking and per-arm seeds **before reading any test outcomes**. Same top-k candidate limit and complete relocation planner/backend/48-grasp family, per-episode/aggregate CPU, robotic safety policy and single postcommit target attempt across arms. **Charge learned scoring and predictor calls**, not only motion search. Include originally feasible targets, difficult scene-order roots and multiple-destination alternatives. Compare G+M, model B-full, B-quadratic/C if justified, A/SF and hybrid G+M+risk-score; same exact static certificate veto for all arms.

**Primary results:** success with goal+safe retreat over **all** eligible episodes; verified minimal mover count *within a declared, coverage-reported teacher catalogue*; false empty commits and unnecessary moves on feasible originals; robot joint travel J and analytic displacement C_d; model/teacher/planner calls, CPU/wall, abstention/censoring; paired differences and root-cluster intervals. If not enough evaluable roots are obtained, report N/A or BLOCKED, not a synthetic significant p-value. Never infer global optimality from a nonexhaustive candidate pool.

# 8. Inference and repair selection — exact intended production pathway

```text
S0 := original observed 3R state, robot q0 and object positions
C  := bounded, frozen ordered-move candidate catalogue (including [])
Q  := predeclared eligible, fixed-robot hypothetical scene edits
for each r in C:
    reject/record sound statically inadmissible r via shared analytic checks
    compute shared root scene Boltzmann distribution P_S(zS | S0)
    compute repair/omission conditional P_Q(zQ | zS, r, S0)
    marginalize z to obtain p_R(r) and predicted explanation marginals
    compute E_rank(r) = E_static(r) - T log p_R(r) [uniform reference]
    compute exact move count m(r), analytic displacement C_d(r), separate predicted J_hat(r)
freeze candidate ranking before any target evaluation
for candidate in frozen top-K:
    plan complete fixed-order relocation with actual 3R robot
    if no relocation witness: continue if within agreed uncommitted search budget
    COMMIT relocation witness and chosen high-level order
    execute, carry achieved robot/objects/gripper state and reobserve every move
    if execution deviates: abort; never claim target result
    attempt target GOAL_AND_SAFE_RETREAT exactly once from achieved state
    stop, record witnessed success or scoped failure; no post-target replan
if no admissible candidate: record ABSTAIN/UNRESOLVED (count in denominator)
```

**Important policy choices:** the P8 historical lexicographic ranking among sufficiently confident candidates remains a frozen comparator: `m → J_hat → C_d → E_rank → stable ID`. Changing to probability-first or risk-aware ranking is a **separate policy ablation**, not evidence that adding a coupling factor helped. A sound static/target certificate may veto a candidate, but no learned marginal is a physical certificate. A diagnostic hypothetical scene edit cannot serve as the executed relocation witness. If the scene edit says the target is now reachable but the robot cannot carry the blocker to that pose, the repair can still be physically infeasible.

# 9. Figure and GIF requirements (every scientific gate)

Keep readable, concise, data-grounded visual evidence. Avoid a large dashboard framework. Save in existing `visualizations/...` conventions with SHA-256 inventory and exact source/data/model revision pointers. Required:

1. **Real factor graph** with circles for z stochastic variables, rectangles for learned factor instances, dashed arrows for observed context and candidate r; separately show endpoint-static factors and repair-cost calculation. Provide versions `full`, `quadratic`, `structured`, `none`.
2. **Outcome probability plot:** table/panel for \(p_0\), \(p_A\), \(p_B\), \(p_{AB}\), \(p_R\), \(p_{O,t}\); observed labels only where evidence decided, indicate source and uncertainty. Joint distribution is not simply independent marginal heads.
3. **Hypothetical edits:** identical original robot q0, fixed original appearance anchor; 0/A/B/A+B; clearly mark **SCENE EDIT / NOT PHYSICAL REPAIR**.
4. **Order and omission:** same endpoint orders and independently evaluated omitted action with actual status. If no motion witness exists, display `NO TRACE`, never draw a plausible animation.
5. **Loss proof:** main observed-root joint NLL; static BCE; witnessed-J regression; gradient norms, clipping, masked bit counts; compare old seven-term P8 training without concealing differences.
6. **Energy and ranking:** finite candidate \(p_R\), static \(E_{\rm static}\), success-conditioned \(E_{\rm rank}\), move count, analytic \(C_d\), predicted/observed J if available; avoid cross-model raw energy comparisons without common temperature/normalization.
7. **Robot 3R motion GIF:** actual stored FK/trajectory/gripper/object array from executed repair, achieved states and target SAFE_RETREAT, exact arm body and attachments, same camera/axis limits. Include synchronized G+M/learned variants only for paired actual episodes.
8. **Failure-source funnel:** wrong original-task prediction, false-empty, precommit no relocation witness, abort, postcommit target failure, policy budget censoring, true success. Distinguish proof and policy-relative negative.

Each figure must have a manifest mapping candidate, root, model seed, inference threshold, source status and SHA. Each stage report includes links, numerical denominators, untested/unknown caveats and stop decision.

# 10. Automated tests — must precede claims

**Mathematical:** exact enumeration on ≤ 3 root scene bits, variable layouts through nine bits; normalization of P_S and P_Q separately; scene consistency across all r; conditional NLL and derivative finite-difference equality; analytically proved static cancellation; correct cost gradient; fixed root scene bits not multiplied by candidate count; duplicate query equality and no zero-move mismatch; all-missing yields zero loss; logsumexp stable under extreme energies; no K-padding probability leak; temperature and gauge invariance where appropriate.

**Physical:** 3R link/gripper/attached-body collisions; no teleport execution; fixed 48 grasps; no rehoming; true initial q0 for intervention; scene edit unchanged anchor; omitted object physically retained in every prefix; exact action order; first relocation-witness J; no target invocation before complete committed execution; at most one target call; abort on achieved-state mismatch. If robot profile or certificate hash differs, fail closed.

**Scientific:** same candidate catalogue and root split across arms, calibration from validation only, no teacher outcome labels to `model.forward`, crossoutcome conditioning oracle labels excluded at deployment, masks for UNKNOWN/NOT_RUN, certified versus operational provenance, root-stratified no leakage, re-run legacy P8 full tests and archived replays. Test smoke on both originally feasible and certified-infeasible starting tasks.

**Optimization:** zero gradients where masks absent, nonzero learnable scene/omission/coupling gradients on constructed complete counterfactual fixtures, no unbounded clipping, deterministic train seed replay, checkpoint manifest/config hashes, no unseen test re-use for threshold choices. Compare \(P(z_R=1)\) from full enumeration and direct aggregation, no independent conflicting sigmoid head in B/C.

# 11. Decision and publication claims

A/B/C hypotheses remain; B/C are legitimate **joint conditional energy-based graphical models** whether or not MCMC search is used. **Novelty does not come from the mere count of energy factors or use of factor graphs**, but from demonstrated transfer of intervention/order/omission relationships to **physically executable, minimal corrective rearrangement decisions**. Factor-graph edges are statistical, not automatically causal DAG edges. A factor's physical interpretation does not mean its learned parameters are separately identifiable, and a higher accuracy alone does not prove it was needed.

If G+M remains best in matched fresh one-shot repair success and minimum moves, report that. If B/C help only a small residual class, specify it and quantify paired benefit/compute. If SF matches B, simplify. If coupling helps intervention NLL but harms hidden conditional completion or is unstable under sparse auxiliary labels, retain it as a research hypothesis only. Do not call an operational-budget negative a logical infeasibility proof. No transition to 3D/hardware before a separately authorized and adequately powered independent 2D result.

# 12. Change log and handoff checklist

**v1.9 → v2.0:** removes obsolete 'current G4D only' progress framing; records reported P8 baseline; clarifies literal factor-graph nodes and five parameter-shared factor families; documents root-consistent P_S/P_Q normalization and a repair-success-conditioned ranking measure; corrects static-energy cancellation; replaces multiple duplicated outcome losses with a **proposed primary masked joint evidence NLL**, plus separately required static BCE and relocation-travel supervision; mandates equality-safe repeated-query handling; distinguishes omission learning from move count; adds targeted per-factor capacity-matched removal tests, DINOv2 feature/geometry controls and constructor-disjoint physical order contrasts; keeps deterministic ranking as the baseline after P8 poor sampler mixing; preserves all teacher protocol/safe-retreat/evidence status protections.

**Handoff acceptance checklist:**

- [ ] Read Methodology **v1.8** and this Guide **v2.0**, plus P8 reports 0024–0027 and `P8_DECISION.md`.
- [ ] Audit clean repo and all existing P8 tests/hashes, no unnecessary folders/refactors.
- [ ] Implement **L1 exact math/equality/leakage tests first**, no teacher calls.
- [ ] Authorize and gate any L2 compute **before** training, record explicit new model version.
- [ ] Keep A/B/C, SF and G+M controls fair; do not force all five factors to show benefit.
- [ ] **Stop** before L3/L4 teacher collection/one-shot execution without explicit new experimental budget approval.
- [ ] Report scientific PASS/NOT_SUPPORTED/BLOCKED distinct from software tests PASS.

**Authority:** Methodology v1.8 defines mathematical/scientific semantics; Guide v2.0 defines code/validation order; verified repository physics and sound proof scopes outrank documentation assumptions; historical P4–P8 data/checkpoints retain their original published interpretation. Neither report commits code or changes GitHub by itself.
