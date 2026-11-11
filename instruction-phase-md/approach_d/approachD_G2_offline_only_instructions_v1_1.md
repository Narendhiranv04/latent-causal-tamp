# Approach D — G1→G2 Migration Instructions v1.1
## Offline-compiled relative-motion retrieval; binary operational labels; zero inference-time IK and motion planning

**Status:** New authoritative amendment to `approachD_methodology.pdf` / `approachD_methodology.md` v1.0 for the next implementation phases. Where those older documents mention online IK, trajectory adaptation, motion planning, `UNKNOWN` labels, or online-planner fallback, **this document supersedes them**. It does **not** retroactively redefine P14–P17 experiments or edit historical records. Treat historical outputs and their labels as immutable.

**Repository:** `Narendhiranv04/latent-causal-tamp`. Continue the existing local, unpushed `approach-d-v1` branch from reported G1 commit `df913ae` (base `027fb7f`). Verify actual `HEAD`, working tree, test counts, report, and the claimed G1 APIs locally before editing. The assistant reviewing the user report could not access the unpushed commit remotely; reported G1 counts are provisional until verified on the working tree.

**Baseline reported by G1:** 502 historical tests and 6 archived replays; 513 tests and the same 6 replays after G1. Reported relative *pattern retrieval* results: 400/442 new-location queries have some candidate, 149/400 top-1 pattern match, 250/400 match with 3 modes × 2 witnesses, 284/400 with 6 modes × 1 witness, and candidate coverage 963/1032 vs legacy 548/1032. **None of these is a new-location executable-motion success rate.**

---

## 1. Immutable decisions — interpret literally

1. **ZERO inference-time IK.** No calls to `geometry.ik`, `motion.ik_track`, `motion.ik_line`, or an equivalent solver when performing Approach D inference. Do not smuggle IK into an adapter, callback, planner, fallback, verifier, or preparation function invoked during inference.
2. **ZERO inference-time motion/trajectory planning.** No `skill.plan_skill`, `planner.plan`, RRT, numerical trajectory optimizer, new grasp synthesis, online motion retargeting, online connector planning, or target-task planning. **This includes the original target T and every obstacle.** There is **no online-planner fallback** when a stored motion is missing or blocked. Offline preparation may use these tools.
3. **Allowed online operations:** frozen learned D forward pass for **original target T only**; deterministic database/index retrieval; finite discrete candidate selection and ordering; geometric occupancy tests; forward kinematics/geometry applied to a **stored, fixed joint trajectory**; continuous *collision verification of that existing trajectory* (not trajectory generation); hypothetical scene update; cache and audit logging. A finite discrete sequence selection is not a motion planner; keep it bounded and label it correctly.
4. **Only two training losses:** feasibility BCE and blocker negative log likelihood, with the historical `lambda_B=2` starting weight. **No** `L_updated`, learned destination/sequence/motion-feasibility head, learned motion-adaptation loss, or learned obstacle-as-target recursion. Additional original-target scenes may be training examples under these same two losses.
5. **All NEW offline task-outcome labels are binary:** `y=1` when an offline witness/teacher verifies target task completion; `y=0` otherwise, including when the offline planner runs out of attempts, time, nodes, or other declared budget. Do **not** create a third `UNKNOWN` label in the NEW operational dataset, and do not silently drop timeout examples. Preserve separate provenance fields `termination_reason`, budget, attempts, hardware, and `negative_kind` (`CERTIFIED`, `TIMEOUT`, `NO_PLAN_FOUND`, `OTHER_FAILURE`) as **metadata, not labels**. Never state that `y=0` from a timeout proves geometrical impossibility. A bounded operational label and universal physical feasibility are not the same thing.
6. **No `UNKNOWN` label at inference either.** An available, valid motion candidate is a success/accepted action; no valid precompiled candidate in the declared library and checker budget is a **framework failure**, with reason codes such as `NO_TEMPLATE`, `NO_COMPATIBLE_START`, `COLLISION_ALL_CHECKED`, `CHECK_BUDGET_EXHAUSTED`, or `EXECUTION_FAILURE`. These reason codes are not third truth labels; an operational binary success/failure may be reported separately. Never fabricate a causal blocker label from a missing motion template.
7. **D is only queried with original T, original goal g_T.** Query on each selected hypothetical updated scene with changed object occupancy and its **achieved stored terminal q**. Never rebind obstacle A/B/C as a new target in the new production arm. Preserve historical `Dp17`, `Dp17-norec`, and historical tests unchanged.
8. **Relative retrieval must work across absolute grid locations.** Local source/destination 3×3 and 4×4 patches and relative displacement retrieve an analogous motion *family*. A fixed-base 3R arm is **not translation invariant**. The runtime may only use motion records whose **actual precompiled absolute joint trajectory** matches the requested source/destination, robot/grasp configuration, and correct robot-start continuity. Never execute, certify as usable, or reconstruct a new robot trajectory by merely shifting a swept mask or a stored joint path at inference.
9. **The target task must not be declared achieved solely from a D probability or vanished blocker score.** A full frozen target motion must pass the current-scene geometric checker, and any physical execution failure counts as a method failure. Do not restart an online planner after an execution failure.
10. **Do not alter `config.toml` or historical labels.** New settings live in `approach_d.toml`; retain independent old-policy switches, fully versioned cache identities, archived fixtures, and reproduction paths.

