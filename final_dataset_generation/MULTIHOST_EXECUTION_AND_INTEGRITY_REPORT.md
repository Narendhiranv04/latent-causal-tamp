# Multi-host execution and integrity

## Table E: machine utilization (2026-11-10 16:10 to 2026-11-11 00:45 IST)

| | Laptop | gvlab | Blackwell |
|---|---|---|---|
| Workers / affinity | 2D: 27 workers on CPUs 0–26, later 20 on 0–19. 3D: 20 on 0–19, then 7 on 0–6 | 20 workers on CPUs 0–19 (4 left free), `nice 5` | 16 workers on CPUs 8–23, then 8 on 16–23, then 5 on 19–23 |
| Jobs (scene constructions) | 1,721 (2D) + 33 (3D) | 744 | 51 |
| Accepted dependent K2 | 517 (2D) + 19 (3D) | 287 | 20 |
| Accepted dependent K3 | 457 (2D) | 93 | 5 |
| CPU-hours | 150.8 + 3.4 | 146.9 | 4.0 |
| Peak memory | about 370 MB per worker; RAM available never below 6 GB; no swap | 62 GB host, under 15 GB used | under 3 GB of 125 GB |
| Peak temperature | 98 °C (CPU) | 69 °C | 96 °C |
| Execution errors | 3 (2D; unresolved, not labels) | 0 | 0 |
| Resource-guard stops | 3 thermal (2D K2 at 960 / 983 jobs; 3D twice). Each was clean and resumed | 0 | 3 thermal, then retired at the user's request |
| Artifacts | `d2/`, `d3_laptop/` | `d3_gvlab/` (copied; sha256 `f89de6c7…`) | `d3_blackwell/` (copied; sha256 `b9f69de2…`) |

## Coordination

- **Blackwell:** it ran with sajid's jobs present. Its thermal guard stopped it 3 times at 95–96 °C. At your request its remaining K2 queue (289 jobs) moved to gvlab, and the laptop took extra 3D work when it was free.
- **Separate namespaces:** `D2_LOCAL_*`, `D3_GVLAB_*`, `D3_BLACKWELL_*`, `D3_LAPTOP_*`. Per-host parent lists were disjoint, and handoffs used each host's own ledger to skip finished jobs.
- **No duplicates:** 0 duplicate root ids across all stores (checked in `select_final.py`).
- **Never touched:**
  - the teammate's `yadu3d` session, watchdog, run directory, ledger and branch;
  - other users' processes (never paused, reniced or killed);
  - the source datasets: read-only copies were pinned by hash, and stray bytecode was disabled.
- **Laptop shortfall:** 5 of its 38 raw-K2 3D jobs did not run, after the last thermal stop. They're optional reserve work.

## Integrity checks (all passed)

- **Selections:** quotas exact (2D 5,000; 3D published 1,990), unique roots, every K2/K3 row has a split, and no selected new scene's parent is also selected. The one exception is a K1 parent kept beside its K3 child, explained in the 3D report.
- **Every selected new scene:** parent hash at the source commit, fresh full `teach` with matching verified K, all orders evaluated with outcomes, and every success witness file present.
- **Checksums:** `FINAL_DATASET_SELECTION_MANIFESTS/SHA256SUMS` and `FINAL_PERMUTATION_OUTCOMES/SHA256SUMS`.
