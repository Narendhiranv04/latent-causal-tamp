# P6 — Expanded 2D four-move dataset, A/B/C stress tests, ablations, and evidence-backed GIFs

**Status:** Proposed *execution authorization contract*, for Claude Opus 5.5 High. Not executed by this document.  
**Basis:** Methodology v1.7, Implementation Guide v1.9, the separate `2D-ABC-OPNEG-v1` teacher-policy addendum, and report `0020_P5_D3_lite_and_G4E_ABC_poc.md` (P5 commit `15e1285`).  
**Stage boundary:** New P6 only: bounded source additions / versioned learner layouts, expanded **2D** collection, targeted retraining and ablations, an optional pre-budgeted one-shot **2D simulator** evaluation and required GIFs. **No** full G5/G6 statistical verdict, 3D, physical hardware, or 300-root release.

> **Priority:** Stop engineering around trivial GOAL_OVERLAP labels. Produce diverse, real, independently evaluated cases involving **0–4 distinct obstacle relocations** and different starting robot/object states. Then determine whether A, B and C learn ordering, higher-order dependencies, causal effects, and executable repair selection on held-out independent roots. Preserve reproducibility and all earlier observations. We expect partial outcomes when computation is limited; never silently fill them in.

---

## 0. How to use this contract

1. Read the entire document before acting; read Methodology v1.7, Guide v1.9, report 0020, the P4 policy/report and the actual repository modules (`zlayout.py`, `sampler.py`, `abc_models.py`, `abc_train.py`, `abc_run.py`, `learn_data.py`, `d3lite*`, `operational_teacher.py`, `teacher_pilot.py`, `sector_cert.py`, `sector_check.py`, `g4d_run.py`, `ordered.py`, `skill.py`, `verify.py`, `run.py`). **Inspect first:** names in this contract are requirements, not claims that source already supports them.
2. Verify HEAD = `origin/main` = `15e1285` or document the exact additional commits if different. Check staged/unstaged content, original hashes, all frozen source/data/report manifests. Pre-existing tracked root-PDF deletions and the user's untracked instruction files are **not** permission to delete/commit them.
3. Keep a **small number of readable modules** (ideally < 180 logical lines per new module). Reuse and minimally extend existing code. Prefer a new versioned adapter/module to modifications of frozen history. Do not redesign A/B/C, the physics engine or teacher protocol.
4. Work in gated order: mathematical/implementation foundation → static scene generation preview → four-root batch 1 → quality gate → additional batches → train/ablate → model-choice verifier (if budget remains) → GIFs/report. **Do not call the entire stage a PASS if collection or model gates fail.**
5. Every command that could invoke a robot planner, teacher worker, costly feature extractor, training run, or animation renderer must have an enforced process-tree CPU and wall limit, with an append-only call/CPU ledger and durable checkpoints. Never use a parent-only `ulimit` to claim aggregate child-process enforcement.

## 1. Frozen conceptual/scientific invariants

