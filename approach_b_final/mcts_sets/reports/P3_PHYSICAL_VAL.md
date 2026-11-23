# P3 physical verification on VAL (development evidence, not an independent test)

**Protocol:** `P2_PREREG.md`. Predictions and the query manifest were sealed and pushed (`ec1431037b`, `P3_SEAL.json`) before any teacher call.

## Teacher run (actual)

| Item | Value |
|---|---|
| Host | gvlab2, unchanged ablation harness (`benchmark.teach`, `evaluate._verify_job`, ablation teacher env and code, read-only); new cache `naren_workspace/mcts_sets/cache/verify_2d.jsonl`; `V3OUT` redirected so nothing was written under k3abl |
| Workers | 32 on CPUs 8–39 (16 CPUs left free; host idle) |
| New queries | **597** (cap 1,200): 166 roots, all 191 primary roots covered for both B = 256 and B = 64. Another 536 primary and 252 secondary REPAIR decisions were already decided in the K≤3 ablation and post-ablation caches (same teacher contract) |
| Teacher CPU | **2.61 h** (cap 24); max single job 450 s; wall about 7 min |
| Retries | none. No 3D query; no K3 or protected cohort |
| Teacher statuses (new queries) | X: VERIFIED 431, CERTIFIED_INFEASIBLE 84, UNKNOWN_PLANNER 71, UNKNOWN_TRANSIT 11. Y: VERIFIED 367, CERTIFIED_INFEASIBLE 77, UNKNOWN_PLANNER 153 |

## Outcome semantics (disclosed)

- **Primary** follows the pre-registered frozen evaluator `scripts/v32b_phys.outcome`, the same function used in V3.4 and in the K≤3 ablations. For 2D it reads the teacher's x / y **values**, so an `UNKNOWN_*` status carrying value 0 counts as a (finite-budget, operational) failure.
- **Strict sensitivity** (`P3_PHYSICAL_VAL_STRICT.json`): a value counts only when its status is VERIFIED or CERTIFIED_*. Otherwise it is UNKNOWN and excluded.

## Results, primary (pre-registered harness; EVAL, seed 0; `P3_PHYSICAL_VAL.json`, per root in `P3_PER_ROOT.jsonl`)

| Arm | K1 success | K2 success | Pooled K1+K2 | Median unique scored (K1/K2) | K0 correct NOOP | NONE correct ABSTAIN |
|---|---|---|---|---|---|---|
| EXACT_K2 | 62/96 (64.6 %) | 58/95 (61.1 %) | **62.8 %** | 817 | 142/147 | 124/128 |
| UCT_SET@256 | 63/96 | 58/95 | **63.4 %** | 256 | 142/147 | 124/128 |
| PW_UCT_SET@256 | 62/96 | 61/95 | 64.4 % | 256 | 142/147 | 124/128 |
| BEAM_SET@256 | 61/96 | 55/95 | 60.7 % | 255 | 142/147 | 124/128 |
| RAND_SET@256 | 57/96 | 53/95 | 57.6 % | 256 | 142/147 | 124/128 |
| UCT_SET@64 | 61/96 | **34/95** | 49.7 % | 64 | 142/147 | 124/128 |
| PW_UCT_SET@64 | 55/96 | 41/95 | 50.3 % | 64 | 142/147 | 124/128 |
| BEAM_SET@64 | 58/96 | 48/95 | 55.5 % | 63 | 142/147 | 124/128 |
| RAND_SET@64 | 63/96 | 38/95 | 52.9 % | 64 | 142/147 | 124/128 |

Under the primary semantics, UNKNOWN = 0 for every arm. Pooled failures for EXACT_K2: FAIL_Y 37, FAIL_X 27, NOOP-on-task 7.

**Paired differences** (pooled K1+K2, 191 roots, 95 % root bootstrap with 2,000 resamples):

| Comparison | Difference [95 % CI] | Wins / losses |
|---|---|---|
| UCT@256 − EXACT_K2 | +0.5 pp [−3.7, +4.7] | 10 / 9 |
| PW@256 − EXACT_K2 | +1.6 pp [−2.6, +6.3] | |
| UCT@256 − BEAM@256 | +2.6 pp [−2.1, +7.3] | |
| UCT@256 − RAND@256 | +5.8 pp [0.0, +11.5] | |
| PW@256 − BEAM@256 | +3.7 pp [−1.6, +8.9] | |
| PW@256 − RAND@256 | +6.8 pp [+1.0, +12.6] | |
| UCT@64 − EXACT_K2 | **−13.1 pp [−20.9, −5.2]** | |
| PW@64 − EXACT_K2 | −12.6 pp [−20.4, −5.2] | |
| UCT@64 − BEAM@64 | −5.8 pp [−14.7, +3.1] | |
| UCT@64 − RAND@64 | −3.1 pp [−10.5, +4.2] | |

## Strict sensitivity (UNKNOWN_* excluded)

| Arm | Pooled K1+K2 | Decided roots |
|---|---|---|
| EXACT_K2 | 81.1 % | 148 |
| UCT@256 | 80.7 % | 150 |
| PW@256 | 80.4 % | |
| BEAM@256 | 80.0 % | |
| RAND@256 | 75.9 % | |

- UCT@256 − EXACT_K2 = +1.4 pp [−1.4, +4.3] (140 decided pairs).
- 19–25 % of primary roots become UNKNOWN, so by the registered rule (> 20 %) this analysis is **INCONCLUSIVE**. Its direction matches the primary analysis.

## Notes

- **K1 vs K2:** at B = 256, set search is as good as exhaustive in both strata. At B = 64 the loss is concentrated in **K2** (UCT 34/95 vs EXACT 58/95). Pairs need far more evaluations than singletons to cover.
- **Safeguards:** K0 NOOP and NONE ABSTAIN are identical for every arm. They are decided by the no-op gate and admission, not by search.
