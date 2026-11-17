# V3.3 physically verified VALIDATION results — S-control vs S-expanded scratch samplers

**Split.** VALIDATION only. No TEST and no fresh-cohort row was used.

**Evidence.**
- Every number is a physically verified top-1 outcome from the unchanged X/Y teachers on parity-passed hosts.
- There are **0 UNKNOWN** selected repairs in every reported arm; UNKNOWN would never count as failure.
- Machine-readable table: `TABLE_PHYSICAL_VAL.json` (`scripts/v33_eval.py table`). Slim per-root records: `records/`. New labels: `labels/`.

## Fixed protocol

| Item | Setting |
|---|---|
| Sampler | scratch `TaskCVAE` `scratch_all`, seeds 0 / 1 / 2 per arm |
| Proposals | S1 top-M of 64 MC draws, per-root generator seed 0, girish CUDA for every sampler |
| Construction | exact exhaustive **M4**, no B cap (`exhaustive.py run`, mmax 4) |
| Scorer | frozen V3.2 **D-expanded s0**, sha256 2D `0fa126da…`, 3D `c02afcbc…`; hash-verified on both hosts; no retraining |
| Rule | `{noop_gate 0.5, eta 0.3, alpha 0, beta 0, gamma 0}`, unchanged |
| Roots | all VAL roots (2D 751, 3D 364). Task roots 413 / 220 (K1 120 / 53, K2 120 / 97, K3 173 / 70); NONE 150 / 58; no-op 188 / 85 |
| Statistics | per-root average over the 3 sampler seeds; paired root-cluster bootstrap with 2,000 resamples |
| Reference | `q2init_all` s0 + D-expanded s0, exhaustive M4 on the same roots. Taken from the existing verified V3.2 records (`E_records/expanded_s0_M6_val`, M4 decisions). Single seed. Different initialization **and** training data: **not** a matched ablation |

## Teacher parity (before any new label)

Each host re-ran the pre-declared V3.2 parity sample with no cache and compared it against the reference labels (`PARITY_V33.json`):
- laptop 2D 30/30, laptop 3D 16/16, girish 2D 30/30, girish 3D 16/16 identical;
- the sample includes successful and failed X and Y cases;
- result: PASS on all four.

## Pilot gate (pre-registered)

Seed 0 of both arms, all VAL roots:

| Domain | Δ task (S-expanded − S-control) | Gate outcome |
|---|---|---|
| 2D | +2.7 [−1.0, +6.3] | not STOP_NULL → continue |
| 3D | −0.5 [−5.0, +3.6] | not STOP_NULL (upper bound ≥ +2.0) → continue |

Sampler seeds 1 and 2 were therefore scored and verified in both domains.

## Primary result (3 sampler seeds)

| Domain | Arm | Task success | K1 / K2 / K3 | Per-seed task | Correct NONE abstention | Per-seed abstention | NONE → failed repair | Correct no-op |
|---|---|---|---|---|---|---|---|---|
| 2D | S-control | 55.1 % | 65 / 72 / 37 | 54.5 / 55.9 / 55.0 | 94.9 % | 95.3 / 94.7 / 94.7 | 2.0 % | 96.8 % |
| 2D | S-expanded | 55.0 % | 64 / 73 / 36 | 57.1 / 55.0 / 53.0 | 95.1 % | 95.3 / 95.3 / 94.7 | 2.0 % | 96.8 % |
| 2D | q2init ref (1 seed) | 56.4 % | 68 / 68 / 40 | 56.4 | 94.0 % | 94.0 | 3.3 % | 96.8 % |
| 3D | S-control | 78.9 % | 73 / 83 / 78 | 78.6 / 80.5 / 77.7 | 78.7 % | 77.6 / 77.6 / 81.0 | 21.3 % | 84.7 % |
| 3D | S-expanded | 79.1 % | 75 / 82 / 77 | 78.2 / 79.5 / 79.5 | 79.3 % | 79.3 / 79.3 / 79.3 | 20.7 % | 84.7 % |
| 3D | q2init ref (1 seed) | 80.5 % | 77 / 80 / 83 | 80.5 | 82.8 % | 82.8 | 17.2 % | 84.7 % |

### Matched contrast: S-expanded − S-control (points, 95 % CI)

| Domain | Task | K1 | K2 | K3 | NONE abstention | No-op | Known-success coverage |
|---|---|---|---|---|---|---|---|
| 2D | **−0.1 [−2.1, +2.0]** | −1.1 [−5.3, +2.8] | +1.4 [−1.9, +4.7] | −0.4 [−3.7, +3.1] | +0.2 [+0.0, +0.7] | 0.0 | +1.2 [−0.8, +3.0] |
| 3D | **+0.2 [−2.6, +2.6]** | +2.5 [−3.1, +7.5] | −0.3 [−4.1, +3.4] | −1.0 [−5.2, +2.9] | +0.6 [−1.7, +3.4] | 0.0 | +0.2 [−1.2, +1.5] |

**Decision (registered rule): NULL in both domains.** Neither task CI excludes 0. The seed-0 2D gain (+2.7) did not replicate: seeds 1 and 2 gave 0.0 and −2.0 points.

### Reference only: scratch arm − q2init_all (different init and data; one reference seed)

