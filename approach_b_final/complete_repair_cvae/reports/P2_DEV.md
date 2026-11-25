# P2: training, DEV diagnostics and freeze

**Gate: PASS.**
- Six fits completed, all finite.
- Static legality is 100 %: 0 illegal draws among 1,024 × 1,115 VAL roots.
- C1 and C2 read the same pool (the hash is checked again at the seal).
- C0 parity with the bundle holds (P0).
- The pre-registered collapse remedy was **not triggered**.
- Settings are frozen in `P2_FREEZE.json` before any cohort access.

All numbers below are DEV evidence on exposed VAL (the released sampler and scorer were selected on the same VAL). Recall counts only *known* witnesses, and each VAL root carries just its single legacy-selected assignment, so every recall is a lower bound.

## Training (`P2_TRAIN.json`, `figures/p2_curves.png`)

| Fit | best step / budget | epochs at best | VAL recon NLL (nats / repair) | KL | per-token NLL | decision CE / acc | wall |
|---|---|---|---|---|---|---|---|
| 2D s0 (deployed) | 600 / 2,400 | 24 | 8.29 | 0.130 | 1.71 | 0.139 / 0.964 | 24 s |
| 2D s1 | 630 | 25 | 8.18 | 0.205 | 1.69 | 0.113 / 0.960 | 24 s |
| 2D s2 | 660 | 26 | 8.35 | 0.127 | 1.73 | 0.139 / 0.961 | 25 s |
| 3D s0 (deployed) | 532 / 1,520 | 28 | 7.16 | 0.0016 | 1.48 | 0.330 / 0.909 | 15 s |
| 3D s1 | 760 | 40 | 7.07 | 0.0017 | 1.46 | 0.478 / 0.909 | 15 s |
| 3D s2 | 684 | 36 | 7.12 | 0.0010 | 1.47 | 0.443 / 0.879 | 15 s |

- **Overfitting.** Every fit overfits after about 25–40 passes: VAL −ELBO and decision CE rise while TRAIN NLL keeps falling. The fixed-step budget with best-VAL selection handles this the same way it did for the released sampler, whose best step was 810 / 665.
- **Cost.** 0.033 GPU-h in total (RTX 5060), with a peak of 239 MiB.
- **Seed stability.** VAL NLL varies by 0.2 nats or less between seeds, and recall@256 ranges over 0.33–0.36 (2D) and 0.54–0.57 (3D).
- **Remedy check (P0_PREREG §3).** The remedy needs both KL < 0.05 and recall@256 < 0.5. 2D has KL 0.130 with recall 0.349, so only the recall condition holds. 3D has KL 0.0016 (collapsed) with recall 0.539, so only the KL condition holds. **Not triggered in either domain**; the original checkpoints are deployed.
- **3D collapse.** The 3D latent is effectively unused, like the released per-object sampler's (KL ≈ 2e-4). Diversity therefore comes from the autoregressive categorical draws, not from z.

## Decision head on VAL (rows = label, columns = head argmax)

| | 2D NOOP | 2D REPAIR | 2D ABSTAIN | 3D NOOP | 3D REPAIR | 3D ABSTAIN |
|---|---|---|---|---|---|---|
| NOOP (K0) | **174** | 14 | 0 | **61** | 24 | 0 |
| REPAIR (K1–K3) | 7 | **397** | 0 | 6 | **212** | 1 |
| ABSTAIN (NONE, relative) | 1 | 5 | **144** | 0 | 2 | **56** |

The weakest cell is 3D NOOP recall (72 %).

## Pools and recall (`P2_DEV_{2d,3d}.json`, `figures/p2_dev_pools.png`)

| VAL, seed 0 | 2D | 3D |
|---|---|---|
| Unique legal sequences @64 / 256 / 1,024 draws | 56 / 198 / 682 | 49 / 161 / 498 |
| Duplicate-draw rate @64 / 256 / 1,024 | 0.13 / 0.23 / 0.33 | 0.19 / 0.32 / 0.46 |
| Repair length in the main pool (1 / 2 / 3) | 11 / 24 / 65 % | 7 / 35 / 58 % |
| Actions off the per-object top-4 | 58 % | 68 % |
| **Ordered-witness recall** @64 / **256** / 1,024 | 0.20 / **0.35** / 0.49 | 0.34 / **0.54** / 0.69 |
| Assignment recall @256 | 0.38 | 0.54 |
| Object-set recall @256 | 0.96 | 0.97 |
| **C0 top-4 exhaustive recall** (every order kept, so order = assignment) | **0.26** with 51,205 scored sequences on average | **0.61** with 3,656 |
| CR ordered recall @256 by legacy K (K1 / K2 / K3) | 0.71 / 0.34 / 0.11 | 0.85 / 0.58 / 0.24 |
| C0 recall by K (K1 / K2 / K3) | 0.48 / 0.20 / 0.16 | 0.66 / 0.64 / 0.53 |
| CR @256 excluding / only layout-overlap roots | 0.35 / 0.27 | 0.57 / 0.48 |
| Median rank of the best known witness: C1 likelihood vs C2 p11 | 13 vs 33 | 9 vs 18 |
| First prior draw is a known witness | 1.0 % | 3.2 % |

