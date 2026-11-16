# V3.2 exhaustive top-M feasibility audit (read-only)

**Scope.** This is a counting, coverage and feasibility audit only. No implementation, no training, no physical teacher queries, no test-split outcomes. Branch `naren/approach-b-v3-2-audit` (from V3.1 `5dde6c0aa9`; the V3.1 and DISCO branches are untouched).

**Execution.** The laptop, as authorised by the user for this audit:
- RTX 5060 (env `rkit-rpx-sm120`, torch 2.10+cu128, used read-only) for the single proposal pass per root, which reproduces V3's CUDA random-number stream;
- 27 CPU workers for exact counting and coverage.

Inputs are read-only copies of the frozen V3 artifacts, all sha256-matched to the V3.1 manifest:
- task cVAE `q2init_all` s0/s1/s2;
- V3 D s0 (throughput benchmark only);
- V3 snapshot `abf_v3_e8a496bc66266fca` (TRAIN labels = base + V2 + V3-4; validation rows = base);
- Q2 feature scalers.

Nothing was launched on gvlab or gvlab2.

**Method.**
- **Proposals.** Frozen S1 rule: top-M of the 64-draw Monte-Carlo destination marginal, with V3's per-root generator seeding. One pass gives top-6, and top-4 / top-5 are its prefixes, because the latent draws do not depend on M.
- **Parity.** The M = 4 prefix equals the proposal sets recorded by V3.1 on gvlab for **751 / 751** (2D) and **364 / 364** (3D) validation roots (`PARITY_M4.json`).
- **Counting.** Exact counts of ordered K1 / K2 / K3 sequences: distinct objects, pairwise-distinct destinations, all permutations kept, legality as in V3. Computed by inclusion–exclusion over destination-set overlaps (`construct.counts`); nothing is materialised and there is no B cap.
- **Coverage.** Known-assignment ingredient recall: all actions of ≥ 1 verified X = 1, Y = 1 assignment are in the proposal set, on K1–K3 roots, from existing labels only. Without a cap this also means every order of that assignment is in the exhaustive pool, so it is a **lower bound** on known-success coverage.
- **Caveat.** TRAIN recall is in-sample (the cVAE was trained on those assignments); validation is the honest estimate.

## 1. Exact candidate counts per root (seed 0; seeds 1–2 within ±5 % on medians, `COUNT_SUMMARY.json`)

Roots: 2D 3,500 TRAIN / 751 validation; 3D 1,766 / 364. Movable objects per root (median / P90 / max):
- 2D TRAIN 9 / 18 / 19; validation 10 / 18 / 19.
- 3D TRAIN 4 / 7 / 12; validation 4 / 7 / 11.

| 2D validation | K1 med / max | K2 med / P99 / max | K3 med / P99 / max | Total median | P90 | P99 | Max | Total (split) | Roots > 4,096 | Roots > 65,536 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| M4 | 40 / 76 | 1,168 / 4,693 / 4,848 | 23,784 / 234,018 / 257,652 | 24,930 | 170,716 | 238,802 | 262,576 | 4.03e7 | 71 % | 30 % |
| M5 | 50 / 95 | 1,912 / 7,530 / 7,704 | 54,240 / 491,529 / 528,972 | 56,202 | 368,030 | 499,155 | 536,771 | 8.59e7 | 72 % | 45 % |
| M6 | 60 / 114 | 2,816 / 11,001 / 11,236 | 100,344 / 889,200 / 949,488 | 103,220 | 694,180 | 900,315 | 960,838 | 1.58e8 | 76 % | 57 % |

| 2D TRAIN | Total median | P90 | P99 | Max | Total (split) | Roots > 4,096 |
|---|---:|---:|---:|---:|---:|---:|
| M4 | 21,002 | 166,498 | 237,828 | 302,098 | 1.77e8 | 69 % |
| M5 | 43,917 | 364,839 | 496,451 | 613,287 | 3.79e8 | 72 % |
| M6 | 79,985 | 686,758 | 888,895 | 1,065,670 | 6.99e8 | 75 % |

