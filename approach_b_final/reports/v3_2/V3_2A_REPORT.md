# V3.2-A: exact exhaustive top-M inference with the frozen V3 model (validation only)

**Scope.** Frozen-model inference diagnostic only:
- no training, no physical teacher queries, no test split;
- nothing launched on gvlab or gvlab2; DISCO and the V3.1 branch, jobs, files and caches untouched;
- no rule tuning: every headline number uses the frozen V3 rule `{noop_gate 0.5, eta 0.3, alpha 0, beta 0, gamma 0}`, and decisions for all 72 grid rules are only stored.

This is not the final architecture. Branch `naren/approach-b-v3-2-audit`.

**Execution.**
- Laptop: RTX 5060, env `rkit-rpx-sm120`; one process pinned to 2 cores (`taskset -c 0,1`, `OMP_NUM_THREADS=2`).
- Inputs: frozen copies of task cVAE `q2init_all` s0, V3 D s0 and the p3 cost head; sha256 matches the V3.1 manifest.
- Physical status: read from the V1–V3 verify caches only. The V3.1 caches were not read (isolation rule). An unverified selection is UNRESOLVED; it is never counted as a success or a failure.

## 1. Method (`exhaustive.py`, `scripts/v32a_report.py`, `tests/test_v32.py`)

- **Proposals.** Same as V3: S1 top-6 of the 64-draw MC marginal, with the per-root CUDA generator. M4 and M5 are prefixes of M6.
- **Streaming.** `exhaustive.stream` lazily yields every ordered K1/K2/K3 sequence:
  - distinct objects, pairwise-distinct destinations, all permutations, V3 legality;
  - no B cap, no materialised pool;
  - scored in chunks of 8,192 with the unchanged `search.Scorer`.
- **One shared M6 pass.** Each sequence is scored once and tagged with the largest proposal rank it uses. It therefore belongs to the M4 / M5 / M6 pools exactly when that rank is below M.
- **Online selectors.** `exhaustive.Selectors` runs independent online selectors for all 72 rules × M = 4, 5, 6. They reproduce `xy.choose` exactly:
  - same cost;
  - admissibility p11 ≥ η;
  - identical tie-break key (rounded cost, m, D, signature);
  - no-op gate and no-op merge.
- **Per root and M, the record keeps:**
  - counts by K and the number scored;
  - admissible-pool sizes;
  - known-success coverage, plus the p11 and rank of the best known success;
  - the 72 decisions;
  - the top 32 candidates.
- **Unit tests (`tests/test_v32.py`):**
  - stream counts equal `construct.counts`, with no duplicates and all orders present;
  - the selectors equal `evaluate.select` for all 72 rules × M, including ties and chunk boundaries.

## 2. Correctness checks: all pass

| Check | 2D validation (751 roots) | 3D validation (364 roots) |
|---|---|---|
| Sequences scored (M6) vs V3.2 audit | **157,886,200 = 157,886,200**; 0 roots with a count mismatch at M4/M5/M6 | **4,339,358 = 4,339,358**; 0 mismatches |
| Uniqueness (`V32_CHECK_UNIQUE`) | OK (M4 pass) | OK |
| Shared M6 pass vs independent exhaustive M4 run | 751 roots: 0 roots with any of 72 decisions different; max \|Δp11\| 5.4e-7 | 364 roots: 0; 3.0e-7 |
| Shared M6 pass vs independent exhaustive M5 run | 100-root fixed subset: 0; 2.4e-7 | 364 roots: 0; 3.6e-7 |
| Old capped path (B = 4,096, `store="all"`) on roots where it was already exhaustive | 220 roots: identical candidate sets, max \|Δp11\| 1.1e-6, 0 decision differences (72 rules) | 293 roots: identical, 8.3e-7, 0 differences |

Δp11 is float32 batch-composition noise. No selection changed because of it.

## 3. Results under the frozen rule (validation, seed 0)

The three quantities are kept separate:
- **Proposal coverage:** is a verified known-successful sequence in the scored pool?
- **Predicted ranking:** what does the frozen scorer select, and where does it rank the known successes?
- **Physically verified success:** cache status of the selected sequence.

Rows K1–K3 count only roots with `eval_task`.

