# Neural Object Retrieval (OSNet + RPNet) — Corrected Learned Baseline Implementation Plan

**Research project:** Latent Causal TAMP / Approach B — learned rearrangement comparison
**File:** `neural_object_retrieval_plan.md`
**Baseline ID:** `NOR-Grid` (adapted Ren–Qureshi OSNet/RPNet; use a single ID consistently; do not confuse with the separate 2021 NeRP paper)
**Authoritative source:** Hanwen Ren and Ahmed H. Qureshi, *Neural Rearrangement Planning for Object Retrieval from Confined Spaces Perceivable by Robot's In-hand RGB-D Sensor*, ICRA 2024, [arXiv:2402.06976](https://arxiv.org/abs/2402.06976), [HTML](https://arxiv.org/html/2402.06976v1).
**Repository:** `Narendhiranv04/latent-causal-tamp`, inspect current local checkout; reference branch `naren/approach-b-v3-4-final-benchmark` (not a claim about local checkout).
**Status:** corrected normative handoff, **not** an implementation, trained model or observed result.
**Historical error corrected:** the prior file with this *same name* was accidentally written for Bingjie Tang and Gaurav S. Sukhatme's *Selective Object Rearrangement in Clutter* (CoRL 2022). **ALL SORC, Tang/Sukhatme, SimGNN, goal-graph edit, DenseNet PUSH/GRASP and visual-correspondence instructions are superseded. Do not implement the old architecture.** (The superseded file is archived at `baselines/neural_object_retrieval/reports/superseded/`.)

> **Primary scientific goal:** Train an integrated neural baseline that (1) selects a non-target object likely to obstruct the robot's original target manipulation, (2) proposes a permissible relocation cell, and (3) composes at most three relocations before attempting the unchanged target-to-goal action. Its object selection and region proposals are its own learned OSNet and RPNet; **no additional symbolic TAMP framework or Approach B X/Y scorer** makes its decisions.

> **Strict compute:** All data reading, labels, neural training, simulations, verification, figures and reports must execute **only on the user's own laptop CPU and GPU**. No server/SSH/cloud/hosted API/remote GPU/remote simulator. Lack of local data means a reported blocker, not permission to use remote compute.

---

## 0. STOP/RESUME PROTOCOL — REUSE THE EXISTING `efa1b8da4f` WORK

The coding agent reported commit `efa1b8da4f` containing only paper-agnostic data auditing, legality checks and scene-graph feature work. **Do not delete it, discard it, reset the branch, force-push, or rerun the audit unnecessarily.** Verify `git show --stat efa1b8da4f` and tests; reuse only components that are truly paper-agnostic. Do not assume this commit is a completed model.

1. Inspect current `git status`, branch, commit, worktrees, local data/asset mounts and any concurrent agent activity. Create an isolated **local** branch from the existing baseline branch/commit or continue an already isolated branch if safe.
2. Replace obsolete SORC plan/prompt references with this corrected paper identity. Commit the correction with a clear `METHOD_SWITCH` changelog; don't silently overwrite the historical explanation in a report.
3. Keep previously created legal/data/graph files if validated. **Graph object features may be reused as Transformer input tokens**, but no SimGNN / graph-edit-distance sequencer should be implemented because it belongs to the wrong paper.
4. Resume model work at the first unimplemented stage, after checking that P0/P1 tests for the new model pass.
5. Never read or modify the **ongoing new 1,120-root V3.4 held-out expansion** or its generation logs/manifests/labels. The historical existing TRAIN/VAL data are the only experimental dataset here.

## 1. Paper fidelity — what the ICRA 2024 method really does

### 1.1 Native original model

The paper addresses **target-object retrieval from a cluttered confined space**, with an in-hand RGB-D active-sensing system and a specified target grasp. It has two learned components and a low-level robot planner:

