---
title: "Latent Causal Infeasibility for Long-Horizon TAMP"
subtitle: "Methodology specification v1.7 | controlled 2D comparison of three energy architectures"
author: "Research and experimental contract"
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

> **STATUS / AUTHORITY.** This is the proposed *v1.7 scientific contract*, prepared from Methodology v1.6, Implementation Guide v1.8, and G4D report 0010. It supersedes **v1.6 for new 2D learned-model comparison experiments only**. Its companion, Implementation Guide v1.9, defines implementation order, module boundaries, experiments, and gates. Prior G0–G4A/G3.5 protocols, results, archived hashes, geometric certificates, and G4D migration evidence remain unchanged. Neither document claims new runs, training, or physical robot results. **The code repository has not been provided for inspection.** No source edit is claimed. Sections below restate the retained normative boundaries explicitly so that an implementing agent need not guess what older reports meant.

![**A/B/C shared teacher, distinct learned energies, common execution and evaluation.**](assets/architecture.pdf){width=98%}


# Scientific decision and hypotheses

The aim is to compare **three genuinely distinguishable ways to learn and use energy** in the **same completed 2D 3R manipulation setting**, then select a justified architecture or report that none beats the geometric controls. Do **not** select a winner in advance. Do **not** frame a classical Hopfield/Boltzmann Machine as automatically causal.

**Shared task.** From one initial observation, known simple object geometry, the robot's initial state, a specified target-and-goal action, and finite permitted placement poses, propose a small **ordered** sequence of move-once object relocations that permits the target action. Return (i) predicted no-repair infeasibility; (ii) explicitly scoped intervention/omission explanations; (iii) ranked corrections with robot-cost estimates and independently verified evidence statuses.

**H1 — local/sequential prediction.** Can a local action-conditioned energy from unary and pairwise endpoint factors, plus an order-sensitive GRU task factor, predict useful complete repairs? This is the **existing V2** architecture, renamed **A: LOCAL-SEQUENCE** for the comparison; Boltzmann search runs **on top of** its learned energy.

**H2 — explicit joint causal energy.** Does making predeclared, testable **intervention outcomes** explicit stochastic variables in a **joint conditional energy over explanation outcomes and repair sequences** improve effect prediction, order-sensitive recourse, or out-of-distribution transfer? This is **B: JOINT-CAUSAL-EBM**. The energy factors and coupling weights are **trained together**, not a post-hoc causal graph read from edge magnitudes.

**H3 — combined representation.** Does a **hybrid** containing both explicit intervention/repair coupling and a GRU higher-order ordered-repair factor improve over either A or B when data and computational effort are matched? This is **C: HYBRID-JOINT**. A vs C principally tests explicit causal variables/couplings **with the GRU held present**. B vs C explores the contribution of a recurrent order factor, but also requires matched-capacity controls.

**Null result is allowed.** A strong geometry-only matching/rearrangement baseline, an exact small-domain solver, or simple V2 may win. If physical order contrasts or paired intervention labels cannot be collected, H2/H3 remain **untested**; do not replace unknown outcomes with invented negatives.

## Precisely what is meant by 'causal'

There is **no claim** of latent-variable identifiability, automatic causal DAG discovery, or universal necessary culprits. The ground-truth supervision refers to **operational, scoped comparisons** under the declared finite intervention catalogue and complete robot/target evidence. A factor-graph edge or high Boltzmann weight is an *interaction*, **not** a certified causal arrow. Distinguish: (a) obstructs a particular geometric motion; (b) changes original-task success under a specified fixed-robot pose edit; (c) is necessary **within a specific ordered repair**; (d) is necessary across **all** possible repairs (only if independently certified). Never conflate these.

# Retained physical problem and interface (unchanged by this revision)

Use the actual repository-validated **fixed-base full 3R planar arm**, full finite-width links, housings, base, palm, two fingers, rigidly carried disc, joint limits, contacts, and **recorded 48-candidate grasp family**. Use the *tested* home, gripper aperture interpretation, collision margins, and safe-retreat policy, not provisional values from older guides.

