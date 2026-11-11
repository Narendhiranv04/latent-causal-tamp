# G4C-D2-P1 — Witness-First 2D Dataset: Small Proof-of-Concept Collection

**Project:** Latent Causal Infeasibility for Long-Horizon TAMP  
**Stage:** `G4C-D2-P1` / `POC_S` only  
**Task for implementer:** Freeze a source-checked execution plan, implement the smallest collection/judging adapters, run an explicitly authorized small witness-first experiment, independently audit every outcome, and **STOP**.  
**Scientific question:** Can we reproducibly construct **robot-meaningful, diverse, completely decided causal-repair examples** by starting with a verified feasible target action, adding obstacles along its complete recorded robot sweep, and requiring proof-carrying feasibility labels?  
**This is not:** a guarantee that blocking a sampled trajectory makes the target infeasible, a license to relabel UNKNOWN, a production dataset, model training, a 3D/hardware demonstration, or a replacement for earlier G4C results.

## 0. Source authority, actual baseline, and authorization

Read this entire file before modifying anything. Inspect the actual repository's instructions, tree, latest commit, remote state, working tree, active config/profile, and stored reports; do not rely on remembered module APIs. In particular read:

- `responses-phases/0015_G4C_D2_precheck.md`, corresponding to reported commit **`5e87559e0a1367149964ddd1ce15879b16d04f8c`** and saved `runs/g4c_d2_precheck/` artifacts, particularly `source_audit.json`, `protocol_proposal.md`, `precheck_variants.json`, `precheck_queries.json`, `precheck_result.json`, `budget_request.json`, `manifest.json` and `precheck_overview.png`.
- `responses-phases/0014_G4C_pilot_collection.md` and historical `0011`–`0013`; addenda A1 and A2; Methodology v1.7 / Guide v1.9 if accessible locally (untracked user bundle is **read-only**), plus original v1.6/v1.8 physics and negative-certificate rules.
- `d2.py`, `d2_precheck.py`, `g4c.py`, `g4c_pilot.py`, `g4d_run.py`, `g4d_gate.py`, `ordered.py`, `verify.py`, `evaluate.py`, `motion.py`, `effects.py`, `certificates.py`, `data.py`, scene/robot/planner/skill, `run.py` and existing tests, after verifying their real paths.

**Reported baseline (must be verified):** precheck PASS, 193 passing tests, six archived runs replay. Three archived feasible target witnesses (97/208/29 segments) passed full-body replay, but comprise only **two independent lineages** (`g4c_r00` and the shared `G2_D1` lineage for `g4d_R0/R1`). A total of 195 obstacle-placement attempts gave 27 static/nested previews. **Every newly created target/repair/intervention result remains `NOT_RUN`** in P0. Earlier G4C-P1 pilot is historically 59 units: 13 POS / 26 NEG / 20 UNKNOWN. Those remain unmodified.

**Execution authorization contract:** The researcher is being presented the exact `POC_S` limits below, drawn from the report's *proposal*. A request to prepare this instruction file **alone** must not be mistaken for authorization to run teacher searches. The implementer may execute the collection only when the researcher submits a message **explicitly approving `POC_S` and all the numerical limits in §1**, for example by pasting the accompanying kickoff prompt containing that statement. If approval is absent or ambiguous, complete source inspection and static preflight only, request exact approval, and STOP before any fresh IK/teacher/planner search.

**Preserve:** every prior stage report and run; original frozen `runs/g4c_preflight/plan.json`, `runs/g4c_pilot/` and `runs/g4c_d2_precheck/`; historical config bytes and hashes; negative certificate scopes; all user-owned untracked PDFs, prompts and A/B/C guide sources; no force-push. New artifacts go to **`runs/g4c_d2_poc_s/`** only. No automatic full-tier run (`POC_F`), no remaining 15 original G4C roots, no neural training or G4E/G5/G6, and no 3D/hardware.

## 1. Pinned SMALL-tier scope and hard numeric ceilings

These figures are from **report 0015's proposed `POC_S`**, not empirical outcomes or historical authorization:

| Field | Exact proposed `POC_S` value |
|---|---|
| **Base families** | `g4d_R1` (`G2_D1` family) and `g4c_r00` (independent family) |
| **Six variants per base** | `base`, `+A`, `+A+B`, `+A+S`, `+G`, `+N` |
| **Frozen teacher evidence units** | **68 total = 50 ordered + 16 scene-target-only + 2 robot-start** |
| **Fresh base-witness attempts** | **At most 2**, separate from the 68 frozen variant units, with at most one target evaluation per attempt. Explicitly account for them in CPU/target caps and the attempt ledger. These are diversity diagnostics; do **not** silently insert their descendants into the 68 units. |
| Per-teacher-unit CPU | **900 s**, enforce cancellation trigger **870 s**; 30 s margin |
| Aggregate CPU | **18,000 s** across all new work in this stage, including coordinator and fresh-base attempts; reserve margin for orchestration |
| Workers | **1**; pin OMP/OpenBLAS/MKL/NumExpr threads to 1 |
| Per-unit wall guard | **1,800 s** |
| Aggregate wall guard | **23,400 s** |
| Planner configuration | **4,000 motion nodes**, preserve tested grasp/action/path parameters; no silent search enhancement |
| Total relocation-skill calls | **46 maximum** |
| Total target evaluations | **70 maximum**, including both optional fresh-base-witness attempts |
| New root-construction attempts | **2 maximum** (the fresh-base attempts); **0** reshuffles/replacements of the two archived families or frozen preview variants |
| Resume | Resume never-started units only, with unchanged source hashes, plan hash, global deadline and remaining budget; never repeat ambiguous STARTED units |

### Important count/admission safeguard

The reported `50` ordered units are *queries*, not necessarily `50` relocation-planner invocations; some are empty, statically certified negatives, or otherwise do not need a relocation call. The reported `46` relocation cap and `70` target cap must be verified against the exact derived unit schedule and worst-case call bookkeeping **before** running. Do not assume a particular unit's future result or planner-call count to make the cap fit. If the plan cannot be safely admitted under these caps, **BLOCK before collection** and request an amended explicit authorization—do not skip evidence units, weaken the schedule, miscount calls or run over cap. Follow the existing guard's pre-invocation admission and charging semantics.

**Do not allocate the aggregate budget independently to each worker or each phase.** Use one guarded overall ledger, process-tree CPU accounting and a global wall deadline; stop cleanly when any ceiling is approached. Record overshoot, cancellation, partially saved checkpoints, and NOT_RUN units honestly.

The published 391 CPU-second central estimate and 14,340 CPU-second high estimate are **uncertain planning estimates**. The cap of 18,000 seconds is a hard ceiling, not expected consumption.

## 2. Scientific semantics: what is constructed and what is proved

### 2.1 Feasible **base witness** first

Start from each of the two archived **complete target-only successes**. Verify their bytes/lineage, initial robot configuration, target pickup and placement, goal and `GOAL_AND_SAFE_RETREAT`, robot joint continuity, gripper opening, attachment state, complete collidable robot + carried-disc geometry, and independent conservative collision replay. An archived successful witness is a *base-family fact only*, not a new result for an obstacle-added variant.

The optional **two fresh base attempts** must be predeclared (seed, target/goal geometry sampling rule, initial robot state, action/profile) **before** their outcomes are known; run them only under §1 authorization. Their new base trajectory, if found and independently rechecked, is a verified witness but does not make untested inserted-obstacle variants positive. If a base attempt is unsuccessful, it is `UNKNOWN/NO_BASE_WITNESS`, not a new infeasibility label. Keep attempts and rejections; do not cherry-pick successful candidates with unreported retries. Respect the family-lineage split.

### 2.2 Constructive obstacle insertion and nested variants

For each base, reuse the **exact precheck-derived, deterministic** cell/role rules, source-bound IDs and candidate geometry from P0. Construct six variants: original base; one nominal-sweep obstacle A; A+B; A plus staging-slot occupant S; goal occupant G; harmless/nuisance N. In all variants preserve the same target/goal, robot q0, gripper state and object identity; existing objects never disappear or clone. Every inserted disc must rest on a legal 8×8 cell, avoid initial robot/body collision, overlap or forbidden support, and preserve all existing objects.

The construction diagnostic checks whether inserted obstacles collide with **the archived specific nominal full-robot trajectory**, including arm links, base/housings, palm, rail, fingers and carried target. Record body pairs, path stage and earliest collision segment, and whether a placement is nominally clear. **This must never be used as an oracle task-feasibility label or a learner feature.**

