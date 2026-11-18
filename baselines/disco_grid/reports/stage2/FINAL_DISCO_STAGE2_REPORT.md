# DISCO-Grid Stage 2 final physical release audit

**Overall status: PARTIAL.** Physical evaluation status: **PARTIAL / NOT_RUN where indicated**.

This is a standalone DISCO study. All rates below come from independently executed teacher episodes or exact, source-bound verification certificates. Training loss and search success are never substituted for learned-policy performance.

Run: `/home/longhorizon/disco_grid_stage2/rootfs/scratch/nav/disco_grid/stage2/releases/F113_completion_20261118/resume_after_boundary_v2/release_initial`. Execution host: girish-laptop; 3 low-priority CPU worker(s), zero GPU allocation. Both VAL and TEST were explicitly authorized. Previous archives remain preserved.

The cohort contains 15 VAL and 25 exploratory TEST roots/domain, balanced over K0/K1/K2/K3/NONE. The three primary protocols use three fixed model seeds, so their K1–K3 denominator is 15 roots and 45 predictions. Source-family bootstrap intervals use 10,000 replicates, seed 20261117; model seeds remain within each root. These small balanced cohorts are neither full-TEST population estimates nor untouched confirmation.

Missing or interrupted outcomes remain in the fixed denominator and the unknown ledger. Verified-success rates are intention-to-evaluate lower bounds when outcomes are unknown; unknowns are never certified physical negatives. Explicit abstention uses no physical query.

## Primary physical task results

| Domain | Protocol | K1–K3 verified task success, 95% root CI |
|---|---|---|
| 2D | O0 open loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 6 |
| 2D | O0 closed loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 5 |
| 2D | O1 closed loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 4 |
| 3D | O0 open loop | 15/45 = 33.33% [15.56%, 51.11%]; 15 roots; unknown 4 |
| 3D | O0 closed loop | 17/45 = 37.78% [20.00%, 57.78%]; 15 roots; unknown 0 |
| 3D | O1 closed loop | 20/45 = 44.44% [20.00%, 68.89%]; 15 roots; unknown 2 |

## Per-stratum results

K0 and NONE physical success are shown separately from their intended NOOP and explicit-abstention diagnostics. A newly verified NONE repair is retained rather than relabeled from the legacy stratum.

| Domain | Protocol | K | Verified physical success, 95% root CI |
|---|---|---|---|
| 2D | O0 open loop | 0 | 8/15 = 53.33% [20.00%, 86.67%]; 5 roots; unknown 0 |
| 2D | O0 open loop | 1 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 4 |
| 2D | O0 open loop | 2 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 2 |
| 2D | O0 open loop | 3 | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 0 |
| 2D | O0 open loop | NONE | 2/15 = 13.33% [0.00%, 26.67%]; 5 roots; unknown 2 |
| 2D | O0 closed loop | 0 | 8/15 = 53.33% [20.00%, 86.67%]; 5 roots; unknown 0 |
| 2D | O0 closed loop | 1 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 3 |
| 2D | O0 closed loop | 2 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 2 |
| 2D | O0 closed loop | 3 | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 0 |
| 2D | O0 closed loop | NONE | 2/15 = 13.33% [0.00%, 26.67%]; 5 roots; unknown 2 |
| 2D | O1 closed loop | 0 | 9/15 = 60.00% [26.67%, 86.67%]; 5 roots; unknown 0 |
| 2D | O1 closed loop | 1 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 1 |
| 2D | O1 closed loop | 2 | 1/15 = 6.67% [0.00%, 20.00%]; 5 roots; unknown 3 |
| 2D | O1 closed loop | 3 | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 0 |
| 2D | O1 closed loop | NONE | 3/15 = 20.00% [0.00%, 46.67%]; 5 roots; unknown 2 |
| 3D | O0 open loop | 0 | 9/15 = 60.00% [26.67%, 93.33%]; 5 roots; unknown 3 |
| 3D | O0 open loop | 1 | 7/15 = 46.67% [13.33%, 80.00%]; 5 roots; unknown 1 |
| 3D | O0 open loop | 2 | 6/15 = 40.00% [6.67%, 73.33%]; 5 roots; unknown 0 |
| 3D | O0 open loop | 3 | 2/15 = 13.33% [0.00%, 26.67%]; 5 roots; unknown 3 |
| 3D | O0 open loop | NONE | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 2 |
| 3D | O0 closed loop | 0 | 11/15 = 73.33% [33.33%, 100.00%]; 5 roots; unknown 0 |
| 3D | O0 closed loop | 1 | 8/15 = 53.33% [13.33%, 93.33%]; 5 roots; unknown 0 |
| 3D | O0 closed loop | 2 | 6/15 = 40.00% [6.67%, 73.33%]; 5 roots; unknown 0 |
| 3D | O0 closed loop | 3 | 3/15 = 20.00% [6.67%, 33.33%]; 5 roots; unknown 0 |
| 3D | O0 closed loop | NONE | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 0 |
| 3D | O1 closed loop | 0 | 12/15 = 80.00% [40.00%, 100.00%]; 5 roots; unknown 0 |
| 3D | O1 closed loop | 1 | 12/15 = 80.00% [40.00%, 100.00%]; 5 roots; unknown 0 |
| 3D | O1 closed loop | 2 | 5/15 = 33.33% [0.00%, 73.33%]; 5 roots; unknown 1 |
| 3D | O1 closed loop | 3 | 3/15 = 20.00% [0.00%, 60.00%]; 5 roots; unknown 1 |
| 3D | O1 closed loop | NONE | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 0 |

