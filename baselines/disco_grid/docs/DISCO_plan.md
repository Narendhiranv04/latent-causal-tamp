# DISCO-Grid Baseline — Full Adaptation, Training, and Evaluation Contract

**Project:** Latent Causal Infeasibility for Long-Horizon TAMP / Approach B  
**Document type:** Implementation-ready research and experiment plan (standalone handoff for a context-free coding agent)  
**Prepared:** 16 November 2026  
**Status:** **PROPOSED**. No DISCO-Grid implementation, simulator parity result, trained model, or benchmark number is claimed by this document.  
**Baseline designation:** **DISCO-Grid**, a *discrete object–destination adaptation* of **DISCO: Distilled Tree Search over Continuous Actions** (Saha et al., CoRL 2026). **Do not claim exact reproduction** of original continuous-action, point-cloud, ManiSkill/curobo/Franka DISCO.  
**Host repository:** `Narendhiranv04/latent-causal-tamp`. Historical inspected Approach B branch: `naren/approach-b-final`. A separate Approach B V3 branch may be under development. **Inspect current branches/worktrees before starting.**  
**Official DISCO implementation:** <https://github.com/kallol-saha/DISCO> (pin and log an exact upstream commit).  
**Paper:** <https://arxiv.org/abs/2610.25785> (CoRL 2026, arXiv v1 as inspected).  
**Primary local project plan:** user's **Approach B V3 `plan.md`** (task-aware candidate sets, one-shot complete-repair selection). Treat it as the evaluation/physical-task contract, **not** as instructions for DISCO's internal training-time search.

> **Core scientific contract:** Learn a sequential *action proposal policy* and *state-action continuation value* by iteratively distilling **training-only** progressive-widening MCTS trees generated using our **unchanged physical scene/action/teacher assumptions**. Test the learned policy/value **without simulation-based MCTS at deployment**, on the same 2D/3D roots and independent X/Y final-verification protocol as Approach B. Report original-style **closed-loop** deployment and strict-comparison **open-loop** deployment **separately**. Never describe a behavior-cloning-only or teacher-labelled-sequence-classifier implementation as full DISCO.

---

## 0. Executive decisions, scope, and invariants

### 0.1 Why this is an appropriate learned baseline

1. DISCO is **genuinely learned**: its policy and value are improved through **search-generated physical experience**. This tests an alternative to Approach B's goal-conditioned placement cVAE + joint, order-sensitive F2/F3/F5 complete-sequence scoring.
2. Existing analytical baselines are **E-M4M, MO-SeGMan, and MS-MCTS**; REAP is assigned separately. DISCO-Grid fills the **policy/value distillation** category. Do not duplicate analytical heuristic search and call it DISCO.
3. Our two tasks (8×8 planar 2D, 6×6 xArm shelf 3D) have **discrete destination cells, known geometry and fixed grasp families**, whereas published DISCO uses 3D point clouds and continuous 7D grasp/place poses. This is a real methodological adaptation, not a drop-in port.
4. The principal meaningful comparison is **task-success per root**, under the same hard action grammar and independent physical teacher. A secondary comparison is total training and test computation needed to reach that success.

### 0.2 Must preserve the task and robot assumptions

- **2D:** the existing **fixed-base planar 3R arm**, 8×8 support lattice, original object sizes, fixed/movable classification, gripper geometry, permitted **side-grasp skill/candidate family**, collision and kinematics/planner protocol. Historical source guide mentions a 48-grasp family, but **query the CURRENT finalized teacher/config for the exact active set before hard-coding numbers**.
- **3D:** the existing **xArm7 shelf**, 6×6 cell projection, box/cylinder geometry, robot base/shelf, permitted **side-grasp pitch and offset candidates**, actual planner attempt/IK/RRT limits and MuJoCo execution as pinned by the finalized teacher. **Do not** silently substitute a Franka/Panda, unrestricted top grasps, new gripper orientations or easier collision geometry.
- **Both:** same original scene and goal; only non-target **movable** objects can be corrected. Fixed objects cannot move. The target itself is **never a corrective action**; it undergoes its originally requested target task *last* and is not included in the K≤3 corrective-action count.
- **Bounded repair grammar:** up to **three** corrective pick-and-place relocations (K1–K3); an object may be moved **at most once**; destination must be in the declared legal/support region, unoccupied at the **original** root, not the target goal, and not reused by another relocation. **No swaps, use of a cell vacated by a previous action, stacks, pushes, multi-object moves, temporary object transfer to a robot hand, or extra staging actions.**
- **No silent relaxation:** no planner budget escalation, additional grasps, target-goal change, target-only shortcut, teleportation as physical success, intermediate robot home reset, added return-home actions or successful-plan substitution after physical failure.
- **Robot state:** actual physical/robot state is **carried through all relocations**. For finalized labels, **X** includes execution of ordered relocations **plus the required terminal free-gripper connector to `q_ref`**; **Y** independently evaluates the target task from `q_ref` in the final edited scene. Preserve these definitions exactly.
- **No privileged learner input:** never expose GT blocker IDs, teacher-selected corrections, legacy K/NONE labels, X/Y labels, success witnesses or planner feasibility as neural features. The simulation oracle is exclusively for **training-time transitions/terminal checks** and **independent test-time verification**, not test-time action scoring.

### 0.3 DISCO-specific allowances versus Approach B V3

- **Training:** DISCO **must** conduct internal MCTS, branch expansions, simulation rollouts and repeated policy/value queries at hypothetical **physically simulated** states. Approach B V3's ban on iterative hypothetical search applies to **Approach B**, not to DISCO's offline training. No contradiction exists if the two are evaluated under common deployment constraints.
- **Open-loop deployment (primary apples-to-apples comparison):** sequentially generate up to 3 corrective actions using a **learned prediction of object-position edits**, re-encoding the predicted scene between predicted actions, but **without running physical simulation, motion planning, ground-truth X/Y queries or checking actual intermediate outcomes**. Commit one sequence; physical verifier checks it once, no recovery or second-best trial. Disclose that the baseline uses multi-step neural queries internally rather than one boltzmann pass.
- **Closed-loop deployment (original-style comparison):** after each *actually executed* correction, consume the new observed scene and select the next action, up to K3; **no training-time MCTS**, no hypothetical motion-planner calls for ranking. This is closer to the published deployment but **not a matched-feedback comparison**. Clearly report feedback access and any failed execution handling.
- **No inference-time training:** policy/value checkpoints remain fixed on test. Test-time sensing/robot execution is not equivalent to privileged test-time search.

### 0.4 No-go conditions

Do **not** proceed to large-scale MCTS if the stateful transition adapter cannot reproduce finalized ordered-X, connector and endpoint-Y semantics. **Do not invent simulated action outcomes** using Q2, a grid teleport, an analytic path proxy or predicted Boltzmann probabilities. If the necessary stateful lower-level teacher API cannot be built, record **BLOCKED**, keep a lower-fidelity exploratory model explicitly separate, and do not promote it as a physical DISCO baseline.

---

## 1. Sources of truth and reproducibility audit

### 1.1 Inspect before editing

**Local project:**

