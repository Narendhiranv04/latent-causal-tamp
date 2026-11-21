# Experiment F: the K>6 physical-teacher restriction

| | |
|---|---|
| Scope | A diagnostic trace of the frozen finalized teachers exactly as the K≤3 ablation and V3.4 benchmark call them, through `benchmark.teach` → `evaluate._verify_job`. |
| Code read | `teacher2d.py`, `abf/teacher2d_wt/{bxy_teacher,bd_core,p15_search,p16_motion}.py`, `dataset-bd/bd_2d.py`, and `final3d_v4/code/fin3d.py` (+ its `bd_core`) on gvlab2. |
| Not touched | The scaling-dataset workspace. Nothing was modified or re-run there, and **no teacher file was changed**. |
| Evidence | The call paths below, plus the existing verifier cache (`budget_spent` of 11,244 verified 2D X queries). |

## 1. The real call paths

**2D: X(q).** The `teacher2d.query(rec, seq, cache, "X")` path:
- **Eligibility check:** `bxy_teacher.x_query` → `eligible(rec, seq)` → `bd_core.check_sequence(seq)`, which raises when `len(seq) + 1 > MAX_ACTIONS (= 7)`.
  - On a raise, the query is returned as `attempted: False`, `teacher_status: INELIGIBLE`, `y: None`.
  - **It is never attempted and is not a label.** `benchmark.cache_labels` then yields `None`, which the evaluator reports as UNKNOWN.
- **Budget:** one `p16_motion.DetPhysics(task_of(k, rec), None, budget=dict(bd_2d.QB))` is created per query and shared by all relocations and the connector.
  - `QB = {motion_checks: 150, online_moves: 8, goal_plans: 3, transit_plans: 6}`.
  - `idx = None` means no edge library, so every relocation edge calls `_take("online_moves")` once (`p15_search` l.203).
  - Exhaustion returns `U_BUD`, i.e. **x = 0, with a budget-limited negative kind**. Under the frozen binary contract this is a 0, not a missing value.
- **Connector:** one terminal `_transit` per query (`transit_plans` shared).
- **Replay:** `replay_x` re-certifies every relocation record and the connector. It has no length limit.

**2D: Y(S^q).** `y_query` also calls `eligible(rec, seq)` for every non-empty `seq`. **An endpoint that edits more than 6 objects is also INELIGIBLE.** The planning itself, `bd_2d.t_goal`, uses its own `QB` (goal_plans 3).

**3D.**
- **X:** `fin3d.run_x` calls `bd_core.check_sequence(steps)` explicitly (same `MAX_ACTIONS = 7`). The `ValueError` is caught by `capped`, giving `resolution: UNRESOLVED_ERROR`. `cache_labels` keeps only `EVALUATED`, so the outcome is UNKNOWN.
- **Y:** `run_y` has no length check.
- **Cap and planning:** each sequence runs under a 3,600 s administrative wall cap (`UNRESOLVED_ADMIN`). Per-relocation planning uses `bd_3dt.query` with the record's `budget` (RRT 5,000 iterations).

## 2. What limits K>6

| Limit | 2D | 3D | Kind |
|---|---|---|---|
| `check_sequence` (≤ 6 relocations + target) | X **and** Y INELIGIBLE for > 6 | X UNRESOLVED_ERROR for > 6 | **Interface restriction.** No physics is attempted. |
| Shared per-query `online_moves = 8` | Relocation 9+ is budget-censored (x = 0, `UNKNOWN_BUDGET`). Verified in the cache: **every** verified relocation used exactly one online move (len 1/2/3 → 1/2/3 moves; 1,088 / 2,604 / 7,552 queries). | — (per-relocation planner budgets) | **Budget restriction.** The labels would be 0, not missing. |
| Shared `transit_plans = 6` | Only the terminal connector uses it inside X (0 or 1 per verified query in the cache). | — | Not binding for K ≤ 12. |
| Wall cap 3,600 s per sequence | — | Long sequences may become UNRESOLVED_ADMIN | Administrative (missing, never 0) |
| RNG keying | The planner seed = `stable_hash(parts + [str(self.budget), …])` (`p15_search._key`) | — | **Any change to the budget dict changes every planner seed, so K≤6 labels would not reproduce.** |

**Answer to "interface, physics or both".**
- **K = 9 and K = 12 cannot be queried at all** by the frozen teachers: interface restriction, in both domains.
- **Lifting only `MAX_ACTIONS` would still not work in 2D for K ≥ 9:** the shared 8-move budget turns relocation 9 into a budget-limited 0, whatever the geometry.
- **Physical planning difficulty is a third, separate factor.** For K = 4–6, which the interface admits, the scaling campaign reported most witness attempts failing at `relocation:0` with UNKNOWN_PLANNER in dense layouts. That observation comes from the scaling campaign's own reports and was not re-examined here.

## 3. The smallest safe extension (specification only; not implemented)

A separately versioned **`BXY_X_TEACHER_V2_LONG` / `BXY_Y_TEACHER_V2_LONG`** wrapper. The frozen files stay unmodified.

**1. Dispatch by length.**
- For `len(seq) ≤ 6`, call the frozen `x_query` / `y_query` **unchanged**. This gives byte-identical results, including RNG keys.
- Only for `len(seq) > 6`, run the extended path.

**2. Extended path.**
- **Eligibility:** the same checks as `eligible()`, with `MAX_ACTIONS_LONG` = K_max + 1, applied to both X and Y.
- **Budget:** keep `QB` as the *dict* (so `str(budget)` and every RNG key stay identical). Give the online-move counter a per-relocation allowance of 8 through a `_take` override, plus a declared, versioned total cap.
  - For example, charge `online_moves` per relocation and reset it at each relocation boundary. Keep `motion_checks` / `transit_plans` per relocation as well.
  - Record the allowance in the teacher-version string and in every row.
- **Unchanged parts:** the connector, `replay_x` and `y_query` stay as they are. Y semantics are unchanged: the target is planned from q_ref in the edited endpoint.

**3. 3D.**
- Bypass `check_sequence` only inside a versioned `run_x_long`.
- Keep the per-relocation planner budgets and the 3,600 s wall cap; declare whether the cap scales with K.
- An admin cap must remain UNRESOLVED, never 0.

**4. Acceptance gates before any K > 6 label is used.**
- (a) **Exact K ≤ 6 regression parity:** at least 500 cached 2D and 3D queries across K1–K6, with identical x/y, status, phase and witness ids.
- (b) **A prefix-monotonicity sanity check:** a long X = 1 implies that the same prefix verified under the frozen teacher, where that prefix has ≤ 6 relocations.
- (c) **A budget-sensitivity report:** the share of long-sequence zeros that are `UNKNOWN_BUDGET`. These must be reported as budget-limited, never as infeasible.
- (d) **No silent relaxation:** the same scene contract, collision checker, ε/δ, replay and connector.

The physical definitions of X and Y are unchanged. Only the eligibility horizon and the *accounting* of the online-move budget change, and both are declared.

## 4. Consequence for the paper

- Any claim about K > 6 needs this versioned extension and its gates.
- With the frozen teachers, K = 9/12 strata must be reported as **BLOCKED by the teacher interface**, not as physically infeasible.
- K ≤ 6 strata are verifiable, but their zeros include budget-limited outcomes, as at K ≤ 3.
