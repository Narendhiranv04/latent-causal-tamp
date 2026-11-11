# 2D target-task dataset: order-dependence audit (read-only)

**Date:** 2026-11-10. **Scope:** read-only aggregation of existing records. No physics, planner, replay, generation, relabelling or training was run, and no dataset file was changed.

## Source and provenance

- **Repository:** `Narendhiranv04/rss-ebm-infeasibility`, branch `yadu/dataset-3d` at `8fe960750b0a2701d76c91d304e0c427cc808d74`, path `gh-yadu-iiith/planar_2d/dataset_bd_classquota/`. The local checkout of this path is byte-identical to that commit (`git diff --quiet`).
- **Read:**
  - `README.md` and `selected.json`;
  - `raw/ledger.jsonl` (13,414 lines);
  - `raw/roots/*.json` (7,218 scene files);
  - the existence of every referenced `raw/witnesses/<xx>/<id>.npz`;
  - the generator and teacher code (`code/bd_2d_plus.py`, `code/dataset-bd/bd_2d.py`, `code/latent-causal-tamp/p16_common.py`).
- **Script:** `approach_b_reuse_audit/order_audit_2d.py` (sha256 `46a961cafa52788e…`), deterministic.
- **Per-scene output:** `approach_b_reuse_audit/order_audit_2d.json` (sha256 `d8008e67f4128189…`). Every root id is kept.
- **Not mixed in:** the 4,620-root Q2 placement-query subset and the 635-root BXY corpus.

## What a recorded outcome means

This comes from the code, not from the README.

- **How a B sequence runs:** each `labels.B` entry comes from `bd_2d.teach → seq(steps) → p16_common.verify_sequence`. The relocations run **on the carried state**: the object cells and the robot configuration after each move. T is then planned **from the robot state reached after the last relocation**.
- **Not connector-valid X:** every outcome below is the **legacy combined target-from-achieved-state outcome**. There is no `q_ref` connector, so none of it is reported as finalized Approach B X.
- **Failure location:** `failed_step` is the index of the failing relocation, or `"target"` if relocations succeeded and T failed.
- **Negative kinds:** `CERTIFIED` is proven infeasible (deterministic geometric checks). `NO_PLAN_FOUND` is budgeted. The teacher's own docstring says "UNKNOWN never = infeasible".
- **Witnesses:** negatives store no witnesses. A successful entry stores one witness per action (relocations + T).
- **`wrong_order`:** it is the minimal repair in **exact reverse order**, with the same objects, the same destinations (`park[o]`) and the same final arrangement. So `minimal` vs `wrong_order` is a valid permutation contrast. No other role re-orders the same assignment:
  - `alternative` uses a different clearing set;
  - `partial`, `redundant+*` and `wrong_destination` change the object set or the destinations.

  I checked this directly: 0 scenes have any other recorded group of the same assignment in several orders.
- **Implied, unrecorded attempts:** while searching for the minimal repair, `teach` tries up to 6 permutations of each clearing set, ordered by distance to T, and stops at the first success. Only that success is stored. When the stored minimal is not the first permutation in that order, the earlier permutations **were attempted and returned y = 0, but their outcome (failed step, kind) is not stored**. They are reported in a separate column and **never counted as evidence**.
- **`independent_moves = true`:** this only certifies that each relocation has a certified edge from the **original** scene (robot at `q0`, everything else in place). It is not a whole-sequence permutation result.

## Classification logic

All categories are mutually exclusive, applied per scene to the minimal repair's assignment.

| Category | Rule |
|---|---|
| A, order-dependent | ≥ 2 recorded orders of the identical assignment, at least one y = 1 and one y = 0 |
| B, order-independent (K2) | both orders recorded and both y = 1 |
| C, partially order-compatible (K3+) | ≥ 2 orders recorded and all y = 1, but fewer than all K! orders |
| D, fully order-independent (K3) | all 6 orders recorded and all y = 1 |
| E, inconclusive | no recorded minimal success, or only one order recorded |
| F, order not applicable | K0 / K1 |
| G, NONE | no repair; split by certification |

## Counts verified

- **Selected scenes:** `selected.json` has 5,000 scenes: K0 1,250 · K1 800 · K2 800 · K3 1,150 · NONE 1,000. That matches the expected distribution.
  - All 5,000 scene files are present.
  - All 5,000 have `verified_K` equal to their selected class.
  - All 5,000 have `independent_moves = true`.
- **Excluded DEPENDENT scenes:** the ledger has 131 `observed = "DEPENDENT"` lines, for 131 unique roots.
  - The scene files give `verified_K` 2 = 107, 3 = 23, 4 = 1, matching the ledger.
  - All 131 files are present, all have `independent_moves = false`, and none overlaps the selected 5,000.
  - All 131 have a target that is infeasible in the original scene (`original.y = 0`).

