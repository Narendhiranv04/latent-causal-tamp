# 0096 — P17-4: frozen prospective cohort, label custody and completed rosters

**Actual result**
- **Rosters completed:** p17test is a new cohort of 174 roots. Every pre-registered roster finished:
  - existential labels on 174 / 174 roots;
  - B execution on 174 / 174;
  - D execution on 90 / 90;
  - the oracle guide on 56 / 56 roots where it is defined.
- **Custody order followed exactly:**
  1. Freeze and push (`f22a444`).
  2. Sealed labels and execution.
  3. Commit and push the sealed-output manifest (`b96870d`).
  4. Unseal, which verified the manifest on origin/main and that no sealed file changed.
  5. Run the oracle guide.
  6. Run the analyses.
- **No outcome inspected early:** no p17test outcome was opened before step 4. Only root keys were counted.

## 1. Cohort and rosters (`runs/p17/data/p17test/plan.json`, `p17_prosp.p_rosters`)

- **Generation:** new seeds (SEED0 = 2026290000). Leakage was checked by root, fingerprint, source trajectory and parent scene; fingerprint duplicates were excluded before the freeze.
- **Family counts:**

| NAT | DENSE | REACH | each of the 8 P13 grammars |
|---|---|---|---|
| 96 | 36 | 18 | 3 |

- **B roster:** all 174 roots.
- **D roster:** every non-NAT root (78) plus the first 12 NAT roots in plan order, as a natural control — 90 in total.

## 2. Frozen before any p17test output existed (`runs/p17/PREREG.json`, sha256:517e9552…)

- **B:**
  - 24 early-stopped checkpoints: 8 arms × 3 seeds, plus the frozen P13 checkpoints;
  - p17calib-only policies (`POLICIES.json`);
  - 22 execution arms, including coupling-off, swapped-threshold, TOP-3 verify-then-next, ALWAYS_EMPTY, random, geometry and VERIFY_FIRST.
- **D:**
  - 3 Dp17 seeds and per-family calibrations;
  - 10 guides plus the oracle after unsealing.
- **Shared:**
  - budgets: sequence `P17_SEQ_BUDGET_V1`, D search 400 / 6 / 16 / 8, node cap 500, n ≤ 4, per object ≤ 2, `P16_FAST` profile;
  - code hashes of 17 files;
  - analysis functions and primary / secondary contrasts;
  - the power statement.
- **Re-checked at unsealing:** every code, checkpoint and policy hash still matched PREREG (0 drift).

## 3. Sealed execution (`runs/p17/data/p17test/sealed_*`)

| roster | workers | roots | CPU-h |
|---|---|---|---|
| existential labels | 9 | 174 | 63.4 |
| B execution (22 arms) | 3 | 174 | 26.2 |
| D execution (10 guides) | 12 | 90 | 55.0 |
| oracle guide (after unsealing) | 6 | 56 | 2.3 |

- **Claims:** atomic per-root claims (`claims_*`), so each root was computed by exactly one worker.
- **Fixed budgets:** per-query budgets were fixed, and no aggregate CPU cap was applied (user authorization).
- **Cost spread:** D roots range from a median of 413 to a maximum of 19,721 CPU-s; REACH roots are the most expensive.
- **No failures:** every sealed worker exited COMPLETED with return code 0.

## 4. Custody record

| step | artifact | hash / commit |
|---|---|---|
| pre-registration | `runs/p17/PREREG.json` | `f22a444` |
| sealed-output manifest | `runs/p17/data/p17test/SEALED_MANIFEST.json` (24 files; labels 174, exec B 174, exec D 90) | sha256:a0c8018e…, commit `b96870d` (local = origin) |
| unsealing | `runs/p17/data/p17test/UNSEALED` | contains the manifest hash; written only after `p17_final.p_unseal` checked origin/main and every file hash |

- **Tests:**
  - `p17_final.p_manifest` refuses while a sealed worker runs or a roster is incomplete;
  - `p_unseal` refuses a changed file;
  - the oracle and the analyses refuse while sealed (`test_custody_manifest_refuses_incomplete_and_unseal_refuses_changed_file`).

## 5. Prospective labels (no model involved)

**Original status by family** (verified / certified / unknown):

| family | verified | certified | unknown |
|---|---|---|---|
| NAT | 55 | 20 | 21 |
| DENSE | 18 | 9 | 9 |
| REACH | 2 | 12 | 4 |

All 24 grammar roots are certified infeasible.

- **Decided originals:** 140 (75 feasible, 65 infeasible); 34 are UNKNOWN, never treated as 0.
- **Sequence labels** (verified / certified / unknown):

| length | verified | certified | unknown |
|---|---|---|---|
| 1 | 451 | 130 | 453 |
| 2 | 644 | 150 | 598 |
| 3 | 319 | 76 | 301 |
| 4 | 206 | 65 | 251 |

## 6. Operational notes (declared)

- **Workers added mid-run:** extra workers were added to the same claim queues during execution, under guarded launches with memory guards. This never changed per-root computation.
- **Analysis adapter:** P17 guide records name the order trace `trace`; the frozen P16 analysis reads `order_trace`. `p17_final._d_sets` passes the identical entries under that name (tested); no decision rule changed.
- **Analyses:**
  - `runs/p17/eval/P17_PROSPECTIVE.json` holds B, D, offline, strata and the matched per-root table.
  - `runs/p17/eval/P17_RETROSPECTIVE.json` holds the retrospective D results.
  - Interpretation is in 0097 (B) and 0098 (D).
