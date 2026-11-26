# P3: physical verification of sealed picks

- **Sealed first.** The seal and the tiered manifest (`P2_SEAL.json`, `P2_QUERY_MANIFEST.json`, `sealed/`) were pushed in `8114a3dbf2` before any teacher call.
- **Teachers:** the unchanged laptop V3.4 runtimes (`~/abf_v3_laptop/env2d|env3d`, hashes equal to the CR P0 audit), called through `benchmark.teach`. Witness stores went to `~/xyo_runs/p3`. No retry, no feedback into selection.

| | 2D | 3D |
|---|---|---|
| T1 primary J / X / Y picks, K1–K3 (whole roots, sha256 `XYO_Q` order) | 283 | 255 |
| T2 O-B panel permutations (1 of 80 already cached) | 79 | 79 |
| T3 K0 / NONE primary REPAIR picks | 30 | 41 |
| T4 rank-only + XC (capacity left after T1–T3) | 8 of 238 needed | 25 of 215 needed |
| **New ordered requests** (each runs X and Y once: same count of factor calls per factor) | **400 / 400** | **400 / 400** |
| Teacher CPU (worker process time) | **1.06 h / 8** | **2.98 h / 16** |
| 3D profile (first 20 roots) | – | 38 requests, 18 CPU-s each |
| Cap stops | none | none |

- **Unqueried picks.** XC and rank-only picks beyond T4's capacity stay UNQUERIED, and their rates are reported with that status (2D XC 49 % unqueried, 3D 45 %). Every primary J / X / Y pick on K1–K3 is queried.
- **Unresolved results.** 2D UNKNOWNs (`UNKNOWN_PLANNER` / `UNKNOWN_TRANSIT`, stored as 0) remain unresolved under the strict mapping. The historical operational convention gives the same verified-success count.
- **3D negatives** are all `resolution = EVALUATED`: **budget-defined execution or target failures** of the fixed teacher, never proofs of impossibility.
- **Storage:** 19 MB new (`~/xyo_runs`); `/home` stayed at 1.5 GB free.
