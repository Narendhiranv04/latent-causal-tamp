# P3–P4: sealed predictions and physical verification

## P3 seal (`P3_SEAL.json`, `sealed/`)

- **What was predicted.** 420 locked-roster roots (210 per domain: 50 K1, 50 K2, 50 K3, 30 K0, 30 NONE), from public rows only. Frozen seed-0 checkpoints, main budget 256, L = 64, frozen rule (P2_FREEZE).
- **Every root has a prediction for every arm.** All per-arm files pass `benchmark.validate`: 0 illegal, 0 missing.
- **C1 and C2 pool hashes are identical on all 420 roots.**
- **C0 equals the V3.4 sealed pick on 210 / 210 roots in both domains.** C0's physical labels are therefore the V3.4 cache labels (same key, same teacher runtime); no C0 query was needed.
- **Sealed before any teacher call:** commit `f40c47cf0c` (seal + primary manifest), then `91e87fa423` (secondary manifest).

## P4 queries (`P4_QUERY_MANIFEST*.json`)

Labels were reused only for an exact (root, ordered sequence) key from the V3.4 caches or this study's cache. No retries, no fallback, no adaptive top-k.

| | 2D | 3D |
|---|---|---|
| Primary queries (C1 / C2 picks, K1–K3 + safeguards) | 275 (0 dropped) | 282 (0 dropped) |
| Secondary queries (K1–K3 picks: common gate > C4 > C3, within the remaining cap) | 175 (57 C3 picks dropped by the cap, by hash) | 152 (0 dropped) |
| **Total new queries** | **450 / 450** | **434 / 450** |
| Teacher CPU (worker process time) | **1.75 h / 8** | **3.49 h / 16** |
| Workers / cores | 16 on cores 8–23 (≥ 8 cores free), nice 10 | same |
| Cap stop triggered | no | no |
| Exact-key cache reuse of C1 / C2 picks | 4 / 12 | 3 / 12 |

- **Teacher runtime:** the V3.4 laptop envs `~/abf_v3_laptop/env2d` and `env3d`, called through the unchanged `benchmark.teach` → `evaluate._verify_job`.
- **Witness stores** were redirected to `~/cr_cvae_runs/p4` (`FIN3D_STORE`, `V3OUT`). No historical directory was written.
- **3D profile:** 36 queries on 20 roots took 99 s wall and 31 CPU-s per query; the rest was then dispatched.
- **Storage:** 78 MB in total for the study; `/home` stayed at 1.2–1.3 GB free (the drop from 2.0 GB came from outside this study).

## Label semantics, as applied

- **2D strict:** decided only if the status is VERIFIED / EMPTY / CERTIFIED_INFEASIBLE.
  - All primary-arm 2D UNKNOWNs are `UNKNOWN_PLANNER` or `UNKNOWN_TRANSIT`, stored with value 0.
  - The historical operational convention counts them as failures. All-root verified success is identical under both conventions (UNKNOWN is never a success); only the decided-only rate and the failure counts differ.
- **3D:** every result had `resolution = EVALUATED` (0 UNRESOLVED), so 0 UNKNOWN.
  - **No 3D negative is a certified impossibility.** The decided negatives are `no feasible side grasp` (every grasp pose failed planning or a geometric check within the RRT iteration budget; `fin3d` does not record which), and `EXECUTION_NOT_VERIFIED` (simulated execution check failed); these are the only two negative reasons among the primary-arm picks.
  - They are **teacher-contract, budget-defined failures**, not proofs that no plan exists.
