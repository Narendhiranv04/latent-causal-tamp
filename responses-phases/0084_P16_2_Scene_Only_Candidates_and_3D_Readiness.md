# 0084 — P16-2: scene-only candidate API, mechanism pilot, splits and 3D readiness

**Actual result**
- **Gate:** `runs/p16/P16_2_GATE.json` → **PASS (API and pilot).**
- **Families:** 8 of the 10 contract families were physically realised on 12 DEV roots. Family 6 (a relocation blocking a later sweep) and family 8 (a required repeat move) were **not realised** on DEV; the search supports them, but none occurred.
- **Splits built and frozen as rosters before any label:** train 80, val 22, calib 40, test 168.
  - No root-id overlap and no index overlap.
  - 2 cross-split geometry duplicates were found and the later copy excluded (`runs/p16/data/{LEAKAGE,EXCLUDED}.json`).
- **3D specification:** `responses-phases/P16_3D_MIGRATION_SPECIFICATION.md` (design only).

## 1. Scene-only runtime interface (`p16_common.py`)

| function | input | output | privileged input |
|---|---|---|---|
| `task_from_root` | constructed root | {scene, goal_cell, fixed_ids, target, key} | none; fixed structures are declared static metadata. A test deletes catalogue, parking, roles, predicates and ids and gets an identical task |
| `propose_movers(task, cells)` | current state | every movable, non-fixed, non-target object, nearest the target first, cap 6; omissions recorded | none |
| `slot_fn(phys, idx)` | current state | the 4 nearest free annulus-safe cells at least 2 cells from target and goal (freed source cells included), plus library-witnessed destinations from the object's current cell; ≤ 6 | none (library from other roots only) |
| `DetPhysics.edges / goal` | state, move | VERIFIED (witness, q_end, travel) / CERTIFIED (scope) / STATIC_INVALID / UNKNOWN_* | none |
| `verify_sequence(phys, seq)` | proposed ordered repair | VERIFIED plan or the first non-verified status | none |
| `catalogue(task, phys)` | task | pool (≤ 3 nearest movers), one scene-only parking slot each, all lattice subsets, sequences = empty + singles + all ordered pairs | none |
| `search(...)` | state, guide order | expanded finite search: repeat moves up to 2 per object (never consecutively), dominance on (occupancy, q) against ≤ counts and ≤ travel, n ≤ 4, node cap | none |

- **Deterministic physical labels** (`label`): y = 1 VERIFIED; y = 0 **only from a sound certificate** (target CERTIFIED_INFEASIBLE, or a step CERTIFIED / STATIC_INVALID); otherwise UNKNOWN, which is masked and never negative.
- **Cost:** about 150 CPU-s per DEV root (range 9–639) under the `P16_FAST` profile. The default profile cost up to 683 s per root, and its five DEV workers were stopped at 5,450 CPU-s, all charged.

## 2. Mechanism pilot (12 DEV roots; physics-only, no model consulted)

