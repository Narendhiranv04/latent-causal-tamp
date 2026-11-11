# Approach D — G2b Implementation Instructions v1.2
## Solver-free precompiled-motion provider, finite robot-state connections, and controlled multi-action tests

**Status:** Authoritative **G2b-only** amendment to `approachD_G2_offline_only_instructions_v1_1.md`. Read v1.1 first; where a G2a assumption conflicts with observed G2a evidence, these G2b instructions refine it. The foundational Approach D methodology and **all P13–P17 historical outputs** remain unchanged. **Do not begin G2c or G3–G5 under this authorization.**

**Repository:** `Narendhiranv04/latent-causal-tamp`, local branch `approach-d-v1`. Reported chain: `main` at `027fb7f` → G1 `df913ae` → G2a `4b8aa2c`. **Verify this from local Git; the branch and commit have not been pushed, so external GitHub review cannot establish their contents.** The reported G2a implementation includes `ad_compile.py`, `ad_runtime.py`, `approach_d.toml`, `tests/test_approach_d_g2a.py`, and `responses-phases/0101_AD_G2a_OFFLINE_COMPILER_AND_ZERO_RUNTIME_SOLVER_CONTRACT.md`. Read their *actual* contents.

**Reported baseline:** 525 tests pass, six historical replays pass. G2a pilot: 36 development relocation queries from 25 roots, 1,145 tested templates, and zero observed runtime IK/planner calls. With six templates: relative 6×1 verifies 15/36; relative 3×2 14/36; unseeded spread-over-branches 5/36; any compiled template 19/36. Among 752 rejected templates, 228 reportedly failed exclusively on home legs. The fast swept-cell prefilter rejected four otherwise valid paths. An apparently obstructed target was reachable after an entry action without any obstacle relocation. These are **reported, unverified locally by the author of this instruction**; reconfirm all counts from code and saved results.

---

## 1. Absolute invariants — non-negotiable

1. **Zero inference-time IK or robot trajectory synthesis, anywhere.** Forbidden calls include `geometry.ik`, `motion.ik_track`, `motion.ik_line`, `skill.plan_skill`, `planner.plan`, any RRT, trajectory optimizer, connector synthesizer, new grasp generation, obstacle-as-temporary-target planner, or equivalents. Applies to obstacles, the **original target T**, approach, retreat, transit, fallback, recovery, replay, and visualization triggered by runtime. **No online planner fallback.**
2. **Offline-only preparation may use IK and planning.** Every deployment action, including connector, target pick/place, and any transition between configurations, must have actual *precomputed absolute joint waypoints* and complete phase/attachment metadata. Merely matching local patches or translating a sweep is insufficient.
3. **Allowed at inference:** database/index lookup; deterministic finite ordering or high-level sequence search over already compiled actions; occupied-cell checks; forward kinematics; swept-body/whole-arm collision checks of frozen paths; exact current robot-configuration continuity; D(T) inference; hypothetical occupancy and joint-state updates; logging. A collision checker that happens to call an IK solver internally is forbidden and must be replaced or bypassed.
4. **New operational outcomes are binary** (`SUCCESS`/`FAILURE` for the finite runtime; offline teacher label `y_B∈{0,1}`). A failed template search, timeout, absent template, or collision is `FAILURE` with a **reason field**, never a third `UNKNOWN` **label**. Preserve historical P13–P17 status strings in their legacy paths, untouched. No failed lookup constitutes a theorem of global geometric infeasibility.
5. **Training is not G2b's task.** Dp17 remains pairless. Only `L_feas + λ_B L_blocker` (initial λ_B=2) is allowed in the subsequent learning phase, no `L_updated` or extra motion-related loss. Do not retrain D or relabel datasets in G2b.
6. **D queries the original target T only**, in original or hypothetical rearranged scenes. No `D(A)` or `D(B)`. Existing `Dp17-norec` already supports target-only re-querying; don't claim that feature is new.
7. **Preserve historical code and experiments.** Do not edit `config.toml`, P13–P17 archived labels, six replays, existing result reports, or baseline arms. All new flags go in `approach_d.toml`. Opt-in only, no silent defaults. Do not push/merge, build a board-wide catalog, or unseal 442 held-out queries.
8. **Separate evidence stages:** local relative-pattern match → offline compiled absolute trajectory → current-scene full-phase geometric verification → complete multi-action plan verification → optional simulation/physical execution. Never call the first two stages "executed" or confuse them with the latter stages.

