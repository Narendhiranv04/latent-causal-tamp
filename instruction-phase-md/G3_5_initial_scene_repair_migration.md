# G3.5 — Initial-scene repair: objective migration and case analysis

**Instruction version:** 1.0, 16 October 2026  
**Next report:** `0007_G3_5_completion.md`  
**Normative references:** Methodology Specification v1.5; Implementation and Experimental Guide v1.7  
**Previous completed stage:** G3, as described in report 0006  
**Authorized scope of this instruction:** implement and validate G3.5 only. Do not start G4 dataset scaling or G5 training.

## 1. Read this decision before touching code

The research objective has changed. The primary learned framework will use the **initial scene, object information, robot state and intended action/goal** to propose **which obstacle objects to move and their destinations**. It receives **no target trajectory, swept-volume input, target-planner result or oracle blocker labels**.

External components still perform IK, determine an executable relocation order, plan collision-checked obstacle movements and evaluate the target action. The primary protocol does not invoke the target planner before selecting the repair or between obstacle relocations. Once the complete repair is committed and executed, a separate evaluator plans the complete target action from the achieved state. Its outcome cannot trigger another proposal within the same primary episode.

This is **initial-scene one-shot high-level repair**, not a low-level open-loop controller. Reobservation can validate execution assumptions and trigger abort. Low-level replanning to the same committed destination is allowed if logged and budgeted. Replacing object selections or destinations based on later observations is a different method and is out of this stage's primary scope.

**Swept geometry is not forbidden inside collision checking or offline diagnostic construction. It is excluded from the primary learned input and no longer defines the primary success label.**

## 2. Sources and authority

Read these before implementation:

1. Repository `AGENTS.md` or equivalent instructions and current working-tree status.
2. Methodology Specification v1.5 and Implementation Guide v1.7 in full.
3. Reports 0001–0006 and the previous G2-review/G3 instruction file, especially actual robot/profile, contact and verification decisions.
4. Relevant current source: configuration, scene/geometry, motion/skills, intervention construction, assignment solving, repair verification, replay and visualization.
5. Existing tests and archived manifests for the G3 fixtures you intend to reuse.

The revised specification defines the new scientific semantics. The guide defines stage order and implementation scope. Existing repository instructions govern code/worktree operations. Older frozen-motion instructions remain authoritative only for preserving and replaying `FROZEN_CONTROL`; they must not force a reference trajectory into the new primary query.

Do not assume code paths or file names in this instruction exist exactly as written. Inspect and adapt minimally. Do not claim this document's author independently audited the repository: the revision was based on the supplied PDFs and completion report.

## 3. Preserve G0–G3 and establish a baseline

- Record branch, commit, dirty files and applicable repository synchronization requirements. Preserve unrelated user work.
- Record the current robot profile/configuration and key archive hashes. Keep G0–G3 run files byte-unchanged.
- Retain the existing frozen-motion solver/replay entry points. Do not rewrite report 0006 or relabel its minimum certificates.
- The G3 report describes 74 tests, a 48-candidate grasp family, a full layered 3R body, and fixed-motion minima. Verify the actual source; do not silently restore old provisional 64-grasp or home-pose settings.
- Do not overwrite the tested robot profile with numeric examples from earlier PDFs. Explain any real discrepancy between report and repository.
- Use `runs/g3_5_initial_scene/` or one equivalent new flat run directory. Do not regenerate earlier figures in place.

The new stage can reuse geometry, IK, full-body collision checking, skill planning, static matching utilities, order search, history tracking and visualization. It changes their composition and the meaning of success.

## 4. Implement explicit protocol separation

Introduce a validated protocol field:

- `FROZEN_CONTROL`: unchanged target trajectory, legacy envelope labels, connector to pinned target start and same-path replay.
- `INITIAL_SCENE_ONE_SHOT_V1`: no required reference trajectory, goal-conditioned repair, no pre-commit target feedback, achieved-state target evaluation after repair.

Keep legacy archive loading compatible with its original semantics. Do not use a single ambiguous boolean such as `replan=true` to define the entire scientific protocol.

### Required component separation