### 2D

| | Capped M4, B = 4,096 | Exhaustive M4 | M5 | M6 |
|---|---:|---:|---:|---:|
| **Coverage:** known success in pool, K1 / K2 / K3 (of 120 / 120 / 173) | 56 / 29 / **1** | 56 / 29 / **27** | 69 / 37 / 42 | 76 / 48 / **47** |
| **Ranking:** median rank of best known success by p11, K1 / K2 / K3 | — | 270 / 109 / 193 | 492 / 243 / 784 | 815 / 404 / 1,502 |
| **Ranking:** selected is a known success, K1 / K2 / K3 | — | 6 / 1 / 0 | 6 / 1 / 0 | 5 / 1 / 0 |
| **Ranking:** median p11, selected vs best known success | — | 0.889 vs 0.745 | 0.909 vs 0.740 | 0.915 vs 0.744 |
| Selections changed vs capped, K0 / K1 / K2 / K3 / NONE (all) | — | 1 / 23 / 35 / 159 / 24 (242) | 4 / 50 / 72 / 167 / 31 (324) | 5 / 69 / 92 / 172 / 36 (374) |
| NONE roots abstained (of 150) | 131 | 119 | 115 | 113 |
| Admissible pool (η 0.3), mean per root | — | 3,792 | 7,642 | 13,388 |
| **Physical status** of selected repairs: verified SUCCESS / FAIL / UNRESOLVED | 99 / 103 / 228 | 71 / 34 / 340 | 46 / 21 / 382 | 35 / 9 / 407 |
| K3 SUCCESS / FAIL / UNRESOLVED | 11 / 59 / 100 | 0 / 4 / **169** | 0 / 2 / 171 | 0 / 0 / **173** |

### 3D

| | Capped M4, B = 4,096 | Exhaustive M4 | M5 | M6 |
|---|---:|---:|---:|---:|
| **Coverage:** known success in pool, K1 / K2 / K3 (of 53 / 97 / 70) | 34 / 59 / 28 | 34 / 59 / 31 | 39 / 67 / 37 | 41 / 69 / 44 |
| **Ranking:** median rank of best known success, K1 / K2 / K3 | — | 27 / 14 / 18 | 41 / 22 / 48 | 55 / 32 / 80 |
| **Ranking:** selected is a known success, K1 / K2 / K3 | — | 4 / 5 / 1 | 4 / 4 / 1 | 3 / 3 / 1 |
| **Ranking:** median p11, selected vs best known success | — | 0.922 vs 0.786 | 0.928 vs 0.764 | 0.931 vs 0.763 |
| Selections changed vs capped, K0 / K1 / K2 / K3 / NONE (all) | — | 0 / 0 / 4 / 4 / 9 (17) | 2 / 12 / 37 / 24 / 12 (87) | 6 / 18 / 51 / 38 / 14 (127) |
| NONE roots abstained (of 58) | 50 | 48 | 45 | 44 |
| **Physical status:** SUCCESS / FAIL / UNRESOLVED | 146 / 49 / 46 | 144 / 40 / 59 | 107 / 30 / 109 | 87 / 22 / 138 |

The capped baseline's UNRESOLVED counts are relative to the V1–V3 caches only. V3.1-C verified the same capped selections on gvlab: task success 2D 44.3 %, 3D 75.0 %, 0 unverified. Those caches are not read here.

### Findings

1. **Exhaustive inference is exact and equivalent to V3 wherever V3 was already complete.**
   - Every candidate is scored once.
   - The shared pass equals independent runs for all 72 rules.
   - The old path is reproduced on every root it could complete.
2. **Coverage rises sharply in 2D K3, where the cap was binding.**
   - Known-success-in-pool goes from 1 (capped) to 27 (exhaustive M4) to 47 (M6) of 173.
   - 3D gains are moderate: K3 28 → 44 of 70.
3. **Coverage does not translate into selecting known successes.**
   - The frozen scorer selects a known success on 0 / 173 2D K3 roots at every M.
   - The best known success's median rank worsens with pool size: 2D K3 193 → 1,502; 3D K3 18 → 80.
   - The selected candidates carry higher predicted p11 (about 0.89–0.93) than the known successes (about 0.74–0.79).
