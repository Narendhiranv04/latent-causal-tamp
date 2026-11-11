# G4C-P0 — 2D A/B/C Data-Readiness Plan and Preflight (NO COLLECTION)

**Prepared 20 October 2026.** Execution contract for Claude Opus 5.5 High.

**Current achieved stages:** G4D PASS (`eb4e661aaaeb90a76cc02bb66d77cbb4a9567303`, report `responses-phases/0011_G4D_corrections_and_collection.md`) and G4B PASS (`84f277d1f26307d5daea9c7a61d94cb4d8768339`, report `responses-phases/0012_G4B_sampler_exact.md`). Source/report information is user-supplied; independently verify current local branch/HEAD and preserved test evidence at start. G4B reported **157 passing tests, six archived replays**, exact 13/29 repair-state examples and 292 joint repair–outcome entries; these are **synthetic-sampler mathematics, not learner/robot-performance evidence**.

**Authority:** Proposed scientific design in `latent_causal_tamp_methodology_v1_7.md` and proposed implementation/data gate in `latent_causal_tamp_implementation_guide_v1_9.md` (find actual copies; they may be untracked). For current achieved milestones, trust the **newer reports 0011 and 0012**, not the superseded paragraphs in v1.9 that still say G4D is blocked. Read repo instructions, addenda A1/A2, all relevant G4D and G4B code, tests and evidence. Do not silently edit old versions or archived reports.

## 0. Stage boundary — the only deliverable

Create a **source- and config-hashed, immutable candidate 20-root G4C DEVELOPMENT DATA-COLLECTION PLAN**, plus a bounded plan validator, no-planner coverage-analysis tooling, preliminary (NOT_RUN) visualizations and a precise **CPU/call/budget authorization request**. Then STOP.

**Do not collect or relabel any teacher samples in this pass.** No fresh planner/skill/target/certificate search; no neural networks, optimizer training, new large roots, 300-root collection, 3D, hardware, or G4E. The historical regression suite may invoke its *existing* planned robot calls; disclose those separately. This preflight is **not G4C PASS**: it freezes prerequisites for a later **G4C-COLLECT** run, which requires independent explicit authorization of numeric limits.

If a fully compatible committed plan already exists, validate/adapt rather than overwrite it. If essential budget-policy values or geometrically constructible roots are missing, mark BLOCKED/PENDING as appropriate, record gaps, and never invent a positive outcome.

## 1. Baseline audit (before editing)

1. Check `git status`, branch, `HEAD`, `origin/main`, remote state, pending untracked instructions/PDFs and current configs. Do not reset, fetch-overwrite or clean any user files. Compare to the reported G4B hash; if HEAD differs, investigate before changing anything.
2. Read all authoritative records and inspect real modules. In particular: `scene.py`, `sequences.py`, `effects.py`, `ordered.py`, `verify.py`, `certificates.py`, `g4d_run.py`, `g4d_gate.py`, `legacy.py`, `sampler.py`, teacher guard / runner, visualization, config and current tests. Discover filenames instead of assuming.
3. Reconcile frozen historical evidence without fresh teacher calls: G4D R4 order contrast, R2 intervention pairs, R4 omission effects, first V2 J witnesses; R2 chain UNKNOWN; R5 baseline UNKNOWN; R1 robot-state difference zero. G4A `NOT_READY_TO_SCALE` remains historic and unchanged.
4. Validate G4B synthetic scope: exact conditional sampler and ≤8-active-outcome marginal. Record that a full `(r,z)` MCMC implementation is **not** present and not required for G4C. Do not use synthetic G4B distributions as supervision.
5. Map the smallest existing APIs needed to construct roots, predeclare queries, validate physical candidates, compare static scenes and store schema/provenance. Avoid refactoring working 3R geometry or both >300-line historical modules merely for style.

## 2. What G4C needs to prove scientifically

Make one **common independently generated dataset** suitable for a fair future 2D comparison:

- **A / LOCAL-SEQUENCE:** full ordered-repair labels, empty-repair labels, static unary/pair compatibility, intervention and omission differences, first relocation-witness joint travel.
- **B / JOINT-CAUSAL:** in addition, explicit **named outcome-variable** labels with complete binary/mask metadata under frozen intervention catalogues: `z0` for empty/no-repair target, `z_scene[q]` for eligible fixed-robot scene substitutions, `z_repair` for the given exact ordered repair, and `z_omit[t]` for each predeclared omitted-action proposal. These represent **feasibility outcomes**, not learned-oracle causal-edge truths.
- **C / HYBRID-JOINT:** exactly the same data and typed outcome schema as B; its GRU is a future model component. **Do not build or train the GRU now.**