- Full fixed-base articulated 2D **3R** arm with actual finite-width links/housings, base, palm/fingers, carried discs, joint/gripper continuity, limits, collision checks, the recorded 48-grasp skill and checked `SAFE_RETREAT`. Grid cells denote **terminal resting poses only**; transport is continuous.
- Each proposal `r=((i_1,k_1),..., (i_m,k_m))` has `0 <= m <= 4`, **distinct relocated object IDs** (move once), no stay/no-op/active-target relocation, legal supported destination, and an immutable **specified action order**. A 4-move proposal is not four independent teleportations; it is four executed pick/carry/place/release/retreat operations, followed by the target action from the genuinely achieved state.
- No reset to HOME/q0 *between* corrective moves, and no made-up successful trajectory after a failure. Different **initial** `q0` choices are allowed as **separately defined scene starts**, verified collision-free and included in the scene hash. A paired second `q0` on an otherwise identical scene is a **correlated sibling**, not another independent root; keep family/split linkage together.
- All learner inputs start from the initial scene: frozen mask-pooled DINOv2 features, allowed primitive geometry, object poses, target/goal, robot q/limits/FK, gripper/attachment, legal placements, and candidate ordered actions/ideal prefixes. No future actual trajectories, initial-target swept path, collision-oracle outcomes, planner seeds/states, privileged labels, or root/family identifiers as model inputs.
- Preserve **A**: learned unary U, symmetric pair V, GRU order task/logit, separate learned first-witness J; local/task/effect/cost and finite-pool ranking losses. Preserve **B**: five conceptual potentials (static, prefix-order sequence, scene, omission, coupling) and genuine jointly optimized finite `(r,z)` Boltzmann likelihood. Preserve **C**: B's explicit typed outcome joint energy plus A's GRU for order, **without** double counting B's prefix order. Do not silently replace the five-factor scientific specification with ordinary independent outcome classifiers.
- The `2D-ABC-OPNEG-v1` teacher policy stays **unchanged**: a complete witnessed success is positive, checker-accepted infeasibility proof is certified negative, three clean completed declared planner seeds without a witness give **`BUDGET_INFEASIBLE`**, incomplete/guard-censored evaluations remain `UNKNOWN`. Operational negatives mean *not solved under that protocol*, **not physically proven impossible**. P4/P5/older labels stay immutable and retain their policy provenance.
- External verified feasibility and analytic static invalidity are not neural factor energies; keep the score and label namespaces distinct. Final selection remains **feasibility threshold → fewest moved objects → predicted J → analytic endpoint displacement → learned feasibility energy → deterministic tie-break**, followed by the prescribed independent motion verifier. Boltzmann energies can guide proposals but never certify feasibility.
- Root-level train/val/test separation is mandatory **before** descendants. No validation/holdout results for construction tuning or choosing architecture mid-collection. Provenance and every attempted or rejected root must remain in the audit.

## 2. Changes required BEFORE any new robot collection

### 2.1 Extend move cap everywhere, *without changing archived P5 layouts*

Build a new versioned `R4`-compatible sequence/layout/schema **view**; do not mutate `Z_LAYOUT_V2`, archived `dataset.pt`, G4C or D3 P5 plans. Audit and update (in versioned code): sequence parsing, canonicalization, move-once constraints, legality, variable-length action/prefix tensors, GRU unroll length, B prefix/pair terms, cost target/masks, omission semantics, sampler proposal/reverse proposal, stratification, visualizer, dataset exports, and regression tests. Check 0, 1, 2, 3 **and 4** moves, not only four moves. Preserve 0–2 parity against P5 on identical examples.

For length four, explicitly exercise: `r=(A→a,B→b,C→c,D→d)`; all four leave-one-out omission sequences; same-endpoint 4-action reorderings; an alternative destination; an invalid static destination as a distinct labelled control. Count only actually attempted/tested sequence variants, not all `4!` permutations as observed labels.

### 2.2 Extend B/C active outcome fields to K = 9; exact sum still mandatory

The existing tested `Z_LAYOUT_V2` restricts to `K <= 8`. For the new designated four-move complete-pool candidate define **exactly**:

`z = (z0, zS[A], zS[B], zS[A+B], zR, zO[0], zO[1], zO[2], zO[3])` → **9 distinct active binary variables**, `2^9 = 512` hypotheses for that candidate. Here `zO[t]` means **delete the real action at position t** while preserving relative order and restarting the entire omission query from the original S0. Never construct a no-op omission that duplicates the repair. The three named scene edits are fixed-robot target-only interventions; include a nuisance scene edit for supervision, but **exclude nuisance from this specific joint-z layout** (predeclared, not decided post hoc). Other lengths activate only applicable outcome variables. Version the schema, active masks, query-to-slot mapping and hash.

