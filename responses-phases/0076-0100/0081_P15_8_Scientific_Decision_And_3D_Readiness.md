# 0081 — P15-8: scientific decision and 3D readiness

**Decision.** P15 is complete as an engineering / scientific **audit**: every executed claim is sound, and every experiment that was not run is labelled.

- **Overall status: PARTIAL.**
  - Search correctness, lookup evidence, B closure and both benchmarks were executed in full.
  - The primary D hypothesis is **UNDERPOWERED**: it produced no informative pairs, and the observed effect is zero.
- **3D is not authorized** by this contract. Our recommendation is **not to move to 3D on the strength of D guidance**; §4 gives the reasons and the preconditions.

## 1. What P15 established (numbers in reports 0073–0080)

| stage | key numbers | verdict |
|---|---|---|
| P15-0 audit | P14 manifest: 0 hash mismatches. D3 reproduced: P14 D 4 / 6 vs 3 / 6 for the others on 6 common roots. Validation-matched coverage 0.694, but test admission 0.827–0.910 | claims corrected (7 errata) |
| P15-1 D interface | Builder reproduces training records exactly. Original-state probes: 116 total, 103 decided (83 V, 20 CI, 13 UNKNOWN), feasible recall 0.169 (old and new). Intermediate states: 60 probes, feasible recall 0.204 → 0.352. DEV recalibration (root-split CV, 157 decided, 36 roots): balanced accuracy 0.924 [0.871, 0.989] | raw interface **NEGATIVE**; recalibrated **SUPPORTED** (CV) → recursion enabled, no retrain |
| P15-2 lookup | 4,821 witnesses (17 fingerprint leaks dropped), 1,163 modes, 328 with ≥ 2 independent roots. 330 held-out queries / 6,890 certifications: top-1 0.506, any 0.724, 53 rare-mode rescues, first−best travel 0.159. DEV threshold rejected (loses 11.6 % on TEST) | multimodality **SUPPORTED**; threshold **NEGATIVE** |
| P15-3 search | tri-state statuses; claims only within the declared finite graph; 19 / 19 tests (2 added after the amendment); 0 replay failures across 408 benchmark root-searches | **SUPPORTED** (sound) |
| P15-5 retrospective (24) | D 16, D-norec 16, D-pairless 17, geometry 16, uniform 18, oracle 18. D vs geometry 1 / 1 discordant, p = 1.0. P14 six-root D edge not reproduced (P15: D 4 / 6, geometry 5 / 6) | **UNDERPOWERED** (exploratory) |
| P15-5 prospective (32) | all deployable arms 27 / 32 (oracle 28). D vs geometry **0 discordant**, CI [0, 0]. Motion calls −1.7 %. D inference 1.3 % of CPU | **UNDERPOWERED**; call-reduction **NEGATIVE** |
| P15-6 ablations (12) | combined / local / global / threshold 10, representative 10 (+18 % travel), modal-top1 9, online-only 8. All ≤ 2 discordant | **UNDERPOWERED** |
| P15-7 B | ranking: K-B > F2-off / SF (p ≤ 1e-5); ≈ others. Zero-move on feasible originals: K-B picks empty 0.543. T + b calibration: no validated gain | extra factors **NEGATIVE**; P16 proposal costed (≈ 31.5 k CPU-s) |

## 2. Why D could not show an effect here

1. **Guidance only reorders a finite graph.** Where the budget allows full adjudication, every sound order returns the same optimum (test 11; 20 / 32 prospective roots have proven minimum moves). Differences can appear only on truncated roots: 9–12 per arm.
2. **On truncated roots the binding resources are the online planner and its wall-clock cut, not ordering.** Six of the ten roots unsolved by every arm fail through UNKNOWN_PLANNER and the CPU cap after 0–172 motion checks.
3. **The arms almost always agree, and when they disagree it cuts both ways.** D and geometry both rank the true blockers first on nearly every root, and outside-union moves are 0 for every arm. Ordering decisions coincide, so outcomes coincide. The two retrospective discordances go in opposite directions (009 favours D, 003 favours geometry).
4. **The oracle barely helps either.** It knows the true blocker union, yet gains only +1 / 32 prospectively and +2 / 24 retrospectively, the same as uniform. That bounds what any blocker-scoring guide could add under this action domain and budget.

## 3. Resources (CPU-s; caps are upper bounds)

| category | spent | cap |
|---|---|---|
| audit | 1 | 3,000 |
| retarget probes | 384 | 8,000 |
| retarget train / teacher | 0 / 0 | 10,000 / 15,000 (not needed) |
| index / transfer | 1,676 | 6,000 |
| search development | 1,368 | 8,000 |
| retrospective 24 | 19,799 | 27,000 |
| prospective | 24,796 | 38,000 |
| ablation | 8,047 | 12,000 |
| B diagnostics | 3 | 3,000 |
| regression | 758 | 3,000 |
| **total** | **56,832** | |

**Notes on the totals:**
- Voided pre-amendment arm runs (11 × 286 = 3,146 CPU-s) stay charged.
- One case-figure attempt was killed by an operator error after ≈ 20 CPU-s and has no guard record (`p15_5_case_retro_003b`).
- The soft per-root cap was overrun beyond 160 s on 101 of 408 root-searches (maximum 601 s); this is counted as recorded and affects every arm.

**Regression:** 457 / 457 tests (438 historical + 19 P15) and 6 / 6 archived replays (`runs/p15/regression/regression_result.json`, 758 CPU-s).

## 4. 3D readiness recommendation

**Do not move to 3D on the basis of D-guided rearrangement.** The 2D evidence shows no benefit at frozen budgets, and the oracle bound is small.

What *is* portable:
- the tri-state certified search, with its UNKNOWN discipline and finite-graph claims;
- the multimodal similarity-indexed witness library;
- the label-custody protocol (prereg → sealed labels → manifest → unseal).

**Preconditions before any 3D phase:**
1. **Make the online planner deterministic** (a seeded iteration budget instead of a wall-clock cut), or record `wall_clock_dependent` per edge. One prospective case re-run diverged under different load.
2. **Lower the online-planner cost per call.** Expensive UNKNOWN_PLANNER failures cause most unsolved roots.
3. **Raise index coverage beyond 72.4 % "any certifiable"** before relying on lookup.
4. **Size any future D-vs-geometry test on truncated roots only.** Expected discordance below 10 % needs well over 60 such roots for 80 % power.
5. **Keep B secondary.** Only the zero-move decision rule (P16) is worth confirming.
