# Slide blueprint and professor-pitch speaker notes

**Use with:** `ABC_Methods_Pitch_Scientific_Reference.md` and `Claude_Design_ABC_Methods_Pitch_Prompt.md`.

**Deck contract:** SIX visible 16:9 slides, **exactly one core slide for A, one for B, one for C**, plus shared problem, shared learning/inference, and honest evidence/3D outlook. Optional **two hidden appendix slides** via a clearly separate presenter-only navigation link; do not expand core methods into multiple ordinary slides. All method detail beyond comfortably readable screen density belongs in hidden speaker notes/presenter panel, not in tiny-font slide body.

**Build all graphics as actual SVG/HTML elements**; no generic stock photography; no AI depiction of a real robot as experimental evidence. Architecture arrows and graphs must be explicit, not decorative. Each slide can have a small top-left `A / B / C` label and one large highlighted one-line claim. Use a shared toy scene that is clearly tagged `Illustrative / NOT measured`, not screenshots passed off as real physics.

---

## Slide 1 — The task: predict what to move, where, and in what order

**Title:** From infeasible manipulation to an ordered minimal repair

**Takeaway / subtitle:** Learn to predict the consequences of high-level corrective actions **without planning every hypothetical intervention**.

**Layout:** Left ~42%: elegant vector scene: 2D robot base/links, target region, two obstacles A and B, two candidate destination pads, dashed proposed routes as *symbolic* arrows (not actual verified robot trajectories). Right ~58%: compact 3-step pipeline plus clearly distinguished questions.

Pipeline:

`Initial scene + q0 + target` → `Candidate ordered object relocations` → `Predicted feasibility + select` → `Motion planning/execute selected repair`.

Three questions shown as small anchored chips, not prose blocks:
- `zS[I]`: Would the original target work if objects were **hypothetically relocated, robot still at q0**?
- `zR[r]`: Would the **full physically executed ordered repair + target + retreat** work?
- `zO[r,t]`: Would the **complete repair with action t removed** work?

On-slide bottom strip: `Shared inputs: object-centric DINOv2 + pose/shape + q0/FK + goal + ordered candidate destinations`.

**Speaker notes (~50–90 seconds):** Our failure mode is task-level obstruction, not local IK optimization. We propose legal object relocation destinations and candidate action sequences. The model learns which sequences restore target feasibility and whether each step is unnecessary. There are **two different kinds of counterfactual**: a target-only teleport edit that keeps q0 fixed, and a fully physical ordered removal/omission query that a training teacher can evaluate. Neither learned prediction calls IK at inference. Robot motion planning is still needed for ground-truth labels and eventual physical execution. We do not claim to learn an arbitrary continuous destination generator or universal minimal repair. This 2D framework is a proof of concept for object-centric 3D manipulation later.

**Never show:** target success from a hypothetical edit as guaranteed executable relocation.

---

## Slide 2 — Approach A: LOCAL-SEQUENCE (GRU + local static energy)

**Headline:** A learns a repair success score **directly from the ordered action sequence**.

**Diagram:**

`Initial object tokens (geometry + frozen DINOv2)` + `(q0, goal)` → `proposed prefix-state action tokens a1…am` → **GRU** → `h_m` → `task logit uA` → `pA = sigmoid(uA)`.

Two real side branches (not fictional modules):
- `Final endpoint x_m` → `static unary U_i + symmetric pair V_ij` → `E_static` (trained BCE)
- `GRU summary h_m` → `cost head` → `J_hat` (trained witnessed travel)

Under a divider label `A's what-ifs = rescore (not a joint factor graph)`, two tiny paths:
`edit object poses, q0 fixed → same task head` ; `remove an action → rebuild prefixes → same GRU`.

**On-slide equations (large, maximum three):**

\[
h_t=\mathrm{GRU}(a_t,h_{t-1}),\qquad p_A(r)=\sigma(u_A(r))
\]
\[
E_{\rm static}=\sum_i U_i+\sum_{i<j}V_{ij}
\]
\[
E_A^{\rm rank}=E_{\rm static}-T\log p_A(r),\quad \widehat J_A=\mathrm{softplus}(f_J(h_m))
\]

