# FIG3_KGT3 P2 — frozen evaluation, bounded training and the fresh local gate

**Contract:** `../FIG3_KGT3_PREREG.json` P2 (models, selection_on_SELECT, training, gate). **Code:** `../learn.py`.

Every decision was written by `guard.decide` and bound to complete manifests, labels, code and checkpoint hashes (`p2/gate_{2d,3d}.json`). VAL_GATE was opened **once**, in 3D only, for the single selected model. 2D GATE was never read by a model.

## Decisions

| Domain | Fresh gate | Reason |
|---|---|---|
| **2D** | **DATA_LIMITED** | GATE has 6 discordant permutation families (< 10) after the pre-registered expansion exhausted every eligible family. The 2D teacher returned UNKNOWN on 62 % of runs. No model was evaluated on GATE and no 2D training was run. |
| **3D** | **DATA_LIMITED** | GATE has 9 mixed h ≥ 1 multi-action families (< 10) after the exhausted expansion. Descriptively, the selected model would also **fail** the AUROC and paired-gain criteria (below). |

Neither domain proceeds to P3 or P5. Historical gates are untouched.

## 2D

**Frozen F0** (descriptive; it never reads GATE):

| Split | Discordant families | Concordance | h ≥ 1, g = 2–3 AUROC | h0 AUROC |
|---|---|---|---|---|
| TRAIN | 5 | **0.15** [0.00, 0.45] (prefers the failing order) | 0.59 | 0.75 |
| SELECT | 0 (concordance undefined) | – | 0.94 (1 mixed family) | 0.83 |

With 5 TRAIN discordant families, bounded 2D training would have no matched-order supervision to speak of. The domain stopped on support anyway, so the 2D MLP challenger was never triggered.

## 3D

**Frozen models on VAL_SELECT** (13 discordant families, 4 mixed h ≥ 1 multi-action families):

| Model | h ≥ 1, g = 2–3 AUROC | Concordance [95 % CI] | h0 AUROC | Family NLL | Qualifies (AUROC ≥ 0.75 and concordance ≥ 0.70) |
|---|---|---|---|---|---|
| F0 | 0.46 | 0.39 [0.15, 0.61] | 0.81 | 0.478 | no |
| M1s s0 | 0.97 | 0.50 [0.20, 0.75] | 0.85 | 0.423 | no |
| G1s s0 | 0.86 | 0.63 [0.33, 0.90] | 0.88 | 0.412 | no |

No frozen model qualifies, so **bounded training was triggered**.

**Stage A training.** M1 is initialized from M1s s0 (X head only; 499,714 trainable parameters). Settings: lr 1e-4, ≤ 40 epochs, patience 8, AdamW wd 1e-4, clip 10. Each batch has 32 replay roots and 32 TRAIN views (304 views: P2 TRAIN plus R3.1 TRAIN_SCALE). Y stayed bitwise identical (asserted) and K ≤ 3 p11 was unchanged. Total GPU time was about 40 s.

| Run | Best epoch | SELECT family NLL | SELECT h ≥ 1, g = 2–3 AUROC | SELECT concordance | Qualifies |
|---|---|---|---|---|---|
| O1 s0 | 6 | 0.381 | 0.88 | 0.66 | no |
| O1 s1 | 0 | 0.374 | 0.91 | 0.61 | no |
| **O2 s0** | 3 | 0.385 | 0.91 | **0.70** | **yes** |
| O2 s1 | 0 | 0.373 | 0.92 | 0.63 | no |

**Selection** (pre-registered):
1. O2 is chosen over O1 because its mean SELECT concordance (0.663) exceeds O1's (0.635).
2. The rule also requires the selected run to qualify. Only O2 s0 does, so it is selected, although O2 s1 has the lower NLL.
3. This resolves an ambiguity in the rule wording (disclosed). Stage B (G1 fine-tune) was not run because a stage-A run qualified.
4. The qualifying margin is thin: 0.702 against 0.70, on 13 families.

**Gate opened once with `M1ft_O2_s0`:**

| Criterion | Result | Pass |
|---|---|---|
| Support: mixed h ≥ 1, g = 2–3 / discordant / mixed h0 (≥ 10 each) | **9** / 22 / 22 | **no → DATA_LIMITED** |
| h ≥ 1, g = 2–3 AUROC ≥ 0.75, lower CI ≥ 0.60 | 0.634 [0.45, 0.79] | no |
| Concordance ≥ 0.70, lower CI > 0.50 | 0.733 [0.57, 0.88] (22 families, 51 groups, 63 pairs) | yes |
| Paired h ≥ 1, g = 2–3 gain over F0, CI > 0 | +0.045 [−0.16, 0.22] (14 families) | no |
| K ≤ 3 p11 AUROC drop ≤ 0.05, Y identical | 0.896 → 0.896; max \|Δb\| = 0 | yes |
| First-relocation FPR not worse than F0 by > 0.05 | not estimable: no single-action h0 negatives in GATE | – |

**All arms on 3D GATE (descriptive only, 22 families):**

| Model | h ≥ 1, g = 2–3 AUROC [95 % CI] | Concordance [95 % CI] | h0 AUROC | Family NLL | ECE |
|---|---|---|---|---|---|
| F0 | 0.59 [0.38, 0.80] | 0.62 [0.46, 0.78] | 0.70 | 0.75 | 0.19 |
| M1s s0 | 0.59 [0.39, 0.78] | 0.72 [0.55, 0.87] | 0.74 | 0.70 | 0.21 |
| G1s s0 | **0.69** [0.52, 0.84] | **0.77** [0.61, 0.91] | 0.79 | 0.65 | 0.23 |
| M1ft O1 s0 / s1 | 0.58 / 0.62 | 0.75 / 0.71 | 0.76 / 0.75 | 0.61 / 0.61 | 0.13 / 0.10 |
| M1ft O2 s0 (selected) / s1 | 0.63 / 0.62 | 0.73 / 0.72 | 0.75 / 0.75 | 0.62 / 0.61 | 0.13 / 0.12 |

**Interpretation (development evidence, small panels)**
- **Order preference.** The query-relative 3D heads, especially G1s, prefer the enabler-first order in most discordant pairs (concordance 0.72–0.77 vs F0 0.62).
- **Multi-action ranking.** No model ranks multi-action chunks at reached intermediate states well across families: AUROC is 0.58–0.69 for every arm.
- **What training changes.** Targeted training improves likelihood and calibration (NLL 0.70 → 0.61; ECE 0.21 → 0.10–0.13). It does not improve multi-action AUROC or concordance over G1s.
- **O2.** The ranking loss O2 shows no established benefit over O1. This is not evidence for or against ranking-loss necessity, nor for or against a GNN: G1s vs M1s is unmatched here.
- **What would be needed.** More reached intermediate states (h ≥ 1, h ≥ 2, g = 3), and in 2D a teacher that can decide feasible orders in dense scenes.

## Resources (P2)

| | Used | Cap |
|---|---|---|
| 2D | 1,032 queries / 7.8 CPU-h | 1,200 / 20 |
| 3D | 515 probes + 525 runs = 1,040 queries / 3.5 CPU-h | 1,200 / 20 |
| GPU training (3D) | about 0.02 GPU-h | 6 |
| GPU evaluation and inference (both domains) | about 0.2 GPU-h | – |

There were no errors, no censored runs and no retries. At most 16 workers ran at once.