- **OSNet (Object Selection Network)**: MLP embeddings of robot location, desired target-gripper pose, target box/state and non-target object bounding boxes; multi-head self-attention Transformer; per-non-target categorical obstruction probability. The original training target comes from *multiple smoothed collision-ignorant RRTConnect paths to the target*: count how often each other object obstructs these path homotopies, normalize counts to a distribution, and minimize **MSE** on the probability vector. Selection at runtime is `argmax` over non-target objects.
- **RPNet (Region Proposal Network)**: MLP embeddings of robot and target context, selected object, gripper pose and candidate surface-region tokens. A Transformer **encoder** processes the robot/target/region context; a Transformer **decoder** takes region tokens augmented by the selected object's embedding and attends to encoder outputs. A small MLP produces **cost per region**. In original offline supervision, occupied/unobserved/homotopy-blocking regions receive maximal cost; valid regions are ranked by distance from the selected object's source. Train by **MSE** to the region cost vector; select the lowest-cost region.
- **Execution loop:** the original pipeline performs active observation, tests target reachability with RRTConnect, selects and **physically relocates** an object if necessary, replans/reobserves, and repeats. That is **native closed-loop physical checking**, not a purely neural standalone success guarantee. The paper uses an underlying motion planner; it is not an external symbolic TAMP planner.

**Source:** arXiv:2402.06976, Sections III-C, III-D and III-E, especially equations (2)–(4). Read the original HTML or PDF before coding. Never claim open-loop equivalence or original paper experimental reproduction.

### 1.2 Mandatory adaptations and exact naming

| Dimension | Original Ren/Qureshi | Our justified adaptation | Reporting honesty |
|---|---|---|---|
| Task | Reach/grasp/retrieve a target object | Execute **original complete target-to-goal manipulation** after corrective relocations | More general/changed task |
| Perception | In-hand active RGB-D, partly unknown scene | Given GT poses/shape/support/IDs, optional available initial RGB-D/masks; no new active sensing claim | Privileged structured observation vs native |
| Target grasp | A specified grasp pose; original may use GraspNet | Fixed **allowed side-grasp family** from benchmark; no new candidate grasps | Not original GraspNet setup |
| Obstruction labels | Path-homotopy collision counts for retrieval | Offline TRAIN-only *complete target-action* reference-path obstruction counts, only if actually generated under unchanged robot/planner contract | Adapted supervision, never fabricate |
| Region labels | Path-homotopy blockage plus distance | Offline TRAIN-only target-to-goal homotopy/legality costs over original-root legal cells | Adapted region map |
| Action space | Select/relocate objects until reachable | K <= 3 move-once, side-grasp pick-place, original-root-empty destinations, target last | Strict shared grammar |
| Online verification | Physical state after each move; RRT target checks | **Primary open-loop** one proposal, then *independent post-seal* X/Y evaluation | Not native execution protocol |
| Comparison | Native object retrieval benchmark | Approach B, REAP, DISCO-Grid same 2D/3D roots and exact X/Y semantics | New benchmark, not paper's reported scores |

Do NOT add a learned GRASP-Q head, goal-arrangement SimGNN head, unrelated action-value network or separate learned feasibility classifier and call them OSNet/RPNet. A small **adapted STOP/NOOP confidence head** may be required for one-shot evaluation; mark it explicitly as an added benchmark adapter, supervised on target Y evidence. The paper itself uses a planner to decide whether to stop.

## 2. Dataset and source audit — existing corpus only

### 2.1 Verified repository metadata (audit local bytes before relying on it)

Frozen base snapshot `abf_9de85710c2a7103f` reported by `approach_b_final/reports/results/data_snapshot.lock.json`:

| | 2D | 3D |
|---|---:|---:|
| Independent target roots | 5,000 | 2,500 |
| Original ordered X observation records | 12,400 | 7,089 |
| Original endpoint Y observation records | 9,700 | 5,305 |
| Legacy K0/K1/K2/K3/NONE root counts | 1,250 / 800 / 800 / 1,150 / 1,000 | 511 / 357 / 612 / 612 / 408 |
| V2 *additional TRAIN-only* X evidence on the same roots | 7,594 | 2,126 |
| V2 *additional TRAIN-only* Y evidence on the same roots | 9,661 | 2,493 |

These are **not** counts of independent X/Y scenes. Y is an endpoint outcome and may be reused by several ordered X sequences; deduplicate physical signatures. The K classes are metadata, not permissible model inputs; `NONE` is a legacy restricted-search outcome, not a global impossibility proof. The historical `naren/dataset-done` reports document 2D K2/K3 dependent/independent scene provenance and 3D 6×6 shelf selection, but their old readiness timestamps do not supersede the frozen compiled snapshot.

Four distinct streams must not be conflated: 2D Q2 individual placement trials; 3D Q2 individual placement trials; 2D target-scene ordered X/endpoint Y; 3D target-scene X/Y. Q2 placement success does not establish target restoration. A complete X/Y repaired sequence does not automatically identify the physically blocking object or give a per-step failure label.

