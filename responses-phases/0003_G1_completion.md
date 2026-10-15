# 0003 — G1 completion report: articulated 3R robot, certified six-phase skill, 64-cell audit

| Field | Value |
|---|---|
| Report number | 0003 |
| Date | 15 October 2026 |
| Stage | **G1** (Guide v1.6 §5): 3R FK/IK, continuous robot phases and first valid nominal skill |
| Gate verdict | **PASS**: every guide G1 criterion and every additional user/instruction-file G1 check passed (see A) |
| Run directory | [`../runs/g1_robot/`](../runs/g1_robot/) |
| Previous reports | [`0001_G0_completion.md`](0001_G0_completion.md), [`0002_workflow_setup.md`](0002_workflow_setup.md) |
| Previous turn sync | report 0002 was committed as `b55063efb7c78062d4fd53c1337b0a640c453beb` on `main` and pushed to `origin/main` (verified: remote head equal to local) |

---

## 0. Context for an independent reviewer

The project studies **intervention-supervised joint relocation for a prescribed, frozen target motion**. Given a scene, the robot state, finite legal resting cells and a validated complete target action, the method predicts which objects obstruct that action and proposes a small executable move-once set of relocations; motion, ordering and replay are verified independently.

G1 builds the robot that every later stage relies on:
- a fully collidable **planar 3R arm with a two-finger side gripper**;
- exact kinematics;
- a **conservative continuous collision certifier**;
- a planner that only ever returns certified segments;
- the six-phase grasp → carry → release skill, with independent replay.

No interventions, blockers, labels, learning or Boltzmann sampling exist yet; those start at G2.

**Inputs read before implementing:**
- both PDFs (Methodology v1.4, Guide v1.6);
- `instruction-phase-md/G0_review_and_next_Claude_message.md`, which carries the user's G1 acceptance additions;
- reports 0001 and 0002;
- the G0 code, configuration and tests.

---

## A. Stage objective and outcome

**Question:** can the specified 3R robot (base (−0.14, 0.32) m, links 0.42/0.34/0.20 m) perform certified, continuous grasp–carry–release manipulation anywhere on the 8×8 grid, with every body checked against every obstacle, its own other bodies and the support?

### Acceptance table

| Requirement (source) | Result |
|---|---|
| FK/IK closure at sampled configurations, both elbow branches (guide G1, user §2) | **PASS**: 2000 random configurations, max error 2.6e-12 rad. The test asserts both branches exist in the interior and reproduce the pose to 1e-12. |
| Joint limits and angle wrapping (user §2) | **PASS**: IK wraps to [−π, π) and rejects out-of-limit solutions; unreachable poses return no solution. |
| Full capsule links, joint housings, palm, **connected** fingers (user §2, instruction item 4) | **PASS**: a finger slide rail joins both fingers to the palm (distance rail–finger = 0 at every aperture); inner clear gap = g, outer width = g + 2t. |
| Closure stops at contact with the 0.048 m cylinder, no penetration (user §2) | **PASS**: the closure segment open → 2r certifies; commanding the configured `closed_gap` 0.046 m is detected as finger–object penetration. |
| Self- and world-collision, gray band, swept detection (guide G1) | **PASS**: folded-arm self-collision is caught. δ ± ε gives UNRESOLVED (gray band). A segment whose endpoints are both clear is caught colliding in its interior. |
| Attachment transform continuity (guide G1) | **PASS**: object world pose continuous to 1e-12 at grasp and release; tool-frame offset (0.032, 0) m. |
| Reproducible home (guide G1) | **PASS, with a justified change**. The provisional `[0,0,0]` is a **certified margin violation** (`housing1` 0.004 m < δ from a disc at cell 27). The new home `[π/2, π/2, π/2]` is clear even with all 64 cells occupied (closest pair `link2|rail`, 0.013 m). |
| A complete full-arm side-grasp nominal trajectory that replays from exact stored q/g/m (guide G1 pass criterion) | **PASS**: nominal S1 task 36 → 19 is VERIFIED_FEASIBLE; `python run.py replay` re-certifies it from `arrays.npz` and the hash matches. |
| 64-cell audit: IK, grasp pose, approach/closure, complete skill, conclusive vs exhausted (user §3, instruction items 1, 6) | **PASS**: **64/64 VERIFIED_FEASIBLE** (complete pick c → place 63−c → home, obstacle-free). Per-cell breakdown in E. |
| All four corners: full approach → closure → attachment → carry → release → retreat, obstacle-free then sparse (user §3, instruction item 2) | **PASS**: 4/4 corner tasks VERIFIED in D0 (empty), 4/4 in S1 (designated sparse) and 4/4 in S2 (sparse stress scene with 0.032 m corridors). |
| Full-clutter attempt in the 35-obstacle G0 scene (user §5E) | **Reported honestly**: **CERTIFIED_INFEASIBLE** within the declared grasp set. All 48 pick candidates are rejected (26 no IK, 22 certified grasp-pose collisions). No trajectory was fabricated. |
| UNRESOLVED ≠ infeasible; budget exhaustion never reported as proof (user §4, §7) | **PASS**: enforced in code and tests (`test_link0_sweep_certificate_and_unresolved_budget`, `test_interrupted_connect_never_joins_uncertified_edges`). |
| Visual deliverables A–E (user §5) | **PASS**: see E. |
| Determinism and replay (user §7) | **PASS**: identical nominal action hash across independent full runs; 77/77 stored trajectories (3206 segments) re-certified by `replay`. |
| Tested robot profile hash frozen (guide G1) | **PASS**: `robot_profile_hash = sha256:2d798676…1ae858`, status `TESTED_G1`. |