- `approach_b_final/contracts.py`: immutable snapshot and learner-visible `inputs` + disjoint X/Y labels, root IDs, 2D/3D feature contracts.
- `approach_b_final/teacher2d.py`: finalized 2D X/Y adapter, independent replay and terminal connector.
- `approach_b_final/evaluate.py`: original-root independent verifier, task-success masks, K0/NONE, physical/travel evaluation.
- `approach_b_final/placement.py`: Q2 records, positive isolated placements, scenes and legal destination masks.
- `approach_b_final/onpolicy.py`: V2 physically labelled complete-sequence data, teacher provenance and missing labels.
- `approach_b_final/search.py`: legal correction grammar and root-scene utilities; **reuse semantics, not Approach B's learned scorer**.
- `approach_b_final/xy.py`: authoritative coupled X/Y probability semantics; **not used as DISCO policy/value supervision**.
- Dataset snapshot manifests such as `reports/results/data_snapshot.lock.json`, `reports/results/v2_data_snapshot.lock.json`, `LOADER_SCHEMA_REPORT*` and referenced raw source packages. **Files may be mounted on a server instead of committed to GitHub.**
- User-provided Approach B V3 `plan.md` — pin its hash, and use it for the latest strict task grammar and evaluation decisions.

**Official DISCO:**

- `README.md`, `run_disco.py`, `pretrain.py`, `config/run_disco.yaml`, `config/mcts.yaml`.
- `disco/search/mcts.py`, `expansion.py`, `candidates.py`, `run.py`.
- `disco/data.py`, `disco/tasks.py`, `disco/policy/models.py`, `disco/policy/shelf_sampler.py`.
- `disco/flowmatch/train_policy.py`, `train_value.py`, and value/policy data loaders.
- Paper sections **3, 4.1–4.3, Appendix B.1–B.4, F.1–F.4**. Verify formula/implementation correspondence, record any code/paper differences.

### 1.2 Record an audit artifact

Create `reports/SOURCE_AND_ASSUMPTION_AUDIT.md` containing exact commits, repo paths, available GPU/CPU resources on the actual host, simulator status, model/dataset paths (do not guess), selected snapshots, active side grasps and collision margins, robot configuration/connector protocol hashes, split family disjointness and verified teacher query types.

Do not assume `gvlab2` provides GPUs because prior work used it for CPU teachers. If implementation is on `gvlab2`, inspect hardware first. Use an isolated baseline worktree and Python environment. Do not interfere with other agents running Approach B V3, teammate data extension, REAP, or physical verification.

### 1.3 Existing data size — historical snapshot, not promised current filesystem

| Domain | Original target roots | Original ordered X labels | Original endpoint Y labels | Added V2 X | Added V2 Y |
|:--|--:|--:|--:|--:|--:|
| 2D | 5,000 | 12,400 | 9,700 | 7,594 | 9,661 |
| 3D | 2,500 | 7,089 | 5,305 | 2,126 | 2,493 |

The Q2 placement records form two further conceptual streams and may reside in uncommitted or mounted source data. They encode individual placement outcomes, sometimes after a hypothetical prefix, **not** guaranteed successful whole repairs. Base and V2 counts should not be naïvely summed as unique scenes, unique assignments or independent labels; deduplicate and retain provenance.

---

## 2. Original DISCO mechanics: what is faithfully retained and what changes

| Component | Published/released DISCO | DISCO-Grid adaptation | Fidelity label |
|:--|:--|:--|:--|
| Pretraining | Feasible single grasp-and-place demos | Positive Q2 placement data; object choice initialized conservatively; fixed low-level grasps | **Adapted** |
| Policy | Two continuous 3D flow-matching actors, grasp then grasp-conditioned placement | Two-part **categorical** object/destination policy, masked legal grid actions | **Changed action representation** |
| Perception | 3D segmented point cloud, PointNet-like/EdgeConv encoders | Existing structured 2D/3D scene and target-goal features | **Oracle geometry inputs / changed observation** |
| Dynamics | Pick/place planning and physical simulator transitions | Identical original 2D/3D low-level robot physics/teacher protocol through a new stateful adapter | **Same benchmark physics, changed simulator wrapper** |
| MCTS | Progressive widening, UCB, simulated expansion, returns | **Retain** training-only MCTS, widening, UCB, rollout backups | **Algorithmically retained** |
| Value | Q(s,a) from fraction of visited successful descendant leaves, log-evidence weighting | Same subtree target and weighted BCE for feasible corrective edges | **Retained** |
| Policy distillation | All feasible expanded edges, not just successful complete plans | Same principle; masked categorical negative log likelihood replaces continuous flow matching | **Training principle retained; loss adapted** |
| Iteration | Search→extract→train policy/Q→fresh trees | Same search/distillation rounds and frozen checkpoint progression | **Retained** |
| Test | Policy+Q direct closed-loop rollouts, without test-time simulator MCTS | Closed-loop original-style; separately reported open-loop fair variant | **Two labelled protocols** |
| Goal | Shelf packing, stacking | Restore known target's physically executable goal task | **Changed task** |

**Do not overstate:** even if MCTS/distillation are exact, the discrete categorical policy and known-state task make this **DISCO-Grid (adapted)**, not the published continuous-action DISCO reproduction. A continuous full-robot reproduction would require new output/action pose datasets, point-cloud observation processing, grasp candidate parameterization, motion planners and likely different environments; it is explicitly out of the main scope.

---

## 3. Formal problem, legal actions and terminal success

### 3.1 Rooted task and action grammar

Each root has original scene `S0`, known target `T`, target goal `g`, geometry, original robot configuration `q0` / declared reference `q_ref`, fixed/movable flags and supported legal cells.

A corrective action is `a_t = (o_t, d_t)`, selecting an eligible movable non-target object and an originally empty legal destination. At a prefix `r_t = [a0, ..., a(t-1)]`, exclude already-moved objects, already-used destinations and invalid placements. Allowed stopping prefix lengths: `t=0,1,2,3`.

Use a **special terminal `STOP` decision** in the adapted policy/value interface. `STOP` means *end relocations and attempt the original target task under the finalized X/Y contract*; it is not an extra relocation, grasp or newly allowed physical action. The original DISCO did not use this exact known-target STOP mechanism, so mark it as a task adaptation.

**Legal static destination set from the original root:**

```
D0 = declared_support_cells
     - occupied_cells_of_original_root
     - {target_goal_cell}
```

Every placement in the episode must choose from `D0`, with no cell reuse and no object reuse. Add any *existing finalized teacher's* stricter static collision/support legality checks unchanged; never widen beyond the shared benchmark. This grammar intentionally excludes freeing a previously occupied slot and then placing into it.

### 3.2 Full physical state versus learned observation

The simulator's **full Markov state** must include at least:

```
root_id; geometry; object poses (3D include offsets/orientation when relevant);
robot joint state q_t; gripper/contact/attachment state; valid physics state;
moved object IDs; used original-empty destinations; action depth;
original target and target goal; random/planner state needed for deterministic replay.
```

The learned **observation** is limited to actually available state data:

```
object positions, object geometry, occupancy/support mask, target/goal,
fixed/movable flags, moved-object mask, remaining steps,
known robot context allowed by the benchmark.
```

Recommended **common default** for open-loop/closed-loop model comparability: use geometry + goal + `q_ref` context, **not actual intermediate `q_t`** as a network input, because the open-loop inference procedure cannot reconstruct `q_t` without executing motion. The simulator still carries `q_t` for physical feasibility. This creates a partially observable learned problem; document it. Optionally test an *additional* closed-loop version with actual observed `q_t`, marked as a different observation budget.

### 3.3 Authoritative X/Y terminal semantics

For a full ordered corrective prefix `r` from `S0`:

- `X(r)=1`: all prescribed relocations are physically executed **in this order**, with robot state carried continuously, and the terminal free-gripper connector to **`q_ref`** succeeds and is replay/verification accepted. A prefix's full `X(prefix)` includes this connector and **must not** be used as a surrogate for whether the prefix's individual action transitions can continue.
- `Y(End(S0,r))=1`: the original target goal is independently checked from `q_ref` in the **canonical edited endpoint scene built by the finalized Y teacher from the original root and the unordered destination assignment**. In the existing contracts, this is not automatically the exact post-execution floating-point object pose state returned by X. Preserve nominal-cell/canonical-endpoint construction where the source teacher does; test carefully in 3D where execution may produce in-cell offsets. Y is independent of relocation order under the pinned Y definition.
- `Z(r)=1[X(r)=1 and Y(End(S0,r))=1]`.
- `STOP` at depth `t` is successful iff the physically executed prefix is valid, the **terminal** connector succeeds, and the target Y query succeeds.
- `K0`: `STOP` at root with Y0 verified true; no correction should be required.
- `NONE`: no repair found by a restricted legacy protocol; **not a certificate of universal physical infeasibility**. Newly found successful repairs must be explicitly flagged, not suppressed.
- Missing/timeouts/admin limits are **UNRESOLVED**, not a negative physics label. Preserve original negative kind and replay/seed/budget metadata.

### 3.4 MCTS terminal branches and horizon

`STOP` is considered at root and after each valid corrective prefix. An unsuccessful `STOP` ends **that termination branch**, but need not prohibit continued exploration of longer corrective sequences from the same physical state. At depth 3, no additional relocation is legal; the only possible completion decision is `STOP`, otherwise failed/horizon terminal. Terminal success never follows directly from an approximate geometric progress score.

**Important subtlety:** A necessary first or second move may fail the terminal `q_ref` connector but still be a valid intermediate step toward a longer repair. Therefore, do not prune an intermediate state by requiring `X(prefix)=1` with a premature connector. Validate individual action execution in its actual carried robot state and apply `q_ref` only at explicit `STOP`/finalization.

---

## 4. Correct simulator-adapter design — the hard prerequisite

### 4.1 Adapter API (pseudocode, not an assertion that it already exists)

```python
class RepairEnv:
    def reset(self, root_id, seed) -> FullState: ...
    def observe(self, state) -> LearnerObservation: ...
    def legal_actions(self, state) -> list[Action]: ...   # static grammar only
    def transition(self, state, action) -> StepResult: ... # actual planner+execution
    def terminal_query(self, state) -> StopResult: ...    # q_ref connector then Y
    def clone_or_serialize(self, state) -> bytes: ...
    def restore(self, blob) -> FullState: ...
```

**`transition` must:**

1. Restore the complete parent scene and robot/gripper state.
2. Try the **unchanged** finite side-grasp and motion-planning skill on the selected object to the proposed cell.
3. Execute the accepted trajectory in the same physics protocol as the finalized teacher; retain final object pose and robot state.
4. Return `EXECUTED`, `PHYSICALLY_FAILED` (with exact status semantics), or `UNRESOLVED` (budget/administrative/tool error), plus time, attempt counts, witness/replay ID and next full physical state if executed.
5. Never teleport/overwrite object pose and call it physically executed. Teleport is allowed only for a **labelled, no-physics predicted-scene edit** used by the open-loop inference generator.
6. Never reset `q` between corrective actions, and never insert the terminal `q_ref` connector between steps.

**`terminal_query` must:**

1. From the carried state, attempt the finalized free-gripper connector to `q_ref` **only when stopping**.
2. Independently run the finalized Y target query **using the original-root endpoint-edit construction**, i.e. the same canonical assignment-to-scene mapping and `q_ref` context as `teacher2d.py`/`fin3d.run_y`, with the same budget and replay rules. **Do not quietly substitute the exact executed post-relocation MuJoCo poses for the official canonical Y endpoint**, especially when per-cell offsets differ. Store both canonical endpoint and physically executed poses; if the mismatch matters, report it as a separate realism diagnostic rather than redefining the benchmark label.
3. Return separate connector/X and Y decisions; `success = X_terminal and Y`, not merely a successful target-only edit.
4. Cache exact repeated Y endpoint queries by **canonical original-root endpoint assignment** + target goal + teacher protocol; cache connector/X by full ordered action/state/robot signature (not unordered endpoint only).
5. For `STOP` at K0, use the existing Y0 protocol and no fictitious corrective action.

**`clone_or_serialize` is essential:** MCTS branches must not cross-contaminate simulator states, robot joint positions, object offsets or random states. If the source simulation API doesn't support arbitrary state restore, implement exact replay from root as a verified slower fallback. Replaying a *whole sequence* via finalized `X_query` is not automatically a correct per-step transition API because it adds a terminal connector and may not expose intermediate robot state.

### 4.2 2D implementation requirements

- Reuse the existing 2D planar arm, actual side-grasp family and dynamic collision checking. Inspect `teacher2d.py`, its pinned `bxy_teacher` source, the underlying planar skill/physics implementation and teacher query statuses. Use the actual currently pinned `geometry_impl` per root.
- If the source has an internal move-step executor that returns a carried `(scene,q,gripper)` state, reuse it. Otherwise factor out a **thin adapter** without changing the source skill's semantics.
- Maintain exact per-root geometry and 8×8 cell-to-meter convention, 0-based cell IDs, robot base and fixed obstacles.
- Label `UNKNOWN_PLANNER`, admin cap, replay mismatch and independent verification failures separately, following the authoritative finalized teacher.

### 4.3 3D implementation requirements

- Reuse **xArm7 + MuJoCo** from the finalized 3D source and exact side-grasp pitch/offset/IK/RRT limits; inspect the actual `fin3d.py`, `bwlphys.py`, relevant robot action primitives and replay audit. The old generation `bd_3d.py` may be useful to understand stateful actions, but it is **not sufficient authority** for the later finalized teacher protocol.
- Preserve object box/cylinder dimensions, original cell and in-cell offsets, shelf geometry, robot joint start/reference (SHELF66 uses a pinned `q_ref`), and independent terminal target check.
- A root `cells0` coordinate alone may not reproduce the full executed MuJoCo state; store/carry sub-cell offsets, contacts and `q_t` as needed.
- Do **not** import DISCO's ManiSkill/Franka/curobo low-level execution as the physical evaluator; that would materially change the task. Use an isolated DISCO fork only as a reference implementation for MCTS and distillation.

### 4.4 Required parity tests (gate before ML training)

Create a deterministic fixture set **from TRAIN only**, stratified by 2D/3D, K0, K1/K2/K3, order-sensitive successes/failures, and endpoint Y positives/negatives. For each decided existing record:

1. Replay the same complete sequence with the new `reset` + repeated `transition` + `terminal_query`.
2. Compare the independently finalized X result, Y result, stop/connector phase, actual endpoint and replay status to stored authoritative labels.
3. Compare alternative orders sharing a **canonical endpoint assignment**: Y should be identical under the finalized Y mapping, while X may differ; check executed sub-cell offset differences separately rather than accidentally changing Y.
4. Check K0/empty repair, fixed objects, forbidden destination/source/goal, never-move-target, repeats, restored state, gripper attachment and robot `q_t` carryover.
5. Distinguish true contradictory labels from nondeterministic/status/budget unresolved results; document disagreements and exact provenance.
6. **Hard gate:** no known unexplained contradictory physical **decisions** on the audited fixture set; otherwise stop and fix. Report `n_checked`, `n_decided`, `n_agree`, `n_disagree`, `n_unresolved`, by domain and failure phase. **Do not assert 100% parity on untested data**.

Only after this gate can simulated MCTS-tree transitions be treated as physical teacher experience.

---

## 5. Training data contracts and the baseline's clean input boundary

### 5.1 Source roles

