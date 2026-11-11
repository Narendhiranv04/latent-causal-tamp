# 0006 — G3 completion report: analytic endpoint assignment and executable move-once repair verification

| Field | Value |
|---|---|
| Report number | 0006 |
| Date | 16 October 2026 |
| Stage | **G3** (Guide v1.6 §5). The scope is A0 terminal assignment, executable move-once repair, and the restricted-domain control. **G4 not started.** |
| Instruction file | `instruction-phase-md/G2_independent_review_and_G3_prompt.md` (read in full) |
| Previous turn sync | Report 0005 was committed as `9d3d7c88274fb3e473e485f38186a419466568c0` on `main` and pushed to `origin/main`; the remote head was verified equal to the local head. |
| Run directory | [`../runs/g3_repairs/`](../runs/g3_repairs/) (`python run.py solve --out runs/g3_repairs`, 23 min 11 s wall) |
| Outcome | **Every G3 fixture has a verified result. None is unavailable or unresolved.** D1, D2 and D3 and the **dense 35-obstacle T07** each have an executed, independently replayed move-once witness whose move count equals the A0 lower bound (**MINIMUM_CERTIFIED**). Both restricted-domain controls are **CERTIFIED_TERMINAL_INFEASIBLE**, each with a checked Hall certificate. |
| Scope | 2D layered-link **kinematic** verification of the full 3R body, gripper, carried disc and connectors, over a finite declared grasp family, with seeded planners. There are no dynamics, no simulation and no hardware. |
| Tests | **74 passed** (G0 15, G1 27, G2 11, G3 matching 12, G3 verify 9) in 62 s. 12 mutation checks: 11 killed; 1 survivor is explained in §6. |
| Replays | `g1_robot` 77/77, `g1_hardening` 77/77, `g2_interventions` 2/2 and `g3_repairs` 50/50 trajectories re-certified, all with hashes matching. The archived G0–G2 run directories are byte-unchanged. |

**Inputs read before coding:**
- `G2_independent_review_and_G3_prompt.md` in full;
- the Methodology v1.4 sections §7 (terminal problem, restoration lemma), §7.1–7.2, §8 and §10, and Guide v1.6 §5 G3 (T07/F8);
- the earlier instruction files and reports 0001–0005;
- the G0–G2 code, tests and archived runs.

---

## 0. Plan as stated before implementing

1. **`solve.py` (A0).** The terminal problem uses all present obstacles over physical cell IDs, with stay cost 0 and move cost 1.
   - It is solved as an exact bipartite matching (identical discs, pitch > 2r + δ) with SciPy `linear_sum_assignment`.
   - It provides Murty k-best, a Hall certificate when infeasible, the restoration-lemma witness, a forced-destination variant, and a published restricted domain.
2. **`verify.py`.** A repair is a list of (real ID, physical cell) pairs in order.
   - Each relocation is the existing six-phase G1 skill, planned **from the achieved scene and achieved q, g**.
   - The moved history is enforced; the last relocation's connector ends exactly at γ0's pinned start.
   - The final check replays the unchanged frozen γ0 through the G2 oracle.
   - The search runs over the k-best assignments × orders under an explicit budget, with LB / UB / minimality accounting.
3. **Fixtures:**
   - D1 and D2 come read-only from `runs/g2_interventions`.
   - D3 is a new development root with an access dependence.
   - The T07 development proxy is labelled as such.
   - Dense T07 has 35 obstacles, with γ0 planned in the dense scene.
   - Each fixture also gets a forced occupied-destination chain.
4. **Visuals A–F**, built only from stored trajectories. Rejected moves are drawn with their first certified offence.
5. **Tests** with negative cases, then mutation checks, then all G0–G2 tests and replays.

---

## A. Stage objective and outcome

G3 asks two questions. First: can the real articulated robot, **starting from the blocked state**, execute an ordered sequence of relocation skills, reconnect to γ0's exact start, and replay the **same frozen γ0**? Second: what can be **proved** about the minimal number of moved objects?

### Result table (from `runs/g3_repairs/result.json`, also in `metrics.csv`)

| Fixture | Domain | \|D\| | LB (A0) | Best verified UB | Minimality | Status | Stop | Relocation plans | Attempts (exec / rejected / pruned) | Replay |
|---|---|---|---|---|---|---|---|---|---|---|
| G3_D1 | ALL_SUPPORTED | 1 | 1 | 1 | **MINIMUM_CERTIFIED** | EXECUTABLE_VERIFIED | WITNESS_FOUND | 1 | 1 / 0 / 0 | pass |
| G3_D2 | ALL_SUPPORTED | 2 | 2 | 2 | **MINIMUM_CERTIFIED** | EXECUTABLE_VERIFIED | WITNESS_FOUND | 2 | 1 / 0 / 0 | pass |
| G3_D3 | ALL_SUPPORTED | 2 | 2 | 2 | **MINIMUM_CERTIFIED** | EXECUTABLE_VERIFIED | WITNESS_FOUND | 3 | 1 / 1 / 0 | pass |
| G3_T07_DENSE | ALL_SUPPORTED | 5 | 5 | 5 | **MINIMUM_CERTIFIED** | EXECUTABLE_VERIFIED | WITNESS_FOUND | 24 | 1 / 14 / 187 | pass |
| G3_T07_DENSE | RESTRICTED | 5 | none | — | NOT_APPLICABLE | **CERTIFIED_TERMINAL_INFEASIBLE** | Hall: \|U\| = 5 > \|N(U)\| = 4 | — | — | — |
| G3_T07_PROXY | ALL_SUPPORTED | 2 | 2 | — | — | NOT_RUN (terminal-only; same scene as D2) | — | — | — | — |
| G3_T07_PROXY | RESTRICTED | 2 | none | — | NOT_APPLICABLE | **CERTIFIED_TERMINAL_INFEASIBLE** | Hall: \|U\| = 2 > \|N(U)\| = 1 | — | — | — |