### 2.2 Where to inspect in the existing repo

- `approach_b_final/contracts.py` — compiled root public `inputs`, split/evidence masks, `view2d/view3d`; the private labels **must never** pass through a learner-visible batch.
- `approach_b_final/benchmark.py` — `public`, `validate`, `seal`, `queries`, `teach`, `evaluate`, `summarize`; primary one-prediction-per-root method adapter.
- `approach_b_final/baseline_adapters.py` — *harness smoke policies only*; they are **not scientific baselines**.
- `approach_b_final/search.py` — `Root`, `legal_dests` semantics, robot/task geometry; reuse legality only, not Approach B cVAE/XYNet or optimizer.
- `approach_b_final/teacher2d.py`, `evaluate.py`, `construct.py`, exact pinned 3D `fin3d` assets — unchanged independent physical verifier and teacher budgets.
- `approach_b_final/placement.py`, `onpolicy.py` — TRAIN-only Q2 placement and extra X/Y query provenance, but not their learned weights.
- `approach_b_final/reports/results/data_snapshot.lock.json`, `v2_data_snapshot.lock.json`, `LOADER_SCHEMA_REPORT*`, `QUALIFIED_TRAINING_EXCEPTION.json` and current experiment config.
- `approach_b_final/docs/PLAN_V3_2026-11-15.md` — archived task restriction and root/split semantics; current V3.4 benchmark configs take precedence for comparing frozen decisions.
- Current **local** DISCO/REAP baseline adapters, if available — compare external action grammar, verification budgets, and method-input privilege, not their internals.

Resolve local paths rather than assuming `/scratch/nav` or server storage. This chat inspected GitHub metadata and source excerpts, **not** every raw dataset byte, local teacher asset or actual local available VRAM. Record exactly what exists on laptop and what is missing.

### 2.3 Mandatory dataset audit report

Produce `baselines/neural_object_retrieval/reports/DATA_AND_LABEL_AUDIT.md` and a machine-readable manifest with:

- Exact `git rev-parse HEAD`, snapshot IDs/SHA256, files, root counts, split counts, family/layout disjointness and unlabeled/missing scope.
- Train/val/test group leakage check **without opening test outcome fields**. Keep historical TEST out of tuning, and don't open the expanded new cohort at all.
- Ordered-X unique signatures `(root, order, destinations)`, endpoint-Y unique signatures `(root, assignment)`, attempted/unknown/infra labels and teacher provenance.
- Counts and masks for OSNet homotopy **path-count supervision actually present**, RPNet **cost maps actually present**, target Y for STOP and Q2 placement trials. These new specific supervision types **must not be claimed to exist merely because X/Y are present**.
- Local cost estimates: how many TRAIN-only path samples, planner calls, RAM/CPU wall estimates are needed to construct OSNet/RPNet targets without a full new 2D/3D dataset; mark missing sources or projected budget excess.

**Hard gating:** if path-homotopy labels are missing, the coding agent must either (a) construct them **locally on a small TRAIN-only pilot using pinned teacher robotics**, then scale only under declared budget, or (b) report `BLOCKED_HOMOTOPY_SUPERVISION`. It may implement architecture and synthetic unit tests, but must not silently substitute ground-truth blocker IDs, K class, successful teacher repair order or XYNet probability as the *original-paper homotopy labels*.

## 3. Shared task, legal correction grammar and physical truth

For initial root `R=(S0,q0,q_ref,T,g,robot/geometry,legal_cells)`, a proposal is `r=((o1,d1),...,(om,dm))`, `0 <= m <= 3`. A corrective action is a complete side-grasp pick/place of a movable **non-target** object to a supported physical destination cell; final original target manipulation is separate and last.

**No exceptions:** each object at most once; no pushes, swaps, stacks, disposal, handing objects off, added staging actions or intermediate home reset. Destinations must be legal and supported, **empty in original S0**, not target goal, not used elsewhere, and free in current hypothetical prefix. An object initially occupying a cell cannot move so another object can reuse that cell. Objects fixed in 2D are never moved; 3D honors the actual fixed/movable semantics and native shapes.

**Embodiments:** 2D full 3R articulated arm, 8×8 0.08-m support lattice, tested side-grasp family; 3D pinned xArm7 shelf, 6×6 0.075-m cells, fixed box/cylinder geometry, verified side-grasp pitch/offset options. The robot/attachment trajectories are continuous. **Read actual current configs**; do not hard-code historical grasp counts without checking the active profile.

