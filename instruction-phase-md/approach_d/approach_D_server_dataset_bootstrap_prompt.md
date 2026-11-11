# Claude Opus High — Begin Structured 2D + 3D Approach B/D Dataset Generation on the Server

You are acting as the implementation and experimental lead for my **latent causal infeasibility / repair** project. **Execute the setup, code audit, small validated pilot, visualizations, and server jobs**; do not merely write a proposal.

## Existing sources and server

- SSH host: `user1@10.4.25.63`. **Use existing passwordless SSH/key authentication. Do not ask for, print, save, or embed any password or credentials.** If key-based access fails, report that specific blocker without attempting insecure automation.
- Source 2D implementation: `https://github.com/Narendhiranv04/latent-causal-tamp` (existing fixed-base 3R 8×8 experiments, P13–P17, Approach D motion-library work).
- 2D results/visual reference: `https://github.com/Narendhiranv04/rss-ebm-infeasibility/tree/naren/PoC`. IMPORTANT: this is primarily a **PoC visualization/results package**, not the complete scene generator; trace its `sources.json` back to the actual 2D implementation.
- Source 3D implementation: `https://github.com/Narendhiranv04/rss-ebm-infeasibility/tree/yadu/dataset-3d`, especially `gh-yadu-iiith/random/grid_dataset.py`, `run_task.py`, and `xarm7_cabinet_env.py`. The present `grid_dataset.py` tests movement of one target among **static** obstacles; it does NOT yet create intervention-validated relocatable-obstacle datasets. The repository also has older cabinet/rearrangement files and inconsistent 6×6/8×8, 0/1-based grid conventions. Audit before reusing them.
- The new Approach D code may still exist only in an **unpushed local branch** (`approach-d-v1`, including G1, G2a/G2b). Locate and use it only if actually available; do not invent or assume access. Record each source SHA and source provenance. Do not replace working historical code.
- Workspace, datasets, logs, cached motions, environments, visualizations, and checkpoints must be under an appropriately spacious directory such as `/data/user1/rss_ebm_dataset/` (use another non-home mounted data volume if it has more safe free space). **Do not store large assets under `/home`**; keep only a tiny launcher/symlink there if unavoidable. Verify permissions and disk space first. No `sudo`, destructive cleanup, or deletion of unrelated data.

## Scientific contract (mandatory)

1. **Same root scenes for Approach B and Approach D**; derive separate labels/records for each method, not separate incompatible datasets. D predicts **original target T feasibility and intervention-grounded blocker participation**, even in hypothetical updated scenes. B evaluates **ordered correction sequences**. Keep the existing two D losses (feasibility BCE + blocker conditional Boltzmann NLL); no extra updated-scene/destination/order loss.
2. **2D** uses the project's original 3R arm, grid and defined side-grasp objects. **3D** uses the xArm7, verified side grasps only, existing MuJoCo grid/cabinet shelf. Render 3D as clear tabletop/shelf scenes viewed from useful camera angles; do not silently replace the existing 3D cabinet geometry with a different task. Any new tabletop-only variant must be named and versioned separately.
3. **Total action budget = seven pick-and-place movements**: up to **four necessary obstacle relocations**, up to **two deliberately redundant relocations**, then **one final movement of the original target T**. Redundant-but-valid sequences still count as successful if the target reaches its goal; separately log minimum verified repair length, excess actions and travel cost. Do not mistake the intended K for verified minimum K.
4. **No IK, RRT, grasp synthesis, or motion planning at inference.** They **ARE allowed during offline teacher/data creation and offline motion-library compilation**. Deployed evaluation must use only previously compiled absolute joint-space trajectories, local-relative retrieval, and full collision checking. Never translate a joint trajectory or swept volume and claim it is executable.
5. **New teacher query labels are binary**: `y=1` when verified within the declared offline teacher protocol, `y=0` otherwise, including search/budget exhaustion. Preserve reason codes, actual attempt counts and deterministic planning/iteration ceilings as metadata. A negative means *not verified under the declared budget*, not a universal physical impossibility proof. **No third UNKNOWN class in new labels.** A blocker mask may separately have `blocker_supervision_valid=false` if evidence is insufficient; do not invent a mask or conflate a missing compiled witness with causal attribution.
6. Do not make wall-clock time the **task difficulty** or target success definition. Nevertheless, enforce **finite offline IK/plan attempt/iteration limits and administrative CPU/wall safety caps** to prevent hung jobs. Fix and log them per version. Do not allow longer-running scenes to receive systematically more teacher search merely because they are interesting.
7. Preserve existing **JSON + NPZ scene/trajectory storage** and existing generated data. Prefer additive sidecar manifests/metadata and backwards-compatible optional keys, plus a content-addressed motion-witness catalog so large trajectories are not duplicated in every B/D record. Validate loadability with current readers. Never silently overwrite previous datasets.
8. All generated scenes and their counterfactual descendants, variants, and motion witnesses must have immutable `root_id`, `parent_family_id`, `construction_seed`, `variant_id`, `config_hash`, `generator_version`, `teacher_version`, and robot/grasp protocol IDs. Avoid any information leaking from teacher labels into D's input.

