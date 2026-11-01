# 0129 — BXY-P22: final 2D method, K0–K4 evidence freeze and independent-test readiness (no confirmatory collection)

Date: 2026-11-01. Gate: BXY-P22, the last gate of the BXY-P19 → P22 contract.
- Compute: ≈ 10 CPU-s plus the checkpoint copy, against a 3,000 CPU-s ceiling.
- **No teacher query, no training, no cohort generation.**

## Verdicts

| Gate | Verdict | Basis |
|---|---|---|
| P20 data | **`K4_PHYSICAL_DATA_NOT_ESTABLISHED`** (frozen rule: K4 < 10). K3 meets the LIMITED threshold | 14 verified K3 and **7 verified K4**, every one certified necessary (K_cert = K) with replayed X + connector + Y witnesses; K4 is physically real but too sparse for stratum inference |
| P21 learning | **`NEGATIVE_OR_INCONCLUSIVE`** for the K3/K4 X/Y-specific hypotheses (H1–H3); the order hypothesis H4 is met (exploratory) | D vs DIRECT-GEO 0.000 [−0.127, +0.111] on repairable K3/K4 roots; D vs E +0.032; D vs G +0.222 [+0.048, +0.413] |
| P22 readiness | **`READY_FOR_K34_INDEPENDENT_CONFIRMATION` (protocol only)** | frozen models with second-copy custody, frozen one-shot analysis, and a new 440-slot K0–K4 plan whose K3 / K4 yield is projected from realized development rates; **no confirmatory test performed** |

**Is K4 truly verified?** Yes, physically, in 7 independent development roots. Each has:
- a replayed 4-move chain from q0;
- the connector to q_ref;
- an independent target witness;
- Y = 0 after one, two and three moves;
- a real-screen certificate that no correction moving fewer than four objects can succeed within the declared grasp family.

**Was K4 learned on held-out roots?** D chose a verified K4 repair in 0.95 of out-of-fold decisions on those 7 roots, against 0.57 for
the order-invariant control. **n = 7 does not support a statistical "learned K4" claim,** so this is descriptive.

## 1. Methodology

- **The October 31 methodology is preserved as the historical specification.**
- **The implemented-extension addendum** [0129A](0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md) documents:
  - GEO2 and SYM as P17 extensions;
  - L_D = L_joint + λ_J L_J + κ L_SYM;
  - root-consistent X/Y with shared Y;
  - the optional, unsupported quadratic coupling;
  - the selection rule;
  - the K definitions (K_intent / K_LB / **K_cert** / K_catalogue);
  - the construction families.
- **Nothing in the original is rewritten,** and no claim of coupling benefit is made.

## 2. K0–K4 evidence matrix ([EVIDENCE_MATRIX_K04.json](../runs/approach_b/bxy_p22_v1/EVIDENCE_MATRIX_K04.json); development roots P16 + P20)

| Verified K | independent roots (V21 / K34) | certified necessary | X negatives certified / budget | Y negatives certified / budget |
|---|---|---|---|---|
| K0 | 29 (18 / 11) | — | 4 / 50 | 25 / 21 |
| K1 | 19 (13 / 6) | — | 2 / 30 | 25 / 42 |
| K2 | 16 (11 / 5) | 10 | 6 / 46 | 64 / 33 |
| K3 | 16 (2 / 14) | **14** | 27 / 108 | 138 / 18 |
| K4 | **7 (0 / 7)** | **7** | 20 / 41 | 72 / 15 |

Also:
- strict permutation order twins on K34 roots: 46;
- harmful-edit roots: 23;
- infeasible roots with no verified catalogue repair: 85, mostly fixed-budget relocation failures.

**Per-stratum held-out selection with uncertainty (P21, K34, availability-conditioned, D):**

| Stratum | Success | Wilson 95% interval (approximate: seed-mean per root treated as a proportion over n roots) |
|---|---|---|
| K3 (n = 14) | 0.74 | [0.48, 0.90] |
| K4 (n = 7) | 0.95 | [0.59, 1.00] |

**Remaining bottleneck:** relocation planning under the fixed per-query teacher budget (P19 / P20). Closing every declared target mode of the
3R arm needs discs along its link paths, which also obstruct relocations. The construction revisions raised the intended K3/K4 repair
verification rate from 3 / 15 (k1) to 10 / 22 (k3).

## 3. Frozen models ([FROZEN_MODELS_P22.json](../runs/approach_b/bxy_p22_v1/FROZEN_MODELS_P22.json), sha `47b19b0b…`)

