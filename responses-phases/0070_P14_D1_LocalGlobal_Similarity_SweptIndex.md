# 0070 — P14-D1: local / global similarity index over witnessed swept motions

**Actual result.**
- **Gate:** `runs/p14/P14_D1_GATE.json` → **PASS**.
- **What it is:** a deterministic, non-learned two-level index (`p14_sweep_index.Index`, `lookup_candidates`) over 4,838 real witnesses, with hard compatibility filters, local and global similarity, and multimodal swept-volume clustering.
- **Retrieval is never a feasibility decision:** each candidate is certified in the current hypothetical scene (with a certified transit) before use.
- **Tests:** 8 / 8 in `tests/test_p14.py`.

## 1. Entry schema (one per witnessed relocation)

| field group | contents |
|---|---|
| ids and provenance | file, record index, root, query, seed / arm, source (teacher / episode), split, family, `support_id` = root |
| motion | absolute `src`, `dst`, relative Δ(row, col), object radius / kind, `held_local` (grasp offset), `q_start`, `q_end`, measured travel (`ordered.joint_travel`) |
| local descriptor | categorical 3 × 3 window centred on source and destination; 4 × 4 window anchored with the cell at local (1, 1). Codes: free 0, object 1, target 2, goal 3, moving object 4, off-board −1 |
| global descriptor | 64-cell categorical occupancy |
| swept | conservative per-phase swept cells (0069 §4) |

**Index version:** `P14_SWEEP_INDEX_V1`; hash `sha256:4c29bbd3…`.

## 2. Retrieval

1. **Hard filters, before any similarity:**
   - same absolute source and destination (fixed-base arm);
   - same object footprint (radius);
   - the start configuration is handled by the certified transit.
2. **Similarity:**
   - local = mean agreement of the four windows;
   - global = 64-cell agreement;
   - combined = local + 0.25 × global (weight fixed on DEV before any evaluation);
   - local-only and global-only are evaluated as ablations.
3. **Motion modes:** greedy clustering by whole-path swept-cell IoU ≥ 0.6. Modes are ranked by (independent supporting roots, best similarity, minimum travel), never by raw record count. Candidates are returned mode by mode, so the best-supported mode is tried first, but **every mode is kept**.
4. **Never used:** intersection or "common overlap" volumes.
5. **Screen only:** `screen_hits` (swept cells currently occupied) is reported but not decisive.
6. **Empty compatible pool:** `UNKNOWN_NO_COMPATIBLE_WITNESS`, never infeasible.

## 3. Library structure (`MODE_STATS.json`)

| statistic | value |
|---|---|
| keys | 278 |
| motion modes | **805** |
| median modes per key | 2 |
| keys with ≥ 2 distinct modes | **185** |
| modes supported by ≥ 2 independent roots | **344** |
| duplicate inflation (records per independent root) | 4.49 |

**Coverage on the D3 evaluation roots** (candidate source → destination pairs of movable objects: four nearest annulus-safe free slots plus the root's catalogue destinations): **166 / 276 (60.1 %)** have at least one compatible witness. The remaining 40 % need the online-planner fallback or are UNKNOWN.

## 4. Required retrieval tests (`tests/test_p14.py`)

| case | result |
|---|---|
| identical Δ at a different absolute source | **no candidate (UNKNOWN)**: fixed-base hard filter |
| incorrect object footprint | rejected (`footprint`), UNKNOWN |
| no match | `UNKNOWN_NO_COMPATIBLE_WITNESS` (not infeasible) |
| duplicate inflation (5 records from one root vs 3 independent roots) | the 3-root mode ranks first |
| frequent mode vs rare mode | frequent first, **all modes returned**; `modal_only=True` returns only the top mode, losing the rare one |
| swept link-body collision despite end-effector clearance | a real witness, CLEAR in its own scene, gets **COLLISION** from the exact certifier once an obstacle sits on a pregrasp-swept cell ≥ 3 cells from source and destination |
| different start configuration | handled by the certified transit (exercised in every D2 / D3 move) |

**Not separately implemented, by design:** translation / rotation invariance of trajectories. It is invalid for this fixed-base robot, and the test above shows the retrieval refuses it.

## 5. Novelty discipline

Similarity-indexed experience retrieval, local environment descriptors and trajectory reuse are established ideas (experience graphs, FIRE-style retrieval, experience-driven trees). P14 claims no novelty for the lookup. The only learned component under test is D's blocker guidance (0072).
