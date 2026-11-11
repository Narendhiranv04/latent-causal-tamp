# 0019 — G4C-LF-P4: operational-negative teacher policy, regression closure and bounded calibration pilot

| Field | Value |
|---|---|
| Report number | 0019 (new; 0001–0018 unchanged) |
| Date | 21 October 2026 |
| Stage | **G4C-LF-P4 only.** New versioned teacher policy `2D-ABC-OPNEG-v1`, its wrapper and tests, closure of the P3a regression gate, and a 12-query development calibration pilot. **No** production collection, A/B/C training, P3b, POC_F, 3D or hardware. |
| Execution contract | `instruction-phase-md/G4C_LF_P4_Operational_Negatives_and_Learning_First_Execution.md` (161 lines, read in full; your file, left untracked) |
| Previous turn sync | Report 0018 was committed as `29b459bbebaeafee2a6dd93456042dce2dcd5361`. At the start, HEAD = `origin/main` = `29b459b`, with no post-0018 work. |
| Run directory | [`../runs/g4c_lf_p4/`](../runs/g4c_lf_p4/): `regression/` (20 manifest files) and `pilot/` (104 manifest files) |
| **Verdicts** | **`P4_PROTOCOL_IMPLEMENTED_PASS`** · **`P3A_REGRESSION_CLOSED`** · **`P4_CALIBRATION_COLLECTED`** · **`P4_READY_FOR_G4B_G4E`**: ready for G4B re-verification and G4E smoke learning; **NOT** ready for full A/B/C training (one complete joint pool). **STOP.** |

---

## 1. Science-policy addendum (versioned; v1.7 and v1.9 themselves are unchanged)

**`2D-ABC-OPNEG-v1`** (`teacher_opneg.toml`, policy hash `sha256:df54878d…`) changes exactly **one** assumption of Methodology v1.7, and only for **new** records. A binary negative training label no longer has to be a proof.

| Status | Source | Definition | Binary label |
|---|---|---|---|
| `VERIFIED_FEASIBLE` | WITNESS | Some seed produced an independently re-checked complete relocation + target + SAFE_RETREAT witness (existential) | 1 |
| `CERTIFIED_INFEASIBLE` | CERTIFICATE | An independent checker accepted a sound certificate at the exact scope (ASSIGNMENT / ORDER / ORIGINAL_TARGET / SCENE_TARGET_ONLY) | 0 |
| **`BUDGET_INFEASIBLE`** | PLANNER_BUDGET | **All 3 declared seeds** of this exact protocol ran to a **clean, allowed algorithmic terminal** without a complete witness. Scope `OPERATIONAL_ONLY:<policy hash>`. | 0 (weight 1.0; down-weight ablation hook) |
| `UNKNOWN` | UNRESOLVED | Unrun seed, guard censoring, crash, wall-clock-involved search, unconfirmed or replay-rejected witness, invalid query, missing records | null (never supervised) |

**The protocol.**
- Seeds are the literal values **20261021, 20261022, 20261023**, used as key namespaces. The RRT seed of each connector is `planner.call_seed(41, key/label)`, so the attempts are deterministic and distinct.
- The planner keeps its 4,000 nodes per connector, and the skill stops after **4 unresolved connectors**. Both are checked equal to `config.toml`, never overridden.
- Per-seed process-tree guard: **250 CPU-s / 600 s wall**. Per query: cancellation at 870 CPU-s, hard ceiling 900 CPU-s, 1,800 s wall.
- Short-circuit happens only on a revalidated witness or an accepted certificate.

