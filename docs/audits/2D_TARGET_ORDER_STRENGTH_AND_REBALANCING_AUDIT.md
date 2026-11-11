# 2D target-task dataset: order strength and rebalancing feasibility

**Date:** 2026-11-10. **Machine:** the local laptop only. No SSH, no pushes, no new scenes, no dataset writes.

**Scope:** finish the six-permutation evidence for the selected 5,000 scenes, measure how strong each ordering constraint is, and work out exactly how far existing data goes towards a dependent-dominant 5,000-scene X/Y dataset. Nothing was rebalanced or selected.

## Headline

- **All 1,150 K3 scenes now have all 6 orders evaluated.** The dependent / independent counts are unchanged, as they must be: completing orders cannot turn a dependent scene independent or add new dependent scenes.
- **Exactly-one-order K3 scenes: 26** (2.3 % of K3), all from the 228 scenes completed today.
- **Dependent share of K2+ stays 30.9 %** (603 / 1,950).
- **A dependent majority is not reachable from existing data.** Even counting every excluded dependent scene, the best case is 731 / 1,950 = 37.5 %. The 60:40 target alone needs **439 more distinct dependent scenes**, and 70:30 needs 634.
- **Only 143 of the 603 dependent scenes have a certified relocation failure behind their contrast.** The rest rest on budget-limited failures or target-step-only failures, which the legacy carried-arm-state convention may cause.

## 1. Sources and verification

| Item | Value |
|---|---|
| Dataset | `rss-ebm-infeasibility` @ `yadu/dataset-3d` `8fe960750b0a2701d76c91d304e0c427cc808d74`, `planar_2d/dataset_bd_classquota/`; local path identical to the commit |
| Stage-1 artifacts verified unchanged | `per_scene_order_classification.jsonl` `52f94039…`, `order_classification_summary.json` `3ecda254…`, `out/run/results.jsonl` `0d999db9…` |
| Starting counts reproduced | K2 105 / 695, K3 498 / 652, total 603 / 1,347, from the per-scene file |
| Excluded scenes reproduced | 131 DEPENDENT: K2 107, K3 23 (21 with a recorded contrast, 2 without), K4 1 |
| Teacher | `BD2D_TEACHER_V1:DetPhysics(P16_FAST,no-library)`, config hash `90d3eb68e8a42108`, budget QB unchanged, carried robot state, T from the achieved state |
| Environment | laptop, Python 3.13.11, numpy 2.4.6 (`rss3d_env`), `PYTHONDONTWRITEBYTECODE=1` |

**Housekeeping found and fixed:** the stage-1 runs had left 54 `__pycache__/*.pyc` files inside the dataset's `code/` folder. I removed exactly those 54 (all created 12:xx today by my runs), the dataset path is again identical to the commit, and every run since writes no bytecode.

## 2. Stage-2 execution (the 228 remaining K3 scenes)

| Step | Result |
|---|---|
| Reproduction, 12 recorded sequences from these 228 scenes (successes, certified / budgeted relocation failures, target-step failures, both geometries) | **12 / 12** match on label, reason, failing step, failure kind |
| Smoke test | 12 scenes, 48 new orders, 0 errors |
| Full run | 228 scenes, **912 / 912** new orders evaluated (469 succeed, 443 fail), **0** errors, **0** admin caps, **6.22 CPU-h**, 16 workers, 08:32–09:03 UTC |
| Historical records carried over | all 456 (2 per scene), each checked equal to the stored record |
| Output | `order_classification_2d/out/run228/results.jsonl` (new, additive) |

## Table 1: complete 5,000-scene classification

| Class | Total | Dependent | Independent | Unresolved |
|---|---:|---:|---:|---:|
| K0 | 1,250 | N/A | N/A | 0 |
| K1 | 800 | N/A | N/A | 0 |
| K2 | 800 | **105** | **695** | **0** |
| K3 | 1,150 | **498** | **652** | **0** |
| NONE | 1,000 | N/A | N/A | 0 |
| **TOTAL** | **5,000** | **603** | **1,347** | **0** |

Ordering does not apply to 3,050 scenes (K0, K1, NONE). Among the 1,950 K2+ scenes: **603 dependent (30.9 %)**, **1,347 independent (69.1 %)**; no strict dependent majority.

## Table 2: K3 success distribution (all 1,150 fully enumerated)

