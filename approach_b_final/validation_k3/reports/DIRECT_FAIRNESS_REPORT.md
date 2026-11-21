# Experiment B: is the comparison with DIRECT fair?

**Sources and scope**
- Scripts: `multipass.py`, `pools.py`, `coupling.py` and `rules.py`. Preregistration: `prereg/PREREG_P1_P4.json`. Outputs: `runs/out/{pools,coupling,rules}/`.
- **D** = the frozen FULL scorer (s0/s1/s2). **DIRECT** = the ablation's direct-Z classifier (s0/s1/s2).
- Both score the **identical per-root M4 candidate pools**.
- Decisions are re-derived offline from raw scores; this reproduces every sealed ablation decision (0 mismatches).
- Every argmax repair of every model, on every K1–K3 root of VAL and TEST, was physically verified. The query lists were hashed before teaching, and **0 UNKNOWN outcomes** occurred.
- **TEST is historically exposed**, so every TEST number here is exploratory, not confirmation.

## B1. Where the discrepancy comes from

**1. Better scores on labeled candidates.** DIRECT has better probability metrics on the *labeled* evaluation nodes (s0):

| | Z NLL | Brier | ECE | AUROC | AUPRC |
|---|---|---|---|---|---|
| 2D VAL, D | 0.544 | 0.177 | 0.094 | 0.818 | — |
| 2D VAL, DIRECT | 0.468 | 0.150 | 0.026 | 0.852 | — |
| 3D VAL, D | 0.411 | 0.133 | 0.060 | 0.900 | — |
| 3D VAL, DIRECT | 0.442 | 0.140 | 0.047 | 0.882 | — |

- Full tables, per seed, with reliability bins: `coupling/*.json`, `per_model`.
- The labeled nodes are a *selected* candidate set (selected-assignment orders, omissions), not the population the selector searches. DIRECT's BCE objective is not comparable to D's joint X/Y NLL.

**2. Over the full pools, DIRECT's maximum score is inflated.** For each root, the score of its best candidate (`pools/*.json`, 2D/3D VAL):

| Root class | D | E | DIRECT s0 / s1 / s2 |
|---|---|---|---|
| NONE (no feasible repair exists), 2D median | 0.038 | 0.018 | **0.60 / 0.31 / 0.27** |
| NONE, 3D median | 0.10 | 0.04 | **0.43 / 0.43 / 0.52** |
| Share of NONE roots with max score ≥ η = 0.3, 2D | 4.7% | 4.0% | **92% / 52% / 47%** |
| K1–K3 roots, 2D median | 0.94 | 0.93 | 0.97 / 0.83 / 0.94 |

- The max over about 51k (2D) or 3.7k (3D) candidates of a classifier that is calibrated *on average* is biased upward: **winner's curse**.
- **D is protected by its factor σ(b_s).** That factor is trained on many endpoint-only Y labels (2D TRAIN 4,232 Y=0 endpoints with no X child; 3D 1,244), which never reach DIRECT. On NONE roots every endpoint is infeasible, so σ(b) caps every candidate.
- The NOOP score is not the problem. DIRECT's p_noop separates K0 from NONE as well as D's does (NONE median about 0.001; K0 ≥ 0.5 for 97% of 2D VAL roots).

**3. How DIRECT fails** (selected repairs, ablation results, s0):
- **2D VAL:** DIRECT has 307 FAIL_Y + 57 FAIL_X, against 111 FAIL_Y + 58 FAIL_X for D.
- **3D TEST:** 70 FAIL_Y vs 27 FAIL_Y.
- **DIRECT's extra failures are almost entirely endpoint (target) failures.**

## B2. Registered vs VAL-tuned decision rules

**Tuning procedure** (preregistered):
- Grid: NOOP gate ∈ {0.3…0.9}, η ∈ {0.0…0.6} (7 × 7).
- Selection on VAL only, maximizing the frozen rule's own objective: the mean of task, correct-NOOP and correct-ABSTAIN rates.
- Tie-break: closest to (0.5, 0.3).
- **The same procedure is applied to D (and E) as the control.**
- The tuned rules were written once (`TUNED_RULES_{dom}.json`, sha 86901ab6… 2D / ccb2588b… 3D) before any TEST metric of a tuned rule was computed.

**Tuned rules (gate, η):**

| Model | 2D s0 / s1 / s2 | 3D s0 / s1 / s2 |
|---|---|---|
| D | (0.8, 0.4) / (0.4, 0.6) / (0.7, 0.3) | (0.4, 0.6) / (0.6, 0.5) / (0.4, 0.6) |
| DIRECT | (0.6, 0.6) / (0.3, 0.6) / (0.3, 0.6) | (0.4, 0.6) / (0.6, 0.6) / (0.5, 0.6) |
| E | (0.5, 0.3) / (0.7, 0.4) / (0.6, 0.3) | (0.5, 0.5) / (0.6, 0.5) / (0.7, 0.6) |

**Seed-mean rates (%)**, registered → VAL-tuned. Forced = repair-forced top-1 (threshold-free).

