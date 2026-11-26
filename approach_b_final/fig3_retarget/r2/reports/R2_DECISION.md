# R2 decision: why the frozen X/Y model plus recursive retargeting struggle beyond K = 3

**Scope.**
- **Branch:** `naren/rss27-fig3-retarget-home`, stages R2.0 `acca6caf64`, R2.1/R2.2 `9903e9474f`, R2.3 and this decision (final commit).
- **Contract:** `fig3_R2_dual_domain_diagnostic_plan.md` with preregistration `r2/R2_PREREG.json` (sha256 `e6d8a225…`).
- **Constraints respected:** gvlab2 only; no training; no TEST or release_v2 access; the production K ≤ 3 method is unchanged.
- **Reading this report:** each claim is marked **established** (its preregistered rule is met), **not established**, or **hypothesis**. 2D and 3D are separate.

## The owner's question: does the total object count N limit the learned representation, independently of m?

| | 3D | 2D |
|---|---|---|
| Training support (R2.0) | N 1–13; **every N ≥ 9 TRAIN root is NONE (Y = 0)** | N 1–20; **every N ≥ 16 TRAIN root is NONE (Y = 0)**; cVAE hard cap MAXOBJ 20 |
| Natural held-out panel, supplied m ≤ 3 labels (R2.1) | **No degradation**: AUROC 0.84–0.94 across N bins; 6–7 vs 1–3 = +0.004 [−0.046, 0.060] | **No degradation up to N 15**: 11–15 vs 1–5 = −0.020 [−0.073, 0.031]. **N 16–20: unidentifiable** (0 feasible labels anywhere) |
| Matched add-distractor panel (R2.1-A, new labels) | The model **tracks** distractor-induced label changes; the unchanged subset keeps discrimination; mean pY of feasible endpoints falls 0.68 → 0.58 → 0.32 (n small) | Added bodies change most labels; the model **shifts every pY toward 0** (feasible: 0.75 → 0.31 → 0.33) while within-level ranking holds (0.91 / 0.81 / 0.84; 3–4 positives) |
| Verdict | **H_N NOT ESTABLISHED.** The K4/K5 cohort (N 5–9) is inside support, and N does not explain its failures. | **H_N NOT ESTABLISHED as a representation-capacity limit.** A **label-support shortcut** at N ≥ 16 (no positive supervision) is **supported as a hypothesis**. It cannot be separated from physical difficulty because added bodies genuinely change feasibility. |

**Answer:** the object count is **not** shown to limit the representation within the counts the model was trained on, in either domain. Beyond that support (2D N ≥ 16, 3D N ≥ 9), the training data contain **no feasible examples at all**. Any failure there is first a **data-support gap**, which the frozen model cannot be expected to bridge. Chunking reduces m but cannot fix this.

## Per-hypothesis summary

| | 3D | 2D |
|---|---|---|
| SCORER_SIGNAL, local m ≤ 3 | **Yes**: AUROC 0.871 [0.854, 0.889]; top-1 +0.26 | **Yes, weaker**: 0.789 [0.775, 0.802]; top-1 +0.19 |
| H_m, longer m is out of distribution | **Established**: m3 − m1 −0.128; direct m = 4/5 ≈ chance (0.55) | **Established**: m3 − m1 −0.088 |
| H_h, rebasing changes the input distribution | **Established, small**: −0.014 | **Established**: −0.047; rebased Y badly under-confident (ECE 0.40) |
| H_T, temporary targets scored worse | **Established** (Y_τ 0.82 vs 0.97); retargeting the scorer is essential (0.82 vs 0.38) | **Established** (0.69 vs 0.89); retargeting helps (+0.11) |
| RETARGET_SIGNAL, within-context ΔpY | **Yes**: 0.89 | **Yes**: 0.70 |
| Admission (relative pY) | Discards 21 % of enabling groups (17/93 verified) | Filters nothing (admits 99.5 % of non-enabling groups) |
| H_C, candidate loss | The staged beam keeps the best group in only 10 % of roots at N 8–13 (default off below 4,096 groups). The R2.3 funnel shows proposals reach 83–86 % recall, but **no arm composes the witness set** (12/20 "proposed but not composed") | The staged beam keeps the best group in 4–30 % of roots at N ≥ 6, where it is active. The R2.3 funnel loses at composition and ranking (11/20); proposal recall 90–97 % |
| H_H, home connectors | **CONNECTOR_COMPATIBLE** (narrow): 47/51 = 0.92 [0.82, 0.97]; failures rise with the number of returns | **CONNECTOR_COMPATIBLE** (narrow): 66/72 = 0.92 [0.83, 0.96] |
| H_R, recursion adds useful repairs over flat | **NOT SUPPORTED**: R-FIG3 5/20 vs F-FLAT 7/20 (0 vs 2 discordant); R-FIG3 vs B0 3 vs 0 | **NOT ESTABLISHED**: R-FIG3 8/20 vs F-FLAT 7 (2 vs 1), B0 6 (2 vs 0), K3 roots only |
| Failure mode of committed long plans | **Endpoints right, execution wrong**: 14 of 15 R-FIG3 failures are X = 0 at a relocation with Y = 1 | Mixed: X1Y0 2, X0Y1 5, X0Y0 3 |