Shared final evidence:

- `X(r)=1`: the exact **ordered** corrections are executable under the frozen robot/planner budget, carried physical `q,g,attachment` between moves, and terminal free-gripper connector to `q_ref` completes.
- `Y(End(S0,r))=1`: original target-to-goal action is feasible **from q_ref** in the independently constructed canonical edited endpoint scene; same Y for endpoint-identical sequences regardless of order.
- `Z(r)=X(r) AND Y(End(S0,r))`: **complete repair success**, both sides independently decided.
- For `r=[]`, `X([])=1` by convention when reference state is available; judge `NOOP` by independently checked `Y(empty)`.
- `ABSTAIN` is a method decision, not proof that no repair exists. A failure within a finite teacher budget is operationally scoped; an unattempted/missing/infra query must not be recoded as negative. Log `UNKNOWN` distinctly.

**Independent verifier** is allowed *after* a root's frozen prediction. No test-time teacher calls, collision traces, partial target probes, simulated motion, trusted blocker sets or failed-proposal feedback in the method's **decision pathway**. Always seal predictions before invoking `benchmark.queries/teach/evaluate`.

## 4. OSNet — paper-based learned object selector

### 4.1 Inputs and architecture

Inputs: observed **original** scene object states and current *hypothetically edited* object poses (not actual robot state), target object and requested target-goal pose, robot base and **declared q_ref/q0 numeric context**, one frozen/known target-side-grasp representation or small fixed set summary. Include every non-target object whether it is fixed, movable or previously moved; mask ineligible objects from the output distribution. 2D physical attributes use known radius/fixedness; 3D use supplied box/cylinder sizes/offset/support. No predicted future robot joints or original teacher path inside the network.

Follow the paper's **MLP token embedding → multi-head self-attention Transformer → non-target object scoring MLP**. Do **not** substitute SimGNN graph-edit-distance, a learned push/grasp classifier, a classical blocker detector or merely the old data-audit graph features. For compact local GPU: propose width 128, 2–3 encoder layers, 4 heads, dropout 0.1; actual choice frozen from validation and recorded. Permutation-equivariant input ordering and fixed/target masking tested.

### 4.2 Train-only homotopy label construction

**Paper-native label idea:** sample multiple smoothed target paths with RRTConnect while *ignoring collisions with the movable non-target objects* but still validating robot kinematics, fixed obstacles, support and allowed target grasp conditions. Count how often each non-target object intersects complete robot/gripper/attached-target path geometry; normalize counts into `p_object` (with defined zero-count mask). In 2D use full 3R links and gripper; in 3D full xArm7/shelf. **Do not use straight-line point-robot or destination-only collision as substitute**, and do not require the path to physically execute through ignored obstacles: it is a *reference homotopy query* for labeling.

**Task extension:** the requested target task is a *full target-to-goal motion*, not just reaching a grasp pose. For each TRAIN root, preregister the stages to include: initial approach, allowed side-grasp closure, attached target transport to goal, release and safe retreat, with any necessary connector/phase semantics from the existing teacher. Generate reference traces that ignore **movable obstruction contacts only** and obey all other verified constraints. If the teacher cannot safely generate these traces, report a target-motion-specific blocker. Do not treat a frozen historical sweep from another protocol as current oracle proof.

- Freeze `path_sampling_seed`, number of reference paths and object collision-count aggregation per root **before** seeing model predictions.
- Counts are **teacher-side labels**, not model inputs. Counts are not a minimal-causal-culprit certificate, nor necessary across all possible repair plans.
- Object identifiers are stable only for logging; no ID/family/root memorization. If no paths or zero counts, mask the OSNet MSE for that query or use an explicitly predeclared zero-target convention with a separate flag, not an arbitrary uniform blocker target.
- On hypothetical *prefix* scenes, use TRAIN-only predeclared scene edits to generate conditional labels. Never generate labels for unselected TEST roots; budget and preserve root family grouping.

**Loss:** original-paper inspired `L_OS = mean_masked ||p_hat - p_homotopy||^2` with probabilities normalized over eligible objects. Optional CE/KL only as a named auxiliary ablation. The privileged path counts never enter inference. Note possible target-to-goal task adaptation in the paper-fidelity report.

## 5. RPNet — paper-based learned destination-region predictor

### 5.1 Inputs, architecture, outputs

