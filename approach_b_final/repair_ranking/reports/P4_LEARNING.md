# P4: controlled learning (data vs ranking objective)

**Outcome: no qualifying finalist. A0 (the frozen scorer) is retained.**

The pre-registration is `P4_TRAIN_PREREG.md` (`c95447641a`). Results are in `P4_ABLATION.json` and `figures/p4_learning_contrasts.png`.

## Runs

- **Setup:** 12 warm-start fits (A1–A4 × seeds 0/1/2) of the frozen coupled arm D from `scorer_s0.pt`.
  - Exact root-sum NLL; A3/A4 add the within-root hinge (λ = 0.1, C = 6, margin 0.2 nats).
  - AdamW lr 1e-4; at most 15 epochs, patience 4. Selected epochs ranged from 0 to 3.
- **Compute:** 66–123 s wall per fit and 266 MB GPU peak on the laptop RTX 5060. **0.31 GPU-h in total** (cap 8).
- **Ranking pairs:** 1,719 TRAIN roots with pairs (orig) and 1,743 (aug).
- **Checkpoints:** in `~/xyrr_runs/p4/<arm>_s<seed>/epNN.pt`, with hashes in `P4_ABLATION.json`. They are not in Git.

## DEV results (mean over 3 seeds at the selected epochs)

| Arm | DEV_CAL top-1 | DEV_CAL concordance | DEV_CAL NLL | DEV_AUDIT top-1 | DEV_AUDIT concordance | DEV_AUDIT NLL |
|---|---|---|---|---|---|---|
| A0 (frozen) | 0.685 | 0.695 | 12.72 | 0.789 | 0.745 | 14.44 |
| A1 (orig, NLL) | 0.715 | 0.716 | 12.69 | 0.794 | 0.737 | 13.99 |
| A2 (aug, NLL) | 0.723 | 0.716 | **12.30** | 0.772 | 0.748 | **13.67** |
| A3 (orig, NLL + rank) | 0.719 | 0.713 | 12.82 | 0.785 | 0.732 | 14.10 |
| A4 (aug, NLL + rank) | **0.730** | 0.716 | 12.41 | 0.772 | 0.746 | 13.79 |

Across all three seeds, every arm kept the K0 NOOP (≥ 0.975 / ≥ 0.951 on DEV_CAL / DEV_AUDIT), NONE ABSTAIN (0.949 / 0.972) and K3 top-1 safeguards within 3 pp of A0. The historical K3 regression check showed no degradation.

## Paired contrasts (within-root concordance; 95 % family CI; range over the three seeds)

| Contrast | DEV_CAL | DEV_AUDIT | Reading |
|---|---|---|---|
| A1 − A0: continued training | +0.015 to +0.028 | −0.015 to −0.003 | DEV_CAL gains come from extra optimization plus epoch selection on DEV_CAL; they **do not transfer** |
| A2 − A1: P3 data | −0.005 to +0.004 | +0.006 to +0.015 (CIs touch 0) | No ranking effect; **NLL improves on both halves** (−0.39 / −0.32 nats per root) |
| A3 − A1: rank objective | −0.008 to +0.005 | −0.012 to +0.001 | No effect, or slightly negative; the TRAIN hinge was nearly satisfied from the start (loss ≈ 0.06) |
| A4 − A2: rank, given augmented data | −0.002 to +0.001 | −0.008 to +0.002 | none |
| A4 − A3: data, given rank loss | −0.001 to +0.006 | +0.008 to +0.020 (lower bounds ≥ 0) | small held-out gain from data under the rank loss |

**Finalist rule (registered):**
- The best arm by mean DEV_CAL top-1 is A4, and its seed-0 checkpoint is the candidate.
- Its DEV_CAL paired concordance difference vs A0 is **+0.0185 [−0.0034, +0.0402]**. The lower bound is not above 0, so it **does not qualify**, even though top-1 rose from 0.685 to 0.719.
- On DEV_AUDIT the difference is +0.001 [−0.023, +0.026], with no veto trigger. That is moot, since nothing qualified.

## Answers

- **Data effect (A2 − A1):**
  - Targeted TRAIN labels **improve the exact held-out likelihood**, which reflects calibration and probability quality: −0.4 nats per root on both DEV halves.
  - They **do not improve within-root repair ranking** on family-disjoint DEV_AUDIT, apart from a small effect when combined with the rank loss.
- **Objective effect (A3 − A1):** adding a within-root ranking hinge to the exact NLL has **no measurable benefit.**
- **Extra optimization (A1 − A0):** this produces DEV_CAL-only gains. That is a reminder that DEV_CAL improvements of about +0.02 are within selection noise.
- **Component probabilities are preserved.** The model, likelihood and readout are unchanged, so pY / pX1 / p11 remain exact functions of (b, a, w).
- **Limits:**
  - There are 3 warm-start seeds and one development cohort, and VAL is exposed.
  - The checkpoint was originally early-stopped on VAL.
  - Larger λ, scratch training (A5) and DIRECT (A6) were not run; A5/A6 are optional and marked not run.
