# P3 physical verification (VAL EVAL: development evidence, not an independent test)

**Protocol.** `P3_PREREG.md` (`3783c57bc5`). Predictions and the query manifest were sealed and pushed (`2d8969d057`, `P3_SEAL.json`) before any teacher call.

## Teacher run

| Item | Value |
|---|---|
| Authorization | owner, 2026-11-23: ≤ 1,200 queries, ≤ 24 CPU-h, gvlab2 |
| Host / harness | gvlab2. Unchanged ablation harness (`benchmark.teach` → `evaluate._verify_job`, k3abl env and code, read-only). New cache and `V3OUT` under `naren_workspace/full_domain_sets` |
| Workers | 32 (16 of 48 cores free) |
| New queries | **1,018** (cap 1,200) on 178 roots. All 191 K1/K2 roots are covered for every primary and secondary arm. 953 sealed REPAIR picks were already in exact-contract caches and were not re-queried |
| Teacher CPU | **3.80 h** (cap 24); maximum per root 1,468 s; wall about 12 min |
| Retries | none. No 3D, K3 or protected-cohort query |
| New-query statuses | X: VERIFIED 724, CERTIFIED_INFEASIBLE 157, UNKNOWN_PLANNER 90, UNKNOWN_TRANSIT 47. Y: VERIFIED 753, CERTIFIED_INFEASIBLE 92, UNKNOWN_PLANNER 173 |

## K1+K2 verified success (191 roots; seed-0 sealed picks)

**Strict** is the registered primary: a value counts only under VERIFIED / CERTIFIED_*, and UNKNOWN is unresolved. **Operational** is the frozen `v32b_phys` rule, under which UNKNOWN with value 0 is a failure, shown for parity with the completed study.

| Arm | Strict, decided rate | Strict UNKNOWN | Strict ITT bounds | Operational |
|---|---|---|---|---|
| **EXACT4** | 120/148 = 81.1 % | 43 (22.5 %) | [62.8, 85.3] | 120/191 = 62.8 % |
| EXACT6 | 120/153 = 78.4 % | 38 | [62.8, 82.7] | 62.8 % |
| EXACT_FULL (offline model optimum) | 109/149 = 73.2 % | 42 | [57.1, 79.1] | 57.1 % |
| RAND_FULL @1024 | 89/138 = 64.5 % | 53 | [46.6, 74.3] | 46.6 % |
| BEAM_SEEDED4 @1024 | 120/155 = 77.4 % | 36 | [62.8, 81.7] | 62.8 % |
| BEAM_FULL @1024 | 121/153 = 79.1 % | 38 | [63.4, 83.3] | 63.4 % |
| **PW_MCTS_SEEDED4 @1024** | 123/153 = **80.4 %** | 38 (19.9 %) | [64.4, 84.3] | **64.4 %** |
| PW_MCTS_FULL @1024 | 122/157 = 77.7 % | 34 | [63.9, 81.7] | 63.9 % |
| PW_MCTS_UNIFORM @1024 | 113/152 = 74.3 % | 39 | [59.2, 79.6] | 59.2 % |
| BEAM_FULL_UNIFORM @1024 | 105/142 = 73.9 % | 49 | [55.0, 80.6] | 55.0 % |
| PW_MCTS_SEEDED4 @4096 | 117/153 = 76.5 % | 38 | [61.3, 81.2] | 61.3 % |
| PW_MCTS_FULL @4096 | 119/153 = 77.8 % | 38 | [62.3, 82.2] | 62.3 % |
| BEAM_SEEDED4 @4096 | 116/150 = 77.3 % | 41 | [60.7, 82.2] | 60.7 % |
| BEAM_FULL @4096 | 114/150 = 76.0 % | 41 | [59.7, 81.2] | 59.7 % |

**Safeguards:** K0 correct NOOP 142/147 and NONE correct ABSTAIN 124/128 are identical for every arm. Both are decided by the no-op gate and admission, not by search.

## Paired contrasts (95 % lineage-family cluster bootstrap; both arms decided)

| Contrast | Strict, K1+K2 | Wins / losses | Operational, K1+K2 |
|---|---|---|---|
| **C1: PW_MCTS_SEEDED4@1024 − EXACT4** | **+1.4 pp [−2.1, +5.0]** (n = 140) | 4 / 2 | +1.6 [−3.7, +6.6] |
| PW_MCTS_SEEDED4 − PW_MCTS_FULL @1024 | +2.8 [−0.7, +7.0] | 6 / 2 | +0.5 [−5.2, +5.9] |
| PW_MCTS_SEEDED4 − BEAM_SEEDED4 @1024 | +2.8 [−1.4, +7.1] | 7 / 3 | +1.6 [−3.7, +6.9] |
| PW_MCTS_SEEDED4 − BEAM_FULL @1024 | +1.4 [−3.6, +6.3] | 8 / 6 | +1.0 [−4.8, +6.7] |
| BEAM_SEEDED4@1024 − EXACT4 | −2.2 [−6.5, +2.1] | 3 / 6 | 0.0 |
| BEAM_FULL@1024 − EXACT4 | −0.7 [−5.8, +3.7] | 5 / 6 | +0.5 |
| PW_MCTS_FULL@1024 − EXACT4 | −2.1 [−6.4, +2.1] | 3 / 6 | +1.0 |
| EXACT6 − EXACT4 | −2.1 [−5.5, +0.7] | 1 / 4 | 0.0 |
| **EXACT_FULL − EXACT4** | **−4.4 [−9.8, +0.7]** | **4 / 10** | **−5.8 [−11.6, 0.0]** (11 / 22) |
| **RAND_FULL@1024 − EXACT4** | **−12.6 [−19.3, −6.6]** | 1 / 16 | −16.2 [−23.4, −8.5] |
| PW_MCTS_UNIFORM − PW_MCTS_FULL | −3.5 [−9.9, +2.8] | 8 / 13 | −4.7 [−11.0, +1.6] |
| BEAM_FULL_UNIFORM − BEAM_FULL | −4.6 [−9.9, 0.0] | 3 / 9 | **−8.4 [−14.1, −2.6]** |
| PW_MCTS_SEEDED4@4096 − EXACT4 | −2.2 [−7.2, +2.2] | 4 / 7 | −1.6 |
| PW_MCTS_SEEDED4@4096 − BEAM_SEEDED4@4096 | 0.0 [−3.4, +3.4] | 3 / 3 | +0.5 |

- **K1 and K2 separately:** every C1 interval includes 0. Strict: K1 0.0 [−4.2, +4.2], K2 +2.9 [−2.9, +9.0]. Operational: K1 −1.0, K2 +4.2 [−3.2, +11.8].
- **Data:** per-root records are in `P3_PHYSICAL_PER_ROOT.jsonl`, with decisions, picks, strata and both outcome modes.
