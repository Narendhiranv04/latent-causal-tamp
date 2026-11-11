# Approach B — SHELF66V3 3D Placement Mock v2 Closure, Live-Source Sync, and GitHub Branching

**Document status:** implementation and acceptance instructions, not a claim that the v2 work has run.  
**Date:** 2026-11-07.  
**Repository:** `Narendhiranv04/rss-ebm-infeasibility`.  
**Primary execution host:** `nav@gvlab`, reached from laptop via `ssh gvlab`.  
**Source-generator host:** `user1@10.4.25.63` (independent machine; access may be unavailable).  
**Maximum project CPU allocation:** **18 distinct logical CPUs, including coordinators, children and any concurrent project process**. Benchmark indicates **12 workers on CPUs 0–11** is preferable.  
**Default permission:** fix code, perform bounded mock tests, perform metadata/integrity audits, copy source data safely, create a branch and commit/push verified artifacts. **NOT** authorized: full 3D placement collection; full 2D collection; generation/relabeling of original 3D roots; ML training; edits to another user's active source generator; merge to `main`.

## 0. Read before touching anything

Read, in this order:

1. Final methodological authority: `final-fixed-methodology-1.pdf`, especially conditional-on-grasp placement supervision versus whole-sequence X/Y evidence.
2. The existing 3D mock and live-source reports on the pushed branch:
   - `gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v1/LIVE_SOURCE_AUDIT.md`
   - `.../mock_v1/MOCK_REPORT.md`
   - `.../mock_v1/LAUNCH_READINESS_DECISION.json`
   - `.../mock_v1/RUNBOOK.md`
   - `.../mock_v1/validation/analysis.json`
3. Existing 3D code: `code/{placement3d,policy3d,plan3d,run3d,replay3d,audit3d,report3d,test_mock3d}.py`, fixtures, source-conversion logic and frozen hashes.
4. Original SHELF66V3 environment and generator: `gh-yadu-iiith/shelf_6x6_open_sides/{README.md,scene/shelf_scene.py,scene/rrt_connect.py,scene/rrt_star.py}`, `dataset_bd_classquota_without_home_position_no_overpass/{README.md,selected.json,raw/,code/shelf66_v3/}`.
5. Existing 2D v2 artifacts under `gh-yadu-iiith/planar_2d/dataset_relocations_v1/{code_v2/,launch_ready_2d_v2/}`. **Preserve, do not change or launch.**

Latest verified GitHub state when this document was authored:

- `naren/2d-dataset-relocation` exists and includes 2D v2 commit `0ba79986` and the pushed 3D mock commit `3baf50ab`.
- **`naren/2d-object-relocations` was not found** on the remote.
- **`naren/3d-dataset-relocations` was not found** on the remote.
- Earlier source snapshot: `yadu/dataset-3d` at `8032ad0bf842a490897a8247ee46312036c12546` (1,492 selected SHELF66V3 roots and 10,927 referenced witnesses).

Re-fetch references before changes; do not assume branch tips are still unchanged. Never use `push --force`, `reset --hard` on research work, destructive cleanup, or an uncontrolled `git merge` of the large source branch.

## 1. Required GitHub ancestry and normal push workflow

**Requested branch topology:**

```text
existing naren/2d-dataset-relocation (currently verified baseline)
    |
    +-- naren/2d-object-relocations        (requested base alias, create only if absent)
         |
         +-- naren/3d-dataset-relocations (new work, normal pushes)
```

*If `naren/2d-object-relocations` appears before execution, inspect both branch histories and determine if it truly contains the 2D v2 and 3D v1 data. Do not silently replace it.*

**Branch preparation from a CLEAN working tree (commands illustrative; adapt to actual repo):**

```bash
git remote -v
git fetch origin --prune
git branch -r | grep -E 'naren/(2d-object-relocations|2d-dataset-relocation|3d-dataset-relocations)'
git status --porcelain=v1
# If base alias absent AND naren/2d-dataset-relocation is the desired verified base:
git branch naren/2d-object-relocations origin/naren/2d-dataset-relocation
git push -u origin naren/2d-object-relocations
# Only if target is not present:
git switch -c naren/3d-dataset-relocations naren/2d-object-relocations
git push -u origin naren/3d-dataset-relocations
```