| Successful orders out of 6 | Scenes | % of K3 | Class |
|---|---:|---:|---|
| 0/6 | 0 | 0.0 | (impossible: the stored minimal always succeeds) |
| 1/6 | **26** | 2.3 | dependent |
| 2/6 | 36 | 3.1 | dependent |
| 3/6 | 113 | 9.8 | dependent |
| 4/6 | 109 | 9.5 | dependent |
| 5/6 | 214 | 18.6 | dependent |
| 6/6 | **652** | 56.7 | independent |
| **Total** | **1,150** | 100 | |

- **The 922 scenes completed earlier** give 3/6: 15 · 4/6: 74 · 5/6: 181 · 6/6: 652, unchanged.
- **The 228 completed today** give 1/6: 26 · 2/6: 36 · 3/6: 98 · 4/6: 35 · 5/6: 33. As expected, none became 6/6.
- **K2** is 1/2 in all 105 dependent scenes and 2/2 in all 695 independent ones.

## 3. Strength of the ordering evidence

Each dependent scene gets one tier from its failing orders:
- **T1, certified relocation:** at least one failing order fails at a relocation step with a geometric certificate (not a search outcome);
- **T2, budget-limited relocation only:** the relocation failures are all `NO_PLAN_FOUND` within the fixed budget;
- **T3, target-step only:** every relocation succeeds in every order; only the final target action fails, from the arm's achieved configuration.

### Table 5: strong physical-order contrasts vs legacy target-step-only contrasts

| | T1 certified relocation | T2 budget-limited relocation | T3 target-step only | Total dependent |
|---|---:|---:|---:|---:|
| K2 | 24 | 72 | 9 | 105 |
| K3 | 119 | 353 | 26 | 498 |
| **Total** | **143** | **425** | **35** | **603** |
| K3 1/6 | 8 | 18 | 0 | 26 |
| K3 2/6 | 9 | 26 | 1 | 36 |
| K3 3/6 | 36 | 74 | 3 | 113 |
| K3 4/6 | 16 | 78 | 15 | 109 |
| K3 5/6 | 50 | 157 | 7 | 214 |

**Failing orders, by step and kind:**

| | Relocation 1 (second move), certified | Relocation 1, budget | Relocation 2 (third move), certified | Relocation 2, budget | Target step (budget) | Total failing orders |
|---|---:|---:|---:|---:|---:|---:|
| K2 | 24 | 72 | – | – | 9 | 105 |
| K3 | 122 | 507 | 49 | 273 | 94 | 1,045 |

- **No failing order fails on the first relocation**, in K2 or K3. That's consistent with the generator's rule that each move works from the original scene. Every failure happens after at least one earlier move, so the arm always starts the failing step from a carried configuration.
- **Certified vs budget-limited, per scene:** 143 scenes have at least one certified failure; 460 rest only on budget-limited failures (`NO_PLAN_FOUND`, including target-step ones).
- **Exactly-one-order K3 (26 scenes):**
  - 8 are T1 (a certified relocation failure among their 5 failing orders) and 18 are T2.
  - In 16, every failing order fails at a relocation, none at the target step.
  - None has all 5 failures certified.

  So these are genuine relocation-order cases under the legacy teacher, but none is a fully certified "only one order is physically possible" case.
- **Possibly confounded by the achieved robot configuration: up to 460 scenes** (T2 + T3). Budget-limited planning from a carried arm pose, and target attempts from the achieved pose, can both change under a fixed-`q_ref` convention. The 143 T1 scenes are the most likely to survive.
- **Needing a `q_ref` connector check and independent Y before final X/Y use: all 1,950 K2+ scenes.** That covers 603 dependent plus 1,347 independent, every permutation record.

### Lineage and composition of dependent vs independent K2+ scenes

Splits from the existing `PLACEMENT_PLAN_V2` lineage split (`launch_ready_2d_v2/split_manifest.json`, lineage union-find):

| | Train dep / indep | Val dep / indep | Test dep / indep | Lineage groups dep / indep (shared) |
|---|---|---|---|---|
| K2 | 68 / 492 | 21 / 99 | 16 / 104 | 97 / 471 (47) |
| K3 | 341 / 464 | 84 / 89 | 73 / 99 | 287 / 303 (156) |

- **K3 1/6 by split:** train 13, val 7, test 6.
- **Dependence is not confined to one mechanism.**
  - K3 `place` scenes are dependent 172 vs independent 162.
  - K3 `mixed`: 300 vs 443. K3 `grasp`: 25 vs 47.
  - K2 `place`: 37 vs 282. K2 `mixed`: 42 vs 233.
- **The median obstacle count matches:** 12 in K3 for both groups; 9 vs 8 in K2.

