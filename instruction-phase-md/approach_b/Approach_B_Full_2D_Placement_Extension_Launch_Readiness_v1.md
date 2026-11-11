# Approach B — Full 2D Placement-Sidecar Extension: Launch-Readiness Contract (v1)

**Prepared:** 6 November 2026  
**For:** Claude Code, Opus 5.5 High, working inside the user's existing local research worktree.  
**Current permission:** Inspect, implement, test, run a small *readiness pilot*, prepare and dry-run the full launch configuration. **DO NOT START THE FULL 5,000-ROOT COLLECTION.**  
**Target local execution:** **25 worker processes on a machine reported to have 32 logical CPUs**, subject to thermal, memory, disk, CPU-affinity and process-safety gates. No lab/server/SSH execution.  
**Scientific authority:** `final-fixed-methodology-1.pdf` (5 Nov 2026), particularly §5, §7–9, §11, §14–18. Historical X/Y model, teacher and archive evidence remain unchanged.

> **Evidence note.** The user reports that `smoke_repro_v2` ended `SMOKE_PASS`: the same 35-query roster was reproducible across serial, two 16-worker, two 28-worker, and interrupt/resume runs; 30 positive queries, four operational zeros, one statically ineligible query, and 222 verified stored placement witnesses. This is **user-provided smoke evidence**, not a source-level verification by this document's author: the new scripts and report are in an uncommitted local worktree, not available on GitHub. Inspect them directly before relying on any detail. Keep both earlier smoke outputs immutable.

---

## 0. Goal and unambiguous STOP boundary

Prepare the complete existing-2D-root *placement-only* sidecar workflow so that the user can start it later with **one explicit command** after reviewing a readiness report. The preparation includes source audit; minimal code/config changes; fixed data/label schema; root-grouped split; deterministic grasp-budget comparison; a 20–30-root pilot; 25-worker resource validation; dataset-scale cost/storage estimates; reproducible dry-run; exact commands for later manual launch, monitoring, pause, resume, audit and cancellation.

**Authorized now**: read-only audits, unit/regression tests, bounded physical teacher calls for *pilot roots only*, pilot visualizations, and full-corpus **manifest/index/dry-run without motion planning**. Pilot records must be clearly separated from the future full dataset.

**Not authorized now**: collecting full 2D placement labels, processing all 5,000 roots with the physical teacher, starting a full run in the background, training cVAE/flow matching or X/Y, running 3D teacher, changing original scene roots/archived witnesses, changing historical X/Y equations, accessing the remote server, or pushing/merging branches. Do **not** trigger the prepared full launcher as part of tests or as a “sanity check.”

The final result must be **`READY_TO_LAUNCH`** or **`NOT_READY_TO_LAUNCH`**, based on explicit evidence. The launch command is delivered but **never executed**.

---

## 1. Inventory and baseline protection before edits

Start by recording: worktree location, branch, HEAD, dirty status, diff, file inventory, Python/NumPy versions, CPU topology (`lscpu -e=CPU,CORE,SOCKET,ONLINE`), process affinity (`os.sched_getaffinity(0)`), available RAM, swap, filesystem capacity, thermal sensors, and current load. Discover actual paths; do not invent module names or assume historical commit is the current HEAD.

Expected places to check, resolving differences from actual checkout:

- Local worktree: `/home/naren/Desktop/rss-placement-smoke` on reported branch `naren/placement-smoke-2d`.
- Original selected 2D roots: `gh-yadu-iiith/planar_2d/dataset_bd_classquota/selected.json`; scene and archived witnesses under `raw/roots`, `raw/witnesses`.
- Smoke code: `gh-yadu-iiith/planar_2d/dataset_relocations_v1/code/{placement_smoke.py,placement_smoke_check.py,test_placement_smoke.py}` (verify exact paths).
- Repaired smoke outputs: `.../dataset_relocations_v1/smoke_repro_v2/{smoke_fix_report.md,comparisons.json,audit/code_changes.diff,...}`.
- Baseline full 3R skill/geometry/robot: `dataset_bd_classquota/code/latent-causal-tamp/{config.toml,skill.py,planner.py,motion.py,geometry.py,p16_motion.py}` and `dataset-bd/{bd_core.py,bd_2d.py}`.

