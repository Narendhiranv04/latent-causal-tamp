# Scientific reference — A / B / C latent causal infeasibility for corrective TAMP

**Status:** source-anchored presentation brief, 23 October 2026. Baseline implementation / evidence through commit `6aa4ba55a267e6dfaded8ba3a8e91369b6795443` (P9-L3); the later P9-L3c *instruction* is a proposal, not confirmed completed implementation. This reference is a presentation aid, **not** a replacement methodology. Prefer Methodology v1.8 and Implementation Guide v2.0 for broader definitions; refer to reports 0028–0033 for implemented changes and measured evidence. Distinguish the old P8 PoE architecture from the current proposed canonical P9-L3 **unique-factor root** implementation (`ABC9U_UNIQUE_V1`).

## 0. One-sentence research question and why three approaches

**Problem:** Given a robot's initial scene and a blocked target manipulation, predict **which obstacles should be moved, to which legal resting destinations, and in what order** so a complete corrective manipulation (including target action and safe retreat) can succeed, using **learned feasibility and counterfactual-outcome relationships** rather than invoking the motion planner for every hypothetical intervention.

The issue is **high-level causal/logical infeasibility** (blocking, occupancy, relocation dependencies, wrong order, omissions), not learning a continuous IK solver. **A** is an ordered, local sequence-score learner; **B** represents multiple physical and hypothetical success outcomes with an explicit conditional joint Boltzmann factor graph; **C** retains B's graph and substitutes a GRU for B's sequence-order representation. The scientific comparison asks whether explicit *dependencies between outcomes* earn their additional complexity beyond simply predicting each outcome.

A, B, C are **trainable** and implemented in 2D. B/C's canonical P9-L3 form is mathematically verified but not proven scientifically superior; none of the P9 revised models has yet been physically executed. The 3D extension is **planned, not implemented**.

## 1. Shared input, physical meaning and allowed information

Initial root context: `c0 = (initial object states and identities, 2D geometry/size, q0 and robot FK, goal, initial mask-pooled frozen DINOv2 features)` plus available supports/allowed resting regions and a candidate catalogue. Visual features are from initial views; DINOv2-small historically produces 384-D descriptors, projected to a smaller trainable visual representation and fused into width-128 object tokens. Exact dimension and backbone are **2D implementation details**, not the novel claim. Shared learner: object/robot/goal numeric encoding, local object tokens, static endpoint compatibility, candidate high-level action tokens, and a predicted witnessed relocation joint-travel cost J.

A proposed repair is a **discrete ordered candidate**

\[
r=[(o_1,d_1),\ldots,(o_m,d_m)],\qquad x_t(r)=\mathrm{apply\ first\ }t\mathrm{\ proposed\ pose\ changes\ to\ }x_0.
\]

Here `d_t` is a legal *object resting pose/cell proposal*, **not** a learned joint-space trajectory. Ideal prefix geometry `x_t` is constructed from the proposal; no ground-truth future robot state is given to the learner. A reversed ordering is a **different physical query** even with identical endpoints. Object displacement `C_d(r)` and number of moves `m(r)` are exact candidate properties. A separate head estimates first-witness robot-joint travel `J_hat(r)`; it is not the same as object displacement.

**Do NOT show as model features:** teacher collision outcomes, IK success, planner timeouts/branch choices, executed trajectories, post-edit image observations, target swept-volume oracle, ground-truth outcome bits, hidden root/split IDs. At *train-data generation*, the physics teacher/planner can produce labels. At *learned prediction*, A/B/C **do not call it**. In end-to-end execution, a shared physical planner may preflight ranked candidate relocations **before commitment**, then executes one committed repair and the target once, with no feedback-based retry after commitment.

## 2. Binary outcome definitions — not 'latent causal masks'

Conditioned on `c0` and a candidate repair catalogue, the explicit **stochastic nodes** are success/failure outcomes:

\[
 z_S=(z_0,\{z^S_I\}_{I\in Q_S}), \quad x_q\ (q\in Q_{\rm seq}),
\]

where a `q` is one canonical **complete ordered physical sequence query**, including sequences reused as omissions of longer ones.

