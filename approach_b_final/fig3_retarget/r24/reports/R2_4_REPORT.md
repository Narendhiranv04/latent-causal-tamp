# R2.4: execution-order recovery and long-horizon composition (frozen cVAE + frozen X/Y)

**Scope.**
- **Branch:** `naren/rss27-fig3-retarget-home`, from `b7ab593fce`. Preregistration `r24/R24_PREREG.json` committed at `5451b87eb9` before any R2.4 plan, query or analysis.
- **Constraints respected:** frozen bundle; no training, architecture change, TEST or release_v2 access, long-root generation or merge; gvlab2 only.
- **Evidence status:** every root is an **exposed development root**, so nothing here is independent confirmation.
- **Reading this report:** each claim is marked **established** (its preregistered rule is met), **not established**, or **hypothesis**. 2D and 3D are separate.
- **Code** (`fig3_retarget/r24/`):

  | File | Role |
  |---|---|
  | `order.py` | Exact subset-DP over joint order and partition; equals brute force in the tests |
  | `arms.py` | Oracle and deployment planners |
  | `labels.py` | Exact chunk labels from archived traces |
  | `jobs24.py` | Sealed manifests with reuse |
  | `analyze24.py` | Analysis |
  | `figs24.py` | Figures |
  | `audit2d.py` | 2D witness audit |
  | `tests/test_r24.py` | 19 tests; the 54 R1 tests are also unchanged and passing |

**Local chunk energy (both domains).** `c(S, C) = -log pX(C | rebase(root, placed set S), q_ref, original task)`:
- The full scene is kept.
- Chunks are ordered and contain 1–3 actions.
- Each intermediate home return adds a declared penalty `-log 0.92`.
- The partition that is scored is the partition that is executed.
- There is no partial original-task Y gate.

---

## 3D

### R2.4A ordering only (the witness assignment is given; its order is hidden)

| Order of the known correct assignment | Verified X=1,Y=1 / decided | Exact witness order | Mean Kendall distance to the witness |
|---|---|---|---|
| **A-DP** (new: exact joint order + partition DP) | **2 / 20** | 0 | 0.47 |
| A-PRE (DP restricted to model-discovered prerequisites) | 3 / 11 (9 not run, budget) | 1 | 0.43 |
| Direct long-sequence p11, continuous (K45, archived) | 5 / 20 | 0 | 0.44 |
| Existing chunk ranking, chunk-H (K45) | 4 / 20 | 1 | 0.41 |
| Seeded random order, continuous (K45) | 4 / 20 | 1 | 0.51 |
| **Privileged witness order, forced q_ref split [2, m]** | **19 / 20** | 20 | 0 |

**Paired comparisons:**
- A-DP vs direct: 0 roots where only A-DP verified, 3 where only direct verified.
- A-DP vs random: 2 vs 4.

**Order recovery:**
- The witness order's median rank under the DP energy is 19, with 0/20 at top-1. A random order's expected rank is 12 of 24 orders for K4 and 60 of 120 for K5.
- The local energy does not prefer the order that physically works.

**Failure location:**
- 15 of the 18 A-DP failures happen at the **first relocation from the initial scene** (chunk 0, h = 0). 2 occur at h = 1 and 1 at h = 2.
- All 18 are relocation failures (no feasible grasp); there are 0 connector failures.
- **17 of the 18 failing chunks had a model pX of 0.83 to 0.997.** These are confident errors, not ties.

**Prerequisites:**
- The model-discovered pairwise prerequisite edges agree with the witness order on 30 of 52 edges (58 %, near chance).
- Restricting the DP to those edges (A-PRE) does not help (3/11 decided).

### Local X at intermediate scenes (exact teacher chunk labels reused, plus the R2.4 jobs)

- **Labels:** 465 chunk labels (231 executable, 234 not), 0 conflicting duplicates.
- **Sources:** K45 primary and oracle runs, R1, R2.1–2.2, R2.3 and R2.4.

| Stratum | n (executable) | Mixed roots | pX AUROC [root-cluster 95 % CI] | Non-executable chunks with pX ≥ 0.5 |
|---|---|---|---|---|
| h = 0 | 297 (104) | 20 | 0.67 [0.60, 0.73] | 150 / 193 |
| **h ≥ 1** | 168 (127) | 19 | **0.52 [0.45, 0.59]** | **38 / 41** |
| h ≥ 1, single action | 108 (91) | 14 | 0.65 [0.52, 0.77] | 14 / 17 |
| h ≥ 1, 2–3 actions | 60 (36) | 13 | **0.17 [0.06, 0.27]** (inverted) | 24 / 24 |
| h ≥ 1, the 20 development roots only | 156 (115) | 19 | 0.54 [0.47, 0.61] | 38 / 41 |

**Verdict:** local X **FAILS** at intermediate scenes. This is **established** by the preregistered rule (cluster-CI upper bound < 0.70, 19 mixed roots ≥ 10). Even at h = 0 it is weak in this dense K4/K5 regime: 0.67, against 0.87 on the natural R2.1 panel.

