# BXY-P19 → P22: K3/K4 Completion of Approach B (2D)

**Execution instructions for Claude Opus 5.5 High**  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Branch:** `approach-b-xy-v1`  
**Audited starting commit:** `20121eee0c337c89134cea621eef7b80d592a008`  
**Reference methodology:** `Approach_B_Final_Methodology_2026-10-31.pdf` and the P16–P18 reports `0123`, `0124`, `0125`.  
**Purpose:** complete and substantiate the already-agreed K0–K4 **2D** research scope, with particular attention to verified K3/K4 repairs. **Do not introduce another learning architecture, new random-variable family, different robot, or 3D setting.**

> **Scientific truth at entry:** K3 and K4 are part of the *specified challenge domain*, not yet an adequately measured capability. In P16, 87 hard-scene roots contain 11 catalogue-relative verified K2, only **2 K3**, and **0 K4**. The current P18 confirmatory plan is honestly scoped to K≤2. Its reserved `bxyg21confirm` namespace and 300-slot manifest must remain untouched. P17 candidate D shows development improvement, but the quadratic coupling itself does not meet the prespecified meaningful-benefit test.

## 0. Outcome contract and authorization boundaries

Finish **P19 audit → P20 K3/K4 development data → P21 matched training/evaluation → P22 final methodology/evidence freeze** sequentially. Each stage produces its own report, deterministic evidence, tests, Git commit and push. Do not mark success merely because code executes or scenes have `K_intent=4`. End-to-end completion requires verified, independently replayed physical repairs at K3 and K4 and statistically honest evaluation by K stratum. If physical constraints or authorized budgets prevent that, return an explicit, useful negative verdict.

### What must remain unchanged

- **Embodiment:** current 2D planar **3R** robot, finite-width arm/gripper, 8×8 resting-placement grid, continuous physical motion, frozen grasp/motion skill family and fixed per-query teacher budgets.
- **Action interface:** proposed ordered relocations `a_t=(object,destination)`, `m≤6`, followed by one target action. Proposer supplies orders and destinations; scorer only ranks supplied candidates.
- **X:** entire ordered physical relocation prefix, with achieved joint state carried between actions **without intermediate home resets**, plus a collision-free final gripper-free connector to `q_ref` at the stopping prefix.
- **Y:** independently attempt the original target manipulation from the *same* fixed `q_ref` in the hypothetically edited scene, whether or not X was executable.
- **Shared Y:** different orders reaching the identical edited scene share one Y query but retain distinct X queries.
- **F1–F5:** analytic F1, predecessor-sensitive F2 X unary, hypothetical-scene F3 Y unary, F4 recomputed omissions **through the same model** (no learned F4 head), optional quadratic F5 XY term. The capacity-matched uncoupled control E remains essential.
- **Normalized probabilities:** `P(Y_s=1)=sigmoid(b_s)`, `P(X_q=1 | Y_s=y)=sigmoid(a_q + w_q*y)`, so `p_success(q)=sigmoid(b_s)*sigmoid(a_q+w_q)` at frozen temperature 1. The no-op success is `P(Y0=1)`.
- **Training:** exact root-deduplicated observed-data joint NLL; optional complete-success travel Huber auxiliary; **already-developed GEO2 and SYM auxiliary** as a documented P17 extension, not a fabricated part of the October 31 original objective. Keep existing architectures and coefficients unless a bug fix is mathematically unavoidable and versioned.
- **Selection:** frozen risk-and-effort score using `-log(p_success) + alpha*m + beta*C_d + gamma*J_hat`, analytic F1 first, no-op eligible, versioned learned thresholds/rules. Do not tune on confirmatory outcomes.
- **Truth semantics:** attempted within-budget negative = operational 0 with failure metadata; unattempted/censored = absent. Distinguish certified impossibility from `NO_PLAN_FOUND`, unknown planner/transit failures, and a truly impossible relocation.
- **Custody:** preserve P-min–P18 all original reports, model hashes, training manifests, checkouts, results and replays. Do not expose, generate, inspect or relabel the 34 historically exposed test roots or any reserved confirmatory namespace.

### Bounded additional development authorization

