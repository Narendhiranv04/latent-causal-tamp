# 0091 — P17-1: physical search and sequence-verification correctness

**Actual result**
- **Search dominance defect: fixed and demonstrated.**
  - P16's search failed to find an existing plan on 2 / 2,000 random finite graphs (seeds 115 and 1563) and on a designed counterexample.
  - The corrected P17 search matches an **exhaustive reference** on all 2,000 random graphs plus 122 test graphs.
- **Greedy sequence verifier replaced** by an existential fixed-sequence verifier, with **9 real 2D counterexamples**: greedy UNKNOWN, existential VERIFIED, under an identical provider and budget, and every one replays CLEAR.
- **Erratum on P16 labels.** 46 of 72 re-checked P16 "CERTIFIED_INFEASIBLE at target" sequence labels rested on a q-dependent certificate; under correct scope they are UNKNOWN.
- **Gate:** `runs/p17/P17_1_GATE.json`.
- **Code:** `p17_search.py`, `p17_verify.py`, `tests/test_p17.py` (P16 modules untouched).

## 1. Search state and dominance (`p17_search.py`)

**SearchState** = (object cells, robot q, last moved object [the no-consecutive-repeat rule is active], per-object move counts, depth).

**Equivalence key** = (sorted occupancy, **exact** q bytes, last).
- The gripper is open and free between actions, so attachment never belongs to a search state.
- Exact q bytes replace P16's 12-decimal rounding, so no distinct configuration is merged (test).

**Dominance within a key:** an entry dominates when it has travel ≤ J **and** counts ≤ counts elementwise. That means at least as many remaining moves per object, at least as much remaining depth, and the same last object; so the future legal action set is a superset at no greater cost.

**Defect.** P16's key omitted `last`. A cheaper path ending with object X could prune a dearer path ending with Y, although only the latter may move X next.
- **Designed counterexample** (`test_last_mover_dominance_counterexample`): P16 finds no plan; P17 finds B, A, B (travel 4.0).
- **Random evidence:** 2,000 graphs with one q value (forced collisions). P16 misses an existing 3-move plan on seeds 115 and 1563; P17 has 0 mismatches against `exhaustive()`, which enumerates every legal sequence and every verified mode with no pruning.

**Claims:**
- `MIN_MOVES…` requires every shallower pass fully enumerated with all applicable edges and goals decided; `MIN_TRAVEL…` adds the same at the found depth.
- New claim `NO_PLAN_IN_FULLY_ADJUDICATED_FINITE_GRAPH` is used only when every pass is complete and decided. Otherwise `NO_PLAN_FOUND` (test: an UNKNOWN edge blocks the proof).

## 2. Existential fixed-sequence verifier (`p17_verify.verify_existential`)

- **Fixed ordered action list.** The ordered (object, destination) list is held fixed. Each step branches over **every certified motion alternative** (library modes with distinct terminal q, direct or planned transits, online fallback), each with its own successor q and measured travel, through the target action.
- **VERIFIED:** some branch completes.
  - Full mode returns the minimum-travel branch, flagged `travel_minimal_over_alternatives` only if no branch is undecided and no edge reported unexplored modes.
  - `first=True` stops at the first verified branch (explored cheapest-first); it is used for labels and execution, and the witness is flagged not proven travel-minimal.
- **CERTIFIED_INFEASIBLE only from motion-independent certificates.** Occupancy at step i is fixed by the sequence, so a pose-only certificate (destination occupied / STATIC_ENDPOINT_INVALID / ORDER_FIRST_ACTION / TARGET_PICK / GOAL_OVERLAP / FIRST_MOVER) refutes every realization.
  - **LINK0_SECTOR_PICK is q-dependent.** It refutes only the branch whose q it was computed at; that branch's failure is UNKNOWN (test `test_certificate_scope_q_dependent_vs_q_independent`).
- **Otherwise UNKNOWN_<reason>**, with per-branch provenance. No motion ever means UNKNOWN, never negative (test).
- **Frozen baseline:** `verify_sequence_greedy_P16` (P16's cheapest-mode-per-step verifier).

### Physical counterexamples (`runs/p17/shared/GREEDY_VS_EXIST_*.json`)

- **Source:** all 289 P16 development sequences whose greedy verification failed after a successful first step, re-verified (75 roots).
- **Rescan outcome:**

| P16 greedy | P17 existential | sequences |
|---|---|---|
| UNKNOWN | **VERIFIED** | 17 |
| CERTIFIED (q-dependent sector) | **UNKNOWN** (correct scope) | 46 |
| UNKNOWN | UNKNOWN | 119 |
| CERTIFIED (q-independent) | CERTIFIED | 25 |

- **Controlled test.** Each of the 17 flips was re-verified with greedy then existential on **one fresh provider with an identical budget**:
  - **9** are greedy-UNKNOWN / existential-VERIFIED with independent replay CLEAR;
  - in the other 8, the larger P17 budget alone explains the flip, so they are not counted.
- **Canonical example:** `calib|p13_2026231012`, sequence `o00>36`. Greedy takes the cheapest library mode for o00, and the target action from its terminal q is unresolved. Existential takes **library mode 2** (a different terminal q), and the target action certifies. Its replay and GIF are in 0093.

## 3. Determinism and cache

- **Mechanism unchanged.** P16's deterministic provider and shared exact cache are reused unchanged (node budgets; no CPU / wall adjudication; seeds a pure function of the query). Under P17 the cache key also covers the planner profile.
- **P17 repeat test:** 3 representative roots (dense, repeat, slot conflict) × 5 repeats with different `PYTHONHASHSEED`, under parallel load (`runs/p17/shared/DET_P17_*.json`). Reported in the gate.

## 4. Status and budget declarations (frozen)

| item | values |
|---|---|
| P17_SEQ_BUDGET_V1 (per sequence) | 150 motion checks, 4 online moves, 6 target plans, 4 transit plans |
| D search budget (per guide) | 400 / 6 / 16 / 8 |
| node cap | 500 |
| per-object moves | ≤ 2, never consecutive |
| moves | ≤ 4 |
| planner profile | `P16_FAST` |

Larger budgets would be a new protocol version run for all arms.
