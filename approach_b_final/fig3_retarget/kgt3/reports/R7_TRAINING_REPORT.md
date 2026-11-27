# R7: clean training and representation controls

All components were trained from fresh initialisation on Blackwell, with seeds 0, 1 and 2. Nothing was inherited from development checkpoints. The training data came from TEST-free copies of the original snapshots. Raw records are in `reports/final/r7/`.

| Stage | What | Result |
|---|---|---|
| A | Q2 placement pretraining (`placement.fit cvae`), then task-conditioned cVAE `q2init_all` initialised from it. Expanded TRAIN snapshot, base-snapshot VAL ELBO, frozen production step budget | VAL ELBO: 3D s0/s1/s2 = 2.027 / **2.005** / 2.028; 2D **2.713** / 2.727 / 2.767 |
| B | Fresh coupled X/Y XYNet arm D (`xy.fit`, original observed-data likelihood and data, frozen D defaults) | 3D s0 VAL NLL 1.363 (each fit ≈ 20 s) |
| C | Stage-B Y frozen (sha asserted, 66/66 fits); fresh X head; lr 1e-3, ≤ 60 epochs, patience 10; family-balanced strict local labels + original replay; no O2 loss | Table below |
| D | Selection by the predefined rules only (R5.2 representation rule, lowest-VAL seed, R5.3 calibration rule, lowest-ELBO cVAE) | See `R7_FREEZE.md` |

**Strict local supervision.** All supervised queries have ≤ 3 actions. Positives are replayed; negatives are certified failing chunks. TRAIN and VAL families are disjoint (asserted).

| Domain | Total labels | TRAIN views | VAL views | Replay roots | VAL families | TRAIN families |
|---|---|---|---|---|---|---|
| 3D | 2,318 | 625 | 90 | 1,722 | 26 | 269 |
| 2D | 3,316 | 887 | 362 | 3,500 | 101 | 136 |

## R7.3: representation × supervision

Values are seed means over 3 seeds, on the local VAL families.

- Representations: A = original ordered X, M = query-relative MLP, G = query-relative GNN.
- Supervision: 0 = original replay only, 1 = replay plus strict local labels.
- Columns: **NLL** = family NLL of marginal pX; **multi** = family NLL on intermediate (h ≥ 1) multi-action chunks; **K≤3** = original-objective root NLL on the K ≤ 3 VAL roots.

| | 3D NLL | AUROC | AUPRC | ECE | concord. | multi | K≤3 | 2D NLL | AUROC | concord. | multi | params |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | .668 ± .009 | .668 | .588 | .131 | .676 | .684 | 1.836 | .488 ± .011 | .752 | .580 | .562 | 247k |
| A1 | .590 ± .014 | .770 | .719 | .085 | .796 | .579 | 1.591 | .424 ± .010 | .828 | .663 | .497 | 247k |
| M0 | .615 ± .008 | .725 | .660 | .131 | .537 | .623 | 1.721 | .472 ± .024 | .774 | .593 | .603 | 500k |
| M1 | .512 ± .077 | .803 | .761 | .048 | .717 | .491 | 1.618 | .330 ± .070 | .915 | .853 | .463 | 500k |
| G0 | .530 ± .101 | .777 | .752 | .083 | .561 | .559 | 1.542 | .364 ± .021 | .865 | .806 | .509 | 504k |
| **G1** | **.224 ± .020** | **.967** | **.962** | **.047** | **.983** | **.267** | **1.388** | **.228 ± .010** | **.981** | **.961** | **.348** | 504k |

**Reading.**
- **Supervision effect (0 → 1):** adding strict local labels improves every representation in both domains. The gain is largest for G (3D −.31, 2D −.14), followed by M (−.10 / −.14) and A (−.08 / −.06).
- **Representation effect at fixed supervision:**
  - With original data only, G0 < M0 < A0 in 2D, and G0 ≈ M0 < A0 in 3D (G0's 3D seed spread is large, ±.10).
  - With local labels, G1 is far ahead in both domains (3D .224 vs M1 .512 and A1 .590).
  - The two effects interact: the GNN gains most from the local labels.
- **K ≤ 3 regression:** G1 also has the lowest original-objective NLL on the K ≤ 3 VAL roots. No degradation was observed.
- **Cost:** G1 takes ≈ 1–2 GPU-min per fit, with 504k trainable X parameters.

**Controls on G1** (VAL family NLL for s0 / s1 / s2; for DIRECT, short-sequence success BCE):

| Control | 3D | 2D |
|---|---|---|
| ORDINV | .460 / .464 / .507 | .293 / .307 / .317 |
| UNCOUPLED | .240 / .230 / .262 | .275 / .199 / .208 |
| DIRECT (BCE) | .407 / .387 / .471 | .472 / .502 / .431 |

- **Order sensitivity matters** in both domains: ORDINV is worse than G1 by about +.24 in 3D and +.08 in 2D.
- **Removing the X/Y coupling** gives a small VAL change. Its physical effect is measured in R8A.

**Resources (R7 + R7b).** About 80 short GPU jobs on Blackwell, below 1.5 GPU process-hours in total (each fit took 7–130 s). The CPU cost was negligible (2 cores per lane).
