# Final 2D target-task dataset (selection V2)

**Status: COMPLETE for the legacy target-task labels.** The 60:40 dependent-to-independent ratio is reached within both K2 and K3, with exact class quotas and no duplicate layouts. **Finalized X/Y is not yet measured** for the new scenes (see `FINAL_XY_EVIDENCE_COVERAGE.md`).

**Selection manifest:** `FINAL_DATASET_SELECTION_MANIFESTS/2D_SELECTION_V2.json` (sha256 `7be7e689…`). The original 5,000-scene selection is untouched and stays the archival snapshot.

## Table A: 2D final dataset

| Class | Total | Dependent | Independent | Unresolved |
|---|---:|---:|---:|---:|
| K0 | 1,250 | N/A | N/A | 0 |
| K1 | 800 | N/A | N/A | 0 |
| K2 | 800 | **480** | **320** | 0 |
| K3 | 1,150 | **690** | **460** | 0 |
| NONE | 1,000 | N/A | N/A | 0 |
| **TOTAL** | **5,000** | **1,170** | **780** | **0** |

**Dependent share:** 60.0 % of K2+ overall, 60.0 % in K2, 60.0 % in K3. It was 30.9 % before.

## Table C: K3 strength (final selection)

| Successful orders | Original selection | Final selection | New scenes selected | New scenes generated (all) |
|---|---:|---:|---:|---:|
| 1/6 | 26 | **37** | 11 | 11 |
| 2/6 | 36 | **79** | 43 | 43 |
| 3/6 | 113 | **221** | 108 | 108 |
| 4/6 | 109 | **139** | 30 | 78 |
| 5/6 | 214 | **214** | 0 | 218 |
| 6/6 | 652 | **460** | – | – |
| **Total** | 1,150 | **1,150** | 192 | 458 |

**Against your preferred strength mix** (40 / 20 / 15 / 15 / 10 % of dependent K3 for 1/6 … 5/6), the final dependent K3 split is 5 / 11 / 32 / 20 / 31 %. That isn't the requested mix.
- **The new scenes are already as strong as possible:** every new 1/6 and 2/6 scene found is in the selection, and the rest were picked strongest first.
- **Why it can't go further:** 1/6 and 2/6 scenes are rare under this teacher (12 % of accepted new K3). The search built to target them (two blocking constraints) cost about 12,000 CPU-seconds per accepted scene, against about 520 for plain re-parking (`DEPENDENT_GENERATION_METHOD_AND_VALIDATION.md`).

## What changed

- **375 independent K2 and 192 independent K3 scenes left the selection.**
  - Each was replaced by a new dependent scene built **on the same layout**, with one mover's destination changed (re-parking).
  - A parent and its child are never both selected.
  - The removed scenes are still archived; nothing was deleted.
- **Splits:** each new scene inherits its parent's split from the existing lineage split (`PLACEMENT_PLAN_V2`).

  | | Train | Val | Test |
  |---|---:|---:|---:|
  | New K2 | 256 | 60 | 59 |
  | New K3 | 137 | 30 | 25 |

  No root moved between splits, and no test outcome was used for any choice.
- **Reserve:** 142 dependent K2 and 266 dependent K3 were generated beyond what 60:40 needs. They are kept as a reserve, not selected.

## Integrity

**Every selected new scene has:**
- the parent's sha256 at the source commit;
- verified K equal to its class, from a full `bd_2d.teach` run;
- **all orders physically evaluated** (2 for K2, 6 for K3), each with its outcome;
- every success trajectory present on disk.

**Duplicates and lineage:** no duplicate root ids; no selected new scene whose parent is also selected; every K2/K3 row has a split.

**Errors:** 3 jobs out of 1,721 hit an infrastructure error. All are logged as unresolved, none produced a label, and none is selected.

**Teacher:** the unmodified `BD2D_TEACHER_V1` (config hash `90d3eb68…`) with the fixed QB budget, carried robot state and target planned from the achieved pose.
