# G4C-LF-P4 — Operational-negative teacher migration + bounded learning-first calibration

**Execution handoff for Claude Opus 5.5 High · 21 October 2026**  
**Status:** new, expressly versioned experimental-policy amendment and executable stage; NOT a retroactive reinterpretation of older evidence.  
**Intent:** make A/B/C training data feasible to collect, without pretending timed-out planning is a mathematical proof. **Complete only P4.**

## 0. Required reading and controlling facts

Read these completely before editing:

1. `latent_causal_tamp_methodology_v1_7.md` and `latent_causal_tamp_implementation_guide_v1_9.md` (inside the available bundle; locate exact paths rather than assume root copies).
2. `responses-phases/0016_G4C_D2_P1_poc_s.md`, `0017_G4C_D2_P2_certificate_soundness_review.md`, and `0018_G4C_D2_P3a_sector_certificate_results.md` (resolve actual locations).
3. Current Git state and all 6 archived run manifests; inspect existing `g4d_run.py`, `g4c_pilot.py`, `ordered.py`, `skill.py`, `planner.py`, `evaluate.py`, `certificates.py`, `sector_cert.py`, `sector_check.py`, `effects.py`, `sequences.py`, `d2*.py`, `run.py`, tests and actual config keys. Inspect by responsibility, not by inventing nonexistent modules.
4. Any post-0018 report / commit present in the repository. If it materially changes the base, stop and report the discrepancy before applying this stage.

Last user-reported pushed code revision: **`29b459b`**, preceded by report-only **`5122592`**. Treat these as *expected*, not as an instruction to reset or overwrite newer work. P3a: 8 new checker-accepted first-action negatives, one access-based r19 order contrast, **0/3 nontrivial original-task negatives**, 115 saved witness controls with zero contradictions; 247-test regression incomplete (157 passed, 90 not reached), 6 replays passed, regression budget overrun 19.8 CPU-s. **These are previous-stage facts, not results of P4.**

The **specific new authorization** in this P4 handoff is a user-directed change of *training/evaluation label policy for NEW data*. It deliberately departs from Methodology v1.7's former requirement that every binary negative be a proof. Retain v1.7/v1.9's A/B/C scientific and physical architecture; add a separately versioned policy overlay, **do not overwrite** the historical normative documents, freezes or labels. Document this exception and its limits explicitly.

## 1. The decision: operational infeasibility is an admissible NEW teacher label

Let `S0` be the observed initial scene, `r=((object_id,physical_pose_id),...)` an EXACT canonical ordered repair (possibly empty), and `P_B` a fully specified, finite, multi-seed robot-planning protocol with fixed grasp family, planner, per-attempt caps, total budget, safe-retreat rule, and deterministic seed order. Define:

- **VERIFIED_FEASIBLE**: at least one independently validated complete fixed-order relocation + target + SAFE_RETREAT witness. This is an existential positive, regardless of other failed seeds.
- **CERTIFIED_INFEASIBLE**: independent checker accepted a sound certificate at exactly the required ORIGINAL_TARGET, SCENE_TARGET_ONLY, ASSIGNMENT or ORDER scope. This is a proof-based negative.
- **BUDGET_INFEASIBLE**: no complete witness after **every scheduled search attempt required by a completed and unchanged `P_B` has actually been executed**, each reaching an allowed terminal reason. This is a **policy/budget-relative operational negative, NOT a claim that all physical trajectories are impossible**.
- **UNKNOWN**: unrun seeds, global budget preemption, CPU-censored process, crash, external kill, serialization failure, inconsistent state/hash, invalid/ineligible query, unresolved numerical boundary not covered by a completed search protocol, or ambiguous label provenance. Do not train a binary target from it.

Precedence: a valid witness wins over budget failures; a valid positive contradicting a supposedly sound certificate is **FATAL** and must stop with forensic evidence; a partial multi-seed schedule is **UNKNOWN**, not budget-negative. Never call a 4,000-node RRT timeout or 870-s cancellation a *physical impossibility certificate*.

