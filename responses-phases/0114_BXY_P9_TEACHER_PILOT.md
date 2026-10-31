# 0114 — BXY-P9: connector-aware physical X/Y teacher and bounded supervision pilot

Date: 2026-10-31. Gate: BXY-P9 only. Instructions: `instruction-phase-md/BXY_P9_TEACHER_PILOT_INSTRUCTIONS_2026-10-31.md`,
`Approach_B_Final_Methodology_2026-10-31.pdf` (§§2–6, 8).

**Verdict (§G): `READY_FOR_P_MIN`.** This means only that the teacher and the protocol produced replayed X=1 and X=0,
independently decided Y, matched pairs and matched J. It does **not** mean the methodology is validated. No P-min, P-full,
training or 3D work was started.

---

## 1. Branch, HEAD, status, inventory, hashes, data availability

| item | value |
|---|---|
| branch | `approach-b-xy-v1` (worktree `.claude/worktrees/approach-b-xy-v1`) |
| HEAD before | `156ddf94117ab2202c7d6f32404043a683157585` (also recorded in `runs/approach_b/bxy_teacher_pilot_v1/RUN_STARTED.txt`) |
| HEAD after | the commit that adds this report (see `git log`); no other commits in this gate |
| `git status` before commit | only the new files below are untracked; no tracked file is modified |
| python / numpy / scipy | 3.13.11 / 2.4.0 / 1.16.3 |

Files added in this gate (nothing else changed):

| file | role |
|---|---|
| `bxy_teacher.py` | BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1: query keys, X query (prefix + connector), Y query, independent replays, pairing, travel |
| `bxy_pilot.py` | roster/worklist predeclaration, per-root subprocess worker, CPU/wall supervisor, sidecar + summary builder |
| `bxy_pilot_viz.py` | figures and the GIF, drawn from the stored witnesses |
| `tests/test_bxy_teacher.py` | 11 tests (§F) |
| `runs/approach_b/bxy_teacher_pilot_v1/` | ROSTER, WORKLIST, per-query results, witnesses, LEDGER, logs, archived-replay regression, `BXY_SIDECAR_V2_PILOT.json`, `SUMMARY.json` |
| `visualizations/approach_b/bxy_teacher_pilot_v1/` | 4 PNGs + 1 GIF |
| `responses-phases/0114_BXY_P9_TEACHER_PILOT.md` | this report |

Protected files were verified unchanged by `git diff --stat HEAD`: `bd_core.py`, `bd_2d.py`, `bxy_core.py`, `bxy_run.py`,
`bxy_lb.py`, `config.toml`, every `p16_*` and `p17_*`, `runs/approach_b/bxy/` (the old sidecar and FROZEN), and
`runs/approach_b/bd2d_lb_v1/`. No Approach D or 3D file was touched.

Dataset: the external snapshot `BXY_DATA=/home/naren/Desktop/rss_ebm_dataset_snapshot/20261031_mock2d_5000_full` exists,
was opened read-only, and has the recorded BD_GEN_V1 hash `sha256:78ca0e7c35d5a2b937554c03ce38b06db2486e5d74af5f2831e37e335ccb1a38`.

Hashes recorded in the sidecar manifest:

| hash | value |
|---|---|
| teacher_hash (all teacher sources) | `sha256:4930754123e6905619b5e34ae450c8e78599643460c03e6cd0ce11393ea0a4fe` (a single value across all 116 rows) |
| robot_profile_hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858` |
| `bxy_teacher.py` | `c18ac91c89b95db46346eb49c3117b4ddc303d0f06c07a0d7a4aa31358f8ba3b` (same at run time and now) |
| `bd_2d.py` / `bd_core.py` | `eb97136c…` / `f34b881c…` |
| `p16_motion.py` / `p16_common.py` | `43f4c38c…` / `dec0b7ed…` |
| `motion.py` / `geometry.py` / `skill.py` / `planner.py` | `f2052d60…` / `3db5ad2c…` / `c45ba175…` / `d48cc2f4…` |
| `ordered.py` / `p15_search.py` / `config.toml` | `05ddac72…` / `9c2af137…` / `56ede7f0…` |
| roster hash (manifest) | `67f8b332061ef73a82cac1ea6524ffa532dac548ad09e644e854554dd85a5091` |
| worklist hash (manifest) | `29529212f1aed8e644181451ff36d6dbc2c4007c7f44f94488e061bd91d34923` |
| file sha256 | ROSTER.json `b7893378…`; WORKLIST.json `0c8564ea…`; BXY_SIDECAR_V2_PILOT.json `adea6983…`; SUMMARY.json `db7bdc9f…` |

## 2. Teacher policy, query semantics, the repo calls they make, deviations

**Reference state.** q_ref = the root's frozen q0 with an open gripper (gap 0.07). It is never redefined. Every query key
carries a context hash, `sha([root, goal_cell, q_ref, gap, robot_profile_hash])[:12]`, so queries with a different q_ref,
task or robot profile cannot alias.
- X keys are ordered: `X2:{root}:{ctx}:{ordered sequence}`.
- Y keys are endpoints: `Y2:{root}:{ctx}:{sorted endpoint}`.

**X = 1 (BXY_X_TEACHER_V1).** An X query asks whether the ordered prefix executes and then reconnects to q_ref:
1. Every relocation is planned **from the achieved state of the previous one**, in the scene that relocation actually
   faces. The call is `p16_motion.DetPhysics(task, None, budget=bd_2d.QB, cache=root cache)` with profile fast and no
   library, so each move is an online `skill.plan_skill`. Among the verified edges, `p16_common.best_edge` picks the
   cheapest one.
2. After the last relocation, a connector is planned by `DetPhysics._transit(s, "t0", q_final, {"q":[q_ref],"gap":[0.07]}, key)`.
   It first tries a certified straight segment; otherwise it runs one bounded RRT (500 nodes), counted under `transit_plans`.
   The connector world is `motion.checkers(...)[("start", False)]`: every object in the edited scene, **including the
   target**, with nothing held and no contact allowed.
3. **Independent replay** (`replay_x`) re-checks everything from the stored arrays alone:
   - path continuity across records;
   - gripper gap and attachment schedule;
   - `certify_trajectory` of every relocation in the scene it faces;
   - each placed pose equals its destination cell centre;
   - each relocation ends released after retreat;
   - every connector segment is CLEAR under `geometry.certify` in the full world;
   - the connector stays inside joint limits and ends within 1e-6 of q_ref.

   X = 1 only when the planning and the replay both pass.
4. **X = 0** is recorded only after a completed teacher run, with the failed phase recorded as `relocation:j` or
   `connector`. If the terminal state or q_ref is not clear, X = 0 with a CERTIFIED negative kind.
5. **Not attempted (`y = null`).** An ineligible sequence (moving T, a fixed object, a duplicate, an illegal cell, or more
   than 6 actions) or an empty prefix is never attempted. The empty prefix is X = 1 by definition and is not stored as a
   label. A censored query also stays `y = null`.

**Y = 1 (BXY_Y_TEACHER_V1).** `bd_2d.t_goal(task, root cache, edited cells, q_ref)` runs the target task from the **same
q_ref** in the hypothetical edited scene, independently of X. The historical per-query budget and planner are unchanged.
`replay_y` checks that:
- the trace starts at q_ref with the reference gap;
- it certifies in the edited scene;
- t0 is placed at the goal;
- the trace ends released.

**Budget.** The per-query budget is the unchanged `bd_2d.QB` = {motion_checks 150, online_moves 8, goal_plans 3,
transit_plans 6}. Planner seeds come from `_key(state, budget)`, and node budgets (not wall time) decide outcomes.

**Pairing.** `pair()` matches an X and a Y only when `x.parent_y_key == y.y_key` (same root, same endpoint, same q_ref).
`full_joint_success` = x·y when both are decided, and `null` if either side is missing; a missing side is never filled.

**Travel.** `J_total` = `ordered.joint_travel` over the **stitched** path (relocations → connector → target from q_ref).
This is the PDF's unwrapped, range-normalised L1 joint travel, computed with continuity checks at every stitch point. Each
part is logged separately: `J_move` per relocation, `J_between_actions` (the pregrasp part), `J_connector` and `J_target`.

**Deviations from the PDF.** None intended. One addition: X rows carry a `legacy_witness_match` diagnostic, a comparison
of the re-planned relocations against the historical server witnesses (see §6).

## 3. Tests, archived replays, what was not run

| command | exit | result |
|---|---|---|
| `python3 -m pytest -q tests/test_bxy_teacher.py tests/test_bxy.py` (before collection and again after) | 0 | 26 passed |
| archived replays `g1_robot`, `g1_hardening`, `g2_interventions`, `g3_repairs`, `g3_5_initial_scene`, `g4a_evidence_audit` | all 0 | `replay_passed: true` ×6 (`runs/approach_b/bxy_teacher_pilot_v1/regression/`) |

The 11 new tests cover:
- key ordering, endpoint keys, no context aliasing, and an omitted object staying at its S0 pose;
- ineligible and empty prefixes not attempted;
- failure metadata that tells a step-0 relocation failure from a connector failure;
- a positive X requiring a written, replayed connector witness;
- a connector world that contains every body, and rejection of a straight segment whose endpoints are clear but whose
  middle collides;
- 8 tampered-witness rejections: discontinuous path, wrong destination, altered pose, missing record, wrong attachment,
  attached connector, connector missing q_ref, wrong gap;
- a Y replay that must start at q_ref (a Y from the achieved state is rejected);
- the four pair states, with a missing side never filled;
- a censored query being unobserved, with its CPU still charged to the ledger;
- a train-only roster and a predeclared worklist within the caps;
- a learner-input leakage audit.

**Not run:** no physical teacher call inside the unit tests (stubs and stored records only); no 3D; no training; no test
cohort.

## 4. Budget vs consumption, roster/worklist, missing and censored queries

| quantity | authorized cap | used |
|---|---|---|
| TRAIN roots | 20 | 20 (all finished) |
| distinct X queries | 60 | 57 attempted, 57 observed |
| distinct Y queries | 60 | 59 attempted, 59 observed |
| aggregate worker CPU-s (RUSAGE via `os.wait4`) | 3,600 | **1,470.0** |
| wall-s | 3,600 | **803.1** |
| workers | 2 | 2 |
| CPU-s per root (`RLIMIT_CPU`) | 300 | max 171.3 (s270), min 6.2 (s034) |
| per-query budget | unchanged `QB` | unchanged |

Per-query process CPU:
- **X:** median 3.3 s, max 48.9 s, sum 377 s.
- **Y:** median 3.2 s, max 99.2 s, sum 1,078 s.
- The rest is process start-up and imports.

Largest per-query counters for X: 5 online_moves and 1 transit_plans (every query used at most one RRT).

**Disclosures on counters:**
- `motion_checks` and `goal_plans` stay at 0 for X, because this physics mode does not draw on them.
- For Y, `bd_2d.t_goal` does not expose its counters, so Y rows record only CPU (`budget_spent: null`).

**Roster.** 20 TRAIN roots, chosen by the hash order `sha([k,"BXY_P9_ROSTER"])` and stratified by verified K:

| stratum | roots |
|---|---|
| K0 | s224, s177, s034, s271, plus s035 and s014 (diversity slots) |
| K1 | s226, s121, s137, s170, s117, s202 |
| K≥2 | s196, s212, s047, s187, s265 |
| None | s025, s270, s068 |

**Worklist.** 57 X / 59 Y with at most 3 X and 3 Y per root:

| item type | X | Y |
|---|---|---|
| Y0 | — | 20 |
| old_success | 20 | 20 |
| old_fail | 15 | 15 |
| reversed_pair | 7 | — (shares the old_success Y) |
| intermediate_prefix | 11 | 4 |
| omission | 4 | — |

**Superseded plan (disclosed).** An earlier worklist (hash `e9c7882b71b2554a7de652a32ac0f14f5dd7bafe784a8fb37b0d83528c0f12b4`,
46 X / 59 Y) left no room for omission items, because it only allowed intermediate/omission/nuisance X when the root also
had Y room. It was replaced **before any teacher query** by the rule "X-only items are allowed for
intermediate/omission/nuisance when only the Y cap blocks them". No outcome was known when it was replaced. No nuisance
item fits within 3 X per root.

**Missing and censored:** 0 censored, 0 not attempted, 0 `.inprogress` markers, and no root killed by the CPU guard. Each
of the 20 roots has one LEDGER line.

## 5. Results

### X (57 observed)

| prefix length | X=1 | X=0 |
|---|---|---|
| 1 | 23 | 0 |
| 2 | 15 | 3 |
| 3 | 7 | 2 |
| 4 | 2 | 2 |
| 5 | 2 | 1 |
| **total** | **49** | **8** |

The 8 negatives:
- by failed phase: `relocation:0` 4, `relocation:1` 1, `relocation:2` 3; `connector` **0**;
- by kind: 3 CERTIFIED_INFEASIBLE and 5 UNKNOWN_PLANNER (NO_PLAN_FOUND within the unchanged budget).

| root | item | failed phase | status |
|---|---|---|---|
| s025 | intermediate_prefix (2) | relocation:0 | CERTIFIED_INFEASIBLE |
| s035 | old_fail (4) | relocation:0 | CERTIFIED_INFEASIBLE |
| s035 | intermediate_prefix (5) | relocation:2 | UNKNOWN_PLANNER |
| s047 | reversed_pair (3) | relocation:0 | UNKNOWN_PLANNER |
| s047 | old_fail (2) | relocation:1 | UNKNOWN_PLANNER |
| s177 | old_fail (3) | relocation:2 | UNKNOWN_PLANNER |
| s177 | intermediate_prefix (4) | relocation:2 | UNKNOWN_PLANNER |
| s212 | reversed_pair (2) | relocation:0 | CERTIFIED_INFEASIBLE |

**Connector:**
- 49 of the 49 successful relocation prefixes received a verified, replayed connector: **100%**.
- 10 used a direct certified segment and 39 used one RRT.
- That gives 49 distinct connector witnesses, all replayed.

### Y (59 observed)

| outcome | count | detail |
|---|---|---|
| Y=1 | 29 | — |
| Y=0 | 30 | 6 CERTIFIED_INFEASIBLE, 24 UNKNOWN_PLANNER |

Every one of the 78 positives (49 X, 29 Y) has `independent_replay: true`, and no replay failed.

Agreement with historical Y labels from q_ref: 45 of the 45 Y queries that have a legacy label agree; 14 have no legacy
label. By stratum, Y0 is 1 on all 6 K0 roots and 0 on all 14 others, which matches the verified K.

### Matched decided pairs: 46 (four-cell table)

| | Y=1 | Y=0 |
|---|---|---|
| **X=1** | **23** (full joint success) | 18 |
| **X=0** | 5 | **0** |

The X=0,Y=0 cell is empty because of the predeclared selection:
- The old_fail items deliberately prefer failures **at the target step**. Their relocations mostly succeed (X=1) and the
  target fails (Y=0), which gives 11 of the 18 X=1,Y=0 pairs. The other 7 are the 3 old_success and 2 reversed pairs on
  the `verified_K = None` roots, plus 2 intermediate prefixes.
- The 5 paired X=0 cases (s035, s047 ×2, s177, s212) all share an endpoint whose Y is 1.
- The other 3 X=0 are X-only intermediate items, so they have no pair.

Coverage by root: the 46 pairs cover 20 roots, and every root has at least one decided pair. By K stratum
(`summary.by_K`, full_joint_success over decided pairs):

| stratum | full joint success = 1 | = 0 |
|---|---|---|
| K0 | 8 | 3 |
| K1 | 6 | 6 |
| K≥2 | 9 | 6 |
| None | 0 | 8 |

**Legacy B success under the new protocol:** 17 of the 20 historical train B successes satisfy the new X+connector+Y(q_ref)
protocol.
- The 3 that do not are exactly the 3 `verified_K = None` roots (s025, s068, s270). Their relocations and connector succeed,
  but the target **from q_ref** fails (UNKNOWN_PLANNER). Their legacy Y label from q_ref was also 0. The historical B
  success had run the target from the *achieved* state, which the new protocol no longer credits.
- **Selection bias:** these 20 are the first historical success per selected root and are not a random sample. The rate is
  descriptive only.

**Reversed-order X contrasts with a shared Y (7 decided):**
- **2 show an order contrast:**
  - s047: `o00→62, o02→4, o01→23` gives X=1, while the reverse order fails at `relocation:0`.
  - s212: `o02→30, o01→46` gives X=1, while the reverse fails at `relocation:0` (CERTIFIED_INFEASIBLE).
- 5 have X=1 in both orders (s068, s187, s196, s265, s270).

There is **no decided omission or nonadditivity contrast**. The 4 omission items are X-only (all X=1), and the cap of 3 Y
per root left no room for their Y.

### Travel ledger

There are 23 valid matched `J_total` witnesses, one per full-joint-success pair. All stitch points are continuous, and
`J_total` equals the sum of its parts to within 0.0.
- The connector is a material part of the cost: its median share of `J_total` is 21%.
- Diagnostic only, not an optimisation claim: Pearson r(J_total, legacy B travel) = 0.84 over the 20 old_success pairs.
  J_total is larger than the legacy travel in every case, because the connector and the q_ref target are now included.
- Order changes travel. On s196 both orders succeed, with J_total 8.31 vs 4.15.

| root | item | moves | ΣJ_move | J_connector | J_target | J_total | connector | connector witness | target witness |
|---|---|---|---|---|---|---|---|---|---|
| s014 | old_success | 3 | 2.988 | 1.553 | 2.697 | 7.239 | RRT | `bd1e1e8968bd4bbf2abd6b67` | `6a4581dadc09d6ade95b36e5` |
| s034 | old_success | 1 | 1.020 | 0.833 | 1.345 | 3.198 | direct | `76f80ebdaf3dedc85912fd5d` | `fc13ed32382de9cdced71604` |
| s035 | old_success | 1 | 1.494 | 2.485 | 1.247 | 5.226 | RRT | `7bfbbff27ee956c273d53a7b` | `ef5ebb125cb355bf04f4cf42` |
| s047 | old_success | 3 | 2.833 | 1.303 | 1.255 | 5.391 | RRT | `c49b35662947528f9d36e159` | `27926dbed0e2b70ac051bf66` |
| s117 | old_success | 1 | 1.146 | 1.042 | 1.539 | 3.727 | RRT | `f8ea8f94e166218a0a6b18af` | `509fe11c155246950c15fa4c` |
| s121 | old_success | 1 | 2.719 | 1.602 | 2.505 | 6.825 | RRT | `6f48840eaf3d10a9e90460d6` | `58dc4e8e0af64ec72cc9ee1f` |
| s137 | old_success | 1 | 1.351 | 1.006 | 2.792 | 5.149 | RRT | `1600a0ed9c4f87800d46d8ff` | `2dd0e4a613c6e7024d88bbda` |
| s170 | old_success | 1 | 3.936 | 0.985 | 2.511 | 7.432 | RRT | `d5c63d8bcfbfbb001defff4b` | `418bbeb2a47a6c3bbca46cbb` |
| s177 | old_success | 1 | 1.033 | 1.372 | 1.437 | 3.842 | RRT | `3e83a3102910690ebe9a1871` | `d7988798ef87dc5fb37f1981` |
| s187 | old_success | 2 | 1.395 | 0.921 | 1.895 | 4.211 | RRT | `00ffad9f2a428938ddd17778` | `7234668b61b891346642ea08` |
| s187 | reversed_pair | 2 | 1.330 | 0.990 | 1.895 | 4.215 | RRT | `43394eff1a4a9205fc340aed` | `7234668b61b891346642ea08` |
| s196 | old_success | 4 | 5.586 | 1.354 | 1.370 | 8.309 | RRT | `1e395284bed48c82d47b10a7` | `be9e325c4402a0e81f84b71b` |
| s196 | reversed_pair | 4 | 1.956 | 0.826 | 1.370 | 4.152 | RRT | `091870f7a35fc7e9d40f3a39` | `be9e325c4402a0e81f84b71b` |
| s196 | intermediate_prefix | 5 | 6.144 | 1.140 | 3.066 | 10.350 | RRT | `507d0825d57c2ad863d4384e` | `b2e532f362a0af19a7a8246f` |
| s202 | old_success | 1 | 1.503 | 0.983 | 2.198 | 4.684 | RRT | `466b7be5540ed2dbc076ec58` | `e31ad4469685c44eea549158` |
| s212 | old_success | 2 | 2.574 | 0.783 | 1.007 | 4.365 | RRT | `8dfa3210598368c9e70e5efa` | `47d92080320b82954cbfb2ef` |
| s224 | old_success | 1 | 1.034 | 0.935 | 0.942 | 2.911 | RRT | `2aa99f8a963c89189f1effdf` | `999030a46b1804de4561ad17` |
| s224 | old_fail | 2 | 1.898 | 0.802 | 1.278 | 3.978 | direct | `38de053805a06d10efa6aede` | `b2efe3743ab324c7241132f2` |
| s226 | old_success | 1 | 1.021 | 0.875 | 2.308 | 4.204 | direct | `b3a24db6532cf373608d60b5` | `979024c035ccf78bfa5f7ed5` |
| s265 | old_success | 2 | 1.410 | 0.665 | 1.361 | 3.436 | RRT | `add14e652b13351884c90622` | `3e5df3e6ece26b12b10e4d7b` |
| s265 | reversed_pair | 2 | 1.731 | 0.965 | 1.361 | 4.057 | RRT | `f4f2c69b364d402e131d8b75` | `3e5df3e6ece26b12b10e4d7b` |
| s271 | old_success | 2 | 1.696 | 0.744 | 1.115 | 3.555 | RRT | `2b99022e03a7d8c089c23238` | `45a210e71f98cf20ce713f3d` |
| s271 | intermediate_prefix | 1 | 1.104 | 0.625 | 1.326 | 3.055 | RRT | `94fab2eca680773304f40567` | `9b995a6f2fa5e488f0501cb8` |

Witness files are stored at `runs/approach_b/bxy_teacher_pilot_v1/witnesses/<id[:2]>/<id>.npz`; there are 160
content-hashed records. Relocation witness IDs are listed per row in the sidecar (`witness_relocations`).

All labels above come from the teacher and are uncalibrated physical labels. **No model prediction was made in this gate.**

### Visuals (drawn from the stored records)

- `visualizations/approach_b/bxy_teacher_pilot_v1/01_query_status.png`: every predeclared query with its outcome and
  failed phase.
- `visualizations/approach_b/bxy_teacher_pilot_v1/02_cpu.png`: per-root RUSAGE CPU against the 300 CPU-s cap, and
  per-query CPU.
- `visualizations/approach_b/bxy_teacher_pilot_v1/03_root_0_s014.png`: S0 at q_ref; the 3-move X with the relocation paths
  (blue), the RRT connector back to q_ref (pink) and the arm before and after the connector; and Y from q_ref in the edited
  scene (green).
- `visualizations/approach_b/bxy_teacher_pilot_v1/03_root_1_s025.png`: X=1 with a connector, but Y=0 from q_ref (the
  `verified_K = None` case).
- `visualizations/approach_b/bxy_teacher_pilot_v1/04_full_joint_witness_s014.gif`: an animation of the full joint
  witness: relocations, connector, then the target from q_ref.

## 6. Issues

1. **Absence treated as X=0: none found.**
   - `bxy_core.views` builds `obs_x` only from observed keys.
   - In P9, an unattempted or censored query is `y = null`, and `pair()` returns `full_joint_success = null` when either
     side is missing.
   - Both behaviours are tested. The pilot had no missing or censored rows.
2. **Test-data access: none.**
   - The roster is TRAIN-only (asserted by a test), and the teacher read only roster roots.
   - The leakage test reads the learner tensors of `bd2d_lb_v1/RECORDS.pt` only to check the input allowlist. It reads no
     labels or predictions.
3. **Historic P7 custody discrepancy (unchanged history).** `bxy_lb.py:run()` writes test predictions during each seed's
   training, before `bxy_run.py:freeze()`. Report 0112's strict "first read after freeze" claim is therefore not
   established. The historical files were left as they are; a fresh evaluation workflow must fix custody later.
4. **F1 screen.** `bxy_run.py:choose()` has no explicit call to the F1 analytic hard screen. This is a tracked deferred
   protocol question and was not changed here.
5. **No-op J convention.**
   - `choose()` scores the no-op with `J_hat = 0`.
   - The PDF's J for a no-op is the target travel from q_ref. In this pilot, the Y0 positives have J_target 1.23–2.63
     (s014 2.517, s034 1.236, s035 1.233, s177 2.627, s224 1.303, s271 1.439).
   - `J_hat = 0` therefore under-charges the no-op relative to every nonempty repair, whose J_total includes the target
     leg. This must be reconciled before any λJ selection. The pilot records the no-op target travel explicitly.
6. **Determinism (1 ulp).**
   - Re-planned relocations match the historical server witnesses exactly in 9 cases and within 1e-12 in 31 cases; 13
     queries have no legacy record to compare against. None differs.
   - The non-exact matches differ by about 2.2e-16 (1 ulp) on the same numpy 2.4.0 and scipy 1.16.3. This is attributed
     to floating-point summation order across machines. The policy is the same.
7. **Y counters.** `bd_2d.t_goal` does not expose per-query budget counters, so Y rows record CPU only. The budget is
   still enforced inside the unchanged `t_goal`.
8. **Plan superseded before collection.** See §4. Nothing was re-run after an outcome was seen.
9. **Coverage limits.**
   - There is no X=0,Y=0 cell and no decided omission or nonadditivity contrast (both are Y-cap limits).
   - The K3/K4 scenes are few: K≥2 has 5 roots.
   - 24 of the 30 Y=0 and 5 of the 8 X=0 are budget-limited UNKNOWN_PLANNER failures, not certificates. They count as 0
     under the binary contract.

## 7. Verdict and next gate

**`READY_FOR_P_MIN`.**
- 8 replayed nonempty X=0 and 49 replayed nonempty X=1.
- 59 independently decided Y from q_ref.
- 46 matched decided pairs covering 3 of the 4 cells.
- 23 matched J_total witnesses.
- 0 connector failures among 49 reached prefixes.
- 0 censored queries, 6/6 archived replays passing, and 41% of the CPU cap used.

The methodology is **not validated**. Nothing here measures selection quality.

**Recommended next gate (only): BXY-P-min design and collection, which needs a new explicit authorization.**
1. Predeclare a prospective roster and worklist, root-grouped and TRAIN/VAL only, with no test cohort. It should:
   - target the empty X=0,Y=0 cell and the omission/nonadditivity contrasts by raising the per-root Y cap for omission
     items;
   - oversample K≥2 roots;
   - include both orders for every multi-move success.
2. Scale estimate, from the measured 1,470 CPU-s for 116 queries (≈ 12.7 CPU-s per query including start-up): about 150
   roots × 8 queries ≈ 1,200 queries ≈ 15,000–20,000 CPU-s. With 2 workers that is about 2.5–3 hours of wall time; with
   more workers it is proportionally shorter. **The user must authorize the CPU-seconds, the wall time and the worker
   count.**
3. Before any λJ selection, retraining or new frozen test cohort, resolve the no-op J convention and the F1 screen (§6.4–6.5).

## 8. STOP

The gate ends here. P-min, P-full, X/Y retraining, selector tuning and 3D were not started.
