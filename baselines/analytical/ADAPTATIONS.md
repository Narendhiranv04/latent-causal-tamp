# Adaptations: E-M4M, MO-SeGMan and MS-MCTS on the K <= 3 target-repair benchmark (2D and 3D)

These are **adapted re-implementations, not unchanged reproductions**. The three papers solve different problems (continuous object
poses, push or pick-and-place with their own motion planners, multiple goal objects, non-monotone rearrangement). Our benchmark fixes
one target task per root and asks for one committed decision: REPAIR (<= 3 ordered relocations of movable non-target objects, each moved
once, to legal ORIGINALLY-empty cells, never the goal cell), NOOP or ABSTAIN. Every deviation is listed here, with the code that
implements it.

Sources read: MO-SeGMan reference code `src/SeGManv2.py` and `src/MOSeGMan.py` (github.com/CankutBoraTuncer/MO-SeGMan, main); MS-MCTS
arXiv 2305.17175v3 (HTML); E-M4M arXiv 2303.13385v1 (HTML). Constants quoted below are from those sources unless marked *ours*. The
legacy 2D port (`legacy_2d_14ade19a/`, see `AUDIT.md`) supplied the E-M4M priority constants (`mamo_search.cpp createDists()` of our
MuJoCo port) and the overall structure of each planner.

## Common layer (all three methods, both domains)

| Topic | Paper(s) | Here | Code |
|---|---|---|---|
| Action | push (E-M4M), pick-and-place with KOMO / RRT (MO-SeGMan), linear pick/place paths + motion planner (MS-MCTS) | one **physically executed** relocation by the benchmark's own X-teacher relocation planner, from the **carried** robot / gripper / physics state of the previous step (DISCO stage-2 `RepairEnv.transition`: 2D BXY DetPhysics, 3D fin3d xArm7 + MuJoCo 3.16). No reset to q_ref and no connector between moves | `phys.py` `RealPhys._step` |
| Goal test | plan the object of interest's retrieval / placement | terminal check = the X terminal connector from the carried state to q_ref, then (only if X = 1) the Y target query from q_ref in the canonical endpoint scene (`RepairEnv.terminal_query`). REPAIR is committed only when this returned success | `phys.py` `terminal`, `common.py` `done` |
| Oracle regime | planners call their own motion planner | **oracle-assisted planning**: search-time physical queries are allowed but counted: `transition_calls` (+ `transition_cache_hits`, `_failed`, `_unknown`), `connector_calls`, `y_calls` (+ `y_cache_hits`), `ref_plan_calls` (obstacle-ignorant target plans), `grasp_attempts` (3D, reported by the planner), `capped_calls`; IK / collision checks inside the teachers are not separately instrumented (reported as part of these calls) | `phys.py` `PhysBase.n`, `stats()` |
| Object-of-interest path | gamma_OoI (E-M4M), task trajectory with clones (MO-SeGMan), T's picking/placing paths (MS-MCTS) | `t_paths`: `planned` = up to 6 obstacle-ignorant target plans (grasp homotopies; NOR-Grid `homotopy.py`: 2D `bd_2d.t_goal` per restricted grasp pair in a scene with the target + fixed structure only, sweep = `p14_sweep_index.swept_cells`; 3D `plan_pick_place` per side grasp in a target-only scene with the full scene's arm ceiling, sweep = cells a generic column of median footprint radius would touch + exact object hits in the initial scene); `linear` = MS-MCTS's linear paths (robot base -> T, T -> goal, swept by T's disc, public geometry); `both` = union | `phys.py` `_ref_paths`, `common.py` `start`, `linear_path` |
| Blockers in a hypothetical scene | collision checks against the path | objects whose **current** cell lies in a path's sweep (+ its exact initial-scene hits while unmoved), **recomputed for every scene**; target never a blocker; 2D fixed objects never (the plans keep them) | `phys.py` `blockers` |
| Candidates | any object, continuous poses | movable non-target objects only (2D `attrs[3]` fixed flag excluded), each at most once; destinations = legal cells free now, **empty in the original scene**, not the goal cell; at most 3 moves. Illegal actions are rejected before physics | `contract.py`, `phys.py` `step` |
| State identity | object configuration (E-M4M vertex) / tree node | physical identity = cells + moved set + achieved q + gripper + (2D planner-budget counters, 3D object qpos/qvel); the prefix order is NOT part of it | `phys.py` `RealPhys._ident` |
| Budgets | wall-clock limits per paper | CPU seconds of the whole process per run (planner + physics, `time.process_time`), default schedule 60 / 300 s (`config/grid.json`); per-call CPU cap 45 s (a capped call = UNKNOWN = planner failure for the search, never a label), reference-plan cap 120 s, administrative wall 4 x budget, optional call-count cap; exhausted -> ABSTAIN, termination TIMEOUT. Smaller budgets are read from the same run (`run.py cut`) | `phys.py` `_timed`, `gate` |
| Caches | positive / negative caches (E-M4M) | each (root, method, config, seed) run starts **cold** (no cross-run reuse); within a run: transitions by (physical key, action), terminal checks by physical key, Y by canonical endpoint (order independent) | `envs.load_root`, `phys.py` |
| Start step | — | every planner first plans the obstacle-ignorant target task (no plan in `planned`/`both` mode -> ABSTAIN) and checks the task in the initial scene (NOOP on success) | `common.py` `start` |
| Final verification | — | independent: sealed predictions -> `approach_b_final/benchmark.py` queries / teach (unchanged finalized teachers, separate process, separate cache) / evaluate. Never retried | `eval.sh` |
| Private data | — | planners receive public rows only; raw records reach the physics scrubbed of labels / roles / construction / teacher ledgers (2D `roles` keys rebuilt from public attrs, values neutralised) | `envs.py` `scrub`, `load_root` |

