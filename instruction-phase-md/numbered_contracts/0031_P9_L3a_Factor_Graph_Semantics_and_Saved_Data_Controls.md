# 0031 — P9-L3a/L3b: Factor-Graph Semantics, Catalogue Invariance, and Saved-Data Controls

**Execution contract for Claude Opus 5.5 High (Antigravity)**  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Verified reference commit:** `4be6d803bbfcff693b8055eb4e2e25707a8da4ee` (`4be6d80`)  
**Repository placement of this instruction:** `instruction-phase-md/0031_P9_L3a_Factor_Graph_Semantics_and_Saved_Data_Controls.md`  
**Authorization:** L3a semantics audit, conditional-inference parity, a *gated* canonical unique-factor prototype; L3b *gated, budgeted* matched **saved-data-only** comparison. **No physical teacher queries, new data, new simulation/robot episodes, 3D, hardware, L4, or automatic rollout.**

> **Core scientific goal.** Decide whether the **existing P9 product-of-experts (PoE) root construction** or a **single conditional normalizer with one well-defined instance per physical factor** is the appropriate implementation of the originally intended five-family joint Boltzmann factor graph. Compare the methods fairly; do not assume the proposed alternative wins. A factor graph is useful only insofar as its factors represent actual physical relations, not an accidental count of how often the catalogue lists the same query.

## 0. Read-first and immutable baseline

Read **entirely** before coding:

1. `instruction-phase-md/latent_causal_tamp_methodology_v1_8.md`;
2. `instruction-phase-md/latent_causal_tamp_implementation_guide_v2_0.md`;
3. `instruction-phase-md/0028_P9_Opus_5_5_High_Joint_Boltzmann_Migration_Prompt.md`;
4. this instruction;
5. `responses-phases/0028_P9_L0_source_and_likelihood_audit.md`;
6. `responses-phases/0029_P9_L1_exact_joint_boltzmann_math.md`;
7. `responses-phases/0030_P9_L2_saved_data_joint_objective_comparison.md`;
8. `responses-phases/P9_NEXT_DECISION.md`, plus `P8_DECISION.md` and reports 0024–0027 where needed.

Inspect **actual code**, not only reports: `abc7_models.py`, `abc7_train.py`, `abc8.py`, `joint_likelihood.py`, `p9_run.py`, `p8_eval.py`, `p9_viz.py`, `p8_select.py`, `tests/test_p9_joint.py`; inspect `runs/p9/l2/{L2_plan.json,summary.json}` and the three P9 gates. Locate versioned docs in `instruction-phase-md/` or report an explicit missing-document blocker. Preserve all old reports and data; do not alter P8/P9-L0/L1/L2 artifacts, pretrained models, gates, or teacher configuration. Capture repository status, hashes of all touched sources, and verify `HEAD` and `origin/main`; do not discard pre-existing user changes or overwrite untracked files. If commit advanced after `4be6d80`, inspect and reconcile, do not reset history.

Historical facts **not to misstate**:

- P9-L0/1/2 are reported engineering PASS (349/349 tests, six archived replays, 27 saved-data training runs) but no proven scientific gain.
- P9 objective for B/C is masked **root-level observed-data joint NLL** + **endpoint-deduplicated static BCE** + **witnessed robot-travel log-Huber**. Static and J are not gradients from `P(z|r,c0)`.
- `P_S(z_S|c0)` is root-scoped; repair outcome blocks are conditional on scene bits; `z0=zR[empty]`; one physical query may appear in complete- or omitted-repair slots; UNKNOWN/NOT_RUN are missing, not failures.
- Existing P9 uses `P_S(z_S) × Π_r P_{Q,r}(x_{σ_r}|z_S)/Z_eq(z_S)` and **allows catalogue-sensitive PoE beliefs**, with aliases tied exactly. The new unique-factor model is an **alternative hypothesis**.
- F4 omission unary already uses the **F2 `order_s` sequence scorer on the actually omitted ordered repair**; the specifically omission-related factor is the `zR–zO` pair. A separate omission network is **not a default requirement**.
- DINOv2 appearance features **are used**; an independent appearance benefit is **not shown**.
- The P8/P9 disclosed test splits are **legacy diagnostics**, not untouched external generalization tests.
- P8 one-shot G+M outperformed tested learned arms, and P9 did not perform any new execution.

