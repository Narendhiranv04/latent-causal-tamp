# 0078 — P15-5: D-guided rearrangement benchmark and anytime performance

**Actual result**

| item | status |
|---|---|
| retrospective benchmark | 6 arms × 24 roots, complete |
| prospective benchmark | 6 arms × 32 roots, complete; preregistered, labels sealed until after deployable arms |
| D vs geometry, retrospective | **UNDERPOWERED** (exploratory): 16 vs 16, 1 / 1 discordant |
| D vs geometry, prospective (confirmatory) | **UNDERPOWERED**: 27 vs 27, **0 discordant**, p = 1.0, CI [0, 0] |
| gate | `runs/p15/P15_5_GATE.json` → **PASS (executed)**; primary hypothesis UNDERPOWERED |

- **Equivalence is not established.** At the frozen budget, every deployable guidance arm solves exactly the same roots.
- **Frozen protocol:** `P15_PREREG.json` (pushed `a747e79`) plus `P15_PREREG_AMENDMENT_1.json` (`8a1bf8e` / `554c40f`). The amendment fixed a guide-independent budget-truncation defect and lowered the per-root soft cap to 150 s, before any valid outcome.
- **Label custody:** prospective labels were hash-committed in `df823f9` before `UNSEALED` was written.
- **Data:**
  - per-root records: `runs/p15/search/{RETRO,PROSP}_{arm}.json`;
  - paired statistics: `runs/p15/eval/{RETRO,PROSP}_SUMMARY.json`;
  - voided pre-amendment outputs: `runs/p15/search/void_v1/`.

## 1. Fair setup (identical for every arm)

- **Inputs:** same initial scene, catalogue movers (move-once), ≤ 6 slots per object, ≤ 3 relocations, the same index v2 (4,821 witnesses, combined ranking, no threshold), the same online planner and the same sound certificates.
- **Counts:** budget 400 motion checks / 6 online moves / 16 goal plans per root.
- **CPU:** 150 s soft cap per root, checked between adjudications. One planner call can overrun it: 101 of the 408 P15 root-searches exceeded 160 s, with a maximum of 601 s. Every arm is affected.
- **Accounting:** D inference is counted inside each root's CPU and inside the anytime clock.
- **Strict success:** a plan is found **and** independent re-certification of every transit, relocation and the final target record returns CLEAR. Replay failures: **0** in every arm.

## 2. Retrospective: the 24 P14 roster roots (P15 algorithm; exploratory, not blind)

| arm | solved | min-moves proven | min-moves + min-travel proven | NO_PLAN | capped | motion / online / goal calls per root | nodes | CPU mean / median | D calls / D CPU per root |
|---|---|---|---|---|---|---|---|---|---|
| **D** | **16** | 16 | 8 | 8 | 11 | 143.3 / 3.8 / 3.7 | 20.0 | 116.8 / 100.6 | 11.5 / 1.71 s |
| D-norec | 16 | 16 | 8 | 8 | 12 | 135.9 / 3.8 / 3.8 | 19.3 | 124.2 / 107.5 | 4.1 / 0.67 s |
| D-pairless | 17 | 17 | 8 | 7 | 12 | 137.3 / 3.8 / 3.9 | 17.9 | 126.1 / 117.3 | 9.4 / 1.41 s |
| **geometry** | **16** | 15 | 8 | 8 | 11 | 161.8 / 4.0 / 4.2 | 22.9 | 108.1 / 85.7 | — |
| uniform | 18 | 17 | 8 | 6 | 10 | 153.3 / 3.8 / 4.7 | 21.0 | 112.1 / 83.7 | — |
| oracle (non-deployable) | 18 | 17 | 8 | 6 | 10 | 153.3 / 3.8 / 4.7 | 21.0 | 112.1 / 84.0 | — |

**Paired against geometry** (exact sign test; root-bootstrap 95 % CI on the success difference):

| comparison | wins / losses | diff | 95 % CI | p | status |
|---|---|---|---|---|---|
| D | 1 / 1 | 0.000 | [−0.125, +0.125] | 1.0 | UNDERPOWERED |
| D-norec | 1 / 1 | 0.000 | — | 1.0 | UNDERPOWERED |
| D-pairless | 2 / 1 | +0.042 | [−0.083, +0.167] | 1.0 | UNDERPOWERED |
| uniform | 2 / 0 | +0.083 | [0, +0.208] | 0.5 | UNDERPOWERED |
| oracle | 2 / 0 | +0.083 | — | 0.5 | UNDERPOWERED |

**Change from P14's six-root evidence** (same roots, changed semantics):