Inputs: same context as OSNet plus the **chosen** movable non-target object and **all declared physical candidate cells** (8×8 or 6×6). Use original paper's MLP region/scene embeddings, Transformer **encoder** on robot/target/region tokens, Transformer **decoder** with `(region embedding + chosen-object embedding)` queries, and scalar per-region cost head. The selected object's current hypothetical source cell is included. Fixed and moved masks are retained. Do **not** replace this with SORC's image correspondence policy or Approach B's categorical cVAE.

Output one numeric **lower-is-better** cost for each physical region; hard-mask **legality** during selection. Legal placement alone is not a complete executable relocation. The RPNet can prefer a bad but legal region, and the independent final verifier must be allowed to expose that failure.

### 5.2 Training targets are different from X/Y

Reproduce the paper's **region cost** principle on TRAIN-only audited homotopy evidence: occupied, unsupported, out-of-scope, or predicted/reference-homotopy-blocking regions have a defined maximum cost; among the eligible nonblocking regions, normalize distance from selected object's source. Before assigning labels, explicitly define what counts as "blocks the target path" for its full target-to-goal action and whether a proposed placement changes the reference-path geometry. Use original-source *robot/full-body* geometry and 2D/3D clearance; no point-robot shortcut.

- Physical legality masking is deterministic/public and can be applied at inference; offline homotopy obstruction status **must not** be applied as an oracle mask at inference.
- If cost labels require a small offline TRAIN-only intervention to evaluate a proposed cell, log `do(object→candidate)` and all changed fields, with **robot state unchanged**; the edit gives a *hypothetical geometry label*, never physical X=1.
- Maintain separate label fields for `static_legal`, `homotopy_nonblocking`, `source_distance` and `whole_repair_outcome`. Never label an isolated Q2 placement or geometrically cleared path as full X/Y success.
- RPNet loss: `L_RP = mean_masked ||c_hat - c_teacher||^2` per observed cost-map cell. Mask missing/unattempted cost-map cells without treating them as max cost. If paper-style complete cost maps are unavailable, local TRAIN-only pilot first; **do not invent them from the legacy K labels**.
- Evaluate raw cost MSE/MAE, top-M valid legal coverage, original-homotopy nonblocking recall, candidate diversity and downstream independently verified task success. Low region cost is a learned prediction, not a certificate.

## 6. Learned termination adapter and one-shot sequence construction

### 6.1 Why this is an **adaptation**

Ren/Qureshi's native system **checks target reachability with RRTConnect after executing each move**. Using that online planner during proposal would give it an information advantage over Approach B's single-commit inference. For primary apples-to-apples evaluation, **replace only the termination signal** with a small learned benchmark-specific target-success/STOP head. This head is NOT OSNet or RPNet and is NOT an original contribution of the ICRA paper. Mark it as `OSRP-openloop-adapter`.

Supervise it using **TRAIN-only endpoint Y** for target-to-goal feasibility on the hypothetically edited scene (and optionally a separately named X/execution auxiliary using exact ordered X). Use only verified/attempted labels; no ground-truth target labels at inference. A Y-only STOP may predict restoration while the repair is physically unrealizable; **that is expected and measured by independent X**. Never use Approach B XYNet/F2/F3/F5 scores or Q2 neural checkpoints as this adapter.

### 6.2 Primary frozen open-loop policy

```text
INPUT public initial root, fixed OSNet, RPNet and trained STOP adapter
INIT r=[], hypothetical object poses = S0 poses, moved={}.
Collect STOP score for r=[] (K0 possibility).
FOR depth=1,2,3:
    OSNet scores all eligible non-target movable, not-yet-moved objects.
    Select highest-ranked with deterministic tie-break and legal-action mask.
    RPNet scores all declared original-root-empty, currently free destination cells.
    Select minimum learned-cost legal cell (deterministic tie-break).
    Append (object, cell) to r; update object poses in hypothetical scene ONLY.
    Record STOP score for current full prefix (may remain low after 1 or 2 moves).
END
Choose ONE visited prefix using frozen VAL-only stopping/admission rule
(never require target Y to rise after every intermediate move).
If selected prefix=[]: output NOOP.
If no admissible prefix: output ABSTAIN.
Otherwise output REPAIR with that exact ordered prefix.
Output one JSONL prediction; do not run robot motion / target planner.
```

**One-shot means:** one initial root observation and one final selected ordered repair, even though the neural networks may receive internally edited hypothetical object states for up to three forward passes. No physical state/reobservation/failure feedback; no retry if independently verified sequence fails. Do not fabricate intermediate robot configurations (`q_t`), actor success or executed repair trajectories.

