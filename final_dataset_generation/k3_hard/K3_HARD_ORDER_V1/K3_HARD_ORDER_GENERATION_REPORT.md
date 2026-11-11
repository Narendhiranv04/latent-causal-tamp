# K3 Hard-Order Generation Report (Approach B, 2D + 3D)
Sidecar `final_dataset_generation/k3_hard/K3_HARD_ORDER_V1/`. V2 selections are unchanged baselines; nothing was trained.
Method: re-parking with a hard-order-focused precedence search (park V next to U's initial cell so U must precede V; pairs ranked by how many currently successful orders they remove), greedy first-improvement toward 1/6, minimal K re-verified by a fresh teach (verified_K = 3, same assignment), all 6 orders evaluated with sequential physical execution (carried robot state, no resets, no swaps, fixed IK/geometry/grasps/budgets, destinations distinct and free in the original scene, identical across the 6 orders). Planner-budget failure = 0; administrative stops = MISSING. 2D also keeps intermediate verified levels (<= 4/6) as lineage siblings.

## 2D
### Distributions
| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| V2 baseline K3 (old, not new) | 37 | 79 | 221 | 139 | 214 | 460 |
| natural source strength of the same layouts | 26 | 36 | 113 | 109 | 214 | 652 |
| target | 403 | 345 | 172 | 115 | 57 | 58 |
| V3 selected | 403 | 326 | 172 | 78 | 67 | 104 |
| deficit (+ = short) | 0 | 19 | 0 | 37 | -10 | -46 |

### Jobs
```
{
 "total": 1113,
 "pilot": 54,
 "bulk": 1059,
 "by_split": {
  "train": 784,
  "val": 164,
  "test": 165
 },
 "handed_to_gvlab": 57,
 "outcomes": {
  "ACCEPTED": 817,
  "NO_IMPROVEMENT": 147,
  "TEACH_REJECTED": 80,
  "NOT_STARTED_OR_IN_FLIGHT_AT_CAP (MISSING)": 68,
  "ADMIN_STOP (MISSING)": 1
 },
 "start_strength_of_all_jobs": {
  "1/6": 0,
  "2/6": 79,
  "3/6": 221,
  "4/6": 187,
  "5/6": 431,
  "6/6": 195
 },
 "final_strength_of_accepted_jobs": {
  "1/6": 416,
  "2/6": 235,
  "3/6": 134,
  "4/6": 29,
  "5/6": 3,
  "6/6": 0
 }
}
```
Start -> final (accepted strength, or `none`):
| | 1 | 2 | 3 | 4 | 5 | none |
|---|---:|---:|---:|---:|---:|---:|
| start 2/6 | 39 | 0 | 0 | 0 | 0 | 40 |
| start 3/6 | 121 | 50 | 0 | 0 | 0 | 50 |
| start 4/6 | 72 | 41 | 37 | 0 | 0 | 37 |
| start 5/6 | 150 | 125 | 69 | 23 | 0 | 64 |
| start 6/6 | 34 | 19 | 28 | 6 | 3 | 36 |

### New verified roots
```
{
 "saved": 1175,
 "gate": {
  "PASS": 1175
 },
 "gate_rule": "consistency2d: every teacher-labelled order re-executed on a fresh cache, all y equal",
 "by_strength_all": {
  "1/6": 417,
  "2/6": 368,
  "3/6": 288,
  "4/6": 99,
  "5/6": 3,
  "6/6": 0
 },
 "by_strength_gate_pass": {
  "1/6": 417,
  "2/6": 368,
  "3/6": 288,
  "4/6": 99,
  "5/6": 3,
  "6/6": 0
 },
 "layouts_improved": 818
}
```
Consistency failures (excluded): 0

### Selection
```
{
 "version": "2D_K3_STRENGTH_SELECTION_V3",
 "targets": {
  "1": 403,
  "2": 345,
  "3": 172,
  "4": 115,
  "5": 57,
  "6": 58
 },
 "selected_distribution": {
  "1/6": 403,
  "2/6": 326,
  "3/6": 172,
  "4/6": 78,
  "5/6": 67,
  "6/6": 104
 },
 "deficit_vs_target": {
  "1/6": 0,
  "2/6": 19,
  "3/6": 0,
  "4/6": 37,
  "5/6": -10,
  "6/6": -46
 },
 "layouts_with_option": {
  "1/6": 454,
  "2/6": 447,
  "3/6": 509,
  "4/6": 286,
  "5/6": 435,
  "6/6": 652
 },
 "n_layouts": 1150,
 "excluded_by_gates": {},
 "xy_checked_selected": 807,
 "xy_verified_selected": 669,
 "source_mix": {
  "NEW_HARD_ORDER": 807,
  "NEW_DEPENDENCE_SEEKING": 135,
  "ORIGINAL_SELECTED": 208
 },
 "by_split": {
  "train": {
   "1/6": 280,
   "2/6": 231,
   "3/6": 123,
   "4/6": 61,
   "5/6": 53,
   "6/6": 57
  },
  "val": {
   "1/6": 67,
   "2/6": 48,
   "3/6": 25,
   "4/6": 7,
   "5/6": 5,
   "6/6": 21
  },
  "test": {
   "1/6": 56,
   "2/6": 47,
   "3/6": 24,
   "4/6": 10,
   "5/6": 9,
   "6/6": 26
  }
 }
}
```

### Reserves
| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| unselected gate-pass hard roots | 51 | 90 | 166 | 61 | 0 | 0 |
| layouts with an unused option at s | 51 | 121 | 337 | 208 | 368 | 548 |

### Uniqueness and lineage
```
{
 "rows_total": 5000,
 "rows_total_v2": 5000,
 "k_counts_v3": {
  "0": 1250,
  "1": 800,
  "2": 800,
  "NONE": 1000,
  "3": 1150
 },
 "k_counts_v2": {
  "0": 1250,
  "1": 800,
  "2": 800,
  "3": 1150,
  "NONE": 1000
 },
 "unique_root_ids": true,
 "unique_k3_layouts": true,
 "k3_layout_set_equals_v2": true,
 "non_k3_rows_identical_to_v2": true,
 "lineage_failures": {}
}
```

### Witness and hash integrity (selected new roots; witnesses re-hashed from content)
```
{"ok": 5646}
```

### Natural-distribution holdout view
test-split K3 layouts, each with its ORIGINAL source assignment and its natural source strength (the 6-order outcome of the published original root); same layouts as the hard-order test view, different assignment: n = 172

| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| natural holdout | 6 | 7 | 11 | 15 | 34 | 99 |
| hard-order test view | 56 | 47 | 24 | 10 | 9 | 26 |

## 3D
### Distributions
| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| V2 baseline K3 (old, not new) | 1 | 27 | 13 | 63 | 146 | 107 |
| natural source strength of the same layouts | 0 | 6 | 13 | 63 | 146 | 128 |
| target | 125 | 107 | 54 | 36 | 18 | 17 |
| V3 selected | 125 | 76 | 42 | 34 | 63 | 17 |
| deficit (+ = short) | 0 | 31 | 12 | 2 | -45 | 0 |

### Jobs
```
{
 "total": 356,
 "pilot": 40,
 "bulk": 316,
 "by_split": {
  "train": 265,
  "val": 40,
  "test": 51
 },
 "handed_to_gvlab": 0,
 "outcomes": {
  "ACCEPTED": 202,
  "TEACH_REJECTED": 44,
  "NO_IMPROVEMENT": 5,
  "NOT_STARTED_OR_IN_FLIGHT_AT_CAP (MISSING)": 104,
  "ADMIN_STOP (MISSING)": 1
 },
 "start_strength_of_all_jobs": {
  "1/6": 0,
  "2/6": 29,
  "3/6": 62,
  "4/6": 68,
  "5/6": 166,
  "6/6": 31
 },
 "final_strength_of_accepted_jobs": {
  "1/6": 144,
  "2/6": 47,
  "3/6": 8,
  "4/6": 3,
  "5/6": 0,
  "6/6": 0
 }
}
```
Start -> final (accepted strength, or `none`):
| | 1 | 2 | 3 | 4 | none |
|---|---:|---:|---:|---:|---:|
| start 2/6 | 13 | 0 | 0 | 0 | 8 |
| start 3/6 | 29 | 6 | 0 | 0 | 9 |
| start 4/6 | 26 | 10 | 1 | 0 | 8 |
| start 5/6 | 65 | 26 | 6 | 3 | 16 |
| start 6/6 | 11 | 5 | 1 | 0 | 8 |

### New verified roots
```
{
 "saved": 202,
 "gate": {
  "PASS": 202
 },
 "gate_rule": "hard3d.finish_checked: every teacher-labelled order re-executed by perm3d.seq on a fresh MuJoCo env before saving",
 "by_strength_all": {
  "1/6": 144,
  "2/6": 47,
  "3/6": 8,
  "4/6": 3,
  "5/6": 0,
  "6/6": 0
 },
 "by_strength_gate_pass": {
  "1/6": 144,
  "2/6": 47,
  "3/6": 8,
  "4/6": 3,
  "5/6": 0,
  "6/6": 0
 },
 "layouts_improved": 202
}
```
Earlier (V1 DEPSEEK) 3D children re-checked on a fresh env: ```{"checked": 98, "pass": 98, "fail": [], "error": []}```

### Selection
```
{
 "version": "3D_K3_STRENGTH_SELECTION_V3",
 "targets": {
  "1": 125,
  "2": 107,
  "3": 54,
  "4": 36,
  "5": 18,
  "6": 17
 },
 "selected_distribution": {
  "1/6": 125,
  "2/6": 76,
  "3/6": 42,
  "4/6": 34,
  "5/6": 63,
  "6/6": 17
 },
 "deficit_vs_target": {
  "1/6": 0,
  "2/6": 31,
  "3/6": 12,
  "4/6": 2,
  "5/6": -45,
  "6/6": 0
 },
 "layouts_with_option": {
  "1/6": 145,
  "2/6": 76,
  "3/6": 70,
  "4/6": 71,
  "5/6": 166,
  "6/6": 128
 },
 "n_layouts": 357,
 "excluded_by_gates": {},
 "xy_checked_selected": 182,
 "xy_verified_selected": 177,
 "source_mix": {
  "NEW_HARD_ORDER": 182,
  "ORIGINAL_SELECTED": 121,
  "NEW_DEPENDENCE_SEEKING": 54
 },
 "by_split": {
  "train": {
   "1/6": 96,
   "2/6": 63,
   "3/6": 27,
   "4/6": 23,
   "5/6": 45,
   "6/6": 12
  },
  "val": {
   "1/6": 9,
   "2/6": 7,
   "3/6": 8,
   "4/6": 4,
   "5/6": 7,
   "6/6": 5
  },
  "test": {
   "1/6": 20,
   "2/6": 6,
   "3/6": 7,
   "4/6": 7,
   "5/6": 11,
   "6/6": 0
  }
 },
 "vs_full_612_target": {
  "target": {
   "1/6": 214,
   "2/6": 184,
   "3/6": 92,
   "4/6": 61,
   "5/6": 31,
   "6/6": 30
  },
  "selected_published_357": {
   "1/6": 125,
   "2/6": 76,
   "3/6": 42,
   "4/6": 34,
   "5/6": 63,
   "6/6": 17
  },
  "remaining_for_unpublished_255": {
   "1/6": 89,
   "2/6": 108,
   "3/6": 50,
   "4/6": 27,
   "5/6": 0,
   "6/6": 13
  }
 }
}
```

### Reserves
| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| unselected gate-pass hard roots | 20 | 0 | 0 | 0 | 0 | 0 |
| layouts with an unused option at s | 20 | 0 | 28 | 37 | 103 | 111 |

### Uniqueness and lineage
```
{
 "rows_total": 1990,
 "rows_total_v2": 1990,
 "k_counts_v3": {
  "0": 511,
  "1": 357,
  "2": 357,
  "NONE": 408,
  "3": 357
 },
 "k_counts_v2": {
  "0": 511,
  "1": 357,
  "2": 357,
  "3": 357,
  "NONE": 408
 },
 "unique_root_ids": true,
 "unique_k3_layouts": true,
 "k3_layout_set_equals_v2": true,
 "non_k3_rows_identical_to_v2": true,
 "lineage_failures": {}
}
```

### Witness and hash integrity (selected new roots; witnesses re-hashed from content)
```
{"ok": 2070}
```

### Natural-distribution holdout view
test-split K3 layouts, each with its ORIGINAL source assignment and its natural source strength (the 6-order outcome of the published original root); same layouts as the hard-order test view, different assignment: n = 51

| | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---:|---:|---:|---:|---:|---:|
| natural holdout | 0 | 2 | 3 | 8 | 24 | 14 |
| hard-order test view | 20 | 6 | 7 | 7 | 11 | 0 |

## 3D completed vs unpublished
```
{
 "target": {
  "1/6": 214,
  "2/6": 184,
  "3/6": 92,
  "4/6": 61,
  "5/6": 31,
  "6/6": 30
 },
 "selected_published_357": {
  "1/6": 125,
  "2/6": 76,
  "3/6": 42,
  "4/6": 34,
  "5/6": 63,
  "6/6": 17
 },
 "remaining_for_unpublished_255": {
  "1/6": 89,
  "2/6": 108,
  "3/6": 50,
  "4/6": 27,
  "5/6": 0,
  "6/6": 13
 }
}
```
teammate's 255 K3 roots (of 510) not published/verified -> not counted; 3D K3 is 357/612 layouts
