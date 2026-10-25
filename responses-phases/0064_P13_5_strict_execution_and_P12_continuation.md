# 0064 — P13-5: strict TOP1 execution on the P13 blind sets and the completed P12 continuation

**Actual result.**
- **Gate:** `runs/p13/P13_5_GATE.json` → **PASS**.
- **P13 execution coverage:** all **129 / 129** executable blind roots (81 challenge, 48 natural) were fully executed, using the frozen choices and the frozen permutation order. **428 / 428** distinct episodes ran: 295 SUCCESS, 34 censored, 51 relocation not executable, 28 target certified infeasible after the repair, 13 target unresolved.
- **Budget:** execution 10,698 / 22,000 CPU-s, of which 768 went to building the frozen job list (G+M rankings).
- **One continuation:** worker 2 had the most jobs and reached its 2,594 CPU-s share with 7 never-attempted jobs at the tail of its frozen order. Their placeholders were logged (`continuation_w2_removed.json`) and the same order resumed (26 CPU-s).
- **The 40 prediction-only roots** (PC_SERIAL and the triples) have no executable candidate and are not part of execution.

## 1. P13 strict TOP1 (seed-mean success per root; abstain = failure)

| arm | all 129 | challenge (81) | natural (48) | moves on success | CPU / root | abstentions (of 387 choices) |
|---|---|---|---|---|---|---|
| **keyed B** | **0.734** | **0.835** | 0.562 | 1.42 | 17.2 | 64 |
| B-F3pm | 0.708 | 0.757 | **0.625** | 1.34 | 18.2 | 64 |
| geometry-only | 0.612 | 0.605 | **0.625** | 1.49 | 22.6 | 0 |
| C | 0.579 | 0.621 | 0.507 | 1.18 | 12.8 | 127 |
| A | 0.558 | 0.638 | 0.424 | 1.42 | 12.8 | 147 |
| B-F4 | 0.525 | 0.568 | 0.451 | 1.19 | 12.1 | 153 |
| B-F5spm | 0.483 | 0.473 | 0.500 | 1.11 | 8.9 | 178 |
| SF | 0.318 | 0.333 | 0.292 | 1.01 | 5.2 | 253 |
| B-F2 | 0.313 | 0.296 | 0.340 | 0.67 | 3.1 | 255 |
| *G+M (planner-assisted, ≤ 5 candidates)* | *0.783* | *0.864* | *0.646* | *1.24* | *22.3* | *—* |

**Paired contrasts** (Δ = B − other; root bootstrap CI; sign test):

| contrast | all 129 | challenge 81 | natural 48 |
|---|---|---|---|
| B − A | **+0.176** [0.142, 0.209] | +0.198 | **+0.139** [0.076, 0.201] |
| B − SF | **+0.416** [0.344, 0.488] | +0.502 | **+0.271** |
| B − C | **+0.155** [0.111, 0.204] | +0.214 | +0.056 (n.s.) |
| B − geometry | +0.121 [0.047, 0.199] (p 0.08) | **+0.230** (p 1e-4) | −0.063 (n.s.) |
| B − B-F2 | **+0.421** [0.344, 0.504] | +0.539 | **+0.222** (p 0.011) |
| B − B-F4 | **+0.209** [0.168, 0.256] | +0.267 | **+0.111** (p 0.007) |
| B − B-F5spm | **+0.251** [0.196, 0.307] | +0.362 | +0.063 (n.s.) |
| B − B-F3pm | +0.026 [−0.016, 0.067] (n.s.) | **+0.078** (p 0.011) | −0.062 (n.s.) |
| B − G+M | −0.049 [−0.111, 0.005] (n.s.) | −0.029 (n.s.) | −0.083 (n.s.) |

**Reversed-order roots** (ORD_CHAIN / OMIT_OPT, 27 roots):

| contrast | Δ | sign-test split |
|---|---|---|
| B − B-F2 | **+0.679** | 19 / 0 |
| B − geometry | +0.679 | 19 / 0 (geometry leaves a necessary obstacle or picks the wrong first move) |
| B − A | +0.185 | — |
| B − C | +0.148 | — |

**Failure attribution** (from the episode outcome and the teacher label of the chosen query):

| arm | wrong original feasibility (chose a certified-infeasible empty repair) | other certified-infeasible choices | target certified infeasible | target unresolved | planner censoring | relocation not executable |
|---|---|---|---|---|---|---|
| B | 4 | 2 | 6 | 6 | 20 | 1 |
| geometry | — | **31**: 21 necessary obstacle left in place (TARGET_PICK, OMIT_OPT / ORD_CHAIN), 7 wrong first move (FIRST_MOVER), 3 remaining sweep barrier (LINK0_SECTOR_PICK) | 5 | 1 | 11 | 2 |

- **Abstention is the dominant failure of the ablations and baselines:** B-F2 255, SF 253, B-F5spm 178, B-F4 153, A 147, against 64 for B.
- **Part of the deployment effect of F4 and F5 is therefore an admission effect.** These arms assign lower probability to feasible repairs, so fewer candidates clear their validation-calibrated thresholds. Executed success is the preregistered deployment metric and counts abstention as failure.

## 2. P12 continuation (supplementary; never P13 confirmation; `P12_FINAL80.json`)

**What ran:** the frozen P12 jobs for the 31 untouched roots, in frozen order with identical episode identity and protocol. That is 172 episodes and 3,539 / 9,000 CPU-s, written under `runs/p13/p12_continuation` (P12 files untouched).

**Coverage:** all **80** roots now have every episode attempted; 66 have no censored episode.

| arm (P12 frozen models) | all 80 (unresolved = failure) | X_SWEEP_GATE | Y_BOTTLENECK | CPU / success |
|---|---|---|---|---|
| geometry-only | **0.838** | 0.700 | 0.975 | 41.0 |
| keyed B | 0.629 | 0.567 | 0.692 | 43.9 |
| A | 0.596 | 0.567 | 0.625 | 37.4 |
| C | 0.546 | 0.358 | 0.733 | 42.6 |
| SF | 0.512 | 0.492 | 0.533 | 45.5 |
| *G+M* | *0.600* | *0.225* | *0.975* | *34.8* |

**Contrasts on 80 roots:**

| contrast | Δ | 95 % CI | p | reading |
|---|---|---|---|---|
| B − SF | **+0.117** | [0.054, 0.183] | 0.008 | was +0.068, n.s., on 49 roots |
| B − A | +0.033 | [−0.037, 0.104] | 0.42 | n.s. |
| B − geometry | **−0.208** | [−0.292, −0.125] | < 1e-4 | geometry better |
| B − G+M | +0.029 | — | 0.58 | n.s. |

**Final P12 reading:** on P12's novel families, B beats SF but not A, and geometry is better than every learned model. 0056's PARTIAL conclusion is unchanged in direction.

**Figures:**
- `visualizations/p13/P13_executed_TOP1.png` (success and cost vs success);
- `P13_executed_success.gif` (one recorded multi-move strict-TOP1 success; recorded trajectory only).
