# DISCO-Grid Stage 2 evidence index

**PARTIAL Stage 2 release. Physical evaluation status: PARTIAL_OR_NOT_RUN. Measured results and execution limits are recorded below; missing evidence stays explicit.**

Branch: `naren/disco-grid-stage2`. D0–D8 and validation archives are unchanged.

- [Release audit](FINAL_DISCO_STAGE2_REPORT.md), generated from stored records by
  [the report script](report_training_release.py).
- [Gate statuses](STAGE2_FINAL_STATUS.json), [standalone manuscript](PAPER_METHODS_AND_RESULTS.md),
  [reproduction instructions](REPRODUCTION.md).
- [Executed TRAIN coverage](SEARCH_COVERAGE.csv), [censoring ledger](CENSORING_LEDGER.csv),
  [child-attempt costs](RESOURCE_ACCOUNTING.csv), [non-overlapping cost totals](RESOURCE_TOTALS.json).
- [Latest 69-test log](training_release_v2/tests.log),
  [archive audit](training_release_v2/archive_audit/input_audit.json).
  Historical preservation: [315 primary predictions exact](campaign_preservation_replay.json),
  1,785 total arm predictions; no new physical queries in that replay.
- [TRAIN loss/depth/STOP/query plots and source CSV](training_release_v2/train_figures_corrected/figure_sources.json).
  These are optimization/search diagnostics, not held-out learning curves.
- [Sixteen native saved-state frames](training_release_v1/scenes/scene_manifest.json),
  [predeclared frame selection](training_release_v1/SCENE_SELECTION.json).
  First TRAIN root per stratum/domain and all three endpoint poses in each
  successful ordered fixture; no invented trajectory is labeled executed.
- [Trained model registry](trained_checkpoint_manifest.json),
  [evaluation preparation hashes](evaluation_preparation_manifest.json),
  [prospective control-correction audit](training_release_v2/CANDIDATE_CONTROL_CORRECTION.json).
  Primary models and 3,470 non-control candidate jobs are unchanged. The corrected
  3D coverage arm uses a genuine 31-tree clean-data fit, with matched P1 initialization.
- [Frozen E16 roots](cohorts.json), [approved TRAIN envelope](COMPUTE_ENVELOPE_REQUEST.json),
  [execution/errata record](E16_EXECUTION.md).
- [Proposed 15/25-root evaluation registry](evaluation_cohorts_v2.json),
  [original physical-evaluation request](EVALUATION_ENVELOPE_REQUEST.json),
  [explicit VAL/TEST approval](EVALUATION_APPROVED.json), and [guarded launch](EVALUATION_LAUNCH.json).
  The resource request remains V15-F25-v1: one gvlab CPU worker, zero GPUs,
  4/8 combined CPU and active wall hours for 2D/3D, 4 GiB RAM, 10 GiB new disk,
  at most 5,523 charged adapter calls. Updated candidate hashes correct the
  coverage control before any outcome. Previous request/preparation copies are
  retained with version suffixes. The user separately authorized both VAL and TEST. The active run is
  `/scratch/nav/disco_grid/stage2/releases/V15_F25_v1_20261117`; TEST follows
  the fixed VAL-only selection gate without further permission.
- [Current physical-results status](FINAL_METRICS.json), [CSV status rows](FINAL_METRICS.csv),
  [ablation status](ABLATIONS.csv). Blank performance fields mean NOT_RUN, not zero.
  Final selected prediction/verification JSONL files require VAL selection and
  actual physical execution; they have not been fabricated.

Canonical on-host campaign:
`/scratch/nav/disco_grid/stage2/campaigns/E16_v1_20261117`.
Large checkpoints, trainer/RNG states, parents, results and witnesses remain there.
The collection/training engine is immutable `89f16995f5ad0d127b3cf3b807cb66bcf9565bfc`;
physical evaluation uses the frozen source recorded in its preparation manifest.
All costs include interrupted attempts; unknown old accounting remains UNKNOWN.

No cross-method performance evaluation is part of this release.

## User-directed host amendment

