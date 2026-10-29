# 0105 — B/D dataset bootstrap on the server (2D + xArm7 3D): audit, generator, smoke, pilots

**Authority:** `approach_D_server_dataset_bootstrap_prompt.md`. **Branch:** `dataset-bd-v1` (local worktree; on the server the same files sit on a server-local branch `dataset-bd-v1` of the clone). Nothing pushed or merged. Scope stops at G4: no 20k / 5k collection.

## G0 — Audit and environment manifest

| item | value |
|---|---|
| server | lab GPU server (key auth only; host not recorded in the repo) |
| GPU | NVIDIA RTX PRO 5000 Blackwell, 48,935 MiB, driver 595.84, CUDA 13.2; idle at start (no processes) |
| CPU / RAM | Intel Core Ultra 9 285K, 24 cores; 125 GiB RAM |
| storage | `/data` (ext4, 7.3 TB, 3.2 TB free, 2 % inodes used); `/` 116 GB free (not used for data) |
| workspace | `/data/user1/rss_ebm_dataset/{src,env,bin,data,logs,viz,cache,manifests,tmp}` |
| Python | micromamba env `/data/user1/rss_ebm_dataset/env/rss`: Python 3.13, numpy 2.4.0, scipy 1.16.3, matplotlib 3.11.2 (pinned to the local versions), pillow, psutil, pytest, mujoco 3.17.0, imageio |
| 2D source | `Narendhiranv04/latent-causal-tamp` `main` 027fb7f + local `approach-d-v1` 43fd985 (G1/G2a/G2b, transferred as a 4.9 MB git bundle) |
| 3D source | `rss-ebm-infeasibility` `yadu/dataset-3d` 1a919ce (imported unmodified) |
| 2D visual reference | `rss-ebm-infeasibility` `naren/PoC` 3a7062f (results package only; scenes trace back to the 2D repo) |
| robot model | MuJoCo Menagerie f3b6013, `ufactory_xarm7` only (sparse clone) |
| other users | 13 pre-existing tmux sessions (`idn_q_bigbox_*`, `wma_*`) left untouched; all sessions of this work are named `bd_*` |

### Grid and protocol conventions (reconciled)

| | 2D (planar 3R) | 3D (xArm7 cabinet) |
|---|---|---|
| grid | 8 x 8, pitch 0.08 m square cells | 8 x 8 on the shelf of one cabinet cell, 3 cm deep x 5 cm wide cells (`grid_dataset.GRID8`); the older 6 x 6 `GRID` in `xarm7_cabinet_env.py` is NOT used |
| cell ids | 0-based `cell = row*8 + col`, row 0 = low y | internal 0-based `(row, col)`, row 0 = front (robot side); the 3D repository's USER ids are 1-based: `id = row*8 + col + 1`. Records store internal `[row, col]` plus `user_id` where shown |
| objects | discs r = 0.024 m | upright cylinders r 0.010-0.012 m and boxes half-size 0.008-0.0095 m (fits 3 cm cells under the env's footprint rule; width >= GRIP_MIN_WIDTH), height 0.05-0.12 m (>= MIN_HEIGHT); T = green cylinder r 0.012 h 0.08 |
| side grasps | the declared 2D grasp set of `skill.py` (24 tool axes x 2 elbow branches) | the planner's own candidates only: hand pitch 0-25 deg (near-horizontal), 5 grasp offsets, grasp heights inside the object; approach from the front (robot side); level hand while carrying |
| start pose | home S0 or a historical non-home stratum S1-S3 | home only (no other validated start configuration in the 3D protocol; non-home specs are not sampled for 3D) |
| movability | movable discs + optional FIXED context discs (P13-P16 convention, never movers) | every object movable by rebuilding the scene with it in the planner's movable slot (see G1) |

### Teacher protocols (binary, `BD_BINARY_BUDGET_V1`)

- **2D:** `p16_motion.DetPhysics` (scoped certificates + certified skill planner, P16_FAST node budgets, no wall clock), FRESH budget per query `{motion_checks 150, online_moves 8, goal_plans 3, transit_plans 6}`, one exact shared cache per root. y = 1 iff VERIFIED (+ replay for sequences); else y = 0 with `negative_kind` CERTIFIED (certificate) / TIMEOUT (budget) / NO_PLAN_FOUND (planner gave up) and the original status string. Admin cap 900 CPU-s per root (a cap hit is a ledger rejection, never a label). Target-only scenes (no other object) call the certified skill planner directly: the historical `sector_cert._sector` cannot run on an object-free scene (empty-array bug, not edited).
- **3D:** `grid_dataset.GridPlanner` (IK + RRT-Connect, 3 attempts, 10,000 IK steps, 4,000 RRT iterations), `rrt_time = time_limit = 1e9` so iteration ceilings decide (deterministic; the repository's 10 s / 300 s wall-clock limits are disabled), admin wall cap 2,400 s per root. Hypothetical D edits are plan-only; B sequences are EXECUTED in MuJoCo step by step and pass only if every step and the final T move are verified by execution (placement error, tilt, no obstacle contact).

(Sections G1-G4 follow below.)
