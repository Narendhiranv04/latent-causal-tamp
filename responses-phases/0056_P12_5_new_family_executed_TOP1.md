# 0056 — P12-5: strict TOP1 execution on the novel holdout

**Actual result.**
- **Gate:** `runs/p12/P12_5_GATE.json` → **PARTIAL**.
- **Coverage:** 280 of 452 distinct physical episodes ran before the 12,000 CPU-s execution cap (11,902 used). **49 of 80 roots** are fully executed for every arm.
  - The coverage set is fixed by the frozen job order, never by outcomes.
  - 45 of the 49 have at least one VERIFIED catalogue repair.
- **Finding: B's executed advantage from P10 does not generalize to the new families,** and a simple analytic geometry proposer beats every learned arm.

## 1. Results (49 fully executed roots; seed mean per root; abstain = failure)

| arm | success (all 49) | success (45 witness-exists) | X family | Y family | CPU / root incl. abstain | relocation plans / root | moves on success |
|---|---|---|---|---|---|---|---|
| **geometry-only TOP1** | **0.796** | **0.867** | 0.640 | 0.958 | 39.3 | 1.45 | 1.72 |
| keyed B | 0.633 | 0.659 | 0.587 | 0.681 | 32.1 | 1.27 | 1.72 |
| A | 0.626 | 0.659 | 0.587 | 0.667 | 29.2 | 1.15 | 1.62 |
| SF | 0.565 | 0.593 | 0.547 | 0.583 | 25.2 | 0.99 | 1.52 |
| keyed C | 0.558 | 0.607 | 0.333 | 0.792 | 29.7 | 1.38 | 1.78 |
| *G+M (planner-assisted, ≤ 5 candidates)* | *0.571* | *0.600* | *0.200* | *0.958* | *25.2 (+ pose-screen ranking)* | *0.90* | *1.00* |

**Paired contrasts (all 49 roots):**

| contrast | difference | 95 % CI | roots a / b better | sign p |
|---|---|---|---|---|
| B − A | +0.007 | [−0.068, 0.082] | 11 / 9 | 0.82 |
| B − SF | +0.068 | [−0.007, 0.143] | 13 / 8 | 0.38 |
| C − B | −0.075 | [−0.170, 0.020] | — | 0.28 |
| B − geometry | **−0.163** | [−0.265, −0.054] | 5 / 22 | **0.0015** |
| B − G+M | +0.061 | [−0.082, 0.218] | — | 1.0 |

**Outcome classes for B** (147 arm × seed choices on the 49 roots): 93 SUCCESS, 13 ABSTAIN, 18 CENSORED, 14 TARGET_CERTIFIED_INFEASIBLE, 8 NO_REPAIR_WITNESS, 1 TARGET_UNRESOLVED.

**Reading.**
- **Easy-repair structure.** On these prescreened-hard but mostly 1-move-repairable scenes, the analytic geometry rule (cover the grasp-adjacent and sweep-occluding movers with the shortest repair) is the best selector.
- **Learned arms.** B, A, SF and C are statistically indistinguishable from each other.
- **G+M** fails badly on the X sweep family (0.20). Its pose screens do not anticipate the link-0 sweep after relocation.
- **No cost-advantage claim** is made: the means are protocol-mismatched, and censoring varies.

**Disclosures:**
- The per-batch execution caps were set too low (censored episodes cost up to 180 CPU-s). The remaining budget was used for an ordered continuation: it completed 3 partial roots first, then roots in frozen order. The removed `NOT_RUN_BUDGET` placeholders, which had no physical attempt, are logged in `runs/p12/p12_5/continuation_removed_placeholders.json`.
- One killed launch ran for less than 1 minute without a guard record.

**Artifacts:**
- `runs/p12/p12_5/EXEC_JOBS.json`
- `runs/p12/p12_5/EXEC_RESULTS.json`
- per-batch ledgers
- `visualizations/p12/P12_executed_TOP1.png`
- `visualizations/p12/P12_executed_success.gif` (recorded episode)
