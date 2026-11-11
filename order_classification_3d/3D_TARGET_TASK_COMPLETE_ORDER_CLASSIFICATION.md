# 3D target-task dataset: complete order classification (SHELF66V3, Snapshot A)

**Date:** 2026-11-10. **Machine:** the local laptop only. GitHub was used only for read-only fetches. No SSH, no pushes, no new scenes, no source files changed. The teammate's generation process and branch were not touched.

## Headline

- **All published K2/K3 scenes are classified, with 0 unresolved:** K2 12 dependent / 345 independent; K3 228 dependent / 129 independent.
- **Dependent share of published K2+:** 240 / 714 = **33.6 %**.
- **No K3 scene has exactly one working order:** 0 at 1/6. The hardest are 6 scenes at 2/6.
- **The six-order evaluation mattered a lot in 3D.** The stored records showed only 26 dependent K3 scenes; testing the 4 missing orders raised that to 228.
- **Most 3D contrasts are not finalized-X contrasts.** On the orders the existing connector-valid X sidecar covers, only 16 of the 240 dependent scenes are X-discordant.

## 1. Sources

| Item | Value |
|---|---|
| Snapshot A | `Narendhiranv04/rss-ebm-infeasibility` @ `yadu/dataset-3d` **`8fe960750b0a2701d76c91d304e0c427cc808d74`**, path `gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass`. Extracted read-only into `order_classification_3d/src_8fe96075/`, with the scene model at the same commit. |
| Snapshot B | One read-only fetch at 10:04 UTC: branch tip still `8fe96075`. **No new commits, no delta.** |
| `selected.json` (verified) | K0 511 · K1 357 · K2 357 · K3 357 · NONE 408 (main 1,990) + K4 9 = 1,999 unique roots, all files present, every `verified_K` equal to its class. Status: "IN PROGRESS: K2 and K3 hold 357 each of 612". |
| Learning branch (read-only, local) | `naren/approachb-3d-learning` @ `4d2d3dbf`. Finalized X/Y sidecar `BD3DS66_XY_SIDECAR_V1` and the first-cohort pin / split. |
| Scene identity | All 1,582 selected K0–K3 roots are **byte-identical** to the first-cohort pin the X/Y sidecar was built on |

## 2. Teacher and reproduction

**Teacher:** `BD3DS66_TEACHER_V2`, unmodified.
- Shelf scene, xArm7 (MuJoCo Menagerie copy in `shelf_scene_6x6`).
- Fingers pre-shaped in every check; first feasible level grasp in the scene's order; RRT-Connect with max 5,000 iterations, seed 0, no wall-clock limit.
- Executed with `run_plan` in MuJoCo.
- A step counts only if the object ends in its cell, upright within 1 cm, with no other object displaced.
- No-overpass and arm ceiling come from the scene.
- **No return to the ready pose between moves.** The environment is reset once to the initial cells; the arm state carries across relocations and into the target action.

`perm3d.py` replicates `bd_3dt.teach.seq()` line for line, using the module's own `query`, `label`, `witness`, `settle` and `build`.

**Environment:** Python 3.13.11, **MuJoCo 3.16.0, numpy 2.2.6** (the pinned versions, installed from PyPI into an isolated venv with your approval), `MUJOCO_GL=disable`.

**Reproduction:** 13 stored sequences, both minimal and reverse orders. They cover successes, execution failures (`EXECUTION_NOT_VERIFIED`), budgeted and certified relocation failures, and certified target-step failures, from lap, srv and srv3 roots.
- **13 / 13 match exactly:** label, failing step, failure kind, the full reason string (including end cell and z-error) and the final object cells.
- Trajectory witnesses agree numerically but not bit for bit (label-equivalent), as in 2D.

## 3. Execution

| | Value |
|---|---|
| K2 | No evaluation needed: both orders already recorded for all 357 scenes, and `wrong_order` is the exact reverse of the minimal assignment |
| K3 | 357 scenes × 4 missing orders = **1,428 new evaluations**: smoke 12 scenes (4 workers), then 16 workers, then 28 workers (clean stop and resume) |
| Result | **1,428 / 1,428 evaluated, 0 errors, 0 admin caps, 0 unresolved** |
| Historical records reused | 1,428 (K2 714 + K3 714) |
| CPU | 23.4 CPU-h (new evaluations), 09:08–10:04 UTC |
| Sidecar | `out/run/results.jsonl` (357 roots, unique); new witnesses in `out/store/witnesses/` |