[Girish authorization](GIRISH_EXECUTION_AUTHORIZATION.json), [current hardware inventory](GIRISH_HOST_INVENTORY.json), [1,301-file migration hash audit](GIRISH_MIGRATION_HASH_AUDIT.json), and [gvlab stop record](GVLAB_USER_HOST_STOP.json). All owned gvlab evaluation and finisher processes exited. The continuation retains completed and interrupted trials without retry, charges all 109 original query intents, and conservatively charges unrecoverable detached-controller CPU. The physical budget is not reset.

Laptop execution: [launch identity](GIRISH_EVALUATION_LAUNCH.json), [postprocessing observer](GIRISH_FINISH_LAUNCH.json), [41-test log](GIRISH_MIGRATION_TESTS.log), and [frozen-input/model qualification](GIRISH_MIGRATION_QUALIFICATION.json). The qualification checked 80 roots, 22 teacher files and 50 model files; 28 sampled frozen model-decision cases matched with zero physical queries.


## Three-worker DISCO continuation

The user explicitly authorized at least three CPU workers and both laptops.
[Parallel authorization](PARALLEL_EXECUTION_AUTHORIZATION.json) records three
one-thread physical workers on Girish at nice 19. The other job's 16 Girish and
14 local workers remain untouched. No physical worker is assigned locally while
available RAM is below the unchanged 8 GiB guard. Measured neural selection was
0.85 seconds across a 1,747.74-second physical phase; frozen CPU inference is
retained and GPU speedup is not claimed.

[Serial drain](PARALLEL_SERIAL_DRAIN.json) completed the current trial normally.
[Prior-cost audit](PARALLEL_PRIOR_AUDIT.json) retains 132 2D and 64 3D attempts,
including timeouts and the earlier host cancellation; none is retried.
[Parallel launch](PARALLEL_EVALUATION_LAUNCH.json) uses immutable source
`bc47221c789f9236a1d940908909d900de43ffcb`. Its pool reserves aggregate CPU and
adapter-call quotas before dispatch, deduplicates identical in-flight open-loop
sequences, and gives each physical child its own accounting supervisor. The
shared pool RSS ceiling remains 4 GiB. Models, roots, rules, query caps and
verification remain frozen; the original 5,523-call and phase CPU/wall ceilings
are not reset. [45-test log](PARALLEL_POOL_TESTS.log) includes actual synthetic
three-process accounting and duplicate-sequence checks; the additional drain
regression [passes separately](PARALLEL_DRAIN_TESTS.log). These fixtures call no
physical teacher and are not benchmark scores.

[Parallel postprocessing observer](PARALLEL_FINISH_LAUNCH.json) waits for the exact physical controller to exit, then packages measured evidence under a separate bounded analysis watchdog. It never restarts physics. The local publication observer fetches and pushes that package only after FINISH_COMPLETE.json and refuses to overwrite concurrent worktree edits.

## Measured physical release

- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).
- [Versioned physical evidence package](physical_release_V15_F25_v1/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_v1/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).
- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).

Earlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.

## Current frozen TEST continuation (supersedes prior stopped-run status)

The user authorized spare Girish CPU capacity with two physical cores reserved. **RUNNING**: `V15_F25_v1_reserved_cores_20261117`, source `0537d1bd12`, four one-thread physical workers; CPUs 22/23 excluded from all DISCO affinity. Live verification observed four concurrent trials and about 2.8 GiB peak pool RSS. No other methodology process was changed. The prior v1 measured package remains an immutable partial snapshot; current canonical numeric tables remain that snapshot until v2 publication.

- [Authorization](RESERVED_CORES_AUTHORIZATION.json), [resource/budget and no-retry contract](RESERVED_CORES_CONTINUATION.md), [49 passing tests](RESERVED_CORES_TESTS.log).
- [Physical launch](RESERVED_CORES_EVALUATION_LAUNCH.json), [live affinity verification](RESERVED_CORES_LIVE_VERIFICATION.json), [report observer](RESERVED_CORES_FINISH_LAUNCH.json).
- Original per-domain CPU/wall and global 5523-call ceilings remain unchanged; earlier costs count. Only never-attempted TEST identities execute; VAL selection remains byte-identical. No GPU required.

## Measured physical release

- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).
- [Versioned physical evidence package](physical_release_V15_F25_v2/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_v2/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).
- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).

Earlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.