## 1. Absolute execution and evidence boundaries

**No teacher or IK/planner calls in model scoring or intervention inference.** The learner must predict hypothetical fixed-robot scene interventions, physical repair success, and omitted-repair outcomes from the scene and proposed edits/sequences. Ground-truth labels were previously produced using an independent physical teacher. For **this task**, use only saved labels and existing learned features. Absolutely no new training labels, per-candidate IK/planner screening to improve rankings, fallback planning to check interventions, fresh simulator calls, or robot trajectories. The full historical regression suite might invoke previously existing deterministic planner fixtures; run it isolated from learning/evaluation and report those fixture calls separately. Do **not** confuse that with a newly authorized teacher budget.

- A/B/C and SF must not see labels, teacher failure categories, trajectories, privileged future swept volumes, split/instance IDs or post-intervention teacher renderings at inference. Oracle-revealed conditional diagnostics are **offline evaluations only** and never candidate-selection inputs.
- Preserve the frozen candidate catalogue for primary matching and use original statuses: VERIFIED; scoped CERTIFIED; OPNEG-v1 BUDGET_INFEASIBLE; UNKNOWN; NOT_RUN. No label upgrading or inference from timeouts.
- Keep static certificate priority, current deterministic ranking and move-count-first/robot-J/displacement ordering, one-shot selection/commit semantics and existing robot physics completely unchanged. No P9 L3 training choice may use disclosed-test labels.
- This stage is **not** a physical success-rate experiment. Its successes are mathematical and offline predictive; do not claim end-to-end gains.

## 2. Required mathematical distinction: three different claims

For scene/root context `c0`, root-scoped scene bits `z_S = (z0,zS[I]...)`, finite repair catalogue `C`, unique physical sequence-query variables `x_q`, and one alias map `σ_r` per repair:

### 2.1 Current ABC9-PoE (retain as baseline)

\[
P_{\rm PoE}(z_S,x\mid c_0,C)=P_S(z_S\mid c_0)\frac{\prod_{r\in C} P_{Q,r}(x_{\sigma_r}\mid z_S,r,c_0)}{Z_{\rm eq}(z_S,C)},\quad
Z_{\rm eq}=\sum_x\prod_{r\in C}P_{Q,r}(x_{\sigma_r}\mid z_S,r,c_0).
\]

This is a legitimate normalized conditional joint, verified against brute force in P9. It is **not automatically duplicate-invariant**. The same query can receive repeated unary contributions even though its observed label is represented by a single variable. Thus `one observed bit once` and `one physical factor instance once` are different properties.

**Toy thought experiment (not an experimental result):** a Bernoulli expert assigns `P(x=1)=0.8`. Duplicating that expert and renormalizing yields `0.8²/(0.8²+0.2²)=0.941176…`. An exact duplicate catalogue entry must be identified distinctly from a genuinely new physical relation.

### 2.2 Canonical unique-factor conditional root model (proposed competitor)

Define an **explicit list of physical factor instances**, each with stable semantic identity and parameter sharing:

\[
E_Q(x,z_S;c_0,C^*) =
 \sum_{q\in Q^*}\phi_{\rm seq}(x_q;q,c_0)
 +\sum_{e\in O^*}\phi_{\rm omit}(x_{r(e)},x_{r(e)\setminus t(e)};e,c_0)
 +\sum_{f\in K^*}\phi_{\rm couple}(x_{scope(f)},z_{S,scope(f)};f,c_0),
\]

with any other valid repair-scoped unary terms **explicitly declared**, not silently removed. Scene energies, including F3 scene unaries / structured `z0–zS` pairs and F5 scene-only coupling, enter the **root-scoped** `P_S(z_S|c0)` **once**. Define

\[
P_{\rm unique}(z_S,x\mid c_0,C^*)=
 P_S(z_S\mid c_0)\,
\frac{\exp[-E_Q(x,z_S;c_0,C^*)/T]}{\sum_{x'}\exp[-E_Q(x',z_S;c_0,C^*)/T]}.
\]

