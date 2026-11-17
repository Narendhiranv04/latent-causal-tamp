# Reproducing DISCO Stage 2

This document describes the implemented pipeline. It does not certify that a
pending physical evaluation has run. Consult the dated execution ledger and
row-level outcome records for completion status.

Use branch `naren/disco-grid-stage2`. The unchanged physical collection/trainer
engine is commit `89f16995f5ad0d127b3cf3b807cb66bcf9565bfc`. Later controller
commits preserve its exact hashes for resumable training. The Stage 1 release is
`8c5213fd0c7cb739e2358452564320eac1891db5`; its original results are historical.

## Environment and artifacts

The authorized experiment host is `gvlab`. Existing environment:
`/scratch/nav/disco_grid/venv/bin/python` (Python 3.10, Torch 2.5.1+cu124,
NumPy 2.2.6, MuJoCo 3.16). Actual experiments are CPU only. Check installed
versions and host headroom before reproducing; do not install into the shared
environment or assume the GPUs are available.

```sh
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export DISCO_SOURCE_COMMIT="$(git rev-parse HEAD)"
stage_python=/scratch/nav/disco_grid/venv/bin/python
stage_campaign=/scratch/nav/disco_grid/stage2/campaigns/E16_v1_20261117
```

Data and native teachers are existing versioned dependencies, not downloaded by
this script. Their paths are resolved by `baselines/disco_grid/data.py` and the
locked BASE/V2 snapshot manifests. Do not substitute another server's dataset.
`audit/input_audit.json` records snapshot, teacher and preserved checkpoint
hashes. Run `audit_inputs.py` into a **new** output directory to verify the
installed dependencies; it fails on archive mismatch or split conflict.

The campaign holds original interrupted directories, durable query intent/result
records, parent states, accepted trajectory witnesses, atomic tree/RNG
checkpoints, resolved trainer configs, trainer optimizer/RNG checkpoints, exported
policy/value weights and all watchdog cost ledgers. The large real artifacts stay
at this versioned on-host path. Git contains code, reports and small manifests;
it does not replace the physical evidence with hand-entered tables.

## Tests and preservation

From the checkout root, run the lightweight/analytical suite serially while no
DISCO physical/training worker is active:

```sh
nice -n 10 "$stage_python" -m pytest \
  baselines/disco_grid/tests/test_d0_audit.py \
  baselines/disco_grid/tests/test_d2_policy.py \
  baselines/disco_grid/tests/test_d3_d4_mcts_distill.py \
  baselines/disco_grid/tests/test_d6_d7_evaluate.py \
  baselines/disco_grid/tests/test_validation_v2.py \
  baselines/disco_grid/tests/test_stage2.py \
  baselines/disco_grid/tests/test_physical_eval.py -q
```

`campaign_preservation_replay.json` records exact historical prediction replay:
315/315 primary predictions within 1,785 archived arm predictions, with zero
physical queries. It is archive preservation evidence, not a new performance
measurement. Physical parity fixtures are separate measured TRAIN runs.

## Regenerate TRAIN tables and figures without physics

The summary reads JSON/journals only; plotting imports no physical teacher:

```sh
"$stage_python" baselines/disco_grid/reports/stage2/summarize_campaign.py \
  "$stage_campaign" /tmp/disco_train_summary_new
"$stage_python" baselines/disco_grid/reports/stage2/training_figures.py \
  "$stage_campaign" /tmp/disco_train_summary_new/training_coverage.json \
  /tmp/disco_train_figures_new
```

Choose unused output names. Figures export their source hashes and CSV rows.
Training losses are optimization diagnostics. Only E16's root/call rung has been
executed; no root-count/search-budget performance learning curve is implied.

Native scene figures reconstruct the pinned teacher geometry from a saved
executed parent state, restore that state and use forward kinematics for display.
The 3D model constructor performs initialization integration; its measured count
is separate from post-restoration integration (zero). Rendering performs no
planning and supplies no new task-success certificate.

## Frozen checkpoints, prediction and physical evaluation

