# G4C-P1 — Authorized 5-Root 2D Teacher-Evidence Pilot

**Execution instructions for Claude Opus 5.5 High | 20 October 2026**  
**Status:** Authorized **pilot only**; execute once within the hard limits below, independently judge, report, and **STOP**.  
**Research protocol:** `INITIAL_SCENE_ORDERED_ONE_SHOT_V2`; comparative study `2D-ABC-v1`.

> **Primary objective:** Run the already-frozen **five-root, 59-unit** subset of G4C's 20-root development plan; collect defensible, scope-aware 2D ordered repair, fixed-robot scene-intervention, omission, robot-start, and first-witness cost evidence. Measure dataset coverage and actual compute use. Do **not** train models, revise the science or expand the collection. A fully executed pilot is **not** G4C data-readiness PASS.

## 0. Required reading, provenance, and precedence

Before modifying a file, read the entire repository instructions (`AGENTS.md`, `CLAUDE.md` or equivalents if present), then:

1. `responses-phases/0013_G4C_preflight.md` (**immediate authority on the frozen G4C plan**); `runs/g4c_preflight/plan.json`, `preflight_result.json`, `schema.json`, `audit.json`, and manifest.
2. `responses-phases/0012_G4B_sampler_exact.md` and `responses-phases/0011_G4D_corrections_and_collection.md`.
3. `docs/addenda/A1*`, `docs/addenda/A2_termination_reasons_v1.md` if present; the actual G4D runner/guard/checker/code and tests.
4. **Methodology v1.7** and **Implementation Guide v1.9**, currently reported as **user-owned, untracked** `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` and ZIP. Read their Markdown sources wherever they actually reside; don't invent file paths, commit them, or overwrite them. Their earlier G4D-blocked historical status is superseded by reports 0011–0013.

**Repository starting point:** the user-provided latest successful commit is `9e7242117a72429ea13f949d68e1d94b5a0f9510` on `main`. Reported baseline: **169 tests** and **six archived replays**. Confirm actual HEAD, branch, remote and working tree; never blindly reset or delete local work. If newer commits or substantive conflicts exist, **pause and report before running the pilot**. Never force push.

**Frozen source:** `runs/g4c_preflight/plan.json` with reported SHA-256
`c761c68497309f6b631f6740237e75f08c2376ade179b7f644731dc775f193a3`.

Confirm the **exact byte hash** and the plan's own canonical/semantic hash as recorded. Use the exact meaning of the hash stated in the preflight manifest; do not assume the reported value is a raw-file hash if it is a canonical plan hash. Re-run the existing deterministic plan validator/regenerator only in read-only/scratch fashion and verify identity. Bind all input/source/profile/action/seed-key hashes required by that plan. If any binding fails, **fail closed, with zero new teacher calls**. Do not regenerate a *different* root/query plan to continue.

## 1. Precise authorization: PILOT ONLY

The user explicitly selected and authorized the **pilot, not the full 20-root collection**. Authorization covers the **predeclared** root subset below, its fixed teacher units and the numeric envelope; it is not permission for new root discovery, new queries, external test roots, changing the 3R planner, large datasets, training, 3D or hardware.

### Frozen selection

| Root | Construction family | Frozen unit count |
|---|---|---:|
| `g4c_r00` | J0 — no-repair / nuisance control | 2 |
| `g4c_r08` | J2 — access and order contrast | 10 |
| `g4c_r10` | J3 — destination/staging dependency | 11 |
| `g4c_r14` | J4 — three-object ordered interactions | 19 |
| `g4c_r19` | J9 — 13-sequence small exhaustive candidate domain | 17 |
| **TOTAL** | five **development** roots | **59** |

Derive the actual 59 unit identities, ordering, scene hashes, query catalogues and seed keys **directly from the frozen plan**. Recheck each unit using the existing G4D runner identity validator before the first planner call. Never add, remove, reorder for outcome convenience, replace or re-sample a unit. J0/J2/J3/J4/J9 are **construction intentions**, not outcome labels. If the plan doesn't contain exactly this subset, **STOP before collection**.

### Mandatory hard budget (all fields binding)

