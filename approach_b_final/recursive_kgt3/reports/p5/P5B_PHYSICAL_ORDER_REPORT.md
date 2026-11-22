# P5B — Bounded physical validation of static order recovery

Branch `naren/kgt3-exec-composition`, from the P5A commit `7fcfe6992d`. This is an evaluator-only stage, authorized by the owner for P5B alone, with hard caps of 32 teacher calls, 2 workers and 1,800 s. The following were all untouched:
- frozen models and checkpoints, P4 seals and predictions, the DEV split;
- historical tests and teacher semantics;
- release_v2 TEST.

## Verdict: **PHYSICAL_ORDER_RECOVERED** (1 endpoint, 1 root)

**The success.** Endpoint ENG2_e3c632c779c0 (certified K=4) is the R3-committed 10-move assignment. Its pre-scheduled static-valid order **q23** (tier T4, a different first mover) returned:
- **X = `VERIFIED`** with the pinned long teacher (`BXY_X_TEACHER_V2_LONG`): all 10 relocations executed in the fixed order with carried robot state, then the terminal free-gripper connector to `q_ref`;
- **independent replay passed**;
- a predeclared fresh-process repeat returned `VERIFIED`, with byte-identical witness ids (10 relocation records plus the connector);
- **Y = `VERIFIED`** from a fresh `y_query`. This agrees with the reused P4 Y=1, whose Y2 key matches.

**Decided same-endpoint contrast: yes, scope-limited.** The original R3 committed order of the **same** 10 moves is `CERTIFIED_INFEASIBLE` at relocation 1 (P4 teacher row, reused). The static checker independently fails that order at the same step (FAIL_PLACE).
- **Scope of that certificate:** it is the teacher's certificate for that fixed order, at the arrangement and carried state after its first move. It is not a global impossibility claim about the endpoint.
- **Order matters even among statically valid orders.** Two other static-valid orders of this endpoint returned `UNKNOWN_PLANNER`: the P5A DP order (q03) at relocation 2, and alternative A (q14) at relocation 4.

**Motion GIF.** `p5b_q23_ENG2_e3c632c779c0_motion.gif` is rendered only from the teacher's stored witness arrays of q23 and the fresh Y. It shows 10 relocations, the connector back to `q_ref`, then the target to the goal. Nothing in it is re-planned or schematic.

## Pre-registration, then execution

| Step | Commit | Content |
|---|---|---|
| Schedule frozen **before any teacher call** | `b1939e8ccb` | `P5B_SCHEDULE.json`, sha256 `08f2857e48be1ad8…`; harness and tests |
| Batch 1: **VOID** | – | 27 launches, all `WORKER_ERROR` |
| Harness fix | `6480fdd517` | Teacher modules can no longer resolve to `recursive_kgt3/` |
| Fail-closed guard | `5f342459ec` | Any `WORKER_ERROR` stops further launches |
| Batch 2 | – | 29 teacher calls, 379.1 s wall, no cap event |

**Schedule rules** (outcome-blind, all listed in the schedule file):
- **Endpoints:** for each of the 6 P5A-recoverable roots, take ≤2 of the 13 A-ORDER-RECOVERABLE endpoints. Committed origin comes first, then the opposite origin; ties go to smallest m, then signature. This gives **9 endpoints**.
- **Orders, by tier:**
  - T1/T2: the P5A DP order;
  - T3/T4: static-valid orders whose first mover is the smallest feasible one different from earlier choices (completed deterministically);
  - T5: the matched original order, as a descriptive control.
- **Deduplication:** any order already tested by the P4 teacher is reused, with no new call. All 9 T5 controls were reused.
- **Execution:** strictly in queue order; no candidate was added or chosen by outcome.
- **Confirmation reserve:** 4 calls, used only for the first two X-positive endpoints (one fresh X repeat plus one fresh Y each). One positive occurred, so 2 were used.
- **Y reuse:** only when the order-invariant Y2 key (root, context, sorted endpoint) and the teacher version match the P4 `VERIFIED` row. The dry run confirmed all 36 matched.

## Results: 36 distinct ordered queries (27 new calls + 9 reused P4 rows)

