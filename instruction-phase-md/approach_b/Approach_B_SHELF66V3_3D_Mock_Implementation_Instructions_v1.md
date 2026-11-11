# Approach B — SHELF66V3 3D Placement Extension: Mock Implementation and Validation Contract v1

**Status:** implementation instructions, **not** evidence of a completed 3D mock.  
**Target host:** `nav@gvlab`, Intel Xeon Gold 5317, 12 physical cores / 24 logical CPUs.  
**Absolute CPU restriction:** no more than **18 logical CPUs / 18 CPU-bound workers for the combined project workload on this host**. Start smaller; 18 is a ceiling, not a required worker count.  
**Allowed:** inspect, snapshot, implement a minimal placement-only 3D teacher, run bounded development tests/mock, verify outputs, produce a launch-readiness assessment.  
**Not allowed:** launch any full 3D placement-label collection, continue/modify the existing source-scene generation without permission, train sampler or X/Y, change the original 3D dataset, merge/push branches, or claim the mock passed on simulations not actually run.

## 0. Source of authority and frozen scope

Read **all** of the following before implementation:

1. `final-fixed-methodology-1.pdf` (final Approach B): §§5, 7, 8, 14. In particular, `V_place(S,o,d;Pi_place)` assumes a successfully held object and tests **carry → place/release → retreat** under a pinned robot/budget policy. A placement label is **not** an X/Y repair label; likelihood is **not** calibrated feasibility confidence.
2. Repository `Narendhiranv04/rss-ebm-infeasibility`, branch `yadu/dataset-3d`, at least audit commit `8032ad0bf842a490897a8247ee46312036c12546` (2026-11-06). Do not assume this snapshot matches the live server.
3. Shelf implementation: `gh-yadu-iiith/shelf_6x6_open_sides/README.md`, `scene/shelf_scene.py`, `scene/rrt_connect.py`, `scene/rrt_star.py`, and `dataset_bd_classquota_without_home_position_no_overpass/{README.md,selected.json,code/shelf66_v3/{bd_shelf.py,bd_3dt.py,bd_3dt_plus.py,run_shelf66_full.py,none_audit66_v3.py}}`.
4. Existing 2D extension for **design patterns only**: `gh-yadu-iiith/planar_2d/dataset_relocations_v1/code/{placement_smoke.py,placement_teacher.py,launch_plan.py,launch_runner.py,launch_check.py,launch_guard.py}` on `naren/2d-dataset-relocation`. Do **not** import its planar robot geometry or transfer its specific grasp/RRT budgets.
5. Existing older 3D open-tabletop dataset `gh-yadu-iiith/open_tabletop/dataset_bd_classquota` for a **separate contrast only**. Do not mix its 8×8, 8-azimuth teacher with the 6×6 shelf sidecar.

**Repository snapshot facts, to verify live:** the SHELF66V3 pushed snapshot selected **1,492 of 2,500** intended roots: NONE 3, K0 511, K1 357, K2 357, K3 264, K4 0. In the latest pushed version the shelf generation was still in progress. The old open-tabletop dataset separately reports 1,225 selected scenes spanning K0–K4. The target of this assignment is the **shelf, not the open tabletop**. K4/NONE shortage is a parent-dataset-generation issue, **not** a reason to fabricate new roots or stall a mock on valid K0–K3 scenes.

## 1. First gate: audit what exists on `nav@gvlab` without disturbing ongoing work

Before writing code or launching workers:

- Identify live dataset location(s), active SHELF66V3 process(es), owner, run logs and current status. The historical server script points to `$HOME/yadu_bd/runs/3d_dataset_v2_no_overpass/shelf_6x6_open_sides/without_home_position/dataset_2500_raw_shelf66v3`; **discover/verify** this path, do not assume it for `nav`.
- Read `selected.json`, `raw/PROGRESS.json`, ledger, valid raw roots, and every witness reference. Independently compute: selected roots by class, raw root/witness count, duplicate IDs, missing/corrupt NPZ, teacher version mix, unsafe/excluded roots, accepted-but-unselected roots, and active generation progress. Report these separately. GitHub snapshot != live ground truth.
- Verify `SHELF66V3` finger pre-shaping, `RETURN_TO_READY=False`, `NO_OVERPASS=True`, arm ceiling, geometry, version hashes, 6×6 lattice, xArm7 7-DoF model, 16 azimuths × 2 height levels = 32 grasp poses. Check any older V2 roots were re-taught and selected status follows V3 protocol.
- Check actual CPU affinity/cpuset, `lscpu -e`, `os.sched_getaffinity(0)`, physical/SMT topology, current CPU and memory load, free disk/inodes, mount type and write permissions, available sensors, cgroup limits if any, MuJoCo execution in headless mode, and Python 3.10 / MuJoCo 3.16.0 / NumPy 2.2.6 compatibility. Do not alter the environment used by active generation.
- **18-logical-CPU absolute ceiling applies across all concurrent project workloads.** If source generation is using 18 logical CPUs, do **not** launch the mock concurrently. Report this as `MOCK_BLOCKED_BY_ACTIVE_SOURCE_GENERATION` and require the user to stop/allocate the active job. Do not send a stop/kill signal to pre-existing jobs without authorization.
- Any external processes whose CPU usage is unknowable are an environmental caveat; neither CPU affinity nor `nice` is a hard resource quota. Prefer an authorized cgroup/cpuset quota where available; otherwise enforce process/thread/affinity limits and instrument aggregate CPU use.

**Deliverable:** `audit/live_source_inventory.json` and a concise readable inventory. Any missing root/witness or unexpected protocol mix must be resolved or excluded with provenance before pilot sampling.

## 2. Preservation, versioned workspace, minimal file design

Create a **separate** 3D sidecar workspace, e.g. `gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v1/` in a new worktree/branch or separate controlled checkout. Do not write under the source dataset's `raw/`, `code/`, `selected.json`, ledger, or active generator output. Freeze a read-only **snapshot manifest** (or immutable local snapshot where necessary); original root/witness SHA-256 hashes and source Git commit must be saved.

Suggested limited file layout (adapt only when needed):

```
dataset_placement_extension_v1/
  README.md
  code/
    placement3d.py          # post-grasp setup, candidate screening, 3D teacher
    plan3d.py               # lineage splits, geometry-only query roster
    run3d.py                # bounded worker/safety/resume coordinator
    audit3d.py              # replay, work counters, comparisons, coverage/forecast
    test_mock3d.py          # focused regression tests
  mock_v1/
    configs/                # frozen experiment/policy/run hashes
    roster.jsonl.gz
    split_manifest.json
    pilot_*/                # audited bounded runs only
    figures/                # scene stills, trajectory GIFs, resource traces
    MOCK_REPORT.md
    RUNBOOK.md              # future preparation only, no enabled production launch
```

Keep functions small and cohesive; target ~120–280 lines per new `.py` where sensible. Never create dozens of one-function modules. If the existing scene implementation is large, **wrap it**; do not refactor unrelated 2,000-line physics code just for line limits.

## 3. Scientific event definition — mandatory

The single placement-only trial is:

`V_place(S_hyp, object, destination/support_pose; Pi_place_3d)`

**Intervention:** object is already held in one declared, valid **post-grasp** 3D state (specific xArm7 q, grasp height/azimuth, IK branch, gripper width and object–gripper transform). The teacher tests:

1. Valid held-state and attached-object / gripper / arm collision configuration.
2. Safe lift and **carry** through the declared no-overpass/arm-ceiling shelf geometry.
3. Put-down on the correct shelf support, **release**, and post-release settling.
4. Straight/local **retreat** with arm/gripper collision safety; stable object at requested shelf cell/pose; no other object displaced or damaged.

**Explicit exclusions:** initial robot-to-object free move, pick approach, opening fingers before grasp, grasp closure, success of picking from the actual scene, connecting between two actions, resetting to home, returning to `q_ref`, reaching T's goal, or deciding an obstacle ordering. The conditional intervention can initialize a valid held state by a documented simulation mechanism. Do not count an inaccessible pick as a placement negative.

