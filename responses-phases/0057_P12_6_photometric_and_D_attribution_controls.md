# 0057 — P12-6: realistic appearance controls and D attribution semantics

**Actual result.**
- **Gate:** `runs/p12/P12_6_GATE.json` → **PASS**.
- **Appearance:** under realistic photometric changes, keyed B is far more stable than under P11's severe palette remap. Mean |Δp| is 0.006–0.026, and the TOP1 choice changes on 4–11 % of roots (against 77 % for the severe remap).
- **D:**
  - **P10b infeasible-only:** D 0.863 vs D-pairless 0.873 vs geometry 0.818.
  - **Novel holdout (infeasible-only):** **geometry 0.850 > D 0.752 > D-pairless 0.598**. D − pairless +0.154 is the first positive evidence for the pair term (exploratory).
  - **Matched A / B / C / SF attribution:** UNSUPPORTED on the holdout (3-object pools).

## 1. Photometric robustness (POST-HOC on the 100 disclosed P10 validation / blind roots; `PHOTOMETRIC.json`)

**Recipes** (`p12_closure.PHOTO`, fixed and deterministic, whole image, texture-preserving):

| variant | change |
|---|---|
| G1 | gain 1.12, contrast 0.88 |
| G2 | white balance (1.06, 1.0, 0.92), 30 % desaturation |
| G3 | gain 0.92, contrast 1.08, white balance (0.96, 1.0, 1.05), 15 % desaturation |

Instance masks, object ids, geometry, robot, goal and candidates are identical. DINOv2 features are recomputed. **The robustness shown is conditional on the recorded instance masks:** segmentation and detection are not tested.

| arm | G1 \|Δp\| / TOP1 changed | G2 | G3 | severe remap (P11) |
|---|---|---|---|---|
| keyed B | 0.006 / 0.037 | 0.026 / 0.107 | 0.020 / 0.090 | 0.248 / 0.770 |
| keyed C | 0.007 / 0.017 | 0.030 / 0.070 | 0.021 / 0.087 | 0.227 / 0.668 |
| A | 0.008 / 0.017 | 0.038 / 0.103 | 0.020 / 0.063 | 0.238 / 0.635 |
| SF | 0.006 / 0.013 | 0.035 / 0.117 | 0.022 / 0.073 | 0.213 / 0.488 |
| B-F3 | 0.007 / 0.017 | 0.035 / 0.180 | 0.022 / 0.110 | — |
| B-F5s | 0.007 / 0.043 | 0.048 / 0.247 | 0.022 / 0.110 | — |
| B-V0 (visual-zero) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

- **H1 κ̂ shift for B** (P10 H1 roots): G1 0.001, G2 0.036, G3 0.026, against 0.616 for the severe remap.
- **Visual-zero** is invariant only because it ignores pixels. That is not robustness.

## 2. D semantics (`D_SEMANTICS_p10b.json`, `D_SEMANTICS_holdout.json`)

**Original-task categories:**

| cohort | feasible original | infeasible with a minimal clearing set | no clearing set in pool | unknown / incomplete |
|---|---|---|---|---|
| P10b blind | 4 | 56 | 0 | 5 |
| holdout | 0 (every original is prescreen-obstructed) | 64 | 0 | 16 incomplete |

**Initial feasibility:**
- **P10b** (64 roots, 4 feasible): see 0050. D and D-pairless are perfect.
- **Holdout** (80 roots, 0 feasible): AUROC and balanced accuracy are **NOT_EVALUABLE**. False-feasible counts: B 1, C 1, D 3, D-pairless 3, A 4, SF 7.

**Blocker identity, infeasible originals only** (union-minimal-set ground truth, frozen parking map):

| cohort / stratum | N | D F1 | D-pairless F1 | geometry F1 | D exact | D-pairless exact | geometry exact |
|---|---|---|---|---|---|---|---|
| P10b all | 56 | 0.863 | 0.873 | 0.818 | 0.548 | 0.643 | 0.536 |
| P10b proof-grounded | 35 | 0.924 | 0.876 | **0.952** | 0.810 | 0.781 | 0.857 |
| P10b operational | 21 | 0.761 | **0.869** | 0.595 | 0.111 | 0.413 | 0.000 |
| holdout all | 64 | 0.752 | 0.598 | **0.850** | 0.542 | 0.339 | 0.547 |
| holdout proof-grounded | 58 | 0.757 | 0.592 | **0.855** | 0.546 | 0.339 | 0.569 |
| holdout 1 blocker | 52 | 0.733 | 0.542 | 0.827 | — | — | — |
| holdout 2 blockers | 10 | 0.872 | 0.860 | 0.960 | — | — | — |
| holdout 3 blockers | 2 | 0.650 | 0.767 | 0.900 | — | — | — |

**Paired contrasts (infeasible-only F1):**

| cohort | contrast | difference | 95 % CI | note |
|---|---|---|---|---|
| P10b | D − pairless | −0.011 | [−0.051, 0.039] | pairless better on more roots, p 0.015 |
| P10b | D − geometry | +0.044 | [−0.015, 0.101] | n.s. |
| holdout | D − pairless | **+0.154** | [0.103, 0.209] | D better |
| holdout | D − geometry | −0.098 | [−0.172, −0.026] | geometry better |

**Alternative minimal sets (union ≠ necessary):**
- P10b: 4 roots, 8 union members that are not necessary.
- Holdout: 7 roots, 15 such members.

D predicts the union only; **no necessity claim is made**.

**Strictly matched A / B / C / SF counterfactual attribution:**
- **P10b:** 33 matched infeasible roots (23 unsupported). A and SF predicted no sufficient clearing set on 7 and 2 choices respectively; these are reported as **NO_PREDICTED_CLEARING_SET**, not scored as empty.

  | arm (33 roots) | F1 |
  |---|---|
  | D | 0.939 |
  | geometry | 0.929 |
  | D-pairless | 0.919 |
  | C | 0.882 |
  | B | 0.872 |
  | SF (scored roots) | 0.855 |
  | A (scored roots) | 0.842 |

- **Holdout:** **0 matched**, 64 unsupported. Every pool has 3 objects, so its subsets exceed the A / B / A+B edit catalogue.

**Correction to P11 (0050):** P11's "D best on proof-grounded masks" included the 4 trivial feasible roots. On infeasible originals only, the geometry heuristic is best on proof-grounded masks, on P10b as well as on the holdout.

**Figures:** `visualizations/p12/P12_appearance.png`, `visualizations/p12/P12_D_blockers.png`.