## 4. The excluded 131 scenes (existing records only)

| | K2 | K3 | K4 |
|---|---:|---:|---:|
| Scenes | 107 | 23 | 1 |
| Dependent, recorded contrast | 107 | 21 | 1 |
| No recorded contrast | 0 | 2 | 0 |
| Orders recorded per scene | 2 (both) | 2 of 6 | 2 of 24 |
| Additional permutations recorded | 0 | 0 | 0 |
| Exactly one **observed** successful order | 107 | 21 | 1 |
| Exactly one **verified across all orders** | 107 (K2 has only 2) | **0** (4 orders never tested) | 0 |
| Certified failing order | 44 | 9 | 0 |
| Fails on the first relocation | 107 | 17 | 0 |
| **Contains immovable structures** (all 5,000 selected scenes are movable-only) | **88** | **19** | 1 |
| Movable-only dependent | **19** | **2** | 0 |
| Identical scene in the selected 5,000 | 0 | 0 | 0 |
| Shares a `parent_family_id` with a selected scene | 42 | 11 | 0 |
| Movable-only and family-disjoint | 11 | 1 | 0 |

Two points matter for reuse:
- **Most excluded dependent scenes use an older generator** (`ROUTE2D_V1`, 109 of 131) **with immovable context structures.** That breaks the current dataset's all-movable rule. Only 21 (K2 19, K3 2) fit that rule.
- **Their failures are strong but differently caused.** Most excluded scenes fail at the first relocation, from the original state. That is layout-caused dependence, unlike the selected scenes, which always fail later.

## 5. Rebalancing arithmetic (fixed class quotas K2 800, K3 1,150; existing data only)

The ratio is enforced within each class, with K2 and K3 computed separately. "Added" means distinct excluded dependent scenes of the same class. The excluded K4 scene is never used.

### Table 3: existing dependent and independent scenes by class

| Class | Quota | Selected dependent | Selected independent | Excluded dependent (evidence-eligible) | of which movable-only | Max dependent share, all excluded | Max share, movable-only |
|---|---:|---:|---:|---:|---:|---:|---:|
| K2 | 800 | 105 | 695 | 107 | 19 | 26.5 % | 15.5 % |
| K3 | 1,150 | 498 | 652 | 21 | 2 | 45.1 % | 43.5 % |
| **K2+K3** | **1,950** | **603** | **1,347** | **128** | **21** | **37.5 %** (731) | **32.0 %** (624) |

### Table 4: required replacements and remaining deficits

Pool A uses every excluded dependent scene; pool B only those that meet the current all-movable rule.

| Ratio | Class | Required dependent / independent | Selected dependent kept | Excluded added (A / B) | Independent to remove | **Deficit (A / B)** |
|---|---|---|---:|---|---:|---|
| 60:40 | K2 | 480 / 320 | 105 | 107 / 19 | 375 | **268 / 356** |
| 60:40 | K3 | 690 / 460 | 498 | 21 / 2 | 192 | **171 / 190** |
| 60:40 | **total** | 1,170 / 780 | 603 | 128 / 21 | 567 | **439 / 546** |
| 70:30 | K2 | 560 / 240 | 105 | 107 / 19 | 455 | **348 / 436** |
| 70:30 | K3 | 805 / 345 | 498 | 21 / 2 | 307 | **286 / 305** |
| 70:30 | **total** | 1,365 / 585 | 603 | 128 / 21 | 762 | **634 / 741** |
| 75:25 | K2 | 600 / 200 | 105 | 107 / 19 | 495 | **388 / 476** |
| 75:25 | K3 | 863 / 287 | 498 | 21 / 2 | 365 | **344 / 363** |
| 75:25 | **total** | 1,463 / 487 | 603 | 128 / 21 | 860 | **732 / 839** |

**None of the three ratios is feasible from existing records.** The deficits are distinct dependent scenes that would have to be generated or found. Duplicating scenes does not count.

**The separate local BXY corpus is not a substitute** (`bxy_order_groups_inventory.json`, reported separately and never merged):
- **Lineage:** 622 roots in the earlier audit's worktree copy, with no shared roots with the class-quota corpus.
- **Development portion:** 120 roots with an X-discordant same-endpoint order group, 208 all-X1 and 141 all-X0.
- **P24 (sealed test, never to be used for selection):** 85 / 86 / 130.
- **Why it can't fill quotas:** these are different scenes, a different construction, and different labels. BXY X is connector-valid (`BXY_X_TEACHER_V1`), but its groups are not K-class target tasks with a verified minimal repair. They could at most seed a separately labelled pool after re-labelling under the class-quota teacher.

