# CLAUDE CODE — Placement-only sidecar smoke test (2D, local CPU, STOP after smoke)

You are working in my existing `rss-ebm-infeasibility` research repository. **Do not assume the current branch, source paths, APIs, or implementation status. Inspect them first.** I am also providing `Approach_B_Placement_Dataset_Extension_Smoke_Plan.pdf` and `final-fixed-methodology-1.pdf`. Treat the new smoke plan as the binding task scope and the November 5 methodology as the authority for Approach B scientific semantics. The included earlier 2D dataset audit is an inspection reference, **not** proof that the current checkout is unchanged.

## Objective — ONLY this scope

Implement and execute a very small, genuinely physical **2D placement-label sidecar smoke test** on my local Linux machine. Aim to exercise **28 logical CPU workers** in its bounded parallel phase *only if* preflight confirms that 28 allowed CPUs and sufficient memory/thermal headroom are available; otherwise stop with a clear preflight report rather than force oversubscription. Confirm that queries, operational binary labels, per-mode accounting, verified robot trajectories, provenance, resumability, and scene-backed visualizations are stored correctly. **Do not launch any 5,000-scene extension, broad labeling campaign, 3D run, sampler training, X/Y training, end-to-end search, or server/SSH run.** Stop entirely after the smoke-test report.

## Read-only audit first

1. Report `git status`, branch, short/full commit, relevant configs, selected 2D scene manifest/root records, archived `raw/witnesses`, grasp and placement mode enumeration, robot profile, teacher budget/termination semantics, scene/trajectory serialization, tests, and installed Python environment.
2. Verify whether the previously reported 8x8 2D lattice and 48 pick / 48 place candidate configurations still apply. In the earlier audit this was associated with the `yadu/dataset-3d` branch at `9e640690`, but do not blindly trust that snapshot.
3. Identify the actual existing full-3R robot/IK/contacts/planner/replay functions. Reuse them; do not create a parallel fake robot or infer physical success from static occupancy.
4. Identify eligible *selected* roots, their existing train/validation/test split, and at least one real matching archived trajectory that might be reused. Do not modify historical datasets or hashes. If required components are missing, report the precise blocker and STOP rather than inventing replacements.

## Frozen labeling contract

- The sampler's event is **placement conditioned on an allowed already-successful grasp/attachment**, not pick accessibility from home, not complete corrective sequence X, and not target restoration Y.
- Declare a versioned `placement_protocol_id` specifying post-grasp initialization, allowed attachment/grasp modes, transport/support/release/retreat conditions, collision checks, planner seed/budget, and success termination.
- **Binary outcomes for every actually attempted placement query:** `label=1` only if a complete, independent verified placement witness is available; `label=0` if the pinned query budget is exhausted or no valid witness is found within that budget, including failed IK/geometry/contact/motion attempts. Preserve `negative_kind`, `failure_phase`, elapsed time, attempts, search-budget flags and `is_certificate` (false for budget failures). This is **operational infeasibility**, not a theorem about all physical trajectories.
- **Do not create a third observed class named UNRESOLVED.** Not-yet-attempted tasks have `attempted=false`, `label=null` or no observed row and are excluded from binary training/evaluation; static-illegal candidate poses may be logged as excluded, outside the eligible placement trial denominator. Never convert missing queries into zero.
- Enumerate and count the nominal pick/place configuration identities (previously 48x48=2304 per object-destination in 2D). Run sound cheap checks and memoized per-pick/per-place checks before bounded full motion planning. Continue past the first success for the **label collection mode** and store every distinct fully verified witness found within the smoke limits. For the smoke, it is acceptable to leave additional physically unattempted combinations masked; it is **not** acceptable to assert that all 2304 modes underwent continuous motion planning. Keep `modes_total`, `modes_geometrically_rejected`, `modes_motion_attempted`, `modes_verified_success`, `modes_budget_failed`, `modes_not_motion_tested` with a reconciliation invariant. If labels at the *mode* level are represented in arrays, a separate `attempted_mask` must distinguish zeros from untested modes.
- Aggregate the object-destination `label=1` if at least one complete placement witness is verified. Otherwise it is `0` after the **declared finite object-destination trial policy** has actually run to its cap. Never conflate mode-success fraction with calibrated probability. A distributional confidence mechanism is NOT part of this smoke test.
- B may be currently ungraspable but become accessible after A: never globally prune object B based on root-state pick failures. Include at least one root-state and one intermediate hypothetical-state placement query where possible; `parent_prefix` and `hypothetical_scene_hash` must be explicit. Hypothetical object edits do not constitute robot execution.
- Existing archived trajectories may be reused as positive evidence **only after verifying exact scene, robot/profile, object, destination, grasp/attachment, collision margin, and completion-policy compatibility**. Otherwise reference them as historical only, not as positive labels.
- Record real robot joint trace, gripper/attachment states, carried-object poses, phase boundaries, start/end q, collision-check/provenance hashes and travel metrics. Never record a fabricated demonstration as physical ground truth. Test-only synthetic round-trip fixtures, if used, must be isolated and marked `SYNTHETIC_TEST_ONLY`.

## Minimal artifacts / code boundaries

Prefer a **single narrowly scoped CLI script plus a small unit test** if existing modules suffice. Only add one extra tiny module if necessary for a clear records/witness serialization responsibility. Do not rename, reformat, or restructure old code. No framework, database, generic worker package or broad refactor. Keep each new Python file approximately 120-280 logical lines where practical; if the real backend requires more, document the smallest defensible split.

Create a new sidecar *only*, e.g. `planar_2d/dataset_relocations_v1/smoke_<run_id>/` beside the immutable original (confirm actual paths before choosing), containing:

```text
manifest.json
records/<root_id>.json
modes/<root_id>.npz
trajectories/<content_hash>.npz
visuals/<root_id>_placements.png
visuals/<root_id>_witness.gif          # only when actual trace is available
summary.json
report.md
```

Record schema must include `schema_version`, `source_root_id`, source/scene/profile/teacher/config hashes, split, `prefix_key`, parent reachability provenance, hypothetical edited-scene hash, `object_id`, `destination_cell`, source cell, support, protocol ID, `attempted`, `label` (binary when attempted), `negative_kind`, failure phase, budget/seed/runtime, all mode counts, and `witness_refs`. Use stable paths, relative references, simple JSON + compressed NPZ, atomic final writes, content-addressed unique witnesses, and deterministic dedup/resume. NPZ must expose typed arrays with shapes/dtypes and phase metadata documented in the manifest. Never include intended blocker/repair metadata as sampler-input features.

## Tiny, predeclared smoke schedule (not a dataset run)

1. **Preflight only:** inventory selected roots; inspect CPU affinity (`os.sched_getaffinity`), physical/logical CPU count, memory available, swap, load, temperature sensors if installed, disk free, Python dependencies, data path writability. Abort on missing requirements rather than silently limiting/exceeding the declared 28-worker plan. Report 28 available *logical* CPU IDs explicitly. Note: the owner's computer may have fewer than 28 physical cores.
2. **Serial correctness pass:** one root, one object, one destination, one worker. Exercise existing full robot/teacher paths and verify labels + trajectory serialization. If a real success is not obtainable within the tiny limit, do not fabricate it; report this as a smoke evidence blocker.
3. **Bounded parallel storage pass:** deterministic predeclared sample from at most **4 selected 2D roots**, at most **2 non-target movable objects per root**, and at most **4-5 legal destinations per object**, with at least **28 independent trial tasks** if possible to exercise all 28 workers. Include near/far and a destination distinct from historical intended repairs. Include **1-2 intermediate edited-scene trials** when existing root data permits, without inventing executed prefixes. Prioritize 1 existing compatible positive witness and 1 failure case. If 28 independent physical tasks cannot be formed, report fewer active tasks instead of fabricating tasks.
4. Use a **hard aggregate CPU budget of 28 CPU equivalents**, exactly 28 Python worker processes maximum, and one numerical/BLAS/OpenMP thread per worker. Prefer cgroup `CPUQuota=2800%` plus taskset to 28 allowed logical CPUs if supported; otherwise report the fallback and enforce an upper worker/affinity bound. Use `nice` but never mistake `nice` for a hard CPU cap. Protect the machine with memory/swap/temp/disk monitoring and a single global run wall-time cap (initial configuration: 4 minutes); worker/process timeouts must terminate and be joined. Do not launch additional hidden subprocesses or GPU workloads. CPU-heavy jobs must not run on a shared SSH server.
5. New smoke-config budget keys must be kept separate from archival teacher configs, with versioned protocol/hash. Suggested *starter smoke limits* (adjust downward if preflight warrants; record actual): <= 8 full-motion pairs per object-destination, <= 2 seconds per attempted motion pair, <= 12 seconds per object-destination, <= 240 seconds aggregate. These are **smoke caps**, not the eventual production protocol. Mode enumeration/geometric screening can count all nominal pairs cheaply without running full planning on all of them.
6. No training, no automated expansion after success, no more roots after the predeclared tiny list, and no production/scheduled/background processes.

## Acceptance tests (must check real outputs)

- Existing tests and archived replay fixtures touched by changed code still pass; old datasets have identical source hashes and remain untouched.
- Reopen every JSON/NPZ/GIF and verify schema version, timestamps, relative paths, arrays/dtypes/shapes, witness references, checksums, non-NaN trajectories, endpoint/attachment consistency, collision/replay provenance and actual saved phases.
- For any verified positive, a matching independently valid stored trajectory exists (do not synthesize one to pass). For an attempted unsuccessful query, binary label is `0` and the exact budget failure/certification provenance survives reopening. No `UNRESOLVED` label; no unattempted query counted as zero.
- Mode counts reconcile and `attempted_mask` is correct; explicitly report the number of 2304 nominal modes that were actually sent to full motion planning vs only screened/not tried.
- Duplicate replay/resume is idempotent: no duplicate witnesses, no changed label on repeated deterministic run, atomic writes safe, and no corruption after interrupted-worker test.
- At least one real intermediate hypothetical scene has provenance if selected roots permit it. It must not be described as a physically achieved state without a complete witness.
- The `placements.png` is rendered from the *actual scene and recorded data*, color-coding attempted `1`, attempted `0`, not attempted, and static-ineligible distinctly. GIF only from a real verified trace; show full 3R links, fingers, carried object and motion phases, not a sliding-disc surrogate.
- Write `report.md` with source commit, exact CLI commands, chosen 28 CPU IDs, worker count, CPU/memory/thermal extrema, root IDs, total requested/attempted/positive/zero/not-attempted queries, per-mode audit, successes and failure reasons, witness counts, file inventory, resume result, images, test results and limitations. Any missing real success or physically invalid archived witness is a BLOCKER, not an excuse to fake the outcome.

## Required finish behavior

After the preflight, serial pass and **one** bounded 28-worker smoke pass, present a concise summary, exact paths to smoke artifacts, validation results, any unresolved *engineering* blockers (not an extra observed label category), and a clear `SMOKE_PASS` / `SMOKE_FAIL` / `SMOKE_BLOCKED` conclusion. **STOP. Do not start full label collection, train cVAE/flow, tune limits, create 3D labels, change frozen X/Y logic, push a production-scale job, or use the remote 64-core server.** Do not schedule anything. Ask for explicit authorization before any next stage.
