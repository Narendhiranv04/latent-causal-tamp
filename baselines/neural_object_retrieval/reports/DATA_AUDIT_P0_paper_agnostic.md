# SORC-Grid P0 data audit (local, read-only; generated from `sorc_dataset_manifest.json`)

Source commit `c5a808ecaa913fedbaf91bb51c1ccd0eacb7dcfc`. Snapshots (read-only, hashes in the manifest): base `abf_9de85710c2a7103f`, TRAIN-superset `abf_v3_e8a496bc66266fca` (VAL/TEST rows byte-identical to base: 2d True, 3d True).

| | 2D | 3D |
|---|---:|---:|
| TRAIN / VAL / TEST roots | 3500 / 751 / 749 | 1766 / 364 / 370 |
| train K0/K1/K2/K3/NONE | 875/560/560/805/700 | 358/251/429/440/288 |
| val K0/K1/K2/K3/NONE | 188/120/120/173/150 | 86/53/97/70/58 |
| TEST (counts only) | 187/120/120/172/150 | 67/53/86/102/62 |
| train: verified successful repairs (X=1 & Y=1, unique ordered) | 5123 | 3702 |
| train: SEQ samples (prefix → positive next objects) | 7637 | 5287 |
| train: PLACE samples (prefix, object → positive cells) | 9863 | 6871 |
| train: EXEC step labels (decided) | 19300 | 11141 |
| train:   of which executed (1) | 16562 | 9906 |
| train: STOP endpoint Y labels (dedup) | 18777 | 7671 |
| train:   of which Y=1 | 5880 | 3068 |
| train: X label conflicts | 0 | 0 |
| train: step-label conflicts (masked) | 0 | 0 |
| train: endpoints with >1 decided order / order-contrast endpoints | 10106 / 1443 | 3999 / 721 |
| val: verified successful repairs (X=1 & Y=1, unique ordered) | 719 | 449 |
| val: SEQ samples (prefix → positive next objects) | 1300 | 751 |
| val: PLACE samples (prefix, object → positive cells) | 1615 | 981 |
| val: EXEC step labels (decided) | 2729 | 1283 |
| val:   of which executed (1) | 2127 | 1099 |
| val: STOP endpoint Y labels (dedup) | 1457 | 751 |
| val:   of which Y=1 | 601 | 304 |
| val: X label conflicts | 0 | 0 |
| val: step-label conflicts (masked) | 0 | 0 |
| val: endpoints with >1 decided order / order-contrast endpoints | 466 / 301 | 237 / 98 |
| families / layouts in 2+ splits (leakage) | 0 / 0 | 0 / 0 |
| max objects per root; grid; legal cells | 20; [8, 8]; [64] | 13; [6, 6]; [36] |

**TRAIN X label kinds** — 2D: {"V3_DIRECT_CANDIDATE": 1587, "SELECTED_ASSIGNMENT_ORDER": 6510, "ONPOLICY_COLLECT": 7133, "ONPOLICY_COVERAGE": 461, "OMISSION_YNEG": 2170}; 3D: {"V3_DIRECT_CANDIDATE": 1625, "SELECTED_ASSIGNMENT_ORDER": 3749, "ONPOLICY_COLLECT": 1933, "ONPOLICY_COVERAGE": 193, "OMISSION_YNEG": 1309}

**X=0 failure localisation (TRAIN)** — 2D: {"x=1": 8784, "None": 5349, "connector": 273, "relocation:1": 1888, "relocation:0": 533, "relocation:2": 1034}; 3D: {"x=1": 5555, "None": 1543, "relocation:1": 902, "relocation:0": 337, "connector": 43, "relocation:2": 429}

## Evidence streams (contract §1.3)
1. **Target X/Y (used).** SEQ/PLACE from verified successful repairs only; STOP from deduplicated endpoint Y; nothing unobserved becomes a negative.
2. **Q2 isolated placement (NOT_LOCAL).** NOT_LOCAL (gvlab-only merge; contract forbids fetching) / NOT_LOCAL (gvlab-only production set; a partial off-host parity mirror is not a provenance-verified copy). Consequence: optional auxiliary conditional-placement head not trained; PLACE learns only from target-repair evidence.
3. **Physical witnesses / phase logs (used, as step labels).** Finalised-teacher X=0 rows carry `x_phase` = `relocation:j` / `connector`: relocations before j were physically executed under continuous robot state (label 1), relocation j failed (label 0); X=1 sequences label every step 1. On-policy / direct-candidate X=0 rows have no phase → their steps are masked. The phase is per *relocation* (pick + transport + place), not per grasp: the action head is therefore a **relocation-step executability** head, the honest GRASP-only analogue (adaptation documented in SORC_FIDELITY_AUDIT.md).
4. **Rendered observations (not used).** Rows are structured geometry; no RGB-D exists. SORC-Grid uses structured object/cell features (no image-equivalence claim).

## Teacher interfaces
2D `teacher2d` (fastgeom1) and 3D `fin3d` boot locally from `~/abf_v31_lapverify/code` with the V3.3 laptop teacher envs (`~/abf_v3_laptop/env2d|env3d`), byte-identical to the parity-checked V3.3 path.

## Gate P0: PASS (2D and 3D). Q2 auxiliary NOT_LOCAL (optional head omitted, disclosed).