---

## 2. Exactly what G2b must achieve

G2a checked individual, mostly **home-to-home** compiled relocations. G2b must show that the new runtime can chain **multiple precompiled actions** with correct object placements and robot joint states *without ever generating a trajectory at inference*.

Minimal intended demonstration:

```text
Input: S0 (objects, robot q0, original target T, target goal)
   ↓
Choose precompiled relocation of A:  (cells0, q0) → (cells1, q1)
   ↓  check stored full-phase trajectory in S0
Choose precompiled relocation of B:  (cells1, q1) → (cells2, q2)
   ↓  check stored full-phase trajectory in S1
Check precompiled original target-T action: (cells2, q2) → goal
   ↓
SUCCESS only if complete concatenated sequence is accepted;
otherwise FAILURE + reason + exact attempted template IDs
```

The G2b provider serves this interface for future D-guided search; **G2b does not train or introduce a new D ordering policy**. For focused demonstrations, use deterministic/geometric mover order or a frozen preexisting guide, without introducing new scientific claims about D.

---

## 3. Robot-state graph and elimination of artificial home dependence

### 3.1 Scope the permitted robot configurations

A trajectory's starting and terminal joint states matter as much as the object's source and destination. Define a **small finite set** of canonical/recorded robot configurations from development data and the existing G2a catalog (for example `q_home`, representative certified post-retreat poses, and a few documented entry poses). Do not instantiate every possible pair of robot configurations.

Every graph node is an **exact joint-configuration identity or a precisely defined, validated tolerance cluster**, with joint limits, gripper-open/free attachment state, and provenance. Clustering must not "snap" an actual pose to another one without a stored certified transition. Include a reproducible hash/ID and a small numeric matching tolerance solely for floating-point equality of *the same* intended state; no interpolation between unmatched configurations.

Every graph edge is either:
- A complete precompiled **object relocation**, including approach → grasp → carry → release → safe retreat; home return is optional if safe retreat is complete.
- A complete precompiled **free-arm connector** between permitted configurations (open gripper, object not held), with frozen joint waypoints.
- A precompiled action for the **original target T**.

A source/terminal q mismatch is solved **only** by finding a stored compatible connector, never by a fresh direct segment, IK, RRT, or trajectory repair. If no compatible connector is available, fail that candidate with `NO_COMPATIBLE_CONNECTOR`.

### 3.2 Offline compilation, not shortcutting

- First **diagnose**, by root and template phase, why 228 of the 752 G2a rejections were home-leg-only. Distinguish entry-home from return-home, and count unique queries that become solvable, not merely templates.
- When the existing phase schedule permits, **offline** cut or separate a redundant home-return segment only *after release and verified safe retreat*, preserving correct scene context, q_end, object placement, attachment flags, and connector semantics. The shorter action must pass its own full trajectory consistency and collision checks; never just discard recorded phases at runtime.
- For a small development-only graph, compile necessary nonhome→nonhome actions/connectors **offline**, using existing algorithms if needed. Record what originated as a teacher witness, a relabelled segmentation of a valid witness, or newly compiled motion. Preserve all ancestry and reject train/test-root leakage.
- Avoid quadratic catalog explosion: only a documented handful of useful q states and links, with explicit coverage/memory/CPU accounting. Do not generate complete board × board × configuration-graph combinations.
- Use one object radius/grasp family initially, as in G2a; do not claim generality to unseen sizes/grippers.

### 3.3 Required full-phase acceptance

For every selected action and connector:
- Exact absolute source/destination, geometry and object-size compatibility.
- Precompiled q_start must match current robot q or be reached through a **stored verified connector**.
- All joint waypoints within limits; no unrecorded interpolation or angle-wrapping shortcut.
- Phase schedule, gap, attached flag, grasp/held-local offset, pick and placement consistency (`motion.check_record` or audited equivalent); complete safe retreat after release.
- Full-arm, gripper, held-object, stationary-object, and self-collision checks for the **entire stored trajectory** in the actual current scene. 3×3/4×4 patches are used for ranking, never as the complete collision check.
- Correct update to object occupancy and q_end, with the gripper open/free before the next action.
- Complete sequence replay without a hidden planner or IK in any replay/checking function.