Operational teacher target for a NEW experiment is `Y_B(r;S0,P_B) ∈ {0,1}` **only on complete, eligible, valid runs under the declared protocol**. Keep `Y^*` (existential mathematical feasibility in v1.7) separate: **`Y_B=0` does not establish `Y^*=0`**. Report effects `Δ_B`, omissions and κ as **budget-protocol-relative effects** when a budget-negative participates; only fully proof/witness decided contrasts support the stronger scoped physical claim. Do not use phrases such as “necessary for any possible robot execution” without a certificate.

### 1.1 Evidence schema (new namespace/version, backward-compatible)

Add a versioned overlay such as `teacher_policy_id = "2D-ABC-OPNEG-v1"` and `label_source ∈ {WITNESS,CERTIFICATE,PLANNER_BUDGET,UNRESOLVED}`. Preserve all historical `VERIFIED_FEASIBLE`, `CERTIFIED_INFEASIBLE`, `UNRESOLVED/UNKNOWN` fields and scopes; attach any new operational label in a **new record**, never mutate historical run JSON. Store:

- `policy_id`, `policy_hash`, code/config/profile/action hashes, original root and lineage, query exact physical signature, q/gap/attachment/goal, source and output file hashes.
- `binary_training_label` (1/0/null), `teacher_status`, `label_source`, `proof_scope`, `is_budget_relative`, `reason`, `eligibility`, and a three-state `decided_mask`.
- Every prescribed seed, deterministic grasp/candidate schedule, planned versus executed attempts, planner node limits, per-seed CPU and wall, total elapsed CPU/wall, termination causes, witness/certificate hashes, preemption/kill flags, and all actual planner/skill/relocation/target calls (including in-flight calls separately).
- `J_first`/cost only from the **first complete relocation witness** under a pinned seed/back-end schedule. No arbitrary J=0 for negatives or missing witnesses; `J(empty)=0` only.
- Differentiate `original_task`, `ordered_repair`, `fixed_robot_scene_edit`, `repair_omission`, `robot_start_edit`, `static_endpoint`; neither scene teleports nor nominal-target-path intersections are executable repair witnesses.

**Three distinct projections:** (i) immutable raw attempt ledger, including UNKNOWN; (ii) admitted binary dataset with no UNKNOWN *rows*; (iii) B/C `joint_pool_complete` subset where **every active required z outcome is eligible and decided under the *same* frozen teacher policy**. A partially labelled pool must not enter the exact joint likelihood. Publish admission counts and reasons, not just retained samples.

## 2. Nonnegotiable preserved science and robot invariants

- **No architectural reset.** Keep A: shared unary/pair local factors + ordered GRU task/first-witness-cost, score-difference explanation, Boltzmann over `r`; B: explicit binary `z0,zscene,zrepair,zomit` outcome variables, trainable scene/omission/coupling and prefix pair order potentials, **joint** `E_B(r,z)` with exact bounded-z marginal where possible; C: B's explicit outcomes/couplings + A's GRU order/task/cost. Same shared frozen visual backbone, initial observation, representations, teacher, motion verifier, and split. No classical Hopfield layer or fake latent causal DAG.
- Full finite-width 2D **3R** arm, real link/gripper/attached object collision checks, declared 48 grasp variants, 8×8 finite *resting* cells, continuous robot motion, same numerically verified robot profile and margins. No toy translating-disc results as physical evidence.
- `r` is a **move-once ordered** physical sequence; always restart offline teacher query from S0, never quietly reorder `r`, never substitute teleported/ideal-prefix states for executed witness continuity. Target goal + SAFE_RETREAT is essential. No HOME requirement smuggled in.
- **One-shot live/deployment boundary unchanged:** rank and freeze repair proposals without target feedback; try fixed-order relocation witnesses, commit one, attempt the target **once**; no target-based retry. Multi-seed repeated target outcomes belong to the **offline dataset teacher only**, isolated from online inference.
- Fixed-robot scene edits keep robot q/g/attachment/target and original appearance anchor unchanged, change only eligible declared pose fields. Omissions regenerate the full prefix from S0 with omitted objects still physically present. Joint effects only if all four queries are decided under the SAME policy.
- No leak of source labels, post-move paths, teacher grasp/seed choices, privileged collisions/sweeps, oracle outcome, root/family ID, or post-intervention rendered observations into learner input. Original DINOv2/pose/known-geometry input contract stays.
- Root-level independence: roots/descendants/stored twins stay in the same split; prior sparse pilot and POC_S roots are **development only**, never untouched holdout. Do not select test roots after looking at outcomes.
- Temperatures/λ, analytical endpoint displacement `C_d`, move count, cost supervision, energy terms and sampler correctness do not change by fiat. Feasibility pool losses **exclude** costs; sampling may add frozen `λ_d C_d + λ_q Jhat`; final admissible selection remains lexicographic as v1.7.

