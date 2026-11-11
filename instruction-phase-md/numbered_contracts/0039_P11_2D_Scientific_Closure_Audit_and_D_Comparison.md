# 0039 — P11: 2D Scientific Closure, Component Identification, Independent Stress Test & D Comparison

**Binding execution contract v1.0 — research integrity first; no new method architecture**  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Start reference:** `0a5aa4d1cbe2cdd161de4e2e1bc873cfc9daddcb` (P10e). Resolve and record actual `HEAD`, `origin/main`, ancestry, tracked/untracked changes, and active instructions *before* running anything.  
**Place this file at:** `instruction-phase-md/0039_P11_2D_Scientific_Closure_Audit_and_D_Comparison.md`  
**Scope:** 2D only. Existing A/B/C/SF and D models. No 3D, hardware, D movement/destination/recursion, new factor-graph design, pretrained vision replacement, broad hyperparameter search, or unrelated refactoring.

## 0. Why this phase exists

P10b–P10e generated a valid and valuable 2D research study: 180 newly generated roots (80 train / 35 validation / 65 sealed blind), matched three-seed full training, 69 completed training runs, strict top-one execution, 3-/4-move repair witnesses, and a separate D blocker model. The existing decision selects **keyed B** as the strongest *learned* tested approach. Its blind, seed-averaged strict TOP1 executed success is ~0.718, tied with C, versus A ~0.585, SF ~0.385, geometry TOP1 ~0.446; planner-assisted G+M ~0.831. Primary B-vs-SF TOP1 and B-vs-A H1 complementarity pass Holm correction; C-vs-B order and B-vs-SF omission do not. These are **existing results to verify, not expected results to force**.

P10e nevertheless leaves concrete scientific loose ends: the H9 recolouring variants may overwrite one another; F1 learned static-head contribution and J/travel-head selector contribution were never independently identified; short-trained (≤2 actions) **physical execution** on 3-/4-move scenes was not performed; the overall timing comparison is incomplete; most blind roots share constructor families with training; D's 3-/4-blocker GT is operational, its pair term has no measured benefit, and the A/B/C-to-D blocker comparison supports only a subset of roots.

**Objective:** Close these issues as rigorously as is physically possible; produce a complete, auditable professor-ready scientific case, including genuinely negative results and unsupported components. This is an **audit and narrowly targeted evidence phase**, not a green light to continuously modify models until a desired ranking appears.

### Non-negotiable integrity rules

1. Preserve all P8/P9/P10 artifacts, checkpoints, raw labels, snapshots, scene construction metadata, witness traces and evidence hashes **byte for byte**. P11 outputs must be new versioned artifacts; never silently regenerate or overwrite historical results.
2. Exactly preserve the model definitions: A local GRU, B keyed predecessor joint Boltzmann, C keyed GRU joint Boltzmann, SF factorized supervised; D conditional feasibility-plus-blocker Boltzmann with unary/pair options. Maintain the `ABC9K_KEYED_V1` physical-scope ontology and F1–F5 definitions. Existing fixed DINOv2 object features remain.
3. No IK/teacher/planner calls in learned predictions, scoring, intervention estimates, blocker prediction or any learned selection branch. Count inference-stage calls using instrumentation. The simulator/planner is allowed for **declared physical truth/one committed execution**, not for secretly screening learned alternatives.
4. **Existing P10b blind outcomes are now disclosed.** All new experiments on them are explicitly **POST-HOC / SECONDARY**. Do not rebrand them as an independently sealed confirmatory result. Freshly designed analyses can use them as retrospective diagnostics. For a genuinely new confirmatory claim, construct a **new sealed, independently locked test** following §5.
5. Every outcome retains `VERIFIED_FEASIBLE`, scope-specific `CERTIFIED_INFEASIBLE`, `BUDGET_INFEASIBLE`, `UNKNOWN`, `NOT_RUN` and any other existing provenance. A budget negative is not a physical impossibility proof. `UNKNOWN` and censored attempts never become class 0. No global minimality claims from finite catalogues.
6. D is **only** initial target-retrieval feasibility and identity of participating causal blockers under **specified hypothetical parking subsets**. No D destination scoring, generation, recursion, rearrangement, or execution. D does not compete with A/B/C on repair-execution success.
7. Stop at a declared gate if a scientific assumption, teacher certificate, experimental seal or source hash fails. Document failure with reproducible counterexample; do not quietly weaken the gate or make outcome-informed changes.
8. The PI/user's preference for B/C is **not** an experimental constraint. Do not remove negative evidence, tune on blind results, or select significance thresholds after examining outcomes.

