# P15 decision: D-guided rearrangement, similarity-indexed motion alternatives and B calibration

**Status:** PARTIAL (a complete audit; the primary hypothesis is UNDERPOWERED).
**Base:** P14 `cbd5d9b`. **Prereg:** `a747e79` + amendment 1 (`8a1bf8e`, `554c40f`). **Label manifest:** `df823f9`.
**Manifest:** `runs/p15/P15_FINAL_MANIFEST.json`.

## Verdicts

| claim | verdict | evidence |
|---|---|---|
| D's arbitrary-target interface (raw) is physically valid | **NEGATIVE** | feasible recall 0.169 (original states) / 0.352 (intermediate states) — 0074 |
| D's interface after DEV-only recalibration | **SUPPORTED (cross-validated)** | balanced accuracy 0.924 [0.871, 0.989], 157 decided probes, 36 roots — 0074 |
| D-guided search beats geometry: prospective primary | **UNDERPOWERED** | 27 / 32 vs 27 / 32, 0 discordant, p = 1.0 — 0078 |
| D-guided search beats geometry: retrospective | **UNDERPOWERED** | 16 / 24 vs 16 / 24, 1 / 1 discordant — 0078 |
| D reduces planner calls ≥ 20 % | **NEGATIVE** | −1.7 % prospective, −11 % retrospective — 0078 |
| recursive D adds over non-recursive D | **NOT SUPPORTED** | identical success in both cohorts — 0078 |
| P14's six-root D advantage | **NOT REPRODUCED** | P15: D 4 / 6, geometry 5 / 6 — 0078 |
| multimodal motion modes matter (rare modes, travel) | **SUPPORTED** | 53 rare-mode rescues; first−best travel 0.159; representatives +18 % travel — 0075 / 0079 |
| similarity threshold safe to deploy | **NEGATIVE** | −11.6 % of available TEST motions — 0075 |
| lookup vs online-only | **UNDERPOWERED** | 10 vs 8 of 12 — 0079 |
| tri-state search soundness | **SUPPORTED** | 0 replay failures in 408 root-searches; UNKNOWN never counted as infeasible; claims restricted to the finite graph — 0076 / 0078 |
| extra moves against proven optima | **0 in every arm** | RETRO 15–17, PROSP 20 roots with proofs |
| B extra factors contribute under fair admission | **NEGATIVE** | ranking ≈ for F3 / F4 / F5; differences are admission effects — 0080 |
| B zero-move on feasible originals | **NEGATIVE** | K-B picks empty on 0.543 of feasible originals — 0080 |
| validation-only T + b calibration | **NEGATIVE** | test NLL worse in 25 / 36 (arm, seed) cases — 0080 |
| lean-B retrain, generic-only F5, optional D retrain, wider catalogue | **NOT_TESTED** | by contract or gate |

## Recommendation

1. **Stop investing in D as a search guide in 2D** at these budgets. Even the oracle's blocker knowledge buys only +1 / 32.
2. **Keep the P15 search stack** (tri-state, multimodal lookup, label custody) as the baseline.
3. **Before any 3D phase:** make the online planner deterministic, cut its per-call cost, and raise index coverage.
4. **P16 (B zero-move confirmation)** is optional, costed at ≈ 31.5 k CPU-s, and preregisterable (`runs/p15/B/P16_PROPOSAL.json`).
5. **3D: not authorized and not recommended** on the present evidence.
