# R3.1 — Targeted local execution labels

Pre-registration: `../R3_PREREG.json` (R3_1_3d, R3_1_2d). Policy and code: `../data.py`.

The manifests were sealed before dispatch:
- `jobs_31_3d.json`, sha16 `602f4b1faed7fec2`
- `jobs_31_2d.json`, sha16 `6331f472831df6a4`

Every label uses the R2.4 contract (`labels.chunks_of`):
- A completed chunk, including its connector to q_ref, is labelled 1.
- The failing chunk is labelled 0.
- Chunks after a failure are unobserved.
- An unresolved (UNKNOWN) outcome is never a negative.

## 3D — TRAIN_SCALE / VAL_SCALE (pilot; no expansion)

**Collection.** 84 scenes, one root per clean family: 58 TRAIN_SCALE and 26 VAL_SCALE. Families are disjoint between the two splits and from every DEV, diagnostic and exposure set (unit-tested).
- N ranges from 5 to 9.
- 27 scenes are HYPSTART: a crowded static layout, not an executed prefix.
- 43 scenes include a fragment of a verified original sequence.

**Cost.** 588 teacher jobs (pilot cap 600), 2.79 CPU-h. There were 0 errors, 0 censored jobs and 0 retries. The 588 jobs yielded 792 exact labels and no conflicting duplicates.

| Split | h = 0 labels (positive / negative) | h = 0 mixed families | h ≥ 1 labels (positive / negative) | h ≥ 1 mixed families |
|---|---|---|---|---|
| TRAIN_SCALE | 406 (236 / 170) | 56 | 142 (56 / 86) | 30 |
| VAL_SCALE | 182 (102 / 80) | 23 | 62 (24 / 38) | 10 |

- **Chunk length.** m = 1 / 2 / 3 counts: TRAIN_SCALE h0 290 / 58 / 58 and h ≥ 1 68 / 45 / 29; VAL_SCALE h0 130 / 26 / 26 and h ≥ 1 26 / 25 / 11.
- **Failure causes.** 367 of 376 negatives are "no feasible side grasp". Six are execution not verified at h0, one is a connector with no plan, and two are other planner failures. Grasp blockage by surrounding bodies dominates; carried-configuration or connector failures are rare.
- **Matched contrasts.** The templates provide these matched pairs:
  - the same action before (T1) and after (T2) one relocation;
  - the same object with a different destination (T7 vs T1);
  - the same endpoint in a different permutation (T4 / T5);
  - model-confident singles (T3, H source): 70 executable vs 14 not at h0.
- **No expansion.** The pre-registered trigger did not fire: VAL_SCALE mixed families are ≥ 10 in both strata, and TRAIN_SCALE has 86 h ≥ 1 negatives (floor 60). The h ≥ 1 VAL stratum sits exactly at the 10-family floor, so its CIs are wide.
- **Disclosures.**
  - 21 scenes are `K_legacy = NONE` roots. The "K ≥ 1 first" sort key did not demote them. They are dense, valid local-X scenes.
  - 4 VAL_SCALE / TRAIN_SCALE roots also had one R3.0 contract-audit run.
- **Natural panel.** NATURAL_VAL (original v32 VAL labels, 776 labels on non-exposed families) is the fixed, naturally sampled panel. VAL_SCALE is the targeted panel.

## 2D — frozen local-X diagnostic (≤ 60 queries)

**Collection.** 15 clean original-VAL families (N 13–20, K_legacy ≠ 0), templates T2 / T3 / T6 / T7. 60 queries, 0.17 CPU-h.

**Outcomes.**
- Teacher statuses:
  - 26 certified-infeasible relocations: 17 at relocation 0, 8 at relocation 1, 1 at relocation 3.
  - 9 VERIFIED runs.
  - 10 unresolved connectors at a boundary (`UNKNOWN_TRANSIT`).
  - 15 unresolved planner runs (`UNKNOWN_PLANNER`).
- These yield 62 labels: h0 44 (27 positive) and h1 18 (9 positive).
- Unresolved connectors and planner runs cut off most h ≥ 1 observations. They are never negatives.

**Pre-registered decision on the h ≥ 1 union** (R2.4 2D panel + this panel; frozen marginal pX): AUROC 0.81 [0.70, 0.90], n = 144, **6 mixed families < 10** → **INCONCLUSIVE (support)**.
- The two panels separately: R2.4 0.74 [0.59, 0.85] on 5 mixed families; R3.1 0.72 on 1.
- At h0: the union is 0.74 (17 mixed families), and R3.1 alone is 0.65.

**Consequence (pre-registered).**
- No 2D targeted collection and no 2D X training or graph model.
- No 2D order recovery, since R3.4 2D requires the 2D X to pass.
- 2D stays blocked while 3D proceeds. The point estimate does not suggest a large 2D deficit, but it is not established.

## 2D — long-witness development cohort (DEV_ORDER_2D)

This stage is **running**. Generator: k3scale `gen_deep.py`, unchanged, with string seeds `R3COH2D|i`, run under `gen2d.py`.
- Static stage: 200 seeds × 8,000 steps, no teacher. It has produced 94 candidate layouts so far (K_lb 4 / 5 / 6).
- Witness stage: `witness_v3.py`, unchanged, under the 400-layout / 4,000-query / 24 CPU-h caps. It follows when the static stage ends.

Results will be added to `R3_DECISION.md`. Release_v2 is never read.

## Figure

`figures/R3_1_data_3d.png`:
- (a) Yield by h × m and split.
- (b) Teacher failure causes.
- Real scenes at true scale:
  - a blocked first grasp with F0 pX = 1.00;
  - the same action executable at S0 but not after one relocation;
  - a matched permutation pair with discordant outcomes.