| Outcome | Event encoded by value 1 | Physical/data meaning |
|---|---|---|
| `z0` | Target action from original `q0` succeeds | No relocation; `zR(empty) ≡ z0` |
| `zS[I]` | Target action succeeds after an instantaneous **hypothetical object-pose edit** `I`, with robot still at original `q0` | Counterfactual **target-only** query; does **not** prove robot can relocate objects |
| `zR[r]` (alias `x_q`) | Executing the entire proposed physical ordered repair and target, including safe retreat, succeeds | Full motion + task teacher label, not an IK-only label |
| `zO[r,t]` (alias `x_{r\\t}`) | A *new complete physical repair* formed by removing action `t` from `r`, then target and retreat, succeeds | Remove action, reconstruct every prefix with omitted objects unmoved; independently measured |

In B/C, **circles** are these binary outcome variables, **square/rectangular factor instances** carry learned potentials, and dashed scene/repair inputs are conditioning data. `z` are 0/1 **variables**; predictions are *marginal probabilities* from the joint. Their being called 'causal' reflects **intervention-defined queries and comparisons**, not a proof of a uniquely identified structural causal model.

A does not instantiate a joint `z` factor graph; it predicts outcome scores independently by rescoring each relevant scene edit or abbreviated repair.

Useful predictions/contrasts:

\[
 p_R(r)=P_\theta(x_{q_r}=1\mid c_0,\mathcal C), \quad
 p_I^S=P_\theta(z_I^S=1\mid c_0), \quad
 p_t^O=P_\theta(x_{q_{r\setminus t}}=1\mid c_0,\mathcal C),
\]

\[
 \widehat\Delta_I^S=p_I^S-p_0,\qquad
 \widehat\Delta_t^O=p_R(r)-p_t^O,\qquad
 \widehat\kappa_{A,B}=p_{A+B}^S-p_A^S-p_B^S+p_0.
\]

For a **toy illustrative** scene, `Y0=0, YA=0, YB=0, YA+B=1` yields complementarity `κ=+1`; actual P8 test `κ=+1` labels are only OPNEG-v1 policy-relative on one intervention side, **not** proved global impossibility.

## 3. Shared learnable **static** factor F1 (present in A, B, C)

\[
 E_{\rm static}(r,c_0)=\sum_i U_\theta(x_i(r),c_0)+\sum_{i<j}V_\theta(x_i(r),x_j(r),c_0).
\]

`U` learns unary object/endpoint compatibility. `V` learns pairwise simultaneous endpoint compatibility, symmetric to object-order swapping. Both provide local *static* plausibility signals; neither proves dynamic reachability, collision-free manipulation or feasible ordering. Neural local static factors are separately supervised with analytic endpoint validity labels (deduplicated across candidate order permutations). Sound analytic screens still apply at their warranted scope.

Crucial math: `E_static(r)` is constant for any fixed `r` as binary outcome vector `z` varies. Therefore it cancels from normalized **conditional** `P(z|r,c0)`, hence **conditional joint outcome NLL cannot train F1**. It needs its own supervised BCE. Likewise first-witness `J_hat` needs supervised cost regression.

## 4. Approach A — LOCAL-SEQUENCE (no joint outcome graph)

**Question answered:** Can we learn which **ordered candidate repair** will work from local object/endpoint interactions and its sequence of proposed ideal prefix states, without explicitly modeling statistical coupling between all hypothetical outcomes?

**Shared encoder:** initial object geometry + DINOv2 object features + robot initial state and target goal → object tokens / action tokens. For repair `r`, the model constructs `a_t = Enc(action_t, x_{t-1}(r), c0)`. It runs a GRU:

\[
 h_0=\tanh(H_0(\mathrm{ctx}(c_0))),\quad h_t=\mathrm{GRUCell}(a_t,h_{t-1}).
\]

Using final ideal object endpoints, it predicts a **repair-success logit**:

\[
 u_A(r)=f_{\rm task}([h_m;v_{\rm scene}(x_m(r))]),\quad
 p_A(r)=\sigma(u_A(r)).
\]

Its candidate scoring energy follows the implemented choice:

\[
 E_A^{\rm rank}(r)=E_{\rm static}(r)+T\,\operatorname{softplus}(-u_A(r))=E_{\rm static}(r)-T\log p_A(r),
\]

with `T=1` in the current shared implementation (some temperature calibration happens separately for selection). `J_hat_A(r) = softplus(Cost(h_m))` for nonempty repairs; zero by construction for empty repair.

