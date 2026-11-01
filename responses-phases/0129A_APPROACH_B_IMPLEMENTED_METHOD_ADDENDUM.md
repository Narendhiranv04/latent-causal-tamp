# Approach B — implemented-method addendum (P16 → P22), companion to the 31 October 2026 methodology

This addendum **does not replace** `Approach_B_Final_Methodology_2026-10-31.pdf`; that document remains the historical, frozen specification.
It records exactly what is implemented and measured at the end of P22. Each item is marked as one of:
- **original**: unchanged from 31 October;
- **extension**: added later and evaluated as such;
- **protocol**: an evaluation or construction rule.

## 1. Unchanged scientific question and physical protocol (original)

- **Setting.** A finite catalogue of proposed ordered relocations r = (a1 … am), m ≤ 6, a_t = (object, legal destination). A planar
  finite-width 3R arm with side grasps (24 approach directions × 2 elbows), an 8 × 8 resting-placement lattice and continuous joint motion.
- **X_q = 1** iff the teacher executes every relocation of the prefix in order:
  - from q0, carrying the achieved joint state with no reset;
  - **then connects to q_ref** in the edited scene, gripper free, nothing attached.
- **Y_s = 1** iff the original target task succeeds from the fixed q_ref in the hypothetical edited scene, whatever X is.
- **Shared Y.** Orders with one endpoint share one Y and keep distinct X. X_empty = 1, and the no-op succeeds iff Y0 = 1.
- **Labels.**
  - An attempted fixed-budget failure is operational 0, with negative kind (CERTIFIED vs NO_PLAN_FOUND / TIMEOUT) and failed phase kept
    evaluator-side.
  - Censored or unattempted queries are absent.
- **Teacher:** BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1 with fixed per-query budgets `bd_2d.QB`, unchanged since P-min.

## 2. Model (original F1–F5 and normalization)

- **F1:** an analytic screen.
- **F2:** a predecessor-aware ordered-prefix X unary a_q.
- **F3:** a hypothetical-scene Y unary b_s.
- **F4:** omissions recomputed through the same F2 / F3.
- **F5:** one optional quadratic coefficient w_q.
- **Root-consistent probabilities:**
  - P(Y_s = 1) = σ(b_s);
  - P(X_q = 1 | Y_s = y) = σ(a_q + w_q y);
  - p_succ(q) = σ(b_s) σ(a_q + w_q);
  - p_succ(no-op) = P(Y0 = 1).
- **Likelihood.** The joint factorizes over unique Y nodes, and unobserved queries are marginalized exactly.

## 3. Implemented extensions (P17; carried unchanged into P21)

- **GEO2** — analytic, label-free access features from the scorer's own tensors plus pre-computed grasp / place access maps:
  - φ_Y: 8 clearances, the open target pick / place mode counts and flags, and goal occupancy, all of the edited scene;
  - φ_X: per-action open pick / place modes in the ideal predecessor scene, or in S0 for the order-invariant control.
  - **They share geometry with the construction generators** (a shortcut risk; DIRECT receives them too).
- **SYM** — a symmetric within-root edit contrast: (0 → 1) softplus(−(b_s − b_0)), (1 → 0) softplus(b_s − b_0), concordant
  softplus(|b_s − b_0| − 1), balanced within the root, plus the P14 edited-pair contrast; κ = 1.
- **Objective:** L_D = L_joint + λ_J L_J + κ L_SYM, with λ_J = 1 and L_J a Huber loss on log(1 + J) over complete replayed witnesses
  only. **The October 31 objective had no SYM term.**
- **Selection.** F1 first, then cost −log p_succ + α m + β C_d + γ Ĵ (β = η = 0, γ = 0.05 for travel-trained arms). The no-op gate and α
  are chosen per fold on early-stop roots only, subject to ≤ 0.10 inner unnecessary repairs.
- **Arms** — matched capacity except B:

| Arm | Model |
|---|---|
| A | DIRECT-GEO |
| B | XYQ-BASE |
| C | XYQ-GEO-CON |
| D | XYQ-GEO-SYM |
| E | XY-UNC-SA-GEO-SYM (w = 0 control) |
| G | XYQ-GEO-SYM-ORDINV (order-invariant F2 control) |

## 4. Difficulty definitions (protocol, P19 / P20)

| Name | Meaning | Evidence status |
|---|---|---|
| K_intent | construction request | never evidence |
| K_LB | exact order-free minimum over finite declared pick × place modes of movable discs to remove (union model) | analytic bound under the union model |
| **K_cert** | for every set of K−1 movable discs, the real screen with them removed is **certified closed** for the target pick or place | **sound necessity bound** within the declared grasp family (removals only open, additions only close) |
| K_catalogue | fewest moves of a verified complete candidate (replayed X + connector, Y), every shorter catalogue candidate decided | catalogue-relative |
| verified-necessary K | K_cert = K_catalogue | physically witnessed **and** certified necessary |

## 5. Construction families (development)

| Family | Version | Description |
|---|---|---|
| V2 | P15 | one nominal target sweep (easy; 21 / 28 roots K0) |
| V2.1 | P16 | analytic access closure; K_geom was later shown to overstate necessity (P19) |
| **K34** | P20 | **doorway closure**: walls outside the doorway, k blockers in the intersection of the doorway modes' kill sets; K_cert = K required; validated short-carry intended relocations; teacher's analytic certificates per step (K34B); arm-reliable rows (K34C) |

## 6. Evidence summary (development only; no independent confirmation has been run)

| Verified K (independent roots) | V21 | K34 | certified necessary |
|---|---|---|---|
| K2 | 11 | 5 | 10 |
| K3 | 2 | 14 | 14 (all K34) |
| K4 | 0 | **7** | **7** |

- **K4 verdict:** physically verified as a phenomenon in 7 roots, but below the frozen 10-root threshold for stratum inference
  (`K4_PHYSICAL_DATA_NOT_ESTABLISHED`).
- **Binding limitation:** relocation planning under the fixed per-query budget. Closing every declared mode of the 3R arm needs discs
  along its link paths, which also obstruct relocations.
- **Learning results (P21, 398 development roots, out of fold):**

| Arm | Success (outcome-blind infeasible) | Success when a verified repair exists | Unnecessary repairs |
|---|---|---|---|
| D | 0.289 | 0.688 | 0.14 |
| E | 0.287 | 0.683 | 0.16 |
| DIRECT-GEO | 0.258 | 0.614 | 0.19 |
| XYQ-BASE | 0.056 | — | — |

  - **D vs XYQ-BASE:** +0.233, which meets the improvement criterion.
  - **D vs DIRECT-GEO:** +0.031 [−0.002, +0.064], **not superior** — P17's development gate does not replicate.
  - **Coupling (D vs E):** +0.002.
  - **Order-aware F2:** concordance +0.32, and +0.22 success on repairable K3/K4 roots (exploratory).
  - **Held-out selection given availability:** K3 0.74 (n = 14, exploratory) and K4 0.95 (n = 7, descriptive).
  - **Deployment preference:** the uncoupled E; the coupling (F5) has never met its benefit criterion.

## 7. What is not claimed

- No causal edge from w.
- No global impossibility from budget failures.
- No K4 learning claim from n = 7.
- No generalization beyond the development construction families.
- No independent-test performance.
