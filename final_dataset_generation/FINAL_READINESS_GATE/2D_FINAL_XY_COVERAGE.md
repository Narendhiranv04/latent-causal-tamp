# 2D finalized X/Y coverage (2D_K3_STRENGTH_SELECTION_V3, 5,000 scenes)

**Result: every selected K0–K3 query has a finalized X and Y: 2750 of 2750 K1–K3 scenes complete, 1250 of 1,250 K0 scenes complete, 0 missing.**

- **Teacher:** BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1 (`bxy_teacher.py`, unchanged since commit 68183081d), booted with each record's own geometry implementation and one exact DetPhysics cache per root, exactly as `k3_hard/xy2d.py`.
- **X:** ordered relocations with carried state, plus the connector to q_ref.
- **Y:** target from q_ref at the shared endpoint, one query per endpoint.
- **Replay:** every positive X and Y passed the teacher's built-in independent replay (geometric re-certification, continuity, placement, q_ref endpoint). Failures are binary teacher outcomes under the pinned finite budget.
- **Administrative failures:** wall cap 1,800 s per query. A hit is MISSING, never 0; none occurred.
- **Reuse:** 807 K3 hard-order scenes reuse `k3_hard/xy2d_all.jsonl` (same teacher, same root file, same assignment, same q_ref). Parity re-run on a seeded sample: X 420/420, Y 70/70.
- **Empty endpoint:** every K1–K3 / NONE scene has a finalized Y query at its unedited scene. It agrees with the legacy labels.original in 3750/3750 scenes; the legacy label is kept separately.
- **NONE:** 1,000 scenes ({'test': 150, 'val': 150, 'train': 700}) keep their audited no-repair provenance. No X/Y is fabricated for a nonexistent corrective sequence; they contribute only empty-endpoint Y labels.

## Coverage by K and split (selected corrective sequences)

| K | queries per scene | split | order rows | complete | missing | X provenance |
|---|---:|---:|---:|---:|---:|---:|
| K0 | empty corrective sequence | train | 875 | 875 | 0 | EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION: 875 |
| K0 | empty corrective sequence | val | 188 | 188 | 0 | EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION: 188 |
| K0 | empty corrective sequence | test | 187 | 187 | 0 | EMPTY_SEQUENCE_X_IS_1_BY_DEFINITION: 187 |
| K1 | 1 relocation, 1 order | train | 560 | 560 | 0 | BXY_X_TEACHER_V1: 560 |
| K1 | 1 relocation, 1 order | val | 120 | 120 | 0 | BXY_X_TEACHER_V1: 120 |
| K1 | 1 relocation, 1 order | test | 120 | 120 | 0 | BXY_X_TEACHER_V1: 120 |
| K2 | 2 orders | train | 1120 | 1120 | 0 | BXY_X_TEACHER_V1: 1120 |
| K2 | 2 orders | val | 240 | 240 | 0 | BXY_X_TEACHER_V1: 240 |
| K2 | 2 orders | test | 240 | 240 | 0 | BXY_X_TEACHER_V1: 240 |
| K3 | 6 orders | train | 4830 | 4830 | 0 | BXY_X_TEACHER_V1: 1404; REUSED_XY2D_K3HARD_V1: 3426 |
| K3 | 6 orders | val | 1038 | 1038 | 0 | BXY_X_TEACHER_V1: 306; REUSED_XY2D_K3HARD_V1: 732 |
| K3 | 6 orders | test | 1032 | 1032 | 0 | BXY_X_TEACHER_V1: 348; REUSED_XY2D_K3HARD_V1: 684 |

## Legacy vs finalized K3 strength

If finalized X strength differs from legacy strength, the learning view uses the finalized X. Legacy strength is kept as metadata (`legacy_y` per order row).

| strength | finalized train | finalized val | finalized test | legacy train | legacy val | legacy test |
|---|---:|---:|---:|---:|---:|---:|
| 0/6 | 20 | 4 | 3 | 0 | 0 | 0 |
| 1/6 | 238 | 59 | 45 | 315 | 73 | 62 |
| 2/6 | 200 | 42 | 47 | 214 | 44 | 45 |
| 3/6 | 153 | 29 | 29 | 110 | 23 | 20 |
| 4/6 | 58 | 9 | 11 | 59 | 7 | 10 |
| 5/6 | 64 | 7 | 9 | 50 | 5 | 9 |
| 6/6 | 72 | 23 | 28 | 57 | 21 | 26 |

## K consistency under the finalized protocol

- Omission queries with X = 1 and Y = 1 (a proven shorter repair): **0**.
- Selected scenes where **no** order of the selected assignment reaches X = 1 with Y = 1: **60**. All have Y = 1 and a verified legacy repair; every order fails finalized X, at the connector back to q_ref or at a relocation under the finite budget. These are not proven K errors, but the selected K-repair is not verified under the finalized protocol.

| K | split | scenes | typical X failure |
|---|---:|---:|---:|
| K1 | test | 3 | UNKNOWN_TRANSIT@connector |
| K1 | train | 17 | UNKNOWN_TRANSIT@connector |
| K1 | val | 3 | UNKNOWN_TRANSIT@connector |
| K2 | test | 1 | UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |
| K2 | train | 7 | CERTIFIED_INFEASIBLE@relocation; UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |
| K2 | val | 2 | UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |
| K3 | test | 3 | CERTIFIED_INFEASIBLE@relocation; UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |
| K3 | train | 20 | CERTIFIED_INFEASIBLE@relocation; UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |
| K3 | val | 4 | CERTIFIED_INFEASIBLE@relocation; UNKNOWN_PLANNER@relocation; UNKNOWN_TRANSIT@connector |

The IDs and options are in `manifests/2D_PROPOSED_CORRECTIONS.json`.

Machine-readable: `manifests/2D_FINAL_XY_LABEL_MANIFEST.json`.