This retains **one conditional repair-state normalizer per scene state**, so `sum_x P_unique=P_S` for any declared catalogue; do **not** replace it with a single unrestricted normalizer over `(z_S,x)` and quietly change scene priors. F1 static and travel-J stay outside this conditional outcome graph with their existing justified auxiliary supervision.

**Key caution about reusing ABC7:** `ModelBC7.joint` produces *already-normalized* `logP_Q` tables from a repair-specific energy, and its F5 higher-order network can span a whole block. The alternative must extract or explicitly re-evaluate **raw factor potentials with their real scopes and contexts**, not simply sum independently normalized `logP_Q` tables and call that a unique-factor construction. If exact factor-instance extraction is impossible within scope, fail closed with a concrete explanation—do not substitute a sigmoid graph, quietly discard higher-order terms, or mislabel a new model as equivalent to B-full.

**Type/context consistency:** ABC7 assigns `zR` versus `zO` type embeddings in *pair representations*. A physical query shared across these roles has one binary value, while its **genuine role-specific pair interaction** can remain distinct. An outcome unary must not be counted twice or become arbitrarily dependent on whether a query was named `zR` or `zO` in the catalogue. Canonical query identities should include the original scene state, exact ordered moves/destinations and final target semantics; validate existing query IDs against this meaning.

### 2.3 What the model may and may not depend on

- **Must be invariant:** repeating the same catalogue candidate with the same physical meaning; permuting candidate presentation order; adding redundant aliases without new physical interactions; renaming dummy IDs.
- **Should be invariant when truly disconnected:** adding an independent factor component to the same root conditional distribution must not alter an unrelated query's marginal; scene priors must be unaffected by the repair catalogue.
- **May change legitimately:** adding a *genuinely distinct repair* that introduces a new relational factor connecting previously modeled outcomes. Measure this change; do not force unrelated- and related-candidate cases into one rule.
- **Must remain normalized:** prior `P(z_S)` root-consistent, posterior `P(z_S|observed repair outcomes)` **allowed** to change. Keep prior and posterior names separate.
- **No claims of causal DAG recovery:** factor edges are probabilistic dependencies supported, where possible, by controlled physical labels.

Do not normalize repair-choice `P(r|c0)` by accident: this is an **outcome probability model conditioned on a finite candidate catalogue**, followed by a separate repair-selection comparator. Number of moves and analytic displacement are not latent Bernoulli variables or new feasibility losses.

## 3. L3a: frozen mathematical audit, *before* proposing new training

### Gate L3a-0 — source/evidence audit (nonmutating)

- Confirm exact commit, saved dataset/checkpoint hashes, three P9 gate contents, all existing P9 reports and current main worktree status.
- Reproduce a small saved-root P9 prediction; separate `per_candidate`, `root_prior`, and `root_posterior_if_conditioned_on_labels` outputs. All selection must use **prior model probabilities without oracle labels**.
- Inspect current `joint_likelihood.log_evidence`, `marginals`, `tables`, `losses`, ABC7 `scene_block`, `_pairs`, `joint`, `order`, `p9_run.root_eval`, `p9_run.evaluate_model`, and `p8_eval.conditional` and create one exact code-path diagram.
- Explicitly identify **which metrics use root marginals** and **which still call per-candidate `p8_eval.conditional`**, and repair the comparison/reporting ambiguity in new evaluation code only. Do not rewrite P9 historic results.
- Verify that P9's name "one label counted once" refers to one observed variable, NOT necessarily a single neural energy contribution; report catalogue multiplicity per query and by factor type.
- Compute a **tiny, saved-data-only** sensitivity audit: catalogue order permutation, exact duplication, irrelevant/disconnected candidate, new related candidate, alias duplication, root scene-prior invariance. Mark each case `EXPECTED_INVARIANT` / `ALLOWED_CHANGE` and record whether P9-PoE passes or fails. Expected PoE failure is a **finding**, not a reason to falsify the baseline.
- Write `responses-phases/0031_P9_L3a_catalogue_and_inference_audit.md` and `runs/p9/l3a/L3A_0_GATE.json` (PASS/FAIL/BLOCKED). **Stop if original source/data integrity, label isolation, or frozen evidence is compromised.**