- Grid: 8 x 8 **resting destinations**, 0.08 m pitch; identical disc radius 0.024 m, single 0.005 m clearance margin, unless a separately versioned control says otherwise. Intermediate object and arm motions remain **continuous**. The 2D dense challenge is 30–40 obstacles **only after** sparse articulated tests succeed.
- Only one target is active per query; other targets remain physical obstacles. Candidate pose 0 is stay. Each nonzero candidate is a unique supported **physical** pose; object IDs are not numerical coordinates. No duplicated or cloned objects in ghost scenes.
- Input includes clean initial RGB-D, GT instance masks, **supplied** primitive poses/shapes/supports, robot joint angles and limits, gripper gap/attachment, link/FK context, target/action/goal, fixed workspace and legal placement domain. DINOv2 or a documented frozen equivalent is a visual feature backbone; mask pooling supplies object features. Occlusion/missing masks are explicitly masked.
- **Forbidden learner inputs:** complete teacher trajectories, frozen target swept volumes, collision-oracle distances/labels, search seeds, teacher grasp choices, privileged post-intervention image/state, future outcome, root/family IDs. We learn **initial-scene** predictions; no target trajectory is supplied to any model. Old frozen-sweep G2/G3 facts remain **diagnostic, historically scoped**.
- A corrective action is a **complete relocation request** (object, supported destination) comprising approach, grasp, attached transport, placement, release and retreat. A proposal is a canonical sequence

  $$r=((i_1,k_1),\ldots,(i_m,k_m)),\quad 0\le m\le b,\quad i_t\ne i_u\text{ for }t\ne u.$$

  The empty sequence $\varnothing$ means no repair. No stay entries, duplicated IDs, padding-derived distinct states, off-grid locations or active-target relocation. Physical outcome depends on the **sequence order**; endpoint assignment $x(r)$ is derived and cannot disagree.
- Motion/IK may select different grasps and joint paths **within the proposed order**, but cannot reorder the moves. Carry forward actual achieved joint/gripper/attachment/object states; never reset to home between moves. Target completion means **goal and checked SAFE_RETREAT**; HOME is a separate diagnostic.

## Three-valued source of truth

For an ordered proposal $r$ let $\mathcal{W}(r,S_0)$ be **all permitted continuous relocation realizations** for that exact ordered high-level proposal. Let $\gamma$ be a complete target action from the final achieved state. Then

$$Y^*(r\mid S_0)=1[\exists w\in\mathcal{W}(r,S_0),\ \exists\gamma:\operatorname{Valid}(w,\gamma)=1].$$

A **positive** needs a complete independent relocation + target witness. A **negative** needs a sound proof excluding all allowed realizations **at that certificate's scope**. A failed grasp branch, one blocked path, a failed connector from one pose or exhausted finite stochastic planner budget is **UNKNOWN**, not a negative. Retain static endpoint, ordered, relocation-attempt, target-attempt, simulation and hardware statuses separately. The current comparison is **2D articulated kinematic** evidence; dynamics and hardware are not implied.

# Shared data / interventions: the only teacher, the same for A, B and C

All three architectures consume **identical learner-visible contexts, candidate pools, root splits and decided oracle labels**. Their inference routes are isolated by model ID but must use the same external checker, same grasp family, same per-proposal node/call/CPU limits, and the same committed one-shot target protocol.

## Labelled quantities, with exact scope

1. **Original task:** $Y_0^*=Y^*(\varnothing\mid S_0)$, checked by the independent target-only planner from initial robot state.
2. **Ordered repair:** $Y_r^*=Y^*(r\mid S_0)$ for exact object IDs, destinations, and action order. An assignment-wide certificate can label every order negative only after scope validation. A complete witness for one order **does not** label its permutations positive.
3. **Static candidate endpoints:** $y_i^w(k)$ for local workspace/support; $y_{ij}^p(k,l)$ for simultaneous endpoints. Static valid **does not** imply executable. Any unresolved factors are masked.
4. **Fixed-robot scene edit:** for a predeclared eligible intervention $I=\operatorname{do}(p_i\gets p_{ik})$ or a specified joint pose edit, construct $S_0^I$ with unchanged original robot q/g/attachment, target, other objects and frozen *appearance anchor*. Label $Y_I^*=Y^*(\varnothing\mid S_0^I)$ **target only**. Ineligible overlap/support edits are masked, not negative. Define $\Delta_I^{S,*}=Y_I^*-Y_0^*$ **only if both decided**.
5. **Repair omission:** for an existing $r$ remove selected action(s) $A$, preserving relative order of remaining actions. Omitted IDs stay in every ideal prefix. Independently label $Y_{r\setminus A}^*$, and define $\Delta_A^{O,*}=Y_r^*-Y_{r\setminus A}^*$ **only if both decided**. An omission cannot be inferred from old trajectories.
6. **Joint intervention / nonadditivity:** for fixed-robot compatible I,J use $\kappa_{I,J}^*=\Delta_{I\cup J}^{S,*}-\Delta_I^{S,*}-\Delta_J^{S,*}$ when all four task-only sides are decided. A global task outcome can stay 0 after every singleton and become 1 after the joint edit. Include nuisance/no-change, harmful and beneficial edits.
7. **Relocation motion cost:** $J^*(r)$ is measured from the **first complete relocation witness** found under a pinned backend and seed schedule, **before** examining target success. Missing witness means **no cost label**; a relocation witness can provide J even when subsequent target status is unknown. Use unwrapped normalized joint travel, all relocation phases and between-action transitions, excluding subsequent target and HOME diagnostic.

