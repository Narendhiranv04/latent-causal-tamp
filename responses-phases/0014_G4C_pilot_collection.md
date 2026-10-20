# 0014 — G4C-P1: authorized five-root 2D teacher-evidence pilot

| Field | Value |
|---|---|
| Report number | 0014 (new; 0001–0013 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4C-P1 pilot only**: 5 roots, 59 frozen units. No full G4C run, no new roots or queries, no budget expansion, no training, no G4E/G5/G6, no 3D, no hardware. |
| Execution contract | `instruction-phase-md/G4C_P1_5Root_Pilot_Collection_Instructions.md` (170 lines, read in full; your file, left untracked). Authorization: your message of 20 October 2026, "I explicitly authorize the G4C five-root pilot only". |
| Documents read | Reports 0011–0013; addenda A1 and A2; `runs/g4c_preflight/*`; Methodology v1.7 and Guide v1.9 from your untracked folder (unchanged hashes; not committed). No `AGENTS.md` or `CLAUDE.md` exists. |
| Previous turn sync | Report 0013 was committed as `9e7242117a72429ea13f949d68e1d94b5a0f9510`. At the start, HEAD, `main` and `origin/main` all equalled it, with no tracked modifications. |
| Starting revision | `9e7242117a72429ea13f949d68e1d94b5a0f9510` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0015. |
| Run directory | [`../runs/g4c_pilot/`](../runs/g4c_pilot/) (2.3 MB). Commands: `g4c-pilot-finalize` → `g4c-pilot-run` → `g4c-pilot-judge`. |
| **Decision** | **`G4C_PILOT_COMPLETE`**: all 59 units ran and all 59 dispositions were independently audited from re-checked checkpoints. **A 20-root G4C readiness claim is NOT possible** (`G4C DATA_READY` not claimed). |
| Labels | **13 POSITIVE, 26 NEGATIVE, 20 UNKNOWN**, 0 NOT_RUN, 0 contradictions |
| Compute | **340.2 CPU-s** (units 338.9 plus coordinator 1.4) against the 10,800 cap. Wall 5 min 46 s (08:26:06–08:31:52 UTC). Maximum unit CPU 105.6 s; overshoot 0.0; 0 cancellations; 0 resumes. |

---

## 1. Identities and preconditions (all checked before the first teacher call)

**Frozen plan.**
- `c761c684…3a3` is the **canonical plan hash**: `stable_hash` of `plan.json` without its `plan_hash` field. It re-derives exactly.
- The raw-file sha256 is `c6c8a016…5b95`, as recorded in the preflight manifest.
- All preflight source, historical-input and output hashes match.
- Regenerating the plan in memory with the current code reproduces it byte-for-byte, with no validator errors.

**Pilot subset.** The predeclared `pilot.roots` are exactly r00/r08/r10/r14/r19 with 2/10/11/19/17 = 59 units, and all 59 pass `g4d_run.unit_scene`'s identity checks (root scene hash, query identity, intervention eligibility, seed keys). Their structural maxima, 60 relocation skills and 59 target evaluations, **equal** the authorized caps, so no admitted schedule could exceed them.

**Authorization record.** [`authorization.json`](../runs/g4c_pilot/authorization.json), hash `sha256:464b6345…4895`, is immutable. It holds:
- every numeric field you authorized;
- the five roots;
- the parent plan's canonical and file hashes;
- the instruction's sha256;
- the excluded scope;
- a 60 s orchestration reserve.

**Derived pilot plan.** [`pilot_plan.json`](../runs/g4c_pilot/pilot_plan.json), hash `sha256:a10ef74d…a3c1`, status `FINAL_AUTHORIZED_PILOT`.
- It copies the 59 units **byte-identically and in the parent's order** (tested), together with the five roots.
- Limits: CPU 900 per unit (cancel at 870), aggregate 10,800 including the reserve, 1 worker, unit wall 1,800, total wall 14,400, poll 0.25 s.
- Threads are pinned to 1.
- It binds HEAD `9e72421` and sha256 hashes of 30 source, config and plan files. These were re-verified before collection and again in the judge: **unchanged**.

**The parent `plan.json` was not modified**; its `budget` fields remain `null` (byte hash compared after the run). The 15 excluded roots and 108 units were **never run**: every ledger entry is one of the 59 pilot units.

---

## 2. Code (new and changed)

Line counts are total / logical (non-blank, non-comment, docstrings included).

| File | Purpose | Lines |
|---|---|---|
| `g4c_pilot.py` (new) | Authorization record and checks; finalization adapter (fails closed); run command (source, authorization and parent re-verification, then the **unchanged** `g4d_run.run_collection`); the G4C judge (`adjudicate`, `judge_root`, `bc_pool`, `judge`) | 317 / 280 |
| `g4c_pilot_figures.py` (new) | Judge runner: evidence rebuilt with `g4d_gate.assemble` / `g4d_run.unit_evidence`, integrity, CSV/JSON outputs, A/B/C entitlement, figures, recursive manifest | 189 / 178 |
| `tests/test_g4c_pilot.py` (new) | 14 tests (mocks and fixtures; no CPU burning, no teacher calls) | 213 / 180 |
| `run.py` | `g4c-pilot-finalize`, `g4c-pilot-run` and `g4c-pilot-judge` dispatch | +11 |

**Not modified:**
- every frozen dependency: `g4d_run.py`, `g4c.py`, `teacher.py`, `ordered.py`, `verify.py`, `evaluate.py`, `skill.py`, the configs and the parent plan;
- `verify.py` and `skill.py` were not refactored.

`run.py` is not in either source manifest. No second teacher pipeline exists: collection is G4D's tested guard, checkpoints and revalidation.

### Pre-collection tests (all passed before the first teacher call)

**Refused before any teacher call** (counters show 0 calls):
- aggregate set to 18,000;
- a missing budget field;
- full 20-root scope;
- a tampered parent plan (hash);
- a 60th unit;
- non-null parent budget fields;
- a tampered source hash.

**Finalization** preserves the parent file byte-for-byte, and the 59 identities, order and seed keys exactly.

**Envelope under mocks:**
- the guard receives 900 s per unit and at most 1,800 s wall;
- an 870 s CPU-censored unit is recorded and the run continues;
- a 905 s overshoot raises `enforcement_failure` and stops;
- 9,900 + 900 + 60 > 10,800 gives `NOT_RUN_BUDGET` without launching;
- an expired deadline gives `NOT_RUN_WALL`;
- a STARTED unit becomes `INTERRUPTED_AMBIGUOUS` and is **not** rerun.

**Judge:**
- a POSITIVE is refused when the invocation or continuity checks fail, when safe retreat is missing, or when success is only self-reported;
- a NEGATIVE is refused for an unaccepted certificate or TRAJECTORY scope;
- CPU-censored stays UNKNOWN;
- witness plus certificate gives CONTRADICTION.

**Scene edits and omissions:**
- scene edits never change q, gripper or attachment, and change exactly the listed objects;
- omission remainders keep their order and omitted objects stay at their initial poses.

**B/C pool rules:**
- one unknown active slot disqualifies a pool;
- a decided NEGATIVE still decides its slot;
- labels never transfer across roots;
- a changed mask or a scrambled catalogue is rejected.

**Denominators:**
- 59 units with COMPLETED processes but UNKNOWN labels give **0 POSITIVE**;
- the 20-root gate stays `NOT_EVALUATED_FULL_SET / PILOT_ONLY`.

**Real archived evidence.** The new adjudicator reproduces all 20 archived G4D labels exactly.

**End-to-end dry run.** The whole judge pipeline ran on a scratch ledger where every unit was unstarted. It made 0 calls and correctly reported `G4C_PILOT_PARTIAL`.

---

## 3. All 59 unit dispositions

Every process stopped `COMPLETED`. Labels are the **G4C judge's** verdicts over checkpoints re-checked by the independent checker:
- certificates are re-run;
- relocation records are re-certified in their pre-move scenes, from the previous achieved state;
- the cost is recomputed;
- the target witness passes `check_witness` and its recorded invocation equals the achieved state.

"Calls" lists relocation-planner calls / target evaluations. "J" is the first-witness relocation cost; scene units carry an empty relocation record (not a cost label).

| Unit | Label | Reason | CPU s | Calls | J |
|---|---|---|---|---|---|
| `seq:g4c_r00:empty` | POS | complete witness, all checks true | 99.72 | 0/1 | 0 |
| `scene:g4c_r00:o03>51` | POS | complete witness (target-only) | 105.61 | 0/1 | — |
| `seq:g4c_r08:empty` | NEG | GOAL_OVERLAP | 2.12 | 0/0 | 0 |
| `seq:g4c_r08:o00>47` | UNK | relocation action 0: SCHEDULE_COMPLETED_ALL_PAIRS_CERTIFIED_BLOCKED | 2.48 | 1/0 | — |
| `seq:g4c_r08:o00>15` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 2.41 | 1/0 | — |
| `seq:g4c_r08:o01>46.o00>47` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 2.45 | 1/0 | — |
| `seq:g4c_r08:o00>47.o01>46` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 2.50 | 1/0 | — |
| `seq:g4c_r08:o01>46` | NEG | GOAL_OVERLAP | 2.31 | 1/0 | — |
| `scene:g4c_r08:o00>47` | UNK | target NO_WITNESS_UNCERTIFIED_REJECTIONS | 7.31 | 0/1 | — |
| `scene:g4c_r08:o01>46` | NEG | GOAL_OVERLAP | 2.05 | 0/0 | — |
| `scene:g4c_r08:o00>47.o01>46` | UNK | target NO_WITNESS_UNCERTIFIED_REJECTIONS | 7.22 | 0/1 | — |
| `scene:g4c_r08:o03>49` | NEG | GOAL_OVERLAP | 0.64 | 0/0 | — |
| `seq:g4c_r10:empty` | NEG | GOAL_OVERLAP | 0.67 | 0/0 | 0 |
| `seq:g4c_r10:o00>20` | POS | complete witness | 5.59 | 1/1 | 1.546 |
| `seq:g4c_r10:o00>6` | NEG | FIRST_MOVER + ORDER_FIRST_ACTION | 1.22 | 0/0 | — |
| `seq:g4c_r10:o00>5` | NEG | STATIC_ENDPOINT_INVALID (deliberate: P occupied) | 0.36 | 0/0 | — |
| `seq:g4c_r10:o01>14.o00>5` | **POS** | complete witness (two moves) | 4.28 | 2/1 | 1.949 |
| `seq:g4c_r10:o00>5.o01>14` | **NEG** | ORDER_FIRST_ACTION | 1.17 | 0/0 | — |
| `seq:g4c_r10:o01>14` | NEG | GOAL_OVERLAP (relocation witness exists) | 2.41 | 1/0 | 1.753 |
| `scene:g4c_r10:o00>20` | POS | target-only witness | 7.03 | 0/1 | — |
| `scene:g4c_r10:o01>14` | NEG | GOAL_OVERLAP | 0.68 | 0/0 | — |
| `scene:g4c_r10:o00>20.o01>14` | POS | target-only witness | 6.78 | 0/1 | — |
| `scene:g4c_r10:o03>62` | NEG | GOAL_OVERLAP | 0.72 | 0/0 | — |
| `seq:g4c_r14:empty` | NEG | GOAL_OVERLAP | 0.61 | 0/0 | 0 |
| `seq:g4c_r14:o00>38` | POS | complete witness | 7.38 | 1/1 | 1.480 |
| `seq:g4c_r14:o00>6` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 4.69 | 1/0 | — |
| `seq:g4c_r14:o01>7.o02>39.o00>38` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 1.29 | 1/0 | — |
| `seq:g4c_r14:o02>39.o01>7.o00>38` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 1.25 | 1/0 | — |
| `seq:g4c_r14:o00>38.o01>7.o02>39` | UNK | relocation action 1 (after a witnessed action 0): NO_WITNESS_UNCERTIFIED_REJECTIONS | 3.42 | 2/0 | — |
| `seq:g4c_r14:o01>7.o00>38` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 1.23 | 1/0 | — |
| `seq:g4c_r14:o02>39.o00>38` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 1.12 | 1/0 | — |
| `seq:g4c_r14:o01>7.o02>39` | NEG | GOAL_OVERLAP | 1.12 | 1/0 | — |
| `seq:g4c_r14:o02>39` | NEG | GOAL_OVERLAP | 0.88 | 1/0 | — |
| `seq:g4c_r14:o01>7` | NEG | GOAL_OVERLAP | 1.00 | 1/0 | — |
| `seq:g4c_r14:o02>39.o01>7` | NEG | GOAL_OVERLAP | 1.11 | 1/0 | — |
| `seq:g4c_r14:o00>38.o02>39` | UNK | relocation action 1: NO_WITNESS_UNCERTIFIED_REJECTIONS | 3.37 | 2/0 | — |
| `seq:g4c_r14:o00>38.o01>7` | UNK | relocation action 1: NO_WITNESS_UNCERTIFIED_REJECTIONS | 3.74 | 2/0 | — |
| `scene:g4c_r14:o00>38` | POS | target-only witness | 1.86 | 0/1 | — |
| `scene:g4c_r14:o01>7` | NEG | GOAL_OVERLAP | 0.57 | 0/0 | — |
| `scene:g4c_r14:o02>39` | NEG | GOAL_OVERLAP | 0.57 | 0/0 | — |
| `scene:g4c_r14:o00>38.o01>7` | POS | target-only witness | 1.87 | 0/1 | — |
| `scene:g4c_r14:o04>8` | NEG | GOAL_OVERLAP | 0.57 | 0/0 | — |
| `seq:g4c_r19:empty` | NEG | GOAL_OVERLAP | 0.45 | 0/0 | 0 |
| `seq:g4c_r19:o00>9` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 1.27 | 1/0 | — |
| `seq:g4c_r19:o00>27` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 1.14 | 1/0 | — |
| `seq:g4c_r19:o01>27` | NEG | GOAL_OVERLAP (relocation witness exists) | 1.35 | 1/0 | 1.181 |
| `seq:g4c_r19:o01>28` | NEG | GOAL_OVERLAP (relocation witness exists) | 1.31 | 1/0 | 1.143 |
| `seq:g4c_r19:o00>9.o01>27` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 1.83 | 1/0 | — |
| `seq:g4c_r19:o00>9.o01>28` | UNK | relocation action 0: NO_WITNESS_UNCERTIFIED_REJECTIONS | 1.71 | 1/0 | — |
| `seq:g4c_r19:o00>27.o01>27` | NEG | STATIC_ENDPOINT_INVALID (deliberate) | 0.38 | 0/0 | — |
| `seq:g4c_r19:o00>27.o01>28` | UNK | relocation action 0: ALL_PAIRS_CERTIFIED_BLOCKED | 1.58 | 1/0 | — |
| `seq:g4c_r19:o01>27.o00>9` | POS | complete witness (two moves) | 9.08 | 2/1 | 3.021 |
| `seq:g4c_r19:o01>27.o00>27` | NEG | STATIC_ENDPOINT_INVALID (deliberate) | 0.36 | 0/0 | — |
| `seq:g4c_r19:o01>28.o00>9` | POS | complete witness (two moves) | 7.22 | 2/1 | 4.242 |
| `seq:g4c_r19:o01>28.o00>27` | POS | complete witness (two moves) | 3.12 | 2/1 | 1.602 |
| `scene:g4c_r19:o00>9` | UNK | target skill returned CERTIFIED_INFEASIBLE (all pairs blocked); no checker-accepted certificate | 0.90 | 0/1 | — |
| `scene:g4c_r19:o01>27` | NEG | GOAL_OVERLAP | 0.46 | 0/0 | — |
| `scene:g4c_r19:o00>9.o01>27` | POS | target-only witness | 0.87 | 0/1 | — |
| `scene:g4c_r19:o02>26` | NEG | GOAL_OVERLAP | 0.45 | 0/0 | — |

**Realized calls:** 38 relocation-planner calls (cap 60), 16 target evaluations (cap 59) and 13 HOME diagnostics (all inside the envelope; they never change a label). 43 target evaluations were not run: 26 because an accepted certificate already covered the unit (target `NOT_RUN` by policy), and 17 because no complete relocation witness existed.

**UNKNOWN reasons (20):**

| Reason | Count |
|---|---|
| First relocation: all pairs certified blocked from q0 | 7 |
| First relocation: schedule completed with uncertified rejections | 7 |
| Later relocation after a witnessed first action | 3 |
| Target schedule completed without a witness | 2 |
| Target skill returned all-pairs-blocked | 1 |

None is a budget or timeout end. "All pairs certified blocked" is the skill's own connector verdict, scoped to the start configuration. **No checker-accepted certificate kind exists for it**, so those units correctly stay UNKNOWN (§6).

**NEGATIVE reasons (26):**

| Reason | Count |
|---|---|
| GOAL_OVERLAP | 21 |
| STATIC_ENDPOINT_INVALID (deliberate) | 3 |
| ORDER_FIRST_ACTION | 1 |
| FIRST_MOVER + ORDER_FIRST_ACTION | 1 |

---

## 4. Root-level evidence

| Root | Family | POS / NEG / UNK | Empty repair | Nonempty positives | Order contrast | Decided scene pairs (Δ) | Decided omissions | Cost labels (nonempty) | B/C full pool |
|---|---|---|---|---|---|---|---|---|---|
| r00 | J0 | 2 / 0 / 0 | **POSITIVE**, J = 0 | — | — | nuisance Δ=0 (**both POSITIVE**) | — | — | qualifies (**trivial**: one sequence, 2 slots) |
| r08 | J2 | 0 / 6 / 4 | NEG (goal overlap) | 0 | none (both orders UNKNOWN) | singleton B Δ=0, nuisance Δ=0 (both NEG by goal overlap) | 0 of 6 | — | no: 15/35 slots |
| r10 | J3 | 5 / 8 / 0 | NEG | o00>20, (o01>14, o00>5) | **YES**: (o01>14, o00>5) POS vs (o00>5, o01>14) NEG ORDER_FIRST_ACTION | A Δ=+1, joint A+C Δ=+1, C Δ=0, nuisance Δ=0 | 6 of 6 | 3 | **qualifies: 40/40 slots** |
| r14 | J4 | 3 / 7 / 9 | NEG | o00>38 | none (every A-later order UNKNOWN) | A +1, joint A+B +1, B 0, C 0, nuisance 0 | 6 of 36 | 1 | no: 78/96 |
| r19 | J9 | 4 / 6 / 7 | NEG | 3 two-move | none (A-first orders UNKNOWN) | joint A+B +1, B 0, nuisance 0; singleton A UNKNOWN | 10 of 24 | 5 | no: 59/88 |

**Order contrasts.** One is decided, on r10, and it is exactly the J3 design. With the staging cell P occupied by C, moving A to P first is certified excluded (PLACE screen over all 48 grasps). C-first followed by A→P has a complete witness. In r08, r14 and r19 the A-first relocations ended UNKNOWN, mostly connector verdicts from q0, so no further contrast was decided.

**Scene effects (fixed robot).** Nonzero decided Δ = +1 occurs in r10 (A, A+C), r14 (A, A+B) and r19 (A+B); all come from moving the goal occupant. Most zero-effect pairs are trivially decided, because both sides carry the same goal-overlap certificate. **The only informative zero-effect control is r00's nuisance edit**, where both sides are target witnesses.

**Omissions.** In r10's positive two-move repair, Δ = +1 for omitting either action and +1 for omitting both. In r19, omitting o00 from each positive repair gives Δ = +1; omitting o01 is masked, because (o00>9) is UNKNOWN. The decided omissions in r14 all have Δ = 0, because the full sequences are NEGATIVE.

**Nonadditivity.**

| Root | Comparison | Δ joint | Δ singletons | κ |
|---|---|---|---|---|
| r10 | omissions of (o01>14, o00>5) | 1 | 1, 1 | **−1** |
| r10 | scene A+C | 1 | 1, 0 | 0 (additive) |
| r14 | scene A+B | 1 | 1, 0 | 0 (additive) |
| r19 | singleton A | — | UNKNOWN | not computable |

The r10 omission case is the only decided nonadditive example: singletons sum to 2 while the joint effect is 1, the access dependency.

**Costs, first V2 witness, nonempty.**

| Root | Sequence | Label | Endpoint distance C_d | J |
|---|---|---|---|---|
| r10 | o00>20 | POS | 0.177 | 1.546 |
| r10 | (o01>14, o00>5) | POS | 0.213 | 1.949 |
| r10 | o01>14 | NEG (goal) | 0.125 | 1.753 |
| r14 | o00>38 | POS | 0.177 | 1.480 |
| r19 | o01>27 | NEG | 0.088 | 1.181 |
| r19 | o01>28 | NEG | 0.125 | 1.143 |
| r19 | (o01>27, o00>9) | POS | 0.265 | 3.021 |
| r19 | (o01>28, o00>9) | POS | 0.302 | **4.242** |
| r19 | (o01>28, o00>27) | POS | 0.302 | **1.602** |

The last two pairs show the same endpoint distance with joint travel differing by 2.6×. Endpoint distance is not robot effort. This is one observation, not a trend.

**B/C full-pool diagnostics.** Each missing item is a (sequence, slot, unit) link: [`bc_pool_coverage.json`](../runs/g4c_pilot/bc_pool_coverage.json).
- **r10** qualifies: every active slot is decided.
- **r00** qualifies trivially (empty repair plus its nuisance scene query only).
- **r08**: 20 of 35 slots missing; its catalogue scene units for A and A+B are UNKNOWN, as are all of A's relocations.
- **r14**: 18 of 96 missing; the A-later two-move remainders and three-move sequences are UNKNOWN.
- **r19**: 29 of 88 missing. 13 come from the UNKNOWN catalogue edit `scene:g4c_r19:o00>9`, which appears in every pool sequence's zS slot. The rest are the A-first sequences.

**A/B/C entitlement** (`pilot_result.json`): equal source information for all arms.

| Arm | May consume |
|---|---|
| All arms | the same 59 units: 39 decided (24 ordered sequences), 15 decided scene pairs, 22 decided omission pairs, 14 cost entries (including empty J = 0) |
| B and C | additionally z-field views: 194 of 261 active slots decided; the exact joint-pool loss only on r00 (trivial) and r10 |

Learner inputs are only the `learner_tensors_v2` allowlist; no labels, witnesses or root IDs.

---

## 5. Progress against the 20-root gate (`NOT_EVALUATED_FULL_SET / PILOT_ONLY`)

The judge's numerators are below. I add a stricter reading where a count is trivially inflated; that reading was **added in this report after seeing the results**, and the judge's own numbers are unchanged.

| Threshold | Required (20 roots) | Pilot (judge) | Stricter reading | Remaining planned capacity | Reachable if all remaining decide? |
|---|---|---|---|---|---|
| Zero-move witness roots | 6 | 1 (r00) | 1 | 6 | yes, but needs 5 of the 6 remaining planned roots (J0 ×5 + J5J6) |
| Nonempty complete witness | 8 | 3 | 3 | 9 | yes |
| Multiple sufficient alternatives | 4 | 2 (r10, r19) | 2 | 5 | yes |
| Decided same-endpoint order contrasts | 4 | 1 (r10) | 1 | 5 | yes, but needs 3 of 5 |
| Decided nonzero scene effects | 4 | 3 | 3 | 9 | yes |
| Decided omission effects | 4 | 3 (r10, r14, r19) | 2 with nonzero Δ | 7 | yes |
| Zero-effect / nuisance controls | 4 | 5 | **1 informative** (r00); 4 trivially decided by goal overlap | 6 | yes |
| Cost-labelled roots | 8 | 5 | **3** (nonempty relocation witnesses; 2 of the 5 are empty J = 0) | 9 | yes |
| Multi-move cost roots | 4 | 2 | 2 | 7 | yes |
| Fully decided B/C mini pools | 4 | 2 | **1 substantive** (r10); r00 trivial | 3 (r06, r07, r09) | only if all three qualify, or if r00-style trivial pools count |
| Nonadditive examples | 2 | 1 (r10) | 1 | 3 | yes |

**Concern recorded without rewriting the plan.** The B/C full-pool target is at serious risk. Under a substantive reading it needs all three remaining designed roots to qualify, and each of the three non-trivial pilot pools that did not qualify lost between 18 and 20 slots to a single UNKNOWN scene edit or A-first relocations. **No 20-root readiness claim is possible from the pilot.**

---

## 6. Findings that matter for the full run (no change made)

1. **The dominant UNKNOWN source is relocation from q0, not budget.**
   - 7 first relocations ended with every grasp pair's connectors certified blocked from the initial configuration, and 7 more completed their schedule with uncertified rejections.
   - The skill's "all pairs certified blocked" verdict has **no independent checker kind**, so it cannot become an order-scope negative. Adding one (a first-action connector certificate over the full grasp family from q0) would need its own soundness review and authorization; I did not add it.
   - Pose screens alone are not enough, because the block is in the connector sweep, not the grasp pose.
2. **Compute was far below the request.** 340 CPU-s against a high estimate of 9,323 and a cap of 10,800; the r00 units (about 100 s each, both POSITIVE) dominate. This lowers the risk of the full request, but does not by itself justify the remaining 15 roots.
3. **Several designed "contrast opportunities" did not materialize.** The J2, J4 and J9 access designs produced A-first UNKNOWNs rather than certified PICK exclusions, so B did not actually block A's grasp from every direction. Only the J3 occupied-staging design produced a certified order contrast. The remaining planned roots include 3 more J3 roots (r11–r13), which are the most likely source of further contrasts.

---

## 7. Figures (from saved evidence; every panel labelled PILOT)

- [`A_initial_scenes.png`](../runs/g4c_pilot/A_initial_scenes.png): the five initial S0 scenes with the full 3R arm at q0, the goal (dashed red circle), role labels, the longest frozen sequence as numbered dashed arrows to ghost poses (proposals, marked SCHEMATIC), and each root's empty-repair label in the title.
- [`B_coverage.png`](../runs/g4c_pilot/B_coverage.png): the pilot's decided numerator per threshold (green) against the FUTURE 20-root target (hatched, NOT_EVALUATED_FULL_SET). The annotation gives remaining planned capacity and reachability; the title gives the 13/26/20/0 label split.
- [`C_compute.png`](../runs/g4c_pilot/C_compute.png). Top: per-unit CPU on a log scale, coloured by label (green POSITIVE, red NEGATIVE, amber UNKNOWN), with dots for wall time and dashed lines at 870 (cancel) and 900 (cap). Bottom: cumulative CPU against the 10,800 cap.
- [`D_recorded_evidence.png`](../runs/g4c_pilot/D_recorded_evidence.png): genuine recorded evidence.
  - **r10's order contrast:** the positive order with its recorded relocation paths (blue) and target transport (orange), beside the other order with its ORDER_FIRST_ACTION certificate.
  - **Fixed-robot scene effects:** the r10, r14 and r19 baselines (NEGATIVE by goal overlap) beside the scene edits with recorded target witnesses (Δ = +1).

  Where no trajectory was recorded, none is drawn.

---

## 8. Tests, replays and integrity

| Command | Exit | Result |
|---|---|---|
| `python -m pytest -q tests/test_g4c_pilot.py` (before collection) | 0 | 14 passed |
| `python -m pytest -q` (before collection) | 0 | 183 passed |
| `python run.py g4c-pilot-finalize --out runs/g4c_pilot` | 0 | plan `a10ef74d…`, authorization `464b6345…` |
| `python run.py g4c-pilot-run --out runs/g4c_pilot` | 0 | 59 COMPLETED, 346 s wall |
| `python run.py g4c-pilot-judge --out runs/g4c_pilot` | 0 | `G4C_PILOT_COMPLETE`, 5.2 s |
| `python -m pytest -q` (after collection; scratch call-counting plugin, not committed) | 0 | **183 passed** |
| `python run.py replay --run runs/<run> --report <scratch>` ×6 | all 0 | all `replay_passed` (77/77/2/50/20/257) |

**Integrity** (`pilot_result.json`), all true:
- sources unchanged since finalization;
- parent plan file and hash unchanged;
- authorization unchanged;
- ledger only contains pilot units;
- excluded roots never run;
- no contradiction.

No tracked file under `runs/` or `responses-phases/` changed.

**Calls.**
- **Pilot:** 38 relocation-planner calls, 16 target evaluations and 13 HOME diagnostics, all inside the guarded envelope.
- **Historical regression tests, separate, in-process:** 621 `planner.plan` and 60 `skill.plan_skill`, identical to before. The new test files made none. Worker subprocesses are not counted.

**Untracked files**, all yours and untouched: the instruction files (G4B, G4C, G4C-P1, G4D), the PDF copies, and `latent_causal_tamp_2D_ABC_guides_v1_7_v1_9/` with its `.zip`.

**Size note.** `g4c_pilot.py` has 280 logical lines, within the guideline.

---

## 9. Decision and recommendation

**`G4C_PILOT_COMPLETE`.** All 59 frozen units ran inside the authorized envelope, and all 59 dispositions are independently audited. Labels: 13 POSITIVE, 26 NEGATIVE, 20 UNKNOWN. **No 20-root G4C readiness claim is possible.**

**Recommendation.** Review the pilot's coverage before any further collection. The remaining 15 roots (108 units) need a **new explicit full-run approval**. Their measured cost suggests the original 30,600 CPU-s request is generous; the pilot's high-side extrapolation is roughly 340 × 108/59 ≈ 620 CPU-s, but tail risk remains.

Two scientific obstacles deserve a decision first:
1. whether to authorize review of a sound **first-action connector certificate** kind, which would convert some q0 "all pairs blocked" UNKNOWNs into order-scope negatives (a methodology-level change, not done here);
2. whether the B/C full-pool target should count trivial single-sequence pools.

Neither changes the frozen plan.

**STOP.** No full G4C run, G4E, G5, G6, 3D or hardware.

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains `g4c_pilot.py`, `g4c_pilot_figures.py`, `tests/test_g4c_pilot.py`, the `run.py` edit, `runs/g4c_pilot/` (2.3 MB, including per-unit checkpoints) and this report. It is pushed to `main` without force. The commit hash is given in chat and recorded in report 0015.