**How A 'intervenes' in learned inference:** For an eligible hypothetical pose edit, recompute an edited **geometry-derived scene vector with the original q0** and evaluate the **same task head** with empty GRU sequence. For omission of action `t`, construct `r\setminus t` with the omitted object unchanged throughout prefixes and rerun the GRU scorer. It does not physically try either edit during prediction. These are **separate/factorized predictions**, not an explicit coupled joint probability over all outcome bits.

**What A learns:** shared appearance/geometry features, static unary/pair potentials, GRU-dependent ordered success score, feasibility of target-only edited scenes via re-scoring, omission outcome via re-scoring, a joint-travel readout. It does **not** learn: z-to-z coupling potentials, a normalized joint outcome distribution, a collision-free trajectory generator, a guaranteed minimal repair.

**A training:** For each root, deduplicate physical queries and mask undecided labels. Minimize **sum of Bernoulli NLL for distinct observed outcomes** (factorized root likelihood) + static BCE + witnessed log-Huber J. Current P9 comparisons use same observed-query access as B/C. AdamW updates parameters; gradients do not call IK/planner. This is not 'the joint Boltzmann NLL'.

**Strength:** simpler, order-sensitive, strong diagnostic baseline. **Limitation:** no explicit learned joint explanatory relationship between scene edits/complete and omitted repairs.

## 5. Approach B — JOINT-CAUSAL-EBM (unique-factor conditional Boltzmann graph)

**Question answered:** Can we learn a coherent **joint distribution of interventional and physical repair outcomes**, so the model captures relationships beyond independent success scores?

### 5.1 How the graph is built, step by step

1. Start with one original context `c0` and a **fixed, predeclared finite catalogue** of eligible hypothetical edits and candidate ordered repairs.
2. Create **one root-scoped** scene bit `z0`, one scene bit `zS[I]` per eligible edit (e.g. A, B, A+B), and **one sequence bit `x_q` per distinct canonical physical ordered repair**. Empty repair uses `z0`; omitted repairs are **aliases** of the physical sequences with that action removed, not independent copies.
3. Root scene factors F3/F5: each `zS[I]` and `z0` has a learned unary; `z0–zS[I]` gets a structured pair when enabled; generic scene-scene pairs and higher-order scene potential model e.g. `(zA,zB,zAB)`.
4. Each unique sequence query `q` gets **one F2 sequence unary** `-s_q x_q`, whether used as a full repair or an omission. `s_q` depends on learned order features, `q0`, original geometry, ideal prefix states and final positions. In B it uses **predecessor interaction pooling**, not a GRU.
5. Each distinct full-repair block gets F4 structured complete-versus-omitted pair factors; full coupled variants also get F5 generic scene–repair and omission–omission pair factors plus higher-order repair-block residuals. Exact duplicate candidate blocks are collapsed. **Current caveat:** role-specific blocks can still introduce new relational factors when an omission is newly listed as a full repair. This is the uncompleted proposed P9-L3c semantics refinement; do not claim full catalogue invariance.
6. F1 static endpoint potentials remain outside the normalized binary outcome graph and are trained by static BCE; the J readout is separate.

### 5.2 B learns ordered sequence scores without a GRU

For `a_t` representing each proposed action and ideal prefix:

\[
 b_t=\mathrm{MLP}_{\rm mix}\!\left(\left[a_t;\ \frac1{t-1}\sum_{u<t}\mathrm{MLP}_{\rm pair}([a_u;a_t])\right]\right)\ \ (t>1),
\]
\[
 b_1=\mathrm{MLP}_{\rm mix}([a_1;0]),\quad
 g_B(r)=\frac1m\sum_{t=1}^m b_t,\quad
 s_r=\mathrm{MLP}_{\rm order}([g_B(r);v_{\rm scene}(x_m(r))]).
\]

This is **order aware** because predecessor sets and ideal prefix tokens vary by order; it is not RNN/GRU. (The code averages the set of earlier action-token pair representations per step, then averages step rows.) Use `(m=0)` zero-vector handling in code; do not expand it on a slide.

### 5.3 Exact current joint Boltzmann formulation

Let `z_S` be root-level scene outcomes, `x=(x_q)_{q∈Q}` distinct physical repair outcomes and `\mathcal B` distinct repair blocks. First define the root scene energy from F3 and scene parts of F5:

\[
 E_S(z_S;c_0)=-s_S^\top z_S-\tfrac12 z_S^\top W_S z_S-H_S(z_S),\quad
 P_S(z_S\mid c_0)=\frac{e^{-E_S(z_S;c_0)/T}}{\sum_{z_S'}e^{-E_S(z_S';c_0)/T}}.