The following are proposed *hard ceilings* for this requested implementation, **not expected usage**. If the user supplies/pastes this instruction as an execution authorization, create separate immutable authorization manifests per gate and enforce them from the first CPU-consuming task. If the environment or operator does not accept these limits, stop at the authorization gate rather than silently increasing them.

| Gate | CPU ceiling (inclusive of overhead) | Wall ceiling | Workers | Additional limits |
|---|---:|---:|---:|---|
| P19 | 2,000 CPU-s | 3,600 s | ≤2 | Read-only audit, synthetic/microcase checks; **no teacher labels or optimizer** |
| P20 | **60,000 CPU-s** | **28,800 s** | ≤4 memory-gated | ≤150 newly accepted development roots, ≤1,400 CPU-s per root; teacher **per-query** limits unchanged |
| P21 | **65,000 CPU-s** | **30,000 s** | ≤4 memory-gated | ≤90 matched learning runs, ≤2,000 CPU-s per run; all evaluation inside cap |
| P22 | 3,000 CPU-s | 5,400 s | ≤2 | Report, reproducibility, frozen analysis and synthetic dry-runs; **no independent cohort generation** |

Keep a durable aggregate ledger, strict per-process cap, remaining-budget reservation, wall accounting over resumes, `SIGTERM`/crash handling, input/output hashes, and equal opportunity for matched arms. Budget-exhausted experiments remain **incomplete**, not success. No API charges, GPU requirement, robot hardware, 3D, enlarged teacher query budgets, or independent confirmation are authorized. Stop at P22.

## 1. Gate P19 — Evidence, implementation and final-method alignment

Produce `responses-phases/0126_BXY_P19_K34_PREFLIGHT.md` and `runs/approach_b/bxy_p19_v1/`.

1. Verify branch/HEAD/origin and all P-min–P18 artifact hashes. Read methodology PDF, all `0123`–`0125` reports, frozen designs, source of `bxy_p16.py`, `bxy_p16_inputs.py`, `bxy_p17.py`, `bxy_p17_data.py`, `bxy_p17_eval.py`, `bxy_p18.py`, `bxy_teacher.py`, `bxy_f1.py`, and the relevant geometry/motion/grasp modules. If any local checkpoint is absent, report it immediately; do not claim that stored hashes substitute for checkpoint bytes.
2. Reproduce P17 / P18 saved metrics and distinguish **out-of-fold 3-seed, fold-specific-rule** performance from **P18 all-15-checkpoint ensemble with one pooled rule**. Do not mislabel one as an independent estimate of the other. Safeguard and hash-verify every checkpoint and dependency; create a second durable backup if available, otherwise explicitly identify the preservation gap.
3. Inspect current geometry access maps and `K_geom` solver: does it compute an exact lower bound over the *declared finite grasp/place candidates* or an optimistic/greedy heuristic? Check that fixed obstacles, robot base, target, no-op and reachable parking destinations are handled soundly. Write small counterexamples where a proposed four-blocker construction is not sufficient to force four moves, or is physically unexecutable.
4. Audit the 16 candidate / 44 query cap, the use of `intended` sequences, catalogued `K`, per-query teacher limits, and the `K_geom=4 → verified K4=0/3` failure. Quantify generator rejection and failed relocation/target/connector phases by mechanism, not just overall counts.
5. Recompute order metrics as an **extra diagnostic**: exact same action/destination multiset under true permutations, same endpoint, both F1-admissible, X discordant; stratify **certified** versus planner-budget negatives. Treat |score difference| ≤ `1e-8` as tie (threshold fixed before calculation). Preserve historical P17 metric unchanged.
6. Correct the planned paired-confidence-width claim: for per-root paired differences `D_i ∈ {-1,0,1}`, `SE(mean D)=s_D/sqrt(n)`; `1.96×0.5/sqrt(n)` is **not** an unconditional worst-case paired bound. Use paired disagreement-rate sensitivity and simulated power, not an unsupported guarantee.
7. Document the already implemented additions to the original methodology: GEO2 analytic access features and symmetric within-root Y contrast auxiliary `L_SYM`; the new objective is `L_joint + λ_J L_J + κ L_SYM`, and SYM is not part of the October 31 base specification. Preserve original as historical provenance.
8. Produce a **requirements-to-evidence matrix** for K0/K1/K2/K3/K4, length 1–6 prefixes, genuine order twins, omissions, harmful edits, X/Y four cells, matched success/travel and the independent test. Make clear which items are proven by real teacher witnesses and which remain proposals.
9. Freeze P20 target counts, mechanism allocations, query custody and analysis plan before any P20 teacher call. Commit and push this gate.