**Critical:** simply cutting the `approach`/`close` prefix off an existing `plan_pick_place()` trajectory does NOT automatically produce a valid standalone MuJoCo trial. Specify how the simulator instantiates the attached object/grasp transform, gripper joint state, robot q and contact state. Re-certificate those configurations, execute only the placement phases, settle, and independently validate before labeling `1`. If a correct held-state execution mechanism cannot be implemented, declare `SEMANTICS_BLOCKED`; do not silently substitute full pick-and-place labels.

**Mode identity:** shelf allows 16 azimuths × 2 grasp heights = 32 nominal grasp poses; each may yield up to 4 allowed IK branches. Enumerate and account for nominal/IK-invalid/held-invalid/geometry-invalid/valid/motion-tested/unresolved/verified modes. **Do not manufacture 32×32 independent source/place grasp pairs:** carry must preserve a physically consistent hand-object attachment; source and destination IK and approach geometries may constrain the same grasp mode. Count the actual attempted *(grasp pose, branch, placement)* configurations, not a misleading Cartesian product.

**Label semantics:** completed finite-policy trial gets `1` iff at least one permitted tested mode passes all physical verification gates; otherwise `0` with precise failure scope. Distinguish geometry-certified negatives from bounded planning failures. Static illegal/occupied proposals and interruptions are **unlabeled**, with reasons, not third supervised classes. Wall-clock, memory, thermal, admin or sensor cutoffs **never** create a binary `0`. Never call `0` a proof of unlimited 3D impossibility.

**Target independence:** candidate destinations are chosen from legal shelf supports, not from T's goal, intended blockers, known parking set, historical minimal repair, K label, or X/Y outcomes. A legal target goal cell is a valid destination candidate for an obstacle (if physically placeable). Do not use old B/D outcomes to create privileged positives except as separately flagged auxiliary data. Hypothetical edits are **object-only counterfactual arrangements**, not automatically physically reached robot states.

## 4. 3D planning policy: benchmark; do not copy 2D budgets

Existing shelf teacher calls `plan_pick_place()` with up to **5,000 RRT-Connect outer iterations** and may invoke expensive IK, joint-space free moves, planar carry RRT and MuJoCo collision checks. The top-level `_connect()` contains additional extensions within one outer iteration; therefore **RRT iteration count alone is not a complete measure of search work**. The existing stage includes 300 shortcut attempts in `rrt_star.py` as well. Preserve source behavior as a reference; version your placement-only implementation separately.

**Freeze a two-dimensional budget comparison before examining outcomes:**

- **Candidate grasp modes:** first 4, 8, 16, 32 modes from a predeclared, deterministic but azimuth-/height-/branch-diverse ranking; nonvalid modes screened separately. Candidate count refers to a precise scheduling unit and is not silently inflated by branch retries.
- **Planner effort per scheduled mode:** initial comparison 500, 1,500, 5,000 RRT *outer iterations*; additionally record actual failed extension attempts, CONNECT steps, collision evaluations, IK attempts, shortcut work and CPU time. If possible enforce nested **work-counted** ceilings (not seconds) so reruns are load-independent.
- **Adaptive candidates (pilot only):** e.g. `(4 modes, 500 RRT) → (8 modes, 1,500 RRT) → (16 modes, 5,000 RRT)` on unsolved queries; a **stronger reference** may test up to 32 valid modes with 5,000 iterations, but only on a small, predeclared reference subset. These are **test proposals**, not the authorized production policy.
- Avoid comparing a cheap policy with a reference that has fundamentally different contact, collision or verification rules. A reference success is relative to its own finite policy, **not** a physical ground-truth oracle.
- Prefer reusing deterministic prefix attempt results within the same policy comparison where semantically valid; verify an independently executed shorter policy against replay/virtual-prefix accounting. Freeze per-mode seeds independent of worker ID and scheduling order.
- Separate costs of static screening, postgrasp IK, RRT carry, trajectory certification, MuJoCo execution/settling, replay, packing. Distinguish saved-witness count from distinct successful modes.