## Fixed catalogue and root grouping

Freeze the explanatory query set $Q_S(S_0)$ **before viewing outcomes**, using an explicit geometry/ID-independent rule (e.g., eligible singleton edit candidates, one joint edit and nuisance controls, capped per root). A repair $r$ has a deterministic bounded set $Q_O(r)$ of omission queries. Keep the catalogue version, eligible/decided masks, baseline/context hashes and *unchanged initial appearance anchor*. Never pick explanations after seeing that they work. Split **independent reference roots before** generating one-edit descendants, candidate orders, rendering variants and hard negatives.

## Distinguish evidence from model prediction

The oracle labels in Section 3 are **privileged training/held-out evaluation**. At deployment, the model is only supplied initial observations and hypothesized edits; its explanations are **predicted contrasts**. A successful diagnostic teleport does **not** prove that the robot can execute the edit. Direct geometrical blockage of a historical frozen path does **not** become an original-task impossibility certificate. No model may treat low energy as its own ground-truth certificate.

# Architecture A: LOCAL-SEQUENCE, preserving V2 without conceptual changes

Object representation: frozen DINOv2 mask pooling, shared trainable width-128 projection, known shape/pose/support and numeric robot/task descriptors. The local heads learn symmetric unary workspace probabilities $q_i^w(k)$ and pairwise placement probabilities $q_{ij}^p(k,l)$. Energy conversion $e=-\log q=\operatorname{softplus}(-\ell)$ preserves nonnegative local penalties.

For each candidate sequence $r$, form **ideal prefix scenes** containing all objects: previously moved objects at requested endpoints; other objects at initial poses. Pool scene/object tokens and process action tokens in exact order with a width-128 GRU. Its complete-task head emits logit $u_A(r)$ and probability-like score $p_A(r)=\sigma(u_A(r))$; its travel-cost head emits $\hat J_A(r)\ge0$ (empty exactly zero).

$$E_A^{\mathrm{feas}}(r)=\sum_i U_A(x_i(r))+\sum_{i<j}V_A(x_i(r),x_j(r))+\lambda_t\operatorname{softplus}[-u_A(r)].$$

A uses **implicit explanation via the shared score**, not separately sampled explanation variables:

$$\widehat\Delta_{A,I}^S=p_A(\varnothing\mid S_0^I)-p_A(\varnothing\mid S_0),\quad
\widehat\Delta_{A,t}^O=p_A(r\mid S_0)-p_A(r\setminus t\mid S_0).$$

Its sampling energy is $E_A^{\mathrm{sample}}=E_A^{\mathrm{feas}}+\lambda_d C_d(r)+\lambda_q\hat J_A(r)$. This architecture already includes **joint neural learning of all its energy factors** through a finite-pool feasibility loss. Boltzmann is its **inference algorithm**, not a separately trained RBM.

# Architecture B: JOINT-CAUSAL-EBM, explicit explanation variables in the energy

**Scientific difference from A:** B represents the outcomes of specified interventions/omissions as explicit binary stochastic variables, learns *compatibility between those outcomes and corrective decisions*, and performs inference over **repair and explanation together**. This is the original causal-factor ambition made testable. It does **not** claim that arbitrary Boltzmann weights identify true physical causes.

## Clearly typed outcome variables

For each fixed initial query and predeclared $Q_S$, define variables

$$z=(z_0,\{z_I^S\}_{I\in Q_S},\ z_r,\{z_A^O\}_{A\in Q_O(r)}),$$

where each $z$ is a **hypothesized binary feasibility outcome**: no-repair target, target under named scene edit, complete ordered repair, or complete ordered repair after a named omission. These are **not** a free-form 'causal object mask'. The observed causal effect is computed from their **difference**. A necessary-cause flag is UNESTABLISHED without independent proof.

