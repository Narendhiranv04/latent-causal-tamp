# 0076 — P15-3: tri-state, multimodal, finite-graph lexicographic search

**Actual result.**
- **Gate:** `runs/p15/P15_3_GATE.json` → **PASS**.
- **Code:** `p15_search.py` replaces P14's search for P15 runs. P14's search is untouched, for its own replay.
- **Tests:** algorithm invariants are tested on synthetic providers (11 / 11; these are **not** physical evidence). Physical behaviour was checked on a 6-root DEV pilot with independent replay.

## 1. Statuses (no bare `None`)

| status | meaning | edge source | goal source |
|---|---|---|---|
| `VERIFIED` | continuous-collision-certified witness in the current state | library witness + certified transit, or online planner | online planner target pick-and-place |
| `CERTIFIED_INFEASIBLE` | sound, scoped certificate (kind recorded) | `ORDER_FIRST_ACTION` for that move | `TARGET_PICK` / `LINK0_SECTOR_PICK` / … for the target from this q |
| `STATIC_INVALID` | this destination only | destination occupied, or `STATIC_ENDPOINT_INVALID` | — |
| `UNKNOWN_PLANNER` | finite planner did not find a witness | online fallback | goal planner |
| `UNKNOWN_BUDGET` | budget exhausted | any | any |
| `UNKNOWN_NO_LIBRARY_WITNESS` / `UNKNOWN_TRANSIT` | lookup outcome before fallback (recorded in edge meta) | lookup | — |

The planner's own `INFEASIBLE` result is **never** promoted to CERTIFIED (it is a finite-search protocol). Only checker-accepted certificates are.

## 2. State, edges, objective

**State:** every object's cell (fixed bodies included), the robot q (open, free), and the moved set.

**Edges:**
- the provider returns **all** certified library modes with **distinct terminal q** (up to `K_MODES = 3`), each with its own transit, travel and resulting q′;
- the online witness is used only if no mode certifies;
- each certified mode is a separate edge, and the search keeps every alternative.

**Action domain** (declared, identical for every guide):
- movers = catalogue movers (`CATALOGUE_RESTRICTED`);
- move-once;
- ≤ 6 slots per object (the 4 nearest annulus-safe free cells plus indexed destinations);
- ≤ 3 relocations.

This is a restricted finite graph. Test 9 shows that a plan needing an object moved twice is correctly **excluded**.

**Objective:** lexmin (relocations, J), with J = `ordered.joint_travel` over transits, relocations and the final target record. There is no risk term.

**Algorithm:**
- iterative deepening over the move count;
- inside a depth, DFS in guidance order with travel branch-and-bound (J ≥ 0), plus exact-state dominance (same occupancy, same q to 1e-12, same moved set);
- the zero-move goal is always tested first.

**Fairness and memoization:**
- planner seeds are hashes of (state, q, object, destination, budget, robot), with no method or counter dependence;
- memo keys include object identity (test 8);
- results censored by the budget are never reused as decided.

**Completeness flags, per depth:**
- `search_enumeration_complete`: no budget truncation during that pass;
- `all_decided`: every edge and goal in that pass was `VERIFIED` / `CERTIFIED_INFEASIBLE` / `STATIC_INVALID`.

**Claims:**

| claim | requires |
|---|---|
| `MIN_MOVES_WITHIN_FULLY_ADJUDICATED_FINITE_GRAPH` | both flags at every shallower depth |
| `MIN_MOVES_AND_MIN_TRAVEL_…` | additionally both flags at the found depth |
| `BEST_VERIFIED_WITHIN_BUDGET` | otherwise |

No claim ever refers to global continuous-space optimality.

## 3. Adversarial tests (`tests/test_p15.py`; synthetic providers)

| # | case | result |
|---|---|---|
| 1 | already-feasible original | 0 moves, no edge evaluated, both proofs |
| 2 | two certified modes, the frequent one longer | the cheaper (1.5) chosen |
| 3 | shorter immediate mode with a bad terminal q | the better whole plan (2.0) wins, min-travel proven |
| 4 | popular mode collides, rare mode valid | physical, not synthetic: 53 real cases in the transfer benchmark (0075) |
| 5 | UNKNOWN shorter edges + VERIFIED longer plan | 2-move plan returned, `BEST_VERIFIED_WITHIN_BUDGET`, no min-moves claim |
| 6 | UNKNOWN zero-move goal + verified 1-move plan | plan valid, zero-move optimality not proven |
| 7 | A on slot 5 blocks B → 5; A's freed cell 1 is offered | pass |
| 8 | memo keys distinguish object identities | pass |
| 9 | a plan needing a second move of one object | `NO_PLAN_FOUND` under move-once (declared restriction) |
| 10 | the same state reached at two costs | the cheaper kept (dominance / B&B) |
| 11 | reversed guidance on an exhaustive graph | identical plan and travel |
| 12 | deterministic re-run | identical outputs |

## 4. DEV pilot (6 DEV roots × 5 guides; budget 120 / 6 / 16)

- **Outcomes identical across all guides:**
  - 3 / 6 solved, each with a **MIN_MOVES_AND_MIN_TRAVEL** claim: one 0-move feasible original, two 1-move plans; all replay CLEAR;
  - 3 / 6 unsolved: the 120 motion checks were spent certifying library candidates for depth-1 edges before any 2-move plan was reached.
- **Cost:** 16–157 CPU-s per root (≈ 273 CPU-s per guide for 6 roots).
- **Decision for the frozen benchmark:** motion-check budget raised to 400 (online 6, goal 16), with a CPU safety cap of 400 s per root.

## 5. Metric erratum

- `unnecessary_moves` is renamed **`moves_outside_original_blocker_union`**.
- True **extra moves vs optimum** are computed only where a min-moves claim is proven. Otherwise UNKNOWN.

## 6. Addendum: PREREG amendment 1 (before any valid outcome)

**Defect.** `Physics._take` set the search-wide truncation flag as soon as **any** single budget ran out, for example the 6 online moves. The search then stopped with motion checks and goal plans still left: p13_2026180012 stopped at 59 / 400 checks. The defect was guide-independent.

**Fix:**
- An exhausted motion-check or online budget now makes only the affected edge `UNKNOWN_BUDGET`.
- A partially adjudicated lookup adds `UNKNOWN_BUDGET` beside its certified modes, so `all_decided` stays false.
- The search stops only at the CPU cap or when goal plans run out.
- Tests 13 and 14 cover the fix.
- Run outputs from before the fix are kept under `runs/p15/search/void_v1/`.

**Per-root CPU cap: 400 → 150 s (soft).** The cap is checked between adjudications, so one planner call can overrun it.

The amendment is in `runs/p15/P15_PREREG_AMENDMENT_1.json`, pushed in `8a1bf8e` / `554c40f`. The test count is now 19.
