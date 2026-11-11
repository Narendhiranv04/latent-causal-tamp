# P16 — 3D migration specification for methods B and D (design only; no 3D result is claimed)

**Status.** P16 implements no 3D simulation, training, benchmark or robot experiment.
- **Environment:** MuJoCo 3.10 and trimesh are installed, but the repository has no 3D scene, robot model or certifier. The contract allows a smoke test only for an already-supported simulator, so none was run.
- **Purpose:** this document fixes what a P17 3D phase must build, and the gates it must pass, before any 3D claim.

## 1. What carries over unchanged (method level)

| 2D component (P16) | 3D form | change |
|---|---|---|
| Task = {scene, target, goal, robot start, object metadata, fixed structures} | same keys; poses become SE(3); slots become discrete shelf / bin / table poses | data model only |
| tri-state statuses (VERIFIED / scoped CERTIFIED_INFEASIBLE / STATIC_INVALID / UNKNOWN_*) | identical semantics | none |
| lexicographic objective (relocations, measured joint travel) | joint travel over 7 DoF (weighted L1, same definition per joint) | none |
| expanded finite search (`p16_common.search`: repeat moves, dominance, node / work caps, finite-graph claims) | identical algorithm; state = object poses + q + gripper attachment | none |
| deterministic provider (`p16_motion.DetPhysics`: node budgets, seeded planner, shared exact cache, independent replay with continuity) | same contract; must be re-validated with the 3D planner | re-test |
| B lean energy (keyed unaries, F2 order, empty repair, calibrated no-op-first rule) | same loss and policy; inputs change (§4) | encoder only |
| D pairless (feasibility + union-blocker Bernoullis, masked labels) | same loss; pool = movable objects in the target's access region | encoder only |

## 2. Robot, grasps and swept volumes

- **Robot.** A fixed-base 7-DoF arm (Franka Panda kinematics and joint limits as the reference) with a parallel gripper (opening 0–80 mm). The base pose is fixed per scene and recorded in the Task.
- **Grasp candidate sets, declared and finite per object class:**
  - **top grasps:** yaw sampled every 15°, approach along −z;
  - **side grasps:** 8 azimuths × 2 heights, horizontal approach;
  - **angled grasps:** 45° pitch × 8 azimuths.
  - Each grasp has a pre-grasp and retreat offset of 6 cm along the approach axis.
  - A grasp is **valid** only if the finger and palm volumes are collision-free at the grasp pose and the IK solution respects joint limits.
- **Swept-volume certification:**
  - every link is a capsule chain, plus the closed or open gripper hull, plus the **carried object's volume** rigidly attached during transfer;
  - continuous collision is checked by interval subdivision against all scene geometry (shelf boards, bin walls, drawer fronts, other objects);
  - the certifier is a separate module with its own tests, mirroring 2D `motion.certify_trajectory`.
- **Certificates that do NOT transfer from 2D:**
  - the link-0 sector certificate (planar link-0 sweep) has no 3D analogue and must not be reused;
  - 2D `TARGET_PICK` (no planar grasp side free) is replaced by a 3D **grasp-set exhaustion certificate**: every declared grasp is in collision at the grasp or pre-grasp pose, or has no IK. Its scope is limited to the declared grasp set; it is not universal impossibility.
- **3D certificates to develop and verify independently (producer / checker split, as in 2D):**
  - **shelf-depth access:** an object behind another in a cubby with closed side walls admits no side or top grasp until the front object is removed (scoped to the declared grasp set);
  - **closed-lid / drawer:** a drawer front or door blocks extraction until it is moved;
  - **stack order:** the object below is ungraspable from the top while it is covered.

## 3. Candidate 3D scene families (development benchmark)