**Optional secondary native-feedback protocol:** implement only after primary if local budget permits. Execute and reobserve after each real move; run existing native target-access check only where authorized. Label as *closed-loop, incomparable feedback budget* and keep statistics separate. It may help paper fidelity but **must never replace** primary open-loop numbers.

## 7. Training and evaluation design

### 7.1 Train/VAL and computational controls

- Train on **historical TRAIN roots only**, including admissible TRAIN sidecars; validate/tune on historical **VALIDATION** only. Do not touch historical TEST or new expanded held-out scenes for selection. Apply lineage/group splitting to all derived path-count and region-cost examples.
- Freeze label construction rules and seeds **before** teacher calls. Cache work per `(root_sha, hypothetical_edit, path_protocol_hash)`; never recompute a label under different planner settings and mix without provenance.
- Keep OSNet and RPNet genuinely trained with MSE on privileged TRAIN-only path evidence. Do not train an imitation-only `(object,destination)` classifier and name it OSNet/RPNet. Optional imitation auxiliary must be declared separately and ablated.
- Suggested compact start (tune VAL only): 128-d, 2–3 Transformer layers, 4 heads; AdamW 3e-4, weight decay 1e-4, batch 8–16, 30–50 epochs max, early-stop patience 8, grad norm clip 1, 3 seeds if local budget permits; label as proposed hyperparameters, not measured optimum.
- Small CPU/data pilot first, then GPU smoke. All model parameters from random initialization (or explicitly declared deterministic feature embeddings); no training on frozen Approach B network weights. Never use external model APIs.

### 7.2 Verification and metrics

The existing **shared benchmark harness** controls all decisions and final verification:

1. `benchmark.public` exports only learner-visible `root_id/domain/inputs`, never K, X/Y, witness, labels, repair solution.
2. Per root write `decision` ∈ `NOOP|REPAIR|ABSTAIN` and `moves=[{"object_id", "object_index", "destination_cell"}, ...]`; record inference timing, number of OSNet/RPNet calls, CPU peak RSS and GPU peak VRAM.
3. Call `benchmark.validate` to certify static K≤3 grammar; **no teacher calls in selection**.
4. Run `benchmark.seal` on predictions **before** any physical verifier query. Hash and preserve weights/rules/seed and public inputs.
5. Only then use shared `queries` → `teach` → `evaluate` → `summarize`; unchanged 2D/3D teachers and same planner/replay attempts/robot configs as other methods.
6. Count correct `NOOP` on K0, `REPAIR` success on evaluable K1/K2/K3, `ABSTAIN` on `NONE` **separately**. `NONE` is not proof of unsolvability. Report per-K success, FAIL_X, FAIL_Y, UNKNOWN, invalid grammar, abstention/failure, action count, displacement, *witnessed* travel, inference latency/CPU/VRAM, teacher call/wall time, root-cluster bootstrap CIs. Never impute unknown as failure or zero travel.

On validation, compare against fixed REAP, DISCO and Approach B with the **same public roots and exact physical verifier** when their predictions are already available. Otherwise record `NOT_RUN_COMPARATOR`; do not borrow paper-native success rates as local benchmark results. Use the new 1,120-root benchmark **only later, under separate explicit authorization**, frozen models and thresholds, with paired root IDs.

### 7.3 Mandatory ablations

- Full OSNet + RPNet + STOP adapter.
- **OSNet-only:** same learned object selector, analytical **legal-region** choice (nearest Euclidean, no oracle target path at inference).
- **RPNet-only:** a predeclared geometric/random eligible-object selector, learned region predictor.
- Both replaced with analytic/random controls (same legality, budget).
- No task-goal context vs full target-to-goal conditioning.
- No learned STOP (fixed validation-independent depths or explicit admissibility rule), clearly distinguish fairness of Y evidence.
- Optional: target **approach-only** homotopy supervision vs full **target-to-goal** homotopy supervision (scientifically important task-specific modification).
- Same-endpoint order-swap held-out validation cases if physically decided, and K2/K3 dependent scenes. Report how order-specific X may differ even when RPNet's endpoint costs are identical.

Ablations must use matched TRAIN/VAL splits, same teacher cache and only the permissible neural/analytic components—no Approach B XY predictor or ground-truth blocker masks at inference.