### R2.4B deployment arms (no privileged information; one discovery run per root; bounded exhaustive local groups)

| Arm | Verified / decided | Mean length / returns | Failures (first failing relocation) | Median latency |
|---|---|---|---|---|
| R-FIG3-X (recursion sets, DP re-ordered) | 3 / 20 | 4.05 / 1.1 | X0Y1 15, X0Y0 2; h0 14, h1 2, h2 1 | 2.2 s |
| R-FIG3-XP (prerequisite-constrained DP) | 2 / 14 | 4.05 / 1.2 | X0 12 (h0 9) | 1.6 s |
| R-FIG3-XC (composed order, best partition) | 3 / 16 | 4.0 / 1.55 | X0 13 (h0 8) | 1.2 s |
| GA-INIT (global assignment over D4 at S0) | 1 / 19 | 3.85 / 1.0 | X0 18 (h0 15) | 0.9 s |
| GA-UNION (global assignment over the union of refreshed proposals) | 3 / 20 | 3.45 / 1.0 | X0 17 (h0 14) | 3.6 s |
| R2.3 reference: B0 / R-FIG3 / F-FLAT | 2 / 5 / 7 (of 20) | | | |

**Proposal coverage vs discovery:**
- The witness assignment lies entirely in the action pool on 12/20 roots with the union of refreshed proposals, against 2/20 with D4 at S0. Action recall is 83 % against 51 %.
- It is **ranked in the top 40 on 0 roots and selected on 0 roots** in every arm. Every verified success is a different (non-witness) set.

**Truncation:** remaining staged-beam calls fell from 16 (R2.3) to 0. There were 0 cap stops and 0 connector failures in 60 new jobs.

**Comparison with R2.3:** no new arm beats R2.3 R-FIG3 or F-FLAT. R-FIG3-X vs R-FIG3 is 0 vs 2 discordant roots, and GA-UNION vs F-FLAT is 0 vs 4. With so few discordant roots, no contrast is established.

### Y representation (identical labelled endpoints)

| Endpoints | n (Y = 1) | AUROC, Y_global | AUROC, Y_rebased |
|---|---|---|---|
| m ≥ 4 | 121 (109) | 0.85 [0.73, 0.93] | 0.86 [0.74, 0.93] |
| m ≤ 3 | 30 (17) | 0.82 | 0.68 |

Y is not the binding limit: most failures are X0Y1. X was always the rebased local query.

### 3D decision

- **ORDER: NOT_RECOVERED** (A-DP 2/20 against the witness ceiling of 19/20).
- **Local X: FAILS** at h ≥ 1.
- Preregistered verdict: **INTERMEDIATE_X_SUPERVISION_NECESSARY.**
  - **Improved inference is not sufficient.** Exact order and partition optimization, bounded exhaustive local scoring, global assignment search and prerequisite constraints all inherit the same confidently wrong local executability score.
  - **The deficit is wider than intermediate scenes.** Most committed failures are the first relocation from the initial scene, scored pX ≥ 0.83. So the targeted X supervision must cover K4/K5-like dense scenes at S0 as well as at intermediate prefixes, with grasp-blocked relocations as negatives.
  - **Hypothesis (not tested):** the TRAIN 3D support has no feasible labels at N ≥ 9, and is sparse for grasp-blocked single moves in such scenes (R2.0).

---

## 2D

### R2.4C bounded exhaustive local scoring (20 VAL K3 development roots, N 9–15)

**Truncation:**
- Staged-beam calls fell from **271 calls on 19 roots, plus 6 readout-cap stops** (R2.3 R-FIG3) to **15 calls on 6 roots and 0 cap stops**.
- Exhaustive local groups up to 50,000 ordered groups per expansion.
- Discovery takes a median of 17 s and 0.44 M readouts per root.

| Arm | Verified / decided | Undecided (UNKNOWN or budget) | Median latency |
|---|---|---|---|
| R-FIG3-X | 7 / 17 | 3 | 21 s |
| R-FIG3-XP | 6 / 15 | 5 | 19 s |
| R-FIG3-XC | 6 / 18 | 2 | 18 s |
| GA-INIT | 4 / 10 | 10 | 2.8 s |
| GA-UNION | 4 / 8 | 12 | 23 s |
| R2.3 reference: B0 / R-FIG3 / F-FLAT | 6 / 8 / 7 (of 20) | | |

**Proposal coverage vs discovery:**
- A known verified K ≤ 3 repair is entirely in the pool on 19/20 roots.
- It is ranked in the top 40 on 9 roots and selected on 6 roots (R-FIG3-X).
- R-FIG3-X vs R-FIG3 (R2.3): 0 vs 1 discordant root.

**Verdict:** the correction removes almost all truncation. **No improvement in verified outcomes is established.**
- The losses remain at selection and Y: X1Y0 on 4–5 roots per arm.
- 11 of the 30 new jobs ended UNKNOWN_PLANNER. These are counted as undecided, never as success.

### Local X (2D)

