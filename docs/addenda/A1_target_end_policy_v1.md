# Addendum A1 — Target completion and end-state policy (version 1)

**Status:** in force for new `INITIAL_SCENE_ONE_SHOT_V1` queries from G4A (report 0008).
**Refines:** Methodology Specification v1.5 §2.2–2.3 and §9 ("the target planner plans the complete skill and checks goal achievement"), and Implementation Guide v1.7 §3 (action context).
**Does not modify:** the PDFs, report 0007, or any G3.5 record. G3.5 queries keep their HOME-constrained scope (`final_connector = "HOME"`; their action-context hashes are unchanged).

## 1. Definition

For a supported-transport action with active target *t* and unique goal pose *g* (tolerance τ_g), a target attempt from the achieved post-repair state *S* has four separately recorded fields:

| Field | Meaning |
|---|---|
| `goal_achieved` | The recorded release places *t* within τ_g of *g*, and the record certifies clear up to and including the release. |
| `safe_retreat_status` | The certified record continues through the declared straight retreat, ending with the gripper open, the target detached and every body clear of every object, the placed target and the support. The record starts exactly at *S*'s joints and gripper gap. |
| `home_return_status` | **Optional diagnostic.** A separately planned and separately certified connector from the retreat end to the designated HOME configuration, with the target placed. |
| `complete_target_status` | `VERIFIED_FEASIBLE` iff `goal_achieved` and `safe_retreat_status` are both verified. HOME is **not** a prerequisite. |

## 2. Rules

1. Primary success for the transport task is `complete_target_status = VERIFIED_FEASIBLE`.
2. A HOME diagnostic failure or unknown never erases a through-retreat witness. A through-retreat failure is never rescued by any HOME result.
3. The witness must be an independently re-certified, complete record from *S* to the retreat end. Success is never inferred by truncating an incomplete or rejected planning record.
4. The end policy is part of the action context and its hash: `end_policy = "SAFE_RETREAT"`, `home_return = "OPTIONAL_DIAGNOSTIC"`, `contract_addendum = <this file>`.
5. Comparisons with the G3.5 HOME-constrained scope use separately identified evaluations on cloned, bit-identical states. They are labelled `HOME_REQUIRED (G3.5 scope)`.

## 3. Implementation

- `evaluate.evaluate_safe_retreat` runs the skill with `q_goal=None` (the record ends after the retreat), re-certifies the record and checks its start, last phase, final gap and goal distance.
- `evaluate.home_diagnostic` plans the optional HOME connector (direct, then RRT-Connect, with the same planner caps).
- `data.action_context(..., end_policy="SAFE_RETREAT")` defines the action-context fields.