- **Q2 2D/3D:** pretrain the destination policy using individual *observed successful* placement outcomes; include their actual hypothetical scene context if available and legal. Do **not** treat all original root objects as demonstrated choices, or Q2 negatives as false whole-repair actions.
- **Target X/Y 2D/3D:** validation fixtures, successful complete sequence checks, optional **separately disclosed** initialization/control. They are **not** automatically transitions or MCTS subtree-value targets.
- **V2 on-policy X/Y:** useful additional audit/initialization controls and outcome verification. Never directly inject original Approach B model's prediction (`p11`, energy, chosen blockers) into DISCO training or inference.
- **Incoming teammate extension:** optional later ablation. Keep baseline primary training from existing fixed sources so comparisons do not depend on a future delivery.

### 5.2 Canonical schemas

Example **scene root** (values illustrative):

```json
{
  "root_id": "...", "domain": "2D", "split": "train", "family_id": "...",
  "root_sha256": "...", "inputs": {
    "ids": ["t0", "A", "B"], "cells0": [5, 17, 22],
    "attrs": [[...], [...], [...]], "tid": 0, "goal_cell": 40,
    "legal_cells": [0, 1, 2], "q_ref": [0.0, 0.0, 0.0]
  }
}
```

Never fabricate the above values for an actual root. Derive them using `contracts.py` and its source hashes. Source 3D records also contain details beyond the compact compiled grid view.

**Training rollout edge** (one action executed *at a physical intermediate state*):

```json
{
  "root_id": "...", "tree_id": "...", "parent_id": 10, "child_id": 37,
  "depth": 2, "action": ["B", 31], "parent_state_hash": "...",
  "child_state_hash": "...", "status": "EXECUTED", "failure_kind": null,
  "observation_ref": "...", "trajectory_ref": "...", "time_s": 0.0,
  "sim_teacher_version": "...", "planner_calls": 0, "seed": 0
}
```

Store the actual measured runtime/calls; the zero values above are *schema examples only*.

**Per-tree distilled value row:** `(root_id, parent_obs_ref, action, n_success_visited_leaves, n_visited_leaves, value_target, evidence_weight, tree_round, provenance)`.

**Policy row:** `(root_id, parent_obs_ref, feasible_action, tree_round, provenance)` from **feasible expanded edges**; a negative/unknown attempted action does **not** become a feasible policy target.

**Terminal observation:** `(prefix_action_ids, stop_depth, terminal_connector_outcome, target_Y_outcome, Z_outcome, failure_kind)`.

### 5.3 Strict data leakage rules

- Split by original root/parent family, not by individual tree edge; all descendants and alternate orders from one root remain in one split.
- Fit all normalizers on TRAIN only. No GT K, masks, X/Y outcomes, teacher labels, scene-solution assignments or future test trajectories in network inputs.
- Training-time MCTS simulations must run only on TRAIN roots. Validation roots can be physically queried for **fixed-checkpoint evaluation/tuning** within a declared limited budget, but may not be used to distill model weights. Freeze validation policy before final test.
- Historical published V1/V2 test outcomes have already been inspected; note that they are **not a newly untouched test cohort**. Never tune DISCO using these tests; for strongest independent claims reserve new roots/families.
- Keep every produced training/validation/test artifact split-stamped and provenance-hashed.

---

## 6. Policy model: correct discrete adaptation and losses

### 6.1 Factorized action proposal

Use one scene encoder shared **within DISCO only**, providing object tokens and a goal-conditioned scene token. The adaptation's policy factorizes:

\[
\pi_\theta(o,d\mid h_t,T)
=\pi_\theta^{\mathrm{obj}}(o\mid h_t,T)
\;\pi_\theta^{\mathrm{dst}}(d\mid h_t,o,T).
\]

`h_t` is the allowed learned observation, including current/predicted object poses and already-moved mask; `T` denotes target and goal context, not a teacher label. Restrict categorical distributions with valid object/destination masks, normalize after masking; prohibit zero-support NaNs. Different objects may have very different legal destination counts.

A compact set/attention or relational encoder is appropriate; **do not reuse cVAE weights or Boltzmann trained energies**, and do not introduce a giant unrelated VLM. Use separate weights for 2D and 3D unless a joint-domain experiment is explicitly preregistered.

`STOP` is an additional action token/mode; teach it from physical terminal success/failure, not from legacy K. **Value training for STOP is a special case:** include all **decided** STOP attempts in a small binary value dataset with target `Z_stop∈{0,1}`, including **failed** STOP attempts as negatives; STOP is not a physically feasible relocation edge and must not be silently filtered out by the ordinary policy-edge extraction rule. A successful STOP can contribute to the policy's STOP-positive supervision; unsuccessful STOP does not become a demonstrated feasible policy action. Prefer scoring `STOP` with the **same Q network** and including it as an eligible terminal action; do not introduce an independent oracle-based stop classifier. The policy may expose a STOP logit, but P0 may keep conservative fixed STOP exploration because Q2 lacks target completion labels.

### 6.2 P0 pretraining on Q2

Q2 includes an explicitly **queried object**, not an expert object-selection decision. Thus:

- Learn `pi_dst(d | scene, queried_o, goal_masked)` with **positive, observed feasible** Q2 examples using masked CE. Treat unknowns as unknown; negative Q2 trials can be used for evaluation and separately disclosed auxiliary feasibility filtering only.
- Do **not** train `pi_obj` by declaring the Q2 query distribution to be optimal task relevance. Initialize `pi_obj` uniformly over eligible objects, or separately disclose an additional object-selection prior trained from real verified complete repairs; the former is the primary faithful single-step-pretraining control.
- The Q2 scene may include hypothetical previous edits; preserve its actual input configuration. Q2 goal conditioning is unavailable or not directly tied to that query; mask the goal features during P0 rather than inventing labels.

\[
\mathcal L_{P0}=\mathbb E_{(s,o,d)\in Q2^+}[-\log\pi_\theta^{\mathrm{dst}}(d\mid s,o,\text{goal-masked})].
\]

Also test a **uniform legal-action proposal** P0 as the no-learned-prior ablation, with exactly matched physical MCTS budgets.

### 6.3 Policy distillation after MCTS

The published DISCO trains its policy from **every feasible expanded action edge**, not only the edges on successful complete paths. Preserve that design:

\[
\mathcal D_\pi^{(r)}=\{(h_{p(i)},o_i,d_i): e_i\text{ is a physically executed feasible tree edge in round }r\}.
\]

\[
\mathcal L_\pi^{(r)}
=\frac{1}{|\mathcal D_\pi|}\sum_{i\in\mathcal D_\pi}
\big[-\log\pi_\theta^{\mathrm{obj}}(o_i\mid h_{p(i)})
-\log\pi_\theta^{\mathrm{dst}}(d_i\mid h_{p(i)},o_i)\big].
\]

This **categorical NLL** replaces original continuous **3DFA flow-matching** on grasp/place poses; explicitly identify the change. Feasible but ultimately unsuccessful continuations are still valid policy targets, while long-horizon preference is learned by Q.

Do **not** endlessly mix original Q2 P0 data back into every distillation phase and still call it the paper's exact training protocol: official DISCO uses the sub-task demonstrations for **pretraining only**. An optional Q2 replay/regularization arm may be tested and clearly labelled.

Avoid allowing a few high-branching roots to dominate: monitor root/family frequency and compare unbiased edge-weighting to a root-balanced sampler as an explicitly labelled adaptation ablation. Do not silently change the primary edge objective.

---

## 7. Value network Q: what it means and exact distillation objective

### 7.1 Prediction semantics

`Q_phi(h_t, a)` is **continuation success under the explored search/policy process** after taking feasible action `a`, *not* `P(X=1,Y=1)` of a fixed entire plan, and not the standalone feasibility of the selected destination. This is why it differs meaningfully from Approach B's coupled F2/F3/F5 model.