## 3. Stage sequence: EXECUTE, not another review

### P4.0 — preflight and preserve (no planner runs)

1. `git status --porcelain=v1`, `git log -4`, `git diff --name-status`, compare HEAD and origin only as safely available. Note two legacy root PDFs were already shown as deleted before P3a; leave those pre-existing deletions untouched. Existing instruction files are user-owned.
2. Read report 0018 and P3a regression logs, all existing teacher schedules / legacy tests. Baseline manifest/source hashes, check six archived replays' paths. Record exact remaining UNKNOWN set and reason categories without relabelling.
3. Audit `skill.plan_skill`'s **4 unresolved connectors** stopping rule and how `SEARCH_LIMIT_PLAN_FAILURES`, `SCHEDULE_COMPLETED_NO_WITNESS`, `CPU_CENSORED` propagate. A fixed budget label must mean completion of **the defined algorithm/schedule**, not a silent early stop or missing seeds. If needed adapt only new wrapper/scheduler logic, preserve historical `skill.py` and old adjudicators.
4. Resolve current CLI/reporter interfaces from code. New modules only if needed; **avoid another 300+-logical-line central script**. Use a short policy module + short runner and tests instead of a second entire planning stack.

### P4.1 — implement v1 teacher policy and deterministic wrapper

1. New standalone policy/config overlay, e.g. `teacher_opneg.toml`, strict allowlisted schema (reject unknown keys) and frozen `policy_hash`. **Never rewrite `config.toml`, `config_v2.toml`, historic POC plans, existing P3a certificates or earlier reports.**
2. One small `operational_teacher.py` (policy and adjudication) and, if necessary, `teacher_pilot.py` (manifest, run guard, collection and figures). Reuse repository's existing process-tree-safe run guard, immutable checkpoint/restart, fixed-order planner adapter, logging and manifest functions. Do not duplicate geometry and planner code.
3. For each eligible root/query: predeclare source state and ordered sequence, deterministic seed list, full per-seed policy (grasp iteration, planner attempts, stops); rerun the **entire ordered relocation + target query** from S0 on each seed if no witness. In particular, a failed target after one relocation witness is not a physical order-negative; for budget-negative, every planned full-sequence attempt must be exhausted according to the operational policy.
4. Collect complete witness whenever found; short-circuit only on verified complete success or sound certificate. A budget-negative requires **all declared attempts completed cleanly**. If a seed is killed externally/censored before its own defined exhaustion, the full label remains UNKNOWN. If the declared inner skill policy stops at four failed connectors, explicitly record that as algorithm termination and **do not imply 48 collision-free connector attempts**.
5. New staged output directory only, e.g. `runs/g4c_lf_p4/`, with separate immutable preflight, policy, attempt ledger, decisions, pool coverage, compute/evidence chart, negative confidence audit, tests/replay result, and sha256 manifest. Use root IDs *for traceability only*, not learner inputs.
6. Frozen new status field `BUDGET_INFEASIBLE` has scope `OPERATIONAL_ONLY:policy_hash`, not `CERTIFIED_INFEASIBLE`. Never feed it into the independent certificate checker. Preserve proof source priority and tamper detection.
7. Policy fields for optional **teacher-label confidence weighting** may be logged, but do **not** conflate weighting with certification; implement baseline weight=1 and an explicit budget-negative downweight ablation hook for later training. No fabricated probability of being physically infeasible.