### 7.4 Scene-backed figures and audit outputs

For every stage generate accurate 2D/3D scene figures from the actual public root: robot reference configuration, all object IDs/poses/shapes, target/goal, fixed vs movable, legal original-empty regions, OSNet object probabilities, RPNet region-cost heatmap, selected ordered cells and actual verified robot trajectories **only if a complete witness exists**. Include at least one K2/K3 dependence/order contrast where evidence exists; if not available, label `NOT_MEASURED`. All figures must distinguish hypothetical placements from achieved motion. Same axis/camera settings for comparisons.

## 8. Local hardware, resource and workspace contract

**Laptop only.** Historical observation: AMD Ryzen 9 8940HX, ~32 GB system RAM, NVIDIA RTX 5060 ~8 GB VRAM. These may have changed; detect them before any run. Historical compatible Torch setup includes `torch 2.9.1+cu128` (not a directive to install a specific build). Print and log `hostname`, `nproc`, lscpu physical/logical, free RAM, disk, CUDA availability, Torch/CUDA versions, `nvidia-smi`, GPU compute capability, currently active processes, temperature and estimated training/teacher costs.

- Use an isolated **local** worktree/virtualenv and minimal project files. No gvlab, Girish, Blackwell, enigma, cloud/SSH, SLURM/Ray remote cluster, remote Docker, hosted model inference or external CPU. **Do not interrupt** another local process generating V3.4 data.
- Start 1–2 CPU teacher workers; increase only after resource and temperature/available-RAM pilot. Maintain headroom (suggest ≥4 logical CPU threads and ≥4 GiB free RAM); bounded teacher **per-query and total** budgets must be pinned before scaling. No unlimited overnight jobs or altered low-level planner limits.
- One local GPU model training process at a time, initial peak target ≤6 GiB allocated on an 8 GiB device, data loader ≤4 workers, CPU threads controlled, reasonable 8–16 minibatches, gradient accumulation, chunked dataset memory maps, deterministic seed/worker initialization, bounded tensor caching. If OOM reduce batch, not physical/planner constraints. Retain separate CPU teacher and GPU usage ledgers.
- No database, distributed trainer or mirrored physical simulator code. Local raw data already present can be used if hashes match, but **do not fetch absent large files from a remote server** under this user's strictly local-compute restriction without an explicit authorization to transfer data (none provided here). If inputs missing locally, report exact bytes/paths needed and stop appropriately.
- Write only under `baselines/neural_object_retrieval/`, except an explicitly documented adapter import and any **additive, isolated** benchmark extension necessary. No edits to archived models, teachers, config hashes, training snapshots, or the ongoing held-out cohort generation.

Suggested minimal files after inspecting `efa1b8da4f`:

```text
baselines/neural_object_retrieval/
  README.md
  config.json                 # one small frozen experiment contract
  data.py                     # exact root/label views and masks; reuse audited files
  homotopy.py                 # TRAIN-only offline full-arm reference-path counting
  region_labels.py            # TRAIN-only region cost map and provenance
  networks.py                 # OSNet + RPNet + explicit STOP adapter
  train.py                    # MSE losses / masks / checkpoints
  policy.py                   # open-loop greedy proposal; no teacher imports
  run.py                      # audit / label-pilot / train / predict / report
  tests/
  reports/
```

Suggested 120–280 logical lines per ordinary module; split >300 where a responsibility genuinely differs. Reuse existing audited data/legality files rather than duplicate. Commit after every passing stage.

## 9. Stage-gated execution (proceed without asking questions unless hard blocker)

**P0 — Correct identity, inspect, reuse.** Validate `efa1b8da4f`; reconcile old SORC wording; inspect ICRA 2024 original; verify local data/hardware/current teacher and benchmark contracts; write `METHOD_SWITCH_AND_FIDELITY.md`, dataset/split audit and resource report. **Gate:** paper/model identity correct and existing work preserved. If missing local 3D assets, flag `BLOCKED_3D` but continue independent 2D preparation.

**P1 — Exact legal and model input adapter.** Retain audited legality/scene feature code, test against `benchmark.legality` and `validate` on legal/illegal 2D/3D sequences and permutation/order cases. Ensure only public root is available to `policy.predict`, and no test labels/teacher/repair K. **Gate:** 100% matching legality and no privilege-leak paths.

