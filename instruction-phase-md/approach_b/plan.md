# Approach B — Final Implementation Plan

**Status:** implementation contract / work plan; **not** authorization to train or execute new physical queries. Dataset-readiness work is owned entirely by the separate `FINAL_READINESS_GATE` job; no duplicate P0 phase.  
**Prepared:** 12 November 2026  
**Scope:** conditional placement proposals, root-consistent X/Y Boltzmann learning, witnessed travel cost, and branch-local dynamic corrective search, for the current 2D and 3D benchmarks. External paper baselines and a two-opposed-shelf extension are downstream work, not prerequisites for this implementation.

## 0. Authority, current evidence, and the finish line

### Source-of-truth precedence

1. **Scientific contract:** `final-fixed-methodology-1.pdf` (5 November 2026), especially §§1–2, 5–16 and Appendices A–C. Its pairwise *root-consistent* X/Y probability model overrides older, incompatible energy formulations.
2. **Existing verified implementation:** reuse the actual source and tests for `bxy_core.py`, `bxy_p11.py`, `bxy_p17.py`, `bxy_teacher.py`, and the P26–P28 universal search modules when available. Audit current checkout and pinned commits; never assume a pathname or module is available merely because a report names it.
3. **Current dataset:** freeze the newest valid 2D selection at **5,000** and the reported 3D V4 selection at **2,500** main K≤3 scenes, with nine K4 examples separate. The older final-fixed document assumed a 5,000-scene 3D basis, **superseded by the later 2,500-scene 3D protocol**. Consume the final hash-verified V4 and `FINAL_READINESS_GATE` artifacts before using any training rows. The user-reported 3D V4 contains K0=511, K1=357, K2=612, K3=612, NONE=408. These are expected counts, **not a substitute for validating the local manifest**.
4. **Historical evidence:** preserve all old model checkpoints, P24 confirmation/test evidence, original V2/V3 selections, legacy complete-task labels, placement-Q2 data, and baseline results without editing. Historic teacher success ≠ finalized X or Y.

**Definition of done:** an externally auditable pipeline independently (a) proposes physical placement candidates, (b) predicts joint outcomes of *entire ordered* corrections and corresponding endpoint task attempts, (c) predicts cost using genuine robot witnesses, (d) searches dynamically with branch-local hypothetical edits, and (e) selects and **independently verifies** repairs on held-out 2D and 3D roots. All model comparisons and failure modes are measured under a frozen, comparable protocol. It is not enough to have passing numerical tests or a visually convincing example.

### Immediately enforced non-negotiables

- **This implementation workstream must not duplicate scene generation, rebalancing, physical re-labelling, or replay while the separate readiness job runs.** That job owns those operations. This plan may proceed with read-only implementation audits and deterministic code/tests, but actual fitting begins only after its final artifacts are hash-verified, its unresolved blockers are resolved or expressly accepted, and the user explicitly approves training.
- Maximum **three corrective relocations** per main experimental scene, each movable object used at most once. The target action occurs *after* correction, and does **not** count as one of those three. The teacher may have a larger historical maximum; report the distinction explicitly.
- Proposals have no access to construction-intended repairs, target solver, certified blocker sets, order labels, X/Y teacher answers, test witnesses, or K at inference.
- No learned intermediate robot state, IK solver, motion generator, causal DAG, or separate blocker classifier is inserted into the final method.
- Static legality may reject out-of-domain, unsupported, overlapping, fixed-geometry-penetrating, repeated-move and invalid-object actions, but **not** run a test-time physical placement/IK/planner veto on every proposal.
- **All labels have query keys and provenance.** An unattempted, cancelled, censored or out-of-scope query is **MISSING**, never a negative. An attempted, pinned finite-budget failure can be a policy-relative binary zero, with its failure phase and budget retained.
- Model selection, calibration, final score weights and compute budgets use **training/validation roots only**. Descendants, edited scenes, permutations and alternative parking assignments inherit their root/lineage split. Disclose any previously inspected challenge-test views rather than calling them blind.

## 1. Typed problem and module contracts

For an immutable root define

\[
R=(S_0,q_0,q_{\mathrm{ref}},T,g_T,\mathcal O,\mathcal F,\Pi,\mathcal B),
\qquad r=[(o_1,d_1),\ldots,(o_m,d_m)],\quad 0\le m\le 3.
\]

`S0` contains observed object identities, shapes, poses, support surfaces and fixed geometry; `q0` is the initial robot state; `q_ref` is the fixed target-reference robot state; `T,g_T` define the *same original task* for every corrective candidate. `Pi` pins grasp/carry/release/connector and target capabilities; `B` pins physical budgets.

A hypothetical endpoint is **only**

\[
S_r=\operatorname{Edit}(S_0,r),
\]

where the chosen object poses change deterministically, other objects and target remain unchanged, and **no actual achieved joint state** is inferred. The root and the complete order must accompany every X/Y score.

