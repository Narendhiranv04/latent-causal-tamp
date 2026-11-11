---
title: "Latent Causal TAMP"
subtitle: "Implementation & experimental guide v1.9 | complete 2D A/B/C study before 3D"
author: "Stage-gated implementation contract"
date: "19 October 2026"
lang: en-US
colorlinks: true
linkcolor: NavyBlue
urlcolor: NavyBlue
toc: true
toc-depth: 2
numbersections: true
fontsize: 11pt
geometry: margin=0.8in
---

> **STOP RULE / REPOSITORY STATUS.** This is a forward plan, **not a patch to the repository**. User reports implementation **through the G4D migration**, but will supply current code separately. The latest G4D report 0010 establishes 115 passing tests, six archived replays, 44 validated ordered positives, 130 transferred assignment-certificate negatives, and **zero** decided same-endpoint order contrasts, **zero** scene-effect pairs, **zero** omission pairs, and **zero** V2-native first-witness cost labels. G4D **code migration was completed; its physical evidence gate was BLOCKED**. G4A was NOT_READY_TO_SCALE. No data collection/training/3D is newly authorized by this report. Read the actual repository and frozen plans before any code change; keep every archived run, code hash, split and negative-evidence scope. Implementation Guide v1.8 is superseded for **future A/B/C work**; Methodology v1.7 defines scientific semantics and wins on scientific conflicts.

![**A/B/C shared teacher, distinct learned energies, common execution and evaluation.**](assets/architecture.pdf){width=98%}


# One unambiguous objective and staged output

**Do not implement three disconnected projects.** Build a **shared 2D evidence/robot platform**, then three interchangeable learning/scoring modules:

- **A_LOCAL_SEQUENCE:** v1.6's unary/pair MLP + ordered GRU + cost head; intervention explanations from differences in its task score; Boltzmann samples $r$ only.
- **B_JOINT_CAUSAL:** explicit typed scene/omission outcome variables $z$, trainable outcome/coupling potentials plus prefix pair-order factors and nonrecurrent cost; joint Boltzmann energy $E_B(r,z)$. Infer over both $r$ and $z$.
- **C_HYBRID_JOINT:** B's typed intervention/omission variables and coupling plus A's ordered GRU task/cost factor; joint energy $E_C(r,z)$, not two separately trained black boxes.

All three share identical **initial context, object features, physical domains, teacher annotations, sampler call accounting, independent robot motion/oracle, safety/status policies, splits, and target-feedback boundary**. Select which approach works by data, not by the expected novelty of its name. Additional baseline: exact geometry/matching or discrete solver plus full robot checking, and V1 endpoint + external order search with clearly charged extra calls.

**Research-release gates** (no advance on test failures): physical/certified contrast data -> mathematically correct sampler -> audited independent-root data -> train all arms -> full matched 2D evaluation -> **explicit 2D decision report** -> only then G7–G10.

# What is inherited verbatim, what may change

**Never rewrite just to fit this guide:** G0 scene/IDs/8x8 physical grid; G1 full 3R geometry, tested home and 48 grasp family; G2 fixed-path local interventions (diagnostic-only historical scope); G3 matching, order and physical path checks; G3.5 one-shot boundary; G4A old sample/provenance/audit; G4D canonical ordered sequences, fixed-order verifier, `effects.py`, V2 schema, cost records, anchored counterfactual tensors, historical replays.

A V1 positive witnesses **only its exact replayed order**. An assignment-wide certificate can be transferred to multiple orders only if the matching state/profile/safe-retreat scope has been checked. Planner failures remain UNKNOWN. Current G4D sparse roots are development fixtures, **never untouched test roots**. Existing `config.toml` and `config_v2.toml` hashes must remain reproducible; add a separately named overlay for A/B/C, rather than rewriting previous archived configs.

