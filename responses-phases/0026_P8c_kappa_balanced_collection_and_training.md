# 0026 — P8c: κ-balanced 36-root collection and fresh A / B / C / S training

**Actual result.**

*Collection.* Both waves of the predeclared 36-root κ-balanced pilot ran under the unchanged OPNEG-v1 teacher:
- **450 queries**: 175 VERIFIED, 142 CERTIFIED, 34 BUDGET_INFEASIBLE, 13 UNKNOWN, **86 NOT_RUN (19 %)**;
- **8,893 / 12,000 teacher CPU-s**;
- the wave-1 gate passed 6/6.

*Development κ.* +1 ×5 (all operational: place side), **0 ×8, −1 ×4**. That meets ≥ 4 decided roots per sign, but there
is **no proof-grounded +1**, and **no same-endpoint order contrast** was decided (24 swaps, all equal labels).

*Training (fresh sealed test, 12 roots, 76 decided candidates, κ test roots 2 / 3 / 2).*
- The arms with **generic coupling are the most accurate repair-feasibility predictors**: B-full 0.882 / AUROC 0.953,
  C-full 0.886 / 0.950, B-quadratic 0.882 / 0.943; then B-none 0.851, SF 0.838, A 0.825, B-structured 0.789.
- **Only coupled arms predict any complementary (+1) interaction** (0.67 / 0.67 / 0.50 against 0.00–0.17).
- Overall κ MAE is similar across arms (0.47–0.64).
- The oracle-revealed conditional advantage seen in P8a **does not transfer** to fresh roots.
- Test NLL is high for every arm (validation-only temperatures from 12 roots).

**Verdicts.**
- `P8C_COLLECTION_PASS`; κ sufficiency met (≥ 4 per sign) but only operational for +1.
- `P8C_TRAINING_PASS` (engineering): 21 runs, **2,879.9 / 11,000 CPU-s**, rankings frozen before unseal.
- Previous turn sync: `b79ef14`.

## 1. Plan (frozen before any teacher call; `p8_scenes.py`, `p8_collect.py`)

**Roots.**
- 36 roots, 12 per construction intent (K_PLUS = P7 KP constructor, K_MINUS = KM, K_ZERO = K0).
- Seeds 2026102501–36. Splits per intent: 6 train / 2 validation / 4 test; waves of 18 with 3 / 1 / 2 per intent.
- Strata S0–S3; the edited sides, target, goal, clutter (0–2), nuisance and destinations vary per root.
- Construction and plan used the P7 constructor with root prefix `p8_` (P7 output unchanged). 42.9 CPU-s, all 36
  constructed, no unavailable intent; every attempt is logged.

**Catalogue** (≤ 20 unique teacher queries per root; 450 total, 1,350 seed units; cap 720). The outcome-blind priority
is: reference, scene edits A / B / A+B / nuisance, empty repair, singles, main, longer alternative (≤ 4 moves), swap,
omissions, alternative destination, pairs, closure. Execution follows this order per root.

**Static admission:** 236.4 CPU-s (total static **279.3 / 800**), no planner call; **142 certified** (TARGET_PICK 140,
FIRST_MOVER 1, ORDER_FIRST_ACTION 1).

**Caps.**

| item | cap | max used |
|---|---|---|
| per root | 650 CPU-s | 496 |
| per wave | 6,000 CPU-s | 5,592 (wave 1) |
| aggregate | 12,000 CPU-s | 8,893 |
| wall | 24,000 s | 9,177 s |

**Wave-1 gate** (development roots only) — **PASS**:
- κ +1 / 0 / −1 = 3 / 3 / 3 (3 operational);
- a fully decided multi-action pool for all three intents;
- 8 roots with two verified repair lengths;
- unresolved + NOT_RUN 31 / 152 = 20 % (≤ 35 %);
- budget held.

## 2. Collection results (`runs/p8/collection`)

| quantity | value |
|---|---|
| seed attempts | 301 (294 completed, 7 CPU-censored) |
| all queries | 175 V / 142 C / 34 B / 13 U / 86 NR |
| development queries | 118 V / 94 C / 23 B / 9 U / 54 NR |
| sealed test (counts only) | 57 V / 48 C / 11 B / 4 U / 32 NR |

