# D0 — Source, Environment, Dataset, and Physical Assumption Audit

**Milestone:** D0 (`DISCO_plan.md` Sections 1.2 & 14)  
**Baseline Designation:** **DISCO-Grid (adapted)** — discrete object–destination adaptation of Saha et al. (CoRL 2026, arXiv:2610.25785)  
**Date:** 16 November 2026  
**Status:** **PASSED**

---

## 1. Repository, Branch, and Upstream Provenance

| Artifact | Path / URL | Verified Commit / SHA256 |
|:--|:--|:--|
| Host repository | `https://github.com/Narendhiranv04/latent-causal-tamp.git` | Inspected `naren/approach-b-final` (`05998d0f12`) & `naren/approach-b-v3` (`ede29034b2`) |
| Isolated DISCO-Grid branch | `naren/disco-grid-baseline` | Branched from `ede29034b2` in `/home/naren/Desktop/boltzmann_lfd/.claude/worktrees/disco-grid-baseline` |
| Official DISCO repository | `https://github.com/kallol-saha/DISCO.git` | `c62b32e5f6e40444459742525a86ffef620951aa` (cloned to `/scratch/nav/disco_grid/../disco_official_ref` on `gvlab`) |
| DISCO implementation plan | `baselines/disco_grid/docs/DISCO_plan.md` | `sha256:e62006add13b64318019d758d64dea12cd0168c87b9a13d1c03bd2ef801ce243` |
| Approach B V3 plan | `approach_b_final/docs/PLAN_V3_2026-11-15.md` | `sha256:276b592bab3b913b0bc37d157b731880cfcca0abe8352b2f254d9530ef5a8e33` |

---

## 2. Compute Hosts and Resource Isolation Audit

| Host | Hardware | Active Workload | Assigned Role |
|:--|:--|:--|:--|
| `gvlab` (`gvlab.iiit.ac.in`) | Intel Xeon Gold 5317 (24 logical CPUs @ 3.00 GHz), **2× NVIDIA RTX 4090 (24 GB VRAM each)**, Driver `560.35.05`, CUDA `12.6` | **0 active user processes (0% GPU/CPU)** | **Primary & exclusive DISCO-Grid compute host** (training, MCTS simulation, physical verification) |
| `gvlab2.iiit.ac.in` (`cstar`) | AMD Ryzen Threadripper 7960X (48 logical CPUs), 1× NVIDIA RTX 5090 (32 GB) | Running 36-worker `learned_reap` job (`build_lib66.py --workers 36`) | **Do not touch** (left completely undisturbed per shared-server non-interference rule) |
| Local laptop | Linux workstation | Antigravity IDE, SSH, Git | **Editing & Git only** (no training, simulation, or large-scale processing) |

**Isolated runtime environment on `gvlab`:**
- Workspace directory: `/scratch/nav/disco_grid/{code,runs,trees,data,caches}`
- Python environment: `/scratch/nav/disco_grid/venv/bin/python` (`Python 3.10.12`, `torch 2.5.1+cu124`, `mujoco 3.16.0`, `numpy 2.2.6`, `matplotlib 3.10.9`, `pytest 9.2.0`, `pyyaml 6.0.3`).

---

## 3. Physical Task, Side-Grasp, and Teacher Specification

### 3.1 2D Planar 3R Domain (`BXY_X_TEACHER_V1` / `BXY_Y_TEACHER_V1`)

| Parameter | Authoritative Value | Source |
|:--|:--|:--|
| Robot arm | Fixed-base planar 3R arm; base `[-0.14, 0.32]` m; links `[0.42, 0.34, 0.20]` m; link widths `[0.018, 0.016, 0.014]` m; joint limits `[-\pi, \pi]` rad; `q_home = [\pi/2, \pi/2, \pi/2]` | `config.toml`, `geometry.py` |
| Reference configuration `q_ref` | Per-root `rec["q0"]` (sampled from 4 collision-free strata `S0..S3` in `p6_scenes.STRATA`) | `bxy_teacher.py`, `contracts.py` |
| Support lattice | 8×8 grid (`rows=8, cols=8`), `pitch_m = 0.08`, 0-based cell $c = 8r + k$, centre $(0.08(k+0.5), 0.08(r+0.5))$ m | `config.toml`, `contracts.py` |
| Gripper geometry | `two_finger_side`; palm `0.028 × 0.034` m; fingers `0.050 × 0.007` m; `open_gap = 0.070` m; `closed_gap = 0.046` m; `grasp_center_x = 0.032` m; `contact_tol = 0.001` m; `release_tol = 0.002` m | `config.toml` |
| Side-grasp candidate family | **48 grasps** per query: `approach_dirs = 24` ($\phi_k = 2\pi k / 24$, every $15^\circ$) $\times$ 2 elbow branches $b \in \{+1, -1\}$; straight `approach_dist = 0.06` m and `retreat_dist = 0.06` m (`line_step = 0.005` m, `max_ik_jump = 0.1` rad) | `skill.py` (`directions`, `screen_pick`, `screen_place`) |
| Collision & certification | Safety margin $\delta = 0.005$ m, $\epsilon = 0.0002$ m, `certify_max_evals = 4000`; per-root `geometry_impl` (`fastgeom1` vs `original`) preserved | `teacher2d.py`, `config.toml` |
| Planner & per-query budget | `DetPhysics(profile="fast")`: RRT-Connect `max_nodes = 1500`, `max_plan_failures = 2`, `transit_nodes = 500`, `max_wall_seconds = 1e9`; `QB = {"motion_checks": 150, "online_moves": 8, "goal_plans": 3, "transit_plans": 6}` | `p16_motion.py`, `bd_2d.py` |
| Terminal connector & X/Y | Relocations chain carried `(cells, q)` without intermediate `q_ref` reset. On `STOP`, free-gripper connector `q -> q_ref` is planned via `DetPhysics._transit` in `("start", False)` world and verified with `replay_x`. `Y` runs `bd_2d.t_goal` from `q_ref` in the canonical endpoint scene + `replay_y`. | `bxy_teacher.py` |
| Protocol & teacher hashes | Protocol: `PLANAR3R_SIDEGRASP_V1:sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858`<br>Config hash: `90d3eb68e8a42108`<br>Teacher hash: `sha256:4930754123e6905619b5e34ae450c8e78599643460c03e6cd0ce11393ea0a4fe` | Verified on `gvlab` |