## 1. Source audit and baseline reconstruction — P11-0 (first, read-only)

Read *in full* the source of truth and cross-reference actual artifacts:

- `responses-phases/0039_P10b0_source_audit_prereg_and_D_math.md` through `0044_P10e_model_component_proofs_and_scientific_verdict.md`, `P10_2D_SCIENTIFIC_DECISION.md`, `D_DESTINATION_AND_RECURSION_DEFERRED.md`, predecessor 0037/0038 and P9 freeze.
- `runs/p10b/p10b0/P10B_PREREG.json`, `PREREG_ADDENDUM_1.json`, `SPLIT_MANIFEST.json`, relevant P10b gates; `runs/p10c/P10C_GATE.json`, 69 run manifests and checkpoint hashes; `runs/p10d/predictions.json`, `BLIND_EVAL.json`, `P1_TOP1.json`, `P10D_GATE.json`, `INFERENCE_COST.json`, episode job mapping/ledgers/witnesses; final regression log.
- `abc7_models.py`, `abc7_train.py`, `abc8.py`, `unique_factor.py`, `unique_factor_keyed.py`, `joint_likelihood.py`, `p9_l3.py`, `p9_l3c.py`, `p10b_dataset.py`, `p10b_prereg.py`, `p10b_scenes.py`, `p10c_train_eval.py`, `p10d_execute.py`, `p10e_report.py`, `d_blockers.py`, `p8_select.py`, `p7_oneshot.py`, `ordered.py`, teacher certificates, geometry and simulator fixtures.

Produce an **evidence-to-source audit matrix**: for *each major reported number and claim*, identify source code line/function, artifact path and SHA (where available), exact unit of analysis, sample count, label provenance, whether it was preregistered, physical/planner-call policy, and whether results can be independently recomputed. At minimum audit:

- 65 blind independent roots; 80/35/65 and history/P10a separation; root geometry/lineage overlap; family/version overlap and the post-development H3 constructor change.
- `255 distinct episodes` vs `975 arm × training-seed selections` and the episode-key deduplication: **these are not 975 independent trials**. Check mapping of every arm/seed choice to the correct deterministic episode, outcomes, abstentions and failure categories.
- Holm P1–P4 raw and adjusted p-values, paired root-based CIs, seed aggregation and contrast signs. For other ablations identify multiplicity handling; don't call exploratory p-values primary.
- P10a/P10b distinctions: proof-grounded κ and order vs OPNEG-v1 budget results; place-stage certificate `FIRST_MOVER` is *assignment/grasp-family scoped*, not a universal placement impossibility proof.
- Training reports' physical CPU ledger error, 404/404 tests and 6/6 replays, actual graph/inference scope cap and time measurement unit.
- Read-only recomputation of all possible metrics without re-running physical teacher. **If source artifacts or GitHub fetches are incomplete, mark INACCESSIBLE, do not fabricate verification.**

**Output:** `responses-phases/0045_P11_0_full_source_result_and_integrity_audit.md`, `runs/p11/P11_0_GATE.json`. **Gate:** block downstream quantitative claims if discrepancies have not been explained. Existing results remain untouched.

## 2. Fix H9 correctly — P11-1

**Concrete suspected bug, verify first:** `p10c_train_eval.build_records()` creates two palette variants for each validation/blind root but `_recolor()` preserves original `audit.root`. `p10d_execute.freeze()` stores each H9 result as `per[split][r['key']]`, so its second palette appears to overwrite its first. If code/data prove otherwise, document and do not invent a fix.