### P4.2 — bounded tests and regression completion (before physical calibration)

Add exact unit tests (no planner calls unless a separately marked integration test):

- full multi-seed completed → BUDGET_INFEASIBLE; missing last seed, CPU-censored seed, crash, partial timeout → UNKNOWN; full witness on any seed → VERIFIED_FEASIBLE;
- verified positive vs certified negative contradiction → fatal and preserve both records;
- BUDGET_INFEASIBLE never passes a certificate checker and cannot be presented as a mathematical impossibility;
- same endpoints swapped order receive independent schedules and distinct outcomes; one order's success/negative cannot be copied to permutations;
- a saved failed target after a *single* relocation trace is insufficient to label all realizations of that sequence physically infeasible;
- within fixed-robot edits: exact changed field audit; all omission prefixes reconstructed with skipped object kept in scene; no mixed teacher policy in effect/κ or joint z pools;
- candidate and z masks; 0/1/null learner targets; old labels/data byte-identical; no privileged-input leakage; root split; correct first-witness J; safe-retreat required;
- process-tree CPU accounting, kill guard, wall and aggregate caps, in-flight calls, checkpoints, resumed-unit policy, histogram denominators;
- counterfactual operational effects' **scope/interpretation** distinct from proven necessity; no score derived from a budget label is a certificate.

**Finish the P3a regression gate on CURRENT code**: full existing pytest suite plus six archived replays **once** in a process-tree CPU and wall guard, preserving stdout/report and call counters on timeout. This is a new authorized regression budget, not retroactive approval of the 0018 overshoot. If tests fail, fix only in-scope new code (or record a separately justified minimal fix) and rerun affected tests within the budget. If the full gate cannot finish, report `REGRESSION_BLOCKED` and **do not run P4.3 physical calibration**. Never assert tests passed when 90 were never reached.

### P4.3 — small DEVELOPMENT calibration pilot (actual collection, explicitly bounded)

**Purpose:** measure how often budget negatives occur and whether they support complete ordered/explanation pools, *not* claim a dataset is ready. Generate a `pilot_plan.json` BEFORE any teacher call. Use **2 existing independent development lineages only** (choose from `g4c_r00`, `g4c_r19`, or another separately verified sparse pilot lineage with reasons), never held-out/test roots. Include when eligible:

- empty original-target query on one historical `+A` nominal-blocker scene;
- same-endpoint swapped ordered pair including a known witness control;
- one or more fixed-robot eligible singleton edits / one joint edit;
- omission of a repair step, reconstructed and independently adjudicated;
- nuisance/zero-effect control and a first-witness J control.

**No promised quotas.** Count all admissible queries and their actual scopes. **No more than 12 new complete teacher query attempts** (query means one exact r or one exact scene-edit request; per-query seeds are subattempts), with at most 2 lineages and at most 2 nontrivial query families. Every query's full **fixed new search protocol** uses the same seed list and costs; witnessed/certified queries can exit early. The pilot serves protocol calibration; remaining UNKNOWNs are legitimate and reported.

**Numerical authorization FOR THIS PILOT ONLY** (no extrapolation to P3b/POC_F/300-root dataset):