### 3.2 3D xArm7 Confined Shelf Domain (`fin3d` / `BD3DS66_TEACHER_V2`)

| Parameter | Authoritative Value | Source |
|:--|:--|:--|
| Robot & simulator | xArm7 (7-DoF arm + 6-joint gripper) in MuJoCo `3.16.0` (`timestep = 0.002` s, `implicitfast`) | `shelf_scene.py`, `bwlphys.py` |
| Reference configuration `q_ref` | `q_ready = [-1.345029, -0.632166, 0.221281, 2.024222, 0.267756, 2.629261, 2.210774]` rad (`TOL_Q = 0.02` rad) | `bwlphys.py`, `contracts.py` |
| Shelf geometry (`SHELF66`) | 6×6 confined shelf (`rows=6, cols=6`), `pitch = 0.075` m, `x0 = 0.42` m, floor `table_z = 0.55` m, `clear_height = 0.60` m, open sides (`side_walls = False`), `NO_OVERPASS = True` (`COLUMN_H = 1.2` m), `ARM_CEILING = True` (`ceiling_margin = 0.10` m) | `bd_shelf.py`, `shelf_scene.py` |
| Side-grasp candidate family | **32 level side grasps** per object: 16 azimuths (`0.0, 22.5, ..., 337.5` deg) $\times$ 1 tilt (`90.0` deg level) $\times$ 2 grip heights (`GRASP_AT = "middle,top"`, pad at $z + h/2$ then $z + \max(0.015, h - 0.012)$ m); up to **4 IK branches** per grasp; fingers pre-shaped (`open_width = width + 0.012` m) in all checks | `shelf_scene.py`, `bd_shelf.py` |
| Collision & motion margins | `STATIC_MARGIN = 0.003` m, `OBJECT_MARGIN = 0.005` m, `FREE_MOVE_MARGIN = 0.02` m, `CARRY_LIFT = 0.025` m, `CARRY_GAP = 0.006` m, `FOOTPRINT_GAP = 0.008` m, `PRE_DIST = 0.13` m, `RETREAT_DIST = 0.05` m, `TOL_PUSH = 0.004` m | `shelf_scene.py`, `bwlphys.py` |
| Planner & execution | `RRTConnect` with `max_iters = 5000`, `max_time = 1e9`, `seed = 0`; `RETURN_TO_READY = False` (arm chains directly from retreat to next pick). Each move executes via `e.run_plan(p)` and checks destination cell, $|z_{\text{err}}| \le 0.01$ m, and no other object changed cell. | `bd_3dt.py`, `fin3d.py` |
| Terminal connector & X/Y | On `STOP`, `bwlphys.connector` (`CONNECTOR_TO_QREADY_V1`) plans `e.plan_free_move(q_now, q_ready, seed=0)`, executes, opens gripper, waits 200 steps, and checks $\|q - q_{\text{ready}}\|_\infty \le 0.02$ rad, no object pushed $> 4$ mm, all cells valid, nothing held, 0 robot-object contacts. `Y` (`BD3DS66_Y_PLAN_V1`, `fin3d.run_y`) settles the canonical endpoint scene at `q_ready` and plans/executes `t0 -> goal`. | `fin3d.py`, `bwlphys.py` |
| Protocol & teacher hashes | Protocol: `XARM7_SHELF66_LEVELGRASP_V1:cd7f78f44022`<br>Config hash: `8d521b1f6d23db23` | Verified on `gvlab` |

---

## 4. Verified Dataset Snapshots and Split Hygiene

