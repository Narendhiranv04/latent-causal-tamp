# 0085 — P16-B0/B1: lean B — exact energy, the no-op, and the dev pilot

**Scope.** This report covers B's mathematics, code and tests, the dev pilot, and the training and calibration set-up. Prospective test results are in 0088.

## 1. The learned method (as implemented in `p16_b.py`; checked against the source)

**Inputs (runtime, scene-only):**
- DINOv2 mask-pooled features of the rendered scene (identical cylinders; no target, goal or robot drawn);
- numeric object, target, goal and robot context (`learn_data.learner_tensors_v2`);
- a **scene-only candidate catalogue** Q(S) from `p16_common.catalogue`:
  - the empty repair ∅;
  - each pool object moved alone to its scene-only parking slot;
  - every ordered pair;
  - the pool lattice scenes (parked subsets).

**Keyed variables.** Every distinct physical query q (one ordered repair, or one parked-subset scene) has exactly one binary outcome y_q. `unique_factor_keyed.instances` raises `IdentityError` if one query string names two sequences (test `test_keyed_identity_rejects_one_query_two_sequences`).

**Energy (couple = "none"):**

E(y | S, Q) = − Σ_q s_q(S) · y_q,  with
- s_∅ = scene head on the unedited scene vector (the **no-op** unary);
- s_zS = scene head on the parked-scene vector;
- s_r = order head on the **ordered** action tokens (F2: B prefix-pair `pairo` / `mix`), so s_{A→a, B→b} ≠ s_{B→b, A→a} (test).

**Joint and normaliser (exact, closed form):**

P(y | S, Q) = Π_q σ((2y_q − 1) s_q / T).

The per-block pairwise energies are identically 0 (asserted in the test), and `unique_factor.log_evidence` equals both brute-force enumeration and the closed-form Σ log σ to 1e-9 (test). **No learned interaction between queries is claimed.**

**Loss:** L = − Σ_{q observed} log σ((2y_q − 1) s_q / T), averaged over roots.
- UNKNOWN labels are **summed out**: the likelihood with an UNKNOWN label equals the likelihood with that label deleted, and differs from forcing it to 0 (test).
- λ_static = λ_travel = 0, so the learned F1 head and the J head receive no gradient and are never used.
- The static veto is analytic (`learn_data._static` screens; certified only at execution).

**Inference (frozen, calibration-split only):**
- p′_q = ensemble mean over 3 seeds of σ(s_q / T).
- **No-op first:** if p′_∅ ≥ t0 → **EMPTY**; else, among repairs with p′ ≥ t, take the fewest moves, then the highest p′ → **REPAIR**; else **ABSTAIN**.
- (t0, t) are chosen on the calibration split to maximise teacher-scored correct decisions; UNKNOWN-labelled choices count as not correct.
- EMPTY, ABSTAIN and a physical UNKNOWN are three distinct outcomes (test `test_lean_b_order_sensitive_and_no_op_distinct_from_abstain`).
- **Execution:** the chosen ordered repair is certified step by step (`verify_sequence`: cheapest certified motion mode per step, then the target) and independently replayed. EMPTY executes the original target action.

## 2. Retained, removed, deferred and untested components

| component | status in P16 lean B | why |
|---|---|---|
| DINOv2 + numeric context | **retained** | predictive (P11–P13) |
| keyed physical-query identity | **retained** | catalogue / omission invariance |
| F2 order-sensitive repair representation | **retained** (B prefix-pair; GRU = arm LC) | P13 targeted order effect; P15 ranking |
| scene / query unaries, including the no-op unary | **retained** | the minimal B |
| learned F1 static head | **removed** (λ = 0; analytic veto) | not supported |
| F3 scene pair | **removed** | reversal / no practical benefit |
| F4 omission pair | **removed** (archived in P13 checkpoints) | gain was admission-driven |
| F5 combined (generic + HO) | **removed** | natural-mix harm |
| F5 higher order | **deferred** | underpowered |
| learned J | **removed** (measured travel only) | underpowered |
| generic-only pair term (`cpl`; HO absent on both sides) | **new arm LB+G**, matched data and seeds | untested hypothesis H-B2 |

**Parameter counts.** The static and J heads are untrained and inactive in every arm (gradient 0).

| arm | parameters |
|---|---|
| LB | 467,365 |
| LB-F2 | 368,549 (order head removed; not capacity-matched, as in P13) |
| LC | 484,133 |
| LB+G | 516,774 |
| A | 450,596 |

