# 0004 — G1 hardening: sound failure labels, verified replay, G2 reference policy

| Field | Value |
|---|---|
| Report number | 0004 |
| Date | 15 October 2026 |
| Task | Targeted **G1 hardening** requested by the independent review `instruction-phase-md/G1_independent_review_and_next_prompt.md`. **G2 not started.** |
| Previous turn sync | report 0003 was committed as `f1651159f7292d0fdfcfb4c7616594fdb88b5ac9` on `main` and pushed to `origin/main` (remote head verified equal to local) |
| Baseline preserved | `runs/g1_robot/` (accepted G1 evidence) is **unmodified**; new evidence is in [`../runs/g1_hardening/`](../runs/g1_hardening/) |
| Verdict | **G1 is ready for G2** within its declared scope (planar, kinematic, declared grasp set); details in §9 |

**Inputs read before any change:**
- both authoritative PDFs (Methodology v1.4, Guide v1.6);
- the new review `instruction-phase-md/G1_independent_review_and_next_prompt.md`, read completely;
- `instruction-phase-md/G0_review_and_next_Claude_message.md`;
- reports 0001–0003;
- the G1 code, tests and run artifacts.

---

## 1. Outcome in one table

| Issue | Source | Status |
|---|---|---|
| A. A numerical IK-continuation jump was labelled certified, so it could be promoted to `CERTIFIED_INFEASIBLE` | review, correction A | **Fixed**: adaptive refinement plus three precise reasons; only exact ones count as definite |
| Planner budget, finite grasp set and numerical failures need correctly scoped outcomes | review, user item 2 | **Fixed / documented**: every rejection carries a stage, a reason, and definite or unresolved; budget stops say `NODES` or `WALL` |
| Continuous-verification assumptions | user item 2 | **Audited** (§5). Two unenforced assumptions are now enforced in replay and certify, with tests. |
| Wall-clock cutoff can change results under machine load | review, reproducibility caution | **Logged**: `wall_clock_cut` per connector, `wall_clock_dependent` per task, and `wall_clock_dependent_tasks` in `result.json`. Budget redesign deferred to the G2 protocol (§7), as the review instructs. |
| B. Dense reference construction for G2 | review, correction B | **Recorded and enforced**: `scene.validate_fixtures` rejects any G2+ fixture without an allowed policy and role. Not implemented beyond the guard. |
| Accepted G1 design (geometry, home, rail, offset, 2D abstractions, planner, modules) | user item 2 | **Preserved**: config hash and robot profile hash unchanged; planner pinned to the accepted behaviour by a golden test |
| Did earlier results change? | user item 4 | **No status changed.** 76/77 trajectories are bit-identical; 1 changed for an explained reason. 6 audit pick and 6 place candidates that were wrongly rejected as certified are now valid (§6). |

---

## 2. Problems identified (including two found during this task)

1. **Unsound "certified" label for IK-tracking failure (review A, confirmed).**
   - `motion.ik_track` returned `None` both when a required pose had no IK on the branch and when two neighbouring 5 mm samples differed by more than `max_ik_jump_rad = 0.1`.
   - `skill._fail` then stamped every such failure `IK_TRACK_DISCONTINUOUS` with `certified=True` (a last-minute G1 change of mine), and `skill._none_left` promotes all-certified candidate sets to `CERTIFIED_INFEASIBLE`.
   - A sampling artefact could therefore become a published infeasibility proof. This is concrete, not hypothetical: audit cell 1, φ = 315°, elbow −1 was rejected "certified" although its approach is smooth and valid (§4).
2. **Budget provenance.** Plans said only `BUDGET_EXHAUSTED`. With ~90 nodes/s, the 20,000-node budget can never bind before the 30 s wall cap, so every exhausted search was wall-clock-limited, and its outcome is load-dependent.
3. **Replay trusted part of the record.**
   - It never checked joint limits. Certification relies on waypoints being inside the (convex) joint box so that joint-linear segments stay inside.
   - It never checked that the stored grasp offset and placement match where the arm actually holds and releases the object.
   - `certify` assumed, without enforcing it, that the finger gap lies in [0, open_gap], which its finger speed bound relies on.
