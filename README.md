# Latent Causal Infeasibility for Long-Horizon TAMP

> **Branch `naren/dataset-done`** — full workspace snapshot taken 2026-11-11 after the Approach B 2D + 3D dataset
> generation (including the K3 hard-order sidecar), updated 2026-11-12 with the final 3D dataset (V4, 2,500 scenes) and
> the final readiness gate. It contains code, reports, run outputs and the generated data. Nothing has been trained.

## Where things are (this branch)

| Path | Contents |
|---|---|
| `*.py`, `*.toml`, `fixtures.json`, `requirements.lock` (root) | Core code and configs. The scripts import each other by plain name and read configs from the root, so they stay here. |
| `tests/` | Test suite. |
| `docs/methodology/`, `docs/methodology_pdfs/` | Methodology and implementation guides (Markdown and PDF). |
| `docs/audits/`, `docs/status/`, `docs/archives/`, `docs/addenda/`, `docs/archive/` | Audits, status notes, archived guides and contract addenda. |
| `instruction-phase-md/` | Instruction contracts, grouped: `numbered_contracts/`, `approach_b/` (incl. `plan.md`, the Approach B final implementation plan), `approach_d/`, `general/`. |
| `responses-phases/` | Numbered stage reports, grouped in blocks of 25 (`0001-0025/`, ...) plus `misc/`. |
| `runs/` | Run outputs per stage (G0–G4, P6–P17, Approach D). |
| `visualizations/`, `teaser-assets/`, `slides-a-b-c/`, `PoC-takeaway/` | Figures, teaser images, slides. |
| `order_classification_2d/`, `order_classification_3d/` | Six-permutation order classification of the 2D and 3D target tasks (code, per-scene outcomes, source snapshot). |
| `approach_b_reuse_audit/` | Approach B existing-data reuse audit. |
| `final_dataset_generation/` | Final 2D + 3D dataset generation: dependence-seeking generators, stores (`d2/`, `d3_*/`), selection manifests V2, final reports. |
| `final_dataset_generation/k3_hard/` | K3 hard-order generation: generators, ledgers, stores, consistency and X/Y checks. |
| `final_dataset_generation/k3_hard/K3_HARD_ORDER_V1/` | The K3 hard-order deliverables: generation report, V3 strength selection manifest, X/Y validation, resource report, readiness JSON, SHA256SUMS. |
| `final_dataset_generation/final3d_v4/` | Final 3D V4 work: K3 completion (fresh-env legacy checks, generated layouts `gen_k3*`, hard-order stores `hard*`), finalized X/Y runs, witness stores, code. The local symlink view `ds_view/` is not included. |
| `final_dataset_generation/FINAL_3D_DATASET_V4/` | The 3D V4 deliverables: 2,500-scene selection (NONE 408, K0 511, K1 357, K2 612, K3 612), X/Y label manifest, reports, readiness JSON, new root files, SHA256SUMS. |
| `final_dataset_generation/FINAL_READINESS_GATE/` | Final readiness gate for 2D (5,000) and 3D (2,500): the 13 omission verdicts, independent 3D replay audit, complete 2D finalized X/Y, label distributions, integrity gates, `FINAL_TRAINING_READINESS.json`, proposed corrections (not applied), code, raw results and witnesses, SHA256SUMS. |
| `visualizations/3d_x022/` | 3D renders of scene s1 X-022: side-grasp approach and top views after each placement. |
| `ST_dummy/` | Dummy ST run outputs. |

Notes for this snapshot:

- Compared with the working tree, only loose documents were moved (root PDFs/Markdown/zip into `docs/`, and the two
  phase folders into sub-folders). Links below that point at root-level PDFs or flat `responses-phases/` files refer
  to the old locations.
- Some manifests record absolute local paths (for example `host_store`); they are provenance only.
- Not included: Python caches, virtual environments and nested git worktrees.

---

Intervention-supervised joint relocation for a prescribed, frozen target motion.

- Scientific semantics: `latent_causal_tamp_specification_v1_5.pdf` (Methodology v1.5, initial-scene repair
  without trajectory inputs; protocol `INITIAL_SCENE_ONE_SHOT_V1`)
- Stages, configs, files, gates: `latent_causal_tamp_implementation_guide_v1_7.pdf` (Guide v1.7)
- G0-G3 were built under Methodology v1.4 / Guide v1.6, archived byte-identically in
  [`docs/archive/`](docs/archive/) (sha256 recorded there); their frozen-motion runs remain valid at their
  original scope as `FROZEN_CONTROL` (archives byte-unchanged).
- Contract addenda (versioned refinements, never edits of the PDFs):
  [`docs/addenda/A1_target_end_policy_v1.md`](docs/addenda/A1_target_end_policy_v1.md) — G4A target completion =
  goal + certified safe retreat; HOME return is an optional diagnostic.

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
| G2 | frozen reference actions (D1, D2), privileged one-edit interventions, per-object fixed-action oracle | implemented; report `responses-phases/0005_G2_completion.md` |
| G3 | A0 min-cost matching + Murty k-best, Hall certificates, executable move-once 3R repair search, restricted-domain control | implemented; report `responses-phases/0006_G3_completion.md` |
| G3.5 | objective migration: one-shot initial-scene protocol, static/relocation/target separation, R0-R6 cases | implemented; report `responses-phases/0007_G3_5_completion.md` |
| G4A | certificate audit, automatic candidates, abort tests, 20-root audit, seed/order panels | implemented; report `responses-phases/0008_G4A_completion.md` |
| G4A follow-up | reporting reconciliation; bounded offline teacher-budget diagnostic on g4a_r04/r14/r15 (all-stay) | implemented; report `responses-phases/0009_G4A_followup_completion.md` |
| G4B–G10 | see Guide v1.7 | not started |

