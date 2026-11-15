# V3-0: environment and successful-assignment audit

**Contract:** `docs/PLAN_V3_2026-11-15.md` (sha256 `276b592b…`). The archived v2.0 plan is kept as `docs/PLAN_V2_2026-11-12.md`.
**Branch:** `naren/approach-b-v3`, created from `naren/approach-b-final` @ `05998d0f12`.
**Phase type:** read-only audit. No model was trained and no teacher was queried.

## 1. Environment (verified 2026-11-16)

| Item | gvlab2 (execution) |
|---|---|
| GPU | 1× RTX 5090, 32 GiB, idle at check. Jobs use `CUDA_VISIBLE_DEVICES=0` with a ≤ 21 GiB budget. |
| CPU / RAM | 48 cores and 125 GiB. About 14–36 cores are busy with `learned_reap` workers under the shared `long-horizon` uid; these were not touched. V3 uses ≤ 7 teacher workers so that ≥ 5 cores stay free. |
| Disk | `/home` is 98 % full (49 GB free). Large V3 outputs stay small; checkpoints are not duplicated. |
| Envs | `~/abf_v2/env2d` (2D teacher), `~/abf_v2/env3d` (MuJoCo 3.16 teacher), both reused unchanged. A new `~/abf_v3/envgpu` holds torch 2.9.1+cu128 (sm_120). |
| Frozen inputs | `~/abf_v3/frozen` (write-protected): base snapshot `abf_9de85710c2a7103f`, V2 snapshot `abf_v2_7d146b53e4b92fe4`, Q2 features, and V1/V2 P1/P2/P3 checkpoints and result JSON. Copied byte-for-byte from gvlab. Teacher mirror and worktree are symlinks to the verified `~/abf_v2/root` copies. |
| V3 outputs | `~/abf_v3/runs/v3_*`. Nothing under V1/V2 directories is written. |
| Git | gvlab2 has no GitHub credentials of ours, so code is edited and committed in the laptop worktree and rsynced to `~/abf_v3/code`. All computation runs on gvlab2. |

The snapshot lock hashes were re-verified (all `true`, see `v3_0/V3_0_AUDIT.json`).

## 2. Split hygiene

| Check | 2D | 3D |
|---|---|---|
| Parent-family / layout split conflicts (base) | 0 / 0 | 0 / 0 |
| V2 vs base: roots identical; split changes | yes; 0 | yes; 0 |
| V2 rows changed on val/test | 0 | 0 |
| V2 rows changed on TRAIN | 900 | 270 |
| Q2 roots shared with the X/Y roots; split disagreements | 3,303; 0 | 1,226; 0 |
| Q2-only roots: same family split as X/Y; target/goal in raw record | 1,317 / 1,317; all | 239 / 239; all |

Conclusion: the four data streams have no split leakage, and a goal-conditioned Q2 branch is possible, because every Q2 root has its target and goal.

## 3. Successful evidence: roots, assignments and orders (TRAIN)

**Definitions.**
- An *assignment* is the sorted set of (object, destination) pairs, i.e. the endpoint. It is the unit of cVAE supervision.
- An assignment is Z = 1 if its endpoint has Y = 1 and at least one of its orders has X = 1. Each of those X = 1 orders is a separate Boltzmann observation.

| TRAIN | 2D base | 2D V2 | 3D base | 3D V2 |
|---|---:|---:|---:|---:|
| K1 / K2 / K3 roots | 560 / 560 / 805 | same | 251 / 429 / 440 | same |
| Roots with ≥ 1 Z = 1 assignment | 543 / 553 / 785 | 549 / 554 / 786 | 251 / 429 / 440 | same |
| Distinct Z = 1 assignments | 543 / 553 / 785 (**1,881**) | 1,341 / 838 / 788 (**2,967**) | 251 / 431 / 445 (**1,127**) | 519 / 616 / 519 (**1,654**) |
| Roots with ≥ 2 assignments | 0 / 0 / 0 | 218 / 134 / 2 | 0 / 2 / 5 | 81 / 62 / 38 |
| Z = 1 ordered rows | 543 / 799 / 2,081 (3,423) | 4,510 | 251 / 847 / 1,278 (2,376) | 2,903 |
| X = 1 orders per assignment (K2 / K3) | 1.44 / 2.65 | — | 1.97 / 2.87 | — |
| K0 / NONE roots with a Z = 1 assignment | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Notes on the counts:
- The base selected-assignment Z = 1 ordered rows reproduce plan §1.2 exactly: 3,423 in 2D and 2,367 in 3D. The 3D figure above, 2,376, also counts 9 Z = 1 omission rows at shorter-repair roots.
- V2 on-policy additions also reproduce exactly: 2D 7,594 X / 9,661 Y; 3D 2,126 X / 2,493 Y.
- In the base snapshot every moved object has exactly **one** positive destination. Alternatives come only from V2. In 2D V2, 348 objects have 2 positive destinations and 203 have ≥ 3; in 3D V2, the figures are 164 and 184.