Implement the minimum **versioned evaluation-only** correction. Do not modify the sealed P10d prediction snapshot, train/validation/blind original records, nor retrain the model. Distinguish variants with a stable compound key `(base_root, palette)` or separate variant field; preserve physical-root grouping, original query IDs and exact geometry; never count two palette views as two independent roots. Change only what is required to run and store **both** P1 and P2 palette predictions for every eligible full-model checkpoint.

Required safeguards and tests:

- Each original scene has exactly two persisted, unique appearance variants; verify 2 × expected number of roots, no overwritten keys; original geometry, robot pose, goal, objects and teacher/label identities bit-identical to source; only appearance-derived feature tensors differ.
- Source-image construction/segmentation mask check: recolouring preserves instance mask and does not inject labels, detections or teacher certificates. If pixels/embeddings unexpectedly unchanged for two intended distinct palettes, FAIL not fake difference.
- Compare original vs each palette **per root**, including absolute `Δp`, threshold crossings, TOP1 changes, κ/order changes where defined, and meaningful subgroup variation; provide full and per-palette root bootstrap CI. Compare A/B/C/SF and B visual-zero; visual-zero expected zero input-driven difference, up to declared numeric tolerance.
- Report **before/after** H9 summary and which original P10e claims are affected. Do not modify primary P1/P2 numerical values or claim that H9 was blind re-confirmation.

**Output:** `responses-phases/0046_P11_1_H9_variant_preservation_and_appearance_robustness.md`, `runs/p11/h9/P11_H9_GATE.json`, corrected H9 PNG(s), test for collision-free variant key and invariance. **Gate:** both palettes correctly preserved, source lineage auditable, no changes to historical artifacts.

## 3. Finish component identification without redesign — P11-2

### 3.1 F1: learned static head versus analytic veto

Do not confuse three things: (a) **analytic hard veto**, (b) learned F1 static unary/pair prediction head and its BCE auxiliary loss, and (c) the learned main repair probability. F1 is **not a named stochastic outcome factor inside the conditional joint probability**. The deployed selector may rely on the analytic veto regardless of learned F1.

First trace all F1 loss/gradient and deployment dependencies. Then run a matched, three-seed B control **with F1 static supervision enabled vs zero-weighted** while retaining the same architecture, all other losses, frozen features, data, root sampler, 400-update schedule, seed and calibration protocol. The existing B checkpoints supply the enabled condition *only if* their training configuration is demonstrably identical; otherwise retrain both. Do not delete layers or alter parameter count for this control. Avoid test-selection-driven changes; use existing validation only for checkpoint selection/calibration. Distinguish:

- F1 unary/pair **static prediction** accuracy, AUROC, BCE/Brier/ECE on held-out independently computed static labels.
- Whether removing F1 auxiliary gradients changes learned repair feasibility, H1/H3 performance, root NLL and strict TOP1 selections.
- Behavior *with analytic veto held fixed* for main controlled comparison; optionally evaluate learned-veto-only as a **clearly labelled unsafe diagnostic**, never call it equivalent protection or a new primary result.
- If the static dataset lacks independent negative/positive diversity or direct F1 evaluation data, mark **NOT_IDENTIFIED** with class counts instead of making an unverifiable claim.

### 3.2 J/travel-cost head

Trace exactly where witnessed `J` is supervised, whether candidate J values enter ranking and what constitutes the witness travel cost. Compare on **identical frozen B/C** checkpoints and candidate pools:

- default `predicted J` tie-break (same admission probability and move count);
- **disable J tie-break** using fixed analytic displacement (`C_d`) and deterministic ID thereafter;
- shuffled/random J as a negative control (fixed seeds); optional direct predicted-J vs witnessed-J regression error on independently witnessed moves;
- optional separately trained no-J auxiliary-loss control **only if justified** by a clear parameter-identification question and remaining budget; mark `NOT_RUN` otherwise.

Do not use the teacher's true J to rank candidates at deployment. An oracle-J ranking may be **labelled offline upper bound only**. Report how often the selector actually reaches the J tie-break (multiple candidates admitted with the same move count), the fraction of changed TOP1 choices, their label provenance, success and travel differences. If it almost never breaks a tie, say **not practically identified**, irrespective of low regression error. Avoid charging historical shared episodes twice as independent executions.

### 3.3 Re-evaluate F2–F5 and visual controls conservatively