| Module / owner | Inputs | Outputs | Must not do |
|---|---|---|---|
| `placement_sampler` | Hypothetical `S`, selected `o`, support domain, pinned grasp-success convention, seed and budget `M` | Deduplicated `(object, destination, score_semantics, provenance)` proposals | Pick the blocker/order, test the target, assert whole-sequence success |
| `candidate_search` | Immutable root, sampler, frozen scorer, budgets | Ordered prefixes, branch-local endpoints, visited/frontier, complete stopping candidates | Reset robot state between hypothetical steps; use teacher labels to expand |
| `xy_scorer` | **Original** `(S0,q0,q_ref,T,gT)` and the **whole ordered prefix** `r`, endpoint `S_r` | `pY`, `pX_given_Y`, `pX`, `p11`, optional `J_hat` | Generate destinations, trajectories or intermediate `q` states |
| `cost_selector` | Candidate probabilities, `m`, analytic displacement and learned travel readout | Ranked stopping candidates, chosen sequence or abstention | Treat current-prefix score as a lower bound on all descendants |
| `physical_teacher` | Versioned full X/Y/placement queries | Actual successes/failures, missing status, witnesses, costs | Participate in test-time proposal filtering or train on test labels |

Use canonical IDs and hashes:

- `x_key = (root_hash, robot/teacher/budget hashes, q0, q_ref, exact ordered [(object,destination)], connector convention)`.
- `y_key = (root_hash, goal/target, endpoint_scene_hash, q_ref, teacher/budget hashes)`; different orders of the **same endpoint share Y**.
- `place_key = (scene_hash including branch edits, object, destination, support/grasp protocol and teacher hashes)`.
- `sampler_cache_key = (hypothetical_scene_hash, object, support, model/version, seed, proposal_budget, legality_version)`.
- `xy_cache_key` retains distinct `x_key`s but deduplicates scene/endpoint Y predictions.

**Contract tests:** serializing/deserializing a root does not move any object; AB and BA have separate X keys but identical Y keys if destinations match; changing target goal changes Y key; adding a candidate must not change any previously computed Y marginal; no-op has zero corrective actions.

## 2. External dataset-readiness handoff — **not an implementation phase (no P0)**

**Owner:** the already-running independent `FINAL_READINESS_GATE` process. **This plan does not repeat its work.** There is no separate P0 dataset collection, replay, relabelling, quota reconciliation, or second readiness report to run before P1. In particular, do not restart 2D X/Y collection, 3D independent replay, omission checks, or empty-endpoint Y queries that are already underway.

### What the external job must deliver

- A final readiness verdict with an immutable, hash-verified 2D/3D scene/label/witness manifest; finalized X and independently defined endpoint Y; valid missing-label masks; original versus finalized K/ordering evidence; lineage-disjoint splits; and a genuine train/validation/test label-distribution summary.
- An explicit disposition for **all** shortened-correction contradictions, including the three already reported as independently verified X=1/Y=1 in the interim run. A confirmed shorter correction invalidates a *minimal-K claim under the finalized protocol*, not necessarily the scene or its usefulness as an X/Y training example. The owner must resolve whether to reclassify, exclude from a minimal-K evaluation stratum, or replace from existing verified candidates. **Do not silently relabel K, discard the evidence, or count a shorter Y=1 omission as sufficient without X=1.**
- Honest provenance for exhaustive versus sampled 3D replay, known legacy-to-finalized disagreements, observed X/Y quadrant coverage, negative-Y origins, censored/missing queries, and usable travel witnesses.

### Tiny implementation-side handoff (only after the job finishes)

1. Read—not regenerate—the external `FINAL_TRAINING_READINESS.json`, final selection and label manifests, witness index, SHA256SUMS, and the placement-Q2 immutable snapshot. Require the documented verdict and explicit user authorization before real model fitting. `READY_WITH_DOCUMENTED_NONBLOCKING_CAVEATS` requires specific user acceptance of those caveats; `BLOCKED` prohibits training on affected labels.
2. Perform an automated **loader compatibility preflight**, not another physical-science audit: resolve manifest paths/hashes; parse the typed root, target/goal, q0/q_ref, action order, endpoint key, masks, split, label provenance and witnessed travel fields; check that requested model tensors can be constructed. Record a single frozen `data_snapshot.lock.json` (path, source commit, manifest hashes, teacher versions and feature schema). Do not create a competing `P0_DATA_CONTRACT.md` or a second independently selected dataset.
3. Freeze the snapshot for all P1–P6 runs. If the external gate is blocked or fields are missing, report the exact incompatibility and work only on toy/unit tests or code contracts—not on re-collecting data, changing source scene counts, or silently substituting legacy labels.

**Handoff gate:** hash-verified final readiness artifacts + no unresolved *blocking* minimal-K/label issues + compatible training tensors + user's explicit training approval. This is a short preflight dependency, **not a new P0 phase**.