| | Task (K1–K3) | Correct NOOP (K0) | Correct ABSTAIN (NONE) | Objective |
|---|---|---|---|---|
| 2D VAL, D | 55.8 → 56.4 (forced 57.8) | 96.8 → 97.2 | 91.3 → 96.0 | 81.3 → 83.2 |
| 2D VAL, DIRECT | 44.9 → 44.2 (forced 46.2) | 94.0 → 96.6 | **36.4 → 77.6** | 58.4 → 72.8 |
| 2D TEST, D | 51.8 → 52.2 (forced 53.8) | 91.1 → 89.7 | 92.0 → 96.2 | 78.3 → 79.4 |
| 2D TEST, DIRECT | 38.5 → 38.0 (forced 39.6) | 88.1 → 90.9 | **39.3 → 78.9** | 55.3 → 69.3 |
| 3D VAL, D | 78.5 → 77.4 (forced 83.8) | 83.9 → 86.7 | 78.7 → 96.0 | 80.4 → 86.7 |
| 3D VAL, DIRECT | 66.1 → 65.2 (forced 71.1) | 84.7 → 86.3 | **31.0 → 63.2** | 60.6 → 71.5 |
| 3D TEST, D | 80.8 → 79.0 (forced 84.1) | 86.1 → 85.6 | 86.0 → 96.8 | 84.3 → 87.1 |
| 3D TEST, DIRECT | 70.0 → 69.3 (forced 72.6) | 82.6 → 82.6 | **32.3 → 61.3** | 61.6 → 71.1 |

**Paired DIRECT − D** (seed-mean per root, 95% layout-cluster CI, pp):

| | Task, registered | Task, VAL-tuned | Task, forced (threshold-free) | ABSTAIN, registered | ABSTAIN, tuned |
|---|---|---|---|---|---|
| 2D VAL | −10.9 [−14.2, −7.7] | −12.2 [−15.5, −9.0] | −11.6 [−14.8, −8.6] | −54.9 | −18.4 [−21.8, −15.1] |
| 2D TEST | −13.3 [−16.4, −10.1] | −14.2 [−17.2, −11.0] | −14.2 [−17.2, −11.1] | −52.7 | −17.3 [−21.1, −13.8] |
| 3D VAL | −12.4 [−16.8, −8.2] | −12.3 [−16.7, −8.2] | −12.7 [−17.1, −8.6] | −47.7 | −32.8 [−42.5, −23.6] |
| 3D TEST | −10.8 [−14.7, −7.1] | −9.7 [−13.8, −5.5] | −11.5 [−15.5, −7.6] | −53.8 | −35.5 [−44.6, −26.3] |

**Reading.**
1. **Threshold tuning helps DIRECT's abstention a lot** (+29 to +41 pp of correct ABSTAIN), so the registered-rule ABSTAIN gap was partly a scale mismatch.
2. **Tuning does not help DIRECT's task success.** The task gap stays at −10 to −14 pp in all four cells.
3. **The gap is just as large with no thresholds at all** (forced repair). DIRECT's *top-ranked* repair is physically worse.
4. **Even with its own tuned thresholds, DIRECT abstains 17–35 pp less often** on NONE roots than tuned D.

## B3. Ranking-only view (thresholds removed)

| Score | Top-1 physical success, forced repair, K1–K3 (seed mean): 2D VAL / TEST / 3D VAL / TEST | Same-endpoint order accuracy (labeled, s0): 2D VAL / 3D VAL | Rank of the best known success, pool median (s0): 2D VAL / 3D VAL |
|---|---|---|---|
| D p11 | 57.8 / 53.8 / 83.8 / 84.1 | 0.802 / 0.797 | 185 / 12 |
| DIRECT | 46.2 / 39.6 / 71.1 / 72.6 | 0.799 / 0.816 | 542 / 17 |
| E p11 | 59.2 / 51.5 / 79.7 / 86.7 | 0.795 / 0.835 | 209 / 13 |

**How to read the four layers**
- **Probability estimation on labeled candidates:** DIRECT ≥ D.
- **Order ranking within an endpoint:** about equal.
- **Ranking across endpoints in the full pool:** DIRECT is clearly worse (its top-1 has more Y failures).
- **Decision thresholding:** fixes part of DIRECT's abstention, not its task success.

## Conclusion

**Can we claim that factorized X/Y modeling beats direct Z classification? Yes, with a stated qualification.**
- With identical candidate pools, the factorized D gives 10–14 pp higher verified task success than DIRECT under the registered rule, under model-specific VAL-tuned thresholds, and with no thresholds at all, in both domains and both splits.
- **The ABSTAIN advantage depends on the rule.** About 60% of it disappears once DIRECT gets its own thresholds, so it must be reported with tuned rules.
- **The mechanism is supported by the data.** The endpoint factor σ(b), trained on endpoint-only Y labels, keeps the pool maximum honest on infeasible endpoints. DIRECT has no such factor and no access to those labels.
- Part of the win is therefore an *information* difference created by the factorization (DIRECT cannot use endpoint-only labels), not only an architectural one.
- **Held-out caveat:** TEST is historically exposed, and the V3.4 cohort was not used, since spending it requires owner approval. The TEST rows are exploratory, but they replicate VAL in direction and size.
