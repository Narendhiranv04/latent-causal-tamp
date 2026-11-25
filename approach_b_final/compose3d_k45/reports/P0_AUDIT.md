# P0: source audit and prerequisites (3D K4/K5 composition pilot)

**Gate: PASS for the learner side and the physical contract, with two documented deviations: K5 needs a new adapter, and minimum K is not certifiable.**

## Provenance

- **Branch:** `naren/rss27-3d-k45-composition`, created from `87ebf65d245dd9368397bf3577c9ff164cff619b` (equal to origin). The branch did not exist before, and nothing was merged.
- **Contracts:** `plan.md` (sha256 `1ef6df7f…`) and `starting_prompt.md` (`99c29503…`) are byte copies of the attached contract.
- **Referenced commits:**
  - `c892af3d95` (kgt3 P4; 2D `recursive_kgt3` planner) and `7fcfe6992d` (P5A order audit) exist and were read as motivation only.
  - The 2D retarget indices are **not** copied; 3D slots are derived from `len(q_ref)` in `scene.ctx_slots`.
- **Fig. 3(a):** `~/Downloads/RSS_we_ball-15.pdf` is present. B4 implements the bounded version defined in the plan.
- **Owner authorization, 2026-11-25:**
  - The proposed generation, evaluation, CPU, GPU, worker and storage caps.
  - A new bounded, instrumented K5 generator adapter.

## Frozen 3D bundle (`~/abf_v34/approach_b_bundle`, hash-checked by `benchmark.load_bundle(…, '3d')`)

| Item | Value |
|---|---|
| Sampler | S1 TaskCVAE `scratch_all` s0 (3D, epoch 34), `propose_many` (task-conditioned). Top-6 per object with a fresh CUDA generator seeded 0; D4 is its prefix |
| Scorer | coupled X/Y **arm D** seed 0 (3D, epoch 57) |
| Rule | NOOP gate 0.5, η 0.3, α = β = γ = 0, M 4, n_z 64, K_max 3 |

- **The 3D configuration is identical to 2D.** The bundle carries one shared configuration and no 3D-specific value differs.
- **TRAIN support:** the 3D TRAIN snapshot (`abf_v32_fb0eef4f5ff433ee`, 1,766 roots) has 1–13 objects per root, and its X labels have lengths 1–3 only (1,274 / 3,477 / 6,139). Sequences of length 4–5 are therefore out of distribution, as declared.

**B0 parity on 5 exposed DEV roots** (`P0_B0_PARITY_DEV.json`; VAL rows built with `benchmark.public` from the snapshot):
- The roots cover one of each archived decision kind: REPAIR-3, REPAIR-2, REPAIR-1, NOOP and ABSTAIN.
- 5/5 decisions and moves are identical to the sealed V3.4 parity predictions (`~/abf_v34/parity/pred_val_3d_gpu.jsonl`).
- Scores agree within ≤ 1.0e-7, and the top-4 proposals are equal.
- No protected TEST row was opened.

## View, grammar and retargeting (`contracts.view3d`, `search.Root`, `placement.task_features`)

- **View:** 6×6 grid, cell id `r*6+c`. `attrs = [is_box, is_cylinder, size, height, is_target]`.
  - `ctx = sin(q_ref)·7 | cos(q_ref)·7 | goal xy | target size, height, is_box` (19 values).
  - In 3D no object is fixed, so movable means every object except the target.
- **Retargeting** rewrites `tid`, `goal`, `goal_cell`, the is_target column for **every** object, and ctx[14:16] / ctx[16:19]. Height is never edited.
  - `task_features` reads only `goal_cell`, `tid`, `cells` and `ctx`. The retargeted features were checked in a test: goal and target one-hots and the ctx copy.
- **No vacated-cell reuse:** rebased rows carry `legal_cells` = all cells minus the original occupancy, the original goal and reserved destinations. The sampler's own mask (`Root.legal_dests`) therefore enforces the rule on every hypothetical scene.

## Physical teacher (deployed on gvlab2: `approachb_final_gen/final3d_v4`)

Sources were read before any run, with copies hashed in `~/k45_private/audit_src`:

| File | sha256 (prefix) |
|---|---|
| `fin3d.py` | `29eb0b29` |
| `bwlphys.py` | `259652f1` |
| `bd_3dt.py` | `62dc853c` |
| `bd_3dt_plus.py` | `c406c3cb` |
| `bd_core.py` | `f34b881c` |

**Runtime:** MuJoCo 3.16.0, numpy 2.2.6, Python 3.13 (`env3d`).