## 3. Phase P1 — Placement proposals, independent of target repair

### 3.1 Use the Q2 data already collected

- **Condition:** `(hypothetical object scene S, selected object o, support/placement domain, pinned post-grasp capability)`. Crucially **exclude target/goal and construction-intended repair**. The object may currently be inaccessible for picking; sampler assumes it has been grasped. X handles actual picking and sequential transfer feasibility.
- **Label:** `V_place=1` only when the isolated placement/carry/release under the declared post-grasp protocol succeeds. `V_place=0` is pinned-policy attempted failure; administrative/missing trials are masked. A successful placement says nothing about target Y, order-dependent X, or terminal connector.
- **Output:** several legal *destinations for the chosen object*, not a whole multi-step plan. The search forms the object–destination action set by invoking the sampler for eligible, unmoved objects.
- **Current 3D shelf scope:** a finite 6×6 set of support-constrained upright placements is an acceptable **3D physical problem with discrete resting pose support**; do not misrepresent the decoder as unconstrained SE(3) unless actually implemented. 2D is a discrete 8×8 resting lattice with an articulated arm operating in continuous joint space. Domain-specific decoders and weights are allowed.

### 3.2 cVAE (primary *candidate*, not presumed winner)

Implement or reuse a small, trainable scene/object condition encoder `c=f(S,o)`. During training,

\[
q_\psi(z\mid c,d^+),\quad p_\phi(d\mid z,c),\quad
\mathcal L_{\rm cVAE}=\mathbb E_q[-\log p_\phi(d^+\mid z,c)]
+\beta_{\rm KL}D_{\rm KL}(q_\psi(z\mid c,d^+)\Vert\mathcal N(0,I)).
\]

- Train the destination decoder on **verified positive** placements. For a finite cell domain, use a **masked categorical decoder** with explicit legal-cell indices; do not interpret an arithmetic mean of multiple good cells as a placement. When trained with a continuous pose decoder, respect support and angle parameterization.
- At inference: **no known destination and no posterior encoder**. Sample `z~N(0,I)`, decode several destinations, static-legality check, deduplicate, optionally spread samples across distinct regions, and return stable seed/provenance. Log raw draws, legal unique count, duplicates, runtime, KL, latent usage, and mode coverage.
- An optional **placement ranker/calibrator** trained on both positive and negative labels may rank proposals. Its `P(V_place=1|S,o,d)` must only be called calibrated after an independent reliability test. A cVAE's destination density/sample frequency **is not** that probability.
- Existing reported 3D results suggest cVAE may beat flow matching and uniform while a simple band-stratified sampler can achieve higher known-good hit@4; **do not erase or assume away that control**. Recheck evaluation on independently teacher-tested *previously unlabelled* proposed destinations (development confirmation; final test after freeze).

### 3.3 Essential same-interface controls

- **Conditional flow matching:** matched scene/object input; learned vector field on destination representation; record ODE steps, legal projections and runtime. It is an ablation, not required as runtime if inferior.
- **Sobol/uniform and near/mid/far or band-stratified analytical sampling:** same eligible domain, exact **unique legal proposal** budgets, seeds and support rules. A strong band baseline stays in the main table.
- **Swept-volume analytical sampler:** include only after its construction/information boundary is frozen. Disclose if it uses historical robot capability or target-specific trajectories; do not quietly provide privileged target repair knowledge.
- **Categorical non-VAE decoder / z-disabled cVAE control:** tests whether latent `z` materially improves coverage.
- **Sampler+ranker versus sampler without ranker:** isolates proposal generation from local placement confidence.

### 3.4 Acceptance tests and plots

- Invariance: changing target goal or generator `intended` fields with identical observed object geometry does not affect proposals.
- No test-time IK/teacher calls, target sweep, privileged catalogue, or construction lookup.
- Multi-mode toy placement: distinct valid regions can both appear; several samples are not all duplicates; illegal destinations rejected identically across samplers.
- Metrics on predeclared **physically checked** proposals: precision/recall or known-success hit@M with tested denominator, diversity, distinct legal locations, sampler latency, confidence Brier/ECE (only if calibrated), and miss rate. Keep **unlabelled proposals** separate; do not call known-label precision true physical precision.
- Visualize: one scene with colored successful/failed/unknown placements and cVAE proposals; per-object proposed destination lists; performance curves at M=1,2,4,8,... under matched budgets.

**Gate P1:** one frozen, audited `sample(S,o,M,seed)` backend can be swapped among cVAE, flow matching and analytical controls; sampler-alone results and precision limitations are reported without assuming it resolves the original target.

## 4. Phase P2 — Exact root-consistent coupled X/Y Boltzmann model

### 4.1 Label events: never interchangeable

For every **full ordered prefix** `r` evaluated *as a stopping correction*:

- `X_r=1`: start from **original** `(S0,q0)`; physically execute relocations in the given order, carrying achieved robot/gripper state into each next action **without intermediate reset**; finally connect and verify to free-gripper `q_ref`. A prefix's *terminal connector* may fail even if its relocation succeeded. This does **not** make all longer extensions impossible.
- `Y_s=1`: independently initialize the hypothetical endpoint `s=Edit(S0,r)` with unchanged target and goal; execute original target task from fixed `q_ref`. Y can be 1 when X is 0. AB/BA with the same endpoint must share this Y observation.
- Empty sequence: `X_empty=1` by the pinned no-op/reference convention; its joint success is `P(Y0=1)`.
- All `(X,Y)=(0,0),(0,1),(1,0),(1,1)` are valid. Duplicated queries deduplicate by canonical `x_key` or `y_key`, not by record index. Missing observations are marginalized, not filled.

### 4.2 Exact model and factor graph

Let `v_s=f_scene(S_s,q_ref,T,g_T,root_context)` and `g_r=f_order(S0,q0,ordered action tokens,original context)`. Predict real coefficients

\[
b_s=h_Y(v_s,c),\qquad a_r=h_X(g_r,v_s,c),\qquad w_r=h_{XY}(g_r,v_s,c).
\]

Interpret `b` as the F3 Y-unary, `a` as F2 ordered X-unary, and `w` as F5 pairwise X–Y coupling. **F1** is shared deterministic legality; **F4** is omission/intervention data using the same event variables, **not a new output head**. The model is a **structured factorized Boltzmann energy model**, not a generic RBM with invented hidden nodes.

Use the normative **scene-first normalized** distribution (temperature `tau=1` unless a predeclared ablation):

\[
P_\theta(\mathbf y,\mathbf x\mid R)
=\prod_{s\in\mathcal S}P(Y_s=y_s)
\prod_{r\in\mathcal Q}P(X_r=x_r\mid Y_{s(r)}=y_{s(r)}),
\]

\[
P(Y_s=1)=\sigma(b_s),\qquad
P(X_r=1\mid Y_s=y)=\sigma(a_r+w_r y).
\]

Consequently,

\[
\begin{aligned}
p_Y(r)&=\sigma(b_{s(r)}),\\
p_{X\mid Y}(r)&=\sigma(a_r+w_r),\\
p_{11}(r)&=p_Y(r)\,p_{X\mid Y}(r),\\
p_X(r)&=p_Y(r)\sigma(a_r+w_r)+(1-p_Y(r))\sigma(a_r).
\end{aligned}
\]

A convenient **raw local** factor energy is `-a_r x_r-b_s y_s-w_r x_r y_s`, **but it is not the complete root probability model**. Preserve the Y-dependent X normalizers (`softplus`) in the root energy. **Do not** replace this with independent sigmoid products or naive four-state normalization per candidate that changes the scene Y marginal when another order is added.

### 4.3 Architecture details that require explicit code audit

- **F3 must see the original target identity, its exact goal, endpoint object geometry, q_ref and applicable robot/task context.** A 3D endpoint-only encoder omitting goal is a blocker; identical object arrangements with different goals can have different Y.
- **F2 must see original root geometry, q0 and the entire ordered sequence** with predecessor-aware interactions (GRU, attention or the verified 2D pattern), destination-specific features, object identity/shape and the effects of earlier hypothetical edits **as features**. Never replace a full prefix with the final scene alone. Never generate explicit intermediate achieved robot joint states.
- Port or reuse verified **GEO2** geometric features, order information and optional **SYM** auxiliary mechanism from the final 2D code only where they match the declared 3D feature semantics. Any domain-specific approximation should be named and ablated, not claimed fully equivalent.
- Implement no-op explicitly, avoiding a zero-length GRU crash.
- Model D (`coupled`): learn `w_r`. Model E (`uncoupled`): force `w_r=0` while matching data and capacity as reasonably possible. Model G (`order-invariant`): remove/restrict order-sensitive encoding while retaining comparable endpoint/feature access. Model DIRECT-GEO: an **independent** direct `P(X=1,Y=1)` predictor with its own output head and matched training examples; **not** a disguised sum `a+b` unless that faithfully matches the preregistered DIRECT control.
- Keep prediction signatures identical across arms and allow inference **only** from visible root and sequence tensors; labels never enter forward features.

### 4.4 Exact training loss and masks

Use exact *observed-data* root-marginal negative log likelihood. For a root, group all observed X queries by shared endpoint `s`:

\[
\ell_s=-\log \sum_{y\in \mathcal Y_s^{\rm allowed}}
P(Y_s=y)\prod_{r\in \mathcal O_X(s)}P(X_r=x_r\mid Y_s=y),
\quad \mathcal L_{\rm joint}=\frac1{N_{\rm roots}}\sum_R\sum_s \ell_s.
\]

