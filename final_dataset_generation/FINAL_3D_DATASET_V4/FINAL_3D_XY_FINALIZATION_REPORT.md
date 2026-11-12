# FINAL 3D finalized X/Y report

- **X:** the order's relocations executed exactly as bd_3dt.teach.seq (fresh env, carried arm state, same checks) WITHOUT the target step, then CONNECTOR_TO_QREADY_V1 (plan_free_move to q_ref = q_ready, RRT 5000 seed 0, execute, open gripper, |q - q_ref| <= 0.02, nothing pushed, every object in its endpoint cell, no contact)
- **Y:** BD3DS66_Y_PLAN_V1: the endpoint scene settled at q_ref, bd_3dt.query(t0 -> goal), executed with seq's target checks (one Y per endpoint)
- **legacy_y:** full-task label: relocations then T planned from the ACHIEVED arm pose (perm3d.seq, fresh env)

Selected K2 + K3 rows fully finalized (every order X and the endpoint Y resolved): **1224 / 1224**.

| row kind | X1 Y1 | X0 Y1 | X1 Y0 | X0 Y0 | missing |
|---|---|---|---|---|---|
| SELECTED_ASSIGNMENT_ORDER | 3006 | 1882 | 3 | 5 | 0 |
| OMISSION_YNEG | 10 | 14 | 1368 | 444 | 0 |
| EMPTY_SEQUENCE_YNEG | 0 | 0 | 1989 | 0 | 0 |

Provenance of X labels (selected assignment orders):

| provenance | orders |
|---|---|
| FIN3D_X_LAPTOP | 1518 |
| FIN3D_X_GVLAB | 1385 |
| R1_GVLAB_XY3D_V3 | 1212 |
| R2_FRESH_LEGACY_RELOCATION_FAILURE | 781 |

Provenance of Y labels (selected rows):

| provenance | orders |
|---|---|
| FIN3D_Y_LAPTOP | 2008 |
| FIN3D_Y_GVLAB | 1676 |
| R1_GVLAB_XY3D_V3 | 1212 |

Shortcut audit (R2 orders re-executed in full): {'agree': 52}; disagreements: []

K2 legacy strength {"1/2": 23, "2/2": 589}; K2 finalized-X strength {"1/2": 21, "2/2": 591}
