# V3.1-A (teacher-free), V3.1-B (full-pool rule re-tuning), V3.1-C (compute-matched budgets) and V3.1-D/E diagnostics (validation)

**Compute.**
- Host: gvlab only. GPU 0, ≤ 1.7 GiB; one GPU job at a time, coexisting with a ≈ 1 GB DISCO GPU job.
- Teacher verification: 5 + 4 workers, sized from the measured load while DISCO's `distill.py` ran. 2,014 (2D) and 633 (3D) new teacher queries; every other label came from the V1–V3 caches.

**Data.**
- Base snapshot `abf_9de85710c2a7103f`, validation split only.
- Frozen V3 task cVAE `q2init_all` s0 and V3 D s0, from the copied artifacts (exact inference parity, V3.1-1).
- V2 models from `approachb_final/runs/v2`. Seed 0.
- No test data.

## V3.1-A: matched goal-conditioning ablation, teacher-free (`v3_1_bc/TEACHER_FREE.json`)

**Training.** Each variant: 3 seeds, identical Q2 initialisation, all-assignment supervision, weights, schedule and checkpoint rule. They differ only in task input. Coverage metric: known-assignment ingredient recall, validation, S1, M = 4.

| | 2D ELBO | 2D recall | 3D ELBO | 3D recall (K3) |
|---|---:|---:|---:|---:|
| `q2init_all`, retrained on gvlab | 2.769 ± 0.026 | 29.3 ± 1.3 % | **2.059 ± 0.042** | **58.1 ± 2.1 %** (46 %) |
| `q2init_all_nogoal` (goal only removed) | 2.782 ± 0.029 | 29.0 ± 1.1 % | 2.151 ± 0.074 | 54.5 ± 3.1 % (41 %) |
| `q2init_all_notask` (all task context removed) | 2.765 ± 0.033 | 28.9 ± 1.3 % | 2.144 ± 0.070 | 56.9 ± 1.2 % (47 %) |
| Frozen V3 `q2init_all` (gvlab2) | — | 29.4 % | — | 58.8 % |

- **2D:** goal and task conditioning give no measurable proposal benefit at any M = 4–16.
- **3D:** a small benefit. ELBO is lower by about 0.09, beyond seed noise, and M = 4 recall is 2–4 points higher, within about 1–1.5 seed SDs.
- **Correction to V3:** the historical `goalablated_one` gap was confounded by initialisation and supervision.

### V3.1-A physical arm (`v3_1a_phys/PHYS_VAL.json`, `scripts/v31a_phys_table.py`)

**Setup.**
- Full validation: 2D 751 roots (413 task roots), 3D 364 (220).
- Each variant uses 3 seeds with V3 D s⟨seed⟩ (frozen), the frozen V3 rule, M = 4 and B = 4,096.
- Every selection was physically verified (0 unverified).
- Δ is the paired root-cluster bootstrap on per-root seed-averaged task success vs `q2init_all`.

| | 2D task (seed mean ± SD) | 2D K1 / K2 / K3 | 2D Δ vs q2init_all [95 % CI] | 3D task | 3D K1 / K2 / K3 | 3D Δ [95 % CI] | No-op / NONE abstain (2D; 3D) |
|---|---:|---|---|---:|---|---|---|
| `q2init_all` (retrained, gvlab) | 44.9 ± 1.5 % | 61 / 67 / 18 | — | 70.8 ± 2.5 % | 69 / 73 / 69 | — | 96.5 / 92.2; 82.4 / 70.7 |
| `q2init_all_nogoal` | 43.7 ± 1.0 % | 61 / 61 / 19 | −1.2 [−3.3, +1.0] | 70.3 ± 2.0 % | 70 / 74 / 66 | −0.5 [−2.7, +1.8] | 96.5 / 92.7; 82.4 / 74.1 |
| `q2init_all_notask` | 43.7 ± 1.6 % | 62 / 63 / 17 | −1.1 [−3.4, +1.1] | 71.5 ± 0.9 % | 70 / 74 / 70 | +0.8 [−2.0, +3.5] | 96.5 / 92.2; 82.4 / 73.0 |