If Y is observed, `allowed={observed y}`; if missing, `allowed={0,1}`. Unobserved X queries contribute nothing. Evaluate with stable **logsumexp/logsigmoid/softplus**, not brute-force over the full root graph. Sum each **unique endpoint Y exactly once**, dedup each exact ordered X query, and mean by root to avoid over-weighting catalogue-heavy roots. If a root has no observed evidence, exclude it explicitly from the supervised denominator.

Travel auxiliary is added separately in P3. Any optional GEO/SYM auxiliary loss must be **named**, weighted, logged separately, and matched/ablated fairly; do not replace joint NLL with a heuristic ordering loss.

### 4.5 Unit and genuine-data gates

1. Compare exact log likelihood and all marginals against brute-force enumeration on tiny synthetic roots with Y shared by several X variables; tolerances appropriate to float64.
2. Adding an extra X alternative **must not change** the existing Y marginal.
3. AB/BA have identical `pY` if endpoints match; `pX` may differ. Reordering actions with changed endpoint is not a valid same-Y test.
4. Test all four X/Y combinations, partly observed Y, partly observed X, no observed X, zero-length/no-op, duplicate source keys, impossible/missing/censored records, and gradients on each factor head.
5. **Goal sensitivity:** keep endpoint geometry fixed, change target goal; F3 representation and potentially `pY` must change. **Order sensitivity:** keep final endpoint fixed, reverse action order; F2 features must change. For G, its intended invariance must be demonstrable.
6. Fit D/E/DIRECT/G on a **synthetic learnable toy** and confirm the loss goes down (a plumbing test only). Then train on actual finalized train/val roots with matched budgets and multiple fixed seeds; record convergence and early stopping from dev joint NLL, not final test results.
7. Report held-out root-clustered joint NLL, Brier, ECE/reliability, calibrated `p11`, X/Y decomposition, same-endpoint order prediction, omission outcomes, failure-phase analysis, and paired confidence intervals. Disclose that previous 2D findings did **not** establish a D-over-E or D-over-DIRECT advantage; never pre-choose a winning result.

**Gate P2:** exact normalized math verified; D/E/DIRECT/G have faithful and goal-aware input schemas; authentic held-out prediction evaluated with physical labels and no leakage. If D fails to beat simpler arms, report it and investigate ablations rather than modifying evidence to manufacture superiority.

## 5. Phase P3 — Cost learning and risk-aware selection

### 5.1 Freeze **which** joint travel is measured before training

The **5 November authoritative document** defines a complete-witness `J` over the pinned physically successful composed protocol: relocation approach/carry/release, between-action motions, terminal connector **and target task**, with a fixed joint-normalization scheme. An **older v1.7 methodology** instead defined first-complete-*relocation*-witness travel **excluding target and HOME diagnostic**. These are different physical targets: **do not combine their labels in one cost head.**

**Implementation decision gate:** adopt the 5 November `J_complete` definition for the final primary experiment **if the current data/witnesses actually support it**; save a decomposed ledger `J_reloc`, `J_connector`, `J_target`, `J_complete` (normalized joint travel), and distinguish target HOME diagnostics if any. If historical `J_reloc` is all that is measured, retain it as a separate, explicitly labelled cost ablation and seek approval before substituting it for `J_complete`. Require a documented metric definition and exact source-witness provider (first valid witnessed sequence under pinned seed schedule). The learned head predicts the **teacher/witness-policy travel**, not globally optimal travel.

### 5.2 Train readout only on genuine witnesses

- Use a nonnegative prediction `J_hat=softplus(head(features))` (or equivalent) from root/sequence features, **without target outcomes as test-time inputs**.
- On appropriate successful *complete* witnesses, fit

\[
\mathcal L_J=\frac{1}{N_J}\sum_{w\in\mathcal W_{complete}}
\operatorname{Huber}(\log(1+\hat J_w),\log(1+J_w)),\qquad
\mathcal L_B=\mathcal L_{joint}+\lambda_J\mathcal L_J.
\]

- No witness ⇒ masked travel label, **not** `0`, `infinity` or an arbitrary punishment for X/Y failures. Choose `lambda_J` on validation roots; report loss terms and witness coverage separately. No target trajectory information leaks into the scorer at test time.

### 5.3 Fixed inference cost and safeguards

For every examined *stopping* candidate `r`, compute

\[
C(r)=-\log\max(p_{11}(r),\epsilon)
+\alpha\,m(r)+\beta\,C_d(r)+\gamma\,\hat J(r).
\]

`m` is exact corrective relocation count; `C_d` is **analytic** sum of object displacements (domain-aware cell/grid vs metric displacement, normalized consistently); `J_hat` is learned. `alpha/beta/gamma`, epsilon, feasibility threshold `eta`, and no-op gate must be set/frozen using validation only. All terms should be logged individually; do not mix units silently. The cost head is **not** a second source of X/Y success evidence.

