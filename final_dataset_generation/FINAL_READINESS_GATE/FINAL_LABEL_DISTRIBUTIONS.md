# Final label distributions

Learning-view rows: selected corrective orders, omission Y-negatives and empty-sequence rows. Counts are actual frequencies, with no artificial balancing.

## All four X/Y combinations

| domain | X=1,Y=1 | X=0,Y=1 | X=1,Y=0 | X=0,Y=0 | missing |
|---|---:|---:|---:|---:|---:|
| 2D | 6161 | 4391 | 5923 | 925 | 0 |
| 3D | 3016 | 1896 | 3360 | 449 | 0 |

## 2D by row kind and split

| row kind | split | X=1,Y=1 | X=0,Y=1 | X=1,Y=0 | X=0,Y=0 | missing |
|---|---:|---:|---:|---:|---:|---:|
| EMPTY_SEQUENCE_K0 | test | 187 | 0 | 0 | 0 | 0 |
| EMPTY_SEQUENCE_K0 | train | 875 | 0 | 0 | 0 | 0 |
| EMPTY_SEQUENCE_K0 | val | 188 | 0 | 0 | 0 | 0 |
| EMPTY_SEQUENCE_YNEG | test | 0 | 0 | 562 | 0 | 0 |
| EMPTY_SEQUENCE_YNEG | train | 0 | 0 | 2625 | 0 | 0 |
| EMPTY_SEQUENCE_YNEG | val | 0 | 0 | 563 | 0 | 0 |
| OMISSION_YNEG | test | 0 | 0 | 331 | 133 | 0 |
| OMISSION_YNEG | train | 0 | 2 | 1529 | 639 | 0 |
| OMISSION_YNEG | val | 0 | 0 | 313 | 153 | 0 |
| SELECTED_ASSIGNMENT_ORDER | test | 769 | 623 | 0 | 0 | 0 |
| SELECTED_ASSIGNMENT_ORDER | train | 3423 | 3087 | 0 | 0 | 0 |
| SELECTED_ASSIGNMENT_ORDER | val | 719 | 679 | 0 | 0 | 0 |

## 3D by row kind and split

| row kind | split | X=1,Y=1 | X=0,Y=1 | X=1,Y=0 | X=0,Y=0 | missing |
|---|---:|---:|---:|---:|---:|---:|
| EMPTY_SEQUENCE_YNEG | test | 0 | 0 | 303 | 0 | 0 |
| EMPTY_SEQUENCE_YNEG | train | 0 | 0 | 1408 | 0 | 0 |
| EMPTY_SEQUENCE_YNEG | val | 0 | 0 | 278 | 0 | 0 |
| OMISSION_YNEG | test | 1 | 3 | 215 | 71 | 0 |
| OMISSION_YNEG | train | 9 | 11 | 971 | 318 | 0 |
| OMISSION_YNEG | val | 0 | 0 | 182 | 55 | 0 |
| SELECTED_ASSIGNMENT_ORDER | test | 494 | 284 | 1 | 5 | 0 |
| SELECTED_ASSIGNMENT_ORDER | train | 2116 | 1382 | 0 | 0 | 0 |
| SELECTED_ASSIGNMENT_ORDER | val | 396 | 216 | 2 | 0 | 0 |

## Y-negative evidence by source and split

### 2D

| Y = 0 source | train | val | test | total |
|---|---:|---:|---:|---:|
| EMPTY_SEQUENCE_YNEG | 2625 | 563 | 562 | 3750 |
| OMISSION_YNEG | 2168 | 466 | 464 | 3098 |

### 3D

| Y = 0 source | train | val | test | total |
|---|---:|---:|---:|---:|
| EMPTY_SEQUENCE_YNEG | 1408 | 278 | 303 | 1989 |
| OMISSION_YNEG | 1289 | 237 | 286 | 1812 |
| SELECTED_ASSIGNMENT_ORDER | 0 | 2 | 6 | 8 |

## 3D K3 strength (finalized X vs legacy)

| strength | finalized train | finalized val | finalized test | legacy train | legacy val | legacy test |
|---|---:|---:|---:|---:|---:|---:|
| 0/6 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1/6 | 156 | 20 | 27 | 162 | 20 | 28 |
| 2/6 | 80 | 15 | 19 | 79 | 15 | 18 |
| 3/6 | 38 | 8 | 11 | 34 | 8 | 11 |
| 4/6 | 37 | 7 | 10 | 31 | 5 | 10 |
| 5/6 | 81 | 13 | 22 | 84 | 15 | 22 |
| 6/6 | 48 | 7 | 13 | 50 | 7 | 13 |

Absent X/Y cells by split: none.

Machine-readable: `manifests/FINAL_LABEL_DISTRIBUTIONS.json`.