**Active robot contract:** 2D fixed-base 3R arm, 8x8 support cells at pitch 0.08 m, object radius 0.024 m and a single 0.005 m margin, continuous full-arm/finger/attached-body collision checks, tested 48-grasp family, supported carry, SAFE_RETREAT success and separate HOME diagnostic. Object resting cells do not imply straight-line robot motion. No simulator-only object teleport can count as a repair. No complete teacher target sweep is supplied as learner input. Only known primitive geometry/poses and GT masks are assumed.

# Concrete module ownership after inspecting actual repo

**Inspect first:** `git status`, `git log`, current config/profile/action hashes, `G4D` report and `g4d_plan.json`, existing source tree and tests. Unknown filenames must be resolved from repo, not fabricated. The following are suggested *responsibilities*, not a demand to rename working files.

| Responsibility | Existing / intended module | Change boundary |
|:--|:--|:--|
| Scene, candidates, robot numeric context, root IDs | existing `scene.py`, `config.py` | Keep stable IDs, immutable roots and strict schemas. |
| FK, IK, collisions, supported transport | `geometry.py`, `motion.py`, existing skill code | **No ML imports**; preserve contact/clearance semantics. |
| Frozen G4D ordered proposals / physical signatures | `sequences.py` | Reuse canonical sequence/prefix/omission; no second independent permutation. |
| Independent fixed-order planning, scopes | `verify.py`, `ordered.py`, `certificates.py` | Never allow learned proposal code to invoke target planner; report witness vs unknown. |
| Deterministic scene/omission effects | `effects.py` | Anchor original appearance, enforce fixed robot for scene do; no label leakage. |
| Generic sampler kernels | `sampler.py` if needed | For A sequence-only; B/C use exactly verified marginalization or joint kernel. |
| Shared feature encoder/static factors | `model.py` | One small backbone + shared local factors; model family code kept separate. |
| A order GRU/task/cost | `model_a.py` **or** coherent section in `model.py` | No duplicate feature extractors. |
| B outcome/coupling potentials | `model_b.py` | Explicit z masks, prefix pair order, outcome marginal. |
| C hybrid combination | `model_c.py` | Reuse B cause factors and A GRU, no forked architecture. |
| Split / teacher data / tensors | `data.py` | Single strict learner allowlist; privilege never in model inputs. |
| Training, losses, checkpoints | `learn.py` or `train.py` | All model versions and loss masks recorded; no trainer framework. |
| Evaluation and plots | `evaluate.py`, `viz.py` | Matched candidate roots/calls, real trajectory replay, uncertainty. |
| Command dispatch | `run.py` | Thin and deterministic; no broad CLI framework. |

**File size:** roughly 120–280 *logical* lines preferred. Above ~300 triggers a responsibility review, not uncontrolled refactoring. Preserve existing utilities and six archived run repros. Two new model files and at most one sampler helper are justifiable; **do not** create three duplicated full packages or independent teacher pipelines. Plain dataclasses, TOML, JSON, NPZ and PyTorch suffice; no database/web dashboard/abstract factory registries.

# One shared schema, three model IDs

Use historical `INITIAL_SCENE_ORDERED_ONE_SHOT_V2` for execution semantics. For **new** records and checkpoints, add a `comparative_model_version` field whose value is `2D-ABC-v1`. G4D's saved V2 data remain untouched. The learner context must expose initial RGB-D and masks, object poses/shapes/supports, robot q/limits/FK/gripper/attachment, target goal, constraints, physical candidate domain and missing-visibility flags. Cache frozen initial appearance features once. Counterfactual object pose substitution changes **only** structural fields; anchor hash and visual features are unchanged. Teacher post-move joint trajectories, oracle distances/labels, dataset family identifiers and search seeds must not enter the learner.

**Proposal:** `sequence=[[object_id,physical_pose_id],...]` is the single authoritative order. `[]` is no-repair. Store derived assignment and physical signature; no duplicate IDs, padding-defined equivalent repairs, active-target move or impossible destination notation.

**Model B/C typed latent/outcome record:**

