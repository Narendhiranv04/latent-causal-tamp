# P4 final decision: full-legal-domain K1/K2 action-set selection

## Verdict (registered rules, `P3_PREREG.md`): **EXPANSION_NOT_ESTABLISHED (INCONCLUSIVE)**

- **Primary contrast C1 = PW_MCTS_SEEDED4@1024 − EXACT4.** Strict difference +1.4 pp [−2.1, +5.0] (140 decided pairs, 4 wins / 2 losses); operational +1.6 [−3.7, +6.6].
  - The lower bound is not > 0, so the result is not HELPFUL. The upper bound is not < 0, so it is not HARMFUL.
  - Strict UNKNOWN is 22.5 % for EXACT4 (> 20 %), so the INCONCLUSIVE sub-label applies.
- **`SEEDED_EXPANSION_HELPFUL`: not met.** Seeded vs soft-prior full MCTS is +2.8 [−0.7, +7.0], although latency is equal (0.170 vs 0.162 s).
- **`MCTS_ADDED_VALUE`: not met.** Against BEAM_SEEDED4: +2.8 [−1.4, +7.1]. Against BEAM_FULL: +1.4 [−3.6, +6.3].
- **Latency** is not harmful by the registered rule (0.170 s ≤ 1.0 s), but it is **6.3× EXACT4's 0.027 s**.

**Recommendation: keep `EXACT4`** (frozen top-4 exhaustive K≤2). It matches every expanded arm on verified success and is the fastest. Do not adopt full-domain beam or batched full-domain MCTS on this evidence.

The binding constraint is **X/Y misranking of out-of-pool sets, not cVAE destination recall**. Of the plan's listed outcomes, the evidence supports *"X/Y misranking dominates candidate recall."*

All of this is **VAL development evidence** (owner-selected dev-only cohort). The completed fixed-pool study already exposed these roots. No independent generalization claim is made.

## Answers to the final question

1. **Is selection limited by cVAE destination recall?** Only a little, and the limitation is not what blocks success.
   - *P1 evidence:* verified K1/K2 repairs outside the top-4 exist on 118/120 K1 and 110/120 K2 VAL roots. But 61 of 71 EXACT4 failures already had a verified success *inside* the top-4 pool.
   - *Expanded arms do commit good off-pool repairs:* PW_MCTS_SEEDED4 had 82 verified off-top-4 successes, and BEAM_FULL 98 (`P4_ATTRIBUTION.json`). Real pool-miss wins exist, for example 3 strict and 10 operational wins for seeded MCTS over EXACT4, all from off-top-4 picks.
   - *They lose as many elsewhere:* the frozen X/Y prefers out-of-pool sets that then fail. The extreme case is the offline full-domain model optimum, EXACT_FULL: off top-4 on 43.5 % of roots, it is **worse** than EXACT4 by −4.4 pp strict [−9.8, +0.7] and −5.8 pp operational [−11.6, 0.0], with 4 / 10 and 11 / 22 wins / losses. All 10 of its strict losses are off-top-4 picks.
   - *Optimizing the model harder does not help:* the search arms at B = 4096 sit closer to the model optimum but score below their B = 1024 versions physically.
   - *The prior acts as a regularizer:* removing the cVAE prior (uniform) costs 3.5–4.6 pp strict and 4.7–8.4 pp operational, and random full-domain sets cost 12.6 pp strict (significant).
   - *Reading:* the frozen X/Y was trained around cVAE-proposed destinations and is over-confident on unfamiliar cells. The cVAE prior restrains that.
2. **Does top-four-seeded → full-domain progressive widening beat immediate soft-prior full-domain search?**
   - Model-only: yes. It has the lowest predicted regret at every budget from 64 to 1024, on DEV and on EVAL (0.0256 vs 0.0301 at 1024).
   - Physically: it is the best expanded arm numerically (+2.8 pp vs full MCTS), but **not significant**. Staging improved the model objective; that improvement was not shown to change verified success.