## Stopping, execution failures and inference costs

| Domain | Protocol | K0 verified NOOP | K0 relocation predictions | NONE explicit abstention | X=0,Y=1 | Neural latency median / p95 ms |
|---|---|---|---|---|---|---|
| 2D | O0 open loop | 0/15 | 15 | 0/15 | 17 | 12.599 / 16.2117 |
| 2D | O0 closed loop | 0/15 | 15 | 0/15 | 13 | 18.409661017358303 / 37.61256784200668 |
| 2D | O1 closed loop | 0/15 | 15 | 0/15 | 12 | 20.45479998923838 / 37.60697022080421 |
| 3D | O0 open loop | 6/15 | 6 | 0/15 | 3 | 6.047000000000001 / 10.723 |
| 3D | O0 closed loop | 7/15 | 8 | 0/15 | 2 | 14.677264029160142 / 25.743696175049987 |
| 3D | O1 closed loop | 7/15 | 8 | 0/15 | 3 | 15.223842929117382 / 25.882765906862904 |

X=0,Y=1 denotes execution failure at a target-feasible endpoint; it does not establish that order alone caused the failure. Complete failure phases/kinds, action counts and reference path travel remain in FINAL_METRICS.json. Travel measures accepted corrective joint waypoints plus the certified connector, excluding target Y; actual servo-integrated arc is NOT_RECORDED. Cached certificates reduce physical calls, not neural latency measurements.

## Paired DISCO-only ablations

| Domain / contrast | Task-success difference | 95% root CI | Roots / fixed seeds | Unknown paired trials |
|---|---|---|---|---|
| test|2d|O0_P1Q1_minus_O0_P1_success_onlyQ1|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 5 |
| test|2d|O0_P2Q2_minus_O0_P0|eta0.0 | -6.67 pp | [-20.00, 0.00] pp | 15 / [0] | 3 |
| test|2d|O0_P2Q2_minus_O0_P1Q1|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 6 |
| test|2d|O0_P2Q2_minus_O0_P2_clean_onlyQ2|eta0.0 | -6.67 pp | [-20.00, 0.00] pp | 15 / [0] | 5 |
| test|2d|O0_P2Q2_minus_O0_P2_success_onlyQ2|eta0.0 | -6.67 pp | [-17.78, 4.44] pp | 15 / [0, 1, 2] | 8 |
| test|2d|O0_P2Q2_minus_O0_P2|eta0.0 | 4.44 pp | [0.00, 11.11] pp | 15 / [0, 1, 2] | 15 |
| test|2d|O1_closed_P2Q2_minus_O0_closed_P2Q2|eta0.0 | 0.00 pp | [-6.67, 6.67] pp | 15 / [0, 1, 2] | 7 |
| test|3d|O0_P1Q1_minus_O0_P1_success_onlyQ1|eta0.0 | 6.67 pp | [-13.33, 26.67] pp | 15 / [0] | 14 |
| test|3d|O0_P2Q2_minus_O0_P0|eta0.0 | 26.67 pp | [6.67, 46.67] pp | 15 / [0] | 15 |
| test|3d|O0_P2Q2_minus_O0_P1Q1|eta0.0 | 13.33 pp | [0.00, 33.33] pp | 15 / [0] | 12 |
| test|3d|O0_P2Q2_minus_O0_P2_clean_onlyQ2|eta0.0 | 20.00 pp | [0.00, 40.00] pp | 15 / [0] | 9 |
| test|3d|O0_P2Q2_minus_O0_P2_success_onlyQ2|eta0.0 | -4.44 pp | [-15.56, 6.67] pp | 15 / [0, 1, 2] | 4 |
| test|3d|O0_P2Q2_minus_O0_P2|eta0.0 | 0.00 pp | [-15.56, 15.56] pp | 15 / [0, 1, 2] | 5 |
| test|3d|O1_closed_P2Q2_minus_O0_closed_P2Q2|eta0.0 | 6.67 pp | [-11.11, 26.67] pp | 15 / [0, 1, 2] | 2 |