- **NOT_RUN causes:** 77 cap-stopped by per-root remainders, after expensive search exhaustion; 9 lineage-stopped. One
  development reference was BUDGET_INFEASIBLE (p8_2026102520).
- **NOT_RUN rate:** 86 / 450 = 19 %, against P7's 201 / 971 = 21 %. The essential-first order put the edits and singles
  before expensive candidates.
- **Development budget terminals:** PLACE_SCREEN_EXHAUSTED_CERTIFIED 54, SCHEDULE_COMPLETED_…_UNRESOLVED_CONNECTORS 9,
  SEARCH_LIMIT_PLAN_FAILURES 3, PICK_SCREEN_EXHAUSTED_UNCERTIFIED 3.
- **Development κ by intent:** K_ZERO → 0 ×7 (certified); K_PLUS → +1 ×5 (operational, place-side negatives under A7
  disabled); K_MINUS → −1 ×4 (certified) and 0 ×1 (operational).
- **Coverage:** 16 of 24 development roots have two different VERIFIED repair lengths; 17 of 24 are joint-pool-ready
  (111 complete candidates).
- **Integrity:** all 8 historical manifests are unchanged.

**Per-root ledger** (test outcomes stay sealed in this table; V / C / B / U / NR):

| root | intent | split | wave | start | attempt | queries | V/C/B/U/NR | CPU-s | verified lengths |
|---|---|---|---|---|---|---|---|---|---|
| p8_2026102501 | K_PLUS | train | 1 | S2 | 0 | 16 | 1/6/1/1/7 | 409.2 | — |
| p8_2026102502 | K_PLUS | train | 1 | S3 | 4 | 16 | 4/6/2/0/4 | 415.5 | 2, 3 |
| p8_2026102503 | K_PLUS | train | 1 | S0 | 19 | 16 | 5/6/4/0/1 | 361.6 | 2, 3 |
| p8_2026102504 | K_PLUS | validation | 1 | S1 | 7 | 16 | 5/6/3/1/1 | 439.5 | 2, 3 |
| p8_2026102505 | K_PLUS | test | 1 | S2 | 13 | 16 | sealed | 126.2 | sealed |
| p8_2026102506 | K_PLUS | test | 1 | S3 | 0 | 16 | sealed | 496.1 | sealed |
| p8_2026102507 | K_MINUS | train | 1 | S3 | 2 | 11 | 6/2/0/0/3 | 422.5 | 1 |
| p8_2026102508 | K_MINUS | train | 1 | S0 | 5 | 11 | 1/2/0/1/7 | 433.7 | — |
| p8_2026102509 | K_MINUS | train | 1 | S1 | 2 | 11 | 8/2/1/0/0 | 61.2 | 1, 2 |
| p8_2026102510 | K_MINUS | validation | 1 | S2 | 8 | 11 | 7/2/0/1/1 | 466.1 | 1, 2 |
| p8_2026102511 | K_MINUS | test | 1 | S3 | 2 | 11 | sealed | 368.7 | sealed |
| p8_2026102512 | K_MINUS | test | 1 | S0 | 4 | 11 | sealed | 433.7 | sealed |
| p8_2026102513 | K_ZERO | train | 1 | S0 | 3 | 11 | 2/6/0/1/2 | 492.8 | — |
| p8_2026102514 | K_ZERO | train | 1 | S1 | 0 | 11 | 7/4/0/0/0 | 28.9 | 1, 2 |
| p8_2026102515 | K_ZERO | train | 1 | S2 | 0 | 11 | 7/4/0/0/0 | 14.3 | 1, 2 |
| p8_2026102516 | K_ZERO | validation | 1 | S3 | 31 | 11 | 7/4/0/0/0 | 228.2 | 1, 2 |
| p8_2026102517 | K_ZERO | test | 1 | S0 | 1 | 11 | sealed | 347.9 | sealed |
| p8_2026102518 | K_ZERO | test | 1 | S1 | 10 | 11 | sealed | 46.2 | sealed |
| p8_2026102519 | K_PLUS | train | 2 | S0 | 7 | 16 | 6/6/4/0/0 | 74.9 | 2, 3 |
| p8_2026102520 | K_PLUS | train | 2 | S1 | 1 | 16 | 0/6/1/0/9 | 224.0 | — (reference BUDGET) |
| p8_2026102521 | K_PLUS | train | 2 | S2 | 36 | 16 | 6/6/4/0/0 | 89.2 | 2, 3 |
| p8_2026102522 | K_PLUS | validation | 2 | S3 | 20 | 11 | 1/3/1/1/5 | 488.8 | — |
| p8_2026102523 | K_PLUS | test | 2 | S0 | 10 | 16 | sealed | 428.9 | sealed |
| p8_2026102524 | K_PLUS | test | 2 | S1 | 2 | 16 | sealed | 64.2 | sealed |
| p8_2026102525 | K_MINUS | train | 2 | S1 | 1 | 11 | 7/2/0/1/1 | 481.7 | 1, 2 |
| p8_2026102526 | K_MINUS | train | 2 | S2 | 0 | 11 | 2/2/0/1/6 | 393.9 | — |
| p8_2026102527 | K_MINUS | train | 2 | S3 | 4 | 11 | 7/2/2/0/0 | 129.4 | 1, 2 |
| p8_2026102528 | K_MINUS | validation | 2 | S0 | 4 | 10 | 1/1/0/1/7 | 396.6 | — |
| p8_2026102529 | K_MINUS | test | 2 | S1 | 8 | 11 | sealed | 170.6 | sealed |
| p8_2026102530 | K_MINUS | test | 2 | S2 | 4 | 11 | sealed | 81.2 | sealed |
| p8_2026102531 | K_ZERO | train | 2 | S2 | 1 | 11 | 7/4/0/0/0 | 53.1 | 1, 2 |
| p8_2026102532 | K_ZERO | train | 2 | S3 | 3 | 11 | 7/4/0/0/0 | 41.8 | 1, 2 |
| p8_2026102533 | K_ZERO | train | 2 | S0 | 1 | 11 | 7/4/0/0/0 | 52.2 | 1, 2 |
| p8_2026102534 | K_ZERO | validation | 2 | S1 | 3 | 11 | 7/4/0/0/0 | 41.1 | 1, 2 |
| p8_2026102535 | K_ZERO | test | 2 | S2 | 1 | 11 | sealed | 32.4 | sealed |
| p8_2026102536 | K_ZERO | test | 2 | S3 | 4 | 11 | sealed | 57.1 | sealed |