```toml
[authorization]
scope = "G4C_P1_PILOT_ONLY"
per_teacher_unit_cpu_s = 900
cancellation_margin_s = 30       # stop/cancel each at 870 CPU-s, never exceed 900
aggregate_cpu_s = 10800          # 3.0 CPU-hours, including orchestration
workers = 1
unit_wall_guard_s = 1800
aggregate_wall_guard_s = 14400  # 4 hours
max_motion_nodes = 4000          # unchanged original planner profile
relocation_skill_attempt_cap = 60
target_eval_attempt_cap = 59
max_root_construction_attempts = 0 # roots already frozen
```

Also carry through any other **frozen** grasp family (48), robot/body/gripper profile, geometric tolerances, collision rules, supported-transport policy, end policy, candidate/sequence cap and deterministic relocation/target seed scheduling. **Do not** raise any limit to finish an uncertain query. The earlier G4D 18,000 CPU-s allowance is not inherited. The 30,600 CPU-s full-collection request is **not** authorized.

**Budget accounting:** measure process-tree CPU including worker descendants; count coordinator/orchestration CPU in the aggregate; use one worker and existing process-tree kill/guard implementation. Set numerical libraries to a single thread as required by the tested G4D runner. Check aggregate admission *before* starting another unit, honoring an explicit reserve/margin; maintain the global wall guard from the fixed start time. Charge every actual relocation-planner and target invocation before the call, including failures. Never let a background child escape the guard. When near any cap, stop the remaining units and record `NOT_RUN_BUDGET` / `NOT_RUN_WALL` rather than overrun.

A cancelled, interrupted or crash-ambiguous unit is never silently re-executed. Use existing resumability semantics: only provably never-started units may be started on restart, within the **original** envelope and deadline. A future extension requires new explicit authorization.

## 2. Implementation allowed in this stage

### A. Pre-run audit (strict zero-planner phase)

1. Capture `git status`, HEAD, remote HEAD, all configured profiles and relevant file hashes; inspect `g4c.py`, `g4c_figures.py`, `g4d_run.py`, `g4d_gate.py`, `teacher.guard`, `ordered.py`, `verify.py`, `effects.py`, `data.py`, `sequences.py` and existing tests **as they actually exist**.
2. Validate the exact frozen plan, the original source manifest and the 59-unit subset, outcome masks (`<=8` active per proposal), eligibility flags, proposal signatures, split metadata and per-root lineage. Verify 59 units are admissible through the existing G4D unit schema.
3. Check **no** teacher label/trace/certificate fields or expected outcomes have leaked into scene construction, candidate selection or learner-visible inputs. Require exact initial robot, goal, masks and appearance-anchor preservation for every counterfactual.
4. Inspect output paths before use; **never overwrite** `runs/g4c_preflight/`, `runs/g4d_evidence/`, `runs/g4b_sampler_exact/`, historical runs, prior reports, untracked user files or guide copies.
5. Record authorization in a separate immutable pilot authorization record, linked to the plan hash, exact numeric fields and the user's pilot-only approval. Treat this file as scope documentation, not permission to expand the plan.

### B. Minimal finalization adapter (only after audit)

The preflight states two pieces do not yet exist: a G4C-specific **finalize** adapter and a **judge**. Implement the smallest possible adapter that:

- Takes the existing frozen preflight plan, applies **only** the externally authorized budget and five-root selection, and writes a new **immutable derived pilot execution plan** with parent plan hash, authorization hash, source/config/profile hashes, 59 unit IDs/seed keys, and all limits.
- Does not write authorized values into or otherwise modify the frozen `plan.json`; its `budget` fields remain `null` in the parent.
- Validates every unit against the original root/action/scene/seed hash and the trusted runner's schema, and fails closed on any stale or modified source binding. If adapting code changes a file whose hash is frozen, stop and reconcile *before* calling the teacher; never quietly accept a new generator or checker under the old source manifest.
- Reuses `g4d_run`'s existing guarded worker, CPU/wall bookkeeping, atomically written checkpoints, content rechecks and interrupt/resume safeguards. Do not copy the planner or build a second teacher pipeline.
- Writes strictly **new** outputs, e.g. `runs/g4c_pilot/` (actual path must be manifested), using content hashes. A CLI wrapper can live in a small dedicated file. Don't modify `run.py` or any frozen input dependency if doing so would invalidate the source contract.