| | 003 | 006 | 012 | 015 | 021 | 024 | total |
|---|---|---|---|---|---|---|---|
| P14 D | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | 4 / 6 |
| P14 geometry | ✗ | ✓ | ✗ | ✓ | ✗ | ✓ | 3 / 6 |
| **P15 D** | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | **4 / 6** |
| **P15 geometry** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | **5 / 6** |

P14's apparent D advantage (4 vs 3) **does not survive** the corrected search. Tri-state statuses, per-resource budgets and multimodal edges let geometry solve 003 and 012.

## 3. Prospective: 32 new preregistered roots (confirmatory)

- **Roster:** 24 mechanism-conditioned roots (4 each of PC_SG, PR_SIDES, PN_SIMP, PN_GIMP, ORD_CHAIN, OMIT_OPT) plus 8 NAT.
- **Labels:** all 32 originals decided (28 infeasible, 4 feasible NAT controls); complete blocker masks on 27 roots; 128 teacher queries at 3,324 CPU-s.

| arm | solved | min-moves proven | + min-travel | BEST_VERIFIED | NO_PLAN | capped | motion / online / goal calls | CPU mean / median | D calls / D CPU |
|---|---|---|---|---|---|---|---|---|---|
| **D** | **27** | 20 | 8 | 7 | 5 | 9 | 138.5 / 3.9 / 4.2 | 105.4 / 65.4 | 9.3 / 1.38 s |
| D-norec | 27 | 20 | 8 | 7 | 5 | 9 | 138.5 / 3.9 / 4.2 | 105.2 / 64.5 | 3.6 / 0.57 s |
| D-pairless | 27 | 20 | 7 | 7 | 5 | 9 | 130.2 / 3.9 / 4.6 | 108.9 / 67.6 | 9.5 / 1.40 s |
| **geometry** | **27** | 20 | 8 | 7 | 5 | 9 | 140.8 / 3.9 / 4.2 | 106.8 / 63.7 | — |
| uniform | 27 | 20 | 8 | 7 | 5 | 9 | 133.0 / 3.9 / 4.3 | 104.6 / 62.4 | — |
| oracle (non-deployable) | 28 | 20 | 8 | 8 | 4 | 8 | 140.8 / 3.9 / 4.3 | 87.4 / 53.7 | — |

**Primary result: D vs geometry.**
- **0 discordant roots.** Difference 0.000, CI [0, 0], p = 1.0. **UNDERPOWERED**: there are no informative pairs, and that is not evidence of equivalence.
- Neither preregistered minimum effect is met:
  - success: +10 pp required, observed 0 pp;
  - motion calls: ≥ 20 % fewer required, observed 1.7 % fewer (138.5 vs 140.8).
- **Secondary:**
  - D-norec, D-pairless and uniform each have 0 discordant roots against geometry;
  - oracle is 1 / 0 (PROSP 052, OMIT_OPT).

## 4. Equal-CPU anytime success (D inference included)

| CPU-s per root | 10 | 25 | 50 | 100 | 200 | final |
|---|---|---|---|---|---|---|
| RETRO D | 11 | 12 | 14 | 15 | 16 | 16 |
| RETRO geometry | 11 | 12 | 15 | 15 | 16 | 16 |
| RETRO uniform | 11 | 12 | 16 | 17 | 18 | 18 |
| PROSP D | 15 | 20 | 22 | 24 | 26 | 27 |
| PROSP geometry | 15 | 20 | 22 | 24 | 25 | 27 |
| PROSP uniform | 13 | 19 | 23 | 24 | 25 | 27 |

The anytime curves overlap at every allowance; see `visualizations/p15/P15_{RETRO,PROSP}_benchmark.png`. D inference is 0.5–1.5 % of per-root CPU, so it is never the reason for a difference.

## 5. Search-level quantities (the contract's §4 readout)

**Tri-state outcomes:**
- **UNKNOWN never counted as infeasible.** Per arm and cohort, UNKNOWN adjudications number 326–546: UNKNOWN_BUDGET edges 276–500, plus UNKNOWN_PLANNER, plus goal UNKNOWN.
- **Sound certificates:** 237–383 CERTIFIED_INFEASIBLE edges and goals per arm-cohort.
- **Distinct terminal-q alternatives kept** per arm-cohort: 121–169.
- **Branch-and-bound / dominance prunes:** 34–77.

**Proof coverage** (within the declared finite graph only; never a global continuous optimum):

| cohort | min-moves proven | min-moves + min-travel |
|---|---|---|
| RETRO | 15–17 / 24 | 8 / 24 |
| PROSP | 20 / 32 | 7–8 / 32 |