| Quantity | Hard limit |
|---|---|
| Development teacher queries | ≤ 12 |
| Seed list per query | exactly 3 frozen, distinct seeds; record literal values before running |
| Per-seed scheduled planning CPU | ≤ 250 CPU-s (750 across 3 seeds, leaving at least 120 CPU-s before the 870 per-query cancellation threshold) |
| Per-query total CPU guard | cancel by 870 CPU-s; hard ceiling 900 CPU-s |
| Aggregate P4.3 CPU | ≤ 3,600 CPU-s, including coordinator and all child processes |
| Aggregate P4.3 wall | ≤ 7,200 s |
| Per-query wall | ≤ 1,800 s |
| Workers | 1 |
| Planner nodes/connector | 4,000 (historical tested default; preserve actual backend rule) |
| New physical query calls | ≤ 12 outer teacher queries, ≤ 36 seeded full-query attempts; **log inner planner/skill/relocation/target counts**, no unapproved unbounded calls |
| Static admission | ≤ 120 CPU-s (within the 3,600 aggregate) |
| Kill and cancellation | stop BEFORE breaching CPU/wall; global kill → current/unrun queries UNKNOWN, never negative |

This 3-seed/250-CPU protocol is a **calibration setting**, not an empirically validated 'huge budget.' If it is too weak/expensive, measure and propose a stronger production protocol; **do not alter seeds/time/nodes post hoc on these labels**. A legitimate operational negative requires all **three** seed attempts to complete per declared policy; if aggregate/cancellation interferes, mark UNKNOWN. Predeclare failure-terminal taxonomy; success and certified negative may short-circuit.

**Regression budget, separate from P4.3:** ≤ **650 aggregate CPU-s** and ≤ **1,500 wall-s**, one guarded worker, counting pytest subprocesses AND six replay subprocesses. New pure unit tests outside this guarded full run: ≤ 120 CPU-s, no physical planner calls. Preflight/read-only costs logged separately. On reaching limits, stop and report; never silently expand caps.

**Immediate early stops:** (i) any sound positive/certificate contradiction; (ii) code/hash/protocol mismatch; (iii) process-tree budget breach; (iv) repeated exact-query nondeterminism that makes status undecidable; (v) no root with both a valid witnessed positive and any eligible planned contrast after static preflight; (vi) blocked regression; (vii) output corruption / leakage. Preserve partial records, count not-run items and do not overclaim.

### P4.4 — quantitative verdict and handoff (no A/B/C full training yet)

Compute and publish:

1. Three outcome breakdowns: raw attempts (POS/CERT_NEG/BUDGET_NEG/UNKNOWN/NOT_RUN); binary-admitted subset; exact B/C z-complete pools. Breakdown separately for original task, ordered repair, scene edits, omissions and order swaps; include ALL attempted denominators and root counts.
2. Cost: CPU, wall, planner/skill/target/relocation calls (including in-flight), seed completion and fraction reaching guard, cost per *admitted* negative/complete pool, root-level clustering.
3. **Operational label stability**: success-after-earlier-failed-seed incidents, disagreements with any existing sound certificates or stored witness, available held-out repeated-seed checks (if authorized within the fixed budget), and limitations from `max_unresolved_connectors=4`. Do not post hoc change label by adding more seeds to this same protocol.
4. Ordering and effect contrasts: show same-endpoint swap results and `Δ_B^S`, `Δ_B^O`, `κ_B` only when all corresponding outcomes are independently completed under the same policy. Explicitly mark **operational** contrasts vs evidence grounded in sound certificates.
5. One scene-backed PNG at least: full actual articulated 3R scene, grasp/obstacle and physical IDs, original vs proposed order and labeled outcome; no made-up robot paths. A clear `labels_by_source.png` and compute plot; actual recorded GIF only if a trajectory exists. Produce JSON/CSV/manifest/replay-proof audit.
6. Integrity: frozen past files byte-identical, tests/replays results with true denominators, branch/commit, code/config/policy hashes, file sizes, preserved user working tree changes.
7. Gate verdict: `P4_PROTOCOL_IMPLEMENTED_PASS|BLOCKED|FAILED`, `P3A_REGRESSION_CLOSED|NOT_CLOSED`, `P4_CALIBRATION_COLLECTED|PARTIAL|NOT_RUN`, `P4_READY_FOR_G4B_G4E|NOT_READY`. A full learning release is **not** implied by protocol code or a dozen pilot cases.

## 4. Next learning gates: ready-to-run PLAN, not unbounded approval