- **Arms:** candidate **D:XYQ-GEO-SYM**, challenger **E:XY-UNC-SA-GEO-SYM**, matched **A:DIRECT-GEO**.
- **Form:** each is the P21 15-checkpoint cross-fit ensemble (mean p and Ĵ, F1 first, one pooled rule).
- **Custody:** every checkpoint hash-verified in the repository and in a second copy (`/home/naren/bxy_checkpoint_backup/p21_v1`).
- **Gap:** the copy is on the same disk, with no off-machine copy.
- **Deployment recommendation (development only):** **E**, because the coupling remains unsupported. D and E are statistically
  indistinguishable, and **neither is shown better than DIRECT-GEO** with the K3/K4 data.
- **The P21 OOF numbers estimate the cross-fit procedure, not the frozen ensemble.** Every ensemble member except those in a root's own
  fold saw that root.

## 4. Independent K0–K4 confirmation proposal ([CONFIRM_PLAN_K04.json](../runs/approach_b/bxy_p22_v1/CONFIRM_PLAN_K04.json), sha `3212dd3c…`) — NOT generated

- **Namespace:** `bxyg34confirm` (new). The generator is BXY_GEN_K34C (doorway) plus P16 V21B controls.
- **Size:** **440 slots**, mix K4-doorway 55%, K3 25%, K2 5%, K0 controls 15%.
- **Expected,** from k3 realization rates (small per-family n, so indicative):
  - ≈ 50 verified K3 and ≈ 41 verified K4;
  - ≈ 91 repairable K3/K4 roots;
  - ≈ 40 K0.
- **Precision:** with the P21 paired SD (0.28; clamped to ≥ 0.30), the paired 95% half-width on repairable K3/K4 is ≈ 0.06.
  - The width scales as s_D / √n, not with the single-proportion bound (P19 correction).
- **Cost:** ≈ 70,000 CPU-s for construction plus teacher, needing **separate authorization**.
- **Missing family:** a geometrically distinct K3/K4 construction family is **not available** under the unchanged robot. Only the V21B
  controls differ in construction logic; this is stated as a limitation.
- **Stops and custody:** fixed slots, one collection, one evaluation, no interim look; a shortfall is labelled UNDERPOWERED. The P18
  300-slot plan stays immutable and unexecuted (hash checked by test).

## 5. Preregistration ([CONFIRM_ANALYSIS_P22.json](../runs/approach_b/bxy_p22_v1/CONFIRM_ANALYSIS_P22.json))

- **Primary endpoints:** unconditional and availability-conditioned repair success on initially infeasible roots, by K stratum.
- **Comparisons:** D vs DIRECT-GEO, E vs DIRECT-GEO, D vs E.
- **Tests:** paired family bootstrap (B = 10,000), two-sided 95%, Holm across the three comparisons.
- **IMPROVES gate:** CI lower > 0, point ≥ 0.10, unnecessary ≤ +0.05.
- **Secondary endpoints:**
  - unnecessary repairs (harmful / harmless);
  - no-op correctness;
  - strict order (all / certified);
  - omission sign;
  - prefix Y patterns;
  - witnessed J on matched successes;
  - certified vs budget negatives;
  - availability;
  - references.
- **Frozen action costs per arm.** **Zero test-look tuning.**
- **Honest expectation from development:** D / E vs DIRECT is likely near zero; the order effect (vs G) is the most robust signal.

## 6. Figures

| File | Content |
|---|---|
| [visualizations/approach_b/bxy_p22_v1/01_k04_evidence_and_plan.png](../visualizations/approach_b/bxy_p22_v1/01_k04_evidence_and_plan.png) | K0–K4 evidence (certified counts, K4 threshold), P21 held-out K-stratified selection, plan composition |
| P20: `00_verified_k4_*` | complete K4 physical stories |
| P20: `04_failed_k4_attempts` | failed K4 attempts |
| P20: `08_relocation_success_by_step` | relocation success by step |
| P21: `05_k4_heldout_gallery` | held-out K4 choices |
| P21: `02_success_by_K` | success by verified K |

## 7. Budgets used (BXY-P19 → P22)

| Gate | CPU-s used / ceiling | Wall s used / ceiling |
|---|---|---|
| P19 | ≈ 120 / 2,000 | ≈ 240 / 3,600 |
| P20 | 23,909 / 60,000 (incl. 2,642 incident charges) | 7,052 / 28,800 |
| P21 | 49,411 / 65,000 | 12,799 / 30,000 |
| P22 | ≈ 10 / 3,000 | < 100 / 5,400 |

## 8. Regression

Recorded in `runs/approach_b/bxy_p22_v1/regression/`:
- full suite: **718 passed, 1 skipped**;
- six archived replays: exit 0;
- hash guard: clean.

STOP (end of the BXY-P19 → P22 contract). No independent confirmatory cohort was generated.
