# The 13 omission cases (3D V4)

**Result: 8 of the 13 scenes are real K contradictions under the finalized protocol; 5 keep their K.**
A contradiction requires a shortened sequence with replayed X = 1 and replayed Y = 1. Y = 1 alone does not count.

- Rows with omission Y = 1 in the V4 label manifest: 24 (K3 omissions have two orders each).
- Unique scenes: **13**. Unique (scene, omitted object) pairs: **13**, so all 13 are distinct.
- Every shortened order was replayed in a fresh environment: the stored relocation and connector witnesses were executed, or a planning failure was re-planned from the replayed state. The omission endpoint Y was replayed from q_ref with its stored target witness.
- Order-level verdicts: {"VERIFIED_SHORTER_REPAIR_X1_Y1": 10, "RETAIN_K_X0_Y1": 14}.

## Per scene

| scene | K | split | omitted | shortened orders X1Y1 | orders | selected rows replay | legacy teacher also succeeds | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3ds66-lap3-w0144-s020 | 3 | train | o02 | 1 | 2 | 6/6 + Y ok | yes | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-lap3-w0148-s023 | 3 | train | o01 | 2 | 2 | 6/6 + Y ok | no | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-lap3-w0156-s008 | 3 | train | o00 | 1 | 2 | 6/6 + Y ok | yes | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-lap3-w0159-s011 | 2 | train | o01 | 1 | 1 | 2/2 + Y ok | no | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-lap3-w0169-s012 | 3 | train | o01 | 2 | 2 | 6/6 + Y ok | no | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-srv-w0032-s002 | 2 | train | o01 | 1 | 1 | 2/2 + Y ok | yes | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-srv3-w0087-s021 | 3 | test | o01 | 1 | 2 | 6/6 + Y ok | no | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| 3ds66-srv3-w0099-s017 | 3 | test | o02 | 0 | 2 | 6/6 + Y ok | no | K_RETAINED |
| 3ds66-srv3-w0103-s001 | 3 | train | o02 | 0 | 2 | 6/6 + Y ok | no | K_RETAINED |
| D3H_GVLAB4_7d6653e840 | 3 | train | o02 | 0 | 2 | 6/6 + Y ok | no | K_RETAINED |
| D3H_GVLAB4_fa3b18e20d | 3 | train | o00 | 1 | 2 | 6/6 + Y ok | yes | K_INCONSISTENT_UNDER_FINALIZED_PROTOCOL |
| D3H_GVLAB_9f2076db42 | 3 | train | o02 | 0 | 2 | 6/6 + Y ok | no | K_RETAINED |
| D3H_LAP4_94cacb8c5f | 3 | train | o01 | 0 | 2 | 6/6 + Y ok | no | K_RETAINED |

## Per shortened order

| scene | K | split | source | omitted | shortened order (object > cell) | label X | replay X | label Y | replay Y | legacy (diag.) | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3ds66-lap3-w0144-s020 | 3 | train | PUBLISHED_RUN_DEPENDENT_K3 | o02 | o01>(5, 1) → o00>(2, 0) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 1 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0144-s020 | 3 | train | PUBLISHED_RUN_DEPENDENT_K3 | o02 | o00>(2, 0) → o01>(5, 1) | 0 (relocation:1) | 0 (REPLAYED_EXECUTION_FAILURE) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-lap3-w0148-s023 | 3 | train | PUBLISHED_ORIGINAL | o01 | o00>(5, 0) → o02>(5, 2) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0148-s023 | 3 | train | PUBLISHED_ORIGINAL | o01 | o02>(5, 2) → o00>(5, 0) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0156-s008 | 3 | train | PUBLISHED_ORIGINAL | o00 | o01>(5, 4) → o02>(5, 2) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-lap3-w0156-s008 | 3 | train | PUBLISHED_ORIGINAL | o00 | o02>(5, 2) → o01>(5, 4) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 1 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0159-s011 | 2 | train | PUBLISHED_ORIGINAL | o01 | o00>(2, 0) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0169-s012 | 3 | train | PUBLISHED_ORIGINAL | o01 | o00>(5, 0) → o02>(5, 4) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-lap3-w0169-s012 | 3 | train | PUBLISHED_ORIGINAL | o01 | o02>(5, 4) → o00>(5, 0) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-srv-w0032-s002 | 2 | train | PUBLISHED_ORIGINAL | o01 | o00>(5, 5) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 1 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-srv3-w0087-s021 | 3 | test | PUBLISHED_ORIGINAL | o01 | o00>(3, 1) → o02>(1, 0) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 0 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| 3ds66-srv3-w0087-s021 | 3 | test | PUBLISHED_ORIGINAL | o01 | o02>(1, 0) → o00>(3, 1) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-srv3-w0099-s017 | 3 | test | PUBLISHED_ORIGINAL | o02 | o00>(4, 3) → o01>(2, 3) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-srv3-w0099-s017 | 3 | test | PUBLISHED_ORIGINAL | o02 | o01>(2, 3) → o00>(4, 3) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-srv3-w0103-s001 | 3 | train | PUBLISHED_ORIGINAL | o02 | o00>(2, 2) → o01>(4, 2) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| 3ds66-srv3-w0103-s001 | 3 | train | PUBLISHED_ORIGINAL | o02 | o01>(4, 2) → o00>(2, 2) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_GVLAB4_7d6653e840 | 3 | train | NEW_HARD_ORDER_V4 | o02 | o00>(4, 3) → o01>(2, 3) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_GVLAB4_7d6653e840 | 3 | train | NEW_HARD_ORDER_V4 | o02 | o01>(2, 3) → o00>(4, 3) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_GVLAB4_fa3b18e20d | 3 | train | NEW_HARD_ORDER_V4 | o00 | o02>(5, 5) → o01>(2, 3) | 1 (ok) | 1 (REPLAYED_CONNECTOR) | 1 | 1 (REPLAYED_TARGET) | 1 | VERIFIED_SHORTER_REPAIR_X1_Y1 |
| D3H_GVLAB4_fa3b18e20d | 3 | train | NEW_HARD_ORDER_V4 | o00 | o01>(2, 3) → o02>(5, 5) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_GVLAB_9f2076db42 | 3 | train | NEW_HARD_ORDER_V3 | o02 | o00>(4, 4) → o01>(1, 2) | 0 (relocation:0) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_GVLAB_9f2076db42 | 3 | train | NEW_HARD_ORDER_V3 | o02 | o01>(1, 2) → o00>(4, 4) | 0 (relocation:0) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_LAP4_94cacb8c5f | 3 | train | NEW_HARD_ORDER_V4 | o01 | o02>(2, 3) → o00>(1, 3) | 0 (relocation:0) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |
| D3H_LAP4_94cacb8c5f | 3 | train | NEW_HARD_ORDER_V4 | o01 | o00>(1, 3) → o02>(2, 3) | 0 (relocation:1) | 0 (PLANNING_FAILURE_RECONFIRMED) | 1 | 1 (REPLAYED_TARGET) | 0 | RETAIN_K_X0_Y1 |