## E-M4M (`em4m.py`)

| Paper element | Here |
|---|---|
| gamma_OoI = PlanRetrieval(I) ignoring movables; NGR = V(gamma_OoI) | `ngr='min'`: the usable obstacle-ignorant path with fewest movable blockers in the initial scene (`t_paths` decides which paths compete); `ngr='union'`: union of all usable path sweeps (*ours*) |
| Done(v): NGR clear, else PlanRetrieval in v | `done_gate='always'`: the terminal check at every vertex, once (paper: plan when NGR not clear); `'screen'`: only when some path is already clear (paper's Line 5 shortcut, then still verified) |
| ExpandState: CBS over NGR objects with invalid goals kappa(v); push each moved object; failed push -> InvalidGoals(v); re-expand; close when MAPF fails / nothing new | same control flow; CBS replaced by its optimal **goal assignment** (exact Hungarian on 4-connected lattice distances around non-agent objects + negative-cache penalty) because pick-and-place does not follow grid paths; goals = legal ORIGINALLY-empty cells outside the NGR; each assigned object = one executed relocation from v's carried state; a valid goal is "hallucinated" invalid once no new invalid goal exists (legacy port behaviour) |
| Negative cache: nearest-neighbour invalid goals | goals within +-`box` (1) lattice cells of an invalid goal penalised (weight 5 per failure, 1 hallucinated, / ceil(distance), x 1000) — reference uses +-3 cells of 1 cm |
| Positive cache keyed by (O_m, pi_m) | exact transition cache keyed by (physical state, action) |
| Priority f(v) = P(E) P(phi1|E) P(phi2|E) prod P(phi3|E) | phi1 (beta, a = 0.3403, b = 45.075), phi2 (exponential, lambda = 1.5635), prior 0.3084 (fitted constants of the reference); **phi3 (mass x friction x volume) dropped**: kinematic 2D domain, 3D masses not public. Ties: more actions, more no-ops, seeded random |
| Vertex = configuration of movable objects | **physical state identity** (fix of legacy em4m2d.py:186-192): the same cells with different arm states are different vertices; an existing key = the same physical state reached by another order (safe transposition, dropped). `transposition='cells_legacy'` reproduces the defect for the regression test |
| Non-monotone (objects move repeatedly) | monotone: each object at most once, <= 3 moves |

## MO-SeGMan (`mosegman.py`)

| Reference (SeGManv2.py) | Here |
|---|---|
| sequence over goal objects (ATSP / Gurobi MTZ), adaptive sub-goals | single fixed target task: the sequence is [T]; sub-goals / refinement for T do not apply |
| find_critical_objects: blockers of the task path (clones every 3 path points); 1 -> it; 2..4 -> first subset (ascending size) for which `run_rrt` succeeds with the subset removed; > 4 -> the 4 nearest to the robot | identical decision rule, but subset feasibility = "some obstacle-ignorant plan's blockers in THIS scene lie within the subset" (several homotopies). **No RRT re-plan per subset** (cost: a failing 2D target query costs 45-70 CPU-s). Recomputed in every hypothetical scene (fix of legacy :122-139 which reused one gamma, making the test vacuous) |
| remove_obstacle: SGFS; on failure one more SGFS with the critical set of `all_objs - blocking_objs` | alternatives = the next minimal critical sets (other homotopies / linear path), up to `sgfs_attempts` (2) — the legacy `objects minus first set` could never succeed for 2-4 blockers (legacy :270-284) |
| SGFS: max_iter = |O_g| + 1, stuck limit max(2, |O_g|/4), select_node, goal check on a changed node, is_reachable, generate_new_nodes (3 kept) | max_iter = K_MAX + 1 = 4 (*ours*: 2 cannot reach K = 3); stuck limit 2; goal check = terminal (gated by `done_gate`); critical set of a node **refreshed after every executed move** (*ours*, fix); is_reachable = the linear picking path from the robot base is free (reference: `find_pick_path`) |
| node score = scene score + 5 / sqrt(visit + 1), visit starts at 1; secondary-obstacle rule (pixels x 200 x 0.6); weight update with score delta (floor 0.001) | same |
| scene image: camera image recoloured (obstacle 0, free 80, task path 200); reachability = BFS of a gripper-sized block (1.1 / 0.99); score = sum(img x reach) / (h w 10) | 1 cm raster of the public board (cell centres + public radii); task-path pixels = cells of the active path's sweep; BFS from the board point nearest the robot base |
| generate_reloc_pts: conv threshold 0.9 on the object's mask, EDT >= 75th percentile; k = min(max(ceil(3 %), amount), n), <= 20 tried, amount = int(w / sum w * 5 * ceil(sqrt(|crit|))) | candidates = legal ORIGINALLY-empty cells off the active path's sweep (the object fits any free cell), EDT >= 75th percentile over the candidate cells; same k / 20 / amount |
| collisions during relocation (`komo.info_sliceCollisions`) | objects on the linear segments base -> object and object -> destination of a failed relocation |

## MS-MCTS (`msmcts.py`)

| Paper | Here |
|---|---|
| multi-stage topology over goal objects | one stage (only T has a goal); object of interest o_k = T |
| Algorithm 2: O_b = objects blocking T's picking/placing paths; empty -> child placing T at its goal; accessible blocker -> Algorithm 1 regions; inaccessible -> objects on its picking path become the focus with it as dependency; halting condition; depth threshold without progress -> O_b = all feasible objects | same; T's paths default to the paper's **linear** picking/placing paths (`t_paths='linear'`); accessibility = linear picking path from the base is free; depth threshold `stuck_depth` = 2 (*ours*, not given) |
| Algorithm 1: Gaussian offsets around discretised regions (unit = object radius), sorted by distance, rejected on o_k's paths / dependency picking paths, accepted when MP(p_i) succeeds, stop at m | discrete buffer variant: legal ORIGINALLY-empty cells (never the goal cell) off T's path sweep and the dependencies' linear picking paths, nearest first, at most `max_tries` (4) executed relocations, stop at `m_regions` (2) successes (*ours*: m not given) |
| tuned UCB (citation, no constants) | UCB1-Tuned on rewards normalised to [0, 1] (failure = -`fail_r` = -4 m, *ours*) |
| rollout: random Algorithm-1 regions until o_k can reach its goal; reward = -accumulated displacement; backprop | same; **a rollout that reaches the objective with a verified terminal check is returned** (the paper halts when the objective is achieved; legacy :179 discarded the plan) |
| transpositions (not in the paper) | one node per physical state (transposition table); duplicate children merged |
| post-optimisation (merge consecutive same-object moves) | vacuous under move-once |

## 3D-specific notes

All three planners run unchanged in 3D through the same layer (RepairEnv 3D backend: xArm7 side grasps on the 6 x 6 confined shelf,
MuJoCo 3.16; NOR-Grid 3D reference paths). Known approximations: (i) the 3D sweep uses one generic column radius (median object
footprint) for hypothetical cells; exact hits are used only for objects still at their initial cell; (ii) the linear paths project the
robot base (0, 0) onto the shelf plane — the arm actually reaches over/around with side grasps, so linear blockers are a coarse proxy
(the executed transitions decide feasibility); (iii) object heights enter only through the reference planner's arm ceiling and the
physics. No 3D component is faked: every relocation and every success is a physical MuJoCo execution plus the finalized connector and Y.