No model gets privileged post-intervention outcomes, teacher trajectories, labels, certificate verdicts, root IDs or random teacher seeds as inference inputs. Outcomes are targets only. Normalized numerical robot geometry, initial robot `q/g/attachment`, supplied shapes/poses and the frozen initial appearance anchor remain available.

**Scientific caution:** a repaired scene can be feasible after instantaneous pose substitution while the robot cannot execute the corresponding relocation. Diagnose scene-only effects and full ordered execution separately. Independently record both, never merge labels by convenience. Preserve `UNKNOWN` and *eligibility* masks.

## 3. Fixed collection interface — records and invariants

Keep `INITIAL_SCENE_ORDERED_ONE_SHOT_V2` execution semantics. New dataset version: `2D-ABC-v1`. A collection root has immutable original `S0` and action/goal/protocol/profile/candidate-domain hash; all sibling scenes, pose interventions, query catalogues, sequences, costs, renders and outcomes link to it.

Predeclare **before any outcomes**:

1. the root construction intent, random seed, original scene, target goal, initial arm joints/gripper/attachment, grasp family, finite supported candidate cells and hash;
2. a finite ordered-sequence pool: `[]`, an explicitly enumerated set of object/destination candidates, same-endpoint swapped orders where permitted, alternative destinations, valid nonparticipants, and deliberate static negatives, all with immutable signatures;
3. finite **fixed-robot eligible scene edits**, including no-change/nuisance, singletons, chosen joint edits and different destinations when eligible; hold `q0/g0/attachment`, task, appearance-anchor hash and every other object fixed;
4. omission requests defined by deleting actions from a canonical repair, preserving other actions' order and recomputing all prefixes; omitted objects remain at original stay poses;
5. the B/C *meaningful* explanation catalogue and deterministic active/inactive `z` mask before outcomes, capped by the G4B **≤8 active** limit (including baseline/repair/omissions/scene fields as appropriate). Select a bounded subcatalogue by a predetermined geometric/identity-invariant rule **before** oracle outcomes, never by successful-case hindsight;
6. clearly separated teacher target-only and fixed-order repair evaluation schedules; certificate scope, safe-retreat policy, first-relocation-witness cost, and how rerenders reuse a fixed learner appearance anchor.

Schema must distinguish `root_id` (split metadata) from `query_id`, `ordered_signature`, `scene_edit_id`, `omission_id`, `candidate_id`, `static_status`, `ordered_feasibility_status`, `target_status`, `certificate_scope`, `witness_exists`, `J_first_label_mask`, `outcome_active_mask`, `outcome_decided_mask`, `scene_pair_eligible_mask`, `effect_decided_mask` and failure/budget provenance.

Label semantics: **POSITIVE** only with a complete independent relocation+target+safe-retreat witness (or independently decided target-only outcome for a scene edit). **NEGATIVE** only with sound scope-covering certificate. **UNKNOWN** on any incomplete search, finite timeout or unverified interval. Negative for an assignment is allowed to transfer to an order only if independent checker revalidates scope. Omission labels must be separately checked, never inferred from the original positive. A cost label is permitted when the first complete relocation witness exists even if the target remains UNKNOWN/NEGATIVE; never reselect a cost witness based on target success. Empty repair cost = exactly zero.

**No prompt-only promises**: add deterministic code/unit tests to validate signatures, counterfactual changed-field audits, mask consistency, split family isolation, privileged loader allowlists and budget admission *without planner calls*.

## 4. Predeclare 20 independent DEVELOPMENT roots, not a cherry-picked success set

Plan 20 *new* independent root seeds or semantically distinct initial scenes, grouped by origin before any one-edit variants. Do not count related twins, trajectory alternatives or renderings as new roots. Do not promote historical G4A/G4D fixtures to independent future held-out roots; they can remain named **development controls** only.

Starting construction **intent** mixture (adjust only with explicit recorded reason **before** evidence):

- Six `J0`-style initially-feasible/no-repair controls, also hosting nuisance edits when eligible.
- Four `J1/J2`-style direct-blocker or order/access cases, with planned same-endpoint reversals and certified first-action exclusion opportunities.
- Four `J3`-style alternative-destination and occupied-staging cases, with explicit stay-versus-move dependencies.
- Four `J4/J7`-style higher-order (2–3 relocation) or displacement-versus-arm-travel contrasts, with move cap and actual construction feasibility audited.
- Two `J5/J6/J8/J9`-style controls or miniature exact checks (nuisance/harmful, robot-start, unknown, tiny exhaustible domain). Log which coverage categories each root is intended to support; a root may legitimately support multiple categories.