*Legacy (diag.)*: the shortened order run by the legacy full-task teacher (target planned from the achieved pose). Diagnostic only, not a label.

## Proposed corrections (not applied)

Nothing in the dataset was changed. Each confirmed contradiction implies the scene's minimal K under the finalized protocol is at most K − 1, for any assignment of that layout. Replacing the assignment within the layout therefore cannot fix it; the scene has to leave its class or be relabelled.

| scene | K | split | proposal | same-class, same-split candidates (existing scenes) |
|---|---:|---:|---:|---:|
| 3ds66-lap3-w0144-s020 | 3 | train | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap4-w0177-s000, 3ds66-lap5-w0176-s007 |
| 3ds66-lap3-w0148-s023 | 3 | train | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap4-w0177-s000, 3ds66-lap5-w0176-s007 |
| 3ds66-lap3-w0156-s008 | 3 | train | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap4-w0177-s000, 3ds66-lap5-w0176-s007 |
| 3ds66-lap3-w0159-s011 | 2 | train | REMOVE_FROM_K2_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap-w0015-s022, 3ds66-lap-w0017-s023, 3ds66-lap-w0042-s022, 3ds66-lap3-w0092-s022, 3ds66-lap3-w0138-s001, 3ds66-lap3-w0138-s019, 3ds66-lap3-w0141-s017, 3ds66-lap3-w0143-s023, 3ds66-lap3-w0149-s019, 3ds66-lap3-w0151-s023, 3ds66-lap3-w0153-s014, 3ds66-lap3-w0164-s000, 3ds66-lap3-w0164-s008, 3ds66-lap3-w0164-s013, 3ds66-lap3-w0164-s018, 3ds66-lap3-w0165-s002, 3ds66-lap3-w0165-s008, 3ds66-lap3-w0165-s018, 3ds66-lap3-w0165-s022, 3ds66-lap3-w0167-s003, 3ds66-lap3-w0167-s006, 3ds66-lap3-w0167-s018, 3ds66-lap3-w0169-s005, 3ds66-lap3-w0169-s014, 3ds66-lap3-w0169-s016, 3ds66-lap3-w0170-s004, 3ds66-lap3-w0170-s010, 3ds66-lap3-w0170-s019, 3ds66-srv-w0000-s009, 3ds66-srv-w0001-s018, 3ds66-srv-w0003-s008, 3ds66-srv-w0027-s021, 3ds66-srv3-w0048-s020, 3ds66-srv3-w0051-s013, 3ds66-srv3-w0051-s015, 3ds66-srv3-w0057-s012, 3ds66-srv3-w0067-s016, 3ds66-srv3-w0070-s000, 3ds66-srv3-w0072-s005, 3ds66-srv3-w0089-s005, 3ds66-srv3-w0089-s011, 3ds66-srv3-w0097-s000, 3ds66-srv3-w0098-s007, 3ds66-srv3-w0098-s012, 3ds66-srv3-w0100-s019, 3ds66-srv3-w0105-s006, 3ds66-srv3-w0115-s006, 3ds66-srv3-w0119-s002, 3ds66-srv3-w0120-s023, 3ds66-srv3-w0121-s001, 3ds66-srv3-w0130-s009, 3ds66-srv3-w0132-s013, 3ds66-srv3-w0135-s004, 3ds66-srv3-w0165-s000, 3ds66-srv3-w0165-s014, 3ds66-srv3-w0165-s016, 3ds66-srv3-w0169-s000, 3ds66-srv3-w0174-s001 |
| 3ds66-lap3-w0169-s012 | 3 | train | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap4-w0177-s000, 3ds66-lap5-w0176-s007 |
| 3ds66-srv-w0032-s002 | 2 | train | REMOVE_FROM_K2_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap-w0015-s022, 3ds66-lap-w0017-s023, 3ds66-lap-w0042-s022, 3ds66-lap3-w0092-s022, 3ds66-lap3-w0138-s001, 3ds66-lap3-w0138-s019, 3ds66-lap3-w0141-s017, 3ds66-lap3-w0143-s023, 3ds66-lap3-w0149-s019, 3ds66-lap3-w0151-s023, 3ds66-lap3-w0153-s014, 3ds66-lap3-w0164-s000, 3ds66-lap3-w0164-s008, 3ds66-lap3-w0164-s013, 3ds66-lap3-w0164-s018, 3ds66-lap3-w0165-s002, 3ds66-lap3-w0165-s008, 3ds66-lap3-w0165-s018, 3ds66-lap3-w0165-s022, 3ds66-lap3-w0167-s003, 3ds66-lap3-w0167-s006, 3ds66-lap3-w0167-s018, 3ds66-lap3-w0169-s005, 3ds66-lap3-w0169-s014, 3ds66-lap3-w0169-s016, 3ds66-lap3-w0170-s004, 3ds66-lap3-w0170-s010, 3ds66-lap3-w0170-s019, 3ds66-srv-w0000-s009, 3ds66-srv-w0001-s018, 3ds66-srv-w0003-s008, 3ds66-srv-w0027-s021, 3ds66-srv3-w0048-s020, 3ds66-srv3-w0051-s013, 3ds66-srv3-w0051-s015, 3ds66-srv3-w0057-s012, 3ds66-srv3-w0067-s016, 3ds66-srv3-w0070-s000, 3ds66-srv3-w0072-s005, 3ds66-srv3-w0089-s005, 3ds66-srv3-w0089-s011, 3ds66-srv3-w0097-s000, 3ds66-srv3-w0098-s007, 3ds66-srv3-w0098-s012, 3ds66-srv3-w0100-s019, 3ds66-srv3-w0105-s006, 3ds66-srv3-w0115-s006, 3ds66-srv3-w0119-s002, 3ds66-srv3-w0120-s023, 3ds66-srv3-w0121-s001, 3ds66-srv3-w0130-s009, 3ds66-srv3-w0132-s013, 3ds66-srv3-w0135-s004, 3ds66-srv3-w0165-s000, 3ds66-srv3-w0165-s014, 3ds66-srv3-w0165-s016, 3ds66-srv3-w0169-s000, 3ds66-srv3-w0174-s001 |
| 3ds66-srv3-w0087-s021 | 3 | test | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | none |
| D3H_GVLAB4_fa3b18e20d | 3 | train | REMOVE_FROM_K3_OR_RELABEL_PENDING_USER_DECISION | 3ds66-lap4-w0177-s000, 3ds66-lap5-w0176-s007 |