**P2 — Homotopy and region-label pilot.** Implement training-only collision-ignorant reference target path sampling using validated full robot, count intersections with movable objects, create original-like OSNet vector and RPNet cost maps; pilot **~10–20 TRAIN roots/domain** under predeclared local per-query/aggregate budgets. Render verified labels and log complete statuses. **Gate:** teacher geometry correct, label provenance sound, at least one nondegenerate multi-object path-count example and at least one nontrivial legal-vs-blocking region map; otherwise `BLOCKED_HOMOTOPY_SUPERVISION` with exact reason. Never invent oracle labels to pass.

**P3 — Neural fidelity and tiny-data learning.** Implement MLP+Transformer OSNet and encoder/decoder Transformer RPNet with MSE loss, optional learned STOP adapter with only decided Y. CPU overfit 16–32 TRAIN examples, deterministic held-out 8–12 VAL smoke, gradient flow, zero probability on masked objects/cells, checkpoint hash/reload, local GPU memory smoke. **Gate:** both networks genuinely train on the correct label type; neither clones Approach B.

**P4 — Bounded local full TRAIN/VAL training.** Estimate CPU-hours for needed homotopy/cost labels from P2 throughput and available laptop; **only scale if within recorded user-imposed local resource constraints**. Train 2D and 3D separately (3 seeds if feasible; clearly flag 1-seed as preliminary), calibrate STOP on VAL only, freeze weights. If label quantity inadequate, report `LIMITED_LABEL_COVERAGE` rather than falsely claiming completed full supervision. **Gate:** train/val leakage=0, per-head data counts/coverage and metric report, no hidden model/test information.

**P5 — Sealed one-shot VALIDATION evaluation.** Run one original-scene prediction/root (up to 3 internal neural steps), static validate, **SEAL BEFORE TEACH**, share unchanged X/Y final verifier, log successes and unknowns by domain/K. Ablations and CI, timed runs and figures. **Gate:** reproducible fixed model, self-contained predictions, same external physics and budgets, all counts and failure types reported. If local teacher too costly, leave a frozen predictions-only report, `PHYSICAL_EVAL_NOT_RUN`, not fake scores.

**P6 — Freeze handoff for later common held-out.** Save commit/model/label/split/homotopy-rule/resource hashes, all reproduction commands, final learned-baseline comparison row and paper-fidelity delta; no test expansion accessed. **Gate:** independent agent can run the frozen `benchmark.public→predict→validate→seal→queries→teach→evaluate→summarize` protocol later without retuning.

At every hard gate: if blocked, state precisely whether it is absent local data, absent safe teacher path-generation API, infeasible local CPU budgets, model learnability or physical parity. Preserve useful completed code and results. Don't change the research algorithm to pass a gate without creating a separately named, honestly labeled ablation.

## 10. Required deliverables / acceptance

1. `baselines/neural_object_retrieval/README.md`, minimal working code/tests and unchanged baseline/harness integration.
2. `reports/METHOD_SWITCH_AND_FIDELITY.md`, `DATA_AND_LABEL_AUDIT.md`, `LOCAL_RESOURCES.json`, homotopy/region pilot results and mask reports.
3. Validated OSNet and RPNet source with actual paper-inspired **MSE supervision** and a clearly separated adapted STOP head; checkpoints if locally trainable.
4. Frozen original-root one-shot VALIDATION prediction JSONL for each available domain; static legality verdict and pre-teacher `.SEAL.json`; post-seal physical X/Y evaluations **only if run locally**.
5. Per-K success, NOOP/ABSTAIN, FAIL_X/FAIL_Y/UNKNOWN, action counts, witnessed travel, displacement, end-to-end runtime and local CPU/GPU use with uncertainty and matching ablations.
6. Real scene-backed visualizations, exact checkpoint/source/dataset/homotopy seed/protocol hashes and a comparison to REAP/DISCO/Approach B (never replacing unavailable rows with fabricated numbers).
7. `reports/NEURAL_OBJECT_RETRIEVAL_BASELINE_REPORT.md` with an explicit *ICRA 2024 adapted baseline* caption; **not Tang/SORC and not exact native reimplementation**.
8. A final stage-by-stage verdict `PASS / BLOCKED / NOT_RUN` with exact evidence, not an assertion that every target was fulfilled.

**Absolute no-go:** no test expansion read, no off-laptop execution, no test-time physics inside policy, no new symbolic TAMP, no different grasp/robot task, no imputed X/Y/path-count/region labels, no SORC modules, no rewriting old commits or teacher, and no success claim without the independent verifier.