The three labels are reported separately everywhere:

- **Proven minimum** (`MINIMUM_CERTIFIED`) means LB = UB.
- **Best verified moves** is the UB of an executed witness.
- **Unresolved** covers the finite-search outcomes. Every rejected order in the attempt lists below is labelled `UNRESOLVED` at the attempt level, never "impossible", even when its first offence is a certified scoped blockage.

### Guide G3 gates

| Gate | Evidence | Result |
|---|---|---|
| A0 exact on small cases vs. complete enumeration | `test_matching_equals_exhaustive_optimum` (300 random cases), `test_exhaustive_small_case_audit_of_a0_on_a_real_status_map` | pass |
| k-best distinct, correct, ties included | `test_kbest_matches_exhaustive_with_ties_and_no_duplicates`: 200 random cases plus a 24-way tie | pass |
| Hall certificate finite and checkable | `test_hall_certificate_is_checkable_proof` (independent `check_hall` plus tampering) | pass |
| Restoration theorem: optimum = \|D\| | `test_restoration_lemma_optimum_equals_direct_blockers` (40 families); premise-failure negative test | pass |
| Real relocations from the achieved state, move-once, exact γ0 start, unchanged γ0 | `test_verify.py` (9 tests) and `replay_repair` per witness | pass |
| LB/UB accounting with no false minimum | `test_failed_order_keeps_first_offence_and_is_not_a_proof`, `test_bounds_and_budget_never_overclaim` | pass |
| D1/D2 reused from the archive; D3 order dependence; T07 paired control; occupied destination | §4 | pass |
| G0–G2 regression and replays | 53 earlier tests; 4 replays | pass |

---

## 1. Formulation (what is implemented)

**Terminal state.** Methodology §7. Every present obstacle i takes one physical cell x_i from its declared domain Dom_i. Its current cell means "stay". A terminal state is **TERMINAL_VALID** iff, for every obstacle, three conditions hold:
- y^a = 1: the disc at that pose is clear of the frozen γ0 (robot bodies plus the target at rest, carried and placed), from the G2 oracle `motion.object_check`;
- y^w = 1: the disc is fully on the support;
- y^p = 1: every pair is compatible.

**A0 objective.** Minimize the number of distinct moved IDs, Σ_i [x_i ≠ current_i] (stay cost 0, move cost 1).

**Reduction to matching (exactness scope).** All obstacles are identical discs (r = 0.024 m) and rest on cell centres of a uniform grid with pitch 0.08 m > 2r + δ = 0.053 m.
- Two **distinct** cells are therefore always pair-compatible, so y^p is exactly "at most one object per cell".
- y^a and y^w for a disc at a cell do not depend on which identical disc it is, so they are computed **once per physical cell** (`solve.cell_status`).
- The terminal problem is therefore *exactly* a min-cost bipartite matching (objects × cells).
- `solve.check_reduction` raises `ReductionInvalid` if radii differ, if pitch ≤ 2r + δ, or if an object is off-lattice. A test confirms it fires.
- Nothing is double-inflated: δ is applied once, inside the oracle.

**Index conventions.** Matching columns are **physical cell IDs** (`r*8 + c`, global and stable). The "stay" edge of object i is its own current physical cell. G0's per-object candidate index k = 0 is not used in A0, so the two indexings cannot be confused. `test_a0_includes_every_obstacle_with_physical_ids` checks the mapping.

**Edges and bounds.**
- VALID cells give **witness** edges.
- VALID ∪ UNRESOLVED cells give the **optimistic** problem, whose optimum is a sound **lower bound LB**: no terminal-valid assignment can be cheaper.
- In all G3 fixtures, every cell status is decided (0 UNRESOLVED cells), so LB equals the witness-edge optimum.

**Cost.** C[i, j] = 0 for staying, ∞ if the edge is not allowed, and 1 + w·dist/d_max for moving, with w = 1/(n+1).
- The integer part is the moved count. n moves add at most n/(n+1) < 1 in tie-break total, so lexicographic minimization never changes the A0 objective. `test_lexicographic_tie_break_never_changes_the_moved_count` compares against a pure 0/1 cost.
- The carry-distance term only **orders equal-move assignments**. Without it, D3's k-best list consisted entirely of far, low-ID ties (cells 0–4); that variant is kept as an explicit comparison (§4.3).
- The tie-break uses geometry only. It has no access to intervention histories, so A0 sees no teacher answers.

**Solver.** `scipy.optimize.linear_sum_assignment` (SciPy **1.16.3**, recorded in `result.json` `solver` and pinned in `requirements.lock`). Infeasible matrices raise `ValueError` and are mapped to "no assignment". No brute force is run on the 35-object grid; enumeration is used only as the test oracle and refuses large cases.

**k-best: Murty's partitioning** (`solve.kbest`).
- From each popped solution with assignment a, child t fixes rows < t to a's choice and forbids (t, a_t). This is the **no-good** that excludes exactly that solution from the child's subspace.
- Subspaces are disjoint and cover everything except the popped solution, so the output consists of **distinct complete assignments** in nondecreasing cost.
- Ties come out in deterministic discovery order (heap key (cost, counter)).
- The output is checked against complete enumeration, including cost sequences with ties, a 24-way all-tie case, and impossible domains.
- k = 12 (`[repair2d] k_best`).

**Hall certificate** (`solve.hall_certificate`). A Kuhn maximum matching finds an unmatched object, and alternating reachability from it gives U (objects) and N(U) (all cells adjacent to U) with |N(U)| < |U|. `solve.check_hall` independently recomputes N(U) from the matrix and checks the inequality.