### Gate L3a-1 — exact two-model semantics (no training)

If L3a-0 passes:

1. Build a **minimal isolated prototype** of canonical unique-factor root inference for B-full **and** B-structured, retaining original factor functions/weights wherever feasible; C-full only if the B equivalence and complexity checks pass. Do not modify P8/P9 historical learner classes or saved checkpoints.
2. Choose and document a canonical semantic identifier per variable and factor instance; deduplicate only exact repeated physical instances, never two genuinely distinct interventions with different order/destinations or contextual roles. For each candidate, expose meaningful scopes and test contribution of F2/F3/F4/F5. F4 unary remains shared with F2 unless separately justified. F1 and J remain outside.
3. Perform exact log-space variable elimination or an equivalent enumerated normalization. Establish a documented complexity cap, numerical stability, and deterministic failure on exceeded scope, never silent approximate sampling.
4. Implement explicit `prior_marginal(query)`, `conditional_marginal(query|observed_binary_evidence)` **offline diagnostic only**, `log_observed_evidence(masked_labels)`, plus static/travel scalar access. Root scene prior remains `P_S`. Do not use observed labels for repair ranking.
5. Include *independent brute-force proof fixtures*: no aliases; repeated exact aliases; same physical query used as `zR` and `zO`; 0-move `z0`; unrelated and genuinely related repair; nonzero structured and generic pair; higher-order; UNKNOWN and NOT_RUN; 2D ordered action swaps with identical endpoints; extreme energy scales/temperatures. Finite-difference gradients for F2/F3/F4/F5, zero outcome gradient to F1 and J, auxiliary gradient to F1/J. Test nonzero learned shared weights on a saved checkpoint.
6. **Invariance gates:** candidate permutation, duplicate candidate, duplicate alias without a new relational factor, unrelated component, scene prior, conditional normalization, all-missing `log P=0`, logical identity, identical result across deterministic runs.
7. Explicitly compare **P9-PoE**, **deduplicated-PoE diagnostic** (canonicalize exact repeated candidate blocks *only*, not an asserted complete solution), and **unique-factor model**. Do not call a deduplicated-PoE model the unique-factor model. Illustrate the `0.8→0.941` counterexample using a 1-variable toy and a real saved root if available.
8. If the raw high-order F5 potentials cannot be reconstructed at acceptable engineering cost, separate `B-quadratic` as a clearly **restricted** prototype, declare B-full unique-factor `BLOCKED`, and stop before using it as the primary scientific competitor. Do not silently compare incommensurate factor families.
9. Run new unit tests and the full historical regression suite / archived replays **only if safely possible**, with old planner fixture calls instrumented separately from the learned inference path.
10. Deliver `responses-phases/0032_P9_L3a_unique_factor_mathematics.md`, `runs/p9/l3a/L3A_1_GATE.json` and 2–3 legible figures. PASS requires mathematical validity and identity/invariance in the unique-factor model, not improved NLL. If FAIL/BLOCKED, stop; no training.

**Engineering style:** smallest possible code change: a focused new root-factor module plus a compact driver/testing extension; avoid edits to `abc7_models.py`, `joint_likelihood.py` and previous datasets, and avoid growing the existing ~832-line `p9_run.py`. A large >300-line new driver needs justification or modularity revision. Tests and separate documentation are fine. Version model name, hash every plan/config/checkpoint, render a *literal factor graph* (circles for binary variables, squares for actual factor instances; conditioned inputs visually separate).

## 4. L3b: conditional, bounded saved-data evaluation

**Only authorized if both L3a gates PASS, factor families are comparable, and the fixed plan is written *before* training.** If either is BLOCKED/FAIL, publish partial results and stop. Do not use disclosed legacy test performance to select variants, hyperparameters or checkpoints. **No new teacher/IK/planner data.**

### 4.1 Frozen experimental plan