**P19 blocking conditions:** label leakage, broken X/Y connector semantics, missing irreplaceable checkpoints needed for planned comparisons, or unexplained source/hash drift. Do not attempt to fix these by changing old evidence.

## 2. Gate P20 — Construct *physically executable* K3/K4 development scenes

Produce `responses-phases/0127_BXY_P20_K34_DEV_COLLECTION.md`, a minimal versioned `bxy_p20*.py` implementation, a frozen generator/teacher ledger, source hashes, saved witnesses, and at least 12 useful 2D figures. Work in a **new development namespace**, e.g. `bxyg34dev`, never `bxyg21confirm` or any historical prefix.

### 2.1 Definitions (do not conflate)

- **K_intent:** construction request. Never evidence of physically necessary relocations.
- **K_geom:** geometric lower-bound candidate inferred from declared grasp/place access modes; specify the exact assumptions under which the bound is sound. If using a greedy heuristic, label it heuristic, not a certificate.
- **K_catalogue:** minimum `m` among **verified complete X=1,Y=1** candidate repairs in a registered, frozen catalogue. This is catalogue-relative, not globally minimal.
- **K_necessary,cert:** a stronger optional claim **only** if a sound certificate excludes every shorter legal correction in a clearly declared finite action/destination grammar. Never infer it from `NO_PLAN_FOUND` or from an incomplete catalogue.
- **No-candidate-success:** no witnessed repair in that catalogue under the fixed teacher policy; not global infeasibility.

### 2.2 First study *why* K3/K4 are failing

Separate (i) closure geometry is too dense for any blocker to be picked, (ii) proposed parking sites are unreachable or block later actions, (iii) intermediate prefixes don't preserve access, (iv) final target scene reopens only a teacher-inaccessible mode, (v) terminal q_ref connector fails, (vi) target budget-limited versus certified failure, (vii) candidate catalogue excludes an intended/alternative success, and (viii) the 3R robot / 8×8 domain may intrinsically lack enough feasible arrangements for some mechanisms.

**No assumption that more obstacles = better scenes.** Show quantified evidence for which cause dominates K4 attempts. Include small geometry diagrams and an exact physical-witness replay for each realized success.

### 2.3 Generator strategies to attempt in order

**Strategy A — Backward-feasible K3/K4 rearrangement construction.** Using geometry and the *declared* grasp family, lay out an analytically open post-repair target scene, assign 3–4 distinct blockers and candidate parking cells, then place blockers back into the initial scene to close target pick/place alternatives. Validate analytic pick and place access for every proposed relocation in the **ideal predecessor scene**, including the final connector footprint. At every shorter intended prefix, analytically check why target access remains closed, but do not call the physical target teacher during construction. Sample alternative geometries and avoid single-path sweep tricks.

**Strategy B — Distributed mode closure with exact small-set geometry.** Across all declared pick/place mode pairs, search for a set of 3 or 4 independently relevant movable blockers that covers each access option. Use bounded exact combinatorial enumeration for the *finite analytic mode* abstraction where tractable (not an untested greedy certificate). Keep each blocker's own feasible pick and safe park options. Require several distinct target modes to reopen after the full intended relocation, where possible, to avoid a one-mode planning bottleneck.

**Strategy C — Order-sensitive nested/interference scenarios.** Engineer F1-admissible alternative orders with the **same final object scene**: moving A first might occlude B's pick or force a bad robot state, while B→A remains executable. Do not count occupied-destination sequences that F1 screens as learned ordering evidence. Track order disagreements on certified and budget-limited subsets.

**Strategy D — Control scenes and independent geometry families.** Preserve K0/K1/K2, neutral and harmful edits, redundant moves, distinct pick/place/mixed closure families, different source and goal regions, and alternative parking distributions. Include at least one geometric construction family that does not trivially expose the generator's exact blocker assignment through GEO2 summary features. Within the unchanged teacher skill/robot, vary construction logic, not skill semantics.