**Footer:** `Learns: geometry/appearance embeddings, local endpoint validity, sequence feasibility, edited-scene and omission predictions by rescoring, travel. Does NOT learn: joint outcome couplings.`

**Speaker notes (~90–120 seconds):** A establishes whether an explicitly ordered GRU plus local static factors is enough. Each input action encodes intended object relocation and ideal object-only prefix geometry. The GRU consumes actions in sequence, so A→B and B→A can yield different states. `u_A` predicts feasibility, trained with BCE on decided query outcomes. For a fixed robot target-only intervention, it does not re-render physics; it modifies known object geometry and re-evaluates the same task head, with an empty sequence. For omission, it reconstructs the shorter sequence and reevaluates the GRU. These are separate scores, not a normalized joint distribution over all potential outcomes. The static energy is learned with analytic validity BCE. The first-witness robot-joint travel head is separately trained. Candidate selection still uses threshold/screen and lexicographic move count, J, object displacement and ranking energy.

**Professor's key question:** “How is A more than a classifier?” Answer: order-aware *sequence scoring* with learned static energies and counterfactual rescoring, but it remains our simpler baseline for testing whether explicit joint coupling adds anything.

---

## Slide 3 — Approach B: JOINT-CAUSAL-EBM (explicit factor graph)

**Headline:** B assigns joint probabilities to **combinations of original, edited, full-repair and omitted-repair outcomes**.

**This is the flagship / most important slide.** Make the factor graph large enough to read with a **true bipartite layout**:

Top row root scene binary circular nodes: `z0`, `zS[A]`, `zS[B]`, `zS[A+B]`.
Bottom row ordered query outcome circular nodes: `x_A`, `x_B`, `x_{A→B}`, `x_{B→A}`.
Small square factor instances: `scene unary (F3)`, `scene interaction (F3/F5)`, `ordered query unary (F2)`, `full↔omitted (F4)`, `scene↔repair / higher-order (F5)`.

A separate **F1 static panel** is linked via dashed conditioning, not an edge to an outcome circle: `final poses → U_i / V_ij → E_static`.

Right-hand slim vertical 5-factor legend (5 colored labels F1..F5) with 3–5-word role descriptions.

Below graph, two key equations (only the **essential two**, notes hold expansions):

\[
E_Q=-\sum_{q\in Q}s_q x_q +\sum_{b\in\mathcal B}[E_{\mathrm{pair},b}+E_{\mathrm{HO},b}]
\]
\[
P_B(z_S,x)=P_S(z_S)\,\frac{e^{-E_Q(x,z_S)/T}}{\sum_{x'}e^{-E_Q(x',z_S)/T}}
\]

**One prominently framed inline fact:** `One binary variable + one sequence unary per distinct physical ordered query. A full repair and the same repair occurring as an omission are the SAME outcome variable.`

**Speaker notes (~150–210 seconds):** Explain variables vs factors first. A factor graph here has outcome circles representing 0/1 teacher-defined events, not object nodes. Scene geometry, the proposed order and destinations are known conditioning inputs. `z0` asks whether the original target succeeds, `zS` asks target-only success with object pose edits while robot q0 remains unchanged, `x_A` asks full physical execution of the A-only repair; `x_{A→B}` is a different physically ordered event. F1 is a learned local static energy outside the normalized outcome distribution. F2 learns order-sensitive sequence unary using **predecessor pair interactions, not a GRU**. F3 predicts scene-edit success, and includes original–edited pairs. F4 relates full repair to omitted repair and uses the same sequence scorer for the omitted query. F5 introduces generic and higher-order couplings across outcomes. The joint energy assigns higher/lower compatibility to whole binary outcome configurations; probabilities come from exact normalized Boltzmann sums. Root scene beliefs must stay fixed when the repair catalogue changes. The P9-L3 unique-factor model counts one query unary once; it also has relational factors per distinct repair block, which can still change predictions when a genuinely new role-specific coupling appears. Do not claim full catalogue independence or identified directed causes. B's order representation is the average of prefix-conditioned pairwise predecessor features, not sequential hidden-state propagation.

**Toy illustration (speaker notes, optional in small sidebar):** With Y0=0, YA=0, YB=0, YA+B=1, κ=+1. This is a **conceptual label pattern**, not a certified P9 result.

