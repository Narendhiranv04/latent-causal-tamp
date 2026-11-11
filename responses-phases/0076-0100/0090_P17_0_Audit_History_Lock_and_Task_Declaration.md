# 0090 — P17-0: audit, history lock and task declaration (2D only)

**Actual result**
- **Start:** `bd9a2e88ff1dbd390616f7a42179c14f69d6780a` (P16 final). Local HEAD equalled origin/main.
- **User modifications left untouched:** the two root PDFs deleted by the user, and the untracked `instruction-phase-md/0045_*`.
- **Historical lock:** `runs/p17/audit/HISTORICAL_MANIFEST.json` records the git blob ids of **50,557** tracked files under `runs/p10…p16`, `visualizations/` and reports 0022–0089 + decision documents. Dirty tracked historical files: **0**. `p17_eval.verify_historical()` returns `[]` and is re-checked at every gate.
- **Historical regression:** **474 / 474** tests (457 historical + 17 P16) and **6 / 6** archived replays (`runs/p17/regression0/`).
- **Scope:** **2D only.** No 3D code, simulator, experiment or new 3D documentation; the P16 3D specification is historical context.
- **Gate:** `runs/p17/P17_0_GATE.json` → **PASS**.

## 1. Declared task (shared by B and D)

**Input (runtime, scene-only; deletion-tested):**
- the initial scene;
- target `t0` and goal cell;
- robot start q;
- declared fixed structures.

**Output:**
- a decision of zero moves, or
- an ordered list of relocations (object, destination) whose every motion is certified, followed by the certified target pick-and-place, all independently replayed.

**Objective:** lexicographic (relocations, measured joint travel including every transit and the target action). There is no risk term.

**Statuses:** VERIFIED; scoped CERTIFIED_INFEASIBLE; STATIC_INVALID; UNKNOWN_<reason>. UNKNOWN is never a negative.

## 2. The two methods (declarations)

| | B (lean) | D (pairless) |
|---|---|---|
| learned | P(y_q = 1) for every keyed physical query (empty repair, parked-subset scenes, ordered repairs 1–4) via scene / no-op and order-sensitive repair unaries; exact product of Bernoullis (LB). LB+G adds only the generic scene–repair coupling | P(target feasible) and conditional pairless blocker-union Bernoullis on a declared pool; conditional vs feasibility-gated marginals kept distinct |
| not learned | order / destination / motion generation; physical certification | everything in search: movers, order, destinations, motion modes, transits, repeats |
| decision | calibrated no-op-first rule over scene-only candidates, then existential physical verification | reorder-only guidance of the corrected finite search |
| controls | LB-W (parameter-matched), LB-F2, LC, A, SF, full keyed B retrained on the same data, frozen P13 arms, ALWAYS_EMPTY, random, geometry selector, VERIFY_FIRST | frozen paired D, frozen Dp, P16 Dp16, P17 Dp17, ± recursion, geometry ± recursion, uniform, oracle |

## 3. Verdict lock (preserved; not re-litigated)

**B:**
- **keep:** DINOv2 + projection, keyed identities, scene / no-op unaries, F2, empty repair, analytic static check;
- **remove:** learned F1, F3, F4, combined F5, J;
- **defer:** F5q;
- **LB+G:** an experimental replication arm (P16: 0.652 vs 0.509, one cohort);
- **P16 facts:** LB+G did not beat ALWAYS_EMPTY (0.652 vs 0.643), and the no-op gain was confounded by data and architecture.

**D:**
- pairless default and paired comparator only;
- union ≠ necessary;
- NO_CLEARING / INCOMPLETE / NON_MONOTONE / UNKNOWN masked;
- no demonstrated guide advantage (P15 27 / 32 each; P16 21 / 21 each, DENSE 4 / 24);
- recursion validated for feasibility only.

**Shared:** deterministic node-budgeted planner, multimodal certified library, alternate transit, scene-only candidates, finite-graph claims only.

## 4. Errata recorded in P17 (no historical file changed)

1. `p16_common.search` omits the last-moved object from its dominance key (0091).
2. `p16_common.verify_sequence` is greedy over motion modes (0091).
3. P16 sequence labels "CERTIFIED_INFEASIBLE at target" that rested on the **q-dependent** LINK0_SECTOR_PICK certificate, computed at the greedy branch's terminal q, are only scoped to that motion realization. 46 of 72 such re-checked labels are UNKNOWN under the correct scope (0091).
4. `p16_d.Guide` used one P15 temporary-target calibration for every D family (0095).
