# 2D target-task dataset: complete order classification

**Date:** 2026-11-10. **Machine:** the local laptop only. **Scope:** classify the existing selected 5,000 scenes.

No scene was generated or altered, and no dataset file was written. The only computation was evaluating the previously untested relocation orders of existing scenes with the original teacher.

**Final table** (all 1,950 K2/K3 scenes conclusively classified):

| Class | Total scenes | Order-dependent | Order-independent | Unresolved |
|---|---:|---:|---:|---:|
| K0 | 1,250 | N/A | N/A | 0 |
| K1 | 800 | N/A | N/A | 0 |
| K2 | 800 | **105** | **695** | **0** |
| K3 | 1,150 | **498** | **652** | **0** |
| NONE | 1,000 | N/A | N/A | 0 |
| **TOTAL** | **5,000** | **603** | **1,347** | **0** |

Ordering does not apply to **3,050** scenes (K0 1,250 + K1 800 + NONE 1,000), and these are reported separately. The K2 and K3 rows reconcile: 105 + 695 = 800 and 498 + 652 = 1,150.

## 1. Source and teacher verification

**Source**
- **Dataset:** `Narendhiranv04/rss-ebm-infeasibility`, branch `yadu/dataset-3d` at `8fe960750b0a2701d76c91d304e0c427cc808d74`, path `gh-yadu-iiith/planar_2d/dataset_bd_classquota/`. The local path is byte-identical to that commit.
- **Selected scenes:** `selected.json` has 5,000 unique roots: K0 1,250 · K1 800 · K2 800 · K3 1,150 · NONE 1,000.
  - All 5,000 scene files exist.
  - `verified_K` equals the selected class in all 5,000.
  - The 131 DEPENDENT scenes are outside the 5,000 and are not in this table.

**Teacher identity:** computed in the run environment and equal to the stored value in **all 5,000** selected records:

| Field | Value |
|---|---|
| `config_hash` | `90d3eb68e8a42108` |
| `teacher_version` | `BD2D_TEACHER_V1:DetPhysics(P16_FAST,no-library)` |
| `robot_protocol` | `PLANAR3R_SIDEGRASP_V1:sha256:2d798676…` |

**Robot and budgets**
- Robot: planar 3R arm with side grasp, on an 8 × 8 grid with 0.08 m pitch.
- Per-sequence budget, from `bd_2d.QB`, unchanged: `motion_checks` 150, `online_moves` 8, `goal_plans` 3, `transit_plans` 6.

**Determinism**
- `DetPhysics` decides by node budget, not wall-clock time.
- The planner seeds every query from its key, "independent of how many plans ran before". The task key is the root id, as in `teach`.
- The per-root cache reuses a result only when the computation would run identically.
- Each scene runs with its own geometry implementation: `fastgeom1` where the record says so (881 of the 922), the original geometry otherwise (41).

**Evaluation path:** the same as `bd_2d.teach.seq()`: `bd_core.check_sequence`, then `p16_common.verify_sequence(bd_2d._phys(task, cache), steps)`, then `bd_2d.label`.
- **Robot state is carried between moves;** there is no reset.
- **T is planned from the achieved robot state** after the last relocation.
- **Destinations are never changed.**

**Environment**
- Laptop, x86-64, Python 3.13.11, numpy 2.4.6 (`rss3d_env` venv).
- The vendored `py310_shim/tomllib` is only added on Python < 3.11. That's an environment detail: the teacher code is unchanged.

## 2. Reproducing the original teacher

**Sample:** 24 recorded sequences, chosen deterministically.
- K2 and K3 minimal successes and reverse successes.
- Reverse failures of every type: certified at a relocation, budgeted at a relocation, budgeted at the target step.
- Both geometry implementations.
- 2 excluded DEPENDENT scenes with step-0 failures.

**Result: all 24 match** on label, reason, failed step and negative kind.

**Trajectory witnesses match numerically, not bit for bit:**
- floating-point differences are ≤ 2.2e-15;
- one segment has one extra waypoint;
- all phases and outcomes agree.

That gives the same standard as the approved Blackwell Q2 share: **LABEL_EQUIVALENT_NOT_BITWISE**.

**Independent check inside the run:** 98 of the 922 scenes had permutations that `teach` attempted and failed before finding its stored minimal, but never stored. The new evaluations reproduce **106 of those 106 permutations as failures, with 0 contradictions.**

## 3. Execution

**Workload:** the 922 K3 scenes that had only 2 of 6 orders recorded, both successful.
- Each scene's 6 permutations were matched by exact ordered action keys.
- Only the 4 missing ones were evaluated: **3,688 new complete-sequence evaluations, no duplicates**.

**Runs**
- **Smoke test:** 15 scenes, 2 workers, 60 sequences, 0 errors.
- **Full run:** after a clean stop and resume at the user's request, 28 workers on the 32-thread laptop, leaving 4 free.
- **Totals:** 07:22–08:10 UTC, 18.9 CPU-h.