Save `runs/p9/l3b/L3B_plan.json`, signed/hashable before the first learner update. Include every job, random seed, sampler sequence, frozen train/validation/disclosed-test root keys, exact active label mask and provenance; model version and factor instance schema; optimizer and gradient clip, training duration/checkpoint policy, loss weights (prefer joint NLL + 1×static BCE + 1×witnessed J); calibration; source SHA; CPU guard; and a stop decision if training exceeds caps. Preserve old comparisons with their original settings. Do not claim a changed number of updates is a matched objective-only comparison.

**Budget authorization for this instruction:** at most **8,000 aggregate CPU-seconds** and **18,000 aggregate wall-seconds** for **all new L3a/L3b audit, test, model construction, training, calibration and evaluation work**, including failed attempts (existing historical replays separately itemized if mandated by regression and covered by remaining budget); ≤1,800 CPU-s and ≤3,600 wall-s for any worker; at most one training worker at a time. **Zero new teacher queries**. If environment lacks a reliable CPU guard, execute L3a-only proofs, disclose the blocker and stop. Do not use any unspent P9-L2 budget as additional allowance. There is no authorization for GPU-intensive retraining or additional models beyond the prioritized matrix below.

### 4.2 Prioritized arms and controls

**Required 200-update matched experiment, 3 seeds each (0/1/2), only if within caps:**

- Existing **P9-PoE B-full** and **P9-PoE B-structured** at their saved 200-update checkpoints (baseline, *no retraining necessary* if exact source and data match); report earlier clip and checkpoint selection.
- New **unique-factor B-full** and **unique-factor B-structured**, from the same available base model seeds/batches and shared factor parameter initialization; fixed 200 updates and training protocol, report parameter counts and genuine factor coverage. If fair matching cannot be established, report the discrepancy and do not claim causal superiority.
- A **factorized SF** baseline from saved P9 checkpoints, using equal observed physical queries.
- A **geometry-only unique-factor B-full** arm, with explicit zero reliance on DINOv2 features (model constructed with `vision=False`, NOT merely zeroing visuals at test time), same 3 seeds. Preserve the learned image-feature control for matched comparison.
- **C-full unique-factor**, 3 seeds, *only if* the same factor-instance semantics are implemented soundly and the budget permits; if not, mark this as `NOT_RUN` rather than removing C's historical results.

**Optional matched longer-training diagnostic, only after the mandatory comparison is secured and budget remains:** extend **both** PoE B-full and unique-factor B-full to a matched, predeclared 400-update schedule, starting from scratch with identical initialization and root minibatches. Do not simply extend one while comparing against the other's 200-update checkpoint; if maintaining the optimizer state from an exact matched 200-step run is impossible, restart both from scratch. Record best-validation update and learning curves. Avoid extra hyperparameter sweeps.

### 4.3 Metrics and evaluations (same model mode!)

Always report exact denominators and root-cluster uncertainty, per seed, provenance (VERIFIED/CERTIFIED vs policy-relative negatives), and both **prior/root** and **per-candidate** predictions with unambiguous labels. For the primary deployed/root model, derive all of these from its **own same joint distribution**:

1. Exact observed-data root NLL; average NLL per observed distinct query; roots with ≥1 label; stratify by single-bit/empty-only and full-catalogue roots.
2. Root-prior scene, physical repair and omission marginal NLL, accuracy/AUROC/ECE where defined; the same calibration/threshold selection protocol using validation only; rank and selection funnel, abstention, false-empty, known VERIFIED candidate opportunity, restricted-catalogue minimality. Static validity and travel diagnostics separate.
3. Root-derived `P(z_R=1 | zS[I]=0/1)` and `P(zO=1 | zR=0/1)` as **offline oracle-revealed conditionals only**; evaluate without feeding teacher labels into prediction/ranking. Legacy per-candidate conditionals reported **separately**.
4. κ interaction by sign (+1/0/−1) and proof provenance; no claims of +1 physical complementarity from operational place-side negatives. Order-swap contrasts by independently decided same-endpoint outcomes, with `N/A` if unavailable. Omission necessity similarly `N/A` if no independently decided comparison.
5. Exact duplicate/permutation/irrelevant-catalogue sensitivity, alias and z0 consistency, choice stability; compute/CPU/number of neural forward calls/model parameters, largest elimination scope; factor gradient histograms, overclipping and non-finite counts.
6. Confound review: whether geometry-only changed architecture capacity; whether longer training changes objective comparison; whether scene prior is identical; whether any improvement in joint NLL is driven mainly by few heavily observed roots.