Recompute the existing 3-seed B-F2/F3/F4/F5s/F5q/V0/U vs keyed B results on the same held-out roots. Verify each ablation *actually* disables its intended factor family (and leaves other families, factor ontology and exact inference intact), preserves comparable data, and was retrained rather than merely zeroed after training (visual-zero is same-architecture input-zero control). Record parameter-count changes and any unfair capacity confound explicitly.

Report effect size, root CI, significant/non-significant with properly qualified multiplicity, and interaction caveats. F2 order essential on studied cases; F3/F5 helpful for complementarity; F4 unproven; C not observed to help. **Never upgrade these provisional interpretations into universal necessity or model equivalence.** A family ablation can impact multiple factors through shared encoders.

**Outputs:** `responses-phases/0047_P11_2_F1_J_factor_ablation_and_selector_audit.md`, `runs/p11/components/P11_COMPONENTS_GATE.json`, compact component scorecard. Default checkpoint remains pinned; any new ablation checkpoint has a distinct name and hash. **Gate:** all comparisons explicit about what they identify, what they do not identify, and any missing class/outcome support.

## 4. Short-trained physical length extrapolation — P11-3

P10d reported *prediction-level* extrapolation from models trained with `len(seq) <= 2`, but its 3-/4-move **executions** used models trained with long examples. Evaluate this exact distinction. Use the existing **short-trained** A/B/C/SF checkpoints (3 seeds each), frozen before the original P10d unsealing.

- Freeze a new **supplementary analysis manifest** that records checkpoint hashes, old P10d root/choice roster, unchanged catalogue (up to 4 relocations), calibration computed from the original short-regime validation set only, analytic static veto, selection sorting, physical episode seed namespace and cost accounting. Under no circumstances tune selection based on outcomes already viewed.
- If old P10d snapshot already includes short-trained TOP1 choices, prefer these *unchanged* choices and reuse already recorded physical episodes **only for the same (root, repair, episode seed, protocol version)**; validate hash equality. For previously unexecuted distinct choices, execute one TOP1 simulator attempt per root/seed choice, no fallback, with SAFE_RETREAT and complete ledger; separately report cache reuse vs new executions.
- Do **not** judge longer repair necessity from a witness alone; split H10_3 (three witness moves) vs H10_4 (four witness moves) and `SOUND` vs `OPERATIONAL` catalogue-relative minimality.
- Report per-root and per-seed strict TOP1 executed success, abstentions, failure classes, repairs selected, 3-/4-move result, confidence intervals, inference time and complete episode cost. Compare short-B/C/A/SF to their full-trained versions. Distinguish `trained<=2, tested 3/4` from `trained 1–4, tested 3/4` clearly in plots and text.
- All results on the original 65 formerly blind roots are **POST-HOC**, even if their predictions happened to be frozen before labels opened. Mark these as supplementary, not a new confirmatory primary.

**Output:** `responses-phases/0048_P11_3_short_trained_long_execution.md`, `runs/p11/length/P11_LENGTH_GATE.json`, ≥1 successful and ≥1 failure recorded 3-/4-move illustration if actually available (no fabricated motion). **Gate:** original model choices not affected by outcomes and every claimed executed event traces to an actual episode.

## 5. Optional but strongly recommended independent constructor-family stress test — P11-4

**Purpose:** Existing P10b train/val/blind roots share generator templates. A new *constructor-disjoint* test is needed to claim more than held-out seeds of known mechanisms. It must be a **new locked diagnostic** of unchanged trained models, not another round of favorable scene construction. This stage is authorized only within caps below and **only after P11-0/1 integrity gates pass**.

### 5.1 Dev-only construction, before sealing

Propose at least **two genuinely new geometric scene-construction programs or compositional layouts**, not trivial seed changes in existing H1/H10 templates, while preserving the 2D simulator physics and four-move cap. Possible candidate stressors (choose only physically constructible ones): independently varied fixed-body positions, alternative q0 sectors, visually identical but geometrically changed transport clearance, occlusion at a different manipulator-link sweep, non-canonical blocker chains, competing valid parking choices. Document how each differs from training families and why the distinction is substantive.