Retain EXACT logsumexp enumeration for every candidate with `K <= 9` (at most 512 states/candidate), and cap both pool candidate counts and full pool total states by a written predeclared memory/time guard. Do not silently truncate z configurations or silently discard unknown slots. Fully decided joint-pool loss is defined only where **all** required active outcome queries for those repairs are independently decided under a compatible label policy. Separate single-field loss masks may still train on partial pools.

**Fix/test the true variable-cardinality entropy issue.** If raw energies are all equal and repairs have different active K, summing `2^K` z states gives an arbitrary preference for the candidate with more diagnostic questions. Use a documented **uniform-reference-measure correction** for comparisons across variable K, e.g. `E_joint_corrected(r,z) = E_joint_raw(r,z) + T*K(r)*ln(2)` (equivalently `Ebar = -T*logmeanexp_z[-Eraw/T]`). This leaves `P(z|r)` unaffected, but removes the spurious *a priori* preference over r when raw energies are equal. Apply the identical convention in joint training, marginal energy, sampling and normalization, and in **both** B/C. Preserve a switch/test for the raw historical P5 convention for reproducibility only; do **not** silently rescore old P5 checkpoints and call them directly comparable. If this proposal conflicts with actual code semantics, document and prove an alternative before proceeding. Test varying K, inactive-slot invariance, exact probabilities, normalization, finite-difference gradients and detailed balance, including reversible birth/death/swap/replace proposals with unequal K_i.

### 2.3 Audit five-factor B/C mapping and higher-order representational ability

Report 0020 describes the current B as a quadratic pairwise binary energy `E_static - Σ s_k z_k - Σ W_kl(r) z_k z_l`. Map every implemented term precisely back to the **five** v1.7 potentials, with which candidate-dependent tensor/weights feed each and which losses update them. A learned symmetric `W_kl(r)` is **not automatically a full higher-order** `φ_couple(r,z)`.

Test two finite synthetic fixtures: (i) a three-outcome interaction/parity-type pattern that cannot generally be represented by a *pure pairwise binary energy with no hidden variables*, and (ii) a four-action order-dependency pattern where the same endpoints but different preceding actions change success. Preserve an explicit quadratic-only B/C baseline. **If** the pure quadratic form fails the high-order fixture by representation (rather than data), implement the *smallest* versioned higher-order masked MLP residual for `φ_couple(r,z,c0)` and train it jointly; expose `quadratic-only` and `no-coupling` controls. Do not add handcoded ground-truth logical rules, hidden teacher labels or a second external classifier. Record added parameters so capacity-matched A controls remain meaningful. Any extra architecture is a named version/ablation, never a retroactive claim about P5.

### 2.4 Engineering/training fixes and core ablations

- Add gradient norm clipping (default proposed `max_norm=1.0`, record global norms **before/after** clipping), NaN guards, deterministic seeding and checkpoint/resume. Keep AdamW, temperature and feature policy initially identical to P5; use validation-only early stopping, without reading holdout.
- Add **capacity-matched A** (same core scientific factor types, comparable trainable parameter count to B/C) and a **geometry-only** A/B/C arm that drops initial DINOv2 features but retains allowed geometry/robot context. Include A-no-order, B-no-coupling and C-no-coupling. Train three optimizer seeds for each primary A/B/C, capacity-matched A, geometry-only controls and core coupling/no-order ablations **as far as the predeclared training cap permits**; publish exact missing runs rather than unequal denominators masquerading as fairness.
- Include static-invalid placement examples from the independent static checker, with balanced static-valid controls, outside the 24 costly teacher queries. Do not manufacture executable repair labels for invalid endpoints. Audit one-sided static supervision and individual head gradients.
- For policy-source sensitivity, certified-only versus certified-plus-budget-negative is a clearly named secondary ablation when there are enough fresh budget negatives; if not, report **NOT_ESTABLISHED** rather than claiming a meaningful comparison. Add a paired-intervention-supervision ablation if sample coverage permits. Keep architecture-specific loss masks correct (cost on only valid first relocation witness; no scene-edit travel cost).
- Validate A/B/C factor numerics and gradients: static, task, per-field, intervention effect, cost, finite-pool A ranking, B/C exact joint NLL, coupled/uncoupled gradients, 4-action order sensitivity, and teacher privilege leakage. A no-order control must be provably invariant to swapping identical-endpoint sequences. B/C predictions are marginal `Pr(z_r=1 | r)` and effect differences, **not** normalized raw energy treated as a success probability.