## What to build: a controlled dataset, not random scenes

Build **one reproducible, factor-controlled scene generation scheduler** on top of the existing generators, with minimal new Python files and functions. It should select currently undercovered **valid factor combinations**, generate a scene, validate it physically, run the teacher, assign its **observed** stratum, and append the result to an incremental coverage ledger. Preserve failed construction attempts with reason codes; never silently resample until a difficult quota appears easy.

Initial root factors/levels:

- Verified correction depth **K = 0, 1, 2, 3, 4** (target about equally represented across accepted K; record scenes with no successful repair as a separately reportable class). K is determined by the declared finite repair domain/teacher, **not** by how many objects the constructor intends to block T.
- Total movable-obstacle count: **K plus 0, 1–2, or 3–4 distractors**, subject to a tested cap (initially at most 6 candidate blocker objects until the D mask dimension is explicitly expanded and tested; do NOT silently drop extra objects).
- Target source: **near/mid/far** robot reach, with region and edge/interior labels.
- Target movement: **short/medium/long** displacement within robot-specific reachable pairs.
- Obstruction mechanisms: **grasp access**, **placement access**, **carried-object / whole-arm transfer**, **mixed**. These may overlap; represent with multi-hot mechanism tags, not artificially exclusive labels.
- Causal structures: **independent necessary blockers**, **joint sufficiency requiring multiple changes**, **alternative sufficient repair sets**, **order/destination dependencies** if actually supported by the domain.
- Parking options: **one/limited/multiple** candidate destinations; include destinations that create new blocking and ones that do not.
- Distractor roles: **near T**, **near goal**, **near potential swept path**, **far away**; positive and negative matched interventions.
- 3D geometry: initially verified side-graspable **upright boxes and cylinders** with bounded footprint/height variation; expand shape families only after stable physical side-grasp validation. 2D geometry stays consistent with existing discs/objects.
- Initial/intermediate robot pose: canonical and a **small set of validated non-home configurations** (only if the current datasets/protocol permit those poses).
- Correction sequence variants: **minimal successes**, **alternative successes**, **redundant successes** (1–2 extra actions), **wrong order**, **wrong destination**, **no-op/irrelevant move**. Stop every sequence at 7 total actions.

Use balanced **marginal levels**, feasible pairwise combinations, and selected 3-way interactions (K × mechanism × distractor location). Do **not** attempt the full Cartesian product. Use a documented deterministic deficit-based sampling policy and show a factor coverage dashboard. Do not presuppose every proposed K3/K4 scene is truly K3/K4.

## Labels and annotation limits

- First evaluate original-target T feasibility **with the same defined task, robot start pose, permitted side grasps and teacher budget** across all variants.
- Test a **small, deterministic selection** of valid obstacle relocations and re-query **only T** in each hypothetical scene (for D). Include noncausal and near-path distractor tests.
- For B, preferentially keep **8–12 strategically diverse sequences/root** when supported: shortest, alternative, 1–2 redundant, incorrect ordering, incorrect destination. Avoid exhaustively trying millions of relocation permutations.
- For D, keep **4–8 focused interventions/root** where useful. Only attach a complete blocker-union mask when the predeclared intervention family has enough verified coverage to justify it. Run a more thoroughly annotated **causal-audit subset** instead of exhaustively annotating every root. The same scene can yield multiple target-only updated-state records using the **same two D losses**.
- Clearly separate **teacher-negative binary outcomes**, **verified successful repairs**, **exact/candidate-scope minimality**, and **causal-supervision validity**. Store evidence coverage and failure-reason metadata.
- Cache/reuse teacher labels for exact canonicalized scene, T goal, robot q, object geometry and frozen teacher protocol. Don't treat nearby or visually similar scenes as identical cache keys.

## Experiment organization

Do **not** bake a specific train/test/OOD split into scene construction. Write a root-grouped, factor-rich master manifest. Produce split manifests **without relabeling or changing physical data** for later IID and OOD protocols: K0–2 vs K3–4, obstacle count scale-up, new source/goal regions, new blocker-combination types, distractor density, and 3D geometric changes. All root descendants and close construction-template siblings must remain together. Keep the final test and OOD groups untouched during generator tuning.

Long-term aspirational collection sizes (not automatically authorized for immediate production): **20,000 independent 2D roots** and **5,000 independent 3D roots**, subject to measured cost, physical validity and coverage yields. These are targets, not a mandate to create fake difficult cases.

## Compute and infrastructure — use the available GPU intelligently

On SSH login:

