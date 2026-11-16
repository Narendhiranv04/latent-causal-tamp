# V3.1-4 — Final test experiments with frozen models, thresholds and budgets

**Milestone.** V3.1-4 is complete. Every configuration below was frozen on validation before the test was touched: the models, the rule `{noop_gate 0.5, eta 0.3, alpha 0, beta 0, gamma 0}`, M = 4, and the budgets. All three arms were then run on the full test split, and **every selected repair was physically verified (0 unverified).** No fresh cohort was evaluated; see *Fresh cohort and exposure* below.

## Changes

- `scripts/v314_test_table.py` is a torch-free test table builder. It reads the selection files, the verify caches and the snapshot labels.
  - For each arm and seed it reports task success, K1–K3, repair, no-op and abstain. Unverified selections are counted and never imputed.
  - It gives the seed mean ± SD and a paired root-cluster bootstrap (2,000 resamples) against the named reference arm.
- `scripts/v314_fig.py` draws the budget curves and the goal / seed bar charts.
- `scripts/v314_gpu_girish.sh` is the GPU driver from earlier in V3.1-4.
- `scripts/v314_verify/` holds the verification launchers and the work-splitting helpers for the laptop, gvlab and girish-laptop.
  - Work splitting uses the existing `V3_PART` root-hash shards, a 2D tail hand-over (`stop_when_done.py`) and a pooled 3D rebalance (`rebalance3d.py`).
- No model, rule or teacher code changed. Construct and evaluate are at `c9da937d` and `18fb3814` on all three hosts.

## Compute

| Stage | Host | Time (IST, 16–17 Nov) |
|---|---|---|
| GPU inference (all test arms) | girish-laptop (RTX 3080 Ti 16 GB); user-authorised | finished 20:58 |
| Physical verification, 2D | laptop 12 workers, gvlab 9, girish-laptop 4 → 19 | 23:07 – 01:23 |
| Physical verification, 3D | laptop 11 → 12 → 14 workers, gvlab 7, girish-laptop 20 (briefly) | 23:07 – 01:21 |

- **Unique teacher queries:** 5,818 in 2D (576 roots) and 2,258 in 3D (317 roots).
- **Executed queries:** 9,628, including 1,552 2D queries that ran on two hosts during the hand-over.
- **Load on shared machines:**
  - gvlab ran at nice 10 on at most 16 of its 24 cores. DISCO and other users' processes were never touched, and its GPUs were not used.
  - The laptop's worker count was capped by free memory.
- **Parity of the girish-laptop teacher legs:**
  - girish ran exact copies of the laptop teacher environments: CPython 3.13.11; numpy 2.4.6 and scipy 1.18.1 for 2D; mujoco 3.16.0 and numpy 2.2.6 for 3D.
  - Before counting any girish result, it re-verified laptop-verified selections with no cache: 40 / 40 identical labels in 2D and 14 / 14 in 3D (`PARITY_GIRISH_TEACHER.json`).
  - In production, all 1,552 cross-host duplicate 2D queries agreed (874 girish vs laptop, 678 girish vs gvlab; `CROSS_HOST_DUPLICATES_2D.json`).
- **Parity of the girish GPU inference:**
  - Validation: 2,230 / 2,230 identical selections (V3.1-A, `v3_1a_phys/PARITY_GIRISH_VS_GVLAB.json`).
  - Test: the re-run V3 primary seeds 0–2 and V2 exp12 needed **0** new teacher queries, because every selection already existed in the V3-6 caches.

## Data

- **Split and labels:** the test split of snapshot `abf_9de85710c2a7103f`, with the same evaluation masks as V3-6.
  - 2D: 749 roots. Task-evaluable 412 (K1 120 / K2 120 / K3 172), NONE-abstain-evaluable 150, no-op-evaluable 187.
  - 3D: 370 roots. Task-evaluable 241 (K1 53 / K2 86 / K3 102), NONE-abstain-evaluable 62, no-op-evaluable 67.
- **Selections:** `v3_1_4/selections/{2d,3d}/` (gzip).
- **New physical labels:** `v3_1_4/verify/{laptop,gvlab,girish}_v314_{2d,3d}.jsonl.gz`.
- **Tables:** `v3_1_4/TABLE_TEST_V314.{json,txt}`.
- **Figures:** `v3_1_4/budget_curves_test.png` and `v3_1_4/goal_and_seed_test.png`.