**Restoration lemma (Methodology §7): b*_terminal = |D|.** Here D is the set of obstacles whose current cell is action-invalid (the direct blockers). The lemma holds when the blocked state came from a valid reference by relocating existing IDs, every blocker's reference cell is still vacant, action-clear and supported, and those cells are distinct. Proof of the two inequalities:

- **(≥)** A direct blocker's current cell is INVALID, so its stay edge is absent from both the witness and the optimistic problem. Every blocker must move, so any terminal-valid assignment moves at least |D| objects.
- **(≤)** Sending exactly the blockers back to their reference cells, with everything else staying, is terminal-valid:
  - the reference cells were VALID for the frozen action and are still vacant and distinct;
  - the non-blockers' current cells are VALID by the definition of D;
  - identical discs keep y^p.

  This assignment uses exactly |D| moves.

`solve.restoration` builds this witness and verifies the premises, returning `terminal_valid = False` if any fails. When the premises fail, the theorem is not claimed (`test_restoration_rejected_when_its_premises_fail`). In all four executed fixtures the premises hold and A0's optimum equals |D| (1, 2, 2, 5).

---

## 2. Executable move-once verifier (`verify.py`)

A **repair candidate** is a tuple ((ID, physical cell), …) in order. It is never an `apply_edit` transition.

1. **`relocate(state, id, cell)`** calls the G1 six-phase skill `skill.plan_skill`. The only extension is `q_start`/`q_goal` (§B); collision physics and the robot class are not duplicated.
   - Planning starts from **`state.q`** in **`state.scene`**, which contains all current objects at their achieved poses.
   - Approach, closure, attachment, fixed-plane carry, release and retreat are certified for the whole body (links, housings, palm, rail, fingers and the carried disc) against every other object and the support.
   - Non-final relocations end after `retreat` (`q_goal=None`), so the next skill starts exactly where this one stopped. **There is no hidden reset to home.**
2. **Achieved state update.** On VERIFIED, the moved object takes the skill's **achieved** `place_xy`; q and g come from the last record waypoint, and the ID is appended to `moved` (the history H).
   - A second move of an ID returns `MOVE_ONCE_VIOLATION` without planning.
   - The scene, root, frozen action hash and episode key are carried in `RepairState`.
