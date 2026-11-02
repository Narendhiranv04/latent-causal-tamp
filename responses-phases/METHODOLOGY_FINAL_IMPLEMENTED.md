# Approach B (X/Y): final implemented methodology and confirmatory evaluation (2D)

This is the manuscript-ready description of what was implemented and tested. It **does not modify** the 31 October 2026 specification
(`Approach_B_Final_Methodology_2026-10-31.pdf`), which stays the frozen historical reference. The P16–P22 changes are recorded in the preserved
addendum [0129A](0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md) and are cited here, not rewritten. The final evidence is in
[0131](0131_BXY_P24_ONE_SHOT_CONFIRMATION.md) and [0132](0132_BXY_P25_FINAL_METHOD_AND_FINDINGS.md).

## 1. Problem

A planar robot must perform a target pick-and-place that is blocked in the given scene. The task is to choose, from a finite catalogue of
proposed **ordered relocations** of movable objects, one that makes the target executable. The catalogue is generated analytically.

- **Robot:** a finite-width 3R arm with side grasps (24 approach directions × 2 elbows).
- **Scene:** an 8 × 8 resting lattice, continuous joint motion, and fixed per-query planning budgets.
- **Model role:** the learned model **ranks** the candidates. It does not generate motions.

## 2. Teacher semantics (labels; original)

For a candidate r = (a1, …, am), with a_t = (object, destination) and m ≤ 6:

- **X_r = 1** iff the teacher executes a1 … am **in order** from the start configuration q0, carrying the achieved joint state forward
  (**no reset between relocations**), and then connects to the fixed reference configuration **q_ref** with the gripper free.
- **Y_r = 1** iff the original target task succeeds **from q_ref** in the edited scene, independent of X. Orders that reach the same final
  scene share one Y node.
- **success(r) = X_r · Y_r.** The no-op succeeds iff Y0 = 1.
- **Negative labels.** A failure under the fixed budget is an operational 0. Its kind is kept evaluator-side: CERTIFIED (a sound analytic
  certificate) vs NO_PLAN_FOUND or TIMEOUT. Censored and unattempted queries are absent, never imputed.

## 3. Scorer (original F1–F5, with the P17 extensions GEO2 and SYM)

| Factor | Role |
|---|---|
| F1 | analytic admissibility screen (never learned) |
| F2 | X unary a_r for the ordered prefix; predecessor-aware, so order matters |
| F3 | Y unary b_s for the edited scene |
| F4 | omissions, scored through the same F2 / F3 |
| F5 | optional coupling w_r; the uncoupled variant E fixes w = 0 |

**Root-consistent probabilities:**
- P(Y = 1) = σ(b_s);
- P(X = 1 | Y = y) = σ(a_r + w_r y);
- p_succ(r) = σ(b_s) σ(a_r + w_r);
- p_succ(no-op) = P(Y0 = 1).

**Likelihood.** The joint likelihood factorizes over unique Y nodes, and unobserved queries are marginalized exactly.

**Extensions** (marked *extension* in 0129A):
- **GEO2:** label-free analytic access features (clearances and open pick/place mode counts) for the edited scene (φ_Y) and per action
  (φ_X). They share geometry with the scene generator.
- **SYM:** a symmetric within-root edit contrast.

**Objective:**

L = L_joint + λ_J L_J + κ L_SYM, with λ_J = κ = 1.

- L_J is a Huber loss on log(1 + J) over complete replayed witnesses.
- The 31 October objective had no SYM term.

**Selection rule:**
1. Apply F1.
2. If P(Y0) ≥ the no-op gate, choose the no-op.
3. Otherwise choose argmin over candidates of −log p_succ + α m + γ Ĵ (β = η = 0). Ties break by (m, displacement, signature).

**Frozen rules per arm:**

| Arm | No-op gate | α | γ |
|---|---|---|---|
| D | 0.7 | 0 | 0.05 |
| E | 0.7 | 0 | 0.05 |
| DIRECT-GEO | 0.5 | 0.3 | 0 |
| G | none | 0 | 0.05 |

These were selected on development early-stop roots only, with at most 0.10 inner unnecessary repairs, recorded as a pooled rule at freeze (P23).

**Arms compared** (matched capacity):

| Arm | Description |
|---|---|
| **D** XYQ-GEO-SYM | full X/Y with quadratic coupling |
| **E** XY-UNC-SA-GEO-SYM | X/Y, w = 0 |
| **DIRECT-GEO** | one success head on the same inputs, no X/Y split |
| **G** XYQ-GEO-SYM-ORDINV | D with an order-invariant F2 |