When an obstacle is introduced in A then B, all predecessor obstacles stay in the scene. Constructed `+A+S` is specifically intended to provide a possible **PLACE-scope order contrast**: when S initially occupies A's proposed staging destination, compare `S→Q; A→P` with `A→P; S→Q` at the **same final physical endpoints**. Do not declare the pair decided until the correct order has a full witness and the reverse has a matching, checked order-wide negative certificate; otherwise UNKNOWN.

### 2.3 Fixed candidate catalogue; no outcome-based pruning

Rebuild the exact unit catalogue from P0 (`precheck_queries.json`), verify identity hashes and construct `68` unit entries in a **frozen** order, before any teacher outcomes. Include empty repair, specified single actions, alternate displacement cells, order reversals, omission remainders, fixed-q scene edits and one robot-start variant per base. Respect canonical sequence grammar, one move/object, no target moves, nonstay supported cells, current move cap, exact robot state identity and scene-view appearance anchor.

**All three A/B/C model arms must have equal raw-information access.** The explicit B/C `z0`, eligible fixed-robot scene `zS`, repair `zR` and omission `zO[t]` variables are **typed views of the same independently checked labels**, not separate privileged teachers. Use the P0 frozen catalogue/layout and require at most **8 active binary slots**. No changed query catalogue after seeing results; no inactive-slot multiplicity; B/C complete pool requires **every active outcome for every declared sequence decided**. `substantive_pool` additionally requires at least two decided nonempty repairs, including a witnessed positive. Never count a trivial one-sequence empty-only pool as substantive.

### 2.4 Evaluate labels independently—never via a blocked nominal path

Each teacher unit restarts from its **own frozen initial scene** and exact initial robot joints/gripper/attachment. Use the existing fixed-order verifier to evaluate the **specified** relocation order; the backend may choose permitted grasps and continuous trajectories, but may **not** permute actions. A candidate with complete relocation witness is evaluated for the target action from the **achieved final robot and scene state**, with GOAL_AND_SAFE_RETREAT. An empty repair runs the target directly. Scene interventions change only listed object poses in a clone; robot q, gripper, attachment, task and original appearance anchor remain fixed; test target-only feasibility. Omission queries must be **rerun independently** and return omitted objects to their original stay poses, preserving remaining action order.

Evidence labels:

- **POSITIVE:** a complete independently rechecked witness to the required outcome (ordered relocation sequence **plus original target + safe retreat**, or a target-only scene/start query as appropriate). Verified alternative target trajectory **after insertion** is `POSITIVE` and may be additionally tagged `REROUTABLE_POSITIVE` if it avoids the originally obstructed nominal witness.
- **NEGATIVE:** an independently accepted **sound certificate** whose claim scope covers the full relevant ordered query/task property under the current 48-grasp and continuous robot-motion model. Existing GOAL_OVERLAP, STATIC_ENDPOINT_INVALID, verified FIRST_MOVER/ORDER_FIRST_ACTION etc. remain valid only in their actual checker-accepted scopes.
- **UNKNOWN:** every unproved case: finite IK/path search exhaustion, timeout/cancel, incomplete connector search, “all attempted pairs blocked” without a sound **full-domain** certificate, missing target witness after completed relocations, partial execution and result/checkpoint ambiguity.
- **CONTRADICTION:** independently valid positive witness *and* accepted contradictory full-scope negative: fail closed, quarantine, investigate.

**Crucial:** 4,000 motion nodes, 48 grasps, or 10,000 hypothetical search steps cannot turn no-solution-found into an infeasibility proof. Nor can the fact that the initial recorded target path collides. Do not implement a new `ALL_CONNECTORS_BLOCKED` or C-space separation certificate in this POC without a **separately requested** soundness review and explicit authorization. Do not silently change physics, contact rules, allowed grasps or negative scopes to obtain fewer unknowns.

### 2.5 First-witness travel cost and one-shot boundary

For each **first complete relocation witness**, record measured normalized **joint travel** over all relocation and inter-relocation segments, including necessary transitions, *excluding* the original target action, and record endpoint displacement separately. Save witness hashes, start/end joints and normalized joint ranges. A valid relocation cost can exist even when target evaluation is unknown or negative. Empty repair has exactly zero relocation cost. Never use a target-selected cheapest successful trace as the training cost target.

