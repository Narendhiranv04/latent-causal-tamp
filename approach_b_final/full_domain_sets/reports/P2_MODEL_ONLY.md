# P2 model-only results, budgets and live latency

Everything in this file is a **frozen-model prediction**, not a physical verification. Per-arm numbers are in `MODEL_SUMMARY_DEV.json` and `MODEL_SUMMARY_EVAL.json` (seeds 0–2 pooled), `P2_TUNING.json`, `P2_BUDGET_LATENCY_LIVE.json` and `P2_LIVE_REPLAY_PARITY.json`. Figures: `figures/p2_*.png`.

## Prior parity and implementation (see `P0_PARITY.json` and `P2_TESTS.json`)

- **Prior parity:** the full-grid S1 marginal reproduces the archived top-6 (and so the top-4) on 751/751 VAL roots. The S1 marginal has strictly positive mass on every legal cell, and the uniform floor ε is applied on top of it.
- **Tests:** the 26 contract tests and the 13 historical tests pass. Among them:
  - *Staged access:* initial top-4-only eligibility; exact inclusive unlock thresholds; early unlock without a charge; node reopening; full reachability after unlock.
  - *Matched controls:* the same domain and schedule for seeded MCTS and seeded beam.
  - *Synergy and order:* an off-top-4-only winning pair whose execution order is chosen by X/Y; the low-singleton / high-pair fixture.
  - *Accounting:* all orders or nothing; batch and wall limits; determinism; cache and batch invariance.
  - *Frozen selection:* `EXACT_FULL` equals brute force; `choose` equals `xy.choose`.
  - *Isolation and real-root parity:* no teacher or private access; `EXACT4` reproduces the sealed historical decisions.
- **Low-singleton / high-pair fixture** (600 of 4,032 sequences, measured): beam finds the pair in 8/8 seeds, seeded MCTS in 3/8 and full MCTS in 1/8. With an adequate budget, all arms find it.

## DEV tuning (151 roots; `P2_TUNING_PREREG.md` criterion)

Frozen choices (`P2_FROZEN_PARAMS.json`). Regret and agreement are measured against `EXACT_FULL` at B = 1024.

| Arm | Frozen parameters | Mean regret | Agreement |
|---|---|---|---|
| `PW_MCTS_SEEDED4` | ε 0.1, (f56, ftail) = (0.20, 0.40), q_dir 0.125, c 0.1, pw (1, 0.5) | **0.0300** | 0.609 |
| `PW_MCTS_FULL` | ε 0.25, q_dir 0.25, c 0.1, pw (2, 0.5) | 0.0348 | 0.586 |
| `BEAM_SEEDED4` | ε 0.1, (0.25, 0.50), q_dir 0.125, w 4 | 0.0347 | 0.596 |
| `BEAM_FULL` | ε 0.1, q_dir 0.125, w 16 | 0.0347 | 0.546 |

Seeded MCTS took the edge of its grid for both c and the schedule. That is disclosed, and nothing was retuned.

## EVAL model-only (600 roots, seeds 0–2; the DEV ordering replicates)

| Arm @ B | Mean regret vs EXACT_FULL | Agreement with EXACT_FULL | Agreement with EXACT4 | Committed set off top-4 | Off-top-4 share of scored sets |
|---|---|---|---|---|---|
| EXACT4 (natural cost, median 1,232) | 0.0319 | 0.565 | 1 | 0 | 0 |
| EXACT6 (median 2,885) | 0.0248 | 0.617 | 0.780 | 0.220 | 0.549 |
| **EXACT_FULL** (median 239k) | 0 | 1 | 0.565 | **0.435** | 0.991 |
| RAND_FULL @1024 | 0.0878 | 0.536 | 0.542 | 0.377 | 0.960 |
| BEAM_SEEDED4 @1024 | 0.0306 | 0.625 | 0.649 | 0.294 | 0.726 |
| BEAM_FULL @1024 | 0.0306 | 0.603 | 0.583 | 0.356 | 0.829 |
| **PW_MCTS_SEEDED4 @1024** | **0.0256** | 0.603 | 0.654 | 0.301 | 0.678 |
| PW_MCTS_FULL @1024 | 0.0301 | 0.584 | 0.597 | 0.340 | 0.848 |
| PW_MCTS_UNIFORM @1024 | 0.0587 | 0.541 | 0.539 | 0.394 | 0.978 |
| BEAM_FULL_UNIFORM @1024 | 0.0526 | 0.547 | 0.542 | 0.407 | 0.957 |
| PW_MCTS_SEEDED4 @4096 | 0.0131 | 0.728 | 0.611 | 0.386 | 0.788 |
| BEAM_SEEDED4 @4096 | 0.0181 | 0.712 | 0.645 | 0.347 | 0.817 |

- **The frozen X/Y prefers sets outside the cVAE top-4 on 43.5 % of roots** when given the whole legal domain.
- At a matched budget, seeded MCTS gets the lowest predicted regret. Staging matters more than search type: the seeded arms beat the full-access arms on regret at 64–1024.
- Removing the cVAE prior roughly doubles the regret, and random sets are far worse.
- At B = 1024, all 1,800 seeded runs (600 roots × 3 seeds, for both seeded MCTS and seeded beam) reached the TTAIL tier and fully scored at least one tail set. `EARLY_TIER_EXHAUSTION` (an unlock caused by an exhausted eligible space, without any charge) fired in 492 of those runs, on small roots.

## Live latency (30 predeclared EVAL roots, RTX 5060, CUDA-synchronized, median of 3 after warm-up)

| Arm @ B | Median end-to-end (s) | p90 (s) | Scorer batches |
|---|---|---|---|
| **EXACT4** | **0.027** | 0.169 | 2 |
| EXACT6 | 0.058 | 0.385 | 2 |
| EXACT_FULL | 6.02 | 27.9 | 36 |
| BEAM_SEEDED4 @1024 | 0.168 | 0.180 | 41 |
| BEAM_FULL @1024 | 0.174 | 0.187 | 43 |
| PW_MCTS_SEEDED4 @1024 | 0.170 | 0.222 | 38 |
| PW_MCTS_FULL @1024 | 0.162 | 0.201 | 36 |
| any search arm @4096 | 0.61–0.68 (RAND 0.91) | | 136–150 |

- **Breakdown:** the uncached cVAE full marginal takes 0.9 ms. Peak GPU memory is 13 MB for search and 89 MB for `EXACT_FULL`.
- **Batching removed the old 6.5× MCTS penalty relative to beam.** At equal budgets, MCTS and beam differ by less than 10 %.
- **Every search arm is still 6× slower than EXACT4 at B = 1024.** Under matched wall caps of 0.06 / 0.25 s, every search arm affords only about 350–400 / about 1,400–1,700 ordered scores, against EXACT4's complete pool in 0.027 s.
- **Replay vs live:** live decisions equal the sealed offline-replay decisions on **930/930** runs. The replay was used only for counting and model-only metrics, never for speed claims.