1. **Static endpoint checker:** checks support, fixed workspace, target-at-rest occupancy, distinct object occupancy and pair collisions. It does not test clearance of a frozen target sweep in the new mode.
2. **Proposal provider:** returns a fixed list/ranking of endpoint assignments from initial allowed inputs. For G3.5 use explicit manually authored candidates or deterministic geometry-based candidates. No model training is required.
3. **Relocation planner/verifier:** searches order, grasps and full robot movements realizing an assignment. Every step starts at the previous achieved state. It cannot invoke the target evaluator.
4. **Commitment boundary:** freeze selected assignment and chosen relocation witness before any target result is available. The initial observation and proposal hashes remain fixed.
5. **Target evaluator:** from the final achieved state, plans and validates the complete intended target action. It may have a declared finite internal search schedule. It is invoked once per completed primary repair, not once per candidate during selection.

Remove the connector to historical `gamma0.start` **only in the new mode**. A newly planned target skill may contain its own approach/connector motions, which still require checking. Pass the final achieved joint configuration, gripper gap, attachment state and object poses into the new target query.

No physical motion is authorized by this stage. Use the existing 2D kinematic backend. No new articulated door backend, 3D environment, visual model, simulator dynamics stack or hardware driver is required.

## 5. Define the action and goal without a reference trajectory

Represent target transport with an explicit active object, goal pose/cell or declared goal region, permitted orientations, grasp family, support/contact mode, upright/no-lift constraints and robot profile. Keep these identical across candidate repairs for a query.

Create an `action_context_hash` from those fields. Do not use a target trajectory hash as the action identity in the new mode. Reference traces may remain optional privileged diagnostics for comparison.

The input must retain task goal and robot context; “no trajectory input” does not mean “scene image alone.” Test that changing the goal changes the query context, while changing only a privileged reference path cannot change learner tensors or deterministic proposal input.

Store object IDs for indexing and reporting, not as ordered numeric geometry or embeddings that leak construction identity. Physical spot IDs are stable; per-object candidate index 0 means stay at that object's current pose.

## 6. Evidence contract: do not collapse these fields

Use separate statuses for static endpoints, specific relocation attempts, complete assignment feasibility, target attempts, simulation and hardware.

- A positive **complete-assignment** label needs at least one full relocation-plus-target witness from the same initial state and under the same action/constraints.
- A negative complete-assignment label needs a sound certificate excluding all allowed realizations of that assignment. Static endpoint invalidity can provide one. A mandatory fixed goal occupied by an object required to stay can provide another if its geometric premise is proved.
- A rejected order excludes that order only. A finite relocation or target-planning failure is `UNRESOLVED` for existential feasibility.
- Operational episode success/failure within a fixed budget is a separate field. A timeout is unsuccessful within the benchmark budget but is not a physical impossibility proof.
- A target witness starting at arbitrary home after diagnostic endpoint substitution is not sufficient unless a complete relocation witness reaches that exact robot state or a checked connector bridges it.
- `NOT_RUN`, `ABORTED`, `CONSTRUCTION_UNAVAILABLE` and `OUT_OF_SCOPE` are not binary feasibility labels.

For the new objective, default lower bound is 0. A complete witness supplies an upper bound. A zero-move witness proves optimum 0. A one-move witness plus a valid mandatory-goal-occupancy certificate can prove optimum 1. Old direct-blocker counts and frozen A0 matching costs are not new action-level lower bounds.

Keep all successful alternative repair sets/destinations. Do not mark a nonteacher repair negative merely because it differs from one chosen demonstration.

## 7. Implement the case analysis before adding learning

Use small full-robot fixtures first. Reuse old scene geometry where useful, but issue new protocol/query records. Find actual witnesses rather than drawing intended paths.

