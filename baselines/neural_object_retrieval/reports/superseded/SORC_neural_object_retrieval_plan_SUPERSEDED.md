# SORC-Grid: Selective Object Rearrangement in Clutter — Adapted Learned Baseline

> **OWNER AMENDMENT (2026-11-18, user's own message, supersedes §0.9, §8.1 and the compute line below where they conflict):**
> Compute = the user's laptop (CPU + RTX 5060 8 GB) **plus the GPU of gvlab2** (RTX 5090, ~18–19 GB VRAM free; shared with a teammate).
> gvlab2 is for GPU work only (with the minimal CPU needed to drive it, <= 4 threads). Every other host (gvlab, Blackwell, enigma,
> girish, dinesh, any cloud) remains forbidden. All other rules of this contract are unchanged.

**Project:** Latent Causal Infeasibility for Long-Horizon TAMP / Approach B
**Deliverable name requested:** `neural_object_retrieval_plan.md`
**Research baseline name:** **SORC-Grid (adapted)**, from **Bingjie Tang and Gaurav S. Sukhatme, "Selective Object Rearrangement in Clutter," CoRL 2022 (PMLR volume published 2023)**.
**Original paper:** https://proceedings.mlr.press/v205/tang23a.html
**Original paper PDF:** https://proceedings.mlr.press/v205/tang23a/tang23a.pdf
**Supplement:** https://proceedings.mlr.press/v205/tang23a/tang23a-supp.pdf
**Original project:** https://bingjietang718.github.io/selective-rearrangement/
**Host repository:** https://github.com/Narendhiranv04/latent-causal-tamp
**Preparation basis:** Read-only review of GitHub branch `naren/approach-b-v3-4-final-benchmark`, repository `naren/dataset-done` historical reports, and the cited paper, on 18 November 2026. **No local raw dataset bytes, local GPU or physical simulator were executed in this preparation.** Every item marked `VERIFY_LOCALLY` must be checked before a coding agent asserts parity or data readiness.
**Status:** Implementation contract, not a claim of a trained baseline or measured benchmark numbers.
**Scope:** Existing data, TRAIN and VALIDATION. The ongoing V3.4 new held-out test-cohort expansion is explicitly out of scope.
**Compute (original text, amended above):** USER'S OWN LAPTOP ONLY, CPU and single local GPU. Never use gvlab, gvlab2, Blackwell, enigma, Girish's laptop, SSH, a remote server, a hosted GPU, a distributed job, or an external inference/training API.

> **Identity warning:** This is **Tang & Sukhatme's Selective Object Rearrangement in Clutter**, NOT Ren & Qureshi's 2024 *Neural Rearrangement Planning for Object Retrieval from Confined Spaces* (OSNet/RPNet). The historical filename `neural_object_retrieval_plan.md` is retained solely as requested; code, citation, metrics, and result tables must identify the method as `SORC-Grid (adapted)`.

---

## 0. Highest-priority scientific and execution rules

1. **Benchmark truth is unchanged.** Same root scene, original target/goal, robot embodiment, permitted side-grasp family, legal cells, physical teacher, X/Y query protocol, and verification budget as Approach B V3.4, DISCO-Grid and REAP. No easier new robot, proxy physics, teleport-as-success, unrestricted grasp, unverified shortcut, hidden target oracle, or extra TAMP planner.
2. **The baseline is an integrated learned rearrangement policy.** Its own neural sequencing + GRASP feasibility/value + placement policy + task-conditioned stopping determine **one ordered correction sequence**. No Approach B cVAE, XYNet, X/Y Boltzmann scorer, learned blocker oracle, external symbolic TAMP, or borrowed DISCO/REAP policy is permitted inside its decision rule.
3. **Allowed correction grammar:** `0 <= K <= 3` corrective relocations. Each movable, non-target object can be moved **at most once**; the original target is not a corrective object and is moved **once at the end** only by its original specified target action. A correction is a full side-grasp pick, attached transport, place, release, retreat. No PUSH, swap, push-grasp workaround, bin/disposal, stack, use of cells occupied at original S0, reuse of previously vacated cells, reuse of a destination, target-goal changes, staging move of an already moved object, intermediate return-home or extra task actions.
4. **Physical semantics:** 2D = existing full fixed-base 3R arm, finite-width links/gripper, 8x8 resting cells; 3D = original xArm7 shelf, 6x6 resting cells with supported boxes/cylinders, pinned body/robot geometry. Use **current tested** grasp candidates and planner budgets from local teacher configs; do not blindly hard-code historical 48/32 counts. Resting cells are discrete; motion is continuous.
5. **State continuity:** Every correction carries the actual attained robot configuration, gripper and attachment state to the next correction. No reset-to-home between moves. X includes correction sequence **and terminal free-gripper connector to q_ref**; Y is the independent original target task from q_ref in the canonical edited endpoint scene. `SUCCESS = (X=1 and Y=1)` for the same proposed ordered sequence. Noop is the independent empty-scene Y. X and Y are observed via teacher **only after prediction is frozen** in primary evaluation.
6. **One-shot open-loop primary comparison:** One original observation; all intermediate states used by this baseline during proposal are **hypothetical object edits only**, not simulated or robot-achieved states. Select one complete ordered sequence, seal it, run independent verifier **once**, no execution-time second-best retry/replanning. A separately declared closed-loop version may be a secondary, **different-feedback-budget** experiment, never quietly merged with the primary comparison.
7. **No test leakage or interference:** TRAIN-only supervised teacher labels; VALIDATION-only hyperparameters/stopping thresholds; never use existing or incoming TEST labels to select model weights, camera, architecture or reward shaping. Do not open, write, modify, clean, read outcome fields from, or generate the ongoing 1,120-root V3.4 test expansion. Treat all expansion code, generation runs, manifests, and working directories as someone else's immutable work.
8. **Three-valued evidence bookkeeping:** An independently replayed success is a verified positive; a finite-budget negative remains `attempted_failure_under_frozen_protocol` unless an independent sound certificate supports a wider impossibility claim; absent/unattempted/infra/timeouts with no operational label stay `UNKNOWN`. Do not turn missing X/Y into zero. Preserve teacher provenance and the legacy `K` meaning; `NONE` is not universal unsolvability.
9. **Local hardware and data:** Never run teacher calls at inference-time for ranking, never offload training. Detect hardware, storage, RAM, CUDA/Torch versions at P0. Train locally with one GPU process and bounded CPU workers. If raw datasets or required physical teacher APIs are not available **on this laptop**, report `BLOCKED_LOCAL_DATA` or `BLOCKED_TEACHER` with concrete missing files; do not substitute remote paths or fabricate labels. *(Amended: gvlab2 GPU also allowed for training/inference.)*
10. **Truthful paper attribution:** Original SORC uses goal **images** describing a desired arrangement, a graph edit/SimGNN object sequencer, a learned **PUSH/GRASP** DenseNet FCN, and a correspondence-based PLACE head (plus a discard bin and swaps). Our task lacks a desired arrangement for the non-target objects and **forbids PUSH/bin/swaps**. Therefore results must be named **SORC-Grid (adapted; grasp-only; task-goal-conditioned)**. Do not call this an exact SORC replication. Preserve its **three-part learned decomposition** as far as the legal task permits, and audit every change.

---

## 1. Verified repository/data starting point, and what is NOT verified

### 1.1 Sources of authority (inspect the actual checkout first)

- `naren/approach-b-v3-4-final-benchmark/approach_b_final/benchmark.py`: common public-input/prediction/seal/validate/query/teach/evaluate/summarize harness; `PolicyAdapter`, `predict_one` API in `baseline_adapters.py` is a **harness test**, not a scientific baseline.
- `approach_b_final/contracts.py`: `view2d` / `view3d`, immutable input-label separation, base snapshot, per-root split and evaluation masks.
- `approach_b_final/search.py`: `Root`, original-root legal-destination and move-once rules; **reuse the shared legality**, not its sampler or scorer.
- `approach_b_final/evaluate.py`, `teacher2d.py`, `construct.py`, and the exact 3D fin3d source referenced by the pinned manifest: teacher semantics, q_ref connector, replay and resource accounting.
- `approach_b_final/placement.py`: Q2 isolated-placement record format and location of frozen **TRAIN/VAL** files; use metadata and legally sourced labels, **not** Approach B sampler weights.
- `approach_b_final/onpolicy.py` and `xy.py`: training-root X/Y query semantics, outcome masks, cost and provenance; **do not import the learned XY model as a feature, reward or policy**.
- `approach_b_final/reports/results/data_snapshot.lock.json`, `v2_data_snapshot.lock.json`, `LOADER_SCHEMA_REPORT*`, `QUALIFIED_TRAINING_EXCEPTION.json`, `approach_b_final/docs/PLAN_V3_2026-11-15.md` and `approach_b_final/config/final_protocol.yaml`.
- `naren/dataset-done/final_dataset_generation/FINAL_2D_TARGET_DATASET_REPORT.md`, `FINAL_3D_TARGET_DATASET_REPORT.md`, `FINAL_XY_EVIDENCE_COVERAGE.md`: provenance and **historical** teacher/readiness reports. Older `FINAL_XY_EVIDENCE_COVERAGE.md` explicitly predates the later Nov 12 compiled finalized snapshot; do not use its old "not yet measured" warning to contradict the frozen `abf_...` manifest.
- Existing local REAP/DISCO baseline contracts and actual adapter output conventions are to be **read and matched** before execution; do not assume every baseline has the same internal model calls.

### 1.2 Snapshot facts from the frozen documents

| Dataset, immutable base snapshot `abf_9de85710c2a7103f` | 2D | 3D |
|---|---:|---:|
| Independent target roots | **5,000** | **2,500** |
| Original ordered X observations | **12,400** | **7,089** |
| Original distinct-endpoint Y observations | **9,700** | **5,305** |
| Legacy K0 / K1 / K2 / K3 / NONE roots | **1,250 / 800 / 800 / 1,150 / 1,000** | **511 / 357 / 612 / 612 / 408** |
| Additional V2 **TRAIN-only** X observations (on these roots) | **7,594** | **2,126** |
| Additional V2 **TRAIN-only** Y observations (on these roots) | **9,661** | **2,493** |

**Critical:** These counts are metadata from checked-in snapshot documents; they are **not** the number of usable unique training sequences after masking, not sums of independent examples and not proof that local raw source packages are mounted. X is ordered; the same endpoint assignment can share Y across orders. Some V2 queries add Y without X. Q2 isolated-placement trial **counts are not established by this document**; P0 must enumerate exact unique trials, eligible labels, provenance, split and consistency in the actual local source package. K-class labels are **private stratification/evaluation metadata**, never network inputs.

Historical 2D final selection was reported complete. Historical 3D partial report predates the later compiled 2,500-root finalized snapshot, so the latter is used for this baseline. `QUALIFIED_TRAINING_EXCEPTION.json` and evaluation masks explicitly flag incomplete relative minimality; never report globally minimum K. Training/validation/test split **counts must be recomputed locally** from actual compiled rows. The pre-existing local historical test split is *not* a development pool.

### 1.3 Four different evidence streams; no mistaken substitutions

1. **2D and 3D target X/Y:** same original-root task, high-level ordered corrections; X exact order includes end connector, Y unique target endpoint query from q_ref. Preferred data for object selection, STOP, successful-sequence and cost supervision.
2. **Q2 individual placement trials:** queried object, context, destination and observed conditional placement feasibility **given that the object has been grasped**; not automatically an executable whole relocation, not X/Y and not guaranteed to specify a useful target repair.
3. **Original physical witnesses / phase logs:** if actually mounted and provenance-verified, may supervise **GRASP/action** prediction and per-step transitions. A complete X=1 witness proves that ordered sequence executed; X=0 of a longer sequence does **not** prove the first grasp failed.
4. **Rendered original-state observations:** data rows in `contracts` are primarily structured pose/geometry/robot context; do not assume real RGB-D and masks are present. If original-state 2D/3D renderers are available, render canonical **initial/hypothetical posed geometry** with a locked camera, without teacher collision outcomes. A pose raster is **not** a genuine sensory-equivalence claim; record observation provenance and distinguish image-like rendering from sensor RGB-D.

### 1.4 Mandatory P0 data audit output

Create `reports/SORC_DATA_AUDIT.md` and machine-readable `reports/sorc_dataset_manifest.json` **from local files** containing: all input paths (or `MISSING`), sha256 sizes, snapshot IDs, source code commit, per-domain TRAIN/VAL/TEST roots (counts only, no TEST outcomes), per-root X/Y/XY decided coverage by K and by full/order-prefix length, replay/witness/cost availability, unique Q2 trial counts, label provenance, duplicate endpoint/order counts, same-assignment order contrast count, split/lineage leakage tests, Q2 overlap with XY roots, support/cell/shape dimensions, and fitted TRAIN-only normalizers. List missing fields that block specific losses. Make no edits to source snapshots.

**Strict local precondition:** if training roots or teacher assets exist only at `/scratch/...` or on another user's host, mark `NOT_LOCAL` and stop that stage. Do not SSH to obtain them or execute work there. Local copies can be used only if already present and hash-verified.

---

## 2. Adaptation versus the paper: preserve the mechanism, disclose differences

| Component in Tang & Sukhatme | Permitted SORC-Grid interpretation | Fidelity / must NOT do |
|---|---|---|
| Object accessibility graph and graph-difference / SimGNN sequencing | **Learned goal-conditioned graph edit/similarity ranking** over the initial (then hypothetically edited) robot/object/task graph; for each eligible movable object, score the graph with its node *masked from the comparison*, then select the highest-priority remaining object. Train from TRAIN outcomes / demonstrated successful sequences with incomplete-label masking. | Masking a graph node is a *sequencing hypothesis*, not proof that an object is a blocker or can be removed. Do **not** create the goal graph from hidden successful repairs or ask a teacher which objects should move at inference. The original desired-arrangement GED is **not defined** for our target-only task; the task-goal graph/learned similarity is an explicit replacement, not original SimGNN fidelity. |
| Image-based PUSH and GRASP Q-maps | **GRASP-only** action-value/feasibility scoring, using actual permitted side-grasp candidates or their common high-level object-action proxy. The push head and any push execution are disabled. Use local *step-level* simulator experience or sufficiently scoped phase/witness annotations for labels. | If true step-level labels cannot be produced locally, do not misrepresent a whole-sequence label as an individual grasp label. Document a `GRASP_HEAD_NOT_SUPERVISED` limitation and provide a transparent GRASP-only ablation, not an invented Q-learning result. Avoid changing the shared lower-level grasp planner or passing a privileged grasp oracle to this baseline. |
| Visual correspondence between current-object patch and **goal arrangement image** for PLACE | **Task-conditioned correspondence/heatmap**: original-scene/object patch + known target/goal representation + scene occupancy and candidate support cells -> learned scores over permissible destination cells. Train only from observed successful complete repairs and Q2 conditional placement signals where semantically appropriate. | There is no ground-truth goal location for relocated **non-target** objects. Do not render privileged teacher-corrected endpoints as a goal image. Do not copy the paper's PLACE cross-entropy as though every object has exactly one correct destination. Use a multi-positive, partial-label loss and mark the changed goal modality. |
| Multiple PUSH, swap, disposal/bin and grasp actions | Restrict exclusively to K<=3 unique non-target **side-grasp pick-and-place** corrections with fixed original-empty cells; original target attempted last. | Original capabilities are removed by benchmark constraint, not silently reintroduced. Report zero push/swap/disposal actions by design. |
| Original closed-loop observation after each action | **Primary:** open-loop, simulated edits in the policy's input only, one sequence. **Optional secondary:** physically reobserve and run the same policy after each executed step, reported separately from the one-shot methods. | Do not give closed-loop corrective feedback to the primary line when Approach B/REAP/DISCO-Grid strict protocol is open-loop. |

**Name of the method in every paper, code README and chart:** `SORC-Grid (adapted Tang & Sukhatme 2022; grasp-only, target-goal-conditioned)`. **Do not call** it "OSNet/RPNet", "original SORC reproduced", a full learned X/Y Boltzmann model or a no-planner physical trajectory policy.

---

## 3. Inputs, action grammar, and target-feasibility interface

### 3.1 Learner-visible input at root

Use the exact `benchmark.py public` JSONL row `{root_id, domain, inputs}`. Each `inputs` record has object IDs, `tid`, `cells0`, `legal_cells`, `goal_cell`, attributes (`fixed` flag where applicable), cell coordinates, robot context and target-goal representation as defined by `contracts.view2d/view3d`. Construct a graph with object and robot/goal nodes using only these public quantities and optional *initial-scene* render/masks. Do not inspect `K_legacy`, split metadata inside a public inference row, teacher labels/phase, root family ids, oracle target swept volumes, private index, future edits or future robot state.

The graph's **goal specification** consists only of the publicly specified original target, desired goal cell / pose and fixed scene geometry. No full desired non-target arrangement exists. Graph edges may encode public relative distance, support, projected occlusion/direction and task-conditioned relations; do not silently invoke full physical collision/IK/motion checks to construct them at inference. In the training split, a learned graph comparison score can be trained against *decided* operational outcomes. If the agent proposes analytical target-action corridor features, preregister them as public **proxy geometry** and ablate them; never substitute a private teacher trajectory/sweep.

### 3.2 Legal moves

Write **one adapter** to call/reproduce the active `benchmark.legality` and `search.Root.legal_dests` behavior, with invariant tests. Formally, for initial occupied cells `Occ0` and target goal cell `g`, a legal destination `d` must satisfy `d in Support`, `d not in Occ0`, `d != g`, and be unoccupied in the current hypothetical prefix. Objects must be movable non-target entities, not already moved. No two chosen moves share a destination. Endpoints are unique physical cells, not continuous off-grid poses; 3D preserves the validated shape/support/offset conventions.

```text
Candidate repair r = [(object_id_1, destination_cell_1), ...]
0 <= len(r) <= 3
one relocation per non-target movable object
original target action appended implicitly at the end, never a corrective r-entry
```

### 3.3 Teacher outcomes and prediction status

For a proposed r, do **not** compute teacher X/Y during model inference. Teacher X/Y are used for TRAIN labels and independent post-seal verification:

- `X(r)`: under pinned budget, execute exactly r physically in order, with continuous robot state, and connect to `q_ref` at the end.
- `Y(End(S0,r))`: target-from-`q_ref` result in canonical hypothetically edited endpoint scene; **same Y** for endpoint-identical different orders.
- `Z(r) = X(r) AND Y(End(S0,r))` when both recorded under the exact contract.
- Empty r: `NOOP` only if the policy predicts target already succeeds; the evaluator checks actual `Y(empty)`.
- `ABSTAIN` is permitted if the policy cannot find an admissible predicted repair. It never claims universal impossibility.
- A teacher failure/exhaustion is not a *certificate* of globally impossible motion, and unattempted/unknown labels never become negative.

---

## 4. Minimal integrated SORC-Grid model, with genuine learned components

Use separate per-domain networks (2D and 3D) with **identical semantics** but input dimensionality adjusted for 8x8 vs 6x6; do not share a checkpoint across embodiments without explicit experiment. Target hardware is a **single 8 GB local GPU** *(amended: or the gvlab2 GPU, <= 18 GB)*; prefer modest shared encoders and small heads, not replicated multi-GB backbones.

### 4.1 Graph-based object sequencer (the central original-paper mechanism)

- Build permutation-equivariant graph tokens for eligible movable objects, fixed obstacle objects and target, plus robot/gripper and desired target-goal nodes. Feature candidates: normalized position, size/type, support, movable/fixed flag, target/goal relation and robot reference q; if a local initial RGB-D renderer is verified, add mask-pooled compact visual features.
- A compact graph encoder (e.g. 2–3 message-passing layers, width 128) computes scene/object features. **Use the same trained encoder** to score a candidate object after virtually masking its node in the *graph comparison*, not by changing the physical scene or pretending the object vanished.
- Construct an explicit **task goal graph** using only target/goal and fixed geometry, rather than faking a fully corrected final arrangement. A similarity/difference head scores `S(G_current minus node i, G_goal-task)`. Document exactly what edit distance/similarity means: since this is not the paper's labeled full-arrangement GED, call it **learned task-conditioned graph difference**, not exact GED or original SimGNN pretraining.
- Score eligible objects and include `STOP` / `ABSTAIN` decisions from a **small goal-completion head** on the same task-conditioned graph. There is no external symbolic TAMP planner. The learned STOP head uses only TRAIN Y(empty)/Y(endpoint) labels under the correct scope.
- Guard against trivial identity shortcuts: object-order permutation invariance, node mask validity, fixed/target nonselection, and counterfactual object-pose sensitivity tests.

### 4.2 GRASP-only action/value component

- Original SORC's high-level Q-map branches over PUSH/GRASP and orientations. In our legal grammar PUSH is forbidden, so there is only **GRASP**. Preserve a **learned masked GRASP score** for legal object candidates or side-grasp approaches as the replacement for action-selection; the existing low-level side-grasp motion planner still chooses a physically permitted realization. Do not invent high-level decisions outside `(object, destination)`.
- Training positives: explicitly replayed **step-level successful** grasps/relocations or COMPLETE X=1 traces whose achieved per-step phases are unambiguous. Step-specific failures only if their phase and attempted candidate are recorded; other failure labels remain masked. Do not label the first action negative from `X(r)=0` when later moves might have failed.
- If the original local teacher has no safe intermediate-state/step APIs, use **logged offline witness prefixes** and a supervised action-value/feasibility head, labeled as an adaptation; a full TD-style Q-learning claim requires actual local simulated transitions and reward accounting. Never fabricate replay data by teleporting a robot or by applying X/Y predictor probabilities.
- Outputs must be distinct from the sequencer and PLACE heatmap, with at least one targeted ablation showing its benefit or null result. GRASP score can reweight choice among permitted objects, but **must never override a legal/physical constraint or grant a new grasp**.

### 4.3 Correspondence-style learned PLACE distribution

- Inputs: original/current *hypothetical* image/occupancy scene, selected object patch/token, target and original-goal map, legal destination mask; build an image-patch-to-cell correspondence/attention score analogous to SORC's feature correlation, with occupancy penalty. If only known primitive rendering is possible, disclose that and test structured-only vs render-based features.
- Output: **one learned categorical distribution over every legal physical resting cell** (`64` potential cells in 2D, `36` in 3D before legality masking); do not sneak in Approach B's cVAE, pretrained Q2 weights or XYNet.
- Goal locations for **non-target** obstacles are *not provided*. Do not use an oracle-corrected reference image. Successful TRAIN complete sequences may produce a set of admissible destinations for the same object/context, not a unique prescribed pixel. Q2 isolated-placeability examples can train a **separate auxiliary conditional-placement head** or constrain a loss **with provenance**; they cannot be treated as goal-restoring repairs. A placement may be easy and still useless for the target.
- During inference score legal cells once for the selected object, choose one destination (or an explicitly preregistered small set, secondary only), and add that move to the predicted prefix. Only hypothetical object-pose edits are used to generate the next policy observation; robot q is not manufactured.

### 4.4 STOP and admissibility decisions

- Evaluate initial `STOP` before moving (K0); after 1–3 hypothetical moves evaluate the learned target-restoration score and GRASP/executability confidence. A low partial-prefix target score **must not automatically terminate the search** before K3; K1 and K2 may fail Y while K3 succeeds.
- At depth 3, stop and output the highest-ranking predicted complete prefix only if it passes the **validation-calibrated** admissibility threshold. Otherwise `ABSTAIN`. A `STOP` after a hypothetical prefix means output that **whole prefix**, not execute target and then choose more corrections.
- No end-to-end physical checker feedback is used to rank proposals. The policy may predict task feasibility, but physical truth is evaluated independently.

---

## 5. Teacher-aligned training samples and losses (no fabricated negatives)

### 5.1 Build root-local, deduplicated training supervision

- Load only `split=train` roots. Each `root_id` is a unit of statistical independence; join V1 and V2 evidence by `(root_id, ordered sequence)` for X and `(root_id, sorted endpoint assignment)` for Y. Resolve exact duplicates and logged conflicts through provenance; never count six orders sharing one Y as six independent Y observations.
- Recover every **witnessed** successful full repair with complete decided `X=1, Y=1`; create **prefix-level positive candidate actions** when physical trace supports the action and its actual order. Deduplicate repeated sequences and missing values.
- For each observed Y endpoint construct the canonical hypothetical *object-only* edited scene; this can train STOP/goal-head Y predictions, but **is not evidence that the robot executed the edit**. Y=0 endpoint labels may train the task goal head; they may not label a specific object as ungraspable.
- For each X=0 ordered sequence, use only the **whole-sequence operational outcome** or specifically localized phase evidence. It is not proof of a particular individual failed step or a globally impossible correction.
- Missing/unobserved sequences and destinations remain **unlabeled**. Use **partial-label positive-only or contrastive objectives** against legitimately observed decided competing candidates; don't train false binary zeros for every unobserved cell.
- Cache small graph/image tensors once per local root/split (separate hashes), not thousands of duplicate goal images or large dense all-sequence tensors. Ensure class balancing does not leak `K_legacy` as a feature.

### 5.2 Losses

Specify each loss and mask in code, log label availability per batch:

1. `L_graph` — multi-positive/selective **first-action set** ranking. Positive candidates are first moves of witness-verified successful sequences with declared provenance. For a fully comparable root/prefix pool, use set likelihood such as `-log sum_{a in Pos} softmax(score(a))`; with unknown candidates, use a **positive-unlabeled/listwise masked** variant rather than assuming all other objects fail. An exact original-paper GED/similarity BCE is allowed **only** if a legitimate task-goal graph GED target is independently defined without leaking repaired goals; otherwise label this learned graph-ranker adaptation.
2. `L_place` — masked softmax over legal destinations for a selected object, using multi-positive observed successful repair destinations and optionally weighted conditional Q2 placeability. Distinguish `P(placeable|grasped)` from `P(useful for target repair)`; record source, root/prefix, and coverage of each target.
3. `L_grasp` — Huber/BCE/TD on **actual available** individual grasp/relocation phase labels; no loss on unresolved/uncertain attribution. If learning from replay rewards, state the reward exactly and discounting / bootstrap behavior; do not report deep Q-learning when only supervised replay classification was used.
4. `L_stop` — masked BCE for target-from-q_ref Y on original and canonical edited scenes, with endpoint dedup. This is the baseline's task-completion head, not the host Approach B Boltzmann predictor. If desired, a separately labeled complete X success auxiliary may regularize the action policy **only** with exact ordered-X labels, never from geometric proximity.
5. `L_cost` — optional small auxiliary Huber on witnessed normalized joint travel **only** when the same source code provides verified comparable witness cost, mask missing; otherwise **no learned cost**. At inference deterministic K and displacement penalties are allowed if preregistered identically to other methods, with exact accounting.

`L = λg L_graph + λp L_place + λq L_grasp + λs L_stop (+ λc L_cost if measured)`. Start with declared equal positive weights for active heads, then tune only on TRAIN/VAL. Report per-head sample counts, mask fractions, calibration and ablations. Do not call every factor a learned *causal* quantity.

### 5.3 Concrete modest training settings (PROPOSALS; freeze after a local dry run)

- Encoder width `128`, graph layers `2–3`, small residual/patch encoder rather than compulsory DenseNet-121, top-down/cell heatmaps, object count capped **by actual observed max**, not guessed. Preserve fixed/target/unknown masks.
- `AdamW`, initial learning rate `3e-4`, weight decay `1e-4`, batch `8–16`, gradient accumulation if needed, max `50` epochs, validation patience `8`, gradient clip `1.0`, seeds `0,1,2` as feasible; mixed precision only if parity/finite-loss tests pass.
- **CPU-only smoke** before GPU. One GPU training process, automatic VRAM check, no tensor caches retained on GPU across epochs. If local RTX 5060 8 GB and torch CUDA is available, target <= `6 GiB` allocated, safe OOM recovery (lower batch / gradient accumulation), no long-lived multi-GPU code.
- Train 2D and 3D separately, identically scoped; do not claim image-based generalization if rendering only known primitives. Quantify validation under each domain independently.

### 5.4 Local teacher collection only if required

Existing X/Y and Q2 evidence are the starting point; do **not** launch new full-grid oracle collection to train a sequencer. Only if GRASP-step supervision is demonstrably insufficient, a bounded **TRAIN-root-only** local teacher sub-study is permitted after a preflight budget: e.g. pilot 20 roots/domain, cap 2 candidate actions/root, pinned original grasp candidates, no changing teacher budgets or simulator. Log CPU-seconds/query, witness/phase coverage and local memory; then scale **only within a separately declared local wall/CPU budget**. Stop and report if projected cost is impractical; a transparent supervised adaptation is preferable to falsely claiming full TD reproduction.

---

## 6. Inference algorithm — one integrated policy, one frozen proposal

```text
INPUT: one public root R = (original scene S0, robot context q_ref/q0,
       target T, goal g, legal support cells), frozen network parameters
SET prefix r = [], hypothetical object poses = S0 object poses
FOR t = 0, 1, 2, 3:
    score task-conditioned STOP from public/hypothetical graph
    record candidate completed prefix r with learned stopping score
    IF t == 3: break
    build graph of hypothetical object placements (never physical robot state)
    for each eligible not-yet-moved non-target movable object:
         graph edit/similarity sequencing score + masked GRASP score
    select object using frozen learned policy and deterministic tie-break
    obtain learned PLACE distribution over ALL legal original-empty cells
    select one statically legal physical destination with learned policy
    IF no legal object / destination: break
    append (object_id, destination_cell); update hypothetical OBJECT poses
END FOR
From the visited completed-prefix candidates select ONE via frozen
VALIDATION-only STOP/admission/cost rule; if none admitted -> ABSTAIN
if selected prefix is [] -> NOOP else -> REPAIR with ordered moves
WRITE the prediction for R; never invoke a teacher or live motion planner
```

This **greedy sequential selection** is the primary SORC-Grid analogue. A beam/tree expansion ablation may be added if carefully declared and charged but is **not** allowed as an unreported default. Crucially, a chosen prefix is only *predicted* to succeed; the independent `benchmark` verifier decides whether it actually restores the target. No fake robot q updates, no unsupported object motion, and no retry.

### 6.1 Exact adapter output

One immutable JSONL row per root, matching `approach_b_final/benchmark.py`:

```json
{
  "root_id": "<copied from public root>",
  "domain": "2d",
  "decision": "REPAIR",
  "moves": [{"object_id": "<original stable ID>", "object_index": 2, "destination_cell": 15}],
  "method": "sorc_grid_adapted",
  "model_hash": "<actual sha256>",
  "inference_mode": "open_loop_one_shot",
  "timing_s": {"total": 0.0},
  "n_graph_queries": 0,
  "n_grasp_queries": 0,
  "n_place_queries": 0
}
```

`0.0` and `0` above are **schema illustration only**; replace them with measured values. `NOOP` and `ABSTAIN` must have `moves: []`. Never output K, teacher labels, oracle collision distances, private masks or causal certificates. `benchmark.validate` must pass for every emitted row. `benchmark.seal` creates the immutable prediction seal before any teacher query.

---

## 7. Evaluation plan: directly paired with REAP, DISCO-Grid, Approach B

### 7.1 Primary comparison (must match host's public/teacher boundary)

- Use exactly the same **public roots**, robot geometry, original target/goal, K<=3 grammar, q_ref, X/Y teacher, phase policies, legal cells, and deterministic verification budget. No per-method budget escalation; local runtime machine is reported for SORC, and cross-machine runtime claims require normalization or a separately matched machine run.
- The policy is **one-shot open-loop**; its own sequence decisions are permitted to be sequential *neural* calls under hypothetical object edits, but no privileged physical result can condition them. Seal all predictions BEFORE physical evaluation. If a proposal fails, count as failure/unknown according to actual verifier; never repair it with second-best sequence.
- Do not silently use existing test or incoming 1,120-scene expansion for tuning or trial selection. Development plots: TRAIN diagnostics, **VALIDATION** comparison. The **primary locked test** will be applied only when externally authorized after model/config freeze.
- SORC on 2D and 3D are two separately trained domain models and two separate verified tables. No shared teacher result is to be interpreted as achieved robot execution by SORC before verification.

### 7.2 Required primary/secondary metrics

1. **Original-task success on K1/K2/K3**, and separately **per K** (complete verified `X=1 AND Y=1`, denominator = independently evaluable roots; UNKNOWN fraction explicitly displayed).
2. **K0 NOOP accuracy**, **NONE abstention and false-repair attempts**; NONE is a restricted-label category, not global impossibility.
3. **Failure decomposition:** X failure versus Y failure versus unknown/replay/infra, as returned by common harness. Do not score X/Y prediction as if the method itself produces calibrated X/Y unless it has a dedicated, calibrated head with held-out truth.
4. **Action economy:** `K_selected` distribution, success by K, selected displacement cost, normalized witnessed joint travel `J_complete` only with valid comparable trajectories; no imputed cost for failed/unknown predictions.
5. **Compute:** CPU-seconds and process CPU, GPU model/device and peak VRAM, memory, latency p50/p90/p99, graph/GRASP/place forward counts, original teacher calls at verification (separate), model parameters, local training compute and data/query budget. Do not suggest cross-machine inference time is directly comparable without matched re-runs.
6. **Paired uncertainty:** 95% group/lineage-cluster bootstrap with same K stratification/weights as `benchmark.summarize`. Compare on **identical roots**. Independent seeds and validation-only stop threshold selection. No pseudo-replication of X/Y queries as independent roots.
7. **Mechanism metrics:** positive first-action recall against decided candidate pools, observed useful destination recall / hit@M (not physical hit on unlabeled destinations), action GRASP success classification where labels exist, STOP Y AUROC/AUPRC/NLL/Brier/ECE, object-order contrast sensitivity when same endpoint assignments have decided differing X, fixed-robot original-target no-op predictions, and conditional placement vs target-restoration distinction.

### 7.3 Mandatory ablations (all evaluated on same validation roots)

- Full learned graph sequence + learned GRASP score + learned PLACE + learned STOP (**primary**).
- Graph sequencer replaced with deterministic legal-object order (isolates learned sequencing).
- Learned PLACE replaced with matched uniform/legal/stratified selection (isolates learned placement).
- GRASP head removed or constant, if actual grasp labels permit a trained head (isolates action-value contribution).
- Task-goal conditioning removed (tests whether learned model uses target/goal rather than generic clutter clearance).
- Structured-only vs initial-render-assisted features, **only if both are locally producible**; expose missing RGB-D rather than asserting paper-style image equivalence.
- Optional learned STOP vs validation-frozen simple score threshold; no hidden oracle STOP.
- Optional beam width >1 **secondary only**, with exactly charged proposals and separate name.

### 7.4 Visual audit and example plots

Save **scene-backed**, non-artistic representations: original root with actual target and goal, numbered proposed corrections and legal ghost destinations, final hypothetical object arrangement, side-grasp/collision evidence overlay **only from independent post-seal verifier**, graph sequence score bars for each eligible object, PLACE heatmap with legal cells, observed X/Y result, first physical failure stage, 2D arm/3D xArm actual checked trajectory when a complete witness exists; `NOT_RUN` elsewhere. Keep same axis/camera within matched scenes. A minimum of K0, each K1–K3, NONE, successful and failed examples per domain (where present) and one same-endpoint order-sensitive pair.

---

## 8. Local-only engineering and minimal source ownership

Recommended one isolated worktree/branch `baseline/sorc-grid` (use a new local branch based on a pinned stable source; **not** the active V3.4 generation checkout) and a small subtree. Do not modify `approach_b_final/teacher2d.py`, `contracts.py`, `benchmark.py`, `evaluate.py`, `onpolicy.py`, original source snapshots, archived model checkpoints or any V3.4 generator/expansion file. Add an adapter instead of changing the benchmark contract.

```text
baselines/sorc_grid/
  README.md                 # adaptation/fidelity, local setup and exact commands
  config.toml               # paths, hashes, CPU/GPU caps, training/validation knobs
  data.py                   # read-only source audit, splits, labels, masks, raster input
  graph.py                  # goal-conditioned graph and candidate node masking
  model.py                  # compact graph, GRASP, PLACE and STOP modules
  train.py                  # losses, train/val loops, checkpoints
  policy.py                 # stateless greedy policy + benchmark JSONL adapter
  run.py                    # one thin CLI: audit / smoke / train / predict / report
  tests/                    # focused data/legality/invariance/teacher-contract tests
  reports/                  # newly generated audit, plots, figures, metrics, decisions
```

Use **existing installed shared robot/harness code** via a small read-only imported adapter, do not copy entire teacher or rebuild a simulator. Prefer 120–280 logical lines per Python file; if >300, split one coherent responsibility. Plain PyTorch, NumPy, stdlib TOML/JSON, and existing project environment only. New package installs must be local in an isolated environment and pinned after passing smoke. No generic plugin registry, notebooks as required runtime, second dataset generator, excessive folder nesting or internet-inference dependency.

### 8.1 Only user's laptop resources *(amended: + gvlab2 GPU, see top)*

- P0 print `hostname`, `uname`, `nproc`, physical/logical CPU, available/free RAM, disk space, CUDA availability, `nvidia-smi` if available, `torch.__version__`, CUDA runtime and GPU name/capacity. Do **not** infer performance solely from earlier hardware reports.
- Previously recorded laptop: Ryzen 9 8940HX (32 threads), approximately 31 GB total RAM, RTX 5060 8 GB; current free RAM may be only 7–8 GB. **Re-detect now.** On this GPU a torch build with working sm_120 support was previously documented as `torch 2.9.1 + cu128`; do not force historical torch 2.5.1 / cu121 or an untested CUDA wheel.
- **Hard local caps (initial defaults, reduce if telemetry requires):** 1 GPU training/inference process; no more than `min(16, max(1, logical_cpus - 6))` CPU workers for teacher work; no more than **4 CPU workers** for data loading; constrain `torch` intra-op threads to `min(8, physical cores)` for training and measure; retain >=4 logical threads and >=4 GB **available** host RAM when possible. Avoid simultaneous CPU physics collection and GPU training if memory constrained.
- First 2D/3D teacher smoke uses 1–2 workers and tight per-call wall/cpu caps. Estimate total teacher CPU cost from the pilot; **never launch hundreds/thousands of unbudgeted simulation tasks**. Graceful Ctrl+C, checkpoint/resume, per-root transaction logs and disk-quotas. Thermal guard, RAM guard and OOM fallback; never increase teacher planner budgets to make this method look better.
- Peak VRAM target <=6 GiB on 8 GiB GPU. Use small images (e.g., 128–192 px square initially) and 8–16 batch, selective data caching, fp32 baseline; only enable autocast after loss/metric parity and max allocated memory evidence.
- Absolutely no `ssh`, `scp`, `rsync user@host`, remote shell, SLURM, Ray cluster, cloud notebook, external GPU API, mounted server compute, or writing to another agent's run files *(amended: except the gvlab2 GPU path of the owner amendment)*. Dataset **already copied locally and hash-verified** is allowed to be read; missing source is a blocker and must be reported.

---

## 9. Tests and invariant gates (fail closed)

### P0 — Repository + paper fidelity + local data gate

- Inspect correct paper and supplementary, record exact methodology differences in `reports/SORC_FIDELITY_AUDIT.md`.
- Resolve branch/commit, original source modules, teacher and config hashes; check hardware and local data paths. Audit snapshot counts/coverage locally against Table 1; unique X/Y signatures and train/val lineage. Confirm test expansion remains untouched.
- `PASS` only when public input loader, labels masks, local 2D and 3D teacher imports and dataset provenance are verified; if 3D assets absent, report `BLOCKED_3D` and implement 2D path without pretending 3D parity. No training.

### P1 — Legal grammar + policy interface gate

- Build one deterministic high-level legality adapter; verify identical verdicts against `benchmark.validate` for random legal/illegal sequences in both domains.
- Test K0, K1–K3, target-not-movable, fixed-not-movable, move-once, original-occupied destinations, reused vacated destination, same destination twice, target-goal exclusion, 2D/3D legal support and offsets, order preserving, padding/IDs, 3D box/cylinder shape. Test model NEVER receives `K`, X/Y teacher, replay or private test index.
- One minimal adapter predicts explicit `NOOP`/`ABSTAIN`/`REPAIR`; no teacher calls. `PASS` when the host `validate` accepts all legal entries and rejects every constructed counterexample.

### P2 — Goal-graph, rendering and supervised-sample provenance

- Build original and hypothetically edited graphs, renderer provenance, graph node removal for scoring and legal destination masks. Confirm permutation equivariance and target/goal sensitivity.
- Build positive sets from X/Y train labels **only**, without treating missing as negative; no six-permutation Y inflation. Every sample must have provenance and loss mask. Explicitly audit whether grasp-step labels are possible. Generate matched 2D/3D figures from available local scenes.
- `PASS` when split leakage = 0, group root provenance preserved, every loss has declared decided teacher targets, rendering is observation-only, all counters are logged.

### P3 — 2D CPU smoke, then local GPU train

- Tiny seed-controlled TRAIN subset (e.g. 24 roots), held-out 8-12 VALIDATION roots, full forward/backward, loss decreases and nonzero gradients for all active heads. Demonstrate overfitting tiny training sample without outcome leakage; no claim of generalization.
- Verify model selects different objects for analytically distinct original target/goal contexts, GRASP head uses only permitted candidates, and PLACE assigns zero probability to illegal cells. Run GPU microbenchmark and memory log. If step-level labels unavailable, explicitly mark the GRASP head limited rather than invent results.
- `PASS`: finite losses, correct masks, deterministic checkpoint/reload and prediction reproducibility, no forbidden oracle in model path.

### P4 — Complete 2D/3D TRAIN + VALIDATION baseline

- Train on existing train split and (optionally) additional properly scoped TRAIN-only Q2/witness data; early stop/tune on VALIDATION. Train each domain separately, 3 seeds if local resources permit; if constrained, report 1-seed preliminary clearly and continue remaining seeds only under the approved local budget.
- Run open-loop learned-policy VALIDATION inference one root at a time, choose one sequence or abstention; seal output before verification. Use common independent X/Y verifier with same budgets as REAP and DISCO. Local teacher budget must be logged and bounded; don't assume all 7,500 roots need fresh teacher queries.
- `PASS`: primary VALIDATION table with by-K denominators, X/Y failure types, no-op/abstain, inference CPU/GPU and timing, memory/travel and locked model hash. No test evaluation.

### P5 — Faithful ablations, hard cases, figures, limitations

- Run the ablations from §7.3 on identical validation roots and teacher caches; quantify learned graph contribution, placement contribution, GRASP contribution (if trained), target-goal conditioning and any visual-feature benefit. Verify same endpoint order swaps where teacher X evidence exists, and report why graph-only selection can fail on order-dependent physical access.
- Plot requested scene-backed figures/heatmaps, root-bootstrap CIs, resource accounting, failures and mismatch with original SORC domain. Document whether SORC-Grid is genuinely learned and differs from REAP/DISCO and Approach B.
- `PASS` only with complete `SORC_BASELINE_REPORT.md` and zero unfounded "paper reproduced" claims.

### P6 — Freeze for future COMMON held-out evaluation (do not execute new test expansion)

- Freeze 2D/3D weights, normalizers, feature/raster hashes, exact source commit, action grammar, threshold, seed list, train/val root hashes and public adapter, with a reproducibility manifest. **No newly generated V3.4 test roots are accessed or scored in P0–P6.**
- Provide exact commands for the host to later create public test rows, run fixed inference, seal predictions, verify independently, summarize paired results. No tuning on those outcomes after the fact.

**Mandatory failure behavior:** If an acceptance test fails, diagnose and correct within the current stage, rerun tests and clearly label any blocking missing local source. Never silently weaken a motion/grasp rule, relabel unknown as negative, invent a 3D outcome, or switch to a simpler classifier while calling it the original baseline.

---

## 10. Deliverables and acceptance checklist

Output locations are **new and isolated**, not old results. Required:

- `baselines/sorc_grid/README.md`, working code/tests, minimal local config, deterministic CLI, runnable local environment instructions.
- `reports/SORC_DATA_AUDIT.md`, `reports/sorc_dataset_manifest.json`, `reports/SORC_FIDELITY_AUDIT.md`, `reports/SORC_LOCAL_RESOURCE_AUDIT.json`.
- Exact TRAIN/VAL split hashes and any TRAIN sidecars generated **locally**, with complete failure/missingness and time budgets.
- 2D and 3D checkpoints and hashes, recorded seeds and per-head training curves, local CPU/GPU peak usage.
- One `open_loop_one_shot` JSONL prediction per original validation root (K absent in inference), full `benchmark.validate` verdict, immutable SEAL, post-seal physical X/Y query/verification ledger and final independent outcomes.
- `reports/SORC_BASELINE_REPORT.md`: side-by-side constraints audit against REAP/DISCO, mechanisms and fidelity, per-K performance, K0, NONE, travel, time, empirical root-bootstrap CIs, ablations, failure cases, truthful unknowns and explicitly **NOT_RUN** entries.
- At least one 2D and one 3D scene with correctly rendered legal cells, selected movers, predicted destination heatmap and full physically witnessed robot trace (only if verified); no artistic stand-ins presented as empirical evidence.
- `reports/SORC_FREEZE_MANIFEST.json` containing commit/teacher/data/model/config hashes and the exact post-freeze testing procedure.

### Absolute no-go list

No extra symbolic TAMP, no copying Approach B XYNet/cVAE or DISCO/REAP policy weights, no target correction among K moves, no PUSH despite original paper, no object moved twice, no initially occupied destination, no scene-edit oracle during inference, no grasp family widening, no robot q reset, no second predicted candidate after failure, no private K/label/test outcome feature, no GPU outside the local system *(amended: gvlab2 GPU allowed)*, no remote CPU, no test-expansion interference, and no claimed physical success until original teacher/replay verifies it.

### Final naming to put in comparisons

**SORC-Grid (Tang & Sukhatme, CoRL 2022; adapted)** — integrated **learned graph-based object selection + GRASP-only action scoring + task-conditioned placement + learned stopping**, matched to K<=3 fixed pick-and-place and original target-task restoration. Its original publication benchmarks full goal-image rearrangement with PUSH/swap/bin capabilities, so **these reported numbers are not imported into our new task**.

**Research release condition:** the baseline is valid only if it emits independently legal, sealed proposals and a detailed fidelity/compute audit. A lower-scoring SORC-Grid baseline remains a scientifically valid result; changing its constraints, grasp set or teacher budgets to improve it is not.
