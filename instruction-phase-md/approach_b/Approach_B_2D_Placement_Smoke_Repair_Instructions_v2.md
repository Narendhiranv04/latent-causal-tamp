# Approach B — 2D Placement Smoke-Test Repair, Reproducibility, and Verification Contract (v2)

**Date:** 6 November 2026  
**Scope:** Repair and rerun the **existing 2D placement-only sidecar smoke test**. **Nothing beyond smoke testing is authorized.**  
**Target agent:** Claude Code / Opus 5.5 High operating in the user's **local** worktree.  
**Authoritative scientific basis:** `final-fixed-methodology-1.pdf` (5 November 2026); preserve the Approach B sampler/X/Y separation.  
**Prior task contract:** `Approach_B_Placement_Dataset_Extension_Smoke_Plan.pdf`. This document **supersedes its smoke-only timeout/reproducibility choices**, but does **not** authorize scaling or change Approach B's scientific architecture.

> **Observed report, not source-verified new code:** An initial smoke run on a local, uncommitted worktree ` /home/naren/Desktop/rss-placement-smoke ` (`naren/placement-smoke-2d`, baseline commit `9e640690`) reported `SMOKE_FAIL`. Its serial pass produced one positive; its 28-worker pass predeclared 35 queries on four roots, attempted 34, yielded 28 operational ones and six budget zeros, stored 190 witnesses (185 new/5 reused), and showed run-dependent labels/witness sets when 2-second plan and 12-second query wall caps bound. Reported mode accounting: 78,336 nominal pairs = 70,825 geometry-rejected + 233 motion-attempted + 7,278 not motion-tested. Twelve of 35 queries changed witness sets across repeats; one label changed 0→1. Local files were **not** accessible for independent review in the previous audit. **Inspect the actual local code and `report.md`; do not accept this summary as code evidence or overwrite the failed output.**

## 0. Scientific and operational decisions — already authorized

1. **Binary supervision, not a three-class classifier.** For an **eligible placement query whose declared deterministic work budget actually finishes**: `label=1` iff at least one complete placement witness has independently passed the correct phase-aware verifier; otherwise `label=0` (operational failure under a named policy). A zero due to completed bounded search is **not** a theorem of global infeasibility.
2. **Unattempted / safety-interrupted ≠ zero.** Static-ineligible requests and tasks never started have `attempted=false`, `label=null`, and a reason. A task preempted by an emergency watchdog, thermal event, OOM, crash, external cancellation, or wall deadline *before finishing its work budget* has `completed=false`, `label=null`, and an interruption reason. **No `UNRESOLVED` observed label**, but also **no forged binary observation**. A resumed task reruns with identical policy/seed from the last committed checkpoint.
3. **Placement only, assuming grasp already achieved.** The sampler teacher begins at a **physically valid, already-attached post-grasp configuration** and evaluates **held transport → supported placement/release → local retreat**. It **does not require approach, pick-access, closure trajectory, reset-to-home, target task, X terminal connector, or Y restoration** to label a placement. It may use a declared finite catalogue of hypothetical allowed post-grasp modes. Complete pick-and-place is the **X teacher's** separate job.
4. **Mode enumeration is not motion exhaustion.** For 2D, enumerate the declared 48 post-grasp mode IDs × 48 place mode IDs = 2,304 nominal pairs for each eligible object/destination. Sound static/IK/contact checks may reject nominal pairs before planning, but their proof scope must be logged. Plan a bounded, deterministic subset of survivors. A query can be operational zero under this *finite policy* despite unattempted survivor modes. Never misrepresent those as proven blocked.
5. **Trajectories are real evidence, not generator targets.** Retain every distinct complete verified placement witness found within the smoke policy, with deduplication. A cVAE/flow model is **not trained** in this task and does **not** learn to output trajectories under the frozen method.
6. **Do not globally reject an initially unpickable object.** Individual placeability can be positive even if initial pick access fails; later hypothetical scenes may change destination availability. Actual ordered execution from original root remains X's responsibility.
7. **No full dataset collection; no model training; no 3D; no remote SSH; no X/Y changes.** The original 5,000 counted 2D roots and archived data remain untouched. The new job is the previously established tiny smoke roster only.

## 1. Mandatory read-only source and artifact audit (before edits)

### 1.1 Establish exact local state

