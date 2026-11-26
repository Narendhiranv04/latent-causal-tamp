# R3.3 — Conditional relational X model (3D)

**Contract:** `../R3_PREREG.json` R3_3 and `../R3_PREREG_ADDENDUM_A1.json`. **Code:** `../xrel.py`.

**What is fixed:**
- the Y path, which is F0 bitwise (`ScalingNet`, max |Δb| = 0 on every panel);
- the X/Y factorization, P(X | Y = y) = σ(a + w·y);
- the cVAE;
- the data, replay mixture, seeds, early-stopping criterion and gate.

**Node features.** Learner-visible only:
- position, attributes, and relations to base, goal and target;
- role flags: mover, destination, target;
- query-relative geometry: [dx, dy, |d|] to the mover and to its destination.

The destination is an extra node. The scene is the ideal within-chunk prefix. No labels, witnesses, K, teacher traces or future prefix enter any input.

**Models**
- **G1:** two query-conditioned relational-attention layers. Edge features are [dx, dy, |d|, attribute difference].
- **M1:** the capacity-matched control. It has the identical node features, including the query-relative geometry, but a per-node MLP and no message passing. It separates graph structure from the geometric information.
- **Size:** G1 503,556 trainable parameters; M1 499,714.

**Tests** (`tests/test_r3.py`, 7 pass):
- object-index permutation invariance;
- order sensitivity, i.e. the same endpoint in a different order gives a different a;
- Y bitwise equal to F0;
- the frozen base has no gradient.

## Optimizer validity (addendum A1)

The first G1 and M1 runs used the F1 fine-tuning optimizer (lr 1e-4, patience 8) from random initialisation. They under-fit: replay train NLL ≈ 3.4 vs ≈ 2.2 for F0-initialised arms, and VAL NLL 0.64 vs chance 0.69. They are therefore not a representation test. Their VAL_SCALE h ≥ 1 AUROC was 0.71 / 0.68 and natural p11 0.82, both worse than F0. They are reported and not used.

Addendum A1 was sealed and pushed in `b3db8afc37` before any further training. It applies the optimizer that trained F0's X from scratch (lr 1e-3, ≤ 60 epochs, patience 10) identically to G1s and M1s.

## Local gate (VAL_SCALE)

| | F0 | G1s s0 | G1s s1 | M1s s0 | M1s s1 |
|---|---|---|---|---|---|
| best epoch, VAL NLL | –, 0.781 | 19, 0.348 | 8, 0.354 | 29, 0.370 | 20, 0.354 |
| h = 0 AUROC | 0.866 | 0.931 [0.87, 0.98] | 0.926 | 0.918 | 0.925 |
| h ≥ 1 AUROC | 0.826 [0.73, 0.91] | **0.948 [0.88, 0.99]** | 0.901 [0.84, 0.96] | 0.912 [0.85, 0.97] | 0.933 [0.88, 0.98] |
| h ≥ 1, m = 2–3 | 0.811 | 0.926 | 0.872 | 0.856 | 0.893 |
| paired ΔAUROC h ≥ 1 vs F0 | – | **+0.123 [0.057, 0.198]** | +0.076 [0.014, 0.147] | +0.087 [0.013, 0.164] | +0.107 [0.036, 0.184] |
| first-relocation FPR at TPR 0.80 | 0.217 (10/46) | **0.087 (4/46)** | 0.109 | 0.174 | 0.109 |
| FPR drop (gate ≥ 0.15) | – | **0.130** | 0.109 | 0.043 | 0.109 |
| FPR / TPR at 0.5 | 0.80 / 0.99 | 0.22 / 0.94 | 0.20 / 0.90 | 0.22 / 0.89 | 0.17 / 0.88 |
| ECE (all) | 0.219 | 0.042 | 0.063 | 0.059 | 0.046 |
| NATURAL_VAL p11 AUROC (paired vs F0) | 0.896 | 0.889 [−0.025, +0.012] | 0.879 | 0.893 | 0.879 |
| NATURAL_VAL marginal pX AUROC | 0.882 | 0.882 | 0.857 | 0.880 | 0.858 |
| **gate** | – | **FAIL (FPR only)** | FAIL | FAIL | FAIL |