Verify original dataset `selected.json` against selected `raw/roots` and `raw/witnesses`: counts, IDs, geometry/config/teacher hashes, broken references, source files and storage size. Known GitHub baseline at `9e640690`: 5,000 selected 2D roots (NONE 1,000; K0 1,250; K1 800; K2 800; K3 1,150); 8×8 lattice; 48 grasp orientation/elbow modes and 48 place modes; selected scenes are constructed with `independent_moves=true`. **Recheck actual local artifacts.** Do not assume a train/val/test split already exists.

Keep archival files immutable, including the first `SMOKE_FAIL`, repaired `SMOKE_PASS`, original scene corpus and all preexisting witnesses. Configure external bytecode cache (`PYTHONPYCACHEPREFIX`) or `PYTHONDONTWRITEBYTECODE=1`. Do not use `git reset --hard`, `git clean -fd`, aggressive refactoring, or retroactive edits to old reports.

If smoke artifacts are absent or the reported pass cannot be reproduced from their saved audit, report the blocker and stop. Do not reconstruct an imaginary successful smoke test.

---

## 2. Immutable scientific/teacher semantics

### 2.1 The sampler is conditional on an already-held object

For a legal object/destination query `(S, o, d)` with scene `S` either original or hypothetical object-only edit, define `V_place(S,o,d; Pi)` under a **pinned finite placement policy** `Pi`:

- The object begins **already attached** in a valid post-grasp robot configuration; no requirement to find approach, pregrasp or closure trajectory. Validate initial held-state IK, joint limits, tool-object transform, collision/contact allowances, and support semantics.
- Evaluate **held transport → supported release/place → local retreat**, with actual joint-space paths and phase-wise independent replay. No return-to-home, X terminal connector, target motion or target-restoration label.
- `label=1` iff at least one mode produces a fully certified witness under this policy. `label=0` iff the entire declared *deterministic work* policy has finished without a witness. A system interruption before that completion yields `label=null, completed=false`, **not another learned class and not zero**.
- A completed zero means **policy-limited operational failure**, never proof of universal physical impossibility. Initially unpickable objects are still eligible for placement supervision if a valid post-grasp state can be defined; report pick access separately as diagnostic.

Preserve the existing 48×48 nominal ID catalogue. For each eligible query, reconcile disjoint mode counts: `total = screened + newly_attempted + reused_verified_without_new_planning + not_attempted`, or an equivalently audited disjoint partition. The reported smoke used 70,358 screened, 272 newly attempted, five reused, and 7,701 unattempted across its eligible queries; these counts are **not universal rates**. Store successful and failed statuses inside attempted modes, and independent counts of unique mode witnesses versus unique trajectory files.

### 2.2 Work is deterministic; time is a safety interrupt only

Preserve the repaired smoke algorithm unless a real bug is found: fixed per-mode seed and order; bounded **attempted** RRT extensions (including failed attempts), collision evaluations, successful nodes and shortcut rounds; fixed per-query number of pairs; no wall-time-dependent scientific shortcutting or stopping. The reported smoke policy was 1,000 attempted extensions, 20,000 collision checks, 200 accepted nodes, 150 shortcut rounds, up to 8 pairs per query; inspect actual code to confirm *scope per plan* and checks. Version the policy whenever it changes.

Time, thermal, memory and disk watchdogs may pause or cancel work but **may not convert interrupted queries to binary zero**. Completed atomic root/query records must survive restart byte-identically. Do not relabel old X/Y outcomes or mutate the archived planner's semantics.

### 2.3 Context/label boundaries