4. **Whether this is better or worse is not yet determined.**
   - The newly selected sequences are almost all UNRESOLVED; in 2D at M6, 173 / 173 K3 selections are unresolved.
   - Either the scorer has found genuinely feasible alternatives, or the larger pools (2D mean admissible pool 3.8k → 13.4k at η 0.3) give it more confident false positives. The latter is the multiple-comparison effect seen in V3.1-E.
   - The fall in *verified* SUCCESS counts reflects only the move to unverified sequences. It is not evidence of degradation.
5. **NONE abstention falls with pool size:**
   - 2D: 131 → 119 → 115 → 113 of 150;
   - 3D: 50 → 48 → 45 → 44 of 58.

   Each extra repair on a NONE root is unresolved until verified.
6. **Predicted ranking quality, not proposal coverage, is the open question for exhaustive inference.** Only physical verification of the list in §5 can settle it.

## 4. Runtime and memory (laptop, one process, 2 CPU cores + RTX 5060)

| | 2D shared M6 pass | 2D exhaustive M4 only | 3D shared M6 pass | Capped B = 4,096 (2D / 3D) |
|---|---:|---:|---:|---:|
| Total | 2.64 h | 0.68 h | 4.1 min | 2.1 min / 0.5 min |
| Per root median / P99 / max | 5.9 / 56.0 / 60.2 s | — | 0.19 / 6.6 / 9.1 s | 0.20 / — / 0.37 s (2D) |
| Throughput | 16.6k seq/s | 16.4k seq/s | 17.7k seq/s | — |
| GPU peak (chunk 8,192) | 338 MiB | 339 MiB | 240 MiB | — |
| Process RSS | ≈ 1.5 GB (bounded; no pool stored) | | | |

The independent M5 check on 100 roots took 692 s. Pools are never stored: only the per-rule argmins and the per-M top 32 are kept.

2D M5 / M6 is an offline-only setting at this throughput (P99 near 1 minute per root). As the audit found, the bottleneck is Python view building, not GPU compute.

## 5. Newly selected repairs requiring independent physical verification

Files:
- `reports/v3_2/v3_2a/2d/NEW_SELECTIONS_TO_VERIFY.jsonl`
- `reports/v3_2/v3_2a/3d/NEW_SELECTIONS_TO_VERIFY.jsonl`

Each line is one (M, root) selection under the frozen rule that differs from the capped baseline and is absent from the V1–V3 caches. Fields: `domain`, `M`, `root_id`, `K_legacy`, `seq`, `p11`, `py`, `px`, `capped_baseline_seq`, `masks`.

| | Entries (M4 / M5 / M6) | Unique (root, sequence) pairs | Roots | Unique pairs by K: K0 / K1 / K2 / K3 / NONE | Sequence length 1 / 2 / 3 moves |
|---|---|---:|---:|---|---|
| 2D | 937 (242 / 323 / 372) | **644** | 372 | 8 / 102 / 133 / 340 / 61 | 26 / 84 / 534 |
| 3D | 208 (17 / 78 / 113) | **145** | 114 | 5 / 14 / 54 / 46 / 26 | 6 / 44 / 95 |

**Total: 789 unique teacher evaluations** (X then Y per sequence).

Before spending teacher queries, the list should be de-duplicated against the V3.1 gvlab caches. Some sequences may already have been verified there, for example by V3.1-C small-B runs.

Verification is not performed here, as instructed.

## 6. Implications (no action taken)

- **Exhaustive inference removes the 2D construction cap as a coverage bottleneck,** at a 2D latency cost of about 30× per root at M6 (median 5.9 s vs 0.2 s).
- **Its value depends entirely on the physical outcome of the selections above.**
  - If they mostly fail, the frozen scorer's ranking does not transfer to the much larger candidate distribution: it was trained on capped, iteratively constructed candidates. This would motivate candidate-matched training (V4), with hard negatives drawn from the high-p11 tail of exhaustive pools.
  - If they mostly succeed, exhaustive M4–M6 inference is a direct gain with no retraining.
- **Rule choice stays frozen.** Re-tuning on validation outcomes is deferred until V3.1 tuning is closed.