| 3D validation | K1 med / max | K2 med / P99 / max | K3 med / P99 / max | Total median | P90 | P99 | Max | Total (split) | Roots > 4,096 | Roots > 65,536 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| M4 | 16 / 44 | 162 / 1,217 / 1,548 | 906 / 26,829 / 42,876 | 1,084 | 10,366 | 28,133 | 44,468 | 1.20e6 | 20 % | 0 % |
| M5 | 20 / 55 | 262 / 1,985 / 2,446 | 1,980 / 61,335 / 86,406 | 2,262 | 21,269 | 63,370 | 88,907 | 2.44e6 | 27 % | 1 % |
| M6 | 24 / 66 | 383 / 2,910 / 3,548 | 3,570 / 111,920 / 152,532 | 3,977 | 37,209 | 114,890 | 156,146 | 4.34e6 | 49 % | 4 % |

| 3D TRAIN | Total median | P90 | P99 | Max | Total (split) | Roots > 4,096 |
|---|---:|---:|---:|---:|---:|---:|
| M4 | 1,216 | 10,248 | 26,722 | 53,206 | 5.90e6 | 23 % |
| M5 | 2,412 | 20,353 | 54,382 | 111,566 | 1.19e7 | 30 % |
| M6 | 4,206 | 35,997 | 97,187 | 205,798 | 2.09e7 | 53 % |

K3 dominates: it is about 95 % of every 2D pool and about 85–95 % of 3D pools. The B = 4,096 cap binds on about 70 % of 2D roots already at M4, and on 20–49 % of 3D roots.

## 2. Known-assignment ingredient recall (validation = honest; seed 0, seeds 1–2 in brackets)

| | All K1–K3 | K1 | K2 | K3 | (seeds 1 / 2, all) |
|---|---:|---:|---:|---:|---|
| 2D M4 | 27.7 % | 47.9 | 24.6 | 16.0 | 28.5 / 29.2 |
| 2D M5 | 36.6 % | 59.0 | 31.4 | 24.9 | 36.6 / 33.7 |
| 2D M6 | **42.3 %** | 65.0 | 40.7 | **27.8** | 41.6 / 39.4 |
| 3D M4 | 56.6 % | 64.2 | 61.5 | 44.3 | 62.1 / 55.7 |
| 3D M5 | 65.3 % | 73.6 | 69.8 | 52.9 | 67.6 / 63.5 |
| 3D M6 | **70.3 %** | 77.4 | 71.9 | **62.9** | 72.6 / 68.0 |

Reading the recall numbers:
- TRAIN recall is in-sample, for reference only: 2D 48 / 55 / 62 % and 3D 83 / 88 / 90 % for M4 / M5 / M6.
- **Cost of the cap at M4.** With the B = 4,096 cap, V3.1's validation run had the known successful order in the scored pool for 21.3 % (2D) and 55.3 % (3D) of roots. Exhaustive M4 raises that to 27.7 % / 56.6 %. So the cap costs about 6 points in 2D, mostly at K3, and almost nothing in 3D.
- **Gain from larger M.** Going to M6 adds another 15 points in 2D (K3: 16 → 28 %) and 14 points in 3D (K3: 44 → 63 %).
- **These are lower bounds.** Only verified *known* assignments count, and coverage is not success: a larger pool also offers the scorer more confident false positives (V3.1 NONE diagnostic: false-positive roots had a median of 11–30 admissible candidates vs 0 on correctly abstained roots).

## 3. Throughput and memory (`BENCH.json`)

**Measured on the laptop RTX 5060, frozen V3 D, unchanged `search.Scorer`.**
- Chunks of 8,192 on the 6 largest validation roots: **17,906 seq/s (2D) and 19,471 seq/s (3D)**.
- Peak GPU memory 338 / 239 MiB per chunk.
- Building sequences runs at about 0.9–1.0 M seq/s, so the scorer, and specifically its Python view building, is the bottleneck, not GPU compute.