- Placement sampler data: object, scene, destination, support, already-held mode policy and independent `V_place` evidence.
- X: the **entire original-root ordered corrective sequence** with achieved robot state carried between moves and final connector.
- Y: the target from fixed `q_ref` in a hypothetical final edited scene; AB and BA sharing endpoints share Y but not X.
- Intermediate sampler contexts: `Edit(S0, prefix)` changes object poses only; record the original root, prefix and hypothetical/actually witnessed provenance. A hypothetical scene is not an achieved robot state. A low-Y prefix or failed terminal connector cannot be used to prune every longer extension.
- No construction-intended repair, blocker list, historical Y label, target swept volume, witness path, family ID, or teacher outcome may enter a *runtime* sampler or X/Y feature tensor. Offline teacher and data audits can read protected metadata with explicit separation.

**Do not silently convert a full relocation witness into a placement sample** without slicing from valid attached state and independently recertifying the carry-release-retreat suffix with the correct scene/protocol hashes. Preserve original evidence provenance.

---

## 3. Freeze root grouping and train/validation/test splits

Generate a **single deterministic, versioned split manifest before any large-scale placement collection or model training**. Select from exactly the counted original 2D roots, not rejected/retired raw attempts. Handle conversions and other proven shared ancestry so related roots cannot cross splits; derive groups from actual IDs/lineage rather than assuming an ID prefix identifies a family. If grouping information is insufficient, document conservative grouping logic and leakage risks.

- Proposed target proportions: approximately **70% train / 15% validation / 15% test** (roughly 3,500/750/750 of the 5,000 roots). Do not break lineage groups to hit exact counts. Stratify across NONE/K0/K1/K2/K3 and measurable clutter/source/region bins where possible.
- Save the seed, algorithm version, source selected-manifest hash, grouping keys and assigned roots. Report actual class counts and group counts per split; assert zero shared ancestors and zero duplicate root IDs across splits.
- Every hypothetical prefix, object/destination query, trajectory witness, image, alternative mode, cached teacher result and later X/Y candidate derived from a root inherits its split.
- **Pilot policy selection uses TRAIN/development roots only.** Validation may audit frozen choices; TEST must not be used for policy tuning, threshold choice, sampler selection or illustrated “good results.” A full dry-run may inventory all split names but must not execute teacher queries on validation/test roots now.
- Store a split-manifest hash in every new sidecar and launch manifest. Do not change splits after seeing pilot outcomes.

---

## 4. Predeclare the full-data trial allocation (but do not run it)

The full dataset is **an extension of the same 5,000 roots**, not a new 5,000-scene generation job. Do not implicitly label every object × every free cell × every hypothetical prefix: that is a different, potentially enormous workload. Freeze a **stratified and cost-bounded trial roster**:

1. Initial scenes: select movable objects without using intended-blocker roles, verified repair labels or construction options. Cover near/mid/far sources, grid regions, obstacle density and different distance/direction bins.
2. Destinations: choose from legal empty 8×8 resting cells by a fixed reproducible stratified/Sobol-like design; include near/far, directions, congestion and edge/corner/interior regions. `static_ineligible` is a legality record, not a teacher-queried zero. Make trial-inclusion probabilities/proposal rules explicit for future confidence calibration.
3. Intermediate scenes: predeclare a bounded small number of object-only prefixes, including archived-witness edits when eligible and also independent nuisance/non-solution edits. Record whether edits are `HYPOTHETICAL` or `WITNESSED`; do not assume a witnessed robot `q_t` for the hypothetical sampler.
4. Reuse only compatible historical witnesses; exact robot, scene/prefix, grasp transform, destination, phase conventions, geometry margin and budget-policy compatibility must be verified. Always re-certify the extracted post-grasp suffix.
5. Each root's query roster, order, random seeds and mode order must be deterministic and computable without calling the physical teacher. Store the query-plan hash and expected counts prior to launch.