Use a bounded **development-only** pilot to verify that the constructors can actually yield mixed positive/negative outcomes and witnessed ≥3/4-move problems if claimed. No outcome-dependent changes after freezing the new evaluation roster; failed construction families remain reported as failed, not hidden. Do not leak teacher outcomes or certificates into neural inputs or candidate selection.

### 5.2 Freeze a new confirmatory test

- Target **up to 40 new independent roots** in two predeclared batches of ~20; preregister family allocation, meaningful 1–2 versus 3/4 strata, difficulty, candidate catalogue, teacher protocol, shared training checkpoints, calibration, all primary/endpoints, analysis script and power limits. **Do not force 40 if constructibility/CPU/soundness fails.** Avoid using the previous H1/H10 templates under renamed families.
- Create two separate commits: **(i) frozen new scene plan + the existing model predictions/top-one choices pushed before new teacher labels or static admission; (ii) labelled outcomes and evaluation after collection**, with SHA256 and immutable manifests. Blind labels encrypted/sealed or stored under access-enforced sealed directories; ensure training/selection code cannot load them before unseal. If unsealing integrity cannot be guaranteed, mark results exploratory.
- Primary *new* endpoint should be **B strict TOP1 executed success vs A and SF** under the same one-choice no-fallback policy; specify multiplicity and sample-size caveats before labels. Secondary: B/C order, κ, H7 alternative destination, 3-/4-move performance, calibration and D feasibility/blockers only where protocol-equivalent GT is obtained.
- Do **not retrain/recalibrate on this test**. Any model repair or new threshold developed from new outcomes invalidates the new test's confirmatory status. No fresh train/test swap. If there are too few independently decided roots, explicitly conclude UNDERPOWERED rather than positive.
- Preserve robot q0, certificate validity and safety boundaries. Physical simulator executor is allowed only for the committed choice. No use of planner to screen alternatives for A/B/C/SF. Keep G+M separate and charge all precommit planning.

If the new constructor families cannot yield hard but sound cases within budget, stop with a documented external-validity limitation. That is preferable to a highly selected favorable new holdout.

**Output:** `responses-phases/0049_P11_4_constructor_disjoint_physical_stress_test.md`, `runs/p11/new_holdout/` plans, source hashes, frozen predictions, teacher ledger, analysis gate and witness visualizations. **Gate:** test seal, mechanism provenance, no label leakage and full independent-root uncertainty audited.

## 6. Infeasibility and blocker identification versus D — mandatory direct comparison (P11-5)

This is **a separate endpoint** from repair execution. It must appear in the report **and verbatim as a clearly labelled final section of Claude's chat reply**, not merely as a file link.

### 6.1 Initial target retrieval feasibility — all models on identical GT roots

Compare D (pairwise), **D-pairless**, A, keyed B, keyed C and SF on the **identical roots** for which `z0` (empty repair = target retrieval with SAFE_RETREAT, fixed robot q0) has a decided label. The original P10d report says D: **64/64** correct, `NLL≈0.005`; verify from `runs/p10d/BLIND_EVAL.json`, not from memory.

Report for every arm: denominator, #positive/#negative decided roots, predicted-feasible threshold, TP/TN/FP/FN, balanced accuracy, accuracy, feasible recall, infeasible recall, AUROC (only if both classes occur), binary NLL, Brier/ECE (with bins and support). Report the **same 64-root cohort** or the actual strict intersection if coverage differs; show any `UNSUPPORTED`, `UNKNOWN` and `NOT_RUN` exclusions with counts. Use seed mean *per root* and also expose seed variability; don't pool 3 seeds as 3× independent scenes. D's perfect initial feasibility does not imply perfect blocker attribution, and majority-class prevalence matters.

### 6.2 Blocker attribution — direct D vs D-pairless vs geometry, plus A/B/C where faithful

Blocker GT is **not an unqualified set of 'all objects physically responsible'**. It is the union of members of *all inclusion-minimal sufficient hypothetical clearing sets under a specific frozen parking map* among a declared movable pool. Separately show the intersection (`necessary`), alternative minimal sets, and unknown / non-monotone cases. If the baseline D code supplies union labels but does not learn intersection, do not claim necessity-head performance.

