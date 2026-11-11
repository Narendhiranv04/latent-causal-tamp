# Final 3D target-task dataset (selection V2, published scenes only)

**Status: the PUBLISHED part is complete.** Within the 357 published K2 and 357 published K3 scenes, 70:30 dependent-to-independent is reached in each.

The main dataset is **not complete**: the teammate's 510 remaining K2/K3 scenes are not yet uploaded. The latest check of `yadu/dataset-3d` showed tip `8fe96075`, with no new commits since this afternoon. **Finalized X/Y is not yet measured** for the new scenes.

**Selection manifest:** `FINAL_DATASET_SELECTION_MANIFESTS/3D_SELECTION_V2.json` (sha256 `ebfa33d9…`). K4 is excluded from it and archived separately.

## Table B: 3D, partial (published + validated + not yet uploaded)

| Class | Final quota | Published (selected) | Dependent | Independent | Unresolved | Not yet uploaded |
|---|---:|---:|---:|---:|---:|---:|
| K0 | 511 | 511 | N/A | N/A | 0 | 0 |
| K1 | 357 | 357 | N/A | N/A | 0 | 0 |
| K2 | 612 | 357 | **250** | **107** | 0 | **255** |
| K3 | 612 | 357 | **250** | **107** | 0 | **255** |
| NONE | 408 | 408 | N/A | N/A | 0 | 0 |
| **TOTAL** | **2,500** | **1,990** | **500** | **214** | **0** | **510** |

**Dependent share of published K2+:** 70.0 % (K2 70.0 %, K3 70.0 %), up from 33.6 %.

**Why 70:30.** I picked it to keep about 30 % independent scenes as controls. More is available:
- **Maximum-dependence alternative:** using every generated dependent scene, published K2 could be 12 + 326 dependent and K3 228 + 98.
- **Higher ratios are possible but leave few controls:** about 330 / 357 dependent for K2 and 326 / 357 for K3, with only about 25 and 31 independent controls left.

That choice is yours.

**Reserve (not selected):** 88 dependent K2 and 76 dependent K3.
- They could fill part of the 510 unpublished slots, but only with the teammate's agreement, since those slots belong to his ongoing run.
- 19 of the reserve K2 are built on raw scenes that are **not** in his published selection (distinct layouts).

## Table C: K3 strength

| Successful orders | Original | Final (published) | New selected | New generated (all) |
|---|---:|---:|---:|---:|
| 1/6 | 0 | **1** | 1 | 1 |
| 2/6 | 6 | **27** | 21 | 23 |
| 3/6 | 13 | 13 | 0 | 49 |
| 4/6 | 63 | 63 | 0 | 5 |
| 5/6 | 146 | 146 | 0 | 20 |
| 6/6 | 129 | 107 | – | – |
| **Total** | 357 | 357 | 22 | 98 |

**Why so few new K3 were selected:** at 70:30, only 22 independent K3 scenes can be replaced, because 228 published K3 were already dependent. So the selection took the 22 strongest new ones (1/6 and 2/6). Another 49 at 3/6 are in the reserve.

**K4:** the 9 published K4 scenes are kept outside every main total and no K4 was generated.

## Splits

New scenes inherit their parent's split from the first-cohort lineage split.

| | Train | Val | Test |
|---|---:|---:|---:|
| New K2 | 171 | 46 | 21 |
| New K3 | 18 | 2 | 2 |

**One lineage note:** one selected new K3 scene (a 1/6, built by adding two obstacles to a K1 scene) shares its layout lineage with that K1 parent, which stays selected. Both are in the same split, and they are different classes with different object sets. The other 259 new scenes replace their own parent.

## Integrity

**Every selected new scene has:**
- its parent's hash pinned to Snapshot A (`8fe96075`) and checked before construction;
- a full `bd_3dt.teach` (`BD3DS66_TEACHER_V2`, MuJoCo 3.16.0, RRT 5000, seed 0, no return to ready);
- all orders executed;
- every success trajectory present.

**Teacher reproduction:** 13 / 13 exact on gvlab and 13 / 13 on Blackwell (label, step, kind, reason string, final cells).

**Errors:** 0 across 828 3D jobs.

**Copies:** gvlab outputs were copied to the laptop with a matching aggregate sha256 (`f89de6c7…`); Blackwell's matched `b9f69de2…`.

**Teammate:** his `yadu3d` session, run directory, branch and ledger were never touched.
