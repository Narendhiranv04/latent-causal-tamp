# 0005 — G2 completion report: frozen obstruction and local causal effects

| Field | Value |
|---|---|
| Report number | 0005 |
| Date | 15 October 2026 |
| Stage | **G2** (Guide v1.6 §5): frozen obstruction and local causal effects. **G3 not started.** |
| Instruction file | `instruction-phase-md/G1_hardening_review_and_G2_prompt.md` (read in full) |
| Previous turn sync | report 0004 was committed as `5e1c311221343db7bafcde60bc39b6bee80dd323` on `main` and pushed to `origin/main` (remote head verified equal to local) |
| Run directory | [`../runs/g2_interventions/`](../runs/g2_interventions/) |
| Gate verdict | **PASS**: all G2 gates true for D1 and D2 (§A) |
| Scope | 2D layered-link **kinematic** fixed-action replay; finite grasp family; privileged diagnostic edits only. No corrective robot motion, dynamics or hardware. |

**Inputs read before coding:**
- both authoritative PDFs: Methodology §§3, 4, 6 and Guide §5 G2 specifically;
- all three files in `instruction-phase-md/`;
- reports 0001–0004;
- the G1 source and tests.

---

## 0. Plan as stated before implementing

1. **Policy.** Add `FINAL_DEV_SCENE_PLANNED / DEVELOPMENT_ONLY` for sparse development scenes whose reference is planned with their final background present, and keep dense-primary strict.
2. **Budgets.** Calibrate a node budget that binds before the wall cap.
3. **Oracle.** A per-object fixed-action oracle that replays the *recorded* γ0, with three-valued labels and first-offence details.
4. **`interventions.py`.** Frozen identity, privileged one-edit diagnostics with an audit, and F_fixed, c_i, d_I, Δ_I.
5. **Fixtures.** D1, then D2.
6. **Visuals.** Scene-backed figures and GIFs, plus clean observations.
7. **Code size.** `scene.py` sat at 287/300 logical lines, so its config section moves to `config.py`, as announced in reports 0003 and 0004.

All seven were implemented as planned.

---

## A. Stage objective and outcome

**Question (Methodology §6).** Given a complete, independently verified, *frozen* target action γ0, which scene entities obstruct *that specific motion*? And what happens to the unchanged action under controlled one-object interventions?

### Gates (from `runs/g2_interventions/result.json`, computed from recorded snapshots)

| Gate | D1 | D2 |
|---|---|---|
| `reference_clear`: γ0 VALID in its own final dev scene | true | true |
| `each_blocker_definitely_blocks` (c_i = 1, certified) | true | true |
| `full_block_invalid` | true | true |
| `all_corrections_restore_unchanged_action` | true | true |
| `oracle_agrees_with_whole_scene_replay` (all snapshots) | true | true |
| `present_state_valid_everywhere` (support y^w, pairs y^p) | true | true |
| `same_frozen_hash_everywhere` | true | true |
| `unrelated_edits_change_nothing` | true | true |
| `partial_correction_keeps_failure` (own conflict gone, action still blocked) | — | true |

### Guide G2 pass criteria

| Criterion | Result |
|---|---|
| Positive direct blocker found | Yes. D1: `o02`. D2: `o05` and `o02`. |
| Verified correction clears the unchanged γ0 | Yes. D1 `clear_a` is VALID; D2 `clear_ab` is VALID. |
| A blocking object leaves global failure at 0 while its own contribution vanishes | Yes. D2 `clear_a`: d_{o05} = −1 and Δ_I = 0, because `o02` still blocks. |
| One figure shows the fixed trace, per-entity delta and overall action status together | Yes: `d2_lineage.png`, `d1_lineage.png`. |

---

## 1. Definitions (exact semantics implemented)

