# V3.3 teacher-free proposal screening (VALIDATION)

## Protocol

- **Proposals.**
  - Top-6 S1 proposals per eligible object: the top-M of the 64-draw Monte-Carlo marginal.
  - Drawn through `exhaustive.proposals`, with a per-root torch generator seed of 0 and the same device (girish CUDA) for every sampler. This is the exact RNG stream the scoring pass uses.
  - M4 and M5 are prefixes of M6. Every VAL root is included (2D 751, 3D 364).
- **Known-success coverage at M.**
  - A VAL task root is covered when some **known** positive assignment has every action inside the top-M proposals of its object. A positive assignment is a Y = 1 endpoint with an X = 1 order.
  - Known positives come from base-snapshot VAL labels plus the V3.2 VAL verify caches. They were computed **before any V3.3 teacher query**.
- **Caveats.**
  - Known labels are incomplete, so coverage is a **lower bound**.
  - Most known VAL positives were found by verifying selections from `q2init_all`-based pipelines, which biases the measure toward the reference sampler.
  - Coverage is diagnostic only and is not comparable with verified task success.
- **Scripts.** `scripts/v33_proposals.py dump` / `cover`; full output in `COVERAGE_VAL.json`.
- **Known positives available.** 2D: 411 of 413 VAL task roots. 3D: 220 of 220.

**Sampler parity (mandatory test 7).** The unmodified production `q2init_all` s0 sampler, run on girish through the patched code, reproduces the archived V3.2 proposal sets exactly:
- 2D: 751 / 751 roots identical;
- 3D: 364 / 364 roots identical.

## Coverage of VAL task roots (%, seed means of 3 samplers per arm)

| Domain | M | S-control | S-expanded | q2init_all s0 (reference) |
|---|---|---|---|---|
| 2D | 4 | 75.9 | 78.0 | 89.1 |
| 2D | 5 | 82.3 | 84.7 | 92.0 |
| 2D | 6 | 86.3 | 88.5 | 93.7 |
| 3D | 4 | 93.2 | 93.5 | 97.7 |
| 3D | 5 | 95.8 | 96.8 | 98.6 |
| 3D | 6 | 97.3 | 97.7 | 98.6 |

### By legacy K at M4

| Domain | Arm | K1 | K2 | K3 |
|---|---|---|---|---|
| 2D | S-control | 90.3 | 85.3 | 59.5 |
| 2D | S-expanded | 91.1 | 88.3 | 61.7 |
| 2D | q2init ref | 99.2 | 95.8 | 77.5 |
| 3D | S-control | 94.3 | 92.4 | 93.3 |
| 3D | S-expanded | 93.1 | 92.4 | 95.2 |
| 3D | q2init ref | 100.0 | 94.8 | 100.0 |

### Paired M4 coverage deltas

Per-root seed averages; root bootstrap with 2,000 resamples.

| Domain | S-expanded − S-control | S-control − q2init | S-expanded − q2init |
|---|---|---|---|
| 2D | +2.0 [−0.3, +4.3] | −13.2 [−16.4, −10.0] | −11.1 [−14.0, −8.4] |
| 3D | +0.3 [−1.5, +2.1] | −4.5 [−7.0, −2.4] | −4.2 [−6.4, −2.3] |

## Pool size and diversity

- **Pool size.** Every sampler returns exactly M distinct legal destinations per eligible object (fewer only when fewer cells are legal). Candidate pools and scoring cost are therefore **identical across arms**:
  - mean distinct (object, destination) actions at M4: 2D 38.1, 3D 15.1;
  - eligible movable objects per root: 2D 9.53, 3D 3.77.
- **Mean Jaccard overlap of per-object M4 proposal sets:**

| | 2D | 3D |
|---|---|---|
| S-control vs S-expanded, same seed (s0 / s1 / s2) | 0.61 / 0.55 / 0.60 | 0.50 / 0.51 / 0.52 |
| Seed 0 vs seed 1, within S-control | 0.58 | 0.47 |
| Seed 0 vs seed 1, within S-expanded | 0.57 | 0.50 |
| S-control vs q2init ref (s0 / s1 / s2) | 0.46 / 0.46 / 0.45 | 0.38 / 0.38 / 0.40 |
| S-expanded vs q2init ref (s0 / s1 / s2) | 0.50 / 0.49 / 0.51 | 0.41 / 0.41 / 0.41 |

  - The two scratch arms differ about as much from each other as two seeds of the same arm do.
  - S-expanded's proposals are slightly closer to the production sampler's than S-control's.
- **No-op and NONE roots.** The sampler never chooses no-op or abstention; those decisions are made by the frozen scorer and rule. NONE roots have no known positive by definition, so coverage is reported for task roots only. Physical no-op and abstention outcomes are in `PHYSICAL_VAL_RESULTS.md`.
- **VAL ELBO.** See `SCRATCH_TRAINING.md`. Seed means are 2D 2.733 vs 2.727 and 3D 2.012 vs 1.986 (control vs expanded).

## Screening decision

Expanded data does **not clearly** improve M4 coverage: 2D +2.0, with a CI that touches 0; 3D +0.3. Both scratch samplers cover clearly fewer known successes than the Q2-pretrained production sampler.

As registered, the decision was **not** taken on coverage. The bounded paired physical pilot (seed 0, all VAL roots) ran regardless.