| Case | Required demonstration |
|---|---|
| **R0: already feasible** | Empty repair plus a complete target witness. New minimum 0. |
| **R1: reference blocked but action feasible** | One stored frozen target path collides; a different complete target path succeeds from the same initial scene/robot state with zero moves. |
| **R2: mandatory goal occupied** | One obstacle overlaps a unique required final target pose; prove this geometric premise, relocate it once, then verify the target. Claim minimum 1 only if all scope assumptions hold. |
| **R3: alternative sufficient repairs** | Two distinct assignments from the same initial state each have a full relocation-plus-target witness. They need not have equal move count or be minimal. |
| **R4: order/access dependence** | Same assignment, different orders: one rejected or unresolved, one fully verified including its final target action. |
| **R5: static validity is insufficient** | Static-valid assignment with a sound target obstruction or a target-planning unknown. Keep those alternatives explicit. |
| **R6: invalid/unknown controls** | Duplicate destination, unsupported endpoint, uncertain numerical boundary, finite planner exhaustion and poisoned privileged fields. |

For R1, do not assume an archived dense root admits an alternate route. Search a small declared fixture set under finite budgets. If necessary construct a sparse new full-3R scene. A failed search does not prove no alternate exists. Report construction unavailability if needed and leave readiness blocked.

For R2, the goal must be unique under the action definition. If orientation or goal-region freedom permits the target to avoid the obstacle, do not use the occupancy certificate. Incidental pushing is not an allowed substitute for a declared relocation.

For R3/R4, the offline case audit is allowed to evaluate multiple candidate repairs. Label that path `OFFLINE_CASE_AUDIT`, keep it separate from primary proposal selection and show both in the results schema. Running an audit does not authorize target feedback inside the primary episode.

No mandatory hinge/drawer fixture is required in this stage. Those examples motivate action constraints but would expand the current backend substantially.

## 8. Primary episode semantics to demonstrate

Use the following structure or an equivalent that preserves the boundary:

```text
c0 = build_allowlisted_initial_context(S0, action, goal, constraints)
ranked = deterministic_case_proposals(c0)
for assignment in ranked:
    static = check_static_endpoints(S0, assignment)
    if static is not VERIFIED_VALID:
        record rejection/unknown; continue
    repair = plan_relocations_on_clone(S0, assignment)
    if repair has a complete relocation witness:
        commit(assignment, repair, source_observation_hash)
        break
if no commitment:
    finish with NO_REPAIR_WITNESS_WITHIN_BUDGET
else:
    execute/replay committed repair from S0
    if achieved-state assumptions fail:
        finish ABORTED
    else:
        target = evaluate_complete_target(achieved_state, action, goal, constraints)
        finish; do not choose another assignment based on target
```

For the empty assignment, relocation is immediately complete and target evaluation still happens after commitment. A future learned method will use a task-score threshold to decide whether all-stay is promising; the G3.5 fixed candidate list only validates plumbing.

Track moved history per episode. An object cannot be moved twice. Failed planning attempts on clones do not count as executed relocations. A failed physical/sim execution cannot be reset and counted as the same untouched one-shot trial.

## 9. Required tests and regression checks

Add targeted tests for the changed scientific contract, not tests that merely mirror implementation details:

1. A new-protocol query needs no `gamma0`, envelope, or nominal target-start state.
2. Poisoning/deleting `oracle_only` fields leaves learner tensors and initial proposal inputs unchanged.
3. Target callback spy/call trace shows zero target invocations before commitment and between relocations.
4. After a target failure/unknown, the primary episode does not advance to another candidate or refresh the proposal.
5. The final target query starts at the actual last relocation state, including gripper and attachment state.
6. Static validity does not automatically label complete action feasibility positive.
7. A finite planner timeout remains unknown and is not accepted as a negative or lower-bound certificate.
8. A rejected order does not exclude an entire assignment when another order succeeds or is unresolved.
9. Moved history, per-object move-once and candidate-clone state isolation remain enforced.
10. Frozen-control start connector, trajectory hash and replay semantics remain unchanged.
11. R0/R2 minimality fields are justified by their actual evidence; the R1 frozen blocker count is not imported as the new lower bound.
12. At least one end-to-end new-mode test uses actual 3R relocation and complete target planning, beyond mocks.

Run the affected existing tests and applicable G0-G3 regressions/replays. Broaden checks only for a concrete remaining regression risk or a repository-required gate. Keep old run directories unchanged and record before/after hashes or a precise unchanged-file check.

