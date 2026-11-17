# DISCO-Grid Stage 2 evidence index

**PARTIAL release: E16 TRAIN cycles and model freezing are complete; new physical
VAL/TEST task-success results are pending the authorized physical run.**

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