The network consumes allowed scene/goal features and an `(object,destination)` token (or `STOP`) and outputs `[0,1]` after sigmoid. All actions in a value batch can share an encoded scene for efficiency. At the terminal `STOP` action, the value target is a **decided binary connector-and-Y terminal result** (including unsuccessful STOP negatives); at ordinary feasible relocation edges, the target is estimated over descendant visited leaves. Keep these terminal value targets identifiable and separately report their positive/negative counts; do not misclassify STOP as a physical relocation.

### 7.2 Per-edge tree value target

For each visited, **feasible** non-root child node `v_i`:

\[
y_i=\frac{n_{\mathrm{success\ leaves}}(v_i)}{n_{\mathrm{visited\ leaves}}(v_i)},
\qquad w_i=\log(1+n_{\mathrm{visited\ leaves}}(v_i)).
\]

\[
\mathcal L_Q(\phi)=\frac{\sum_i w_i\,\mathrm{BCE}(Q_\phi(h_{p(i)},a_i),y_i)}{\sum_i w_i}.
\]

Use **visited feasible descendant leaves** consistent with released `disco/data.py` `leaf_stats`; an unvisited unexpanded node is **not** a verified failure. Do not use the fraction of **all legal but untried** actions. Handle leaves with `UNRESOLVED` terminal status: exclude from decided success-denominator targets or carry a separate censored-evidence count; document the policy rather than assuming failure.

`Q` targets are biased by the exploration policy and partial search coverage. They are **not calibrated world-wide success probabilities**. Test ranking and calibration on independent observed outcomes.

### 7.3 Feasibility of proposed actions

Published DISCO evaluates proposed grasp/place actions through physics, and feasible edges become Q/policy training examples; model-generated candidates can still fail physical execution at test time. In our adaptation, keep that honest:

- Training MCTS: evaluate proposed actions with the **physical** transition interface; failed actions do not become feasible child nodes, but count against sample efficiency.
- Distilled policy: trained on feasible children, so it should favor executable actions, but has **no feasibility guarantee**.
- At inference: **do not call the physical teacher to screen all proposals**. If the chosen correction fails, count it. Static action legality masks remain allowed.
- An auxiliary failed-action feasibility head or direct supervised `Z` predictor is **not** part of primary DISCO-Grid; if explored, label it a new architecture ablation and apply identical oracle/query accounting.

---

## 8. Training-only progressive-widening MCTS, backups, and search reward

### 8.1 Tree node

Each node stores: parent pointer, ordered prefix, exact serialized physical full state, learner observation reference, incoming action, physical transition status, terminal-query status if tested, progress score, edge reward, visit count, backed-up Q, candidate sampling seeds, and source hashes. Do not store mutable global simulator references as snapshots.

### 8.2 MCTS selection, widening and expansion

Use released DISCO as reference:

\[
|\operatorname{children}(v)| < k\,[N(v)]^\alpha,
\quad \operatorname{UCB}(v')=Q(v')+C\sqrt{\frac{\log(N(v)+1)}{N(v')+1}}.
\]

**Paper/released reference:** `k=2.0`, `alpha=0.3`, `C=1.5`; candidate expansion batch `B=32`; 25 MCTS iterations per training environment per distillation round. Published global budgets `270,000` shelf and `27,000` stacking simulator calls are **not assumed appropriate for our slower teachers**.

Implementation rules:

1. Root counts as visited from initialization using a declared safe `N=0` convention; test widening behavior at N=0 and thereafter.
2. A widening event samples a new action batch using **current policy** and current action masks; dedup exact `(parent_state, object, destination)` pairs.
3. Execute each sampled action through the real adapter; only verified executed actions become feasible child nodes. Invalid/unresolved outcomes are logged as attempts; ensure repeated invalid samples cannot create an infinite loop.
4. Use Q as a **prior value** for new feasible children after Q exists; in round 0 initialize from a declared progress reward. Later visits update from actual simulated rollout returns.
5. Select children using UCB; continue for horizon ≤3 (or an accepted `STOP`) and backpropagate actual obtained return up the selected path.
6. Batch independent candidates if the simulator supports true independent state cloning. Otherwise use sequential physical rollouts with the **same logical MCTS**; record the throughput change; **never claim 32 parallel simulations simply because `B=32` was requested**.
7. Apply finite iteration, leaf, CPU, physical-query and wall-clock budgets. Administrative exhaustion is `UNRESOLVED` and must not be silently converted into failed physics.
8. Cache identical state/action queries only when robot, gripper and all physically relevant state plus teacher configuration match. Cache terminal Y by endpoint under exact endpoint/Y teacher key; not X by unordered assignment.

### 8.3 Reward: original task is not shelf packing

Published DISCO uses `r(s,a,s')=kappa(s')-kappa(s)` where task progress `kappa` is task-specific (e.g. packed-volume fraction). For *our* target feasibility task, defining `kappa` by **the physical Y teacher at every simulated prefix** could massively increase teacher calls and can reward/penalize intermediate states incorrectly because the q_ref terminal connector need not be feasible at an intermediate prefix.

Propose a **fixed, cheap geometric progress proxy** for **training-time search guidance only**. Set its value to **exactly 1 for a physically verified successful terminal**, and bound heuristic nonterminal values **strictly below 1** so the heuristic cannot rank a false geometric partial clearance as a true terminal solution, for example:

\[
\kappa_{\mathrm{geom}}(s)=1-\operatorname{clip}
\Bigl(\frac{h_{\mathrm{goal\ occupancy}}(s)+h_{\mathrm{target\ swept\ interference}}(s)}{H},0,1\Bigr).
\]

`h` measures currently occupied goal/declared target approach-interference under **a fixed, label-blind geometric recipe**; the displayed formula is a candidate *nonterminal proxy*, and the verified successful-terminal override to 1 is part of the actual implementation contract. No `GT blocker`, original K, finalized Y verdict or target-planner query is allowed to drive this proxy. Validate with hand-audited geometry-only examples and disclose failure cases (non-monotonic K3 prerequisites, side-grasp obstacle effects). Do not call a cheap 2D swept cell approximation a full 3D physical feasibility certificate.

**This proxy is a proposed adaptation, not a published DISCO reward.** Also run a preregistered **sparse terminal-only** progress control: `kappa=1` only at physically verified successful `STOP`, `0` otherwise. If geometric shaping harms success or leaks privileged information, retain sparse as primary. Report MCTS returns separately from actual task success and teacher calls.

Progress return for a completed simulated path: `R = sum_t (kappa(s_{t+1})-kappa(s_t))`, with an explicit terminal-success contribution if a terminal-only variant is used; do not mix incompatible reward scales without normalization. Because the original published DISCO uses telescoping progress returns, preserve that math where feasible and audit any terminal bonus as an adaptation.

### 8.4 STOP, terminal label and branch completeness

- At all depths 0–3, the tree can explore `STOP` as a terminal action. Its physical success requires **connector plus Y**, as in Section 3.
- An unsuccessful STOP branch does **not** imply its parent state cannot be repaired with further actions.
- An open prefix may have no immediate progress and still be the necessary first part of a K3 solution. Do not greedily terminate search solely because `kappa` fails to increase.
- At depth 3, no more corrective actions are legal; STOP or fail under horizon.
- Count successful leaves and visited unsuccessful leaves by **decided** physical terminal outcomes. Track unresolved leaves explicitly.
- Store successful full action histories, not just final object assignments. Different orders are distinct physical execution experiences; same endpoint can share Y.

---

## 9. Iterative distillation and training rounds

### 9.1 Round P0: no long-horizon value model

1. Build P0 destination policy from positive Q2 as in Section 6. Object-selection initially uniform over legal eligible objects; STOP exploration defined without privileged labels.
2. Validate sampled actions on limited TRAIN physical queries, reporting legal rate, verified execution rate, diversity, duplicates and per-domain cost. Do not use Q2 success as a substitute for actual stateful step success.
3. Save P0 checkpoint, train/validation curves, source hashes, seed, normalizers and real resource usage.

### 9.2 Search round 0

1. Start fresh training-root MCTS trees with P0 and **no learned Q**. New feasible children use fixed progress reward initialization.
2. Run a **small measured pilot first**, not the published 270k budget. Suggested initial audit cohort: 2D and 3D separately, 10–30 TRAIN roots across K1/K2/K3 plus a few K0/NONE; actual counts must follow available teacher cost.
3. Save exact feasible edges, attempted failures, visited paths, restored physical states, progress and terminal status. Require at least some decided terminal outcomes; **no forced success quota**.
4. Distill first policy `P1` from all feasible edges and first value `Q1` from decided visited-subtree statistics.

### 9.3 Search round 1, optional round 2

1. Start **fresh trees** using frozen `P1` and `Q1`; preserve all old trees and their query budgets.
2. Repeat MCTS under the same or preregistered budget and seeds for valid comparison; the value initializes UCB child prior, not an unverified physical label.
3. Distill `P2` and `Q2` (the name **Q2_value** must be distinguished from our pre-existing *Q2 isolated-placement dataset*; prefer `value_round2`).
4. Optional further round only if prior rounds show signal and resources permit; do not keep iterating until held-out test success looks good.
5. **Primary result** should include P0, P1, P2 and paired policy-only vs policy+Q for each; preserve matching seeds and candidate budgets.

### 9.4 Losses and scheduler

- **Policy:** masked categorical CE of actual feasible edges; log object head CE and destination head CE separately, and evaluate both. `STOP` supervision is a separate terminal-decision adaptation: include **decided positive and negative terminal attempts** in Q with binary targets, and include only verified-success STOP decisions as policy demonstrations (unless a separately disclosed policy-STOP objective is introduced). Do not accidentally discard negative STOP queries under the all-feasible-relocation-edge filter. Do not train STOP on legacy `K0/NONE` labels as network input.
- **Value:** weighted BCE with `y = n_success / n_decided_visited_leaves`, `w = log(1+n_decided_visited_leaves)` and normalization by total batch weights, checking code/source policy on unresolved leaves. Recommended default optimizer AdamW; choose LR, epochs, early-stop and model width via TRAIN/VALIDATION, **not test**.
- Maintain separate value/policy checkpoints and resource budgets. Do not pretrain on test candidate sequences, or let the model indirectly learn all validation outcomes through repeated tuning.
- For unstable/empty trees: preserve last valid checkpoint, report no learned improvement. Never manufacture positive edges or use model probabilities as outcomes.

---

## 10. Strictly specified inference protocols

### 10.1 Common model-only action-selection interface

At a learned observation `h_t`, produce a candidate set of legal `a=(object,dest)` (and STOP) from `pi`, then rank using `Q`:

\[
\hat a_t=\arg\max_{a\in C_\theta(h_t)} Q_\phi(h_t,a).
\]

Candidate count `B_test` (e.g. 8/16/32), unique proposals, duplicates, model calls, timing and random seed must be explicit. Compare **policy alone** versus **policy+Q**; candidate selection never queries the teacher. A `STOP` choice must be based on learned/scored terminal likelihood, not actual `Y` test evidence. Calibrate any STOP threshold on validation, report the sensitivity to false no-op/early-stop.

### 10.2 Open-loop DISCO-Grid (main matched-protocol baseline)

1. Observe the **original root** only.
2. Choose the first action from policy/value; apply **only a deterministic predicted object-position edit** to the observation (not physical simulation), update moved-object/destination masks and the remaining horizon.
3. Repeat up to K3 or learned STOP. This is autoregressive learned inference, not MCTS/physics-based test-time search.
4. The resulting complete sequence is **committed**. Independent teacher evaluates ordered X and endpoint Y once; failure remains failure. No retry, no second-highest score, no physical execution-time replan.
5. The open-loop generator may produce geometrically inconsistent states due to missing actual robot q/pose offsets; disclose that limitation and evaluate its impact. Never give it actual robot handoff data as a hidden privileged feature.
6. Report exact number of neural query passes and scoring operations; match latency and action-space budgets where feasible to Approach B's complete-sequence enumeration.

### 10.3 Closed-loop DISCO-Grid (original-style secondary baseline)

1. At each **actually observed** physical state, select one action with policy+Q, execute it, observe the result, then choose the next (up to 3 corrective actions).
2. Do not run simulated MCTS or extra candidate motion-planner screening during action selection.
3. An action failure must be counted under a predeclared handling policy; if a retry is allowed, disclose count and compare separately with no-retry deployment. Default fair evaluation should count a physically failed selected correction as failure.
4. `STOP` commits to terminal connector + target task and ends the episode. Do not use the true target Y query to decide whether to keep acting before STOP.
5. Report actual intermediate feedback access and physical planner/simulator calls. It is **not** directly comparable with our strictly open-loop Approach B without qualification.

### 10.4 K0, K1–K3, NONE reporting

- **K0:** test zero-relocation learned STOP accuracy and correctness against physically verified Y0; avoid mandatory relocation.
- **K1–K3:** count overall task success `Z=1` independently of legacy minimal-K; also report matching legacy-K success only when the dataset's qualified evaluation mask supports it.
- **NONE:** report abstention/no-repair predicted under restricted benchmark status; it is not proof of global impossibility. Report any novel verified repair found despite a legacy NONE label, with provenance.
- `STOP` failure on a nominal repairable root is a task failure, not an abstention success. Reject invalid action grammar at model level without wasting physics; log all masked/rejected proposals.

---

## 11. Scientific comparison protocol against Approach B and other baselines

### 11.1 Mandatory fairness dimensions

- **Same scene roots and family splits; same known goal; same geometry and side grasps; same max three corrective actions, fixed objects and target-last protocol; same physical X/Y verifier.**
- **Different learning inputs disclosed:** Approach B cVAE is trained on positive Q2 and complete-repair successes; DISCO P0 Q2 then MCTS-generated feasible actions and value targets; model widths/training budgets not necessarily identical.
- **Test-time feedback:** open-loop primary (single committed plan) vs DISCO closed-loop (separate). Do not blend results or assert feedback equality.
- **Teacher physics budgets:** training oracle counts are first-class. DISCO may need vastly more transitions than supervised Boltzmann; report queries, failures, parallelism, CPU/GPU-hours and disk.
- **Output/classification:** both return a full correction or no-op/abstain, and physical `Z` is computed identically. Use same terminal connector and target task.
- **Score budget:** count number of neural model evaluations and candidate actions, not simply compare `B=32` to `M=4` as if equivalent. Report measured wall-clock and physical calls separately.
- **Validation:** tune all thresholds and stopping criteria on validation only; historical Approach B test results exist, so an untouched new independent cohort is preferred for strong confirmatory paper claims.

### 11.2 Primary metrics

1. **Top-1/one-committed-sequence physical task success:** `X=1 and Y=1`; show K0/K1/K2/K3/NONE separately.
2. **Repair success on qualified roots** (only where certificate/mask is valid) versus general task success.
3. **Policy-only vs policy+Q** physically verified success, and closed-loop vs open-loop gaps.
4. **Training sample efficiency:** verified successful plans per 1,000 physical simulation transitions or per teacher CPU-hour, by round.
5. **Deployment compute:** model calls, unique action candidates, policy latency, Q latency, total latency, peak memory, real physical planner calls during execution, recovery opportunities.
6. **Task economy:** number of corrective relocations, total displacement, witnessed robot travel where original witness cost is available/physically decided; never impute nonexistent cost.
7. **Failure categories:** invalid predicted action, grasp/IK/planning/execution failure, terminal connector failure, Y goal failure, early STOP, horizon exhaustion, unresolved query, and NONE protocol differences.
8. **Variability:** at least 3 independently seeded training/eval runs where resources permit, paired root/family-cluster bootstrap CI, clear status if pilot underpowered.

### 11.3 Baseline/ablation matrix (prioritized)

| Arm | Purpose | Mandatory? |
|:--|:--|:--|
| Uniform legal sampling + no Q | Unlearned action prior and raw physical exploration | Yes |
| P0 policy only | Effect of single-step Q2 pretraining | Yes |
| P0 + MCTS (training-only), no distillation | Search itself as data generator, not final policy; report planning performance distinctly | Yes |
| P1 policy only | Benefit of policy distillation | Yes |
| P1 + Q1 | Learned value guidance | Yes |
| P2 policy only / P2 + Q2_value | Second distillation effect | If D3 passes |
| Fixed width/no progressive widening, same query budget | Is PW needed on small discrete grid? | Yes, if MCTS run is viable |
| Train policy only on successful-plan edges | Published policy-target ablation; tests loss of feasible-edge diversity | Yes if sufficient successful trees |
| Sparse terminal versus geometric shaping | Tests heuristic progress dependence | Yes as small controlled pilot |
| Open-loop versus closed-loop evaluation | Feedback fairness and published-style behavior | Yes if stateful adapter available |
| Full continuous grasp/place or ported point-cloud 3DFA | Materially different project; no requirement for this baseline | No |

Avoid attempting all ablations before proving D0 physical parity and D2 search feasibility. Never cite unrun ablations as completed.

---

## 12. Visualizations and scientific diagnostics

After each milestone, produce **actual** visuals generated from ground-truthed scenes/results:

- **D0/D1:** original scene and physical state transition (2D grid+arm; 3D xArm shelf view), exact side-grasp and target trajectory overlays, q-ref connector, replay parity success/failure.
- **P0:** legal-cell heatmap per queried object, learned destination distribution, random-vs-P0 sampled cells, physically observed one-step success, training curves.
- **MCTS:** trees with labelled branch decisions (`EXECUTED`, `FAILED`, `UNRESOLVED`), visits, UCB, learned Q prior and confirmed terminal success; seed-specific sample traces. Do not render hypothetical teleport as verified physics.
- **Distillation:** leaf-target histograms, number of leaves/weights, policy CE and Q weighted BCE curves, score calibration by round, found successful assignments/orders, value-branch comparison.
- **Evaluation:** per-root selected action sequence, actual replay trajectory or GIF where available, exact X/Y failure phase, success-vs-sim-budget curves, success-vs-test-latency, K1/K2/K3 breakdown, closed/open-loop comparisons.
- Every graphic carries domain, root ID, seed, teacher/commit version and whether it is **predicted**, **training-simulation verified**, or **independently test verified**.

Prefer a minimal script with both 2D matplotlib and existing 3D simulator rendering utilities. Do not generate attractive but invented examples as experimental evidence.

---

## 13. Minimal implementation structure and resource isolation

Suggested new isolated directory in the existing project (adapt to actual repo; inspect first):

```
baselines/disco_grid/
  README.md                # scope, exact paper attribution, commands, limitations
  config.yaml              # all domain/train/MCTS/evaluation budgets
  data.py                  # snapshot/Q2 loading, split checks, schema/dedup
  env.py                   # thin domain-dispatched physical adapter API
  policy.py                # compact categorical policy + shared observations
  mcts.py                  # search tree, widening, UCB, backup, disk save
  distill.py               # extract feasible edges / visited leaf stats, train
  evaluate.py              # open-loop / closed-loop, oracle eval, metrics
  viz.py                   # 2D/3D & tree visualizations
  tests/                   # contract, state, parity, math, leakage, cache tests
  reports/                 # staged results, figures, source audits
```

Use separate helper files only where a large module truly needs split responsibilities, e.g. `env_2d.py` and `env_3d.py` if physics complexity requires it. Target clear, concise modules, often ≲250–300 logical lines where practical; **do not force a physics adapter into an unsafe monolithic file merely to satisfy a line limit**.

- Keep `approach_b_final/` unchanged except minimal documented read-only integration, if absolutely needed.
- Use an independent branch/worktree such as `naren/disco-grid-baseline`; inspect whether it already exists. Never reset other worktrees or overwrite teammate files.
- Store large simulator states, meshes, trajectories, tree dumps and checkpoints in separately versioned data/output paths outside tracked source, with small committed manifests and hashes.
- Pin Python, Torch, CUDA, simulation, teacher and DISCO versions; avoid installing DISCO's global dependencies into shared Approach B environments unless truly required. Most of the original ManiSkill/curobo stack is unnecessary for the discrete adaptation.
- Run reproducible train and eval CLI jobs, idempotent checkpoint resumes, deterministic seeds, optional CPU fallback for unit tests. Implement fixed source/hash checks.
- Every major milestone: tests → concise report → focused commit → push to the dedicated branch → verify remote SHA. Never fake executed work or claim a push without confirmation.

---

## 14. Stage-gated execution roadmap

### D0 — Context recovery, frozen task specification and source audit

**Deliverables:** inspected source commits, root/split/teacher manifest audit, exact 2D/3D side-grasp/robot configuration table, GPU/CPU inventory, independent worktree, `reports/D0_SOURCE_AUDIT.md`, preflight tests.

**Pass:** no unresolved confusion about which teacher, q_ref, action grammar, source provenance or dataset is authoritative; physical source packages verified present.

### D1 — Statefully executable 2D/3D robot adapter

**Implement:** `reset`, `restore`, `transition`, `terminal_query`, `observe`, legal actions, state hashes/cache. **First 2D, then 3D.** Do not replace q carryover with hypothetical `Edit`; no interim connector.

**Tests:** known positive and negative orders, K0, Y-only change, fixed/collision legality, variable episode depth, duplicate states, 3D pose offsets, q_ref terminal connector, per-root geometry. Audit decidable parity under exact teacher budgets.

**Pass:** all **decided** matched fixture cases agree or every disagreement is resolved through protocol fix; explicit unresolved counts; no false physical successes by teleport. If blocked, stop at D1.

### D2 — DISCO policy P0, source-compatible Q2 initialization

**Implement:** structured scene/goal observation, legal object + destination categorical policy, Q2 destination pretraining with goal masking, uniform object prior, policy-only inference. Train separately in 2D/3D.

**Tests:** input leakage, masks, normalizers, positive Q2 loading, split hygiene, sample uniqueness/entropy, legal sampling, no use of final success labels to pretrain.

**Pass:** nontrivial held-out placement reproduction and physically measured valid proposal yield, with comparable uniform baseline. No claim of whole-task improvement yet.

### D3 — Functional physically grounded MCTS

**Implement:** node snapshots, true physical expansion, progressive widening, UCB, progress/sparse reward, STOP, backups, candidate budget, resilient resume. Test against a toy deterministic transition model first, then real physical adapter.

**Tests:** PW threshold and visits, UCB tie breaks, root at N0, maximum depth, duplicate action suppression, exact state restoration, no cross-branch state leakage, decided vs unresolved leaves, correct terminal X+Y, true call budget counts.

**Pilot:** small fixed TRAIN root set stratified by K, no optimistic results. Check successful plan discoveries, failed proposal rates, wall time and disk usage.

**Pass:** some physically verified complete plans discovered on known solvable training roots and correct serialized trees; if zero, diagnose P0 proposals/progress/teacher before scaling.

### D4 — Exact tree-to-policy/value distillation

**Implement:** all executed feasible edges → policy CE; visited decided descendant leaves → Q target, log(1+n) weighted BCE; STOP terminal decision semantics; dataset and loss auditing.

**Tests:** hand-computable toy tree target fractions and BCE weights, no label-missing→failure conversion, dedup/ordering correct, lineage split checks, trained checkpoint reload parity.

**Pass:** numeric target audit and stable policy/Q training; validation ranking and action sampling measured without test leakage.

### D5 — Iterative self-improvement rounds

**Implement:** round 0 P0→P1/Q1 and round 1 P1/Q1→P2/Q2_value, fresh search trees, comparable budgets, frozen configs, old artifacts immutable.

**Pass:** run-resume reliable, model comparisons and budget accounting correct. Improvement is **measured**, not assumed; null/negative results preserve implementation integrity.

### D6 — Primary matched open-loop deployment

**Implement:** no simulator/teacher in action generation, conditional object/destination/STOP, predicted static scene edits, commit at most one K≤3 correction, independent X/Y once.

**Pass:** zero physical calls inside model ranking/generation, single committed corrective plan per root, honest replay success/failure, K0 and NONE handling. All action grammar and cost accounting verified.

### D7 — Published-style closed-loop deployment and ablations

**Implement:** observed-state rollouts, frozen policy/value, no test-time MCTS, no hidden physical candidate pre-screening; compare P0/P1/P2 with and without Q, PW ablation, success-only policy edges, sparse versus shaped training rewards.

**Pass:** clear separation of feedback budgets and failure handling; fair query counts and paired outcome evaluation.

### D8 — Final 2D/3D evaluation and paper-ready artifacts

**Implement:** reproducible metrics/test runs, variance, physically verified scenes, visualizations, failure taxonomy, runtime and training-simulation cost report; release/checkpoint hashes and full deviations ledger.

**Pass:** every displayed quantitative claim reconstructible from a frozen manifest of scene/seed/prediction/teacher-result rows; all unresolved/blocked results marked; manuscript baseline name is **DISCO-Grid (adapted)**.

---

## 15. Tests that must never be skipped

- Action grammar: target never moved, fixed obstacles frozen, no source swap/reused originally occupied cells, no repeated moved objects, at most K3, no goal-cell placement.
- Robot: **same active side grasp set**, IK/collision/motion attempt limits, executed trajectory, gripper release, no intermediate q_ref/home reset, terminal connector only on STOP, 3D executed pose offsets and real MuJoCo state.
- X/Y: same endpoint same Y, different permutations may have different X; X from original root, Y from terminal q_ref; `Z=X∧Y`, unknown ≠ 0.
- MCTS: N=0 behavior, widening, UCB, backups, rewards, visited leaves, independent states, STOP branch semantics, max horizon and budget enforcement.
- Data/model: no GT K/blocker/correction as features, no validation/test training, Q2 queried-object label not misused as object-relevance oracle, per-root family lineage.
- Inference: no hidden physical calls before plan commitment, no second attempted plan after physical failure in open-loop, Q prefilter doesn't use final teacher, count all neural calls.
- Reproducibility: deterministic fixture seeds, source hashes, resume integrity, no overwriting existing results/branches.

---

## 16. Decision gates and failure modes

| Symptom | Interpretation | Required response |
|:--|:--|:--|
| D1 cannot carry exact robot state or connector | Physical training transitions not faithful | **STOP**. Fix simulator API; cannot report physical DISCO success. |
| P0 produces many invalid first actions | Q2 supervision/domain shift or policy masking issue | Inspect true Q2 query contexts and legal mask; report uniform comparison. |
| MCTS gets stuck at K2/K3 with no progress | Sparse/flat reward or bad proposal support | Test sparse-vs-geometry reward, wider proposal support under equal query budget; do not inject GT blockers. |
| Search finds success but Q value target is always 0 | Tree extraction, terminal leaf or success criterion bug | Validate hand-computed leaf stats and STOP/connector results. |
| Good Q on TRAIN, bad held-out roots | Overfitting/biased search targets | Check family leakage, scene diversity, Q calibration and target weighting; no test tuning. |
| Open-loop fails but closed-loop succeeds | Benefit of actual intermediate feedback | Report separately, not as a direct victory over one-shot Approach B. |
| K0 incorrectly moves objects | STOP proposal/value defect | Explicit K0 training terminal examples, valid thresholds; no GT K input. |
| NONE scene gets physically verified repair | Legacy search was incomplete | Flag newly verified repair; do not erase original benchmark provenance. |
| Teacher timeout or cap | Undecided outcome | Mark UNRESOLVED and charge time/query; not X=0 or terminal failure. |
| Too much GPU/CPU cost | Resource-limited baseline | Report pilot, budget curve and honest blocked scope; avoid making up full comparisons. |

---

## 17. Required records from each milestone

Each report `reports/D*_*.md` must state:

1. Hypothesis, source configuration, domain, root counts/splits and stage gate.
2. Exact code/source/teacher commits, configuration hashes, resource inventory and deterministic seeds.
3. What was implemented; what was reused; deliberate differences from official DISCO and Approach B.
4. All requested and actual physical-label/simulation calls, planner failures/unresolved statuses, runtime, GPU-hours, memory/disk.
5. Numeric metrics with denominators and uncertainty; no stale/archive test data presented as newly obtained.
6. Visuals with root/seed/ground-truth status and a failure case.
7. Tests/parity outcomes, known blockers, decisions to continue or stop.
8. Git commit, push status and verified remote commit SHA.

Final `reports/DISCO_GRID_FINAL_REPORT.md` requires a direct **fidelity/deviation table** (paper vs code vs DISCO-Grid), a **cost and fairness table**, K0/K1/K2/K3/NONE metrics, open- and closed-loop separately, primary ablations, limitations (finite K3, discrete destination choices, known state, no push/swap/new grasp), and complete run manifests.

---

## 18. Sources and attribution

1. Kallol Saha et al., **Long-Horizon Multi-Object Rearrangement via Distilled Tree Search over Continuous Actions**, CoRL 2026. <https://arxiv.org/abs/2610.25785>. §§3–4.3, Appendices B/F specify MCTS progressive widening, policy/value distillation, feasible-edge training and visited-success-leaf weighted BCE.
2. Official code: <https://github.com/kallol-saha/DISCO>. Inspect current commit before implementation; `run_disco.py`, `config/{mcts,run_disco}.yaml`, `disco/{search,data,policy,tasks}.py` or directories. Released defaults are **reference values only**.
3. Project task contracts: <https://github.com/Narendhiranv04/latent-causal-tamp/tree/naren/approach-b-final/approach_b_final> and the supplied **Approach B V3 `plan.md`**. Physical X/Y semantics and side-grasp limits come from the verified project's **finalized** teachers/configs, not from an arbitrary paper, historical guide or adapted standalone simulator.

**End-state definition:** An honestly labelled **DISCO-Grid** comparator that learns policy/value by stateful physically grounded MCTS distillation, evaluates one open-loop corrective sequence under identical X/Y physical checks, and separately reports the published-style closed-loop deployment. No components of Approach B V3's learned cVAE/Boltzmann are used to give DISCO privileged guidance, and no differences in feedback or physics assumptions are hidden.
