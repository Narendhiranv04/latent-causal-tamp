# Approach B V3.2 — Exhaustive top-M repair construction and clean Boltzmann X/Y scorer retraining (final report)

| | |
|---|---|
| Branch | `naren/approach-b-v3-2-training` |
| Base | V3.1-4 `82de92e682` + V3.2-A `b2b8012969` |
| Pre-registration | `b6de8c432b` |
| Evidence | Every number below is a physically verified top-1 outcome from the unchanged X/Y teachers, with **0 unresolved selections** in any reported arm |
| Details | `A_…`, `B_…`, `C_…`, `D_…`, `E_…` reports; registry `EXPERIMENT_REGISTRY.json`; hashes `resolved_config.json`; commands `REPRODUCE.md` |

## Summary

1. **Removing the B = 4,096 cap with the frozen V3 model (E1, VAL) is a mixed result.**
   - 2D task success rises by about 5 points at M4 and M5 (K3 20 % → 32–34 %).
   - Correct NONE abstention falls by 8–12 points in 2D and 3–10 points in 3D as M grows, because the frozen scorer confidently picks infeasible endpoints in larger pools.
   - 3D task success is unchanged.
2. **Physically labelled exhaustive-distribution TRAIN evidence fixes much of this (E3, matched, VAL, 3 seeds).** D-expanded was compared with D-control, which shares the same architecture, initialisation, roots, optimiser and step count and differs only in the evidence:
   - Correct NONE abstention rises by +5.6 / +8.9 / +10.7 points in 2D and +22 to +26 in 3D at M4 / M5 / M6 (all CIs exclude 0).
   - 2D task success rises by about 3 points at every M (CIs exclude 0 at M5 and M6 and touch 0 at M4).
   - 3D task success is unchanged.
   - Selected-repair over-confidence drops in both domains.
3. **One unified scorer works across M4 / M5 / M6 (E4).** Within-model M effects are not significant. The pre-registered trigger for M-specific scorers (E5) was not met, so none were trained.
4. **Exposed-TEST regression (E6) of the registered configuration** (D-expanded, exhaustive M4, 3 seeds) against the capped V3 path:
   - 2D: 52.0 % vs 43.6 % (**+8.4 [+5.4, +11.3]**); K3 12 → 26 %.
   - 3D: 81.2 % vs 77.3 % (**+3.9 [+0.4, +7.3]**).
   - Abstention is not degraded and no-op correctness improves.

   TEST was used in earlier versions, so this is a regression check, not a fresh confirmation.
5. **The remaining 2D bottleneck is proposal coverage (E2).** For 59–73 % of 2D VAL task roots, no known physical success lies in the top-M pool. The dominant residual failure class is a confident infeasible endpoint in such pools. The next scientific step is a matched sampler study (separate stage), not more scorer variants.
6. **No fresh confirmation cohort was produced (`FRESH_CONFIRMATION_NOT_RUN`).** Generating and teacher-labelling a family-disjoint cohort of the required size is multi-day work, beyond a safe overnight allocation on the shared hosts.

## Results tables

### Validation (development cohort; root-paired bootstrap; per-root seed averages)

| Domain | Arm (seeds) | M4 task / abstain | M5 task / abstain | M6 task / abstain |
|---|---|---|---|---|
| 2D | capped V3, frozen D (1) | 44.3 / 87.3 (M4 only) | — | — |
| 2D | exhaustive, frozen V3 D (1) | 49.2 / 79.3 | 49.4 / 76.7 | 47.0 / 75.3 |
| 2D | exhaustive, D-control (3) | 52.9 / 85.1 | 52.5 / 81.3 | 52.1 / 79.1 |
| 2D | **exhaustive, D-expanded (3)** | **55.9 / 90.7** | **55.8 / 90.2** | **54.9 / 89.8** |
| 3D | capped V3, frozen D (1) | 75.0 / 86.2 (M4 only) | — | — |
| 3D | exhaustive, frozen V3 D (1) | 75.0 / 82.8 | 75.0 / 77.6 | 74.5 / 75.9 |
| 3D | exhaustive, D-control (3) | 76.2 / 60.3 | 77.1 / 54.6 | 77.6 / 50.6 |
| 3D | **exhaustive, D-expanded (3)** | **78.5 / 82.8** | **78.0 / 80.5** | **77.1 / 75.9** |

**Matched deltas (D-expanded − D-control) with 95 % CI:**