Q on/off, policy evolution, all-feasible/successful-only, clean/prefix data and observed-joint effects use identical frozen roots and common model seeds. Secondary evolution/coverage arms use seed 0. These are descriptive paired estimates without multiplicity-adjusted hypothesis tests. No improvement is inferred from fitting loss. Successful-only P2 starts from all-feasible P1, and the clean-data contrast holds current-P2 fitting controls fixed; neither is a whole-curriculum or root-count learning curve.

## VAL-only selection and provenance

Selected eta: `{"2d": 0.0, "3d": 0.0}`. SELECTION_FREEZE.json records the VAL evidence hashes and selected TEST job identities before TEST execution.

final_predictions.jsonl, final_verifications.jsonl, final_root_manifest.json and final_checkpoints.json preserve the actual model/root bindings. The checkpoint registry has SHA-256 hashes; all large weights, optimizer/RNG states and physical witnesses remain on gvlab. The completed TRAIN inventory verified 315 checkpoint files from 63 fits. The prospective 3D clean-control correction used no held-out outcome; original candidates and weights remain archived.

## Resource accounting

| Phase | Domain | Predictions attempted / frozen | Charged adapter calls | Charged CPU s | Active wall s |
|---|---|---|---|---|---|
| val | 2d | 145/255 | 381 | 3560.354 | 2658.970 |
| val | 3d | 162/255 | 339 | 7111.527 | 3928.404 |
| test | 2d | 525/525 | 1199 | 23798.507 | 3894.199 |
| test | 3d | 414/525 | 880 | 21438.587 | 6348.953 |

PHYSICAL_RESOURCE_TOTALS.json provides non-overlapping phase costs and, when available, shared-overhead-inclusive release totals. All interrupted attempts are charged. Phase limits and the 5,523-call global ceiling are checked against the explicit approval. TRAIN recorded subtotal: 10935.151 CPU / 11497.676 active-wall seconds. These scopes must not be summed with overlapping upper bounds. Older unprofiled work remains UNKNOWN; no exact all-stage total is claimed.

## Implementation, TRAIN evidence and remaining work

TRAINING_RELEASE_AUDIT.md retains the detailed search/distillation audit: 16 independent attempted TRAIN roots/domain in two rounds, 544/411 charged intents (2D/3D), certified prefix handling and the P0→R0→P1/Q1→R1→P2/Q2 chain. O0 is q-blind; O1 consumes actual observed joints in closed loop. Geometry and the independent physical X/Y contract are unchanged. The deployed physical engine is pinned in the preparation manifest, separately from later reporting code.

Search remains UCB C=1.5, widening k=2 and alpha=.3 before a two-proposal batch, with a 12-iteration E16 cap. Q is learned from decided descendant-leaf success fractions; its unvisited-child prior is overwritten by shaped-return backup. All 45 returned 3D K3 TRAIN terminal probes passed X and failed target Y with no feasible side grasp. This diagnoses missing successful endpoint evidence, not universal impossibility or learned-policy performance.

DONE: source/archive audit, journal/watchdog/checkpoint fixes, bounded physical pilots, two iterative TRAIN rounds, 63 completed fits and frozen candidates. Physical evaluation completion is reported from evidence above. PARTIAL: overall Stage 2 because root-count/search-budget task-success ladders were not collected. NOT_RUN: additional ladder rungs, capacity-matched joint controls, reward/widening/retry experiments and full-arm animation. NOT_RECORDED: actual servo arc. UNKNOWN: exhaustive external TEST exposure, historical transitive assets and old unrecoverable query costs. No saturation or sufficiently trained K3 claim is made.

