# CLAUDE DESIGN — Build professor-pitch slides for Approaches A, B, C

**Paste this entire prompt into Claude Design and attach the two companion Markdown documents.** If the design workspace supports attachments, upload `ABC_Methods_Pitch_Scientific_Reference.md` and `ABC_Methods_Slide_Blueprint_and_Speaker_Notes.md`. Attach the bundled reference reports if useful. If you cannot access an attachment, say precisely which one is missing; do not silently invent mathematics.

## ROLE AND NON-NEGOTIABLE OUTPUT

Act as a scientific visualization designer, robotics researcher and meticulous technical illustrator. Create a polished, **professor-ready**, 16:9 presentation explaining **three approaches to learning high-level corrective task-and-motion-planning (TAMP) infeasibility**:

- **A — LOCAL-SEQUENCE:** object-centric static energies + GRU ordered repair success; outcome/edit/omission rescoring; **NO explicitly coupled joint outcome factor graph**.
- **B — JOINT-CAUSAL-EBM:** object-centric static energies + **explicit unique-factor joint Boltzmann outcome graph**, with predecessor/prefix interaction order encoder; five factor families F1–F5.
- **C — HYBRID-JOINT:** B's **same types** of variables, factors, joint Boltzmann distribution and training, but **B's prefix/predecessor sequence encoder is REPLACED by a GRU** (not stacked with it); C's learned weights are independently trained.

**Exactly SIX visible slides**, with **EXACTLY ONE complete core methodology slide devoted to A**, **ONE to B**, and **ONE to C**. Other three slides: shared problem/context; training/decision mechanics; current evidence, remaining validation and 3D extension. Optional at most two *hidden presenter-only appendix slides* for a dense worked numerical example/full factor glossary. Add rich presenter notes on all six slides and an unobtrusive notes toggle. Prioritize clear diagrams over wall-of-text slides; the provided reference has the full technical narrative.

**Output:** a self-contained, fully working **single HTML file** suitable for Chrome/Firefox on a Linux laptop, with SVG-based scientific diagrams, keyboard navigation, presenter-notes toggle, on-screen slide count, full-screen behavior where supported, and `@media print` rules that print one 16:9 slide per page. All content, fonts fallback and equations must render **offline**. Do not rely on remote image search, CDNs, external libraries or network calls. If exporting HTML is not possible in the Design workspace, produce the closest available slide artifact **while keeping the same content and slide rules**. Don't claim files or links exist unless you generated them.

## UPLOADED DOCUMENT AUTHORITY ORDER

1. **Scientific ground truth for the currently implemented 2D design:** `ABC_Methods_Pitch_Scientific_Reference.md`, including P9-L3 unique-factor updates; contains actual equations, variables, loss structure, implementation caveats and honest results.
2. **Exact slide texts, content limits, diagrams and talk track:** `ABC_Methods_Slide_Blueprint_and_Speaker_Notes.md`.
3. **Original project methodology:** `latent_causal_tamp_methodology_v1_8.md` and `latent_causal_tamp_implementation_guide_v2_0.md` if supplied. These predate P9-L3 and describe proposed root likelihood; where different, the **implemented P9-L3 reports/code** and the scientific reference take precedence for factual *implementation status*. Do not silently alter the original ideas.
4. **P9-L3 evidence:** reports `0031_P9_L3a_catalogue_and_inference_audit.md`, `0032_P9_L3a_unique_factor_mathematics.md`, `0033_P9_L3b_saved_data_model_comparison.md`, `P9_L3_DECISION.md`, and historical execution report `0027_P8d_matched_oneshot_execution.md` if attached.

Date/status: **23 October 2026**. Last *verified completed implementation* through GitHub commit **`6aa4ba5`**, P9-L3 `KEEP_UNIQUE`; the later P9-L3c **instruction document is not evidence that its proposed model freeze was executed**. Model architecture and presentation must reflect the verified P9-L3 code, not invent the next implementation stage.

## REQUIRED DECK CONTENT — NO SCIENTIFIC SHORTCUTS

