# Dataset card: LEGOLAS_FINAL_v1

**What it is:** shelf (3D, xArm7 + MuJoCo, 6×6 grid at 7.5 cm) and planar (2D, 8×8) rearrangement scenes.
- **Task:** make the target object t0 reachable to its goal by relocating up to 3 obstacles (short horizon), or 4–5 obstacles (3D composition benchmark).
- **Constraints:** each object moves once, to a distinct, initially vacant destination; the target is protected; q_ref connectors join chunks.

**Generators:** BD_GEN_V1 + ROUTE_V15 + SHELF66V3 (3D, teacher BD3DS66_TEACHER_V2, config 8d521b1f) and the planar class-quota generator (2D). No new generator was written for this release; the TEST_FEAS_3D annex uses the unchanged 3D generator.

**Labels:**
- **X:** physical executability of an ordered chunk, with continuous replay.
- **Y:** target feasibility at the endpoint.
- **K_legacy:** a historical class only: a witness length, never a certified minimum K.
- UNKNOWN, budget-relative and operational outcomes are never certified negatives.

**Tracks:**

| Track | Use | 2D | 3D |
|---|---|---:|---:|
| TRAIN / VAL | learning / selection and calibration | 3,802 / 917 | 1,859 / 402 |
| TEST_SHORT | primary short-horizon evaluation (held-out, historically outcome-exposed) | 729 | 370 |
| BENCH_SHORT | V3.4, exposed benchmark (supplementary) | 719 | 395 |
| BENCH_COMP_3D | R8B, exposed fixed composition benchmark (L_ref 4: 68 / 5: 31) | — | 99 |
| TEST_FEAS_3D | independent initial-target feasibility (annex, prospective protocol) | — | see annex seal |
| DEV_EXPOSED / QUARANTINE / EXCLUDE | not used for learning or primary metrics | 30 / 29 / 2 | 20 / 0 / 0 |

**Identity:**
- `scene_id` = S<dom>-<geometric fp>. The geometric fingerprint covers objects (cell, shape and dimensions at 1e-6), the target cell and the goal cell.
- `family_id` = connected component of exact-geometry, 3D object-instance and declared-lineage links.
- `template_id` = the 8-factor construction template.
- Source aliases are kept per record.

**Known limitations:**
- TEST_SHORT is not blind: its outcomes for earlier model generations were viewed.
- V3.4 and R8B share VAL factor templates, at template level only; their geometry is new.
- 2D near-duplicates between independently generated scenes occur at the same rate in every pair of tracks. They are reported, not merged.
- The 3D baselines' V4 split equals our original 3D split.

**Files:**
- `registry.jsonl`, `splits/*.jsonl`, `provenance/*`, `checks/counts.json` and `R10_DATASET_SEAL.json`.
- Large blobs stay on gvlab2 and are referenced by sha256: the snapshot (`abf_r10_70e8ec7db1d4c56b`), Q2 features, and root files.
