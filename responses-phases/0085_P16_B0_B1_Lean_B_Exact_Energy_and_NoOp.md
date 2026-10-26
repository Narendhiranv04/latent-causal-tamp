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
