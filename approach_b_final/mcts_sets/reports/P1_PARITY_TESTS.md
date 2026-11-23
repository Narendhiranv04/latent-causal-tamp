# P1 parity and contract tests

`python -m pytest approach_b_final/mcts_sets/tests -q` → **13 passed**. The fixtures use illustrative mock scores, not model predictions.

| Test | What it establishes |
|---|---|
| `test_pool_enumerates_every_legal_set_once` | every legal K ≤ 2 assignment appears exactly once and equals the brute-force set; duplicate objects and duplicate destinations are rejected |
| `test_single_relocation_solves` | a one-move repair is selected when it is the best admissible candidate |
| `test_pair_required_and_every_singleton_poor` | every singleton is below η and a two-object repair is high: EXACT and UCT find the pair (G2) |
| `test_order_chosen_by_energy_not_insertion` | across six seeded insertion orders (object permutations π), the committed order is always the higher-p11 permutation |
| `test_budget_never_exceeded_and_no_partial_set` | for every arm and B ∈ {1, 2, 3, 16, 64}: unique scored = requests ≤ B, and every scored pair has both orders |
| `test_noop_charged_identically_and_gate` | the no-op is charged first; the no-op gate gives NOOP; nothing admitted gives ABSTAIN; exact scores = pool size + no-op |
| `test_terminates_without_looping` | empty pool, a single action, and full pool exhaustion all end EXHAUSTED; a tight budget ends BUDGET well inside the iteration guard |
| `test_full_budget_mcts_scores_every_set_exactly_once_and_matches_exact` | with unlimited budget, UCT, PW-UCT, RAND and a wide BEAM each score every set once and commit exactly the EXACT decision |
| `test_reentrance_uses_cache` | re-evaluating a set (in either insertion order) is a cache hit with no new scorer call |
| `test_deterministic_per_seed` | identical output for an identical (root key, seed) |
| `test_choose_matches_frozen_xy_choose` | 300 random candidate pools: `search_sets.choose` ≡ `xy.choose` (gate, η, rounding, tie order) |
| `test_exact_matches_exhaustive_selectors_k_le_2` | 25 random pools: EXACT_K2 ≡ `exhaustive.Selectors` (M4) on the same scores |
| `test_planner_modules_import_no_teacher_or_private_data` | the planner modules import no teacher or simulation module and reference no private field |

## Parity on real roots

- **K ≤ 3 benchmark vs frozen V3.4 VAL predictions:** 40/40 roots identical (`P0_EMPIRICAL.json`).
- **Live vs replay:** on the predeclared timing subset (30 EVAL roots, all arms × budgets, seed 0), 0 of 510 decisions differ (`P2_LIVE_TIMING.jsonl`).
- **Figures re-run:** the four figure roots re-run UCT_SET@256 and reproduce their sealed decisions (`FIG_ROOT_CHECKS.json`).
- **Post-seal change:** after sealing, `uct()` was changed only to also return its tree root, for the figures. Decisions are unchanged (tests plus the four re-runs).
