# P1: Is the frozen top-4 destination pool a real failure source?

**Scope.** All 751 public 2D VAL roots. This is already-examined **development evidence** and serves for hypothesis generation only. Private labels (K, teacher caches, generator labels) are used **only here**, in `analyze.py recall`. They never reach `domain.py`, `fsearch.py`, `run.py`, tuning or the sealed predictions. Numbers come from `P1_RECALL.json`; witness-level records stay private (`~/fds_private`).

**Witness definition.** A *witness* is a complete ordered relocation sequence with an independently **VERIFIED** success (x = y = 1, both statuses VERIFIED). Sources:
- **exact-contract teacher caches** (primary): the K≤3 ablation, the post-ablation validation and the completed MCTS study;
- **generator labels** (secondary): `labels.B`, a different label protocol.

The two sources overlap on 78 (root, sequence) pairs with **0 conflicts**. Each witness is classified by its **worst per-action frozen S1 rank**: TOP4, RANK5_6 or BEYOND6. K>2 sequences and illegal, vacated or repeated destinations are classed GRAMMAR_OUTSIDE_SCOPE. A K2 witness counts as TOP4 only if **both** actions are in their objects' top-4.

**Every count below is a lower bound.** No historical teacher exhausted the legal domain, so the absence of a known witness proves nothing.

## Known witnesses (K≤2 grammar, K1 / K2 roots)

| Source | K1 TOP4 | K1 RANK5_6 | K1 BEYOND6 | K2 TOP4 | K2 RANK5_6 | K2 BEYOND6 |
|---|---|---|---|---|---|---|
| exact-contract caches | 804 | 35 | 189 | 508 | 39 | 121 |
| generator only | 85 | 43 | 243 | 51 | 24 | 151 |

## Roots (120 K1 and 120 K2 VAL roots)

| | K1, cache | K1, any source | K2, cache | K2, any source |
|---|---|---|---|---|
| any known K≤2 witness | 118 | 120 | 103 | 120 |
| a witness inside D4 | 116 | 118 | 103 | 106 |
| **a witness outside D4** | 76 | **118** | 47 | **110** |
| a witness outside D6 | 73 | 116 | 43 | 100 |
| **only** outside-D4 witnesses known | 2 | 2 | 0 | **14** |

Outside-top-4 witnesses sit at median frozen rank 12 (IQR 8–19). Their frozen X/Y p11 (best order) has median 0.92 (IQR 0.67–0.98). These are model predictions.

## Where EXACT4 failed physically (completed study, EVAL, operational outcome)

| Of the EXACT4 non-successes | K1 (34 of 96) | K2 (37 of 95) |
|---|---|---|
| a verified witness **inside** D4 was known (the pool held a success, so selection or ranking failed) | **33** | **28** |
| **only** outside-D4 witnesses known (**pool-miss candidates**) | **1** | **9** |
| no known K≤2 witness | 0 | 0 |

Model-only check on the 68 EXACT4-failed K1/K2 roots that have a known outside-top-4 witness:
- the best witness clears admission (p11 ≥ 0.3) on 59;
- the frozen X/Y scores it **above EXACT4's own committed pick on only 15**.

A full-domain search that maximizes the frozen p11 could therefore be steered toward a known successful outside witness on at most those 15 roots. It could equally well commit some other, unlabelled outside set.

## Gate decision: **EVIDENCE_OF_CANDIDATE_DOMAIN_LIMITATION (concrete but small); proceed to P2**

- **The pool limit is real.** Verified complete K1/K2 repairs outside the frozen top-4 exist on almost every K1/K2 root: 118/120 K1 and 110/120 K2 roots, 76 and 47 from the exact-contract caches alone. On 10 roots where EXACT4 failed physically, the only known successes lie outside the top-4 pool (`POOL_MISS` candidates).
- **Most EXACT4 failures are selection failures, not recall failures.** In 61 of 71 EXACT4 failures a verified success was already inside the top-4 pool and X/Y committed something else. The prediction to test is that wider domains can help only on the small pool-miss slice, and X/Y misranking may absorb that gain.
- **Labels stay out of search.** No label was used to build an action list, a prior, a tier or any planner input.

Figures (real VAL scenes, 4 pool-miss candidates; heatmap = frozen marginal; rings = top-4 / rank 5–6; star = known verified witness): `figures/p1_root_*.png`, listed in `P1_FIGURES.json`.