If the local worktree is unclean, stop and preserve changes with a separate `git worktree` or patch; **do not stash/drop other users' work indiscriminately**. If the new target branch already exists, fetch it and integrate non-destructively rather than recreate it. Record actual commit SHAs in `BRANCH_PROVENANCE.md`. `git merge-base --is-ancestor <base_sha> HEAD` must pass. Verify `planar_2d/.../launch_ready_2d_v2` remains present and unchanged. Existing v1 mock paths stay immutable; v2 is a sibling directory or clearly versioned code path.

**Normal commits and pushes permitted:** branch creation, v2 scientific/guard fixes, bounded proof artifacts, sanitized server source-data updates. After each coherent checkpoint: `git diff --check`, tests/audit, `git add` only reviewed paths, `git commit`, then `git push -u origin naren/3d-dataset-relocations`. No automated periodic pushing, no merge, no force-push, and no claimed success until remote HEAD and a fresh verification checkout match.

## 2. Non-negotiable scientific contract

For a hypothetical **object-only** scene `S_hyp`, obstacle `o`, empty destination `d`, and valid held-state mode `h`, evaluate physical placement *conditioned on the object already being held*. A positive requires a physically confirmed hold followed by **lift → carry → lower → release → retreat → settle**, including every required contact, clearance, object-placement, stability and neighbor-preservation gate.

**Not part of the placement label:** pick-access/free approach, grasp acquisition from a distant configuration, inter-action arm configuration, target T success, corrective-prefix execution/order, return to ready, or an archived repair solution. Do not let labels or candidate generation depend on hidden `B/D` solutions, `parking`, blockers, roles or target-goal veto. Goal-cell destinations are allowed when physically legal. One-/two-edit scenes are hypothetical and must never be reported as physically executed corrective prefixes.

Definitions:

- `1`: at least one **tested and fully certified** held mode completes placement.
- `0, NEG_CERTIFIED_GEOMETRY`: a documented complete deterministic certificate **under the declared finite grasp/IK model**. Do not silently upgrade this to global geometric impossibility.
- `0, NEG_UNDER_POLICY`: all declared policy work completed without success; preserve `BOUNDED_SEARCH`, `DETERMINISTIC_PLAN` or `EXECUTION` reason and work scope. **Not a proof of impossibility.**
- `unlabeled`: static invalid candidate (`OCCUPIED`, `OUT_OF_BOUNDS`, `SAME_CELL`), `NO_VALID_POST_GRASP_STATE`, CPU/resource interruption, source inconsistency or any noncomplete result. Never convert these to 0.

Use only deterministic, counted planner work to define negative labels; wall-clock timeout or safety stop **must not** become a negative. Preserve 32 nominal poses (16 azimuths × two heights) and source physical constraints, except when introducing a separately named and revalidated protocol.

## 3. Surgical v2 scientific closure — mandatory

### 3.1 Physically validate **all eligible IK branches** within each grasp-mode unit

Current `policy3d.evaluate()` screens branches but tests physical held-state only with `br[0]`; `run_mode()` may accept a plan on one branch and stop after a hold failure. This risks false negatives.

Implement a deterministic `branch` inventory per ranked mode:

- Enumerate source IK candidates in a stable order, maximum four; perform source-consistent checks for each candidate.
- For each eligible branch, instantiate held state, pre-shape fingers, close in place and record physical hold success/failure and the required contact evidence; **do not reject an entire grasp pose because only branch 0 fails**.
- For placement, try branch-specific lift/carry/lower/release/retreat planning and MuJoCo execution until verified or all eligible branches are exhausted at the declared stage. Track branch-specific deterministic failures and budget truncations. Reuse a geometric route only when its independence from the branch is established and tested.
- A grasp *unit* is still **one** ranked pose, not four extra modes. Charge every IK check, hold, plan and execution to its original mode and give branches a separate accounting field; avoid unbounded hidden retries.
- Recheck `NEG_CERTIFIED_GEOMETRY`: show why no eligible physically-held branch in the declared model has an admissible carry endpoint. Any incompleteness/uncertainty remains `NEG_UNDER_POLICY` or unlabeled, never an overstated certificate.
- Update nested-budget virtual replay or replace it with actual reruns when branch retry semantics make old virtual evidence invalid. Include exact real-policy comparisons for representative work-truncated cases.
- Pin a **new teacher protocol ID** and hash all changed source/adapter/scheduler files. Do not mutate or overwrite v1 pilot records.

**Mandatory regression fixture:** construct or find a mode with branch 0 physically held-invalid and branch 1 or later physically held-valid; demonstrate `v1` may reject but `v2` reaches the successful held branch. If no natural fixture exists, add a precise deterministic injected branch-failure unit test plus at least one genuine multi-branch physical execution. Report which is synthetic. Require a second real fixture where a branch plans but fails at hold/execution and another verified branch rescues it, if discoverable within bounded budget; otherwise mark not found, never invent it.

### 3.2 Witness preservation policy

The existing reference verified 149 modes but saved only one witness per positive query. Define two layers:

- **Canonical production**: store every **distinct physically VERIFIED** trajectory encountered within the selected policy's actually attempted modes/branches, including the full planned and executed samples, held configuration, mode/branch identity, attached-object pose and release/retreat phases. Deduplicate by content ID but preserve query↔mode↔branch↔witness associations.
- **Evaluation**: for reference runs, preserve every verified mode/branch witness (or an explicitly audited, documented diagnostic-only cap); do not claim all were retained if capped.

The first positive can still determine the query's binary label and stop further search under `adaptive_v1`. Do **not** run extra grasp modes solely to inflate witness counts unless a separately frozen diversity-collection policy is explicitly approved. Implement atomic per-unit NPZ + JSON + ledger hashes and replay all stored positives. Forecast storage using actual v2 bytes per witness, not v1 estimates.

### 3.3 Gripper structure-check conservatism

The source SHELF66V3 object collision checks pre-shape fingers, but its shelf-structure check retains fully open fingers. Preserve the original source code intact. Implement a diagnostic with matched grasp poses showing differences between default-finger and pre-shaped structure checks.

- If changing the structure collision checker, do it ONLY in a versioned sidecar wrapper with the actual finger joint state set to the held-mode opening and all structure/collision checks covered by tests; then **change protocol ID**, revalidate witness replays, and rerun affected budget experiments.
- If preserving conservative source behavior, label it explicitly in the policy scope and quantify affected poses on the expanded v2 sample. Do not assert it was "fixed".

### 3.4 Reproducibility, leakage, source snapshots

- Immutable v1 artifacts remain readable/replayable under source commit `8032ad0b` even after a live-source update. For old v1 replays, use a separate pinned checkout/worktree or an immutable source reference rather than silently replaying against modified source bytes.
- Geometry-only candidate selection must remain independent of archived `B/D` solutions, parking, roles, blockers, requested K mechanisms and target-goal *filtering*. K is allowed only as a **stratification/reporting field**, never as a privileged input to destination feasibility.
- New roots must not silently reassign old train/val/test membership. **Extend existing lineage groups and split allocations**: same `parent_family_id` or identical layout inherits its established split. If newly added data bridges previously separate groups assigned different splits, fail with a `SPLIT_CONFLICT`; do not silently merge or relabel. New standalone groups use a frozen stable hash rule. Ensure old selections, cross-root duplicates and derived hypothetical scenes do not cross split boundaries.
- Full-dataset validation/test queries stay untouched during the tuning/mock stage. Bounded independent validation examples must come from previously unused **training** lineages.

### 3.5 Safety/collector fixes