### Scope of the word “planning”

At inference, the method can enumerate/choose a *finite sequence of already compiled actions* (e.g., move A to slot 20, then B to slot 24). This is high-level **selection** of a finite catalog, not generation of any new path/IK solution. If a candidate has no admissible precompiled trajectory, report a bounded framework failure for that candidate; no inference-time motion synthesis is permitted.

---

## 2. The only viable way to generalize relative motions without runtime IK

The G1 relative index is useful for **matching patterns**, but its cross-location retrieval is not proof of an executable motion. For a fixed-base arm, new absolute endpoints usually need different joint angles. Therefore add an **OFFLINE motion compiler** that takes relative-motion families and generates a finite catalog of usable, absolute-position 3R robot actions **before inference**.

### 2.1 Offline compilation, allowed operations

The offline data/compilation job MAY use IK, task-space path retargeting, robot motion planning, grasp enumeration, trajectory optimization, replay, and collision checking. It should:

- Generate destination proposals for every declared source cell and destination cell (or a clearly specified finite subset) on the 8×8 workspace, separated by object footprint and robot/grasp class. Prefer a generic static robot/workspace catalog with scene-independent geometry; prevent any held-out test-root scene from leaking into precomputation.
- Retrieve G1 relative displacement families and local 3×3/4×4 patterns as **seeds**; use supported robot symmetries where exact, then *offline* IK/retargeting/optimization as necessary. An exact base rotation is permitted only when one rotation maps both stored endpoints and the associated action frames consistently. Otherwise it is a general retargeting problem. Mirroring is experimental until gripper/tool symmetry is proven.
- Build a **complete** phase-labelled absolute joint-space witness: current canonical start (see §2.2), pregrasp, approach, grasp/attach, carry, release/place, retreat, and canonical terminal pose. Save `q[k]`, gap, phase, attachment, held offset, endpoints, travel, geometric swept bodies/cells per phase, and all compiler/provenance metadata.
- Validate every template in its offline compilation environment for exact endpoints, continuous joint-limit compliance, tool/object attachment consistency, no self collision, and expected terminal robot state. Store only validated templates in the deployable catalog; retain failed compilations with reason codes for coverage accounting.
- Store a position-aware **execution index** mapping the query's actual absolute source/destination and robot-start contract to precompiled feasible motion templates. G1's relative index ranks/selects matching local *patterns*; the execution index guarantees that the selected action already has an absolute-location joint trajectory. Do not conflate these indexes.
- Compile target T motions as well as obstacle motions, because original-target feasibility checking cannot invoke an online planner.

### 2.2 Required robot-state continuity contract

Every runtime action must start at the actual robot q and end at a known q. **The simplest recommended first implementation** is a canonical-home contract:

- Root initial q must be `q_home` (or an explicitly precompiled, verified entry action must exist); each compiled relocation and compiled target task starts at `q_home` and returns safely to `q_home`.
- A stored witness with a different starting q is not immediately admissible; it requires an **already precompiled** compatible connector, not runtime planning. Without such a connector, the candidate is a library-domain failure.
- The return-to-home trajectory is part of the witness and must be checked against the **actual** current scene. The fact that it was collision-free in an empty offline workspace is not sufficient.
- If future versions allow multiple start/end q values, precompile a **finite graph of configuration transitions** offline and select only existing connected edges at inference. No automatic online bridging.

