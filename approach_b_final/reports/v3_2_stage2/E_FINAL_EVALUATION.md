# V3.2 stage 2 — Phase E: physically verified evaluation (E2, E3, E4, E5, E6)

## Protocol

| | |
|---|---|
| Arms | D-control and D-expanded (`D_MATCHED_TRAINING.md`), seeds 0 / 1 / 2 each |
| Sampler / rule | Frozen sampler (task cVAE `q2init_all`, seed-0 per-root draws, top-6 destinations); frozen rule `{noop_gate 0.5, eta 0.3, alpha 0, beta 0, gamma 0}` |
| Pools | One shared exact exhaustive M6 pass per model; M4 and M5 decisions are its nested prefixes (`exhaustive.py`, B uncapped). Both arms score the identical candidate sets. |
| Scoring hosts | Blackwell, girish-laptop, laptop. All passed exhaustive-inference parity: identical decisions, \|Δp11\| ≤ 3e-7 (`A/`). |
| Physical verification | Every selected repair (top-1 only, no retry) verified once, on parity-passed teacher hosts only |
| Validation verification volume | 2D 3,889 unique queries (19.7 CPU-h); 3D 986 (12.7 CPU-h) |
| Unresolved | **0 unknown selections in any arm, seed, M or domain** |

**Statistics.** Per root, outcomes are averaged over the 3 model seeds. Deltas use a paired root-cluster bootstrap with 2,000 resamples over task roots (2D 413, 3D 220) or NONE roots (2D 150, 3D 58). Seeds are not treated as independent roots.

**Exposure.** VAL was already exposed through V3.2-A and Phase B and used for these decisions, so it is a development cohort, not a confirmation cohort.

## E3: does expanded-distribution evidence help? (VAL; `E/TABLE_VAL_E3_E4.{json,txt}`)

| Domain | M | D-control task % (± seed SD) | D-expanded task % | Δ task [95 % CI] | D-control correct NONE abstain % | D-expanded | Δ abstain [95 % CI] |
|---|---|---:|---:|---|---:|---:|---|
| 2D | 4 | 52.9 ± 3.0 | 55.9 ± 0.8 | **+3.0 [+0.0, +5.9]** | 85.1 | 90.7 | **+5.6 [+2.9, +8.2]** |
| 2D | 5 | 52.5 ± 3.0 | 55.8 ± 1.1 | **+3.3 [+0.6, +6.1]** | 81.3 | 90.2 | **+8.9 [+5.8, +12.2]** |
| 2D | 6 | 52.1 ± 3.5 | 54.9 ± 1.3 | **+2.8 [+0.2, +5.6]** | 79.1 | 89.8 | **+10.7 [+7.3, +14.2]** |
| 3D | 4 | 76.2 ± 1.7 | 78.5 ± 1.4 | +2.3 [−0.5, +5.0] | 60.3 | 82.8 | **+22.4 [+14.4, +31.6]** |
| 3D | 5 | 77.1 ± 2.6 | 78.0 ± 2.1 | +0.9 [−2.0, +3.8] | 54.6 | 80.5 | **+25.9 [+17.8, +34.5]** |
| 3D | 6 | 77.6 ± 1.5 | 77.1 ± 1.8 | −0.5 [−3.5, +2.6] | 50.6 | 75.9 | **+25.3 [+16.7, +33.3]** |

**Per-K and no-op detail.**
- K1 / K2 / K3, 2D at M4: control 65 / 69 / 33, expanded 64 / 70 / 40.
- K1 / K2 / K3, 3D at M4: control 67 / 78 / 80, expanded 73 / 80 / 81.
- No-op correctness: 2D 95.9 → 96.8; 3D 84.7 → 83.9.

**Calibration of the selected repair** (mean p11 vs physically verified success rate, all selected repairs):

| Domain | M4 | M5 | M6 |
|---|---|---|---|
| 2D control | 0.885 vs 0.522 | 0.889 vs 0.510 | 0.892 vs 0.501 |
| 2D expanded | 0.833 vs 0.569 | 0.842 vs 0.566 | 0.848 vs 0.557 |
| 3D control | 0.910 vs 0.733 | 0.912 vs 0.731 | 0.911 vs 0.729 |
| 3D expanded | 0.901 vs 0.793 | 0.907 vs 0.781 | 0.905 vs 0.768 |

D-expanded is less over-confident everywhere: the gap shrinks from 0.36–0.39 to 0.26–0.29 in 2D, and from 0.18 to 0.11–0.14 in 3D.

**Answer to H3.** The physically labelled exhaustive-distribution TRAIN evidence improves the scorer:
- **Correct abstention** rises strongly at every M in both domains (2D +5.6 to +10.7 points; 3D +22 to +26 points).
- **2D task success** rises by about 3 points at every M; the CIs exclude 0 at M5 and M6 and just touch 0 at M4.
- **3D task success** is unchanged (CIs include 0).