### C. G4C judge, developed and tested before collection

Build a small fail-closed coverage judge over **revalidated evidence**, never over a self-reported success flag alone. Validate with synthetic **fixture** records before any pilot execution; negative-mutant tests must fail as expected.

**Evidence distinctions to maintain:**

- `POSITIVE` ordered repair requires complete proposed-order relocation witness **and** complete goal + `SAFE_RETREAT` target witness from the **achieved** final state.
- `NEGATIVE` requires an independently checked, matching **scope-wide** certificate (`ORDER`, `ASSIGNMENT`, or other documented valid scope). An ordinary failed IK/grasp search, connector failure, `SCHEDULE_COMPLETED_NO_WITNESS`, wall/CPU censoring, or historical raw `PLANNER_BUDGET` string stays `UNKNOWN` unless independently certified.
- `UNKNOWN`/`UNRESOLVED`, `NOT_RUN`, `ERROR`, `CANCELLED`, `OUT_OF_SCOPE` and `INELIGIBLE` are separate evidence/operation statuses. Unit process `COMPLETED` is **not** equivalent to positive or decided feasibility.
- A target-only **fixed-robot scene intervention** clones the initial scene, changes only allowed object poses, verifies support/no penetration/initial-robot compatibility, and preserves initial joints, gripper gap, attachment, task and appearance anchor. Its target-only outcome never establishes the physical executability of the hypothetical edit.
- A **repair omission** removes one or two named sequence actions, restores those objects to initial stays, rebuilds all hypothetical prefixes, and independently looks up/rechecks the omitted sequence. No deleting an object, copying positive labels to other orders, or reusing invalid trajectories.
- **Robot-start contrasts** are a separate scope, not fixed-robot scene intervention labels. Nuisance zero effects and nonzero effects require both outcomes independently decided.
- **Cost** `J_first`: only first complete relocation witness under frozen policy, including robot joint travel and continuity; can exist even when target outcome is negative/unknown. Exact zero for empty sequence. Never choose a better/lower J retrospectively because the target passed; never compare endpoint distance as though it were learned joint travel.
- Check all stored witnesses/certificates independently as in G4D, including actual target-call invocation state (object poses and q/gap/attachment), joint continuity, no silent reorder and safe-retreat end. If verification is missing, mark `UNKNOWN` rather than PASS.

**Coverage must use the frozen G4C schema and thresholds, without pretending the pilot is the entire 20-root study:**

- Per-unit attempted/started/completed/cancelled/not-run, label and reason, robot/target calls, CPU/wall, witness/certificate hash and recheck verdict.
- Per-root zero-repair positive, nonempty complete positive, multiple sufficient positive repairs, same-endpoint order contrasts (one POSITIVE + one certified NEGATIVE under exactly matched endpoints), decided/eligible scene pairs and effect deltas, omissions, nuisance controls, harmful effects if actually measured, two-/three-move witnesses, first-witness cost availability and endpoint-vs-J comparison.
- **Nonadditivity** only when every compared original/singleton/joint outcome is decided; no guessing from other roots.
- **B/C exact-mini-pool completeness:** read each root's predeclared catalogue and active outcome-slot mask. The root qualifies only if **every active slot for every sequence in its predefined pool is decided** with the proper scene/repair/omission scope. Inactive slots create no evidence requirement and no partition multiplicity. A partially decided pool remains useful for individual supervised terms but does **not** qualify for the exact joint-pool loss. Report per-root list of missing `(sequence,slot,unit)` links and reasons. In the J9 domain, preserve all 13 candidate ordered sequences; any unmapped required active slot must be counted missing, not silently assumed negative/zero.
- Report the exact outcomes and masks A, B, C would each be entitled to consume. All arms must have **equal source information**; no oracle fields in learner data. No loss or training actually runs.
- Preserve **all** difficult/unknown roots and queries in the denominator. Distinguish G4D legacy/development controls from these **five new** roots.
- Score scientific thresholds for the full **20-root** G4C gate as `NOT_EVALUATED_FULL_SET / PILOT_ONLY`, with pilot progress numerators shown separately. Do **not** claim `G4C DATA_READY` or mark absent 15 roots as failures. If the pilot already shows a planned target mathematically impossible within the frozen full set, document this concern without rewriting the plan.