## 3. Dev pilot (12 DEV roots; frozen P13 checkpoints; `runs/p16/b/B_DEV_PILOT.json`)

| frozen P13 arm | mean P(empty) on feasible originals (n = 2) | on infeasible originals (n = 10) | mean within-root AUROC | top-1 decided-feasible |
|---|---|---|---|---|
| K-B | 0.679 (DENSE 0.41, NAT 0.94) | 0.075 | 1.00 | 0.667 |
| A | 0.780 | 0.020 | 1.00 | 0.583 |
| SF | 0.709 | 0.023 | 1.00 | 0.333 |
| K-C | 0.955 | 0.057 | 0.95 | 0.667 |
| B-F2 | 0.964 | 0.082 | 1.00 | 0.583 |

The frozen K-B reproduces the P15 defect on a non-NAT feasible original: P(empty) = 0.41 on DENSE 10004. This is development evidence only (n = 2 feasible).

## 4. Data, training and checkpoint selection (frozen in `437e771` before any test label)

**Training data** (`runs/p16/b/TRAIN.pt`, sha `1d9c736c…`):

| split | P13 roots | P16 roots |
|---|---|---|
| training | 440 P13 train (constructor catalogues, P13 teacher labels) | 79 train + 12 dev (scene-only catalogues, certificate-only labels) |
| checkpoint selection | 74 P13 validation | 21 P16 val |

- **P16 labels:**
  - 42 train roots carry full sequence labels;
  - the other 37 train roots and 16 val roots carry **lattice-only** labels (original + parked subsets), after measured labelling cost (~350 CPU-s per full root) threatened the `data` cap;
  - the calibration split keeps full labels.
- **Feasible NAT originals:** train 24, val 3, calib 12. Many NAT originals stay UNKNOWN under `P16_FAST` (train 9, calib 10); they are masked.

**Training protocol** (P13 protocol, matched across arms): 400 updates, batch 12 (RootSampler), AdamW lr 1e-3, clip 10, checkpoint chosen on validation root NLL, λ_static = λ_travel = 0 for every arm.

| arm (3 seeds) | best validation root NLL | best update | CPU-s / run |
|---|---|---|---|
| **LB** | 1.979 / 2.275 / 2.347 | 380 / 300 / 280 | 381–398 |
| LB-F2 (order-invariant) | 2.362 / 2.612 / 2.639 | 380 / 200 / 280 | 340–352 |
| LC (GRU order) | 1.951 / 2.155 / 2.487 | 400 / 300 / 400 | 403–410 |
| **LB+G** (generic-only coupling) | **1.654 / 1.759 / 1.890** | 400 / 320 / 400 | 415–432 |
| A (retrained) | 2.197 / 2.062 / 2.184 | 380 / 300 / 280 | 283–296 |

**Validation readings (development evidence, not confirmatory):**
- Removing order sensitivity (LB-F2) gives the worst validation NLL in every seed, which is consistent with P13's F2 finding.
- The generic-only coupling arm gives the lowest validation NLL in every seed. This motivates H-B2 but is **not** a test result.
- Several best checkpoints fall at the final evaluation (update 400), so longer training might help every arm equally. It was matched, not tuned.

## 5. Calibration (calibration split only; `runs/p16/b/POLICIES.json`)

The no-op-first thresholds were fitted on the 30 calibration roots with a decided original. Calibration-split correct decisions:

| arm | t0 (no-op) | t (repair) | calib correct |
|---|---|---|---|
| LB | 0.87 | 0.56 | 0.667 |
| LB-F2 | 0.87 | 0.23 | 0.633 |
| LC | 0.87 | 0.35 | 0.700 |
| LB+G | 0.76 | 0.74 | 0.700 |
| A | 0.88 | 0.38 | 0.667 |
| P13:K-B | 0.87 | 0.77 | 0.633 |
| P13:A | 0.83 | 0.08 | 0.700 |
| P13:SF | 0.82 | 0.17 | 0.633 |
| P13:K-C | 0.90 | 0.62 | 0.700 |
| P13:B-F2 | 0.83 | 0.62 | 0.600 |

Every learned arm, frozen or new, is given the same calibrated no-op-first rule. Comparisons therefore isolate the scorer, not the decision rule.

## 6. B gate (`runs/p16/P16_B_GATE.json`)

- **Passed:**
  - exact maths and inference;
  - no-op, ABSTAIN and UNKNOWN distinct;
  - scene-only candidate generation;
  - a frozen calibration-split policy;
  - matched 3-seed training of every new arm.
- **Prospective physical evidence:** see 0088.