Only use **analytic geometry, finite action grammar, predeclared proposer logic, and deterministic random seeds** for scene/candidate creation. Development outcomes may inform the *next separately frozen wave design*, but never alter a wave's own candidate catalogue after any teacher outcome. No witness chasing or success-conditioned discarding within a declared outcome-blind evaluation distribution.

### 2.4 Candidate/query capacity and evidence completeness

The P16 16-candidate / 44-query cap may truncate meaningful four-move prefixes or omissions. Audit this before collection. For a versioned P20 design, reserve slots for **no-op, intended full 3/4-move repair, every stopping prefix, all single-action omissions, one or more same-endpoint order permutations, shorter alternatives, different destinations, harmful/neutral controls, and up to two nuisances**. Deduplicate unique X ordered queries and Y final scenes. Enlarge candidate/query caps **only if needed**, before labelling a wave, document the computational implications and do not rewrite prior P16 evidence.

Demand **complete X/Y evidence** at every stopping prefix for a claimed verified K3/K4 witness, with replayed relocations, connector-to-q_ref and target. For a catalogue-relative minimum K=m, every registered F1-admissible candidate with fewer than m moves must have an attempted valid X/Y verification outcome sufficient to determine its complete success; unknown/censored candidates prevent a minimum claim. Classify attempts that fail by budget separately from certified infeasibility. Retain X=0/Y=1, X=1/Y=0, redundant/harmful, and order-twin controls.

A teacher may try alternate grasps under the *same fixed budget*. Do **not** secretly increase the teacher query cap in K4-only cases or revise failed labels without versioning an entirely new protocol and rerunning all fair controls.

### 2.5 Three sequential development waves and honest stopping

- **Wave 1 (physical feasibility probe):** a small deterministic batch focused on K3/K4 plus easy sanity controls, with a frozen catalogue before teacher. Collect phase failures and per-prefix labels; report fraction with verified complete witnesses.
- **Wave 2 (geometry revision):** change only the generator/proposer if Wave 1 identifies a justified bottleneck. Freeze a new version before teacher queries; preserve Wave 1 as-is.
- **Wave 3 (coverage):** allocate remaining bounded resources using *predeclared* development composition; do not cherry-pick unseen test or success labels.

**Targets, not guaranteed results:** ≥20 independently generated verified K3 and ≥20 verified K4 roots in development, across at least two construction mechanisms each; ≥10 strict F1-admissible same-endpoint physical-order contrasts for the combined K3/K4 set; ≥10 harmful and ≥10 neutral counterfactual controls associated with hard scenes; complete matched prefixes/omissions. A **limited-data** gate may proceed at ≥12 K3 and ≥10 K4, but K-stratum inference must be labelled exploratory with wide uncertainty. If K4 remains absent despite legitimate bounded attempts, return `K4_PHYSICAL_DATA_NOT_ESTABLISHED`, not a fictitious completed method.

Do not confuse a subset chosen after teacher verification for curriculum learning with an *outcome-blind sample of the generating distribution*. Publish both the all-attempted generator denominator and the K-conditioned curriculum subset, with separate evaluation claims. Preserve rejected scenes and CPU charges in the denominator and ledger.

### 2.6 Visualization and reproducibility

At least: construction diagrams showing all grasp/placement mode closures; initial, each of 3–4 edited prefixes, final target scene; X physical evidence on each successful relocation and q_ref connector; independent Y target witnesses; a successful-versus-failing exact-order twin; harmful vs beneficial destinations; successful/failed K4 attempts with phase labels; K_intent/K_geom/K_catalogue confusion matrix; counts by root and generation family; CPU spent by teacher phase. Each scene image must be tied to an actual record or clearly marked geometric proposal. Save animation frames or replay trace IDs if already supported, without introducing major visualization dependencies.

## 3. Gate P21 — Learn K3/K4 with the existing Approach B model

Produce `responses-phases/0128_BXY_P21_K34_LEARNING.md`, immutable experimental design and 5-fold/3-seed run ledger, out-of-fold predictions, ablations and 2D evidence.

### 3.1 Do not redesign the model

Train existing P17 arms with their **same** architectures and mathematical semantics. Include the earlier 197 P-min and 28 P15 development roots, 87 V2.1 roots, and the new P20 development data; keep source strata and family identities. Use fixed DINO input contract, GEO2 and `SYM`, not new latent variables, graph edges, learned F4 pair heads, grasp-specific online IK or 3D modules.