| Projected exhaustive scoring at the measured rate | Median root | P99 root | Worst root | Whole split | Full pool as 26-byte binary records |
|---|---:|---:|---:|---:|---:|
| 2D validation M4 / M5 / M6 | 1.4 / 3.1 / 5.8 s | 13 / 28 / 50 s | 15 / 30 / 54 s | 0.6 / 1.3 / 2.5 h | 1.0 / 2.2 / 4.1 GB |
| 2D TRAIN M4 / M5 / M6 | 1.2 / 2.5 / 4.5 s | 13 / 28 / 50 s | 17 / 34 / 60 s | 2.8 / 5.9 / 10.9 h | 4.6 / 9.8 / 18.2 GB |
| 3D validation M4 / M5 / M6 | 0.06 / 0.12 / 0.20 s | 1.4 / 3.3 / 5.9 s | 2.3 / 4.6 / 8.0 s | 1 / 2 / 4 min | 0.03 / 0.06 / 0.11 GB |
| 3D TRAIN M4 / M5 / M6 | 0.06 / 0.12 / 0.22 s | 1.4 / 2.8 / 5.0 s | 2.7 / 5.7 / 10.6 s | 5 / 10 / 18 min | 0.15 / 0.31 / 0.54 GB |

The 26-byte binary record holds 3 object ids, 3 destinations, p11, P(Y), P(X), D and the endpoint id.

## 4. Verdict

- **3D: exhaustive M4, M5 and M6 are all feasible** with the existing scorer: worst root ≤ 11 s, whole validation split ≤ 4 minutes, full pools ≤ 0.6 GB.
- **2D: exhaustive M4 is feasible**: median 1.4 s, P99 13 s, 0.6 h for validation. **M5 / M6 are feasible offline** (validation 1.3 / 2.5 h; TRAIN 5.9 / 10.9 h), but with tens-of-seconds tails per root and multi-GB pools if stored. The current per-root latency is unsuitable for interactive use without faster view building.
- **Storing JSON full pools is not viable** at 2D M5 / M6: about 150 B per candidate, i.e. 13–24 GB for validation. Streaming with optional binary sidecars is required.

## 5. Recommended bounded-memory streaming design (not implemented)

1. **Lazy generator.** Per root, iterate object k-subsets in a fixed order (`itertools.combinations`), the destination products with a distinct-destination filter, then the k! permutations. O(1) memory, deterministic, label-blind. The exact counts above become the expected-total checksum.
2. **Score each assignment's orders together.** Batch by unordered assignment, so the shared-endpoint Y branch is computed once per assignment and only the ordered-X branch per permutation (up to 6× fewer endpoint encodings at K3).
3. **Vectorise view building.** Build tensors directly from (object index, destination cell) arrays with the cell→xy table, replacing per-sequence `make_view` Python loops. This targets the measured bottleneck; the expected 5–10× gain must be benchmarked.
4. **Fixed-size GPU chunks** of 16–32k sequences, so GPU memory is set by the chunk size (≈ 0.3–0.7 GB) rather than the pool size.
5. **Online selection with exact equivalence to `xy.choose`.** Keep a running argmin of the frozen rule's cost (−log p11 + α m + β D + γ Ĵ, admissible if p11 ≥ η), with the identical tie-break key (rounded cost, m, D, signature), and keep the no-op separate. Simultaneously keep running argmins for every rule of the tuning grid (O(#rules) state), so full-pool rule tuning needs no stored pool.
6. **Optional exact sidecar.** Append-only binary records (26 B per candidate, `float32` scores) per chunk, enabled only for diagnostics or tuning splits, plus a per-root top-K-by-p11 heap (K = 4,096) for compact JSON reporting.
7. **Accounting** per root: expected vs streamed count (must match §1), chunks, scorer time, peak memory, and selection parity against the B = 4,096 path on roots where the full pool fits.

**Recommended first V3.2 step.** Not started, as instructed: exhaustive M4 for both domains, with 3D also at M5 / M6, on validation only, with the frozen V3 D and frozen rule. Report coverage vs top-1 against the capped B = 4,096 baseline before considering 2D M5 / M6 or retraining.
