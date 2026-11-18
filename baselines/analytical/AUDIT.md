# AUDIT: analytical baselines (E-M4M, MO-SeGMan, MS-MCTS), K <= 3 target repair, 2D + 3D

Every claim tagged **Dn** / **Fn** is checked by `tests/test_audit.py` (exact legacy line text, or a regex that must be present in the
new code); behavioural claims cite the test that exercises them. Run: `python3 -m pytest baselines/analytical/tests -q`.

## 1. Provenance of the prior implementation

* Teammate code: `rss-ebm-infeasibility` @ `14ade19a950dbe5f24e2c0711ef83ed8c6238eb3`, folder `baselines2d/` (2D only). Copied
  verbatim to `legacy_2d_14ade19a/` (blob ids in `legacy_2d_14ade19a/PROVENANCE.md`; `test_legacy_copy_is_verbatim`).
* Its historical results (`legacy_2d_14ade19a/RESULTS.md`: K <= 4, TEST split, 300 CPU-s; Task E-M4M 61.7 / MO-SeGMan 30.7 /
  MS-MCTS 27.0) are historical only: other contract (K <= 4, vacated cells allowed), other split, shared caches. Not used for any decision.
* 3D: the only prior 3D code is an unrelated MuJoCo push port (`mamo/mamo/em4m`, REAP environments, not the SHELF66V3 benchmark).
  Nothing of it is reused; the 3D planners here are the same code as 2D running on the 3D physical layer.

## 2. Legacy components: present / simplified (verified by reading `legacy_2d_14ade19a/b2d/*.py`)

| Method | Present in legacy | Simplified / missing in legacy |
|---|---|---|
| E-M4M (`em4m2d.py`) | NGR from an obstacle-ignorant target plan, best-first OPEN, DONE once per vertex, MAPF-as-assignment with invalid goals, negative cache, Naive-Bayes priority (phi1, phi2), hallucinated goals | vertex identity = sorted cells only (**D1**); fixed objects can be agents (**D4a**); goals may be vacated source cells (**D4d**); K <= 4 (**D4e**) |
| MO-SeGMan (`mosegman.py`) | critical objects (1 / 2-4 subsets / > 4 nearest), GOM + reachability scene score, object weights, node score + exploration, secondary-obstacle rule, EDT relocation points, SGFS, second attempt | subset feasibility tested against ONE stale obstacle-free path (**D2a**: vacuous - the first feasible subset is always the full blocker set); the second attempt removes the first set from the candidates, so for 2-4 blockers it can never find a set (**D2b**); critical set never recomputed after moves; fixed objects counted as collision objects (**D4c**) |
| MS-MCTS (`msmcts.py`) | Algorithm 2 expansion (blockers, accessibility, dependencies, halting, stuck rule), Algorithm 1 regions verified by MP, UCB1-Tuned, rollouts, back-propagation | single stage (acceptable: one goal object); no transposition handling; a successful rollout's plan is discarded (**D3a**); picking paths cached by (object, its cell) ignoring the rest of the scene (**D3b**); hard caps 2 regions / 4 tries (**D3c**); fixed objects can be O_b members (**D4b**) |
| shared (`common.py`, `teacher.py`, `run.py`, `paths.py`) | dataset planner with per-call cap, exact caches, X/Y verification | target blockers over every non-target object incl. fixed (**D4f**); final verification reuses the search's planner cache (**D5**); data layout hard-wired to the Windows/Docker mount `D:\RRC\New folder` -> `/work` (**D6**, README.md:37-53); movable set read from the private `roles` field (**D7**) |

## 3. Defects verified (exact legacy lines) and fixes

