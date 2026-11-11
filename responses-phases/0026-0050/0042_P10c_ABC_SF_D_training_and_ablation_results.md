# 0042 — P10c: matched A / B / C / SF training, length-restricted copies, retrained factor ablations, and D

**Actual result.**
- **Runs:** **69 / 69** preregistered runs completed with finite losses (3 seeds each). True training compute was **17,258 CPU-s** (sum of the runs' own `train_cpu_s`).
  - A, B, C, SF in the full regime (1–4-move data);
  - A, B, C, SF in the short regime (≤ 2-move data);
  - 7 retrained B ablations;
  - D and D-pairless (λ_B grid {0.5, 1, 2}, plus short-regime copies).
- **Training cap:** lifted by explicit user instruction before any confirmatory job (`runs/p10b/PREREG_ADDENDUM_1.json`). No arm was NOT_RUN for budget.
- **Freeze:** calibration and admission thresholds were chosen on the **35 P10b validation roots only**. All predictions for validation, blind and H9 roots were frozen as `runs/p10d/predictions.json` (`sha256:52a2d278…`, 0 physical calls) and **pushed (`162338e`) before the blind labels were unsealed**.

## 1. Data and protocol

**Training data:** 284 roots.
- 190 historical P8c learner-view roots, relabelled train;
- 14 P10a roots (disclosed development);
- 80 P10b train roots.

**Selection and blind sets:** 35 P10b validation roots for selection; 65 blind roots.

**Schedule:** RootSampler batch 12, AdamW 1e-3 / 1e-4, clip 10, 400 updates, best validation own-likelihood NLL every 20 updates (unchanged from P10-0).

**Objectives (unchanged):**
- B / C: exact keyed joint root NLL + static BCE + witnessed-J log-Huber;
- A / SF: the documented factorized objective.

**Ablations** (retrained from scratch with the same data, seeds and schedule; not weight-zeroing). Code hooks are `abc7_models.ModelBC7(order=, drop=)`; defaults are unchanged and verified bit-identical.

| arm | what changes |
|---|---|
| B-F2 | order-invariant repair summary: sorted, prefix-free action tokens, mean; no predecessor term |
| B-F3 | scene pair factor removed |
| B-F4 | repair–omission pair factor removed |
| B-F5s | generic scene–repair / scene–scene couplings and higher-order removed (`B-structured`) |
| B-F5q | higher-order residual only removed (`B-quadratic`) |
| B-V0 | same architecture with zeroed DINOv2 inputs |
| B-U | historical unique (non-keyed) ontology |

**Short regime (length extrapolation):** drops every H10 root, every root whose shortest VERIFIED repair needs more than 2 moves, and every candidate longer than 2 moves. That leaves 253 train and 26 validation roots.

## 2. Validation own-likelihood NLL (35 roots; seeds 0 / 1 / 2)

| arm | params | full | short |
|---|---|---|---|
| keyed B | 698,154 | 1.47 / 1.53 / 1.43 | 1.49 / 1.95 / 1.42 |
| keyed C | 714,922 | 1.47 / 1.59 / 1.68 | 1.10 / 1.70 / 1.42 |
| A | 450,596 | 2.73 / 2.68 / 2.54 | 2.55 / 2.16 / 2.71 |
| SF | 351,396 | 3.13 / 3.15 / 3.47 | 2.90 / 2.60 / 3.18 |
| B-F2 | 599,338 | 2.28 / 2.20 / 2.29 | — |
| B-F3 | 648,745 | 1.26 / 1.59 / 1.92 | — |
| B-F4 | 648,745 | 1.57 / 1.46 / 1.48 | — |
| B-F5s | 566,183 | 2.32 / 3.02 / 2.59 | — |
| B-F5q | 615,592 | 2.09 / 1.96 / 1.98 | — |
| B-V0 | 698,154 | 2.14 / 2.19 / 2.27 | — |
| B-U | 698,154 | 1.82 / 1.68 / 1.95 | — |

- **Comparability:** the short column is NLL on the short validation set (26 roots), so it is not directly comparable to the full column. Own-likelihood NLL is the negative log-probability of the same observed bits, so it is comparable across arms within a column. For A / SF the probability is the product of their factorized marginals.
- **Best update:** 180–400; most runs selected at 340–400, so 400 updates is not over-trained on validation.
- **Gradient clipping fraction:** 0.15–0.69 (lowest for B-V0, highest for SF / B-F5s).
- **Calibration** (temperature τ, threshold), validation only: τ 0.84–1.89, thresholds in {0.5, 0.7, 0.85, 0.95}. All values are in the snapshot.

## 3. D (validation)

| model | λ_B = 0.5 | λ_B = 1 | λ_B = 2 | chosen |
|---|---|---|---|---|
| D (pairwise) | 0.07–0.15 | 0.03–0.08 | 0.03–0.05 | λ_B = 2.0, threshold 0.3 |
| D-pairless | 0.22–0.24 | 0.18–0.24 | 0.19–0.24 | λ_B = 2.0, threshold 0.4 |

Values are validation NLL (λ = 1 scoring), seed range.

- **Training data:** 276 roots with a decided original task. Blocker loss is applied only to complete, proof-grounded, infeasible-original masks; per the preregistration, operational H10 corridor masks are excluded.
- **Cost:** about 7 CPU-s per run.

## 4. Preliminary development pass (disclosed)

Before the confirmatory runs, the same arms were trained on P10b batch 1 only (`runs/p10c_prelim`) and scored on its 10 validation roots. That pass is labelled PRELIMINARY and never confirmatory. Results:
- keyed B per-root NLL 0.30 vs A 0.44 and SF 0.46;
- D blocker F1 0.95 vs pairless 0.96.

Its threaded runner over-counted the training ledger, as disclosed in 0041. Its true compute was 4,600 CPU-s.

Blind results, the executed TOP1 primary and the ablation verdicts are in **0043** and **0044**.
