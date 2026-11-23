# P4 final decision: original-root set-MCTS for K < 3 (K1 / K2)

## Verdict: **NULL: same verified performance as exhaustive, but slower. MCTS is not useful at K1/K2.**

Keep exhaustive K ≤ 2 enumeration (EXACT_K2) for K < 3. Treat set-MCTS at most as a scaling idea for larger branching, and only if its latency problem is solved.

## Registered decision (`P2_PREREG.md`), UCT_SET at B = 256

| Criterion | Result | Met? |
|---|---|---|
| (a) noninferior vs EXACT_K2 (lower 95 % bound ≥ −5 pp) | +0.5 pp [−3.7, +4.7] | **yes** |
| (b) median unique scored ≤ 25 % of EXACT_K2 (K1/K2 roots) | 256 / 817 = **31 %** | **no** |
| (c) better than BEAM_SET **and** RAND_SET (lower bounds > 0) | vs BEAM +2.6 [−2.1, +7.3]; vs RAND +5.8 [0.0, +11.5] | **no** |

- **No registered class applies exactly.** USEFUL needs (a)(b)(c). NONINFERIOR_NOT_BETTER_THAN_SIMPLER needs (a)(b). WORSE and INCONCLUSIVE do not apply: UNKNOWN is 0 % and coverage is 100 %. The analysis code labels this case `NOT_EFFICIENT`; that label was added descriptively and is **not** a registered class.
- **Plan §5 P4 vocabulary:** the outcome is **"same performance but slower"**.
- **PW_UCT_SET@256** gives the same picture: (a) yes, (b) no; (c) fails against BEAM, though it passes against RAND (+6.8 [+1.0, +12.6]).
- **At B = 64**, both MCTS variants are significantly **worse** than exhaustive (−13.1 and −12.6 pp), and not better than beam or random.

## The plan's questions, answered from the evidence

1. **Did MCTS recover the correct unordered action sets?** Partly, and only with enough budget.
   - Model-only agreement with EXACT_K2's committed decision on EVAL (600 roots): 0.59 at B = 64, 0.79 at B = 256, 0.98 at B = 1,024.
   - On K1 / K2 at B = 256: 0.73 / 0.60.
   - **The simple beam agrees more often at every budget** (0.67 / 0.85 / 0.99; K1 / K2 at 256: 0.91 / 0.68).
2. **Was the order chosen by X/Y rather than by insertion order?** Yes, by construction and by test.
   - A STOP scores every permutation from the original root, and the frozen `xy.choose` key picks among them.
   - `test_order_chosen_by_energy_not_insertion` (six seeded insertion orders, one committed order).
   - Real example (`figures/root_D2H_ccfcca393e.png`): both orders share pY = 0.674, with pX 0.965 vs 0.179. The X/Y energy picks the order.
3. **Did it use fewer unique scorer evaluations than full enumeration?** Yes: 256 vs a median 817 on K1/K2 roots (31 %), with equal verified success. At 64 (8 %), success drops by 13 pp.
4. **Was it faster end-to-end?** **No.**
   - Live wall times (30 predeclared EVAL roots, RTX 5060): EXACT_K2 has a median of **0.058 s**, scoring the whole K ≤ 2 pool in a few large batches. UCT_SET@256 takes **0.381 s (6.5× slower)**, @1,024 takes 1.51 s, and only @16 is faster (0.026 s, poor agreement).
   - Reason: on a GPU the cost is per call, not per sequence, and MCTS issues hundreds of tiny sequential scorer calls.
5. **Did it improve verified task success, or only optimize the predictor?** Neither beyond exhaustive.
   - Verified success equals exhaustive (+0.5 pp, not significant).
   - It is numerically, but not significantly, above beam and random at 256.
   - At a fixed budget, maximizing predicted p11 more completely (beam) does not translate into more verified success. Agreement with EXACT is not physical success.
6. **Do K1 and K2 behave differently?** Yes, under tight budgets. K2 pools are larger (median 997 vs 636 sequences). At B = 64, K2 success collapses for UCT (34/95 vs exhaustive 58/95), while K1 stays close to exhaustive.

## What fails and why

- **The space is too small for MCTS to help.** At K ≤ 2, exhaustive scoring costs about 1,000 sequences, and they can be batched. The MCTS advantage (fewer evaluations) is real, but it is the wrong cost model on a GPU, where batching makes extra sequences nearly free and sequential calls expensive.
- **UCT statistics add little over a simple beam.** Terminal rewards are deterministic, with no rollout noise and a shallow depth of 2. A singleton scan plus pair expansion captures the same structure with fewer wasted evaluations.
- **The predicted optimum is not the physical optimum.** Physical failures of the exhaustive pick (FAIL_Y 37, FAIL_X 27) bound what any search over the same pool and scorer can reach.

## What the evidence does and does not permit

**Permits:**
- At K1/K2 on VAL (development data, already examined extensively), set-MCTS with 31 % of exhaustive's scorer evaluations reaches statistically indistinguishable verified success.
- It is slower in wall time.
- It is not significantly better than a beam over unordered sets.

**Does not permit:**
- any claim that MCTS is superior, faster or useful at K < 3;
- any claim about K ≥ 3 or long horizons;
- causal discovery claims;
- generalization beyond VAL (no independent cohort was generated; the V3.4 fresh cohort was not used).

## Justified next steps (none started)

1. **No change** to the released K ≤ 3 method.
2. A K3 follow-up (plan §5 P5) is justified only with a new pre-registration **and** a batched MCTS (parallel leaf evaluation / virtual loss). It should be compared to the same beam, because at K3 the exhaustive pool is about 27k sequences (2.5 s per root) and evaluation count starts to matter.
3. Any positive claim would need an independently generated, lineage-disjoint K1/K2 cohort, sealed before inference.
