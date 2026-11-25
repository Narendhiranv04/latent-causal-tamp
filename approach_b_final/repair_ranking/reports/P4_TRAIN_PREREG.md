# P4 pre-registration: controlled learning (data vs ranking objective)

Registered before any training fit. The P3 teacher run was in progress and its outcomes were unseen. The code is `train_rank.py`.

## Fixed for every arm

- **Model:** the frozen coupled X/Y **arm D** architecture, unchanged (`xy.XYNet`). No cVAE change, no new head.
- **Warm start:** the same production checkpoint `2d/scorer_s0.pt` for A1–A4. A0 is that checkpoint unchanged.
- **Likelihood:** the exact observed-data NLL (`xy.batched_log_evidence`). It is a root SUM of observed nodes with missing nodes marginalized, then a mean over roots. Its normalization is not changed.
- **Optimizer:** AdamW, lr 1e-4, wd 1e-4, grad-clip 10.
  - Batches of 64 roots, from a seeded fixed partition. TRAIN roots are identical across data arms, so batch composition is identical too.
  - At most 15 epochs, patience 4, float32 on the laptop RTX 5060.
- **Ranking objective (A3, A4):**
  - Per-root mean hinge `max(0, 0.2 − s(z+) + s(z−))`, where `s = logsigmoid(b[parent]) + logsigmoid(a + w)` is computed from the logits.
  - Pairs are verified Z+ against Z− within the same root only. Z is the logical conjunction, so a Z− may have one factor missing. Missing labels are never treated as negative.
  - At most 16 pairs per root per batch: 8 uniform (seeded) plus 8 hardest by the current detached scores, or all pairs when there are ≤ 16. Roots without a pair contribute 0.
  - The total loss is `mean_r [NLL_r + λ·C·rank_r]`, with **λ = 0.1** and **C = 6** (the median observed nodes per TRAIN root, fixed in P0).
- **Data:**
  - "orig" is the original TRAIN snapshot `abf_v32_fb0eef4f5ff433ee`.
  - "aug" is that snapshot plus the strict P3 merge (`collect.py merge`).
  - No VAL, CONFIRM or TEST labels enter any weight update.
- **Seeds:** {0, 1, 2} for every arm. They vary the batch order and pair sampling; the warm start is the same. Training is cheap (P0: about 34 s for 60 epochs originally).

| Arm | Data | Objective | Identifies |
|---|---|---|---|
| A0 | none | none | frozen reference |
| A1 | orig | NLL | continued-training control |
| A2 | aug | NLL | data effect (A2 − A1) |
| A3 | orig | NLL + rank | objective effect (A3 − A1) |
| A4 | aug | NLL + rank | combined (A4 vs A2, A4 vs A3) |

A5/A6 (scratch coupled and DIRECT) are optional and are run only if budget and time remain. If not run, they are reported as not run.

## Epoch selection on DEV_CAL only

Evaluated after every epoch on DEV_CAL (370 roots; known exact-contract candidates):
- **K1/K2:** known-candidate top-1, within-root concordance, and top-1 restricted to known D4 candidates.
- **K3:** known top-1 on cached legal length-3 candidates (historical regression; no K3 queries).
- **Safeguards:** correct NOOP on K0 and correct ABSTAIN on NONE, under the frozen EXACT4 rule.
- **Likelihood:** exact NLL of the DEV_CAL labels.

**Eligible epoch:** each of D4 top-1, K0 NOOP, NONE ABSTAIN and K3 top-1 is ≥ A0's DEV_CAL value − 0.03.

**Selected epoch:** the highest top-1 among eligible epochs, then lower DEV_CAL NLL (ties within 1e-3), then the earlier epoch. Epoch −1 (the warm start) is not selectable.

## Finalist A*

1. **Arm:** among A1–A4, the highest mean DEV_CAL top-1 over 3 seeds at the selected epochs, then lower mean NLL.
2. **Checkpoint:** the deployed finalist is that arm's **seed-0** checkpoint.
3. **Qualifies only if both hold on DEV_CAL:**
   - Its paired concordance difference vs A0 (family-cluster bootstrap, 4,000 resamples) has a lower bound > 0.
   - Its top-1 is ≥ A0's.
4. **DEV_AUDIT is evaluated once and can veto.** A veto applies if the point concordance difference vs A0 is < 0, or top-1 is below A0 by more than 3 pp, or any safeguard or K3 value is below A0 by more than 3 pp. A vetoed finalist is not replaced by another arm, and nothing is retuned.
5. **If nothing qualifies:** A0 is kept and the negative learning result is reported.

## Reported regardless of the finalist

- Every arm and seed: curves, selected epoch, DEV_CAL and DEV_AUDIT metrics.
- Paired contrasts on both halves: A1 − A0, A2 − A1, A3 − A1, A4 − A2, A4 − A3.
- Seed spread, wall time, GPU peak and checkpoint hashes.
- One cohort and three warm-start seeds do not establish robustness.