No physical success rate is computed anew. P8d's G+M 9/12 vs learned results are **historical execution evidence only**.

**Evidence decision rule:** mathematical validity and invariant satisfaction are mandatory; prefer a simpler model when neutral metrics show no robust gain; do not select based solely on training likelihood, catalogue-length sharpening or disclosed-test performance. For scientific improvement use predeclared validation contrasts and root-cluster confidence intervals; small-N CIs are not proof of equivalence. Do not assert novel causal mechanism from factor removal or interpretability diagrams.

Write `responses-phases/0033_P9_L3b_saved_data_model_comparison.md`, `runs/p9/l3b/L3B_GATE.json`, `responses-phases/P9_L3_DECISION.md` with `KEEP_POE` / `KEEP_UNIQUE` / `SIMPLIFY` / `BLOCKED` and a clearly conditional future data proposal (no collection authorized). Save source hashes, guarded CPU ledger, checkpoints only as appropriate, and two useful result figures plus a factor-graph schematic.

## 5. Mandatory reporting and stop conditions

**Final reports, in order:**

1. `responses-phases/0031_P9_L3a_catalogue_and_inference_audit.md`;
2. `responses-phases/0032_P9_L3a_unique_factor_mathematics.md` (only if L3a-0 PASS; otherwise `BLOCKED` report with specific blocker);
3. `responses-phases/0033_P9_L3b_saved_data_model_comparison.md` (only if both L3a gates PASS; otherwise concise `NOT_RUN` report);
4. `responses-phases/P9_L3_DECISION.md`.

Gate status fields must be **PASS / FAIL / BLOCKED / NOT_RUN**, not a binary boolean concealing missing evidence. Every numerical plot must carry a data/config SHA-256 manifest. Visualize a **real factor graph** with variable circles and factor squares, and show duplicate-catalogue sensitivity and B-full vs structured vs SF/geometry-only comparisons. Do not create fake execution videos or robot trajectories. Keep repo subfolders minimal: reuse `responses-phases/`, `runs/p9/`, `visualizations/p9/`, `tests/`, and `instruction-phase-md/`.

**Immediate STOP / fail-closed:** unverified source/data identity; missing required docs; conflicting physical query labels; changed teacher policy; privilege/ID leakage; new IK/planner calls during inference; any unbudgeted dataset generation, simulation or physical execution; numerical discrepancy to brute force; loss of root scene-prior consistency; duplicate-candidate dependence in canonical unique-factor model; source mutation of P8/P9 historic artifacts; no reliable CPU guard; proposed uniqueness requiring silently dropping full-coupling/HO terms.

If mathematics makes the unique-factor model genuinely non-identifiable or too costly, **report that openly**, preserve P9 as a valid PoE baseline, and recommend a narrower explicit factor graph rather than fabricating completeness. Preserve every P9 prior gate as historical evidence; do not re-label it as failed retroactively.

**Git discipline:** Before coding record `git status` / `HEAD` / `origin/main` and hashes. Stage only the authorized new instruction, new code/tests/figures, reports and small reproducible manifests. Do not stage unrelated untracked datasets/checkpoints or erase PDFs. Commit/push after all permitted gated work if repository access is authorized and branch remains safely synced; otherwise report local commit and remote status distinctly. No force push. Do not claim `origin/main` updated without verifying it.

**Response format to the user:** concise gate-by-gate verdict, best-known root-model semantics, main numerical outcome and whether confidence is justified, what changed in code, all report paths, CPU spent and independent teacher/IK calls (should be zero for newly generated evidence), commit SHA and push status, exact STOP boundary. Distinguish physical execution success from prediction-only metrics. End the response after stopping at the contract boundary; no L4/3D/hardware.