From the existing worktree, record `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff --stat`, and current file hashes. Determine whether `placement_smoke.py`, `placement_smoke_check.py`, `test_placement_smoke.py`, `smoke_20261106/report.md`, the original 5,000-scene manifest, and the smoke NPZ files exist and are readable. Do not create a replacement checkout and do not reset/rebase/clean the worktree.

Inspect at minimum:

- Existing smoke scripts and report (actual source, complete—not only summaries).
- `gh-yadu-iiith/planar_2d/dataset_bd_classquota/README.md`, `selected.json`, selected `raw/roots` and `raw/witnesses`.
- `code/latent-causal-tamp/{skill.py,planner.py,motion.py,geometry.py,config.toml,p16_motion.py}` and `code/dataset-bd/{bd_core.py,bd_2d.py,tests/test_bd_dataset.py}` in their **actual local paths**.
- Prior smoke's predeclared **35-query roster**, hashes, original config/protocol, mode counting, positive/negative provenance, resume mechanism, actual timing/temperature controls, and the comparison logic that flagged nondeterminism.

### 1.2 Baseline code facts to verify locally

The GitHub baseline at commit `9e640690` has `skill.directions()` with 24 angles × two elbows; `skill.screen_pick()` checks **approach and closure** and must not silently be reused as the sampler's post-grasp feasibility filter. `skill.plan_skill()` returns after its **first** validated full skill witness; a smoke-specific post-grasp labeler must explicitly continue under a finite policy if collecting multiple distinct mode witnesses. `planner._rrt_connect()` limits **successfully inserted vertices** and uses `time.time()>deadline` both during search and shortcutting; failed extension attempts can consume work without adding nodes. The P16 deterministic physics provider sets planner wall time effectively off and uses work budgets instead. The original test `test_existing_json_npz_readers_still_load()` reads optional `runs/p16/...` and `runs/p14/...` paths, so its absence must be separated from new regressions.

Confirm these facts against the local code; if the smoke adapter already handles some correctly, preserve that implementation rather than rewriting it.

### 1.3 Audit output and hashes before any destructive action

Preserve `smoke_20261106/` as **read-only failure evidence**. Compute source-dataset manifest/selected-root hashes and relevant archived witness hashes before work. Record the output tree and whether any new `.pyc` or cache was written into the old dataset. Use an external `PYTHONPYCACHEPREFIX` or `PYTHONDONTWRITEBYTECODE=1`; do not delete arbitrary caches. Reusing prior smoke files as read-only diagnostics is allowed; do **not** carry over labels from the wall-limited run as canonical labels for the new deterministic protocol.

Deliver an audit note in the new report describing what actually differs from this contract. If the local files are missing or code is unreadable, **STOP with `SMOKE_BLOCKED`**, do not fabricate code, experiments, or paths.

## 2. Correct the teacher semantics before changing time budgets

### 2.1 Define the exact place-conditioned event

Let `S` be a root scene or an object-only hypothetical edited scene, `o` a selected movable object, and `d` a statically permitted resting destination. Let `g` be a **declared, post-grasp held configuration** (robot joints, gripper gap, object-to-tool relative transform, allowed contact state) representing the object **already grasped at its source**. Under the frozen permitted `g` catalogue and bounded search policy `Π_place`:

`V_place(S,o,d; Π_place) = 1` if **at least one** allowed held starting mode `g` and place mode yields a fully verified **carry + place/release + local retreat** trajectory within the declared deterministic work budget; otherwise operational `0` after that budget completes.

**Not included:** motion from `q0` to the grasp pose, a collision-free approach to the object, forceful finger closure, target action, a target-reference connector, or intermediate full-robot sequence continuity. Do not call the full old `plan_skill()` with its original pick screening and simply relabel its result as `V_place`.

### 2.2 Post-grasp initialization must be physically coherent

For each of 48 declared orientation/elbow IDs, compute or retrieve the candidate **attached robot configuration** without imposing approach accessibility. Check finite joint limits and IK for the held tool–object transform, robot self-collision, robot/environment and held-object/environment collisions under **correct grasp-contact exceptions**. The object must be attached at its real source pose with the recorded local transform and valid finger aperture. An impossible held geometry may be rejected with a **mode-scoped** reason; no pick-approach/closure failure is allowed to reject it.