Required controls: `gamma=0`; `beta=0`; `alpha=0`; all correction penalties off; `lambda_J=0` with/without travel term; matched X/Y model with joint travel training on/off; cost-vs-success Pareto curves. Check `p11→0` numeric clipping; positive cost; stable tie-breaking. **Do not allow low travel to compensate for a score below the declared `eta` threshold.**

**Gate P3:** cost semantics are pinned and auditable; learned travel predicted from real witnesses; measured cost error and success–travel trade-off presented, including travel-off ablation. A strong cost result cannot be claimed when valid travel witnesses are too sparse.

## 6. Phase P4 — Dynamic branch-local candidate search

### 6.1 Search state and single source of truth

Use immutable `R` and a per-branch state such as:

```python
Node(
    ordered_prefix=[(object_id, destination), ...],
    endpoint_scene_hash="...",  # recomputed by deterministic Edit(S0, prefix)
    moved_object_ids=frozenset(...),
    stopping_prediction={"pY": ..., "pX_given_Y": ..., "p11": ..., "cost": ...},
    proposal_provenance=[...],
    depth=..., seed=...
)
```

Each prefix is a possible **stopping correction**, even when its current Y is low. Search-control priority is distinct from stopping cost. Nothing physically executes until after final selection.

### 6.2 Exact inference loop

```text
frontier = [empty_prefix]
score/store no-op from P(Y0=1)
results = [no-op]

while frontier nonempty and search budget remains:
    r = choose_expandable_prefix(frontier, fair_best_first_schedule)
    if len(r) == 3: continue
    S_r = Edit(original_S0, r)           # hypothetical object edits only
    for each eligible object o not in r:
        D = sampler.sample(S_r, o, M, seed/variant)  # repeat for this branch
        D = shared_static_legality_and_dedup(D)
        for d in D:
            child = r + [(o,d)]
            stage child for batch scoring
    scorer.batch_score(original_R, complete_ordered_children)
    for child in scored_children:
        record pY, pX_given_Y, p11, J_hat, m, C_d, C(child)
        store child as a stopping candidate
        if len(child) < 3: place it on the frontier, subject to fairness/budget

select best admitted stopping candidate using frozen eta/no-op/cost rule
if none qualifies: ABSTAIN/UNKNOWN with proposal/search coverage status
send selected ordered action specification to external executor/teacher
verify physical correction + original target task; log outcome independently
```

Notes:
- A sampler call **does not force one synchronous model call**; batch many proposals, reuse cached Y on identical endpoints, reuse existing X results on identical ordered sequences.
- `xy_scorer` **always** sees `(S0,q0,q_ref,T,gT,whole ordered r)` and endpoint `Edit(S0,r)`. It never scores `(hypothetical S_A, B)` as if this were a new independent robot starting state.
- No low-`pY` or connector-failed partial prefix is **soundly pruned** merely because stopping there fails; a later corrective move can succeed. No early-stop cost is a valid descendant lower bound without proof.
- The same object is relocated at most once; destinations are initially permitted and distinct under the chosen dataset action grammar; no slot swapping. Static support/overlap validity is checked for each hypothetical state. Canonicalization cannot merge distinct action orders that have different X semantics.
- Use a predeclared finite sampler budget `M`, expansion/score budgets, max frontier size, beam/fair-best-first policy and deterministic tie-breaking. Count every raw draw, unique legal proposal, expanded prefix, score, cache hit, timeout and abstention. Do not claim exhaustive physical infeasibility when proposals or compute are exhausted.
- Separate **prediction-time** (sampler + neural scoring + search) from **physical verification time**. Never run the physical teacher in the online search's proposal/re-ranking path for the main Approach B condition.

### 6.3 Mandatory toy regression suite

1. **A then B:** moving A changes B's valid destinations; sampler re-query finds a new `B→Q`, whereas static-only sampling misses it.
2. **AB vs BA:** identical final object poses and Y, different X; both orders remain distinct in frontier/cache.
3. **A insufficient, AB sufficient:** prefix A has `pY` near 0, child AB can have high `p11`; search may still find AB.
4. **Connector trap:** stopping after A has `X_A=0` due only to terminal `q_ref` connector; continuing AB is not discarded.
5. **Sampler false positive:** physically failed placement/relocation is scored by X, not called success because sampler proposed it.
6. **Sampler miss:** no generated candidate reaches the needed parking; report proposal coverage failure even if scorer is perfect.
7. **No-op and harmful extra move:** originally feasible target selects no-op; moving a legal object can make Y worse.
8. **Cross-branch immutability:** exploring A→P never mutates B→Q sibling or original root.
9. **K3 depth:** three moves allowed; fourth rejected; target action excluded from corrective count.
10. **Deterministic cache/batch:** batching, cache hits, checkpoint-resume and different candidate insertion order do not change existing scores or final choice at a frozen seed/budget where scheduling equivalence is expected.