No successful goal check may use a newly planned T trajectory. The target action must be precompiled as well.

---

## 4. New opt-in precompiled provider

### 4.1 Integrate safely

Implement a lean, explicit `AD_PRECOMPILED` provider using G2a's `ad_runtime.py` and `ad_compile.py`. Do **not** subclass or call historical `p16_motion.DetPhysics` methods that can invoke planners/IK. Reuse only **audited pure** geometric checks and immutable state/record manipulation.

An acceptable minimal interface is:

```python
provider.edges(cells, current_q, obstacle_id, destination_cell)
    -> admissible already-compiled action records plus FAILURE reason data
provider.goal(cells, current_q)
    -> verified original-target-T frozen action or FAILURE reason data
provider.verify_plan(ordered_stored_actions, initial_scene, initial_q)
    -> binary SUCCESS/FAILURE, reasons, witness hashes, updated states
provider.stats() -> counts, CPU, hashes, budget, source tiers
```

Exact return type may differ; match the existing code and keep it small. **Do not silently reuse P17's `CERTIFIED_INFEASIBLE` semantics** for `NO_TEMPLATE` and do not claim finite-catalog failures prove physical impossibility. If adapting `p17_search.py`, inspect its handling of `DECIDED`, `all_decided`, minimum-moves proof flags and statuses. A separate thin finite-catalog search adapter may be cleaner. Its optimum claims can apply only to a fully enumerated **declared finite precompiled graph**, never arbitrary continuous robot motions.

### 4.2 Retrieval and ordering tiers

For a candidate relocation, select among **compatible compiled absolute trajectories** in this order:

1. Exact-cell-origin stored/compiled templates with a compatible starting configuration (or a **precompiled** allowed connector), full-phase witness, and correct object size.
2. Offline-compiled absolute templates derived from G1 relative families, ranked by local source/destination patches, relative Δ, robot-relative compatibility, motion-mode diversity, and development-calibrated cost.
3. **No third online-planning tier.** If no acceptable template is found under the declared budget, return binary failure and reason.

`3 modes × 2 witnesses` versus `6 modes × 1 witness` must remain configurable. The G2a physical pilot reported 14/36 versus 15/36; this does not support freezing a universal winner. Include `K=1` as a diagnostic. Hold the number of **actual continuous certifications** equal when comparing policies. Exact-witness ranking should not trump an incompatible q_start. Avoid needless checking of duplicates after a valid move under a first-valid policy.

### 4.3 Failure-reason contract

All new **task and runtime outcomes remain binary**. Store granular reasons separately, e.g. `NO_TEMPLATE`, `NO_COMPATIBLE_Q`, `NO_COMPATIBLE_CONNECTOR`, `DESTINATION_OCCUPIED`, `PHASE_INCONSISTENT`, `ATTACHMENT_INVALID`, `SWEEP_PREFILTER_REJECT`, `COLLISION_CURRENT_SCENE`, `CHECK_BUDGET_EXHAUSTED`, `TARGET_TEMPLATE_UNAVAILABLE`, `TARGET_ACTION_COLLISION`, `SEQUENCE_DISCONTINUITY`, `EXECUTION_FAILURE` (if simulated or physical execution is actually used). Distinguish **attempted candidate failure** from **overall repair failure**. Reasons do not create a third truth label.

### 4.4 Cache and reproducibility

Cache records must discriminate: compiler/catalog/index hash, retrieval policy and K, source/destination, relative descriptor, object/grasp/footprint class, scene occupancy/fingerprint, current exact q or canonical ID, checker and phase version, allowed connectors, robot config hash, time/call budget, and template ID. Never cache a valid action across changed occupancy or changed q; do not share caches between arms if the witness sets/check budgets differ. Keep the original `config.toml` byte-for-byte unchanged.

---

## 5. Swept-cell prefilter — test rather than assume

The reported G2a conservative swept-cell prefilter rejected **four** paths that the exact checker would have accepted, affecting three policy-level successes. This is a *false rejection*, not evidence of an unsafe false acceptance. At K=6 it can be costly.