All four source packages (`FINAL_READINESS_GATE`, `FINAL_3D_DATASET_V4`, `K3_HARD_ORDER_V1`, `FINAL_DATASET_SELECTION_MANIFESTS`) and compiled snapshots on `/scratch/nav/approachb_final` passed SHA256 verification with zero mismatches:

| Dataset Stream | Snapshot ID / Path | 2D Counts | 3D Counts | Split Hygiene |
|:--|:--|:--|:--|:--|
| Base X/Y Snapshot | `abf_9de85710c2a7103f` | 5,000 roots (3,500 train / 751 val / 749 test)<br>12,400 X rows, 9,700 Y endpoints | 2,500 roots (1,766 train / 364 val / 370 test)<br>7,089 X rows, 5,305 Y endpoints | 0 root, family, or layout split conflicts |
| V2 On-Policy Snapshot | `abf_v2_7d146b53e4b92fe4` | +7,594 TRAIN X, +9,661 TRAIN Y (val/test byte-identical to base) | +2,126 TRAIN X, +2,493 TRAIN Y (val/test byte-identical to base) | 0 root, family, or layout split conflicts |
| Q2 Isolated Placements | `/scratch/nav/approachb_final/data/q2_{2d,3d}` | 238,160 queries across 42,285 contexts<br>Train: 162,484 (119,377 `label=1` across 3,120 roots)<br>Val: 37,800 (28,369 `label=1` across 751 roots)<br>Test: 37,876 (28,292 `label=1` across 749 roots) | 55,036 queries across 9,729 contexts<br>Train: 39,152 (29,175 `label=1` across 1,036 roots)<br>Val: 8,088 (6,025 `label=1` across 225 roots)<br>Test: 7,796 (5,622 `label=1` across 204 roots) | Scalers fit on TRAIN only; 0 roots in two splits; 0 split disagreements with X/Y snapshot |

---

## 5. Official DISCO Code vs. Paper vs. DISCO-Grid Audit

Inspection of `https://github.com/kallol-saha/DISCO` (`c62b32e5f6e40444459742525a86ffef620951aa`) verified the exact equations and implementation details:

1. **Progressive Widening (`disco/search/mcts.py:797`, `config/mcts.yaml:341-344`):**
   - Condition: `len(node.children) < self.k * (node.visit_count ** self.alpha)` with defaults `k = 2.0`, `alpha = 0.3`, `C = 1.5`.
   - Note on `N=0`: In `mcts.py:879-894`, `_increment_visit(current_node)` is called *before* `widening_condition(current_node)`, so on the very first visit to the root (or any newly entered child), `node.visit_count == 1`, giving $k \cdot 1^\alpha = 2.0 > 0$, which immediately triggers expansion!
2. **UCB Selection (`disco/search/mcts.py:479-484`):**
   - `ucb = self.Q + self.C * np.sqrt(np.log(n_parent + 1) / (n_edge + 1))`. Failed children return `-inf` and are never selected.
3. **Child Q Initialization and Backup (`disco/search/mcts.py:1106-1121, 1201-1228`):**
   - In Round 0 (no $Q_\phi$), new feasible children initialize `child.Q = float(reward)`. When $Q_\phi$ is provided, `child.Q = float(q_init)` from $Q_\phi(s_{\text{parent}}, a)$.
   - On backup from `leaf`, path return is $R = \sum_{\text{edge} \in \text{root}\to\text{leaf}} r_{\text{edge}}$, and each node on the path updates `node.Q = node.Q + (R - node.Q) / max(node.visit_count, 1)`.
4. **Distillation Dataset Extraction (`disco/data.py:1876-1954`):**
   - **Policy rows:** Every non-failed child `c` of every node (`kids = [c for c in parent.children if not c.is_failed and c.prev_action is not None]`).
   - **Value rows:** Every visited non-failed child (`c.visit_count > 0`), with target $y_i = n_{\text{succ}}(c) / n_{\text{leaf}}(c)$ computed recursively over visited non-failed descendant leaves (`leaf_stats`).
5. **Value Network Loss (`disco/flowmatch/modeling/policy/value_network.py:130-139`):**
   - `per_sample = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")`
   - `weights = torch.log1p(n_leaves)`
   - `loss = (weights * per_sample).sum() / weights.sum().clamp_min(1e-6)`

---

## 6. Preflight Test Suite Results

Executed on `gvlab` via `/scratch/nav/disco_grid/venv/bin/python -m pytest -v baselines/disco_grid/tests/test_d0_audit.py`:
- `test_snapshots_and_locks`: **PASSED**
- `test_split_hygiene_and_root_counts`: **PASSED**
- `test_raw_root_files_exist_and_match_sha`: **PASSED**
- `test_static_action_grammar`: **PASSED**
- `test_q2_datasets_and_zero_split_leakage`: **PASSED**

**Gate Decision:** **PASS D0** — Proceed immediately to **D1 (Stateful 2D/3D Physical Simulation Adapter and Parity Verification)**.