**Design-time starting option, not a mandated quota**: up to 4 movable objects × 12 diverse destinations in the original scene and up to 2 edited prefixes × 2 remaining objects × 6 destinations (at most ~72 eligible candidate requests per root, before deduplication/ineligibility). Compare with pilot prevalence and cost, and explicitly freeze a feasible workload. A 5,000-root upper bound under this option is ~360,000 requests and is **not** permission to execute them now. If estimated runtime/storage are unacceptable, revise development-only quotas and re-audit before freezing; never quietly reduce coverage midway through production.

Use the same predeclared query roster across 8/16/32/64 mode-budget comparisons. For fair nested budgeting the first `B` eligible mode pairs and their deterministic per-pair search effort must be identical across larger `B` policies. Running more pairs should not cause previously completed verified positives to disappear; if it does, investigate inconsistent scheduling/aggregation.

---

## 5. Run a bounded *readiness pilot* only

### 5.1 Pilot roster

Select **25 independent TRAIN/development roots**, aiming for five per class (NONE, K0, K1, K2, K3), subject to ancestor grouping. Include varied clutter, source regions, relocation lengths and root provenance. Predeclare all pilot queries before seeing their physical outcomes; use a balanced limited subset of initial and intermediate queries. No new randomized roots. If the original selected dataset cannot supply a particular physical order-dependency contrast, say so; `independent_moves=true` means intended independent repairs are not sufficient evidence of learned sequence dependence.

### 5.2 Grasp-pair budget pilot

For an identical fixed eligible-query roster, compare candidate pair budgets **8, 16, 32, 64** with all lower-level counted-work caps and deterministic mode order fixed. Continue collecting within each budget after first success if that is required by the declared *coverage* protocol; retain every distinct real witness actually found. Reuse certified per-mode evaluations between nested budgets **with exact virtual accounting** or run them independently to cross-check. Never use a timeout-produced zero as reference truth.

Output by budget and by distance/source/clutter/prefix stratum:

- Query-level 1/0 counts, rescue rate `0(B) -> 1(64)` on fixed queries, and an explicit label-flip matrix.
- Fraction of surviving modes attempted, mode-level positive prevalence among attempted modes, unique verified modes/witnesses, reused-witness scope.
- Teacher calls, deterministic work units, worker CPU-seconds, median/p95 latency, failures by phase, negative-root diversity.
- Total bytes per record/trajectory, projected disk growth, memory, swap and peak/sustained temperature.
- Confidence caveat: empirical mode-success fractions over a selectively truncated catalogue are *coverage statistics*, **not calibrated probabilities**. A 64-pair zero remains policy-limited if unattempted modes survive.

### 5.3 Predeclared policy choice and go/no-go

Before viewing pilot outcomes, lock a decision rule in a small `pilot_policy_selection.json`/TOML. **Suggested rule:** use `B=64` as the *pilot comparison reference*, select the smallest `B` for which the fraction of positive 64-pair queries missed by `B` is at most **2%** on this predeclared roster, provided enough independent positive/negative examples and enough thermal/compute/storage headroom. Report Wilson/bootstrap uncertainty, not only a point estimate. A smaller `B` is acceptable only if it also preserves coverage across the relevant distance/prefix strata. If 64 pairs still show an unacceptable compute burden, **NOT_READY_TO_LAUNCH**; do not pretend a cheap `B` is reliable just because the dataset is convenient. `B=64` is not exhaustive physics ground truth; never describe it as such.

Ensure the pilot has useful negative examples from multiple independent roots. If it has overwhelmingly positives or a single negative-source object, expand **TRAIN-only pilot trial diversity within the declared small cap** or mark the confidence-quality gate blocked. Record the full attempted distribution. Do not fabricate minimum positive/negative counts after outcomes.

The pilot authorizes no cVAE/flow training, X/Y retraining, full 5,000-root labeling or 3D teacher calls.

---

## 6. CPU execution: target 25 workers / 32 logical CPUs

### 6.1 Hard requested target and topology-aware scheduling

The user specifically requests **25 worker processes** on the local machine with **32 reported logical CPUs**, retaining at least **7 logical CPUs outside the dedicated worker affinity set**. This is a **target**, not permission to exceed safe hardware limits.

