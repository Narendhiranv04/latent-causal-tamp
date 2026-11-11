# 0007 — G3.5 completion report: initial-scene repair, objective migration and case analysis

| Field | Value |
|---|---|
| Report number | 0007 |
| Date | 16 October 2026 |
| Stage | **G3.5** (Guide v1.7 §4–5): objective migration and R0–R6 case analysis. **No G4 scaling, no G5 training, no learned-performance result, no simulation and no hardware execution were performed.** |
| Normative documents | Methodology Specification **v1.5** and Implementation Guide **v1.7** (both read in full); instruction `instruction-phase-md/G3_5_initial_scene_repair_migration.md` (read in full) |
| Previous turn sync | Report 0006 was committed as `7c880cd29d989be7b1e863baad881822d98038b0` on `main` and pushed to `origin/main`; the remote head was verified equal to the local head. |
| Protocols | **Primary:** `INITIAL_SCENE_ONE_SHOT_V1`, new. **Archived:** `FROZEN_CONTROL` (G0–G3, unchanged). |
| Run directory | [`../runs/g3_5_initial_scene/`](../runs/g3_5_initial_scene/) (`python run.py case-analysis --out runs/g3_5_initial_scene`, 2 min 32 s wall, 5 workers) |
| Outcome | **All R0–R6 cases demonstrated with real full-3R evidence.** Each case is either a complete witness, a sound certificate, or an explicitly kept unknown. All six computed readiness items are PASS. |
| Proposals | `MANUAL_CASE_CANDIDATES`: hand-authored per query, then ranked by a fixed deterministic rule. They test the **contract**, not proposal intelligence, and were authored with knowledge of G3 results and scratch probes (§9). |
| Tests | **83 passed** (74 existing + 9 new contract tests) in 77 s. Mutation checks on the new contract: 11 of 11 mutants killed (2 after test strengthening, §6). |
| Regression | Replays pass: `g1_robot` 77/77, `g1_hardening` 77/77, `g2_interventions` 2/2, `g3_repairs` 50/50, and the new `g3_5_initial_scene` 20/20. The **84 archived run files are byte-identical before and after** (sha256 list compared). |

---

## 1. Baseline and inputs (instruction §2–3)

| Item | Value |
|---|---|
| Branch / commit at start | `main` @ `7c880cd2` (G3) |
| Working tree at start | (a) `instruction-phase-md/G3_5_initial_scene_repair_migration.md` (untracked); (b) new PDFs `…specification_v1_5.pdf` and `…implementation_guide_v1_7.pdf` (untracked); (c) the old `…v1_4.pdf` / `…v1_6.pdf` **deleted locally by the user**. See "Repository synchronization": the deletion is not committed. |
| Repository instructions | No `AGENTS.md`/`CLAUDE.md`. The workflow rules from the user and instruction files apply (numbered immutable reports, commit + push + verify, STOP). |
| Robot profile hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858`. This is **unchanged** and equals the full hash recorded at G1–G3, with the prefix quoted by Guide v1.7 §2. |
| Tested profile check | home q = [π/2, π/2, π/2]; 24 approach directions × 2 IK branches = **48 declared grasp candidates**; full layered 3R body (links, housings, palm, rail, two fingers, carried disc). There is no discrepancy with report 0006, and nothing was reset to provisional values. |
| Config hash | G3: `sha256:9af02e1f…`. G3.5: `sha256:c1854e4e5adab543cf570e290d358a1ac7596299f5d2f22426c8a0851bf4a73a`. The change consists only of the three new sections (§2). Archived runs replay with the sections they predate filled from the current config, and this is recorded. |
| Archive check | sha256 of all 84 files under `runs/` taken before any code change and after the final run: identical. |

Also read: reports 0001–0006, the G2-review/G3 instruction file, and the current source and tests. Report 0006 is unchanged; its frozen-motion minima keep their original labels and scope.

---

## 2. What changed scientifically, and how it is enforced

The primary problem is now:

> Given the initial scene, object information, robot state and a parameterized action/goal, propose which obstacles to move and where.
>
> External IK and motion planning realize the relocations. **After** the repair is committed and executed, a target planner evaluates the intended action from the achieved state.

There is no trajectory input. There is no target feedback before the commitment, none between relocations, and no retry after the result.

**Configuration** (`config.toml`; validated in `config.py`, where contradictory settings raise `ConfigError`, tested):

```toml
[protocol]           name = "INITIAL_SCENE_ONE_SHOT_V1", proposal_observation = "INITIAL_ONLY",
                     target_feedback_to_selection = false, target_calls_between_relocations = 0,
                     target_reference_required = false, execution_observation = "VALIDATE_OR_ABORT", move_once = true