**Findings.**
- **No physically measurable benefit of goal or task conditioning in either domain** once initialisation, supervision and schedule are matched. Every Δ is within about ±1 point, and every CI contains 0.
- **The small teacher-free 3D advantage does not carry over to verified top-1 success.** That advantage was ELBO −0.09 and M = 4 recall +2–4 points.
- **Correction to V3-6.** V3-6 attributed −4.8 points in 2D (significant) to goal conditioning. That gap came from the confounded `goalablated_one` control, so the sampler gain should be attributed to repair-assignment supervision, not to goal conditioning.
- **Seed variance is comparable to the effects.** Per-seed task success: 2D 42.9 / 45.5 / 46.2 %, 3D 71.8 / 73.2 / 67.3 %. The gvlab-retrained `q2init_all` s0 reaches 71.8 % in 3D vs 75.0 % for the frozen V3 s0 (trained on gvlab2) under the same D, rule and budget. This is retraining nondeterminism, of the same order as the seed SD.

**Compute.**
- GPU part on gvlab GPU 0.
- Physical verification began on gvlab CPU (seed 0, and seeds 1–2 up to 2D 275 / 427 and 3D 150 / 239 roots). At 20:08 IST the user moved it off gvlab because of CPU contention.
- The remaining 2D 151 roots (575 queries) and 3D 83 roots (273 queries) were verified on the laptop. The laptop used the same unchanged teachers (copies parity-checked in V3-6), resumed from the gvlab cache, and ran 12 + 10 workers.
- The new results were appended to the gvlab cache. `verify_<d>.jsonl.pre_lap` keeps the previous version.

## V3.1-B: full-pool rule re-tuning (`v3_1_bc/tune_full_*.json`)

**Setup.** Primary arm on validation `valsub`, with every scored candidate stored (`store="all"`). All 72 grid rules were re-selected from the complete pools, and all their selections were physically resolved, so **0 rules are unresolved**.

| Domain | Best rule (full pool) | Objective | Task | No-op | Abstain | Best rule with a move-count or travel penalty |
|---|---|---:|---:|---:|---:|---|
| 2D | gate 0.5, η 0.3, α = β = γ = 0 (= frozen V3) | 0.770 | 49.4 % | 96.7 % | 85.0 % | α = 0.5: task 33.9 % (mean moves 1.63 vs 2.27); γ = 0.5: task 34.4 % |
| 3D | gate 0.5, η 0.3, α = β = γ = 0 (= frozen V3) | 0.797 | 76.3 % | 76.7 % | 86.2 % | β = 0.1: task 68.2 %; α = 0.5: task 51.4 % |

**The probability-only selector remains optimal on the complete candidate pool.** The frozen V3 rule is confirmed rather than an artefact of truncation. The penalties do shorten repairs, but cost 15–25 task points, so they stay at zero.

## V3.1-C: compute-matched budget curves (`v3_1_bc/SUMMARY_budget_*.json`, `budget_curves.png`)

**Setup.** Full validation: 2D 751 roots (413 task roots), 3D 364 (220). Every selection was physically verified, with 0 unverified. Task Δ is vs V3 at B = 4,096 (paired root bootstrap 95 % CI).

| 2D | Median scored | Median latency | Task | K1 / K2 / K3 | No-op | NONE abstain | Δ task vs V3 B = 4,096 |
|---|---:|---:|---:|---|---:|---:|---|
| V3 B = 128 | 128 | 0.024 s | 32.2 % | 60 / 47 / 3 | 96.8 % | 96.0 % | −12.1 [−16.7, −7.7] |
| V3 B = 512 | 512 | 0.049 s | 36.6 % | 63 / 53 / 6 | 96.8 % | 92.7 % | −7.7 [−11.9, −3.4] |
| V3 B = 2,048 | 2,048 | 0.145 s | 40.4 % | 61 / 61 / 12 | 96.8 % | 90.0 % | −3.9 [−7.0, −0.7] |
| V3 B = 4,096 | 4,094 | 0.308 s | 44.3 % | 62 / 62 / 20 | 96.8 % | 87.3 % | — |
| V2 iterative, 3 expansions | 108 | 0.045 s | 24.5 % | 57 / 22 / 3 | 95.2 % | 95.3 % | −19.9 |
| V2 iterative, 12 (original) | 412 | 0.179 s | 29.1 % | 59 / 36 / 3 | 95.2 % | 94.7 % | −15.3 [−20.6, −9.9] |
| V2 iterative, 48 | 1,648 | 0.730 s | 24.7 % | 53 / 28 / 3 | 95.2 % | 84.0 % | −19.6 |

