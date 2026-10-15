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
| G1 | 3R kinematics, collision bodies, certified six-phase skill, 64-cell audit | implemented; report `responses-phases/0003_G1_completion.md` |
| G1 hardening | sound IK-tracking labels, replay record checks, planner stop provenance, G2 reference policy | report `responses-phases/0004_G1_hardening.md` |
| G2–G10 | see Guide v1.6 §5 | not started |

The 2D robot profile was tested at G1 (`robot_profile_hash` in `runs/g1_robot/result.json`);
robot motion claims are kinematic only (`PLANAR_ARM_KINEMATIC_SKILL`), never dynamic or hardware.

## Layout (flat; files appear only when their stage arrives)

| File | Responsibility |
|---|---|
| `config.toml` | 2D suite values; unknown/missing keys fail |
| `fixtures.json` | reproducible cases: root/variant IDs, seeds, lineage |
| `scene.py` | config validation, lattice, scene state, candidate maps, snapshots, hashes |
| `geometry.py` | 3R FK/IK, collision bodies (links, housings, palm, rail, fingers), exact 2D distances, conservative interval certifier |
| `motion.py` | recorded trajectories and hashes, IK-tracked lines, certified chains, replay, path sampling |
| `planner.py` | certified connectors: direct, guide line, link-0 sweep certificate, seeded RRT-Connect (joint or held-object pose space) |
| `skill.py` | six-phase side-grasp skill (pick/place screening, connectors) and its JSON summary |
| `viz.py` | clean learner observation, drawing primitives (robot drawn from `geometry.bodies`), G0 overview |
| `figures.py` | G1 task, audit and corner figures and GIFs composed from recorded results |
| `diagnostics.py` | figures that explain verification verdicts (rejections, certificates, budgets, IK tracking) |
| `run.py` | the sole command dispatcher |
| `tests/` | one test file per stage component |
| `runs/` | flat per-run output directories |
| `responses-phases/` | one numbered, immutable Markdown report per substantive response (`NNNN_<topic>.md`) |
| `instruction-phase-md/` | user-supplied workflow instructions and stage reviews |

## G2 reference-construction policy (report 0004)

From G2 on every fixture must declare `reference_policy` and `benchmark_role`
(enforced by `scene.validate_fixtures`):

- `FINAL_DENSE_PLANNED` / `PRIMARY`: the final 30-40-object clutter is in place while
  the nominal 3R grasp/carry/release/retreat/connector is planned, certified and frozen;
  blocked variants then relocate existing IDs into the frozen sweep.
- `SPARSE_SEEDED_REFERENCE` / `BOOTSTRAP_ONLY`: plan sparse, fill cells clear of the
  sweep, re-verify. Development bootstrap only; never a primary benchmark claim.

Canonical planning budgets are node/evaluation budgets; the wall-time limit is a
safety cap and any result it affects is flagged `wall_clock_dependent`.

## Conventions

Metres, radians, float64 geometry. World x is right, world y is backward on the
support. Lattice row r grows with +y, column c with +x; cell (r, c) has physical ID
`r*8 + c` and centre `((c+½)·0.08, (r+½)·0.08)`. In rendered images pixel row v grows
*downward* (with −y), so the image is row-reversed relative to the lattice.

## Run

```sh
python -m pytest tests -q
python run.py scene --config config.toml --case G0_ILLUSTRATIVE --out runs/g0_scene
python run.py check --config config.toml --out runs/g1_robot   # ~1.5 min with 24 workers
python run.py replay --run runs/g1_robot                      # re-certify stored trajectories
```

Each run writes `config.json`, `scene.json`, `result.json`, `overview.png`,
`observation.png` (clean learner RGB), `arrays.npz`, `metrics.csv`, `manifest.json`.

Tested with the versions in `requirements.lock` (Python ≥ 3.11 for `tomllib`).