```text
explanation_catalogue: {version, scene_query_ids, fixed_eligibility}
explanation_layout: {z0, z_scene[Q], z_repair, z_omit[slots], active_mask}
scene_query: {kind, object_ids, from, to, fixed_robot_hash, anchor_hash}
omission_query: {sequence_signature, omitted_positions, regenerated_prefix_hash}
model_prediction: {p_empty, p_repair, predicted_delta_scene,
                   predicted_delta_omit, energy, predicted_J}
privileged_teacher: {Y0, Yscene, Yrepair, Yomit, J_first,
                     label_masks, statuses, proof_scope, witness_hash}
```

The `privileged_teacher` namespace is **never** in the model input batch. B/C require an active-mask-stable z layout: inactive explanation slots have deterministic values and no partition multiplicity. Valid scene queries cannot change robot state; robot-start contrast is **separate** and labelled as such. An omitted action restores stay in all reconstructed prefixes; **no object is deleted**.

**Status fields:** `static_status`, `ordered_feasibility_status`, `relocation_attempt_status`, `target_attempt_status`, `simulation_status`, `hardware_status`, and `explanation_label_mask`. Status = VERIFIED_FEASIBLE, CERTIFIED_INFEASIBLE with exact scope, or UNRESOLVED. A finite search timeout is never an impossibility certificate. History persists within a committed repair episode.

# Staging order: preserve G4D, add one bridge gate, reuse G5/G6

| Gate | Owns | Must produce / stopping criterion |
|:--|:--|:--|
| **G4D-EVIDENCE** (unfinished part of existing G4D) | Frozen `g4d_plan.json`; no new architecture | Authorized per-unit CPU, aggregate CPU, workers, wall guard, cancellation. Collect actual two-move witness; **decided** same-endpoint order contrast; decided scene and omission pair; joint continuity and target-start equality. Otherwise BLOCKED and STOP. |
| **G4B** (existing ID, expanded sampler tests) | Generic sequence kernels, optional bounded-z exact marginal | Tiny exhaustive target distribution, row sums, detailed balance, Hastings ratios for variable `K_i`, gradients, cache recomputation, z-mask/partition invariance. No neural training. |
| **G4C** (existing ID, wider data contract) | New **20 independent roots** / teacher cases | Attempt ledger, decided paired label coverage, candidate and cost provenance, 2D complete 3R witnesses. Freeze fresh 300-root plan only after threshold audit. No test roots used for design. |
| **G4E-ABC** (**new, after G4C**) | A/B/C model interfaces and isolated tiny-data learnability | All arms share tensors. B/C explicit z and coupling tests; finite-pool likelihood exact on small domain; controlled memorization/order-swap/explanation gradient checks; no deployment claim. |
| **G5-2D-ABC** (expanded existing G5) | Train A, B, C, matched ablations | Three independent seeds/model, same roots, masks and budgets; save calibrated checkpoints and held-out validation analysis. Reject teacher-feature leakage. |
| **G6-2D-DECISION** (expanded existing G6) | Frozen held-out 2D comparison | Independent replay, root bootstrap CIs, cost/compute-matched comparisons, explicit winner/no-winner verdict and **2D completion report**. Do not start G7 without it. |
| **G7–G9** | 3D gated extension **after** 2D decision | Pin full xArm7 assets/geometry; start sparse, then 3D separate training/evaluation. No automatic cross-dimensional certificate transfer. |
| **G10** | Scripted three-target task | Actual achieved-state continuity; local success and complete task separate; record interference with later actions. |

**Do not renumber archived G3.5/G4A/G4D/G4B/G4C/G5/G6**. G4E is intentionally added **after G4C** as a small comparative-model wiring gate. If G4D-EVIDENCE still fails, preserve negative outcome and either construct new predeclared sparse scenes under a *new* plan or report architecture-data infeasibility; never loosen oracle thresholds or silently substitute guessed labels.

# Detailed data plan: complete articulated 2D, not a translating-disc toy

## Independent sparse fixtures, with measured—not desired—outcomes