3. **Last relocation.** Its connector ends at **exactly `frozen.arrays["q"][0]`** (`q_goal = q0`, with the gripper open as at γ0's start).
4. **Final check** (`execute`). `interventions.evaluate` replays the **unchanged frozen γ0** in the final achieved scene. The status is `EXECUTABLE_VERIFIED` only if:
   - F_fixed = VALID,
   - the whole-scene replay is VALID,
   - q equals q0 bit-for-bit,
   - g equals γ0's initial gap.
5. **Failures.** The first failing relocation, its index, the skill status and reason, and all pick/place candidates with their first offending pair are kept (`Attempt.stop/reason/skills`). They are drawn in figures B–E.
6. **`replay_repair`** independently re-checks an episode:
   - `frozen.verify()` (hash);
   - each relocation record re-certified in its own pre-move scene;
   - exact q and g continuity at every record start and end;
   - the achieved pose equals the record's `place_xy`;
   - move-once history;
   - the final state at γ0's q0 and g0;
   - F_fixed and whole replay VALID.

**Search** (`verify.search`). The outer loop runs over the A0 k-best certified-valid assignments in nondecreasing cost; the inner loop runs over the move orders of each.

- **Budgets** (`[repair2d]`):
  - `k_best = 12`;
  - `max_orders = 6` non-dominated orders per assignment;
  - `max_relocations = 40` skill plans per search, checked before each order (an order in progress may finish its remaining relocations);
  - `skill_plan_failures = 2`: carry/connector query failures per skill before it returns `UNRESOLVED PLANNER_BUDGET`. G1 used 3, so this is a tighter per-skill cap.
- **Memo.** The memo is keyed by the exact executed prefix (and whether its step is final). Within one run, the same prefix from the same start state with the same seeded key always yields the same result, so the memo only avoids recomputation.
  - It never turns an `UNRESOLVED` into a proof: attempts that hit a failed prefix keep their own `UNRESOLVED` status.
- **Pruning.** An order whose prefix already failed would replay that identical memoized failure. `fresh_orders` counts such orders as **pruned** and does not charge them to the order budget (dense T07: 187 pruned).
  - This fixed a real defect found during development: `itertools.islice(permutations, 6)` only ever varied the last three of five moves, so all 72 dense attempts reused **one** failed first relocation.
- **Bounds:**
  - LB comes from A0's optimistic optimum;
  - UB is the move count of the first executable witness (assignments are visited in nondecreasing cost);
  - `MINIMUM_CERTIFIED` iff UB = LB;
  - `NOT_APPLICABLE` if a Hall certificate exists;
  - otherwise `MINIMUM_UNRESOLVED`, with `stop_reason` ∈ {`WITNESS_FOUND`, `RELOCATION_BUDGET`, `SEARCH_SPACE_EXHAUSTED`}.
- **Wall-clock.** The wall-clock cap (300 s per planner query) is a safety limit only. Every attempt records `wall_clock_dependent`. All witnesses and all search attempts recorded `false`; one dense comparison attempt (`o25→51` first, `PLANNER_BUDGET`) recorded `true`.

---

## 3. Fixtures

| Fixture | Policy / role | Origin | Obstacles | Direct blockers |
|---|---|---|---|---|
| G3_D1 | FINAL_DEV_SCENE_PLANNED / DEVELOPMENT_ONLY | **archived** `runs/g2_interventions` G2_D1 / `block_a` (read-only; frozen hash re-verified) | 4 | o02 (cell 51) |
| G3_D2 | same | **archived** G2_D2 / `block_ab` | 6 | o02 (57), o05 (50) |
| G3_D3 | same | **new** `root_d3`: γ0 = t0 20 → 44, planned with obstacles at [5, 9, 31, 58, 63] present; then privileged blocking edits o00 5→28, o01 9→27 | 5 | o00 (28), o01 (27) |
| G3_T07_PROXY | same, explicitly a **DEVELOPMENT PROXY (not dense)** | archived D2 `block_ab` | 6 | o02, o05 |
| G3_T07_DENSE | **FINAL_DENSE_PLANNED / PRIMARY** | **new** `root_t07`: 35 obstacles on every cell outside the link-0 sweep zone except the nearest one; γ0 = t0 0 → 34 **planned and certified with the 35-obstacle background present**; then five existing IDs relocated into the frozen sweep (G2 rule): o30 59→57, o25 51→40, o26 52→48, o21 44→49, o00 3→8 | 35 | o00, o21, o25, o26, o30 |

Frozen γ0 hashes:
- D1: `sha256:487ec18878068e01501c6737f1c58ec4cd1b9e410560bd4d8f7f8c32c5784355`, identical to the G2 archive.
- D2 / proxy: `sha256:27cb5a04f8caac257dc622bbe3fc32e460de092928e2b64701152bb79a99295f`, identical to the G2 archive.
- D3: `sha256:6f3dfb6948f35e7e1f82cba38cbc5732a27009bf978efacce6c572b18e0b566e`.
- Dense T07: `sha256:d3cbc6fd1d312f4c1c1ee1518cc43da780cbfd01b21550fffe304efdc4c3368d`.

**D3 selection criterion (stated before execution).** These conditions were checked during construction with the robot's grasp screening:
- o00 has **no admissible grasp while o01 is present**, and all those rejections are definite;
- o01 is graspable;
- o00 becomes graspable once o01 has gone.

The order claim itself comes only from the executed full-arm paths below, not from that screen.

**Candidates rejected during construction** (scratch probes, not committed):
- D3 variants "c" and "f": their reference γ0 stayed `UNRESOLVED` (planner budget) in the final scene, so no frozen action could exist.
- In G2, D2a was unresolved (report 0005).

No archived G2 record was altered.

---

## 4. Results per fixture (all from `runs/g3_repairs/result.json`)

Every outcome below is a real robot attempt. "Rejected" names the first failing relocation and its first certified offence. Such an attempt is never an impossibility claim for the assignment.

### 4.1 D1 (archived G2 blocked state)

- **A0 cell status:** 18 INVALID cells, 45 VALID, 0 UNRESOLVED.
- **Direct blockers:** D = {o02}, so LB = 1.
- **k-best:** 12 assignments, all with cost 1. Rank 0 is o02→43 (tie-break 0.0177); rank 1 is o02→50 (the same tie-break).
- **Search:** rank 0, order (o02→43), is **EXECUTABLE_VERIFIED** after 1 plan. UB = 1, so **MINIMUM_CERTIFIED**. The replay passed with H = [o02].
- **G2 diagnostic correction endpoint** (o02→43) is **robot-executable** (EXECUTABLE_VERIFIED). A0 independently chose the same cell because it is the nearest action-clear cell.
- **Reference restoration** (o02→50, the lemma witness) is also EXECUTABLE_VERIFIED.
- **Occupied preferred destination.** o02 is forced into o03's cell 60, so o03 must also move (A0 cost 2, LB still 1):
  - o02 first: rejected at relocation 1, `CERTIFIED_INFEASIBLE NO_PLACE_CANDIDATE` (o03 still occupies cell 60: 38 of the 48 declared place candidates collide first with o03, the other 10 have no IK);
  - o03→61 first, then o02→60: **EXECUTABLE_VERIFIED** with 2 moves.

  This gives UB = 2 for that forced assignment, but it is **not** a minimum claim, since the unrestricted LB is 1 and is unchanged.

### 4.2 D2 (archived; two independent blockers)

- **A0:** D = {o02, o05}, LB = 2.
- **Rank 0** is o02→49, o05→41, which coincides with the G2 diagnostic endpoints; the geometric tie-break picked it, not intervention data.
- **Search:** order (o02→49, o05→41) is **EXECUTABLE_VERIFIED** after 2 plans. UB = 2, so **MINIMUM_CERTIFIED**. H = [o02, o05], and the replay passed.
- **G2 diagnostic endpoints:** both orders executable.
- **Reference restoration** (o02→40, o05→49): both orders executable.
- **Why the diagnostic fix of A alone is not an executable A-then-B repair.**
  - G2 cleared each blocker by a privileged edit on a frozen snapshot. That shows the *terminal* effect, not that the robot can reach, grasp, carry and release each object, from the state left by the previous move, without hitting anything.
  - Executability depends on the order and on where things end up. The forced-destination chain shows this: o02 forced into o03's cell 61 (A0 cost 3, LB still 2).
    - Both orders that move o02 *before* o03 are rejected at the o02 relocation with `CERTIFIED_INFEASIBLE NO_PLACE_CANDIDATE`.
    - The three orders that clear o03 first are all EXECUTABLE_VERIFIED.
    - One order was pruned, because it shared the failed prefix.

### 4.3 D3 (new root; order and access dependence)

- **A0:** D = {o00, o01}, LB = 2. Rank 0 is o00→29, o01→18.
- **Same assignment, two orders:**
  - **o00 first** is rejected at relocation 1: `CERTIFIED_INFEASIBLE NO_PICK_CANDIDATE`. All 48 declared grasp candidates failed with definite reasons (GRASP_POSE ×46, APPROACH ×2). Counts of first offending pairs: o01 ×21, t0 ×10, o00 itself ×5, o03 ×5, o02 ×2.
  - **o01→18 first, then o00→29** is **EXECUTABLE_VERIFIED**. H = [o01, o00]; the second skill starts exactly at the first skill's retreat end (tested).

  UB = 2, so **MINIMUM_CERTIFIED**.
- **Alternative endpoints** (comparison: the "low-ID" assignment o00→0, o01→1, i.e. A0 ties broken by cell ID instead of carry distance):
  - o00 first: NO_PICK (as above);
  - o01→1 first: `CERTIFIED_INFEASIBLE ALL_CONNECTORS_CERTIFIED_BLOCKED`.

  The A0 terminal cost is the same (2), but the motion outcome differs.
- **Reference restoration** (o00→5, o01→9; TERMINAL_VALID by the lemma):
  - o00 first: NO_PICK;
  - o01 first: o01→9 is verified, then o00→5 returns **`UNRESOLVED PLANNER_BUDGET`**.

  This is a case of **TERMINAL_VALID but not EXECUTABLE_VERIFIED within budget**, reported as such.
- **Occupied preferred destination** (o00 forced into o02's cell 31; A0 cost 3, LB unchanged at 2): all 4 non-dominated orders were rejected (2 pruned):
  - (o00→31, …): NO_PICK;
  - (o01→18, o00→31, …): `NO_PLACE_CANDIDATE` (o02 still holds 31);
  - (o01→18, o02→23, …): `ALL_CONNECTORS_CERTIFIED_BLOCKED` at o02→23;
  - (o02→23, …): the same.

  The forced assignment therefore stays **UNRESOLVED** at its tried orders and budget. That is no proof that it is unexecutable, and it does not change the minimum, which is already certified at 2 by the unforced witness.

### 4.4 T07 paired control: development proxy (6 obstacles; same scene and γ0 as D2)

- **ALL_SUPPORTED:** LB = 2 = |D|. The restoration witness {o02: 40, o05: 49} is terminal-valid; it was robot-executed in D2 (§4.2).
- **RESTRICTED:** the published domain lets each blocker use only the nearest vacant action-clear cell that is not its own reference cell, i.e. {48} for both; everyone else may only stay.

  The Hall certificate is U = {o02, o05}, N(U) = {48}, |N(U)| = 1 < 2, so the status is **CERTIFIED_TERMINAL_INFEASIBLE** (independently checked).
- Excluding the reference cells is what makes the restriction bind. Without it the domain could contain the lemma's own witness cells, and that bug was caught during development.
- This fixture is a **proxy**. It is never called dense T07.

### 4.5 Dense T07 (35 obstacles, γ0 planned with the dense background present)

**A0 terminal problem.**
- 19 INVALID cells, 44 VALID, 0 UNRESOLVED.
- All 35 obstacles are in the matching. D = {o00, o21, o25, o26, o30}, so LB = 5.
- All 12 k-best assignments have cost 5; the 30 non-blockers stay.

**ALL_SUPPORTED side.**
- The restoration witness {o00: 3, o21: 44, o25: 51, o26: 52, o30: 59} is terminal-valid, so the optimum is exactly 5 = |D|.

**RESTRICTED side.**
- Each blocker may use only the 4 nearest vacant action-clear non-reference cells: [24, 32, 35, 43].
- The Hall certificate is U = all 5 blockers, N(U) = {24, 32, 35, 43}, |N(U)| = 4 < 5, so the status is **CERTIFIED_TERMINAL_INFEASIBLE**.

**Executable search** (24 relocation plans, 15 executed orders, 187 pruned):
- Rank 0 (o00→16, o21→51, o25→32, o26→24, o30→59), 6 orders, all rejected:
  - o00 first: `ALL_CONNECTORS_CERTIFIED_BLOCKED`;
  - o21 first: `NO_PICK_CANDIDATE`;
  - o25→32 first, then each of o00, o21 and o26 is rejected; o25, o30 first, then o00 is blocked.
- Rank 1 (o25→24, o26→32, …), 6 orders: rejected, mostly `UNRESOLVED PLANNER_BUDGET` at o00→16 (wall-clock independent).
- Rank 2 (o25→32, o26→43, …): the third order, **o25→32, o30→59, o21→51, o26→43, o00→16**, is **EXECUTABLE_VERIFIED**.

  UB = 5 = LB, so **MINIMUM_CERTIFIED**. H = [o25, o30, o21, o26, o00], and the replay passed.

**Lemma witness vs. executability.** The reference-restoration assignment (the lemma witness) is TERMINAL_VALID, but **none of its 6 non-dominated orders executed**:
- o00→3 is certified connector-blocked in every order that reaches it;
- o21→44 has NO_PICK;
- o26→52 has NO_PLACE;
- one attempt hit PLANNER_BUDGET, the single wall-clock-dependent attempt.

So the exact optimum 5 is attained by a *different* 5-move assignment, found by the k-best search.

Per the instruction, the claim is limited to what was shown: LB = 5 from A0, plus an executed and replayed 5-move witness, prove the exact minimum for this scoped fixture. No 6-move-necessity claim is made.

**Scope of "dense T07".** This is the G3 dense control fixture: 35 obstacles and an action-first planned reference. It is not the G4 T00 reference bank, the 20 audited roots or the 300-root pilot; none of those were started.

---

## 5. Visualizations (all in [`../runs/g3_repairs/`](../runs/g3_repairs/))

Every robot pose comes from a stored, certified record: relocation skills (starting at the achieved state) and the unchanged γ0. Rejected relocations have no trajectory. They are drawn as a red dashed intended move, with the first certified offence written out, including the counts of blocking pairs per object.

| | File | What it shows |
|---|---|---|
| A | [`A_matching_board.png`](../runs/g3_repairs/A_matching_board.png) | **A0 matching board** for D1, D2, D3 and dense T07, on the support only with physical cell IDs. Cell tint gives y^a ∧ y^w for an obstacle-sized disc (green VALID, red INVALID, amber UNRESOLVED); the orange line is γ0's target path; red rings mark direct blockers; arrows show k-best ranks #0 (solid), #1 and #2 (dashed). The box lists all objects, D, LB, the k-best costs and the cell counts. |
| B | [`B_d1_repair.gif`](../runs/g3_repairs/B_d1_repair.gif) | **D1 repair.** It starts in the blocked G2 scene, showing γ0 colliding and the first violating configuration. Then the real skill moves o02→43 (pregrasp, approach, close, carry, release, retreat), the connector reaches γ0's start, and the **unchanged frozen γ0** (hash shown) replays VERIFIED. The final frame is the achieved scene. |
| B | [`B_d1_stepwise.png`](../runs/g3_repairs/B_d1_stepwise.png), [`B_d1_forced.png`](../runs/g3_repairs/B_d1_forced.png) | The witness, the G2 diagnostic endpoint and the restoration (all executed). The forced chain shows the rejected o02-first order (NO_PLACE, blocked by o03) and the executed o03-first order. |
| C | [`C_d2_stepwise.png`](../runs/g3_repairs/C_d2_stepwise.png), [`C_d2_forced.png`](../runs/g3_repairs/C_d2_forced.png), [`C_d2_repair.gif`](../runs/g3_repairs/C_d2_repair.gif) | D2 step by step. Each row is one order; each panel is one real relocation, with the cumulative H, phase label and status. Each row ends with the final scene and γ0. The forced chain shows two rejected and three executed orders. |
| D | [`D_d3_stepwise.png`](../runs/g3_repairs/D_d3_stepwise.png), [`D_d3_forced.png`](../runs/g3_repairs/D_d3_forced.png), [`D_d3_repair.gif`](../runs/g3_repairs/D_d3_repair.gif) | **D3 order and access comparison.** It covers the rejected o00-first order (NO_PICK, with candidate breakdown and blocking IDs), the executed o01-first witness, the low-ID endpoints (two rejections), and the restoration (NO_PICK; then PLANNER_BUDGET after a verified first move). The GIF shows the blocked scene, then the rejected order holding on its offence, then the executed witness, then the γ0 replay. |
| E | [`E_restricted_vs_all_supported.png`](../runs/g3_repairs/E_restricted_vs_all_supported.png) | The **proxy and dense T07 pairs**. In each pair, the same scene and γ0 are shown with the ALL_SUPPORTED restoration witness (green arrows, LB = \|D\|) and the RESTRICTED domain (hatched cells) with the Hall set U, N(U) and \|N(U)\| < \|U\|. |
| E | [`E_t07_dense_witness.png`](../runs/g3_repairs/E_t07_dense_witness.png), [`E_t07_dense_repair.gif`](../runs/g3_repairs/E_t07_dense_repair.gif) | The dense 5-relocation executed witness among 35 obstacles, step by step, followed by the connector and the unchanged γ0 replay. |
| F | [`F_verification_summary.png`](../runs/g3_repairs/F_verification_summary.png) | The table of \|D\|, LB, best verified UB, minimality, status, stop reason, plans, attempts and replay. Below it are witness keyframes: the grasp configurations of each relocation (ghosts), the robot at γ0's start, and the γ0 path with its **re-verified unchanged hash**. |
| F | [`F_attempts.png`](../runs/g3_repairs/F_attempts.png) | Every candidate (A0 rank, comparison or forced) with its terminal cost, order, real outcome and first failure. |

Rendering note: the shared `figures.write_gif` built its 128-colour palette from the **first frame only**, so status colours that first appear later (the green VERIFIED tag) were quantized to grey. It now samples five frames across the whole animation. Archived G1/G2 GIFs were not regenerated.

---

## 6. Tests and verification

`python -m pytest tests -q`: **74 passed in 61.8 s**.

**`tests/test_matching.py`** (12 tests, about 0.4 s, no robot planning):
1. Matching vs. complete enumeration over 300 random matrices with ∞ entries.
2. Murty k-best vs. enumeration: the same cost sequence including ties, no duplicates, consistent costs; a 24-way all-tie case.
3. Hall certificate ⇔ infeasibility, checked by `check_hall`; tampered certificates are rejected.
4. A0 includes every obstacle; physical IDs; witnesses use only VALID cells; never the target's cell; cost equals the moved count; tie-break ordering.
5. The lexicographic tie-break never changes the moved count (vs. a pure 0/1 objective).
6. UNRESOLVED edges enter the LB but never a witness.
7. Restoration lemma over 40 random reference-to-failure families: restoration valid, moves = |D| = A0 optimum.
8. **Negative case:** restoration rejected when a reference cell is taken or action-blocked.
9. Occupied preferred destination: forced cost 2 with LB unchanged at 1; a forced stay at a blocked cell has no edge.
10. Restricted vs. all-supported: Hall infeasible with the exact certificate; a wider domain becomes feasible; excluded cells honoured.
11. The reduction guard rejects non-identical discs.
12. Exhaustive small-case audit on a status map with stay options, blocked sources and an UNRESOLVED cell.

**`tests/test_verify.py`** (9 tests, about 45 s, real 3R planning on D1 and D3):
1. One real relocation from the achieved state:
   - the record starts at s0.q;
   - the next state equals the record end (q, g, pose and cell);
   - nothing else moved;
   - the record re-certifies;
   - a second move gives `MOVE_ONCE_VIOLATION` without planning.
2. D1 search gives MINIMUM_CERTIFIED:
   - the last record ends bit-exactly at q0;
   - F and the whole replay are VALID;
   - `frozen.verify()` passes, the frozen arrays are unchanged and the target never moves (no replanning);
   - `replay_repair` passes.
3. Replay rejects tampering: wrong achieved pose, dropped history, wrong q, wrong gap, or a different γ0 (hash mismatch raises).
4. The occupied-destination order keeps its first offence (stop 0, reason, INFEASIBLE skill); the other order executes; UB 2 > LB 1 gives MINIMUM_UNRESOLVED.
5. Bounds never over-claim: no assignments gives UNRESOLVED; a Hall certificate gives CERTIFIED_TERMINAL_INFEASIBLE / NOT_APPLICABLE; a tight relocation budget gives RELOCATION_BUDGET with UB = None, even though a valid assignment existed further down the list.
6. D3 order sensitivity on the same assignment (rejected vs. executed); H per step; two-relocation state continuity; replay; a mid-episode gripper tamper is detected.
7. Dominated-order pruning.
8. A0 terminal-valid agrees with the original G2 terminal oracle (three k-best assignments placed by substitution give F = whole replay = VALID); the blocker's source cell is INVALID; the target cell is excluded.
9. Relocation planning is deterministic (two runs give identical arrays).

**Mutation checks** (scratch copies; each mutation re-runs its targeted tests):

| Mutation | Result |
|---|---|
| k-best without the no-good exclusion | killed |
| Hall certificate with an extra cell | killed |
| stay cost 1 | killed |
| optimistic bound ignores UNRESOLVED | killed |
| restoration ignores vacancy | survived in round 1 → negative test added → **killed** |
| no move-once check | killed |
| relocation planned from home instead of the achieved q | killed |
| last move without the γ0 connector | killed |
| minimum claimed whenever a witness exists | killed |
| budget never stops search | killed |
| no dominated-order pruning | killed |
| replay skips its per-record state-end check | **survives, by design** |

The state-end check is redundant with two later checks: the next record's start check (q and g, added this stage) and the final q0/g0 check. Every tamper it would catch is caught by those, as test 3 and the D3 mid-episode gap tamper show. It is kept as defence in depth.

**Regression and replays.**
- All 53 G0–G2 tests pass after the `plan_skill`, `interventions.py` and `figures.py` changes; this includes the golden RRT hash test.
- After the `interventions.py` refactor, a full `run.py intervene` rerun into scratch reproduced the archived G2 run exactly: families, gates, scenes and every array. The only differences were wall-clock "seconds" fields.
- `run.py replay` reports were written to scratch, so the archives stay untouched:

| Run | Trajectories | Result | Config sections filled from current |
|---|---|---|---|
| g1_robot | 77 | all certified, hashes match | `repair2d` (unused by replay) |
| g1_hardening | 77 | all certified, hashes match | `repair2d` |
| g2_interventions | 2 (frozen D1/D2 γ0) | certified, hashes match | `repair2d` |
| g3_repairs | 50 | all certified, hashes match | none |

The G3 replay covers the following. Each relocation of every executed episode (witnesses, executable comparisons and forced orders) is re-certified in its stored **pre-move** scene against its stored hash. γ0 is re-certified both in its reference scene and in each episode's stored **final achieved** scene. For the latter, the hash is bound to the reference scene through the new `hash_scene` task field.

`git status` shows no change under `runs/g0_scene`, `runs/g1_robot`, `runs/g1_hardening` or `runs/g2_interventions`.

---

## B. Files created or modified

| File | Change | Lines (total / logical) |
|---|---|---|
| `solve.py` | **new**: A0 cell status, domains, cost, matching, Murty k-best, enumeration oracle, Hall certificate and check, restoration, forced, restricted domain | 231 / 155 |
| `verify.py` | **new**: RepairState and Attempt, relocate, execute, fresh_orders, search, replay_repair, fixtures, forced chain, run record and archive | 308 / 231 |
| `repair_figures.py` | **new**: relocation, failure and final panels, offence text, stepwise figure, repair GIF | 189 / 143 |
| `assignment_figures.py` | **new** (split from `repair_figures.py` for size): A0 board, restricted vs. all-supported, summary and attempts tables, G3 figure set | 234 / 195 |
| `tests/test_matching.py` | **new**, 12 tests | 205 / 161 |
| `tests/test_verify.py` | **new**, 9 tests | 177 / 135 |
| `skill.py` | `plan_skill(…, q_start=None, q_goal="home")`; default behaviour unchanged (G2 rerun identical, golden test passes) | 341 / 271 |
| `interventions.py` | `add_blockers` and `_corrections` extracted from `build_family`; `_child` replaces duplicated lambdas; `load_archived` (read-only archive loader with hash re-verification). G2 output reproduced exactly. | 345 / 243 |
| `figures.py` | GIF palette sampled across the animation | 193 / 154 |
| `config.py`, `config.toml` | `[repair2d]` section (k_best 12, max_orders 6, max_relocations 40, skill_plan_failures 2) with validation | 183 / 139 |
| `fixtures.json` | version 4: G3_D1, G3_D2, G3_D3, G3_T07_PROXY, G3_T07_DENSE | — |
| `run.py` | `solve` command; `replay` fills sections a run predates from the current config (recorded) and supports `hash_scene` | 372 / **318** |
| `README.md`, `requirements.lock` | G3 status, layout and commands; `scipy==1.16.3` | — |
| `runs/g3_repairs/` | **new** run: result, scenes, arrays, config, metrics, manifest, 11 PNGs and 4 GIFs (6.3 MB in total; no file exceeds 1.4 MB, so no LFS is needed) | — |

**Size review.** `run.py` is at 318 logical lines, above the ~280 guidance; it held about 290 before G3. G3's per-fixture packaging was already moved into `verify.archive`.

- **Proposal (not done here, to avoid unrelated changes to earlier stages):** at the start of G4, move each stage's command body next to its stage module, keeping `run.py` as the dispatcher plus shared I/O.
- `verify.py`, `skill.py`, `geometry.py` and `interventions.py` are within the guidance.

---

## C. Configuration and reproducibility

| Item | Value |
|---|---|
| Config hash (G3) | `sha256:9af02e1f4cc76577b63275fdd7593fa83b7dc34eaa7344cfb790bba22618e28f`. It changed from G2 (`95c78c4b…`) only by the new `[repair2d]` section. |
| Robot profile hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858` (**unchanged since G1**) |
| Planner seeds | base seed from `[planner2d]`; per query crc32 of the episode key (fixture / prefix / step), so results are deterministic (tested) |
| Solver | SciPy 1.16.3 `linear_sum_assignment` with Murty k-best |
| Environment | Python 3.13.11, numpy 2.4.0, scipy 1.16.3, matplotlib 3.11.2, pillow 12.0.0, pytest 9.1.1 (manifest) |
| Commands | `python run.py solve --out runs/g3_repairs` (23 min 11 s wall on 5 workers, dominated by dense T07); `python run.py replay --run runs/g3_repairs --report <path>` (4.4 s) |
| Timing | Earlier scratch batches with identical outcomes: D1 33 s, D2 67 s, D3 22 s, proxy 20 s, dense T07 1313 s. |

---

## D. Unavailable, unresolved and not-run items (explicit)

- **CONSTRUCTION_UNAVAILABLE:** none. Dense T07 was constructed with γ0 planned in the dense scene.
- **UNRESOLVED outcomes, kept and shown, none claimed impossible:**
  - D3 restoration (o01 first, then o00→5): `PLANNER_BUDGET`.
  - D3 forced chain: 4 orders rejected, so the forced assignment is UNRESOLVED.
  - Dense rank-0 and rank-1 assignments: all tried orders rejected, several at `PLANNER_BUDGET`.
  - Dense lemma-witness assignment: no tried order executed.
- **NOT_RUN:** the T07 proxy's ALL_SUPPORTED side was not robot-executed as a separate fixture. Its scene and γ0 are D2's, which was executed (§4.2).
- **Not attempted (out of G3 scope):** simulation replay, physical execution, the G4 T00 bank, the 20 audited roots, the 300/1000-root pilots, Gibbs/Boltzmann inference and learning.

---

## E. Deviations and corrections made during G3

1. **Archived run replay.** Strict config validation rejected archived run configs that predate `[repair2d]`. `replay` now fills only the sections the run predates, from the current config, and records which ones (`config_sections_filled_from_current`). None of these sections is used by replay.
2. **Ties in D3's k-best.** All 12 tied optima at cells 0–4 were certified blocked, so the search was UNRESOLVED. The carry-distance lexicographic tie-break fixed this, and the moved count stays exact. The old behaviour is kept as an explicit comparison.
3. **Restricted domain.** It could contain the lemma's witness cells; restoration cells are now excluded.
4. **Order enumeration.** It only varied the tail of the order; replaced by dominated-order pruning (§2).
5. **`replay_repair`.** It did not check that each recorded state's q and g equal its record's end, nor the gripper at each record start; both checks were added. Execution and replay now also require γ0's initial gripper gap, not only q0.
6. **GIF palette** fix (§5).
7. **Circular import.** Created while splitting the figure modules and removed; the dependency is now one-way (`assignment_figures` → `repair_figures`).

---

## F. Scientific interpretation and limitations

**What G3 shows:**
- **Terminal validity and robot executability are different things.**
  - In D3 and in dense T07, the reference-restoration assignment is terminal-valid and attains the A0 optimum, yet no tried order of it executed.
  - Executable optima were found through other k-best assignments and orders.
  - Order matters for the same assignment (D3: o01 must leave first to open grasp access to o00).
- **The A0 lower bound is the right proof tool here.** With an executed witness at LB, minimality is certified without any complete motion-level search. Where a witness exceeds LB (forced chains), the result is honestly `MINIMUM_UNRESOLVED`.

**Limitations:**
- **Kinematic 2D only.** The finite declared grasp family uses 48 (φ, branch) candidates per object. The planner is seeded RRT-Connect with node and evaluation budgets. "Certified infeasible" therefore always means *for this declared grasp set and these straight-line or certified connector queries* (the skill's scope string). It is never a general robot impossibility.
- **The search is finite**: k = 12 assignments, 6 non-dominated orders each, 40 relocation plans, and 2 failures per skill. A failed search is reported as UNRESOLVED, never as an impossibility proof. In every fixture here a witness reached the LB, so no such case arose in the headline results.
- **Matching exactness** depends on identical discs on a uniform grid with pitch > 2r + δ. `ReductionInvalid` blocks use outside that scope. Mixed sizes would need an explicit pairwise constraint solver.
- **Construction is privileged.** Dense T07's blockers were placed by privileged G2-rule edits after γ0 was frozen. That is the guide's construction, not a natural process.
- **Fixture count.** Only one dense root exists. This is a G3 control, not a benchmark statistic.

---

## G. Next-stage readiness

G3's acceptance evidence is complete:
- an exact A0 with k-best and Hall certificates;
- executable move-once verification with exact γ0 identity;
- LB/UB accounting;
- paired restricted vs. all-supported controls, including a genuinely dense 35-obstacle T07 with a certified 5-move executable optimum.

**Open items to settle at G4 entry, needing approval:**
1. The `run.py` size split (§B).
2. Whether the per-skill failure allowance in search (2) should be raised for the dense bank, given the time cost: about 55 s per relocation plan in dense scenes.
3. Whether the T07 proxy should also be robot-executed separately, or whether D2's execution is accepted as covering it.

**G4 has not been started.** Per the workflow, I stop here for approval.

---

## Repository synchronization

Committed together with this report:
- the source files, tests, `fixtures.json`, configs, README and `requirements.lock`;
- `runs/g3_repairs/`;
- the instruction file `instruction-phase-md/G2_independent_review_and_G3_prompt.md`.

The commit hash is given in chat, because a report cannot contain its own hash. It will be recorded as "Previous turn sync" in report 0007.