## Table 1: currently published 3D scenes (Snapshot A = latest)

| Class | Total | Order-dependent | Order-independent | Unresolved |
|---|---:|---:|---:|---:|
| K0 | 511 | N/A | N/A | 0 |
| K1 | 357 | N/A | N/A | 0 |
| K2 | 357 | **12** | **345** | **0** |
| K3 | 357 | **228** | **129** | **0** |
| NONE | 408 | N/A | N/A | 0 |
| **MAIN TOTAL** | **1,990** | **240** | **474** | **0** |

Ordering does not apply to 1,276 scenes (K0, K1, NONE). K4: 9 scenes, reported separately in §6.

## Table 2: cumulative dataset against the final quota (latest verified commit `8fe96075`)

| Class | Published | Final quota | Dependent | Independent | Unresolved | Not yet uploaded |
|---|---:|---:|---:|---:|---:|---:|
| K0 | 511 | 511 | N/A | N/A | 0 | 0 |
| K1 | 357 | 357 | N/A | N/A | 0 | 0 |
| K2 | 357 | 612 | 12 | 345 | 0 | **255** |
| K3 | 357 | 612 | 228 | 129 | 0 | **255** |
| NONE | 408 | 408 | N/A | N/A | 0 | 0 |
| **MAIN TOTAL** | **1,990** | **2,500** | **240** | **474** | **0** | **510** |

## Table 3: K3 successful-permutation distribution (Snapshot A; cumulative is identical)

| Successful orders | Scenes | % |
|---|---:|---:|
| 1/6 | **0** | 0.0 |
| 2/6 | 6 | 1.7 |
| 3/6 | 13 | 3.6 |
| 4/6 | 63 | 17.6 |
| 5/6 | 146 | 40.9 |
| 6/6 | 129 | 36.1 |
| Unresolved | 0 | |
| **Total** | **357** | 100 |

**K2:** 12 at 1/2 and 345 at 2/2.

## Table 4: failure mechanisms (the 347 failing orders behind the 240 dependent scenes)

**By failure kind:**
- 169 certified (every grasp fails a deterministic geometric check);
- 125 budget-limited `NO_PLAN_FOUND`;
- 53 execution failures (51 `EXECUTION_NOT_VERIFIED`, where the planned move ran in MuJoCo but the object ended in the wrong cell, tilted, or displaced a neighbour; 2 `GRASP_FAILED`).

| Where the order fails | Certified | Budget-limited | Execution | Total |
|---|---:|---:|---:|---:|
| First relocation (accessibility from the start state) | 0 | 2 | 18 | 20 |
| Later relocation (accessibility after earlier moves) | 164 | 119 | 35 | 318 |
| Target step (from the achieved arm configuration) | 5 | 4 | 0 | 9 |

**Per scene, the strongest failure behind each contrast:**

| | T1 certified relocation | T2 budget-limited relocation | T2E execution failure at a relocation | T3 target-step only |
|---|---:|---:|---:|---:|
| K2 | 0 | 1 | 11 | 0 |
| K3 | 136 | 72 | 17 | 3 |

- **First-relocation failures** occur in 2 K2 and 9 K3 dependent scenes, almost all execution failures. The order changes which object goes first, so the start state for that object differs.
- **K2 dependence is almost entirely execution failures** (11 of 12). The scene construction guarantees each move plans from the original scene and with the others parked, so only execution can differ.
- **Final robot configuration:** every contrast is under the carried-arm convention. A different order leaves the arm in a different pose before each later move and before the target action. The 9 target-step failures and the budget-limited later failures are the ones this convention can confound.

**Finalized-X evidence (existing sidecar only; no new connector runs):**

| | Final X discordant on the same assignment | Final X = 1 for all measured orders | Final X not measured |
|---|---:|---:|---:|
| K2 dependent (12) | **10** | 2 | 0 |
| K2 independent (345) | 3 | 342 | 0 |
| K3 dependent (228) | **6** | 222 | 0 |
| K3 independent (129) | 6 | 123 | 0 |