| ID | Construction question | Mandatory logged contrast |
|:--|:--|:--|
| J0 | Originally feasible from actual q0 | Empty candidate positive, J=0, safe retreat complete. |
| J1 | Two independent target blockers | Singleton scene edits each 0 effect, compatible joint edit +1 **if verified**; independently checked two-move ordered repair. |
| J2 | Same endpoints but order-specific access | One complete positive and one **sound scope-wide negative**. Timeouts -> UNKNOWN, not artificial contrast. |
| J3 | Destination changes whether C participates | A->P needs C move, A->Q avoids C; actual omission/alternative replay. |
| J4 | Three-move access dependency | Same endpoints, several canonical orders; order/prefix higher-order check. |
| J5 | Nuisance or harmful intervention | Pair fixed robot and matched eligible scene; include zero-effect, and negative effect if constructible. |
| J6 | Same scene, different valid robot q0 | Independently decided task outcomes and separately labelled robot-start effect. |
| J7 | Endpoint distance vs joint-travel inversion | At least two first relocation witnesses, logged exact J and C_d; inequality only if actually measured. |
| J8 | Static-valid but physically unresolved | Precise unknown reason; no negative contamination. |
| J9 | Finite tiny checker | 2–3 objects, nonstay options 2 each, b <= 2; enumerated ordered r and bounded z. |

For each fixture save `scene.png` (complete full 3R arm), `candidates.png` (ghosts with physical ID), `interventions.png` (fixed-robot initial/edited pairs), `orders.gif` (actual stored trajectory *only if executed*, else NOT_RUN), `explanation_effects.csv`, `labels.json`, `evidence.json`, `robot_trace.npz`, `energy_a_b_c.png` **after training**, and `manifest.json` with root/source/action/profile hashes. A reduced picture with a point arm or straight-moving discs is insufficient. Show every robot body, fingers, target, support, numbered action order, achieved joints/attachment when motion exists, first collision or UNKNOWN interval, and original/edited appearance anchor IDs. Comparisons use identical camera/axis limits.

## Dataset quota and limitations

The original v1.8 **proposed** 20-root readiness targets remain a planning starting point: >=6 zero-move witnesses, >=8 nonempty complete witnesses, >=4 roots with multiple sufficient repairs, >=4 decided same-endpoint order contrasts, >=4 decided nonzero scene effects, >=4 decided omission effects, >=4 decided nuisance/no-change roots, >=8 cost-labelled roots (>=4 multi-move). In addition, to evaluate B/C, log >=4 **fully decided, mask-complete bounded-z mini pools** spread across independent roots and >=2 measured nonadditivity cases where available; if not attainable, mark B/C's joint-causal supervision BLOCKED rather than use latent IDs as oracle labels. These quotas are **design targets, not observed outcomes**. No deleting difficult roots.

Save the true number of independent roots $R$, candidate queries $Q$, ordered sequences $N_r$, scene pairs, omission pairs, decided pairs, cost witnesses, and exact negative certificates separately. Retain G4A's 44/86/110 assignment label counts as V1 provenance, not V2 label coverage. A fresh 300-independent-root set (210 train/45 validation/45 test) is created/split **before** its descendants; enlarge to 1,000 only after a measured CPU/coverage feasibility report and explicit budget authorization.

## Teacher collection procedure

1. Freeze root, robot profile, goal, initial q/g/attachment and supported-cell domain; hash all.
2. Predeclare canonical candidate sequences with same-endpoint swaps and alternative destinations. Predeclare eligible scene edits and omission rules **before teacher outcomes**.
3. For each ordered r, restart exactly from S0; run **fixed-order** relocation backend. Save the **first complete relocation witness** and its normalized joint travel before target evaluation; other realizations may establish feasible existence but don't replace the first-witness J target.
4. If a sound static/first-action/all-order certificate already decides negative, log scope and do not pretend the target ran. If relocation witness exists, run **complete target evaluation** from the achieved final state, including safe retreat. Unknown stays unknown.
5. For fixed-robot scene edits, clone S0 and change only allowed object pose fields; check eligibility; independently evaluate **target-only** from same q/g/attachment and anchor. Omission sequence outcomes are new full ordered teacher queries.
6. Write immutable lineage, hashes, actual CPU/planner calls, first-witness J, all scope/status/masks and a scene-backed visualization. Mixed pool training only uses comparable decided outcomes; no teacher path in proposal tensors.