4. **IK at the reach boundary.** `ik` declared "no IK" whenever |cos q2| > 1 exactly, so a pose exactly on the boundary could be rejected by rounding.
5. **Found by a new test during this task:** my first `validate_fixtures` accepted a G2 fixture with neither policy nor role (`None == None`). Fixed before commit.
6. **A regression I introduced and caught during this task.** While adding stop-reason logging I accidentally deleted RRT-Connect's `trees.reverse()`. That silently changed the accepted planner into a one-sided variant. All 41 tests and both replays still passed, because every path stayed certified, so the planner remained *sound*. The old-vs-new **hash comparison** exposed it (8 extra RRT trajectories differed). It is restored, and a new golden test now pins the accepted planner's output.

---

## 3. Exact code corrections

| File | Change | Why (smallest sufficient fix) |
|---|---|---|
| `motion.py` | `ik_track` returns `(waypoints, reason)`. A step above `max_ik_jump_rad` is **bisected along the specified path** (pose interpolated linearly), up to `IK_REFINE_DEPTH = 12` levels (step/4096 ≈ 1.2 µm). Reasons: `NO_IK`, `JOINT_LIMIT_CROSSING`, `IK_CONTINUATION_UNRESOLVED`; `DEFINITE_IK_FAILURES = (NO_IK, JOINT_LIMIT_CROSSING)`. `ik_line`/`carry_line` pass `depth` through. | Separates exact facts from numerics; the review prefers compact refinement |
| `motion.py` | `check_record` (called by `certify_trajectory`) checks joint limits at every waypoint; the gap in [0, open_gap]; m against the phase schedule; the stored offset reproducing the object's resting pose at the first carry waypoint; and the stored placement at release (1e-9 m) | Replay must verify, not trust, the record |
| `skill.py` | `_fail(c, stage, v, why)`: geometry failures are definite only if `COLLISION`; IK failures only if `why ∈ DEFINITE_IK_FAILURES`. Explicit `NO_IK` reason at grasp/place poses; `CLOSURE_GEOMETRY` named. `summary` adds `rejection_reasons` (`STAGE:reason:definite|unresolved`) and `wall_clock_dependent`. | Sound labels; per-candidate provenance |
| `planner.py` | `_rrt_connect` returns the stop reason (`SOLVED`/`NODES`/`WALL`); `_shortcut` reports whether the wall cap cut it; `Plan.wall_clock_cut`; reason `BUDGET_EXHAUSTED:NODES|WALL`. **No search change** (verified by the golden test). | Label provenance only, as the review asks |
| `geometry.py` | `IK_BOUNDARY_TOL = 1e-12`: "no IK" only beyond rounding. `certify` raises if a gap is outside [0, open_gap]. | Soundness at boundaries |
| `scene.py` | `REFERENCE_POLICIES` + `validate_fixtures` (G2+ fixtures must declare an allowed `reference_policy`/`benchmark_role`) | Enforces correction B without implementing G2 |
| `run.py` | Fixtures validated on load; `check --no-figures` (re-certification runs do not duplicate unchanged visuals); `replay --report PATH` (no overwriting of historical runs); `wall_clock_dependent_tasks` in `result.json`; writes `ik_tracking.png` | Evidence without touching the baseline |
| `diagnostics.py` (new), `viz.py`, `figures.py` | The verdict-explanation figures (existing diagnostics/clutter panels plus the new IK-tracking figure) moved to `diagnostics.py`; panel primitives (`scene_panel`, `status_tag`, `STATUS`) moved to `viz.py` | Adding one figure would have pushed `figures.py` to 335 logical lines (> ~300). This is the guide's "split one separated responsibility" rule; the full G1 figure set was re-rendered to verify. |
| `README.md` | Module list; G2 reference-construction policy; budget semantics | Recorded policy |

No change to `config.toml`, `fixtures.json`, robot geometry, home, rail, grasp offset, contact model or planner search. The config hash `sha256:bcfd8bd2…a3bd0` and robot profile hash `sha256:2d798676…1ae858` are **unchanged**.

---

## 4. Mathematical justification and proof boundary

**Setting.** The specified path is the declared straight line: the tool point moves along the approach axis with φ fixed, on one elbow branch b. Along it, IK is the closed-form map g_b(pose):
- w = TCP − L3 u(φ);
- q2 = b·acos(c2);
- q1 = atan2(w) − atan2(L2 sin q2, L1 + L2 cos q2);
- q3 = φ − q1 − q2.

