# Approach B V3.4: final fresh-cohort benchmark

**Frozen methodology:**
- S-expanded TaskCVAE `scratch_all` s0.
- D-expanded coupled X/Y scorer s0.
- Exhaustive M4.
- Rule `noop_gate 0.5 / eta 0.3`.
- CUDA proposal RNG, on the laptop RTX 5060, with parity checked against the V3.3 records.

**What the evaluation is:**
- An independent fresh cohort (Option B).
- Every root has new seeds, a new identifier and a new lineage, and is disjoint from all historical roots. Disjointness is by root id, seed, sha256 and the GEOM_V1 layout fingerprint.
- Each root gets one committed answer: NOOP, REPAIR or ABSTAIN.
- Predictions were sealed before any teacher call.
- An independent X/Y verification then used the unchanged finalized teachers.
- There was no retry.

## Cohort

| | K0 | K1 | K2 | K3 | NONE | total |
|---|---|---|---|---|---|---|
| 2D quota | 180 | 116 | 116 | 167 | 145 | 724 |
| 2D admitted | 180 | 116 | 116 | **162** | 145 | **719** |
| 3D quota | 93 | 58 | 106 | 76 | 63 | 396 |
| 3D admitted | 93 | 58 | 106 | **75** | 63 | **395** |

- **Status:** **PARTIAL_COHORT**, 1,114 of 1,120 slots. There were 0 disjointness or assertion failures.
- **MISSING slots (6):** `2d-3-019`, `2d-3-024`, `2d-3-063`, `2d-3-119`, `2d-3-138`, `3d-3-023`.
  - Each was capped on its round-2 template under the registered re-target rule.
  - Late fills of declared-MISSING slots from in-flight attempts were **not** admitted. This is conservative: attempt order across runs cannot be audited.
- **Two batches:**
  - **Batch A:** 1,087 roots, frozen at 13:50 IST.
  - **Batch B:** 27 roots.
  - Each batch was sealed separately before its teacher calls. Batch A's selections were locked (1,087 of 1,087 identical selections). Only the cell-level *sensitivity flag* of one batch-A root changed after batch B joined.
- **Amendments:** every one is in `config/final_protocol.yaml`. They cover blackwell recovery, the NONE trim cascade, the re-target rounds RT1–RT9 with genuine-cap criteria, the voided infrastructure re-targets, and the user-approved GEOM_V1 fingerprint with cell-level sensitivity.

## Results (verified X·Y; 0 UNKNOWN in both domains)

| | 2D (719 roots) | 3D (395 roots) |
|---|---|---|
| **Task success, K1–K3** | **51.8% [47.2, 56.1]** (394 roots) | **76.6% [71.1, 82.0]** (239 roots) |
| K1 / K2 / K3 | 67.2 / 69.8 / 27.8 | 67.2 / 78.3 / 81.3 |
| Correct NOOP on K0 | 98.3% | 87.1% |
| Correct ABSTAIN on NONE | 97.2% | 81.0% |
| Repairs on NONE (verified / attempted) | 4 / 4 verified successful repairs | 0 / 12 (all FAIL_Y) |
| Outcomes | 211 SUCCESS · 63 FAIL_X · 120 FAIL_Y · 183 NOOP · 142 ABSTAIN | 193 SUCCESS · 29 FAIL_X · 31 FAIL_Y · 91 NOOP · 51 ABSTAIN |
| Latency p50 / p99 per root (GPU) | 1.42 / 12.8 s | 0.054 / 2.53 s |

**Notes on these outcomes:**
- **2D K3** is the weak point: 45 of 162 succeed, and 91 of the failures are FAIL_Y (wrong endpoint).
- **The 4 verified 2D repairs on NONE roots** confirm that NONE means "not found by the historical teacher scope", not impossible.
- **3D K0:** 10 roots got an unnecessary repair that succeeded; 2 got an unnecessary repair that failed X.

**Sensitivity analysis on the cell-level fingerprint (registered key; roots without any cell-level collision):**

| Domain | Roots | Task success |
|---|---|---|
| 2D | 719 (no cell collisions) | 51.8%, identical |
| 3D | 275 | **71.5% [63.9, 79.2]** on 130 task roots |

## Artifacts

All under `reports/final_v34/`:
- `batchA/`: sealed predictions, results, PRIVATE_INDEX and summaries.
- Re-target records: `RETARGET_*.json`, `CAPPED_*.json`, `RETARGET_VOID.json`.
- `MISSING_SLOTS.txt`.
- `SLOT_PLAN_SUMMARY.json`.

On the host (`~/abf_v34/`):
- `final/`: the PRIVATE_INDEX and COHORT_MANIFEST.
- `batchB/`.
- `final_results/`: the pooled A+B results, `SUMMARY_headline.json` and `SUMMARY_cellclean.json`.

Cross-method comparisons are deliberately **not** part of this report; they are done later on the same frozen cohort.