**Critical variable-dimension rule.** Fix a maximum index layout for scene queries and up to the $b$ order positions/prespecified omission subsets in a run. An inapplicable slot has a deterministic value and is masked from both energy and partition count; it must not introduce additional Boltzmann states. A repair-induced omission query changes **with** $r$, by a deterministic rule known before outcomes. No padding or inactive-variable multiplicity advantage.

## Explicit conditional joint energy

A compact implementable factorization is

$$\begin{aligned}
E_B(r,z\mid c_0,Q) ={}& E_B^{\mathrm{static}}(x(r),c_0)
+ \phi_B^{\mathrm{seq}}(r,z_r,c_0)\\
&+\sum_{I\in Q_S}\phi_B^{\mathrm{scene}}(I,z_0,z_I^S,c_0)
+\sum_{A\in Q_O(r)}\phi_B^{\mathrm{omit}}(r,A,z_r,z_A^O,c_0)\\
&+\phi_B^{\mathrm{couple}}(r,z_0,\{z_I^S\},z_r,\{z_A^O\},c_0).
\end{aligned}$$

All $\phi$ are **trainable potential functions**, parameterized by small shared MLPs with numeric geometry/robot context and a masked pooled summary. $\phi^{\mathrm{couple}}$ sees **predicted candidate outcome variables z**, never teacher labels at inference. It learns dependencies between predeclared diagnostic effects and proposed correction outcomes. Its effects must disappear in an explicit no-coupling ablation. Static factors reuse the same label semantics as A. **Order in B:** use selected-item and **prefix-conditioned adjacent/predecessor interaction factors**, summed over steps; do not use A's GRU in pure B. Include at least a two-action swap contrast and a three-action interaction fixture. Higher-order dependence may remain poorly represented in B; that is a hypothesis, not silently fixed with a hidden GRU.

The conditional distribution is

$$P_B(r,z\mid c_0,Q)=\frac{\exp[-E_B(r,z\mid c_0,Q)/T]}{Z_B(c_0,Q)}.$$

Outcome-variable marginals are explicit explanation predictions; e.g. $\Pr_B(z_I^S=1)-\Pr_B(z_0=1)$ reports a scene-effect prediction. For omissions use $\Pr_B(z_r=1)-\Pr_B(z_A^O=1)$. This is **probability over scoped outcomes**, not a physical-cause certificate. Report model-consistency and probability calibration.

## How joint learning really occurs

Train B's potential parameters **together** with supervised *conditional outcome* losses on decided $z$ fields and a joint finite-pool ranking/likelihood objective over fully decided candidate combinations. A log-probability factor can be learned via BCE; shared coupling potentials are updated by a joint contrast over $r$ and **valid completely observed z assignments**. Train without needing ground-truth 'latent causal edges'.

For a small finite candidate pool $\mathcal C_{\rm full}$ in which **every active oracle outcome field is independently decided**, construct the teacher's observed outcome vector $z^*(r)$ for each $r$. The conditional **joint** partition explicitly includes **all hypothesized** binary outcome vectors $z$ for each fully decided repair, including incorrect outcome assignments: $\mathcal A_{\rm full}=\{(v,z):v\in\mathcal C_{\rm full},z\in\mathcal Z(v)\}$. A repair-discriminative exact finite-pool loss is

$$\mathcal L_{B,\mathrm{joint}}=-\sum_{r\in\mathcal C_{\rm full,+}}\frac{1}{|\mathcal C_{\rm full,+}|}\log\frac{\exp[-E_B(r,z^*(r))/T_{\rm tr}]}{\sum_{(v,z)\in\mathcal A_{\rm full}}\exp[-E_B(v,z)/T_{\rm tr}]},$$

where $\mathcal C_{\rm full,+}$ contains **every** witnessed feasible repair in that fully decided pool. Unlike a sequence-only loss, its denominator really sums over $z$ as well as $r$: **this trains the joint Boltzmann energy**, not merely a GRU score followed by sampling. Incorrect $z$ vectors are valid *model hypotheses*, not fabricated teacher labels, because every corresponding true field is known for these roots; independently supervised outcome-field BCE further penalizes incorrect configurations even for negative repairs. Do **not** include a candidate with even one required unknown/ineligible outcome field in this exact joint-pool term. Do not interpret the candidate-restricted probability as a globally normalized scene-wide likelihood. Test the normalization and gradients on fully enumerated microdomains. When fully decided joint pools cannot be collected, mask this term, retain single-outcome training, and mark the joint causal hypothesis **not established**.