### Gate checks recorded in `result.json`

`home_clear_of_all_64_cells`, `all_64_cells_verified_obstacle_free`, `corner_tasks_verified_D0_and_S1`, `nominal_skill_verified` and `robot_frames_within_fixed_axes` are all `true`.

---

## 1. Robot model and conventions

### Kinematics (Methodology §2.1)

- **Absolute link angles:** θ_j = q_1 + … + q_j.
- **Joint positions:** J0 = b (base), J1 (elbow), J2 (wrist), J3 = TCP, where J_k = b + Σ_{j≤k} L_j (cos θ_j, sin θ_j). The TCP is the palm tip (`tcp_at_palm_tip`), and the tool x axis points along φ = θ_3.
- **IK for (x, y, φ):**
  1. Compute the wrist w = TCP − L3 (cos φ, sin φ).
  2. Compute cos q2 = (|w − b|² − L1² − L2²)/(2 L1 L2).
  3. Take both branches, q2 = ±acos(·) (branch +1 means q2 > 0).
  4. Compute q1 = atan2(w − b) − atan2(L2 sin q2, L1 + L2 cos q2), and q3 = φ − q1 − q2.
  5. Wrap all three to [−π, π) and reject any outside the joint limits ±3.14159265 rad.
- **No wrapping through the limit:** joint limits make the configuration space a box. Motions never wrap through ±π, and an IK track that would jump across ±π is rejected as discontinuous.

### Collision bodies (`geometry.bodies`)

All bodies are convex cores dilated by a radius, with exact 2D distances. The signed distance between two bodies is the core distance minus both radii.

| Body | Geometry |
|---|---|
| base | disc r = 0.018 at b |
| link0, link1 | capsules J0→J1, J1→J2, half-widths 0.009, 0.008 |
| housing1, housing2 | discs r = 0.012 at the elbow and wrist |
| link2 | capsule from the wrist to the **palm's back face** (TCP − 0.028 along φ), half-width 0.007 |
| palm | rectangle, x ∈ [−0.028, 0], \|y\| ≤ 0.017 (tool frame) |
| **rail (new)** | finger slide rail, x ∈ [−0.008, 0], \|y\| ≤ open_gap/2 + t = 0.042 |
| finger_l / finger_r | rectangles, x ∈ [0, 0.050], inner faces at y = ±g/2, thickness 0.007 |
| held | the grasped disc at its tool-frame offset, measured at closure (`validated_contact_at_closure`) |

**Gripper fix (user §2, instruction item 4).** At G0 the 0.034 m palm could not carry fingers spread to 0.084 m, which is why they appeared detached. The rail is the smallest coherent mounting: both fingers slide on it, so they touch it at every aperture. The palm dimensions are unchanged.

**Aperture semantics:**
- `open_gap` 0.070 m is the inner clear gap; the outer width is 0.084 m.
- At closure the gap stops at contact, g_c = 2(r + |y_offset|) = 0.048 m.
- `closed_gap` 0.046 m is only the commanded limit. It is never reached on an object, and reaching it would be detected as penetration.

**Grasp convention.**
- **Contact geometry:** `grasp_center_x_m = 0.032`, so the object centre sits 32 mm ahead of the TCP. Its back face is 8 mm (> δ) from the rail and palm, and the finger contact points lie on the fingers (0 ≤ 0.032 ≤ 0.050).
- **Approach and retreat:** pregrasp sits 0.06 m back along the tool axis; the config check enforces ≥ finger overhang + r + δ = 0.047 m. Retreat is 0.06 m.

**Tested pairs.** Every pair is tested except mechanically mounted ones:
- base–link0;
- each housing with its two links;
- link2–palm;
- palm/rail/fingers among themselves (one gripper assembly);
- the guide's adjacent-link exclusions link0–link1 and link1–link2.

Exclusions never hide robot–object pairs. The only object-contact allowance is **finger ↔ the scheduled object during closure, carry and release**, and it requires d ≥ 0 (no penetration) rather than d ≥ δ.