This makes relative generalization genuinely feasible without silently relying on runtime IK/online transit RRT.

### 2.3 Fast online checks without online planning

For a new scene and requested move `A: src → dst`:

1. Reject occupied/forbidden destination cells, incompatible footprint/grasp, unsupported source/destination, or incompatible starting q.
2. Retrieve/rank *precompiled absolute-location* templates using the G1 relative/patch/mode information. Prioritize exact-location historical witnesses if a compatible full witness exists; then cross-location-family-derived **offline-compiled** absolute templates.
3. Check **the actual precompiled whole-arm swept geometry** (all links, gripper, carried object, approach, carry, release, retreat and return-to-home) against current objects. Local 3×3/4×4 patches are retrieval keys, **never** the complete collision test. A swept-cell prefilter may be conservative and reject extra motions; for candidates accepted as valid, call the existing deterministic continuous collision checker on the **frozen trajectory** if available, but never generate or alter that trajectory.
4. If a candidate is collision-free, select it and stop searching its destination unless a declared travel-quality comparison budget requires more. Do not check all stored duplicates after a valid answer.
5. If a candidate collides, try other precompiled modes/witnesses within the predeclared budget; then another destination. **No online planner, no IK, no runtime trajectory deformation.** If exhausted, record explicit failure, not physical impossibility.

**Check the precompiled target-T action using the same lookup and geometry contract.** Only a valid target template in the hypothetical updated scene can support a successful complete repair.

---

## 3. G1 retrieval corrections to carry into G2

- Preserve the exact `(src,dst)` legacy index and historical arm unchanged. It is the control baseline, not the only candidate key in the new approach.
- Keep G1's relative key `(Δrow,Δcol,footprint)` and patch descriptors; make robot-base-relative position and wrist/elbow class explicit rank/compatibility metadata.
- **Do not assign equal physical meaning to a matched local pattern and a realizable joint trajectory.** Report `pattern_retrieved`, `absolute_template_compiled`, `current_scene_verified`, and `target_verified` separately.
- Precompute canonical source/destination patch descriptors and motion-mode statistics. Avoid per-query linear scans of the original giant corpus; allow a bounded catalog of compiled witnesses and a mode-level index.
- G1 reported `3 modes × 2 witnesses` pattern recall 250/400 versus `6 modes × 1 witness` 284/400 at the same six-witness budget. Keep both and a small `K=1` baseline. Select a default **on DEV physical success/cost**, never based on held-out test outcomes. Prioritize diversity of compatible *absolute* templates over redundant local patterns.
- An exact-cell witness should precede adapted-family templates **when its start-q, gripper, and full-phase requirements match**. A nominal exact-cell hit with incompatible q must not outrank a fully compatible offline-compiled template.
- Version cache keys by policy, compiler/version, source/destination, robot q, scene fingerprint, object class, phase model, index hash, collision-check version, and relevant budget. Never share a cached accepted action between policies whose underlying witness sets differ.
- Keep root- and geometry-fingerprint leakage checks for every source witness, adapted template lineage, calibration datum, and comparison. A catalog compiled purely from generic robot geometry must be identified as such, not misreported as a held-out scene witness.

---

## 4. New binary operational-label protocol

### 4.1 One label for every offline task evaluation

For a fixed offline teacher/planning budget `B`, define:

`y_B(S,T,g_T,q)=1` **if and only if** an offline teacher produced and independently verified a valid action within the declared budget. Otherwise `y_B=0`, **including all planner timeouts, capped attempts, unavailable skill witnesses, and unsuccessful search**.

Do not use `UNKNOWN`, `None`, or missing outcome labels for such *completed offline evaluation attempts*. Never quietly drop the `y_B=0` timeout cases when creating the training set. Each row must retain separate metadata describing why it received 0. The classifier learns **operational success within budget B**, not a theorem about all possible robot motions. Ensure the paper and figure legends say this explicitly. Never present a timeout negative as a mathematically certified impossibility.

Sample record:

```json
{
  "label_protocol": "AD_BINARY_BUDGET_V1",
  "target_id": "t0",
  "label": 0,
  "negative_kind": "TIMEOUT",
  "termination_reason": "PLANNER_TIME_LIMIT",
  "teacher_budget_id": "B_fixed_1",
  "teacher_witness": null,
  "scene_root": "...",
  "scene_fingerprint": "..."
}
```