### Visible Slide 1 — The blocked manipulation and shared inputs

A clear illustrative diagram of a 2D articulated robot, goal/target and two obstructing objects A/B, with named *proposed* relocation endpoints. Distinguish three outcome questions with exact labels:

- `z0`: target succeeds from original scene/robot `q0`?
- `zS[I]`: target succeeds after a *hypothetical pose edit* of objects with the **robot still at q0**? This is a fixed-robot target-only query.
- `zR[r]` / `zO[r,t]`: full **physically ordered** repair-and-target succeeds, or does it succeed if one move is omitted?

Show shared input schema: initial RGB-D/masks / frozen mask-pooled DINOv2 (initial appearance), object shape/pose and relations, robot `q0`+FK, goal, candidate ordered action/destination sequence. Ideal prefix object geometry is computed from the proposal, **not observed from execution**.

### Visible Slide 2 — Approach A

Make a big, easy-to-follow pipeline: object/robot inputs → action/prefix tokens → **GRU** → task logit `u_A` → `p_A=σ(u_A)`; branch to learned `E_static` and `J_hat`. Display three legible math equations:

`h_t=GRUCell(a_t,h_{t-1})`

`E_static=Σ_i U_i+Σ_{i<j}V_ij`

`E_A^rank=E_static−T log p_A(r)`

A's interventions: edit object geometry with unchanged original `q0`, rerun the same task scorer; omission: remove action, reconstruct ideal prefix states and rerun GRU. **A has no joint z-factor graph and no z-to-z coupling.** Train factorized Bernoulli NLL over *distinct observed physical queries* plus static BCE and witnessed travel log-Huber. Explain exactly what A learns vs does not learn in the speaker notes.

### Visible Slide 3 — Approach B (FLAGSHIP)

Draw a **genuine bipartite factor graph**, with binary outcomes as large circles, potential instances as smaller labeled squares, solid undirected factor-variable links and dashed conditioning feature inputs. Include scene circles (`z0`, `zS[A]`, `zS[B]`, `zS[A+B]`), repair circles (`x_A`, `x_B`, `x_{A→B}`, `x_{B→A}`), and clearly distinguish variable nodes from model *predicted probabilities*.

Show F1–F5 visibly on the slide:

- **F1 STATIC:** learned unary endpoint `U` and symmetric pair `V` on final proposed object poses, **OUTSIDE** the conditional binary outcome graph.
- **F2 ORDER:** one ordered physical query unary per distinct sequence, encoded by **predecessor/prefix pair interactions**. **No GRU in B.**
- **F3 SCENE:** unary outcome scores for original and hypothetical fixed-robot scene edits; structured `z0–zS` interactions.
- **F4 OMISSION:** the omitted sequence is recomputed and shares F2 scorer, plus a structured complete-versus-omitted outcome pair factor.
- **F5 COUPLING:** additional scene–scene, scene–repair, omission–omission pair and optional higher-order outcome compatibilities.

The graphic MUST make the distinction between **one physical query and multiple references**: one `x_q` circle and one sequence unary even if the same query occurs as one candidate's full repair and another candidate's omission. Scene prior `P_S` is root scoped. Distinct repair blocks carry their allowed relational potentials; note remaining role-specific coupling sensitivity honestly in speaker notes.

Show B's **current unique-factor** math, not old P8 or P9 PoE formula:

`E_Q(x,zS)= − Σ_{q∈Q} s_q x_q + Σ_{b∈B}[E_pair,b(z_b) + E_HO,b(z_b)]`

`P_B(zS,x)=P_S(zS) exp[−E_Q(x,zS)/T] / Σ_{x'} exp[−E_Q(x',zS)/T]`

Equations should be real SVG/HTML typeset, at least 32 px equivalent on a 1920×1080 slide. **Do not use** `P_S · Π_r P_Q,r / Z_eq` as the *current* model: that is the **previous PoE baseline**.