| # | family | logical infeasibility | expected repair |
|---|---|---|---|
| 1 | shelf cubby, single row | target behind 1–2 objects; side walls closed | front objects out (order fixed) |
| 2 | two-deep cubby with an alternative | either the left or right front object clears a side approach | union differs from intersection |
| 3 | closed-side bin | target at the bottom-centre; tall neighbours block top / angled grasps | move 1–2 neighbours to a buffer bin |
| 4 | object in front of a drawer | drawer extraction swept volume blocked | move the object, then open |
| 5 | stack | target under 1–2 objects | unstack top-down (order chain) |
| 6 | slot conflict | few free shelf slots; a wrong slot blocks the later extraction sweep | joint slot assignment |
| 7 | buffer reuse | one free slot; an object must be parked and re-parked | repeat move |
| 8 | vertical extraction limit | low shelf clearance permits only a side extraction path | destination choice |
| 9 | feasible original with decoys | target directly graspable | 0 moves (no-op) |
| 10 | certified vs planner-unknown negatives | grasp-set exhaustion vs a budget-limited planner | status discipline |

## 4. Learned-input changes

- **B and D visual input:** DINOv2 features on **two fixed rendered views** (front, top) plus depth, mask-pooled per object.
- **Numeric context:** SE(3) object pose (position plus yaw for symmetric classes), size class, target / goal pose, robot q (7), base pose.
- **Unchanged:**
  - keyed query identity strings now include the slot id and object id;
  - the B order encoder (F2) and the D pairless head are unchanged.
- **Exact enumeration limits:** B MAX_ACTIVE 9 and D CAP 6 are retained. Larger pools need the declared shared pruning of §5, with recorded omissions.

## 5. Search and library changes

- **Candidate movers:** objects whose volume intersects the target's grasp-approach corridors or extraction sweep, plus all objects in the same cubby or bin. Omitted movers are recorded.
- **Candidate slots:** free shelf / bin / table slots that are statically valid (support, clearance) and at least one slot away from the target corridor. Freed source slots are included.
- **Witness library:** relocation trajectories indexed by (source slot, destination slot, object class, grasp type), with similarity computed on voxelised local occupancy (3×3×2 slot neighbourhood) plus global occupancy.
  - Modes are clustered by swept-voxel IoU together with terminal-q distance, as in 2D.
  - Every reuse is re-certified in the new scene.
  - **Alternate transit:** a bounded RRT from the current q to the witness start.
- **Fixed-base reuse rule:** the same absolute source and destination slot plus a certified transit.

## 6. Determinism and compute quote (from measured 2D costs; to be re-measured in a 3D pilot)

| item | 2D measured (P16) | 3D factor (assumed) | 3D estimate |
|---|---|---|---|
| exact certification per trajectory | ≈ 0.05–0.3 CPU-s | ×20 (7 DoF, 3D distance queries) | 1–6 CPU-s |
| online plan per move | ≈ 10–60 CPU-s | ×10 | 100–600 CPU-s |
| labelling per root (lattice + catalogue) | measured in 0084 | ×10 | — |
| search per root (one arm) | ≈ 40–450 CPU-s | ×10 | 0.4–4.5 k CPU-s |

**Quote for a minimal 3D P17:**

| item | CPU-s |
|---|---|
| certifier + planner + determinism validation | 20 k |
| 10-family construction pilot (50 roots) | 30 k |
| B / D labels for 150 roots | ≈ 150 k |
| training | 20 k |
| evaluation | 60 k |
| **total** | **≈ 280 k** |

These are estimates, not commitments.

## 7. Gates for a 3D phase (must pass in order)

1. **Certifier and grasp-set tests,** including held-object sweep, closed-wall cubby and drawer cases. **Determinism:** 5 seeded repeats under load give identical status, trajectory hash and travel.
2. **Construction of all 10 families,** with physics-only acceptance statistics and random-unfiltered strata.
3. **Scene-only API:** no constructor or teacher input at runtime (static scan plus a deletion test, as in P16).
4. **B and D 3D smoke on DEV only.** Then a frozen, pre-registered prospective cohort with hash-committed labels before unsealing.
5. **No transfer claims.** No claim that 2D results transfer, and no real-robot claim without a separate hardware protocol.