**Frozen action γ0** (`interventions.FrozenAction`):
- **Contents:** the recorded joint-linear trajectory (q, finger gap g, phase per segment, attachment m per segment, tool-frame object offset, placement), the target ID, the reference scene hash and the robot profile hash.
- **Identity:** `action_hash = trajectory_hash(arrays, target, reference_scene_hash, robot_profile_hash)`.
- **Freezing:** only allowed after the full G1 replay (`certify_trajectory`, every segment CLEAR) in the reference scene.
- **Use:** every evaluation first calls `verify()`, which recomputes the hash. A replanned trajectory, or a descendant's scene hash substituted into the identity, raises.

**Per-object fixed-action compatibility y^a_i** (`motion.object_check`, Methodology §3). For a non-target object i resting at pose p:
- **Moving bodies:** every stored segment is certified by `geometry.certify` with a checker whose world is **object i alone**. That covers all robot bodies (links, housings, palm, rail, fingers), plus the **carried target** during `carry` under the recorded offset. Robot–robot pairs and support containment belong to γ0 itself and were certified at freeze time.
- **Resting and placed target:** the resting target (start phases) and placed target (`release`, `retreat`, `return_home`) are exact static disc pairs.
- **Thresholds:** single margin δ = 0.005 m on uninflated shapes; numeric band ε = 0.0002 m:
  - definite violation if d < δ − ε;
  - clear if d ≥ δ + ε;
  - otherwise UNRESOLVED, and a budget stop is also UNRESOLVED.
- **Result:** y^a_i is the three-valued conjunction over segments: any INVALID dominates; all VALID gives VALID; otherwise UNRESOLVED.
- **First offence recorded:** kind (`ROBOT_BODY`, `CARRIED_TARGET`, `RESTING_TARGET`, `PLACED_TARGET`), body, phase, segment, s, d. This is the first *certified* violation, which can be a δ-margin breach before the deepest overlap.
- **Per-phase magnitude:** the minimum clearance at stored waypoints (a diagnostic magnitude, not a proof).

**Other quantities:**

| Quantity | Definition |
|---|---|
| y^w_i (support) | resting at a legal supported cell, disc inside the support |
| y^p (pairs) | all present resting pairs (symmetric), gap ≥ δ |
| **F_fixed(S; γ0)** | AND_i y^a_i (three-valued). Methodology §6 F_fixed: does the *unchanged* action succeed in S? |
| Present-state validity | AND of y^w and y^p |
| **c_i(S, γ0)** | 1[y^a_i = INVALID] (None if UNRESOLVED): the operational direct-blocker indicator, D(S; γ0) = {i : c_i = 1}. It is reported with the deficit max(0, δ − d_min,i) and the first offence. It is **not** a causal-identifiability claim. |
| **d_I** | c(S^I, γ0) − c(S, γ0) per ID; an absent (removed) object contributes 0 |
| **Δ_I** | F_fixed(S^I) − F_fixed(S), with VALID = 1 and INVALID = 0, None if either is unresolved |
| Independent cross-check | `whole_scene_replay`: the full G1 replay with **all** objects present at once (full checker), plus static placed-target pairs. It must equal F_fixed; it does in all 15 snapshots. |

**Interventions** (`interventions.Edit`, `apply_edit`, `audit_edit`):
- **RELOCATE:** an existing obstacle ID moves from its legal resting cell to a *vacant* legal cell. These form the ancestry edges.
- **REMOVE:** do(present_i = 0), used only for twins, never to create a failure.
- **Labelling:** every edit carries `role = PRIVILEGED_DIAGNOSTIC` and `robot_executed = False`. Families record `executed_repairs = 0` and `moved_history = []`. Corrective robot motion is reserved for G3.
- **Audit on every edge:**
  - identical root, lattice, robot state, legal cells, domain policy, profile and action fields;
  - identical ID list (or exactly the removed one missing);
  - every other object bit-identical;
  - the edited object at its destination cell;
  - no present-state overlap.

---

## 2. Reference-policy correction (instruction item 1)

`config.REFERENCE_POLICIES` now has three classes; `validate_fixtures` runs whenever fixtures are loaded:

| Policy | Role | Enforced condition |
|---|---|---|
| `FINAL_DENSE_PLANNED` | `PRIMARY` | if obstacle cells are explicit: 30–40 obstacles (Methodology §1) |
| `FINAL_DEV_SCENE_PLANNED` (new) | `DEVELOPMENT_ONLY` | explicit obstacle list with fewer than 30 obstacles |
| `SPARSE_SEEDED_REFERENCE` | `BOOTSTRAP_ONLY` | unchanged |

D1 and D2 use `FINAL_DEV_SCENE_PLANNED / DEVELOPMENT_ONLY`. They are neither dense primary roots nor sparse-seeded bootstraps.

`test_g2_reference_policy_is_enforced` checks all three valid classes, plus rejection of:
- a missing policy;
- a role mismatch;
- an unknown policy;
- a dev scene posing as primary;
- a "dev" scene with 35 obstacles;
- a dev scene without an explicit list;
- a sparse scene posing as dense primary.

---

## 3. Deterministic budget calibration (instruction item 2)

- **The problem:** the 20,000-node cap could never bind before the 30 s wall cap.
- **Measured:**
  - verifier calls are now counted per connector (`Checker.n_evals` → `Plan.evals`, logged with nodes, seconds and `wall_clock_cut`);
  - **G1 under the accepted planner:** the largest successful RRT search used **1,387 nodes**, across 28 RRT successes;
  - **G2 references:** at most **139 nodes**;
  - about 90 nodes/s.