Offline teacher may test many candidates. **No target feedback to the learned proposer** (which does not exist in P1), no hidden target trajectory or collision diagnostic in `data.learner_tensors_v2`. Do not treat offline teacher retries as the permitted online one-shot deployment policy. No trained EBM or sampler-generated execution is part of this POC.

## 3. Code responsibilities: minimum delta from P0

Inspect real source and reuse existing modules; resist copying the teacher. Only add narrowly scoped functionality if missing:

1. **D2 POC finalization/admission:** build a separate `POC_S` immutable final execution plan from exactly P0's declared variants and queries, bind P0 source manifest and witnessed base hashes, explicit user authorization, per-unit identifiers/seeds and all ceilings; dry-run validate each unit with `g4d_run.unit_scene` or the closest actual equivalent; reject schema mismatches with a clear error. Plan must be hashed before collection. Preserve the P0 precheck previews byte-for-byte.
2. **Guarded orchestration adapter:** route the 68 units through the existing `g4d_run.run_collection` (or actual tested analog), preserving atomic checkpoints and independent rechecking; if new fresh-base attempt dispatch is required, subject it to the same global CPU/call counters/wall guard and separate attempt ledger. Do not produce two disconnected budgets or silently replace failed bases. Any fresh-base motion can run only after budget admission, source identity and tests pass.
3. **Independent evidence judge:** reconstruct each claim from checkpoints; rerun checker on negatives and verify complete witnesses, continuity/achieved poses, first-witness cost and exact invocation state on positives. Derive root no-repair outcomes, eligible scene-effect labels and omission deltas only from **decided pairs**. Report interaction/nonadditivity only when all compared sides are decided; UNKNOWN makes the corresponding effect masked. Detect conflicting evidence. Compute complete/substantive B/C pool status using exact active masks and all frozen declared query links. **No retraining, no rerunning failed units from the judge.**
4. **Visualization/report:** new 2D figures with full robot at q0, archived base trajectory, inserted blockers, separately overlaid recorded successful alternative/repair paths when these exist, rejected/infeasible markers only with checked certificates, UNKNOWN/NOT_RUN clearly labeled. Visuals must not imply an impossible path from a failed search or show imagined trajectories as verified. Show nominal path and alternative witness in different visual styles with an explicit legend; distinguish ghost destinations and achieved poses.

Prefer a single thin D2 POC module or two short, focused files; keep typical logical lengths near 120–280, >300 review trigger. Use existing `run.py` dispatcher with minimal new commands. No generic data framework, new orchestration scheduler, duplicated certificate checker or speculative 3D data stack. Do not refactor `verify.py`/`skill.py` merely for line-count cosmetics. Make JSON/NPZ records deterministic, source-hashed and auditable.

## 4. Exact implementation order and pre-run hard STOP checks

### Phase 0 — baseline and immutable-source audit

- Verify git branch/HEAD/current changes/remote; do not reset a user-modified tree. Verify P0 report and hashes; source witness lineage and independent replay; historic G4D, G4B, G4C-P0/P1 artifacts and frozen plan/config SHA-256; existing prior tests/replays.
- Detect any pre-existing D2-P1 implementation. Reconcile safely instead of overwriting.
- Inspect predeclared P0 query counts and robot/state hashes; **resolve discrepancies by STOP + written explanation**, not post-hoc changing candidates.

### Phase 1 — static finalization and dry-run tests (zero fresh teacher calls)

- Construct exactly 2 families × 6 variants. Verify 68 ordered/scene/start queries = 50/16/2 with exact IDs, sequence signatures, linked outcome views and lineage IDs. All inserted obstacles legal at q0; frozen catalogue not contingent on teacher labels. Allow **two separately predeclared** fresh-base diagnostic attempts max.
- Bind numerical authorization, plan hash, manifest, all source files, profiles and initial witness hashes. Verify call ceilings against actual runnable plan and reject if inconsistent.
- Add tests using temporary dirs/mocks that fail closed on wrong budget, changed parent/precheck hash, wrong lineage, mutated robot state, unit count 67/69, extra `POC_F` variant, leaked teacher data, noncanonical sequence, changed catalogue after label lookup, invalid negative scope, missing target invocation, corrupted cost, over-budget, cancellation or ambiguous resume.
- Dry-run judge on a synthetic ledger with positive, certified negative, unknown and contradiction cases; ensure UNKNOWN is not dropped and substantive complete-pool status is computed correctly. Run existing suite and required replay gate **before** collection. Count regression planner calls separately.
- If this phase or approval fails, report `G4C_D2_P1_BLOCKED_PREFLIGHT` and STOP. No budget-consuming teacher calls to “see if it works”.

