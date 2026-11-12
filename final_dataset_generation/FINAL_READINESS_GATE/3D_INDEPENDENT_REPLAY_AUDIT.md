# 3D independent replay audit (FINAL_3D_DATASET_V4)

**Result: 7367 of 7367 replayed X/Y queries agree with the stored finalized labels; 0 unresolved mismatches.**

## Replay path

- The scene is loaded from the selected root JSON (immutable source; sha256 checked against the selection manifest) and built and settled in a new MuJoCo environment, in a fresh worker process.
- **X:** each stored relocation witness is executed in order, with carried robot state and no reset. Before execution its content id is re-derived and its first configuration is checked against the current one (continuity ≤ 1e-6 rad). The grasp is recovered by forward kinematics of the stored grasp configuration against the object's candidate grasp poses (≤ 5 mm, ≤ 3°, unique open width). The pinned `bwlphys.move` checks apply: end cell, |z| ≤ 1 cm, no other object changed cell.
- **Connector:** the stored path is executed with `bwlphys.connector`. It checks |q − q_ref| ≤ 0.02 rad, nothing pushed > 4 mm, every object in its endpoint cell, gripper opened and nothing held, and zero robot–object contacts. The path must also end exactly at q_ref.
- **Y:** the endpoint scene is settled at q_ref and the stored target witness is executed (t0 to goal) with the same checks.
- **Negatives:** a planning failure is re-confirmed by re-planning (`bd_3dt.query` / `plan_free_move`, seed 0) from the *replayed* state. An execution failure is reproduced from its stored witness.
- **Rows without stored witnesses** (gvlab-V3 reuse R1, legacy shortcut R2): the unchanged finalized teacher is re-run in the fresh process into a separate store, then its witnesses are replayed in a new environment.
- Grasp recovery: {"OK": 12810}. Root hashes all match: True.

## Coverage and agreement by tier

| tier | what | queries | agree | mismatch |
|---|---:|---:|---:|---:|
| A_MANDATORY | Mandatory: 13 omission scenes (all their rows), 2 selected Y = 0 scenes | 130 | 130 | 0 |
| B_STRATIFIED | Stratified sample of selected and omission rows (incl. re-runs of rows without witnesses) | 755 | 755 | 0 |
| C_ALL_WITNESSED | Every other witness-backed X row and Y = 1 endpoint | 5166 | 5166 | 0 |
| D_RERUN_REPLAY | Every legacy-shortcut (R2) row and every gvlab-V3 (R1) positive not in A/B: re-run + replay | 1116 | 1116 | 0 |
| E_EMPTY_SAMPLE | Stratified sample of empty-sequence Y labels: re-run + replay | 200 | 200 | 0 |

Teacher re-run reproducibility (re-run label vs stored label, before replay): {"X|agree": 1140, "Y|agree": 402}.

## Agreement by label stratum (all tiers)

| stratum | agree | replayed |
|---|---:|---:|
| selected X = 1 | 3009 | 3009 |
| selected X = 0 | 1034 | 1034 |
| selected Y = 1 | 1222 | 1222 |
| selected Y = 0 | 2 | 2 |
| omission X = 1 | 1378 | 1378 |
| omission X = 0 | 458 | 458 |
| omission Y = 1 | 13 | 13 |
| omission Y = 0 | 51 | 51 |
| empty-sequence Y = 0 | 200 | 200 |

## Agreement by split, strength, provenance, failure phase, source family