Sixteen native saved-state frames and TRAIN loss/search-coverage figures accompany the release. Held-out plots use measured metrics only. ROOT_STOP_DIAGNOSTICS.json uses independent root STOP probes for descriptive raw-Q calibration, never legacy K labels or fitted TEST calibration. Reproduction commands are in REPRODUCTION.md.

## User-directed host migration

The user revoked gvlab execution and authorized girish-laptop. Existing gvlab evidence was copied with byte-hash checks; finished and interrupted trials were retained without retry. The primary models, roots, rules and precommitted open-loop sequences are unchanged. VAL therefore includes both hosts where recorded; TEST is on the laptop. Only file paths and the explicit host guard were amended.

All gvlab query intents and reaped worker CPU remain charged. The detached gvlab controller's final CPU could not be recovered, so its entire elapsed interval is conservatively charged as controller CPU, in addition to exact reaped worker CPU. Thus phase/total CPU figures containing gvlab work are charged upper bounds, not exact CPU measurements. Worker accounts and HOST_MIGRATION.json retain the distinction. Environment installation/transfer qualification is reported separately from physical query runtime.

## Explicitly authorized parallel execution

The user authorized at least three CPU workers and both laptops. The current continuation configures 3 one-thread physical workers on Girish, each with its own supervisor and durable query journal. Total CPU and adapter-call quotas are reserved before dispatch; active wall time is elapsed pool time, not the sum of concurrent worker durations. All prior serial attempts remain charged and are not retried.

The other methodology job was observed using 16 workers on Girish and 14 on the user laptop. DISCO physical workers use nice 19 and leave the other processes unchanged. The user laptop had only about 6 GiB available RAM, below the unchanged 8 GiB headroom guard, so no physical DISCO worker was allocated there. The pool retains the shared 4 GiB RSS ceiling plus individual watchdogs. Configured workers do not guarantee that all slots are simultaneously active trials near the end of a queue or budget.

Frozen CPU inference is retained. Measured 2D neural-selection latencies totalled 0.85 seconds during a 1,747.74-second physical phase, so GPU inference was not the runtime bottleneck. No GPU speedup is claimed. Parallel execution changes scheduling, not the model, action grammar, verification caps or TEST selection. PARALLEL_HANDOFF.json and per-phase accounts record topology, prior cost bounds and actual pool costs.

## Two-core reservation and frozen TEST continuation

The user authorized remaining available Girish CPU capacity while reserving two physical cores. DISCO affinity excludes all threads of those two cores; other processes are unchanged, so global idleness is not guaranteed. The configured one-thread trial slots retain the 4 GiB pool RSS cap, 8 GiB available-memory floor, 20 GiB disk headroom and load ceiling of 22/24 logical CPUs. Only never-attempted TEST identities are dispatched; prior timeouts, cancellations and returned results are retained without retry. The existing VAL selection is byte-preserved; all earlier costs remain charged against the original ceilings.

## Explicitly approved frozen 2D completion extension

The user approved execution of the 113 previously unattempted 2D TEST identities, with at most 370 additional adapter calls, 43200 additional CPU seconds and 18000 additional active-wall seconds. New data are capped at 2 GiB across the extension directory; three workers and the two-core exclusion remain. CPU and wall ceilings are each prior charged use plus the explicitly approved extension, rather than resetting earlier costs. All models, prior outcomes, teacher limits, and the VAL selection remain frozen. The original global 5523-call ceiling and original 3D CPU/wall limits are retained. COMPLETION_EXTENSION.json records approval hashes, the exact eligible trial IDs, and the prior release. This approval contains no new TRAIN collection or retry of an earlier interrupted episode.

## Audited phase-boundary recovery

A shared-load refusal occurred after the 2D phase closed and before any 3D pool directory existed. The stopped release remains unchanged. A new metadata-only ledger carries all published outcomes and durable query counts; no prior episode was retried. The final controller CPU was unavailable, so an affinity-wide elapsed upper bound adds 9573.639 charged CPU seconds. This is deliberately conservative and is not measured CPU consumption. Exact child/supervisor subtotals and the upper-bound derivation are preserved in PHASE_BOUNDARY_RECOVERY.json. Subsequent startup resource refusals now write a zero-attempt phase ledger, allowing the normal headroom supervisor to continue without losing a completed preceding phase.
