# Coverage, experiments and compute

All execution was on gvlab, CPU only, with one thread per process and nice priority. Other named hosts were read-only inventory. No GPU training/context was allocated. Existing Approach B 9+7 workers and other users’ GPU jobs were preserved.

## Historical physical trees (measured, immutable)

| Stream | Distinct TRAIN roots | Feasible edges | Adapter calls | Depth1/2/3 edges |
|---|---:|---:|---:|---|
| 2d/r0_p0_pw_geom | 24 | 171 | 326 | {'1': 69, '2': 70, '3': 32} |
| 2d/r1_p1q1_pw_geom | 24 | 170 | 324 | {'1': 70, '2': 70, '3': 30} |
| 3d/r0_p0_pw_geom | 12 | 48 | 105 | {'1': 27, '2': 21} |
| 3d/r1_p1q1_pw_geom | 12 | 47 | 108 | {'1': 29, '2': 18} |

Rounds reuse the same 24 2D / 12 3D roots; three network seeds do not create three independent search datasets. Exact root/family IDs are in artifact_inventory.json. R0 and R1 use per-root hashed search seeds from cohort seeds0 and100 respectively (`tree|domain|root_id|seed`); these differ from network initialization seeds 0, 1, 2.

## Newly executed evidence

Fresh physical parity:4/4 complete-sequence queries over 2 TRAIN roots, including both orders in each domain; wall296.09s, process CPU293.13s. This is additional small replay, not a rerun of all48 historical queries. Internal planner-call counts for this replay were not separately reconstructed.

The frozen original implementation replayed 1,785 historical arm predictions. Primary sequence/status/X/Y replay was exact 225/225 2D and 90/90 3D;0 new physical calls. Replay wall 19.81 s 2D / 5.49 s 3D.

2D matched round-1 controls: 9 completed runs, fixed 45 epochs / batch 64 /AdamW LR .001 WD .0001, seeds 0/1/2 for each O0 all-feasible, O0 successful-only and O1 all-feasible arm; wall98.67s. Same immutable R0 trees and same seed-specific P0 initialization per comparison. Source/checkpoint hashes and actual losses are in new_training.json. These are TRAIN-loss diagnostics; no new checkpoint was selected using TEST. No new task-success result is claimed. CPU-time/peak-RAM profiling for these fits was NOT_CAPTURED; GPU use was zero.

3D matched round-1 controls: 9 completed runs, fixed 45 epochs / batch 64 /AdamW LR .001 WD .0001, seeds 0/1/2 for each O0 all-feasible, O0 successful-only and O1 all-feasible arm; wall49.35s. Same immutable R0 trees and same seed-specific P0 initialization per comparison. Source/checkpoint hashes and actual losses are in new_training.json. These are TRAIN-loss diagnostics; no new checkpoint was selected using TEST. No new task-success result is claimed. CPU-time/peak-RAM profiling for these fits was NOT_CAPTURED; GPU use was zero.

Independent 2D K3 pilot `pilot_2d_k3_seed 20261116`: root `D2H_7aa5bebefe`, family `fam-309a0a9cb9`. One family disjoint from all historical MCTS families. 10 transitions +6 terminal invocations =16 adapter calls, 8 feasible edges,0 complete solutions, 2 completed iterations before call exhaustion. Wall99.582s /CPU99.377s. Requested ceiling16 calls /180 seconds, actually enforced. New edges are not folded into historical archives or the matched R0 controls.

Independent 3D K3 pilot `pilot_3d_k3_seed 20261116`: root `D3H_GVLAB_366ce85b50` /family `fam-08037cd63c`. Requested12 calls /300 seconds. Stopped at 300+5-second watchdog grace during the first iteration. No completed tree; actual invocation count and CPU seconds UNAVAILABLE because this preceded per-query journaling. Count is not reported as zero, and no failed label or successful edge is inferred from partial witnesses. IN_FLIGHT prevents automatic resume. Artifacts remain on host for reconciliation.

## Learning-curve and scaling gate

No independent-root-size or per-root-budget performance learning curve was executed. The nine figures contain loss curves and physical-edge coverage, not invented success-vs-data curves. Proposed ladders16→32→64 roots and16→32→64 calls remain NOT_RUN and require an explicit aggregate budget beyond this pilot. Current3D cost and absent depth 3 historical edges make another blind sweep inappropriate.

Next: reconcile the interrupted 3D attempt from preserved witness/store files and journal a single affordable root; use measured feasible depth 3/decided STOP yield to propose the next budget. Then freeze a genuinely larger, family-disjoint TRAIN/VAL/confirmatory TEST manifest before scaling.

The O0/O1 controls share seed-specific P0 policy initialization, tree supervision,
model seeds and optimizer schedule. Q is freshly initialized at each schema's
input dimension; an exact common-weight padded-Q initialization control was not
run. No task-performance difference is attributed to proprioception from these
training diagnostics. Optimizer-state training resume and peak-RAM profiling
remain unimplemented/unmeasured; checkpoint writes are atomic and output reuse
is refused.