**Support constraint during carry.** The carried disc must stay over the support rectangle, with its centre in [r, 0.64 − r]². This is checked continuously like any other pair (entry `held|support`). The 2D suite declares no walls, so robot bodies may extend beyond the support edge. In a top view the arm sits above the tabletop plane but still collides with the upright cylinders.

---

## 2. Verification semantics (how "certified" is earned)

**Thresholds** (Methodology §3, single margin convention). The oracle uses uninflated shapes and demands d ≥ δ = 0.005 m. With ε = 0.0002 m:

| Pair type | Clear | Definite violation | Gray band |
|---|---|---|---|
| Margin pair | d ≥ δ + ε | d < δ − ε | between the two: UNRESOLVED |
| Scheduled finger contact, support containment | d ≥ −ε (contact) or d ≥ ε (support) | d < −ε | as above |

**Continuous certification** (`geometry.certify`). Along a joint-linear segment q(s) = qa + s Δq (finger gap linear too), each pair distance is Lipschitz in s.
- **Robot body against a static disc:** L = Σ_k |Δq_k| ρ_{b,k} (+ |Δg|/2 for a finger). Here ρ_{b,k} is the maximum distance from joint k to any point of body b; it holds for any configuration by the triangle inequality.
- **Two robot bodies in frames f_a ≤ f_b:** joints shared by both move them rigidly together, and a rigid motion preserves distance. So L = Σ_{k=f_a}^{f_b−1} |Δq_k| ρ_{b,k} + (fingers in pair)·|Δg|/2.
- **Interval bound:** on [s0, s1], d(s) ≥ (d(s0) + d(s1) − L (s1 − s0))/2. This dominates the spec's sufficient bound min(d0, d1) − LΔs/2.
- **Algorithm:** intervals are bisected left-first until every bound clears (CLEAR), a sample definitely violates (COLLISION, reported with the first detected pair), or the evaluation budget runs out (UNRESOLVED, with the interval recorded).
- **Soundness tests:** the bound is checked against exact distances on 12 random long segments that include finger travel (`test_lipschitz_bound_is_sound`). A mutation that zeroes the bound makes this test and the swept-collision test fail.

**Link-0 sweep certificate** (a sound proof of connector infeasibility).
1. Link 0 and the elbow housing depend on q1 alone, and joint 1 cannot wrap.
2. So every path from qa to qb points link 0 at every angle between qa[0] and qb[0].
3. At angle α towards a resting disc with centre at distance ρ, the disc lies within max(ρ − L1, 0) of link 0's tip and housing.
4. That is a definite violation whenever ρ < L1 + max(w0/2, housing_r) + r + δ − ε = **0.461 m**.
5. Therefore, if such a disc lies at an angle between the endpoints, the connector is **CERTIFIED** blocked.

`test_sweep_certificate_band_is_sound` checks this: with q1 aimed at such a disc, 200 random (q2, q3) are all definite collisions.

**Status vocabulary per query:**
- **VERIFIED_FEASIBLE:** every stored segment certified, then independently re-certified by replay. Scope: `PLANAR_ARM_KINEMATIC_SKILL`.
- **CERTIFIED_INFEASIBLE:** only when every alternative failed definitively. Scope suffix `/DECLARED_GRASP_SET` (24 tool-axis directions × 2 elbow branches, straight approach) and/or `+LINK0_SWEEP`.
- **UNRESOLVED:** everything else, including planner budget exhaustion and gray-band verdicts.

Kinematic only: `simulation_replay_status` and `physical_execution_status` are `NOT_RUN`.

---

## 3. Planning and the six-phase skill

**The skill** (`skill.plan_skill`). The phases are pregrasp → approach → close_attach → carry → release → retreat, plus **return_home**. Return_home is a connector back to the stored home, which makes the start and end state repeatable.

Each stored waypoint records:
- q (rad) and the gap g (m);
- a phase label per segment;
- the attachment mode m per segment (replay rejects any record where m disagrees with the phase schedule);
- the measured tool-frame object offset;
- the achieved placement (error ≤ 8.3e-16 m against `release_xy_tolerance` 0.002 m).

**Candidate screening** over the declared grasp set:

| Candidate | Checks, in order |
|---|---|
| Pick | exact IK → clear open-finger grasp pose → IK-tracked straight approach (5 mm waypoint spacing, ≤ 0.1 rad joint jump) certified segment by segment → contact closure (centred within 1 mm, g_c ≥ closed_gap) certified with contact allowed |
| Place | exact IK → clear held pose → certified release (opening with contact allowed) → certified straight retreat |

Places are screened before picks, and picks whose elbow branch has an admissible place are tried first.

**Connectors** (`planner.plan`), cheapest first:
1. the direct joint-linear segment;
2. for same-branch carries, an IK-tracked **guide line** (the object moves straight while the tool axis turns);
3. the link-0 sweep certificate (an immediate certified COLLISION);
4. a seeded **RRT-Connect**, with every tree edge certified (edge budget 200 evaluations; an uncertified edge is dropped) and certified shortcutting (150 rounds).

