# P2 predictive pilot and model-only EVAL results (no physical labels used)

## Tuning (DEV, 151 K-blind roots; `P2_TUNING.json`)

Criterion, fixed in code before the pilot: mean agreement with EXACT_K2's committed decision over B ∈ {16, 64, 256, 1024} × seeds {0, 1, 2}.

| Arm | Chosen | Mean agreement | Grid |
|---|---|---|---|
| UCT_SET | c = 0.1 | 0.698 | c ∈ {0.1, 0.3, 1.0}; 0.1 is the grid edge |
| PW_UCT_SET | c = 0.3, (k, α) = (2.0, 0.5) | 0.678 | |
| BEAM_SET | w = 16 | 0.742 | ties w = 32; first in grid order |
| RAND_SET | – | 0.637 | |

## EVAL model-only (600 roots; `MODEL_SUMMARY_EVAL.json`, `MODEL_AGREEMENT_BY_K_EVAL.json`)

**EXACT_K2 cost:** median 1,232 unique ordered evaluations including the no-op (90th percentile 4,047). By stratum: K1 636, K2 997, K0 93, NONE 4,034.

**Agreement with EXACT_K2's committed decision:**

| Arm | B=16 | B=64 | B=256 | B=1024 |
|---|---|---|---|---|
| BEAM_SET | 0.567 | **0.673** | **0.848** | **0.985** |
| UCT_SET | 0.547 | 0.593 | 0.792 | 0.979 |
| PW_UCT_SET | 0.545 | 0.604 | 0.752 | 0.963 |
| RAND_SET | 0.543 | 0.582 | 0.676 | 0.912 |

**K1 / K2 only, at B=256:**

| Arm | K1 | K2 |
|---|---|---|
| BEAM | 0.906 | 0.684 |
| UCT | 0.729 | 0.604 |
| PW | 0.691 | 0.488 |
| RAND | 0.528 | 0.270 |

**Observations:**
- **UCT beats random sampling at every budget, but trails the simple beam at every budget and in every stratum.** Progressive widening does not help in this shallow, finite space.
- **K0 and NONE agreement is ≥ 0.97 for every arm** at every budget. The no-op gate and abstention are decided by p_noop and admission, almost independently of search.

## Live wall time (30 predeclared EVAL roots; laptop RTX 5060; `P2_LIVE_TIMING.jsonl`)

| Planner | Median live wall time |
|---|---|
| EXACT_K2 (full K ≤ 2 pool in large batches, including selection) | **0.058 s** |
| UCT_SET@16 | 0.026 s |
| UCT_SET@64 | 0.097 s |
| UCT_SET@256 | 0.381 s |
| UCT_SET@1024 | 1.51 s |

- PW, RAND and BEAM are similar to UCT (BEAM@1024: 1.23 s).
- **Set search is faster than exhaustive only at B=16.** At B ≥ 64 it is slower, because each step is a small sequential GPU call (about 3 ms) while exhaustive scoring is one batched pass.
- Live vs replay decisions: 0 of 510 differ.