The minimal matched arm roster should include:

- **D**: XYQ-GEO-SYM, original quadratic candidate;
- **E**: capacity-matched uncoupled XY-UNC-SA-GEO-SYM (the simpler practical challenger);
- **A**: matched DIRECT-GEO;
- **B**: unchanged XYQ-BASE;
- **G**: order-invariant GEO-SYM control.

If resources allow within the **frozen** roster, retain **C** (GEO-CON) to isolate SYM, yielding 6 arms × 5 folds × 3 seeds = 90 runs. Do not add unregistered arms after seeing results. If only five arms are preregistered, cap at 75 runs and explain the reduction beforehand.

### 3.2 Split and loss custody

Use family-/mechanism-grouped five-fold out-of-fold evaluation. Never split different variants or shared-causal-root edits across folds. Independently report overall, originally feasible, initially infeasible, verified-repair available, K1, K2, K3, K4, and geometry-family holdout. Predeclare the exact difficulty strata and selection-rule tuning using only each fold's training/early-stop material. Keep the exact root-normalized observed-data likelihood; `L_SYM` is separately logged and clearly a P17 extension. Travel Huber is supervised **only by complete replay-verified witnesses**, including no-op target travel. Limit optimizer scope to this roster and fixed hyperparameters; any altered hyperparameter requires a versioned experiment **before** starting.

Use both: (i) OOF model with fold-specific inner rule, the directly comparable P17 evaluation; and (ii) a clearly marked read-only diagnostic of the P18 pooled rule on OOF scores. Do not present a 15-model ensemble's predictions on its own training roots as held-out evaluation. If freezing a new deployment ensemble after P21, explicitly distinguish that new predictor from the CV estimate.

### 3.3 Primary measurable endpoints

Pre-register **two separate endpoints**:

1. **Unconditional repair success:** fraction of all initially infeasible roots whose selected candidate is verified X=1 and Y=1.
2. **Availability-conditioned repair success:** fraction of initially infeasible roots *with at least one verified candidate* whose selected candidate is verified.

Also pre-register the unnecessary-repair rate on originally feasible roots, including harmful-vs-harmless, no-op correctness, selection confidence, hard-case abstention, complete travel on matched successful decisions and number/displacement of relocations. Report distinct n by K and generator family. Use paired family-cluster bootstrap with correctly calibrated confidence intervals; include sensitivity/power for **paired** model disagreements.

**K3/K4-specific tests:** per-prefix Y pattern (not forced to increase at every move), complete X+Y physical proof, counterfactual omitted-action Y sign, strict same-endpoint exact-permutation order accuracy, certified-only order subset, K3/K4 success conditional on catalogue availability, and nearest lower-K confusion. If K4 n is inadequate, say so and do not claim a verified statistical improvement.

**Core comparisons:** D vs DIRECT-GEO (whole-system benefit), E vs DIRECT-GEO (simpler XY factorization), D vs E (quadratic incremental value), D vs G (order representation), D/E vs analytic-access baseline and no-op. Report both P17's preregistered safety criterion and any *new* criterion without silently weakening the former. The new K3 and K4 hypotheses must be frozen before training.

**Guardrails:** proposed success improvement ≥0.10 absolute against matched DIRECT on the repairable K3/K4 subset, with paired CI95 lower >0 and unnecessary-repair difference ≤ +0.05 as a **target**, plus a stricter sensitivity CI for the safety outcome. These conditions are *targets*; insufficient n, failure to improve or coupling being unnecessary do not authorize result-driven retries. No baseline is removed for performing well.

### 3.4 What counts as a successful K3/K4 evaluation

Do not claim “learned K4” from training fit alone. It requires a nontrivial number of held-out K4 roots with complete physical witnesses, model-selected true repairs (including correct order/destination), and a matched baseline comparison. Separate generalization *within development generator families* from genuinely independent generator-family tests. Do not describe classifier AUROC alone as corrective-action success.

## 4. Gate P22 — Final evidence freeze and independent test readiness (NO CONFIRMATORY COLLECTION)