For each of 48 destination pose mode IDs, test the corresponding attached placement configuration, legal support/occupancy/contact, release, and certified retreat. Only compatible start/end modes reach continuous motion planning. Use the correct **pick-specific `held_local`** for transport and place; avoid accidentally replacing it by a generic nominal attachment if that changes the robot's actual grasp transform.

**Important:** A planned held state is a hypothetical *conditional* configuration, not proof the robot could pick the object there. It must not be reported as a physically executed pre-grasp motion.

### 2.3 Verify the precise witness phases

Every positive must contain a complete, collision-certified held-object trajectory starting at the declared attached `q_hold`, continuing through carry, release/detachment, and post-release local retreat under the correct contact modes. No target reference connector or home motion is required. Store phase-per-segment values, actual `q`, gap, attachment mask, relative attachment transform, achieved place pose, start/end states, and verification verdict/scope. If reusing a full historical pick-and-place witness, isolate its **post-grasp suffix** and **independently reverify with phase-aware checks**; the old complete-trace verifier may assume approach phases and cannot automatically be used on an arbitrarily cropped trace without checking its preconditions.

Classify a root-state object that fails **pick access only** separately from individual placement outcomes. Add a tiny synthetic/constructed **regression test only** demonstrating `pick_access=0` while a geometrically valid held start and verified placement can still produce `V_place=1`. If the available real tiny smoke roots do not exhibit this, do not fabricate a real positive; a unit test with an expressly named fixture can validate the logical separation while the smoke report remains honest.

### 2.4 Intermediate scene meaning

Use object-only `Edit(S0,prefix)` for selected historical/controlled prefixes. Record the original root ID, canonical prefix, `prefix_key`, `hypothetical_scene_hash`, edited object IDs, and `parent_reachability ∈ {WITNESSED, HYPOTHETICAL}` (or equivalent provenance; this is **not** a training-label class). The skipped initial occupied-cell request remains nonobserved/ineligible; the new valid query after A moved is a distinct edited-scene query. Never infer an achieved `q_A`, or use it to start the new sampler query.

## 3. Eliminate wall-clock dependence from scientific decisions

### 3.1 The required deterministic budgets

Stop **canonical** mode/placement search using predeclared counts, not wall time. At minimum record and enforce:

- attempted RRT extension/connection operations **including rejected extensions**;
- collision/interval evaluations or an equivalently precise work count, including calls inside invalid expansions;
- accepted nodes (existing cap remains available, but is **not sufficient alone**);
- a deterministic number of shortcut attempts, with a fixed seed and schedule;
- number/order of screened post-grasp modes, place modes and compatible pairs;
- number/order of full motion-planning calls, with per-pair and per-query work limits.

Select explicit small limits by inspecting the original failed-run work distribution and the baseline node/eval budgets. **Do not mechanically pin `60 steps`**; define what a 'step' is and prove every failed extension consumes a bounded unit. One sound, auditable work policy is preferable to many interacting ad hoc caps. Keep all necessary geometric certification routines intact; a work-exhausted subcheck produces operational failure **for that attempt**, not a fabricated certified collision.

The random stream must be **per query/mode key** with stable hash/CRC32 or cryptographic digest, **not** Python's salted built-in `hash()`; do not depend on worker ID, task dispatch order, global RNG consumption, process PID, wall time, or directory iteration order. Fix tie-breaking among modes and paths. Use one BLAS/OpenMP thread per worker; document any remaining platform-dependent numerics.

### 3.2 Runtime safety must remain independent

Use a **generous emergency process watchdog** to ensure no hung process can damage the machine. The previous 2-second per-plan and 12-second per-query clocks **cannot decide a canonical 0** and cannot cut off shortcutting. The overall smoke must remain bounded and supervised (previously 240 seconds; choose an explicit safe global ceiling based on preflight, and document it).

- If a **scientific work budget** finishes: `completed=true`, `attempted=true`, and `label∈{0,1}`.
- If **emergency wall/thermal/OOM/worker shutdown** interrupts before completion: `completed=false`, `label=null`, `interruption_reason=...`. On resume, retry with exactly the same deterministic scientific policy. Do not silently enlarge the work budget.
- If a witness is certified and fully serialized **before** a later interruption, preserve it only if the declared query-success policy allows early success; for *mode coverage* completion and canonical witness-set comparison, mark incomplete collection separately and do not claim the exhaustive bounded mode pass finished.