**Failure mode to prevent:** deriving a zero from “time remaining in this query” while worker load varies. Emergency CPU/wall timeout means **interrupted/no observed label**; it must be safely retryable. If a strong reference exceeds safety budget, record censoring and exclude from missing-positive denominator rather than interpreting its incomplete result as `0`.

## 5. Small, predeclared development mock (never the full extension)

All physical pilot queries must use **training roots only**, fixed by the root-lineage split before teacher calls. For the first mock, start with at most **20–24 selected K0–K3 roots** (roughly balanced across K classes; use distinct parent-family groups). If NONE has a few confirmed roots, audit them as exploratory cases but do not enforce missing class quotas. Never put any test/validation root into development. Include varied obstacle counts and source/goal regions.

Define **at most ~8–10 physical placement queries per root**, yielding a **hard cap of 240 distinct development placement queries** in the first mock. These include:

- Root scene (zero edits), **one-edit** hypothetical scene, and **two-edit** hypothetical scene (where valid/representable).
- Near, mid, far, vacated-cell, and at least some geometrically difficult/legal placements. The roster must actually contain mid/far examples in edited scenes; do not repeat the 2D runtime-extrapolation problem.
- Different movable objects, object types (box/cylinder), side-grasp orientations and shelf rows/columns.
- **Static ineligible contrasts** as separate, unlabeled records (occupied/unsupported/out-of-bounds), counted but never sent to motion planner.

Define two reproducible subsets **before running**:

1. **Broad pilot:** all ≤240 eligible queries at the initially selected modest placement policy, spanning all strata.
2. **Stronger-reference subset:** at most **40–60 fixed queries**, stratified by root class, edit depth, source/destination bands, object shape and difficulty. Escalate grasp/RRT budgets only here. The subset cannot be chosen post hoc solely from successes. You may add a prespecified failed-query diagnostic supplement, but report it separately from unbiased paired comparisons.

Reserve a few deterministic unit fixtures using **training roots only**: inaccessible original pick but valid held-state placement; genuinely obstructed held-state carry; release/settling failure; vacated cell after edit vs same occupied cell before edit; target-goal-cell destination; two-edit scene with exact descendant hash; valid negative after exhausting declared work budget; admin interruption remains unlabeled. Build synthetic fixtures if genuine selected roots cannot supply one, clearly separate them from statistical pilot counts.

## 6. CPU policy and host-safety experiments

The server has **12 physical cores and 24 logical CPUs**. The instruction is **at most 18 logical CPUs** for the combined project's CPU-bound work at all times. No assumption that 18 workers are optimal.

- Run serial, then **8, 12, 16 and 18** worker sweeps on matched small fixed query subsets. Compare *verified queries per wall-second*, CPU-seconds/query, memory peak, context switching, completion-tail effects, system load, thermal behavior (only if sensors are available), and interference with other server users.
- Production preference should be the **fastest safe measured configuration**, capped at 18. If 12 physical-core workers beat 18 hyperthreaded workers, select 12.
- A worker must use one logical CPU under an allowed affinity mask, one BLAS/OpenMP/NumPy numerical thread, and no nested process pool; global process and descendant count must be audited. Reserve ≥6 logical CPUs outside the chosen 18-worker mask when all 24 are available. Respect narrower cgroup affinity if present.
- Fail closed on runaway processes, memory/swap pressure, disk headroom, planner worker death, excessive load or changed host policy. Never lower the limits just to pass. If hardware temperature sensors are unavailable, state that explicitly and use alternative conservative host-safety gates rather than inventing Celsius readings.
- No `sudo` system-wide CPU-boost/power change on shared server without explicit authorization. Laptop's AMD boost-off solution must **not** be copied as a Xeon default.
- For safety, use a **small test subset for worker-count sweeps**, then repeat the chosen configuration twice on the same predeclared pilot. Avoid repeating every expensive strong-reference query for each worker-count variant; compare canonical overlapping queries.
- If the original shelf generator is still running, **do not consume CPUs until its allocation is explicitly coordinated**.