# Exact implementation for each model, not a framework rebuild

## Shared representation and energy conventions

Frozen DINOv2 mask-pooled feature -> trainable 128-d object projection. Append supplied normalized object pose, primitive shape, candidate-pose difference, support, target/action features and robot numeric profile (q, limits, FK positions, gap, gripper dimensions, attachment). No pose encoded from learned image alone when GT pose is supplied. Pair symmetry under object exchange, invariance to object list permutation, and sensitivity to action order are mandatory.

Local MLPs: two hidden layers width 128 with ReLU; logits -> nonnegative $e=\operatorname{softplus}(-\ell)$. Model A: width-128 GRU processes ordered selected action + **all-object prefix** summary, task feasibility logit, nonnegative travel cost. Model B: same local representation; **separate bounded binary outcome slots** and trainable scene/omission/coupling potentials; prefix-conditioned adjacent/predecessor interaction MLPs for order; nonrecurrent cost MLP. Model C: B's outcome/coupling factors and A's GRU order task and cost; no duplicate old B order sum unless named ablation.

**No separate Slot Attention, learned IK/dynamics/policy, RL, trajectory decoder, full target sweep input or classic Hopfield hidden layer.** Calling B a 'joint Boltzmann energy model' refers to its **trained joint $E(r,z)$**, not an unsupervised causal discovery algorithm.

## Exact B/C explanation layout and energy audit

Define a fixed capped scene-query array before outcomes; for every proposal generate deterministic omission slots up to moved-object cap b, plus an active boolean mask. Outcome variables: `z0`, `zscene[q]`, `zrepair`, `zomit[t]`. Each equals a **hypothesized binary outcome** conditional on the named intervention/repaired sequence. Never train `z_i = 'object i was causal'` from teacher-selected moved IDs. Direct-cause labels and universally necessary repair participants must have independent sound proof if reported.

Required B/C functions:

```python
build_explanation_layout(context, sequence, catalogue) -> layout
energy_joint(model, context, sequence, z, layout) -> scalar
all_active_z_states(layout) -> iterator      # tiny bounded exact
repair_marginal_energy(context, sequence) -> scalar
predict_effects(context, sequence, catalogue) -> fields_with_scopes
```

On mini domains, verify $\sum_z e^{-E(r,z)/T}$ by both direct enumeration and stable `logsumexp`; compare derivatives to finite differences; adding inactive z slots must leave r probabilities identical. For B/C, **do not** blindly apply A's Gibbs difference to `E(r,z)` with a z chosen for a *different* proposal. Either marginalize z exactly or run a separately proven joint reversible transition kernel. Test the temperature and constant-energy limit, same candidate identities under object relabeling, correct omitted-prefix regeneration, no unbounded z-state enumeration in dense 2D, and absence of dependence on teacher fields.

## Finite sampler experiments before neural training

Implement the four V2 sequence kernels: (i) destination Gibbs conditioned on all others, using **full changed energy**; (ii) symmetric action-order swap with Metropolis acceptance; (iii) birth of unused object+destination+insertion position with correct Hastings ratio; (iv) death and reverse ratio. For pure A: birth from sequence length m has reverse/forward ratio $(N-m)K_i$ under equal fixed birth/death kernel probabilities; death from m has ratio $1/[(N-m+1)K_i]$. Use actual object-specific $K_i$; unavailable kernel is a **self-transition**. Optimize caches only after equality to full recompute.

For B/C's **bounded exact z marginal**, apply the same sequence kernels to $\bar E(r)$, then draw or enumerate $z\mid r$. Detailed balance, row sums and exact stationary distribution are checked on 2–3 object enumeration, with unequal candidate counts. A separate approximate joint (r,z) chain remains **disabled** until its own transition matrix is independently validated. No cherry-picked pleasing sampler GIF counts as mathematical verification.

