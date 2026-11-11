# 0095 — P17-D1: per-family temporary-target calibration, multi-destination labels, blocker diagnosis

**Actual result**
- **Calibration defect fixed.** The P16 shared-calibration defect is fixed: each D family (D, Dp, Dp16, Dp17) has its own temporary-target calibration. It is fitted on p17calib probes and evaluated on held-out P16-calib probes; no D family trains on either.
- **Dp17.** Dp17 was trained (3 seeds, early-stopped) on P13 parking-lattice items plus P16 / P17 roots with the separately named `MULTI_DEST_LATTICE_V1` labels.
- **Diagnosis.** On p17calib, all four families diagnose the original target about equally well (AUROC 0.956–0.967, blocker F1 0.94–0.98). The new Dp17 is **not** better than the frozen models.
- **Recursion scope.** Temporary-target blocker marginals stay unvalidated (6 masks), so recursion is used for **feasibility only**. `-blk` remains experimental.

## 1. Label protocols (never silently relabelled)

**`PARKING_LATTICE_V1`:** the B catalogue's parked-subset edits (one parking cell per object).

**`MULTI_DEST_LATTICE_V1`** (`p17_d.multi_dest_lattice`):
- A subset S is *sufficient* if **some** admissible assignment of S to its first k = 2 domain slots (distinct cells) makes the original target VERIFIED.
- S is *negative* only if every assignment is CERTIFIED.
- Otherwise S is UNKNOWN.
- Every assignment and its status is recorded.
- This says nothing about whether the relocations themselves are executable (tested: `test_multi_destination_semantics_existential_and_unknown`).

Lattice types on p17calib (51 decided originals):

| type | PARKING | MULTI_DEST |
|---|---|---|
| FEASIBLE_ORIGINAL | 21 | 21 |
| MINIMAL_SETS (mask defined) | 15 | 16 |
| NO_CLEARING_SET_WITHIN_POOL | 6 | 5 |
| INCOMPLETE | 9 | 9 |

10 originals are UNKNOWN. NO_CLEARING and INCOMPLETE never become all-zero masks.

## 2. Dp17 training (`runs/p17/d/runs/`)

- **Data:** 609 train items (203 with proof-grounded masks), 91 validation items (47 masks); λ_B = 2.
- **D_TRAIN_SPLITS** = P16 train / dev + p17train. P16 calib is excluded because it is the held-out calibration evaluation set.

| seed | val NLL | best update |
|---|---|---|
| 0 | 0.322 | 1,060 |
| 1 | 0.281 | 1,200 |
| 2 | 0.323 | 400 |

All three stopped early.

## 3. Original-target diagnosis on p17calib (`runs/p17/d/D_DIAG_P17CALIB.json`; no D family trained on these roots)

| family | AUROC | Brier | blocker F1 (PARKING / MULTI) | exact union (PARKING / MULTI) |
|---|---|---|---|---|
| D (frozen, paired) | 0.967 | 0.088 | 0.980 / 0.982 | 0.933 / 0.938 |
| Dp (frozen) | 0.965 | 0.066 | 0.980 / 0.982 | 0.933 / 0.938 |
| Dp16 | 0.956 | 0.081 | 0.962 / 0.964 | 0.867 / 0.875 |
| Dp17 | 0.960 | 0.078 | 0.941 / 0.945 | 0.800 / 0.812 |

- Union ≠ necessary on 4 masks.
- Alternative minimal sets on 4 masks.
- 15–16 masks is a small denominator.

## 4. Per-family temporary-target calibration (`runs/p17/d/calibration/<family>.json`)

**Probes:**
- one per decided temporary-lattice state: other pool objects parked in every subset, at the original state and after a certified first relocation;
- fit set: 256 probes from p17calib, 19 of them infeasible;
- held-out set: 149 probes from P16 calib, 9 infeasible.

**Form selection:** the calibration form (identity / bias / full Platt with a prior centred on identity) is chosen by root-split 2-fold CV log loss. **Every family selected `bias`.**

| family | bias b | raw feasible / infeasible recall | CV feasible / infeasible recall | held-out feasible / infeasible recall | held-out Brier |
|---|---|---|---|---|---|
| D | 9.41 | 0.38 / 0.16 | 0.89 / 0.42 | 0.95 / 0.44 | 0.065 |
| Dp | 7.22 | 0.49 / 0.16 | 0.89 / 0.47 | 0.96 / 0.44 | 0.056 |
| Dp16 | 4.78 | 0.71 / 0.32 | 0.91 / 0.53 | 0.97 / 0.44 | 0.045 |
| Dp17 | 5.29 | 0.59 / 0.05 | 0.93 / 0.47 | 0.97 / 0.44 | 0.045 |

- Raw models are strongly under-confident about temporary-target feasibility; calibration corrects this.
- Infeasible temporary targets are rare (7 % of probes), and fewer than half are recognized.
- Consequence for recursion: a mover is deferred only when its calibrated feasibility < 0.5, and this happens rarely.

**Temporary-target blocker marginals:** 6 defined masks in total. F1 per family:

| D | Dp | Dp16 | Dp17 |
|---|---|---|---|
| 0.50 | 0.71 | 0.71 | 0.80 |

**Conclusion (contract 6.2 b):** not validated, so blocker recursion is not production. `Dp17-blk` stays an experimental arm.

## 5. Interface and correctness (D-CORRECT items)

- **Arbitrary target rebinding:** `p15_retarget.build_record` rebinds roles, goal, numeric context and DINOv2 features at (state, q, temporary target, destination).
- **Calibration isolation:** `Guide` loads only `calibration/<family>.json` and refuses a missing or foreign file (tested).
- **Search:** reorder-only; never prunes.
- **Other D tests:**
  - union ≠ necessary;
  - NO_CLEARING / INCOMPLETE get no blocker term;
  - conditional vs gated marginals;
  - pairless normalization (P16 tests);
  - multi-destination semantics;
  - Platt-form finiteness and identity recovery (P17 tests).