B has a separate nonnegative travel-cost readout $\hat J_B(r)$ from prefix-conditioned pooled features (no GRU). It is supervised by the same measured first-witness cost as A. Its inference feasibility score and threshold must be defined **before** test: $p_B(r)=\Pr_B(z_r=1\mid r,c_0,Q)$, with outcome variables marginalized. Avoid using an unconstrained joint energy as an uncalibrated physical success probability.

## Boltzmann inference jointly, not merely post-processing

For B and C, the repair marginal is

$$P(r\mid c_0,Q)=\sum_z P(r,z\mid c_0,Q),\quad
\overline E(r)=-T\log\sum_z\exp[-E(r,z)/T].$$

**Exact small-catalogue route:** for a bounded diagnostic layout ($\le8$ binary active fields), enumerate all compatible z (at most 256), use $\bar E$ for ordinary destination Gibbs/order swap/birth-death proposals, then sample/compute z conditional on r. Test equality to complete exact $P(r,z)$ on tiny scenes. This is a genuine joint-energy probabilistic model, not 'energy on repairs followed by a separate explanation'.

**Larger route:** if enumeration is impractical, use a documented joint Gibbs/Metropolis chain over (r,z), with reversible proposals and the correct asymmetric birth/death + newly activated explanation-variable probability ratios. A naive reuse of V2's sequence-only acceptance ratio **is wrong** whenever the state layout changes. Do not enable approximate inference without exact tiny-domain stationary-distribution tests, autocorrelation/mixing diagnostics and a declared truncation budget.

**Non-negotiable bias check:** verify no entropic preference arises from different numbers of explanation variables or queries; fix layout/masks and compare $P(r)$ after adding logically inactive diagnostic slots.

# Architecture C: HYBRID-JOINT, high-order ordered factor + explicit causality

Keep B's typed $z$, scene/omission factors and cause–repair coupling. Replace or augment B's prefix pair-order score with **A's single order-sensitive GRU task potential** and GRU cost readout, using the **same initial object and robot encoding**.

$$E_C(r,z)= E_B^{\mathrm{static}}+E_B^{\mathrm{scene}}+E_B^{\mathrm{omit}}+E_B^{\mathrm{couple}}+\lambda_g\phi_C^{\mathrm{GRU}}(r,z_r).$$

Do not count B's old order factor twice unless a **separately named** additive-order ablation warrants it. C's sampler and outcome marginalization follow Section 5.4. C's joint loss, effect losses, static loss and cost loss share A/B's labels and masks. **A vs C** is the main controlled test of explicit causality *with GRU held in common*; add a parameter-matched A+WIDTH control and C without coupling to separate model capacity from causal supervision. **B vs C** tests local/prefix pair-order interactions versus the GRU on matched data, while recording architecture and parameter-count differences.

# All three models: cost, feasibility energy, and selection

The move count $m(r)$ is the number of **distinct** moved object IDs and is bounded by $b$. Compute displacement exactly:

$$C_d(r)=\sum_{(i,k)\in r}\frac{\|p_{ik}-p_{i0}\|_2}{L_W}.$$

Measure relocation-only normalized unwrapped joint travel on the backend's **first complete relocation witness**:

$$J(w)=\sum_{s,j}\frac{|q_{s+1,j}-q_{s,j}|}{q_j^{\max}-q_j^{\min}}.$$

This is **joint travel**, not real electrical energy, time or a global motion optimum. $J(\varnothing)=0$ exactly. Unknown/unwitnessed proposals do not get cost labels. Each architecture predicts $\hat J_M(r)$; all use identical task eligibility, budget, cost target and final tie-break policy.

During proposal sampling, $E_M^{\mathrm{sample}}=\bar E_M^{\mathrm{feas}}+\lambda_d C_d+\lambda_q\hat J_M$; for A the bar is not required. The energy trained by the **feasibility** pool loss excludes motion-cost terms. Final ranking after an independently learned/validation-frozen task-score threshold and exact static screen is **lexicographic**: (1) fewest moved objects; (2) lowest predicted joint travel; (3) shortest endpoint displacement; (4) lowest feasibility energy; (5) deterministic physical signature. Do not rank an invalid/all-stay repair first merely because it has zero moves/cost. Report how many candidate and z scores were evaluated.