Selected scenes whose selected assignment has **no** finalized X = 1, Y = 1 order (from Issue 2): 2.

| scene | K | split | X strength | Y | Y replay | proposal | same-layout candidate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3ds66-srv3-w0096-s012 | 2 | val | 2/2 | 0 | AGREE | REMOVE_FROM_K2_OR_RELABEL_PENDING_USER_DECISION | none |
| D3H_GVLAB_41f7a72379 | 3 | test | 1/6 | 0 | AGREE | REPLACE_ASSIGNMENT_WITHIN_LAYOUT | 3ds66-srv3-w0049-s009 |

**Quota consequence if every flagged scene were removed without replacement:** {"NONE": 408, "0": 511, "1": 357, "2": 609, "3": 605} (now {"NONE": 408, "0": 511, "1": 357, "2": 612, "3": 612}). Removed by K/split: {"K3/train": 5, "K2/train": 2, "K3/test": 2, "K2/val": 1}.

Candidate pool: the only existing, already-verified spare layouts of the right class are listed below. None of them has finalized X/Y or an omission check yet, so admitting any would need the same X/Y + omission + replay pass first.

| class | candidates (existing scenes) | with split = the flagged scene's split |
|---|---:|---:|
| K3 | 2 | train |
| K2 | 75 | test; train; val |

Machine-readable: `manifests/OMISSION_13_VERDICTS.json`, `manifests/PROPOSED_CORRECTION_MANIFEST.json`.