## Table 1: the selected 5,000 scenes

| K class | Total | Verified order-dependent (A) | Fully verified order-independent (B / D) | Partially order-compatible (C) | Inconclusive (E) | Order not applicable (F / G) |
|---|---:|---:|---:|---:|---:|---:|
| K0 | 1,250 | – | – | – | 0 | 1,250 |
| K1 | 800 | – | – | – | 0 | 800 |
| K2 | 800 | **105** | **695** | 0 | 0 | 0 |
| K3 | 1,150 | **228** | **0** | **922** | 0 | 0 |
| NONE | 1,000 | – | – | – | – | 1,000 |
| **Total** | **5,000** | **333** | **695** | **922** | **0** | **3,050** |

**Kind of failing order in the 333 A scenes:**

| Class | CERTIFIED at a relocation | NO_PLAN_FOUND at a relocation | NO_PLAN_FOUND at the target step |
|---|---:|---:|---:|
| K2 | 24 | 72 | 9 |
| K3 | 38 | 172 | 18 |

**No selected A scene fails at step 0.** All failures are at relocation 1 or 2, or at the target. That is consistent with the generator's per-move independence check. From these records, the cause cannot be split into "the object moved earlier now blocks" versus "the arm starts the step from a different configuration".

## Table 2: the excluded DEPENDENT scenes (not part of the 5,000)

| K class | Existing scenes | Successful complete target-task witness exists | Verified contrasting unsuccessful permutation exists | Fully usable as order-dependent evidence | Missing / incomplete evidence |
|---|---:|---:|---:|---:|---:|
| K2 | 107 | 107 | 107 (44 CERTIFIED, 63 NO_PLAN_FOUND; all at step 0) | **107** | 0 |
| K3 | 23 | 23 | 21 (9 CERTIFIED, 12 NO_PLAN_FOUND; 17 at step 0, 4 at step 1) | **21** | 2 (reverse also succeeded, so no contrast is recorded; category C) |
| K4 | 1 | 1 | 1 (NO_PLAN_FOUND, step 3) | **1** | 0 |
| **Total** | **131** | **131** | **129** | **129** | **2** |

- **Witnesses:** every successful sequence has its full witness set on disk: K + 1 files, 0 missing.
- **Step-0 failures:** 124 of the 129 fail at step 0. Step 0 starts from the true original state (arm at `q0`, original layout). So for these 124, the order dependence comes from the object layout, not from the arm's carried configuration. 49 of the 124 are CERTIFIED.
- **The 2 K3 scenes without a contrast:** `2d-plus2d-w0038-s016` and `2d-plus2d-w0124-s008`.

## Table 3: what existing data alone can provide

**Available scenes** (no selection or split was made):

| Pool | Available |
|---|---:|
| Usable order-dependent (selected A 333 + excluded A 129) | **462**: K2 212 · K3 249 · K4 1 |
|  · of which the failing order is CERTIFIED | 115 (selected 62 + excluded 53) |
|  · of which the failing order is budgeted NO_PLAN_FOUND | 347 |
|  · of which the dependence comes from the object layout (fails at step 0) | 124 (excluded only) |
| Usable order-independent, fully verified (K2, both orders succeed) | **695** |
| Order-compatible but not fully verified (K3, 2 of 6 orders succeed) | 922 selected + 2 excluded = **924** |
| Fully verified order-independent K3 | **0** |
| NONE, certified (construction `none_cover2d`: no repair of ≤ 4 moves among any objects) | **974** |
| NONE, not certified (no repair found within budget) | **26** |
| K0 / K1 | 1,250 / 800 |

**Order-dependent share among K2+ corrective scenes:**
- **All corrective scenes with any ordering evidence:** 462 / (462 + 695 + 924) = **22.2 %**.
- **Verified categories only (A vs B / D):** 462 / (462 + 695) = **39.9 %**.
- **To go higher:** use only a subset of the independent pool. Every dependent-to-independent ratio below is achievable with existing verified scenes and **without duplication**. These are eligibility limits, not a proposed selection.

| Target ratio (dep : indep) | Using all 462 dependent | Using the 115 CERTIFIED-contrast only | Using the 124 step-0 (layout-caused) only |
|---|---|---|---|
| 60 : 40 | 462 + ≤ 308 of 695 verified-independent = 770 | 115 + ≤ 76 = 191 | 124 + ≤ 82 = 206 |
| 70 : 30 | 462 + ≤ 198 = 660 | 115 + ≤ 49 = 164 | 124 + ≤ 53 = 177 |
| 75 : 25 | 462 + ≤ 154 = 616 | 115 + ≤ 38 = 153 | 124 + ≤ 41 = 165 |