1. Inspect **online and permitted CPU IDs**. Do not assume they are `0..31` or that “32 cores” means 32 physical cores. Inspect core IDs and SMT siblings. Select 25 distinct allowed logical CPU IDs, spreading them over physical cores where possible and intentionally reserving seven permitted logical CPUs for host/UI/monitor processes. Record explicit `worker_cpuset`, `reserved_cpuset`, actual topology and worker bindings.
2. Set worker count to **25** in the prepared full config and run the readiness pilot under this allocation **only after resource preflight**. Each worker is affinitized to one chosen logical CPU; the coordinator/monitor should use reserved CPUs where technically possible. Set `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1` **before numerical imports**; control threadpools inside workers if needed.
3. A 25-CPU affinity set is **not** a guaranteed 25-CPU resource reservation, nor a hard aggregate quota. If a user-level cgroup CPU quota is available, apply and verify `CPUQuota=2500%` or equivalent. If unavailable, use process count + affinity + reasonable `nice` + monitoring, record `hard_cpu_quota=false`, and do not claim a quota exists.
4. Do not oversubscribe via multiprocessing child planners, OpenMP, joblib, BLAS or renderer subprocesses. Track total descendants and terminate the entire process group on cancel. Reject ambiguous CPU counting.

### 6.2 Thermal and system protection

The reported repaired smoke had a 97.5°C cancellation, 92°C pause / 85°C resume and short spikes above 95°C, although some 28-worker runs peaked lower. Thus **25 workers are not already proven safe for sustained collection**.

Use a configurable fail-safe default:

- **Pause new work and safely SIGSTOP/hold worker groups at >=88°C**, resume only at <=80°C with hysteresis and bounded cooling cycles. Temperatures must be read from a reliable identified package/CPU sensor; incorrect sensors are not acceptable evidence.
- **Emergency cancel at >=95°C** (or any lower manufacturer/system limit, whichever is stricter), not after a prolonged grace period. Preserve completed records and mark in-progress tasks incomplete; never label them zero. Also cancel on memory/swap/disk danger, sensor loss, process leaks, cooling-stall or excessive repeated pauses.
- Enforce minimum free memory and disk headroom, avoid swap thrashing, log CPU utilization and per-worker RSS, record time spent paused, and keep room for the OS. Check battery/AC mode and use appropriate fan/performance controls without defeating protections.
- Pause/resume must not advance any work-count budget. If 25-worker sustained pilot is unsafe, **do not silently claim success at 25**; record `NOT_READY_TO_LAUNCH_25_WORKERS`, optionally test safer worker counts for diagnosis, and leave the prepared full launch disabled pending user choice.

Run a predeclared **representative thermal-soak test** during the bounded pilot (up to ~10 minutes or until the pilot finishes, with explicit total workload cap), so 25-worker stability is supported by more than a ~12-second smoke. Do not artificially generate pointless heat to reach a duration. No remote fallback.

---

## 7. Minimal code ownership and storage

**Reuse the three repaired smoke scripts and existing teacher; do not create a second planning backend or a whole new framework.** Current reported script sizes (549, 337, 116 lines) justify a narrow module responsibility split if it improves clarity. Aim for cohesive files of ~120–280 logical lines where reasonable; do not churn working low-level code merely to reach a line-count goal. Add no unnecessary dependencies.

New responsibilities needed:

- **Inventory/splits/roster:** one module or existing class for loading immutable selected roots; deterministic grouped splits; pilot/full dry-run manifests and stable query IDs.
- **Placement teacher adapter:** post-grasp held-mode checks, exact deterministic mode search, per-mode work evidence, conditional placement labels and witness storage; reuse current smoke implementation.
- **Runner:** bounded worker pool, topology-aware affinity, thermal pause/resume, emergency cancellation, idempotent root/query checkpoint, pilot-vs-full execution guard.
- **Validator/report:** read saved JSON/NPZ only, reconcile counts/lineage/hashes, independently replay witnesses, compare canonical fingerprints, project resources and emit readiness verdict.