Use exactly the same shortlisted compiled templates to compare:

- **OFF:** every candidate goes straight to the full continuous certifier.
- **ADVISORY:** record prefilter hits but do not reject; full certifier decides.
- **HARD:** prefilter may reject before continuous checking, measured against the latter's verdict when auditing.

Record both types of disagreement and actual checker/CPU savings, including examples outside 3×3/4×4 patches. For G2b's initial production-default candidate, prefer **OFF or ADVISORY** until the DEV analysis justifies a hard filter. Never treat a prefilter pass as a substitute for continuous full-phase verification.

---

## 6. Investigate the anomalous original target root

In G2a, one root labelled as initially obstructed apparently allowed a target-T action without any obstacle relocation, after a permitted entry motion to home. This must not be ignored.

For that **exact** root, write a reproducible paired trace:

- Original scene and original `q_initial`; original declared target goal and original offline teacher-budget label/termination.
- The precompiled entry connector, its full q path, and resulting `q_after_entry`.
- Target-T check at **original q_initial** versus target-T check **after the entry connector**, both with the same scene occupancy, action class, and verification contract.
- Whether the target became reachable only because q changed; whether the original `y=0` was timeout-derived; whether the target validation accepted a genuinely different action mode; whether there is an actual data/record or checker bug.
- A simple regression fixture and a truthful conclusion.

Do not relabel historical data; do not turn a teacher timeout into a proof of impossibility. If q changes without relocating an obstacle, the two task queries are **not identical**. No positive result on the changed-q condition should be silently counted as clearing an object-caused infeasibility.

---

## 7. Controlled development experiment — no sealed evaluation

Use the **same 36 pilot relocation moves / 25 development roots** where practical (or document precisely why a root cannot be reconstructed), plus a small, fixed set of complete repair-chain fixtures. Every compared policy must use the **same frozen compiled-template universe**, same robot constraints, checker, current-scene input, maximum checked templates, and identical budget accounting. This avoids confusing *better offline template generation* with *better retrieval policy*.

Compare:

1. Exact-cell compatible templates only.
2. Exact-cell then relative templates, 3×2.
3. Exact-cell then relative templates, 6×1.
4. Fixed-catalog robot-geometry-only ranking (no 3×3/4×4 similarity).
5. Fixed-catalog deterministic/random ranking with fixed seed.
6. The reported G2a unseeded policy as an additional compilation-generation comparator, clearly marked as **not the same template universe** unless rebuilt into a shared union catalog.

Add prefilter OFF/ADVISORY/HARD ablations on the **same policy candidates**. Do not compare 11/23 exact-cell success directly with 15/36 relative success; report the paired shared-root or shared-query results and exact-cell availability separately.

Metrics: successful verified relocation queries / fixed denominator; *distinct query* rescue from relaxing home-only; complete multi-action repairs / fixed denominator; target checks at original and changed q; success@K; first accepted retrieval rank; template/connector provenance and count; number of genuinely new-to-location adapted successes; collision reasons; exact checker calls; CPU; offline compiler CPU and storage; runtime forbidden-call count (must equal zero); terminal-q continuity; any invalid cache reuse; root-clustered paired uncertainty where meaningful. Identify all failure reasons, not only successful cases.

**Compute limit for this session:** reuse G2a assets. At most **120 new offline compile attempts or 25 CPU-minutes**, whichever is hit first, unless a lower local budget is already frozen. Stay on the 36 development moves and up to **12 handpicked chain fixtures**. Do not build 34×33 full-board pairs, train D, or run the held-out 442-query experiment. If these limits prevent a demonstration, report `PARTIAL/BLOCKED`, not a manufactured PASS. Keep existing curated fixtures fixed before comparing policies; do not tune on the held-out cohort.

---

## 8. Essential tests and explicit G2b gate

### Tests (include real saved-record checks, not only mocks)

