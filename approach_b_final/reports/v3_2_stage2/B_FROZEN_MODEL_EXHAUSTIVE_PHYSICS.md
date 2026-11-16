# V3.2 stage 2 — Phase B: physical outcomes of frozen-model exhaustive selection (E1, H1)

## Setup

| | |
|---|---|
| Model | Frozen V3: task cVAE `q2init_all`, seed-0 per-root draws, frozen V3 D seed 0 |
| Rule | `{noop_gate 0.5, eta 0.3, alpha 0, beta 0, gamma 0}` |
| Roots | All VALIDATION roots: 2D 751, 3D 364 |
| Reference arm | Capped M4, B = 4,096 (`construct.run_root`) |
| Treatment arms | Exact exhaustive M4 / M5 / M6 from the V3.2-A shared M6 pass (nested prefixes) |
| Variable | Only the candidate pool. Draws, model, rule, roots, teacher and masks are identical. |

**Labels.**
- V3.2-A listed 644 2D and 145 3D unique selections that had no physical label.
- After deduplicating against every available cache (52 files, `B/CACHE_BUNDLE.sha256`), 574 2D (339 roots) and 94 3D (81 roots) were verified in Phase B.
- They ran on the laptop, gvlab and girish-laptop, all parity-passed (`A_BASELINE_AND_PARITY.md`). Labels are in `B/*_B_verify_*.jsonl.gz`, with SHA-256 sums in `B/PHASE_B_LABELS.sha256`.
- **0 selected repairs remain unknown in any arm.** 37,490 2D and 12,545 3D labels were merged; decided labels never conflicted (the merge refuses conflicts).

## Results (validation; `B/B_FROZEN_EXHAUSTIVE_PHYS.{json,txt}`)

| Domain | Arm | Task % (K1–K3) | K1 / K2 / K3 % | Δ task vs capped [95 % CI] | Correct NONE abstain % | Δ abstain [95 % CI] | Selections changed |
|---|---|---:|---|---|---:|---|---:|
| 2D | capped M4 B4096 | 44.3 | 62 / 62 / 20 | — | 87.3 | — | — |
| 2D | exhaustive M4 | 49.2 | 59 / 64 / 32 | +4.8 [+1.2, +8.2] | 79.3 | −8.0 [−12.7, −4.0] | 242 |
| 2D | exhaustive M5 | 49.4 | 57 / 63 / 34 | +5.1 [+0.7, +9.2] | 76.7 | −10.7 [−16.0, −6.0] | 324 |
| 2D | exhaustive M6 | 47.0 | 58 / 61 / 29 | +2.7 [−1.9, +6.8] | 75.3 | −12.0 [−17.3, −7.3] | 374 |
| 3D | capped M4 B4096 | 75.0 | 72 / 77 / 74 | — | 86.2 | — | — |
| 3D | exhaustive M4 | 75.0 | 72 / 77 / 74 | +0.0 [+0.0, +0.0] | 82.8 | −3.4 [−8.6, 0.0] | 17 |
| 3D | exhaustive M5 | 75.0 | 72 / 79 / 71 | +0.0 [−3.6, +3.6] | 77.6 | −8.6 [−15.5, −1.7] | 87 |
| 3D | exhaustive M6 | 74.5 | 77 / 78 / 67 | −0.5 [−5.0, +3.6] | 75.9 | −10.3 [−17.2, −3.4] | 127 |

**Population and statistics.**
- Task roots: 413 in 2D (K1/K2/K3 = 120/120/173) and 220 in 3D (53/97/70). NONE roots: 150 2D, 58 3D. No-op-evaluable roots: 188 2D, 85 3D.
- Bootstrap: 2,000 root-cluster resamples, one model seed, so the intervals are root-level only.
- No-op correctness is unchanged in every arm (96.8 % 2D, 76.5 % 3D), because the no-op gate is applied first.

**Outcomes on NONE roots** (the protocol says abstain):

| Domain | Arm | ABSTAIN | Verified SUCCESS | FAIL_Y | FAIL_X |
|---|---|---:|---:|---:|---:|
| 2D | M4 | 119 | 4 | 26 | 1 |
| 2D | M6 | 113 | 3 | 32 | 2 |
| 3D | M6 | 44 | 0 | 14 | 0 |

- The capped baseline already finds 4 physically verified repairs on 2D NONE roots. Exhaustive pools add none.
- Almost all new NONE-root errors are confident selections of physically infeasible endpoints (Y = 0).

## Answer to H1 (does removing B help, at a fixed frozen model?)

**It is a mixed result: it helps 2D task success but hurts abstention in both domains.**

1. **2D task success improves at M4 and M5** (+4.8 and +5.1 points; both CIs exclude 0), mainly in K3 (20 % → 32–34 %). The cap was discarding real K3 solutions. M6 gains less (+2.7, CI includes 0).
2. **3D task success does not change.** Its pools are mostly complete under the cap already: only 17 selections change at M4.
3. **Correct NONE abstention falls significantly as M grows** (2D −8 / −11 / −12; 3D −3 / −9 / −10 points). The frozen scorer's maximum p11 grows with pool size: winner's curse, high-confidence false positives, mostly Y = 0. Larger M therefore trades abstention for 2D K3 coverage.

**Implication for E2 / E3.** The failure mechanism is ranking and calibration, not coverage, so the pre-registered matched training experiment (E3) is justified. Its TRAIN evidence over-samples the right things: high-p11 non-top candidates, the top-1 at each M, and order contrasts. NONE-root TRAIN items are included through the K stratification (NONE 75 2D / 40 3D roots).

These validation results are now exposed: they informed the E3 data design and are not a confirmation cohort.