All are wrapped to [−π, π).

Inside the reach annulus (|c2| < 1) this map is continuous, **modulo 2π**, in the pose. Near the boundary its derivative grows like 1/√(1 − c2²), but it stays continuous. Consequently:

| Outcome after refinement | Claim | Sound because |
|---|---|---|
| `NO_IK` at a sampled or bisected pose | The specified straight path on branch b is impossible | Exact non-existence at a point the path must pass through (|c2| > 1 + 1e-12, or the solution is outside the joint limits) |
| `JOINT_LIMIT_CROSSING`: raw step > π but wrapped step ≤ max_jump at bisection depth 12 | Same scope | Between two poses about 1.2 µm apart, the continuous branch solution is close modulo 2π yet changes sign across ±π. The unwrapped joint angle must pass ±π, which lies outside the limits ±3.14159265. |
| `IK_CONTINUATION_UNRESOLVED`: any other step > max_jump at depth 12 | **Nothing**; the candidate is unresolved | A numerical limit, not a fact |
| Steps ≤ max_jump after refinement | The waypoints are accepted; the **executed** path is their joint-linear chain, certified segment by segment for collisions | `max_jump` only bounds how far that chain deviates from the ideal straight line. It is not a collision argument. |

**Proof boundary of `CERTIFIED_INFEASIBLE`** (scope `PLANAR_ARM_KINEMATIC_SKILL/DECLARED_GRASP_SET[+LINK0_SWEEP]`). The claim is that no candidate exists among:
- 24 tool-axis directions × 2 elbow branches;
- with a straight 6 cm approach/retreat;
- certified by exact IK and certified geometry;
- and, with `+LINK0_SWEEP`, no connector, by the link-0 sweep certificate.

It does **not** cover:
- approach angles between the 15° steps, or curved approaches;
- other homes or robots;
- dynamics.

A planner budget stop is always UNRESOLVED.

---

## 5. Audit of the continuous-verification assumptions

| Assumption used by `geometry.certify` | Holds? | Enforcement / evidence |
|---|---|---|
| Executed segments are joint-linear in (q, g) | Yes, by construction | Stored waypoints are the path; figures sample the same segments |
| Waypoints inside the joint limits, so segments stay inside the convex box | Yes | **New**: `check_record` in replay; IK filters limits; the RRT samples and steers inside the box |
| Bodies rigid in their frame; ρ_{b,k} = Σ L + max point distance (triangle inequality, any q) | Yes | `test_lipschitz_bound_is_sound` (exact distances, 12 long segments, with finger travel) |
| Same-frame pairs: shared rigid motion preserves distance | Yes | Same test; the self pairs are included |
| Finger speed ≤ \|Δg\|/2 with g ∈ [0, open_gap] (ρ computed at open_gap) | Was assumed | **New**: `certify` raises outside the range; `check_record` checks stored gaps; tested |
| Bounding-circle values far from contact are lower bounds, so interval bounds stay valid | Yes | Lower-bound argument (d(s) ≥ d̲(s0) − L\|s − s0\|) |
| Contact allowed only for fingers ↔ the scheduled object; m matches the phase | Yes | Phase-to-context table; m check in replay |
| The object is held where it rested and released where recorded | Was trusted | **New**: `check_record` (first carry waypoint, release), tamper tests |
| Classification bands δ ± ε (ε = 0.2 mm) are far above floating error | Yes | `test_world_collision_margin_and_gray_band` |
| A segment whose endpoints are clear may still collide | Detected | `test_swept_collision_between_clear_endpoints` (mutation-checked) |

---

## 6. Did earlier results change? (old `runs/g1_robot` vs new `runs/g1_hardening`)

**Replay of the stored G1 trajectories with the stricter replay** ([`replay_of_g1_robot.json`](../runs/g1_hardening/replay_of_g1_robot.json)): **77/77 pass**. All segments are certified, all hashes match, and all new record checks pass. The original `runs/g1_robot/` files are untouched (`git status` clean for that directory).

**Corrected rerun** (`python run.py check --out runs/g1_hardening --workers 24 --no-figures`): all five gates true, and replay of its own 77 trajectories passes ([`replay.json`](../runs/g1_hardening/replay.json)).