- Make `run3d.py` v2 verify **both** the atomic per-root JSON and its full NPZ witness archive, including required IDs/content hashes, **before marking a unit completed on resume**. An absent, truncated, mismatched or orphan NPZ must not be accepted; recover safely and deterministically.
- Freeze source selected-root SHA manifest and the per-root source hashes into the run manifest. Detect changed source/selected data on resume. Check code, configs, roster, protocol, worker policy and source hashes at each resume.
- Fail closed if the CPU-temperature sensor disappears while the job is running or paused; never resume on an unreadable sensor. Capture the sensor identity and error, stop own workers/process group only.
- Constrain coordinator, workers and all owned child processes to a union of **at most 18 logical CPU IDs**. **Default 12 workers, mask 0–11; benchmark 16/18 only if host remains safe.** Set `OMP/BLAS/MKL/NUMEXPR` threads=1; use `nice`, identity-checked monitor, per-query counted work, conservative RAM/disk/swap/temperature stops. No hard CPU cgroup quota was available on gvlab: never claim affinity is a kernel quota. Attempt a genuine tested cgroup if available with permission; otherwise document affinity+monitor limitation, keep <=12 workers for production.
- Worker monitor must terminate the owned process group on error; check parent+children, detect nested workers, preserve checkpoints and explicit stop reason. Never `pkill -f`, kill another user's process, stop an active generator, alter system-wide CPU/power state, or sudo without permission.
- Treat any thermal/swap/administrative interruption as unlabeled, not 0.

## 4. Bounded **v2 closure mock** (not production)

Prefer the same 24 train roots/205 v1 queries for a before/after semantic regression, **plus a predeclared independent holdout** of approximately 12–24 new training roots (about 100–240 queries) enriched for far destinations, 3+ intervening objects, 2-edit contexts, both shapes, target-goal and vacated cells, physical hold edge cases. Do not exceed **48 roots and 500 physical placement queries** in total without asking the user; keep reference rechecks bounded by the actual selected mock and host availability. Keep all original roots untouched.

Freeze these **before** executing any new teacher calls:

- Root/lineage roster and independent holdout hashes, 0 val/test roots.
- Policies and mode/branch scheduling, deterministic seeds, RRT caps, verification tolerances.
- Explicit comparison of `adaptive_v1` (4×500 → 8×1,500 → 16×5,000), **`fixed_4x5000`**, `fixed_4x1500`, optional `fixed_8x5000`, and **`reference_v2`** (all valid units × all eligible held branches at 5,000 RRT iterations, no early stop). `fixed_4x5000` matters because it had zero misses on the old 40-query subset with low virtual cost but was not evaluated on the full old pilot.
- Acceptance gates, including **missed-positive fractions by distance/depth/high clutter**; sample counts and Wilson CIs; CPU and wall time, actual worker sweep, per-mode/per-branch coverage; no cherry-picking based on test outcomes.
- Distinguish *finite reference recall* from physical truth, and do not conflate 0 observed misses with zero population risk. Avoid using a point-estimate threshold as a guaranteed upper confidence bound.

Test sequence:

1. Baseline integrity, 15 existing regressions, new tests for physical branch retry, witness retention and missing NPZ resume, temperature-sensor loss, source hash drift, split preservation, fail-closed production launcher.
2. Replay representative v1 witnesses under the **pinned v1** protocol to verify historical data not broken.
3. Execute real MuJoCo v2 physics under a stable 12-worker allocation, 0–11, once for each frozen mock query. Any policy comparison must be **actually run** or virtual-replayed only after empirical prefix-equivalence proof for the revised branch semantics. Document which is which.
4. Execute at least two independent 12-worker v2 repetitions, a serial subset, a bounded 8/12/16/18 throughput sweep only when safe and no other project load, SIGKILL+resume of **own** process group, fresh-process witness replay and end-to-end certificate/negative audits.
5. Require full source hash integrity, zero split leaks, zero unaccounted modes/branches, exact matching scientific fingerprints across repetitions, 100% witness replay success, no CPU/thermal/memory/disk/monitor safety violations. For nonvalidated classes K4/NONE, declare `COVERAGE_BLOCKED` rather than passing them.
6. Forecast runtime/storage on the *actual tested* source cohort, grouped by K×edit depth×distance×clutter with backed-off strata and root-lineage bootstraps; disclose unavailable strata. Do not claim the original 4.4-hour estimate survives the new branch-search/witness policy unchanged.

