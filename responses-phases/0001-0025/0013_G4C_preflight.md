# 0013 — G4C-P0: 2D A/B/C data-readiness plan and preflight (NO COLLECTION)

| Field | Value |
|---|---|
| Report number | 0013 (new; 0001–0012 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4C preflight / plan only.** No teacher labels, no planner/skill/target/certificate search, no neural network, no 300-root work, no 3D, no hardware, no G4E. |
| Execution contract | `instruction-phase-md/G4C_2D_ABC_Data_Readiness_PLAN_ONLY.md` (151 lines, read in full; sha256 `bc7ef71f…cc955`; your file, left untracked) |
| Documents read | Reports 0011 and 0012; addenda A1 and A2; Methodology v1.7 and Guide v1.9 from your untracked `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` (`.md` sha256 `c03ac617…` and `899cb95d…`, unchanged since G4B; read only, not moved or committed) |
| Previous turn sync | Report 0012 was committed as `84f277d1f26307d5daea9c7a61d94cb4d8768339`. At the start, `main`, HEAD and `origin/main` all equalled it, with no tracked modifications. The untracked items were your instruction files, the PDF copies and the v1.7/v1.9 bundle. |
| Starting revision | `84f277d1f26307d5daea9c7a61d94cb4d8768339` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0014. |
| Run directory | [`../runs/g4c_preflight/`](../runs/g4c_preflight/), produced by `python run.py g4c-plan --out runs/g4c_preflight` (exit 0, 1.0 CPU-s) |
| Plan | `plan.json`, hash **`sha256:c761c68497309f6b631f6740237e75f08c2376ade179b7f644731dc775f193a3`**, status **`FROZEN_PENDING_BUDGET_AUTHORIZATION`**. Regenerated identically. |
| **Decision** | **`G4C-PREFLIGHT_READY_PENDING_BUDGET`. `G4C DATA COLLECTION NOT RUN`. STOP.** |

---

## 1. Baseline audit (§1)

- **Revision and tests.** HEAD equals the reported G4B commit. **169 tests pass** (157 earlier plus 12 new), and all six archived replays pass (77/77/2/50/20/257) into scratch paths. Historical inputs are unchanged: the sha256 of 9 archived records was compared before and after the plan run (`historical_inputs_unchanged: true`).
- **G4D inventory**, from saved records only, not replanned:
  - R4 order contrast POSITIVE vs NEGATIVE by ORDER_FIRST_ACTION;
  - R2 fixed-robot scene effects, Δ = +1 twice;
  - R4 omission effects of +1, +1 and +1;
  - first V2 J values 1.041, 1.021, 1.394 and 1.723;
  - R2 chain UNKNOWN, R5 baseline UNKNOWN, R1 robot-start Δ = 0.

  G4A **NOT_READY_TO_SCALE** remains historical. In `audit.json` these are **development controls only**, never G4C independent roots and never test roots.
- **G4B scope.** The exact conditional sequence sampler and the bounded z-marginal (at most 8 active slots) exist. A full (r, z) MCMC is **not implemented**, and G4C does not require it. Synthetic G4B distributions are never used as supervision.
- **Interfaces reused, unmodified.** The plan emits its teacher units in **exactly the G4D runner's unit schema**. A test passes all 167 planned units through `g4d_run.unit_scene`, which checks root scene hash, query identity, intervention eligibility and seed keys, without planning.
  - `scene.place_scene`; the `geometry.Checker` initial-robot clearance check (as G4A roots used);
  - `sequences.parse_sequence` / `omit` / `endpoint_distance`, `proposals.static_endpoints` (static geometry);
  - `effects.pose_substitution` / `robot_start_substitution` (fixed-robot geometric eligibility, changed-field audit);
  - `data.make_query`.

  `verify.py` and `skill.py` were not touched.
- **Contradictions between documents and code** (recorded, nothing silently changed):
  - Guide v1.9 still says G4D is blocked; reports 0011 and 0012 are authoritative.
  - Guide v1.9's tentative "move cap 3" matches `config_v2.toml` (`move_cap = 3`). J4 triples rely on it.
  - The fixture name "J8, static valid but unresolved" cannot be **constructed** deliberately without outcomes. It stays an observed category with no quota.

---

## 2. What the plan freezes (§3–§4)

### Root construction

All 20 roots are built from seeded geometry, starting at seed 2026102001 and consumed sequentially per family. Acceptance uses static geometry only:
- distinct supported cells;
- target and goal at least 3 cells apart;
- the intent's cell predicate;
- geometry unique against **all archived G4A and G4D roots** and against each other;
- the robot clear at its initial configuration.

The ledger records **32 attempts** with **12 rejections**, all "intent predicate not met", with at most 200 attempts per family. No root needed `CONSTRUCTION_UNAVAILABLE`, though the route exists.

### Construction-intent mixture (as instructed)

J0–J9 are construction questions, not labels.

| Family | Roots | Construction (geometry) | Designed to exercise |
|---|---|---|---|
| J0 | 6 | Free goal; 3–5 obstacles at least 1.5 cells from the target–goal segment | zero-move witness; nuisance zero-effect edit |
| J1 | 2 | A on the goal; C on the transport corridor near its midpoint | singleton vs joint scene edits (nonadditivity), two-move repair, omissions |
| J2 | 2 | A on the goal; access blocker B adjacent to A | same-endpoint orders (B,A)/(A,B): first-action opportunity; omissions |
| J3 | 4 | A on the goal; staging cell P beside the goal occupied by C | A→Q (C stays) vs (C→, A→P); A→P alone is a deliberate static negative; (A→P, C→) is a first-action PLACE opportunity |
| J4 | 2 | A on the goal; blockers B and C adjacent | three-move orders (B,C,A), (C,B,A), (A,B,C), two-move subsets, single and pair omissions |
| J7 | 2 | A on the goal; near, alternative and far destinations | alternative repairs; endpoint-vs-joint-travel contrast, **only if measured** |
| J5/J6 | 1 | Free goal | nuisance edit; a *harmful candidate* edit putting an obstacle on the corridor (effect only if measured); robot-start variant q = (π/2, −π/2, −π/2), the first eligible of a frozen list |
| J9 | 1 | A on the goal; B adjacent; 2 destinations each, cap 2 | exhaustive 13-sequence domain (includes 2 deliberate static negatives); the full B/C mini pool |

**Per-root predeclaration**, all before any outcome:
- **Destinations.** A geometric, ID-invariant rule: free cells outside the 1.5-cell corridor, nearest first (ties by x, y). Destinations are assigned jointly across participants (except in J9's exhaustive domain), so planned pairs are static-valid. This fixed a planning defect I caught before freezing: two participants on `g4c_r08` had both received the same cell.
- **Sequences.** Validated by the strict parse contract and statically screened; single- and pair-omission remainders are added, keeping the remaining actions in order.
- **Scene edits.** Singleton, joint, nuisance and harmful-candidate edits, each with fixed-robot eligibility and a changed-field audit; all 58 are eligible.
- **The B/C catalogue.** The first three eligible edits in rule order, hashed.
- **Ceilings.** At most 14 sequences, 5 edits, 1 robot start and 8 omission remainders per root.

| Root | Fam. | Seed | Goal | Roles | Sequences (omission remainders) | Static negatives | Eligible edits | B/C scene catalogue | Max active z | Units |
|---|---|---|---|---|---|---|---|---|---|---|
| g4c_r00–r05 | J0 | 2026102001–05, 011 | 20, 19, 47, 16, 41, 24 | — | 1 (0) | 0 | 1/1 | nuisance | 2 | 2 each |
| g4c_r06, r07 | J1 | 012, 013 | 7, 58 | A=o00, C=o01 | 6 (1) | 0 | 4/4 | A, C, A+C | 8 | 10 each |
| g4c_r08, r09 | J2 | 014, 015 | 31, 57 | A=o00, B=o01 | 6 (1) | 0 | 4/4 | A, B, A+B | 8 | 10 each |
| g4c_r10–r13 | J3 | 017, 018, 020, 023 | 4, 28, 19, 58 | A=o00, C=o01 | 7 (1) | 1 | 4/4 | A, C, A+C | 8 | 11 each |
| g4c_r14, r15 | J4 | 024, 026 | 22, 23 | A, B, C = o00, o01, o02 | 14 (6) | 0 | 5/5 | A, B, C | 8 | 19 each |
| g4c_r16, r17 | J7 | 027, 029 | 41, 0 | A=o00 | 4 (0) | 0 | 2/2 | A, nuisance | 4 | 6 each |
| g4c_r18 | J5J6 | 031 | 63 | — | 1 (0) | 0 | 2/2 | nuisance, harmful | 3 | 4 |
| g4c_r19 | J9 | 032 | 11 | A=o00, B=o01 | 13 (0) | 2 | 4/4 | A, B, A+B | 8 | 17 |

**Totals:** **167 units**, made up of 108 ordered-teacher, 58 scene target-only and 1 robot-start unit. Upper bounds: **136 relocation-skill calls** and **167 target evaluations**. Seed keys are frozen per unit (`g4c/<root>/<signature>/reloc|target`). Root independence and split metadata: one lineage family per root (`family_id = root_id`, split `DEVELOPMENT`); descendants never cross roots.

### B/C outcome layout (§3.5)

Per repair, the slots are `z0`, `zS[q]` for the root's catalogue (at most 3), `zR` (active iff m ≥ 1) and `zO[t]` for t < 3 (active iff m ≥ 2). Inactive slots hold the value 0 and never enter the energy or the count. The **maximum is 8 active**, within the G4B bound, and the validator checks every pool sequence against it.

A root's pool supports the **exact B/C joint loss only if every active slot of every pool sequence is decided**. The required units are listed per root in `bc_mini_pool`. A partly masked pool trains single-outcome terms only.

**A/B/C equal information.** All three architectures consume the same units and labels. B/C only add typed views (z slots) of the same decided outcomes; nothing extra is collected for B/C.

---

## 3. Label and evidence policy (§3; `schema.json`)

| Label | Requires |
|---|---|
| POSITIVE | A complete relocation, target and safe-retreat witness, or a decided target-only outcome for a scene or robot-start unit |
| NEGATIVE | A re-checked certificate whose scope covers the query (ORDER or ASSIGNMENT) |
| UNKNOWN | Everything else, including timeouts, censoring and failed connectors (addendum A2 reasons) |

- **Omissions** are separate teacher queries, never inferred from a positive.
- **Cost labels** come from the first complete relocation witness, even if the target is UNKNOWN or NEGATIVE, and are never reselected by target success. The empty repair has J = 0 exactly.
- **Leakage.** Root IDs, labels, outcomes, witnesses, certificates, trajectories and seeds belong to the privileged namespace. The learner allowlist is `data.learner_tensors_v2`.
- **Legacy evidence** (G4A derived, G4D development) is kept separate and is not counted toward G4C thresholds.

---

## 4. Thresholds: planned capacity vs. measured (§5; `coverage_plan.csv` / `.png`)

Every measured value is **NOT_RUN**. Planned capacity is "sufficient if all decide", which is not a prediction.

| Threshold | Required | Roots planned to support it |
|---|---|---|
| Zero-move witness roots | 6 | 7 |
| Nonempty complete witness roots | 8 | 13 |
| Multiple sufficient alternatives | 4 | 7 |
| Decided same-endpoint order contrasts | 4 | 9 |
| Decided nonzero scene effects | 4 | 13 |
| Decided omission effects | 4 | 11 |
| Decided zero-effect / nuisance controls | 4 | 7 |
| Cost-labelled roots | 8 | 13 |
| … of which multi-move cost | 4 | 11 |
| Fully decided B/C mini pools | 4 | **5** |
| Nonadditive examples (if constructible) | 2 | 5 |

**Risks, stated plainly.**
- **The B/C full-pool threshold is the most fragile.** It needs every active slot decided on at least 4 of 5 roots. G4A left 46% of static-valid assignments UNKNOWN, and G4D left 3 of 20 units UNKNOWN. A single unknown remainder or edit voids a root's pool.
- **Order contrasts depend on structure, not on success.** They need a certificate (first-action PICK in J2/J4/J9, first-action PLACE in J3) **and** a complete witness for the other order.
- **Zero-move roots** may simply not be initially feasible.
- **J7's cost inversion and J5's harmful effect** count only if measured.

The ≤50% unknown and ≥50% decided-pair targets from Guide v1.8 are carried as diagnostics, not pass gates, unless the collection judge freezes them in advance.

---

## 5. Requested compute (§6). Not authorized; the plan's `budget` fields are all `null`

**Measured basis:**
- G4D collection units: median 4.44, mean 6.66, maximum 60.16 CPU-s (n = 20);
- G4A median whole query: 297 CPU-s;
- G4A share of first-pass rows whose raw reason is target `PLANNER_BUDGET`: **12.1%** (an upper-side proxy, per addendum A2);
- the follow-up's censored target evaluations: 870 CPU-s.

The high scenario assumes 12.1% of target evaluations each run to the 870 s cancellation and every other unit costs the G4D maximum. The request is the high scenario × 1.1, rounded up to 30 minutes of CPU, with wall time = aggregate × 1.25.

| Field | Pilot (5 roots: r00 J0, r08 J2, r10 J3, r14 J4, r19 J9; 59 units) | Full 20 roots (167 units, pilot included) |
|---|---|---|
| CPU estimate low / central / high | 262 / 393 / 9,323 s | 741 / 1,113 / 26,389 s |
| `per_teacher_unit_cpu_s` | 900 (cancel at 870) | 900 (cancel at 870) |
| `cancellation_margin_s` | 30 | 30 |
| `aggregate_cpu_s` | **10,800** (3.0 CPU-h) | **30,600** (8.5 CPU-h) |
| `workers` | 1 (the tested guard and runner are single-worker) | 1 |
| `unit_wall_guard_s` | 1,800 | 1,800 |
| `aggregate_wall_guard_s` | 14,400 | 37,800 |
| `max_motion_nodes` | 4,000 (the **unchanged** planner profile, not extra effort) | 4,000 |
| `relocation_skill_attempt_cap` | 60 | 136 |
| `target_eval_attempt_cap` | 59 | 167 |
| `max_root_construction_attempts` | 0 (roots are already frozen) | 0 |

**Proposed sequence:** pilot first, then the remaining 15 roots, only if you authorize the full scope and the pilot's measured cost justifies it. Pilot roots are inside the 20-root development set; their outcomes never retune or replace any root. Censored and failed units are kept; there is no automatic retry and no expanded budget in the same frozen run.

The G4D 18,000 CPU-s envelope is **not** inherited.

**Uncertainty is large.** The low estimate (about 0.2 CPU-h) assumes G4D-like sparse behaviour. These roots carry 4–8 obstacles, and their access dependencies resemble G4A's, which saw target searches run to their limits.

**Before G4C-COLLECT can run**, two small pieces remain (not written here):
1. a G4C finalize step linking `plan.json` to an authorized budget and a source manifest; `g4d_run.make_final_plan` is G4D-specific;
2. a G4C judge that turns rebuilt unit evidence into the coverage tags `g4c.coverage` consumes, including the B/C full-pool rule.

The runner, guard, checkpoints and per-unit revalidation (`g4d_run`) are reused as-is; the units already pass its identity checks.

---

## 6. Code, tests, artifacts

Line counts are total / logical (non-blank, non-comment, docstrings included).

| File | Purpose | Lines |
|---|---|---|
| `g4c.py` (new) | Construction, predeclaration, B/C layouts, plan, budget request, fail-closed validator, admission and no-planner coverage | 435 / 387 |
| `g4c_figures.py` (new) | Runner: audit, schema, coverage CSV/PNG, overview, manifest, call instrumentation | 167 / 155 |
| `tests/test_g4c.py` (new) | 12 tests | 128 / 109 |
| `run.py` | `g4c-plan` subcommand | +7 |

**Size review.** `g4c.py` exceeds the ~300 review trigger. It holds one contract: the frozen construction and predeclaration rules, together with the validator that re-derives them. Splitting it would separate those rules from their check. I kept it whole and am documenting the trigger here; if you prefer, the validator and coverage half (about 90 lines) could move to its own module.

**Tests:**
- deterministic plan hash and zero planner, target or teacher calls (counters wrapped around every loaded entry point);
- historical inputs unchanged;
- intent counts, ceilings and the 13-sequence J9 domain;
- mask invariants;
- omission order preserved and scene-edit changed-field audits;
- J3's deliberate negative;
- **mutation rejections:** malformed mask, leaked oracle field, duplicated root seed, mixed lineage, changed catalogue, unauthorized budget values, and tampering without re-hashing;
- fail-closed admission: null fields, and requested numbers without an authorization record, are both refused;
- coverage is NOT_RUN without evidence and NOT_MET with partial synthetic evidence;
- every unit passes the G4D runner's identity checks.

**Two corrections made during this stage:**
- The validator crashed on a leaked field inside a scene record; it now reports a malformed scene and rejects the plan.
- Two of my mutation tests initially mutated nothing; they were fixed so that each mutation is real.

**Artifacts** in `runs/g4c_preflight/` (472 KB):
- `plan.json`, `audit.json`, `schema.json`, `coverage_plan.csv`, `preflight_result.json`, `manifest.json`;
- `manifest.json` holds sha256 for 14 source and config files, the 3 documents and 9 historical inputs.

**Figures:**
- [`overview.png`](../runs/g4c_preflight/overview.png). Panel 1 is the archived G4D R4 root, drawn from saved records and tagged **CONTEXT ONLY - NO PLANNER/NEW EVIDENCE**. Panels 2–6 show planned roots r06 (J1), r08 (J2), r10 (J3), r14 (J4) and r19 (J9), each tagged **SCHEMATIC / NOT_RUN**:
  - the full arm at its initial q;
  - the goal as a dashed red circle;
  - role labels (A/B/C);
  - the longest declared sequence as numbered dashed arrows to ghost poses;
  - a box with sequence and edit counts, the catalogue and the maximum active z.

  No arm path is drawn.
- [`coverage_plan.png`](../runs/g4c_preflight/coverage_plan.png): for each threshold, the required count beside the planned supporting roots, each labelled "measured: NOT_RUN".

### Commands and exits

| Command | Exit | Time |
|---|---|---|
| `python run.py g4c-plan --out runs/g4c_preflight` | 0 | 1.5 s wall, 1.0 CPU-s |
| `python -m pytest -q tests/test_g4c.py` | 0 (12 passed) | 0.9 s |
| `python -m pytest -q` (scratch call-counting plugin, not committed) | 0 (169 passed) | 162 s |
| `python run.py replay --run runs/<run> --report <scratch>` ×6 | all 0, all passed | — |

**Calls.**
- **New G4C code: 0** planner, skill, target or teacher calls.
- **Historical regression tests, in-process:** 621 `planner.plan` and 60 `skill.plan_skill`, the same as at G4B. These come from the established tests only; `test_g4c.py` and `test_sampler.py` made none. Worker subprocesses in the runner and teacher tests are not counted.

**Untracked files**, all yours, untouched and uncommitted:
- the instruction files (G4B, G4C, G4D) and the two PDF copies;
- `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` and its `.zip`.

---

## 7. Decision

**`G4C-PREFLIGHT_READY_PENDING_BUDGET`. `G4C DATA COLLECTION NOT RUN`.**

The plan is frozen, validated, deterministic and source-hashed. No label exists for any G4C root.

**Next dependency:** your explicit authorization of numeric limits (pilot and/or full; the table above is a request). After that, G4C-COLLECT needs the small finalize and judge pieces in §5 before any unit runs.

**STOP.** No G4E, G5, G6 or 3D.

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains `g4c.py`, `g4c_figures.py`, `tests/test_g4c.py`, the `run.py` edit, `runs/g4c_preflight/` and this report. It is pushed to `main` without force, following the established per-stage convention. The commit hash is given in chat and recorded in report 0014.