| Quantity | Accepted G1 | Hardened | Change |
|---|---|---|---|
| Query statuses (78) | 77 VERIFIED, 1 CERTIFIED_INFEASIBLE | identical | **none** |
| 64-cell audit | 64 VERIFIED | 64 VERIFIED | none |
| Clutter task (t0 → 36, G0 scene) | CERTIFIED_INFEASIBLE | CERTIFIED_INFEASIBLE | none. Its certificate rests on 26 exact `NO_IK` grasp poses and 22 certified grasp-pose collisions; it never depended on IK tracking. |
| Audit pick candidates (of 3072) | OK 1812, APPROACH 254 | OK **1818**, APPROACH **248** | 6 wrongly-rejected approaches now valid (cells 1, 4, 57, 60) |
| Place candidates, all tasks | OK 2058, RETREAT 300 | OK **2064**, RETREAT **294** | 6 wrongly-rejected retreats now valid (cells 3, 6, 59, 62) |
| `IK_CONTINUATION_UNRESOLVED` remaining | (did not exist) | **0** | every former "jump" resolved to OK, `NO_IK` or `JOINT_LIMIT_CROSSING` |
| Rejections, all tasks | — | 3305 definite / 14 unresolved | the 14 are gray-band geometry (δ ± ε), never promoted |
| Trajectory hashes | — | **76/77 bit-identical** | `G1_S1_t1` changed (below) |
| Nominal action hash | `sha256:913799bf…a7e464` | **identical** | — |
| Wall-clock-dependent tasks | not recorded | **none** | — |
| Determinism under another load (6 vs 24 workers) | — | all 78 statuses and hashes identical | — |

**Approach and retreat rejections now carry these exact reasons:**
- approach: `NO_IK` 137, `JOINT_LIMIT_CROSSING` 10, certified collision 140, gray band 4;
- retreat: `NO_IK` 118, `JOINT_LIMIT_CROSSING` 28, certified collision 144, gray band 4.

**The one changed trajectory: `G1_S1_t1`** (S1 corner 7 → 63). Its carry uses the **object-pose RRT**, whose edges are built by `ik_track`. With refinement, some edges that previously failed on a sampling jump are now admitted, so the deterministic search differs. Its pick and place candidates and connector method are the same, and the new certified path has 282 waypoints instead of 304. Still VERIFIED, and replayed.

**Note on the earlier `G1_S2_t0` wall-clock flag.** An intermediate rerun flagged it. That flag came from the accidental tree-swap deletion in §2 item 6, and disappeared once the accepted planner was restored. The structural point stands: no 2D search can reach `max_nodes` before the wall cap.

---

## 7. Policies recorded for G2 (not implemented here)

**Reference construction** (README, enforced by `scene.validate_fixtures`):
1. **Primary: `FINAL_DENSE_PLANNED` / `PRIMARY`.**
   - Choose the target, source/goal and a structured 30–40-object layout first; reject invalid support/start poses.
   - Plan the complete grasp/carry/release/retreat/connector **in that final dense snapshot** with the existing planner (honest UNRESOLVED).
   - Independently certify, then freeze the trajectory and its phase/contact hash. A feasible witness is required before any failure variant.
   - Measure safe cells, density, path curvature, closest clearance and path-shaping clutter. Regenerate the root rather than silently lowering density.
   - Create blocked variants only by **relocating existing IDs** into cells intersecting the frozen full arm/tool/held-object sweep, preserving one-edit ancestry.
   - Verify object-specific collisions independently of corrective-motion existence.
   - Start with D1 and D2.
2. **`SPARSE_SEEDED_REFERENCE` / `BOOTSTRAP_ONLY`** (plan sparse, fill cells clear of the sweep, re-verify): allowed as a labelled development/diagnostic fallback only. Never a primary benchmark claim, because it biases the clutter away from the path.

**Budgets.** The canonical budget must be a node/evaluation budget that actually binds: G1 measured about 90 nodes/s, and successful searches needed at most 2,260 nodes. The wall time stays a generous safety cap. The proposal for G2 is to calibrate `max_nodes` (e.g. about 3,000) below a much larger wall cap, and to have the gate refuse canonical data with `wall_clock_dependent` true. G1's accepted budgets are unchanged in this response.

---

## 8. Tests and evidence (commands actually run)

