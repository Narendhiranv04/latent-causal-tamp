# 0062 — P13-3: preregistration, training / validation data, matched retraining and the frozen test

**Previous turn sync:** P13-2 pushed as `a551db6575a2f29236469fe648b146683aafc59f`; roster plans and the dedup rule pushed as `ac6b4e38`.

**Actual result.**
- **Gate:** `runs/p13/P13_3_GATE.json` → **PASS** (deviations are disclosed below and in `PREREG_ADDENDUM_1.json`).
- **Preregistration:** `PREREG.json` (sha256:7dbcb3a9…) was pushed before any roster label. The addendum (sha256:0be5c0d3…) was written before any blind label and is pushed with the freeze.
- **Roster:** 370 new roots, 0 unavailable:

  | split | roots |
  |---|---|
  | train | 160 |
  | validation | 40 |
  | blind challenge | 122 |
  | natural blind | 48 |

  Six cross-batch fingerprint duplicates (parallel builders could not see each other's plans) are resolved by a rule fixed before any label:
  - five train / validation roots excluded from learning (leakage);
  - one blind duplicate excluded from analysis.

  This leaves **169 blind roots**.
- **Training / validation labels:** 200 roots, 1,496 queries. Statuses: 560 VERIFIED, 745 CERTIFIED, 103 BUDGET (operational), 78 UNKNOWN, 10 NOT_RUN.
- **Matched retraining:** 39 checkpoints and 18 D models; training cost 33,683 / 35,000 CPU-s after the accounting correction (§3).
- **Frozen predictions:** `runs/p13/holdout/PREDICTIONS_FROZEN.json`, **sha256:ed31d4ef…**.
  - Every checkpoint scores every blind root: marginals, the keyed P_S joint, F1 static P(valid), TOP1 rows and choice.
  - D, the geometry heuristic and geometry TOP1 are included.
  - **0 physical calls**, and the analytic veto fired on **0** candidates.
- **Frozen execution plan:** `p13_5/EXEC_JOBS.json` (one random root permutation, 8 workers, G+M ranking) is part of the same freeze.

## 1. Training / validation evidence (mechanism-conditioned, as designed)

**Proof-grounded pair four-tuples:**

| family | κ classes |
|---|---|
| PC_SERIAL | +1: 16 |
| PC_SG | +1: 14 |
| PR_SIDES | −1: 14 |
| PN_SIMP | 0: 12 |
| PN_GIMP | 0: 19 |
| NAT | 0: 19 |
| ORD_CHAIN | +1: 4 |
| OMIT_OPT | +1: 6 |

**Totals:** κ = +1: 40, κ = 0: 50, κ = −1: 14.

The realized κ follows the family by construction (case-control). A model can therefore learn "family geometry → κ". This is exactly what the challenge set tests; the natural stream is the guard against it.

**Triple lattices:** TRI_SERIAL 105 CERTIFIED / 13 VERIFIED / 2 UNKNOWN; TRI_CTRL 90 / 24 / 6.

**Learner data:** the 319 P10c roots plus 195 P13 roots (156 train, 39 validation).

## 2. Matched training (`runs/p13/models`, 400 updates, batch 12, selection by validation root NLL every 20 updates)

**Validation root NLL** (three seeds; A / SF use their PoE objective and are not comparable on this scale):

| arm | seeds | validation NLL |
|---|---|---|
| **K-B** | 3 | 1.45 / 1.71 / 1.85 |
| K-C | 3 | 1.77 / 1.54 / 1.80 |
| B-F3pm | 3 | 1.90 / 1.41 / 1.60 |
| B-F4 | 3 | 1.87 / 1.64 / 1.62 |
| B-F5qpm | 3 | 1.87 / 1.69 / 1.90 |
| B-F1off | 3 | 1.66 / 1.76 / 1.57 |
| B-U | 3 | 1.86 / 1.61 / 1.88 |
| B-V0 | 3 | 2.04 / 1.85 / 1.97 |
| B-F2 | 3 | 2.10 / 2.33 / 2.35 |
| B-F5spm | 3 | 2.12 / 2.10 / 2.26 |
| B-F3 / B-F5s / B-F5q (plain) | 1 each | 1.81 / 2.41 / 1.92 |

**Training health:** all runs are finite, the selected update is 220–400, and the clip fraction is 0.11–0.67.

**D validation NLL:** D (λ_B = 1.0, selected) 0.094–0.137; D-pairless (λ_B = 2.0, selected) 0.192–0.219.

**Parameter-matched controls:** within 0.06 % of K-B (+127, +383 and −2 parameters).

## 3. Deviations (disclosed in `PREREG_ADDENDUM_1.json`, all before any blind label)

1. **Accounting error.** The first training launcher ran 28 guards as threads of one parent process. `teacher.guard` reports the maximum of its psutil tree sample and the parent's RUSAGE_CHILDREN delta, and that delta absorbed other jobs' children: the ledger showed 110,274 CPU-s.
   - **Correction:** a training child is single-threaded, so its CPU is bounded by its wall time; training CPU is counted as min(guard, wall).
   - **Validation:** the A s0 child's own process_time is 734 s and its wall 753 s, while the guard reported 2,025 s.
   - **Record keeping:** the original guard records are unchanged, and every later launch is one OS process per job (test: `_cpu`).
2. **Oversubscription.** That launch also ran 28 single-threaded jobs on 16 physical cores. Hyperthread contention roughly doubled CPU per job (~1,000 versus ~400 CPU-s at ≤ 14 concurrent).
3. **Seeds.** Before the error was understood, 13 jobs were terminated to protect the cap; 7,560 CPU-s were sunk. After the correction, every arm was restored to 3 seeds except the plain off arms B-F3, B-F5s and B-F5q (1 seed each, secondary capacity attribution only).
4. **Implementation only.** The freeze was split into per-checkpoint processes plus a merge, using the identical TOP1 rule.

**Unchanged:** every primary hypothesis, endpoint, cohort, threshold and verdict rule.

## 4. Commit sequence

1. `PREREG` → pushed in `a551db6`, before any roster label.
2. Plans + `DEDUP.json` → pushed in `ac6b4e38`.
3. Training / validation labels, models, frozen predictions, frozen execution jobs and the addendum → **the freeze commit** (SHA in the chat reply and in 0063).
4. Only then `runs/p13/holdout/FREEZE_PUSHED` is written (it checks that the files on origin are byte-identical), and blind static admission and labelling start.
5. Blind outcomes go to `sealed/` and are hash-committed (`LABELS_MANIFEST.json`) before `UNSEALED`.