Do not permanently change baseline `p16_motion.py`, old archive configs, or old `planner.py` semantics for other experiments. Use the narrowest opt-in smoke-specific planner/teacher path, with deterministic budget configuration and a new `placement_protocol_id` and `budget_hash`.

## 4. Correct and preserve mode accounting, labels and witnesses

Each eligible object–destination has `modes_total=2304` (if all 48×48 pair identities exist in that source config) and mutually exclusive per-pair screening/attempt states, with an actual mask or enum that distinguishes **hard-screened**, **motion-attempted**, and **not motion-attempted**. Motion-attempted modes must then distinguish verified success from operational failed attempt, and include exact tested work. If pick-mode checks are inherited from `screen_pick()`, recompute all counts under the corrected post-grasp semantics—**the old count of 70,825 geometric rejections cannot be carried forward unquestioned.**

For consistency, either define a disjoint 3-way base partition:

`total = hard_screened + motion_attempted + not_motion_attempted`,

and refine `motion_attempted = success + attempted_failure`; or define a documented, disjoint 4-way partition. Do not add overlapping subtotals and accidentally double-count. Report `n_mode_witnesses` and `n_unique_trajectory_files` separately; reused historical trajectories may count as verified evidence even when no new planner call is launched, but must have explicit `evidence_source=REUSED_REVERIFIED` and consistently placed mode accounting. Same mode can have multiple distinct paths.

At query level, use `attempted`, `completed`, `eligible`, `label`, `failure_phase`, `negative_kind`, `negative_scope`, `work_budget_consumed`, `safety_interruption`, and `witness_refs`. For positive labels require **at least one** verified path; for completed zero labels require the declared deterministic query schedule to have terminated without any positive. Report unattempted viable modes separately from completed negative evidence. Mode coverage or generative density is not a calibrated probability.

Store simple sidecars; reuse the prior smoke's readable JSON + compressed NPZ layout if valid. The original data must remain immutable. Each trace should be referenced by a stable **content hash over canonical arrays and relevant geometry/protocol identity**, not a filename derived from wall-clock time. Write atomically, verify durable references, and clean orphan artifacts **only when no worker can still commit a reference**. Keep IDs, schema/protocol version, robot/source/scene/config hashes and original-root split (`null` if genuinely unspecified). Do not invent dataset train/val/test splits.

## 5. Freeze and rerun the *same tiny smoke roster*

**No new randomized scene generation; no new root roster.** Read the original predeclared 35-query selection, including four root IDs/classes K0–K3 and the intermediate edited-scene query. Preserve each root, object, destination and query-key identity, unless an item was provably malformed—in that case version the roster and explain precisely what changed. Do not select replacement tasks to make success look better.

### 5.1 Preflight and scheduling

- Local machine **only**. Inspect allowed logical CPU IDs, NUMA/physical core topology, memory, swap, background load, available storage, and thermal-sensor availability. Prefer physical-core affinity for correctness and then the predeclared 28-logical-CPU stress condition.
- **Serial reference:** one worker, fixed roster; include the prior Pass A query. Must finish under deterministic policy and write a complete record even if slow.
- **16-worker comparison:** same frozen roster and seeds, at least two independently fresh run directories; if there are fewer than 16 physical cores available, select the safely available number and report it precisely.
- **28-worker stress:** same frozen roster and seeds, at least two independently fresh run directories, **only if** safety preflight accepts 28 logical CPUs and temperature/headroom constraints. Up to 28 worker processes total, each one numerical thread. Never mistake affinity or `nice` for a hard aggregate cgroup CPU quota. If cgroups are unavailable, log `hard_cpu_quota=false` and use strict affinity + process count, with monitoring; do not claim an enforced 28-CPU quota.
- The total number of independent physical queries must remain the original smoke roster (normally 35, with eligibility evaluated per edited scene). Repeating that roster for reproducibility is allowed; broadening the corpus is not.

### 5.2 Thermal and resource gates

