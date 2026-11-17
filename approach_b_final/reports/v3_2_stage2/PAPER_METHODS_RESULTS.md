# Methods and results — exhaustive top-M repair construction with a retrained Boltzmann X/Y scorer

## Methods

**Problem and outputs.** For a scene where the target manipulation is blocked, the system outputs one of three things:

- an ordered repair of K ≤ 3 obstacle relocations;
- a no-op;
- an abstention (declaring the scene not repairable).

A repair counts as successful only when both physical teachers accept it:

- **X:** the ordered relocation chain, with its final connector, executes.
- **Y:** the original target manipulation, started from the canonical edited endpoint at q_ref, executes.

**Candidate construction.**

1. A frozen task-conditioned cVAE proposes destinations for each eligible movable object. Its marginal comes from 64 Monte-Carlo draws, with a fixed per-root seed.
2. We keep the top-M destinations per object, for M ∈ {4, 5, 6}.
3. We enumerate every legal ordered sequence of length 1–3 over these sets. There is no cap on the number of sequences. The previous system capped construction at B = 4,096.
4. M4 and M5 pools are exact nested prefixes of the M6 pool, so one M6 pass yields all three.

**Scoring and selection.**

- The coupled Boltzmann scorer D gives each sequence a success probability p11.
  - Y is computed once per unique endpoint and shared across that endpoint's permutations.
  - X is order-sensitive and conditioned on Y.
- Selection uses a fixed rule that was tuned on validation in V3-5:
  - a no-op gate at 0.5;
  - an admissibility threshold η = 0.3;
  - then argmin of −log p11.
- Selection is online and exact over the streamed pool.

**Expanded-distribution evidence (TRAIN only).**

- **Roots:** 449 2D and 305 3D TRAIN roots, stratified by legacy K class (including no-op and NONE), in a fixed hash order.
- **Candidates per root:** for each root we enumerated the exhaustive M6 pool with the frozen model and drew a label-blind, seeded sample:
  - the top-1 at each M;
  - the next-highest-p11 candidates;
  - one draw from each of three p11 bands;
  - one uniform draw;
  - all other orders of the top-1 assignment and of known successful assignments.
- **Teacher queries:** the unchanged teachers labelled Y once per endpoint. X was labelled where Y = 1, plus a seeded third of the Y = 0 items.
- **Result:** 4,477 2D and 2,680 3D labelled candidates (0 unresolved). These were added to the label sets of those TRAIN roots, and no validation or test row changed.

**Matched training.**

- **D-control** was retrained from scratch on the original evidence. **D-expanded** used the original evidence plus the new labels.
- Everything else was identical:
  - architecture and seed (hence initialisation);
  - root list and batch partition;
  - optimiser (AdamW, lr 1e-3);
  - number of optimiser steps (60 epochs);
  - checkpoint rule (lowest validation NLL on identical historical validation labels).
- Each arm was trained with three seeds.

**Evaluation.**

- Every selected repair was physically verified once (top-1, no retries).
- Outcomes were averaged over model seeds per root.
- Confidence intervals come from a paired bootstrap over roots (2,000 resamples).
- Metrics:
  - task success over K1–K3 roots;
  - correct abstention on NONE roots;
  - correct no-op on no-op roots;
  - calibration (mean p11 of the selected repair minus its verified success rate).
- **Validation** (751 2D / 364 3D roots) was used for all development decisions.
- **Exposed TEST** (749 / 370 roots) was used only once, for a configuration fixed by a rule registered before the trained arms' 2D validation outcomes were computed.

## Results

**Removing the construction cap at a fixed model** (validation, frozen V3 model).

- **2D task success** rose from 44.3 % to 49.2 % at M4 (+4.8, 95 % CI [+1.2, +8.2]) and to 49.4 % at M5 (+5.1, [+0.7, +9.2]). The gain was driven by K3 repairs (20 % → 32–34 %).
- **Correct abstention** on NONE roots fell from 87.3 % to 79.3 % / 76.7 % / 75.3 % at M4 / M5 / M6 in 2D, and from 86.2 % to 82.8 % / 77.6 % / 75.9 % in 3D. Almost all added errors were confident selections of physically infeasible endpoints.
- **3D task success** was unchanged.

**Expanded-distribution evidence** (validation, matched, 3 seeds). D-expanded improved correct abstention over D-control at every M:

| Domain | M4 | M5 | M6 |
|---|---|---|---|
| 2D | +5.6 [+2.9, +8.2] | +8.9 [+5.8, +12.2] | +10.7 [+7.3, +14.2] |
| 3D | +22.4 [+14.4, +31.6] | +25.9 [+17.8, +34.5] | +25.3 [+16.7, +33.3] |

- **2D task success** improved by about 3 points at every M: 55.9 / 55.8 / 54.9 % vs 52.9 / 52.5 / 52.1 %. The CIs exclude 0 at M5 and M6.
- **3D task success** was statistically unchanged.
- **Calibration:** over-confidence of the selected repair fell in both domains (2D 0.36–0.39 → 0.26–0.29; 3D 0.18 → 0.11–0.14).
- **Across M:** within a model, success did not change significantly, so a single scorer served all three pool sizes.

**Exposed-TEST regression** (D-expanded, exhaustive M4, vs the capped V3 path, 3 seeds each).

| Domain | Capped V3 | D-expanded M4 | Δ task |
|---|---|---|---|
| 2D | 43.6 % | 52.0 % (K3 12 → 26 %) | +8.4 [+5.4, +11.3] |
| 3D | 77.3 % | 81.2 % | +3.9 [+0.4, +7.3] |

Abstention did not degrade (2D +0.2; 3D +5.4, n.s.), and no-op correctness improved (+1.4 and +8.5 points).

**Remaining errors.** For most 2D validation task roots (59–73 %, depending on M), no known physical success lies in the top-M pool. The largest residual failure class is a confident infeasible endpoint in such pools, which points to proposal coverage as the next bottleneck.

**Cost.**

- **Exhaustive scoring:** 2D M6 scores a median of 103 k (max 961 k) sequences per root, about 9.5 s per root on one CPU plus GPU. M4 scores about 25 k (median) with equal or better verified success.
- **Training evidence:** 43 CPU-hours of teacher labelling.
- **Training:** 12 scorer fits took about 6 GPU-minutes in total.

**Limitations.** The test split is historically exposed, and no fresh family-disjoint cohort was evaluated, so these results do not constitute an unbiased generalisation estimate. Physical outcomes come from simulation teachers.