### D. Pilot execution (after both A/B/C pass pre-run fixture tests)

Run the **59 frozen units only** using the existing trusted teacher/guard. Follow the frozen unit order/seed keys (or deterministic order declared before outcomes where the plan permits). Each root's candidate sequence is evaluated afresh from the same immutable initial scene, with continuous robot state across its ordered relocations and a `plan_fixed_order` verifier that never chooses another order.

Allowed teacher evidence:

1. For an ordered repair: independently screen static certificates, attempt exact fixed-order relocations within node/call/time budget, checkpoint the **first full relocation witness** and `J_first` before target exploration, evaluate the original target from the achieved final robot/scene state, check target safe retreat, write all provenance.
2. For a scene intervention: clone the original state, apply its *predeclared eligible* object-pose edit at fixed robot q/gap/attachment, perform target-only teacher verification. Store both state hashes, changed-field audit and anchored appearance metadata.
3. For a robot-start intervention: preserve the original object arrangement, change only the approved initial robot state and evaluate the target under the separately labeled robot-start scope.
4. For omitted repairs: use the predeclared canonical remainder sequence and obtain/reuse **only properly matching** checked independent teacher evidence. Never infer omission failure from full-sequence success.

External static checks are permitted as required by the teacher; **no model or Boltzmann sampler** chooses these predeclared queries. Any diagnostic optional HOME path never replaces the checked `SAFE_RETREAT` target witness and is included in the budget. Write checkpoints atomically; validate them before a result can be counted. A late crash after a valid target-witness checkpoint must not erase it, and an incomplete certificate record must not turn into a success.

### E. Finalization, visualizations, decision

- Recheck every completed/certified unit and recompute the per-root counts. Compare hashes to **both** parent frozen plan and derived authorized pilot plan; compare source/profile/context hashes before/after collection. Save the audit ledger and machine-readable results.
- Produce `pilot_units.csv` (all 59 planned IDs and statuses), `pilot_roots.csv`, `pilot_coverage.json`, `bc_pool_coverage.json`, `budget_ledger.json`, `manifest.json` (SHA-256), and `pilot_result.json`. Existing G4D-style NPZ witness/certificate records are retained in per-unit directories. Naming may adapt to actual repo; document mapping.
- Make at least: (i) a scene-backed overview of all five initial full-3R scenes and frozen ghost actions; (ii) coverage chart showing **pilot decided vs unknown vs not-run** separately and full-gate targets as future targets; (iii) actual CPU/wall/guard chart; (iv) one **genuine recorded** trajectory/order/scene-effect comparison if supported by decided evidence (otherwise explicitly `UNDECIDED/NOT_AVAILABLE`; do not draw fictional executed paths). Each figure labels `PILOT`, provenance, scope and PASS/NEGATIVE/UNKNOWN. A single root can display A/B/C *data readiness*; never draw learned energy predictions.
- Before reporting, run relevant unit tests, full regression suite and six independent archived replays to scratch outputs. Track planner/skill/target calls from regression separately from the 59 pilot units. Preserve original historical archives and manifests exactly.
- Write **one new numbered report**, suggested `responses-phases/0014_G4C_pilot_collection.md` (choose next unused number). Include exact Git SHA, clean/dirty state, source hashes, authorized numeric limits, pilot and full parent-plan hashes, all 59 unit dispositions, root-level evidence table, unknown reasons, B/C full-pool slot diagnostics, cost statistics, leakage and witness checks, CPU/wall per unit and aggregate, guard/cancellation behavior, test/replay commands and exit codes, representative witness/certificate figure links, risks and the **specific** next authorization needed.
- Judge state must be one of `G4C_PILOT_COMPLETE` (all 59 dispositions independently audited), `G4C_PILOT_PARTIAL` (some unrun, censored or inadequately validated), or `G4C_PILOT_BLOCKED` (precondition/evidence/guard failure). Separately report per-label `POSITIVE/NEGATIVE/UNKNOWN` and scientific metric status. **`G4C_PILOT_COMPLETE` is not `G4C DATA_READY`**. A fully audited unit with UNKNOWN outcome does not invalidate completion, but it remains unknown for learning.

## 3. Essential automated tests to add