| Tier | Queries | VERIFIED X | CERTIFIED_INFEASIBLE (scoped) | UNKNOWN_PLANNER |
|---|---|---|---|---|
| T1 P5A DP order, first endpoint | 6 | 0 | 0 | 6 |
| T2 P5A DP order, second endpoint | 3 | 0 | 0 | 3 |
| T3 alternative first mover A | 9 | 0 | 0 | 9 |
| T4 alternative first mover B | 9 | **1** (q23) | 0 | 8 |
| T5 original order (reused P4) | 9 | 0 | 3 (all static-invalid) | 6 |

**Counts by unit:**

| Unit | Result |
|---|---|
| Unique endpoints | 1 of 9 has a physical X=1 witness |
| Unique roots | 1 of 6 (ENG2_e3c632c779c0) |
| Full X∧Y successes | 1 (q23, plus its identical repeat q23c) |
| Decided same-endpoint contrasts | 1 (q23 X=1 vs original `CERTIFIED_INFEASIBLE`) |
| Distinct ordered queries | 36 |

**Static-valid orders reaching physical X=1:**
- 1 of the 27 new calls. Wilson 95% interval 0.7–18%, but the queries are clustered within 6 roots, so they are not independent.
- 1 of 31, counting the 4 static-valid orders already tested in P4 (all UNKNOWN).

**Where the 26 new UNKNOWNs fail.** Relocation 0: 8, relocation 1: 4, relocation 2: 5, relocation 3: 5, relocation 4: 4. None reached the connector.

**What is inside each UNKNOWN.** The motion planner reported `CERTIFIED_INFEASIBLE` for the failing move (from the achieved carried state) in 10 cases and `UNRESOLVED` in 16. In all 26 the lookup channel was `UNKNOWN_NO_LIBRARY_WITNESS`, so the teacher's aggregate status is `UNKNOWN_PLANNER`.
- These are reported as **unresolved within budget, never as negatives**.

## Strongest counterexample: static validity is necessary, not sufficient

- All 27 new orders were statically valid under the MINK_STATIC_V2 kill tables, yet only 1 executed physically.
- 8 failed at the **first** relocation, from `q_ref` itself. Static liveness (a grasp screen at the source and destination) says nothing about arm reach or approach from the carried configuration.
- Within the successful endpoint, 2 of 3 static-valid orders failed (UNKNOWN). A static order is therefore at best a screen, and choosing among statically valid orders requires execution-aware information.

## Resources and protocol

**Resources:**
- Teacher calls: **29** in batch 2 (27 X + 1 fresh-process X repeat + 1 fresh Y), within the cap of 32.
- Voided batch-1 launches: 27, discussed below.
- Wall time: batch 2 **379.1 s**, plus 15.0 s for the void batch, giving 394 s cumulative against the 1,800 s cap.
- Teacher process CPU, summed over new X calls: 650 s. Workers: 2.
- Per-query budgets, grasps, attempts and tolerances were not changed: the pinned `teacher_long` (`af0e9fd4ac94…`), unchanged frozen `bxy_teacher` (`c18ac91c89b9`) / `p16_motion` (`43f4c38c6418`) / `p15_search` (`9c2af1373798`). The workers loaded the same teacher `planner.py` (`d48cc2f43a18`) as P4's `dev_verify`.

**Protocol deviations, disclosed:**
1. **Batch 1 was voided (harness defect).** My module put `recursive_kgt3/` on `sys.path`, whose `planner.py` shadowed the teacher's. All 27 calls raised `AttributeError` at the first planner call: 15 s, 0 outcomes, 0 witness files.
   - The owner chose to void them and rerun the identical frozen schedule under a fresh 32-call cap, with the wall cap cumulative. The ledger is preserved as `P5B_LEDGER_batch1_VOID_HARNESS_ERROR.jsonl`.
   - The fix and a fail-closed guard were committed before batch 2.
2. **GIF header text.** The GIF reuses `scaling2d_k12/gif_physical._render` unchanged, except that its header text is replaced, because "K=len(seq) (certified min)" would be false for a reordered 10-move plan.

## Checks

