# 0010 — G4D: V2 architecture migration checkpoint (ordered repairs, explanations, cost provenance)

| Field | Value |
|---|---|
| Report number | 0010 (new; 0001–0009 unchanged) |
| Date | 19 October 2026 |
| Stage | **G4D only**: a migration checkpoint, not a renumbering of earlier phases. Work: representation and checking support, a migration record, focused checks and a frozen sparse evidence plan. Not done: G4B, G4C, G5, training, bulk generation, 3D or hardware work. **No new experimental collection.** |
| Normative documents | Methodology **v1.6** and Implementation Guide **v1.8**, both read in full from their extracted text; addendum A1; reports 0007–0009 |
| Plain-language guide | `Architecture_Explained_Step_by_Step.md` is **not in the repository or anywhere on this machine** (filesystem search). The plain-language reading used here comes from the two contracts' appendices A and B. |
| Previous turn sync | Report 0009 was committed as `fcb7700c6f26384d82863a33b861e4ea1ca5b2dc` on `main`. At the start of this work, branch, HEAD and `origin/main` were verified identical. The only untracked items were the two new PDFs, which you placed in `instruction-phase-md/`. |
| Starting revision | `fcb7700c6f26384d82863a33b861e4ea1ca5b2dc` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0011. |
| Run directory | [`../runs/g4d_migration/`](../runs/g4d_migration/), produced by `python run.py g4d-plan --out runs/g4d_migration` then `python run.py g4d-migrate --out runs/g4d_migration` |
| **Decision** | **Implementation and plan: complete. G4D evidence: BLOCKED** until a numerical collection budget is authorized. **No physical order contrast was obtained**, and **no matched scene-effect or omission label was obtained.** Their counts are 0 because nothing was collected. |
| Compute used | 10.7 CPU-s for the migration audit (archived-trajectory replay only), about 0.6 s for plan freezing, about 4.5 min for tests and replays. No planner ran outside the focused tests. |
| Tests / replays | **115 passed** (101 existing + 14 new). All six archived runs replay (77/77/2/50/20/257 trajectories), written to a scratch path. Every prior run file and reports 0001–0009 are unchanged (`git status`: no tracked change under `runs/` or `responses-phases/`). |

---

## 1. Starting state and evidence reconciliation (step 1)