## 3. Expanded scenario population: 16 independent roots, 0–4 moves

**Proposal and numerical authorization requested in the companion prompt:** at most **16 fresh independent initial-scene lineages**, four batches of four, four predeclared scenario families. This is a *bounded development/stress-test collection*, **not** a new release benchmark or statistically powered G5. Existing P4/r19/P5 records remain available for **development only** and retain dataset provenance; do not count repeated views as new independent roots.

### 3.1 Four distinct families (four independent roots each)

| Family | Physical test to construct | Why it matters |
|---|---|---|
| **F1 — access-order (2–3 moves)** | A is not grasp-accessible until B is displaced. Keep identical endpoints in order-swap pair. Prefer existing **P3a `FIRST_ACTION_ORDER`** geometry for sound first-action negatives; verify successful order with actual full trajectory. | Real robot-access order effect, not only destination occupancy. |
| **F2 — dual necessary blockers (2–3 moves)** | In fixed-robot scene edits: original=0, edit A=0, edit B=0, edit A+B=1 **when independently observed**. Separately check whether physically executing A+B can restore target success. | Nonzero κ interaction and causal–repair coupling. |
| **F3 — 3/4-step access chain** | Four distinct movable obstacles; intermediate displacements enable grasp/access to later objects, or their destinations. Candidate 3/4 action orders share final endpoints; target completion after fully executed chain. Attempt full 4-move witness and four leave-one-out queries. | Long-prefix reasoning, move-once, 3/4-step dependencies; cannot be solved merely by 2-action cues. |
| **F4 — alternative destinations, starts and nuisance** | A relocation destination may require 3–4 moves while another destination avoids an extra move; include harmless/harmful nuisance and varied predeclared start poses. | Cost vs move-count tradeoffs, start-state sensitivity and misleading interventions. |

For **F2 and F3**, avoid putting any obstacle directly in the goal cell as the sole reason the original target fails: actively construct access/transport dependencies. Keep some GOAL_OVERLAP controls in F1 but report their proportion; target **less than one-third of admitted negative labels from trivial GOAL_OVERLAP**, as a diagnostic diversity goal, never by deleting labels. Do **not** assume desired outcomes; every `F2 κ=1` or `F3 four-move necessary` condition remains a *construction hypothesis* until independently labelled. Static admission can use geometric plausibility and certificates; **do not use held-out oracle outcomes to handpick successful scenes**. Log reject reasons and achieved family yields. A family that fails its physical construction gate must be marked inadequate, not silently replaced by trivial occupancy cases.

### 3.2 More starting positions means both object layouts and robot q0

- Predeclare at least **four collision-free, joint-limit-valid robot initial-pose strata**: existing default plus three reproducible, varied configuration/sector alternatives. Obtain them from actual FK/pose/collision checks and deterministic seed/rule before teacher outcomes, **not guessed joint angles**. Keep gap/attachment valid. Balance these strata across F1–F4 and splits. Report actual initial q arrays and whether the sampled stratum was admitted.
- Independently vary target/goal resting cells, obstacle layout/order around workspace, nonmoving distractors, staging destinations, and which object is blocked. Do not change the certified 2D object-radius/robot/grasp physics just to create difficulty; alter those only under a separately named physics ablation.
- If adding matched different-q0 variants to the *same geometry*, account for their full descendant catalogue and budget, and keep them in one lineage/split. **They never inflate the independent-root count.**
- Predeclare 16 unique geometry seeds, a fixed family/pose/batch schedule, construction rejection policy, and balanced split of **8 train, 4 validation, 4 sealed holdout** (2/1/1 per family), before outcome collection. Static geometry acceptance may reject invalid scenes; do not promote a post-hoc favorable seed. If an independent root cannot be constructed within the frozen candidate-attempt quota, log it as rejected/NOT_RUN and preserve the denominator.