**Professor's key questions:**
- “What is latent?” The neural scene, action and factor embeddings; the explicit outcome variables are binary and observed/missing, not latent arrows.
- “Where does the graph come from?” Deterministically instantiate typed outcome variables and factor scopes from the eligible scene-edit catalogue and physically distinct repair/omission queries; neural networks *learn factor values*, not the underlying variable ontology or candidate catalogue.
- “What makes it causal?” Intervention-grounded prediction contrasts; this alone is not causal-graph identification.

---

## Slide 4 — Approach C: HYBRID-JOINT (B's graph, GRU order)

**Headline:** C holds the outcome graph fixed and tests whether **GRU action memory** improves order reasoning.

**Diagram:** top central `B's joint graph (z0, zS, zR/zO; F1, F3, F4, F5 unchanged)` with a highlighted removable F2 plug. Left small panel `B's F2: prefix/predecessor pair pooling`; arrow `REPLACE`, not `ADD`; right panel `C's F2: action tokens → GRU → g_C → success unary s_q`. Connect C encoder output into same `query unary` factor location and omit subquery rescoring.

**Equations:**

\[
h_t=\mathrm{GRUCell}(a_t,h_{t-1}),\quad g_C=h_m,\quad s_q^C=f_{\rm order}([g_C;v_{\rm scene}(x_m)])
\]
\[
P_C(z_S,x)=P_S^C(z_S)\frac{e^{-E_Q^C(x,z_S)/T}}{Z_Q^C(z_S)}
\]

**On-slide 2-column contrast (2 lines only):** `B order: explicit predecessor interactions` vs `C order: recurrent sequence memory`; `B & C explanation model: identical factor types and outcome ontology`.

**Footer:** `Do not say 'C = A + B'. It is B's factor graph with A-style GRU sequencing replacing B's order encoder.`

**Speaker notes (~100–140 seconds):** C isolates a hypothesis: explicit pair-pooling may miss or poorly summarize long dependencies, whereas a GRU can retain order history. Apart from that switch, B and C use the same binary variables, conditional normalized Boltzmann likelihood, static endpoint supervision, travel head, omission relation factors and generic couplings. For an omitted action, rebuild the shortened sequence and re-run C's GRU. The same physical query receives one binary outcome and one unary in the current unique-factor model. We train C separately with the same root data and masks. Existing 2D P9-L3 B-vs-C differences are statistically unresolved; no physical C-full win has been demonstrated. This is a clean architecture hypothesis, not a victory claim.

---

## Slide 5 — Training, factor formation and deployment: ONE methodological loop

**Title:** Training teaches outcomes; inference predicts interventions; execution uses the robot planner once committed

**Left visual:** Three partitions, separated by thick vertical dividers and labels:

1. **OFFLINE TEACHER (labels only)**: initial scene & proposed counterfactuals → target-only teleport checks or independent complete ordered repair checks → evidence `VERIFIED/CERTIFIED/BUDGET_INFEASIBLE/UNKNOWN/NOT_RUN` (status provenance noted; no oracle labels at inference).
2. **LEARNED ENERGY TRAINING**: input + observed mask → root graph & energies → exact normalization/marginalization → observed-data NLL and necessary static/travel auxiliaries → AdamW.
3. **INFERENCE / EXECUTION**: new initial observation + catalogue → predictions with **zero IK/planner calls** → analytic screens + threshold → lexicographic sort → shared physical precommit planning / committed execution; after commitment one target attempt.

**Primary equation big:**

\[
\mathcal L_{B/C}=\underbrace{-\tfrac1N\sum_c\log P_\theta(D_c)}_{\rm joint\ observed\ outcome\ NLL}\; +\; \lambda_s\underbrace{\mathcal L_{\rm static\ BCE}}_{\rm F1}\; +\;\lambda_J\underbrace{\mathcal L_{\log(1+J)\rm\ Huber}}_{\rm travel}
\]

**Small explicit A note:** `A replaces joint outcome NLL with factorized Bernoulli NLL on the same distinct decided queries.`

**Small ranking equation:**

