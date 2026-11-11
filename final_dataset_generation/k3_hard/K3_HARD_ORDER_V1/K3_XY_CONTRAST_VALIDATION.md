# K3 X/Y Contrast Validation
Finalized Approach-B check: X = the ordered relocations with carried robot state + connector back to q_ref; Y = target from q_ref in the endpoint scene (all 6 orders of one assignment reach the same endpoint and share one Y). Legacy strength (target planned from the achieved pose) is NOT assumed to equal X strength; selection prefers roots whose X strength equals the legacy strength with Y = 1.

## 2D
checked 1175, errors 0 []

| | X=0/6 | X=1/6 | X=2/6 | X=3/6 | X=4/6 | X=5/6 | X=6/6 | X_and_Y_verified | X_same_per_order_pattern | X_same_strength | X_unresolved_orders | Y_success | checked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1/6 | 31 | 324 | 27 | 25 | 1 | 4 | 5 | 324 | 323 | 324 | 0 | 417 | 417 |
| 2/6 | 9 | 27 | 289 | 26 | 6 | 9 | 2 | 289 | 288 | 289 | 0 | 368 | 368 |
| 3/6 | 0 | 6 | 20 | 241 | 11 | 4 | 6 | 241 | 240 | 241 | 0 | 288 | 288 |
| 4/6 | 0 | 0 | 4 | 12 | 71 | 9 | 3 | 71 | 69 | 71 | 0 | 99 | 99 |
| 5/6 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 3 | 3 | 0 | 3 | 3 |

Totals: ```{"checked": 1175, "Y_success": 1175, "X_same_strength": 928, "X_same_per_order_pattern": 923, "X_and_Y_verified": 928}```

Selected V3 K3 rows with an X/Y record: 807; X/Y-verified at the selected strength: 669

## 3D
checked 202, errors 0 []

| | X=1/6 | X=2/6 | X=3/6 | X=4/6 | X=5/6 | X_and_Y_verified | X_same_per_order_pattern | X_same_strength | X_unresolved_orders | Y_success | checked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1/6 | 139 | 3 | 2 | 0 | 0 | 138 | 139 | 139 | 0 | 143 | 144 |
| 2/6 | 0 | 45 | 1 | 0 | 1 | 45 | 45 | 45 | 0 | 47 | 47 |
| 3/6 | 0 | 0 | 8 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 8 |
| 4/6 | 0 | 0 | 0 | 3 | 0 | 3 | 3 | 3 | 0 | 3 | 3 |

Totals: ```{"checked": 202, "Y_success": 201, "X_same_strength": 195, "X_same_per_order_pattern": 195, "X_and_Y_verified": 194}```

Selected V3 K3 rows with an X/Y record: 182; X/Y-verified at the selected strength: 177

3D X/Y is a teacher pass (no independent replay); 2D X/Y includes independent replay.