- **Tests:**
  - `tests/test_p5b_physical.py`: 9 tests. They cover static validity of alternative orders vs brute force, and that the frozen schedule rebuilds identically. The mock teacher checks the call cap, the confirmation reserve, strict queue order, resume, the cumulative wall cap, wall-cap abort to UNKNOWN, fail-closed on Y-key mismatch and on `WORKER_ERROR`, that UNKNOWN never becomes a negative, and that public modules never import P5B.
  - Together with P5A's 19 tests: **28/28 pass**.
- **Historical regression:** `test_p1_p2.py` passes 22/22. The `test_p4_mock.py` output is identical to the committed `GATE_B_MOCK.json`. No pre-existing file was modified. P4 and K≤3 parity are preserved because data, models and planners are byte-unchanged.
- **Leakage:**
  - No private construction-witness sequence appears in any P5B file (programmatic check). The GIF strips the layout's `witness_set`.
  - The P5A kill-table DP is used only offline, to schedule.
  - Public modules (`data`, `models`, `planner*`, `run_p4`) do not import `p5b_physical`, `teacher_long` or `dev_records` (tested).

## Downstream (report only, nothing implemented)

**P6: REVISE before GO.** Order recovery is *possible*: one decided physical rescue on a committed P4 endpoint. But static validity predicts execution poorly (1/27), so a P6 that only finds statically valid orders would mostly produce UNKNOWNs. P6 must therefore be **execution-aware**:
- order search over prefixes using only learner-visible public scene fields and the frozen K≤3 models (local `px` from the *achieved-state proxy*, cVAE proposals), with prefix histories kept separate, as plan2 states;
- the P5A kill-table DP must stay an evaluator; it must never be a ranking feature, filter or look-ahead;
- a predeclared bounded DEV physical check is needed before any comparison.

The single witness (1 root, K=4) does not support claims about K≥9 or about learned causal inference.

**P7: amend as follows.**
- In 29 of the 40 P5A irreparable endpoints, a mover's pickup is blocked by never-moved clutter. These need **enabling-mover insertion or replacement** within the 12-action cap: no object moved twice, and no private blocker identities used online.
- For the 22 endpoints already at the cap, a move must be **replaced or the candidate rebuilt**, because insertion alone is impossible.
- Destination-only repair is a separate ablation, with matched-compute flat and random controls.
- All of this describes a finite P4 candidate pool. It does not show that K9/K12 is unsolvable.

**Recommendation: GO on the P5B gate (PHYSICAL_ORDER_RECOVERED); REVISE for P6** (an execution-aware composition hypothesis plus a bounded physical DEV check). P7 should be amended as above. Nothing beyond P5B was started.

## Files

**Added:**
- `p5b_physical.py`: evaluator-only; `schedule` / `run` / `gif` / `report` modes;
- `tests/test_p5b_physical.py`;
- in `reports/p5/`: `P5B_SCHEDULE.json` (+ `.sha256`), `P5B_LEDGER_batch2.jsonl`, `P5B_LEDGER_batch1_VOID_HARNESS_ERROR.jsonl`, `P5B_ATTEMPTS.jsonl`, `P5B_SUMMARY.json`, `p5b_orders.png` (static-only diagrams labelled with teacher outcomes; the verified order in green), `p5b_q23_ENG2_e3c632c779c0_motion.gif`, and this report.

**Not committed:**
- the teacher witness `.npz` arrays (`/home/naren/kgt3_runs/p5b/run2/witnesses`);
- `dev_private`, kill tables and raw P4 `verify.jsonl`.

**Reproduce** (from `scaling2d_k12`, with `ABF_ROOT` set and the env2d Python):
```
p5b_physical.py run reports/p5/P5B_SCHEDULE.json $PWD DEV_PRIVATE RUN_DIR [--dry-run]
p5b_physical.py gif RUN_DIR/ledger.jsonl $PWD DEV_PRIVATE RUN_DIR q23 GIF_DIR
python p5b_physical.py report reports/p5/P5B_SCHEDULE.json LEDGER VOID_LEDGER VERIFY DEV_PUBLIC reports/p5
```
