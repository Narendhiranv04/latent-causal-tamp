# DISCO-Grid Stage 2 evidence index

**Active execution. This is not the final numerical release.**

Branch: `naren/disco-grid-stage2`. Original validation archives are unchanged.
E16-v1 TRAIN search/fitting is approved; physical VAL/TEST execution is separate.

- [Execution and accounting](E16_EXECUTION.md): authorization, exact ceilings,
  original accounting interruption, explicit continuation and preservation.
- [Frozen roots](cohorts.json), [approved envelope](COMPUTE_ENVELOPE_REQUEST.json).
  The root file's old planning-only authorization field is intentionally preserved;
  the subsequent explicit approval is recorded in the envelope and execution log.
- [Source/split audit](S2_0_AUDIT.md), [old 3D quarantine](S2_1_INTERRUPTION.md),
  [92 checkpoint/teacher hashes](audit/input_audit.json).
- [Changed-source prediction preservation](campaign_preservation_replay.json):
  315 primary predictions exact, 1,785 arm predictions, zero new physical queries.
- [2D collection snapshot](training_coverage_precontinuation.json): 32 root-rounds,
  544 charged intents, 531 returned results, 19 clean and 13 quarantined attempts.
  This snapshot predates 3D continuation and is not a final task-evaluation table.
- [Working manuscript](PAPER_METHODS_AND_RESULTS.md): method, source adaptation,
  intended statistics and explicit NOT_RUN results.
- [Native 3D saved-state figure](figures/native_3d_executed_depth2.png),
  [geometry/state provenance](figures/native_3d_scene_manifest.json).
  Figure framing is being improved; it is a genuine saved executed state.
- Scripts: [coverage/cost summary](summarize_campaign.py),
  [certified completed-prefix recovery](recover_prefixes.py),
  [bounded prefix-augmented P2 fits](fit_known_prefixes.py),
  [model/prediction freezing](prepare_evaluation.py),
  [native scene rendering](scene_evidence.py).

Actual gvlab root: `/scratch/nav/disco_grid/stage2/campaigns/E16_v1_20261117`.
Logs: `/scratch/nav/disco_grid/stage2/evidence/E16_v1_20261117.log` and
`E16_v1_continuation.log`. Physical/training engine remains immutable at
`source/89f16995f5/baselines/disco_grid`; controller continuation is source
`a5838322833c7616219ef88fac3109d05c4b3449`.

No held-out learned-policy success rate, Q gain or O1 task benefit is claimed yet.
No competing-method evaluation is part of this stage.
