# 0037 — P10: 2D Scientific Validation of A/B/C — Master Execution Contract v1.0

**Status:** Next-stage execution instructions. Begin with **P10-0 (no physical queries)** and, when the operator explicitly accepts the launcher prompt's bounded authorization, **P10a (capped constructibility pilot)**. **P10b–P10e are documented here for continuity but are not authorized by the initial launcher.** Every stage must have its own source/data/plan freeze and STOP gate. This is a *scientific validation* program, not a new architecture project.

**Verified source state:** `Narendhiranv04/latent-causal-tamp`, commit `37cd2b7b84ce4666f93b13f31db331ae96a3e457`. Do not assume the repository has not moved; inspect current HEAD and report exact ancestry and dirty/untracked paths. Never overwrite user work.

**Authoritative project documents (read before changes):**
- `responses-phases/0034_P9_L3c_factor_ontology_and_selection_audit.md`
- `responses-phases/0035_P9_L3c_keyed_factor_comparison.md`
- `responses-phases/0036_P9_L3d_visual_control_and_model_freeze.md`
- `responses-phases/P9_2D_FREEZE_DECISION.md`
- `runs/p9/2d_freeze_manifest.json`
- `responses-phases/P10_TARGETED_CAUSAL_EVIDENCE_PILOT_PROPOSAL.md` (design only; superseded where corrected explicitly below)
- Historical P8c/P8d and P9 reports, Methodology v1.8, Implementation Guide v2.0.
- **Read actual code**, especially `abc7_models.py`, `abc8.py`, `abc7_train.py`, `joint_likelihood.py`, `unique_factor.py`, `unique_factor_keyed.py`, `p9_l3.py`, `p9_l3c.py`, `p9_l3d.py`, `ordered.py`, `evaluate.py`, `teacher.py`, `p8_select.py`, `p7_oneshot.py`, and existing tests. Documentation does not replace source audit.

---

## 0. Research question and immutable scientific boundary

**Research question:** Given an infeasible manipulation task, initial scene and robot state, and a finite catalogue of candidate high-level object relocations (object, destination, order), can learned object-centric, intervention-aware representations predict successful **minimal corrective repairs**, including causal interactions, order and omission, *without using a motion planner/IK to evaluate hypothetical alternatives at inference*, and does explicit **joint** outcome modeling provide an advantage over an independent sequential predictor and simpler baselines?

**Success is not predetermined.** If A or C beats B, report it. If no learner beats a geometry/motion baseline, report it. A correct negative scientific conclusion is an acceptable finished experiment; falsified positives, manufactured certificates, data leakage and cherry-picked comparisons are not.