[proposal]           source = "MANUAL_CASE_CANDIDATES", budget_cap = 6, max_candidates_to_verify = 12,
                     include_all_stay = true, task_score_threshold = 0.5
[target_evaluation]  when = "AFTER_REPAIR_COMMIT_AND_COMPLETION", start_state = "ACHIEVED",
                     scope = "COMPLETE_TARGET_SKILL", final_connector = "HOME", max_queries_per_primary_episode = 1
```

`FROZEN_CONTROL` code paths (`solve` and `replay`, A0, `verify.execute`/`search`/`replay_repair`) keep their exact semantics. They do not read these sections. G3.5 fixtures must declare `protocol: INITIAL_SCENE_ONE_SHOT_V1` and no frozen reference policy.

### Component separation (instruction §4; Guide v1.7 §1, §3)

| Component | Code | Access | Cannot |
|---|---|---|---|
| Learner context / query | `data.make_query`, `learner_tensors` | allowlisted `learner` namespace only: scene geometry and poses, robot q / gap / attachment, legal spots, action context | see `oracle_only` (reference action hash, frozen diagnostics, construction ancestry, root IDs), `labels` or `execution` |
| Proposal provider | `solve.rank_proposals` | learner scene + action + declared candidate list | import or call any target or relocation component |
| Static endpoint checker | `solve.static_endpoints` | final endpoint poses with the target at rest | use a robot body or any frozen sweep; it never claims action feasibility |
| Relocation planner / verifier | `verify.realize`, `verify.plan_repair` | immutable clones of S0, achieved states, IK and full-body checking | call the target evaluator (module does not import `evaluate`) |
| Commitment boundary | `evaluate.primary_episode` | freezes assignment, order, witness hash, proposal hash, source-observation hash | try another candidate after COMMIT |
| Target evaluator | `evaluate.evaluate_target` (injected callback) | final achieved q, gripper gap, attachment (free after retreat), object poses, action context | feed its result back; it is invoked once per primary episode |
| Offline teacher | `evaluate.audit_candidate` (`OFFLINE_CASE_AUDIT`) | full relocation and target search per candidate | send anything to a primary episode (separate record namespace) |

**Action identity.** `action_context_hash` is a hash of five fields:
- the target ID;
- the unique goal cell and pose, with its tolerance (the release tolerance) and orientation freedom ("ANY", because the target is a rotationally symmetric disc);
- the grasp family (24 directions × 2 branches, approach and retreat distances);
- the contact mode (planar supported side grasp, no lift, no pushing) and the final connector;
- the robot profile hash.

It never contains a trajectory hash. R0 and R1 share an action-context hash (same action) but have different observation hashes (different scenes).

**New-mode relocation.** Every relocation is planned from the achieved state and **ends after its retreat**. There is no connector to any historical γ0 start (tested). The target skill is then planned afresh, starting **exactly** at the last record's q and gap (tested bit-exact; gripper open, attachment free). It may contain its own checked approach and connector motions.

**Episode semantics** (`evaluate.primary_episode`):

```
PROPOSE (fixed ranked list; proposal_hash)
for each candidate: STATIC_CHECK -> REPAIR_PLAN on clones (orders, budgets)
first complete relocation witness -> COMMIT (assignment, order, witness hash)
RELOCATE / REOBSERVE per move (replay on a clone of S0; ABORT on deviation)
TARGET_EVALUATE once, from the achieved state -> FINISH (no further candidates)
```

---

## 3. Evidence contract and bounds (instruction §6; spec v1.5 §2–3, §7)

Separate fields per assignment and attempt: `static_status`; `relocation_status` (per order); target attempt status; `assignment_feasibility_status`; `certificate` and `unknown_reason`; and, per query, bounds and the episode outcome. `simulation_status` and `hardware_status` are both `NOT_RUN`.

**Static endpoint factors.** These cover support (the disc fully on the support), the target at rest, and pairwise disc clearance ≥ δ = 0.005 m. They use the declared numerical gray band ε = 0.0002 m, so the result is VALID, INVALID or UNRESOLVED. There is no robot body and no sweep: "a relocated object may occupy a region vacated by the arm".

**Assignment labels.**
- **VERIFIED_FEASIBLE** only with a complete relocation-plus-target witness from S0.
- **CERTIFIED_INFEASIBLE** only with one of three sound certificates:
  1. **Static endpoint invalidity**: any realization has those endpoints.
  2. **Goal overlap.** Even at the most favourable allowed target placement (goal tolerance) and achieved obstacle pose (release tolerance if moved), clearance to an obstacle stays below δ − ε. This is sound because the goal is a single disc pose with no orientation freedom, and obstacles move only by declared relocation (pushing and contact are forbidden by the collision checks).
  3. **First-mover pose-only screen in S0.** Every object of the assignment, if moved first, fails a pick or place screen in S0 that depends only on object poses (not on the robot start). That failure is certified for the whole declared grasp family. Every realization must move one of them first, so all realizations fail within the declared skill scope.
- Everything else, including finite planner budgets, is **UNRESOLVED**. A rejected order rejects only that order.

**New-objective bounds.** The default LB is 0. LB = 1 for each obstacle with a goal-overlap certificate. One more (+1) is added if every such obstacle also has a certified pick failure in S0 (pose-only, declared grasp family): none of them can move first, so another object must move before them. UB is the fewest moves among complete witnesses (primary or audit). `MINIMUM_CERTIFIED` only when LB = UB. **Old direct-blocker counts and frozen A0 costs are never imported** (tested: the R1 frozen blocker o02 does not change LB = 0).

---

## 4. Case results (all from [`../runs/g3_5_initial_scene/cases.json`](../runs/g3_5_initial_scene/cases.json))

| Query | Cases | Initial scene | Action | Primary episode | Committed | LB / UB | Minimality |
|---|---|---|---|---|---|---|---|
| G35_R0_D1REF | R0 | archived G2 D1 `ref` | t0 → cell 45 | **SUCCESS** (target 10.7 s) | all-stay | 0 / 0 | MINIMUM_CERTIFIED (0) |
| G35_R1_D1BLOCK | R1, R6 | archived G2 D1 `block_a` | t0 → 45 | **SUCCESS** (target 67.1 s) | all-stay | 0 / 0 | MINIMUM_CERTIFIED (0) |
| G35_R2_GOAL | R2, R3, R5, R6 | new root: t0 at 18; obstacles at 3, 13, 50, **45** | t0 → 45 | **SUCCESS** (8.3 s) | o03 → 60 | 1 / 1 | MINIMUM_CERTIFIED (1) |
| G35_R4_ACCESS | R4, R2 | new root: G3 D3 blocked layout (t0 at 20; obstacles 28, 27, 31, 58, 63) | t0 → **28** | **SUCCESS** (4.3 s) | o00 → 29, o01 → 18, executed o01 first | 2 / 2 | MINIMUM_CERTIFIED (2, scoped) |
| G35_R5_D2BLOCK | R5 | archived G2 D2 `block_ab` | t0 → 53 | **TARGET_UNRESOLVED** (4.5 s) | all-stay | 0 / — | MINIMUM_UNRESOLVED |

### R0 — already feasible
All-stay passed the static screen and was committed with an empty relocation. The newly planned target skill from the initial state was **VERIFIED**: a zero-move witness, so the minimum is 0.

The audit also witnesses the unnecessary one-move repair o02→43 (VERIFIED). The primary rule (fewer moves first) chose all-stay without any target information.

### R1 — reference blocked, action feasible
**Privileged diagnostic (`oracle_only`, FROZEN_CONTROL).** The stored G2/G3 γ0 `sha256:487ec188…` replayed unchanged in this scene gives F_fixed = **INVALID**. The blocker is o02: the carried target passes 3.4 mm < δ from it during carry.

**Primary.** All-stay was committed, and a newly planned target skill from the **same initial state** was **VERIFIED_FEASIBLE**. Its planner record:
- grasp and place candidates screened: 18 of 48 picks and 17 of 48 places pass;
- pregrasp connector: 9 queries certified blocked by the link-0 sweep, then one RRT (104 nodes);
- carry: one query exhausted its 4000-node cap; the next pick/place pair connected directly;
- no wall-clock dependence.

The audit's independent all-stay evaluation (different seed key) also succeeded (66.7 s).

The new-objective minimum is therefore **0**. The frozen-control minimum of 1 from report 0006 remains valid **only** for that frozen path. This is the objective distinction the case requires.

### R2 — mandatory goal occupied (G35_R2_GOAL)
**Premise.** o03 sits exactly at the goal centre (distance 0). The target cannot be placed within the goal tolerance with clearance δ, so the **goal-overlap certificate** gives LB = 1.

**Primary.** The ranking scores all-stay 0 (goal provably occupied: a deterministic geometric rule on initial inputs only), so it is screened out.
- o03→60 was static-valid. Its relocation was verified (0.4 s), committed, executed, and the target was planned from the achieved state (q = [1.793, −1.745, −0.572] rad, gap 0.07 m) as **VERIFIED**.
- UB = 1, so MINIMUM_CERTIFIED (1). The moved history is H = [o03].

The same premise, plus o00's certified NO_PICK in S0, gives LB = 2 in G35_R4_ACCESS (below).

### R3 — alternative sufficient repairs (offline audit, G35_R2_GOAL)
**o03→60** and **o03→38** each have a complete independent relocation-plus-target witness from the same S0 (target 5.0 s and 6.9 s). Both are positive labels. Neither is called "the" culprit set, and the audit assumes neither is minimal; minimality comes from the LB/UB argument above.

### R4 — order and access dependence (G35_R4_ACCESS)
The assignment is {o00→29, o01→18}.

**Rejected order:**
- order (o00, o01) is rejected at relocation 1: `CERTIFIED_INFEASIBLE NO_PICK_CANDIDATE`;
- all 48 declared grasps are definitely rejected (GRASP_POSE ×46, APPROACH ×2);
- the first offending pairs involve o01 ×21, t0 ×10, o00 itself ×5, o03 ×5 and o02 ×2.

**Verified order:**
- order (o01, o00) is **VERIFIED_FEASIBLE**;
- each relocation starts at the previous retreat end;
- the target is newly planned from the achieved state (q = [1.264, −2.023, −0.027] rad) as **VERIFIED**.

**Primary episode:**
- the single move {o00→29} ranks first (fewer moves); its only order fails the same way;
- the audit labels it **CERTIFIED_INFEASIBLE** by the first-mover pose-only screen;
- the planner then committed the two-move assignment in order o01 first.

**Bound.** LB = 2 follows from the goal-overlap and o00-pick-certificate premises; together with UB = 2 it gives MINIMUM_CERTIFIED (2). Its scope is the declared grasp family, move-once relocation, no pushing, and a target that is not itself a repair object.

### R5 — static validity is insufficient
- **Sound obstruction (G35_R2_GOAL).** The assignment {o01→21} is static-VALID but leaves o03 on the goal, so it is CERTIFIED_INFEASIBLE by goal overlap. Its own relocation attempt was UNRESOLVED (planner budget) and is kept. All-stay in R2 and R4 is also static-VALID and certified infeasible by goal overlap; the audit's target attempt there returns scoped `NO_PLACE_CANDIDATE`, consistent with that.
- **Target-planning unknown (G35_R5_D2BLOCK).** All-stay is static-VALID and the empty repair commits. The target evaluation returns **UNRESOLVED PLANNER_BUDGET** (4.5 s). The planner record (seeded; from the identical-key scratch run) shows 15 pregrasp and 27 carry connector queries certified blocked by the link-0 sweep and 3 pregrasp queries connected; the skill's declared search budget then ended without a witness. Certified blockage of the queries tried is not a proof over all pick/place pairs or motions, so the status is UNRESOLVED.

  The episode is therefore unsuccessful within budget, the assignment is UNRESOLVED, LB stays 0 and UB is none. No other candidate is tried and no negative label is created. The audit's independent evaluation (5.8 s) is also UNRESOLVED.

### R6 — invalid and unknown controls

| Control | Result |
|---|---|
| Duplicate destination {o03→60, o02→60} | static **INVALID** (pair clearance −0.048 m) → CERTIFIED_INFEASIBLE |
| Onto the resting target {o03→18} | static **INVALID** (target_at_rest −0.048 m) |
| Unsupported pose {o03→(−0.01, 0.30)} | static **INVALID** (support margin −0.034 m) |
| Numerical boundary {o03→(0.253, 0.52)}: clearance to o02 = δ exactly | static **UNRESOLVED** (gray band) → assignment UNRESOLVED |
| Forced planner exhaustion (G35_R1, all-stay, `max_nodes` 20, `max_plan_failures` 1) | target **UNRESOLVED PLANNER_BUDGET** (0.65 s) → assignment UNRESOLVED; no negative and no bound, while the default-budget evaluation of the same query is VERIFIED |
| Poisoned privileged fields | Learner tensors are identical after poisoning every `oracle_only` and `labels` field, and after deleting both namespaces. This holds for all 5 queries (runtime audit and test). Changing the goal changes the action-context hash and the goal tensor; the observation hash is unchanged. |

**Label-source mix in this run** (16 audited assignments):
- 7 positives: complete witnesses;
- 7 certified negatives: 3 static-invalid, 3 goal-overlap, 1 first-mover;
- 2 unknowns: a static gray band and a target budget.

The R6 forced-exhaustion control adds one more unknown.

---

## 5. Visualizations (all in [`../runs/g3_5_initial_scene/`](../runs/g3_5_initial_scene/))

All motion is replayed from stored records. Proposed endpoints are dashed arrows (proposals, not motion). Missing witnesses are drawn as text (UNRESOLVED / NOT_RUN), never as invented paths.

| File | Content |
|---|---|
| [`A_protocol_cases.png`](../runs/g3_5_initial_scene/A_protocol_cases.png) | Each query's initial scene with the arm, the unique goal (orange dashed), the committed proposal, the primary outcome and bounds, and a per-candidate table: static / relocation / target / assignment status. Plus an R6 and leakage-audit panel. |
| [`B_r1_route_comparison.png`](../runs/g3_5_initial_scene/B_r1_route_comparison.png) | The same scene twice. Left: the stored γ0 replayed unchanged, labelled **PRIVILEGED DIAGNOSTIC (FROZEN_CONTROL)**, with the first certified violation (carried target vs o02). Right: the actual newly planned zero-move target witness (VERIFIED). |
| [`C_r2_repair.gif`](../runs/g3_5_initial_scene/C_r2_repair.gif) | Initial state with the goal occupied, then the committed relocation o03→60 with phase labels and H, then the newly planned target action from the achieved state (phases and H = [o03]). |
| [`D_r3_alternatives.png`](../runs/g3_5_initial_scene/D_r3_alternatives.png) | Both independently witnessed alternatives (o03→60, o03→38): the relocation panel and target keyframes from each achieved state. |
| [`E_r4_orders.png`](../runs/g3_5_initial_scene/E_r4_orders.png) | Same assignment, two orders. The rejected o00-first order with its first certified offence and candidate breakdown (target NOT_RUN for that order). The verified o01-first order with both relocations, the start q of the target, and the target keyframes. |
| [`F_call_trace.png`](../runs/g3_5_initial_scene/F_call_trace.png) | Ordered event trace per primary episode, with the commitment boundary dashed. Every row shows "target calls: before commit 0, between relocations 0, total 1 \| boundary ok = True". |
| `obs_<query>.png` | Clean learner RGB per query: no paths, arrows or status overlays. |

Data files: `result.json` (summary, readiness, replay tasks), `cases.json` (per query: `learner`, `hashes`, `oracle_only`, `execution` with event trace, `offline_case_audit`, bounds, controls), `metrics.csv`, `config.json`, `scenes.json`, `arrays.npz` (20 trajectories), `manifest.json`.

---

## 6. Tests and verification

`python -m pytest tests -q`: **83 passed in 77.2 s**. The 74 G0–G3 tests are unchanged and pass; `tests/test_protocol.py` adds 9 tests (about 14 s, real 3R planning).

| # (instruction §9) | Test | Covered by |
|---|---|---|
| 1 | Query needs no γ0, envelope or nominal start; contradictory protocol configs rejected | `test_new_protocol_query_needs_no_reference_path` |
| 2 | Poisoning or deleting privileged fields leaves tensors and proposals unchanged; goal change changes context | `test_privileged_fields_cannot_change_learner_inputs_or_proposals` |
| 3, 4 | Spy: 0 target calls before COMMIT or between RELOCATEs; after a target failure no further candidate, proposal or commit | `test_no_target_call_before_commit_or_between_moves_and_no_retry` |
| 5, 12 | End-to-end real relocation + complete target plan; target starts bit-exactly at the last relocation's q and gap (not home); last relocation ends at retreat; live S0 untouched | `test_target_starts_at_actual_last_relocation_state` |
| 6, 7 | Static-valid ≠ positive; target budget failure stays UNRESOLVED (no certificate, LB 0, UB none, MINIMUM_UNRESOLVED); static-valid without relocation witness is not positive | `test_static_validity_and_timeouts_never_become_labels` |
| 8 | Rejected order does not exclude the assignment; single-mover first-mover certificate; no certificate when another mover can go first | `test_rejected_order_does_not_exclude_the_assignment` |
| 9 | Move-once (second move of the same ID refused), clone isolation, empty repair needs no plans | `test_move_once_history_and_clone_isolation` |
| 10 | FROZEN_CONTROL `execute` still ends bit-exactly at γ0's start with the frozen hash verified; the new mode ends at retreat | `test_frozen_control_semantics_unchanged` |
| 11 | R1 frozen blocker not imported (LB 0); R2 LB 1; R4 LB 2 from a real pick certificate | `test_frozen_blocker_count_is_not_a_new_lower_bound` |

**Mutation checks** (scratch copies; targeted test selection):

| Mutation | Result |
|---|---|
| fallback to the next candidate after a target failure | killed |
| target evaluated from home instead of the achieved state | killed |
| new-mode last relocation connects home | killed |
| target timeout labelled negative | killed |
| oracle field leaking into learner tensors | killed |
| proposal ignores the goal-occupancy score | killed |
| frozen blockers imported as a lower bound | killed |
| move-once check removed | killed |
| contradictory protocol accepted | killed |
| static-valid promoted to assignment positive | survived in round 1 → test strengthened → **killed** |
| first-mover certificate checking only one mover | survived in round 1 → test strengthened → **killed** |

**Refactor safety.** `verify.replay_repair` now delegates its per-relocation checks to `replay_step`, which the new executor shares. The G3 replay and tamper tests pass, and `runs/g3_repairs` replays 50/50.

---

## 7. Measured costs and the G4 label-source assessment

| Component | Measured here (sparse 4–6-obstacle scenes) |
|---|---|
| Static endpoint check | < 1 ms per assignment |
| Relocation skill plan | 0.03–2.2 s each (primary REPAIR_PLAN events); one o01→21 relocation hit its budget |
| Target evaluation (complete skill + home) | 1.9 s (R4), 7.8 s (R2), 10.7 s (R0), **67 s** (R1, one 4000-node carry query); UNRESOLVED in 4.5–5.8 s (R5) |
| Primary episode | 4.3–67 s |
| Whole case analysis | 2 min 32 s wall on 5 workers: 5 queries, 16 audited assignments, 20 stored trajectories |

**Projection for G4** (to be validated in G4A, not a commitment):
- **Sparse queries.** A sparse query with about 8 audited candidates costs about 1–2.5 CPU-min. A 20-root audit with about 3 queries per root is therefore about 1–2.5 CPU-h, roughly 10–20 min on 8 workers. The 300-root pilot is about 15× that.
- **Dense queries.** Dense 35-obstacle relocations cost about 55 s per plan in G3. New-mode dense queries are therefore expected to be 10–50× costlier and were **not** exercised here.

**Label sources available now:**
- **Positives:** complete witnesses.
- **Certified negatives:** static invalidity, goal overlap, first-mover pose-only screens.
- **Unknowns:** target or relocation budgets, and gray bands, kept separately.

**Risk for G4.** Target UNRESOLVED arises quickly (about 5 s) in clutter, when the skill's finite pick/place-pair and connector budget ends without a witness. In dense scenes the unknown fraction could therefore be large. "Informative action-level negatives beyond trivial duplicate cells" currently come only from goal overlap and first-mover screens. Certified *path-level* negatives for static-valid assignments are not available from this backend.

---

## 8. Files changed (line counts: total / logical)

| File | Change | Lines |
|---|---|---|
| `data.py` | **new**: query records with `learner` / `labels` / `oracle_only` / `execution` namespaces, allowlisted learner scene, `action_context` and its hash, observation hash, `learner_tensors` (float32 + clean uint8 RGB) | 85 / 55 |
| `evaluate.py` | **new**: `Trace` (event log), `evaluate_target` (post-commit, achieved start), `primary_episode` (commitment boundary, replay-execute, abort, one target call), `audit_candidate` (offline teacher, certificates) | 159 / 120 |
| `cases.py` | **new**: scene construction (archived read-only or placed), `run_query`, poison audit, bounds, run record, replay archive, readiness matrix, summary rows | 210 / 162 |
| `case_figures.py` | **new**: figures A–F and clean observations | 243 / 207 |
| `tests/test_protocol.py` | **new**: 9 contract tests | 187 / 146 |
| `solve.py` | + `endpoint_xy`, `static_endpoints`, `goal_blockers`, `action_lower_bound`, `rank_proposals`; frozen A0 untouched | 319 / 212 |
| `verify.py` | + `replay_step` (shared by both protocols), `realize`, `plan_repair`, `final_state`; FROZEN_CONTROL functions unchanged in behaviour | 362 / 265 |
| `skill.py` | + `pick_certificate` (pose-only pick screen via the existing `screen_pick`) | 352 / 277 |
| `config.py`, `config.toml` | + `[protocol]`, `[proposal]`, `[target_evaluation]` with contradiction rules; fixture validation accepts stage `G3_5` (protocol declared, no frozen reference policy) | 228 / 177 |
| `fixtures.json` | version 5: five `G35_*` queries; G0–G3 entries unchanged | — |
| `run.py` | + `case-analysis` command (thin: Pool, records, figures, file writes) | 416 / **356** |
| `README.md` | documents v1.5 / v1.7, both protocols, new modules and commands | — |
| `runs/g3_5_initial_scene/` | **new** run (1.2 MB; no LFS needed) | — |

**Size review.** `run.py` is at 356 logical lines, above the ~300 review point.
- **G3.5's contribution:** about 38 lines. The G3.5 body lives in `cases.py`; the summary rows were moved there too.
- **Why the older bodies stayed:** the G0–G3 command bodies were left in place so archived CLI behaviour is preserved, as the instruction requires ("avoid unrelated rewrites").
- **Proposal, carried from report 0006 and still awaiting approval:** at G4 entry, move each stage's command body next to its owning module, keeping `run.py` as dispatcher plus shared I/O.

All other modules are within ~120–280 logical lines.

---

## 9. Unresolved issues, deviations and limitations

1. **Proposal source.** The candidates are hand-authored per query and were written with knowledge of G3 results and scratch probes. That is privileged knowledge, allowed for G3.5 plumbing only. The primary ranking rule itself uses only initial learner inputs (goal-occupancy score, moved count, declared order).
2. **R1 coverage.** R1 was found in **1 of 4** probed archived scenes. Zero-move target plans in G2 D2 `block_ab` and G3 D3 blocked were UNRESOLVED; dense T07 was not probed in the new mode. A failed search does not prove that no alternate route exists.
3. **Seed dependence.** Target evaluations are seeded from the episode key: primary and audit use different keys. Both R1 evaluations succeeded, but per-situation seed variance was **not measured**.
4. **Audit budget.** An assignment gets one target query, from its first complete relocation order. If that query fails, the assignment stays UNRESOLVED, even though another order (with a different end state) might succeed.
5. **Execution and abort.** Execution is a kinematic replay on a clone. REOBSERVE compares the achieved state with the committed witness exactly. The ABORT path is implemented but was **not exercised by a real deviation** in this run, because replay cannot deviate. No simulation and no hardware were used.
6. **Certificate scope.** Goal overlap needs a unique disc goal pose with the declared tolerance and no pushing. The first-mover and R4 LB = 2 arguments are scoped to the declared 48-candidate grasp family and its approach and closure checks. Neither is a general physical impossibility proof.
7. **Not yet implemented (G4/G5 items).** The slot-permutation equivariance test of learner tensors; the whole-assignment energy and Gibbs conditional; root splits; loss masks. None of these is claimed.
8. **Deviation in proposal source naming.** The config uses `MANUAL_CASE_CANDIDATES` rather than the guide's example `DETERMINISTIC_CASE_CANDIDATES`. Both are accepted, and the stricter name is used because the lists are hand-authored.
9. **Not committed.** The local deletion of the v1.4/v1.6 PDFs is not committed (see "Repository synchronization").

---

## 10. G4 readiness matrix (instruction §12)

| Prerequisite | Status | Evidence |
|---|---|---|
| Goal-conditioned query works without trajectory fields | **PASS** | `data.make_query` (no γ0/envelope fields); test 1; poison/delete audit for 5/5 queries (`cases.json` → `leakage_audit`) |
| Primary selection has no target feedback | **PASS** | `F_call_trace.png`; boundary check = True for 5/5 episodes; spy test 3/4; dependency direction (`solve`/`verify` do not import `evaluate`) |
| R0 zero-move witness and R1 objective distinction demonstrated | **PASS** | §4 R0, R1; `B_r1_route_comparison.png` |
| R2 occupancy certificate/witness | **PASS** | §4 R2 (LB 1 = UB 1); `C_r2_repair.gif`; also the R4 LB 2 argument |
| R3 alternative positives and R4 order dependence | **PASS** | `D_r3_alternatives.png`, `E_r4_orders.png` |
| Static/sequence/assignment/target statuses remain distinct | **PASS** | `cases.json` schema; R5 rows; tests 6–8 |
| Unknowns and old minima handled correctly | **PASS** | R5, R6 exhaustion control, gray band; test 11; report 0006 unchanged |
| Full-state continuity and legacy regressions pass | **PASS** | test 5 (bit-exact start); 83 tests; 5 replays; 84 archive files unchanged |
| Case-derived figures and reproducible data saved | **PASS** | §5; `run.py case-analysis`; replay 20/20 |
| Proposed G4 label sources and measured generation cost assessed | **PASS (assessment)** | §7. The coverage risk is flagged: path-level negatives are absent and the unknown rate in clutter may be high. |

**Decision.** The G3.5 interface and evidence prerequisites are met. G4 (G4A independent evidence generation, sparse roots first) **may start once you authorize it**.

This is not a data-readiness claim: data readiness is G4's own gate. Before scaling, I recommend that the G4 run plan declares four things:
1. Numerical coverage targets: zero-move successes, alternative repairs, decided negatives beyond static-invalid, and the maximum unknown fraction.
2. A deterministic geometry-based candidate generator (the B1-type control) to replace the hand-authored lists.
3. A seed-variance measurement of the target evaluator.
4. A decision on the `run.py` split.

**Stopping here for review. No G4 work has begun.**

---

## Repository synchronization

This turn commits the following together with this report:
- the source files, tests, configuration and fixtures;
- `runs/g3_5_initial_scene/`;
- the instruction file;
- the two new authoritative PDFs (v1.5, v1.7).

**Not committed:** the user's local deletion of `latent_causal_tamp_specification_v1_4.pdf` and `latent_causal_tamp_implementation_guide_v1_6.pdf`. They remain tracked in the repository because the archived G0–G3 frozen-control evidence was produced under those versions. Removing them from `main` needs your explicit decision; until then they remain an unstaged local deletion.

The commit hash is given in chat and will be recorded as "Previous turn sync" in the next report.