Before allowing execution, create focussed tests proving:

1. Wrong/missing budget authorization, over-full-scope authorization, changed parent hash, tampered source binding, or 60th distinct pilot unit -> rejection **before teacher calls**.
2. Pilot root list and unit count exactly `(r00:2,r08:10,r10:11,r14:19,r19:17)`. Finalization preserves parent plan and all 59 identities and seeds byte-for-byte in the derived selection.
3. Process-tree CPU guard, per-unit 870 s cancellation, 900 s hard cap, aggregate 10,800 CPU-s with reserve, global 14,400 s wall and max target/relocation invocation caps; mock clocks/workers, **do not burn real CPU** for testing the guard. Interrupted `STARTED` unit is not rerun.
4. Judge rejects false POSITIVE if target invocation differs from achieved state or witness misses safe retreat; rejects false NEGATIVE if only exhausted IK/budget or certificate scope mismatch.
5. Scene pose intervention never modifies q/gripper/anchor; omission preserves other action order and returns omitted object to stay.
6. B/C complete-pool validator: one unknown active slot disqualifies pool; an inactive slot does not; scrambled catalogue/changed mask is rejected; no cross-root label reuse.
7. Coverage denominator retains all planned units and avoids treating `COMPLETED` as `POSITIVE`. Entire 20-root G4C threshold is **not run** after only the pilot.
8. Existing 169 baseline tests and six archived replays still pass; no modification to historical outputs.

Do not add test-only bypasses to live execution paths. If a test or authorization invariant fails, **do not collect**; report the blocker.

## 4. Science invariants and exclusions

- **No G4C full run:** The remaining 15 roots and 108 units are outside authorization, even if pilot costs are small.
- No new root construction, no supplementary intervention catalogue, no extra scene-effect/omission queries to fill difficult labels, no relabeling timeouts, no planner parameter or grasp-family relaxation.
- No G4E neural code, A/B/C model implementation, GRU, DINOv2 training, gradients/optimizer, pseudo-causal labels, energy optimization experiments, 3D or hardware.
- No target trajectory/swept volume, teacher verdict, motion witness, certificate, root/split ID or oracle distance in learned proposals or future learner tensors.
- Preserve G4D's one-shot **deployment** boundary; the *offline teacher* is permitted to test many frozen candidates separately from identical initial scenes.
- No edits to methodology or guide PDFs or to user-owned untracked copies in this gate. The guide's historical G4D status is superseded by newer reports; document the discrepancy, do not erase history.
- Code minimal, one responsibility/module. A source >300 logical lines triggers a review explanation, **not** a forced refactor of working modules. Do not build a generic orchestration framework, new database, dashboard or replacement sampler. No mutation of `g4c.py` frozen generator/validator if doing so invalidates the freeze; keep collection adapters separate.
- Use reproducible hashes, canonical sequence signatures, seeded planner calls, deterministic source manifests and non-destructive Git operations. Commit/push stage results per existing repository convention after reviewing diff/secrets; no force push; leave user's untracked files unchanged.

## 5. Required last-message structure / STOP

Return a concise plain-language summary followed by:

1. **Decision**: `G4C_PILOT_COMPLETE`, `G4C_PILOT_PARTIAL`, or `G4C_PILOT_BLOCKED` (and whether any 20-root G4C readiness claim is possible: **NO**).
2. **Exact commit/branch/remote**, modifications and preserved untracked files.
3. **Frozen plan + authorization identities** and all numerical caps; evidence that the 15 excluded roots were never run.
4. **Pilot evidence**: all 59 statuses, per-root positives/negatives/unknowns, decided matched intervention and order contrasts, first J labels, complete/partial B/C pools; unresolved cases explicit.
5. **Safety and integrity**: max CPU/wall/overshoot/cancellations/resumes; planner/target counts; source and lineage checks; revalidated witnesses and certificates.
6. **Tests and reproducibility**: commands, exit codes, tests and replays, plots and report paths.
7. **Recommendation**: proceed with remaining 15 only after reviewing pilot coverage and a **new explicit full-run approval**, or stop/diagnose data-readiness obstacles first.

**STOP immediately after reporting. Never initiate the full 20-root run, G4E, G5, G6, 3D, or hardware.**