# Training: same data, clear losses, no automatic 'causal discovery'

**Common teacher masks:** local static labels, exact-ordered complete positives and scoped negatives, fixed-robot target-only pairs, repair omissions, first-witness travel cost. Unknown/ineligible pairs are always masked. Same root split, effective batch distribution and labeling budget across architectures; report if any architecture makes use of fewer complete joint z pools.

**A objective:** $L_{\rm static}+\lambda_sL_{\rm task}+\lambda_eL_{\rm effect}+\lambda_cL_{\rm cost}+\lambda_JL_{\rm pool,A}$. $L_{\rm pool,A}$ uses decided ordered repair pool and the feasibility energy **without cost**. The effect term compares the same scorer under anchored pose changes and rebuilt omission sequences.

**B objective:** shared $L_{\rm static}$ and decided repair/task BCE (derived from explicit outcome marginal), plus individually supervised masked z-field outcome BCE, scene/omission effect MSE, first-witness nonrecurrent cost Huber, **joint exact finite-pool negative-log probability over verified (r,z) pairs**, and a coupling-removed ablation. Joint loss is skipped with an explicit reason when fully decided pools do not exist. Do not train B only on a pseudo culprit mask; train its **joint energy parameters** with actual intervention outcome comparisons.

**C objective:** B's outcome/causal coupling and pool objectives **plus** GRU order/task/cost training, without accidental duplicate step-order terms. Control C-no-coupling and A matched width/parameter count; otherwise apparent hybrid gains can be capacity gains.

**Training phases**, each with checkpoint and diagnostics: (1) frozen backbone and factor BCE smoke; (2) ordered task and cost heads + outcome/effect supervision; (3) exact small-pool joint loss and finite-difference gradient tests; (4) 3 seeds/model on independent roots; (5) choose feasibility threshold, abstain threshold, lambda coefficients, temperature and stopping epoch on **validation only**; (6) lock test runs. Initial settings: AdamW LR 1e-3, weight decay 1e-4, width 128, lambda=1 for supervised losses, sampler T=1, 8 chains, 300 updates/chain, move cap 3, 64 unique candidate maximum and 12 full-motion checks per query **as tentative starts from v1.8**; all actual hardware/runtime and compiler pins verified before claiming results. Do not silently use another project's Torch/CUDA build.

**Required loss tests:** BCE positive/negative sign; nonnegative energies; $J(\emptyset)=0$; cost/Huber target exactness; masked unknown effects produce **no** gradient; exact joint energy gradients by finite difference; no label leakage; C and A task changes under genuine action permutation; invariance to object slot order; B/C z-mask partitions correct; checkpoint/config/protocol hashes reject incompatibility; oracle poisoning/deletion leaves learner outputs unchanged. For a randomly initialized model, order scores need not differ predictably; test **capacity to distinguish** and then learned performance on decided contrasts.

# One-shot inference and motion continuation, identical for all arms

```text
RESET to initial observed S0 with q0/g0/attachment/goal
SCORE r=[] (and fixed-budget eligible explanation queries)
SAMPLE/SEARCH up to identical proposal budget using E_sample or z-marginal
DEDUP and FREEZE ranked physical ordered sequences, before target outcomes
STATIC SCREEN (exact local/endpoint oracle, common to all arms)
for r in frozen rank:                       # no target feedback
    TRY fixed-order relocation witness, varying grasps/paths but never order
    if no complete relocation witness: continue or exhaust budget
    COMMIT that exact order, destinations, full witness
    EXECUTE and validate achieved joint/object/gripper state for every move
    if deviation beyond committed policy: ABORT, no target invocation
    EVALUATE TARGET from achieved state exactly once, goal + SAFE_RETREAT
    FINISH success/failed/unknown; NO second candidate after target result
if no witness: record ABSTAIN/UNRESOLVED with full attempted denominator
```

Offline teacher **may** evaluate target for many different r starting from S0 to create labels; the primary deployment episode **may not** use those outcomes while selecting a repair. Historical V1 external order search is compared under a clearly named extra order budget. Repair prefix scenes for scoring are **ideal object pose hypotheses** only, not predicted future arm states; achieved-state replay is external.