**Per-class limit:** the K3 independent side has **no fully verified scenes**. A K3-balanced mix could only use "partially order-compatible" scenes as independents. A fully verified dependent-vs-independent contrast exists for K2 only (212 vs 695).

## Table 4: ordering-evidence coverage

| | Selected K2 | Selected K3 | Excluded K2 | Excluded K3 | Excluded K4 |
|---|---:|---:|---:|---:|---:|
| Denominator (scenes) | 800 | 1,150 | 107 | 23 | 1 |
| Original successful sequence recorded, witnesses complete | 800 | 1,150 | 107 | 23 | 1 |
| Reverse order attempted (recorded) | 800 | 1,150 | 107 | 23 | 1 |
| Reverse order successful | 695 | 922 | 0 | 2 | 0 |
| Reverse failed during relocation | 96 | 210 | 107 | 21 | 1 |
|  · at step 0 (from the original state) | 0 | 0 | 107 | 17 | 0 |
| Reverse failed during the target action | 9 | 18 | 0 | 0 | 0 |
| Reverse failure kind, CERTIFIED / NO_PLAN_FOUND | 24 / 81 | 38 / 190 | 44 / 63 | 9 / 12 | 0 / 1 |
| Other permutations recorded | 0 | 0 | 0 | 0 | 0 |
| Other permutations attempted but outcome not stored (implied by search order) | 57 † | 216 | 73 † | 16 | 0 |
| All permutations evaluated (recorded) | 800 (2 of 2) | 0 (2 of 6 each) | 107 (2 of 2) | 0 (2 of 6) | 0 (2 of 24) |
| Missing or unusable witnesses for successful sequences | 0 | 0 | 0 | 0 | 0 |

**† K2:** the implied attempt is the same reverse order that `wrong_order` later recorded. All 57 and all 73 agree: the recorded reverse failed too.

**K3:** the implied attempts are other permutations, and their outcomes are not stored. In the 216 selected scenes, the recorded reverse failed in 118 and succeeded in 98.

## Verdict

1. **How many of the 5,000 are demonstrably order-dependent?** **333**: 105 K2 and 228 K3.
   - 62 have a CERTIFIED failing order; 271 fail by budgeted NO_PLAN_FOUND, 27 of them at the target step.
   - None fails at step 0, so for these the layout and carried-arm-state causes cannot be separated from the records.
2. **How many are demonstrably order-independent?** **695**, all K2 (both orders succeed).
   - **K3:** 0 are fully verified. 922 are only partially compatible (2 of 6 orders succeed).
   - **The generator flag:** it marks all 1,950 K2/K3 scenes as independent, and whole-sequence records **contradict it in 333**.
3. **How many of the 131 excluded scenes are reusable without new simulation?** **129**: K2 107, K3 21, K4 1.
   - All 129 have complete success witnesses and a recorded failing reverse; 53 are CERTIFIED and 76 NO_PLAN_FOUND.
   - 124 fail at step 0 from the original state.
   - The other 2 (K3) have no recorded contrast.
4. **Is there enough for an order-dependent-majority dataset?** **In counts, yes.** 462 dependent against 695 verified independent supports 60:40, 70:30 or 75:25 subsets with no duplication. Three caveats:
   - only 115 of the dependent scenes rest on a CERTIFIED failing order;
   - every outcome is the legacy combined target-from-achieved-state result, not connector-valid Approach B X;
   - the K3 independent side is not fully verified.
5. **How many unsolvable scenes can be kept?** **1,000 NONE**: 974 certified by construction, 26 budgeted "no repair found".
6. **What is the maximum existing-data-only mix?** For example: 462 dependent + ≤ 308 verified-independent K2 (60:40) + 1,000 NONE + K0 1,250 + K1 800. This is an eligibility limit, not a selection. The evidence still missing is listed below.

## Evidence that would be needed later (not collected)

- **Connector-valid outcomes:** a `q_ref` connector after each relocation sequence, for both orders of each contrast, so that order effects count as Approach B X rather than legacy combined outcomes.
- **Remaining K3 permutations:** the 4 untested orders of each of the 1,150 + 23 K3 assignments. Without them, no K3 scene can be called fully order-independent.
- **The implied, unstored failures:** stored outcomes (failed step, kind) for the earlier permutations, 216 + 16 K3 scenes.
- **Budgeted failures:** certification or re-attempts for the 347 NO_PLAN_FOUND contrast failures, if a proof-level order effect is required. Under the current rule ("no plan found means infeasible") they already count.
- **Cause of later-step failures:** a step-wise replay from `q0` against carried state, to separate layout-caused from arm-state-caused order dependence in the 333 selected A scenes.
