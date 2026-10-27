# 0098 — P17-D2: retrospective re-analysis of all 48 P16 D roots and prospective D evaluation

**Actual result**
- **Retrospective, `P17_REANALYSIS_OF_P16_ROOTS`, 48 / 48 roots, all 11 guides including the oracle.** This closes P16's 21 / 48 coverage gap.
  - Dp17 solves 39 / 48 and geometry 38 / 48 (2 : 1, UNDERPOWERED).
  - The oracle solves 27 of the 33 roots where it is defined; the learned guides and geometry solve 28.
- **Prospective, p17test D roster, 90 / 90 roots, 10 guides plus the oracle on 56.**
  - Dp17 solves 70 / 90 and geometry 67 / 90 (4 : 1, p = 0.375, UNDERPOWERED).
  - The simplest orderings (geometry-norec, Dp17-norec, Dp16-norec) solve the most, 71 / 90.
- **No guide differs from geometry** (Holm p = 1.0 everywhere). Knowing the true blocker union (oracle) does not help either.
- **Verdict on learned guidance:** no demonstrated search advantage on either cohort.
- **The D original-target classifier is informative.** Dp17 reaches AUROC 0.952 and blocker F1 0.89 (31 masks).

## 1. Prospective (`runs/p17/eval/P17_PROSPECTIVE.json` → `d`; figure `visualizations/p17/d/P17_D_prospective.png`)

All guides use the same action domain (0–4 relocations, freed sources, repeats ≤ 2 per object), the same budgets (400 / 6 / 16 / 8, node cap 500), the same certifier and independent replay.

| guide | solved (replay CLEAR) | proven optimum (moves[+travel]) | best within budget | no plan found | mean nodes | mean motion checks | virtual CPU / root |
|---|---|---|---|---|---|---|---|
| **Dp17** (production) | **70** | 48 | 22 | 20 | 25.7 | 151.5 | 436 s |
| Dp17-norec | 71 | 49 | 22 | 19 | 22.7 | 148.0 | 422 s |
| Dp17-blk (experimental) | 70 | 48 | 22 | 20 | 25.7 | 151.5 | 428 s |
| Dp16 | 68 | 46 | 22 | 22 | 29.1 | 152.2 | 446 s |
| Dp16-norec | 71 | 48 | 23 | 19 | 22.6 | 150.8 | 442 s |
| Dp | 68 | 46 | 22 | 22 | 28.8 | 151.2 | 422 s |
| D (paired) | 68 | 46 | 22 | 22 | 28.9 | 148.3 | 425 s |
| **geometry** | **67** | 45 | 22 | 23 | 26.6 | 152.3 | 402 s |
| geometry-norec | 71 | 49 | 22 | 19 | 21.6 | 145.9 | 373 s |
| uniform | 66 | 48 | 18 | 24 | 22.2 | 157.1 | 378 s |
| oracle (56 defined roots) | 48 / 56 | — | — | — | — | — | — |

- **Paired tests vs geometry:**
  - Dp17: 4 : 1, UNDERPOWERED.
  - D / Dp / Dp16: each 2 : 1, UNDERPOWERED.
  - The no-recursion variants: 5 : 1, Holm p = 1.0.
  - uniform: 4 : 5.
- **Oracle subset** (56 roots): every learned guide and geometry solve 48, the norec variants 49, the oracle 48, uniform 47.
- **Strata:**
  - NATURAL (12): 11 / 12 for every guide.
  - CONSTRUCTED (78): 55 (uniform) to 60 (norec variants); Dp17 59, geometry 56.
- **Plan quality and limits:**
  - Against proven optima there are 0 extra moves for every guide, with one exception each for Dp16-norec and uniform.
  - No node-cap hits.
  - The first expanded move differs from geometry on 34 roots, with no outcome effect.
- **Unsolved roots:** 19–24 per guide end in `NO_PLAN_FOUND` (budget-censored, not proven infeasible). REACH roots dominate this group.

## 2. Retrospective (`runs/p17/eval/P17_RETROSPECTIVE.json`; figure `visualizations/p17/d/P17_D_retrospective.png`; 51.4 CPU-h)

| guide | Dp17 | Dp17-norec / -blk | Dp16 | Dp16-norec | Dp | D | geometry | geometry-norec | uniform | oracle |
|---|---|---|---|---|---|---|---|---|---|---|
| solved / 48 | 39 | 39 / 39 | 38 | 39 | 39 | 38 | 38 | 40 | 39 | 27 / 33 defined |