- **Chosen:** `max_nodes = 4000` (about 2.9× the largest observed success; the deterministic, canonical limit) and `max_wall_seconds = 300` (a safety cap about 6× the node budget's time). Evaluation budgets are unchanged (`certify_max_evals = 4000`, `edge_max_evals = 200`).
- **G1 preserved:** G1 was rerun under the new budget (`check --no-figures`, scratch). **No status change, no trajectory-hash change, no wall-clock dependence** against `runs/g1_hardening`. The G1 run directories keep their original `config.json` (G1 config hash `bcfd8bd2…`); the live config hash is now `95c78c4b…`. The robot profile hash is unchanged.
- **This run:** both G2 references used every connector with `wall_clock_cut = false`.

| Reference connector | D1 nodes / verifier calls / s | D2 nodes / verifier calls / s |
|---|---|---|
| pregrasp | 97 / 1562 / 0.57 | 137 / 2582 / 0.95 |
| carry | 139 / 9001 / 4.5 | 2 (direct) / 5 / 0.0 |
| return_home | 135 / 3581 / 1.27 | 93 / 1748 / 0.65 |

---

## 4. Reference actions (instruction item 3)

Both references were planned by the existing G1 planner in their **final** development scene, with every background object present, then independently replayed, frozen and stored.

| | D1 (`G2_D1`, `root_d1`) | D2 (`G2_D2`, `root_d2`) |
|---|---|---|
| Background obstacles (cells) | 4: o00 3, o01 13, o02 50, o03 60 | 6: o00 4, o01 15, o02 40, o03 61, o04 7, o05 49 |
| Target action | t0: cell 18 → 45 | t0: cell 26 → 53 |
| Reference status | VERIFIED_FEASIBLE, replayed clear; every y^a_i VALID | same |
| Waypoints | 197 | 32 |
| action_hash | `sha256:487ec18878068e01501c6737f1c58ec4cd1b9e410560bd4d8f7f8c32c5784355` | `sha256:27cb5a04f8caac257dc622bbe3fc32e460de092928e2b64701152bb79a99295f` |
| reference_scene_hash | `sha256:f635e6aa76d6e6bd40d535df97eda3669323917a19c128f48f84802289b2a977` | `sha256:ea6ac30b4aad7e00d9209a8a88513fd5280e3cbfefa832ab9e196a1990e6754d` |
| robot_profile_hash | `sha256:2d798676…1ae858` (G1-tested) | same |

- **Stored:** the arrays are in `arrays.npz` (`G2_D1__q`, `__gap`, `__phase`, `__attached`, `__held_local`, `__place_xy`), the scenes in `scenes.json`, and the full records in `result.json`.
- **Replay:** `python run.py replay --run runs/g2_interventions` re-certifies both frozen references and their hashes ([`replay.json`](../runs/g2_interventions/replay.json)).
- **Determinism:** the hashes were identical across three independent full G2 runs.
- **Candidate not used:** an exploratory candidate `D2a` (t0 18 → 45 with 6 obstacles) was **UNRESOLVED** in reference planning under the old 30 s budget. It was not used, and nothing was fabricated. D2 was chosen as a different valid development fixture.

---

## 5. Interventions, lineages and results (instruction item 4)

**Deterministic construction rules** (`interventions.build_family`; nothing is hand-picked):
- **Intrusion cell:** a vacant legal cell (not the target's resting or placement cell) whose disc **genuinely overlaps** the swept full body: negative clearance at stored waypoints, not just a δ graze. Preference order: a first-offending phase not used by earlier blockers, then the deepest overlap, then the lowest cell ID.
- **Moved ID:** the currently non-blocking obstacle nearest to that cell.
- **Correction endpoint:** the nearest vacant cell that is VALID for the object, excluding its original reference cell. This is an alternative admissible endpoint, not an undo; `test_one_edit…` separately proves that undoing an edit reproduces the reference scene hash.
- **Removal twins** come from the fully blocked snapshot. **Unrelated edits** come from the reference and from the fully blocked snapshot.

### D1 lineage

```
ref ──RELOCATE o02 50→51──► block_a ──RELOCATE o02 51→43──► clear_a
 │                            ├──REMOVE o02 (twin)──► remove_a
 └──RELOCATE o00 3→4──► unrelated_ref       └──RELOCATE o00 3→4──► unrelated_block_a
```

| Snapshot | Edit | F_fixed | Whole replay | Δ_I | d_I | Blocking IDs (c = 1, deepest waypoint overlap) |
|---|---|---|---|---|---|---|
| ref | — | VALID | VALID | — | — | none |
| block_a | o02 50→51 | **INVALID** | INVALID | −1 | o02: +1 | o02 (−46.1 mm) |
| clear_a | o02 51→43 | **VALID** | VALID | +1 | o02: −1 | none |
| remove_a | REMOVE o02 | VALID | VALID | +1 | o02: −1 | none |
| unrelated_ref | o00 3→4 | VALID | VALID | 0 | none | none |
| unrelated_block_a | o00 3→4 | INVALID | INVALID | 0 | none | o02 (−46.1 mm) |

**D1 first offence:** the **carried target** (`held`) during **carry**, segment 133. The first certified violation is a δ breach of 3.4 mm; the deepest overlap at stored waypoints is −46.1 mm. Per-phase status: o02 is clear in pregrasp, approach and close/attach, and INVALID from carry onward.

### D2 lineage (two independent direct blockers)

```
ref ─RELOCATE o05 49→50─► block_a ─RELOCATE o02 40→57─► block_ab ─RELOCATE o05 50→41─► clear_a ─RELOCATE o02 57→49─► clear_ab
                                                          ├─REMOVE o05─► remove_a
                                                          ├─REMOVE o02─► remove_b
                                                          └─RELOCATE o00 4→3─► unrelated_block_ab
ref ─RELOCATE o00 4→3─► unrelated_ref
```

| Snapshot | Edit | F_fixed | Whole replay | Δ_I | d_I | c_{o05} | c_{o02} |
|---|---|---|---|---|---|---|---|
| ref | — | VALID | VALID | — | — | 0 | 0 |
| block_a | o05 49→50 | **INVALID** | INVALID | −1 | o05: +1 | **1** (−34.0 mm) | 0 |
| block_ab | o02 40→57 | **INVALID** | INVALID | **0** | o02: +1 | 1 | **1** (−31.6 mm) |
| clear_a | o05 50→41 | **INVALID** | INVALID | **0** | o05: **−1** | **0** | 1 |
| clear_ab | o02 57→49 | **VALID** | VALID | +1 | o02: −1 | 0 | 0 |
| remove_a | REMOVE o05 | INVALID | INVALID | 0 | o05: −1 | 0 (absent) | 1 |
| remove_b | REMOVE o02 | INVALID | INVALID | 0 | o02: −1 | 1 | 0 (absent) |
| unrelated_ref | o00 4→3 | VALID | VALID | 0 | none | 0 | 0 |
| unrelated_block_ab | o00 4→3 | INVALID | INVALID | 0 | none | 1 | 1 |

**D2 first offences:**
- `o05`: **link 2** during **pregrasp**, d = −31.0 mm, segment 1.
- `o02`: **link 1** during **pregrasp**, d = −17.4 mm, segment 1.

Both obstacles intrude on the home→pregrasp connector's arm sweep. The rule preferred a different first phase for B, but no vacant overlapping cell had a different *first* phase. The phase heatmap shows `o05` also overlaps the carry sweep, and `o02` every phase.

**The central G2 observation (Methodology §6).** In `block_ab` → `clear_a`, Δ_I = 0 (the action stays blocked), yet d_{o05} = −1: `o05`'s own conflict disappears. A binary whole-action outcome alone would have wrongly suggested `o05` was irrelevant. Both relocation and removal of a single blocker leave the action blocked; correcting both restores the **unchanged** γ0. These snapshots prove geometric clearance of the frozen action only, **not** that a robot could execute these relocations; that is G3.

**Oracle cost:** 207–1038 verifier calls per snapshot (all obstacles). The whole G2 run takes about 2.5 min on 2 worker processes.

---

## 6. Tests and verification (instruction item 6)

| Command | Result |
|---|---|
| `python -m pytest tests -q` | **53 passed** (15 G0 + 27 G1 + 11 G2) in 18.3 s |
| `python run.py intervene --out runs/g2_interventions` | exit 0, all gates true |
| `python run.py replay --run runs/g2_interventions --report runs/g2_interventions/replay.json` | `replay_passed: true` (2 frozen references) |
| `python run.py replay --run runs/g1_robot --report runs/g2_interventions/replay_of_g1_robot.json` | `replay_passed: true`, 77/77 |
| `python run.py replay --run runs/g1_hardening --report runs/g2_interventions/replay_of_g1_hardening.json` | `replay_passed: true`, 77/77 |
| G1 `check --no-figures` under the new budget (scratch) | identical statuses and hashes to `runs/g1_hardening` |
| `git status` on `runs/g0_scene`, `runs/g1_robot`, `runs/g1_hardening` | 0 changes (archives untouched) |

**New tests** (`tests/test_interventions.py`, plus the policy test in `tests/test_scene.py`):

| Test | Guards |
|---|---|
| `test_frozen_hash_invariance_and_tamper_detection` | the same root across the lineage; a **silently replanned** γ0 (only the last waypoint perturbed) is rejected; a **descendant scene hash substituted** into the identity is rejected |
| `test_one_edit_invariants_and_forbidden_edits` | identical IDs and count; exactly one object changed; same robot and legal cells; rejects **inserting a new obstacle**, two changes on one edge, an occupied destination, moving the target, and an edit claiming robot execution; undo reproduces the reference hash |
| `test_support_vacancy_and_pair_validity` | y^w, y^p and occupancy invariants on every snapshot; closest pair gap 0.032 m |
| `test_blocker_detected_on_full_body_sweep` | `o05` INVALID on **link 2** (not a TCP trace); the whole-scene replay agrees; others VALID |
| `test_per_id_conflict_cancels_while_global_failure_stays` | `clear_a`: Δ_I = 0, d_{o05} = −1, c_{o02} = 1; `clear_ab` restores; oracle agreement |
| `test_removal_differs_from_relocation_but_both_clear_own_conflict` | do(present = 0) twin: the object is absent, its contribution 0, the action still blocked |
| `test_unrelated_edit_leaves_outcome_unchanged` | from the reference and from the blocked state: Δ_I = 0 and d_I = 0 |
| `test_privileged_diagnostics_are_never_executed_repairs` | `executed_repairs = 0`, `moved_history = []`, the robot state never changes, one frozen hash, gates computed |
| `test_margin_boundary_and_gray_band` | a disc at δ + 2ε is VALID, at δ **UNRESOLVED**, at δ − 2ε INVALID (first body `base`); conjunction semantics |
| `test_contact_kinds_resting_carried_and_placed_target` | phase-specific kinds: resting target (pregrasp), carried target (carry), placed target (release); clear elsewhere |
| `test_budget_exhaustion_is_unresolved_not_proof` | the same truly-clear disc is VALID with full budget (after subdivision) and UNRESOLVED with 2 evaluations |
| `test_g2_reference_policy_is_enforced` | §2 |

**Mutation checks** (each test fails on the mutant and passes on the real code):
- gray band counted as VALID;
- ID-insertion audit disabled;
- frozen identity not verified;
- carried target ignored by the oracle.

Two tests initially passed under their mutant, because a *second* check caught the tampering. They were sharpened so each targets exactly its own guard: an inserted ID that sorts last (`z99`), and a perturbation of the final waypoint only.

---

## 7. Visualizations (instruction item 7; all in `runs/g2_interventions/`)

Every panel uses the same fixed axes (the G1 robot view), physical 8×8 grid, robot base, object IDs and full articulated robot (links, housings, palm, rail, fingers, carried disc). Robot poses come only from the frozen recorded γ0. Edits are dashed arrows labelled "diagnostic, not robot-executed".

| File | What it shows |
|---|---|
| [`d1_lineage.png`](../runs/g2_interventions/d1_lineage.png) | **D1: reference → intrusion → corrected.** The blue TCP and orange object traces of the *recorded* γ0 are the same in all three panels. In the intrusion panel the robot is drawn at the certifier's **first violating configuration** of the actual segment (segment ends ghosted), with the carried target overlapping `o02` (red ring). The text gives F_fixed, c_{o02}, the first certified violation and the deepest overlap. |
| [`d2_lineage.png`](../runs/g2_interventions/d2_lineage.png) | **D2: reference → A → A+B → A corrected → both corrected**, printing F_fixed, c_{o05} and c_{o02} in every panel. Link 2 (A) and link 1 (B) are outlined at their real violating configurations. Panel 4 shows the key fact: **F_fixed = INVALID with c_{o05} = 0**. |
| [`attribution.png`](../runs/g2_interventions/attribution.png) | **Per obstacle × phase:** colour is the certified phase status (green VALID, amber UNRESOLVED, red INVALID), numbers are the minimum waypoint clearance in mm, and bold names the first offending body. Panels: D1 `block_a`, D2 `block_ab`, D2 `clear_a`. |
| [`fixed_action_replay.gif`](../runs/g2_interventions/fixed_action_replay.gif) | **The unchanged q/g/attachment trajectory replayed synchronously** on six snapshots (D1 ref/block/clear; D2 A+B / A cleared / both cleared). Frames where the full body comes within δ of an object are outlined, with a "fixed-action COLLISION" banner (e.g. link 1 through `o02` during release); the corrected snapshots replay clean. Each panel's certified F_fixed is tagged. |
| [`interventions.gif`](../runs/g2_interventions/interventions.gif) | **The lineage as held snapshot frames**, each labelled "PRIVILEGED DIAGNOSTIC EDIT, not robot motion". There is no animated teleportation. |
| `obs_G2_D{1,2}_<variant>.png` (15 files) | **Clean learner observations** for every snapshot: top-down RGB with no overlays, the target rendered like every obstacle. |

**What these do not prove:**
- that any intervention is executable by the robot (G3);
- dynamics or contact forces;
- causal identifiability;
- anything about other target actions. Every verdict is about **this** frozen γ0.

The animation frames' collision outlines are *sampled* illustrations; the certified status is the panel tag.

---

## B. Files created or modified

| File | Status | Purpose | Physical / logical lines |
|---|---|---|---|
| `config.py` | **new** (split from `scene.py`) | Config schema, physics checks, hashes, `REFERENCE_POLICIES` + `validate_fixtures` (three classes) | 181 / 137 |
| `scene.py` | modified | Config section moved out; scene records only | 250 / 163 |
| `interventions.py` | **new** (guide) | `FrozenAction`, `freeze`, `Edit`/`apply_edit`/`audit_edit`, y^w/y^p, `evaluate`, `whole_scene_replay`, contributions, `edge_effect`, `scan_cells`, `build_family`, `reference_family`, `family_summary`, `family_gates` | 314 / 224 |
| `intervention_figures.py` | **new** (split from `figures.py`, size) | lineage, attribution, replay GIF, snapshot GIF | 197 / 156 |
| `motion.py` | modified | `ObjectCheck`, `object_check` (per-object oracle), `_conjoin`, three-valued labels | 298 / 197 |
| `geometry.py` | modified | `Checker(self_pairs=False)` for the per-object oracle; `n_evals` counter | 369 / 251 |
| `planner.py` | modified | `Plan.evals` | 253 / 182 |
| `skill.py` | modified | Connector costs in `used`; G1 job helpers moved here from `run.py` | 331 / 265 |
| `run.py` | modified | `intervene` command; replay usable for G2 frozen references | 312 / 265 |
| `config.toml` | modified | `max_nodes` 4000, `max_wall_seconds` 300 (calibrated) | 84 |
| `fixtures.json` | modified | `G2_D1`, `G2_D2` (`FINAL_DEV_SCENE_PLANNED / DEVELOPMENT_ONLY`) | 164 |
| `tests/test_interventions.py` | **new** (guide) | 11 G2 tests | 205 / 155 |
| `tests/test_scene.py`, `tests/test_arm2d.py` | modified | Imports from `config`; extended policy test | 219 / 169, 300 / 222 |
| `README.md` | modified | Status, modules, `intervene`, policy table | — |

**Code organisation:**
- **`config.py`:** split out because `scene.py` was at 287 logical lines and would have exceeded 300 with the policy rules (announced in 0003 and 0004).
- **`intervention_figures.py`:** split out because adding G2 figures to `figures.py` would have exceeded the guideline. This is a separate responsibility: intervention/attribution views versus G1 task views.
- **`skill.py`:** receives the G1 job helpers, so `run.py` stays a thin dispatcher.

The largest modules are `run.py` and `skill.py` (265 logical lines each). The undefined-name and unused-import scans are clean.

**Source SHA-256:**

| File | SHA-256 |
|---|---|
| `config.py` | `9f6c11f5a79e763c89e57f3c13f437c4fa0d23ac887924b5df4de2dcc5d90e11` |
| `scene.py` | `befae9f1d724120bc070a74b5145443af17b0a6ba592e460b1ce02a5872c807c` |
| `geometry.py` | `3db5ad2cee5dc506c6d3315c6a099c755897b2b07a4a432c7d309e642eab3917` |
| `motion.py` | `f2052d6049e288036122f0a31bc70791d9da6824b59036866ad411b215dd9678` |
| `planner.py` | `d48cc2f43a18c5b35456397fbf8fb5fa4fedd9f83ebe2371331f49696fc831d2` |
| `skill.py` | `657ea06dab9684eb37a95b2ffda4e2f30eca96cdffa7c78c4b87b9a2d756dd5c` |
| `interventions.py` | `3c419b5f3f4ed743ca774cf9f254ac9ee54a1386ed8d9137faeb9b281e122491` |
| `intervention_figures.py` | `4533fa1dace58de0294e9dda974ffb4124b8527c739126ab2f551397b03056e5` |
| `run.py` | `fd073bd8afda5758569ae72a565092f140406c2bbb870ff3ff250d7df18ad06b` |
| `tests/test_interventions.py` | `d157ecbc98f3d39cef486d6e5135409c1d3f1e31541ab6fcaa98ba25907d449e` |
| `config.toml` | `f8f71110ec8bc05a02f97f88eb232d9b4235cbeeeb0b1f3a2a1c90cd4ecb78a0` |
| `fixtures.json` | `8653944656d56e68cb67d5da15673149b0f69e97970537b236572a30ac1e1c17` |

---

## C. Configuration and reproducibility

| Item | Value |
|---|---|
| Config hash (G2) | `sha256:95c78c4b7fb89bacad99f799de6d4cadf52107a754104a1b367350f70244efc9` |
| Robot profile hash | `sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858` (G1-tested, unchanged) |
| Seeds | planner base 41; per query `crc32("<fixture>/<connector>")` |
| Versions | Python 3.13.11, numpy 2.4.0, matplotlib 3.11.2, pillow 12.0.0, pytest 9.1.1 |
| Determinism | identical frozen hashes across three G2 runs; G1 hashes unchanged under the new budget |
| Run directory | `runs/g2_interventions/`: 3.0 MB (largest file: `fixed_action_replay.gif`, 2.1 MB); no LFS needed |

---

## F. Scientific interpretation and limitations

**Established**, for these two development families and within the kinematic 2D scope:
- the frozen-action oracle localises obstruction **per object, per robot body and per phase** on the full articulated sweep, including the carried object;
- it is independently confirmed by a whole-scene replay;
- matched one-edit interventions with stable IDs and an unchanged action hash move objects into and out of conflict exactly as the per-object attribution predicts;
- per-object effects (d_I) can be nonzero while the whole-action effect (Δ_I) is zero, which is the reason Methodology §6 keeps them separate.

**Limitations and boundaries:**
1. **Kinematic only.** The scope is `FIXED_ACTION_KINEMATIC_REPLAY`: no dynamics, contact forces, controller or hardware (`NOT_RUN`).
2. **Development scenes only.** D1 and D2 are `DEVELOPMENT_ONLY` sparse scenes. No dense 30–40-object primary root was constructed or claimed; that is later work under `FINAL_DENSE_PLANNED`.
3. **Per-object decomposition.** y^a_i judges each object against γ0 alone. Object–object interactions enter only through the present-state pair factor. The whole-scene replay agreeing everywhere is evidence that the decomposition holds here; it holds in general for this rigid, pairwise model (Methodology §4).
4. **Magnitudes are not proofs.** Waypoint-sampled clearances are diagnostic magnitudes; the statuses are certified.
5. **Excluded cells.** Intrusion scans exclude the target's resting and placement cells. "Occupied desired endpoint" conflicts (`PLACED_TARGET`) are implemented and tested, but belong to the later F4 family.
6. **Interventions are not repairs.** They are privileged diagnostics. Whether a robot can execute a correcting relocation, and in what order, is G3's move-once verifier.
7. **No unresolved cases** occurred in the G2 run. Gray-band and budget handling are covered by tests.

---

## G. Next-stage readiness

**G2 gate: PASS.**

**G3 (not started)** is the analytic endpoint assignment (A0 min-cost matching / k-best) and the full move-once order verifier with robot-executed relocations, connectors and replay of the unchanged γ0. It starts from these frozen families, the oracle (y^a, y^w, y^p) and the policy and budget rules.

**Blockers:** none. Two points to confirm before G3:
1. Whether D1/D2 should be reused as G3's first development roots, or new D2/D3 roots built with order/access dependence (Guide Dev-3).
2. The T00/dense-root timeline under `FINAL_DENSE_PLANNED`.

---

## Repository synchronization

- Repository `https://github.com/Narendhiranv04/latent-causal-tamp`, branch `main`.
- The code, configs, fixtures, tests, README, the new instruction file, `runs/g2_interventions/` and this report are committed together.
- The commit hash and push result are given in the chat reply and recorded in report 0006.

**STOP — Awaiting explicit approval before G3.**