## 10. Required visualization and output files

Produce from recorded states and trajectories:

- `A_protocol_cases.png`: all case statuses, scene, goal, candidate endpoints and moved counts.
- `B_r1_route_comparison.png`: frozen failed motion versus actual new zero-move motion, same scene.
- `C_r2_repair.gif`: complete relocation and target motion, phase labels and achieved states.
- `D_r3_alternatives.png`: both independently witnessed repair alternatives.
- `E_r4_orders.png`: rejected/unresolved order and successful order, with precise first reason.
- `F_call_trace.png`: proposal, repair planning, commitment, relocation and target-evaluation timing; no target calls inside selection/relocation.
- `result.json`, `cases.json`, `metrics.csv`, `config.json`, `manifest.json`, `arrays.npz` and the completion report.

A missing witness must remain visibly unavailable/unknown. No fabricated path interpolation. Keep all obstacles, arm links, fingers, target and goal visible. Use consistent axes, meter units and physical cell labels. Clean learner images contain no diagnostic envelopes/arrows/status overlays.

## 11. Minimal code and runtime discipline

Reuse existing source ownership. Add `evaluate.py` only if there is no clean existing owner for post-commit evaluation. Do not create a new package hierarchy, generic planner framework or duplicate 2D stack. Keep ordinary modules approximately 120–280 logical lines; explain a narrow responsibility split above about 300. A small `run.py` dispatcher refactor is allowed if required; unrelated cleanup is not.

Use actual tested planner caps from the repository. The G3 report mentions 12 assignments, 6 non-dominated orders, 40 relocation plans, 2 failures per skill and high dense-scene cost. Do not automatically raise all limits. Start sparse, declare search budgets, and record attempted scenes, seeds, node/evaluation caps and wall time.

Pin versions actually used. No speculative dependency upgrades, no training jobs, no large downloads and no live robot commands. Preserve unresolved attempts in the report. Use one flat output directory rather than frame subfolders.

## 12. G4 readiness decision and stop condition

The completion report must contain this matrix with evidence links:

| Prerequisite | Pass / blocked / not attempted, with evidence |
|---|---|
| Goal-conditioned query works without trajectory fields | |
| Primary selection has no target feedback | |
| R0 zero-move witness and R1 objective distinction demonstrated | |
| R2 occupancy certificate/witness, or explicit missing premise | |
| R3 alternative positives and R4 order dependence demonstrated | |
| Static/sequence/assignment/target statuses remain distinct | |
| Unknowns and old minima handled correctly | |
| Full-state continuity and legacy regressions pass | |
| Case-derived figures and reproducible data saved | |
| Proposed G4 label sources and measured generation cost assessed | |

If a required case or interface is missing, complete all feasible work, document why it remains blocked and stop honestly. Do not claim G4-ready by turning a timeout into a negative or by using a point/disc surrogate as a full-robot witness.

The report must explicitly state: no G4 scaling, no G5 training, no learned-performance result and no hardware execution were performed. Explain the practical next step using measured costs and evidence coverage. Stop after G3.5 for review before any next-stage work.

## 13. Mathematical changes that the next stage must retain

These are not instructions to train now, but they prevent reverting to the old formulation:

- The exact product of static support/pair factors describes static endpoint validity only.
- The intended task label is existence of an executable relocation sequence realizing the assignment followed by an allowed complete target motion.
- The primary learned energy adds a goal-conditioned whole-assignment success term. The original frozen-sweep unary label is not reused as an action-level truth.
- Gibbs updates must include the change in the whole-assignment term; local factor updates alone are no longer correct.
- Global BCE and joint finite-pool supervision use complete witnesses and sound negatives. Unknowns are excluded from the joint normalization pool, not silently treated as negative competitors.
- A privileged offline teacher may search with target feedback. The primary deployed proposal may not.
- Old frozen A0 matching is an archived control. Static matching under necessary endpoint constraints is useful, but is not a complete solver for action feasibility or executable minimum repair.

Use the PDFs for full definitions, losses, B0-B9/O1/F0 baseline registry, 3D constraints and staged implementation.