3. **Does MCTS add value over a fair, identically staged beam?** **No.**
   - +2.8 pp [−1.4, +7.1] over BEAM_SEEDED4 at 1024, and 0.0 [−3.4, +3.4] at 4096.
   - Batching removed the old 6.5× MCTS-versus-beam latency gap (0.170 vs 0.168 s). But anything staging achieved was achieved by the staged beam as well (the seeded arms beat the full-access arms on regret for both search types), so no gain can be credited to MCTS itself.
4. **Wall time.** EXACT4 takes 0.027 s median end-to-end. Every search arm at 1024 takes 0.16–0.17 s, at 4096 0.61–0.68 s, and EXACT_FULL 6.0 s (p90 28 s). The cVAE full marginal costs 0.9 ms. Live decisions equal the sealed replay on 930/930 runs.

## Attribution (strict, B = 1024 / exact; `P4_ATTRIBUTION.json`, `P4_WINLOSS_VS_EXACT4.json`)

| Arm | Success in D4 | Success off D4 | Ranking failure (a known success was scored, a failure committed) | Retrieval failure (eligible, never scored) | Pool miss | Unresolved (UNKNOWN) |
|---|---|---|---|---|---|---|
| EXACT4 | 120 | 0 | 22 | – | 6 | 43 |
| EXACT6 | 56 | 64 | 30 | – | 3 | 38 |
| BEAM_SEEDED4 | 42 | 78 | 30 | 5 | – | 36 |
| BEAM_FULL | 23 | 98 | 24 | 8 | – | 38 |
| PW_MCTS_SEEDED4 | 41 | 82 | 23 | 7 | – | 38 |
| PW_MCTS_FULL | 33 | 89 | 26 | 9 | – | 34 |
| RAND_FULL | 10 | 79 | 21 | 28 | – | 53 |

- **Tiers and witness orders.** `TIER_LOCKED` = 0: with the frozen schedule, every tier unlocked within B = 1024 on every root. `ORDER_SELECTION_FAILURE` = 0 among decided cases with a known same-set witness.
- **Ranking dominates.** Among decided failures, ranking failures (22–30 per arm) far outnumber retrieval failures (5–9 for the guided arms), and both are lower bounds that depend on the known witness set.
- **Granularity.** Unlocked-not-expanded and expanded-not-scored are merged into retrieval, because per-node logs were not kept for physical arms.

## What the evidence permits and does not permit

**Permits:**
- On VAL K1/K2 development roots, opening the full legal destination domain under the frozen X/Y gives **no verified gain** over the frozen top-4 exhaustive pool at 6× the latency.
- The frozen X/Y's full-domain optimum is *physically worse* than its top-4 optimum, by a small margin with a borderline CI.
- Removing the cVAE prior, or random full-domain search, hurts.
- Seeded staging improves only the model objective.
- MCTS shows no advantage over an identically staged batched beam.

**Does not permit:**
- any independent-test or generalization claim;
- any claim that MCTS, seeding or full-domain search is better;
- any claim that the top-4 pool is *sufficient* (pool misses exist; they simply did not translate into net gains under this scorer);
- K3, K>3 or 3D claims;
- causal or blocker-identification claims.

## Justified next steps (none started)

1. **Keep EXACT4** in the released K≤3 method.
2. **If out-of-pool repairs matter,** the lever is the scorer, not search. That means calibrating or training X/Y on off-pool destinations (new training needs separate authorization). A cheaper diagnostic would be EXACT6 or a capped-rank pool with a separate admission threshold for off-pool sets, which would need a new pre-registration.
3. **Any positive claim** needs a lineage-disjoint, freshly generated K1/K2 cohort sealed before inference, with UNKNOWN below 20 %.

## Resources

| Item | Used |
|---|---|
| Physical teacher | **1,018 new 2D queries** (cap 1,200) and **3.80 CPU-h** (cap 24), gvlab2 with 32 workers; no retries, no 3D, no K3 |
| Laptop GPU (RTX 5060) | P0/P1 under 5 min; DEV pilot about 55 min (4–8 processes); frozen EVAL and DEV about 80 min (8 processes, kept under the memory guard); live timing about 25 min (GPU alone) |
| Learned weights | none changed, none trained |
| Search-time teacher calls | 0 |
| Private data | stays in `~/mcts_sets_private` and `~/fds_private`; only aggregates and sealed decisions are committed |
