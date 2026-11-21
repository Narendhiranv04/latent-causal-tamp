# K12: BLOCKED by the 20-object model cap

**Verdict:** BLOCKED. No certified minimum-K12 scene exists within the declared constraints:
- 8×8 original geometry;
- object count ≤ 20 (model cap);
- objects in the TRAIN-supported columns 3–7;
- certificate MINK_STATIC_V1 = V2 = witness length.

No K12 scene is in the final release, and nothing was substituted.

## Why the certificate rules it out

Acceptance needs K_lb(V2) = K_lb(V1) = |verified witness| = 12. K_lb is a sound lower bound and is monotone in occupancy. So a scene with K_lb < 12 might still have a true K* of 12, but it can never be *certified* as 12. Every search below measured the largest certifiable K_lb.

## Evidence (all files in `G3/k12_evidence/`)

| Search | Space | Largest K_lb reached |
|---|---|---|
| Full-occupancy ceiling (`ceiling.py`, `CEILING_cols3.json`) | all 1,248 target/goal pairs, every column-3–7 cell occupied (39 objects) | **13** only for (5,7) and (61,63); 11 for (23,39), (31,47), (39,23), (47,31); ≤ 10 for every other pair |
| Greedy pruning (61,63) (`prune_61_63.jsonl`) | remove one object at a time, keeping K_lb maximal | 13 down to 28 objects, **12 at 27–25**, 11 at 24, 10 at 23–21, **9 at 20** |
| Greedy pruning (23,39), (31,47) (`prune_23_39.jsonl`, `prune_31_47.jsonl`) | same | 8 at 24 objects, **7 at 20** |
| Seeded annealing at exactly 20 objects (`anneal20.py`, `a_5_7.log`, `a_61_63.log`) | 18 runs, fixed corner pair, swap moves, 5,800 steps each | **9** in every run; 10,641 distinct K_lb 9 layouts ((5,7): 5,262, (61,63): 5,379); none ≥ 10 |
| Annealing arms A / B (gvlab2 `out/`) | random target/goal, 20k steps, columns 3–7 (A) or all columns (B), 784 rows | 8 |

## Blocker

At ≤ 20 objects, the largest certifiable minimum K in this geometry and support is **9**, reached only by the two corner pairs (5,7) and (61,63). On the best pair, **K_lb 12 needs at least 25 objects**.

Reaching K12 would need one of these. Each changes the declared protocol and is not authorised:
- raising the 20-object model cap to ≥ 25;
- a larger lattice;
- objects outside the TRAIN support.

## K9 consequence

All K9 candidates come from the two corner pairs. The locked diversity rule (≤ 2 scenes per target/goal pair per stratum) therefore caps the final K9 stratum at **4** scenes, against a quota of 5.