**V3 grammar admissibility.** All verified Z = 1 assignments satisfy the V3 static initial-scene grammar, in every split and in both domains:
- each object moves at most once, and the target and fixed objects never move;
- destinations are support cells, distinct from each other, not initially occupied, and not the goal cell;
- length is 1–3.

So the `outside_v3_grammar` ledger is **empty**. This is expected, because both teachers and the V2 search used the same static grammar. 100 % of the positive supervision roots stay usable.

**Legacy K vs finalized evidence (base, TRAIN).**
- 2D: the minimal Z = 1 assignment size equals the legacy K at every root that has one. 44 K1–K3 roots (17 / 7 / 20) have no finalized Z = 1 assignment.
- 3D: 7 roots have a Z = 1 assignment shorter than K (2 at K2, 5 at K3).
- These are the known flagged scenes of `QUALIFIED_TRAINING_EXCEPTION_V1`. They are kept, and stay excluded from the Repair denominator.

**Label resolution (TRAIN).**
- Every X row has its endpoint Y observed; there are no X rows with missing Y.
- 2D base: 3,089 X = 0 / Y = 1, 1,529 X = 1 / Y = 0 and 639 X = 0 / Y = 0 contrasts, besides the 3,423 Z = 1 rows.
- V2 adds 3,396 X = 0 / Y = 0 and 1,865 X = 1 / Y = 0 on-policy rows in 2D.
- V2 coverage endpoints with Y = 0 have no X queried. They stay **missing** and are marginalized, never coerced to 0.

## 4. What the current data can supervise

1. **Task-conditioned cVAE (repair-only):** base one assignment per root gives 1,881 (2D) and 1,120 (3D) TRAIN roots with 1–3 destination targets each. These are 4,004 (2D) and ≈ 2,430 (3D) object-destination targets after deduplicating orders (2D: 543·1 + 553·2 + 785·3).
2. **One assignment per root vs all distinct.** Base data allows the one-assignment variant only, since 0 / 7 roots have alternatives. The all-distinct variant needs V2:
   - 2D: 354 roots with ≥ 2 assignments, almost all at K1 / K2;
   - 3D: 181 roots.
   K3 alternatives are nearly absent (2D: 2 roots; 3D: 38 roots). The one-vs-all comparison therefore mainly tests K1 / K2 diversity. Teammate data would be needed for K3.
3. **Primary assignment rule (frozen now, TRAIN only):** `argmin sha256("v3primary|root_id|assignment_key")` over V3-legal Z = 1 assignments. It is stored per root in the ledger as `primary_assignment_id`.
4. **No positive cVAE targets come from K0 or NONE.** Unchosen objects and unobserved destinations are never negatives.
5. **Q2** gives 162,484 (2D) and 39,152 (3D) labelled TRAIN placement queries (the compiled Q2 features count only completed 0/1 labels). These are goal-blind isolated-placement labels, used for pretraining or the auxiliary branch only.

## 5. Artefacts

- `v3_0/V3_0_AUDIT.json`: all counts by split and K, grammar, legacy K, labels, and Q2.
- `v3_0/Q2_FAMILY_AUDIT.json`.
- `v3_0/assignments_per_root.png`.
- `v3_0/assignment_vs_order_examples.png`: a 2D grid and a 3D shelf, from recorded labels only.
- Ledger on gvlab2 at `~/abf_v3/runs/v3_0/assignments_{2d,3d}.jsonl`. It has one line per root, with assignments, orders, source (base / V2), grammar status and the primary assignment. The sha256 values are in the audit JSON.

Code:
- `contracts.py v3audit` provides `ekey`, `v3_grammar` and `positive_assignments`.
- `figs.py v3_0`.
- `tests/test_v3.py` covers order-free assignment keys, six orders = one assignment, Y = 0 never positive, and all grammar rules. It passes.

## 6. Limitations and next phase

- Ingredient recall of known assignments under the frozen Q2 cVAE at M = 4 needs the direct constructor, so it is measured in V3-1 rather than here.
- Q2 raw (unlabelled or censored) query counts are not in the compiled features. Only completed 0/1 labels are counted.
- **Next: V3-1.** Build the direct one-shot constructor (`construct.py`) with batched scoring and one-result selection on the frozen V2 models.