Use P4's measured label yield to create a named follow-on P5 execution plan, **not to automatically start it**:

1. **G4B** mini exhaustive sampler validation on exact 2–3-object domain: A destination Gibbs, swap, birth/death with correct Hastings and unequal `K_i`; B/C exact bounded-z marginal via stable `logsumexp`, inactive-slot partition invariance, full recomputation equality, finite difference gradients, detailed balance. No model train until correct.
2. **G4C** construct *new* independently split development roots and data, using proof-based negatives whenever cheap and named fixed-budget operational negatives otherwise; use a pool-completeness-aware selection strategy, but preserve attempted / rejected denominator and don't pretend selected roots are unbiased. Interventions catalogued **before** outcomes. A/B/C share ALL common labels, candidates and budgets.
3. **G4E-ABC** smoke learning on tiny fully labelled pools: same shared encoder, local factors, A GRU and cost, B outcome/coupling energy, C hybrid; overfit tiny cases, verify order sensitivity and effect supervision gradients, exact joint objective, leakage protections. Do not replace B/C joint loss with A's sequence-only loss.
4. **G5/G6** separate training, 3 seeds each, matched roots and label provenance, certified-only vs certified+budget-negative training **and held-out evaluation sensitivity**, confidence/coverage and compute match. Select after complete 2D evaluation only. Then G7–G10 remain gated.

**Proposed** production negative policy must be derived from measured P4 yield/false-negative indicators: predeclare larger seed lists and compute caps before any new collection, stratify audit by `WITNESS`, `CERTIFICATE`, `PLANNER_BUDGET`, and make the main paper's inference claims appropriately scoped. Do not claim P4's 3 seeds is “asymptotic proof.” Production train/val/test should be split at the independent-root level **before** descendants; prior r00/r19 pilot evidence is development only.

## 5. Repository, coding, and evidence discipline

- **No historical mutation:** all files in existing `runs/`, reports 0001–0018, original scene, robot and planner source, existing status semantics and hash-bound configs remain unchanged. No rewriting `d2.py` to redefine negatives. Only add new versioned policy/runner/adapter/test/run outputs and minimal CLI wiring based on actual repository interfaces. A separately versioned *science-policy addendum* inside the new report or `teacher_opneg_policy.md` is mandatory to record v1.7's specific changed assumption.
- Each file normally ~120–280 logical lines; ≥300 triggers split/review. Small module and test files are preferred; no new frameworks, package hierarchies, hidden cache databases or duplicated robot stack.
- No training GPU runs, new image backbones, data release, P3b, old POC_F, fresh 300 roots, 3D or hardware in this stage. **Actual bounded P4.3 teacher pilot is authorized only within its numerical envelope.**
- Don't pretend the uploaded reports are live Git state; verify actual repo. Do not revert/stage pre-existing two deleted root PDFs or any untracked instruction bundle. Explicit `git add` only the new P4 files, run evidence and report if repository conditions permit; push non-force and verify origin. If unexpected tracked changes could be accidentally included, stop the commit and leave evidence on disk. Run may still proceed if safe and source scope isolated, unless input integrity is compromised.
- Fail closed on incompatible histories/hashes, incomplete backups, invalid proof, prior physical witness contradicted by an operational negative, or a lost provenance ledger.

## 6. Mandatory final numbered report (next unused index; do not overwrite 0019 if it exists)

The report must give: actual Git HEAD/remote before and after, files created/changed, exact command and exit codes, full test count, six replay statuses, every budget and actual usage, every operational-negative decision with evidence/source status, mixed-policy exclusion safeguards, per-family and full denominators, example proof/witness/timeout case, loss-facing masks, figure links, static-vs-full-robot statement, resulting B/C pool completeness, stage PASS/PARTIAL/BLOCKED/FAIL, and the next precisely costed training-first authorization recommendation.

Finish code + regression + small data pilot + new report **within this stage**, then **STOP**. Do not wait for permission at every implementation substep. Do not automatically start production collection or training.