# Training objectives: no confusion about what learns

**Shared learned parameters:** trainable object projection, local unary and symmetric pair MLPs, architecture-specific sequence factors, explanation/coupling potentials (B/C only), feasibility and cost readouts. **Frozen initially:** visual backbone, geometry, FK/IK, collision checker, independent planner, legal spot generator, label generator. **Not trainable:** temperature/search kernel probabilities, displacement formula, move count, certificate logic, target protocol; tune declared hyperparameters on validation only.

Base losses (masked when no decided label):

$$\begin{aligned}
\mathcal L_{\rm static}&=\operatorname{mean}_{f\in\mathrm{decided}}\operatorname{BCEWithLogits}(\ell_f,y_f),\\
\mathcal L_{\rm task}&=\operatorname{mean}_{r\in\mathrm{decided}}\operatorname{BCEWithLogits}(u_M(r),Y_r^*),\\
\mathcal L_{\rm effect}&=\operatorname{mean}_{q\in\mathrm{decided\ pairs}}(\widehat\Delta_q-\Delta_q^*)^2,\\
\mathcal L_{\rm cost}&=\operatorname{mean}_{w\in\mathrm{reloc.\ witnesses}}\operatorname{Huber}\bigl(\log(1+\hat J_M),\log(1+J^*)\bigr).
\end{aligned}$$

Here for B/C $u_M$ is a **derived logit from the outcome marginal $p_M(z_r=1\mid r)$**, not a second independently trained head that disagrees with the energy. A/C use the GRU task potential as appropriate. In B/C add explicit masked **outcome-field BCE** for $z_0,z_I^S,z_r,z_A^O$ and scored **coupling contrast** for fully decided joint records. Calibrate margin/temperature to avoid treating $\bar E$ as exact physical success likelihood.

**A joint pool:** $\mathcal L_{J,A}$ is the cross-entropy between a uniform target distribution over all **positive** ordered repairs and the Boltzmann distribution constructed from $E_A^{\rm feas}$ across the pool's **decided** candidates. Skip all-positive/all-negative pools; keep all verified successful alternatives, not only a teacher favorite.

**B/C joint pool:** use $\mathcal L_{B,\rm joint}$ as Section 5.3, and an explicit calibration task loss; the finite compared states and masks must match the actual joint hypothesis. Do **not** silently substitute A's sequence-only loss and call it joint causal Boltzmann training. Include a baseline *B with coupling removed* under the exact same examples and optimization budget. A/B/C have independently frozen temperatures/hyperparameters selected from the **same validation roots**, not test.

Training schedule: (0) deterministic scene/factor/sequence tests; (1) local supervised factors; (2) model-specific ordered task + cost + available effect/outcome losses; (3) add finite-pool joint loss; (4) calibrate feasibility/abstention on validation; (5) freeze checkpoints, seeds and test protocol. AdamW lr 1e-3, weight decay 1e-4, width 128, all initial loss coefficients 1 and three seeds are **starts**, not privileged tuned results. Per-term effective label counts and gradients are reported. No backprop through motion planner. Conditional full-state contrastive-divergence/maximum-likelihood beyond the **exact small fully decided pool** is optional research only after separate gradient/stationary tests; never call BCE + Gibbs 'trained a classical BM'.

# Search, teacher-feedback boundary and execution

**Offline teacher:** for every frozen candidate restart from identical immutable S0; check fixed-order relocations with achieved-state continuity, record the first relocation witness/cost before target, then obtain target label or scoped negative/unknown. Teacher can explore target outcomes offline **only to create labels**.

**Deployment:** (1) score no-repair and predeclared diagnostic queries from initial observation; (2) generate candidate ordered sequences via architecture-specific energy and matched Boltzmann budgets; (3) deduplicate and freeze pool, static screen and rank; (4) try fixed-order relocation witnesses, moving to next **frozen** candidate if no complete relocation witness within budget and **without target feedback**; (5) COMMIT first complete relocation witness; (6) execute with actual achieved-state checks; (7) evaluate target **at most once, only after** completed committed relocations; (8) stop on target failure. Reobserved deviations do not permit silent high-level reorder or resetting executed history. A teacher/test result cannot enter initial proposal inputs.