| Claim | Legacy evidence | Fix (new code) | Behavioural test |
|---|---|---|---|
| **D1a** **D1b** E-M4M visited key = sorted cells; an equal-length duplicate overwrites parent / seq / q of the existing vertex | `em4m2d.py:186`, `:191` | **F1** vertices keyed by `phys.key` = cells + moved set + achieved q + gripper (+ 2D planner budget counters, 3D object qpos/qvel), prefix order excluded; an existing key = identical physical state (dropped), different q = different vertex | `test_em4m_transposition_regression` (two orders -> same cells, only one has a feasible connector: the legacy key loses it for some seeds, the physical key never), `test_order_sensitivity_same_endpoint_different_x`, real 2D: `keys_differ` |
| **D2a** **D2b** MO-SeGMan subset test reuses one gamma; second attempt impossible for 2-4 blockers; no recompute after moves | `mosegman.py:124`, `:283` | **F2a** subsets tested on several obstacle-ignorant plans (and the linear path) in THE CURRENT hypothetical scene; **F2b** critical set refreshed after every executed move; **F2c** alternatives = next minimal critical sets, kept up to `sgfs_attempts` | `test_solves_k2_and_commits_one_legal_answer[MOSeGMan]`, `test_target_path_modes` |
| **D3a** **D3b** **D3c** MS-MCTS discards successful rollout plans; scene-blind pick cache; fixed caps | `msmcts.py:179`, `:63`, `:36` | **F3a** a rollout reaching the objective with a verified terminal check is returned; **F3b** pick-path cache keyed by (full scene, object); **F3c** transposition table (one node per physical state, duplicate children merged); m / tries are declared hyperparameters (`config/grid.json`) | `test_solves_k2...[MSMCTS]`, `test_deterministic_replay[MSMCTS]` |
| **D4a**-**D4f** fixed objects not excluded; destinations = currently free (vacated source cells allowed); K <= 4 | `em4m2d.py:158`, `msmcts.py:116`, `mosegman.py:231`, `common.py:31`, `:18`, `:45` | **F4a** destinations = legal, free now, ORIGINALLY empty, not the goal cell; **F4b** K_MAX = 3; **F4c** every action is checked by `contract.legality` before physics (illegal -> rejected, never sent); movable = public non-target, non-fixed objects | `test_rules`, `test_agrees_with_benchmark_legality` (3000 random prefixes + 1800 on real 3D rows vs `benchmark.legality`), `test_phys_never_sends_illegal_actions` |
| **D5** final verification shares planner + cache with the solvers | `run.py:127` | **F5** predictions are sealed, then verified by `approach_b_final/benchmark.py` (unchanged finalized teachers, separate process, separate cache dir) | `eval.sh`; smoke results below |
| **D6** Windows / container paths | `paths.py:7` | **F6** paths from env vars (`env.sh`) and worktree-relative imports (`ANALYTICAL_WORKTREES`) | — |
| **D7** movable set from private `roles` | `teacher.py:103` | **F7** raw records scrubbed of private keys; the 2D teacher's `roles` keys rebuilt from public attrs (values neutralised; equality with the record's key set asserted: 751/751 2D and 364/364 3D VAL roots) | `test_private_keys_scrubbed`, real `private_fields_irrelevant` (labels / roles / construction corrupted -> identical run) |

## 4. Contract tests (all in `tests/`)

legality (fixed / target exclusion, move-once, originally-empty, goal cell, K <= 3): `test_contract.py`; order sensitivity and
transpositions: `test_order_sensitivity_*`, `test_em4m_transposition_regression`; Y order independence: `test_y_order_independent` +
real `y_order_independent` (endpoint cache); exact restore after rejected branches: `test_restore_after_rejected_branch_and_carried_state`
+ real `restore_equal_after_branch` / `parent_untouched`; no state reset between moves: same test + real `second_move_starts_at_carried_q`
(2D: the second relocation's first recorded configuration equals the first's achieved q); connector required: `test_connector_required`
+ real `connector_calls_for_two_terminals`; timeout / UNKNOWN: `test_timeout_is_abstain_never_label`, `test_call_cap_unknown`,
`test_wall_and_call_budgets`; no private-label access: `test_private_fields_do_not_change_output`, `test_private_keys_scrubbed`, real
`private_fields_irrelevant`; deterministic replay: `test_deterministic_replay`, real `deterministic_replay`; budget accounting:
`test_cache_and_accounting`; one committed answer: `test_prediction_line_and_one_answer`, `run.py merge` (exactly one line per root).

## 5. Coverage

| | 2D (planar 3R, BXY DetPhysics) | 3D (xArm7 SHELF66V3, MuJoCo 3.16) |
|---|---|---|
| E-M4M / MO-SeGMan / MS-MCTS | yes / yes / yes | yes / yes / yes |
| physical transitions with carried state | RepairEnv 2D | RepairEnv 3D |
| terminal connector + Y | BXY_X / BXY_Y teachers | CONNECTOR_TO_QREADY_V1 + BD3DS66_Y_PLAN_V1 |
| obstacle-ignorant target plans | NOR_HOMOTOPY_2D_V1 (6 of <= 12 grasp pairs) | NOR_HOMOTOPY_3D_V1 (<= 6 of 12 side grasps) |
| final verification | benchmark.py teach (env2d) | benchmark.py teach (env3d) |

Not reproduced in either domain (see ADAPTATIONS.md): continuous object poses, push actions, KOMO / CBS / RRT re-plans per critical
subset, multi-object goal sequencing, non-monotone moves. In 2D the obstacle-ignorant arm sweeps cover most of the 8 x 8 board
(43-63 of 64 cells on the TRAIN roots inspected), so planned-path blockers are a weak screen there; this is a property of the 3R arm, not
a defect, and is why `t_paths` (planned / linear / both) is a grid hyperparameter.