### 4.2 Counterfactual blocker teaching with binary outcomes

For the selected original target T, make offline scene interventions by relocating eligible objects to admissible cells, and evaluate T under the same binary `AD_BINARY_BUDGET_V1` teacher protocol. Train feasibility on both originals and eligible edited scenes via the same BCE loss. When a complete declared intervention lattice is available, derive inclusion-minimal `y_B=1` clearing sets and their union-participation mask (do **not** claim the union is a unique required repair). If one singleton A or B suffices, union `[1,1]` remains legitimate supervision but the runtime may stop after moving just A.

When `y_B(original)=0` but no successful edit is found, or the lattice is nonmonotone/does not support a meaningful union, **do not invent an all-zero causal mask**. Keep the binary feasibility `label=0`; set a separate `blocker_supervision_valid=false` metadata flag and exclude only that sample's blocker term from the loss. This flag is **not** an `UNKNOWN` task label. Maintain an auditable count of such records. With timeout-as-negative labels, explicitly monitor false negative contamination and run sensitivity analyses to offline teacher budget B; do not treat budget-dependent blocker sets as universal causal truth.

**Historical records:** P13–P17 `UNKNOWN_*`, `CERTIFIED_*`, archived replays, and old status semantics remain intact solely for reproducibility. Provide a named *new* dataset adapter/version. Do not overwrite or silently reinterpret earlier runs. Every new training example is explicitly versioned with the binary label protocol.

### 4.3 Exactly the original two losses

For `p_T = sigmoid(uθ(S,T,g_T,q))` and blocker distribution `Pθ(b | y_B=0,S,T)`:

`L_feas = BCE(p_T, y_B)`

`L_blocker = -log Pθ(b* | y_B=0,S,T)` when `y_B=0` and `blocker_supervision_valid=true`.

`L_D = mean[L_feas + λ_B × 1[valid blocker supervision] × L_blocker]`, with initial `λ_B=2` and pairless Dp17 as production. The paired quadratic variant stays historical ablation. No `L_updated`. Updated scenes are just more original-target input samples under the same loss. All D calls are original-target T only.

---

## 5. Runtime target-only Approach D

For the finite precompiled library and original target `(T,g_T)`:

1. Construct current `(scene S, robot q)`. Call the **same D model with T only**. Output `p_feasible` and conditional blocker marginals; prioritize objects using `(1-p_feasible)*marginal`. D is a *heuristic*, not the collision oracle.
2. Generate candidate obstacle destinations using existing scene-only grid rules, without IK/planning. Obstacle order is **not** learned by Boltzmann weights. Evaluate blocker-first, nearest-current-robot/end-effector, estimated catalog travel, and geometry-only order in ablations. Preserve bounded alternative orders; never assume the blocker union must be entirely relocated.
3. Use **only precompiled, absolute-location complete trajectories** retrieved/ranked through relative patch/motion-mode lookup. Reject invalid destinations, missing/mismatched q, or collisions; never call IK/planning. Select valid relocation and hypothetically apply its object placement and terminal robot q.
4. Re-query D with **same T** for each selected hypothetical scene. If the target remains infeasible under D, consider the next blocker or another destination/order. Do not insist D's `p_feasible` increase after every necessary intermediate move; some repairs require two objects.
5. Use **precompiled T action and current-scene collision checks** to verify a proposed terminal repair. No target online planner. A large D score is not a success criterion; a vanished blocker score alone is not a success criterion.
6. Stop at first fully accepted repair under a first-valid policy, or compare a finite number of accepted repairs by `(number of relocations, recorded joint travel)` if explicitly budgeted. Return explicit `SUCCESS` or `FAILURE_WITH_REASON`, plus verified witness hashes. Never claim minimum globally unless the *entire finite precompiled action graph* was enumerated within budget.
7. If actual execution (real or simulation) fails despite selection, record method failure; do not fix it by online replanning. Keep execution failure separate from offline teacher labels.

**Important G3 check:** Existing `Dp17-norec` already calls D on updated states for T only. A new arm is scientifically different only if its **finite compiled-motion backend, candidate selection, scoring, or compute allocation** differs demonstrably. Do not present target-only calls themselves as novel or duplicate the old policy with a new name.

---

## 6. G2 gate redesign and required ablations

### G2a — Baseline, compiler design, and small OFFLINE pilot