\]

The unique repair root energy is:

\[
 \boxed{E_Q(x,z_S;c_0,\mathcal C)=\sum_{q\in Q}(-s_qx_q)+\sum_{b\in\mathcal B}\left[-\tfrac12 z_b^\top W_b z_b-H_b(z_b)\right],\quad z_b=(z_S,x_{\sigma_b}).}
\]

`W_b` includes structured F4 `zR–zO` and enabled F5 generic pair terms; `H_b` is F5 higher-order (`B-full`, not structured or quadratic). The physical meaning of `q` is *one specific ordered sequence from the same original robot state*. Each unique physical success unary appears once. Repair-specific pair/higher-order instances are counted once per distinct repair block (see caveat above).

Root-consistent normalized joint distribution:

\[
 \boxed{P_B(z_S,x\mid c_0,\mathcal C)=P_S(z_S\mid c_0)\,\frac{e^{-E_Q(x,z_S;c_0,\mathcal C)/T}}{Z_Q(z_S;c_0,\mathcal C)},\quad Z_Q(z_S)=\sum_{x'}e^{-E_Q(x',z_S)/T}.}
\]

**Why conditional partition?** Summing over all repair outcomes recovers *exactly the same scene distribution `P_S`*, independent of which candidate repairs were enumerated. For fixed weights the scene marginal is root-consistent.

**What is a marginal?** `p_B(r)=Σ_{z_S,x: x_{q_r}=1} P_B(z_S,x|c0,C)`; `P(zR=1)` is not a raw energy or the partition of all z (which equals 1). Exact variable elimination computes observed-data likelihoods and marginal predictions. It is a legitimate Boltzmann-distributed **outcome** model; it is **not necessarily** a Boltzmann MCMC sampler over repair candidates.

### 5.4 B learns different things in each factor family

- **F1** unary/pair endpoint validity penalties (independently trained).
- **F2** the physically **ordered** full-repair success unary, using predecessor/prefix pairing.
- **F3** probabilities of original and edited-scene target-only success; structured pair relationship.
- **F4** omitted repair's success through the same physical sequence scorer, plus the distinct complete-versus-omitted **pair interaction**.
- **F5** extra scene–scene, scene–repair, omission–omission and higher-order **joint outcome** compatibilities, conditioned on input geometry and appropriate repair context.

Couplings are **learned conditional correlations**, not automatically a uniquely discovered causal DAG, universally necessary action, or motion-planning oracle.

### 5.5 B training (current P9-L3)

For each training root with observed labels `D_c` and missing labels marginalized:

\[
 \boxed{\mathcal L_B=-\frac1{|\mathcal R_{\rm obs}|}\sum_{c\in\mathcal R_{\rm obs}}\log P_B(D_c\mid c_0,\mathcal C_c)
 +\lambda_s\mathcal L_{\rm static}+\lambda_J\mathcal L_{\rm travel}.}
\]

Implementation uses `λ_s=λ_J=1`, static BCE on endpoint-deduplicated analytic labels and witnessed cost `Huber(log(1+J_hat),log(1+J_witness))`. UNKNOWN/NOT_RUN are **marginalized**; VERIFIED yes, sound scoped CERTIFIED no, OPNEG-v1 BUDGET_INFEASIBLE 0 **only as explicitly policy-relative**. Identity ties `zO[r,t]` to the same sequence `x_{r\\t}` and `zR(empty)` to `z0`. No automatic extra κ-MSE, intervention effect MSE or repeated BCEs.

**Why joint training:** the log probability of an observed *combination* of outcomes is differentiated through the joint energy and its normalizer, teaching compatible/incompatible configurations; no single factor necessarily gets separately identified by this objective. Finite-difference checks verify gradients where data provide support.

**Known limitation:** the structured `z0–zS` pair gets weak identification because saved roots with scene edits all have `z0=0`, and originally feasible roots have no edits; complementarity, order-swaps and omission necessity still need independently decided physical contrasts.

## 6. Approach C — HYBRID-JOINT (B's graph + A-style GRU order)

**Question answered:** Does a recurrent representation of action history make physical repair ordering more learnable while **retaining explicit joint intervention and omission outcome structure**?