Each arm is a 15-member ensemble (mean of p, Ĵ, px, py). It was trained in P21 on 398 development roots and then frozen.

## 4. Difficulty and necessity

| Term | Meaning | Evidence status |
|---|---|---|
| K_intent | the generator's request | never evidence |
| K_cert | every set of K − 1 movable discs, when removed, leaves the target's declared pick or place modes **certified closed** | sound necessity bound |
| Verified K | the fewest moves of a teacher-verified candidate, with every shorter catalogue candidate decided | — |
| Certified-necessary K | K_cert = verified K | — |

## 5. Confirmatory protocol (P23 lock → P24 one-shot)

**Custody.** The 60 frozen checkpoints were hash-manifested and uploaded to independent storage (Google Drive). They were downloaded and verified
byte for byte (126/126 files), re-loaded, and checked prediction for prediction (max |Δ| = 0).

**Authorization.** Explicit user approval was required, with these limits:
- 90,000 CPU-s, including a 3,000 CPU-s evaluation reserve;
- 40,000 s wall time;
- 4 single-thread workers;
- 1,400 CPU-s per root;
- unchanged per-query teacher budgets.

**Cohort.** Exactly 440 predeclared construction slots of the K34 doorway generator, with new seeds in the namespace `bxyg34confirm`:

| Family, K_intent | Slots |
|---|---|
| local_mixed, K2 | 22 |
| local_mixed, K3 | 66 |
| local_mixed, K4 | 198 |
| local_pick, K3 | 44 |
| local_pick, K4 | 44 |
| v21b_near_closed, K0 | 66 |

Every rejection is kept and none is replaced.

**Order of operations:**
1. Generate the cohort.
2. Freeze the catalogues and label-free inputs.
3. Run all ensembles once.
4. **Seal the predictions** (hashes in an append-only, hash-chained ledger) and commit them.
5. Collect teacher labels with one exclusive supervisor, write-once rows and conservative CPU charging.
6. Run **one** locked evaluation.

**Endpoints:**
- **U**, the single authoritative endpoint: verified success over all initially infeasible roots.
- **C**: success over roots with any verified repair; a consistency requirement.
- **REP34**: success on verified K3/K4 roots; secondary.
- **Unnecessary repairs** on initially feasible roots: a guardrail, failing if the increase exceeds 0.05.
- **Success-gain gate:** +0.10.

**Statistics:**
- Paired root-family bootstrap, B = 10,000.
- Holm adjustment within three families:
  - primary: D − DIRECT, E − DIRECT, D − E;
  - secondary K34;
  - order: D − G and E − G strict order, and D − G REP34 success.
- Labels: IMPROVES, POSITIVE_BELOW_THRESHOLD, GUARDRAIL_FAILED, REVERSED, NOT_ESTABLISHED.

## 6. Result (P24, one look)

**Cohort:** 237 / 440 accepted. Populations: INF 193, AVAIL 75, REP34 52, FEA 44.

**U:**

| Arm | U |
|---|---|
| D | 0.259 |
| E | 0.269 |
| DIRECT-GEO | 0.218 |
| G | 0.212 |

**Primary contrasts.** All three are **not established**:
- D − DIRECT +0.041 (Holm CI [−0.005, 0.088]);
- E − DIRECT +0.052 (Holm CI [0.000, 0.104]);
- D − E −0.010.

**Order.** The order-aware F2 is **confirmed**: D − G REP34 success +0.173 (Holm CI [0.058, 0.308]).

**False repairs.** D/E repair 10/44 feasible scenes, against 2/44 for DIRECT. All of those edits are neutral.

**K3/K4 physics.** 31 K3 and 21 K4 roots are physically witnessed and certified necessary.

## 7. Scope and limitations

- **One 2D generator family.** The test uses new seeds only, so there is no claim of cross-generator or 3D generalization.
- **Shortcut risk in GEO2.** GEO2 shares geometry with the generator. DIRECT receives the same features, and on its own it matches the analytic
  access rule.
- **Planner-bound labels.** Budget-bounded planner failures are operational, not proofs of impossibility, unless certified.
- **Small feasible-scene control.** n = 44, so the absence of harmful edits is not a safety proof.
- **F5 coupling is unsupported.** If the X/Y architecture is used, the uncoupled E is preferred.