`J0`–`J9` are **construction questions**, not labels or automatic feasibility claims. Include all families in the plan and a `CONSTRUCTION_UNAVAILABLE` route if an intended fixture cannot be built under the actual full 3R robot, 48 permitted grasps and no-lift supported transport rules. Do not cheat by deleting robot links, altering tolerances, declaring a timeout negative or preselecting a lucky trajectory after inspecting outcomes.

Predeclare per-root *attempt ceilings* (number of attempted seed/scenes, candidate endpoints and ordered sequences, fixed-robot edits, omission probes, max teacher and target evaluations), so expensive exploration cannot quietly continue until the desired label appears. The plan may **estimate** costs from existing records; estimates do not authorize execution.

## 5. Proposed 20-root readiness thresholds (NOT guaranteed)

Record each as `MET`, `NOT_MET`, `UNDECIDED`, `CONSTRUCTION_UNAVAILABLE` with numerator, denominator, independent-root IDs and evidence scope. These are from Guide v1.9 and remain **proposed scientific targets**:

- ≥ 6 independent roots with a verified empty/no-repair witness.
- ≥ 8 independent roots with a complete nonempty ordered repair witness.
- ≥ 4 roots with multiple independently sufficient alternative corrections.
- ≥ 4 roots with a **decided same-endpoint order contrast**, i.e. positive complete witness and negative scope-wide certificate; one positive plus timeout is **not** a contrast.
- ≥ 4 roots with decided nonzero fixed-robot scene-intervention effects.
- ≥ 4 roots with decided omission effects.
- ≥ 4 roots with decided nuisance/no-change/zero-effect controls.
- ≥ 8 roots with first-complete-relocation-witness joint-travel labels; ≥ 4 have multi-move relocation witnesses.
- B/C extra: ≥ 4 independent roots with **fully decided, active-mask-complete** bounded-z mini pools (ideally containing multiple repair outcomes), and ≥ 2 independently measured nonadditive intervention/omission examples *if constructible*.

Also report static-valid candidate unknown proportion and its breakdown, exact negative certificate types, distinct scene-pair eligibility vs decided coverage, expected number of valid/negative/unknown proposals, and matched equal-information coverage across A/B/C. Guide v1.8 suggested ≤50% unknown among static-valid ordered candidates and ≥50% decided among eligible planned effect pairs; carry these as **proposed diagnostics/targets** if the later G4C judge retains them, never label an unmet metric PASS without declaring the threshold policy in advance.

**Anti-shortcut:** ≥4 fully decided B/C mini pools is a requirement on **complete outcome-vector coverage**, not merely 4 successful repairs or 4 roots where one intervention has a known effect. A partly masked pool can train unary supervision, but not the exact B/C joint pool loss. Plan explicitly for complete vectors with bounded catalogues to avoid impossible quotas.

Report coverage also by exact proof scope and original/edited robot state, and keep `NEGATIVE`, `UNKNOWN`, `OUT_OF_SCOPE` distinct.

## 6. Teacher and compute plan — requires numeric user authorization

Create a plan JSON with **requested but initially null, blocking numeric budget fields** unless the user explicitly supplies and authorizes them in this stage:

```
per_teacher_unit_cpu_s: null
aggregate_cpu_s: null
workers: null
unit_wall_guard_s: null
aggregate_wall_guard_s: null
cancellation_margin_s: null
max_motion_nodes: null
relocation_skill_attempt_cap: null
target_eval_attempt_cap: null
max_root_construction_attempts: null
```

Use a safety envelope analogous to the successfully tested G4D CPU/process-tree guard, atomic per-unit checkpoints and resumability; **do not inherit G4D's 18,000 CPU-s** or its timeouts as new authorization. Distinguish mandatory stage caps from nominal planner profile inherited for semantic consistency: values can be proposed with provenance but remain unauthorised until explicitly accepted. Estimate total cost using actual G4D/G4A measured calls and conservative ranges; call out large uncertainty and near-zero cost of many certified negatives without claiming the entire pilot will be cheap.

Specify a two-step subsequent collection plan: a small **pilot subset** with all planned categories and cap/coverage monitoring, followed by the full 20-root development audit **only if** user authorization includes that scope and measured pilot results justify it. If pilot is separate, never replace/retune originally held-out roots using pilot labels. Preserve failed construction attempts and censored units. No automatic retry or expanded budgets in the same frozen run.