C uses **exactly the same root/repair binary outcome variable definitions, F1/F3/F4/F5 factor families, raw potential instances, conditional normalizer and joint masked NLL as B** (model parameters are separately trained; sharing here means *design*, not tied B/C weights). Its only intended architectural replacement is **the F2 sequence encoder**:

\[
 h_0=\tanh(H_0(\mathrm{ctx}(c_0))),\quad h_t=\mathrm{GRUCell}(a_t,h_{t-1}),\quad
 g_C(r)=h_m,\quad s_r^C=\mathrm{MLP}_{\rm order}([g_C(r);v_{\rm scene}(x_m(r))]).
\]

The omitted sequence `r\setminus t` is **reconstructed and passed through the GRU afresh**, and its scored event aliases a full query for the same physical sequence. **Do not stack B's predecessor encoder on top of C's GRU** unless presenting an explicitly separate ablation.

\[
 P_C(z_S,x\mid c_0,\mathcal C)=P_S^C(z_S\mid c_0)\frac{\exp[-E_Q^C(x,z_S)/T]}{\sum_{x'}\exp[-E_Q^C(x',z_S)/T]}.
\]

Training `\mathcal L_C=\mathcal L_{\rm joint,C}^{\rm obs}+\mathcal L_{\rm static,C}+\mathcal L_{\rm travel,C}`. C is *not* A plus B as two separately added outcome networks: it is B with **A's type of sequence encoder** replacing B's order mechanism.

**Hypothesis:** long repair dependencies might suit GRU memory; **counterhypothesis:** B's explicit predecessor interactions may be simpler/easier to learn with sparse data. Existing P9-L3 C vs B validation differences are not conclusive and there is no new C full physical execution comparison.

## 7. Boltzmann feasibility, candidate selection and physical execution are three different stages

**Feasibility outcome prediction:** B/C infer `P(x_q=1)` via joint factor-graph marginals; A uses `σ(u_A)`. All use only known scene/candidate input (no planner/IK calls for hypothetical checks).

**Finite-catalogue ranking:** after sound analytic screens and calibration/admission threshold, compare candidate repairs lexicographically:

\[
 \boxed{(m(r),\ \widehat J(r),\ C_d(r),\ E_{\rm rank}(r),\ \text{deterministic ID})},\qquad
 E_{\rm rank}(r)=E_{\rm static}(r)-T_s\log p_R(r)
\]