**Do not redesign the methodology.** Retain A (LOCAL-SEQUENCE/GRU, independent re-scores); B (JOINT-CAUSAL-EBM, prefix/predecessor order representation); C (HYBRID-JOINT, B's graph with GRU order representation); binary outcome definitions; five factor families F1–F5; fixed-scene interventions; omission queries; shared encoders; DINOv2. Treat `ABC9K_KEYED_V1` as the B/C **canonical factor-instantiation logic**. Do not silently substitute `ABC9U_UNIQUE_V1` for frozen B.

### 0.1 What is learned and what is *not* learned

- Learned: object/scene embeddings; static-validity potentials (auxiliary); sequence success logits; ordered repair representations; scene/edit unary and structured interaction potentials; full-versus-omitted pair potentials; generic pair/higher-order potentials for B/C; predicted witnessed joint travel `J`.
- Not learned: continuous 2D destination generation beyond supplied finite catalogue; grasp/IK; collision checking or trajectory generation; analytic certificates; sound negative certificates; a causal DAG; global optimality.
- `z0` = original task success = empty-repair outcome; `zS[I]` = target-only success after **hypothetical fixed-q0 object pose edits**, NOT a physically executed relocation; `x_q` = success of a particular ordered physical repair from **the same** root; `zO[r,t]` = independently evaluated physical repair `r` with relocation `t` removed and **restarted from S0**.
- The physical teacher/planner may be called **only for generating independent training/assessment ground-truth labels** and **for executing the actually chosen repair**. During learned training steps, feasibility scoring, energy inference, hypothetical intervention prediction, ablation evaluation and ranking: **zero new planner/IK/collision-based feasibility or teacher calls**. Existing saved labels are permitted only as training targets and offline post-hoc evaluation, never as deployment inputs.

### 0.2 Canonical B/C probability and three-term objective

For a root with physical query set `V` and root-scoped scene bits `z_S`,

`P_K(z_S, x | c0, C) = P_S(z_S | c0) * exp[-E_K(x,z_S)/T] / Z_K(z_S)`;

`Z_K(z_S) = sum_{x ∈ {0,1}^{|V|}} exp[-E_K(x,z_S)/T]` (implemented via exact elimination, fail closed on MAX_SCOPE=16).

Each physical sequence query contributes one F2 unary, scene-query couplings once per `(scene bit, physical query)`, F4 omission relations by their actual ordered sequence scope, and retained F5 generic pairs/higher-order potentials by physical scope. Scene F3 and scene-F5 terms enter `P_S` once. F1 static endpoint energy and J are **outside the outcome likelihood**; a constant-in-z static term would cancel.

`L_B,C = mean_root[-log P_K(observed decided bits | root inputs)] + 1.0 * L_static_BCE + 1.0 * L_witnessed_logHuber_J`.

Missing UNKNOWN/NOT_RUN bits are marginalized; `BUDGET_INFEASIBLE` remains an **operational negative**, never claimed sound. A has its own historical documented non-joint training objective; do not mislabel A as training a joint root NLL. Compare A/B/C with identical input features, data splits, physical query budgets, candidate pools and appropriately disclosed optimizer/training budgets; report different objectives and parameter counts.

### 0.3 Physical 2D contract

2D fixed-base finite-width 3R arm with links/housings/palm/fingers/attached-object geometry, joint limits, fixed 48-grasp family; 8x8 placement support grid at 0.08 m pitch; discs radius 0.024 m, clearance 0.005 m; finite pick-place primitives; goal includes **GOAL_AND_SAFE_RETREAT**. Every order comparison starts from identical root scene, robot `q0`, target, grasp policy and destinations; each outcome is a **separate physical query**. No shortcut from a teleport/scene edit to a physical relocation label.

---

## 1. Research hypotheses and what can falsify them

Freeze a hypothesis registry and endpoints **before** teacher queries or training on new labels. Do not claim a factor is logically required because the resulting output changes on ablation: a factorized predictor can reproduce `kappa` from independent marginals; omission dependencies can also arise through shared scene/generic potentials.

| ID | Physical mechanism | Independent labels needed | Primary *prediction* endpoint | Test of additional learned value |
|---|---|---|---|---|
| H1 | **Complementarity**: neither A nor B alone removes blockage, both edits together enable task (`κ=+1`) | `z0`, `zS[A]`, `zS[B]`, `zS[A+B]` all decided; negative soundly certified within applicable scope, positive witnessed | Complete four-outcome contrast consistency; κ signed/calibrated error | B/C vs A, SF, scene-factorized; retrain −F5 scene coupling/HO, report if still able to predict κ |
| H2 | Redundancy (`κ=−1`) and neutral control (`κ=0`) | Full four-query set, root/goal matched | Per-root κ signed/error and four-bit NLL | Check that improvements on H1 do not destroy H2/neutral calibration |
| H3 | Same endpoints, **opposite action order**, from same `q0` | Both full ordered repairs independently VERIFIED or soundly CERTIFIED; never infer failure from a budget timeout | Paired correct-order choice and probability margin | A GRU vs B prefix/predecessor vs C GRU; −order controls; same-final-state geometry baseline |
| H4 | Omission necessity/redundancy | Witnessed full repair plus every compared omitted sequence from S0 decided independently | Necessity decision, ability to choose strictly shorter successful candidate | B/C with vs without F4 `zR–zO` pair, plus SF/A; any other dependencies explicitly reported |
| H5 | Initially feasible task, edited variants | Original `z0=1` VERIFIED; harmful/neutral edited target-only labels decided | Empty-repair choice; `z0–zS` calibration; unnecessary moves | B/C with vs without F3 structured pair, A, SF |
| H6 | Alternative destinations / travel | Paired different destinations, same moved object, decided complete repairs; J witnessed where applicable | Feasibility selection, J error and excess displacement | F1 static+B learned vs analytic F1 screen; J vs no-J ranking |
| H7 | Hypothetical scene edit **not equal** executable physical repair | Edit target-only query VERIFIED, matching sequence negative CERTIFIED/operational with source disclosed | Edit-versus-repair discrimination | F3-to-F2 coupling ablation, independent predictor |
| H8 | Constructor-disjoint swept/carry/robot-body obstruction | Independent scene family not generated by G+M heuristic; independent teacher outcomes | Generalization and one-shot success, rooted CI | Learned vs geometry-only, A/SF, **G+M** as planner-assisted reference |
| H9 | Nuisance appearance change, fixed geometry | Identical physical root/labels, altered texture/color only; masks and object IDs fixed | Probability shift and held-out appearance calibration | Full DINOv2 vs masked-visual control with matched training |

**Label provenance:** `VERIFIED_FEASIBLE` = full trajectory/witness including target and SAFE_RETREAT; `CERTIFIED_INFEASIBLE` = valid *scope-specific sound certificate*; `BUDGET_INFEASIBLE` = policy-relative 0 only under pinned OPNEG-v1; `UNKNOWN`, `NOT_RUN` = missing, never negative. Preserve original status, proof/witness metadata, planner budget and stop reason alongside training binary views. Never claim a **place-side** certificate: current `LINK0_SECTOR_PICK_V1` only covers its valid pick-side proof scope.

**Proof-grounded and operational results are separate estimands.** Report both if available; never pool them under a single “proved causal” label. If a decisive class is unconstructible, use `UNCONSTRUCTIBLE_UNDER_CURRENT_TEACHER` and limit claims.

---

## 2. Corrections to the older P10 proposal (binding)

1. **B primary is `ABC9K_KEYED_V1`, not the older unique-factor model.** `ABC9U` and PoE are historical modeling ablations only. The keyed 200-update B-full seed-1 checkpoint is provisional; all new learner comparisons use explicit, matched training schedules.
2. **C-full must use the keyed factor-instantiation adapter,** with its GRU order encoder; train and calibrate C alongside B. A remains a standalone GRU scoring/control architecture. Report model size and optimization effort; do not assert capacity equivalence.
3. **Do not assert**: “−F5 loses ability to predict κ”, “−F4 makes omissions independent”, or “−F3 cannot fit edit outcomes”. These are *hypotheses about incremental transfer performance*, not impossibility theorems.
4. **Do not silently mix two execution protocols.** A strict top-one learner proposal (`TOP1_COMMIT`) must call no planner on alternate candidate repairs; if its selected repair cannot be planned/executed, episode is a failure. The P8d `TOP5_PRECOMMIT` planner may test up to five ranked candidates before the first commit and is a **separate secondary experiment**. The original G+M is a *planner-assisted* baseline; include an analytic-geometry-only top-one proposer for equal no-IK-ranking comparison. Report planning calls and CPU by stage for every arm.
5. **No six-root “decisive” holdout.** The previous 54-root split (24 train/24 validation/6 holdout) conflicts with its own two-blind-roots-per-mechanism target for seven key mechanisms. Treat 14+ independent blind roots as a *minimum feasibility pilot*, not statistical proof; plan at least 24 train + 24 validation + 14 blind (=62 roots) only if later budget supports it. All children, appearance variants and near-duplicates inherit one parent split. A holdout must be genuinely untouched until predictions are sealed.
6. Freeze root-generation and query catalogues **before teacher outcome inspection**. Q8 constructor must not reuse G+M pose-screen logic as its own root-selection criterion. Maintain a disjoint family holdout and report any unavoidable geometric overlap.
7. Keep DINOv2 enabled in the B/C default. Visual-zero is an ablation; no Slot Attention or 3D implementation during P10.
8. Preserve no-physical-check prediction path; teacher checks of counterfactual scene edits are solely to **obtain supervised labels**, not live intervention screening at inference.

---

## 3. Stage P10-0: validation readiness, reproducibility and A/B/C checkpoint protocol

**Authorized without physical calls. Do this first.**

### 3.1 Source/data audit

- Verify commit ancestry, original P9 2D freeze manifest, source hashes, dataset manifests, existing P8/P9 checkpoints and archived replay hashes. List any untracked paths; do not delete or overwrite them. If frozen checkpoint is missing from remote, STOP with reproducibility blocker.
- Reproduce `392/392` tests and six archived replays under a recorded process-tree budget *only if the local runtime permits*; fixture planner calls are permitted for regression tests but isolate and itemize them—never classify them as learned scoring.
- Audit and unit-test static certificate precedence: confirm it operates **before** learned admission; do not rely on prose. Confirm the complete exact selector `(admit, #moves, predicted J, analytic Cd, energy, id)` against the deployed path and fail closed for candidate-ID collisions, factor-graph complexity and nonfinite values.
- Check that `ABC9K` module patching via `installed()` is scoped and restored after every training/evaluation call; no accidental use of `ABC9U` after context exit. A and SF do not use this patch.
- Register exact robot q0, goal, root scene, geometry hash, grasp profile, source IDs, DINOv2 mask, root-to-split provenance; no outcome or teacher metadata in learner inputs or proposal generation.

### 3.2 Matched saved-data B/C/A baseline

- Reproduce frozen `K-B-full#s1` val root NLL 0.255281... at 200 updates **before new training**. Its model logic is frozen, checkpoint provisional.
- Set one comparison plan before running anything: paired seeds 0–2, identical P8c train/validation splits, known 200 and/or 400 optimizer-update schedules, identical candidate catalogues, same DINOv2 input, fixed evaluation metrics, saved outcome status handling and parameter/CPU accounting.
- **Priority 1:** 400-update keyed B-full and keyed C-full with appropriate shared training pipeline, selected checkpoints only by validation. **Priority 2:** A re-training at the matched schedule *if feasible and useful*; existing A checkpoint remains a historical control if skipped; never fake comparability. **Priority 3:** SF/B-structured control only if within budget.
- B/C: canonical keyed three-term objective. A/SF: their own documented supervised losses, not a fictitious shared joint NLL. Compare common physical bit-NLL and decision endpoints, not only architecture-specific training losses.
- A/C same-seed paired run is important for disentangling GRU order representation from B's predecessor representation; C should not inherit a different data or model version.
- Record CPU spent incl. failed runs; early-stop on nonfinite/invariance failure. If training cannot fit declared cap, run a declared pilot subset and mark comparisons incomplete. Do not change dataset split or warm-start from disclosed-test metrics.

**Initial P10-0 learner compute allowance:** at most **4,000 CPU-seconds** (one worker; max 1,800 per job, 3,600 wall per job; 10,000 aggregate wall); stop when exhausted. This is a cap, not a target. Do not spend additional compute without separate authorization.

### 3.3 Pre-register statistical analysis

- Fix primary endpoint per H1–H9 and the planned *paired unit*: independent reference root/constructor seed. Children, candidate queries, nuisance appearances and opposite orders are dependent within a root; never bootstrap them as independent replicates.
- Archive frozen definitions of `κ = p_{AB}−p_A−p_B+p_0`, sign handling, score, missing-label exclusions and certificate-vs-operational strata.
- Report own-joint exact root NLL for B/C, **common** per-observed-event NLL/accuracy/AUROC/Brier/ECE on matched decided outcomes for A/B/C/SF, separately root prior, per-candidate and oracle-revealed **offline-only** conditional diagnostics. Do not present oracle-conditioned likelihoods as deployable predictions.
- Compare selection on the **same admissible catalogue**; record no-repair abstention, false-empty, chosen #moves, known-catalogue regret, predicted J error, Cd, cost, rare mechanism success, and calibrated threshold fixed on validation.
- For each paired root contrast, report effect size, 95% root-cluster confidence interval, exact discordant-pair test where applicable, n roots, n decided contrasts, by-constructor subgroup and seed scatter. No equivalence claim from CI crossing zero. For small n, prioritize descriptive evidence and failure modes over p-values.
- Correct for multiplicity or designate one primary contrast each for H1/H3/H4 and the main TOP1 execution endpoint; label other ablations exploratory. Do not move thresholds after inspecting results.
- Significance is neither guaranteed nor required for engineering gate PASS. A study with insufficient contrast yield is **UNDERPOWERED**, not scientifically validated.

**P10-0 deliverables:** `responses-phases/0037_P10_0_validation_readiness_and_training_protocol.md`; `runs/p10/P10_0_GATE.json`; frozen split, mechanism, source-hash and evaluation plans; small interpretable plots of sample roots, action order and factor scopes; optional checkpoint/metric manifest. STOP if anything shows leakage or inconsistent query identity.

---

## 4. Stage P10a: small, independently adjudicated physical constructibility pilot

**Start only with explicit bounded authorization in the launcher prompt.** Initial authorization covers **P10a only**. A pilot should produce quality-controlled ground-truth mechanisms, not claim statistical superiority.

### 4.1 Scene families and query bundles

- Seven mandatory pilot mechanisms, **two independent reference roots each** (14 roots total): H1 (+1 complementarity), H2 (redundancy/neutral), H3 (order swap), H4 (omission necessity), H5 (feasible original plus edits), H8 (constructor-disjoint), H7 (edit/repair discrepancy). H6 (destination/J), H9 (appearance) are attached where physically compatible; no extra root quota by default.
- Construct two waves of 7 roots (one independent root per mechanism per wave). Freeze each wave's root geometry, source/appearance/robot q0, task, 48 grasps, possible edits, query IDs, candidate catalogues, priority and run order **before teacher labels**. Predeclare seeds and a maximum per-root query count.
- Labels required: H1 four scene-outcome values with scoped negative certificate and witnessed double edit; H2 complete ±/0 four-outcome tuples; H3 reversed order same endpoints/q0 with one verified and other certified (operational shown separately); H4 full sequence plus omissions independently queried *from original state*; H5 initial feasible and harmful/neutral edits; H8 novel geometric obstruction; H7 hypothetical edit vs physical sequence mismatch.
- Treat proposed scene sketches as hypotheses only. Do not call an unverified constructor intent a causal outcome. Show graphical scene before/after and failed/successful witness/certificate frames; no fabricated trajectory.
- **Soundness-first:** do not add a place-side certificate simply to improve yield. An operational negative cannot substitute silently for a sound negative in a proof-grounded stratum. `UNKNOWN` and `NOT_RUN` stay missing. An infeasible outcome depends on scoped task/robot/grasp assumptions, not a universal fact.
- Every teacher call produces append-only `root_id`, `query_id`, caller stage `LABEL_ACQUISITION`, immutable input hash, status/provenance, witness/certificate if any, timeout/stop and CPU/wall; deduplicate identical *physical teacher requests* without counting a reused old label as a new observation.
- Query only necessary outcomes in outcome-blind priority order, stopping within budget. Adaptive choice of queries based on prior teacher results, if necessary for yield, must be explicitly labeled **adaptive-construction** and excluded from the blind evaluation; no hidden test-set selection by teacher success.

### 4.2 P10a quantitative budget (hard cap)

- **≤ 14 reference roots**, **≤ 16 physical queries per root**, **≤ 224 new teacher queries**, **≤ 5,000 total teacher CPU-seconds** incl. timeouts, failed attempts, retries and guard overhead. Per-query cap: **at most 120 teacher CPU-seconds and 360 wall-seconds**, or tighter limits from the pinned teacher policy. Enforce using the same process-tree guard; fail closed. Do not silently increase the teacher policy’s allowed effort. One physical teacher worker at a time.
- Stage CPU budgets separate: P10-0 learner ≤4,000 CPU-s; P10a teacher ≤5,000 CPU-s. Regression fixtures charged separately and clearly declared; no loophole to run a teacher process under a “test” name.
- **Wave-1 yield gate:** report decided complete contrast / attempted root per H (proof-grounded and operational separated). If <50% of attempted mechanisms have at least one complete contrast or sound negatives for H1/H3 are absent, STOP that unproductive mechanism, diagnose constructor/certificate limitations, do not silently scale. Other productive mechanisms may finish their predeclared second-wave root within the total cap.
- **No new 3D, simulator family, Slot Attention, hardware**, and no changing the frozen energy/likelihood architecture. Constructor additions must be minimal and parameterized, with tests/visualizations.

### 4.3 P10a test of saved-data model (exploratory only)

Before running the new physical teacher, **freeze predictions from every available A/B/C/SF checkpoint** on all 14 *unlabelled* candidate catalogues. If a model cannot score the catalogue, record `NOT_RUN` and its exact blocker; do not invent a prediction. Hash and store predictions. Once teacher evidence is available, score them offline **without tuning on P10a labels**. These are diagnosis/constructibility results, not an unbiased untouched test for subsequently trained models.

**P10a deliverables:** `responses-phases/0038_P10a_constructibility_and_label_provenance.md`, `responses-phases/P10a_NEXT_DECISION.md`, `runs/p10/P10A_GATE.json`, root/query/wave manifests, status/proof/witness ledger and per-mechanism decided-contrast matrix; visualizations before/after with 3R arm, swept motion *only when actual recorded witnesses exist*, and captioned certificate scopes. Store raw teacher outputs; hash and version everything. Report unconstructible and unknown examples as prominently as positives.

**STOP BOUNDARY:** P10b/P10c/P10d/P10e are **NOT AUTHORIZED** by the initial prompt, even if P10a passes. Do not collect a second dataset, train on P10a labels for a claimed blind result, launch 3D, or run new execution episodes. Produce a precise bounded next-phase recommendation based on observed contrast yield and CPU/query cost.

---

## 5. Subsequent stages — full scientific validation blueprint (NOT authorized yet)

These specifications prevent another methodological reset. Prepare code/plan structure in P10-0 if cheap; execute them only after a separate user-approved budget and gate.

### P10b — Ground-truth coverage and honest split construction

- Using empirical P10a mechanism yields, decide whether proof-grounded H1/H3/H4 are actually constructible under current 2D teacher. If not, report the blocker and narrow scientific claims rather than teaching the model operational labels then calling them causal proof.
- Desired pilot floor: **24 train + 24 validation + ≥14 blind roots = ≥62 independent reference roots** when feasible. The blind floor is at least two reference roots per each of seven key mechanism groups, but this is still **insufficient for strong statistical power**; separately plan sample size/power from observed pilot effect sizes, with minimum detectable effect and attrition estimates. Do not claim ≥62 alone proves superiority.
- Root lineage, near-duplicate geometry, nuisance appearance variants and order-swaps stay within one split. Explicitly separate root-disjoint, constructor-disjoint and appearance-disjoint holdouts; avoid adaptive optimization using the blind holdout. Any exploratory constructor searches on P10a roots are developmental, never blind.
- Blind-set scenario generator **must be frozen without using its teacher labels**; freeze predictions/rankings/calibration/seed/budget before exposing blind outcomes. A sealed teacher service can generate evaluation labels unseen to the learner, but no human/model redesign based on them until analysis unlock.
- Older proposal forecast `≤800` additional physical queries / `≤16,000` teacher CPU-s for P10b, **request only after P10a yield/cost analysis**. Do not promise it will be enough for the increased root count.

### P10c — Pre-registered matched training / factor ablations

- Train **A, B-keyed, C-keyed** on the *same root-disjoint training evidence* with 3 seeds and matched budgeted schedules, separately report model parameter counts and loss functions. Include SF independent predictor, uniform and geometry-only. Historical B-unique/PoE as secondary; don't multiply arms without an endpoint.
- Factor ablations prioritized by hypotheses: B/C (−F5 generic pair), B/C (−F5 higher-order), B/C (−F4 omission pair), B/C (−F3 `z0–zS` pair), B/C (−F2 order), F1 neural static vs analytic static screen, full DINOv2 vs visual-zero. Where frozen-factor knockout is only a sensitivity diagnostic, **retrain** the ablated arm for a controlled claim.
- For C vs B, preserve everything except the order architecture whenever code allows; explicitly disclose remaining differences; inspect order-swap pairs rather than unconditional NLL alone.
- B/C retain the exact three-term training objective. A/SF retain appropriate documented nonjoint objectives and identical shared physical label provenance; don't quietly advantage B with privileged training outcomes unavailable to A if the comparison claims architecture-only fairness. If not all labels can be used by A without changing the model, disclose this limitation and report a label-matched subset control.
- Proposed learner cap ≤6,000 CPU-s for the *future* phase, subject to feasibility after P10a; if insufficient, prioritize B/C/A/SF/H3/H4 and label uncovered ablations NOT_RUN.

### P10d — Truly blind prediction + execution

**PRIMARY: strict TOP1_COMMIT.** Given the untouched root, frozen model computes probabilities, hypothetical edits and ranking with **zero IK/planner/teacher calls**. Choose **exactly one** candidate (or abstain). Use the physical planner/IK only to produce/execute that selected repair. If precommit planning that selected repair fails, it is a failure; never try a second candidate. After selected relocation, attempt target once with SAFE_RETREAT. Count budget censoring and all failures in the denominator. This includes a choice that failed the analytic static screen as a failure/invalid proposal under predeclared policy; don't silently rerank via IK.

**Comparators:** A, keyed B, keyed C, SF, uniform, analytic geometry-only **TOP1** baseline (no IK in proposal). The **G+M** reference may use motion planning to score/find a feasible candidate and must be shown as a **planner-assisted, different-resource** baseline unless a fully matched precommit planner budget is imposed; report its calls and total CPU. This is crucial for interpreting any advantage. No opportunistic G+M downgrade.

**SECONDARY: P8d-compatible TOP5_PRECOMMIT.** Frozen ranking up to 5; run an equal-budget fixed-order relocation planner on candidates in sequence until a relocation witness or budget failure; COMMIT first witnessed one; no postcommit retries; one target+SAFE_RETREAT attempt. This is a **planner-assisted policy** even for learned arms. Report results separately from TOP1; do not use TOP5 to claim planner-free inference.

Measure, paired by blind root: GOAL_AND_SAFE_RETREAT success, abstentions, selected-order correctness, unnecessary moves, catalogue-bounded optimality/regret **only where verified best exists**, joint travel J, analytic Cd, model inference CPU, planner calls, planner CPU/wall, censoring, failed target after committed relocation, failure taxonomy and conditional success. Compare confidence intervals and discordant roots, not a single percentage alone.

**Blind label leakage guard:** if the candidate predictions, calibration or scene generator were adapted after any blind label was disclosed, mark the evaluation compromised and do not claim held-out generalization.

### P10e — Factor attribution, negative results, readiness memo

- Mechanism-centric test reports with full positive/negative/neutral and proof/witness examples; for each factor F1–F5, what it learns, which label data train it, what the ablation did, whether the measured difference generalizes to unseen roots.
- Results matrix for A, B, C, SF, G-only, G+M and ablated B/C; confidence interval and support size next to every headline; no cherry-picked best seed or arbitrary test-time selection.
- Evaluate causal contrast prediction, not inferred physical cause from a purely statistical factor graph: teacher interventions generate the causal supervision; learned energies capture predictive dependence conditional on this experimental design.
- **Professor-readiness gate:** independent decided mechanisms (or explicit unconstructible blockers), frozen physical-validity provenance, matched baseline fairness, untouched execution evaluation, reproducible seeds/checkpoint manifests, error taxonomy, honest negative findings, and every figure traceable to original scenes/results. If any central claim remains unverified, mark it OPEN and narrow the talk; never claim “perfect” or “proved causal” without evidence.
- Only after this stage should a technical professor-facing results deck be treated as externally ready. Negative/null experimental results are still valid to discuss transparently.

---

## 6. Cross-stage engineering quality, statistics and STOP rules

1. **Reproducibility:** immutable hashes of source, config, splits, data, policy, teacher and checkpoints. Prefix every artifact with stage. Use guard-enforced per-process budgets; count failed/retried jobs and fixture planner calls separately. No silent data edits or hidden reseeding.
2. **Minimal code:** prefer reusing existing teacher and model APIs; proposed new `p10_protocol.py`, `p10_collect.py`, `p10_eval.py`, and optionally `p10_viz.py`, with small functions. Avoid more subfolders. Target **≤300 logical lines per new Python file**; if a justified exception is needed, record it and refactor logically instead of creating a 900-line orchestrator.
3. **Program/data separation:** model may read observed geometry, DINOv2 features, q0, goal, proposed actions and hypothetical pose edits. It may **not** read teacher statuses, ground-truth successes, IK flags, swept collision traces or privileged future states at learned inference. Assert this with a fresh-process import/monkeypatch test.
4. **No invented labels/metrics:** especially don't convert a timed-out planner into a sound infeasibility result, fabricate certificates or infer omission success from a full-repair witness.
5. **Do not demand a false positive conclusion:** if proof-grounded κ+ cannot be constructed within budget, report failure of the constructor and scientist-facing limitation; perhaps scope the claim to operational evidence, but do not increase budget automatically.
6. **Uncertain statistics:** confidence intervals with small n are descriptive and correlated estimates; don't claim equivalence from an insignificant difference. Avoid comparing root NLL from differing label counts without per-event and mechanism-stratified results.
7. **Factor truthfulness:** F1 static and travel J are outside conditional outcome Boltzmann likelihood, so separate auxiliary gradients; A does not have B/C's explicit joint outcome graph. Report this consistently.
8. **Stop immediately:** failed mathematical identity, source hash mismatch, unexpected physical teacher call in learned inference, leakage, certificate unsoundness, missing required gate or exhausted compute budget. Write an explicit BLOCKED or PARTIAL report and exact next action.
9. **No 3D yet.** Preserve DINOv2/object-centric pathways for M4M-style future 3D transfer; do not introduce Slot Attention or change F1–F5 now.

---

## 7. Required outputs for the initial authorized handoff (P10-0 + P10a only)

Write in `responses-phases/`:

- `0037_P10_0_validation_readiness_and_training_protocol.md` — source audit, frozen architecture, A/B/C 400-update comparison if budget permits, pre-registration and unbiased metrics, CPU ledger.
- `0038_P10a_constructibility_and_label_provenance.md` — actual teacher outcomes, decided-contrast yield per mechanism and provenance, sound proof/witness status, selected scene renderings, open blockers and model predictions frozen before labeling where applicable.
- `P10a_NEXT_DECISION.md` — **GO / REVISE_CONSTRUCTORS / BLOCKED / STOP** for each physical mechanism; data/power and budget estimates for P10b; NOT a claim of completion of scientific validation.

Write under `runs/p10/`: plan JSON(s), gates (`P10_0_GATE.json`, `P10A_GATE.json`), immutable root/query manifests, saved labels with original statuses, cost ledger, checkpoint hashes and exact conditionally evaluated model predictions. Under `visualizations/p10/`, make legible plots and short actual-scene diagrams from recorded information only. `instruction-phase-md/` may contain this contract (stage only if explicitly requested). Keep source and result changes committed atomically; do not stage unrelated user files or touch archived P8/P9 checkpoint data.

**Report on completion:** exact pushed commit SHA, gates/checks, A/B/C comparable metrics, **counts of actually decided** κ/order/omission/feasible-original/edit-vs-repair contrasts and their physical provenance, allocated/spent CPU/queries, failure reasons, and an evidence-grounded authorization request for next stage.

**Final boundary:** Stop after P10a. P10b–P10e require a new explicit go-ahead, regardless of whether all engineering gates pass. The intent is to finish scientific validation over staged, auditable experiments—not to claim that the first 14 roots prove the method.