Explain in notes **how the factor graph is constructed** from a *predeclared* finite hypothetical-edit + candidate repair catalogue and why it represents correlations rather than learned directed causal arrows. Write B's predecessor-interaction formula in notes with order-sensitive token pooling; mention exact variable elimination computes marginal probabilities and masked observed-data likelihood.

### Visible Slide 4 — Approach C

Visual reuse of B's graph should be obvious (show the same factor graph faded/compact, not redraw an unrelated graph). Highlight **replace F2 only**:

`B: action token + predecessor interaction pooling → g_B`

`C: a1...am → GRUCell sequence → g_C`

`g_C=h_m`, `s_q^C=f_order([g_C;v_scene(x_m)])`

`P_C(zS,x)=P_S^C(zS) exp[−E_Q^C/T] / Z_Q^C(zS)`

Show rebuilt omitted candidate `r\t` goes through the GRU again. Keep B's outcome nodes, F3/F4/F5 couplings, F1 local static and the joint training. Do **not** claim B's F2 and GRU are combined. Do **not** say C is A+B; it is B's graph **with a replacement sequence encoder**.

### Visible Slide 5 — One coherent training, prediction and execution pipeline

Make three visually isolated stages:

1. Offline training labels from teacher **may call IK/planner** for ground truth. Target-only teleport edit remains from fixed `q0`. Full ordered repair+target+retreat has a different independently tested scope. Statuses VERIFIED / CERTIFIED / OPNEG-v1 policy negative / UNKNOWN / NOT_RUN have distinct meanings.
2. Model fits **exact masked root observed-data NLL** for B/C, while UNKNOWN and NOT_RUN bits are summed/marginalized. Alias queries appear once as a variable and label. F1 gets separate static BCE because an `r`-only static energy cancels in conditional `P(z|r)`. `J_hat` gets witnessed log-Huber regression. For A, the outcome term is factorized Bernoulli NLL.
3. At inference, model computes repair/scene/omission outcome probabilities with **NO IK/planner**; static analytic screening and calibrated admission; select lexicographically by move count, predicted joint travel, exact object displacement and success-conditioned ranking energy; motion planner then handles precommit path feasibility and physical execution of the committed candidate, with a single post-commit target attempt.

**Two key equations, readable:**

`L_B/C=−(1/N) Σ_c log Pθ(D_c) + λ_s L_static BCE + λ_J L_logHuber(J)`

`rank(r)=lex(m(r), J_hat(r), C_d(r), E_static(r)−T_s log p_R(r))`.

Explicit note `No additional κ loss or effect MSE by default; the goal is to learn through the joint outcome likelihood.`

### Visible Slide 6 — Truthful empirical status and transfer to 3D

Do NOT make the pitch read as though A/B/C already beat the motion planner.

Show a small, honest evidence chart of **historical P8d** 2D executed successes:

`Geometry+Motion 9/12`, `old B-full 8/12`, `old B-structured 7/12`, `Uniform 7/12`, `A 6/12`, `SF 4/12`.

Put beside it **P9-L3 engineering**: current unique-factor inference mathematically exact; **375 tests passed**, 6 replays; verified brute force on 51 saved roots; *no physical execution of new unique models*.

Clearly state still missing scientific evidence: proof-grounded complementarity κ=+1, same-endpoint physically decided order swaps, independently decided omission necessity, ablations on unseen scene-generation families, and stronger than G+M end-to-end benefit. Mark few-scene / operational-label caveats; 12 validation roots are too few for strong model comparisons.

Then an unobtrusive 3D extension ribbon:

`2D object/mask/pose encoder → 3D RGB-D + multi-view/6DoF/shape/support + DINOv2 object features (Slot Attention optional) → unchanged A/B/C factor semantics → 3D ground-truth teacher and execution`.

**3D IS PLANNED**, not implemented. Preserve DINOv2 in the design and do not portray Slot Attention as mandatory or existing.

End with one highlighted research question: **"Can explicit learned intervention, omission and order couplings improve corrective TAMP beyond geometry-only screening and sequence scoring?"**