(for uniform `ρ`; `T_s` is a ranking scale, not a claim that `r` is a stochastic node of B/C's outcome graph). In code `E_static+Tsoftplus(-logit p_R)` with `T=1`. **Fewest object moves** is an exact hard-first choice among admitted repairs, not a learned differentiable cost. `C_d` is exact proposed object displacement, `J_hat` is learned robot-joint travel. Boltzmann MCMC over candidate repairs is **not** required; deterministic enumeration and sorting were cheaper/more reliable in P8b.

**Physical step:** shared teacher/motion planner can *preflight fixed-order ranked repairs* using feasible grasps/trajectories, then commit first relocation witness; after commit, execute ordered relocation and a single target attempt with safe retreat, no feedback-based second candidate. If no executable repair or execution fails, episode fails/abstains under the defined protocol. The physical planner is used for ground truth and real execution, **not** for prediction-only simulated what-ifs.

## 8. Exactly what to claim to the professor (evidence split)

- **2D implementation:** A/B/C trained on saved oracle-labelled 2D geometry/object-centric features; P9-L3 unique-factor B/C exactly normalized, shared canonical variables; reported **375/375 tests**, 6 archived replays; 51 saved roots brute-force verified (max log-evidence error ~`3.9e-14`). Those are engineering facts, not task gains.
- **P9-L3 comparison:** B-full Unique validation root NLL ~0.289 vs PoE ~0.243 after matched 200 updates, C-full Unique ~0.223 vs PoE ~0.286; intervals cross zero, **predictive parity unresolved**. B-full unique 400-update validation ~0.065 vs PoE ~0.064; disclosed test diverges (~1.481 vs ~0.620), not a model-selection split. The validation is **12 roots**, 3 account for ~95% of unique B-full NLL. Do not claim significant superiority.
- **Factor value:** Unique B-full beats unique B-structured by ~0.33 validation root NLL, but the contrast removes multiple coupling components at once, with uncertain generalization and no proof of decision benefit.
- **P8d historical execution**, **not** newly executed P9: geometry+motion 9/12; old B-full 8/12; B-structured 7/12; uniform 7/12; A 6/12; SF 4/12. No learned arm won a root lost by G+M. **Only previous architecture was physically evaluated**, not updated Unique.
- **Intervention evidence gap:** κ=+1 test roots rely on an operational negative; independent positive proof/witness remains missing. Independent same-endpoint order contrast and omission necessity are insufficient in latest test. `z0–zS` pair poorly identified. No 3D execution, no hardware trials.
- **Ablation caution:** frozen DINOv2 features are actually used in 2D. Zero/shuffle changes predictions, but a capacity-matched geometry-only ablation remains needed for causal appearance benefit. **Retain vision pathway for 3D transfer**; optional Slot Attention is future work, not already in code.

## 9. Planned 3D transfer — the architectural invariants do NOT require 2D-only geometry

For M4M-style object rearrangement, add RGB-D/multiview object masks or proposals, DINOv2 pooled appearance features, depth/point-cloud/6-DoF pose/size/support/inside-outside features, and 3D legal resting poses. Optionally train a slot-based object-centric discovery module *if* instance segmentation/tracking are not supplied; **Slot Attention is an alternative object-discovery frontend, not a required replacement for DINOv2**. Adapt 3D teacher, grasp/placement/motion checks and analytic static constraints. The five factor jobs, discrete high-level repair semantics, `z0/zS/zR/zO` ontology, exact joint likelihood principle, and no-planner prediction remain conceptual design targets. 3D training/inference scaling and exact enumeration size require verification: **not built or demonstrated**.

## 10. Avoid these false claims

1. 'All three approaches are joint Boltzmann models' — false: A is factorized GRU and local ranking energy, B/C are joint Boltzmann over outcomes.
2. 'The factor graph nodes are obstacles and their displacements' — false for this outcome graph: variable nodes are **binary outcomes**. Objects/poses/actions are known conditioning inputs; local static endpoint potentials are not stochastic outcome nodes.
3. 'Intervention predicts that a robot can move the obstruction there' — false: `zS` is a fixed-robot target-only hypothetical teleport diagnostic; `zR` handles physical ordered feasibility.
4. 'Omission is action-count regularization' — false: it's an independent full-repair *outcome* for an omitted action.
5. 'Joint NLL trains F1 or J' — false for conditional outcome model; two separate auxiliaries required.
6. 'Predicted p is a binary z node' — false: z is 0/1 variable, p its marginal probability.
7. 'Training proves causal arrow discovery / universal necessity' — false; intervention-grounded conditional associations, scoped contrasts, not universal causal identification.
8. 'All P9 Unique predictions are catalogue-independent' — false: exact duplicate / no-new-factor aliases invariant, **genuine and role-specific added relational factors still change outcomes**.
9. 'The robot planner tests each hypothetical during model inference' — false; planner only used for independent labels and actual execution/precommit planning.
10. 'C = A plus B combined' — misleading: C inherits **B's joint factor graph** but *replaces* B order encoder with GRU.
11. 'DINOv2 is unnecessary/unused' — false; the vision pathway is implemented. 2D marginal advantage is not established; 3D extension is motivation.
12. '3D/Slot Attention tested already' — false.

### Sources for project handoff

- `latent_causal_tamp_methodology_v1_8.md` §§2–9.
- `latent_causal_tamp_implementation_guide_v2_0.md` (implementation contracts).
- `responses-phases/0028_P9_L0_source_and_likelihood_audit.md`, `0029_P9_L1_exact_joint_boltzmann_math.md`, `0030_P9_L2_saved_data_joint_objective_comparison.md`.
- `responses-phases/0031_P9_L3a_catalogue_and_inference_audit.md`, `0032_P9_L3a_unique_factor_mathematics.md`, `0033_P9_L3b_saved_data_model_comparison.md`, `P9_L3_DECISION.md`.
- Source code: `abc7_models.py`, `abc_models.py`, `abc7_train.py`, `joint_likelihood.py`, `unique_factor.py`, `p9_l3.py` at verified GitHub commit `6aa4ba5`.
- `responses-phases/0027_P8d_matched_oneshot_execution.md` (historical execution outcomes).

**Speaker framing:** "We first show that the model can represent and learn a coherent joint distribution. The next decisive question is whether its learned relational factors provide predictive and executed gains on physical ordering, complementarity and omission examples beyond simple geometric planning."
