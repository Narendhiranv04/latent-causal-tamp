# R3 decision (stopped at the R3.2/R3.3 local gate)

**Branch:** `naren/rss27-fig3-retarget-home`; baseline `a4265ccf54`.

| Commit | Content |
|---|---|
| `bdbbce7e0c` | R3.0 audit and pre-registration |
| `56c1894f2f` | R3.1 data |
| `b3db8afc37` | Addendum A1, sealed before G1s/M1s training |
| this commit | R3.2/R3.3 results, 2D cohort, decision |

**Production.** The K ≤ 3 bundle is untouched. Every scaling checkpoint lives under gvlab2 `naren_workspace/fig3/r3/ckpt`. Nothing was merged.

**Evidence status.** No result below is independent confirmation. VAL_SCALE is a pre-registered development validation panel. The R2.4 K4/K5 panel is exposed and was used for diagnosis only.

## 3D

| Stage | Outcome |
|---|---|
| R3.0 contract | **PASS.** Teacher determinism 8/8; ideal-pose hypothetical start equals physically reached prefix 12/12; derived prefix negatives 6/6; original training labels equal chunked contract 8/8. The F0 error is in the conditional execution logits: 144/157 confident negatives have σ(a) and σ(a+w) ≥ 0.8. Training X labels contain almost no blocked first relocation (natural m = 1: 133/134 positive). GA Y-only shortlist ranks verified witness sets 349–11,897. |
| R3.1 data | 588 jobs (pilot cap 600), 792 exact labels. VAL_SCALE mixed families: 23 at h0, 10 at h ≥ 1. Expansion trigger not met. 367/376 negatives are "no feasible side grasp". |
| R3.2 F1 head-only | **FAIL.** Paired h ≥ 1 +0.03 [−0.02, 0.08]; first-relocation FPR does not fall. Mostly recalibration (ECE 0.22 → 0.08). Y bitwise. |
| R3.2 F2 full | **FAIL.** +0.04 [−0.01, 0.10]; FPR drop 0.00. Y AUROC −0.002. |
| R3.3 G1 / M1 at lr 1e-4 | Under-fit from random initialisation, so not a representation test. Addendum A1 applied. |
| R3.3 G1s / M1s at lr 1e-3 | **Best: G1s s0.** VAL h ≥ 1 0.948 [0.88, 0.99]; paired +0.123 [0.057, 0.198]; h0 0.931; m 2–3 at h ≥ 1 0.926; Y bitwise; NATURAL_VAL p11 0.889 vs 0.896 [−0.025, +0.012]. **First-relocation FPR at TPR 0.8: 0.087 vs F0 0.217. The drop of 0.130 misses the pre-registered ≥ 0.15 by one negative of 46.** No other candidate passes. Graph vs capacity-matched MLP with the same query-relative geometry: not separable (+0.036 [−0.018, 0.091]). |
| R3.3 diagnostic, exposed K4/K5 panel | G1s s0: h ≥ 1 0.52 → 0.76; first relocations 0.64 → 0.93; FPR at TPR 0.8 0.80 → 0.09. Multi-action intermediate chunks still weak (0.59). Descriptive only. |
| R3.4 order recovery | **NOT STARTED.** It requires a passed local gate. |
| R3.5 search | **NOT STARTED.** It requires R3.4. |

**3D decision.** The local gate is **UNRESOLVED (narrow miss, a single FPR component)**. It is not DATA_LIMITED, because support is adequate. It is also not a representation failure: a geometry-aware X head trained on the new local labels clears every other component by wide margins.

The frozen model's deficit is regime-specific. F0 already reaches 0.83 at h ≥ 1 on family-independent N 5–9 scenes, but only 0.52 on the dense, enabler-constructed K4/K5 layouts. That regime is under-represented in VAL_SCALE.

## 2D