It does this without extra gradient steps, a different initialisation or different roots. The only change is the evidence.

## E4: one unified scorer across M (within-model M5 / M6 vs M4)

| Domain | Arm | M5 − M4 | M6 − M4 |
|---|---|---|---|
| 2D | control | −0.4 [−2.1, +1.4] | −0.8 [−2.9, +1.4] |
| 2D | expanded | −0.1 [−1.9, +1.8] | −1.0 [−3.2, +1.4] |
| 3D | control | +0.9 [−0.9, +2.9] | +1.4 [−1.1, +3.9] |
| 3D | expanded | −0.5 [−2.6, +1.7] | −1.4 [−3.9, +1.1] |

- **Task success:** a single D-expanded generalises across M4 / M5 / M6 with no significant change.
- **Abstention:** it erodes mildly with larger pools (2D 90.7 → 89.8; 3D 82.8 → 75.9). For D-expanded this is much smaller than for D-control or the frozen V3 D.

## E5: M-specific fitting (conditional) — **NOT_RUN**

The pre-registered activation condition (a) required D-expanded VAL task success at M6 below M4 by ≥ 3 points with a CI excluding 0. Observed: 2D −1.0 [−3.2, +1.4] and 3D −1.4 [−3.9, +1.1]. Condition (a) fails, so no M4-only or M6-only scorer was trained.

## E2: coverage vs ranking vs abstention (VAL task roots; `E/TABLE_FAILURES_VAL.{json,txt}`)

Each outcome is classed as follows:
- **RANK_FAIL:** a known physically successful sequence was in the scored pool, but the selected top-1 failed or no repair was chosen.
- **COVER_UNKNOWN:** no known success was in the pool. This is a lower-bound notion: an unknown feasible repair may exist.

**2D (413 task roots).** Seed-averaged % of roots. "Known in pool" is the share of task roots with a known success in the top-M pool (M4 27.1, M5 35.8, M6 41.4).

| Arm | Success | Rank-fail (Y / X / no-op + abstain) | Cover-unknown (Y / X / other) |
|---|---:|---|---|
| capped M4 B4096 | 44.3 | 3.1 / 3.9 / 0.7 | 39.7 / 7.0 / 1.2 |
| frozen V3 D s0 M4 | 49.2 | 6.8 / 4.6 / 0.7 | 28.8 / 9.4 / 0.5 |
| frozen V3 D s0 M6 | 47.0 | 12.3 / 6.8 / 0.7 | 24.9 / 7.7 / 0.5 |
| D-control M4 | 52.9 | 7.1 / 3.7 / 0.4 | 25.3 / 10.3 / 0.3 |
| D-control M6 | 52.1 | 10.8 / 6.3 / 0.5 | 22.1 / 8.1 / 0.2 |
| D-expanded M4 | 55.9 | 5.3 / 4.4 / 1.4 | 21.0 / 10.4 / 1.6 |
| D-expanded M6 | 54.9 | 9.7 / 6.1 / 1.6 | 17.2 / 9.4 / 1.1 |

**3D (220 task roots):** see `E/TABLE_FAILURES_VAL.txt`. The share with a known success in the pool rises with M (56.4 / 65.0 / 70.0 %). Frozen-D Y rank-failures grow with M (5.9 → 10.5 %), while both trained arms stay at 2.7–4.1 %.

**Reading.**
- Enlarging M raises known-success coverage, but with the frozen scorer most of the added pool becomes high-confidence Y-infeasible rank-failures. The retrained arms, and most of all D-expanded, convert more of the added coverage into verified successes and abstain more often when they should.
- The largest remaining 2D class is COVER_UNKNOWN_Y (17–21 % for D-expanded): no known success in the pool and a confidently chosen infeasible endpoint. For 59–73 % of 2D task roots, no known physical success lies in the top-M pool at all.
- The next bottleneck in 2D is therefore proposal coverage (the sampler), not ranking. Under the contract this is a separate stage: a matched sampler-original vs sampler-expanded pair evaluated with a frozen D. It was not started here.

## Observational comparison with the frozen V3 model (not a matched contrast)

| | 2D task / NONE-abstain % | 3D task / NONE-abstain % |
|---|---|---|
| Capped V3 (M4 B4096, frozen D s0) | 44.3 / 87.3 | 75.0 / 86.2 |
| Frozen V3 D s0, exhaustive M4 (Phase B) | 49.2 / 79.3 | 75.0 / 82.8 |
| **D-expanded, exhaustive M4 (3 seeds)** | **55.9 / 90.7** | **78.5 / 82.8** |

