# Final dataset integrity

Status: **BLOCKED**

| gate | check | result | detail |
|---|---:|---:|---:|
| G1 | 2D has exactly 5,000 selected scenes | PASS | {"rows": 5000, "unique": 5000} |
| G2 | 3D has exactly 2,500 main scenes (K4 archived outside) | PASS | {"rows": 2500, "k4_archived_outside": 9} |
| G3 | K0/K1/K2/K3/NONE quotas | PASS | {"2D": {"0": 1250, "1": 800, "2": 800, "NONE": 1000, "3": 1150}, "3D": {"NONE": 408, "0": 511, "1": 357, "2": 612, "3": 612}} |
| G4 | Roots, label records and referenced witnesses resolve (witness content ids re-derived) | PASS | {"3d_roots_missing": [], "witness_check": {"3d:ok": 12441, "2d:ok": 15570}, "2d_label_rows_missing_x_or_y": 0, "3d_label_rows_missing_x_or_y": 0, "note": "2D rows reused from k3_hard/xy2d_all.jsonl carry teacher replay flags but no witness ids (parity re-run regenerates them)"} |
| G5 | Source hashes, lineage-disjoint splits | PASS | {"2d_source_sha_mismatch": 0, "3d_root_sha_mismatch": 0, "3d_family_split_conflicts": 0, "2d_family_split_conflicts": 0, "3d_layouts_shared_by_two_selected_rows": 0} |
| G6 | Identical endpoints share one Y (any permutation) | PASS | {"3d_endpoints": 4437, "3d_conflicts": 0, "2d_endpoints": 9700, "2d_conflicts": 0} |
| G7 | Observed labels come from finalized teachers, not legacy substitutions | PASS | {"3d_provenance": {"SELECTED_ASSIGNMENT_ORDER/FIN3D_X_LAPTOP/FIN3D_Y_LAPTOP": 1518, "SELECTED_ASSIGNMENT_ORDER/FIN3D_X_GVLAB/FIN3D_Y_GVLAB": 1385, "SELECTED_ASSIGNMENT_ORDER/R1_GVLAB_XY3D_V3/R1_GVLAB_XY3D_V3": 1212, "SELECTED_ASSIGNMENT_ORDER/R2_FRESH_LEGACY_RELOCATION_FAILURE/FIN3D_Y_GVLAB": 291, "SELECTED_ASSIGNMENT_ORDER/R2_FRESH_LEGACY_RELOCATION_FAILURE/FIN3D_Y_LAPTOP": 490, "OMISSION_YNEG/FIN3D_X_LAPTOP/FIN3D_Y_LAPTOP": 1836, "EMPTY_SEQUENCE_YNEG/EMPTY_SEQUENCE/TEACHER_ORIGINAL_T_DIRECT_CHECK": 1989}, "2d_provenance": {"EMPTY_SEQUENCE_K0/EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION/BXY_Y_TEACHER_ |
| G8 | Positive and negative supervision in train / val / test | PASS | {"2D": {"train": {"X=1,Y=1": 4298, "X=1,Y=0": 4154, "X=0,Y=1": 3089, "X=0,Y=0": 639}, "val": {"X=1,Y=1": 907, "X=1,Y=0": 876, "X=0,Y=1": 679, "X=0,Y=0": 153}, "test": {"X=1,Y=1": 956, "X=1,Y=0": 893, "X=0,Y=1": 623, "X=0,Y=0": 133}}, "3D": {"train": {"X=1,Y=1": 2125, "X=0,Y=1": 1393, "X=1,Y=0": 2379, "X=0,Y=0": 318}, "val": {"X=1,Y=1": 396, "X=0,Y=1": 216, "X=1,Y=0": 462, "X=0,Y=0": 55}, "test": {"X=1,Y=1": 495, "X=0,Y=1": 287, "X=1,Y=0": 519, "X=0,Y=0": 76}}, "absent_cells": []} |
| G9 | No duplicate labels contradict each other | PASS | {"3d_x_conflicts": 0, "2d_x_conflicts": 0, "3d_y_conflicts": 0, "2d_y_conflicts": 0} |
| G10 | No model training launched | PASS | {"training_processes": []} |
| G11 | 3D replay agrees with stored labels | PASS | {"agree": 7367, "queries": 7367, "mismatches": 0} |
| G12 | 2D reused-evidence parity | PASS | {"empty_checked": 3750, "empty_agree": 3750, "sel_y_checked": 70, "sel_y_agree": 70, "sel_x_checked": 420, "sel_x_agree": 420} |
| G13 | K labels consistent with the finalized protocol | FAIL | {"3D_omission_X1Y1_shorter_repair": 8, "3D_selected_without_X1Y1_order": 2, "2D_omission_X1Y1_shorter_repair": 0, "2D_selected_without_X1Y1_order": 60, "2D_rate_over_K1_K3": 0.0218, "3D_rate_over_K2_K3": 0.0082} |

Machine-readable: `manifests/FINAL_INTEGRITY_GATES.json`, `FINAL_TRAINING_READINESS.json`.