Use the original 65-root sealed P10d benchmark for the retrospective comparison, then the new holdout if one exists and valid matching D-subset labels can be obtained. Original reference counts to verify: 60 complete masks, of which 39 proof-grounded, 21 others operational; categories with 0/1/2/3/4 union blockers. Three-/four-blocker labels are **operational only**, so report them separately and do not call them certified causal ground truth.

For **D, D-pairless, geometry heuristic**, report per-root macro object precision, recall, F1, exact-union-mask match, Jaccard, cardinality error, false-positive rate on irrelevant objects; class prevalence and 95% root-bootstrap CIs. If F1 is computed as macro per-root and some paper-style 'micro F1' differs, give both with definitions. Include number and nature of all excluded cases; handle empty GT/pred masks explicitly.

For **A/B/C/SF**, their model architecture does **not** directly produce arbitrary D blocker masks. Only derive blocker masks via **exactly matching** counterfactual `z0, zS[A], zS[B], zS[A+B]` queries where the movable pool and D parking destinations match physically. Source indicates approximately **33 / 60** complete masks are supported; 27 unsupported. This equivalence must be verified by object IDs, source/destination, robot q0, GT teacher/query hash and intervention semantics. Never impute unsupported predictions, treat `UNKNOWN` as negative, or compare 60-root D scores to 33-root B scores and declare superiority.

Provide **two distinct fair tables**: (i) D/D-pairless/geometry on **all complete roots**, separated proof/operational; (ii) D/D-pairless/geometry **and** faithful A/B/C/SF derived attributions on the **same supported intersection**, with counts and CIs. If the new holdout includes >2 blocker pools, do not force A/B/C blocker attribution from an insufficient edit catalogue; record UNSUPPORTED.

### 6.3 D pairwise identification

Reconfirm the pair-term ablation. Existing P10d: D blocker F1 ~0.872, D-pairless ~0.882, geometry ~0.797; exact mask 0.578 / 0.667 / 0.533. An interval spanning zero **does not prove equivalence**. Report exact paired differences, CI, proof-only performance, 3–4 blocker operational subset and model complexity. Conclude **NOT BENEFICIAL / NOT IDENTIFIED** unless genuinely new evidence changes it under a prespecified analysis. D's exact enumeration cap is six movable objects; the physical benchmark D pools are ≤4. Do not claim unlimited scaling.

### 6.4 End-of-chat output contract (mandatory)

**Claude must finish its final response with the following content, in actual numeric form (not a link):**

```
ADDITIONAL RESULT — D VERSUS A/B/C: INITIAL INFEASIBILITY AND BLOCKERS

1) Same-root initial target feasibility (retrieval from q0):
   cohort N=..., feasible GT N=..., infeasible GT N=..., provenance=...
   D: accuracy ... TP/TN/FP/FN ... balanced accuracy ... AUROC ... NLL ...
   D-pairless: ...
   A: ...  B-keyed: ...  C-keyed: ...  SF: ...
   winner/uncertainty: ...  important class-prevalence caveat: ...

2) Blocker identity against GT (union-minimal-set semantics, frozen parking map):
   all-complete N=...; proof-grounded N=...; operational N=...;
   D: precision ... recall ... F1 ... exact-set ... CI ...
   D-pairless: ...  geometry heuristic: ...
   paired D − D-pairless and D − heuristic with CIs: ...

3) Faithfully matched A/B/C/SF counterfactual attribution:
   matched N=...; unsupported N=...; proof-only matched N=...;
   D: F1 ...; D-pairless ...; geometry ...;
   A ...; B ...; C ...; SF ... (all from SAME matched roots)
   unsupported cases are not assigned scores.

4) Long-blocker categories and limitations:
   n=1/2/3/4 blockers: supports, F1 by model, provenance;
   pairwise term supported? ...; D movement/destinations/recursion: NOT IMPLEMENTED.
```

This section must be the **last substantive section** of the reply even if the user primarily asked about A/B/C. Print the numbers straight from the regenerated result artifacts. Explicitly state missing values as `NOT_EVALUABLE`, never invent measurements or use values with incomparable root cohorts. Provide report paths and the final Git commit SHA *before* this section.