- Locally inspect the reported G1 commit, audit/report, 11 tests, `approach_d.toml`, index changes, leakage checks, and visualizations; independently rerun 513 tests + 6 archived replays. If absent or different, report truth and stop before dependent changes.
- Inventory every function reachable from the **new inference entry point** that can invoke any IK, motion planner, online connector, online grasp synthesis, or replanner (including indirect calls to `provider.goal/edges` and historical `p16_motion.DetPhysics`). Build deny-by-default dependency/call-graph tests.
- Design the compiled absolute-motion schema and canonical-q contract. No motion adaptation at inference.
- Implement **offline compiler only** and pilot a small fixed assortment of 8×8 cell pairs, including pure base-rotation-compatible and genuinely shifted/non-symmetric pairs; multiple grasp/elbow branches; full-phase return-to-home; collisions; unreachable pairs. Use existing `geometry.ik` and `motion.ik_track` or `skill.plan_skill` **offline**, and existing continuous certifiers for the compiled full trajectories. Preserve lineage from the relative G1 pattern.
- Visualize at least four cases: exact-cell witness, nontrivial shifted transfer after offline compilation, end-effector-similar but whole-arm collision, and unreachable/no compiled template. Display stored q path/robot links and resulting actual absolute swept volumes, not shifted cartoon sweeps.
- Compare offline compiled coverage under relative templates vs direct offline baseline; record compiler CPU/time separately from inference. A valid physical transfer is not established until the *new-location* compiled action replays in a held-out scene or controlled independent fixture.
- Stop after G2a pilot and report the gate; do not run the 442-query sealed benchmark or launch large offline compilation without explicit budget authorization.

### G2b — Runtime lookup integration, only after G2a passes

- Introduce a new opt-in `AD_PRECOMPILED` motion provider. It may fetch templates, check exact q continuity, assess precomputed sweeps, and certify **frozen** path geometry. It must not invoke any runtime solver. Cache identities isolate all modes and compilation versions.
- Try compatible exact-cell precompiled witnesses, then relative-family-derived absolute compiled witnesses, all within the same lookup/check budget. No online planner fallback, ever.
- Add a **runtime guard test that monkeypatches all known IK/planner/grasp-synthesis entry points to throw**, then exercises multi-action retrieval, failed witness, alternative destination, target-check, and execution failure paths. Zero forbidden calls, including indirect paths, is a hard PASS requirement.
- Test home/q contract, swept-volume midpath collisions, carried disc, finger/grasp phases, static destination, pair compatibility, object-radius mismatch, phase-replay consistency, clipped budgets, and absence of cached cross-policy contamination.

### G2c — Frozen matched physical transfer benchmark

- **Only after dev tuning and freezing** retrieval K and compiler policy, evaluate on the same G1 held-out 442 queries (or a precisely justified feasible subset with unchanged cohort labels). Use scene-root and geometry-fingerprint leakage isolation.
- Compare: (i) exact-cell precompiled lookup; (ii) relative-pattern-selected offline-compiled absolute lookup; (iii) fixed frozen-catalog baseline without relative ranking; plus two K=6 diversity policies (3×2 vs 6×1) and K=1 where available. No condition may call runtime motion planning/IK.
- Measure: compiled absolute coverage, physical replay success on a new location, valid-path success@K, failure reasons, mean checker calls, time, full-motion cost, precomputation cost, q continuity, and result concordance. Report *pattern recall* separately; it is not a physical success metric.
- Cluster inferential uncertainty by root; do not pretend many actions from one root are independent. Report failures, not only successes. Do not tune after unsealing the held-out results.

### G3–G5 (subsequent, not G2a scope)

- **G3 target-only iterative D:** a new arm using the precompiled provider and repeated D(T) on proposed updated scenes; compare with existing `Dp17-norec` on same provider. No calls `D(A)` / `D(B)`.
- **G4 binary-label learning:** add a separately versioned operational binary dataset adapter, train Dp17 with precisely `L_feas + λ_B L_blocker`, audit timeout-derived negatives, held-out original/post-edit predictions, model seeds, calibration, and sensitivity to teacher budget.
- **G5 scientific comparison:** learned D vs geometric-only and proximity/minimum-travel order with exactly the same finite precompiled-motion library and budgets; ablate D re-query, paired vs pairless, relative ranking, shortlist diversity, and binary-label data effect. Distinguish lookup gains from learned-causal gains.

---

## 7. Mandatory tests, instrumentation, and safety of scientific claims