\[
\mathrm{rank}(r)=\mathrm{lexicographic}\big(m(r),\widehat J(r),C_d(r),E_{\rm static}(r)-T_s\log p_R(r)\big)
\]

**Bottom 3 pills:** `Unknown labels = marginalized`, `Candidate-only E_static cancels from joint conditional NLL`, `No κ auxiliary loss by default`.

**Speaker notes (~120–160 seconds):** One independently labeled physical query becomes one observed binary event. Teacher may invoke full IK/planner offline for physical repair and target feasibility and a target-only planner for hypothetical pose edits; a budget-negative is policy-relative, not a universal proof. The observed-data NLL marginalizes unknown bits and ties alias queries. It trains the coupled outcome factors through their joint normalization. Because static energy depends on candidate endpoints but not on binary z, adding it uniformly to all z configurations cannot train F1 from the conditional NLL; a separate analytic-label BCE is necessary. J is independently supervised using log-Huber on actual *first relocation witness* joint-travel, never using a guessed trajectory. There are three main terms, not seven overlapping outcome losses. A instead uses factorized likelihood. At prediction, perform no checks by planner; at execution a common motion planner can try candidate fixed orders before commitment (do not falsely say it must be exactly one planner call), but there is no feedback-based second candidate after committed execution. The model predicts a repair's feasibility; the motion planner is the final physical actuator and validator.

---

## Slide 6 — What has been demonstrated and why 3D matters

**Headline:** Mechanism implemented; causal-repair advantage still must be proved.

**Layout:** Left ~52% clean comparison with **historical P8d** executed 2D success (no decorative bar exaggeration): `G+M 9/12`, `Old B-full 8/12`, `Old B-structured 7/12`, `A 6/12`, optional `Uniform 7/12` / `SF 4/12` tiny footnote. Below: `P9-L3 unique-factor: 375 tests, exact factor inference, NO fresh robot execution.` Avoid writing that new B/C achieved 8/12 (these were old P8 checkpoints).

Right ~48% horizon diagram:

`2D objects/masks + poses + q0 + goal` → `3D RGB-D / multi-view + object masks (DINOv2, optional slot discovery) + 6-DoF poses/shapes/supports` → `same A/B/C factors and z outcomes` → `3D physical teacher/execution`.

**Bottom readiness / evidence matrix**, three terse rows:
`Needs physical proof: κ complementarity; same-endpoint order swaps; omission necessity`;
`Needs evaluation: independent constructor families, factor-removal, fresh one-shot G+M comparison`;
`Preserve: original five factor families, DINOv2 as 3D-capable perception route`.

**Speaker notes (~90–150 seconds):** The essential contributions at this stage are engineering and modeling: exact root-consistent conditional inference, one physical query per outcome variable, no double-counted unary across aliases, a clean three-term loss, and frozen initial object-centric input. We have NOT yet shown improved execution success over G+M; the earlier physical baseline remains strongest. Under P9-L3 Unique vs PoE, predictive differences are inconclusive on 12 validation roots, and 3 roots account for 95% of B-full validation NLL. The scarce positive-complementarity cases are operational-label dependent. Before publication-level claims we need targeted physical counterfactual outcomes and independently verified ordering/omission tests, then factor ablations and matched one-shot execution. Extending to 3D requires better perception + 3D geometry + appropriate physical teacher, not inventing a new factor ontology: frozen DINOv2 is already in the 2D code, Slot Attention is optional and not implemented. End with precise question for the professor: **Do the joint factors earn their complexity by learning useful causal repair dependencies beyond analytic geometry screens and an order-aware classifier?**

---

## Hidden appendix (only if the medium supports it)

### Backup A — Complete energy-factor inventory

Show `F1` static unary/pair; `F2` B predecessor vs C GRU sequence unary; `F3` scene unary + z0/zS pair; `F4` rescore omission via same F2 unary + full/omitted pair; `F5` generic pairs/higher-order. Equation `P_S * exp(-E_Q)/Z(z_S)`. Show one instance per canonical query unary, not one per slot occurrence. Show root-level `P_S` + repair graph factor separation.

### Backup B — Full mathematical worked toy

