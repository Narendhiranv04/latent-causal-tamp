# Paper-ready tables: structured-energy readouts and execution order

## Table A. Repair selection by readout, same frozen model and same top-4 candidate pool

Locked roster of 50 roots per K per domain. Verified task success (X·Y) as % of K1–K3 roots, strict labels.

| Domain | Readout | K1 | K2 | K3 | K1–K3 | UNKNOWN | Δ vs joint [95 % CI] |
|---|---|---|---|---|---|---|---|
| 2D | Joint p11 (ours) | 66 | 72 | 26 | **54.7** | 24 % | – |
| 2D | Execution only (marginal pX) | 40 | 6 | 0 | 15.3 | 45 % | −39.3 [−47.9, −31.0]† |
| 2D | Target only (pY) | 44 | 50 | 20 | 38.0 | 31 % | −16.7 [−25.6, −7.8]† |
| 3D | Joint p11 (ours) | 66 | 78 | 82 | **75.3** | 0 % | – |
| 3D | Execution only (marginal pX) | 34 | 2 | 2 | 12.7 | 0 % | **−62.7 [−70.4, −54.7]** |
| 3D | Target only (pY) | 40 | 46 | 42 | 42.7 | 0 % | **−32.7 [−41.9, −23.1]** |

- **CIs and tests:** paired whole-family bootstrap; Holm-adjusted randomization p = 0.0002 for every 3D row.
- **† Not established:** UNKNOWN > 20 % in 2D (teacher planner give-ups).
- **Shared across readouts:** pool, no-op gate and admission threshold. Teacher calls at inference: 0.
- **Typical failures:** execution-only picks single-move repairs that execute but leave the target blocked; target-only picks orders that fail to execute.

## Table B. Same final arrangement, different execution order

Exposed VAL groups with all orders labelled and a feasible endpoint (Y = 1); % of groups whose chosen order executes.

| Domain | Objects moved | Groups | Learned order (pX1) | Canonical order | Random order | Any order works | Concordance, mixed groups |
|---|---|---|---|---|---|---|---|
| 2D | 2 | 288 | **92.7** | 84.0 | 83.7 | 97.6 | 0.83 (80 groups) |
| 2D | 3 | 173 | **72.3** | 39.3 | 42.3 | 97.7 | 0.77 (188) |
| 3D | 2 | 242 | **88.8** | 85.1 | 86.8 | 91.7 | 0.71 (24) |
| 3D | 3 | 70 | **75.7** | 55.7 | 49.8 | 100 | 0.77 (111) |

- **Locked-cohort panel** (20 preregistered assignments per domain, descriptive because fewer than 10 groups have mixed order outcomes): the learned order executed in 3D 20 / 20 (canonical 80 %, random 79 %) and in 2D 11 / 11 complete groups (canonical 82 %, random 88 %).
- **pY is identical across orders by construction**, so the ordering signal comes entirely from the execution head.

## Table C. Factor diagnostics (exposed VAL)

AUROC against each head's own label.

| | pY vs Y | marginal pX vs X | pX1 vs X given Y = 1 | pX0 vs X given Y = 0 | p11 vs X·Y |
|---|---|---|---|---|---|
| 2D | 0.933 | 0.805 | 0.769 | 0.828 | 0.883 |
| 3D | 0.939 | 0.828 | 0.787 | 0.840 | 0.884 |
