# R7.1: dataset audit and consolidation

| Dataset | Role | Notes |
|---|---|---|
| Original K ≤ 3 TRAIN (expanded snapshot `abf_v32_fb0eef4f5ff433ee`) and VAL (`abf_9de85710c2a7103f`) | Stage A / B training and selection | Training uses **TEST-free copies**: lines whose split is `test` are dropped before parsing (2D 4,251 rows = 3,500 train + 751 val; 3D 2,130 = 1,766 + 364). Historical TEST was never read by any R7–R9 model |
| Strict additional local supervision | Stage C | KGT3 P2, R3.1 (3D), R4.3/R4.4, R5.1. Positives must be replayed and negatives certified. Unresolved, budget-relative and operational outcomes are never converted. All supervised queries have ≤ 3 actions. Prefix length, provenance and dependency annotations are not features. Byte-identical rebuild of the R5 data audit (`xl/data_*.json`) |
| Local TRAIN / VAL split | Stage C selection | Family-disjoint (`sha256('R5.1-split'|fam)`, asserted). 3D: 269 TRAIN / 26 VAL families. 2D: 136 / 101 (+ KGT3 GATE families as VAL) |
| V3.4 cohort (1,114 roots: 2D 719, 3D 395) | R8A independent K ≤ 3 evaluation | Unchanged. Identified as V3.4 Option B, distinct from the protected TEST and release_v2 sets. Exposure: the production model's predictions and 1,183 teacher answers existed before R8 and seeded the shared verifier cache; R8 models never saw labels. The V3.4 report's partial-cohort status (6 missing K3 slots) carries over |
| 20 exposed 3D DEV roots (k45 cohort) | Development sanity check only | Never in the independent cohort (different generator namespace) |
| R8B cohort (99 roots) | R8C independent K = 4 / 5 evaluation | See `R8_K45_DATASET_REPORT.md` |

**Protected data.** Nothing named release_v2 and no historical TEST rows or metadata were accessed by R7–R9 code. Teammate baseline checkpoints selected on their own V4 split: 348 of the 395 V3.4 3D roots descend from layouts in GRN's V4 VAL split, and none from its TRAIN split. This is disclosed in the feasibility report.
