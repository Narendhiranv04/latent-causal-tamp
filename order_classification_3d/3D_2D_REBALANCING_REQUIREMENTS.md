# 2D and 3D: requirements for a dependent-dominant target-task dataset

**Basis:** existing evidence only (2D six-order audit and the 3D Snapshot A audit, both 2026-11-10). No selection, rebalancing or generation was done.

**Rules for the arithmetic**
- Ratios are enforced within K2 and within K3.
- The excluded K4 scenes never fill a K2/K3 quota.
- All dependence is **legacy**: arm state carried between moves, target attempted from the achieved pose.
- The placement datasets (2D Q2, 3D Q2) are separate and are not counted.

## Where each domain stands

| | 2D (5,000 scenes, final) | 3D (2,500 planned; 1,990 published) |
|---|---|---|
| K2 / K3 quota | 800 / 1,150 (1,950 K2+) | 612 / 612 (1,224 K2+) |
| Published K2+ | 1,950 | 714 (510 not yet uploaded) |
| Dependent / independent (published) | 603 / 1,347 (**30.9 %**) | 240 / 474 (**33.6 %**) |
| K2 dependent / independent | 105 / 695 | 12 / 345 |
| K3 dependent / independent | 498 / 652 | 228 / 129 |
| K3 exactly one order (1/6) | **26** | **0** |
| Excluded dependent, evidence-eligible | K2 107, K3 21 | K2 18, K3 25 |
| of which meet current dataset rules | K2 19, K3 2 (movable-only) | K2 18, K3 25 (fixed-object check not recorded) |
| Strict dependent majority needs | 976 | 613 |
| Final dependent count if the unpublished scenes arrive (a range, not evidence) | – | 240 to 750 (19.6 %–61.3 %) |

## Required replacements and deficits

Columns, per class:
- **required:** dependent scenes needed at the target ratio;
- **existing:** dependent scenes in the published set;
- **excluded added:** distinct excluded dependent scenes of that class;
- **independent to drop:** existing independent scenes that would have to leave;
- **deficit:** dependent scenes still missing after using all existing ones.

### 2D (all scenes published)

| Ratio | K2: required / existing / excluded added / independent to drop / **deficit** | K3: required / existing / excluded added / independent to drop / **deficit** | **Total deficit** |
|---|---|---|---:|
| 60:40 | 480 / 105 / 107 / 375 / **268** | 690 / 498 / 21 / 192 / **171** | **439** |
| 70:30 | 560 / 105 / 107 / 455 / **348** | 805 / 498 / 21 / 307 / **286** | **634** |
| 75:25 | 600 / 105 / 107 / 495 / **388** | 863 / 498 / 21 / 365 / **344** | **732** |

Using only the 21 rule-compatible (movable-only) excluded scenes, the totals rise to **546 / 741 / 839**.

### 3D (published scenes plus excluded; 255 K2 and 255 K3 slots still to be uploaded)

| Ratio | K2: required / existing / excluded added / independent to drop / **deficit** (if all 255 unpublished were dependent) | K3: required / existing / excluded added / independent to drop / **deficit** (if all unpublished dependent) | **Total deficit** |
|---|---|---|---:|
| 60:40 | 368 / 12 / 18 / 101 / **338** (83) | 368 / 228 / 25 / 0 / **115** (0) | **452** |
| 70:30 | 429 / 12 / 18 / 162 / **399** (144) | 429 / 228 / 25 / 0 / **176** (0) | **574** |
| 75:25 | 459 / 12 / 18 / 192 / **429** (174) | 459 / 228 / 25 / 0 / **206** (0) | **635** |

**Answers per domain**

| Question | 2D | 3D |
|---|---|---|
| Current eligible dependent | 603 (+128 excluded) | 240 (+43 excluded) |
| Current eligible independent | 1,347 | 474 |
| Hard 1/6 K3 available | 26 | 0 |
| Feasible from existing data at any of the three ratios? | **No** | **No** |
| Could the pending generation cover it? | n/a (complete) | **Not for K2.** Even if all 255 unpublished K2 were dependent, K2 still lacks 83–174. K3 could only be covered if most unpublished K3 turned out dependent. The teammate's generator keeps the independence rule, so it does not aim for dependence. Expect roughly the current rates: 3 % for K2, 64 % for K3. |
| Targeted generation mathematically necessary? | **Yes**, at all three ratios | **Yes**, at all three ratios (K2 always; K3 unless the pending scenes are unusually dependent) |

## What the two domains show

- **K2 is the bottleneck in both.** Two-move repairs that work from the original scene rarely depend on order: 13 % in 2D, 3 % in 3D. Dependent K2 scenes need a construction that targets dependence, for example a blocker whose parking cell blocks the other blocker's grasp.
- **3D K3 is already dependent-leaning (64 %), but has no 1/6 scenes.** 2D has 26 1/6 scenes but a lower K3 dependent rate (43 %).
- **The excluded DEPENDENT pools are the closest existing source of strong dependence.** In both domains they fail mostly at the first relocation with certified failures, which is layout-caused. But they are small (2D 128, 3D 43), the 2D ones mostly break the movable-only rule, and K3 among them has only 2 of 6 orders tested.

## Evidence still missing before any rebalanced X/Y dataset (not collected)

1. **Connector-valid X (to `q_ref`) for every order record:**
   - 2D: 1,950 K2+ scenes, 8,500 orders.
   - 3D: 1,448 K3 + 2 K2 orders not yet covered by the sidecar.
2. **Independent Y from `q_ref`** at each assignment endpoint, including the 294 3D K2/K3 endpoints with no Y record.
3. **All 6 orders for the excluded K3 scenes** (2D 21, 3D 25) and for any newly generated K3, before claiming 1/6.
4. **New dependent scenes** in the amounts in the deficit tables, generated under the current rules and assigned through the lineage split. Never pick or tune using frozen test outcomes.