**Gate P4:** search returns a valid ordered high-level repair, abstention or bounded-search unknown; tests show *genuine branch-local repeated sampling* and correct scorer-root inputs. No oracle has slipped into proposal filtering.

## 7. Phase P5 — True 2D/3D integration and physical confirmation

Run in increasing risk order, after each earlier gate:

| Milestone | Minimum demonstration | Pass condition |
|---|---|---|
| Toy 2D / algebraic | Handcrafted root, proposal list, known X/Y values | Finds expected sequence; all masks, caches and branch semantics correct |
| 2D genuine held-out development | Articulated-arm tasks across K0–K3 and NONE | Independently checked selected orders, success/abstention correctly reported; sampler, score and physical time logged |
| 3D genuine held-out development | Actual 6×6 support-limited shelf simulator | Same X/Y semantics, target/goal-conditioned F3, q_ref connector, verified final task; all finite-budget failures logged |
| Paired order contrasts | At least matched same-endpoint AB/BA and K3 permutations | Common Y invariant, learned X differentiates *only where supported by physical labels* |
| Counterfactual sufficiency | Omissions, shorter prefixes, different parking | Predicts Y changes from **independently tested** endpoint outcomes; catches K inconsistencies |
| End-to-end | Frozen sampler + D/E/DIRECT/G + dynamic vs static | Complete verification rates, ranked costs and resource budgets with root-clustered uncertainty |

Keep separate success statuses: `FOUND_VERIFIED`, `SELECTED_UNVERIFIED`, `SEARCH_BUDGET_EXHAUSTED_UNKNOWN`, `PROPOSAL_COVERAGE_UNKNOWN`, `TEACHER_BUDGET_EXHAUSTED/CENSORED`, `EXHAUSTED_DECLARED_CANDIDATE_SET`, and `ABSTAIN`. **Never turn predicted `p11` into a claimed verified success.**

For evaluation, use the same low-level robot/teacher protocol for every method and never rank using outcomes from that root. After choosing `r*`, execute the exact correction once under the declared evaluation budget, then independently attempt the target; retain collision, grasp, connector and target failure phases. An execution reattempt is a new declared trial, not a concealed rescue.

## 8. Phase P6 — Minimum fair ablation matrix and evidence

### Layer A: placement proposal quality

- cVAE versus conditional flow matching versus Sobol/uniform versus **band-stratified**; swept-volume method if independently specified.
- cVAE with/without `z`, with/without placement ranker, unique proposal budget sweeps; one-shot versus edited-scene resampling.
- Physically checked proposed destinations, including previously untested cells, not just recovery of already labelled positives. Show sample latency, physical precision/coverage/diversity, censored counts.

### Layer B: main X/Y prediction on an **identical frozen candidate set**

- **D coupled** versus **E uncoupled** versus **DIRECT-GEO** versus **G order-invariant**, plus X-only and Y-only selection controls.
- Same root splits, physical evidence, token features where applicable, parameter/compute accounting, seeds and early-stop protocol. Include matched same-endpoint order contrasts and omission changes.
- Report joint NLL/Brier/calibration, exact `p11` and Y invariant, root-clustered paired intervals, per-K and per-strength results. The direct-success control need not output calibrated X and Y separately, and should not be punished for not doing so.

### Layer C: full search, always physically verified

- **Dynamic sampler + D + cost** (primary) versus initial-only sampler + same D; learned sampler + analytic ranker; analytic sampler + D; full learned sampler + E/DIRECT/G; length/displacement/travel on/off; budget sweeps.
- Main results: verified target-task success, success by K and K3 order strength, unnecessary corrections on K0, proposals and sequences evaluated, planning time, independent physical calls, terminal connector failures, actual relocation count/displacement/joint travel, abstention and true unknowns, repair omitted from old privileged catalogues.
- Strong historical and external analytical/learned methods are a later baseline workstream. Do not delay correct P1–P5 integration merely to port them; keep a common backend interface ready.

### Visual proof obligations after each stage

Produce a minimal set of **actual evidence-backed** 2D grid/3D shelf visualizations: placement positive/negative/unknown maps; one main dynamic branch with updated proposals; real same-endpoint AB/BA video or trajectories (distinct X/shared Y); energy calibration plot; travel predicted-versus-observed scatter; selected-vs-executed corrective sequence and final target outcome; failure-attribution chart. Schematic figures must be labelled schematic. Never substitute an attractive conceptual animation for an executed robot trajectory.

## 9. Minimal implementation footprint and proposed file ownership

**First reuse existing files.** Do not copy all legacy modules into a giant new framework. Prefer a small integration layer with explicit boundaries, short functions, and no Python file growing unchecked; split only on genuine ownership. Suggested *logical* arrangement (not a mandate to create every path):

