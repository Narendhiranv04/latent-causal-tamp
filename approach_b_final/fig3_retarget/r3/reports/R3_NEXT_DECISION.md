# R3 — next decision (after addendum A2)

**Branch:** `naren/rss27-fig3-retarget-home` (not merged).

| Commit | Content |
|---|---|
| `d56e1253b5` | A2 pre-registration and sealed manifests |
| `9a538428e2` | Partial R3.3A evaluation, **superseded** (see the incident below) |
| `df1e611f09` | R3.4 / K≤3 regression manifests, **void** |
| this commit | Complete results and reports |

**Unchanged:** production K ≤ 3 bundle, cVAE, the X/Y formulation, the teacher contracts and every checkpoint. No training was done. TEST and release_v2 were not accessed. Everything below is development evidence.

## 3D

| Stage | Outcome |
|---|---|
| R3.3A validation extension (195 jobs, 27 new clean VAL families) | **Pre-registered rule NOT PASSED.** On POOLED, all four original components pass for G1s s0: support 46 / 15; h ≥ 1 0.914 [0.85, 0.97]; paired +0.088 [0.006, 0.163]; first-relocation FPR 0.255 → 0.092. **The guard fails:** the new independent labels alone give paired h ≥ 1 −0.020 [−0.155, 0.081]. NEW_DENSE h ≥ 1 has only 2 mixed families, so the DIAGNOSTIC_ONLY route is also closed. |
| What replicated | The first-relocation / h0 gain on new families: paired +0.103 [0.03, 0.17]; first-grasp false positives 13/52 → 5/52; DENSE 8/37 → 2/37; calibration ECE 0.33 → 0.07. |
| What did not | The h ≥ 1 (intermediate-scene) gain. The static DENSE chains over-blocked: E1 executable 6/19, pivot freed by E1 1/5. Most h ≥ 1 states were never reached. Multi-action h ≥ 1 chunks have 0 mixed families on the new panel. |
| R3.4 order recovery | **NOT AUTHORIZED; no result.** 20 R3.4 jobs and 29 regression jobs ran in error before being stopped. Their outcomes are quarantined unopened (`R3_3A_VALIDATION_REPORT.md` §3). |
| K ≤ 3 physical regression | Not completed, so there is no claim about short-horizon preservation. The sealed selection shows that 166/338 NATURAL_VAL roots would change their EXACT4 selection under G1s. Deploying G1s at K ≤ 3 is therefore a material change. |

**3D decision.** STOP. The local gate stays failed, both on the original VAL_SCALE and under the A2 extension. No R3.4, R3.5 or deployment claim is made.

## 2D

| Stage | Outcome |
|---|---|
| R3.1D diagnostic (120 queries, established prefixes) | **PASS** for frozen X at h ≥ 1: union 0.829 [0.751, 0.899], 18 mixed families; R3.1D alone 0.829, 12 families. Prefixes reproduced 90/90. 28 UNKNOWN runs kept as UNKNOWN. **The pass is single-step:** h ≥ 1, m = 2–3 gives 0.725 on 3 mixed families (R3.1D alone 0.40). |
| R3.4D order pilot (30 certified K4/K5/K6 roots, given assignment) | **FX-DP 3/30**, RANDOM 2/30 (paired p = 0.50), **WITNESS 29/30** under the same chunk protocol. Fails the 70 % / 50 % reference bands. FX-DP mostly fails at the first relocation (19/27 non-successes), choosing long chunks that skip enablers. The model ranks the verified order at a median quantile of 0.80. |

**2D decision.**
- **What works.** Single-step local X is adequate, and the execution protocol is sound (witness 29/30).
- **What fails.** Frozen-X ordering does not recover long repairs.
- **The bottleneck.** The X score of *order- and chunk-dependent* groups, not single moves. Better single-step AUROC did not imply better ordering.

## R3.5

**No proposal.** A2 makes the R3.5 proposal conditional on order recovery in either domain, which did not happen. The known GA Y-only shortlist bottleneck (R3.0) remains documented but does not bind until ordering works.

## Owner decisions needed (nothing started)

1. **Quarantined 3D outcomes** (20 R3.4 + 29 regression jobs, gvlab2 `fig3/r3/QUARANTINE_unauthorized/`). Choose one:
   - discard them;
   - authorize opening them as a labelled DIAGNOSTIC only, with no gate or recovery claim.

   They were produced against the sealed plans, so they are scientifically interpretable. But they were not authorized by the A2 rule.
2. **3D h ≥ 1 validation** (if 3D continues). The static DENSE design does not produce reached intermediate states. A design that would:
   - build chains with the K4/K5 generator's teacher-verified pick/park probes on clean VAL families;
   - or take h ≥ 1 states from verified K ≤ 3 VAL sequences.

   Either needs a new budget, and the guard should be pre-registered again.
3. **2D next question.** Why does frozen X mis-rank enabler orders even though it passes single-step?
   - A zero-cost first step: analyse the exact chunk labels already produced by the pilot (90 runs). It would show which chunks (h, m) the DP mis-scores.
   - Any new 2D order-specific supervision or training needs separate authorization. It would use the R3.1 2D targeted reserve, which is unspent and was untriggered.
4. **R4** is not started and needs separate approval.

## Resources (A2 tranche, gvlab2 only, ≤ 16 workers)

| Item | Used | Cap |
|---|---|---|
| 3D R3.3A | 195 jobs / 0.76 CPU-h | 200 / 4 |
| 3D R3.4 (unauthorized, quarantined) | 20 jobs / 0.20 CPU-h | 80 / 4 |
| 3D regression (unauthorized, quarantined) | 29 jobs / 0.15 CPU-h | 60 / 3 |
| 3D killed in-flight jobs | ≤ 0.2 CPU-h (estimate) | – |
| 2D R3.1D | 120 queries / 0.30 CPU-h | 120 / 4 |
| 2D R3.4D | 120 queries (90 X + 30 Y) / 0.41 CPU-h | 180 / 5 |
| GPU | ≈ 0.05 GPU-h (inference only) | 2 eval per domain |
| Storage | ≈ 12 MB | – |

Cumulative R3: 3D 866 jobs / 4.1 CPU-h; 2D 1,633 queries / 7.1 CPU-h. Details are in `R3_LEDGER.json`.

## Limitations

- VAL_SCALE was used for G1s early stopping. Only the NEW panel is independent, and it is small at h ≥ 1 (5 mixed families).
- The DENSE stratum differs from the teacher-constructed K4/K5 chains (static adjacency vs verified pick/park probes).
- The 2D pilot cohort is dense (N 14–20). WITNESS success is under the frozen-X partition, not the witness's own continuous mode.
- **Process error:** the premature evaluation and dispatch, disclosed in full in `R3_3A_VALIDATION_REPORT.md` §3.

## Reports and figures

- **Reports:**
  - `R3_3A_VALIDATION_REPORT.md`
  - `R3_1D_2D_DIAGNOSTIC_REPORT.md`
  - `R3_4D_2D_ORDER_PILOT_REPORT.md`
- **Figures:**
  - `figures/R3_3A_validation.png`
  - `figures/R3_1D_2d.png`
  - `figures/R3_4D_order_2d.png`
- **Sealed manifests and results:** `r33a/`, `r31d/`, `coh2d/`, `r34/` (void), `regr/` (void).
- **There is no `R3_4_ORDER_RECOVERY_REPORT.md`:** 3D R3.4 was not validly executed.