### 3.3 Per-root catalogue (up to **24 UNIQUE teacher queries**; duplicates removed)

| Class | Max | Notes |
|---|---:|---|
| Clean reference base (no repair) | 1 | Separate context, not a z variable |
| Obstructed original task (empty repair) | 1 | z0 |
| Single-action repair candidates | 4 | One for each selected movable obstacle; include nuisance where appropriate |
| Two-action sequences | 3 | At least one same-endpoint swap pair |
| Three-action sequences | 3 | Order variants/prefix alternatives |
| Four-action sequences | 3 | Main r4 plus two distinct same-endpoint permutations; 24 possible permutations exist, only sampled ones evaluated |
| Four leave-one-action-out omission queries of **designated main r4** | 4 | Each independently run from S0; deduplicate with already scheduled triples |
| Fixed-robot scene edits | 3 | Predeclared A-only, B-only, A+B; independent target-only queries from q0 |
| Nuisance fixed-robot edit | 1 | Learner effect supervision, outside designated r4 z-layout |
| Alternative destination | 1 | A different legal endpoint, not a robot teleport |
| **Total (max)** | **24** | Includes reference; **never pad with duplicate/no-op queries** |

This is an *upper-bound template*: a scene where only two moves are meaningful should not fake third/fourth causal moves. Predeclare the applicable subset, map every physical query to exactly one deduplicated teacher invocation, and record omitted/unavailable catalogue rows. The 4-move designated pool has 9 outcome variables requiring at most 9 separately decided physical teacher queries; those queries may be shared with other catalogue entries. A second complete 2-move candidate under the same edit catalogue is strongly preferred so the exact multi-repair joint loss is genuinely discriminative. Do **not** require all permutations or all possible destinations to be exhaustively evaluated.

**Upper limits:** `16 roots × 24 unique queries = 384`, each up to 3 declared seeds = **1,152** possible seed attempts, **not** a promise that budgets permit all. Static-invalid endpoint checks are tracked in a separate dataset and do not consume teacher query slots. Root and policy hashes are frozen before first run.

### 3.4 What to keep when UNKNOWN occurs

The 250 CPU-s/seed P4 guard remains; a difficult four-move repair can be censored. Keep UNKNOWN and all partial relocation witnesses; their genuine relocation first-witness J may be used under the existing cost mask only when valid. Do not call a censored query budget-infeasible and do not count an omitted z slot as negative. If the UNKNOWN rate makes length-four complete pools infeasible, stop that *family/batch* under the predeclared gates; report need for a separately authorized budget/teacher-policy variant rather than mutate OPNEG-v1 midrun.

## 4. Hard limits and stop gates

**Collection budget (authorized only by an explicit user prompt):**

| Quantity | Hard maximum |
|---|---:|
| New independent roots | **16** (4 batches × 4) |
| Teacher queries | **384** (≤24/root) |
| Declared teacher seed attempts | **1,152** (≤3/query) |
| Per-seed and per-query guards | **UNCHANGED OPNEG-v1**: per seed 250 CPU-s, 600 wall-s; per query cancel 870 / hard 900 CPU-s, wall 1,800 s |
| Per-root teacher CPU | **1,500 CPU-s** |
| Per-batch teacher CPU | **5,000 CPU-s** |
| Aggregate new collection CPU | **20,000 CPU-s** total process tree, workers + coordination |
| Static construction/admission CPU | **700 CPU-s separately measured** |
| Teacher+static overall CPU | **20,700 CPU-s** |
| Aggregate collection wall | **36,000 s** |
| Workers | **1** |
| New model-selected simulator episodes (separate P6 diagnostic) | ≤12; ≤4,800 CPU-s total, ≤400 per episode, no multi-candidate target feedback |
| Training + ablations | ≤**9,000 CPU-s**, ≤18,000 s wall, CPU-only first |
| GIF/render/plot stage | ≤**2,000 CPU-s**, ≤4,000 s wall |
| Foundation/regression/sampler | ≤800 regression + 160 G4B CPU-s, each separately guarded |