Variable-length sequence sampling: for A use v1.6's destination Gibbs, symmetric order swap, and birth/death Metropolis--Hastings with correct variable-candidate-count ratios. For B/C use the **exactly marginalized $\bar E$ route on tiny/bounded z**, otherwise a separately validated joint kernel; **same number of ranked repair candidates does not mean equal compute**. Match total model calls, wall/CPU, relocation/target planner calls, and rank budgets.

# The 2D experiment: fixtures, data and necessary contrasts

Mandatory **full-articulated 3R** development fixtures before dense scale:

- **J0 — zero move:** initial task success with SAFE_RETREAT; all methods score $r=\varnothing$, $J=0$.
- **J1 — independent blockers:** two goal/path blockers; single eligible scene edits each retain task failure but joint pose edit restores; record $\Delta_I=\Delta_J=0$, $\Delta_{I\cup J}=+1$ and a verified two-move repair if possible.
- **J2 — same endpoints, different order:** both sequences static-valid; **one complete positive and one sound order-scope negative**. Failed randomized planning is UNKNOWN and **does not satisfy J2**.
- **J3 — destination changes participants:** A->P requires first moving C; A->Q may leave C at stay; compare one-, two- and omission results.
- **J4 — three-action compositional access:** same final poses; order/prefix interactions not reducible to a single terminal pair check; specify actual proof/witness scopes.
- **J5 — nuisance/harmful:** nonblocking object edit with $\Delta=0$, and an eligible change that worsens feasibility when measurable; no false 'causal' attribution from mere motion.
- **J6 — initial-robot-state contrast:** same objects/goal, different valid q0 and independently decided outcomes where possible.
- **J7 — cost inversion:** two complete relocation witnesses; nearer endpoint has **measured** higher normalized robot-joint travel, if constructible. If not, report CONSTRUCTION_UNAVAILABLE rather than manufacture inequality.
- **J8 — static valid but motion unresolved/blocked:** preserve statuses and contrast against static-only factor accuracy.
- **J9 — finite exact miniature:** 2–3 obstacles, 2 nonstay destinations each, move cap <= 2, restricted catalogue. Fully enumerate ordered proposals and explanation states, audit partition functions/gradients/detailed balance.

Keep older G4D fixtures D-V2-0..6 as historical sparse evidence; reuse only by matching protocol, hash, policy and label scope. **Never promote G4D sparse development roots to held-out benchmark roots.** Initial 2D dense 30–40 obstacles are research challenges, not substitutes for completed sparse robot evidence.

Data progression: finish frozen G4D data collection; G4B correct sampler; G4C 20-root **independent** development audit including at least six zero-move, eight nonempty witnesses, four alternative sufficient proposals, four decided same-endpoint order contrasts, four decided nonzero scene effects, four decided omissions, four nuisance/zero-effect roots, and cost witnesses on eight roots with four multi-move traces (these are **proposed feasibility gates**, not guaranteed constructible). Record all attempts and UNKNOWN rates. Then split a **fresh** 300-independent-root 2D pilot (210/45/45 train/val/test), with a conditional 1,000-root expansion only after throughput/evidence approval. For fair learning, train A/B/C on the **same roots and same collected labels**, with B/C extra labels masked where absent, never substituted with fabricated negatives.

## Independent-variable controls

Keep candidate domain, original task, geometry, gripper/grasps, planner backend, safe retreat, root families, label budgets, training compute, query and outcome masks and physical verification policy fixed. Root IDs split **before** intervention generation. Report root counts, query counts, sequence count, valid/invalid/unknown counts, and class-conditional decided coverage. Separate cost/selection effects from feasibility learning. Hold a root-level untouched test set throughout.

# Evaluation and attribution of architectural value

**Required baselines:** geometry-only static/matching plus k-best full-motion/order checker; V1 endpoint + external order search under its own declared additional order budget; uniform ordered proposals; purely supervised non-energy task scorer; exact tiny-space oracle upper bound. A, B and C use the same one-shot target boundary.

**Required model comparisons:** A; B; C; a geometry-only learned variant of **each** arm (remove DINO features but keep supplied poses and shapes; identical discs are particularly vulnerable to visual shortcut claims); A with matched total trainable parameters; C without explicit cause–repair coupling (retrained, same labels); B without cause–repair coupling; A/C without intervention-effect supervision (matched root/label accounting); A/C without GRU; A/C no pair factors (retrained versus inference lesion kept distinct); without joint pool loss; without cost head; random/fixed order and altered factor graph topology with matched capacity. Explicitly distinguish **A vs C: adds explicit outcome variables/coupling**, **B vs C: recurrent higher-order order effect**, and **B vs B-no-coupling: graph causal structure**. Do not imply 'architecture advantage' if parameter count, labels, or search calls differ without controls.