## 3. Training (`runs/p8/c_training`, one guard, 2,879.9 / 11,000 CPU-s, 0 teacher calls)

**Setup.**
- **Data:** train = P8c train roots plus all historical P4–P7 roots, relabelled train with source tags (P7 test roots
  tagged `HIST_P7_TEST_DISCLOSED`): **178 roots, 1,250 candidates**. Validation = 12 P8c validation roots.
- **Arms:** A, B-full, B-structured, B-none, C-full and SF × 3 seeds, plus the optional B-quadratic × 3 (P8a's best
  variant; offline only).
- **Protocol:** the P8a configurations, 200 matched updates, the κ-balanced sampler. Temperature and threshold (same
  lexicographic rule over {0.5, 0.7, 0.85, 0.95}) are chosen on P8c validation only.
- **Freeze order:** all checkpoints, thresholds and the 72 one-shot rankings were frozen and hashed
  (`rankings.json`, `sha256:5d2f9238…`) **before** test labels were read. Rankings were computed on a label-blinded copy
  of the test roots.

**Fresh sealed-test results** (calibrated, mean ± sd over 3 seeds; seed-0 root-bootstrap 95 % CI for accuracy):

| arm | accuracy [CI s0] | AUROC | NLL | ECE | scene NLL | κ MAE | κ sign by obs. −1 / 0 / +1 | offline selection (7 roots) |
|---|---|---|---|---|---|---|---|---|
| C-full | **0.886 ± 0.020** [0.76, 0.96] | 0.950 | **0.637** | **0.104** | **0.491** | 0.522 | 0.50 / 0.78 / **0.67** | **0.95** |
| B-full | **0.882 ± 0.023** [0.81, 0.97] | **0.953** | 0.870 | 0.114 | 0.495 | **0.466** | 0.50 / 0.44 / **0.67** | 0.71 |
| B-quadratic (optional) | 0.882 ± 0.039 [0.87, 0.97] | 0.943 | 0.785 | 0.103 | 0.568 | 0.521 | 0.50 / 0.67 / 0.50 | 0.81 |
| B-none | 0.851 ± 0.015 [0.73, 0.96] | 0.931 | 1.055 | 0.143 | 0.552 | 0.635 | 0.67 / **1.00** / 0.00 | 0.76 |
| SF | 0.838 ± 0.008 [0.77, 0.94] | 0.898 | 0.894 | 0.147 | 0.565 | 0.479 | 0.67 / 0.89 / 0.17 | 0.62 |
| A | 0.825 ± 0.020 [0.72, 0.95] | 0.891 | 0.910 | 0.159 | 0.590 | 0.539 | 0.67 / 0.89 / 0.00 | 0.62 |
| B-structured | 0.789 ± 0.013 [0.65, 0.91] | 0.892 | 1.026 | 0.178 | 0.576 | 0.619 | **1.00** / 0.78 / 0.00 | 0.71 |