# Full 2D comparison matrix with clean research questions

| Comparison | Variable actually changed | Interpretation |
|:--|:--|:--|
| A vs geometry/matching + full verifier | Learned proposals versus analytic/oracle informed proposals | Does learning add anything with known geometry? |
| Every arm vs its geometry-only learned counterpart | Drop mask-pooled appearance, retain supplied poses/shapes/robot context | Does appearance actually add value for visually identical discs? |
| A vs uniform ordered | Learned energy versus generic ordered candidate search | Does energy rank better at equal compute? |
| A vs endpoint+external order | Joint learned ordered score versus separate external order enumeration | Cost and outcome accounting must include external order search. |
| **A vs C** | Explicit z and cause–repair coupling with GRU retained | Best primary test of causal-factor modeling; add A capacity-matched. |
| **B vs C** | Pair/prefix order potentials versus GRU higher-order order factor | Order modeling, with parameter-count/compute controls. |
| B vs B-no-coupling | Explicit learned causal–repair coupling | Does a genuine joint term improve explanation/repair? |
| C vs C-no-coupling | Same GRU and data, omit coupling | Is causal coupling useful beyond task-score differences? |
| A/C with vs without paired interventions | Matched roots/families/label amounts and decided coverage | Do interventions, rather than extra examples, matter? |
| No-order versus full order | Retrain without GRU/order interaction | Is order learned, not merely read from an array? |
| No-pair, local-only, no-cost, no-joint | One factor/learning objective each | Preserve separate retrained and inference-lesion controls. |
| Exact small z-sum vs approximate sampler | Inference correctness/complexity | Only after exact stationary distribution tests. |

**Primary release metrics:** blocked repair success and overall query success with full eligible denominators (abstention, unknown, abort and no witness included), scoped minimum vs best-found, unnecessary moves on originally feasible queries, median and tail candidate/score/motion calls and CPU, normalized measured J, $C_d$, first valid candidate rank, and all failure-source counts. **Explanation metrics:** per-query scene effect and omission-effect errors and signs, interaction residual and nuisance false-positive, with masks/decided coverage. **Order:** same-endpoint decided pair-ranking accuracy **and coverage**. **Learning:** factor precision/recall/calibration, task AUROC/Brier, joint pool ranking, cross-seed variance. **Stats:** root-cluster bootstrap only; hold all descendants together.

**Do not claim:** B has learned a causal graph because a weight is large; C's lower energy is higher physical success; a sampled trajectory timeout is an order-wide negative; 'more accurate' if a method abstains on half the roots; 'minimal repair' without a sound lower bound; 2D kinematic replay is a real-world grasp; the sampled first-witness cost is globally minimum motion.

# Figures and mandatory stage report outputs

For every gate, produce one **scene-backed** overview PNG and (for robot motion) a stored-trajectory GIF/MP4 (no linear artistic invented paths). Then attach a machine-readable result and manifest. For A/B/C train/evaluate figures specifically:

1. **Root scene**: full 3R arm, actual q/gripper/target/obstacles and candidate placements, same camera.
2. **Causal contrast**: original and eligible do(I) scene sharing the original visual anchor; labels, predicted $\Delta$, masks and changed-field list.
3. **Joint-intervention synergy**: same-root singleton/joint intervention effects and success (may remain 0 after single edits).
4. **Ordered contrast**: identical endpoints with A-before-B and B-before-A, real certificate/witness or explicitly UNKNOWN.
5. **Energy landscape**: same finite candidate set scored by A/B/C; for B/C show marginalized repair energy and posterior explanation outcome, not compare incompatible raw additive-energy offsets.
6. **Training curves**: separate static/task/effect/cost/joint losses, active decided samples and gradients; the GRU curve is not enough.
7. **Robot trace**: gripper and all links, q trajectory, actual relocation order, achieved poses, first-witness J and SAFE_RETREAT, with genuine planner record.
8. **Decision dashboard**: held-out successes, uncertainty coverage, root-cluster intervals, CPU/verifier calls, explanation/order errors and ablations. The paper-facing comparison must have a transparent per-root CSV, not only aggregate bars.