## VISUAL LANGUAGE / STYLE

- Intent: a technically rigorous, high-end academic lab presentation; restrained and highly legible, not marketing, not a dense paper screenshot.
- Use a bright neutral background (warm white `#FAFAF8`), ink `#152331`, subtle thin dividers; use **A amber**, **B cobalt**, **C muted purple** as accents. F1–F5 use a restrained repeatable legend, not rainbow confetti.
- 16:9 slide canvas, accessible text contrast. Recommended: main headings 40–56 px, equation display 28–36 px, body 22–28 px; legends may be 17–20 px but not smaller. Prefer **enlarging SVG diagrams and reducing body text** to minuscule formulas.
- Core scientific diagrams must use semantically meaningful layout and good orthogonal routing. Factor nodes are squares, random-outcome nodes circles; boxes with rounded corners only for conditioning inputs and layer modules. Avoid excessive crossing edges: use scoped panels and light visual guide lines.
- Use gentle reveal animation only when it improves teaching (e.g. graph nodes → factors → probability, or B predecessor → C GRU). Provide a reduce-motion setting and a static fully revealed print version.
- Keep one core message per slide. Split detailed caveats into speaker notes; slide body should remain scannable in 10 seconds.
- No stock robots, no fictional photographs or simulator frames. An illustrated geometry diagram is permitted **only if clearly labeled illustrative**.
- Sources and status line in small readable footer: `Methods: verified P9-L3 (6aa4ba5) | Historic executed P8d | 3D: proposed`.

## PRESENTER NOTES / TEACHING REQUIREMENTS

The slides must teach a skeptical robotics professor, not just decorate headings. Copy the detailed talking points from the supplied blueprint into a presenter-notes overlay (presenter-only) for each slide, including:

- Precise input and output definition (what's learned vs held fixed).
- How labels are obtained and why operational negatives are policy-relative.
- A's independent/GRU approach and why it is not B's joint graph.
- Complete factor F1–F5 definitions, their scopes and interpretations; explicit B graph construction steps.
- B's predecessor encoder equation vs C's GRU equation.
- Boltzmann normalization and marginalization (not simply `sigmoid` all factors); root scene consistency.
- Loss: one primary NLL + two mathematically necessary auxiliaries, fair factorized A comparator.
- Counterfactual scene edit vs physical repair omission; κ and omission-effect arithmetic.
- Actual ranking and what **does not** get learned (no IK, paths, arbitrary destinations, causal DAG, universal necessity).
- What current results do and do not support, how 3D can reuse object-centric inputs/factors.

Presenter notes should run approximately **8–12 minutes in total** when read aloud at normal technical presentation speed. Include `Q&A` with at least eight tough professor questions / scientifically honest answers (can be in hidden panel, not as visible slides), taking the Q&A from the blueprint.

## ROBUSTNESS / QUALITY GATE BEFORE FINAL ARTIFACT

Do an internal content and rendering audit, make changes, then deliver:

1. Exactly six visible slides; exactly one each for A/B/C.
2. All five factor families covered accurately; B/C variable/factor graph truly bipartite and readable.
3. Equations reflect current **unique-factor** root Boltzmann distribution rather than old PoE; static outside outcome partition.
4. A factorized, B no GRU, C GRU **replaces** B order module.
5. Output outcome labels and marginals mathematically distinct; alias identity and fixed-q0 scene edit stated accurately.
6. No planner/IK call while *predicting* interventions; correct training-label and real-execution exceptions.
7. Historical execution results and current unique-model status are **not conflated**.
8. Slides look convincing at 1920×1080 and on a 13–16 inch laptop; print preview not clipped; formulas never overflow; no overlapping diagram labels/edges.
9. No made-up numeric experiments or citation claims; future 3D/slot attention as a design path only.
10. HTML works offline (all CSS, JS and SVG bundled) with keyboard navigation, presenter notes toggle and print layout.

**Conclude with the delivered file and a short note listing the six slides and what is in the presenter notes. Do not replace the deck with a long written essay.**