**Allowed clean terminals** (algorithm completion, never guard intervention):
- `SEARCH_LIMIT_PLAN_FAILURES` (the skill's 4-unresolved-connector stop; this does **not** mean 48 connectors were tried);
- `SCHEDULE_COMPLETED_NO_WITNESS_{UNCERTIFIED_REJECTIONS, WITH_UNRESOLVED_CONNECTORS}`;
- `SCHEDULE_COMPLETED_ALL_PAIRS_CERTIFIED_BLOCKED`;
- `PICK/PLACE_SCREEN_EXHAUSTED_*`.

**Precedence rules.**
- A witness beats budget failures.
- A witness against a sound certificate is **FATAL** (both records preserved).
- A partial schedule is UNKNOWN.

**Interpretation.**
- **`Y_B = 0` does not imply `Y* = 0`.** A budget negative is never fed to a certificate checker; both `certificates.check` and `g4c_pilot.adjudicate` refuse it (tested).
- Any effect, omission or κ with a budget-negative side is reported as **operational** (budget-protocol-relative), never as proven necessity.

**Unchanged.** The A/B/C architectures, losses and Boltzmann inference; the full 3R arm; the 48 grasps; the 8×8 resting cells; continuous motion; GOAL_AND_SAFE_RETREAT; the one-shot deployment boundary (multi-seed retries exist **only** in the offline teacher); fixed-robot edits; omission semantics; root-level splits; no leakage.

## 2. Code (new or changed; nothing historical modified)

| File | Role | Lines (total / logical) |
|---|---|---|
| `teacher_opneg.toml` (new) | Policy overlay with an allowlisted schema (unknown, missing or ill-typed keys are rejected) | 40 |
| `operational_teacher.py` (new) | Pure logic: policy load/hash/config check, per-seed terminal classification, query adjudication, projections, same-policy effects and κ, exact B/C pool completeness, loss masks | 216 / 187 |
| `teacher_pilot.py` (new) | Guarded regression gate; frozen pilot plan; static admission (existing certificates plus the P3a sector checker); seed-major rounds through the **unchanged** `g4d_run.run_collection`; revalidation through `g4d_run.unit_evidence`; outputs | 211 / 194 |
| `teacher_pilot_figures.py` (new) | Three figures from recorded data | 79 / 73 |
| `tests/test_operational_teacher.py` (new) | 15 pure/static tests | 231 / 191 |
| `run.py` | Two commands: `g4c-lf-p4-regression`, `g4c-lf-p4-pilot` | +13 |
| `runs/g4c_lf_p4/regression/countcalls.py` (new, run artifact) | Pytest plugin flushing per-test outcomes and in-process planner counts after **every** test, so a kill loses nothing | — |

**Two defects found and fixed before collection:**
- **Unconfirmed witness counted as a positive.** `seed_terminal` would have passed a target termination literally named `WITNESS`, whose safe-retreat recheck had failed, through as a positive terminal. It is now `UNCONFIRMED_WITNESS`: never clean, never positive (tested).
- **Leakage test false alarm.** The test matched the scene's own `domain_policy` field; it was refined to teacher-specific identifiers. There was no leak.

**One post-gate addition, disclosed.** After the regression gate and the pilot, I added `operational_teacher.loss_masks` and 1 test (15/15 pass, 7.5 CPU-s). It was needed because the worker gives every target-only query an empty-repair cost of 0.0, and a scene edit must carry **no** cost label. `pilot/loss_masks.json` is derived from the saved `decisions.json` with **no teacher call**, and the pilot manifest was rewritten to include it. The full regression suite was **not** re-run after this pure addition, because the regression budget (650 CPU-s) would not allow a second full run.

## 3. P4.2 regression gate (current code; one process-tree guard)

`python run.py g4c-lf-p4-regression --out runs/g4c_lf_p4/regression`: exit 0, verdict **`P3A_REGRESSION_CLOSED`**.

| Item | Result |
|---|---|
| Guard | `teacher.guard` over `bash regression.sh` (whole tree incl. pytest subprocesses and replays): **340.0 CPU-s of 650** (trigger 635), **347.6 s wall of 1,500**, overshoot 0.0, stop COMPLETED |
| Six archived replays (reports written to `regression/`, never into frozen runs) | **all exit 0 and `replay_passed`**: g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit |
| Full suite | **261 / 261 passed**, 0 failed, 0 skipped: 216 historical + 31 P3a + 14 P4 (`pytest exit 0`, 304 s) |
| In-process regression planner calls | `planner.plan` **621**, `skill.plan_skill` **60**: exactly the historical baseline (per-file counts in `calls.json`) |
| Pure unit tests outside the gate | ≈ 29 CPU-s for P4 + P3a during development, and 7.5 CPU-s for the post-gate re-run (≤ 120) |

This closes the 0018 gap (157 of 247 tests run). It is a new authorized run, not retroactive approval of the 0018 overshoot.

## 4. P4.3 calibration pilot

`python run.py g4c-lf-p4-pilot --out runs/g4c_lf_p4/pilot`: exit 0. Plan hash `sha256:3191e195…`, written before any teacher call.

**Scope.**
- 2 development lineages (never held out): **`d2_g4c_r00_AB`** (POC_S `+A+B` nominal-blocker variant of `g4c_r00`) and pilot root **`g4c_r19`**.
- **12 queries × 3 declared seeds = 36 declared attempts.**
- The roots were chosen *because* their historical evidence makes the calibration interpretable. **They are not an unbiased sample.**

### 4.1 Every decision (`decisions.json`, `attempts.jsonl`, `static_admission.json`)

| Query | Family | Historical label | **P4 status** | Source / evidence | Seeds run | CPU-s (seed attempts) |
|---|---|---|---|---|---|---|
| `seq:d2_g4c_r00_AB:empty` | original task | UNKNOWN | **BUDGET_INFEASIBLE** | 3/3 clean: `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS` ×3 | 3/3 | 2.27, 2.34, 2.27 |
| `scene:…AB:o04>49` | fixed-robot singleton | POS | **VERIFIED** | witness, seed 20261021 | 1/3 | 4.87 |
| `scene:…AB:o05>41` | fixed-robot singleton | UNKNOWN | **BUDGET_INFEASIBLE** | same terminal ×3 | 3/3 | 2.30, 2.32, 2.33 |
| `scene:…AB:o04>49.o05>41` | fixed-robot joint | POS | **VERIFIED** | witness | 1/3 | 4.31 |
| `seq:…AB:o04>49.o05>41` | ordered repair (2 moves) | POS | **VERIFIED** | witness; J = 2.785 | 1/3 | 10.76 |
| `seq:…AB:o04>49` | ordered repair / omission | POS | **VERIFIED** | witness; J = 1.238 | 1/3 | 6.93 |
| `seq:…AB:o05>41` | ordered repair / omission | UNKNOWN | **BUDGET_INFEASIBLE** | relocation witness every seed (J 1.671 / 1.617 / 1.639), target `…UNCERTIFIED_REJECTIONS` ×3 | 3/3 | 4.66, 5.03, 4.86 |
| `seq:g4c_r19:o01>28.o00>27` | ordered repair (order A) | POS | **VERIFIED** | witness; J = 1.653 | 1/3 | 4.99 |
| `seq:g4c_r19:o00>27.o01>28` | ordered repair (order B) | UNKNOWN (P3a: certified) | **CERTIFIED** | `LINK0_SECTOR_PICK`, ORDER, static | 0/3 | 0 |
| `seq:g4c_r19:o00>27` | ordered repair / omission | UNKNOWN (P3a: certified) | **CERTIFIED** | `LINK0_SECTOR_PICK`, ORDER, static | 0/3 | 0 |
| `seq:g4c_r19:empty` | original task | NEG (GOAL_OVERLAP) | **CERTIFIED** | `GOAL_OVERLAP`, ASSIGNMENT, static | 0/3 | 0 |
| `scene:g4c_r19:o02>26` | nuisance scene edit | NEG | **CERTIFIED** | `GOAL_OVERLAP`, static | 0/3 | 0 |

The P3a sector certificate was used **only after** the regression gate closed, as the contract required.

### 4.2 Three projections

| Projection | Content |
|---|---|
| (i) Raw ledger (12 queries, 14 attempts executed, 22 short-circuited by witness or certificate) | **5 VERIFIED / 4 CERTIFIED / 3 BUDGET / 0 UNKNOWN / 0 NOT_RUN**. All 14 attempts stopped COMPLETED (no censoring, no crash). |
| (ii) Binary-admitted (`projections.json`, `loss_masks.json`) | **12 / 12** admitted: y = 1 ×5, y = 0 ×7 (4 proof-based, **3 operational**). Excluded: none. |
| (iii) Exact B/C z-complete pools (`pools.json`) | **`d2_g4c_r00_AB : o04>49.o05>41` COMPLETE, 8/8 active slots decided**: z0 = 0 (budget), zS[o04] = 1, zS[o05] = 0 (budget), zS[joint] = 1, zR = 1, zO[0] = 0 (budget), zO[1] = 1, zO[2] = 1. **zO[2] duplicates zR** (finding in §4.6), so there are **7 distinct decided outcomes**. The pool is **operational** (it contains budget negatives). **`g4c_r19 : o01>28.o00>27` INCOMPLETE, 4/8.** Missing zS[singleton:A], zS[singleton:B], zS[joint:A+B] and zO[1] (`o01>28`), which were deliberately left out of the 12-query cap. |

**By family:**
- Original task: 1 budget negative, 1 certified negative.
- Ordered repair: 4 verified, 2 certified, 1 budget negative.
- Fixed-robot edits: 2 verified, 1 budget negative, 1 certified.

**Loss masks** (`loss_masks.json`):
- y, decided mask, weight and source per query.
- Cost labels exist only for ordered repairs with a recorded first relocation witness, and are 0 for the empty repair. The budget-negative repair `o05>41` keeps its genuine relocation cost (methodology v1.7: relocation J exists independently of the target).
- Scene edits: `cost_mask = false`.

### 4.3 Effects and contrasts (one policy, all sides decided; `effects.json`)

| Contrast | Value | Grounding |
|---|---|---|
| Scene Δ, AB: edit `o04>49` / `o05>41` / joint (vs empty) | **+1 / 0 / +1** | operational (empty and `o05>41` are budget negatives) |
| **κ_S (AB)** | 1 − 1 − 0 = **0** (four sides decided) | operational |
| Omission Δ^O for `o04>49.o05>41`: drop `o04>49` / drop `o05>41` / drop both | **+1** (operational) / **0** (proof-grounded: witness vs witness) / **+1** (operational) | mixed |
| **κ_O (AB)** | **0** | operational |
| Nuisance Δ, r19 `o02>26` vs empty | **0** | **proof-grounded** (two GOAL_OVERLAP certificates) |
| Omission Δ^O, r19: drop `o01>28` from the witnessed repair | **+1** | **proof-grounded** (witness vs LINK0_SECTOR_PICK) |
| **Same-endpoint swap, r19** | `o01>28.o00>27` = 1 (WITNESS) vs `o00>27.o01>28` = 0 (CERTIFICATE) | **proof-grounded access contrast** |

### 4.4 Cost, calls and label stability (`compute.json`, `stability.json`)

**Cost.**

| Measure | Value |
|---|---|
| Aggregate CPU | **77.6 CPU-s** for the whole process tree (`time`, incl. interpreter, figures and manifest), of a **3,600** cap. Internal ledger: units 60.2 + coordinator 9.4 = 69.6. |
| Static admission | **8.2 CPU-s** of 120 (14,293 IK, 41 pick screens, 20,771 distance evaluations) |
| Wall | **72.9 s** of 7,200 |
| Per seed attempt | 2.3–10.8 CPU-s (max 10.76), all ≪ 250 |
| Per query | ≤ 14.6 CPU-s (≪ 870) |

**Calls.**
- **Inner teacher calls:** 8 relocation-skill calls and 14 target evaluations, recorded per attempt. None were in flight at a kill (no censoring).
- **Coordinator:** 0 planner, skill, target or relocation calls (P3a guards active).
- **Limitation:** connector-level `planner.plan` counts inside workers are not instrumented. Only skill-level counts exist.

**Yield.**
- Cost per admitted label: 77.6 / 12 ≈ **6.5 CPU-s**.
- Cost per complete joint pool: **77.6 CPU-s** for the one pool, i.e. the whole pilot, of which the AB root's 7 queries used ≈ 55 CPU-s.

**Label stability.**
- **No** success after an earlier failed seed.
- **0** disagreements with historical witnesses or sound certificates.
- **0** FATAL.
- **Every budget negative was seed-invariant.** All 3 seeds ended in the same deterministic terminal (`…UNCERTIFIED_REJECTIONS`), and no RRT search was involved. For these queries the extra seeds carried **no** new information: the operational negative reflects the deterministic screen and link-0 schedule, including at least one gray-band (uncertified) rejection.
- No query reached the 4-connector stop, so this pilot gives **no** measurement of seed sensitivity for RRT-limited queries. The `g4d_R1` type (440–870 CPU-s per attempt in POC_S) would be censored at 250 CPU-s and become UNKNOWN under this policy.

### 4.6 Finding: the frozen D2/G4C B/C layout double-counts one slot

**The defect.** `g4c.layout` (frozen, unchanged) activates `zO[t]` for **all t < 3 whenever m ≥ 2**. For a 2-move repair, `zO[2]` removes nothing and maps back to the repair itself, the same outcome as `zR`. `g4c_pilot.bc_pool` and this stage's `pool()` mirror that mapping.

**Consequences.**
- No label changes, and the AB pool is complete either way.
- In the B/C joint energy, however, this is an **inactive-slot multiplicity** that methodology v1.7 forbids: the same outcome would be counted twice in the exact z-marginal.
- **Required for G4E (P5.3):** a versioned layout with `zO[t]` for t < m only, plus a regression test, leaving the frozen G4C plan untouched.

### 4.5 Figures

- `pilot/labels_by_source.png`: status and source per query. The legend swatches render uniformly blue (cosmetic); the bars and texts are correct.
- `pilot/compute.png`: CPU per seed attempt, plus cumulative CPU against the cap.
- `pilot/scenes_and_witnesses.png`: both S0 scenes with the full 3R arm at q0, and the two **recorded** 2-move witnesses (AB repair, r19 order A). No imagined paths.

## 5. Integrity

**Frozen evidence.** All six frozen run directories are byte-identical against their own manifests, 934 files, 0 mismatches:

| Run | Files |
|---|---|
| `runs/g4c_d2_poc_s` | 452 |
| `runs/g4c_pilot` | 324 |
| `runs/g4d_evidence` | 129 |
| `runs/g4c_d2_precheck` | 9 |
| `runs/g4c_preflight` | 7 |
| `runs/g4c_d2_p3a_static` | 13 |

**Unchanged.** `config.toml`, `config_v2.toml` and all historical source files are unchanged; the policy is a separate overlay. No old label was rewritten. New labels live only in `runs/g4c_lf_p4/pilot`, each under the policy hash.

**Safeguards.**
- **Mixed-policy guard:** `projections()` refuses records of another policy hash (tested).
- **Unknown handling:** UNKNOWN rows never enter the binary dataset.
- **Pool completeness:** pools require every active slot decided.

**Working tree.** The two pre-existing root PDF deletions are untouched and unstaged. Instruction files are untracked.

## 6. Verdicts

| Gate | Verdict |
|---|---|
| `P4_PROTOCOL_IMPLEMENTED_PASS` | PASS: policy, wrapper, adjudicator, projections, masks; 15 + 31 unit tests; FATAL/UNKNOWN precedence tested |
| `P3A_REGRESSION_CLOSED` | **CLOSED**: 261/261, 6/6 replays, 340/650 CPU-s, 0 overshoot |
| `P4_CALIBRATION_COLLECTED` | **COLLECTED**: 12/12 queries decided, 0 UNKNOWN, within every cap |
| `P4_READY_FOR_G4B_G4E` | **READY** for G4B re-verification and G4E-ABC smoke tests on tiny complete pools. **NOT** ready for G5/G6 training: 1 complete joint pool, 2 development lineages. |

## 7. Next authorization: P5 (proposal only, costed from P4 measurements)

1. **P5.1 — G4B re-verification on current code** (`python run.py g4b`). This re-checks the sampler: A Gibbs, swap and birth/death Hastings with unequal K_i; B/C exact bounded-z marginal; detailed balance; finite-difference gradients.
   - G4B already passed in report 0012; this is a regression of the sampler only.
   - **≤ 120 CPU-s, zero planner calls.**
2. **P5.2 — G4C-D3 development collection under unchanged `2D-ABC-OPNEG-v1`.**
   - **Roots:** 40 **fresh** independent J0 roots, split **before** descendants (e.g. 28/6/6). Target at ρ ≥ 0.45 m to avoid `g4d_R1`-type RRT tails.
   - **Catalogue per root (frozen before outcomes, ≤ 12 queries):** the empty repair, 2 single repairs, 1 same-endpoint two-move pair in both orders, 2 singleton scene edits, 1 joint edit, the omissions of the two-move repair, and 1 nuisance edit.
   - **Measured basis:** about 6.5 CPU-s per decided query on `g4c_r00`/`r19`-type roots.
   - **Proposed caps:**

     | Limit | Value |
     |---|---|
     | Queries | ≤ 480 |
     | Seed attempts | ≤ 1,440 |
     | Per seed | 250 CPU-s |
     | Aggregate CPU | **≤ 12,000 CPU-s** (expected ≈ 3,000, plus tail allowance) |
     | Wall | ≤ 6 h |
     | Workers | 1 |
     | Static admission | ≤ 600 CPU-s |

   - **Kill gates:** FATAL contradiction ⇒ stop. More than 20 % UNKNOWN in the first 5 roots ⇒ stop and report. Process-tree breach ⇒ stop.
   - **Report** the attempted, admitted and z-complete denominators per root, and the operational versus proof-grounded split.
3. **P5.3 — G4E-ABC smoke learning** on the complete pools (P4's AB pool plus P5.2's), with the **corrected versioned z-layout** (zO[t] for t < m, §4.6).
   - Same encoder; A (local factors + GRU + cost), B (explicit z + couplings + joint E_B with exact bounded-z marginal), C (hybrid).
   - Checks: overfit tiny pools, order sensitivity, masked-gradient tests, exact joint objective, leakage guards.
   - CPU only, ≤ 1 h, no GPU, no release.
4. **G5/G6 only after P5.3 passes:** 3 seeds per arm, matched roots, budgets and provenance, with a **certified-only versus certified+budget-negative** training and evaluation sensitivity analysis.
5. **Production-policy question to decide before P5.2.**
   - Either keep 3 seeds (P4 showed them redundant for deterministic terminals but unmeasured for RRT-limited ones), or predeclare a v2 that records "deterministic terminal" separately and adds seeds only for RRT-limited terminals.
   - **This needs your decision. P4's own labels will not be changed post hoc.**

## 8. Commands and commits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest -q tests/test_operational_teacher.py tests/test_sector_cert.py` | 0 | 45 passed (pre-gate) |
| `python run.py g4c-lf-p4-regression --out runs/g4c_lf_p4/regression` | 0 | 261/261, 6/6 replays, CLOSED |
| `python run.py g4c-lf-p4-pilot --out runs/g4c_lf_p4/pilot` | 0 | 12 decided; 5 / 4 / 3 / 0 |
| `python -m pytest -q tests/test_operational_teacher.py` (after adding `loss_masks`) | 0 | 15 passed |

Committed with explicit paths only: `teacher_opneg.toml`, `operational_teacher.py`, `teacher_pilot.py`, `teacher_pilot_figures.py`, `tests/test_operational_teacher.py`, `run.py`, `runs/g4c_lf_p4/` and this report. Pushed without force. Hashes and remote verification are given in chat and recorded in report 0020.

**STOP.** P5 (G4B re-check, G4C-D3 collection, G4E-ABC smoke), any production collection and any training need your separate authorization.
