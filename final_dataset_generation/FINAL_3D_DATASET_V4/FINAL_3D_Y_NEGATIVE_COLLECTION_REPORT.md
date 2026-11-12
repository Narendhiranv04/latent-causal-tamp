# FINAL 3D Y-negative collection report

All Y-negatives come from EXISTING selected scenes / assignments (no new scenes):

- **OMISSION_YNEG:** each selected K2 / K3 assignment with one mover omitted (sha256 choice); X for every order of the remaining movers, Y at that endpoint (minimality predicts Y = 0; Y = 1 would expose a shorter repair).
- **EMPTY_SEQUENCE_YNEG:** the original scene of every selected K1 / K2 / K3 / NONE scene (no relocation): T from q_ref is infeasible by the teacher's original check / the NONE certificate; fresh-verified on a sample.

| row kind | X1 Y1 | X0 Y1 | X1 Y0 | X0 Y0 | missing |
|---|---|---|---|---|---|
| SELECTED_ASSIGNMENT_ORDER | 3006 | 1882 | 3 | 5 | 0 |
| OMISSION_YNEG | 10 | 14 | 1368 | 444 | 0 |
| EMPTY_SEQUENCE_YNEG | 0 | 0 | 1989 | 0 | 0 |

All label rows: Y=1 4912, Y=0 3809, missing 0 (Y=0 share 43.7%; excluding empty-sequence rows 27.0%).

Empty-sequence fresh verification sample: {0: 60} (expected all 0).

Omission endpoints with Y = 1 (a shorter repair exists from q_ref; reported, not hidden): 13 roots ['3ds66-lap3-w0144-s020', '3ds66-lap3-w0148-s023', '3ds66-lap3-w0156-s008', '3ds66-lap3-w0159-s011', '3ds66-lap3-w0169-s012', '3ds66-srv-w0032-s002', '3ds66-srv3-w0087-s021', '3ds66-srv3-w0099-s017', '3ds66-srv3-w0103-s001', 'D3H_GVLAB4_7d6653e840', 'D3H_GVLAB4_fa3b18e20d', 'D3H_GVLAB_9f2076db42', 'D3H_LAP4_94cacb8c5f']