`training/{2d,3d}_P1Q1` and `*_P2Q2` contain clean-cycle exports;
`*_P2Q2_knownprefix` contains separately certified prefix-augmented final P2.
Each schema/filter/seed folder contains `policy.pt`, `value.pt`,
`resolved_config.json`, `distill_report.json` and an exact-resume trainer state.
O1 cannot be deployed by silently transferring an O0 checkpoint. The final model
registry gives exact paths, SHA256s, domain, seed and observation schema.

Prediction preparation is model-only. It validates checkpoint and frozen root
hashes, asserts zero physical selection counters and creates immutable candidate
files for the preregistered admission thresholds:

```sh
"$stage_python" baselines/disco_grid/reports/stage2/prepare_evaluation.py \
  --campaign "$stage_campaign" \
  --cohorts "$stage_campaign/evaluation_cohorts_v2.json" \
  --out /tmp/disco_prediction_preparation_new
```

The E16 approval does **not** authorize final VAL/TEST. The release runner requires
a separately approved, hashed envelope. `--request` produces a reviewable request
bound to the actual model registry and all candidate files. After explicit user
approval, it runs one serial worker, selects admission eta from VAL only, persists
`SELECTION_FREEZE.json`, then executes only the selected TEST branch. It refuses
to proceed if raw-Q physically decided VAL coverage is insufficient; abstention
does not constitute a physical decision. Never change the selected checkpoint,
threshold or cohort using TEST outcomes.

For an executed release, regenerate numerical tables without teacher queries:

```sh
"$stage_python" baselines/disco_grid/reports/stage2/analyze_evaluation.py \
  /path/to/actual/approved/release /tmp/disco_metrics_new
```

This preserves fixed root/seed denominators and reports unresolved/not-run rows,
root-family bootstrap intervals and paired within-DISCO differences. Three model
seeds do not triple the independent scene sample size. Reference joint-waypoint
travel is separated from actual servo integration travel, which is not recorded.

## Expensive reproduction

Do not rerun an interrupted directory or overwrite an archived run. A new
collection needs a new campaign identity, source/root/teacher hash manifest,
current host inventory and explicit compute authorization. `campaign.py` and
`continue_e16.py` implement the approved E16 limits; they are not permission to
launch additional campaigns. `physical_fixtures.py` exposes the physically
executed 2D/3D TRAIN order fixtures used for parity, but rerunning these also
creates charged physical queries and requires an unused output path and an
applicable authorized envelope. Preserve original robot/task/connector/Y
semantics and all host guards.

## Current release revision

The final TRAIN release has 63 completed fits and a 69/69 gvlab test pass.
`evaluation_preparation_v3` supersedes the first complete preparation: the
3D clean-data arm now points to `training/3d_P2Q2_strictclean`, whose current
supervision excludes the recovered R0 prefix. The primary models, other arms,
roots and decisions are unchanged; regenerate the audit with:

```sh
"$stage_python" baselines/disco_grid/reports/stage2/audit_preparation.py \
  "$stage_campaign/evaluation_preparation_v2" \
  "$stage_campaign/evaluation_preparation_v3" /tmp/disco_control_audit_new.json
```

The resource envelope enforces a global maximum of 5,523 charged calls in
addition to per-phase CPU/wall ceilings. Its uncached proposal matrix can require
six more calls; cached certificates reduce actual dispatch, and hitting a ceiling
retains unexecuted trials rather than exceeding approval.

All initial release artifacts remain in `training_release_v1`; corrected
coverage/cost tables and the genuine clean-data fit are in `training_release_v2`.
The final native frames are reused from v1, whose source/state hashes and actual
construction cost are preserved. Do not sum these snapshots as independent runs.

Regenerate the current explicitly partial, pre-evaluation report from copied
CSV/JSON without physics:

```sh
python3 baselines/disco_grid/reports/stage2/report_training_release.py \
  baselines/disco_grid/reports/stage2
```

The generator refuses to replace populated physical metrics. After authorized
physical execution, use `analyze_evaluation.py` and `evaluation_figures.py` on
that actual release, then update the final numerical report. Source-only fixture
checks can run locally; all real physical collection and model fitting ran on
one low-priority gvlab CPU worker. Earlier unprofiled diagnostic CPU remains
UNKNOWN instead of being added as zero to a claimed all-stage total.


