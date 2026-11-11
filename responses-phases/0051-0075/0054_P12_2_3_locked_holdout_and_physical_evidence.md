# 0054 — P12-2 / P12-3: locked novel holdout and its physical evidence

**Actual result.**
- **Gates:** `runs/p12/P12_2_GATE.json` → **PASS**; `runs/p12/P12_3_GATE.json` → **PASS**.
- **The lock** (`runs/p12/PREREG.json`, `sha256:29921369…`), pushed in commit **`caa49df`** before any label:
  - 80 new independent roots: 40 X_SWEEP_GATE and 40 Y_BOTTLENECK, seeds 2026140001–080, 4 batches of 20;
  - 1,840 frozen queries;
  - frozen predictions from all 33 frozen checkpoints plus D (`PREDICTIONS_FROZEN.json`, `sha256:90028569…`), with **0 physical calls** and **no coverage failures**.
- **Labels:** all 80 roots were adjudicated (teacher 26,025 / 40,000 CPU-s). The labels were hash-committed (`LABELS_MANIFEST.json`, commit `a2d7833`) **before** unsealing.
- **Primary cohort:** **65** proof-grounded four-tuples (original, A, B, A+B all VERIFIED or CERTIFIED). By κ class: **κ = 0: 59, κ = +1: 4, κ = −1: 2**. This matches the κ = 0 dominance disclosed before the lock (0053).

## 1. Construction (P12_FAMILIES_V1_1, sound prescreens; `SCENE_MANIFEST.json`)

- **Attempts:** 776 across the 4 batches. Every rejection is ledgered (prescreen failures, layouts, start collisions, duplicates).
- **Dedup:** against every P10a / P10b / P11 / P12-dev geometry and fingerprint.
- **Selection:** none by model output or teacher label. The benchmark is **conditional on the sound prescreen**: every original is certifiably obstructed.

## 2. Physical outcomes (1,840 queries; `runs/p12/p12_3/YIELD.json`)

| status | X_SWEEP_GATE | Y_BOTTLENECK | total |
|---|---|---|---|
| VERIFIED | 366 | 569 | 935 |
| CERTIFIED | 272 | 296 | 568 |
| BUDGET (operational) | 138 | 33 | 171 |
| UNKNOWN | 111 | 8 | 119 |
| NOT_RUN (root CPU cap) | 33 | 14 | 47 |

- **Certificates:** LINK0_SECTOR_PICK 272, TARGET_PICK 290, ORDER_FIRST_ACTION 6. All are pick-side; there are no place-side proofs.
- **Repair length:** the shortest VERIFIED catalogue repair is 1 move on 64 roots, 2 on 11 and 3 on 1; 4 roots have no verified repair. Minimality is catalogue-relative only. These families are hard to start but mostly **one-move repairable**; there is no 4-move witness.
- **Teacher CPU per root:** mean 292, median 169, p90 798.
- **Evidence:** raw unit outputs are under `runs/p12/holdout/batch*/q/`; the sealed per-root ledgers are under `batch*/sealed/` and are committed with this report.

**Figure:** `visualizations/p12/P12_kappa_ground_truth.png` shows real holdout four-tuples for κ = +1 (X sweep gates: both single edits sector-CERTIFIED, A+B VERIFIED), κ = 0 and κ = −1 (Y bottleneck). Edits are labelled HYPOTHETICAL.