Produce `responses-phases/0129_BXY_P22_FINAL_2D_METHOD_AND_K34_READINESS.md`, updated standalone methodology appendix, all reproducibility hashes, plots and a new versioned confirmatory **proposal** only.

1. Carry forward the October 31 methodology intact as provenance; publish an explicit *implemented extension addendum*: GEO2 inputs, SYM term, root-consistent X/Y loss and shared Y, optional quadratic interaction, current selection rule. Do not rewrite history or assert coupling is beneficial without matched evidence.
2. Update the evidence matrix for K0–K4: counts of independent roots, verified complete repairs, strict shorter alternatives, omissions, order twins, certified vs budget-only negatives, per-stratum confidence intervals, and remaining physical/proposer bottlenecks.
3. Verify that the intended 2D benchmark permits the observed K4 under the unchanged embodiment. If no verified K4, document an informative bounded infeasibility/teacher limitation and the exact missing evidence rather than lowering the meaning of K.
4. Freeze a candidate model and matched E and DIRECT controls with hashes and **second-copy** checkpoint custody. If D's coupling remains unsupported, state that E may be preferred; choose any operational recommendation from development results only.
5. Design an **independent** test including K0–K4 and at least one distinct construction family where practical. Determine sample size from actual K3/K4 realization and paired disagreement assumptions. The previously frozen P18 300-slot plan remains unchanged and **not executed**; create a new plan/namespace for any expanded K3/K4 confirmation. No test-root generation, model scoring, teacher collection or tuning in P22.
6. Include an independent preregistration specifying primary and secondary endpoints and multiplicity, K strata, operational/certified negatives, no-op and availability, exact model deployment form and action costs. No post-test waves.
7. Full suite and six archived replays after every gate; commit/push gate reports, changed code, immutable provenance and visualizations. Final output: SHAs, measured counts, training/eval results, budgets used, strong/weak contributions, stop decision.

### Gate verdicts

- `K34_DATA_READY`: adequate replay-verified K3 and K4 development evidence; ready for P21 learning.
- `K34_LIMITED_DATA`: K3/K4 witnesses exist but do not meet strong per-stratum inference thresholds; bounded P21 exploratory analysis only.
- `K4_PHYSICAL_DATA_NOT_ESTABLISHED`: no K4, or insufficient verified data under unchanged robot/teacher/budget; stop and report why (do **not** fabricate K4).
- `K34_METHOD_DEVELOPMENT_SUPPORTED`: trained models show hard-case improvement with honest comparator, scope and calibrated uncertainty.
- `READY_FOR_K34_INDEPENDENT_CONFIRMATION`: model/protocol/checkpoint custody frozen and a separate harder independent plan is demonstrably feasible; **no confirmatory test performed**.
- `NEGATIVE_OR_INCONCLUSIVE`: a legitimate scientific endpoint if evidence does not support the hypothesis.

## 5. Minimal code and repository hygiene

Keep files small and discoverable; reuse existing `bxy_p16`, `bxy_p17`, `bxy_p18`, `bxy_teacher`, `bxy_f1`, `bxy_pmin_collect` functions. Prefer ~4 new focused Python modules plus focused tests and figures over a large duplicate framework. Suggested new files: `bxy_p19_audit.py`, `bxy_p20_k34.py`, `bxy_p21_k34.py`, `bxy_p22_freeze.py`, with `*_viz.py` only as needed. New outputs under `runs/approach_b/bxy_p19_v1` through `bxy_p22_v1` and `visualizations/approach_b/bxy_p20_v1` etc. Never modify old run trees. All experiments must be non-destructive and resume-safe.

## 6. Expected final response from Claude

Return concise but quantitative gate summaries and a **single integrated final table**: verified K0–K4 counts and witnessed repairs, X/Y order and omission evidence, arm-by-arm held-out selection success with uncertainty, unnecessary-repair rates, pairing with DIRECT/uncoupled, candidate availability, CPU/wall use, final SHAs, and the *actual* limitations. Link/report the 2D scene figures and updated methodology. Clearly state whether K4 is truly verified and whether it was learned on held-out roots. Stop after P22.

**Research objective:** execute the originally specified Approach B as far as the unchanged 2D robot and bounded teacher genuinely support it. Realize K3/K4 through verified physics and better curated *development* evidence, not additional model complexity or optimistic labels.