```text
approach_b_final/
  config.toml              # seeds, root manifests, proposal/search/cost budgets
  contracts.py             # typed root, action, X/Y and query-key/schema validators
  placement.py             # existing sampler adapters, cVAE/FM/analytic interface
  xy.py                    # thin wrappers to validated bxy_core/p11/p17 + 3D encoders
  search.py                # immutable branch tree, dynamic proposal loop, caches
  evaluate.py              # matched ablations, independent verification, metrics
  tests/                   # semantic toy examples, math/regression, leakage, IO
  runs/<version>/          # append-only configs, checkpoints, outputs, plots
```

Do not instantiate another physical teacher unless the existing teacher cannot fulfill its contract; adapt it read-only for offline supervision/evaluation. Keep 2D/3D physics domain handlers behind one tested API. Use versioned checkpoint signatures (domain, source hash, feature schema, model arm, sampler, RNG, dataset hashes). Store optimizer state and early-stop selection reproducibly.

### Canonical configuration groups

- `data`: roots, sidecars, selected views, masks, hashes, split/family mapping.
- `teacher`: q_ref, grasp/connector semantics, finite budgets, physical seed schedule.
- `placement`: method, grasp convention, input features, latent size, KL schedule, optional calibrator, per-object unique M.
- `xy`: arm D/E/DIRECT/G, tau=1, encoder features, GEO/SYM flags, model seeds, loss masks.
- `cost`: witness metric version, lambda_J, alpha/beta/gamma, epsilon, eta, no-op threshold.
- `search`: max_corrective_moves=3, frontier/expansion/scoring/timeout caps, fairness and cache policy.
- `eval`: blinded/previously inspected view flags, physical verification budget, metrics, saved plots.

**Never silently infer missing numeric hyperparameters from the methodology.** Create a versioned development configuration, report validation-driven choices, freeze before test. An example configuration is not an experimental result.

## 10. Execution sequence and stop/go checklist

**External prerequisite (not P0):** the separate readiness job finishes; loader preflight consumes its immutable artifacts; the user authorizes training. All collection, omission decisions, replay, and data-science readiness verification belong to that job.

| Step | Work | Blocking evidence needed to advance |
|---|---|---|
| **P1** | Reuse/refine cVAE and analytical/FM sampler adapters | Independent proposal checks, same interface, no target leakage |
| **P2a** | Port/review 2D exact math + complete 3D target-aware/order-aware encoder | Brute-force-normalization, goal/order/no-op tests, genuine feature schema |
| **P2b** | Train D/E/DIRECT/G on matched real evidence | Root-wise masked NLL, joint calibration, held-out prediction + order contrasts |
| **P3** | Audit witness travel, fit cost head, validation-freeze selector | Matching J definitions and labels; cost/travel ablations |
| **P4** | Integrate branch-local sampler requery + score batches | Ten search regression cases, bounded uncertainty statuses |
| **P5** | Independently verify selected repairs in 2D then 3D | Real executed X+Y, exact budget/resource logs, failure taxonomy |
| **P6** | Run matched ablations, visualize, aggregate results | Reproducible tables, confidence intervals, fixed test protocol |

**Go/no-go rule:** each step produces a short evidence report with exact file paths, source hashes, config hash, input counts, passed/failed tests and scientific limitations. Do not call a stage complete because a small smoke test or a copied report passed. Stop at a failure, isolate the smallest corrective change, and rerun its exact regression tests; no sweeping architectural revisions or hidden new data generation.

## 11. Nonclaims and decision discipline

- We predict **operational** feasibility under pinned physical planners and budgets, not mathematical impossibility in general.
- The cVAE/flow learns conditional placement *proposal distributions*, not feasible repair sets or causal blockers. A high-probability destination can still fail X; a good placement can still leave Y=0.
- The energy model is root-consistent and joint, but **F5 coupling is a hypothesis to test**, not guaranteed to beat E/DIRECT. A strong order-aware improvement does not imply the quadratic interaction is useful.
- We learn order-dependent outcomes statistically, **not** an identifiable directed causal graph or intermediate robot dynamics. Claim causal relevance only when supported by explicitly verified order, omission and edited-scene contrasts.
- Bounded finite sampling/search cannot prove that no possible correction exists. Distinguish sampler miss, model misrank, search exhaustion, and physical failure.
- **Two shelves 180° apart** are a separate benchmark extension: source retrieval, destination placement and actual transfer must be jointly verified. Reuse the interface later, but do not expand the current architecture or postpone its main 2D/3D results for that extension.

**Immediate instruction to the implementer:** while `FINAL_READINESS_GATE` runs independently, prepare P1–P4 interfaces and deterministic toy/unit tests using read-only existing code; **do not** run another P0. Do **not** fit networks, re-label roots, replay the teacher, run new physical experiments, or use final test data for tuning. When the external verdict and snapshot hashes pass the short loader preflight **and the user approves training**, execute P1 → P2 → P3 → P4 → P5 → P6 in order, saving a small auditable deliverable at every gate.