**Primary:** verified complete target success / *all eligible initial episodes*, including abstain, abort, no witness and unresolved; number of distinct moves; normalized joint travel; wall/CPU and verifier/target calls. **Feasibility:** calibrated original no-repair accuracy/Brier/AUROC and coverage. **Explanations:** scene-effect sign and error, omission-effect sign and error, joint-minus-singleton residual, fixed-robot eligibility, nuisance false-positive rate, independently certified necessity separately. **Order:** same-endpoint decided pair ranking and proportion of held-out roots where a decided contrast exists. **Energy:** positive/negative ranking under finite pools, calibration, sampler stationary tests and chain mixing at 2D scale. **Costs:** predicted-versus-measured J on actual witnesses, not endpoint-distance correlations. Present root-cluster bootstrap intervals; an empty denominator is N/A.

**Decisive decision rule (freeze before test):** advance to 3D only when one architecture (or the geometric baseline) has a reproduced, independently verified sparse-and-held-out 2D pipeline and all three branches have been fairly attempted or honestly BLOCKED. Select by verified success first, then matched verifier compute and joint travel; require improvement versus strong geometry-only controls before calling learning useful. Use explanation and order gains as separately supported claims. If a more complex model does not improve relevant held-out metrics after matching cost/labels, prefer the simpler architecture. Do not choose based on lower training energy alone.

# 3D and long-horizon hold point

**No G7–G9 3D implementation or model selection before the 2D A/B/C decision report.** The existing conceptual 3D contract is preserved for later: pin actual full xArm7 + gripper assets and hashes, cupboard fixed roof/walls, upright supported 0.024 m radius x 0.075 m height cylinders, no vertical overflight, checked support-contact attachment/upright constraints, side grasp, and separate kinematic/dynamic/hardware statuses. Start 6–10 clutter objects in 3D; train anew before any transfer claim. G10 is a separate 3-action scripted **long-horizon integration** study, preserving achieved states and reporting suffix interference, with **no** learned future-plan-suffix energy or globally optimal TAMP claim in this revision. Physical hardware actuation requires separate authorization, calibration and contact/safety evidence.

# Falsification, negative outcomes and decision log

1. **No order contrast** -> neither 'learned order' nor superiority of GRU/order factors is established.
2. **No decided joint edit / omission labels** -> no supported explicit-causal coupling result for B/C.
3. **B/C only improves on extra training labels** -> cannot attribute the improvement to energy structure without coverage- and parameter-matched controls.
4. **Pairwise model represents all tested scenes** -> no demonstrated need for higher-order causal/order factors.
5. **Exact geometry/matching beats all learned methods** -> report that honestly, restrict novelty claim to evidence analysis if warranted.
6. **Boltzmann sampler fails detailed balance or mixes poorly** -> no sampling claim; use exact tiny solver/declared deterministic fallback for the diagnostic experiment.
7. **One-shot repair fails after commit** -> count failure, do not secretly retry target or rewrite the rank.
8. **Unknown source** -> never relabel as infeasible; record scope, budget and uncertainty reason.
9. **Unreliable explanation calibration** -> separate 'predicted effect' from 'verified necessity'.
10. **B/C energy collapses onto arbitrary explanation states** -> fail the variable-multiplicity, supervision and coupling controls.

# Version delta and retained contracts

**Changes relative to v1.6:** adds an explicit *three-arm 2D comparative scientific question*; formal B explanatory outcome variables $z$ and conditional joint energy $E_B(r,z)$; a C hybrid with GRU + causal coupling; precise distinction between B's joint Boltzmann **training** and A's learned feasibility energy plus search; exact marginalization/variable-dimension handling; intervention synergy labels; matched architectural/factor-graph/parameter ablations; and a mandatory 2D architecture decision before 3D.

**Unchanged:** initial-only observation, supplied GT masks and known geometry, full 3R physical verification, 48-candidate grasp family, canonical ordered move-once proposals, first-witness cost labels, GOAL_AND_SAFE_RETREAT, no-target-feedback-to-selection, eligible fixed-robot counterfactuals, omission semantics, unknown masking, root-level splits, authentic robot replay, and historical G4D/G4A findings. This report neither changes code nor closes G4D's missing-evidence gate.