| Domain | Metric | M4 | M5 | M6 |
|---|---|---|---|---|
| 2D | Task | +3.0 [+0.0, +5.9] | +3.3 [+0.6, +6.1] | +2.8 [+0.2, +5.6] |
| 2D | Abstain | +5.6 [+2.9, +8.2] | +8.9 [+5.8, +12.2] | +10.7 [+7.3, +14.2] |
| 3D | Task | +2.3 [−0.5, +5.0] | +0.9 [−2.0, +3.8] | −0.5 [−3.5, +2.6] |
| 3D | Abstain | +22.4 [+14.4, +31.6] | +25.9 [+17.8, +34.5] | +25.3 [+16.7, +33.3] |

Per-K, no-op and calibration values are in `TABLE_K_BY_M.csv`, `TABLE_MODEL_BY_M.csv` and `TABLE_CALIBRATION.csv`.

### Exposed TEST regression (`E/TABLE_TEST_REGRESSION.txt`)

| Domain | Capped V3 (3 seeds) task / abstain / no-op | D-expanded exhaustive M4 (3 seeds) | Δ task |
|---|---|---|---|
| 2D | 43.6 / 92.7 / 89.7 | 52.0 / 92.9 / 91.1 | +8.4 [+5.4, +11.3] |
| 3D | 77.3 / 76.9 / 77.6 | 81.2 / 82.3 / 86.1 | +3.9 [+0.4, +7.3] |

## Hypotheses

| | Question | Answer |
|---|---|---|
| H1 | Effect of removing the cap at a fixed model | +5 task points in 2D at M4 / M5; −8 to −12 abstention points; 3D task unchanged. Coverage gains are partly lost to winner's-curse false positives. |
| H2 | Coverage vs ranking vs abstention | Frozen-model losses at larger M are ranking / calibration failures (Y-infeasible high-p11 picks grow with M). After retraining, the largest 2D residual is coverage. |
| H3 | Value of expanded-distribution training | Positive and matched: abstention improves strongly in both domains, and 2D task success by about 3 points. |
| H4 | One scorer across M | Yes. No significant within-model M effect, so no M-specific models were needed. |
| H5 | Compute / latency | Exhaustive M6 scores a median of 103 k (max 961 k) 2D sequences per root, against 4,096 under the cap. CPU-bound view construction makes it 9.5 s median and 111 s p99 per root on one CPU. M4 is about 4× cheaper than M6 (25 k vs 103 k median) with equal or better verified success, so M4 is the efficient operating point. Teacher labelling for the training evidence took 43 CPU-h; training 12 models took about 6 GPU-min. |

## Limitations

- **Exposure.** VAL drove V3.2-A analysis and these decisions, and TEST was used throughout V1–V3.1. No fresh family-disjoint cohort was evaluated, so there is no unbiased generalisation claim.
- **Seeds.** Model seeds share one labelled dataset; they are not independent data collections. The frozen-model arms (capped, frozen exhaustive) are single-seed.
- **Control calibration.** D-control abstains clearly worse than the frozen V3 D, especially in 3D. Fixed 60 epochs and different hardware may change calibration relative to the early-stopped original. The matched contrast remains valid; the observational comparison with the frozen model is not causal.
- **Coverage measure.** Known-success-in-pool is a lower bound: unknown feasible repairs may exist.
- **Physical evidence.** Physical outcomes come from the simulation teachers only; no real-robot hardware was used.
- **Inference cost.** Exhaustive scoring is costly at M6 in 2D. The vectorised view builder (contract Phase A item 5) was not implemented and would need exact-equivalence proof.
- **Not committed to git.** Model checkpoints (`*.pt`, 12 × ~1.9 MB) are pending Git LFS approval; SHA-256 values are recorded and mirrors listed in `D_MATCHED_TRAINING.md`.
- **Journal granularity.** The distributed journal is per root, not per query (`EXECUTION_MANIFEST.md`).

## Figures (`figures/`)

- `verified_success_vs_M.png`
- `abstention_vs_M.png`
- `calibration_selected_vs_M.png`
- `failure_decomposition.png` (with known-success coverage vs M)
- `compute_vs_M.png`
- `cases/case_a_*.png`: K3 repairs where capped and frozen exhaustive fail and D-expanded succeeds.
- `cases/case_b_*.png`: NONE roots where frozen exhaustive M6 confidently fails and D-expanded abstains.

The case figures are schematic scene drawings from the snapshot records, labelled with physically verified outcomes.

## Recommended next step

Run a matched sampler study (sampler-original vs sampler-expanded data, scored by the frozen D-expanded) to address 2D proposal coverage. Separately, produce a fresh family-disjoint confirmation cohort for an unbiased headline number. Both need explicit approval of their multi-day compute budgets.