**Extra moves against proven optima:** **0** on every root with a proof (RETRO 15–17, PROSP 20), in every arm.

**`moves_outside_original_blocker_union`** (renamed metric; scored with labels only after unsealing):
- **RETRO:** 0 on all 14–16 scoreable found plans per arm.
- **PROSP:** 0 on 24–25 found plans, and **2** on one root (051, OMIT_OPT). There, the teacher's parking-lattice edits verified **no** clearing subset (mask [0, 0]), while the search cleared the target with non-lattice destinations (o01→59, o00→20). The union metric is destination-specific; this is **not** an extra move against an optimum.
- **Erratum:** the per-root stored field in `run_arm` built the union without the mask bits, so it read 0 for every plan. The summaries recompute it from labels; the stored field is superseded and the code is fixed.

**Co-solved plan quality:**

| cohort | co-solved roots | moves (D / geometry) | travel (D / geometry) |
|---|---|---|---|
| RETRO | 15 | 1.00 / 1.00 | 1.527 / 1.459 |
| PROSP | 27 | 1.22 / 1.22 | 2.411 / 2.445 |

## 6. Cases: D better / D worse / tie (only certified recorded motion is drawn)

| case | root | outcome | reason (from the run log) | figure |
|---|---|---|---|---|
| **D better** | RETRO 009 (OMIT_OPT) | D 2 moves at 62.6 s, MIN_MOVES proven; geometry no plan | Guidance really changed expansion order: D ranked o00 0.9999 and o01 0.89, while geometry put o01 at 0.00. Geometry spent all 400 motion checks on 162 UNKNOWN_BUDGET edges before reaching the plan. | `P15_RETRO_case_009.png`, `.gif` |
| **D worse** | RETRO 003 (PC_SG) | D no plan (capped, 323 s); geometry 2 moves at 33 s | D's order front-loaded edges whose library candidates failed. They fell back to online planning: 5 online calls, 2 UNKNOWN_PLANNER, consuming CPU before a cheap lookup plan was reached. | `P15_RETRO_case_003.png`, `_geometry.gif` |
| tie, different destinations | PROSP 053 (OMIT_OPT) | both 2 moves (benchmark: D o01→21, travel 4.55; geometry o01→52, travel 5.64) | Different first destination after a different first-object ordering | `P15_PROSP_case_053.png` (**re-run plans; see note**) |

**Reproducibility note.**
- **Retrospective cases:** both re-runs (003, 009) reproduced the benchmark plans exactly, for both guides.
- **Prospective 053:** the D re-run differed from the benchmark (online o01→53, travel 5.14), and geometry repeated its steps with a different travel (5.39). The online planner has a **wall-clock cut** (recorded `wall_clock_dependent` in the planner), so its outcomes can vary with machine load.
- **What the figure shows:** the 053 re-run plans, each replay-CLEAR, not the benchmark records. `P15_PROSP_case_053.json` carries `matches_benchmark: false` for D.
- **Fairness:** all benchmark arms ran concurrently under the same load. The two retrospective D-vs-geometry discordances (009, 003) each reproduced on re-run.

**Failure taxonomy (unsolved by every arm: RETRO 005, 018, 019, 021, NAT 001, NAT 006; PROSP 022, 030, 043, 104).**
- **Motion-check budget exhausted:** 400 checks spent and all remaining edges UNKNOWN_BUDGET (RETRO 019, NAT 006).
- **Expensive online-planner failures reaching the CPU cap:** UNKNOWN_PLANNER after only 0–172 motion checks (RETRO 005, 021; PROSP 022, 030, 043, 104).
- **Certified-infeasible goals plus budget:** RETRO 018.
- **Mixed:** RETRO NAT 001, with 12 UNKNOWN_PLANNER and the online budget spent.
- **Never claimed:** no failure is reported as physical infeasibility.

## 7. Verdicts

| question | verdict |
|---|---|
| D guidance increases strict physical success over geometry (prospective, primary) | **UNDERPOWERED** (0 / 32 informative pairs; no effect observed) |
| D reduces planner calls ≥ 20 % at non-inferior success | **NEGATIVE** (−1.7 % prospective, −11 % retrospective motion checks with the same success) |
| D recursion matters | **NOT SUPPORTED** (D ≡ D-norec on success in both cohorts) |
| P14's six-root D advantage | **NOT REPRODUCED** under corrected semantics (P15: D 4 / 6, geometry 5 / 6) |
| search soundness (replay, UNKNOWN handling, proofs) | **SUPPORTED** (0 replay failures; claims only within the declared finite graph) |