## Per-domain decisions (plan section 6 labels)

- **3D: SCORER_SIGNAL (local) + RETARGET_SIGNAL + CONNECTOR_COMPATIBLE + SEARCH_LIMITED (composition) + FROZEN_MODEL_LIMITED (executability of composed sequences beyond m = 3).**
  - **Where the >K3 failure lies:** composing retargeted proposals into an **executable order**. Neither the frozen energy (direct pX at m = 4/5 ≈ chance; chunk pX on rebased views) nor the R-FIG3 composition rule identifies it.
  - **Where it does not lie:** object count, Y, or home returns.
- **2D: SCORER_SIGNAL (weaker) + RETARGET_SIGNAL (modest) + CONNECTOR_COMPATIBLE + SEARCH_LIMITED (staged beam, composition / selection) + FROZEN_MODEL_LIMITED beyond N 15 (no positive supervision).**
  - K > 3 cannot be evaluated in 2D with physically verified, non-protected material.

## Recommended next action (requires owner approval; nothing started)

**3D (most promising):**
1. A model-only composition study on the 20 exposed roots: search the **union** of retargeted proposals (83–86 % witness recall) for complete action sets, then rank orders by local chunk pX. Report how often the witness set and other verified sets become reachable.
2. Only if that shows reachable sets: a small physical check within a new budget (≤ 60 jobs).
3. Executability needs a signal the frozen pX lacks at m > 3 and h > 0. The honest options are new X labels for intermediate-scene chunks (data collection) or targeted training. **Both are owner decisions.**
4. No new long-root generation is justified until (1) shows reachable executable sets.

**2D:**
1. Replace the staged beam inside recursion with bounded exhaustive per-object scoring (an engineering fix, model-only, cheap).
2. Use Y_global rather than rebased Y for temporary and chunk energies (R2.1: rebased is badly under-confident).
3. Any claim at N ≥ 16 or K > 3 requires **new positive supervision or new verified long witnesses**. This is a data and training decision for the owner; do not attempt it with the frozen model.

## Resources (all within authorization; gvlab2 only)

| | Authorized | Used |
|---|---|---|
| 2D teacher | 300 queries / 4 CPU-h | **261 queries** (202 job records) / **0.47 CPU-h** |
| 3D teacher | 120 jobs / 6 CPU-h | **120 jobs** / **0.80 CPU-h** (cap reached; 29 lower-priority R2.3 plans NOT_RUN) |
| GPU (RTX 5090) | 0.5 GPU-h per domain | about 0.31 GPU-h total (2D ≈ 0.2, 3D ≈ 0.1) |
| Workers | ≤ 8 | 8 |
| Storage | ≤ 5 GiB, keep ≥ 20 GiB free | 81 MB; 34 GB free |
| Errors / retries / censored | | 0 / 0 / 0 |

TEST, release_v2, training and merges: none.

**STOP.** The R2 tranche is complete.
