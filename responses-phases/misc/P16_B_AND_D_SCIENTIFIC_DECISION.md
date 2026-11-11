# P16 decision: B and D methodology completion

**Status:** PARTIAL.
- **Base:** `20f7754`.
- **Pre-registration:** `437e771` (sha256 `ba17080d…`), amendment 1 `0c8bd12`.
- **Sealed manifest:** `9389d34`.
- **Manifest:** `runs/p16/P16_FINAL_MANIFEST.json`.

## Retained / removed / deferred / untested

| track | component | decision |
|---|---|---|
| B | DINOv2, keyed identity, order-aware repair unaries, no-op unary, analytic static veto | **retained** |
| B | learned F1, F3, F4, combined F5, learned J | **removed** (λ = 0 / not built) |
| B | higher-order F5q | **deferred** |
| B | generic-only coupling (`cpl`, HO absent) | **new arm; SUPPORTED on one prospective cohort** (replication required before default) |
| D | feasibility head + pairless union-blocker head | **retained** |
| D | paired blocker term | frozen comparator only (no benefit) |
| D | label rule | NO_CLEARING_SET / INCOMPLETE **masked** (fix of P13 semantics) |
| D | recursion | feasibility-only (blocker marginals **not validated**) |
| shared | deterministic provider, alternate transit, multimodal lookup, scene-only API, expanded finite search, independent replay | **retained** |

## Verdicts

| claim | verdict | evidence |
|---|---|---|
| deterministic physics | **SUPPORTED** | identical hashes, 3 seeds + load (0083) |
| B no-op defect fixed vs frozen K-B | **SUPPORTED** | 32 vs 7 / 72, p = 6e-8 (data / architecture confounded) |
| B infeasible repair retained | non-inferior | 25 vs 24 / 40 |
| generic-only coupling (H-B2) | **SUPPORTED (one cohort)** | 0.652 vs 0.509, Holm p = 0.0003 |
| order-on vs order-off on test decisions | NOT SUPPORTED | n.s. |
| learned B vs always-EMPTY | **NEGATIVE** | 0.509–0.652 vs 0.643 |
| D-guided search vs geometry | **UNDERPOWERED** | 0 / 21 discordant; coverage 21 / 48 |
| D effort reduction ≥ 20 % | **NEGATIVE** | +1.7 % |
| D union-blocker diagnosis | **SUPPORTED (descriptive)** | F1 0.981 (16 masks) |
| corrected-label D retrain improves feasibility | NOT SUPPORTED | AUROC 0.805 vs 0.898 |
| temporary-target blocker marginals | **UNDERPOWERED** | 2 labelled lattices |
| oracle bound | **NOT_RUN** | budget |
| 3D | **NOT STARTED** (specification only) | |