### Phase 2 — only after explicit budget approval and Phase 1 PASS

1. Write separate immutable authorization and **final** plan; compute/configure global CPU and wall deadline, margin and per-call counters.
2. Re-verify code hashes and plan immediately before work. Execute at most **two** fresh-base witness diagnostics under the same budget with predetermined seed/config. Record independent base witness or UNKNOWN; do not expand the frozen 68 units.
3. Execute the **exactly 68** declared teacher units in frozen order using guarded single-worker run; checkpoint each completed unit atomically. Respect source hashes, per-invocation and per-unit costs, aggregate caps and global wall deadline. A unit that cannot start due to exhausted admission is `NOT_RUN_BUDGET`; a cancellable unfinished unit is UNKNOWN. Abort safely on any enforcement failure or contradiction.
4. When complete, independently rebuild and judge saved checkpoints (no new teacher calls); preserve the entire attempt ledger. Verify original archival checksums again.
5. Rerun the full regression suite and all six archived replays, writing reports only to new scratch/output paths. Report all planner calls separately: fresh-base, POC ordered-relocation, target-only, HOME diagnostics and historical test calls.

### Phase 3 — evaluation and reporting, **not** model training

Report the following, all with clear denominators:

- 68 planned / attempted / completed / not-run; all 50 ordered, 16 scene, 2 robot-start outcomes **POSITIVE / NEGATIVE / UNKNOWN / NOT_RUN**, plus any separate fresh-base diagnostics.
- Coverage: original targets still succeed vs verified reroutable success vs certified task infeasibility; collisions with nominal base path but unknown task; any no-repair outcomes that have sound nontrivial cause evidence.
- Positive repair witnesses by move count (0,1,2,3), destination alternatives, **same-endpoint ordered contrasts** (positive + certified bad order), first-witness robot joint travel versus endpoint distance, objective cost scatter; count both ordinary final states and genuinely robot-executable ones.
- Scene interventions: singleton, joint, nuisance, robot-start comparisons; exact changed-field eligibility, decided denominators, zero/nonzero measured effects; repair omissions and measured nonadditivity (no claims where a side UNKNOWN).
- **B/C pool statistics**: each full frozen pool's declared active slots, decided vs unknown, pool complete status and substantive status. Report **complete substantive pools separately** from trivial complete pools. Reuse raw information for A/B/C, no split leakage.
- Certificate breakdown by reason and exact scope; the share of easy GOAL_OVERLAP/static negatives versus physically interesting access/order negatives. Never inflate “nontrivial” counts with these easy cases.
- Complete-label yield from several perspectives: decided units / all attempted units; fully decided repair catalogue pools / attempted pools; **substantive** fully decided B/C pools / attempted substantive pools; number of lineages released; clear released-vs-rejected counts and reasons. Do not suppress unknown raw attempts or shrink a pool after seeing outcomes.
- CPU/unit distribution and tail, total CPU/wall, call caps, cancellations, provenance checks, number of fresh-base attempts/successes and cost to obtain one usable complete pool.
- Failure-mode analysis: no path found vs valid impossibility proof, access limitations, counterexample where obstacle blocks nominal trajectory yet target succeeds by alternative route, and any explicit unachieved acceptance requirements.

## 5. Six required proof-of-concept questions (each MET / NOT_MET / UNAVAILABLE)

Independently report each, with direct evidence IDs rather than optimistic construction intent:

**Q1. Verified bases:** Both archived base-family target witnesses replay with complete full-arm and safe-retreat checks; independently summarize any newly attempted bases. No inflated independence for G4D R0/R1 siblings.

**Q2. Sound blocked target:** At least one inserted-obstacle variant has a **full-scope certified target-only negative**, ideally **nontrivial** (not merely a goal occupant). If only `+G` gives a target-negative, say `TRIVIAL_ONLY`; do not claim a meaningful swept-body-induced infeasibility.

**Q3. Corrective recovery:** On the same *certified blocked root*, an actual complete **nonempty relocation plus target + safe retreat** witness exists. A hypothetical scene edit alone does not satisfy this. If it is absent, NOT_MET.