**Output:** `responses-phases/0050_P11_5_D_vs_ABC_initial_infeasibility_and_blocker_accuracy.md`, `runs/p11/d_compare/D_VS_ABC.json`, one clean comparison figure (matched-cohort and provenance-labelled).

## 7. Full-pipeline and proof-strength audit — P11-6

Recompute end-to-end resource accounting for all methods from the existing traces where possible:

- Feature extraction (including DINOv2/mask pooling if not cached), network inference, exact Boltzmann normalization, analytic static veto, candidate ranking, precommit planning/pose-screen checks, selected plan/attempt, target/SAFE_RETREAT, abstentions and failures. Separate **CPU-seconds**, **wall-seconds**, **planner calls** and **number of candidates physically screened**; don't conflate average time conditioned on executed episodes with total per-root time including abstentions.
- G+M can plan/screen up to five candidates, while learned TOP1 physically checks one. But historical G+M mean episode CPU was **lower** (~15.7 s) than B's (~20.0 s), so do not claim lower total cost for B without a truly comparable measurement.
- Verify result reproducibility with fresh regression (expect prior baseline 404/404 + 6/6; any change must be explained), equality of old checkpoint hashes, deterministic replay of sampled end-to-end executions, all original and new gates, test coverage for fixes, and source integrity.
- If source-level issues beyond H9 materially affect headline primary results, stop and classify their severity. New held-out evidence becomes necessary if P10's integrity is compromised. Do not repair a compromised blind benchmark by modifying labels after observing outcomes.

Build a **component evidence ledger** with exact component, implementation, math, training signal, tests, performance control, CI, coverage, and scientific status: `SUPPORTED`, `NOT_BENEFICIAL`, `NOT_IDENTIFIED`, `UNDERPOWERED`, `FAILED`, `DIAGNOSTIC_ONLY`. Must include A GRU, B keyed joint, C GRU-vs-predecessor, F1–F5 (F5 generic vs HO), DINOv2 visual, static veto, J, D feasibility, D unary/pair and exact blocker inference.

Produce a professor-facing summary **without exaggeration**:

- Proven on this specific 2D benchmark: keyed B beating A/SF/geometry under strict TOP1, complementary intervention prediction advantage; tested 3-/4-move physical executions; joint-factor ablation effects in the tested families.
- Unproven or bounded: global minimum move count, all factors necessary, C equivalent to B, unrestricted longer-length scalability, D's pairwise utility, hardware/3D transfer, fully general causal-mechanism transfer, planner-assisted computational superiority.
- Existing blind set vs new truly locked independent holdout, post-hoc diagnostics vs predeclared primaries, and proof-grounded vs operational labels.
- If one of the original results fails verification, state the corrected result; do not maintain the winner by assumption.

**Deliver:** `responses-phases/0051_P11_6_professor_ready_2D_scientific_closure.md`, `responses-phases/P11_2D_FINAL_SCIENTIFIC_DECISION.md`, `runs/p11/P11_FINAL_MANIFEST.json`, concise results visualizations and clear PASS / PARTIAL / BLOCKED statuses. The decision may legitimately be `PARTIAL` even if every engineering test passes. Do not claim every component helps if its ablation is null.

## 8. Sequential workflow, authorizations, budgets and stop rules

Proceed **in this order**: P11-0 → P11-1 → P11-2 → P11-3 → P11-4 (if constructible under budget) → P11-5 → P11-6. Deliver each stage's committed artifacts and ledger. If a critical gate fails, stop and report exact repro; do **not** substitute a bland progress summary. If optional P11-4 is genuinely infeasible, continue with P11-5/6 honestly marking external generalization as open.

The following are **new aggregate upper limits for P11** and do not retroactively alter P10 ledger caps; compute usage includes failed attempts, retries, pilots and overhead. These are authorizations to run the narrowly described work, **not requirements to spend**:

| P11 category | New aggregate CPU-s cap | Additional constraint |
|---|---:|---|
| Audit + nonphysical evaluation + H9 + figures | 4,000 | Reuse saved outputs where possible; report CPU and wall |
| F1 matched three-seed control training | 6,000 | No broad tuning; only matched ablation, stop if cap reached |
| Existing-root short-trained physical TOP1 supplementary episodes | 5,000 | Deduplicate identical root/repair/seed; one committed choice |
| New constructor development (P11-4) | 1,200 | Development-only, no cherry-picked test outcomes |
| New holdout teacher/certificates (P11-4) | 8,000 | <=40 roots, per-query/seed guards fixed before collection |
| New holdout executed TOP1 (P11-4) | 5,000 | Stop/partial if budget exhausted, no fallback |
| Final regression | 1,700 | Fixture planner calls counted separately, never inference |

No excessive parallel worker ledger double-counting; one physical teacher worker unless proven independent and reliably accounted; protect each subprocess with CPU+wall guards, preserve its partial output and detailed stop reason. No external paid compute/API calls. Before each new stage, check remaining aggregate budget and **estimate** the planned jobs; skip/mark NOT_RUN before exceeding caps rather than attempting uncapped work. At most minimal new `.py` files; favor small versioned fixes to existing modules and targeted tests; target ≤300 logical lines per newly created file. No hidden background jobs; if a tool session ends, record what was actually completed without pretending an async run continues.

**Fresh holdout safeguard:** new physical labels/scene certificates must not be used for classifier retraining, architecture changes, threshold selection or recoding candidates after the frozen prediction commit. If a bug forces any of these changes, invalidate the fresh test and document it. No absolute guarantee of 'perfect science'—state remaining statistical limitations and uncertainty.

## 9. Required visual and report coverage

Use existing `visualizations/p10b/` as immutable provenance-linked references; create new material under `visualizations/p11/`. Must provide legible non-decorative scenes with actual robot, collision bodies and confirmed GT statuses where available:

1. Corrected paired-palette H9: same geometry / differing appearance; both palettes visible side by side, annotated probability shifts.
2. F1 and J: decision flow, component enabled/disabled, observed selections and failure modes.
3. Short-trained vs full-trained 3-/4-repair physical witness sequences (only real traces).
4. New construction mechanisms and full attempt/yield atlas if P11-4 is run, including failed constructors and non-witnessed negatives as static status panels.
5. D attribution: original scene and visually marked GT union-minimal-set members; correct/incorrect blocker IDs, false positives/negatives; no use of a successful *hypothetical edit* as a fabricated executable repair.
6. One graph showing A/B/C/SF TOP1 outcomes, with G+M protocol visibly differentiated. Include uncertainty and independent-root counts.

Output readable artifacts without screenshotting error messages or inventing trajectories. Each figure traces to root/query, checkpoint, code/hash and teacher provenance.

## 10. Final direct decisions

End `P11_2D_FINAL_SCIENTIFIC_DECISION.md` with explicit answers:

1. Do the original P10 B > A/SF strict TOP1 and complementarity results survive code-level reconstruction? Which values and adjusted p-values?
2. What does the *correctly evaluated* H9 two-palette experiment show; did the overwrite exist?
3. Does F1 add independent static/repair value? Does J meaningfully change decisions, and is its cost prediction useful?
4. Which of F2, F3, F4, F5-generic, F5-HO, DINOv2 genuinely improve held-out outcomes? Which do not, and why can't a null effect be called proof of redundancy everywhere?
5. Do short-trained models physically execute three-/four-move repairs, not just score them? Was minimality sound or operational?
6. Does a completely new 2D constructor family support generalization, or remain inconclusive/failed?
7. Which approach is best for **repair execution**, and which is best for **initial infeasibility** and **blocker identification** on matched GT cohorts? These are separate tasks and rankings.
8. What exact limitations remain for journal/conference/professor claims? Include the 2D simulator-only boundary and G+M advantage.

**Final-chat compliance:** Summarize completed stages and corrected B results, link reports/commit, and **print** the full §6.4 D-vs-A/B/C numeric comparison as the **last section**, even when D shows no advantage or pairless wins. This instruction is non-optional. Stop when the contract's gates and bounded supplementary evidence are complete; do not start D recursion, destination learning, 3D, or speculative additional modeling.