**X (`fin3d.run_x`):**
- Fresh environment, settled at the initial cells **and q_ready**.
- Every move is `bd_3dt.query` from the **current** arm state: the scene's side-grasp poses in order, first feasible wins, RRT-Connect with a 5,000-iteration ceiling and no wall clock, seed 0. It is executed by `run_plan` in MuJoCo.
- Checks per move: the mover ends in its cell, |z_err| ≤ 1 cm, and no other object changed cell. **The arm state is carried between moves (no return to ready).**
- Then `bwlphys.connector` (CONNECTOR_TO_QREADY_V1): `plan_free_move` to q_ready, **executed**; |dq| ≤ 0.02, nothing pushed > 4 mm, cells kept, nothing held, no robot-object contact.

**Y (`fin3d.run_y`):** endpoint cells settled at q_ready, then the target query and execution with the same checks.

**Other contract facts:**
- **Length cap:** `bd_core.check_sequence` allows ≤ 7 actions (≤ 6 relocations), so K5 is within the teacher contract.
- **Administrative wall:** 3,600 s per sequence (UNRESOLVED_ADMIN means missing, never a label).
- **Statuses:** a negative is CERTIFIED (every grasp fails a deterministic geometric check), NO_PLAN_FOUND, TIMEOUT or OTHER_FAILURE. A 0 is never proof of physical impossibility.

**Witnesses and replay:**
- Move plans and connector paths are stored content-addressed (`bd_core.Store`).
- `bwlphys.move` and `bwlphys.connector(path=…)` re-execute stored witnesses.

**New adapter (`evaluate_k45.run_xb`):**
- It is `fin3d.run_x` line for line, plus (i) grasp-id logging and (ii) the connector at every declared group boundary.
- Continuous mode = boundary only at the end. Chunked mode = after every group.
- Replay refuses any stored witness whose first configuration differs from the current arm state by > 0.02 rad (DISCONNECTED; never teleported).

## Generator (`bd_3dt_plus` SHELF66V3 route construction, `bd_3dt.teach`)

- **K limits:** `FACTORS["K"] = [0, 1, 2, 3, 4]` and `MAX_NECESSARY = 4`. The verified-K search is a BFS over relocation sets of a ≤ 8-object pool to **fixed** parking cells, stopping at 4.
- **K5:** not supported by the existing generator. Handled by the new adapter `generate.py` (authorized): existing route construction with K_b ∈ {2, 3} plus `n_chain` enabling obstacles.
- **K4 by direct route construction:** historically rare. The existing raw set has 10 K4 roots out of 3,031, the runner notes say K4 "stays out of reach", and K ≥ 4 exact covers need ≤ 4 feasible azimuths.
- **Minimum K is not certifiable soundly.**
  - The route construction's "every feasible grasp cut by ≥ K blockers" uses single-blocker RRT probes.
  - The generator's BFS is restricted to a fixed parking cell per object and a pool cap.
  - Neither is a sound certificate over the full grammar.
  - **Every admitted root is therefore labelled `WITNESS_LEN_k_MIN_UNKNOWN`.** A probe of every (k−1)-subset endpoint of the witness is run and reported (`SHORTER_WITNESSED_LE_{k-1}` excludes a root).
- **Instrumentation:** every `XArm7TableEnv.plan_pick_place` and `plan_free_move` call is counted by a process-local wrapper (behaviour unchanged). Construction stages keep the generator's own wall caps (route 30 min / 45 min for K_b = 3), and the chain stage is capped at 15 min.
  - A **job** is one complete-plan X run or one endpoint Y run.
  - CPU is measured per layout with `process_time`. The dispatcher counts running layouts at wall time, an upper bound on CPU, and stops dispatch with 0.6 CPU-h of headroom per running layout.

## Deviations from the plan (declared before any fresh-root inference)

1. **Construction styles.** Route blockers are independent by construction, so the plan's 4 direct / 3 enabling / 3 mixed quota cannot come from the existing generator.
   - Every root is *route-direct blockers + enabling chain obstacles*.
   - K4: 5 × (3 direct + 1 enabling), 5 × (2 + 2). K5: 5 × (3 + 2), 5 × (2 + 3, one depth-2 chain where needed).
   - The "direct-heavy" and "enabling-heavy" strata replace the plan's three styles. There are no pure-direct K4/K5 roots.
2. **Minimum K:** WITNESS_LEN only (see above).
3. **The 3D view is a geometric block drawing** from real cells, sizes and heights. Rendering is disabled in the teacher env (`MUJOCO_GL=disable`), so there are no simulator screenshots.