## 6. Recommended conditional mixture (proposal only; no selection made)

This is a target for a future 5,000-scene dataset, at 70:30 within K2 and within K3, with K0 / K1 / NONE unchanged.

| Category | Available now (selected) | Desired | Deficit | Validation still needed |
|---|---:|---:|---:|---|
| K3 exactly one order (1/6) | 26 (0 more verified in excluded) | 290 | **264** | all 6 orders; `q_ref` connector for each; independent Y; prefer T1 (certified) |
| K3 other dependent (2/6–5/6) | 472 | 515 | **43** | connector-valid X for failing and succeeding orders; independent Y |
| K3 independent (6/6) | 652 | 345 | 0 (307 to drop) | connector-valid X for all 6 orders |
| K2 dependent | 105 (+107 excluded, 19 movable-only) | 560 | **455** (348 using all excluded) | as above |
| K2 independent | 695 | 240 | 0 (455 to drop) | connector-valid X for both orders |
| K0 / K1 / NONE | 1,250 / 800 / 1,000 | unchanged | 0 | – |

**Why this mixture**
- **Ordered-sequence learning needs contrasts on the same scene and endpoint.** Today 69 % of K2+ scenes give the model nothing to learn about order, because every order works.
- **D vs G comparison.** G is order-invariant: it must give all orders of one assignment the same score.
  - Its classification handicap is largest on 3/6 scenes, where the best constant is right only half the time.
  - Its planning handicap is largest on 1/6 scenes, where picking any order other than the one that works fails 5 times in 6.
  - A mixture spanning 1/6 to 5/6, plus a 6/6 control group, separates "D learns order" from "D just fits harder scenes better".
- **The independent scenes stay as controls.** On 6/6 scenes, D and G should agree.

**Constraints for any future fill**
- Keep the K quotas, the mechanism mix (dependence is spread across `place` / `mixed` / `grasp`), obstacle counts and start strata matched between dependent and independent groups.
- Assign new scenes through the same lineage union-find split, so dependent scenes don't cluster in one split.
- Never select or tune using frozen test (P24) outcomes.
- Prefer scenes whose contrast is T1, which survives a change of arm convention.

## 7. Next-stage experimental requirements (not executed)

1. **Connector-valid X for every permutation record of the 1,950 K2+ scenes:** 1,600 K2 orders and 6,900 K3 orders. Run the same relocations, then a connector to fixed `q_ref`. This tells which of the 603 legacy contrasts (especially 425 T2 and 35 T3) remain X contrasts.
2. **Independent Y from `q_ref`** on each assignment's shared endpoint: 1,950 endpoints, one Y per assignment.
3. **New dependent scenes**, if the ratio target stands: 439 at 60:40 or 634 at 70:30, including about 264 more exactly-one-order K3. Generate under the current movable-only class-quota generator with a dependence-seeking construction, then run the full six-order evaluation.
4. **Optionally, certify budget-limited failures** where proof-level ordering claims are needed.

## 8. Artifacts (all new; `boltzmann_lfd/order_classification_2d/`)

| File | Content | sha256 (prefix) |
|---|---|---|
| `per_scene_six_permutation_outcomes.jsonl` | All 5,000 scenes. For K2/K3: all 2 / 6 permutation records (source historical / new, outcome, failed step, kind, witnesses), class, tier, split, lineage group, mechanism, obstacle count | `0157f5b6…` |
| `k3_success_distribution.json` | Table 2, by source group, plus stage-2 run stats | `43808d8e…` |
| `order_dependence_failure_phase_summary.json` | Tiers, failure steps and kinds, exactly-one-order breakdown, splits, lineage, mechanisms | `b8b7401a…` |
| `rebalancing_availability_and_deficits.json` | Tables 3–4, excluded-scene audit | `603d7fad…` |
| `excluded131_lineage.json` | Duplicate / family / seed / conversion checks for the 131 excluded scenes | `0c3a8bdf…` |
| `bxy_order_groups_inventory.json` | Separate BXY order-group inventory (not merged) | `6b33d538…` |
| `out/run228/results.jsonl` | Stage-2 sidecar, 228 roots | `a8be5c12…` |
| `out/repro2/results.jsonl` | Stage-2 reproduction | `9dcdd659…` |
| `perm2d_stage2.py`, `stage2_analyze.py` | Wrapper and analysis | `47879db3…`, `f7506ccf…` |