Admission and compute ledgers are cumulative; no reset between batches, no duplicate work on resume, 0 unmetered planner calls. The batch/root budgets are nested within the aggregate; hitting any of them halts admission/run as appropriate. Make process-tree coordinator, worker and nested connector call counters visible. Do not claim zero planner calls simply because the parent coordinator called none.

**Batch 1 — mandatory four-root checkpoint:** include **one root from each F1–F4**, with at least one 4-action sequence proposed. Gate into batch 2 only if: (i) zero proof–witness contradiction and zero integrity violations; (ii) an actual physical four-action execution or a decided three-action dependency is present, **and** (iii) at least one decided same-endpoint access-order contrast **or** one independently decided nonzero interaction; (iv) ≤25% UNKNOWN of attempted teacher queries; (v) budgets and at least one multi-repair complete B/C pool hold. If not, **do not silently burn the remaining collection**; continue with math/training/visualization on measured data, and report blocked diversity target. Do not relax the gate afterward to keep running.

**Subsequent batch checkpoint:** require evidence from both the access-order and 3/4-step families, measured nontrivial supervision and useful B/C pool completeness per CPU. A root with two consecutive 250-CPU-censored seeds on two queries must stop new expensive queries for that root; preserve its planned denominator. Every batch must have cross-family root counts. Stop on FATAL witness/certificate contradiction, corrupted state, process-tree cap overshoot or source-hash inconsistency.

**Coverage targets, not guarantees:** at least 4–6 new roots with decided access-order contrasts, 3–4 with nonzero κ (scene or omission, scoped), ≥6 fully decided B/C multi-repair pools from ≥4 new independent roots, ≥2 complete **four-action** repair witnesses with real saved relocation+target+safe-retreat traces, and diverse 0/1/2/3/4-move outcomes; plus measured cost labels and balanced static invalid/valid endpoint examples. Report denominators and shortfalls, never invent evidence or selectively erase rejected roots.

## 5. Train, ablate and assess A/B/C on new data

1. Build a **new** learner-view dataset with manifest and frozen policy/layout hashes. Merge historical decided *development* records only if compatible and deduplicated by source/query; keep historical P4/P5 selected development roots **out of the newly sealed holdout**. Do not train on sealed holdout labels, positive trajectory details, or planner diagnostics. Root/family IDs remain metadata only.
2. Ensure each model has functioning 4-token GRU/prefix representations. For B/C exact `K<=9` finite sum and proposed entropy-normalization convention; test `m=0…4`, active masks, gradients, 2^9 states, and repairs of different K. Examine computation cost as K grows. Do not shift parameterized factor definition midway through the training comparison.
3. Add validation-only early stopping, global clipping and seed controls before retraining. Fit on train roots, choose checkpoints/hyperparams **only with val roots**, and evaluate sealed holdout **once** after choices frozen. For each model/ablation log per-term loss curves, gradient norms, source-weighted training masks, exact joint-pool counts, calibration, outcome effects, κ errors and 4-move ranking.
4. **Matched primary experiments:** A, B, C each with **3 independent optimizer seeds**, identical root/query/cost masks and proposal pools; A-capacity-matched; A-no-order; B-no-coupling; C-no-coupling; geometry-only A/B/C. Prioritize primary nine runs and no-coupling controls, then capacity/no-vision/no-order as compute permits; if one comparison is incomplete, do not cherry-pick the completed seed count. Quadratic-only B/C versus higher-order residual is a named representational ablation when activated.
5. Train strong **analytic geometry-only** and uniform ordered candidate baselines with the same candidate pool and verifier budget. A learned geometry-only arm is *not identical* to the analytic baseline. Preserve confirmed improvements only if measured on root-held-out labels and preferably independent one-shot executions.
6. Distinguish: in-sample overfit, new-root task prediction, decided same-endpoint order accuracy, sign/magnitude of scene and omission effects, nonzero κ prediction, separate outcomes for length-four cases, expected-calibration error/Brier/AUROC where sample size supports, cost error, moved-object count, verifier CPU and one-shot successful repair rate. Report model parameter counts and matched inference-call budgets. Root-cluster uncertainty; no statistical significance claims from tiny heldout n.
7. Outcome-model comparison **must** include a `B/C vs B/C-no-coupling` effect on **independent** nonzero-κ roots. A vs C with GRU held and A matched-width remains central. Do not choose the 'winner' based only on train MSE or GPU speed.