Each new report (one numbered checkpoint per gate) includes: precise Git revision, source and config hash, dataset/root/split hash, model/protocol/profile, command exit codes, attempted/decided/unknown/failed counts, out-of-scope reasons, actual planner calls/CPU/wall, model trainable parameters, example witnesses/certificates, plot paths, leakage guards, budget compliance, comparative coverage and an explicit **PASS / BLOCKED / FAILED / STOP**. Never modify previous stage reports in place. No automatic scaling if acceptance remains blocked.

# Exact budget dependencies and next action after receiving the repo

The current G4D frozen evidence plan (per report 0010) has **no authorized numeric** `per_unit_cpu_s`, `aggregate_cpu_s`, `workers`, `wall_guard_s` or `cancellation_margin_s`. Therefore its planned collection was **not run**, and a `g4d-run` collection command was not written. Do not invent these numbers and do not launch costly teacher data collection before explicit authorization. The report also mentions a `PLANNER_BUDGET` reason-code defect where exhaustion/completion reasons can be misclassified **while remaining UNRESOLVED**; preserve that distinction and fix/test the reason before counting negatives.

On receiving the actual G4D repo, the implementing assistant should **first** do a nonmutating audit, not start G5:

1. Inspect tree/branch/current HEAD, working changes, G4D `g4d_plan.json`, source/docs, version hashes, all current tests and six archived runs.
2. Build a mapping from these proposed A/B/C responsibilities to existing modules; propose **minimal new file additions only** and a testable G4D-EVIDENCE plan with explicit budget fields for user authorization.
3. Identify which G4D evidence units remain blocked or reusable, plus exact fixed-order oracle/certificate and teacher interfaces. Preserve historical V1 and G4D evidence scopes.
4. Only after user authorizes numbers and the plan is frozen, run **G4D-EVIDENCE only**, produce report and STOP.
5. Follow with G4B, G4C, G4E-ABC, G5-2D-ABC and G6-2D-DECISION one gate at a time; no unrequested architecture redesign mid-run.

# Selection and stopping: what counts as '2D complete'

The **2D comparison is complete** only when: full 3R robot and candidate/target replay are verified; all three models have defined trainability and test runs or explicit irreducible data failure; finite samplers meet stationary/marginal consistency tests; decided intervention, omission and same-endpoint order coverage is reported; no unknown negative leakage; strong analytic + uniform controls are included; three seeds with identical root splits and matched budgets are reported; held-out executable repair success, joint cost, explanation, order and CPU are compared; and a signed **A/B/C decision memo** names the supported scientific claim, limitations and whether 3D is worth proceeding with.

**The winning architecture is not automatically the most complex.** Choose the simplest method that improves independently verified robot repair outcomes, at a defensible inference cost, with useful explanation/order generalization. If A and the analytic solver equal or beat C, report it; no forced novelty claim. If no model is supported due to label sparsity, the correct result is BLOCKED / insufficient causal supervision, not a conjectured win. Only then may the 3D stage be designed against the chosen or explicitly compared 2D branches.

# Revision log relative to Guide v1.8

**Added:** complete 2D architecture contest A/B/C; B explicit typed outcome variables, joint-energy likelihood, causal–repair coupling and exact bounded-z marginalization; C hybrid GRU plus causal coupling; G4E-ABC model interface/learnability bridge; exact stationary/partition checks; fully crossed explanation/order/effort ablations; full 3R J0–J9 experimental fixtures; data-label sufficiency and cross-model comparability requirements; mandatory 2D architecture decision before G7. **Retained:** G4D migration versus blocked evidence, prior reports/hashes, full 2D robot, canonical ordered move-once repairs, anchored scene edits and omissions, one-shot target boundary, first relocation-witness J, unknown masking, G4B/G4C/G5/G6 IDs, and separate later 3D/hardware contracts.