| Item | Verified value |
|---|---|
| Branch / HEAD / `origin/main` | `main` / `fcb7700` / `fcb7700` |
| Working tree | clean, apart from the two untracked PDFs in `instruction-phase-md/` |
| Deployment config hash | `sha256:a9f3f2360e17d9827e24b4e9bb32727569afdf04aa4f87c72ba3cccf50953ae3`. **Unchanged by G4D**; a test pins it to the G4A archive. |
| Robot profile hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858`, unchanged |
| G4A follow-up status | **Complete** (report 0009, commit `fcb7700`). No new zero-move witness; coverage stays at 3 (r05, r10, r19). |
| G4A gate | **NOT_READY_TO_SCALE** (3 zero-move roots against a target of 6). This is preserved; nothing here re-decides it. |
| G4A CPU overrun | 4.56 CPU-h against a 4.0 CPU-h cap. This is preserved and reported again here. |
| G4A label counts | 240 assignments: 44 positive, 86 negative, 110 unknown. Recomputed in the migration audit with the same counts. |

Guide v1.8 §8 restates the follow-up's unknown split as "67 relocation-search exhaustion, 29 target-budget exhaustion, 14 other". Report 0009 §2.5 attributes part of the 29 to a reason-code defect: `plan_skill` returns `PLANNER_BUDGET` even when enumeration finished. That defect is still **unfixed** and still applies to V2 relocation-failure *reasons*. It does not affect labels, because such failures stay UNRESOLVED either way.

---

## 2. Documents and versioning (step 2)

I followed the convention established at G4A: superseded PDFs move byte-identically to `docs/archive/` and the current pair sits in the root.

| File | Action | sha256 |
|---|---|---|
| `latent_causal_tamp_specification_v1_5.pdf` | moved to `docs/archive/` (git rename, blob `b3a6864b`) | `b2cd20967b2050dc6fdf8075abd6a46beda930cccb5fffc453d0a5bf2446c5a7` (unchanged) |
| `latent_causal_tamp_implementation_guide_v1_7.pdf` | moved to `docs/archive/` (git rename, blob `e505d6b1`) | `761cdd59cfc2650defc171f773febb2bb44481c6770445774844dec1d563fe48` (unchanged) |
| `latent_causal_tamp_specification_v1_6.pdf` | added to the root (copied byte-exactly) | `a4dcda1b308c4fbee4a830a5bfdc4a0a0ec3f34cbac3721a6dc1b080b77a4f42` |
| `latent_causal_tamp_implementation_guide_v1_8.pdf` | added to the root (copied byte-exactly) | `702637b8b695f1f37ee9c81ab88f9802af6aba91b30446833d4c2b936abbc446` |

`docs/archive/README.md` now lists all four archived files and the two current ones, with sha256 and blob IDs. Your untracked copies in `instruction-phase-md/` are **left in place and not committed**, so they are not duplicated in history. You can delete them or keep them.

---

## 3. Migration record: V1 → `INITIAL_SCENE_ORDERED_ONE_SHOT_V2`

The full machine record is [`migration_manifest.json`](../runs/g4d_migration/migration_manifest.json). It references the V1 sources by sha256: `g4a_plan.json`, `candidate_labels.json`, `result.json`, `scenes.json`, `arrays.npz`.

### 3.1 Fields and APIs

| V1 | V2 | What changes |
|---|---|---|
| `query.protocol = INITIAL_SCENE_ONE_SHOT_V1` | `INITIAL_SCENE_ORDERED_ONE_SHOT_V2` with `schema_version 1` | Same learner allowlist. The V2 query requires the SAFE_RETREAT action context, so its action hash equals G4A's (tested). |
| candidate `{label, cells}` | proposal `{label, sequence=[[id, cell], …]}`; `assignment` derived by `sequences.assignment` | Order is part of the proposal. There are no stay, padding or duplicate entries, and `[]` is the unique no-repair proposal. |
| `proposals.rank_proposals` | `sequences.rank_sequences` | Deduplication by ordered physical signature; V2 lexicographic rank (move count, predicted joint travel, endpoint distance, feasibility energy, signature) |
| `verify.plan_repair` (searches orders) | `verify.plan_fixed_order` | Realizes exactly the proposed order. V1 order search is kept for V1 and named baselines. |
| `evaluate.primary_episode` | same function with `planner=` injection; `ordered.primary_v2` plus `ordered.episode_audit` | A witness whose order differs from the proposal aborts before COMMIT. |
| `evaluate.audit_candidate` (assignment label) | `ordered.teach_sequence` (ordered label) | The first relocation witness and its cost are stored before the target is examined. |
| `data.aggregate` | `data.ordered_aggregate` | Evidence carries a scope: ORDER, ASSIGNMENT or TRAJECTORY. |
| single `status` | `static_status`, `ordered_feasibility_status`, `relocation_attempt_status`, `target_attempt_status`, `simulation_status`, `hardware_status` | Separate evidence masks |
| certificate kinds | `certificates.CERTIFICATE_SCOPE`, plus the new `ORDER_FIRST_ACTION` | Assignment-wide proofs are distinguished from order-specific ones. |
| `data.learner_tensors` | `data.learner_tensors_v2` | Adds the numeric robot profile (16 dimensions), FK joint positions, joint limits, normalized joints, instance masks and an appearance-anchor hash. V1 tensors are unchanged. |
| (none) | `effects.py`: scene and robot-start substitutions, omissions, deletion diagnostic, effect records | New |
| (none) | `ordered.cost_record`: first-witness normalized joint travel | New |
| REOBSERVE `{matches, reasons}` | adds object, commanded and achieved pose, q, gap, attachment and moved history | Additive trace fields; V1 decisions unchanged |

### 3.2 Labels: what transfers, and which need scope validation

| V1 label | V2 treatment | Validation performed here | Result |
|---|---|---|---|
| First-pass POSITIVE (44) | POSITIVE **for the exact recorded order only**; other orders UNRESOLVED | Replay of each archived witness, covering: identity and end policy; each relocation certified in its own pre-move scene; trajectory hash; start at the previous achieved q and gap; placement at the destination; retreat end; move-once; target record starting at the last achieved state and ending in a certified safe retreat inside the goal tolerance | **44/44 validated**: 3 empty, 25 one-move, 10 two-move, 6 three-move |
| NEGATIVE with an ASSIGNMENT-scope certificate (86) | NEGATIVE for **every** canonical order of that assignment | Scope rule plus the identical observation and action-context hash. The archived checker verdict is reused, not recomputed. | 86 assignments → **130 ordered sequences** (sum of m!) |
| NEGATIVE without such a certificate | UNRESOLVED | none needed | 0 occurrences |
| UNRESOLVED (110) | UNRESOLVED | none needed; no failed-search negatives | 110 |
| G3.5 labels (HOME_REQUIRED) | **Not transferred** (separate historical scope) | — | — |
| Legacy relocation traces | Joint travel reported under `LEGACY_V1_AUDIT_ORDER_SEARCH_FIRST_RELOCATION_WITNESS`; **not V2 cost labels** | J computed for all 41 nonempty validated witnesses (median 1.64, range 1.01–6.09) | 0 V2 cost labels |
| Order contrasts, scene-effect pairs, omission pairs | none exist in V1 records | — | **0** of each |

Labels that need scope validation before any future reuse:
- ordered positives, against exact state, policy, schema and witness replay (done here for G4A first-pass);
- assignment-wide negatives, against observation, action context, grasp family and move-once (done by rule);
- any use of G4A roots as V2 roots. They are V1 development roots and must not become a V2 benchmark without a new plan, as guide §10 requires.

The record is [`legacy_label_audit.json`](../runs/g4d_migration/legacy_label_audit.json), with one row per G4A assignment.

---

## 4. Requirement-by-requirement status

The learned outputs are design requirements. **No learned component exists.** The deterministic geometric task score stands in for ranking only.

| Requirement (v1.6 / v1.8) | Already existed | Changed or added at G4D | Still unimplemented or unvalidated |
|---|---|---|---|
| Initial infeasibility = empty-sequence query | Empty assignment evaluated by V1 primary and audit | The empty sequence is the unique no-repair proposal, has its own ordered label, and costs exactly 0 (tested) | Learned score, calibration and abstention (G5) |
| Scoped intervention-effect explanations | G2 privileged fixed-path interventions (different scope) | `effects.pose_substitution` (fixed robot, eligibility, changed-field audit); effect records with baseline/alternative hashes, fixed fields, anchor, both statuses and a mask; necessity UNESTABLISHED | No decided scene pair; no learned effect head |
| Repair-omission explanations | — | `sequences.omit`, `effects.omission_plan` and `omission_records` (subsets ≤ 2, capped at 16); omitted objects stay in every prefix (tested) | No decided omission pair |
| Ordered corrective proposals (objects, destinations and order together) | V1 endpoint assignments with external order search | Canonical sequences, derived assignment, ordered signature, frozen ranked pool | Learned scorer and sampler (G4B/G5) |
| Instance-mask pooling, not Slot Attention; robot in context | V1 tensors: poses, q, gap, attachment | Instance masks, robot profile, FK and limits in `learner_tensors_v2` | Frozen visual backbone and pooling (G5) |
| Ghosts are alternative poses; omission restores stay; deletion separate | Ghost substitution (`scene.substitute_pose`) | Prefix scenes keep every ID, with no clones; `deletion_diagnostic` is scoped DIAGNOSTIC_ONLY with label use NONE | — |
| One canonical sequence; no duplicates or padding; no target; cap | — | `validate_sequence` rejects duplicates, stays, the active target, the target's cell, unknown or off-grid poses, bool entries and lengths above the cap | — |
| Scorer sees order and prefixes; GRU summarizes | — | Prefix tensors (all objects, selected slot, destination, step, length) | GRU and readouts (G5) |
| Energy and Boltzmann sampler with Hastings ratios | — | Rank terms recorded as None, not invented | G4B |
| Separate scene/omission targets; anchored appearance; unknowns never labelled | V1 masks for binary and joint losses | `data.effect_label` (definite only when both sides are decided); `counterfactual_tensors` changes only `object_xy`; a re-rendered counterfactual image is rejected as an anchor | — |
| Cost = first complete relocation witness, normalized joint travel including transitions | — | `ordered.joint_travel` and `cost_record`, with policy and backend IDs, witness hash, start and end joints, per-record and per-phase breakdowns, and label availability | No V2 cost label collected |
| Full robot check may vary grasps and paths, never reorder | V1 per-skill grasp family | `plan_fixed_order` (greedy, no backtracking); the commit guard aborts on silent reordering (tested) | — |
| One-shot boundary | V1 trace boundary, abort, `advance` | `episode_audit`: ≤ 1 target call, after COMMIT and the last RELOCATE; committed order equals proposed; joint continuity; target start equals achieved state; per-move commanded vs achieved records | — |
| Target success = goal + SAFE_RETREAT; HOME diagnostic | Addendum A1 (`evaluate_safe_retreat`) | The V2 overlay requires `GOAL_AND_SAFE_RETREAT` and `SEPARATE_DIAGNOSTIC` | — |
| A failed path is not an order-wide proof | V1 assignment rule | TRAJECTORY scope is ignored by `ordered_aggregate`. The only order-scope negative is `ORDER_FIRST_ACTION`, checked independently. | — |

---

## 5. Files changed and why

Line counts are total / logical (non-blank, non-comment).

| File | Change | Lines |
|---|---|---|
| `config_v2.toml` (new) | Strictly validated V2 overlay: [protocol], [proposal], [cost], [explanation]. Kept separate so `config.toml` and every V1 hash and archived-plan guard (`audit.check_plan`, `teacher-run`) are untouched. Sampler, model and energy sections arrive with the code that reads them (G4B/G5). | 34 |
| `config.py` | `SCHEMA_V2`, `validate_v2` (contract rules: no reordering, ≤ 1 target evaluation, goal + safe retreat, move-once, no learned source, fixed rank keys), `load_config_v2` | 329 / 281 |
| `sequences.py` (new) | Proposal side only, importing no planner or target code (tested in a subprocess). Canonical form, validation, derived assignment, ordered signature, prefixes, omission subsets, endpoint distance C_d (support diagonal), deterministic task score, frozen ranked pool. Split from `proposals.py` (215 lines), whose primitives are reused. | 149 / 124 |
| `verify.py` | `plan_fixed_order` and `FIXED_ORDER_POLICY` | 412 / 352 |
| `evaluate.py` | `primary_episode(planner=…)`; proposal hash includes the sequence; abort on order mismatch before COMMIT; richer REOBSERVE record | 303 / 273 |
| `data.py` | `PROTOCOL_V2`, `make_query(protocol=…)`, `appearance_anchor`, `learner_tensors_v2`, `counterfactual_tensors`, `prefix_tensors`, `ordered_aggregate`, `effect_label` | 211 / 171 |
| `certificates.py` | `check_order_first_action` (independent re-check over all 48 grasps); `CERTIFICATE_SCOPE` | 207 / 181 |
| `ordered.py` (new) | Teacher and execution side: joint travel, cost record, certificate producers with scope, `teach_sequence`, `primary_v2`, `episode_audit` | 217 / 191 |
| `effects.py` (new) | Scene and robot-start substitutions, deletion diagnostic, changed-field audit, effect and omission records | 140 / 116 |
| `g4d.py` (new) | Migration manifest, legacy scope audit, frozen plan, commands | 365 / 331 |
| `g4d_figures.py` (new) | Figures A–D | 256 / 231 |
| `run.py` | `g4d-plan` and `g4d-migrate` subcommands | 137 / 126 |
| `tests/test_g4d.py` (new) | 14 focused checks | 312 |
| `docs/archive/README.md` | Lists the v1.5/v1.7 archive and the v1.6/v1.8 current pair | — |

**Size notes.** `verify.py` was already above the ~300 logical-line review trigger before G4D (330), and is now 352. `g4d.py` is 331, mostly declarative plan and field-map data. Neither is split here, because the guide calls the size a review trigger, not a reason to split arbitrarily. If you want them reduced, the natural split is the V1 FROZEN_CONTROL half of `verify.py` and the plan tables of `g4d.py`.

### Compatibility effects

- `config.toml` and the deployment hash are unchanged, so V1 commands, the G4A and follow-up plan guards and the replay adapter behave exactly as before. The replays fill the same sections as at report 0009.
- `primary_episode` without `planner` follows the same path. The extra REOBSERVE keys are additive. All 101 earlier tests still pass, including the G3.5 boundary, abort and fault-injection tests.
- No archived file was regenerated or edited.

---

## 6. Focused correctness checks (`tests/test_g4d.py`, 14 tests, about 13 s)

The target callbacks are stubs. Relocations on the G3.5 R4 fixture are actually planned, as earlier G3.5 tests already did. **These are software checks, not G4D evidence, and nothing from them is recorded as a label.**

| Check | What it asserts |
|---|---|
| V2 overlay strict | Reordering, 2 target evaluations, HOME end policy, wrong rank, target feedback, a learned source and an unknown section all fail. The deployment hash equals G4A's. V2 and V1 query hashes are equal. |
| Duplicate IDs, stays, target, cap | Each illegal form is rejected. The derived assignment is identical for both orders while the ordered signatures differ. Order is never re-sorted. |
| Frozen pool | The repeated sequence and the second `[]` are rejected. Both orders are kept once. The empty repair is screened out because the goal is provably occupied. The pool hash is deterministic. |
| Stay vs omission vs deletion | Prefixes keep every ID. An object is at its destination only after its own action. Omitted objects stay in every prefix. Deletion is DIAGNOSTIC_ONLY. |
| Unchanged visual anchor | A counterfactual changes **only** `object_xy`, and only o00's row. RGB, masks, anchor hash and robot fields are identical. A re-rendered counterfactual image is rejected as an anchor. |
| Fixed robot, eligibility | The eligible substitution changes only o00's pose and cell. A penetrating substitution is ineligible, and its effect stays **masked** rather than negative. A robot-start substitution leaves objects unchanged. |
| Unknown masking and scopes | Δ is definite only when both sides are decided. Trajectory-scope failures never decide. A witness plus an order-scope negative gives CONTRADICTION. Omission records are masked where a side is missing. |
| Order-scoped certificate | R4 order (o00→29, o01→18): `ORDER_FIRST_ACTION`/PICK is accepted with scope ORDER. The swapped order gets no certificate. Four tampered records are rejected. |
| Order preservation, cost accounting | The fixed-order verifier tries only the given order (the bad order stops at action 0, UNRESOLVED). The good order's witness keeps the order. J equals the sum per record and the sum per phase, starts at S0 and excludes `return_home`. Empty sequence gives J = 0.0 exactly. No witness gives no label. |
| Joint continuity, cost arithmetic | Hand-computed J matches. A discontinuous q or gap between records gives no label. A legitimate 6.2 rad joint-linear step is counted in full (no wrap shortcut). A waypoint outside the limits gives no label. |
| One-shot V2 boundary | Pool [bad, good]: the bad order fails before commitment, the good one is committed with its exact order. One target call, after the last RELOCATE. The audit flags pass. Per-move commanded pose equals achieved pose. A planner that silently reorders is aborted with zero target calls. |
| Teacher scopes | Unknown target with a relocation witness: ordered status UNKNOWN, but a **valid cost label**. A certified bad order: NEGATIVE, target NOT_RUN. A stay entry raises. |
| Proposal isolation | Importing `sequences` loads none of verify, evaluate, planner, skill, ordered or certificates. |
| Legacy validation | An archived two-move G4A witness validates. A 1e-4 rad waypoint change, or a missing end policy, makes it UNKNOWN. |

**A defect found and fixed during the checks.** `legacy_positive` first let `certify_trajectory`'s `ValueError` on a malformed record propagate. It now treats such a record as not validated, as `teacher.check_witness` already did.

**A design correction during the work.** My first cost check treated any single-segment joint step above π as a wrap. A real R4 witness has a certified 3.41 rad joint-linear step: the backend interpolates linearly inside ±π limits, so wrapping cannot occur. The criterion is now "every waypoint within the configured limits". The `max_wrap_step_rad` key was replaced by `waypoints_within_joint_limits = true`.

---

## 7. Supervision coverage (what exists for V2 now)

| Label family | Available now | Source |
|---|---|---|
| Initial infeasibility (empty sequence) | 3 POSITIVE, 13 NEGATIVE, 4 UNKNOWN (20 G4A roots) | Migrated (positives validated by replay; negatives by scope) |
| Ordered positives | 44 exact-order (multi-move: 16); 8 roots with ≥ 2 positives | Migrated |
| Ordered negatives | 130 sequences from 86 assignments; all ASSIGNMENT scope (70 goal-overlap, 10 target-pick, 3 first-mover, 3 combined) | Migrated |
| Order-scope negatives | **0** | — |
| Decided same-endpoint order contrasts | **0** | — |
| Scene-effect pairs (decided) | **0** | — |
| Omission pairs (decided) | **0** | — |
| Robot-start pairs | **0** | — |
| V2 first-witness cost labels | **0** (41 legacy J values are diagnostic only) | — |

---

## 8. Sparse G4D evidence plan (frozen, outcome-free)

The plan is [`g4d_plan.json`](../runs/g4d_migration/g4d_plan.json), with plan hash `sha256:c0f3bcb2c712ea7d1fd5ea36eb3e03428a0aa659e1f81ff8aaf7b8eeee13c4bf`, reproduced identically on regeneration. Its status is `FROZEN_PENDING_BUDGET_AUTHORIZATION`. It binds:
- both document hashes;
- the deployment config hash and the V2 config hash (`sha256:fd721f15…`);
- the robot profile hash;
- sha256 of 14 execution source files.

**Roots.** These are frozen G3.5 fixture scenes, plus the G4A legacy roots for D-V2-0:

| Key | Fixture | Goal cell |
|---|---|---|
| R0 | `G35_R0_D1REF` | 45 |
| R1 | `G35_R1_D1BLOCK` | 45 |
| R2 | `G35_R2_GOAL` | 45 |
| R4 | `G35_R4_ACCESS` | 28 |
| R5 | `G35_R5_D2BLOCK` | 53 |

These are sparse development scenes. They are not a V2 benchmark.

**Units.** There are 20 units (13 relocation skills and 20 target evaluations at most). Every unit has a frozen relocation key and target key; seeds come from `call_seed(41, key)`.

| Case | Units (sequence or intervention) | What decides it |
|---|---|---|
| D-V2-0 empty-repair success | Legacy g4a_r05, r10, r19 (validated: exact empty sequence, SAFE_RETREAT, J = 0); planned `seq:R0:empty` | **Already met by validated legacy evidence (3 roots).** R0 is kept as a V2-native unit. |
| D-V2-1 goal occupant | `seq:R2:empty`, `o03>60`, `o03>38`; scene `R2:{o03→60}`, `{o03→38}` (both eligible at fixed robot) | Accepted GOAL_OVERLAP on empty, a complete witness for a nonempty sequence, and both sides of a scene pair decided |
| D-V2-2 order contrast | R4 (o01→18, o00→29) vs (o00→29, o01→18); R2 (o01→21, o03→13) vs (o03→13, o01→21) | One POSITIVE and one **order-scope** NEGATIVE with the same endpoints. **A timeout never counts.** Otherwise BLOCKED. |
| D-V2-3 destination dependency | R2: o03→60 (o01 stays), (o01→21, o03→13) (chain), o03→13 alone (expected static-invalid: occupancy) | Alternatives retained with their occupancy constraints |
| D-V2-4 interaction | R4 r = (o01→18, o00→29), omissions {o01}, {o00}, {both}; R5 restorations of the G2_D2 blockers o02→40, o05→49 singly and jointly (all eligible) | Joint vs singleton effects, with both sides decided |
| D-V2-5 cost | R2 o03→60 vs o03→38 (C_d differs); R4 two-move | ≥ 2 complete relocation witnesses with V2 J. No predetermined inequality. |
| D-V2-6 robot start | `seq:R1:empty` at home vs `start:R1:0`, q = (π/2, −π/2, −π/2): the first eligible entry of a frozen list | At least one independently decided outcome per valid start |

**Policies.**
- Relocation uses `FIXED_ORDER_GREEDY_SKILL2D_V1` (repair skill budget, 2 failures).
- The target uses `evaluate_safe_retreat` (skill budget 4 failures, `max_nodes` 4000); HOME is a diagnostic only.
- The target is NOT_RUN when an accepted covering certificate already decides the order.
- Unknowns stay unknown. There is no root replacement and no loosening of collision rules, tolerances or budgets.

**Cancellation.** Each unit runs under the follow-up's process-tree CPU guard (`teacher.guard`); a censored unit becomes UNRESOLVED. A unit starts only if the CPU already spent plus the per-unit cap fits within the aggregate cap; otherwise it is NOT_RUN_BUDGET.

**Blocking acceptance (guide §9).** G4D fails if any of these is missing:
- one checked nonempty two-move sequence;
- one decided same-endpoint order contrast;
- one decided, eligible scene-effect pair;
- one decided omission pair;
- joint continuity and target-start equality on every complete witness.

### Budget dependency (not invented)

`per_unit_cpu_s`, `aggregate_cpu_s`, `workers`, `wall_guard_s` and `cancellation_margin_s` are **null**, with `authorization: REQUIRED`. To set them you need to authorize those five numbers. The plan includes reference measurements only:
- G4A whole-query CPU: median 296.7 s, maximum 3,743 s (primary episode plus a 12-assignment audit);
- follow-up target evaluations: 870 CPU-s censored twice (r04), and 0.56–0.63 s (r14, r15).

A G4D collection runner (`g4d-run`) that would execute the frozen units under the guard is **not written**. It depends on those numbers, and I did not want to ship an orchestration path that has never run.

---

## 9. Figures (scene-based; every node and arrow explained)

All four figures are drawn from frozen geometry or archived recorded trajectories. No path is interpolated or invented, and every planned item is labelled NOT RUN.

### A — [`A_canonical_sequences.png`](../runs/g4d_migration/A_canonical_sequences.png) (R4)

- **Panel 1** shows the real R4 scene with the full 3R arm at home.
  - Grey discs are obstacles; the orange disc t0 is the active target. The dashed red circle labelled GOAL is goal cell 28, occupied by o00.
  - Dashed circles are **ghosts**: proposed poses of the *same* object, not clones.
  - Each dashed arrow runs from an object's initial pose to its ghost. The number on it is the action index. Blue is r1 = (o01→18, o00→29); purple is r2 = the swapped order.
  - The box states that both orders have the same derived assignment and the same C_d (0.2134) but different ordered signatures.
- **Panel 2** is the ideal prefix scene before action 2 of r1. o01 is drawn at its proposed pose, and its dotted "vacated" circle marks the removed old occupancy. No robot is drawn, because a prefix carries no robot state.
- **Panel 3** is r1's final endpoint scene. Both vacated poses are marked.
- **Panel 4** is the learner appearance anchor: the clean initial RGB, with instance-mask contours in blue, reused unchanged for every hypothetical context. The box lists the five forms rejected before ranking, each with its reason.

### B — [`B_explanation_operations.png`](../runs/g4d_migration/B_explanation_operations.png)

- **Panel 1** is the R2 baseline c0: o03 on the goal, robot at q0.
- **Panel 2** is the intervention c0^I: o03 at cell 60. The dotted circle marks o03's vacated pose. The robot drawing is identical to panel 1, which is the fixed-robot rule. The box gives the computed eligibility (True), the changed fields (only o03's cell and xy), "robot unchanged: True", and states that Δ stays masked until both sides are decided.
- **Panel 3** shows the R4 omission. The numbered arrow is the remaining action (o00→29). The green ring marks o01 staying at its initial pose. The box lists the three planned omissions from the explanation budget.
- **Panel 4** shows R5's frozen interaction rule. The arrows restore the two G2_D2 blockers (o02→40, o05→49) to their reference cells, singly and jointly, and all three units are eligible. The note says deletion is a separate DIAGNOSTIC_ONLY operation. Every target-only outcome is labelled NOT RUN.

### C — [`C_legacy_witness_continuity_cost.png`](../runs/g4d_migration/C_legacy_witness_continuity_cost.png) (archived G4A g4a_r00, audit index 7)

- **Panel 1** shows S0 with the recorded three-move order (o03→40, o01→10, o04→28) as numbered arrows. The thin solid curves are the moved objects' **recorded** carried paths.
- **Panel 2** shows the achieved state after the last relocation. The dark arm is the target record's first waypoint, which is exactly the last relocation's end. The orange curve is t0's recorded transport, and the faint arm is the retreat end. The box gives the replay checks (start at the achieved state, safe retreat, goal tolerance, certified, hash).
- **Panel 3** plots the concatenated joint traces q0–q2 against waypoint index. Each dashed vertical line is a record boundary, where the end q equals the next start q bit-exactly. The dotted segment is the target record, excluded from J.
  - The title gives legacy J = 2.384 (per record 1.343, 0.723, 0.319).
  - It is labelled "NOT a V2 cost label", because the V1 seed keys and order search differ from the frozen V2 backend.

### D — [`D_sparse_plan_cases.png`](../runs/g4d_migration/D_sparse_plan_cases.png)

There is one panel per D-V2 case, each on its real frozen scene with the full robot.
- Numbered dashed arrows and ghosts are the planned sequences; each colour is a different sequence.
- The faint second arm in D-V2-6 is the frozen alternative start.
- Each box lists that case's unit IDs and eligibility.
- D-V2-0 carries a green "replay-validated legacy witness; J = 0" tag. Every other case is tagged "PLANNED - NOT RUN (budget not authorized)".
- The text panel restates the plan status, the work bounds, the UNSET caps and the five blocking acceptance items.

### Architecture flow as now implemented (text diagram)

```
initial scene + robot + task ──► sequences.rank_sequences ──► frozen ranked pool
        (learner fields only)          (no planner/target)            │
                                                                       ▼
                         verify.plan_fixed_order (exact order) ◄── next candidate (no target feedback)
                                       │ witness
                                       ▼
                     evaluate.primary_episode: COMMIT ─► RELOCATE/REOBSERVE per move ─► TARGET_EVALUATE once ─► FINISH/ABORT
                                       │
                                       ▼
                     ordered.episode_audit (order equality, continuity, target start, ≤1 call)
