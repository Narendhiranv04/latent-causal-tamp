# Approach B final: implementation audit (2026-11-12)

Inputs read: `plan.md` v2.0, branch `approach-b-universal-search` @ 45b0fb05 (2D Approach B code), `rss-3d-learning` branch
`naren/approachb-3d-learning` @ 4d2d3dbf (3D samplers and X/Y port), the FINAL_READINESS_GATE package and FINAL_3D_DATASET_V4.
Scope (user, 2026-11-12): gvlab GPU 0 only; the eight external 3D baselines are deferred; 3D goes up to running our own model.

## Reusable and verified (used unchanged)

| Component | Source | Use here |
|---|---|---|
| Exact root-consistent X/Y math: `log_py`, `log_px`, `log_evidence`, `batched_log_evidence`, `marginals`, `energy_root`, `brute_force`, selftest | `bxy_core.py` (2D) → `xy3d.py` (batched, parity-verified vs e113c6680) | `xy.py` (copied verbatim) |
| Batched F2 / F3 / F5 network (`XYNet`), views (`make_view`, `labels_for`, `collate`), arms D / E / G / DIRECT, `choose` (cost rule) | `xy3d.py` | `xy.py` |
| Placement samplers: SceneEncoder, cVAE, flow matching, uniform and band-stratified controls | `approachb_3d_learning/src/models.py` | `placement.py`, generalized from the fixed 6×6 grid to R×C |
| 2D finalized X/Y teacher with independent replay | `bxy_teacher.py` @ 68183081d | final 2D execution / verification |
| 3D finalized X/Y teacher and replay | `final3d_v4/code/fin3d.py` + `bwlphys.py`, gate `rpl3d.py` | 3D label completion, final 3D verification |
| Universal bounded search (fair best-first, statuses, sealed resume) | `bxy_fullsearch.py` | design reference for `search.py` |

## Reusable but corrected or reconfigured

| Item | Change | Why |
|---|---|---|
| X/Y arms | GEO features off and SYM auxiliary off in every arm; travel weight 0 in P2 | plan 4.4 specifies the exact observed-data NLL; GEO features are not defined uniformly for 2D and 3D; travel is fitted in P3 |
| X/Y precision | float32 on GPU (source used float64 on CPU) | RTX 4090 FP64 throughput is a small fraction of FP32; selftest stays in float64 |
| 2D X/Y encoder inputs | geometry-only form (no DINOv2 visual features) | the 5,000 class-quota roots have no visual features; the source supports `vision=False` |
| Samplers | grid size, base pose and Chebyshev bands parameterized by domain; 2D attributes = radius / fixed flag | 2D is an 8×8 lattice with legal cells; 3D features are identical to the earlier 3D study |

## Missing and implemented here

- `contracts.py`: verified handoff, qualified-training exception, evaluation masks, compiled snapshot, loader / schema report.
- `labelfill3d.py`: 3D label completion (below).
- `placement.py` data builders for the 2D and 3D Q2 placement datasets, training, evaluation and proposal API.
- `xy.py` snapshot loader, training loop, held-out metrics (binary-Z NLL / AUROC / AUPRC / Brier / ECE, matched-endpoint order accuracy).
- Still to build: travel targets and head (P3), branch-local search plus the one-shot comparator (P4), end-to-end runner (P5).

## Data facts found during the handoff

- 2D: finalized X/Y complete for every selected query (gate). 3D: finalized X/Y exist for K2/K3 only; the 357 K1 roots
  had none and the 511 K0 roots had no finalized Y at the unedited scene (V4 listed them as legacy-only). They are being completed with
  the unchanged fin3d teacher into a separate store and replayed (`labelfill3d.py`), recorded as a new snapshot version; no existing label changes.
- Repair certificate available: legacy-verified minimal K + finalized X=1/Y=1 order at that K + no shorter finalized repair found by the omission
  check. This is a relative certificate, not a proof of global minimality under the finalized protocol.
- 2D travel witnesses exist for queries labelled in the gate (relocation + connector + target arrays); the 807 reused K3 roots carry no
  witness ids. 3D travel witnesses exist for fin3d-labelled rows (relocation plans, connector path, target plan).