Previous run's reported CPU temperatures peaked at **87.8–91.5°C**, near the stated **95°C** abort threshold. Use conservative safeguards: abort/pause before hardware thermal safety threshold, never override firmware controls. Suggested policy: log a warning above 85°C, stop launching fresh tasks at a user/configurable threshold no greater than 90°C, and cancel safely if overheating persists or temperatures approach the machine's validated maximum. If temperature sensors are unavailable, document that limitation and choose a safer worker count. Avoid unbounded retries. Track CPU utilization, per-worker RSS, aggregate memory, swap events, disk space, process hierarchy, and whether a cgroup limit was really enforced. All safety-stop outcomes are **interrupted / no training label**, not zero.

A reproducible 16-worker scientific run plus a safety-blocked 28-worker stress test is **not** evidence that 28-worker execution passed. Report each gate separately. Do not sacrifice hardware safety to force an overall `SMOKE_PASS`.

### 5.3 What to compare between fresh repeats

Use a **canonical semantic fingerprint**, independent of wall time, process ID, scheduling order, log order, JSON indentation, NPZ ZIP timestamps or image encoding timestamps. Hash or compare sorted query keys, eligibility, attempted/completed flags, canonical binary labels, mode status/attempt masks, deterministic stop reasons and work counts, ordered witness identities and path arrays. For real floating-point arrays, require bitwise equality where deterministic code guarantees it; otherwise define a **tight, declared numerical tolerance** and hash a documented canonical rounding/serialization representation. Do **not** use a loose tolerance that masks physically different trajectories.

Compare **serial vs 16 vs 28** on the same fully completed queries. If workload makes one run safety-interrupted, report incomplete comparison rather than forcing zeros. Record raw timing and resource logs separately as intentionally variable. For every canonical mismatch, output a concise per-query diagnostic diff (seed, mode order, work counts, first differing waypoint/phase, interruption flag, and policy hashes).

### 5.4 Resume/recovery

Perform one deliberate interruption after some completed query records are atomically committed. Resume **only** missing or genuinely incomplete work under the same scientific configuration. Prove committed records' canonical checksums are unchanged. Prevent duplicate attempts and witnesses; ensure orphan cleanup runs after worker joins/terminated writer checks. Include a post-resume full re-open and physical replay audit.

## 6. Tests, figures and gates

Test at least these cases:

1. Deterministic seed/mode order/work budgets independent of worker index and process start order.
2. A failed RRT extension consumes a deterministic attempt counter; a work-budget cutoff cannot be mistaken for a certified collision.
3. Shortcut behavior is deterministic and **not** truncated by scientific wall time.
4. Already-grasped placement can be considered when pick approach is blocked; no root-state pick filter may veto it.
5. Correct `held_local`, attachment/finger contact, source/destination consistency and phase-aware independent replay for positive placement-only witnesses.
6. Binary outcome only for **completed eligible** queries; emergency interruption or never-attempted task has `label=null` and is excluded from training labels.
7. Same root + edited-prefix lineage and sibling immutability; initial occupied-cell case ineligible versus edited-scene available case correctly distinguished.
8. Exact 48×48 count and mutually exclusive mode category reconciliation; reused witness provenance does not break accounting.
9. Atomic files, idempotent completed-run resume, crash-and-resume with no dangling references after safe cleanup.
10. Canonical scientific fingerprints match across **fresh** repeats at different worker counts, while runtime/resource logs are explicitly excluded.
11. Original selected scene/witness data hashes unchanged and historical replay still works. Run relevant existing tests; distinguish pre-existing missing `runs/` fixtures from regressions. Do not edit the legacy test to hide the failure.

For visuals, regenerate actual 2D scene/mode placement maps with distinct visual encodings for attempted positive, attempted zero, excluded/ineligible and not motion-tested. Save at least one full articulated 3R robot placement-only GIF from a real recertified trajectory (including held-body motion and release/retreat). Mark illustrative diagrams or unit-test fixtures, if any, as **not** physical experiment evidence.

## 7. Output layout and immutable provenance

Use a **new versioned output directory** (example only; match the actual local layout):

```text
gh-yadu-iiith/planar_2d/dataset_relocations_v1/
  smoke_20261106/                       # original failed run; NEVER overwrite
  smoke_repro_v2/
    manifest.json                       # protocol, roster, root/config/robot/code hashes
    roster.json                         # original frozen 35 queries and eligibility context
    serial/                             # separate fresh run; semantic record/witness refs
    workers16_repeat1/
    workers16_repeat2/
    workers28_repeat1/                  # only if safe
    workers28_repeat2/                  # only if safe
    comparisons.json                    # scientific fingerprints and per-query diffs
    visuals/                            # scene-backed, labeled evidence only
    smoke_fix_report.md                 # result, commands, data, diagnostics, verdict
```

