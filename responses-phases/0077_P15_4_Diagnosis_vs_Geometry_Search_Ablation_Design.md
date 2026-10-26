# 0077 — P15-4: design of the diagnosis-vs-geometry search comparison (frozen before outcomes)

**Frozen:** `runs/p15/P15_PREREG.json` (sha256:0f35c237…), pushed **before** any benchmark outcome or prospective label.

## 1. Guides (reorder-only; identical graph, index, provider, budget)

| guide | definition |
|---|---|
| **D** | frozen P13 D (λ_B 1.0, 3 seeds) on the **rebuilt current state** (0074). Recursion: an object whose DEV-recalibrated temporary-target feasibility to its first candidate slot is < 0.5 is deferred |
| D-norec | D without recursion |
| D-pairless | frozen D-pairless (λ_B 2.0), same recursion policy |
| geometry | analytic heuristic on the updated positions, plus geometry recursion. The zero-move-first test is common to every arm, so `Geometry_same_gate` equals geometry here |
| uniform | catalogue order |
| oracle | teacher **original** blocker union only (non-deployable); no recursion; does not know destinations or order |

D inference CPU and call counts are recorded per root and included in every CPU comparison.

## 2. Two fairness regimes

1. **Identical counts:** the same motion-check, online-plan and goal-plan budgets (400 / 6 / 16), the same action domain and the same 400 s CPU cap per root.
2. **Equal CPU, including D inference:** anytime curves built from the CPU time at which each arm first found or improved a plan (the `anytime` log), compared at common CPU allowances.

**Guidance can matter only when the budget truncates the search.** On exhaustively adjudicated finite graphs, every sound ordering returns the same optimum (test 11).

## 3. Cohorts

| cohort | roots | status |
|---|---|---|
| P14 primary roster | 24 | **retrospective / exploratory**: 6 roots already had P14 outcomes. Re-run under the corrected P15 algorithm; never confirmation |
| new prospective cohort | 32 (24 mechanism-conditioned: 4 each of PC_SG, PR_SIDES, PN_SIMP, PN_GIMP, ORD_CHAIN, OMIT_OPT; 8 NAT unconditioned) | **confirmatory**. New seeds 2026200000+, built before any outcome, 0 index overlap by root or fingerprint. Labels limited to the original task + lattice edits (oracle / union metric), sealed and hash-committed before unsealing |

## 4. Primary hypothesis and power

- **Primary:** paired strict physical success (plan found **and** independent replay CLEAR; UNKNOWN or budget counted as unsuccessful but stratified), D vs geometry.
  - Test: exact two-sided sign test, α = 0.05, with a root bootstrap CI.
  - Minimal meaningful effect: +10 pp success, or ≥ 20 % fewer planner calls at non-inferior success.
- **Power** (exact sign test):
  - significance needs ≥ 6 discordant roots, all favouring one arm (6 / 0, p = 0.031);
  - 10 discordant roots at an 80 % win rate gives power 0.38.
  - Fewer than 6 informative pairs means **UNDERPOWERED**. Non-significance is not equivalence.
- **Secondary:** equal-CPU anytime success, calls, nodes, proof coverage, cost on co-solved roots, unknown counts, `moves_outside_original_blocker_union`, extra moves only versus proven optima.
- **Stopping:** no adaptive stopping. Roots run in a fixed order, and a resource stop is reported as incomplete coverage.

## 5. Cost forecast (DEV pilot)

- **Measured:** 16–157 CPU-s per root at the 120-check budget; at the 400-check budget, about 100 CPU-s per root-arm is expected.
- **Retrospective:** 6 arms × 24 roots ≈ 14 k, under the 27 k cap.
- **Prospective:** 6 arms × 32 roots ≈ 19 k plus ≈ 3 k teacher labels, under the 38 k cap.
- **Hard cap per root:** 400 CPU-s.