## Validation

- **Unverified selections:** 0 in every arm, seed and domain.
- **V3-6 reproduction:**
  - Seed-0 E, G and DIRECT and the 3-seed V3 primary are identical to the V3-6 table: 2D 43.6 / 43.7 / 40.8 / 30.6 and 3D 77.3 / 80.1 / 61.4 / 68.0.
  - V2 exp12 seed 0 is 27.7 (2D) and 50.2 (3D), consistent with V3-6's 3-seed 25.6 and 52.4.
- **Retrained versus frozen sampler:** the V3.1-A retrained `q2init_all` sampler (3 seeds) gives 43.3 (2D) and 77.9 (3D), within seed noise of the frozen primary's 43.6 and 77.3.

## Findings (test, all physically verified)

### 1. Compute-matched budget curve (seed 0; reference V2 iterative exp12)

| Domain | Arm | Scored / root (median) | Latency / root | Task % | Δ vs V2 exp12 [95 % CI] |
|---|---|---:|---:|---:|---|
| 2D | V3 B=128 | 128 | 0.02 s | 32.0 | +4.4 [−0.2, +9.2] |
| 2D | V3 B=512 | 512 | 0.04 s | 38.6 | +10.9 [+6.3, +15.3] |
| 2D | V3 B=2,048 | 2,048 | 0.12 s | 41.5 | +13.8 [+9.5, +18.7] |
| 2D | V3 B=4,096 | 4,094 | 0.23 s | 43.9 | +16.3 [+11.4, +21.1] |
| 2D | V2 exp3 | 108 | 0.04 s | 23.3 | −4.4 [−7.5, −1.2] |
| 2D | V2 exp12 | 408 | 0.14 s | 27.7 | — |
| 2D | V2 exp48 | 1,632 | 0.51 s | 23.5 | −4.1 [−7.3, −1.0] |
| 3D | V3 B=128 | 128 | 0.01 s | 58.9 | +8.7 [+0.8, +16.2] |
| 3D | V3 B=512 | 508 | 0.03 s | 71.0 | +20.7 [+13.7, +27.8] |
| 3D | V3 B=2,048 | 1,292 | 0.06 s | 77.6 | +27.4 [+20.3, +34.4] |
| 3D | V3 B=4,096 | 1,292 | 0.06 s | 79.3 | +29.0 [+21.6, +36.5] |
| 3D | V2 exp3 | 36 | 0.02 s | 34.4 | −15.8 [−22.0, −10.0] |
| 3D | V2 exp12 | 124 | 0.10 s | 50.2 | — |
| 3D | V2 exp48 | 456 | 0.44 s | 55.6 | +5.4 [+0.4, +10.8] |

- **V3 dominates V2 at every matched budget, in both domains.**
  - 3D: V3 at B = 128 (0.01 s) already beats V2's largest budget, exp48 (0.44 s), at 58.9 vs 55.6 %.
  - 2D: V3 at B = 128 is +4.4 points over V2 exp12 while scoring about a third as many sequences. That interval just touches 0; from B = 512 up, every interval excludes 0.
- **More V2 search does not help in 2D.** Exp48 is 4.1 points worse than exp12: abstention falls from 94.7 % to 88.7 %, and the larger pool yields more high-probability non-solutions. This matches the V3.2-A selector finding.
- **3D unique candidates saturate at about 1,292 per root** for B ≥ 2,048, so B = 2,048 and B = 4,096 cost the same in 3D.

### 2. Matched goal / task-conditioning ablation (V3 D, B = 4,096, seeds 0–2; reference `q2init_all`)

| Domain | Sampler | Task % (mean ± SD) | Δ [95 % CI] |
|---|---|---:|---|
| 2D | q2init_all | 43.3 ± 0.5 | — |
| 2D | no goal | 43.5 ± 2.1 | +0.2 [−1.7, +2.1] |
| 2D | no task | 42.8 ± 1.8 | −0.5 [−2.8, +1.8] |
| 3D | q2init_all | 77.9 ± 1.3 | — |
| 3D | no goal | 75.9 ± 1.8 | −1.9 [−4.2, +0.6] |
| 3D | no task | 76.1 ± 2.2 | −1.8 [−4.7, +0.8] |