| Command | Result |
|---|---|
| `python -m pytest tests -q` | **42 passed** (15 G0 + 27 G1) in 14.2 s |
| `python run.py replay --run runs/g1_robot --report runs/g1_hardening/replay_of_g1_robot.json` | `replay_passed: true`, 77 trajectories |
| `python run.py check --out runs/g1_hardening --workers 24 --no-figures` | exit 0, all gates true |
| `python run.py replay --run runs/g1_hardening --report runs/g1_hardening/replay.json` | `replay_passed: true`, 77 trajectories |
| `python run.py check --out <scratch>/g1_load6 --workers 6 --no-figures` | all 78 statuses and hashes identical to the 24-worker run |
| Full figure run to scratch (`check` with figures) | all G1 figures re-render through the refactored modules (not committed; the baseline visuals are kept) |

**New regression tests:**

| Test | Guards |
|---|---|
| `test_refinement_resolves_a_jump_the_old_tracker_called_infeasible` | cell 4, φ 90°, elbow −1: the old fixed-step tracker gives `CONTINUATION`; refinement gives a valid line with all steps ≤ 0.1 rad |
| `test_ik_track_definite_reasons` | exact `NO_IK` (sampled and between samples); `JOINT_LIMIT_CROSSING`; `CONTINUATION` is not definite |
| `test_restrictive_jump_threshold_never_certifies_infeasibility` | review-mandated: `max_ik_jump_rad = 1e-7` makes every approach fail numerically. The skill is **UNRESOLVED**, and every such candidate is uncertified with reason `IK_CONTINUATION_UNRESOLVED`. The old code gave CERTIFIED_INFEASIBLE. |
| `test_ik_on_reach_boundary_is_not_declared_missing` | straight-elbow pose solved; a pose 1 µm outside is not |
| `test_wall_cap_is_recorded_as_load_dependent` | zero wall budget → `BUDGET_EXHAUSTED:WALL`, `wall_clock_cut` |
| `test_link0_sweep_certificate_and_unresolved_budget` (extended) | node budget → `BUDGET_EXHAUSTED:NODES`, not load-dependent |
| `test_replay_rejects_inconsistent_records` | tampered waypoint beyond limits, gap beyond open, moved placement, wrong grasp offset → rejected; `certify` rejects a gap outside [0, open_gap] |
| `test_rrt_connect_matches_accepted_g1_planner` | golden lock: certified RRT-Connect path hash equals the accepted G1 planner's (`sha256:4c86c080…c594`, computed from commit `f165115`) |
| `test_g2_reference_policy_is_enforced` (`test_scene.py`) | allowed policy/role pairs pass; missing, mismatched or unknown ones are rejected |

**Mutation checks** (each test fails on the mutant and passes on the fix):
- `CONTINUATION` counted as definite (the old semantics) → 2 tests fail;
- refinement disabled → the refinement test fails;
- replay without the joint-limit check → the replay test fails;
- `trees.reverse()` removed → the golden test fails.

---

## 9. Visualization

[`../runs/g1_hardening/ik_tracking.png`](../runs/g1_hardening/ik_tracking.png) is the only new figure. The baseline G1 visuals were not regenerated.

The examples are selected automatically from the real audit: the first candidate of each kind whose label changed.

- **Top row:** joint angles q1, q2, q3 along the declared approach, both from the fine continuous branch solution (gaps would mean no IK) and at the 13 fixed 5 mm samples the old tracker used. The dotted lines are ±π.
- **Bottom row:** for each old sample gap, the largest joint step (log scale) against the dashed `max_ik_jump_rad`. Red bars exceed it.
- **Left (audit cell 1, φ 315°, elbow −1).** A perfectly smooth approach, where the first 5 mm step moves a joint 0.110 rad, just over 0.1. The old code called it certified infeasible; it is **valid**. This is exactly the label error the review predicted.
- **Right (audit cell 18, φ 330°, elbow +1).** q3 crosses ±π (a 6.19 rad step between the 3rd and 4th samples). The jump is real: the straight approach on this branch would leave the joint limits, so it is now `JOINT_LIMIT_CROSSING`, definite within its scope.

**What it does not show:** anything about other approach curves. Labels are scoped to the declared straight approach.

---

## 10. Files, line counts and hashes

Logical lines exclude blanks, comments and docstrings.

