# V3.4 Phase 0 audit — models, provenance, resources (2026-11-17)

**Source.** Branch `naren/approach-b-v3-4-final-benchmark` from `0274fe8b664c80e41aaf6146e2200353eb70d30b`. Archived V3.x reports and branches are untouched.

## Final models: verified, scratch-trained

| Model | Domain | sha256 | Init | Training data |
|---|---|---|---|---|
| S-expanded `scratch_all` s0 | 2D | `a01f25eb…f1e918` | scratch (`prov.init`) | `abf_v32_fb0eef4f5ff433ee` (train data sha `963c16b2…`) |
| S-expanded `scratch_all` s0 | 3D | `6a0e26c4…e84be472` | scratch | same snapshot |
| D-expanded s0 / s1 / s2 | 2D | `0fa126da…`, `ea6dba7a…`, `928a6e2b…` | `xy.fit`: `torch.manual_seed`, then a fresh `XYNet`, no state loaded | same snapshot |
| D-expanded s0 / s1 / s2 | 3D | `c02afcbc…`, `88f49a60…`, `948ac820…` | same | same snapshot |

- All 12 V3.3 sampler checkpoints on the laptop match `MODELS_SHA256`, and all six D-expanded checkpoints match V3.2 `C/EXPANDED_SHA256`. Nothing was retrained.
- The Q2 scaler JSONs (`884b3567…`, `36a94926…`) are TRAIN-only normalisation constants recorded in the sampler provenance. They are not neural weights.
- Inference loads models only through the bundle (`benchmark.load_bundle`). No `init_from_q2` / `PL.load` path is used.

## P1 parity (portable `benchmark.py predict` vs archived V3.3 exhaustive records)

| Domain | Device | Proposals equal | Decisions equal | max abs Δp11 |
|---|---|---|---|---|
| 2D | laptop RTX 5060 (torch 2.9.1 cu128) | 751 / 751 | 751 / 751 | 3.6e-7 |
| 3D | laptop RTX 5060 | 364 / 364 | 364 / 364 | 4.2e-7 |
| 3D | CPU | 273 / 301 | 300 / 301 | 5.4e-7 |

The proposal RNG is part of the method (a per-root CUDA generator, seed 0). On the CPU, the generator stream changes tie-level top-M proposals, so CPU inference is documented as a **non-identical fallback**.

## Teacher code

`evaluate._verify_job` / `construct._boot` are byte-identical to the V3.3 parity-checked laptop teacher path (`~/abf_v31_lapverify/code`). `teacher2d.py` sha256 is `8dd8bc46…`.

## Generator source recovery (Option B cohort)

**Available locally:**
- 2D `run_2d_plus` (ROUTE2D_V6), `perm2d`, `dep2d`, `k3_hard` (hard2d).
- 3D `run_shelf66_full` (SHELF66V3), `run_shelf66_none` + `none_dense` + `trim_none66_v3`, `perm3d`, `dep3d`, `hard3d` (V3/V4).

**Missing on every authorized host:**
- `bd_2d_cover_table.json`: a geometry pre-filter of the 2D exact layout search, built on a teammate's machine. A reconstruction is being validated against the production ledger.
- 2D ROUTE2D_V1–V5 and the CONV1 conversion: conversion needs the table.
- 3D SHELF66V2 construction code.
- 3D dense-NONE ledger and NONE_TRIM66_V1 code.

These are registered as provenance shifts in `config/final_protocol.yaml`.

**Teacher config hashes:** 2D `90d3eb68e8a42108` and 3D `8d521b1f6d23db23` are asserted by the generation driver on every host before anything is written (laptop, gvlab, girish).

## Resources: dynamic, every host keeps at least 4 threads free

| Host | Hardware | V3.4 use |
|---|---|---|
| Laptop | Ryzen 9 8940HX 32T, 31 GB (about 7–8 GB available), RTX 5060 8 GB | 2D generation, guarded by RAM (≥ 2 GB free) and temperature (≤ 97 °C); all Approach B inference on the GPU; power profile set to Performance |
| gvlab | 24T, 62 GB, 2× RTX 4090 | 3D generation, 20 workers on CPUs 0–19 (user authorised 2026-11-17 18:25 IST) |
| girish | i9-12900HX 24T, 31 GB, RTX 3080 Ti | 3D generation, DISCO-aware watchdog: workers ≤ 24 − 4 − DISCO cores − 2. DISCO (user `longhorizon`, `disco_grid_stage2`) is active and is never touched |

Per-decision log: `~/abf_v34/logs/RESOURCE_LOG.jsonl` plus each host's `gen/*/RESOURCE.log`, `STATUS.json`.

**Gate P0: PASS for models, provenance and parity.** The cohort generation sources are PARTIAL until the 2D cover-table question is resolved. Only the 424 2D exact-search slots are blocked.
