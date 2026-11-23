# P2 tuning pre-registration (written and committed before any DEV pilot run)

## Data and reference

- **Data:** the 151 DEV roots, using the identical K-blind split of the completed study. The planner sees public inputs only. No physical label, K or teacher field is used anywhere in P2.
- **Model-only reference:** `EXACT_FULL`, an offline diagnostic. Every legal K≤2 ordered sequence of the full domain is scored once by the frozen X/Y (about 239k per median root, 9–27 s), and the frozen `xy.choose` is applied.
- **Replay:** every arm replays that table through the budgeted `Oracle`, so each arm is still charged for every unique ordered sequence it requests. The table is never presented as a deployable cost; deployable latency comes only from the live P2 timing subset.

## Arms and grids

The no-op is always one charged token. Every search arm uses `nb = 16` sets per scorer batch.

| Arm | Tuned grid | Configurations |
|---|---|---|
| `PW_MCTS_SEEDED4` | ε ∈ {0.1, 0.25, 0.5} × (f56, ftail) ∈ {(0.20, 0.40), (0.25, 0.50), (0.40, 0.70)} × q_dir ∈ {0.125, 0.25} × c ∈ {0.1, 0.3} × (k_pw, α_pw) ∈ {(1, 0.5), (2, 0.5)} | 72 |
| `PW_MCTS_FULL` | ε × q_dir × c × pw (same values) | 24 |
| `BEAM_SEEDED4` | ε × (f56, ftail) × q_dir × w ∈ {4, 16}; q_single = 0.5 | 36 |
| `BEAM_FULL` | ε × q_dir × w | 12 |
| `PW_MCTS_UNIFORM`, `BEAM_FULL_UNIFORM` | not tuned: the frozen `*_FULL` parameters with ε = 1 (uniform prior), a pure prior ablation | – |
| `RAND_FULL` | none | – |
| `EXACT4`, `EXACT6`, `EXACT_FULL` | none (natural exhaustive cost) | – |

- **Tuning budgets:** B_score ∈ {256, 1024}, seeds {0, 1}.
- **After freezing:** each frozen configuration is rerun on DEV at B ∈ {64, 256, 1024, 4096} with seeds {0, 1, 2} for the model-only report.

## Criterion

The criterion is the same for every arm and is fixed now. Define the per-root model regret as p11(EXACT_FULL committed) − p11(arm committed), where a committed NOOP or ABSTAIN counts as p11 = 0 unless EXACT_FULL made the same NOOP or ABSTAIN decision, in which case the regret is 0.

1. Minimize the mean regret over all 151 DEV roots at **B = 1024**, averaged over seeds 0 and 1.
2. Ties within 1e-4 go to the lower mean regret at **B = 256**.
3. Remaining ties go to the higher committed-decision agreement with EXACT_FULL at B = 1024.
4. Then to the first configuration in grid order.

## Audits reported alongside, not used for selection

- agreement with `EXACT4` (overfitting to the fixed-pool optimum);
- off-top-4 budget share;
- strata of the picks;
- tier events;
- batch counts.

## Overrides

- **Primary budget:** B_score = 1024 is the primary physical budget, the closest power of 4 to `EXACT4`'s median natural cost (817) in the completed study. B = 4096 is secondary.
- **Re-registration:** if the model-only results show a budget-dependent ranking, nothing is changed after the fact. All budgets are reported and the P3 registration uses these two budgets.
