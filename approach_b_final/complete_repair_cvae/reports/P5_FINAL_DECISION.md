# Final decision: complete-repair cVAE vs factorized proposal + X/Y (RSS RQ1)

## Verdict

- **The separate X/Y feasibility scorer is justified, and the factorized per-object proposal is not established as necessary.**
  - **3D:** reranking the complete-repair generator's own candidate pool with the frozen X/Y improves verified task success by **+24.0 pp [13.7, 34.0]** (Holm p < 0.001, 0 % UNKNOWN). With that same scorer, the released factorized proposal + exhaustive construction is **not distinguishable** from the complete-repair pool: **+0.7 pp [−5.9, 7.5]**.
  - **2D:** both primary contrasts point the same way (C2 − C1 **+8.0** [−1.3, 17.3]; C0 − C2 **+7.3** [0.7, 14.0], Holm p = 0.14). They are **INCONCLUSIVE** under the pre-registered rule because strict UNKNOWN exceeds 20 % (24–35 %, all `UNKNOWN_PLANNER` / `UNKNOWN_TRANSIT`).
  - **What the 2D C0 advantage is attributable to:** the count-matched control shows it travels with scoring about 230 times more candidates, not with the factorized representation.
- **The single-model CR-ONLY baseline is clearly worse than the deployed system in 3D:** −24.7 pp [−34.9, −14.5].

This is a locked retrospective comparison on the V3.4 fresh cohort (its C0 outcomes were already known). It is not a new independent benchmark. No causal, minimality or K > 3 claim is made.

## Paper-ready table

K1–K3 roots, 50 per K per domain. Success is verified X·Y by the unchanged teachers, as a percentage of all roots (strict; UNKNOWN counts as not verified). Brackets give the upper bound with every UNKNOWN treated as success.

| Domain | Arm | K1 | K2 | K3 | **K1–K3** | UNKNOWN | decided-only | Correct NOOP (K0, 30) | Correct ABSTAIN (NONE, 30) | Scored candidates / root (mean) | Planning time p50 / p90 | Inference params |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2D | **C0 ours** (top-4 + exhaustive + X/Y) | 66.0 | 72.0 | 26.0 | **54.7** [78.7] | 24.0 % | 71.9 | 100 | 100 | 47,283 | 1.20 / 7.51 s | 794 k |
| 2D | **C1 CR-only** (likelihood + head) | 44.0 | 46.0 | 28.0 | **39.3** [74.0] | 34.7 % | 60.2 | 93.3 | 100 | 207 (+13.2 k decoder passes) | 0.037 / 0.039 s | 548 k |
| 2D | **C2 CR + X/Y** (same pool) | 62.0 | 62.0 | 18.0 | **47.3** [76.0] | 28.7 % | 66.4 | 100 | 100 | 207 | 0.017 / 0.019 s | 1,014 k |
| 3D | **C0 ours** | 66.0 | 78.0 | 82.0 | **75.3** | 0 | 75.3 | 86.7 | 83.3 | 3,160 | 0.032 / 0.29 s | 779 k |
| 3D | **C1 CR-only** | 60.0 | 46.0 | 46.0 | **50.7** | 0 | 50.7 | 66.7 | 96.7 | 166 (+10.6 k decoder passes) | 0.024 / 0.029 s | 538 k |
| 3D | **C2 CR + X/Y** | 68.0 | 76.0 | 80.0 | **74.7** | 0 | 74.7 | 86.7 | 90.0 | 166 | 0.014 / 0.016 s | 1,005 k |

- **Planning time** is live, CUDA-synchronized, uncached, on 20 DEV roots on an RTX 5060 Laptop. It is planner latency only, not teacher verification or robot execution time. The cohort-recorded times agree: C0 2D p50 / p90 1.16 / 7.57 s, 3D 0.046 / 0.44 s.
- **Teacher calls during inference:** 0 for every arm.
- **Parameters:** CR inference excludes its training-only posterior; the released sampler count includes its posterior.
- **Training cost:** CR six fits 0.033 GPU-h in total (15–25 s each). The released sampler trained in 4–7 s per fit; the X/Y scorer's training cost is not re-measured here.

**Paired differences, K1–K3** (family-cluster bootstrap stratified by K, 4,000 draws; percentage points):