The RRT runs in one of two spaces:
- **Joint space.** While carrying, samples are object poses drawn over the support with a random elbow branch, mapped through exact IK. Every sample therefore satisfies the carry constraint, and branch switches stay reachable.
- **Held-object pose space (x, y, φ)**, for same-branch carries. Sampling inside [r, W−r]² keeps the object over the support by construction. Each edge moves the object straight while φ turns, IK-tracked on one branch and certified.

The per-query seed is crc32 of task and connector, combined with the base seed 41, so a plan never depends on what ran before it in the process.

**Why not OMPL.** The guide asks for an established planning library, and OMPL 2.0.1 (pip wheel, Python 3.13) was installed and tested. Its Python bindings work, and a Python `MotionValidator` can plug in this certifier. However, OMPL's global RNG seed can be set only once per process: re-seeding logs *"Random number generation already started. Changing seed now will not lead to deterministic sampling"*. Per-query reproducibility, which the guide requires ("separate seeds for … nominal planner"), was therefore impossible. A compact RRT-Connect, about 60 lines sharing one implementation for both spaces, was used instead, and OMPL was uninstalled so the environment matches the code. **Please confirm this substitution.**

---

## 4. Development record: problems found and fixed within G1

All of these were found by tests, by replay, or by inspecting search statistics. None were hidden.

1. **The provisional home is invalid** (certified, not a hand estimate). `q=[0,0,0]` comes 0.004 m < δ from a disc at cell 27, and it lies across the support, so in a dense root it would be in collision before any action. Replaced by the folded off-support home `[π/2, π/2, π/2]`, clear even with all 64 cells occupied.
2. **The link-0 sweep certificate was initially too weak.** It only covered discs with ρ ≤ L1. An S1 obstacle at cell 43 (ρ = 0.437 m) partitions link 0's range through the elbow housing, and the planner was searching a provably empty space. The certificate was extended to ρ < 0.461 m and proven by test.
3. **RRT-Connect join bug, caught by replay.** When the budget ran out mid-CONNECT, the trees were spliced even though they had not met, inserting an uncertified 2.98 rad jump. Replay rejected 5 such trajectories (`held|support` −0.14 m). Fixed (join only when CONNECT reaches the node), with a regression test that fails on the buggy code and passes on the fix.
4. **Over-conservative Lipschitz bound for self pairs.** Adding both bodies' speeds made finger↔held contact (d ≡ 0) impossible to certify, so carries exhausted their budgets. Replaced by the shared-frame bound in §2, which is sound and tested. The full 78-query batch dropped from more than 10 min to about 26 s, and every UNRESOLVED carry became VERIFIED.
5. **Sparse fixture design.** The first sparse layout put obstacles beside the border columns. It is kept, unchanged, as the stress scene **S2**. The second layout had cell 43 inside the sweep zone (item 2). The designated scene **S1** now keeps every obstacle outside the 0.461 m sweep zone.
6. **Choice of nominal action.** 29 → 44 was verified with the second layout; 29 → 36 had no admissible pick in the final layout (cell 29 boxed in by o01, o02, o05; 47/48 candidates certified rejected). The nominal became **36 → 19**: t0 is picked from between o02 (3,4) and o04 (5,4) and placed beside o00 (1,3).
7. Search efficiency (not correctness): waypoint pre-pass in chain certification, a cap on direct (pick, place) pairs, and IK-based carry sampling.

---

## B. Files created or modified

Logical lines exclude blanks, comments and docstrings.

| File | Status | Purpose | Physical / logical |
|---|---|---|---|
| `geometry.py` | new | Robot model, FK/IK, collision bodies, exact distances, `Checker` (pair table, thresholds, Lipschitz), `certify` | 357 / 244 |
| `motion.py` | new | Trajectory record and hash, phase contexts, replay certification, IK tracking (approach/retreat/carry lines), certified chains, path sampling | 160 / 104 |
| `planner.py` | new (split from motion) | `Plan`, per-query seeds, link-0 sweep certificate, joint and pose spaces, generic RRT-Connect, shortcutting, `plan` | 240 / 171 |
| `skill.py` | new (split from motion) | Declared grasp set, pick/place screening, six-phase assembly, statuses, JSON summary, audit rows | 266 / 217 |
| `figures.py` | new (split from viz) | G1 figures and GIFs from recorded results | 349 / 285 |
| `viz.py` | modified | **Drawing-only FK removed**; the robot is drawn from `geometry.bodies` (one kinematic model); status colours defined | 257 / 185 |
| `scene.py` | modified | `place_scene` for designated fixtures; schema and physics checks for the new config keys | 391 / 278 |
| `run.py` | modified | `check` (parallel G1 jobs, gates, artifacts) and `replay`; shared manifest writer | 288 / 237 |
| `config.toml` | modified | New home; `rail_depth_m`, `grasp_center_x_m`; `[geometry]`, `[planner2d]`, `[skill2d]`; robot-view limits | 82 |
| `fixtures.json` | modified | G1_D0 (audit + corners), G1_S1 (designated sparse + nominal), G1_S2 (stress), G1_CLUTTER | 43 |
| `tests/test_arm2d.py` | new | 20 G1 tests | 220 / 165 |
| `tests/test_scene.py` | modified | Robot-extent test now uses geometry bodies (rail included) | 195 / 147 |
| `README.md` | modified | Status, layout, commands | — |