Use **illustrative** `Y0=YA=YB=0,YAB=1, κ=1`; order `r1=A→B` and `r2=B→A` are distinct physical queries; omissions `r1\A=B`, `r1\B=A` are query aliases if those full queries are also listed. Express `\Delta_O` and `\kappa`, but DO NOT claim this exact vector has already been witnessed physically. Include effect labels and status/provenance distinction; note complete ordered target+retreat for repair outcomes.

---

## Professor Q&A — concise, defensible answers

**Q1. Why latent?** Latent *learned representations* parameterize energy factors for unseen geometric configurations; the outcome nodes themselves are explicitly binary. Factor identities and candidate repairs are constructed, not discovered latent causal arrows.

**Q2. Why a joint Boltzmann model if A can predict feasibility?** B/C hypothesize that learning compatibilities between intervention/repair/omission outcomes aids generalization when the same scene contains dependent ways of succeeding/failing. That incremental value has not yet been proven in execution.

**Q3. Exactly how is B's factor graph formed?** Given root scene and candidate repair catalogue, create scene outcomes once and unique ordered physical queries once; instantiate typed scene, sequence, omission, generic pair/higher-order factors from observed geometry; score all binary assignments and normalize conditionally on the scene variables. No planner during learned inference.

**Q4. Why conditional normalization?** Guarantees a common scene prior `P_S` across different repair catalogues. The unique-factor conditional model also removes duplicated query unaries; some role-specific block factors still legitimately change model predictions.

**Q5. Are factor nodes learned or manually defined?** Factor **families and their scopes** are manually declared; neural potentials and embeddings are learned. The model doesn't invent new graph topology through backprop.

**Q6. How is ordering represented?** A/C: GRU over ordered prefix tokens; B: predecessor-interaction pooling over tokens before each action. Same endpoints, different order, different query identities and possible predictions.

**Q7. Is displacement itself learned?** No arbitrary action destinations or continuous trajectories generated. Destinations come from legal proposals. Their final positions and order affect learned scores; `m` and exact object displacement `C_d` are ranking criteria; `J_hat` estimates physical joint travel from supervised witnesses.

**Q8. Do interventions call IK/planner at inference?** No. Teacher data labels do offline. Execution may motion-plan ranked physical repairs before commitment and will physically execute a committed repair once.

**Q9. Are 'causal factors' mathematically proven causal?** No. The intervention definitions support scoped causal *effect comparisons*, but factor interactions can be confounded/capacity-substitutable; independent decided interventions and matched execution are required.

**Q10. Why three objective terms?** Outcome conditional NLL cannot train an energy independent of outcomes (`E_static` cancels); travel cost is outside the outcome graph. Therefore two separately supervised auxiliaries are necessary; A uses factorized rather than joint observed outcome NLL.

**Q11. Why keep DINOv2 if geometry-only tests looked good?** It is already used and is a natural 3D object-centric perception route. The 2D empirical benefit of appearance beyond supplied geometry is not yet established; do not claim it is.

**Q12. What is novel today?** The intended contribution is intervention-grounded outcome coupling and ordered causal repair inference. The verified current result is a sound implemented probabilistic representation; application-level novelty must still be supported by prospective physical evidence and baselines.

---

## QA checklist for the generated slide artifact

- Exactly 6 visible slides, with one main full slide each A/B/C.
- Every slide has speaker notes or presenter-only expanded explanations.
- A slide explicitly says **no joint outcome graph**.
- B/C slide depicts a **bipartite factor graph** (outcomes = circles, factors = squares); `F1` outside the binary graph.
- Includes all F1–F5 with correct scopes and a clear B-vs-C replacement, not addition.
- Displays exact `P_U=P_S * exp(-E_Q)/Z_Q(z_S)` and exact masked-NLL + static BCE + travel loss.
- Clearly distinguishes hypothetical scene teleport vs physically executable repair.
- No planner/IK as an input to learned prediction; no oracle posterior used in ranking.
- Candidate selection: confidence/static admission, lexicographic `m, J_hat, C_d, E_rank`.
- Reports P8d **old** execution results honestly; does not claim new unique model executed.
- Marks positive κ examples as *illustrative* if invented or policy-relative if from P8.
- 3D extension explicitly future, Slot Attention optional, no false 3D results.
- All equations legible; notes get detail, slide body gets visual hierarchy.