- **Labels:** 247 chunk labels, of which only 23 are non-executable.
- **h ≥ 1:** AUROC 0.74 [0.59, 0.85], but on only **5 mixed roots**. All 13 non-executable chunks at h ≥ 1 scored pX ≥ 0.5.
- **Verdict:** **INCONCLUSIVE**, because the preregistered rule needs ≥ 10 mixed roots.
- The preregistration called for new matched labels in this case. **The 60-query 2D budget was already spent on the arm verification, so they were not collected.**

**Y on identical endpoints:** n = 48 with 7 negatives, too few to separate Y_global from Y_rebased. Y_rebased remains badly calibrated (ECE 0.82).

### 2D K4–K6 witness audit (`audit2d.json`; TEST and release_v2 never opened)

- **Label pool:** the R2.0 pool (TRAIN/VAL verifier caches) has X labels only for m ≤ 3.
- **Raw records:** the 4,251 TRAIN/VAL raw records contain 214 verified B sequences of length 4–6.
  - Nearly all are padded or perturbed variants of K ≤ 3 repairs: redundant+1 or +2 (199), wrong order, wrong destination, alternative destination, or intended union.
  - **Only 2 roots** (1 TRAIN, 1 VAL; N 5–6) have a shortest verified sequence of length 4 and no certified K ≤ 3.
- **Other sources:** the R2.3 long verified plans are on K3 roots, and the kgt3 P7A-R roots are static-only.
- **Conclusion:** no usable non-TEST 2D K4–K6 cohort exists.

**Proposed bounded 2D development cohort (NOT collected; needs owner approval):**
- **Roots:** 30 roots, 10 each with witnessed length 4, 5 and 6, at N 9–15 (inside the positively supported TRAIN range).
- **Generator:** the existing BXY / plus2d generator with a chained-blocker construction, plus the unchanged BXY X/Y teacher.
- **Labels:** WITNESS_LEN_k_MIN_UNKNOWN unless a bounded K ≤ 3 refutation is run.
- **Budgets:**
  - Generation and certification: ≤ 400 candidate layouts, ≤ 4,000 teacher queries, ≤ 24 CPU-h, ≤ 16 workers on gvlab2.
  - Evaluation of the R2.4 arms: ≤ 300 queries and ≤ 6 CPU-h.
  - Storage: ≤ 2 GiB.

### 2D decision

- **R2.4C correction:** truncation removed; outcomes not improved; no contrast established.
- **Local X:** INCONCLUSIVE (too few non-executable chunks).
- **K > 3:** not testable without the cohort above.
- Whether 2D needs intermediate-scene supervision is **unresolved**. The 13/13 confident misses are consistent with 3D, but that is only a hypothesis.

---

## Resources (gvlab2 only; all within authorization)

| | Authorized | Used |
|---|---|---|
| 3D teacher | 60 jobs, 4 CPU-h | **60 jobs** (27 plans reused), **0.43 CPU-h**; 16 lower-priority plans not run (budget) |
| 2D teacher | 60 queries, 4 CPU-h | **60 queries** (30 jobs; 25 plans reused), **0.16 CPU-h**; 12 plans not run (budget) |
| GPU (RTX 5090) | 1 GPU-h per domain | ≈ 0.05 GPU-h 3D, ≈ 0.21 GPU-h 2D |
| Workers | ≤ 8 | 8 |
| Storage | ≤ 3 GiB, keep ≥ 20 GiB free | 6 MB; 34 GB free |
| Censored / errors / retries | | 0 / 0 / 0; every X = 1 independently replayed (6 in 3D, 7 in 2D) |

**Sealed manifests (sha256, first 16 characters):**

| Manifest | 3D | 2D |
|---|---|---|
| Jobs | `9e9a2225f594c80f` | `d6f82cc455ce437d` |
| Selection | `d477204b05d0c3cf` | `3c56e21b14e65bd2` |

**Figures:**

| File | Shows |
|---|---|
| `figures/R2_4A_order_recovery.png` | Per-root order-recovery matrix, witness-order rank, failure location |
| `figures/R2_4B_arms.png` | Arm outcomes; coverage vs discovery |
| `figures/R2_4_local_x_and_y.png` | Local-X AUROC by h; Y_global vs Y_rebased |
| `figures/R2_4_sequences.png` | Successful and failed sequences with chunk boundaries, home returns, the failing relocation and recursion PREREQ edges (schematic top-down layouts of the actual scenes) |

## Next steps (owner decisions; nothing started)

1. **3D:** collect targeted X supervision. These are exact local chunk labels (1–3 actions from q_ref) in K4/K5-like dense scenes at S0 and at intermediate prefixes, with blocked relocations as negatives. Then either use them for an approved training or calibration step, or for a learned executability head. Each needs its own budget and approval.
2. **2D:** approve or modify the bounded K4–K6 cohort above. Separately, a ≤ 60-query matched-label top-up would make the 2D local-X test decidable (≥ 10 mixed roots).
3. **Production:** keep the K ≤ 3 method unchanged; nothing in R2.4 justifies changing it.

**STOP.** R2.4 is complete.