**Reading.**
- **The CR generator nearly always finds the right objects** (object-set recall 0.96–0.97), but often not the exact cells and order.
- **2D:** CR at 256 draws already beats the top-4 pool on known witnesses (0.35 vs 0.26) with about 250 times fewer candidates. 58 % of its actions are off the per-object top-4.
- **3D:** the top-4 pool covers more (0.61 vs 0.54) until about 1,024 draws.
- **K3 is weak for both proposers** in 2D (0.11 vs 0.16).
- **Ranking:** among pools that contain a known witness, the CR likelihood ranks it higher than the frozen p11 does. That is a DEV signal only: these witnesses are the training distribution's style of repair.
- **The first draw is a poor standalone policy** (1–3 % known), which is why C1 ranks the whole pool.

DEV decisions of C0 / C1 / C2 are almost all unlabelled on VAL (for example 2D C1 K1–K3: 17 of 406 REPAIR picks have a label). No DEV success rate is claimed, and none was used for tuning.

## Budgets, controls and timing (DEV rules from P0_PREREG §4)

- **Main budget stays 256 and L stays 64.** The rule switches only above 10 s; C1 + C2 p90 per root is 0.04 + 0.02 s (2D) and 0.03 + 0.015 s (3D), and the GPU peak is far below 6 GiB.
- **Live timing** (`~/cr_cvae_runs/dev/timing_*.json`; 20 DEV roots, 1 warm-up + 3 repeats, CUDA-synchronized, no other GPU job), p50 / p90 per root:

| | C0 natural | CR pool (256 draws) | C1 (pool + likelihood) | C2 (pool + X/Y) | C0 scored | C2 scored |
|---|---|---|---|---|---|---|
| 2D | 1.20 / 7.51 s | 0.004 s | 0.037 / 0.039 s | 0.017 / 0.019 s | 52,933 | 210 |
| 3D | 0.032 / 0.29 s | 0.003 s | 0.024 / 0.029 s | 0.014 / 0.016 s | 2,756 | 169 |

- **Matched wall caps** (frozen: 0.05 / 0.25 / 1.0 s). Under each cap, C0 scores candidates in its stream order (k = 1, then 2, then 3) and decides among what it scored. C2 always completes. Natural picks kept by C0:

| cap | 2D C0 completes / same pick | 3D C0 completes / same pick |
|---|---|---|
| 0.05 s | 3 / 12 of 20 | 14 / 19 of 20 |
| 0.25 s | 4 / 16 | 18 / 20 |
| 1.0 s | 8 / 19 | 20 / 20 |

- **Count-matched controls on DEV100:**
  - **C3** (the CR stream continued to C0's count, cap 4,096 draws) is **underfilled on 78 / 100 (2D) and 39 / 100 (3D) roots**: mean 2,062 vs 50,688 and 934 vs 4,588 unique candidates. CR cannot be scaled to C0's candidate count within the cap, because duplicates grow with the number of draws.
  - **C4** (C0 pool subset matched to C2's count) scores 191 (2D) and 146 (3D).

## Deviation (disclosed)

The full 2D C0 DEV run takes 5–15 s on large VAL scenes (up to 238k scored sequences). After 300 roots it was stopped and the remaining 451 roots got C0 *proposals and exact pool size only* (`--c0props`), which is enough for recall, off-top-4 rate and pool size. A duplicate 2D DEV writer had started by accident. It was stopped by PID; its 40 duplicate rows were identical in pool hash and every decision (determinism check) and were removed. The raw file is kept as `pred_2d_s0.jsonl.with_dups`.

## Freeze (`P2_FREEZE.json`)

- **Fixed for P3:**
  - Seed-0 checkpoints: 2D `fc9a565e…`, step 600; 3D `f3edbc31…`, step 532.
  - Budgets 64 / 256 / 1,024 with main 256, L = 64.
  - The pool and likelihood RNG recipes, the C3 / C4 rules, wall caps, the frozen rule, the bundle manifest hash, the roster hashes and the prereg hash.
- Nothing about the cohort has been read beyond the P0 roster.