1. Inspect `nvidia-smi` (actual GPU model, total/free VRAM, driver, current competing users), `lscpu`, `free -h`, `df -h /data`, `df -i /data`, mounts, installed CUDA/Python, MuJoCo, OpenGL/EGL, and source checkout status. Avoid echoing credentials.
2. Confirm whether the card is **RTX PRO 5000 Blackwell** or another model; do not assume availability merely from the request.
3. Benchmark actual 2D teacher, 3D MuJoCo IK/RRT/collision checking, rendering, and optional batched DINO/image encoding separately. Standard MuJoCo and Python RRT may be **CPU-bound**. Use the GPU for supported accelerated rendering (`MUJOCO_GL=egl` where verified), batch visual feature extraction, and/or GPU-native tools **only if implemented and measured**. Never claim high GPU utilization means faster teacher labeling, or introduce dummy GPU tasks to inflate utilization.
4. Benchmark 1/2/4/8 workers as resource limits permit, compare actual verified-root throughput, RAM/GPU VRAM, CPU, disk I/O, retry counts and failure rates. Set worker count based on **measured throughput**, not automatically `nproc`. Leave safety headroom and respect other server users; no OOM, runaway CPU, or unlimited retry loops.
5. Run resumable bounded jobs in `tmux` (or an equivalent safe manager) with structured logs and atomic checkpoints under `/data/...`, with deterministic restart, per-job caps and a clear stop command. Keep a machine-readable ledger of completed, failed and in-progress scene IDs. Prefer compressed NPZ, avoid generating GIFs for every scene and prevent disk filling.

## Mandatory scene-wise visualization

Use the existing **2D PoC visual style as a reference**: labeled gridded source scene, T and target-goal positions, obstacle IDs, intended/verified blocker distinction, example robot-arm motion and true swept volumes. Add matched **before/after** intervention panels, plus a representative successful/failed ordered-repair strip.

For 3D, produce **actual MuJoCo xArm7 rendered screenshots** (overview + side/oblique view) of the existing cabinet shelf/tabletop-style scene, labeled source and goal, color-coded objects, and after-intervention scene. For at least one validated sequence, render keyframes/GIF showing side grasp, lift/carry, placement and T motion. Never use a schematic in place of simulation evidence. Keep a sample gallery per K/mechanism, not a video for every root. Include a consolidated stratification/coverage dashboard, teacher label counts, cumulative examples, throughput and storage plots.

## Implementation sequence — start executing now

**G0 — Audit and setup:** SSH via key; select large `/data` workspace; check GPU/CPU/storage; inspect actual 2D generator and both 3D generator versions; reconcile 8×8 cell indexing, world coordinates, side grasps, target task, obstacle movability and schema. Verify whether the unpushed G1/G2a/G2b branch is accessible. Preserve original sources. Write concise audit and environment manifest.

**G1 — End-to-end fixtures:** Reproduce a handful of existing 2D scenes and xArm7 scenes; build at least **one 3D intervention that physically relocates a previously static obstacle** and successfully re-evaluates original target T. Show actual 2D/3D visuals. If this fails, do **not** manufacture 3D blocker labels or launch a huge 3D job; report the specific limitation and keep progressing on valid 2D work.

**G2 — Minimal stratified sampler:** Implement factor specifications, deterministic sampling, coverage ledger, binary teacher protocol, scene/variant IDs, minimal-change storage extension and B/D annotations. Add tests for label semantics, hard 7-action cap, K versus constructed K, grouped split integrity, reproducibility, side-grasp restrictions and old JSON/NPZ readers.

**G3 — Smoke/pilot jobs:** First run **20 2D roots and 5 3D roots**, including K0, distractors and at least one verified multi-blocker fixture, verifying images and records. Then, if valid and resource-safe, launch resumable **500-root 2D and 100-root 3D stratified pilots** with conservative per-job limits (100 3D roots is an upper pilot target; stop earlier if failure/throughput thresholds show the design is broken). Collect coverage by **verified** K and construction acceptance rate, not requested K alone. Use the GPU where it demonstrably accelerates supported operations. Do not forge difficult strata to hit quotas.

**G4 — Report and stop before scale-out:** Produce a report with actual commit hashes, storage directory, tmux session names/commands, jobs running/completed, plots/gallery links, exact per-stratum counts, fraction of operational negatives and their reasons, successful counterfactual edits, valid blocker-mask coverage, average teacher attempts and calls, CPU/GPU utilization, measured throughput, disk consumption/root, projected cost of 20k/5k, and remaining gaps. Give a specific next-step scaling plan but do **not** launch the full 20k/5k collection or touch sealed test data yet.

## Engineering / safety constraints

- Minimal modules and subfolders; prefer additive code and small comprehensible files. Branch locally and version config separately; do not overwrite, delete, push, merge or edit historical experiments without explicit approval.
- No hidden online IK/planner in the eventual inference path. No broad model retraining now; focus on trustworthy data and visualization.
- No fabricated physical success: distinguish static geometric checks, planned motion verification and actual MuJoCo execution.
- If any key part is inaccessible, deliver the maximum honest partial implementation, clearly marked BLOCKED, instead of inventing results.
- Do not ask for permission merely to run the bounded smoke and pilot specified here. Stop rather than silently expanding compute/storage beyond this scope.

**Start with a real SSH/environment and code audit, then actually implement and launch the bounded jobs. Return reproducible artifacts and precise progress, not just a proposed design.**