### Tests

- **Forbidden-call tests:** patch `geometry.ik`, `motion.ik_track`, `motion.ik_line`, `skill.plan_skill`, `planner.plan`, and every discovered equivalent to throw if reached from the new runtime. Include hidden transits, goal checks, fallbacks, `provider.edges/goal`, and executor recovery. Existing old-arm invocations remain permitted **only when not executing the new production mode**.
- **Binary-label tests:** 1 for independently verified offline success; 0 for teacher timeout, attempts cap, node cap, no plan; no third labels. `negative_kind` provenance retained. No hidden filtering of timeout negatives. No fabricated zero blocker mask when no sufficient intervention is found.
- **Motion/kinematics tests:** same relative displacement at different grid cells retrieves a *pattern*, but cannot be accepted without an actual precompiled absolute valid action; invalid q-start fails; exact rotation transformation must satisfy source **and** destination constraints; general offline retarget requires offline IK/solver; no runtime shifted swept mask accepted; full arm/gripper/held object/retreat collisions checked against current occupancy.
- **Search tests:** different destinations, several candidate witnesses, 3×2 and 6×1 policies, no unnecessary traversal after first accepted motion, alternative blocker order, finite state cache, absent template gives bounded failure; original T fixed across all model calls; hypothetically updated q and occupancy reflected in D input.
- **Regression:** 513 reported tests and 6 historical replays, no changed historical baseline; G1 counters/figures preserved; `config.toml` unchanged.

### Required result fields

`root_id`, `split`, `scene_fingerprint`, `label_protocol`, `teacher_budget`, `y_binary`, `negative_kind`, `blocker_supervision_valid`, `index_version`, `compiler_version`, `runtime_policy`, `source_cell`, `dest_cell`, `delta`, `local_patch_similarity`, `robot_relative_compatibility`, `original_witness_provenance`, `compiled_template_id`, `template_q_start`, `template_q_end`, `mode`, `sweep_hash`, `collision_status`, `full_phase_check`, `retrieval_rank`, `runtime_ik_calls=0`, `runtime_planner_calls=0`, `D_target_id='t0'`, `final_status`, `failure_reason`, `calls_by_type`, `offline_compiler_cost`, and `online_inference_cost`.

### Claims discipline

- New `y=0` from an offline teacher timeout = **operational negative under fixed budget**, not proven impossibility.
- No template / no accepted motion online = **finite-library failure**, not proof no feasible physical path exists.
- Relative patch match = **retrieval success**, not proof same 3R joint motion works.
- Offline adapted and fully checked absolute motion = **compiled motion candidate**; new-scene full-phase check = **valid under tested geometry**; execution may still fail and is counted.
- Improved library coverage cannot be claimed as a learned Boltzmann improvement unless the shared-backend learned-vs-geometry comparison proves it.

---

## 8. Minimal files and versioning

Prefer opt-in additions around existing `p14_sweep_index.py`, `p15_lookup.py`, `p17_domain.py`, and a lean offline compiler plus compact new motion provider. The current `p16_motion.py` invokes online planning; **do not reuse it unguarded in the new inference path**. Reuse its **pure trajectory checking / replay primitives** where they have no hidden planner call. `p17_d.py` may retain historical recursion; new D policy must disable it, target-only. Keep each module short and avoid a new deep folder hierarchy; reports in `responses-phases/`, figures in `visualizations/approach_d/`, opt-in config in `approach_d.toml`.

Preserve base branch and prior `df913ae` local G1 commit. Use commits with individually testable changes and exact commit hashes. Do not push or merge unless explicitly authorized. If an existing requirement is mathematically impossible without runtime motion synthesis and no offline precompiled action covers it, **fail closed and report reduced coverage**; do not secretly invoke IK or planning.

## 9. Immediate instruction for the next coding session

**Implement G2a only**: verify G1 locally; audit all runtime solver entry points; design and implement the OFFLINE compiled absolute-motion catalog; run a modest controllable physical pilot and visuals; run all unit tests and six replays; write a concrete G2a gate report. In that report, explain which G1 matches yield actual compiled executable actions and which fail due to robot geometry. Stop before G2b integration or the 442-query held-out benchmark; request explicit permission before high-cost dataset compilation. This sequencing makes the next phase scientifically interpretable and keeps the zero-runtime-IK / zero-runtime-planning rule enforceable.