**Code-organisation audit:**
- **New modules beyond the guide's G1 list.** `planner.py`, `skill.py` and `figures.py` are size-motivated splits, each one clearly separated responsibility, as the guide permits with a recorded reason. **Please confirm** these module names.
- **Modules at the size ceiling.** `scene.py` (278 logical) and `figures.py` (285) are at the guideline. Before reaching 300, `figures.py` lost its sampling helpers to `motion.py` and the audit rows to `skill.py`. If `scene.py` grows again, its config schema moves to `config.py`.
- **No duplication.** There is one FK, one distance model and one RRT implementation, and the AST check found no unused imports.

---

## C. Configuration and reproducibility

| Item | Value |
|---|---|
| Config hash | `sha256:bcfd8bd274d1ad563e153d1d632e00f0c7db32d2ca5aecb3cf2acb64990a3bd0` |
| Tested robot profile hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858` (`TESTED_G1`) |
| Nominal action hash (G1_S1_t4, 36 → 19) | `sha256:913799bfa2e5405d1ccaa52a32d47aaf423b40a35ecd995ab00f640fd7a7e464`, identical across independent full runs |
| Seeds | planner base 41; per query `crc32("<task>/<connector>")` |
| Versions | Python 3.13.11, numpy 2.4.0, matplotlib 3.11.2, pillow 12.0.0, pytest 9.1.1. No new runtime dependency; OMPL was tested and removed (see §3). |

Key new settings:
- `[geometry]`: `numeric_margin_band_m` 0.0002, `certify_max_evals` 4000.
- `[planner2d]`: `max_nodes` 20000, `max_wall_seconds` 30, `extend_step_rad` 0.25, `shortcut_rounds` 150, `pose_step_m` 0.06, `pose_phi_weight_m` 0.1, `edge_max_evals` 200.
- `[skill2d]`: 24 approach directions, approach and retreat 0.06 m, line step 5 mm, max IK jump 0.1 rad, 4 planner failures per skill, 64 direct pairs.

**Robot-view axes.** Measured over every recorded frame: x ∈ [−0.80, 0.77], y ∈ [−0.43, 1.33]. The fixed limits were set to x [−0.85, 0.85], y [−0.50, 1.40], and gate `robot_frames_within_fixed_axes` checks them.

Source SHA-256 at this report:

| File | SHA-256 |
|---|---|
| `scene.py` | `f72a42e842eccb2246beb82171a895fcc3ff26d36bc5d27f9154c045775c8d0c` |
| `geometry.py` | `ddedb6da84a5a6912e363e32f1e60c96afc31ecb369cd96d13a53815315af803` |
| `motion.py` | `cdbb9f580bb4a8ea2c54a2e38ed09da47d2ab697c4542ab9df35ee68215dbb0b` |
| `planner.py` | `1edbcdc62218b3c4129e0f68ee468549a1200eaf1706c2cf87a51abe0aaaea3a` |
| `skill.py` | `7b5808fd4d564444dc9bdefe3685413923b1e3b18bc6bb443b9d7e7f86e48280` |
| `viz.py` | `aa43f52908480bec1b8c3a043642fae062cb2d618e5085344f30020c62ff072d` |
| `figures.py` | `fb1d8041c0ae0fe4ff30828a8167147f31b430e8f76bceb11498572d56ec88d6` |
| `run.py` | `25dd5da869aedae6d4001b70e08afd3cdb13744bf6a7c68081bea2fc5c762dd5` |
| `tests/test_scene.py` | `ba0329f4c805da551048efab20762226958bf6e9bf891af90ea0d62b47c0b36a` |
| `tests/test_arm2d.py` | `47d5cfcf482e14bb30dfe12a89c481799ee1de82c3777549cb165a65ca7b5cc3` |
| `config.toml` | `230bd3b0418eebec7ef05e681cf156f22a2078e6a08d90395d4c282e050d3535` |
| `fixtures.json` | `e03536cd9fc9bb4af43e727d9cc2d54e62c91e8c94fe72b55566cdd55da384b8` |

---

## D. Tests and verification (commands actually run)

| Command | Result |
|---|---|
| `python -m pytest tests -q` | **34 passed** (14 G0 + 20 G1) in 13.4 s |
| `python run.py check --config config.toml --out runs/g1_robot --workers 24` | exit 0, all 5 gates true, 1 min 28 s wall |
| `python run.py replay --run runs/g1_robot` | exit 0, `replay_passed: true`; 77 trajectories, 3206 segments re-certified, all hashes match |
| `python run.py scene --case G0_ILLUSTRATIVE --out <scratch>` | exit 0 (G0 command still works; the historical `runs/g0_scene` is untouched) |

**Mutation checks** (each test fails on the mutant and passes after restoring):
- zeroing the Lipschitz bound → `test_swept_collision_between_clear_endpoints` and `test_lipschitz_bound_is_sound` fail;
- reverting the RRT join fix → `test_interrupted_connect_never_joins_uncertified_edges` fails.

**G1 tests** (`tests/test_arm2d.py`):

| Group | Tests |
|---|---|
| Kinematics | FK/IK round trip on both branches; IK limits, wrapping, unreachable |
| Gripper | rail connection and aperture (open/contact); closure stops at contact, penetration detected, contact disallowed outside schedule |
| Collision | self-collision; world collision and gray band; swept collision between clear endpoints; Lipschitz soundness (joints + finger travel) |
| Certificates | link-0 sweep certificate and budget → UNRESOLVED; sweep certificate band soundness |
| Home and grasp access | home clear of all 64 cells, `[0,0,0]` rejected on `housing1\|o27`; certified grasp candidates at every corner |
| Full skill | six-phase corner skill VERIFIED, with phase order, home→home and replay; attachment continuity; determinism (same hash); interrupted-CONNECT regression |

**Unresolved cases in the final run:** none. No query ended UNRESOLVED; 77 ended VERIFIED_FEASIBLE and 1 CERTIFIED_INFEASIBLE.

---

## Full 64-cell coverage audit (D0, obstacle-free)

**Task per cell:** home → pick at c → carry → place at its point-mirror 63 − c → retreat → home. Long cross-table carries are deliberate.

**Complete skill:** **64 VERIFIED_FEASIBLE, 0 CERTIFIED_INFEASIBLE, 0 UNRESOLVED.** Per cell: mean 2.3 s and at most 9.2 s; 30–188 waypoints.

Pick-candidate breakdown over all 64 × 48 = 3072 candidates:

| First failed check | Count | Meaning |
|---|---|---|
| NO_IK | 580 | Wrist outside the 2-link annulus or outside joint limits for that tool direction. Far columns lose about half: 20/48 remain at column 7 vs 48/48 near the base. |
| GRASP_POSE | 426 | Open-finger grasp pose collides, mostly self-collision in folded configurations (`link1\|rail` 190, `link0\|link2` 36) or the arm crossing the target itself (`link1\|t0` 138, `link0\|t0` 40) |
| APPROACH | 254 | Straight 6 cm approach fails: IK tracking discontinuous (132, a branch or limit jump), or certified collisions (`link1\|rail` 82, `link0\|t0` 30, …) |
| CLOSURE | 0 | — |
| **OK** | **1812** | Certified approach and closure; **every cell has ≥ 20 certified pick candidates** |

**Corner cells:**
- (0,0) and (7,0): 32/48 OK.
- (0,7) and (7,7): 20/48 OK (28 have no IK, because from far away only tool directions roughly pointing away from the base are reachable).

**Connectors used:**
- carry: 62 DIRECT, 1 GUIDE_LINE, 1 RRT_JOINT;
- pregrasp: 63 DIRECT, 1 RRT_JOINT;
- return: 64 DIRECT.

**Intrinsic vs clutter restrictions.** In the empty scene the only restrictions are intrinsic: reach annulus, joint limits, self-collision, and the arm crossing the target itself. None prevents manipulation anywhere on the grid, so **no corner or cell is unreachable because of the base or link choice**. The arm dimensions were therefore not changed.

---

## Four-corner manipulation results (cycle 0 → 7 → 63 → 56 → 0)

| Scene | (0,0)→(0,7) | (0,7)→(7,7) | (7,7)→(7,0) | (7,0)→(0,0) |
|---|---|---|---|---|
| D0 empty | VERIFIED (carry guide line) | VERIFIED (guide line) | VERIFIED (RRT joint) | VERIFIED (direct) |
| S1 designated sparse (6 obstacles) | VERIFIED (RRT joint carry **with elbow-branch switch**: pick branch −1, place branch +1) | VERIFIED (RRT **object-pose** carry) | VERIFIED (guide line) | VERIFIED (direct) |
| S2 stress (8 obstacles, 0.032 m corridors) | VERIFIED (RRT joint) | VERIFIED (RRT joint) | VERIFIED (guide line) | VERIFIED (direct) |

**Why (0,0) → (0,7) in S1 needs an elbow-branch switch.**
1. With t0 resting at (0,0), 0.333 m from the base, the sweep certificate proves that all 15 branch-+1 pick configurations are unreachable from home: link 0 would have to sweep through the target.
2. In S1 every admissible place at (0,7) is on branch +1.
3. So the arm must pick on branch −1 and straighten the elbow (q2 = 0) while carrying.

This is a genuine kinematic phenomenon that a pose-space-only planner would miss, and it is why both RRT spaces exist.

---

## Nominal reference action (S1, t0: cell 36 → cell 19)

- **Status:** VERIFIED_FEASIBLE, `PLANAR_ARM_KINEMATIC_SKILL`; action hash `sha256:913799bf…a7e464`.
- **Segments:** 41 waypoints (pregrasp 2, approach 12, close_attach 1, carry 9, release 1, retreat 12, return_home 3).
- **Connectors:** RRT_JOINT for pregrasp, carry and return.
- **Grasp:** only 6 of 48 pick candidates are admissible, because t0 sits between o02 (3,4) and o04 (5,4) (41 grasp-pose rejections).
- **Release:** the object is placed with error 8e-16 m.

The trajectory, the gripper gap and the per-segment attachment mode are stored in `arrays.npz` (keys `G1_S1_t4__*`), and the scene is in `scene.json`.

---

## Full-clutter reference attempt (G0 illustrative scene, t0 at cell 55 → cell 36)

**CERTIFIED_INFEASIBLE**, scope `PLANAR_ARM_KINEMATIC_SKILL/DECLARED_GRASP_SET`. None of the 48 declared pick candidates survives:
- **26 have no IK.** t0 at (0.60, 0.52) is 0.79 m from the base, so only tool directions roughly pointing away from the base keep the wrist inside the 0.76 m annulus.
- **22 are certified grasp-pose collisions.** The arm cannot reach into the cluttered back-right region without links crossing occupied cells. Most frequent offending pairs: `link2|o01`, `link1|o09`, `link1|o14`.

Every rejection is definite (exact IK absence or a sampled definite violation), which is why the status is certified rather than unresolved.

**What this does not prove:** infeasibility for approach directions between the 15° steps, for curved approaches, or for other robot homes.

**Is a separately generated clutter-aware reference scene required?** **Yes.** The G0 illustrative scene was generated at random *without* a target action, so it was never meant to admit one. Methodology §3 and Guide G2/T00 require "a feasible *populated* reference scene S_ref" in which γ0 is planned *with the background present*. G1 adds two quantitative facts G2 must respect:
1. **Sweep zone.** Any object within 0.461 m of the base (22 cells, mainly columns 0–2) partitions link 0's reachable angles. Dense roots must keep the angles that γ0 needs clear on that side.
2. **Squeezed targets.** Targets boxed in by neighbours lose most of their declared grasp directions (nominal: 6/48).

A clutter-aware S_ref therefore has to be constructed around a verified γ0 (for example, populate only cells whose discs certify clear of γ0's swept envelope, then re-verify γ0 with the background present). That construction is G2 work; it is noted here, not implemented.

---

## E. Visualizations (all in `runs/g1_robot/`)

| File | What it shows |
|---|---|
| [`overview.png`](../runs/g1_robot/overview.png) | **(A) 64-cell audit.** A: complete-skill status per cell (OK/INF/UNR, colour plus text). B: number of grasp candidates with IK. C: … with a collision-free grasp pose. D: … with certified approach and closure, with a small tick for every certified tool-axis direction. The base and the home pose are drawn in every panel. |
| [`corners.png`](../runs/g1_robot/corners.png) | **(B) Corner tasks.** 12 panels (rows D0, S1, S2) showing obstacles, source (filled) and destination (dashed), the full recorded TCP trace (blue) and object trace (orange), robot ghosts at the end of approach and the end of carry, and the final robot at home. |
| [`corners_d0.gif`](../runs/g1_robot/corners_d0.gif), [`corners_s1.gif`](../runs/g1_robot/corners_s1.gif) | **(B) Animations.** 2×2 synchronised animations of the four corner tasks: full arm, housings, palm, rail, fingers, carried disc and growing traces, with the current phase labelled in each panel. |
| [`trace.gif`](../runs/g1_robot/trace.gif), [`skill.png`](../runs/g1_robot/skill.png) | **(C) Nominal six-phase skill** in S1 (36 → 19), animated with phase labels, plus a 7-panel filmstrip with the robot at the end of each phase. |
| [`diagnostics.png`](../runs/g1_robot/diagnostics.png) | **(D) Certification diagnostics.** A: a rejected grasp pose in clutter, offending pair in red (`link2\|o01`, d = −31 mm). B: a joint-linear segment whose **endpoints are both clear** but which collides at s = 0.5 (`link1\|o06`), found by the interval certifier. C: the link-0 sweep certificate, a red wedge showing every path sweeping link 0 through the target. D: an RRT search that exhausts its budget, its tree vertices drawn and labelled **UNRESOLVED, not a proof** (see note). |
| [`clutter.png`](../runs/g1_robot/clutter.png) | **(E) Full-clutter attempt.** A: all 48 declared pick candidates as rays at t0, coloured by verdict (all red = certified). B: representative rejected poses with highlighted offending pairs, plus stage and pair counts. |

**Diagnostics note on panel D.** The final run produced **no natural** budget-exhausted search, because every query resolved. Panel D therefore reruns a real query that the RRT solved (an S1 pregrasp connector) with the node budget **deliberately cut to 40**, and says so on the figure. It shows the key point: the *same* query is UNRESOLVED under a small budget and VERIFIED under the configured one, so exhaustion proves nothing.

**What to observe:**
- The fingers are now visibly joined by the rail.
- Carried discs follow curved, recorded paths, never grid edges.
- Connector swings of the arm are large but certified.
- Every frame stays inside the fixed axes, with no clipping.

**What the visuals do not prove:**
- dynamic feasibility, grasp stability or contact forces (kinematic scope only);
- optimality of any path;
- infeasibility beyond the declared grasp set.

The traces are the stored joint-linear segments themselves, never task-space interpolation.

---

## F. Scientific interpretation

**Established.** Within a 2D kinematic, layered-link abstraction, the specified 3R robot with a coherent connected gripper can perform certified grasp–carry–release with every body checked continuously:
- on all 64 cells and all four corners in the empty scene;
- in a designated sparse scene and a harder corridor scene.

Every reported success has been independently replayed. Failures are separated into:
- exact IK absence;
- certified collisions (pose, segment, sweep certificate);
- gray-band or budget UNRESOLVED.

That separation is the status discipline Methodology §8 requires before any learning.

**Connection to the methodology.**
- **Frozen action γ0 for G2.** A verified trajectory and its hash now exist: the nominal action hash. It records the full robot/gripper/attachment schedule from which G2's swept envelope ℰ0 will be built.
- **Two quantitative constraints for dense references.**
  1. **Sweep zone:** objects within 0.461 m of the base partition what link 0 can reach. This is a robot-intrinsic causal mechanism, worth exploiting carefully in G2 intervention design, because one blocker can act through link 0 alone.
  2. **Squeezed targets:** dense clutter collapses the admissible grasp set (nominal: 6/48).

**Not established:**
- any obstruction labels, envelopes, blockers or interventions (G2);
- executable *repair* sequences (G3);
- 3D anything (G7+);
- dynamic, controller or hardware success.

**Abstraction choices that need your confirmation:**
1. **Link layering.** The guide's adjacent-link exclusions (link0–link1, link1–link2) imply a layered (SCARA-like) arm whose adjacent links may overlap in the top view. All other pairs, and every robot–object pair, are tested.
2. **Carried disc stays on the support,** checked continuously. The robot itself may extend past the support edge (no walls in the 2D suite).
3. **Folded home `[π/2, π/2, π/2]`,** off the support. A side effect: link 0 must sweep down through the near-left table band to reach low rows, which is exactly where the sweep certificate applies.
4. **Declared grasp set:** 24 tool directions × 2 elbow branches with a 6 cm straight approach. Infeasibility claims are scoped to this set.

---

## G. Next-stage readiness

**G1 gate: PASS**, and the tested robot profile hash is frozen.

**G2 (next, not started):**
- plan and validate γ0 *with its background present*;
- freeze the full arm/tool/object envelope;
- build matched one-edit descendants that move an existing object into the sweep;
- test the action conflict and per-entity contributions under diagnostic removal and relocation;
- apply the single-margin oracle with three-valued factor aggregation;
- start with D1, then D2.

**Decisions needed before or at G2:**
1. **Confirm the G1 substitutions:**
   - the own RRT-Connect instead of OMPL;
   - the new home;
   - the finger rail and `grasp_center_x`;
   - the layered-link and support-containment interpretations;
   - the new module names `planner.py`, `skill.py`, `figures.py`.
2. **Construction of the clutter-aware populated reference.** As argued above, the G0 illustrative scene is not a valid S_ref for t0. G2 needs a construction rule that populates obstacles consistently with a verified γ0. The guide defines T00 only loosely ("dense reference physically populated before full 3R trajectory planning"). I propose: plan γ0 first in a sparse root, then populate only cells whose discs certify clear of ℰ0 by δ, then re-certify γ0 against the full background. Please confirm, or prescribe another rule.
3. **Undefined fixtures.** T01/T02/T06/T11 and C00–C07 (except C04) are still undefined in v1.4/v1.6. They are not needed for G2's D1/D2 development fixtures.

**Blockers:** none for starting G2.

---

## Repository synchronization

- Repository `https://github.com/Narendhiranv04/latent-causal-tamp`, branch `main`.
- This report is committed in the same commit as the G1 code, configuration, fixtures, tests and the `runs/g1_robot/` evidence (4.0 MB in total; largest file `corners_s1.gif` at 1.28 MB, so no LFS is needed).
- The commit hash and push result are given in the chat reply and recorded as "Previous turn sync" in report 0004 (convention of report 0002 §3).

**STOP — Awaiting explicit approval before proceeding to G2.**