**Result**: `MOCK_V2_PASS`, `MOCK_V2_FAIL`, or `MOCK_V2_BLOCKED`. `MOCK_V2_PASS` is not the same as `PRODUCTION_READY` or authorized production execution.

## 5. Safely obtaining and publishing the live server's 3D source updates

Current sources are on **two separate hosts**. From the user's laptop use `ssh gvlab` to access execution host. The original SHELF66V3 generator's launcher points to `user1@10.4.25.63` and:

```text
$HOME/yadu_bd/runs/3d_dataset_v2_no_overpass/shelf_6x6_open_sides/without_home_position/dataset_2500_raw_shelf66v3
```

The `user1` host was **not reachable in the previous mock**. Do not claim the live store is synchronized without confirmed access. Try authorized SSH configuration and connectivity; do not request, print or commit passwords/keys. If unavailable, finish code/mock work using pinned source, publish code/report branch, mark source sync **`LIVE_SOURCE_BLOCKED`**, and provide concrete authorized transfer steps. Do not invent missing K4/NONE roots.

If access is available:

1. **Observe** live process state and store version first. Determine whether generation/re-teaching is still ongoing. Obtain a **consistent, immutable read-only snapshot** (coordinated checkpoint, filesystem snapshot or approved paused copy). Do not read a changing live store as though it were consistent. Never stop other researchers' jobs without authorization.
2. Include all **approved** raw roots, ledger, `selected.json`, `PROGRESS.json`, `EXCLUDED_FIXED_OBJECT.json`, referenced witness NPZ files, code/configuration and source provenance needed for reproducible replay. Transfer to a *staging directory*, not the active original dataset. Use incremental/resumable `rsync -a`/`--partial` or a hash manifest; verify the original and staged manifests match. Preserve source format/paths and object naming. Zero silent omissions.
3. Compare staged data with the GitHub snapshot by id, exact content hash, parent family, V3 teacher/robot/geometry version, label class, and references. Flag changed old root bytes, changed witness bytes, mixed protocol, missing files, overlapping/duplicate lineages, incomplete ledgers, excluded fixed objects, and abnormal classes. Any incompatible mixed dataset must be separated by protocol, not silently relabeled or merged.
4. Preserve a provenance `LIVE_3D_SOURCE_SYNC_REPORT.md` and machine-readable `SOURCE_SNAPSHOT_MANIFEST.json{,.gz}` with exact source host, snapshot time/consistency method, commit parent, selected counts per K, root/witness counts, protocol hashes, new/changed/removed files, missing and corrupt references. Never commit credentials, home paths with secrets, customer/private datasets or unrelated home directory content.
5. **Publish approved snapshot updates** in the *existing* source dataset path so it remains natively replayable, while preserving the prior snapshot reproducible from Git history. Keep the v1 placement mock at its historical source commit; do not overwrite its frozen files. If the live source is incomplete or contains K4/NONE gaps, publish honest partial-state markers; never fabricate quotas.
6. **GitHub size preflight:** use `git status`, `git diff --stat`, a sensitive-file scan, individual file size and total push-size checks. GitHub rejects blobs >100 MB and warns at 50 MB; avoid giant binary/commit batches. If LFS is already configured and approved, use it with verified remote object availability; otherwise chunk transfer *with a documented reconstructible manifest* or declare `PUBLISH_BLOCKED` for oversized data and request approval. **Never silently omit witness binaries while calling the dataset fully synced.**
7. Verify by cloning/fetching the new remote branch into an independent scratch checkout: ensure every selected root and referenced witness is present, loadable and hash-equal, source code/protocol match, V3 scene replays still work. Verify no old 2D files changed and no accidental extra roots/secret files are in the commit.