**No numeric authorization means STOP at plan + validation.** Output plan status `FROZEN_PENDING_BUDGET_AUTHORIZATION`, not `G4C PASS` or `DATA_READY`.

## 7. Scale beyond the 20-root development gate is not part of this instruction

A fresh **300-independent-root** pilot with root split 210 train / 45 validation / 45 test is only prepared in *principle* for a separate future approval **after** the development audit. Before any descendant generation, split by independent root. Freeze untouched test root IDs. A later 1,000-root expansion requires throughput evidence, label sufficiency and its own cap. DO NOT generate or split 300 roots in this stage.

## 8. Minimal code and visual output

Prefer reusing `g4d_run.py`, existing `teacher.guard`, `effects.py`, `ordered.py`, `data.py`, and `viz.py` as permitted by actual responsibility boundaries. New plan/preflight code may live in **one small focused source module** (or augment an existing small stage-specific tool) and **one test module** plus a thin `run.py` CLI dispatcher if necessary. Avoid generic training frameworks, per-model data generators, extra nested directories or changing V1/V2 protocols. Existing `verify.py` and `skill.py` should not be refactored for aesthetics.

Plan-only artifacts in one new flat root directory such as `runs/g4c_preflight/`:

- `plan.json`: complete frozen root seeds, candidate/query generation recipes, outcome catalogues, expected unit counts, source/config/robot/policy hash, requested budgets NULL, and pass gates.
- `audit.json`: available historical evidence map, reuse eligibility by scope, future data gap audit, and explicit NOT_RUN for new roots/labels.
- `schema.json` (or a human-readable schema section in `plan.json`): active outcome slots, masks, split metadata and example canonical records.
- `manifest.json`: source hashes, input provenance, reproducible plan hash; record all output files.
- `overview.png`: actual existing 2D scene geometry for one historical G4D example **labelled CONTEXT ONLY** and/or geometry-validated construction proposals labelled **SCHEMATIC/NOT_RUN**. All future outcome panels must be marked NOT_RUN. Do not draw nonexistent arm paths.
- `coverage_plan.png` or `coverage_plan.csv`: target quotas and planned root/category coverage with clear distinction between **plans** and **measured evidence**.
- Next sequential `responses-phases/NNNN_G4C_preflight.md`: report of what was inspected/proposed/validated, exact test commands, Git status and hashes, intended/actual new calls (actual must be zero), risks, requested authorization and next-step STOP.

If `run.py` already supports plan creation, reuse its convention; otherwise add a single `g4c-plan` dispatch. Tests must show deterministic plan hashing, construction-intent counts, no label leakage, no historical input modification, no target/planner invocations, fail-closed budgets, and label/mask/data-split invariants. A deliberately malformed mask, leaked oracle field, duplicated root, mixed lineage across splits or changed-query catalogue must be rejected.

## 9. Required report and STOP behavior

Report:

1. Existing HEAD/upstream, repo dirty/untracked state and how untracked v1.7/v1.9 documents were read without altering them.
2. Precise source versions and any contradiction discovered between real code and the proposed guide (resolve only within this stage or BLOCK, never silently change the methodology).
3. Each proposed fixture's physical construction plan, root independence, candidate quotas and **why** it can exercise a distinct causal/order/cost question; never call it a measured success.
4. Outcome-query/catalogue layouts and total active `z` bound; all-masked/partially decided vs fully decided semantics for A/B/C.
5. Full label accounting policy and how G4A/G4D legacy evidence stays separate.
6. Pilot/full-development CPU/call/node budgets **requested, not assumed approved**, with measured historical basis and estimated risks.
7. All tests/exits, zero new teacher/planner/target calls, reproducible hashes, visuals, files changed and module lines.
8. Explicit decision **`G4C-PREFLIGHT_READY_PENDING_BUDGET`**, **`G4C-PREFLIGHT_BLOCKED`**, or **`G4C-PREFLIGHT_FAILED`**, and **`G4C DATA COLLECTION NOT RUN`**.
9. No G4E, G5, G6 or 3D. **STOP**.

Follow the established repo synchronization convention only with user authorization; no force-push, no deletion/mutation of archived reports/runs, no speculative numerical label targets, no taking over unrelated untracked documents. If there is an essential ambiguity in physically constructing fixtures, provide a finite alternative and mark the issue rather than guessing a verified outcome.

**The central gate:** G4B proved the sampler's math on synthetic microdomains. G4C must next establish that independent, meaningful **real 2D robot labels** exist in sufficient breadth and with intact negative/unknown/causal scopes to *train* A, B and C fairly. Planning that evidence precedes spending unapproved robot-teacher compute.
