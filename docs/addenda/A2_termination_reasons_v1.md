# Addendum A2 — Explicit termination events and normalized V2 failure reasons (version 1)

**Status:** in force from report 0011 (G4D corrections) for new skill results and for V2 evidence.
**Refines:** Methodology v1.6 §4 (three-valued evidence; a timeout or exhausted planner is no proof) and Implementation Guide v1.8 §7–8 (unknown attribution).
**Does not modify:** the PDFs, reports 0001–0010, or any archived run record. Every historical `reason` string is kept exactly as recorded.

## 1. The ambiguity

`skill.plan_skill` initialises its result as `SkillResult(UNRESOLVED, "PLANNER_BUDGET")`. Before this addendum it returned that default in two different situations:

1. **A search limit ended the search.** The number of UNRESOLVED connector results reached `skill2d.max_plan_failures`.
2. **The declared schedule finished without a witness, below that limit.** Every pick × place pair was tried (direct, then RRT-Connect), and some rejection was uncertified, for example a gray-band grasp pose or a connector that hit the node cap fewer times than the allowance.

Both are correctly UNRESOLVED. The string `PLANNER_BUDGET` describes only the first, however.

Report 0009 §5 found the second case on the follow-up roots g4a_r14 and g4a_r15: all 9 pregrasp connectors were certified blocked by the link-0 sweep from HOME, and gray-band grasp rejections remained. It documented the defect without fixing it.

## 2. Consequence for earlier counts

The G4A unknown split restated in Implementation Guide v1.8 §8 is: 67 relocation-search exhaustion, 29 target-budget exhaustion and 14 other. Its "29 target-budget" figure counts archived first-pass rows whose unknown reason is `TARGET_UNRESOLVED:PLANNER_BUDGET`.

That count rests on the raw reason code, which report 0009 subsequently questioned. Some of the 29 may be completed schedules rather than budget ends; r14 and r15 are two such cases. All 29 remain **UNRESOLVED**. The figure is a count of recorded reason strings, not a count of runs that a larger budget would decide.

The archived rows are **not** re-split here. Doing so would require re-planning the 29 evaluations, which is not authorized.

## 3. Rule from report 0011

`SkillResult` carries a new field, `termination`, which records the explicit end event. The status and `reason` are unchanged, so V1 results and hashes are unchanged.

| `termination` | Meaning |
|---|---|
| `START_STATE_NOT_CLEAR` | the start configuration is not clear |
| `PICK_SCREEN_EXHAUSTED`, `PLACE_SCREEN_EXHAUSTED` | no grasp of the declared family passes the pose-only screen |
| `SEARCH_LIMIT_PLAN_FAILURES` | the failure allowance ended the search (a real search limit) |
| `SCHEDULE_COMPLETED_NO_WITNESS` | the declared enumeration finished below the allowance without a witness |
| `SCHEDULE_COMPLETED_ALL_CERTIFIED_BLOCKED` | the enumeration finished and every pair was certified blocked (status CERTIFIED_INFEASIBLE, as before) |
| `WITNESS_RECHECKED`, `WITNESS_REPLAY_REJECTED` | a record was assembled and its independent re-check passed or failed |

`ordered.normalized_reason` maps these events to V2 reasons:
- It splits `SCHEDULE_COMPLETED_NO_WITNESS` into `_WITH_UNRESOLVED_CONNECTORS` and `_UNCERTIFIED_REJECTIONS`.
- It appends `+WALL_LIMIT_INVOLVED` whenever any connector query hit the per-query wall cap.
- CPU and wall **censoring** is a separate, runner-level stop status (`CPU_CENSORED`, `WALL_CENSORED`) recorded in the collection ledger.

None of these is a negative label. Only an independent, scope-matching certificate establishes a negative.

**Demonstration.** `tests/test_g4d_corrections.py::test_completed_schedule_is_not_reported_as_a_search_limit` replays the archived g4a_r14 all-stay evaluation. The historical reason is `PLANNER_BUDGET`; the termination event is `SCHEDULE_COMPLETED_NO_WITNESS`.