| 3D | Median scored | Median latency | Task | K1 / K2 / K3 | No-op | NONE abstain | Δ task vs V3 B = 4,096 |
|---|---:|---:|---:|---|---:|---:|---|
| V3 B = 128 | 128 | 0.024 s | 59.5 % | 70 / 68 / 40 | 76.5 % | 96.6 % | −15.5 [−21.4, −9.5] |
| V3 B = 512 | 508 | 0.044 s | 70.9 % | 72 / 75 / 64 | 76.5 % | 94.8 % | −4.1 [−7.7, −0.9] |
| V3 B = 1,024 | 1,020 | 0.072 s | 73.6 % | 72 / 74 / 74 | 76.5 % | 91.4 % | −1.4 [−4.1, +1.4] |
| V3 B = 4,096 | 1,084 | 0.079 s | 75.0 % | 72 / 77 / 74 | 76.5 % | 86.2 % | — |
| V2 iterative, 12 (original) | 116 | 0.159 s | 51.4 % | 57 / 48 / 51 | 81.2 % | 93.1 % | −23.6 [−30.9, −15.9] |
| V2 iterative, 48 | 454 | 0.651 s | 55.5 % | 57 / 57 / 53 | 81.2 % | 63.8 % | −19.5 |

Findings:
- **At matched scored-sequence counts and at matched latency, V3 beats V2 on task success in both domains.**
  - 2D: V3 at 128 sequences (32.2 %) beats V2 at every budget tried (best 29.1 % at 412). More V2 expansions *reduce* 2D success.
  - 3D: V3 at 128 sequences (59.5 %) beats V2's best (55.5 % at 454 sequences and 0.65 s).
- **3D K3 at very small budgets.** At about 100–250 scored sequences V2 is comparable (V2 57 % at 224 vs V3 56 % at 256); V3 pulls ahead from about 500.
- **The 3D pool saturates** near 1,050 candidates; B ≥ 1,024 is equivalent.
- **Abstention cost.** Larger candidate pools lower NONE abstention for both methods: V3 2D 96 → 87 %, V3 3D 97 → 86 %, V2 3D 93 → 64 % at 48 expansions. This is the coverage vs false-positive trade-off.
- **Physical queries for these curves:** 2,014 (2D) and 633 (3D) new teacher queries; the rest came from the V1–V3 caches.

## V3.1-D/E: failure attribution and NONE false positives (validation, primary at B = 4,096; `v3_1_bc/DIAG_VAL.json`)

**2D K3 (173 roots), decomposed by the known successful assignment** (a lower bound; alternatives exist):

| Stage | Roots | Of which still succeed (alternative repairs) |
|---|---:|---:|
| D1: an ingredient of the known assignment is missing from the one-pass proposals | 142 | 28 |
| D2: all ingredients proposed, but the B = 4,096 cap did not construct the assignment | 26 | 6 |
| A known successful order was in the scored pool | 1 | — |
| No known assignment | 4 | 0 |

The remaining D1 / D2 roots that did not succeed split into "no success known in pool" (126) and "another candidate selected" (8). So **2D K3 is limited mainly by proposal coverage and the construction cap, not by the scorer.** The V3.2 audit separately quantifies how much exhaustive M4–M6 coverage recovers.

**2D K1 / K2 and all 3D classes show substantial ranking losses (D4):** a known success is in the pool, but another candidate is selected.
- 2D K1: 31 such roots vs 22 known-success selections.
- 3D K2: 10 roots; 3D K3: 5.

**NONE false positives.**
- 2D: 19 of 150 NONE roots got a repair. **4 are physically verified successes**, i.e. real repairs on legacy-NONE roots, so NONE is protocol-relative. The other 15 fail, mostly at the first relocation.
- 3D: 8 of 58 got a repair, all failing.
- The false positives have moderate confidence (p11 ≈ 0.47–0.50, P(Y) ≈ 0.58–0.67, P(X | Y) ≈ 0.68–0.71). Their pools contain a median of 11 (2D) and 30 (3D) admissible candidates, against **0** on correctly abstained roots. This is a multiple-comparison effect of large pools, not single overconfident endpoints.

## Status

- V3.1-A physical arms: complete (above).
- **V3.1-4 GPU inference runs on girish-laptop** (RTX 3080 Ti, user-authorised, at most 4 CPU workers) because the gvlab GPUs are full.
  - Inputs are sha256-checked against the V3.1 manifest (155 / 155 files).
  - Parity with gvlab is exact: identical selections on 2,230 / 2,230 validation roots (2D and 3D, B = 128 and 4,096).
- Next: V3.1-4 test-split physical verification on the laptop CPU, then V3.1-5, the final scientific report.