- **Roots:** the same 48 roots P16 pre-registered (24 DENSE plus 24 grammar roots), labelled `P17_REANALYSIS_OF_P16_ROOTS`.
- **Oracle:** from P16's unsealed parking-lattice labels.
- **Primary contrast, Dp17 vs geometry:** 2 : 1, p = 1.0, UNDERPOWERED.
- **Search effort:** mean nodes are lower for the learned guides (38–42) than for geometry (47), but the no-recursion and uniform orderings are cheaper still (34–36).
- **Plan quality:** 0 extra moves against every proven optimum.

## 3. D as a classifier (`d.offline`; 140 decided originals, 75 feasible; no D family trained on p17test)

| family | AUROC | Brier | feasible / infeasible recall | blocker F1 PARKING (31 masks) / MULTI (39) | exact union PARKING / MULTI |
|---|---|---|---|---|---|
| D (paired) | 0.947 | 0.138 | 0.69 / 0.95 | 0.879 / 0.831 | 0.65 / 0.59 |
| Dp | 0.939 | 0.121 | 0.76 / 0.91 | 0.899 / 0.869 | 0.71 / 0.67 |
| Dp16 | 0.936 | 0.106 | 0.85 / 0.85 | 0.889 / 0.855 | 0.71 / 0.64 |
| Dp17 | 0.952 | 0.106 | 0.79 / 0.92 | 0.893 / 0.846 | 0.71 / 0.64 |

- **Lattice types on the D roster** (parking protocol):

| FEASIBLE_ORIGINAL | MINIMAL_SETS | INCOMPLETE | UNKNOWN_ORIGINAL | NO_CLEARING |
|---|---|---|---|---|
| 27 | 22 | 18 | 16 | 7 |

- **Classifier vs search:** the classifier signal is real but does not turn into search gains. Under the shared corrected search, the plan is found by exhaustive iterative deepening whatever the expansion order, so reordering affects only which budget-limited branches are reached first.
- **Temporary-target blocker marginals:** unvalidated (6 masks, 0095). Recursion is therefore feasibility-only, and `-blk` performs exactly like Dp17 (70 / 90).

## 4. Matched operational comparison with A / B / C (`matched`; 90 D-roster roots, all four approaches executed)

Operational convention: feasible means the original is VERIFIED; everything else counts as infeasible (27 feasible, 63 infeasible).

| approach | blockage detected | false alarms | blockage resolved |
|---|---|---|---|
| A (retrained A) | 58 / 63 | 15 / 27 | 26 / 63 |
| B (LB) | 59 / 63 | 17 / 27 | 29 / 63 |
| C (P13:K-C) | 49 / 63 | 11 / 27 | 22 / 63 |
| D (Dp17: learned p_feasible < 0.5; search plan ≥ 1 move + replay) | 54 / 63 | 6 / 27 | 43 / 63 |

- **Definitions:**
  - A–C: "detected" means any non-EMPTY choice; "resolved" means a verified non-empty repair.
  - D: "detected" comes from D's own learned original-target feasibility, not the planner.
- **D's resolution comes mostly from the search:** geometry-ordered search alone resolves 40 / 63, and D resolves 43 / 63. So most of D's advantage over A–C is the search itself.
- **D's false-alarm advantage is learned:** 6 / 27 against 11–17 / 27 for A–C, from the D feasibility classifier.
- **Search plans and labels agree:** no D plan with 0 moves occurred on an operationally infeasible root, so the label budget and the search budget did not conflict.

## 5. D correctness (D-CORRECT) and verdict

**Verified and tested:**
- dominance with the last mover in the key (exhaustive reference);
- finite-graph claim semantics;
- independent replay of every plan;
- per-family calibration with no foreign calibration file;
- the multi-destination label protocol;
- union ≠ necessary, and no zero mask for NO_CLEARING / INCOMPLETE;
- arbitrary target rebinding;
- oracle scope (non-deployable, defined only for MINIMAL_SETS / feasible lattices);
- the DENSE cohort and the oracle both completed.

**Not closed:** the contract's mechanism gate M7 (repeat necessity with a finite-domain proof) is PARTIAL — witness yes, proof blocked on the 8 roots listed in 0093 §2.

**Verdict:** **METHOD_D_2D_COMPLETE is not granted: D is PARTIAL / BLOCKED on M7 only.** The scientific result is negative or underpowered: learned guidance is no better than geometric ordering.