## 6. One-shot simulator checks (bounded, optional gated execution)

After model selection is frozen (using **train/val only**), attempt up to **12** new model-chosen executions: A, B and C on the same **four** selected root queries (two val and two holdout, each from independent lineages when possible). If sufficient roots/candidates do not exist, do fewer and report denominator. Starting S0 is re-created identically per model. Each model ranks its own candidate repairs once, before robot motion; it may attempt ordered relocation candidate(s) under the same prescribed no-target-feedback rule, then **commit** one witnessed order and evaluate the target **once** from achieved state, including SAFE_RETREAT. Never use target failure to switch to another repair; no privileged oracle selection. Instrument calls, costs, failures, one-shot target calls and outcomes. This is simulated 2D verification, **not** physical xArm hardware. Match number of candidate scores, maximum motion attempts and per-episode CPU across A/B/C.

## 7. GIF visualization deliverables (mandatory and scientifically honest)

User must be able to **watch** the generated data and the learned model decision process, not merely inspect static PNGs. Use saved actual robot traces and recorded energies; do not animate invented robot trajectories. GIF is mandatory; optional MP4 may accompany it.

**For each collected root** create `scene_start.png` and `catalogue.png`, then (as appropriate and supported by evidence):

- `executed_repairs.gif`: real 3R links, housings, palm, fingers, gripper state, attached obstacle transport and true resting object poses, full ordered action sequence **including up to four relocations**, target and checked safe retreat, rendered from recorded robot q/object/phase samples; no synthetic interpolation presented as verified motion. Annotate action `1/4` etc, target attempt, status, achieved joint state, and measured J.
- `order_comparison.gif`: split screen of **recorded** successful and alternative ordered executions with same endpoints. If one side is certificate-negative, display a **static failure/certificate panel** and no fictional moving robot on that side. If UNKNOWN, visibly state `UNKNOWN / NO VERIFIED TRACE`.
- `interventions.gif`: before/after/combined **fixed-robot** pose edits using the same exact q0 and original appearance anchor; clearly stamp `HYPOTHETICAL SCENE EDIT — NOT A ROBOT RELOCATION`; present measured outcomes, provenance and κ when decided. May show object pose changes as a labelled edit, not as physical trajectory.
- `candidate_orders.gif`: all 0–4-move sampled candidate orders/destinations as **ghost overlays** (explicitly `PROPOSED, NOT EXECUTED` unless a matching witness exists). Do not render a ghost teleportation as a verified motion path.

**For each of A, B, C** create:

- `A_proposals.gif`, `B_proposals.gif`, `C_proposals.gif`: deterministic saved sampler snapshots through candidate repair space. Overlay selected action order/ghost destinations, predicted feasible probability, model-internal energy (per-model normalization), predicted travel J, Boltzmann/sample weight, and whether the *separately recorded* outcome was witness/certificate/budget/unknown. B/C also show their exact `K`-active outcome marginals and selected intervention/omission probabilities; A shows re-scored effect estimates. Never claim a model generated/executed a robot trajectory.
- `A_training.gif`, `B_training.gif`, `C_training.gif`: selected saved epoch checkpoints at fixed axes showing per-term losses, actual prediction or energy evolution, and a fixed set of shared root candidates. This is **model training visualization**, not robot execution.
- `ABC_side_by_side.gif`: synchronize A/B/C on the SAME one or more representative roots/candidate catalogues. Show relative rankings and prediction probabilities, not raw cross-model energies with incompatible offsets. Include examples of length 2 and length 4 when actually available.
- `ABC_selected_execution.gif`: render model-selected **actually verified** 2D trajectories from §6 when available; otherwise render model proposals only, with a clear `NOT EXECUTED` label. Annotate distinct chosen orders, verified outcomes and CPU/verifier cost.

**Renderer requirements:** headless, deterministic, fixed workspace/scale per comparison, normal speed 8–12 fps with readable labels, final status frame held for ≥1 s, capped output dimensions/filesize, frames written/closed atomically, source trace/checkpoint/config hashes stored alongside each GIF, optional contact sheet PNG and index `visualizations/README.md` linking all figures. Check GIF first/last frames automatically; spot inspect one four-move trace and one failure/unknown comparison. Fail the visualization gate if any animation depicts a nonexistent or unverified robot path as actual execution.

## 8. Tests, analysis and required final report

Before teacher calls, run 0–4 move/parser/proposal tests, `K=9` exact enumeration and entropy-invariance tests, sampled detailed balance, 4-move omission and no-op/alias invariance, tamper/hash tests, first-witness cost semantics, no-future-input test, regression impact. Re-run applicable historical regression under its separate guarded budget, plus six archived replays; if these don't complete, block robot collection and report clearly. Test the five-factor mapping/representational audit and static head training behavior. B/C coupling and higher-order residual must have explicit gradient-path tests.

After collection, report one new numbered **immutable** stage report (next available, likely 0022 after report 0020/0021 sync), containing:

1. P6 pass/partial/blocked gates, source/HEAD/policy/layout hashes, exact file changes and line counts, test commands and exit codes, branch/remote status.
2. Every root seed, initial q, geometry/family, split and accepted/rejected static-construction attempt; frozen denominators (16 roots, 384 max queries, 1152 attempts), actual attempts/labels/reasons by length 0–4 and evidence source.
3. Costs/CPU/wall/calls per root, batch, seed and skill; full process tree and censoring/STOP rationale; first witness cost, analytic displacement, no target-selected cheapest-trace leakage.
4. Complete B/C pools with distinct z outcomes, K per candidate and exact `2^K` count; measured scene/omission effects and nonzero/zero κ; proof-grounded versus operational comparisons; outcome coverage masks.
5. Actual trained results, seed means/variation, parameter counts, cross-model matched/root-held-out metrics, exact joint loss and sampler correctness, geometry/capacity/ablation comparisons, calibration and optimizer stability.
6. Model-selected 2D one-shot execution evidence, or explicit NOT_RUN counts, and **GIF index with clickable relative paths**. Clearly separate `OBSERVED`, `DERIVED`, `PREDICTED`, `NOT_RUN`, `UNKNOWN` and `PROPOSAL_ONLY`.
7. A falsifiable recommendation for G5/G6: whether to collect additional independent roots or proceed with matched 2D evaluation. State what evidence supports B/C over A or the analytic control, if any; no invented advantage.

Only commit/push explicitly authorized new code, tests, versioned teacher/learner views, new P6 run evidence/GIFs and new report after verifying existing manifests remain byte-identical. Never stage the pre-existing tracked PDF deletions or user's untracked source instructions. End with **STOP**; G5/G6, 3D, real hardware and further large collections require separate explicit authorization.