| Domain | Comparison | Task | NONE abstention | Known-success coverage |
|---|---|---|---|---|
| 2D | S-control − q2init | −1.3 [−4.8, +1.9] | +0.9 [−0.4, +2.7] | −7.5 [−10.3, −4.8] |
| 2D | S-expanded − q2init | −1.4 [−4.8, +1.8] | +1.1 [+0.0, +2.9] | −6.3 [−8.9, −3.9] |
| 3D | S-control − q2init | −1.5 [−5.6, +2.6] | −4.0 [−10.9, +2.3] | −2.3 [−4.4, −0.3] |
| 3D | S-expanded − q2init | −1.4 [−5.0, +2.4] | −3.4 [−9.2, +2.3] | −2.1 [−4.1, −0.3] |

- Both scratch samplers place known successes into the M4 pool significantly less often than the Q2-pretrained production sampler.
- Their verified task success is 1.3–1.5 points lower, but not significantly so.
- The known-success measure is biased toward q2init, because most known VAL labels came from verifying its selections.

## Calibration (selected repairs, all seeds)

| Domain | Arm | Selected repairs | Mean selected p11 | Verified success rate | Over-confidence |
|---|---|---|---|---|---|
| 2D | S-control | 1,252 | 0.876 | 0.571 | 0.305 |
| 2D | S-expanded | 1,250 | 0.879 | 0.568 | 0.311 |
| 2D | q2init ref | 419 | 0.874 | 0.578 | 0.296 |
| 3D | S-control | 706 | 0.902 | 0.782 | 0.120 |
| 3D | S-expanded | 705 | 0.908 | 0.784 | 0.124 |
| 3D | q2init ref | 233 | 0.904 | 0.803 | 0.102 |

The frozen D-expanded scorer is about equally over-confident on all three samplers' pools. The sampler swap did not create a new calibration failure, so there is no reason to retrain D (not done; out of scope).

## Failure decomposition (failed VAL task roots, seed-mean counts)

A failure is **RANK_** when a known success lies in that run's M4 pool and **COVER_** otherwise. Known successes now include the V3.3 labels; this is a lower bound.

| Domain | Arm | Failed task roots | RANK: Y-infeasible pick | RANK: X-infeasible pick | RANK: no-op / abstain | COVER: Y fail | COVER: X fail | COVER: no-op / abstain |
|---|---|---|---|---|---|---|---|---|
| 2D | S-control | 185.3 | 57.0 | 47.7 | 5.7 | 54.3 | 17.0 | 3.7 |
| 2D | S-expanded | 185.7 | 65.3 | 44.3 | 6.0 | 48.0 | 18.3 | 3.7 |
| 2D | q2init ref | 179.0 | 73.0 | 55.0 | 8.0 | 34.0 | 9.0 | 1.0 |
| 3D | S-control | 46.3 | 9.7 | 16.7 | 10.0 | 1.7 | 7.3 | 1.0 |
| 3D | S-expanded | 46.0 | 11.3 | 15.0 | 10.0 | 2.3 | 6.3 | 1.0 |
| 3D | q2init ref | 43.0 | 10.0 | 17.0 | 11.0 | 0.0 | 5.0 | 0.0 |

- **2D:** the scratch samplers lose about 25–30 roots to *coverage* (no known success in the pool) that q2init covers. They lose fewer roots to *ranking*, because their pools contain fewer high-scoring infeasible decoys. The two effects nearly cancel, which is why task success differs only by 1.3–1.4 points.
- **S-expanded vs S-control:** S-expanded moves about 5 roots from COVER to RANK failures (better pools, same scorer mistakes), consistent with its +1.2 coverage, but this does not convert into verified successes.

## Query census and compute

| | 2D | 3D |
|---|---|---|
| Repair selections (6 runs) / unique (root, ordered sequence) | 2,502 / 1,510 | 1,411 / 774 |
| Labels reused from V3.2 caches | 382 | 303 |
| **New** teacher queries (laptop / girish) | **1,128** (536 / 592) | **471** (338 / 133) |
| New-query resolution | 100 % EVALUATED, 0 unresolved | 100 % EVALUATED, 0 unresolved |
| Teacher CPU time (new queries) | 9.7 CPU-h | 7.1 CPU-h |

**Labelling rules.** Y is shared per canonical endpoint; X is never reused across orders. Conflicting decided labels across caches would abort the merge (`v32b_phys.labels`); none occurred.

**Exhaustive M4 scoring per root** (girish CPU + shared 3080 Ti GPU):
- 2D: median 3.9 s, p99 about 40 s; median 26–28 k sequences scored.
- 3D: median 0.18 s, p99 6.4 s; median about 1.1 k sequences.

**Total scoring compute.** 12 runs in about 35 minutes of wall time on the shared GPU (up to 20 concurrent processes); peak ≤ 1 GB of GPU memory per process.
- One 2D shard hit a GPU out-of-memory error with 20 concurrent processes. Output is per root, so it resumed without loss.

**Not comparable.** The q2init reference latency (9.2 s median in 2D) comes from its M6 V3.2 run.

## Figures

- `figures/physical_val.png`: per-seed and mean task success and NONE abstention.
- `figures/failure_decomposition.png`
- `figures/proposal_coverage_vs_M.png`
- `figures/training_curves.png`

## Robustness check

Registered to run only if the primary decision was SUPPORTED or HARMFUL. The decision was NULL in both domains, so it was **not run**. No other D-expanded scorer seeds were evaluated.