- **Coverage:** the sidecar measures connector-valid X only for the minimal and reverse orders (2 of 6 in K3).
  - 1,448 K3 orders and 2 K2 orders still lack a finalized-X measurement.
  - 294 K2/K3 endpoints have no Y record (K2 142, K3 152).
- **Per order, legacy outcome vs finalized X:**
  - K2: 699 agree as success, 10 agree as failure, and 3 legacy successes are X = 0.
  - K3: 679 agree as success and 3 agree as failure; 9 legacy successes are X = 0 and 3 legacy failures are X = 1.
- **Reading:** legacy order dependence and finalized-X dependence overlap only partly. **No legacy dependent label is promoted to an Approach B X label here.**

## 5. Source integrity

- **Missing witness files:** 1,070 of the 7,491 witness files referenced by selected K2/K3 B records are **absent at this commit**.
  - They affect 93 K3 scenes (87 `srv3`, 6 `lap3`), whose historical minimal / reverse trajectories can't be inspected.
  - Their labels are present and consistent; the `srv3` roots in the reproduction sample matched exactly.
  - Their classification uses the 2 historical labels plus 4 new evaluations, which have fresh witnesses.
- **K4:** 3 of the 9 have no witness files for their minimal sequence.
- **No other violations:** no duplicate roots, no class mismatches, no missing root files.

## 6. K4 and the excluded DEPENDENT scenes (existing records only)

| | K2 excluded | K3 excluded | K4 published (9) |
|---|---:|---:|---:|
| Roots (unique) | 19 | 25 | 9 (6 of them are also the raw ledger's 6 K4 DEPENDENT lines; counted once) |
| Successful correction recorded | 19 | 25 | 9 |
| Minimal witness files present | 19 | 25 | 6 |
| Reverse order recorded | 19 | 25 | 9 |
| Reverse failed (certified / budget) | 18 (11 / 7) | 25 (24 / 1) | 9 (7 / 2) |
| Reverse succeeded (no recorded contrast) | 1 | 0 | 0 |
| Reverse fails on the first relocation | 7 | 18 | – |
| In the X/Y cohort pin, split or sidecar | 0 | 0 | 0 |

**Reconciling with the earlier count:** the Nov 8 reuse audit counted 75 DEPENDENT roots (K2 28, K3 40, K4 7) in an earlier, pre-commit state of `raw/`. At `8fe96075` the raw ledger and root files hold exactly **50** (K2 19, K3 25, K4 6), and the other 25 roots aren't in this commit.

**Reusable for a future dependent-rich dataset:** 18 K2 + 25 K3 have a recorded failing reverse, a successful correction and present witnesses. They need:
- a split assignment, since they're outside the cohort split;
- the fixed-object check, whose status isn't recorded for them;
- the full 6-order evaluation for K3. Only 2 orders are recorded, so a "1/6" claim is not possible yet.

## 7. Split provenance (first-cohort lineage split)

| | Train dep / indep | Val dep / indep | Test dep / indep |
|---|---|---|---|
| K2 | 8 / 238 | 2 / 65 | 2 / 42 |
| K3 | 168 / 97 | 23 / 17 | 37 / 15 |

## 8. Deliverables (`boltzmann_lfd/order_classification_3d/`)

| File | sha256 (prefix) |
|---|---|
| `3D_ORDER_CLASSIFICATION_PER_SCENE.jsonl`: 1,999 roots. Commit and sha256, K, assignments, every permutation outcome (source, kind, step), class, tier, finalized-X coverage, split, witness status | `9fcd3b6c…` |
| `3D_K3_PERMUTATION_DISTRIBUTION.json` | `6e7e56b2…` |
| `3D_SOURCE_SNAPSHOT_MANIFEST.json`: Snapshot A roots and hashes, Snapshot B check, environment, integrity | `68c676cd…` |
| `3D_ORDER_AUDIT_SUMMARY.json` | `07e21b38…` |
| `3D_2D_REBALANCING_REQUIREMENTS.json` / `.md` | `9cb8e0b1…` |
| `out/run/results.jsonl` (sidecar), `out/repro/results.jsonl` | `f5ce2378…`, `d7627ab3…` |
| `perm3d.py`, `analyze3d.py`, `rebalance_3d2d.py` | `3879b41e…`, `19dedffa…`, `427b8b32…` |

No background process or watcher of mine remains running.