| Contrast | 2D all-root | 2D complete-case | 3D all-root | Holm p (primary) | Verdict |
|---|---|---|---|---|---|
| **C2 − C1** (separate X/Y scorer) | +8.0 [−1.3, 17.3], W 32 / L 20 | +4.8 [−7.2, 16.9] (n = 83) | **+24.0 [13.7, 34.0]**, W 49 / L 13 | 2D 0.21 · 3D < 0.001 | 2D inconclusive · **3D established** |
| **C0 − C2** (factorized proposal + enumeration, same scorer) | +7.3 [0.7, 14.0], W 20 / L 9 | +7.0 [−1.0, 15.0] (n = 100) | +0.7 [−5.9, 7.5], W 14 / L 13 | 2D 0.14 · 3D 0.93 | 2D inconclusive · 3D no established difference |
| C0 − C1 (overall; unadjusted) | +15.3 [6.0, 24.7] | +11.5 [−1.1, 24.1] | +24.7 [14.5, 34.9] | – | 2D inconclusive (UNKNOWN) · 3D C0 better |

2D UNKNOWN bounds (every UNKNOWN set in the arm's favour or against it) span about −27 to +37 pp for each contrast; see `P5_STATS.json`.

## Secondary accounting controls (descriptive, unadjusted)

| | 2D K1–K3 | 3D K1–K3 |
|---|---|---|
| **C3** = CR + X/Y with the pool grown toward C0's count (cap 4,096 draws; reaches it on 32 / 210 2D and 143 / 210 3D roots; mean 2,268 / 802 scored) | 34.0 [87.3], 53 % UNKNOWN or UNQUERIED (57 picks not queried by the cap) | 74.0 |
| **C4** = C0's own pool subset to C2's count (hash order within k, round-robin k; mean 203 / 149 scored) | 41.3 [64.7], 23 % UNKNOWN | 73.3 |
| C0 − C4 | **+13.3 [5.3, 21.3]**; complete-case +10.5 [1.1, 20.0] | +2.0 [−2.8, 6.8] |
| C4 − C2 (two proposers at equal scorer count) | −6.0 [−14.0, 2.0] | −1.3 [−8.6, 6.8] |
| C3 − C2 | inconclusive (underfilled, unqueried) | −0.7 [−6.8, 5.3] |
| **C1 with the common frozen no-op gate** | 39.3, identical to C1 on K1–K3 | 46.7 (−4.0 vs C1) |

**Matched wall time (DEV, `P2_DEV.md`).**
- At 0.05 / 0.25 / 1.0 s caps, C2 completes on every root.
- 2D C0 completes on only 3 / 4 / 8 of 20 roots and keeps its natural pick on 12 / 16 / 19.
- 3D C0 is mostly complete by 0.25 s.

## Direct answers to RQ1

1. **Does separate X/Y reranking help complete generative proposals?**
   - **3D:** yes, +24.0 pp, established.
   - **2D:** the same direction (+8.0), not established because of UNKNOWN.
   - **Mechanism: selection, not recall.** In 3D, 46 of C1's 56 FAIL_Y picks were on roots whose pool contains a known working repair (`P5_ATTRIBUTION.json`). The CR likelihood favours short repairs (3D C1 picks: 64 / 25 one- / three-object, against C2's 17 / 62) that are statically legal and often physically executable (X = 1) but leave the target blocked (Y = 0: 49 of C1's 3D negatives).
   - **The supervision differs and this is part of the effect.** The scorer was trained with negative and partially observed X / Y labels (2D TRAIN snapshot: 20,550 X and 21,911 Y labels, incl. 5,096 X0Y1 and 5,095 X0Y0). The CR model saw only verified positive orders (6,394 / 4,890) plus root-level NOOP / REPAIR / ABSTAIN labels. Part of C2 − C1 is therefore "more and negative supervision", not architecture alone.
2. **Does the factorized cVAE proposal + enumeration help with the same scorer?**
   - **3D:** no detectable benefit. C0 − C2 = +0.7 [−5.9, 7.5], and the count controls C3 / C4 land within 2 pp of both.
   - **2D:** the +7.3 is inconclusive. The C4 control (C0's own proposal cut to C2's count) is not better than C2 (−6.0 [−14.0, 2.0]) and is 13.3 pp below full C0. **The 2D gain travels with scoring about 47k instead of about 200 candidates (search budget), not with the per-object factorization.**
3. **Is the extra complexity worth the cost?**
   - The component that earns its keep is the **separate feasibility scorer**.
   - The factorized proposal + exhaustive construction costs 230× (2D) / 19× (3D) more scored candidates and 70× / 2× more planning time than C2. Its only advantage that the data can show is the inconclusive 2D gap that follows the candidate budget.
   - CR + X/Y uses about 27 % more inference parameters than the released system (1.01 M vs 0.79 M), because it carries both networks.
4. **Is the conclusion robust by domain and K?**
   - **3D C2 − C1** is driven by K2 / K3: +30.0 [14, 46] and +34.0 [18.6, 49.2]. K1 is +8.0 [−12.0, 27.5].
   - **3D C0 − C2** is within ±2 pp at every K.
   - **2D:** C2 − C1 is +18 (K1), +16 (K2) and −10 (K3); C0 − C2 is +4 / +10 / +8. Every 2D stratum has 8–52 % UNKNOWN.
   - **2D K3 is weak for every arm** (18–28 % verified).
5. **Which failures are recall, order, selection, gate or unknown?** (`P5_ATTRIBUTION.json`)
   - **3D C1:** mainly selection (FAIL_Y with a known witness in the pool) and gate (6 NOOP, 2 ABSTAIN).
   - **3D C0 / C2:** split between FAIL_X and FAIL_Y, plus 9 NOOP gates each (the frozen no-op gate).
   - **2D:** UNKNOWN dominates every arm (36 / 52 / 43 roots for C0 / C1 / C2).
   - **Recall** (legacy-generator witnesses only, an unbiased lower bound): the CR pool contains one more often than the top-4 pool at K1 (2D 43 vs 37; 3D 44 vs 32) and far less often at K3 (2D 2 vs 8; 3D 5 vs 20).

## Safeguards

- **K0** (Y(empty) verified for all 30 per domain): C0 and C2 return NOOP on 100 % (2D) and 86.7 % (3D). C1's head returns NOOP on 93.3 % (2D) and 66.7 % (3D). In 3D, 9 of its 10 unnecessary repairs still succeeded physically.
- **NONE:** C1 abstains most often (96.7 % in 3D, vs 83.3 % C0 and 90.0 % C2). No repair on a NONE root was a verified success in this roster. NONE stays benchmark-relative.

## Deviations, limitations and resources

- **Deviations** (`AMENDMENTS.md`):
  - Fixed-step training budget.
  - A 210-root roster per domain.
  - DEV C0 run as proposals only for 451 of 751 2D VAL roots.
  - One duplicate DEV writer (rows identical, removed).
  - The secondary physical tier ran after primary coverage, within the caps; 57 2D C3 picks were not queried.
- **Limitations:**
  - Retrospective locked cohort; exposed VAL for all model selection.
  - 2D strict UNKNOWN 24–35 % makes every 2D contrast inconclusive.
  - 3D negatives are teacher-budget-defined, not certified.
  - Known-witness recall is a lower bound.
  - One deployment seed was evaluated physically; seeds 1 and 2 are DEV-only, with VAL recall 0.33–0.36 (2D) and 0.54–0.57 (3D).
  - The CR model is one credible design, not every possible single generator. It is the first one trained, with no tuning on outcomes.
- **Resources used:**

| Resource | Used | Authorized |
|---|---|---|
| GPU training | 0.033 GPU-h | 4 |
| GPU inference / analysis | under 1 GPU-h (DEV ≈ 0.6 h incl. the stopped 2D C0 run; cohort ≈ 0.2 h) | 3 |
| Teacher queries | 2D 450, 3D 434 | 450 each |
| Teacher CPU | 2D 1.75 h, 3D 3.49 h | 8 / 16 |
| Workers | 16 | 16, ≥ 4 cores free |
| Storage | 78 MB | 1 GB |
| Protected TEST | not opened | – |
| Data generation / X/Y or sampler retraining | none | – |
| K4/K5 study | its worktree, gvlab2 runtime and data were never touched | – |

## Commits

`f49b5f3dd3` P0/P1 · `02108f9e28` P2 · `7cfcb354a3` freeze · `f40c47cf0c` seal + primary manifest · `91e87fa423` secondary manifest · final commit: this report (hash recorded in chat).