**Result:** **3,688 / 3,688 evaluated**, with 0 infrastructure errors and 0 admin-cap hits.

**Sidecar** (additive, resumable, never overwriting the source):
- `order_classification_2d/out/run/results.jsonl`: 922 lines, 922 unique roots;
- `out/store/witnesses/`: 11,280 content-addressed trajectories, 62 MB.

**Not evaluated:** the remaining orders of the 228 K3 scenes already proven order-dependent from historical records (912 orders). They aren't needed for the classification.

## 4. Additional numbers

**K2+ scenes: 1,950**

| | Scenes | Share |
|---|---:|---:|
| Order-dependent | 603 | 30.92 % |
| Order-independent | 1,347 | 69.08 % |
| Unresolved | 0 | |

**Order-dependent scenes do not form a strict majority.**

**K3 success counts** (the 922 fully enumerated scenes):

| Orders succeeding | 0/6 | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Scenes | 0 | 0 | 0 | 15 | 74 | 181 | 652 |

- **3/6 to 5/6** (270 scenes) are order-dependent; **6/6** (652) are order-independent.
- **The other 228 K3 scenes** were dependent from historical evidence: 1 success and 1 failure out of 2 recorded orders, with the other 4 not evaluated. So they have no full distribution.

**Permutation records**

| Source | Records |
|---|---:|
| Historical, reused (K2 1,600 + K3 456 + K3 1,844) | 3,900 |
| New, evaluated | 3,688 |
| Not evaluated (not needed) | 912 |

**Failures behind the classification** (historical + new)

| | Total | Of which new |
|---|---:|---:|
| Failures | 707 | 374 |
| Certified | 127 | 65 |
| Budget-limited (`NO_PLAN_FOUND`) | 580 | 309 |
| At a relocation step | 646 | 340 |
| At the target step | 61 | 34 |

**Where the order contrast arises, among dependent scenes**

| | At a relocation step | Only at the target step |
|---|---:|---:|
| K2 | 96 | 9 |
| K3 | 463 | 35 |
| **Total** | **559** | **44** |

The 44 target-only contrasts depend directly on the legacy rule that T starts from the arm's achieved state, so they are the most likely to change under a `q_ref` connector.

**Unresolved:** none.

**NONE:** 974 certified by construction (`none_cover2d`: no repair of ≤ 4 moves exists) and 26 "no repair found" within budget. That still verifies.

## 5. Legacy outcomes are not finalized Approach B X/Y

Every outcome above, historical and new, uses the dataset's **legacy combined convention**: relocations, then T from the robot's achieved state. They are directly comparable with the existing 5,000-scene labels, but they are **not** finalized Approach B supervision. Under the Nov 5 methodology, each permutation record would still need:
- **for X:** a connector to the fixed `q_ref` after its relocations;
- **for Y:** an independent target replay from `q_ref` in the final arrangement.

**That applies to every permutation record:**
- 7,588 evaluated records (3,900 historical + 3,688 new);
- above all, the order contrasts behind the 603 dependent scenes. The 44 target-only contrasts are the most fragile.

## 6. Artifacts (in `boltzmann_lfd/order_classification_2d/`)

| File | Content | sha256 (prefix) |
|---|---|---|
| `per_scene_order_classification.jsonl` | One line per selected scene (5,000). Root id, K, source sha256, geometry. For K2/K3 also: successful original sequence, fixed assignment, all 2 / 6 permutation records with source (historical / new / not_evaluated), outcome, failure kind, failed step and witness ids, plus the final class. NONE rows carry `none_kind`. | `52f94039…` |
| `order_classification_summary.json` | Every number in this report | `3ecda254…` |
| `perm2d.py` | Evaluation harness: pinned teacher, read-only on the dataset | `4c111b93…` |
| `classify.py` | Deterministic classification | `a91bb857…` |
| `out/run/results.jsonl` | Sidecar of the new evaluations | `0d999db9…` |
| `out/repro/results.jsonl` | Reproduction audit | `e96aada1…` |
| `roots_k3_unresolved_922.json` | The evaluated root list | `1d5f6d11…` |
| `repro_sample.json` | The reproduction sample | `5bab4b90…` |
| `out/store/witnesses/` | New trajectories | – |

## 7. Conclusion

**All 5,000 scenes are conclusively classified under the original reproducible teacher:**
- 1,950 K2/K3 scenes as dependent or independent, with 0 unresolved;
- 3,050 as ordering-not-applicable.

**About 31 % of K2+ scenes are order-dependent.** An order-dependent majority cannot come from the existing selected scenes alone. The 129 reusable excluded DEPENDENT scenes from the earlier audit lie outside this table; adding them would give 732 / 2,079 = 35 %.

What would be needed later (not started): connector-valid X and independent Y for the permutation records, and more order-dependent scenes if a dependent-majority dataset is required.
