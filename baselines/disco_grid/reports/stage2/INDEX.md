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

## Current three-slot continuation after transient load stop

At 2026-11-17 18:24 UTC the four-slot release had reached 338/525 2D TEST and 18/525 3D TEST attempts, and its immutable v2 reports were pushed as `32815ce9b7`. Both phases stopped on transient load >22/24. Current load had fallen to 16.75. Remaining never-attempted frozen TEST jobs resumed as `V15_F25_v1_reserved_stable3_20261117`, with three slots to lower scheduling pressure. CPUs 22/23 remain excluded; prior interrupted jobs are never retried, and budgets do not reset. VAL freeze is unchanged. Original physical engine source `0537d1bd12` is reused without edits.

[Authorization](RESERVED_CORES_STABLE3_AUTHORIZATION.json), [physical launch](RESERVED_STABLE3_EVALUATION_LAUNCH.json), [report observer](RESERVED_STABLE3_FINISH_LAUNCH.json). Current canonical numbers remain the v2 partial snapshot until v3 publication. Additional training-budget ladders remain NOT_RUN.

## Measured physical release

- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).
- [Versioned physical evidence package](physical_release_V15_F25_v3/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_v3/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).
- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).

Earlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.

## Current continuation, 18 November IST

The v3 partial package is archived and pushed at `24fca20b4f`: TEST attempts 412/525 (2D), 119/525 (3D). 2D charged 10720.020898/10800 CPU seconds, leaving insufficient reserve for another physical trial. 3D charged 3470.321474/21600 CPU seconds and stopped at load 22.089/24. Load recovered to 16.67, so never-attempted frozen TEST identities resumed as `V15_F25_v1_reserved_stable3_20261118` with the existing immutable engine, three slots and CPUs 22/23 excluded. Cancelled or timed-out identities are never retried. No budget, model, threshold or selection changed.

[Physical launch](RESERVED_STABLE3_20261118_EVALUATION_LAUNCH.json), [report observer](RESERVED_STABLE3_20261118_FINISH_LAUNCH.json). Canonical metrics remain the v3 partial snapshot until v4 publication. Resource stops make wall-clock completion uncertain; no full Stage 2 completion claim is made.

## Measured physical release

- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).
- [Versioned physical evidence package](physical_release_V15_F25_v4/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_v4/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).
- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).

Earlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.

## Current continuation, 18 November 03:50 IST

The v4 partial report was pushed as `70977c09c0`; TEST attempts remain 412/525 (2D), 237/525 (3D) at this handoff. The previous 3D phase stopped at load 22.006; no worker remained active. With load recovered to 16.89 and 19.85 GiB available RAM, unattempted identities resumed as `V15_F25_v1_reserved_stable3_20261118_r2`, reusing immutable physical engine `0537d1bd12`, three workers and the same two-core exclusion. 3D has 11686.682902 CPU seconds remaining before startup/supervisor reserves. 2D has insufficient CPU reserve for further physical dispatch. Prior cancelled/unknown attempts are not retried, and VAL selection is unchanged.

[Physical launch](RESERVED_STABLE3_20261118_R2_EVALUATION_LAUNCH.json), [report observer](RESERVED_STABLE3_20261118_R2_FINISH_LAUNCH.json). Canonical numeric tables remain the v4 partial snapshot until v5 publication. No additional training campaign or budget increase is implied.

## Prioritized bounded completion

[Completion monitor contract](PRIORITY_COMPLETION_MONITOR.md) and [frozen 113-trial 2D CPU extension request](COMPLETION_RESOURCE_REQUEST.json). The current 3D run is being supervised through resource stops and report publication without requiring a new user prompt to continue ordinary authorized work. Numeric CPU ceilings, two-core exclusion, no-retry semantics and VAL freeze remain enforced. Additional 2D execution remains unapproved.

## Approved frozen 2D completion extension

[Approval and request hash](COMPLETION_RESOURCE_APPROVAL.json), [implementation and limits](F113_COMPLETION_EXTENSION.md), [54 passing relevant tests](F113_EXTENSION_TESTS.log), and [two disk-guard regressions](F113_DISK_GUARD_TESTS.log). The exact 113-trial completion is approved and is queued behind the existing 3D supervisor, with final report publication following both. Earlier statements that the 2D extension is unapproved describe history.

## Live approved 2D queue

The approved extension is deployed at immutable source `7665c3a528` and its queue is live. [Queue configuration](F113_COMPLETION_QUEUE_CONFIG.json) and [launch identity](F113_COMPLETION_QUEUE_LAUNCH.json). It waits for the upstream 3D supervisor's final marker, preserves that evidence, then starts the frozen 2D registry with separate CPU/wall caps. Deployment footprint is 79,654,631 bytes, within the reserved 0.5 GiB; runtime artifacts use the stricter 1.5 GiB cumulative guard. The additional startup-manifest race regression passed; local metadata/monitor coverage is now nine passing tests. Final combined reporting/publication follows the queue's terminal marker.

## Current phase-boundary recovery queue, 18 November

The extension reached 460/525 total 2D attempts (48/113 new) and the original 3D allowance closed at 414/525 attempts. A startup load refusal before the next 3D pool prevented the old release's COMPLETE ledger. Original error and partial evidence are preserved. [Audited metadata recovery](F113_PHASE_BOUNDARY_RECOVERY.md), [cost/proof JSON](F113_PHASE_BOUNDARY_RECOVERY.json), and [test log](F113_PHASE_BOUNDARY_TESTS.log). The test run passed 42 checks; one unchanged synthetic deduplication process fixture was blocked by its own resource guard, and is not claimed passed in that run. Nine local metadata/monitor tests passed separately.

The corrected queue uses immutable source `cb38026b7f` and resumes only the 65 remaining approved identities after sustained load <=18, with CPUs 22/23 excluded. [Configuration](F113_BOUNDARY_RECOVERY_QUEUE_CONFIG.json), [launch](F113_BOUNDARY_RECOVERY_QUEUE_LAUNCH.json). No budget or model changed; prior 48 extension attempts and their 131 calls remain charged. The recovered controller cost is a conservative affinity-wide upper bound, not measured consumption. Current numeric tables remain the last published snapshot until final combined publication.

## User-requested 10-minute status watchdog

A dedicated agent added a persistent read-only observer with 600-second snapshots, process/start-identity and heartbeat checks, immutable source checks, durable status logs and checked desktop notification delivery. The existing 30-second supervisor remains the sole physical recovery authority. [Configuration and relocation qualification](TEN_MINUTE_WATCHDOG_CONFIG.json). No new physical or competing-method jobs are launched by the status observer. User-laptop migration is currently blocked by available RAM <8 GiB and disk <20 GiB; gvlab remains revoked and other hosts have not been qualified/authorized. Timed chat-message delivery is unavailable; desktop acceptance/failure and every update are recorded explicitly. Six observer tests passed.

## Measured physical release

- [Standalone measured report](FINAL_DISCO_STAGE2_REPORT.md), [metrics](FINAL_METRICS.csv), and [paired ablations](ABLATIONS.csv).
- [Versioned physical evidence package](physical_release_V15_F25_v200/FINISH_COMPLETE.json), [query/state byte inventory](physical_release_V15_F25_v200/physical_evidence_index.json), and [publication hashes](PHYSICAL_RELEASE_PUBLICATION.json).
- [Root STOP diagnostics](ROOT_STOP_DIAGNOSTICS.json), [failure examples](FAILURE_EXAMPLES.json), and [physical resource totals](PHYSICAL_RESOURCE_TOTALS.json).

Earlier pending-run statements in this index describe preparation history; the measured report and status JSON are current.