| root | family | movers | original | scene-only lattice | union / necessary | contract family realised | search (uniform, n ≤ 4, repeat ≤ 2) |
|---|---|---|---|---|---|---|---|
| 11000 | NAT | 3 | VERIFIED | FEASIBLE_ORIGINAL | — | 1 (0 moves, decoys) | 0 moves, both minima proven |
| 10004 | DENSE | 4 | VERIFIED | FEASIBLE_ORIGINAL | — | 1 | 0 moves |
| 15000 | PN_GIMP | 2 | CERTIFIED | MINIMAL_SETS | [0,1] / [0,1] | 2 (one necessary blocker) | 1 move, both minima proven |
| 16000 | PN_SIMP | 2 | CERTIFIED | MINIMAL_SETS | [0,1] / [0,1] | 2 | 1 move, min-moves proven |
| 14000 | PC_SG | 2 | CERTIFIED | MINIMAL_SETS | [1,1] / [1,1] | 3 (complementary) | 2 moves |
| 13000 | ORD_CHAIN | 2 | CERTIFIED | MINIMAL_SETS | [1,1] / [1,1] | 3 + **5 (access chain: reversed order certified infeasible)** | 2 moves, min-moves proven |
| 17000 | PR_SIDES | 2 | CERTIFIED | MINIMAL_SETS | **[1,1] / [0,0]** | **4 (alternatives: union ≠ intersection)** | 1 move, both minima proven |
| 19000 | TRI_OR | 3 | CERTIFIED | MINIMAL_SETS | [1,1,1] / [0,0,1] | 4 + 9 (A and (B or C)) | 2 moves |
| 12000 | OMIT_OPT | 3 | CERTIFIED | MINIMAL_SETS | [1,1,0] / [1,1,0] | 9 (2 necessary, 1 decoy) | 2 moves |
| 10000 | DENSE | 4 | CERTIFIED | **NO_CLEARING_SET_WITHIN_POOL** | — | **7 (slot choice)**: parking at the scene-only slot never clears the target, but moving o02 to cell 62 does | 1 move, min-moves proven |
| 10001 | DENSE | 4 | CERTIFIED | NO_CLEARING_SET_WITHIN_POOL | — | 10 (unresolved: no plan within budget; **not** a proof) | NO_PLAN_FOUND |
| 18000 | TRI_CTRL | 3 | CERTIFIED | INCOMPLETE (UNKNOWN subsets) | — | 10 (incomplete lattice) | — (worker stopped) |

**Informative branching (physics only):** every non-trivial root has 2–10 verified distinct first moves (`first_moves_verified`). A guidance policy can therefore change expansion order. Whether that changes outcomes under budget is the P16-D question.

**Not realised on DEV:**
- family 6 (relocation endpoint free but a later sweep blocked);
- family 8 (a verified plan that needs a repeat move).

Repeat moves are enabled in the search (unit test `test_repeat_move_found_only_in_expanded_domain`). Both families are reported as **NOT_REALISED (n = 12)**, not as absent from physics.

**Label semantics in practice (DENSE 10000).** The scene-only lattice says "no clearing set at these parking slots", while the search finds a 1-move plan to another slot. The `NO_CLEARING_SET` mask is therefore destination-scoped and **not** evidence of zero blocker membership. P16 D masks such records (0086).

## 3. Splits (frozen rosters; disjoint seed ranges; `runs/p16/data/SPLIT_COUNTS.json`)

| split | seeds | NAT | DENSE | mechanism families × | total | use |
|---|---|---|---|---|---|---|
| dev | 2026210000+ | 2 | 6 | 2 | 24 (12 labelled) | development only (also added to training) |
| train | 2026220000+ | 40 | 16 | 3 | 80 (79 after exclusion) | training |
| val | 2026250000+ | 10 | 4 | 1 | 22 (21) | checkpoint selection, temporary-target validation |
| calib | 2026230000+ | 24 | 8 | 1 | 40 | thresholds / calibration only; temporary-target validation |
| test | 2026240000+ | 120 | 24 | 3 | 168 | prospective, sealed (B: all; D: the 48 non-NAT roots) |

**Leakage:** 334 roots in total. Root ids are disjoint. Two geometry fingerprints repeated across splits (train↔val and dev↔train, from different family constructors). The later copies were excluded **before any label**. The test split has no duplicate. No P16 root or fingerprint appears in the motion index (which predates P16).

## 4. 3D migration

See `P16_3D_MIGRATION_SPECIFICATION.md`:
- robot, grasp sets and swept volumes;
- which certificates do **not** transfer (link-0 sector);
- 10 candidate 3D families;
- input changes for B and D;
- the determinism and compute quote (≈ 280k CPU-s for a minimal P17);
- the gates.

No 3D experiment was run. MuJoCo and trimesh are installed, but the repository supports no 3D scene, robot model or certifier.

## 5. Figures

- `visualizations/p16/shared/P16_dev_families.png`: initial scene, pool, scene-only parking arrows, fixed structures, lattice semantics and search result for all 12 DEV roots.
- `visualizations/p16/shared/P16_dev_ORD_CHAIN_13000.gif`: deterministic re-run of a certified 2-move access-chain plan; only replay-CLEAR arrays are drawn.