## 7. Reproducibility, trajectory semantics and integrity tests

A mock can report `MOCK_PASS` only after the following are backed by actual files and replayed evidence:

1. **Scientific reproducibility:** canonical label, mode status/masks, deterministic work counts, exact attempt selection/ordering and witness trajectory content agree across serial vs parallel runs and two independent selected-worker-count runs. Wall time, CPU scheduling, temperature and monitor timestamps are expected to vary and are excluded from scientific fingerprints.
2. **Physical witness:** for every stored positive, MuJoCo execution/replay verifies the post-grasp start, actual 7-joint arm motion, gripper width/attachment, no-overpass, arm ceiling, place/release, stable supported object, no other objects moved, and collision-free local retreat. The witness is **not** merely a kinematic plan or a trajectory GIF.
3. **Negative audit:** operational-zero kind/scope/phase, attempted mode budget, verified static screen reason and tested/untested mode counts reconcile. Ensure no `None`/incomplete outcome is trained as 0.
4. **Interrupt/resume:** kill **only test-owned** worker process group midway, retain committed hashes, resume on the same frozen policy, reproduce uninterrupted canonical output. Do not kill original generator or other users' processes.
5. **Storage:** complete per-root JSON + compressed NPZ and content-addressed witnesses; `q` arrays shaped `(N,7)` with phase/attachment/gripper/object-state evidence, offsets preserving segment alignment. Source B/D witnesses use `q`, `segment`, `carry_xy`, `phases`: keep a documented **compatibility converter**, not an unsupported assumption these arrays already mean placement-only trajectories. Deduplicate by scene/policy/actual trajectory, not file name alone.
6. **Source integrity:** SHA-256 before/after of selected roots and referenced witnesses, original selected manifest and ledger unchanged; no writes to active generation paths; no test/val query; no generated new original scenes.
7. **Split/leakage:** lineage groups closed across splits. Root and all hypothetical descendants share the same split. Archived role/parking/solution metadata must not enter candidate-selection features.
8. **Planner/finger bug regression:** explicitly demonstrate that a formerly too-wide **fully open** finger collision check is not used by the new placement teacher, and the held-state gripper configuration is physically valid. Preserve SHELF66V3 model/protocol identity.
9. **Visualization:** render representative source layout, hypothetical edited layout(s), a true xArm7 animated carry/release/retreat witness, negative collision/failure case, budget/mode coverage plots and throughput/CPU-memory traces. Generate GIF only from the verified artifact (not as a substitute for verification).
10. **Original scene baseline:** re-open/replay a small set of existing B/D source witnesses unchanged. If a scientific result differs, analyze whether environmental dependency or physics initialization caused it before continuing.

## 8. Predeclared scientific and engineering gates

Freeze these rules in `mock_v1/configs/selection_rule.json` **before** labeling:

- **Semantics:** zero forbidden pick-phase/target-task checks in the placement label; at least one pick-inaccessible but held-placeable fixture tested where feasible; all stored positives physically verified; no unverified trajectory admitted.
- **Determinism:** 0 mismatched canonical outcomes on every shared completed query across repeated workers/serial; nested smaller-budget schedules agree with independently rerun shorter schedules.
- **Coverage:** record examples per K class (available K0–K3), 0/1/2 hypothetical edit depth, near/mid/far/vacated, box/cylinder, and collision-density bands. If a stratum has no samples, mark `COVERAGE_BLOCKED`; do not extrapolate to it.
- **Label-quality:** for paired queries complete under reference, report relative missed-positive fractions and **Wilson 95% confidence intervals** overall and by eligible stratum; track positive/negative diversity by distinct parent lineage and negative kind. Choose the smallest policy meeting **predeclared** thresholds. Do not assert population-level error bounds from 40–60 references; mark confidence limits clearly. Prefer an adaptive policy if it recovers meaningful positives at modest extra CPU cost.
- **Safety:** all test-owned processes together remain under the 18-logical-CPU ceiling; resource gates pass without forced overrides. Two repeated runs at chosen worker allocation finish cleanly.
- **Storage:** all packed witness records round-trip and reverify; no missing or corrupt reference, no mutation to source.
- **Runtime:** project full workload **only after** enumerating the actual accepted-root roster and its query design, and measuring cost by **(K, root/prefix depth, near/mid/far/vacated, shape, clutter)**. Bootstrap by root-lineage, report expected wall days, uncertainty, conservative buffer, disk and future expansion cost. Do not infer mid/far edited-state cost from root-scene samples without explicit uncertainty and preferably a targeted diagnostic mock.