offline teacher: ordered.teach_sequence ─► certificates (scope) + first witness + cost ─► target once ─► data.ordered_aggregate
explanations:   effects.pose_substitution / omission_records ─► data.effect_label (masked unless both decided)
```

- **Learner-side arrows.** The first arrow carries only learner-allowlisted fields into the ranked pool. The pool is frozen before any check.
- **Commitment arrows.** The verifier receives one candidate at a time. On failure the episode moves to the next candidate, and no target feedback is used. A witness feeds COMMIT; after COMMIT the selection is fixed, and each move is executed then re-observed (validate, or abort).
- **Target and audit arrows.** The single target evaluation starts from the achieved state. The audit re-derives the boundary from the trace.
- **Teacher and explanation arrows.** The teacher path is separate and privileged, and is never imported by `sequences.py`. Explanation records compare two contexts that share the anchor.

---

## 10. Budget used

| Item | CPU | Notes |
|---|---|---|
| Migration audit (`g4d-migrate`) | 10.7 CPU-s | Replay of 44 archived witnesses; figures |
| Plan freeze (`g4d-plan`) | about 0.6 s | Geometry and eligibility screens only |
| Tests (full suite) | about 2.2 min | Includes real R4 relocations in focused tests |
| Compatibility replays (6 runs) | about 2 min wall, in parallel | Scratch outputs |
| **New G4D collection** | **0** | Not authorized |

---

## 11. Measured results vs. speculative benefits

**Measured or verified here:**
- 44/44 G4A positives replay-validate for their exact recorded order;
- 86 assignment-wide negatives transfer to 130 ordered sequences;
- no V1 record contains an order contrast, effect pair or V2 cost label;
- the V2 code passes 14 focused checks;
- V1 behaviour and hashes are unchanged.

**Not measured (design intent only):**
- that ordered proposals improve repair success;
- that a learned scorer can learn order dependence;
- that effect outputs localize causes;
- that the cost head reduces joint travel.

Nothing in this report supports or refutes these.

**Explicit statement.** **No physical same-endpoint order contrast was obtained**, and **no matched scene-effect or omission label was obtained.** The R4 first-action certificate computed inside a focused test confirms the checker, and repeats G3.5's known o00 pick exclusion. It is not recorded as G4D evidence, and its paired positive order was not evaluated with a real target.

---

## 12. Limitations

- `FIXED_ORDER_GREEDY_SKILL2D_V1` never backtracks into earlier actions, so a later failure may stem from an earlier realization choice. Such failures stay UNRESOLVED and never become negative.
- The only order-scope negative kind is the first-action screen in S0. Later-action exclusions would need tolerance-aware prefix proofs, because achieved poses lie within the release tolerance.
- Skipping the target when an accepted certificate covers the order saves compute but forgoes a contradiction probe on those units.
- The `PLANNER_BUDGET` reason-code defect (report 0009 §5) still mislabels some relocation-failure reasons.
- The G4D roots are sparse G3.5 development scenes.

---

## 13. Next blocking gate

**G4D collection**, which needs your authorization of the per-unit CPU cap, aggregate CPU cap, worker count, wall guard and cancellation margin. Then:
1. write and test `g4d-run` against the frozen plan;
2. collect;
3. report the D-V2 statuses against the blocking acceptance.

G4B (sampler exactness) has not started, and per guide §10 no downstream claim passes without G4D's physical evidence.

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains:
- code: `config_v2.toml`, `sequences.py`, `ordered.py`, `effects.py`, `g4d.py`, `g4d_figures.py`, `tests/test_g4d.py`, and edits to `config.py`, `verify.py`, `evaluate.py`, `data.py`, `certificates.py`, `run.py`;
- documents: the v1.5/v1.7 archive renames, the v1.6/v1.8 root PDFs and `docs/archive/README.md`;
- `runs/g4d_migration/` (about 0.8 MB);
- this report.

It is pushed to `main` at https://github.com/Narendhiranv04/latent-causal-tamp without force. The untracked PDFs in `instruction-phase-md/` are not part of the commit. The commit hash is given in chat and recorded in report 0011.