The 2D robot profile was tested at G1 (`robot_profile_hash` in `runs/g1_robot/result.json`);
robot motion claims are kinematic only (`PLANAR_ARM_KINEMATIC_SKILL`), never dynamic or hardware.

## Layout (flat; files appear only when their stage arrives)

| File | Responsibility |
|---|---|
| `config.toml` | 2D suite values; unknown/missing keys fail |
| `config.py` | config schema/validation, canonical hashes, fixture reference policy (split from `scene.py`) |
| `fixtures.json` | reproducible cases: root/variant IDs, seeds, lineage |
| `scene.py` | lattice, scene state, candidate maps, snapshots, scene hash |
| `geometry.py` | 3R FK/IK, collision bodies (links, housings, palm, rail, fingers), exact 2D distances, conservative interval certifier |
| `motion.py` | recorded trajectories and hashes, IK-tracked lines, certified chains, replay, path sampling |
| `planner.py` | certified connectors: direct, guide line, link-0 sweep certificate, seeded RRT-Connect (joint or held-object pose space) |
| `skill.py` | six-phase side-grasp skill (pick/place screening, connectors) and its JSON summary |
| `viz.py` | clean learner observation, drawing primitives (robot drawn from `geometry.bodies`), G0 overview |
| `figures.py` | G1 task, audit and corner figures and GIFs composed from recorded results |
| `interventions.py` | frozen action identity, privileged diagnostic edits and their audit, F_fixed / c_i / d_I / Delta_I, families |
| `intervention_figures.py` | G2 lineage, attribution and fixed-action replay figures and GIFs |
| `solve.py` | frozen A0 control (cell status, matching, Murty k-best, Hall, restoration) |
| `proposals.py` | initial-scene endpoint geometry: static endpoint check, goal-overlap producer, action-level lower bound, frozen primary ranking, G4A automatic generator `B1_GEOMETRIC_V1` (moved from `solve.py` at G4A) |
| `certificates.py` | G4A independent certificate checker (goal overlap, first mover, static, lower bound) |
| `verify.py` | move-once relocations from the achieved state; FROZEN_CONTROL search (gamma_0 connector, replay, LB/UB) and G3.5 `realize`/`plan_repair` (end at retreat, no target query) |
| `repair_figures.py` | G3 relocation panels, rejected-move panels, repair GIFs |
| `assignment_figures.py` | G3 A0 boards, restricted vs all-supported control, verification summary, G3 figure set |
| `data.py` | G3.5 query records: learner allowlist, observation / action-context hashes, clean learner tensors |
| `evaluate.py` | G3.5 post-commit target evaluation, primary one-shot episode (event trace, commitment boundary), offline case audit |
| `cases.py` | G3.5 R0-R6 queries: scene construction, controls, evidence and bounds, run record, readiness |
| `case_figures.py` | G3.5 figures A-F and clean learner observations |
| `roots.py` | G4A stratified development roots, construction ledger, frozen audit plan and panel selection |
| `audit.py` | G4A collection (primary episodes, first-pass teacher audit, seed/order panels) and its commands |
| `coverage.py` | G4A first-pass / enriched labels, coverage, cohorts and readiness |
| `controls.py` | G4A adversarial certificate suite, G3.5 certificate re-audit, execution fault injection |
| `audit_figures.py` | G4A figures A-H, repair GIFs, clean learner observations |
| `teacher.py` | G4A follow-up: named offline teacher schedule `TEACHER_BUDGET_V1`, frozen plan, in-flight process-tree CPU guard, isolated worker, witness check |
| `teacher_figures.py` | G4A follow-up figures: reconciliation, budget panel, scenes, witness GIFs |
| `diagnostics.py` | figures that explain verification verdicts (rejections, certificates, budgets, IK tracking) |
| `run.py` | the sole command dispatcher and cross-stage replay; stage command bodies live in their owning modules (split at G4A) |
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
- `FINAL_DEV_SCENE_PLANNED` / `DEVELOPMENT_ONLY`: an explicitly sparse development scene
  (< 30 obstacles, e.g. D1, D2) whose reference is planned with its final background
  present. Never a primary claim; dense primary roots must hold 30-40 obstacles.

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
python run.py intervene --out runs/g2_interventions           # ~2.5 min: D1/D2 frozen actions + interventions
python run.py solve --out runs/g3_repairs                     # G3: A0 + executable repairs (see report 0006 for time)
python run.py replay --run runs/g3_repairs --report <path>    # re-certify relocations and gamma_0 in the final scenes
python run.py case-analysis --out runs/g3_5_initial_scene     # G3.5: R0-R6 under INITIAL_SCENE_ONE_SHOT_V1 (~2.5 min)
python run.py g4a-plan --out runs/g4a_evidence_audit          # G4A: freeze roots/candidates/panels (no outcomes)
python run.py g4a-audit --out runs/g4a_evidence_audit         # G4A: bounded audit, panels, controls, figures
python run.py teacher-plan --out runs/g4a_teacher_budget_diagnostic   # G4A follow-up: freeze (no outcomes)
python run.py teacher-run --out runs/g4a_teacher_budget_diagnostic    # guarded: <= 6 evals, 900 CPU-s each, 2 CPU-h
```

Each run writes `config.json`, `scene.json`, `result.json`, `overview.png`,
`observation.png` (clean learner RGB), `arrays.npz`, `metrics.csv`, `manifest.json`.

Tested with the versions in `requirements.lock` (Python ≥ 3.11 for `tomllib`).
