# Latent Causal Infeasibility for Long-Horizon TAMP

Intervention-supervised joint relocation for a prescribed, frozen target motion.

- Scientific semantics: `latent_causal_tamp_specification_v1_4.pdf` (Methodology v1.4)
- Stages, configs, files, gates: `latent_causal_tamp_implementation_guide_v1_6.pdf` (Guide v1.6)

Development follows the guide's stage registry **G0–G10** one gate at a time; each
gate ends with a stage report and an explicit STOP.

Every substantive response is saved as the next numbered report in
`responses-phases/` and committed together with the work it describes, then
pushed to `main` of `github.com/Narendhiranv04/latent-causal-tamp`.

## Status

| Stage | Scope | State |
|---|---|---|
| G0 | scene, records, visual foundations | implemented; report `responses-phases/0001_G0_completion.md` |
| G1–G10 | see Guide v1.6 §5 | not started |

The 2D robot profile in `config.toml` is **provisional** and untested; robot poses
drawn before G1 are `SCHEMATIC / NOT_RUN`.

## Layout (flat; files appear only when their stage arrives)

| File | Responsibility |
|---|---|
| `config.toml` | 2D suite values; unknown/missing keys fail |
| `fixtures.json` | reproducible cases: root/variant IDs, seeds, lineage |
| `scene.py` | config validation, lattice, scene state, candidate maps, snapshots, hashes |
| `viz.py` | clean learner observation, robot body shapes, overview figures |
| `run.py` | the sole command dispatcher |
| `tests/` | one test file per stage component |
| `runs/` | flat per-run output directories |
| `responses-phases/` | one numbered, immutable Markdown report per substantive response (`NNNN_<topic>.md`) |
| `instruction-phase-md/` | user-supplied workflow instructions and stage reviews |

## Conventions

Metres, radians, float64 geometry. World x is right, world y is backward on the
support. Lattice row r grows with +y, column c with +x; cell (r, c) has physical ID
`r*8 + c` and centre `((c+½)·0.08, (r+½)·0.08)`. In rendered images pixel row v grows
*downward* (with −y), so the image is row-reversed relative to the lattice.

## Run

```sh
python -m pytest tests -q
python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
```

Each run writes `config.json`, `scene.json`, `result.json`, `overview.png`,
`observation.png` (clean learner RGB), `arrays.npz`, `metrics.csv`, `manifest.json`.

Tested with the versions in `requirements.lock` (Python ≥ 3.11 for `tomllib`).
