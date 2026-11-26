# R3.2 — Existing X/Y architecture, controlled fine-tuning (3D)

**Contract:** `../R3_PREREG.json` R3_2. **Code:** `../train.py`, `../evaluate.py`.

**Data**
- **REPLAY:** 1,722 original v32 TRAIN roots, minus the 44 DEV-lineage rows.
- **TRAIN_SCALE:** 197 start-scene views, 548 labels.
- **VAL_SCALE:** 86 views, 244 labels on 26 families.

**Setup**
- **Steps:** each step mixes 32 replay roots and 32 family-balanced TRAIN_SCALE views.
- **Loss:** the unchanged exact observed-data likelihood. Local labels are lone X observations, so the loss reduces to the marginal Bernoulli on pX, with permutations sharing the endpoint Y node.
- **Seeds:** 0 and 1. There was no hyperparameter sweep.
- **Early stopping:** on the VAL_SCALE family-mean X NLL.

## Arms

| Arm | Trainable | lr | Seed 0 best epoch, VAL NLL | Seed 1 best epoch, VAL NLL | GPU seconds |
|---|---|---|---|---|---|
| F0 (frozen) | – | – | 0.781 | – | – |
| F1 | `act`, `pairo`, `mix`, `order_s`, `xy` (247k of 467k) | 1e-4 | 3, 0.451 | 3, 0.455 | 6 + 8 |
| F2 | all 467k | 3e-5 | 12, 0.443 | 20, 0.443 | 17 + 21 |

## Local gate (VAL_SCALE, marginal pX, family-cluster 95 % CI)

Support was adequate: 23 mixed families at h0 and 10 at h ≥ 1.

| | F0 | F1 s0 | F1 s1 | F2 s0 | F2 s1 |
|---|---|---|---|---|---|
| h = 0 AUROC | 0.866 | 0.882 | 0.883 | 0.888 | 0.887 |
| h ≥ 1 AUROC | 0.826 [0.73, 0.91] | 0.856 [0.75, 0.94] | 0.849 | 0.861 [0.76, 0.95] | 0.866 |
| h ≥ 1, m = 2–3 | 0.811 | 0.840 | 0.831 | 0.848 | 0.852 |
| paired ΔAUROC h ≥ 1 vs F0 | – | +0.031 [−0.018, 0.083] | +0.023 [−0.027, 0.071] | +0.035 [−0.014, 0.088] | +0.041 [−0.010, 0.097] |
| first-relocation FPR at TPR 0.8 (drop needed ≥ 0.15) | 0.217 | 0.283 (−0.07) | 0.283 | 0.217 (0.00) | 0.239 |
| ECE (all) | 0.219 | 0.080 | 0.083 | 0.090 | 0.054 |
| **gate** | – | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

- **K ≤ 3 regression (NATURAL_VAL, 776 labels).**
  - F1: Y is bitwise identical (max |Δb| = 0); p11 AUROC is 0.900 vs 0.896 (paired CI [−0.002, 0.010]).
  - F2: Y drifts (max |Δb| 3.05) but Y AUROC only falls 0.9723 → 0.9699, inside the 0.02 rule; p11 AUROC is 0.900.
- **Interpretation.** Neither fine-tune changes the ranking materially. Both mostly recalibrate: ECE falls from 0.22 to 0.05–0.09. Monotone recalibration cannot fix ranking, and these arms barely change it.
- **The deficit does not reproduce here.** F0 already meets the absolute h ≥ 1 threshold on the new family-independent VAL_SCALE panel (0.826). The R2.4 failure regime (F0 h ≥ 1 0.52 on the exposed K4/K5 roots) is therefore specific to those dense, enabler-constructed layouts, not to h ≥ 1 in general.
- **Exposed panel (diagnostic only).** F1 and F2 lift R2.4 first relocations from 0.64 to 0.72–0.73 but leave h ≥ 1 at 0.52–0.53 (`eval/hard_3d.json`).

**Outcome (pre-registered):** F1 FAIL and F2 FAIL on adequate data → **R3.3**.

Reproduce (gvlab2, `source fig3/env.sh; cd $CODE/fig3_retarget/r3`):
```
$PYG train.py fit 3d F1 {0,1}
$PYG train.py fit 3d F2 {0,1}
$PYG evaluate.py gate 3d F1 0 F1 1
$PYG evaluate.py gate 3d F2 0 F2 1 G1 0 M1 0
$PYG evaluate.py hard 3d F1 0 F2 0 ...
```