- **No verified benefit from goal or task conditioning on test.** This replicates validation (V3.1-A: 2D −1.2 / −1.1, 3D −0.5 / +0.8). The 3D point estimates lean slightly negative, but both intervals include 0.
- **The V3-6 "goal-ablated control" result was confounded.** That control was a differently trained sampler and showed −4.8 (2D) and −2.6 (3D). It should not be cited as evidence for goal conditioning.

### 3. Coupled D vs E / G / DIRECT, three seeds (task cVAE, B = 4,096; reference V3 D)

| Domain | Scorer | Task % (s0 / s1 / s2) | Mean ± SD | Δ vs D [95 % CI] | K3 % | Correct abstain % |
|---|---|---|---:|---|---:|---:|
| 2D | D (coupled, primary) | 43.9 / 40.3 / 46.6 | 43.6 ± 2.6 | — | 12 | 92.7 |
| 2D | E (uncoupled) | 43.7 / 41.3 / 41.7 | 42.2 ± 1.0 | −1.4 [−4.0, +1.1] | 12 | 96.0 |
| 2D | G (order-invariant) | 40.8 / 35.7 / 42.2 | 39.6 ± 2.8 | −4.0 [−6.7, −1.4] | 8 | 92.9 |
| 2D | DIRECT | 30.6 / 28.4 / 34.7 | 31.2 ± 2.6 | −12.4 [−15.7, −9.0] | 7 | 27.1 |
| 3D | D (coupled, primary) | 79.3 / 75.9 / 76.8 | 77.3 ± 1.4 | — | 74 | 76.9 |
| 3D | E (uncoupled) | 80.1 / 80.9 / 73.9 | 78.3 ± 3.1 | +1.0 [−2.1, +4.0] | 79 | 79.0 |
| 3D | G (order-invariant) | 61.4 / 57.3 / 63.1 | 60.6 ± 2.4 | −16.7 [−21.7, −12.0] | 44 | 89.2 |
| 3D | DIRECT | 68.0 / 65.6 / 62.2 | 65.3 ± 2.4 | −12.0 [−16.6, −7.6] | 52 | 28.0 |

- **The coupling term itself is not supported on test.** With three seeds, D and E are statistically indistinguishable: 2D −1.4, 3D +1.0, both intervals spanning 0. V3-6's seed-0 reading agrees (E 43.7 / 80.1).
- **Order-aware sequence scoring is strongly supported.** The order-invariant G loses 4.0 points in 2D and 16.7 in 3D, and the loss concentrates on K3 (3D 44 vs 74 %).
- **DIRECT fails mainly on abstention, not just success.** Correct NONE abstention collapses to 27–28 % (vs 77–93 % for the energy scorers), and task success drops 12 points in both domains.
- **Seed spread is 1–3 points** for every scorer. Single-seed differences below about 4 points should not be interpreted.

### Fresh cohort and exposure

- **No genuinely untouched cohort was evaluated.**
  - Doing so requires new roots from the existing generators, then full teacher labelling of each: K, evaluation masks and known solutions. Only then could V3 and V2 inference and physical verification be run.
  - At the cohort size needed for the intervals above (about 400 2D and 240 3D task roots), the original cohorts took multi-day CPU production.
  - Under the V3.1 compute rules (gvlab only, DISCO priority; gvlab CPUs were busy for most of V3.1), it was not feasible inside V3.1-4.
- **Exposure statement.**
  - The test roots were used for V1 / V2 reporting and for the V3-6 test table.
  - V3.1-4 added only pre-specified, validation-frozen arms on those roots. No model, rule, budget or threshold was chosen, re-tuned or discarded on test, and every arm run is reported.
  - The residual risk is design-level: earlier versions were developed with knowledge of test-split behaviour. These results are therefore strong within-split evidence, not an untouched-cohort estimate.
- **Recommendation.** A fresh cohort of about 400 / 240 task roots is the single remaining step needed for an unbiased headline number. The analysis pipeline (`v314_test_table.py`) runs on it unchanged.

## Git

- Branch `naren/approach-b-v3-1-validation`. This commit adds:
  - `reports/v3_1/V3_1_4_REPORT.md` and `reports/v3_1/v3_1_4/` (tables, figures, selections, new physical labels, parity);
  - `scripts/v314_test_table.py`, `scripts/v314_fig.py` and `scripts/v314_verify/`.

## Next stage

V3.1-5: the comprehensive final report and the reproducibility manifest.
