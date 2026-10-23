# 0034 — P9-L3c/L3d: Final 2D Factor Semantics, Matched Visual Control, and Evidence Readiness

**Binding execution contract for Claude Opus 5.5 High**  
**Project:** Latent Causal Infeasibility for Long-Horizon TAMP (`Narendhiranv04/latent-causal-tamp`)  
**Last verified pushed commit:** `6aa4ba55a267e6dfaded8ba3a8e91369b6795443` (`6aa4ba5`)  
**Place this document at:** `instruction-phase-md/0034_P9_L3c_2D_Model_Freeze_and_Evidence_Readiness_Contract.md`  
**Authorized scope:** one tightly bounded final saved-data-only 2D audit of factor semantics, optional small physically keyed relational-factor competitor if it can be implemented *without removing the high-order potentials*, capacity/input-controlled visual ablation, decision memorandum, and a **proposal only** for the next physical-evidence pilot.  
**Not authorized:** new teacher queries, simulator/planner/IK queries for intervention checking or candidate ranking, new physical/robot episodes, new dataset collection, new 3D code or hardware activity, L4 execution, broad architecture redesign, changes to old results, or unbudgeted training.

> **Central decision:** P9-L3's `KEEP_UNIQUE` is the default. **Do not restart Boltzmann methodology design.** Investigate one remaining ambiguity: can adding an already-known physical sequence query in a new *candidate role* inadvertently introduce duplicated scene–repair couplings or higher-order factor scopes? If this cannot be fixed cleanly while preserving the existing factors, document the semantic limitation and keep `ABC9U_UNIQUE_V1` as the provisional 2D baseline. Either way, end this task with a reproducible freeze candidate and a narrowly targeted physical-evidence plan, not another open-ended architectural campaign.

---

## 0. Required read-first audit and source synchronization

Read completely, in this order, before modification:

1. `instruction-phase-md/latent_causal_tamp_methodology_v1_8.md` and `instruction-phase-md/latent_causal_tamp_implementation_guide_v2_0.md` (locate unchanged copies if instructions were left untracked; don't invent content).
2. `instruction-phase-md/0031_P9_L3a_Factor_Graph_Semantics_and_Saved_Data_Controls.md`.
3. `responses-phases/0031_P9_L3a_catalogue_and_inference_audit.md`, `0032_P9_L3a_unique_factor_mathematics.md`, `0033_P9_L3b_saved_data_model_comparison.md`, and `P9_L3_DECISION.md`.
4. `responses-phases/0028_P9_L0_source_and_likelihood_audit.md`, `0029_P9_L1_exact_joint_boltzmann_math.md`, `0030_P9_L2_saved_data_joint_objective_comparison.md`, `P9_NEXT_DECISION.md`, and `0027_P8d_matched_oneshot_execution.md`.
5. Actual source and tests: `unique_factor.py`, `joint_likelihood.py`, `abc7_models.py`, `abc7_train.py`, `abc8.py`, `p9_l3.py`, `p9_run.py`, `p8_select.py`, `p8_eval.py`, `p9_viz.py`, `tests/test_p9_joint.py`, `tests/test_p9_l3_unique.py`; `runs/p9/l3/{L3A_0_GATE.json,L3A_1_GATE.json,L3B_GATE.json}` and `runs/p9/l3/l3b/{L3B_plan.json,summary.json}`.

Capture `git status --porcelain`, local `HEAD`, remote `origin/main`, source/dataset/checkpoint/plan hashes, and any pre-existing user edits. Verify commit ancestry; **do not reset, discard, auto-add or overwrite user-owned untracked artifacts**. If the branch advanced, inspect the delta before proceeding. The reports above document engineering outcomes; independently inspect source before asserting correctness. Record a source manifest **before** running any experiments.

### Frozen facts and caveats to retain

- P9-L3 implemented a mathematically valid **unique-factor conditional root Boltzmann model** `P_U(z_S,x)=P_S(z_S) exp(-E_Q(x,z_S)/T)/Z_U(z_S)`; keep this as the current canonical/default model. One binary variable and one unary per distinct physical sequence query; distinct relational factor instances; exact elimination; scene-marginal consistency.
- Five conceptual families are retained: F1 static (outside outcome likelihood), F2 ordered repair, F3 hypothetical fixed-robot scene intervention, F4 omission, F5 cross-outcome coupling. Travel `J` is a separate supervised cost, not a sixth feasibility factor. **Do not claim all five are gradients of one outcome likelihood.**
- Training: one masked, root-level observed-data joint NLL, plus separately justified endpoint-deduplicated static BCE and witnessed-travel log-Huber; unknown/not-run labels marginalized; scoped certificates and OPNEG-v1 operational negatives remain distinguished.
- F4 omission unary shares F2 `order_s` on the actual shortened ordered sequence. **No separate omission network** is authorized.
- Exact identical-candidate duplication must be invariant; genuine addition of physical relational information may change beliefs. `ABC9U_UNIQUE_V1` still permits role-specific coupling changes up to ~0.31 (B) / ~0.51 (C) in recorded alias-promotion tests. These are **not** proof of physically meaningful dependencies.
- P9-L3 validation contains only **12 roots**, with the three hardest roots accounting for ~95% of U-B-full validation NLL. The 24 disclosed-test roots are **not a new holdout** and must never be used to select models, losses, variants, thresholds, or training duration.
- At 400 updates, B-full unique vs PoE validation root NLL ~0.065 vs ~0.064 but disclosed-test NLL ~1.48 vs ~0.62: do not conceal the warning or use disclosed test to choose PoE.
- Geometry-only (`vision=False`) in P9-L3 changed parameter count and initialization. It is **not** a clean ablation. Do **not** discard DINOv2 or object-centric representations: their intended role in future 3D scenes remains essential to study. Slot Attention is a **possible** later perception choice, not a new requirement now.
- P8d matched 72 physical episodes across six arms. G+M succeeded **9/12**, previous B-full **8/12**; no P9 unique model has been physically executed. Do not re-label prediction-only gains as robot success.

---

## 1. Absolute inference, evaluation, and resource restrictions

1. **No IK, collision-checking, motion-planner, skill planner, teacher, physical verifier or simulator** may be invoked during learned intervention prediction, candidate scoring/ranking, ablations, or synthetic catalogue tests. All training/evaluation labels must already exist on disk. Synthetic manipulations of *candidate metadata alone* do not generate physical labels. Existing historical regression tests may separately call old deterministic planner fixtures; count and disclose those calls, and isolate them from training/inference.
2. Input = original scene/robot/goal geometry, frozen DINOv2 object features where enabled, *proposed* ordered object moves and destinations, and hypothetical pose edits for F3. **Never feed** outcomes, labels, teacher statuses, trajectories, privileged swept volumes, future observations, root identifiers or evaluation-split flags to the learned network. Oracle-revealed conditional analysis is **offline-only**, never selection input.
3. Preserve P8 static certificate precedence and the actual deployed selection semantics: validation-calibrated admission then lexicographic **fewest moves, predicted robot travel `J`, analytic displacement `C_d`, learned energy, query ID**, not a simplified probability-first `(moves,-p,id)` proxy. Selection reports may check existing saved outcomes *after* the choice; no planner calls for alternatives.
4. Freeze all old data, P8/P9 code and checkpoint manifests. Prefer additive small modules/tests and reports. Do not mutate `unique_factor.py`, `joint_likelihood.py`, `abc7_models.py`, historical tests, old reports or 0027/0033 result tables. Any future code reuse should be via wrappers/adapters and a versioned new model identifier.
5. **Aggregate compute budget: 5,000 CPU-seconds and 12,000 wall-seconds for this entire L3c/L3d task, including regression and failed attempts.** At most 1,500 CPU-seconds and 3,000 wall-seconds per worker; one trainer at a time; reproducible process-tree resource guards and append-only attempt ledger. **Zero new teacher/planner/IK calls** in learned paths. No implicit rollover of unused earlier phase budgets. If guard/ledger unavailable, restrict to read-only analysis and stop with `BLOCKED`.
6. Test/evaluation work may be performed on CPU using existing datasets, pretrained scene features and small networks. No new foundation-model pretraining, DINO feature extraction over new data, or large GPU experiments.

---

## 2. L3c-0 — Mandatory factor ontology and deployed selection audit (NO new training)

Write `runs/p9/l3c/L3C_0_PLAN.json` first, freeze its hash, and use only existing checkpoints/data for this stage.

### 2.1 Enumerate actual nodes and factor instances

For ≥6 representative multi-repair saved roots and at least one empty-only root, enumerate **literal** binary nodes and the actual contributing factor instances:

- root scene variables `z0`, `zS[I]` and root `P_S` factors (once);
- sequence-outcome variables `x_q` for full repair and every omission alias (one per canonical physical query);
- F2 sequence unary keyed by `(root state, target/goal, exact ordered moves and exact destinations)`;
- F4 `zR–zO` factors keyed by physically meaningful `(full physical sequence, omitted action position/identity, resulting physical sequence)`; discuss when two descriptions should or should not count as distinct factors;
- F5 scene–query and omission–omission pair factors; record their **actual** role embeddings, parent repair context and semantic variable scopes;
- F5 higher-order `ho_q` per parent block, including exact scene/query scope and model context; F5 root scene-only HO `ho_s` once;
- F1 static endpoint checks and `J` outside joint-outcome likelihood.

For each factor record: variable scope, raw network/potential, physical identity key, parameter sharing, conditioned information, multiplicity in a root, and why adding/removing this factor would or would not represent a real physical relationship. Note that an ordinary `factor graph` has **factor instances**, not necessarily one box for each of the five factor **families**. Draw a diagram with circular variable nodes, square factor nodes and conditioned context separately; use an actual existing saved root, **not** invented numbers.

### 2.2 Distinguish catalogue transformations

Using identical frozen model weights and **no labels passed into prior inference**, run:

- exact duplicate candidate; candidate permutation; arbitrary ID renaming; unrelated/disconnected candidate; one-move omission promoted to standalone `zR` when **no new physical relationship** is introduced; and a genuinely new two-move sequence with new dependency scope;
- alias promotion under B-full/C-full with a new **role-specific** scene–repair pair; isolate the effect of that pair from the additional **higher-order factor** and from any legitimate new `zR–zO` relationships;
- conflicting candidate IDs: same ID with distinct sequence/destination/omission structure must **fail closed** with `IdentityError` or equivalent. Test this explicitly in a new wrapper or test before deduplication. Query identity must depend on actual physical semantics, not only an arbitrary label.

Measure maximum change in pre-existing query prior marginals, NLL (for existing labels only, interpreted correctly), and selection using **the full deployed selector** with its frozen calibration, costs and tie-breaks. State which transformations are required invariant and which are deliberately permitted to alter true relational factors. A synthetic candidate has unknown outcome; never presume success/failure.

Record **both** `root_prior` (deployable, no labels) and `root_posterior` (offline oracle-revealed, diagnostic only) separately. Include all factor-multiplicity histograms by role/scope. Do not use any alleged 'choice changes' from the previous simplified probability-first diagnostic as though they were tested deployed selections.

**L3c-0 PASS:** all baseline-source/query integrity checks; concrete ontology for F1–F5; exact duplicate, permutation, renaming and disconnected-component invariance for the canonical unique model; adversarial identity mismatch fail-closed; no label leakage/planner calls; correct deployment-selector implementation. Existing allowed alias sensitivities should be measured and reported, **not** hidden or automatically called failure. If a test contradicts the baseline model's declared semantics, report `FAIL` with trace and stop further model development.

Report: `responses-phases/0034_P9_L3c_factor_ontology_and_selection_audit.md`; gate: `runs/p9/l3c/L3C_0_GATE.json`.

---

## 3. L3c-1 — ONE optional minimal physically keyed relational variant (strict change budget)

**Goal:** Determine whether the remaining role-dependent alias sensitivity can be reduced without discarding learned dependencies. This is a **single optional competitor**, not permission to rebuild the factor graph. Only implement it if L3c-0 PASS and a small, exact implementation is feasible.

### 3.1 Design requirements

- Retain original `P_S(z_S|c0)` untouched and one root-consistent conditional normalization `Z_Q(z_S)`. Preserve `z0=zR[empty]`, all actual sequence-query identities, and missing-label masks.
- Preserve one F2 sequence unary per physical query and shared F2/F4 scorer; preserve F4 omitted-repair pair factors and **all available higher-order terms** with their actual scopes.
- For F5 scene–sequence relationships, investigate an optional canonical `(scene query, physical ordered sequence query)` key, computed using that physical sequence's own representation rather than whether it was introduced under the `zR` or `zO` role. Document parameter sharing and context choices. The same physical relation should appear only once; genuinely distinct multi-query relationships may each appear once.
- For `ho_q` and `zO–zO` factors, **specify exactly what physical scope/context causes two factor instances to be identical versus genuinely new**. Deduplication by parent-candidate string alone is not an adequate scientific definition. No silent omission, zeroing, reweighting or truncation of higher-order terms to manufacture invariance.
- Respect the fact that a new full candidate can introduce **genuinely new omission links** that were absent when it existed only as an omission. Invariance is not mandatory for those genuinely new edges/hyperedges.
- A narrow model may lack exact one-candidate equality to ABC7 because canonicalizing role embeddings changes its pair potential; if so, explicitly state and test this, rather than claiming architectural identity. It must nonetheless retain *all five factor families*, higher-order expressivity, exact normalization and physical semantic identities.
- The variant may add a few narrowly scoped learned adapters if necessary, but **no new factor family, no independent omission head, no additional supervision term and no broad redesign**. Favor reusing trained networks and changing instantiation keys only if physically justified. Document parameter counts.

### 3.2 Strict go/no-go

Before implementing, produce a 1–2 page feasibility memo stating whether *scene–query pair*, *omission pair*, and *higher-order* scopes can be physically canonicalized within a **small adapter** and existing exact-inference cap. If achieving advertised invariance requires deleting HO, inventing labels, changing the input/label protocol, abandoning five families, or sprawling into a new architecture, **do not implement**. Mark `NARROW_VARIANT_BLOCKED`, keep `ABC9U_UNIQUE_V1` as the default, and proceed to the visual control and evidence proposal. Such a block is an acceptable outcome, not a phase failure.

If implemented, use a separate new `unique_factor_keyed.py` (or a similarly small isolated module), a model version string, and independent tests for each scope and counterexample. Provide toy brute-force numerical equality on small rooted graphs; normalization/scene marginal tests; monotonic gradient/finite-difference checks; duplicate/permutation/ID invariance; physically redundant alias test; genuine-new-relation behavior; extreme energies and elimination-scope fail-closed. Report the absolute differences at **frozen existing checkpoints before retraining** to isolate factor-instantiation semantics.

**L3c-1 gate:** `PASS` if verified, `BLOCKED` if not feasible within constraints, `NOT_RUN` if L3c-0 failed. Any implementation failing numerical exactness or leaking physical labels is `FAIL` and cannot be used for training or freezing.

Report under `responses-phases/0035_P9_L3c_keyed_factor_comparison.md` (or write a `BLOCKED` note explicitly); gate: `runs/p9/l3c/L3C_1_GATE.json`.

---

## 4. L3d — Limited saved-data learning controls and freeze decision

**Mandatory after L3c-0 PASS regardless of whether L3c-1 was `PASS` or `BLOCKED`.** Do not make further architectural variants.

### 4.1 Capacity/input-controlled visual representation test

DINOv2 is intended for eventual object-centric **3D** perception, including object recognition and properties not captured by simple geometry. Keep it available in the method. Evaluate whether the 2D results actually need it:

- Existing full-vision **U-B-full** checkpoints are the reference; for a matched input ablation, instantiate **the same** B-full architecture with `vision=True`, identical parameter count and seed initialization, but replace the **precomputed visual-feature input** with a fixed zero tensor **consistently throughout training/validation/evaluation** (not only at test time).
- Do not use `vision=False` for this primary controlled comparison because it deletes the projection and changes initialization/parameter count. Keep P9-L3's `vision=False` result as a historical diagnostic only.
- The visual-zero run has the same *nominal* architecture/parameter count but fewer effective informative inputs; do not call it a proof of equal effective capacity. Record input masking and the gradient path/bias behavior. No new DINOv2 inference or external image collection.
- Match optimizer, root sampler, initialization and batch sequence to the chosen existing U-B-full full-vision checkpoint(s). Prefer the **400-update** schedule already reported to have much better validation NLL; use the same schedule and checkpoint-selection policy, no test-informed hyperparameter sweep. If full-vision 400-update checkpoints are unavailable or cannot be verified for all 3 seeds, fall back to the **predeclared 200-update matched** baseline for all arms; do not mix durations.
- Three seeds (0,1,2) where safely feasible under the overall budget. If a trial cannot complete under budget, report partial results and refuse superiority claims.
- Compare validation-only decisions using exact root NLL and per-observed-query NLL, root-stratified accuracy/calibration and scene/repair predictions, proof provenance, likelihood concentration in the top three roots, and leave-one-root-out sensitivity of aggregate conclusions. The already-disclosed test remains descriptive only.

### 4.2 Optional tiny narrow-versus-existing comparison

Only if L3c-1 PASS **and** there is clear CPU budget after visual-control and correctness work: train the one **keyed** alternative versus frozen `ABC9U_UNIQUE_V1` at matched **200 updates**, seeds 0–2, same root batches and starting weights, while preserving identical supervision. Do not use disclosed test for variant selection. If omitted, record `NOT_RUN` and prefer original Unique by simplicity.

Report under `responses-phases/0036_P9_L3d_visual_control_and_model_freeze.md`; gate: `runs/p9/l3d/L3D_GATE.json` with `PASS`, `FAIL`, `BLOCKED` or `NOT_RUN` for the engineering gate, and a separate `scientific_verdict` field (never infer scientific superiority merely from an engineering `PASS`).

### 4.3 Select and freeze, with a one-page signed configuration manifest

Write `runs/p9/2d_freeze_manifest.json` and `responses-phases/P9_2D_FREEZE_DECISION.md`. Decision options:

- `FREEZE_UNIQUE` — preferred default if the keyed alternative is blocked, not reliably better, or only provides cosmetic invariant changes. Document remaining allowed candidate-role sensitivities and all scientific uncertainties.
- `FREEZE_KEYED` — only if exact semantics, five-family retention and invariance are verified, no new unjustified factor effects are introduced, and neutral validation evidence is not materially degraded. Do not pick it on disclosed test results.
- `FREEZE_BLOCKED` — if an unresolved contradiction, label leak or invalid likelihood prevents a trustworthy 2D model.

The manifest must pin: model family/version, exact factor ontology and known allowed sensitivity, objective and coefficients, source hashes, dataset and root splits, DINOv2 mode (retain enabled in canonical 3D-ready model unless extraordinary validation justifies otherwise), selected checkpoint(s) and hashes, calibration/threshold rules, full deployed selector, teacher status definitions, exact inference complexity limits, and incomplete physical-evidence claims. **Freeze model logic, not scientific superiority.** No 3D implementation is allowed by this instruction.

### Mandatory external-validity note

Do not call `root NLL` a test of action-order causality or omission necessity unless the data contain independently decided pairs. No same-endpoint order contrast on the P8c fresh set; no omission-only test labels; κ=+1 evidence only operational for reported test roots. Clarify any P7 historic order evidence separately. No claim that the learned model beats G+M at actual execution.

---

## 5. P10 targeted physical-evidence pilot: **design only, not execution**

Write `responses-phases/P10_TARGETED_CAUSAL_EVIDENCE_PILOT_PROPOSAL.md`, a **specific implementable protocol proposal** for *subsequent user approval*, without calling IK/planner or collecting one new label now. Include:

- Primary causal questions: genuine A/B/A+B intervention complementarity; same-endpoint opposite order from same robot state; physical repair-omission necessity; unnecessary-repair/feasible-original controls; alternative destinations; static-invalid screens; a constructor-disjoint obstacle family; held-out nuisance appearance versus geometry; and fixed-robot intervention vs actual sequential execution.
- **Prioritize by decisiveness, not coverage count:** at minimum one independently witnessed/certified physically meaningful contrast of each high-value category before a larger benchmark. Distinguish VERIFIED, sound certified infeasible (including place-side soundness if available), operational BUDGET_INFEASIBLE, UNKNOWN and NOT_RUN. No fabricated negatives or conditional-independent assumptions disguised as evidence.
- Mechanism diagrams for 2D robot/objects with concrete object/destination/order examples; initial scene, robot q0, intervention target, candidate repair sequences, omitted versions, exact teacher question, label provenance, and predicted outcome differences under F2/F3/F4/F5 removals. No invented witnessed outcomes.
- Freeze root/disjoint constructor splits *before* any teacher query, a blind holdout untouched by earlier reports, paired controls and matched G+M (strong geometric baseline) / A / SF / B / C evaluation. One-shot executed evaluation separated from training-label query budget. No learned IK-based screening at prediction/ranking.
- A staged **proposed** teacher CPU/query/scene-root budget including stop rules and expected cost based on P8c usage; label it *REQUESTED, NOT AUTHORIZED*. Clearly state what failure or unconstructible +1 would mean, and avoid using operational negatives as proofs.
- 3D transition appendix: 3D object-centric observations (RGB-D/multi-view, masks/tracklets, possible frozen DINOv2 features or optional Slot Attention), 3D pose/shape/region features, observed vs privileged state, fixed-robot scene edits, higher-level TAMP repair ordering, and 3D motion planner only for training labels and executed selected action. **Same conditional binary outcome graph and five factor families; no radical methodology change**. Explicitly note 3D sensor/perception/teacher code is NOT implemented here.

This proposal is the scientific handoff to a separate future authorization. It must not claim results from experiments that have not happened.

---

## 6. Deliverables, visualization, tests, repository discipline

Use existing top-level code layout; **no new nested package tree**. The preferred engineering budget is one compact audit/runner module + optional one isolated keyed-factor adapter + focused tests; avoid growing `p9_run.py` and `p9_l3.py` further. If a driver exceeds 300 logical lines, split *by audit vs training* only into at most two short top-level scripts or justify every additional line. Existing historical code, old datasets, checkpoint manifests and old reports immutable.

Required reporting/filenames:

1. `responses-phases/0034_P9_L3c_factor_ontology_and_selection_audit.md`
2. `responses-phases/0035_P9_L3c_keyed_factor_comparison.md` (or reasoned `BLOCKED/NOT_RUN`)
3. `responses-phases/0036_P9_L3d_visual_control_and_model_freeze.md`
4. `responses-phases/P9_2D_FREEZE_DECISION.md`
5. `responses-phases/P10_TARGETED_CAUSAL_EVIDENCE_PILOT_PROPOSAL.md`
6. `runs/p9/l3c/L3C_0_GATE.json`, `L3C_1_GATE.json`, `runs/p9/l3d/L3D_GATE.json`, `runs/p9/2d_freeze_manifest.json`, and `runs/p9/l3c/`/`runs/p9/l3d/` manifests, plans, source hashes, per-attempt ledger and results.

At least three interpretable artifacts (all with input/config SHA-256 manifests), using **actual saved scenes/results**:

- Variable-node **circles** / factor-instance **squares** factor graph, differentiating query-unique unary vs scene–query pair, omission pair, and higher-order potentials. Show aliases explicitly.
- Probability/candidate-selection changes under genuine new relational factors versus redundant alias/duplicate; show actual deployed selector and probability calibration.
- Full-vision versus matched visual-zero validation curves, grouped NLL and sensitivity to the three dominant validation roots. Do not fabricate new execution videos/GIFs.

For every gate report **PASS/FAIL/BLOCKED/NOT_RUN**, measured criteria, counters, CPU/wall accounting, exact independent oracle/teacher/planner calls (zero in learned paths), and source/plan hashes. Unit/integration tests must cover numerical normalization, exact brute-force checks on toy roots, gradients for each surviving factor family, zero static/travel outcome-NLL gradients, identity clash failure, alias invariance expectations, missing labels, no inference planner imports, and determinism. Rerun historical suite/replays under the **same aggregate CPU guard** if affordable; if not, report `NOT_RUN` honestly rather than silently reusing the earlier suite PASS.

**Immediate fail-closed conditions:** unverified label/query identity, differing source/dataset hashes, privileged evaluation-label exposure, teacher/planner calls in inference, broken normalization, lost scene consistency, pseudo-exact approximation beyond scope, dropped higher-order factor without explicit declaration, unauthorized new physical observations, truncated or fabricated metrics, or changed P8/P9 results. Preserve previous gate files; newly discovered concerns go into an erratum/new report, not retroactive edits.

**Git:** stage only intended new/changed instruction code/tests/reports/manifests/figures and small necessary checkpoints. Avoid staging user-owned untracked PDF/MD copies or seed 1/2 checkpoint files by default; hash them and explicitly distinguish `LOCAL_ONLY` from committed. No force push. Commit and push safely if branch is synced and the user repository is configured; verify exact remote SHA after push. If remote access fails, disclose instead of claiming push success.

**Response to the user:** state (i) 0034/0035/0036 gates, (ii) freeze decision and factor interpretation, (iii) most important validation and visual-control numbers, (iv) known scientific unknowns including +1/order/omission/execution, (v) no teacher/planner calls for learned checking, (vi) budget used, (vii) exact reports and push SHA, (viii) that P10 is **proposal only** and actual data collection/3D await separate approval. STOP at this contract boundary.
