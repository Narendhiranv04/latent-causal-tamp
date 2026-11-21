# G1: versioned long-horizon 2D teacher (BXY_X_TEACHER_V2_LONG / BXY_Y_TEACHER_V2_LONG)

**Code:** `teacher_long.py`. The frozen files are untouched: bxy_teacher c18ac91c89b9, p16_motion 43f4c38c6418, p15_search 9c2af1373798.
- **Up to 6 relocations:** dispatched to the frozen `x_query` / `y_query`, unchanged.
- **7 to 12 relocations:** the same frozen code path, with two substitutions for that one call only:
  - **Eligibility:** the 7-action cap is raised to 13 actions (12 relocations plus the target). Every other rule is kept: only movable objects, never the target, no object moved twice, legal destinations only.
  - **Physics:** `LongPhysics(DetPhysics)` uses the identical budget dict, so `str(budget)` and every planner RNG key are unchanged. Only the accounting of `online_moves` differs: 8 per relocation, with an explicit total cap of 96.
- **Unchanged:** geometry, collision checks, the 48 grasp candidates, skill planner node budgets, certificates, carried robot state, the single terminal connector (`transit_plans` = 6), `replay_x` / `replay_y`, and Y = `bd_2d.t_goal` from q_ref.

**Why this preserves the frozen semantics:** with `idx=None` there is no edge library. Each relocation calls `_take("online_moves")` exactly once. Every one of the 11,244 verified cached queries used exactly *len(seq)* online moves. So for ≤ 8 relocations the shared budget never binds, and the long teacher computes the frozen result.

## Parity gate (girish, frozen environment; `parity_long.py`; `G1_LONG_PARITY_run1.json`, `G1_LONG_PARITY_P34.json`)

| Check | Result |
|---|---|
| **P1: K ≤ 6 dispatch.** The 46 G0 parity queries (cached girish results with witness ids), plus every recorded prefix and final query of the 16 certified engineering roots (K4–6). | **250/250 identical**: x, status, phase, witness ids where cached, y and Y status. |
| **P2: 7–8 relocations.** The long teacher vs the frozen `x_query` with only the eligibility cap lifted. | **12/12 identical**: x, status, phase, every relocation witness id, connector id, replay. |
| **P3: 9 and 12 relocations,** synthetic layouts (objects in columns 3–7, TRAIN-prior parking). | Two layouts give **X = 1 at both 9 and 12 relocations, independently replayed, with the connector ending at q_ref**. The frozen path is **censored at relocation 8** (UNKNOWN_BUDGET) on exactly those sequences. The first 6 relocation witnesses equal the frozen 6-prefix query in 6/6 comparable cases. Where planning fails earlier (relocation 0, 1 or 6), the long and frozen results are identical. Long Y is evaluated on 9- and 12-object endpoints, with the version tag `BXY_Y_TEACHER_V2_LONG`. |
| **P4: explicit exhaustion.** `total_cap = 3` on an 8-relocation sequence. | x = 0, **UNKNOWN_BUDGET at relocation:3**, never a success. The second test sequence failed planning at relocation 0, before the cap applied. |

**Verdict: G1 PASS.**
- Budget-limited outcomes stay labelled UNKNOWN_BUDGET or UNKNOWN_PLANNER, with the failed phase.
- They are never treated as infeasibility.
- They are never counted as a certificate.

## Certificate grammar audit (G0/G1)

**What `cert.py` (MINK_STATIC_V1) assumes:**
- deletion relaxation over moved-object sets, in any order;
- each object moved at most once (this matches `eligible`);
- the target is never a corrective move;
- destinations exclude the goal and q_ref-blocking cells. A disc left in either makes Y or X fail, so no X = 1 / Y = 1 repair uses them.

**The gap:** V1 also excluded *initially occupied* destinations. The teacher would allow parking in a vacated cell, so for the teacher's full grammar V1 is not sound.

**The fix:** `MINK_STATIC_V2` (`dest_mode='any_legal'`) ignores occupancy for destinations, which is a sound over-approximation for the full grammar.

**Acceptance:** requires witness length = K_lb(V2) = K_lb(V1).

**The 16 engineering roots:** V1 = V2 = witness length for all 16.

`masks_fast` replaces the quadratic antichain computation and is identical to `masks`: 0/720 mismatches on random layouts, about 125× faster.
