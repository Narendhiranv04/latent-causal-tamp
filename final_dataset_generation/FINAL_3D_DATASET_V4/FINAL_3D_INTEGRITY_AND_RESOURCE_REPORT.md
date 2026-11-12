# FINAL 3D integrity and resource report

## Integrity

```
{
 "n_rows": 2500,
 "class_counts": {
  "NONE": 408,
  "0": 511,
  "1": 357,
  "2": 612,
  "3": 612
 },
 "class_counts_ok": true,
 "root_ids_unique": true,
 "k3_layouts_unique": true,
 "frozen_classes_equal_published": true,
 "published_k3_layouts_all_present": true,
 "k4_not_in_main": true,
 "row_file_and_lineage_failures": {},
 "split_conflicts_with_frozen_manifest": 0,
 "witness_check": {
  "root:ok": 4513,
  "xy:ok": 11407
 },
 "2d_and_v2_selection_files_unchanged": true,
 "v3_k3_package_unchanged": true,
 "training_started": false
}
```

## Resources

```
{
 "limits": {
  "laptop": "<= 27 workers (of 32 logical CPUs)",
  "gvlab": "<= 16 workers (of 24), >= 3 free, from 2026-11-11 21:01 IST (user approval)"
 },
 "stage1_fresh_legacy_cpu_h_laptop": 40.7,
 "stage1_fixed_object_cpu_h_laptop": 2.1,
 "generation_worker_wall_h": {
  "laptop_lap4": 59.4,
  "laptop_lap5": 52.1,
  "gvlab_srv5": 29.4
 },
 "generated_checks_cpu_h_laptop": 3.7,
 "hard_order_cpu_h": {
  "laptop": 28.3,
  "gvlab": 69.1
 },
 "xy_and_yneg_cpu_h": {
  "laptop": 43.1,
  "gvlab": 22.3
 }
}
```

Parity: laptop vs earlier gvlab evidence 24/24 legacy orders and 3/3 X/Y roots identical; gvlab vs laptop 48/48 fresh-env orders identical (incl. witness ids) before gvlab was used (from 2026-11-11 21:01 IST, user-approved, <= 16 workers).