**Q4. Ordering dependency:** At least one pair of identical-endpoint repairs differs only in order, with one fully witnessed POSITIVE and the opposite full-order certified NEGATIVE, ideally in `+A+S`. If one side is UNKNOWN, NOT_MET.

**Q5. Fully supervised B/C:** At least one **substantive** fully decided B/C pool (at least two nonempty decided repairs, one positive, all active z outcomes decided) from the frozen catalogue. An empty-only pool is trivial and does not satisfy Q5.

**Q6. Transparent construction/evidence audit:** Every base attempt, insertion, variant, unit, witness, certificate, unknown, mask and rejection is traceable to source hashes, original robot/goal profile, cost and CPU limits. Complete labels on accepted examples must be sound; overall collection **need not** be 100% decided to pass the operational collection gate. Report completeness honestly.

Do not reinterpret failures as passes. Distinguish:
- **`G4C_D2_P1_COLLECT_COMPLETE`**: all 68 units completed/accurately adjudicated within limits (scientific Q1–Q6 may still be NOT_MET).
- **`G4C_D2_P1_COLLECT_PARTIAL`**: budget/guard/not-run prevented all units, with no enforcement failure and all raw attempted evidence preserved.
- **`G4C_D2_P1_BLOCKED`**: required plan/hashes/authorization/preflight missing; no collection.
- **`G4C_D2_P1_FAILED`**: integrity violation, unsound certificate, contradiction, unauthorized scope or uncontained overshoot.

No `DATASET_READY` claim follows automatically from this POC. The two-family POC is a **development feasibility study**, not a root-disjoint train/validation/test set. If no substantive complete pools emerge, show the exact blockers and propose a new *separately approved* protocol/certificate study; never cherry-pick by omitting declared hard queries.

## 6. Deliverables, figures, tests and STOP

After run, create **new** artifacts under `runs/g4c_d2_poc_s/` (names may conform to existing conventions):

- `source_audit.json`: HEAD, remote, working-tree exceptions, version/profile hashes and archived evidence validation.
- `authorization.json`: explicit source of **numerical user approval**, 68-unit scope, 2 fresh-base attempts maximum, all call/CPU/wall caps.
- `final_plan.json`: stable hash, parent P0 source identity, 68 exact units and fresh-base diagnostics, source binding, seeds and split/lineage metadata.
- `construction_attempts.jsonl`, `unit_evidence.json`/per-unit checkpoints, `ledger.json`, `manifest.json`: preserve EVERY attempt, raw status and recheck.
- `poc_result.json`, `per_root_coverage.json`, `bc_pool_coverage.json`, `certificate_breakdown.json`, `compute_summary.json`, `comparison_effects.json`: measured coverage, with UNKNOWN/NOT_RUN denominators and all six question verdicts.
- `A_base_and_blockers.png`: archived verified base motions, generated obstacle variants and nominal-sweep diagnostics.
- `B_outcomes_by_variant.png`: POS/NEG/UNKNOWN/NOT_RUN across 12 variants (2 families × 6).
- `C_order_and_repair_evidence.png`: **real** paths/witnesses and independently checked scopes only, not invented animation.
- `D_interventions_and_bc_pools.png`: original/edited state comparisons, label masks and substantive completeness.
- `E_compute_and_cost.png`: CPU/call accounting and C_d vs first-witness J (only decided witnesses).
- A next unused **numbered stage report**, likely `responses-phases/0016_G4C_D2_P1_poc_s.md` **after checking existing repo**, documenting exact commands/exit codes, code diff/line counts, run envelope, hashes, replays, 68-unit disposition, six acceptance questions, weaknesses and future options.

Write concise tests for exact plan identity, no relabeling or privileged-feature leakage, failure-safe budget/attempt counting, independent judge checking, active z masks, archived-hash unchanged, all-cases denominator and figure provenance. Count no new neural training. Keep primary protocol as `INITIAL_SCENE_ORDERED_ONE_SHOT_V2` and D2 dataset protocol as a separately versioned construction mode.

**Final mandatory STOP:** After producing the report and code/tests, stop. **Do not** run `POC_F` / 194 units, finish old 15 G4C roots, change certificate semantics, mass-generate 300 roots, train A/B/C, or begin 3D/hardware. Preserve user-owned untracked files. Follow existing repo Git workflow, do not force-push, and report actual commit/push success honestly. If unable to push, say so.
