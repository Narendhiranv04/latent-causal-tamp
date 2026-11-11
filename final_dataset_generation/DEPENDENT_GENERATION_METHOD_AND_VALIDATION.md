# Dependence-seeking generation: method and validation

**Code:**
- `dep2d.py`: 2D, families `K2_REPARK`, `K3_REPARK`, `K2_CHAIN`, `K3_CHAIN`, `K3_DOUBLE`.
- `dep2d_k3.py`: 2D two-constraint K3 search, `K3_STRONG`.
- `dep3d.py`: 3D, the same families.

All of them reuse the unmodified teachers (`bd_2d.teach` / `bd_3dt.teach` and the exact `seq` path) through `perm2d.py` / `perm3d.py`. Nothing in the robot model, grasp sets, budgets or planner changed.

## Constructions

**Re-parking (`*_REPARK`)** produced almost every accepted scene.
- **What it does:** keep the layout of an existing verified K2/K3 scene, give one mover a different destination, then run every order.
- **Candidate destinations:** the generator's own alternative parking cells first, then free cells within 1–2 cells of another mover.
- **Acceptance:** the scene is kept only if the orders disagree (K2 at 1/2, K3 at 1–5 of 6) **and** a fresh full `teach` confirms the same verified K and the same assignment.
- **The resulting dependence is sequential.** A parked object, or the arm's pose after the first move, changes whether the next pick is reachable.

**Object behind object (`*_CHAIN`, `*_DOUBLE`):** a K1 scene plus 1–2 ordinary obstacles placed next to the original blocker. It was low-yield in both domains.

**Two-constraint K3 search (`K3_STRONG`):** look for two parking cells, each blocking a different mover's pick, to target 1/6 and 2/6 scenes. It was correct but too expensive.

## Rules enforced in code (`assert` before any labelling)

- Every destination is **free in the original scene** and distinct from every other destination and from every initial cell.
- No slot exchange: no destination is another mover's start cell.
- No teleporting or robot reset between moves (`settle` happens once, as in the original teacher).
- The same budget for every order.
- Unattempted or crashed orders are never labels. A scene is accepted only if every order resolved to 0 or 1.

## Pilots (kept: `pilots/`)

| Pilot | Finding | Action |
|---|---|---|
| 2D v1 (42 jobs) | Object-behind-object found a blocking cell in 12 of 42 tries; 2 K2 accepted | Widened the candidate ring; added re-parking |
| 2D v2 | Re-parking accepted 7 scenes where **both** orders succeed (bug) | Deleted those 7 outputs, fixed the check, reran |
| 2D v3 | K2 re-parking 50 % accepted; K3 re-parking strong-only 3 of 23 | K2 scaled up; K3 kept piloting |
| 2D K3 two-constraint (3 versions, 44 jobs) | 4 accepted; usually all orders fail, or more than 2 succeed | Abandoned; K3 accepts any dependent strength (recorded) |
| 3D pilots (gvlab + Blackwell, 72 jobs) | K2 re-parking 60–80 %; K3 re-parking accepts strong scenes on Blackwell; chains rare | 3D K2 and K3 re-parking scaled up |

## Measured yield (all hosts)

| Kind | Domain | Jobs | Accepted | Strength of accepted | CPU-s per accepted |
|---|---|---:|---:|---|---:|
| K2_REPARK | 2D | 784 | 468 | all 1/2 | 561 |
| K2_CHAIN | 2D | 243 | 49 | all 1/2 | 555 |
| K3_REPARK | 2D | 623 | 454 | 1/6: 10 · 2/6: 40 · 3/6: 108 · 4/6: 78 · 5/6: 218 | 520 |
| K3_STRONG / REPARK2 | 2D | 29 | 3 | 1/6: 1 · 2/6: 2 | 1,355–12,223 |
| K3_CHAIN / DOUBLE | 2D | 42 | 0 | – | – |
| K2_REPARK | 3D | 378 | 271 | 1/2 (one 2/2 rejected by selection) | 350–1,000 |
| K2_CHAIN | 3D | 297 | 56 | all 1/2 | 410–1,207 |
| K3_REPARK | 3D | 129 | 97 | 2/6: 23 · 3/6: 49 · 4/6: 5 · 5/6: 20 | 1,650–2,443 |
| K3_CHAIN / DOUBLE | 3D | 24 | 1 | 1/6: 1 | – |

**CPU-seconds per accepted scene, by strength:**
- **2D K3 re-parking:** 1/6 or 2/6 costs about 4,700 CPU-seconds each (50 of 454 accepted), against about 520 for any dependent strength.
- **3D:** 1/6 or 2/6 costs about 9,000.

## Teacher reproduction before any bulk run

| Domain | Host | Sample | Result |
|---|---|---|---|
| 2D | Laptop | 24 + 12 recorded sequences | label, step, kind 100 % |
| 3D | Laptop | 13 recorded sequences | 100 %, including reason strings and final cells |
| 3D | gvlab | 13 recorded sequences | 100 % |
| 3D | Blackwell | 13 recorded sequences | 100 % |

**Standard:** trajectories reproduce numerically but not bit for bit (floating point across CPUs), the same `LABEL_EQUIVALENT` standard as before.
