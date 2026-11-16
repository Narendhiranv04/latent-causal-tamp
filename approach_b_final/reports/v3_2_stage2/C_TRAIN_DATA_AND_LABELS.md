# V3.2 stage 2 — Phase C: TRAIN-only expanded-candidate physical dataset

## Design (pre-registered in `EXPERIMENT_REGISTRY.json` before any label; commit `b6de8c432b`)

- **Roots.** TRAIN only, stratified by K, in `sha256("v32c|" + root_id)` order (`v32c.roots`).

  | Domain | K1 | K2 | K3 | K0 | NONE | Total |
  |---|---:|---:|---:|---:|---:|---:|
  | 2D | 100 | 100 | 150 | 50 | 75 | 475 |
  | 3D | 70 | 80 | 90 | 30 | 40 | 310 |

  The pilot (2D 8/8/8/4/4, 3D 6/6/6/3/3) is a prefix of the same order.
  - The final sets are 449 2D and 305 3D roots.
  - Roots with no selectable new item were dropped: 26 in 2D (mostly K0 / NONE roots where every candidate was already labelled) and 5 in 3D.
  - No validation, test or confirmation root was ever touched.
- **Pools.** The frozen task cVAE `q2init_all` (seed-0 per-root draws) proposes the top-6 destinations per movable object. Exact exhaustive enumeration then covers every legal ordered K1–K3 sequence (`exhaustive.stream`), each scored by the frozen V3 D seed 0 in fixed GPU chunks. Only a compact, label-blind, seeded summary per root is stored (`v32c.mine_root`).
- **Items.** These were seeded and label-blind (`v32c.items`):
  - the frozen-rule top-1 at M4, M5 and M6;
  - the next 2 highest-p11 candidates;
  - one reservoir draw per p11 band ([0.3, 0.9), [0.1, 0.3), [0, 0.1)) and one uniform draw;
  - every other order of the M6 top-1 assignment and of up to 2 known successful assignments.

  Items whose X label already existed in the V3 training snapshot `abf_v3_e8a496bc66266fca` were dropped: 947 in 2D and 1,294 in 3D.
- **Teachers.** `onpolicy.v3_label` with the unchanged teachers:
  - Y is queried once per canonical endpoint.
  - X is queried where Y = 1, and for a seeded third where Y = 0, so the X | Y = 0 factor keeps observations.
  - X not queried stays MISSING and is marginalised by `xy.py`.
- **Hosts.** Only the four parity-passed teacher hosts were used: laptop, gvlab, girish-laptop and gvlab2 (`A_BASELINE_AND_PARITY.md`).
- **Cross-host determinism.** Mining on Blackwell reproduced the laptop pilot exactly on all 32 2D and 24 3D overlapping roots.

## Labels collected (`C/LABEL_YIELD_BY_STRATUM.txt`, per-host files `C/<dom>_labels_v32c_*.jsonl.gz`)

| Domain | Roots | Candidates | Y = 1 / Y = 0 / unresolved | X = 1 / X = 0 / not queried / unresolved | Z = 1 | Teacher CPU |
|---|---:|---:|---|---|---:|---:|
| 2D | 449 | 4,477 | 1,826 / 2,651 / 0 | 1,577 / 1,114 / 1,786 / 0 | 1,273 | 71,514 s (19.9 CPU-h) |
| 3D | 305 | 2,680 | 1,778 / 902 / 0 | 1,294 / 789 / 597 / 0 | 1,190 | 83,564 s (23.2 CPU-h) |

Per-root teacher CPU had a median of 101 s (p90 340 s) in 2D and 242 s (p90 514 s) in 3D.

**Hard negatives by stratum.** The frozen-rule top-1 at M4 / M5 / M6 on TRAIN is endpoint-infeasible (Y = 0) for:
- 2D: 318 / 677 candidates (47 %);
- 3D: 53 / 359 (15 %).

The next-highest-p11 candidates are Y = 0 for 438 / 897 (2D) and 137 / 609 (3D).

**Order contrasts.** Alternative orders of the top-1 assignment, which share its endpoint, yield 346 X = 0 and 464 X = 1 labels in 2D, and 258 X = 0 and 282 X = 1 in 3D. This is direct ordering supervision.

The low p11 bands are mostly infeasible, as expected: Z = 1 for 22 / 402 (2D) and 14 / 283 (3D) in [0, 0.1).

## Snapshot (`C/SNAPSHOT_abf_v32_fb0eef4f5ff433ee.lock.json`)

`abf_v32_fb0eef4f5ff433ee` is built from `abf_v3_e8a496bc66266fca` plus these labels, using `onpolicy.v3_snapshot` unchanged:

| | 2D | 3D |
|---|---:|---:|
| New Y labels | 3,134 | 1,921 |
| New X labels | 2,689 | 2,081 |
| Rows changed (all TRAIN) | 449 | 305 |
| Validation rows byte-identical to base | 751 | 364 |
| Test rows byte-identical to base | 749 | 370 |

- **Conflicts.** Same-teacher duplicate labels were checked by assertion, and none conflicted.
- **Leakage.** No validation or test label entered training.

Every label file is SHA-256 pinned in the lock file. The snapshot directory is read-only.