| Stage | Outcome |
|---|---|
| R3.0 | Determinism 8/8, including deterministic unresolved planner outcomes. `x_query` = `x_chunked({m})` 3/3 (R1). Same confident-logit pattern: 17/18. |
| R3.1 diagnostic (60 queries) | Pooled h ≥ 1 AUROC 0.81 [0.70, 0.90] on only 6 mixed families (< 10): **INCONCLUSIVE (support)**. Unresolved connectors (10) and planner runs (15) truncate most h ≥ 1 observations. |
| Consequence | No 2D targeted collection, training, graph model or order recovery in this tranche. |
| R3.1 cohort (DEV_ORDER_2D) | **30 roots, all CERTIFIED_MIN_K** (witness length = sound bound K_lb V1 = V2; X = 1 and Y = 1 independently replayed; Y(empty) = 0 certified): 10 each at L = 4 / 5 / 6. N ranges 14–20; only 4 are in 9–15, because the generator favours dense layouts. 5 more certified roots are held in reserve (in-flight overshoot). Generator: k3scale `gen_deep` + `witness_v3`, unchanged, with string-seed namespace `R3COH2D`. Release_v2 was never read and was not de-duplicated against, by design. Manifest: `r31/DEV_ORDER_2D_cohort.json`. |

**2D decision.** Local X is **INCONCLUSIVE (support)**. A long-required cohort now exists for future 2D order recovery, which was blocked by the X gate in this tranche.

## Resources (gvlab2 only, cumulative R3)

| | Used | Ceiling |
|---|---|---|
| 3D R3.0 | 34 jobs / 0.21 CPU-h | 40 / 2 |
| 3D R3.1 | 588 jobs / 2.79 CPU-h | 1,000 / 20 (pilot 600) |
| 3D R3.2–R3.5 physical | 0 | 60 + 80 + 120 |
| 2D R3.0 | 8 queries / 0.02 CPU-h | 40 / 2 |
| 2D R3.1 diagnostic | 60 queries / 0.17 CPU-h | 60 / 2 |
| 2D R3.1 cohort | 139 layouts / 1,325 queries / 6.17 CPU-h (static 3.14 + witness 3.02; plus a 15 CPU-s smoke run) | 400 / 4,000 / 24 |
| 2D targeted, regression, R3.4, R3.5 | 0 | – |
| GPU | ≈ 0.15 GPU-h in total; training ≈ 0.05 GPU-h | 6 + 2 per domain |
| Workers | ≤ 16 concurrent | 16 |
| Storage | ≈ 45 MB | 5 GiB; 34 GiB free |

There were 0 errors, 0 censored jobs and 0 retries. Sealed manifests:

| Manifest | sha16 |
|---|---|
| `parity_jobs_3d` | `7ec6bf5428e04a98` |
| `parity_jobs_2d` | `e26e17ba0566f26c` |
| `jobs_31_3d` | `602f4b1faed7fec2` |
| `jobs_31_2d` | `6331f472831df6a4` |

Checkpoint sha16:

| Checkpoint | sha16 |
|---|---|
| G1s s0 | `6dae59fd97cb5cd3` |
| G1s s1 | `aae2eeceace50119` |
| M1s s0 | `bb8373a0260dd40c` |
| F1 s0 | `64d9aa6092c0998f` |
| F2 s0 | `ad8256e2f933b987` |

## Next required action (owner decision; nothing started)

1. **3D gate.** Choose one of:
   - **(a) Recommended: a sealed confirmation top-up.** Use part of the unspent R3.1 3D reserve (e.g. ≤ 200 of the remaining 412 jobs) to collect new VAL_SCALE families with no retraining. Re-evaluate the frozen G1s s0 and F0 on the enlarged panel with the same pre-registered gate. Include dense enabler-constructed layouts from clean families (the K4/K5 regime), since that is where F0 fails. This settles the FPR component with more negatives and tests the regime that matters.
   - **(b) A gate exception.** Authorize R3.4 with G1s s0 as is (80 jobs), recorded as an exception.

   Neither may tune on the 20 exposed roots.
2. **3D search (if R3.4 later passes).** Address GA retention first: Y_global saturates, so the shortlist needs X-aware diverse retention.
3. **2D.** Choose between:
   - a re-designed h ≥ 1 diagnostic (prefixes chosen to avoid unresolved connectors, or a larger budget) to reach ≥ 10 mixed families;
   - an owner-approved frozen-X order-recovery pilot on the new 30-root certified cohort.
4. **R4** is not started and needs separate approval.

**Limitations**
- The VAL_SCALE h ≥ 1 support is exactly at the 10-family floor.
- There is no F0-architecture-from-scratch ablation, so the optimizer and the query-relative-geometry effects are not fully separated.
- The 2D cohort is denser than the preferred N range.
- The 2D cohort was not de-duplicated against release_v2 (by design; disjoint seed namespace).

**Figures**
- `figures/R3_0_audit.png`
- `figures/R3_1_data_3d.png`
- `figures/R3_1_cohort_2d.png`
- `figures/R3_2_3_training.png`