| File | Physical / logical | SHA-256 |
|---|---|---|
| `scene.py` | 408 / 287 | `66cb3337aa944911237c131e9b91b8b12345c8bb772ac4f70428fb3886b25f8a` |
| `geometry.py` | 362 / 247 | `69e753e1e1aa0b1897a15603c0c4d091b7f23272881e76284dc73bc2d85b90d4` |
| `motion.py` | 223 / 147 | `7790dd6174d424fb7cb1016440e5bfc5c39b6b51d8ab4b8de2d0fdb4cd47811d` |
| `planner.py` | 252 / 181 | `0f01d2319940037f8564672ac400cf869a192b02e74ae945d208fa9a41fe43db` |
| `skill.py` | 280 / 226 | `c561c5bfab768b4f73f6a61e9ba37db09f8cf847a5a621c1dcf51db61d53d66f` |
| `viz.py` | 284 / 205 | `cd14ee08ae2f7df5bf9b7a76881205088d104dad03381d77d375e55756676959` |
| `figures.py` | 189 / 150 | `bb52e4b4c025ffa86d91f589985405c7da0b4664465748ff6b3f96bc90650d20` |
| `diagnostics.py` (new) | 215 / 174 | `d28f5f701af75334b3c1e6d72ce1043907db4fab2ec3ed4c5afe100eb37137e6` |
| `run.py` | 297 / 246 | `bf3bb7ca8563d11fc3ddfe1305f520ac08ef04ac21206f16df38ca984b631b24` |
| `tests/test_scene.py` | 207 / 157 | `9fc0fac8a8308252167732afcd27a8c6e79d0b8e091b4f4337a1144ae940c9ac` |
| `tests/test_arm2d.py` | 299 / 221 | `8c7993ff8a4cc491bf39f92b62d2e4eaadeb3ae81c364fc1448ac533d522ba2a` |

- `config.toml` and `fixtures.json` are unchanged (`230bd3b0…`, `e03536cd…`).
- Diff against `f165115`: +321 / −227 lines across 11 tracked files, plus `diagnostics.py`, `runs/g1_hardening/` (544 KB) and this report.
- **Size watch:** `scene.py` (287) is the largest module. If it grows at G2, its config schema moves to `config.py`.

---

## 11. Remaining limitations

1. **Scope.** All claims are `PLANAR_ARM_KINEMATIC_SKILL`: a 2D layered-link kinematic abstraction. There is no dynamics, contact force, grasp stability, simulation replay or hardware evidence (`NOT_RUN`).
2. **Declared grasp set.** Infeasibility is scoped to 24 directions × 2 branches with straight approaches.
3. **Gray band.** 14 rejections in the gray band are reported as unresolved, never certified.
4. **Wall-clock budgets.** The accepted G1 budgets still let the wall cap bind before `max_nodes`. Search stops are now labelled, and no G1 result was affected, but canonical node-bound budgets are a G2 calibration (§7).
5. **IK refinement depth.** `IK_REFINE_DEPTH = 12` is a numerical resolution constant in code, not in config, so that historical run configs remain replayable. Its exhaustion is always UNRESOLVED.

---

## 12. Verdict: is G1 scientifically and computationally ready for G2?

**Yes, within the declared scope:**
- Every definite (`CERTIFIED_INFEASIBLE`) label now rests only on exact IK non-existence, exact joint-limit crossing, certified geometry, or the proven link-0 sweep certificate.
- Numerical continuation, gray-band and budget outcomes are UNRESOLVED, with their reason and their load dependence recorded.
- Replay independently re-derives everything from the stored record, including limits, gaps, attachment and placement.
- The accepted design and planner are preserved (golden-locked).
- No earlier G1 classification changed. 12 candidate-level labels that were wrongly certified are corrected. Results are deterministic across machine loads.
- The G2 reference rule (final dense scene first; sparse-seeded only as a labelled bootstrap) is recorded and enforced at fixture load.

**No blockers.** The G2 budget calibration in §7 is the first G2 task, not a G1 defect.

---

## Repository synchronization

- Repository `https://github.com/Narendhiranv04/latent-causal-tamp`, branch `main`.
- This report, the code and test changes, `diagnostics.py`, the review file under `instruction-phase-md/` and `runs/g1_hardening/` are committed together.
- The commit hash and push result are given in the chat reply and recorded in report 0005.

**STOP — Awaiting explicit approval before starting G2.**
