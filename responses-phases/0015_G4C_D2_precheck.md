# 0015 — G4C-D2-P0: witness-first constructive 2D dataset — PRECHECK ONLY

| Field | Value |
|---|---|
| Report number | 0015 (new; 0001–0014 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4C-D2-P0 precheck only.** Static geometry, replay of ARCHIVED witnesses, synthetic and unit tests, planning artifacts. **No** new teacher labels, IK or motion search, target evaluation, root-scale generation, training, 3D or hardware. |
| Execution contract | `instruction-phase-md/G4C_D2_P0_Witness_First_Precheck_Instructions.md` (170 lines, read in full; your file, left untracked) |
| Documents read | Reports 0011–0014; addenda A1 and A2; Methodology v1.7 and Guide v1.9 (your untracked bundle, unchanged hashes); Methodology v1.6 and Guide v1.8 (root PDFs) |
| Previous turn sync | Report 0014 was committed as `68161515534000f0211c578e72911f78aa4b6fe0`. At the start, HEAD, `main` and `origin/main` all equalled it, with no tracked modifications. |
| Starting revision | `68161515534000f0211c578e72911f78aa4b6fe0` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0016. |
| Run directory | [`../runs/g4c_d2_precheck/`](../runs/g4c_d2_precheck/), produced by `python run.py g4c-d2-precheck --out runs/g4c_d2_precheck` (exit 0; 234 CPU-s, all of it certification replay) |
| **Decision** | **`G4C_D2_PRECHECK_PASS`.** All new target, repair and intervention labels are **NOT_RUN**. **STOP.** |

---

## 1. Verified baseline and preservation

- **Reported G4C-P1 claims verified.**
  - Reported values: 59 units, 13/26/20 labels, 340.2 CPU-s.
  - `runs/g4c_pilot/pilot_result.json` agrees with them.
  - Tests and replays still pass: **193 tests** after this stage (183 plus 10 new), and all six archived replays (77/77/2/50/20/257).
- **Untouched.** The frozen G4C parent plan, pilot plan, pilot result and G4D final plan, plus `config.toml` and `config_v2.toml`, are unchanged: sha256 was compared inside the tests (`tests/test_d2.py::test_generator_has_no_teacher_path_and_made_no_calls`) and listed in `source_audit.json`.
- **Pilot outcomes are not relabelled.** None of the 20 UNKNOWNs was relabelled or rerun.
- **Calls.**
  - **G4C-D2-P0 code: 0.** Instrumented entry points: `planner.plan`, `skill.plan_skill`, `evaluate.evaluate_target`, `verify.relocate`, `verify.plan_fixed_order`, `ordered.teach_sequence`.
  - **Historical regression tests**, in-process, disclosed separately: 621 `planner.plan` and 60 `skill.plan_skill`, unchanged; `test_d2.py` made none.

---

## 2. Archived base witnesses (provenance-checked replay, no search)

| Base | Archived unit | Scene lineage | Segments | Replay |
|---|---|---|---|---|
| `g4c_r00` | G4C-P1 `seq:g4c_r00:empty` (POSITIVE) | G4C root, seed 2026102001 | 97 | **BASE_WITNESS_REPLAYED** |
| `g4d_R0` | G4D `seq:R0:empty` (POSITIVE) | G2_D1 reference | 208 | **BASE_WITNESS_REPLAYED** |
| `g4d_R1` | G4D `seq:R1:empty` (POSITIVE) | G2_D1 blocked variant | 29 | **BASE_WITNESS_REPLAYED** |

**Checks per base:**
- every recorded segment re-certified CLEAR by `motion.certify_trajectory`, a conservative continuous check over links, housings, base, palm, rail, both fingers and the held disc;
- the record starts bit-exactly at the scene's q0 and gap;
- the final phase is retreat with the gripper open;
- the placement is within the goal tolerance;
- the target is attached only during carry.

Provenance in `source_audit.json`:
- sha256 of each witness file and plan file;
- a content hash of each witness;
- status `ARCHIVED_EVIDENCE`.

A tampered witness (1e-4 rad on one joint) is refused (test).

**Lineage correction made during this stage.** R0 and R1 differ only in one obstacle cell (o02 at 50 vs 51). They are **one** lineage family (G2_D1), so they share a family ID and a split. Independent lineages: **two** (G4C r00 and G2_D1).

---

## 3. Obstacle-insertion previews (`construction_attempts.jsonl`, 195 rows)

Every cell of each base was tried (64 × 3 = 192 rows), plus one staging-occupant row per base. Rejections: **15**, all "occupied by an existing object". No cell was rejected for initial-robot clearance: all three bases start at the tested home configuration, which G1 chose to clear every cell. The check is still enforced and tested.

**Accepted insertions by role.** Roles come from the first interrupted segment of the **recorded** sweep; this is a diagnostic, not a label.

| Base | arm-link sweep | grasp/access (palm, rail, fingers) | transport (held disc) | retreat | goal occupant | harmless (certified clear) |
|---|---|---|---|---|---|---|
| g4c_r00 | 32 | 16 | 0 | 0 | 1 | 10 |
| g4d_R0 | 7 | 10 | 0 | 0 | 1 | 41 |
| g4d_R1 | 6 | 8 | 5 | 1 | 1 | 38 |

**Full-robot nominal-sweep diagnostic: works.**
- Collisions are detected on links, housings, palm, rail, fingers and the carried target.
- A test confirms that blockers far (> 6 cm) from the carried-target path are still detected through robot-body pairs, so the check is not a target-centre-only check.
- A test also confirms certified-clear cells report `NO` with no unresolved segment.

**Limitation.** The certifier records the **first** violating pair per segment. The diagnostic lists first pairs per segment, not every body pair.

**Frozen blocker choice** (earliest interruption; other roles; non-adjacent):

| Base | A | B | C | N (nuisance) | G (goal) | S (staging) |
|---|---|---|---|---|---|---|
| g4c_r00 | 57 grasp/access (segment 0) | 42 arm-link (segment 1) | 21 grasp/access (segment 2) | 55 | 20 | 49 |
| g4d_R0 | 49 grasp/access (segment 0) | 59 arm-link (segment 133) | 44 arm-link (segment 172) | 7 | 45 | 57 |
| g4d_R1 | 42 grasp/access (segment 0) | 57 arm-link (segment 0) | 19 transport (segment 15) | 7 | 45 | 41 |

---

## 4. Nested variants and predeclared catalogue (`precheck_variants.json`, `precheck_queries.json`)

Each base has **9 variants**, all `PRECHECK_STATIC`: `base, +A, +B, +A+B, +A+B+C, +N, +A+N, +G, +A+S`.

- Earlier obstacles keep their IDs and cells, q0 and the goal are unchanged, and nothing is cloned (tests).
- The robot at q0 is clear in every variant.
- Every variant's `target_task_status` is **NOT_RUN**.

| Variant | Sequences (incl. omission remainders) | Deliberate static negatives | Eligible scene edits | Max active B/C slots |
|---|---|---|---|---|
| base | 1 (empty) | 0 | 0 (plus 2 eligible robot-start alternatives) | 1 |
| +A, +B, +G, +N | 3 | 0 | 1 | 3 |
| +A+N | 5 | 0 | 2 | 4 |
| +A+B | 7 | 0 | 3 | 8 |
| +A+B+C | 16 | 0 | 4 | 8 |
| +A+S | 8 (incl. the staging trio) | 1 (A→P, slot still occupied) | 2 | 7 |

**Catalogue rule** (frozen, geometric, no witness information):
- participants are the added obstacles;
- destinations follow the G4C rule;
- sequences: singles to two destinations, both orders of each pair, three orders of the triple, the staging trio, and single- and pair-omission remainders;
- scene edits: singletons, the first joint pair and the nuisance edit; geometrically ineligible edits are discarded;
- the B/C catalogue is the first ≤ 3 eligible edits, with layout `z0, zS, zR (m ≥ 1), zO[t] (m ≥ 2)`;
- **maximum active slots 8 everywhere, no inactive multiplicity** (checked against `g4c.layout`).

**Validated by tests:**
- strict sequence grammar (distinct IDs, no stays);
- same-endpoint reversals have distinct ordered signatures;
- omissions preserve the remaining order and the omitted objects stay at their initial poses;
- scene edits never change q, gap, attachment or target;
- an overlapping edit is rejected, not labelled.

**D2 family coverage** (`precheck_coverage.json`). F0 through F9 are all **statically constructible** from the archived bases, and every label outcome is `NOT_RUN`. The single requirement F4 needs is the PLACE-scope order contrast (the `+A+S` trio).

---

## 5. The central guard: nominal obstruction is not infeasibility

- **No label from the diagnostic.** `blocks_nominal_witness` ∈ {YES, NO, UNVERIFIED} is stored apart from `target_task_status = NOT_RUN`. No variant, attempt or query carries a POSITIVE or NEGATIVE label.
- **`d2.root_release_label` semantics** (tested):

  | Nominal blocked | Fresh target witness | Sound full-scope certificate | Label |
  |---|---|---|---|
  | yes | — | — | **NOT_RUN** |
  | yes | failed search | no | **UNKNOWN**, never NEGATIVE |
  | yes | yes | no | **REROUTABLE_POSITIVE**: the abstract alternative-path control (no new robot trajectory is claimed) |
  | — | no | yes | NEGATIVE, only with a sound certificate |
  | — | yes | yes | CONTRADICTION |

- **Closed pools.** `d2.pool_release`: a pool is DECIDED_COMPLETE only when every declared item is decided. One unknown makes the **whole** pool PARTIAL_OBSERVATION, and a silently dropped item makes it INVALID.
- **Substantive pools.** `d2.substantive_pool` needs at least two decided nonempty repairs including a POSITIVE. Empty-only or all-NEGATIVE pools do not qualify.

---

## 6. Leakage, splits, interfaces

- **Leakage.** Poisoning the privileged fields leaves `data.learner_tensors_v2` byte-identical: base witness, nominal sweep, family ID, construction role and seed. The learner sees the **actual obstructed scene**: adding obstacles changes `object_xy` (test).
- **Import guard.** Importing `d2` loads none of `verify`, `evaluate`, `ordered`, `teacher`, `g4d_run`, `g4c_pilot` or `certificates`. It loads `skill` and `planner` modules only transitively through `effects` (for parameter helpers); the instrumented call counts are 0.
- **Splits.** Keyed by lineage family; every descendant inherits it. The current families are G2_D1 → train and g4c_r00 → validation; with only two families this is a policy demonstration, not a split.
- **Interface map** (`source_audit.json`).
  - **Reused unchanged:** `motion.certify_trajectory`, `geometry.Checker`, `sequences.*`, `proposals.static_endpoints`, `effects.pose_substitution` / `robot_start_substitution`, `g4c._dests` / `layout`, `data.learner_tensors_v2`.
  - **New:** `d2.py` (static construction and release semantics) and `d2_precheck.py` (artifacts).
  - **D2-P1 only:** a fresh base witness via `evaluate.evaluate_target` under the guarded runner; labels via `g4d_run.run_collection` / `unit_evidence` plus `g4c_pilot.adjudicate`, unchanged; a D2 finalize and judge adapter mirroring `g4c_pilot` (not written).

---

## 7. The 20 G4C-P1 UNKNOWNs (read-only analysis, `precheck_coverage.json`)

| Class | Count | What decides them |
|---|---|---|
| Q0 "all pairs certified blocked" connector verdict (7 relocations and 1 target) | 8 | **Need a new sound certificate kind** (full-domain connector proof with an independent checker), which needs a separate proof-obligation review. Not done. |
| Uncertified search incompleteness (first or later relocations, target schedules) | 12 | **Cannot be avoided without hindsight.** Under D2's release policy such a pool becomes `PARTIAL_OBSERVATION` as a whole. |

**Witness-first construction helps in one specific way:** it guarantees a verified base, and it predeclares repairs, such as the staging trio and goal-occupant relocations, whose negatives are certifiable by existing kinds. It **does not** turn uncertified failures into labels.

---

## 8. Risks

- **Sample selection.** Released `DECIDED_COMPLETE` pools will over-represent easy geometry. Mandatory reporting of `released / attempted` and `decided / released` exposes this, but does not remove it.
- **Trivial-certificate dominance.** `+G` and the static negatives are cheap and certain (goal overlap, static invalid). The pilot was 21 of 26 goal-overlap negatives. D2-P1 must report certificate kinds and cap trivial negatives in any quota.
- **Sound negative coverage.** Apart from goal overlap and static checks, the only order-scope negative is ORDER_FIRST_ACTION (a first-action PICK or PLACE screen). Nominally blocked scenes will often be REROUTABLE_POSITIVE or UNKNOWN, not NEGATIVE.
- **Base diversity.** Only two independent lineages are archived, and all start at the home configuration. Fresh bases (D2-P1) are needed for variety.

---

## 9. D2-P1 proof-of-concept proposal (NOT authorized; [`budget_request.json`](../runs/g4c_d2_precheck/budget_request.json))

The **measured basis** is the G4C-P1 unit CPU: median 1.35 s, mean 5.74 s, maximum 105.6 s (n = 59). The high case assumes 12.1% of units run to the 870 s cancellation and all others cost the pilot maximum.

| Field | **POC_S (recommended)** | POC_F (only after POC_S) |
|---|---|---|
| Families × variants | g4d_R1 and g4c_r00 × {base, +A, +A+B, +A+S, +G, +N} | 3 bases (2 lineages) × 9 variants |
| Units (ordered / scene target-only / robot-start) | **68** (50 / 16 / 2) | 194 (147 / 45 / 2) |
| Fresh-base attempts (one target evaluation each) | 2 | 4 |
| CPU estimate low / central / high | 92 / 391 / 14,340 s | 262 / 1,114 / 40,911 s |
| `per_teacher_unit_cpu_s` / `cancellation_margin_s` | 900 / 30 | 900 / 30 |
| `aggregate_cpu_s` | **18,000** | 50,400 |
| `workers` | 1 | 1 |
| `unit_wall_guard_s` / `aggregate_wall_guard_s` | 1,800 / 23,400 | 1,800 / 61,200 |
| `max_motion_nodes` | 4,000 (unchanged profile) | 4,000 |
| `relocation_skill_attempt_cap` | 46 | 168 |
| `target_eval_attempt_cap` | 70 | 198 |
| `max_root_construction_attempts` | 2 | 4 |

**POC_S must report each of (a)–(f) as met or as an explicit failure** (`protocol_proposal.md` §6):
- (a) a verified base per family;
- (b) a sound target-blocked NEGATIVE (non-trivial if constructible);
- (c) a witnessed repair POSITIVE on that same root;
- (d) one decided order contrast (`+A+S`) or a failure report;
- (e) a complete substantive B/C pool, if constructible;
- (f) the full construction and discard audit.

The central estimate is small, but tail risk dominates the cap.

---

## 10. Files, tests, commands

Line counts are total / logical (non-blank, non-comment, docstrings included).

| File | Purpose | Lines |
|---|---|---|
| `d2.py` (new) | Base loading and replay, obstacle insertion, nominal diagnostic, roles, nested variants, staging occupant, catalogue, release semantics, lineage splits | 303 / 258 |
| `d2_precheck.py` (new) | Runner: audit, pilot-UNKNOWN analysis, coverage, budget tiers, overview, instrumentation | 204 / 187 |
| `tests/test_d2.py` (new) | 10 tests (replay and tamper, determinism, legality, full-body diagnostic, the semantic guard, nesting, queries/edits/omissions/B/C, release rules and splits, leakage, import guard and zero calls with frozen-input hashes) | 183 / 157 |
| `run.py` | `g4c-d2-precheck` dispatch | +6 |

**Artifacts** in `runs/g4c_d2_precheck/` (632 KB):
- `source_audit.json`
- `protocol_proposal.md`
- `construction_attempts.jsonl`
- `precheck_variants.json`
- `precheck_queries.json`
- `precheck_coverage.json`
- `precheck_result.json`
- `budget_request.json`
- `precheck_overview.png`
- `manifest.json`, with sha256 of every file

**[`precheck_overview.png`](../runs/g4c_d2_precheck/precheck_overview.png)** has one panel per base:
- the arm at q0 (dark) and 14 faint arm samples along the **archived recorded** witness;
- the recorded carried-target path (orange);
- the goal (dashed red circle);
- the chosen obstacle cells as coloured rings labelled by role (A/B/C/N/G);
- the robot pose at A's/B's/C's first interrupted segment, with the colliding body outlined in red;
- dashed blue ghost relocations for `+A+B+C`.

The banner reads "ARCHIVED VERIFIED NOMINAL TARGET TRAJECTORY / CONSTRUCTED OBSTACLE PREVIEW / NEW TARGET FEASIBILITY: NOT RUN". No new path is drawn.

| Command | Exit | Result |
|---|---|---|
| `python run.py g4c-d2-precheck --out runs/g4c_d2_precheck` | 0 | 3 bases replayed; 195 attempt rows; 27 variants; 0 calls; 234 CPU-s |
| `python -m pytest -q tests/test_d2.py` | 0 | 10 passed (13.4 s) |
| `python -m pytest -q` (full) | 0 | **193 passed** (176 s) |
| `python run.py replay …` ×6 (scratch reports) | all 0 | all passed |

**Corrections made during this stage:**
- **Variant IDs.** The variant builder first mapped new obstacle IDs by scene position; `Scene` sorts objects by ID, which mislabelled `t0` as a participant. It now maps by cell.
- **Lineages.** R0 and R1 were first given separate families; they share the G2_D1 lineage and now share one family and split.
- **Budget tiers.** The single 194-unit budget did not match the "tiny" POC the contract asks for; it now has a small tier.
- **Test fixes.** One test-guard ordering fix.

**Untracked files**, all yours and untouched: the instruction files (G4B, G4C, G4C-P1, G4C-D2-P0, G4D), the PDF copies, and the v1.7/v1.9 bundle with its zip.

---

## 11. Decision

**`G4C_D2_PRECHECK_PASS`** against the acceptance list:
1. The repository state is verified, and prior results and the 20-root parent plan are unchanged.
2. Three archived full-arm target witnesses are replay-validated without search.
3. Reproducible, eligible obstacle previews, nested variants and catalogues exist for all three bases.
4. The nominal-sweep diagnostic uses the full robot geometry, and q0 is clear in every variant.
5. The semantic guard holds: nominal collision is not infeasibility, and no POSITIVE or NEGATIVE label was fabricated.
6. The release, attempt-denominator, lineage-split and substantive-pool policies are written and tested.
7. The source, budget and provenance plan, tests, replays and this report exist.

**STOP.** D2-P1 (POC_S recommended) requires your explicit numerical authorization. Nothing was collected; the remaining G4C 15 roots, G4E, G5, G6, 3D and hardware are not started.

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains `d2.py`, `d2_precheck.py`, `tests/test_d2.py`, the `run.py` edit, `runs/g4c_d2_precheck/` and this report. It is pushed to `main` without force. The commit hash is given in chat and recorded in report 0016.