**Offline conditional diagnostic on the test roots** (oracle-revealed; NLL per hidden bit, tasks a / b / c / d;
7 / 7 / 2 / 7 roots):

| arm | a | b | c | d |
|---|---|---|---|---|
| B-structured | **0.56** | **0.67** | 0.46 | 0.99 |
| SF | 0.62 | 0.95 | 0.60 | **0.81** |
| B-full | 0.95 | 1.03 | **0.33** | 0.83 |
| C-full | 1.06 | 1.23 | 0.39 | 0.83 |
| B-quadratic | 1.11 | 1.23 | **0.33** | 0.95 |

The P8a conditional advantage of coupled models **reverses** on fresh roots: their joint scene structure is
over-confident out of distribution.

**Validation** (12 roots, κ roots 1 / 2 / 1): B-full 0.990, C-full 0.980, B-quadratic 0.980, B-structured 0.971,
B-none 0.971, A 0.951, SF 0.931.

**Diagnostics.**
- Clip fractions: B-structured 0.95, B-none 0.92 (optimization-limited at clip 1); B-full 0.56; C-full 0.56; A 0.29.
- Temperatures often reach the grid edge 0.25: with 12 validation roots, calibration is poorly determined. That is
  reflected in test NLL.
- No same-endpoint order pairs exist in the P8c test or validation data (order accuracy N/A).

## 4. Interpretation

- **Supported on fresh roots, pilot scale (12 test roots): generic within-scene coupling.**
  - It is the only route by which these models predicted complementarity (+1). The same was seen in P8a, with
    B-structured, B-none, A and SF at 0.0–0.17 for +1.
  - The arms that have it are the most accurate feasibility predictors (B-full vs B-structured +0.093 accuracy; vs SF
    +0.044; vs A +0.057).
  - CIs overlap, κ denominators are 2 / 3 / 2, and every +1 label is operational, so this is **INCONCLUSIVE-positive**,
    not established.
- **Not supported.**
  - Conditional (oracle-revealed) coupling value on fresh data.
  - Order effects: no decided contrasts.
  - Calibration: every arm is poorly calibrated on test.
- **The decisive executed comparison is P8d** (report 0027).

## 5. Artifacts and accounting

- **Code:** `p8_scenes.py`, `p8_collect.py`, `p8_learn.py`, `p8c_train.py`; `p7_scenes.PREFIX` added (default `p7_`).
- **Evidence:**
  - `runs/p8/collection/*`: plan, construction ledger, static admission, progress, decisions, sealed_test, attempts,
    effects, pools, summary, manifest, `q/` unit records;
  - `runs/p8/c_training/{results.json, rankings.json, guard.json, log.txt}` plus seed-0 checkpoints, with all checkpoint
    hashes in `checkpoint_manifest.json`.

| item | used | cap |
|---|---|---|
| construction + static admission | 279.3 CPU-s | 800 |
| teacher collection | 8,893.1 CPU-s, 9,177 s wall | 12,000 / 24,000 |
| training | 2,879.9 CPU-s, 2,881 s wall | 11,000 / 22,000 |