On VAL, D-expanded at exhaustive M4 is the best of all configurations measured:
- **2D:** +11.6 task points over the capped V3 path with higher abstention.
- **3D:** +3.5 task points with abstention similar to the frozen exhaustive path, though below capped.

The frozen D was a single seed trained with early stopping, so this comparison is not causal.

## Inference cost (`E/TABLE_RESOURCE_COST_INFERENCE.{json,txt}`)

Wall times are per root per process, one pinned CPU, nice 10, shared hosts; GPU peak ≤ 340 MiB.

| Domain | Scored sequences / root, median M4 / M5 / M6 | Max per root (M6) | Wall / root, median / p90 / p99 / max |
|---|---|---:|---|
| 2D | 24,930 / 56,202 / 103,220 | 960,838 | 9.5 / 77.6 / 111 / 194 s |
| 3D | 1,084 / 2,262 / 3,977 | 156,146 | 0.45 / 5.7 / 16.6 / 26 s |

- **Total scoring cost** for 6 trained models on VAL was 28.5 process-hours (2D) and 1.0 (3D). The frozen V3 D pass on the laptop took 2.6 h (2D).
- **Bottleneck:** scoring is CPU-bound in Python view construction, so a production deployment at M6 needs the vectorised view builder (Phase A item 5). That optimisation was not done here; exact equivalence would have to be proven first.
- **The capped path is cheap:** 4,096 sequences, 0.23 s / root on test in V3.1-4.

## E6: exposed TEST regression and fresh cohort

**TEST configuration**, fixed by the rule registered before any 2D VAL outcome of the trained arms (commit `0f438dfb95`): D-expanded at M4 in both domains (2D VAL 55.9 vs control 52.9; 3D 78.5 vs 76.2), 3 seeds.

**Procedure.**
- **Scoring:** both arms' TEST pools were scored before the rule was applied. Scoring makes no teacher calls and reveals no outcome. Only the registered configuration was physically verified.
- **New TEST queries:** 960 in 2D (422 roots) and 297 in 3D (186 roots), on parity-passed hosts. The rest were already labelled in the V3.1-4 caches.
- **Unknown:** 0. Files: `E/TABLE_TEST_REGRESSION.{json,txt}`, `E/*_T_verify_*.jsonl.gz`, compact decisions `E/records/*_test_expanded_decisions.jsonl.gz`.

| TEST (exposed) | Capped V3 (V3.1-4, M4 B=4,096, frozen D s0–s2) | D-expanded exhaustive M4 (s0–s2) | Δ [95 % CI] |
|---|---:|---:|---|
| 2D task % (± seed SD) | 43.6 ± 2.6 | 52.0 ± 1.2 | **+8.4 [+5.4, +11.3]** |
| 2D K1 / K2 / K3 % | 72 / 61 / 12 | 71 / 70 / 26 | |
| 2D correct NONE abstain % | 92.7 | 92.9 | +0.2 [−1.3, +1.8] |
| 2D correct no-op % | 89.7 | 91.1 | +1.4 [+0.2, +2.9] |
| 3D task % | 77.3 ± 1.4 | 81.2 ± 1.9 | **+3.9 [+0.4, +7.3]** |
| 3D K1 / K2 / K3 % | 80 / 79 / 74 | 77 / 84 / 81 | |
| 3D correct NONE abstain % | 76.9 | 82.3 | +5.4 [−2.7, +12.9] |
| 3D correct no-op % | 77.6 | 86.1 | +8.5 [+3.5, +13.9] |

The capped numbers reproduce the V3.1-4 table exactly.

**What this comparison changes.** It changes the candidate pool (uncapped exhaustive M4) and the scorer (retrained with expanded evidence) together; the matched VAL experiments (E1, E3) separate the two.

**TEST interpretation.** The registered configuration improves verified task success over the capped V3 path, by +8.4 points in 2D (K3 doubles) and +3.9 in 3D. NONE abstention does not degrade, unlike frozen-model exhaustive selection on VAL. TEST is historically exposed, so this is a regression check consistent with the VAL findings, not an unbiased confirmation.

**Fresh cohort: `FRESH_CONFIRMATION_NOT_RUN`.**
- **What it would need:** a family-disjoint confirmation cohort means new scenes from the frozen 2D / 3D generators, then full teacher labelling of each root (K class, evaluation masks, known successes) before evaluation. At the size of the historical cohorts (~400 2D and ~240 3D task roots), the original production took multiple days of CPU on gvlab.
- **Why it did not run:** that does not fit a single safe overnight allocation while keeping every shared host's reserve.
- **Consequence:** no unbiased generalisation claim is made. All V3.2 numbers are VAL (development) or historically exposed TEST (regression).