**If the live generator is still running:** prefer to publish a clearly named stable snapshot with timestamp and explicit `IN_PROGRESS`, not a copy made mid-write. A fully final selection and runtime projection require a consistent live selection, not just the old 1,492-root GitHub snapshot.

## 6. Production preparation is allowed; full collection is not

When the source snapshot is audited and v2 mock passes, implement an **inert guarded** `launch_full_3d.sh` and a versioned collector supporting frozen train/val/test query rosters without tuning on val/test. The original `run3d.py` filters train-only; modify only in a new version with documented test coverage. No production worker may start without all of:

- `--execute-full --confirm <token>` and a matching explicit `production_policy.json` including the user's separately recorded authorization;
- frozen selected-source snapshot hash, root/lineage split, query plan, policy and teacher/collector code hashes;
- mandatory metadata preflight + test suite + disk/RAM/CPU/temperature checks; 0 planner calls from a dry run;
- no active conflicting job and correct CPU affinity ceiling; refusal if sensors unavailable;
- atomic JSON/NPZ/ledger resume validation and fail-closed monitor;
- token matches *current* hashes and is not reusable across changed policy/roster/source;
- no launch on default/no-args invocation.

Run **only refusal and metadata-only dry-run tests**, then stop. A state of `PRODUCTION_READY_PENDING_AUTHORIZATION` is allowed if every test passes; do not start collection, even if asked to "finish quickly" elsewhere.

## 7. Git milestones and deliverables

Work under the new branch `naren/3d-dataset-relocations`. Commit and **normal-push** each coherent completed milestone, e.g.:

- `3d: add v2 branch-aware placement teacher and regression tests`
- `3d: validate bounded v2 mock and freeze policy decision`
- `3d: sync audited SHELF66V3 live source snapshot` (only if truly obtained and audited)
- `3d: add guarded full-collection preflight (disabled pending authorization)`

Keep commits reviewable; do not push failed/intermediate unlabeled results as final, but retain diagnostic artifacts with an explicit `superseded` or `failed` status where useful. Preserve all original 2D data and mocks, and original 3D v1 reports/runs. Do not push huge redundant duplicate reports, caches, virtualenvs, render caches or secrets. Push valid code/metadata even if live data is inaccessible, and make partial status clear.

Required outputs on `gvlab` and, where safe/approved, on the new GitHub branch:

- `BRANCH_PROVENANCE.md` (actual base and HEAD SHAs, aliases created, push commands, remote URLs, no merges);
- `LIVE_3D_SOURCE_SYNC_REPORT.md` and a checksummed source manifest (or `LIVE_SOURCE_BLOCKED.md` with reason);
- `3D_MOCK_V2_REPORT.md`, `3D_MOCK_V2_DECISION.json`, `3D_MOCK_V2_RUNBOOK.md`;
- surgical v1→v2 code diffs, new tests, per-branch witness accounting, failed cases, independent holdout, all positive replay results, CPU/RAM/temperature traces;
- selection justification comparing **adaptive_v1 versus fixed_4x5000** and others on a broad/new reference; register post-hoc policy amendments explicitly;
- live-root/split/roster and forecast, with assumptions and missing K4/NONE strata called out;
- `PUSH_AUDIT.md` with commit SHA(s), remote HEAD, remote clone verification, count/hash checks and any excluded data;
- one final verdict: `MOCK_V2_PASS/FAIL/BLOCKED`, `LIVE_SOURCE_SYNC_PASS/BLOCKED`, `PRODUCTION_READY_PENDING_AUTHORIZATION/NOT_READY`, and **`FULL_COLLECTION_NOT_STARTED`**.

## 8. Hard stop conditions

Stop the affected stage immediately on unexpected source mutation, cross-split lineage conflict, mismatch in frozen code/roster/source hashes, unreproducible positive witness, CPU use outside the declared mask, sustained RAM/swap/disk pressure, loss of monitoring/temperature sensor, inability to verify copied data, or Git push-size/credential concern. Save evidence, report the blocker, and continue with independent safe stages only. **Do not lower scientific or safety thresholds merely to obtain PASS. Do not launch full 2D or 3D collection.**
