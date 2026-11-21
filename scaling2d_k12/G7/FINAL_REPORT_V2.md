# 2D K>3 scaling dataset: release_v2 (K4–K12)

`G7/release_v2` (`SCALING2D_K4_12_TEST_V1` format) contains **23 physically verified scenes with a certified minimum K**:

| K | Scenes | Objects | Target/goal pairs | New in v2 |
|---|---|---|---|---|
| 4 | 5 | 16–17 | 5 | – |
| 5 | 5 | 17–18 | 5 | – |
| 6 | 5 | 18–19 | 5 | – |
| 9 | **5** | 20, 20, 25, 25, 25 | (61,63) ×2, (23,39) ×2, (31,55) ×1 | +3 (25 objects) |
| 12 | **3** | 27, 28, 28 | (61,63) ×3 | +3 (27–28 objects) |

The owner closed the extension at K12 = 3 and K9 = 5 ("3 K12 is enough; whatever we have for K9 is enough"). release_v1 (17 scenes, ≤ 20 objects) is unchanged and is contained in v2.

## Acceptance (unchanged from v1)

`CERTIFIED_MIN_K` requires all of the following:
- the witness length equals both sound lower bounds, MINK_STATIC_V1 (declared grammar) and V2 (teacher grammar);
- X = 1 and Y = 1, both independently replayed;
- Y0 = 0.

The G5 audit runs in a fresh process and checks:
- Y0 = 0;
- X = 1 and Y = 1, with replays;
- **Y = 0 after every proper prefix** (1 … K−1);
- the witness hashes reproduce.

Result: **23/23 LABEL_OK.** For K12 that is 14 physical queries per scene, all passing.

**Cross-host numerics.** The 3 new K9 witnesses were found on girish. Re-run on the laptop or gvlab2, every *label* is identical (X = 1, Y = 1, replays true, all 8 prefix Ys = 0), but the trajectory arrays differ in floating point, so the hashes differ. Re-run on girish, the hashes reproduce exactly (3/3 LABEL_OK). G5 is therefore taken on the producing host, and the cross-host label agreement is recorded. Every other scene reproduces bit-for-bit on gvlab2 and the laptop.

## What changed for the extension (scaling-lock amendments 1–7, all dated in `G3/EXPERIMENT_LOCK.json`)

| # | Change | Why |
|---|---|---|
| 1 | Object cap 20 → 25 for new K9/K12 (owner) | K12 needs ≥ 25 objects in columns 3–7 |
| 2 | enigma: K12 engineering test + seeded chains | speed (owner) |
| 3 | witness_v4: first-mover candidates rotate across objects | v3 spent every alternative on one object |
| 4 | witness_v5: failure-directed restarts (parking penalties, mover boosts) | parked discs walled off the arm at relocation 9 |
| 5 | K9 pool frozen at a time snapshot (outcome-blind cutoff); cores moved to K12 | speed |
| 6 | Laptop compute allowed; K12 cap 28 objects; **witness_v6** (all minimal goal sets of the relaxation, seeded parallel searches); **K12 pair cap 3** | only (5,7) and (61,63) can reach K12 in columns 3–7 |
| 7 | **witness_v7**: the endpoint Y check is part of the search | every (5,7) failure verified all 12 relocations, then failed the final target move |

## Coverage (`private/COVERAGE.jsonl`, every candidate)

| K | Candidates | Run | Certified | Selected | Not run |
|---|---|---|---|---|---|
| 9 | 259 (198 at 20 objects + 61 at 25) | 180 | 16 | 5 | 79 (pair filled / stopped by owner) |
| 12 | 67 (novel, random-start, 25–28 objects) | 13 | 7 | 3 | 54 (stopped by owner) |

- **K12 by pair:** (61,63) certified 7 of 8 tried. (5,7) produced 0 of 5 under v6; every failure was the final target move, and the v7 searches were stopped before finishing.
- **K12 order caveat.** Selection follows the locked sha256 order among candidates that *had a verdict* when the owner stopped the search. Some earlier-order (61,63) candidates were never run and are recorded as `NOT_RUN_STOPPED_BY_OWNER`.

## Caveats for evaluation

- The 25–28-object scenes exceed the TRAIN object-count support (≤ 20). The frozen model accepts them (dynamic padding), but results on them are out-of-support in object count.
- K12 has a single target/goal pair, (61,63). Its three layouts differ: occupied-cell Jaccard ≤ 0.85 to each other and to every engineering layout.

## Figures

| File | Contents |
|---|---|
| `G7/overview_v2.png` | All 23 scenes with numbered witness relocations |
| `G7/gifs_physical/K*_*.gif` | **Physical execution** of every scene, drawn only from the teacher's stored witness arrays (the planar arm's joint trajectories): each relocation with the disc carried at the tool point, the connector back to q_ref, then the target move to the goal. Produced by `gif_physical.py` (dump on the producing host with hash check, then render). |