**Sidecar layout** (adapt names only to actual repo):

```text
gh-yadu-iiith/planar_2d/dataset_relocations_v1/
  code/                         # existing smoke code plus minimal reusable extensions
  smoke_20261106/              # immutable historical failed smoke
  smoke_repro_v2/              # immutable passed smoke
  launch_ready_2d_v1/
    configs/                   # policy, allocations, split spec and safety guards
    split_manifest.json        # exact root/lineage assignments, checksums
    query_plan.jsonl           # deterministic roster; no physical teacher results
    pilot/                     # ONLY authorized new physical labels
      records/ modes/ trajectories/ visualizations/ audit/
    audit/                     # manifest hashes, tests, resource forecast, readiness report
    RUNBOOK.md                 # exact prepared launch/pause/resume/check/cancel commands
    launch_full_2d.sh          # inert unless explicit user-confirmation token supplied
  full_2d_v1/                  # MAY be named in config; DO NOT create data records now
```

Use atomically committed per-query or per-root JSON records and compressed NPZ modes/trajectories, stable content-addressed witness references, no conflicting writers, fsync/rename where practical, no live garbage collection of another worker's files, and a deterministic resume index. Create no database and no duplicate trajectory representation. Original datasets and all smoke artifacts must remain byte-identical.

Include required fields: `root_id`, `source_selected_hash`, `root_group_id`, `split`, `original_scene_hash`, `hypothetical_scene_hash`, `prefix_key`, `prefix_provenance`, `object_id`, `source_pose`, `destination`, `support`, `held_grasp_policy`, `robot_hash`, `teacher_hash`, `budget_hash`, `query_seed`, `eligible`, `attempted`, `completed`, `label`, `negative_kind`, `failure_phase`, `mode_counts`, `per_mode_outcomes`, `witness_refs`, `runtime/work_counts`, `resume_version`. Keep `privileged_teacher` evidence separate from anything fed into the runtime sampler.

Every visual must be scene-backed and correctly captioned; actual trajectories only, with all articulated 3R links, fingers, attached object, support grid, move phases and initial/edited-scene IDs. A static hypothetical edit must not be drawn as a real executed robot path.

---

## 8. Full launch preparation without executing it

Build a **two-stage launch interface**, defaulting to `--dry-run`/`--pilot`:

1. **Preflight / dry-run**: verify exactly 5,000 selected unique roots, split and query-plan hashes, policy files, disk/RAM forecast, topology and sensor visibility, permissions, witness store, replay verifier and no existing full job. Show planned class/query counts and worker affinity. This may scan/index metadata for all roots, **must not call the physical planner on any full-roster query** and must write no full-dataset placement label.
2. **Explicit future production command**: provide a single copyable executable `launch_full_2d.sh` or equivalent that **refuses to start** without (a) a `--execute-full` switch, (b) a user-supplied confirmation string matching the exact frozen plan/policy hash, and (c) passing current safety preflight. It must refuse when the selected-root set or configuration has drifted. **Do not run this command in the current task.**

Production runner requirements (implementation-ready, but not exercised over the full roots):

- Local 25-worker target (or fail closed); one numerical thread per worker; explicit CPU affinity and source-of-truth resource log.
- Unique root/query task lease or atomic committed-record ownership; resumable at query boundaries; frozen deterministic seeds; no duplicate witnesses; no silent widening of teacher budget.
- Stop/pause/resume scripts, process-group cleanup, temperature/memory/swap/disk guards; incomplete tasks remain unlabeled.
- Live per-class/prefix/region/source coverage counts, decided label counts, positive/negative breakdown, survivor-mode coverage and actual CPU-hours. Report drift/slowdown early; never silently change labeling or roster policy during a run.
- Keep all archived sources and lineage/splits intact; never treat incomplete run as a completed full dataset.