**Selected candidate.** The pre-registered seed rule (lower VAL NLL) picks **G1s seed 0**, which passes:
- support (23 / 10 mixed families);
- h ≥ 1 ≥ 0.75 with lower CI 0.88 ≥ 0.60;
- a paired gain with CI above 0;
- no K ≤ 3 loss beyond 0.05;
- identical Y.

It misses the pre-registered first-relocation FPR drop (≥ 0.15 at each model's own TPR-0.80 threshold) by one negative: 4/46 against F0's 10/46, where the target needs ≤ 3/46. The pre-registration counts this component in PASS, so **the gate is not passed and is not re-interpreted after the fact**.

**Graph vs control (VAL_SCALE, paired family bootstrap).**

| Pair | h ≥ 1 | h0 |
|---|---|---|
| G1s s0 − M1s s0 | +0.036 [−0.018, 0.091] | +0.012 [−0.032, 0.051] |
| G1s s1 − M1s s1 | −0.032 [−0.069, 0.000] | – |

Graph structure is not separable from the query-relative geometric features on this panel. Most of the gain over F0 comes from the X head that sees query-relative geometry, trained on the new local labels.

There is no ablation of F0's own architecture trained from scratch at lr 1e-3. Optimizer and feature effects are therefore not fully disentangled; F2 at 3e-5 gained only +0.035.

## Diagnostic only: R2.4 exposed K4/K5 panel

465 exact labels on 20 roots. This panel was never used for training, early stopping or selection (`eval/hard_3d.json`).

| | F0 | F1 s0 | F2 s0 | M1s s0 | G1s s0 | G1s s1 |
|---|---|---|---|---|---|---|
| all | 0.656 | 0.682 | 0.685 | 0.814 | **0.849 [0.81, 0.89]** | 0.819 |
| h0, m1 (first relocations) | 0.642 | 0.718 | 0.733 | 0.904 | **0.930 [0.88, 0.97]** | 0.904 |
| h ≥ 1 | 0.522 [0.45, 0.59] | 0.525 | 0.534 | 0.702 | **0.757 [0.69, 0.84]** | 0.733 |
| h ≥ 1, m = 2–3 | 0.166 | 0.334 | 0.332 | 0.510 | 0.594 | 0.582 |
| FPR at TPR 0.8, first relocations | 0.80 | 0.54 | 0.54 | 0.13 | **0.09** | 0.15 |

On the regime where R2.4 failed, the new X head removes most confident first-relocation false positives, which were 15 of the 18 R2.4 failures. h ≥ 1 rises from 0.52 to 0.76. Multi-action intermediate chunks stay weak (0.59).

These are exposed development roots, so this is descriptive and not confirmation.

## Outcome

Per the pre-registration, **no candidate passes the local gate**: R3.2 → F2 → R3.3 (G1, M1; G1s, M1s under A1). Support is adequate, so this is not DATA_LIMITED. The precise failed stratum is **VAL_SCALE first-relocation FPR at TPR 0.80**: best drop 0.130, gate 0.150. Every other component passes for G1s s0.

R3.4 requires a passed local gate, so it is **not started**. Selected-but-not-passed checkpoint: `fig3/r3/ckpt/3d_G1s_s0/model.pt`, sha16 recorded in `curve.json`. Training stays at ≈ 0.07 GPU-h for all arms.

Reproduce:
```
$PYG train.py fit 3d {G1,M1,G1s,M1s} {0,1}
$PYG evaluate.py gate 3d G1s 0 G1s 1 M1s 0 M1s 1
$PYG evaluate.py hard 3d F1 0 F2 0 G1s 0 G1s 1 M1s 0 M1s 1
```

Figure: `figures/R3_2_3_training.png`:
- (a) VAL_SCALE gate strata;
- (b) first-relocation ROC with the FPR at TPR 0.8;
- (c) early-stopping curves, including the under-fit lr-1e-4 G1;
- (d) the diagnostic exposed panel.