If gate fails, **fix and rerun only the relevant bounded tests** with a new policy/version. Preserve failed runs and superseded decision files; never silently edit thresholds after seeing results. You may stop with `MOCK_FAIL` or `MOCK_BLOCKED` if scientific correction or host restrictions cannot be resolved within the bounded mock.

## 9. Why budget selection matters and what NOT to do

- Do not copy 2D's 48×48 mode matrix or its 8→32 policy verbatim. The 3D shelf has 32 grasp poses and multiple IK branches, with physically consistent held-object transforms.
- Do not use the entire original `plan_pick_place()` from home/ready as the placement-label teacher; that conflates access-to-pick with placeability. It may be run as a **diagnostic** only.
- Do not treat 5,000 iterations as a justified new placement budget simply because the source B/D teacher used it for an **entire pick-place query**.
- Do not equate a witnessed placement success with target repair success or with downstream X/Y labels.
- Do not draw negative labels from motion attempts that were resource-stopped mid-query.
- Do not build production predictions from an arbitrary subset that lacks the costly scene strata.
- Do not attempt to fill K4 or NONE by relabeling unsupported scenes; parent-dataset K-label completeness is a separate issue.
- Do not train a cVAE, flow-matching model, calibration/confidence head or X/Y Boltzmann model during this mock.
- Do not store only success labels: preserve the candidate proposal distribution, operational negatives, attempted/untested modes and physical evidence needed for future confidence calibration.

## 10. Required outputs

At the end supply real paths and audit hashes for:

- `LIVE_SOURCE_AUDIT.md` and `audit/live_source_inventory.json` (what was actually on `nav@gvlab`, not just what GitHub once held).
- `README.md` defining action semantics, candidate roster, held-state and witness contracts, computational policy and source provenance.
- Minimal versioned code and focused tests; command outputs for syntax/tests and actual numeric/physical validation.
- Frozen root-grouped split manifest, candidate roster and pilot selection/budget plan; per-mode work masks and labels.
- `MOCK_REPORT.md`: all pilot tables, budget-quality comparisons, positive/negative diversity, detailed failed fixtures, 8/12/16/18 CPU throughput, resource observations, serial/parallel fingerprints, replay checks, graphics, interruptions, integrity and limitations.
- `RUNBOOK.md`: exact **future-only** commands for metadata preflight, selected 3D mock replay, monitoring, safe pause/resume, and the design of a **disabled/guarded** full-collection launcher. Include no auto-launch hooks.
- `LAUNCH_READINESS_DECISION.json`: `MOCK_PASS`/`MOCK_FAIL`/`MOCK_BLOCKED`, separate semantic/determinism/safety/storage/coverage/label-quality decisions, recommended finite policy and worker count, projected production query count, CPU-hours, wall time and disk, unresolved issues.

**Final verdict guidance:** `MOCK_PASS` means the small 3D teacher/collector is semantically correct, reproducible and physically validated under its chosen finite policy. It **does not mean** the full source dataset is complete, all 3D grasp configurations were searched, model confidence is calibrated, or production collection has already been authorized.

**STOP after the validated mock and report. No full 3D extension collection, 2D production, source-scene generation, model training, push/merge or other research stage without explicit separate authorization.**