## Authorized V15-F25 physical release

`EVALUATION_APPROVED.json` records the explicit user approval of both domains'
VAL and TEST phases. `EVALUATION_LAUNCH.json` records the exact detached process
identity, immutable engine, log and output paths. The physical run uses
`source/final_eval_v3` (4aae3d12720be39a175c010059c35c31b320c8fa), without
replacing that deployed source. Do not rerun the command into the existing output.
The request/preparation version suffixes preserve the earlier prospective
clean-control binding before its outcome-free correction.

After the exact authorized process exits, `finish_physical_release.py` runs
analysis once, under a separate 600 CPU/active-wall second watchdog and 3 GiB
child RSS limit. It never launches or retries physical evaluation. It records
partial evidence if a guard or the VAL coverage gate stops the release. Native
failure frames reconstruct saved query-parent poses; their model initialization
steps are separately counted and no planner is called. The finisher writes a
versioned output outside the physical release, containing metrics, root STOP
calibration, paired ablations, saved-state failure frames, reports and a streaming
SHA-256 inventory of the quiescent physical evidence. Its watchdog account
covers analysis/plotting/native reconstruction; observer CPU and inventory
costs are separate in FINISH_COMPLETE.json. Time waiting for the already-running
physical process is inactive observation time.

```sh
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  nice -n 10 /scratch/nav/disco_grid/venv/bin/python \
  baselines/disco_grid/reports/stage2/finish_physical_release.py \
  /scratch/nav/disco_grid/stage2/evidence/V15_F25_v1_20261117_LAUNCH.json \
  /scratch/nav/disco_grid/stage2/evidence/V15_F25_v1_20261117_final_v1 \
  baselines/disco_grid/reports/stage2
```

`report_training_release.py` is the archived **pre-evaluation** generator;
do not use it to replace actual physical results. Use `analyze_evaluation.py`
and `report_physical_release.py` for the measured release instead.


## Girish-laptop continuation (supersedes gvlab execution)

The user explicitly revoked gvlab execution and authorized girish-laptop.
`GIRISH_EXECUTION_AUTHORIZATION.json` is the runtime host amendment. Set
`DISCO_EXECUTION_AUTHORIZATION` to the on-laptop copy; the guard then accepts
only hostname `gvcstar` / alias `girish-laptop` and rejects gvlab. Load, RAM,
disk, CPU-worker, query-time and GPU guards remain enforced.

The isolated Python 3.10 environment is
`/home/longhorizon/disco_grid_stage2/venv`. Frozen checkpoint/input/teacher files
were copied under `rootfs` with all 1,301 SHA-256 hashes verified. Set
`ABF_ROOT`, `DISCO_ROOT`, `FIN3D_CODE` and `FIN3D_SRC` to their relocated
rootfs paths. This does not edit benchmark files or assume a shared filesystem.
The CPU PyTorch build is 2.5.1; NumPy 2.2.6 and MuJoCo 3.16.0 match gvlab.
Prediction parity and actual input/teacher hashes must pass before physical work.

`continue_physical_laptop.py` keeps original job IDs, models, roots, rules and
open-loop sequences. Only path bindings and the explicit host guard change.
The first 32 completed gvlab outcomes and the 33rd administratively cancelled
attempt are retained without retry. All 109 original query intents are charged.
Worker CPU is exactly reaped; detached-controller final CPU is unavailable,
so the controller's entire elapsed interval is conservatively charged as CPU
in addition to worker CPU. The resulting bound reduces the remaining 2D VAL
CPU envelope. It is not presented as an exact CPU measurement. The full original
phase ceilings and global 5,523-query ceiling are never reset.

The prior frozen gvlab tree remains an immutable input to the continuation.
New physical fragments are stored separately and joined through explicit
symlinks and provenance rows. All TEST physical execution is on the laptop;
VAL may contain both hosts. No failed/timed-out/cancelled trial is rerun.