| stratum | agree | replayed |
|---|---:|---:|
| split / X / test | 968 | 968 |
| split / X / train | 4141 | 4141 |
| split / X / val | 770 | 770 |
| split / Y / test | 235 | 235 |
| split / Y / train | 1042 | 1042 |
| split / Y / val | 211 | 211 |
| K3_strength / 1 | 578 | 578 |
| K3_strength / 2 | 509 | 509 |
| K3_strength / 3 | 311 | 311 |
| K3_strength / 4 | 318 | 318 |
| K3_strength / 5 | 695 | 695 |
| K3_strength / 6 | 408 | 408 |
| K2_strength / 1 | 42 | 42 |
| K2_strength / 2 | 1182 | 1182 |
| x_provenance / FIN3D_X_GVLAB | 1385 | 1385 |
| x_provenance / FIN3D_X_LAPTOP | 1518 | 1518 |
| x_provenance / R1_GVLAB_XY3D_V3 | 359 | 359 |
| x_provenance / R2_FRESH_LEGACY_RELOCATION_FAILURE | 781 | 781 |
| phase / connector:connector | 25 | 25 |
| phase / none | 3009 | 3009 |
| phase / relocation:0 | 199 | 199 |
| phase / relocation:1 | 543 | 543 |
| phase / relocation:2 | 267 | 267 |
| source_family / GENERATED_V4_K3 | 30 | 30 |
| source_family / NEW_DEPENDENCE_SEEKING_V1 | 222 | 222 |
| source_family / NEW_HARD_ORDER_V3 | 359 | 359 |
| source_family / NEW_HARD_ORDER_V4 | 666 | 666 |
| source_family / PUBLISHED_ORIGINAL | 2634 | 2634 |
| source_family / PUBLISHED_RUN_DEPENDENT_K3 | 132 | 132 |
| xy_cell / X=0,Y=0 | 5 | 5 |
| xy_cell / X=0,Y=1 | 1029 | 1029 |
| xy_cell / X=1,Y=0 | 3 | 3 |
| xy_cell / X=1,Y=1 | 3006 | 3006 |
| method / X / RERUN+REPLAY | 1140 | 1140 |
| method / X / STORED_WITNESS_REPLAY | 4739 | 4739 |
| method / Y / RERUN+REPLAY | 402 | 402 |
| method / Y / STORED_WITNESS_REPLAY | 1086 | 1086 |

## Per-label replay coverage of the V4 label manifest

Counts of label rows by how their X and Y were checked. NOT_REPLAYED rows were not part of any tier.

| row kind / check | rows |
|---|---:|
| EMPTY_SEQUENCE_YNEG / x:N/A(empty sequence) | 1989 |
| EMPTY_SEQUENCE_YNEG / y:FRESH_RERUN(es_verify) | 60 |
| EMPTY_SEQUENCE_YNEG / y:NOT_REPLAYED | 1729 |
| EMPTY_SEQUENCE_YNEG / y:RERUN+REPLAY | 200 |
| OMISSION_YNEG / x:STORED_WITNESS_REPLAY | 1836 |
| OMISSION_YNEG / y:NOT_REPLAYED | 1731 |
| OMISSION_YNEG / y:STORED_WITNESS_REPLAY | 105 |
| SELECTED_ASSIGNMENT_ORDER / x:NOT_REPLAYED | 853 |
| SELECTED_ASSIGNMENT_ORDER / x:RERUN+REPLAY | 1140 |
| SELECTED_ASSIGNMENT_ORDER / x:STORED_WITNESS_REPLAY | 2903 |
| SELECTED_ASSIGNMENT_ORDER / y:RERUN+REPLAY | 1212 |
| SELECTED_ASSIGNMENT_ORDER / y:STORED_WITNESS_REPLAY | 3684 |

## Mismatches

None.

**Scope:** tiers C and D cover every witness-backed X row, every Y = 1 endpoint and every R2 row. The remaining R1 X = 0 rows, Y = 0 endpoints and empty-sequence labels are covered by samples (tiers A, B, E). This audit is therefore **not** an exhaustive replay of every 3D label; the per-row coverage table above is exact.

Machine-readable: `manifests/3D_REPLAY_RESULTS.json` (every replayed query), `manifests/3D_FINAL_XY_LABEL_MANIFEST_WITH_REPLAY.json` (V4 labels unchanged, annotated per row).