**Generate exact real commands in `RUNBOOK.md` after reading local CLI code**. Do not copy imaginary module paths or flags from this specification into a finished runbook. Include a minimal 1-query dry-run/check command, pilot rerun, full preflight, later explicit launch (marked DO NOT EXECUTE NOW), status, resume, stop, audit and visualization examples.

---

## 9. Required testing and readiness gates

Run tests **now** only on pilot/microdomain fixtures, plus full-manifest metadata-only validation:

- [ ] Existing repaired smoke results stay immutable; smoke regression suite and current baseline tests have no new failures (the known missing `runs/p16` baseline fixture failure must be reported separately, not suppressed).
- [ ] Correct conditional-on-grasp semantics: held-start valid while pick-access blocked still yields an independently verified positive when physically possible; no approach/closure in stored placement trajectory.
- [ ] Deterministic results for identical pilot queries: one serial reference and two 25-worker runs where safe; canonical labels, mode order/status, work counts and witness arrays/hash are identical. Wall time/thermal logs explicitly excluded from *scientific* fingerprint.
- [ ] Binary labels only for completed physical queries; static ineligible and safety-interrupted queries are unlabeled with separate reasons. Exact disjoint 48×48 mode accounting.
- [ ] Reused witness suffixes pass independent phase-aware replay; novel witnesses do too. No global-witness leakage, no orphan artifacts after safe finalization, no duplicate records on resume.
- [ ] Simulated failure/kill/resume in pilot leaves already committed files byte-identical; unfinished queries replay from frozen IDs and seeds.
- [ ] Root group/split lineage integrity and no observed label leakage; deterministic query trial distribution; no read of protected construction fields in learner-facing request.
- [ ] 8/16/32/64 budget pilot and policy selection are recorded, with observed prevalence, stability, diverse negatives, cost and uncertainty. Selected 25-worker thermal policy does not force label zeros.
- [ ] Full 5,000-root dry-run roster hashes and resource projections pass. The **production physical planner call count is exactly zero** in this task.
- [ ] Safe 25-worker stress/preflight; thermal/swap/disk data are real. If unsafe, do not claim readiness at 25.
- [ ] Full command requires a fresh explicit confirmation and was not executed. Original dataset + both smoke stores remain unchanged by hash.

Do not grant `READY_TO_LAUNCH` if there are missing source files, unverified physical negatives, nonreproducible pilot labels, insufficient negative diversity for the intended confidence model, undisclosed split leakage, unvalidated 25-worker sustained thermal behavior, absent disk headroom, disabled launch guard or incomplete evidence. It is acceptable to produce `NOT_READY_TO_LAUNCH` with the smallest precise blocker list.

---

## 10. Required deliverables and final report

Deliver *in the local repo/worktree*, with actual file locations:

1. Versioned launch-readiness configuration (25-worker affinity + safety + deterministic teacher + selected mode-pair budget).
2. Frozen selected-root split and lineage manifest, deterministic trial roster and generation method, query and policy hashes.
3. A completed 25-root (or explicitly blocked) 8/16/32/64 budget pilot with verified trajectories, saved modes, plots/GIFs and independent audit.
4. Production-ready local runner, full preflight/dry-run, guarded **disabled** full launcher, cancel/resume/status commands, brief `RUNBOOK.md`.
5. `readiness_report.md` with source/commit/diff, schema, pilot sample/label/mode counts, stability/uncertainty and negative diversity, actual/estimated CPU hours, estimated disk and upper-bound run duration, 25-worker temperature logs, reproducibility, resume and hash audits, and explicit remaining limitations.
6. Final verdict: exactly `READY_TO_LAUNCH` or `NOT_READY_TO_LAUNCH`, separate from any claim that the full dataset has been collected.

If all gates pass, give the user the exact later manual command and **STOP**. If a gate fails, report exactly what blocked readiness and **STOP**. Do not start the 5,000-root dataset extension, train models, use a remote GPU/server, edit X/Y, or silently push/merge/commit. Preserve current dirty work; record a patch/diff. A local commit should only be made if the user independently authorizes it.