Avoid gratuitous extra Python files. Reuse the existing smoke CLI, checker and tests. If a small implementation split is essential, name one clear responsibility and justify it in the report. A change to foundational `planner.py` should be backwards compatible, opt-in, and covered by legacy tests and source diffs.

## 8. Acceptance and stop conditions

A **repaired scientific smoke gate** is `PASS` only if:

- [ ] Correct conditional-on-grasp semantics were inspected and tested (no pick-approach contamination).
- [ ] The frozen small roster completed under deterministic work budgets with correctly committed binary labels; unattempted/interrupted records stayed unlabeled.
- [ ] At least one authentic, independently reverified placement-only witness is stored and reopened.
- [ ] Mode counts and provenance reconcile in every record.
- [ ] Fresh repeated **serial and 16-worker** scientific outputs agree exactly under the declared canonical comparison; 28-worker comparisons also agree **if those stress runs safely complete**.
- [ ] Resource safety, temperature behavior, and actual enforcement (or lack) of CPU quotas are faithfully logged; no orphan workers/witness references.
- [ ] Interrupted/resumed outputs pass, original 2D dataset unchanged, relevant regression tests pass (excluding clearly established pre-existing missing-fixture failures).
- [ ] Evidence figures and a detailed report are readable; no data-generation/training stage was started.

**Report separate sub-verdicts:** `SEMANTICS`, `REPRODUCIBILITY_1V16`, `REPRODUCIBILITY_28_STRESS`, `RESOURCE_SAFETY`, `STORAGE_REPLAY`, `DATA_INTEGRITY`; each `PASS/FAIL/BLOCKED`. Overall `SMOKE_PASS` requires **both** the core scientific gates **and** two safe, canonical-matching 28-worker stress repeats, because 28-worker reproducibility was the original failed acceptance criterion. If the core scientific gates pass but 28-worker testing is prevented by a genuine safety/resource limitation, report `SMOKE_BLOCKED` overall with `CORE_SMOKE_PASS` explicitly noted; **do not** claim 28-worker validation. Use `SMOKE_FAIL` for a demonstrated scientific/implementation mismatch and `SMOKE_BLOCKED` when necessary evidence cannot safely be collected. Do not overrule temperature or resource protections to force a pass.

**STOP after the fixed smoke experiment.** No 5,000-root labeling, no 3D, no new randomized scenes, no cVAE/flow training, no X/Y training/evaluation or architecture modification, no remote 64-core server, no scheduled/background campaign. Do **not** commit, push, merge, or clean the existing worktree without explicit approval; instead provide exact local diff, commands, output paths and the final sub-verdicts. Keep all failure evidence.

## 9. Required final report outline (`smoke_fix_report.md`)

1. **Executive verdict** with all six sub-verdicts and precise meaning of a completed operational 0.
2. **Source/worktree audit**: branch/SHA, code diffs, old vs new policy hashes, what was actually wrong.
3. **Label semantics**: post-grasp initialization, excluded pick phases, mode selection/aggregation, coverage limits, exact witness validity.
4. **Determinism implementation**: work counters, seed derivation, deterministic mode order, shortcut handling, emergency watchdog separation.
5. **Frozen roster**: all root IDs, prefix queries, objects/destinations, eligibility, no test-selection after outcomes.
6. **Result counts**: attempted/completed, 0/1/null, unique modes/pairs, attempts, negative_kind, newly produced/reused verified witnesses, all invariants.
7. **Repeat comparisons**: serial / 16 / 28 scientific fingerprints, mismatches or none, resume test and why variable timing is exempt.
8. **Resource report**: allowed logical/physical CPUs, process/thread cap, CPU-quota enforcement, per-run wall and CPU time, peak RSS/free RAM, swap, temperature and any safety intervention.
9. **Data integrity and regression tests**: hashes, `pytest` details, old fixture-path caveat, original corpus unchanged.
10. **Visuals and artifact inventory**: actual relative file paths, genuine-scene maps and replayable GIF.
11. **Remaining limitations and STOP statement**: no inference about untested 2,304 modes or universal infeasibility; no authorization to scale.