- **Zero solver calls end-to-end:** patch `geometry.ik`, any locally imported aliases, `motion.ik_track`, `motion.ik_line`, `skill.plan_skill`, `planner.plan`, online connectors/other discovered generator entrypoints to raise; exercise successful A→B→T chain, failed A candidate → alternative slot/mode, failed connector, target `goal()`, full replay, cache hit/miss, and an execution-failure path if such an executor exists. Static call-graph scan plus runtime tripwires; compare invocation counters. The goal path must not call the historical IK-dependent `p15_retarget.certified`.
- **Start/end configuration identity:** exact q continuity, no implicit snap or new straight-line transit, independent safe-retreat requirement, legal stored connectors, insufficient graph coverage causing failure.
- **Trajectory integrity:** `q`, gripper gap, phases, attachment flags and carried object checks; static and mid-path whole-arm collisions; current occupancy changes; no mutation of frozen trajectory data; final target is T.
- **Swept prefilter discrepancy:** all four reported G2a false rejections reproduced or an explained numerical difference; record OFF/ADVISORY/HARD outcomes and cost.
- **Target anomaly:** original q vs changed q controlled comparison, with metadata and fixed regression.
- **Binary outcome and semantics:** timeout of an **offline teacher** maps to `y_B=0` when dataset generation is in scope; new runtime returns `SUCCESS`/`FAILURE`, never third label; legacy statuses untouched; failures have reason metadata. No synthetic all-zero blocker mask when a teacher intervention has no supported clearing set.
- **Isolation:** `config.toml` unchanged, old arms unchanged, cache keys include q, occupancy and policy; G1 and G2a tests still pass; all six historical replays pass.

### PASS requires all of:

1. All old + new tests pass; six archived replays unchanged; G2a baseline metrics reproducible or discrepancies documented and resolved.
2. **Zero IK, trajectory planning or online-generated connectors during any new runtime path**, including original target-T check and complete multi-action replay; guard tests genuinely trip on an injected forbidden call.
3. At least **one genuinely multi-relocation A→B→T chain** (or comparable two-obstacle chain) accepted from actual compiled frozen records, with exact q state continuity and complete checked phases. Also at least one controlled failed chain with correctly isolated cause. If a chain cannot be obtained under the small offline budget, G2b is `PARTIAL/BLOCKED`, not `PASS`.
4. Demonstrated support for a nonhome post-retreat state or a precompiled connector graph, with explicit q identities and no unrecorded online transitions.
5. Current-scene continuous checking is decisive; prefilter false-rejection consequences measured.
6. Original-T anomaly resolved or explicitly classified with a reproducible test and a named, scoped unresolved blocker; no silent label mutation.
7. Shared-catalog paired development comparison, exact denominators, provenance and cost accounting, no premature statistical or real-robot claims.
8. Catalog schema hashes, policy switches, failure reasons, and cache isolation tested.

### Reporting and artifacts

Write `responses-phases/0102_AD_G2b_SOLVER_FREE_PROVIDER_AND_SEQUENTIAL_REARRANGEMENT.md` with: branch/commit provenance; exact files diffed; test/replay commands and counts; forbidden-call audit and counts; finite-q graph specification; actual compiler template/connector counts and offline cost; before/after home-only rescue **by distinct query**; paired policy results on common denominators; failure taxonomy; prefilter ablation and G2a discrepancy; anomalous target root trace; success/failure end-to-end chain visualizations showing full robot links and q states; cache/version hashes; limitations; and an explicit `PASS`, `PARTIAL`, or `BLOCKED` decision. Visual assets in `visualizations/approach_d/g2b/`.

Commit tested G2b changes on the same **local** `approach-d-v1` branch if gate conditions are met. No push, merge, broad refactor, training, full catalog build, or 442-query unsealing. Stop and ask for authorization before G2c.

---

## 9. What G2b is NOT meant to prove

- It does **not** prove a general movement is geometrically impossible when no compiled witness exists.
- It does **not** prove cross-location transfer works for all unseen grippers, object sizes, or 3D arms.
- It does **not** prove that the Boltzmann model identifies better blockers than geometry (that is a later matched G3–G5 comparison).
- It does **not** authorize model retraining or changes to the original pairless energy/losses.
- It does **not** establish simulation or real-robot execution from a geometric checker alone.

**Scientific boundary:** G2b should prove that a *finite, precompiled, relative-retrieval-assisted motion library can support actual multi-action candidate repair sequences without any inference-time motion synthesis*. Claims beyond this boundary must wait for subsequent gates.
