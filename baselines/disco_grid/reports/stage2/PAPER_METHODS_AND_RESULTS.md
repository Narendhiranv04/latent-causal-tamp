# DISCO-Grid (adapted): standalone methods and evidence

**Working manuscript. The E16 TRAIN cycle is complete. Measured physical evidence and completion limits follow below.** Historical results are not substituted for this physical study.

## Method and declared adaptations

We adapt the policy-guided physical tree search and policy/value distillation of
Saha et al., *Long-Horizon Multi-Object Rearrangement via Distilled Tree Search
over Continuous Actions*, CoRL 2026 ([paper](https://arxiv.org/abs/2610.25785),
[official implementation](https://github.com/kallol-saha/DISCO)). The reference
code was inspected at commit c62b32e5f6e40444459742525a86ffef620951aa.
This is a discrete object–destination adaptation; continuous-action policy and
robot-hardware reproduction are not claimed.

The task permits at most three corrective object relocations, with a separate
terminal STOP. The learned categorical action distribution factorizes into an
object-or-STOP head and a destination-given-object head. Illegal object and cell
choices are masked using the shared task grammar. P0 destination pretraining
uses positive isolated-placement records from TRAIN with task-goal features
masked; its object choice is uniform over eligible objects. P1/P2 learn object,
destination and successful STOP demonstrations from actual physical search.

O0 uses the historical canonical object-cell geometry, goal, task context,
moved-object mask and remaining correction budget. It omits intermediate robot
configuration. O1 adds sin(q), cos(q) and visibility for the actual three (2D) or
seven (3D) observed joints. Gripper and full simulator state are carried by the
physical adapter but are not additional learned inputs. The 3D physical state
also retains actual subcell placement offsets, whereas the learned scene uses
canonical cells. O1 inputs come from saved executed node states, with lineage
checks. O1 models start from O0 weights by zero-padding added input dimensions;
Q initialization is matched before padding. Missing joint visibility is permitted
for isolated pretraining features; O1 deployment requires observed joints.

## Physical search and terminal semantics

The existing 2D 3R arm uses the 8×8, 0.08 m resting lattice, base
(-0.14, 0.32) m, link lengths (0.42, 0.34, 0.20) m and finite-width links,
palm and fingers. Its 48 side grasps are 24 azimuths × two elbow branches.
These native geometry settings, collision checks, per-root implementation and
physical budgets are reused. The 3D xArm7 uses the 6×6, 0.075 m shelf lattice
and 32 level side-grasp candidates. It retains its original meshes, side-grasp search,
settling, support/collision checks and planner behavior. Teacher source hashes
are recorded per run. No alternative simulator or simplified verifier supplies
training labels.

A physical transition executes a selected relocation and carries the resulting
joint, gripper and simulator state forward. It does not reset the arm between
corrections. Terminal X certifies the executed prefix and its terminal connector;
independent canonical-endpoint Y checks the original target task from its
prescribed ready state. Empty-prefix X is one by definition. Z is X AND Y:
a decided zero in either factor certifies failure; otherwise missing factors
remain unknown. Administrative time/budget limits are censored rather than
negative physical labels. The Stage 2 evaluator queries independent canonical Y even following a selected
execution failure, to distinguish X=0,Y=1 execution-at-feasible-endpoint cases
from target-endpoint failures. Such a case alone does not prove that order caused
the failure. Matched reversed physical fixtures provide direct order evidence.

MCTS uses UCB, not PUCT, with exploration constant C=1.5:
`UCB(v)=Q_tree(v)+1.5 sqrt(log(N_parent+1)/(N_v+1))`.
The learned continuation score initializes unvisited child Q; its first backup
replaces that prior by the observed root-path return. Progressive widening
allows further feasible relocation children when their count is less than
2 max(N,1)^0.3; each expansion samples up to two previously unattempted actions.
The check precedes the batch, so the resulting child count can overshoot that
threshold. E16 uses a maximum of 12 search iterations per root-round in both
domains; actual query caps, rather than YAML defaults, constrain the search.
STOP is evaluated at physical states and cached as one observation. Verified
successful STOP is absorbing on revisits. The correction depth limit is three;
the extra STOP child is bookkeeping, not a fourth relocation. Geometric shaping
and root-path backup guide search. With zero root edge reward, a path's shaped
return telescopes to kappa_leaf minus kappa_root; verified terminal success
therefore need not have numeric return one. Within a root the subtraction is
constant. Shaped return is not the learned success
probability and is not an empirical task-success rate.

The execution unit called an adapter query is one transition or terminal call.
A terminal call may include connector and Y planning. Accordingly, adapter counts,
transition-planner calls, connector calls, Y calls and cache hits are reported
separately. Internal IK/RRT invocations that the teacher does not expose remain
unknown. A durable intent and full parent state precede every query; a returned
result is hashed before its completion event. An external parent watchdog applies
query, CPU, RAM and wall limits even if teacher code replaces signal alarms.
Incomplete intents are retained and charged. Ambiguous work is never silently
resumed or replayed as a new physical observation.

## Distillation and experimental control

Policy training includes every executed feasible edge in the eligible clean
trees and each verified-positive STOP. The successful-only control filters policy
edges to those with successful descendant evidence; Q rows remain unchanged.
The joint categorical negative log likelihood averages object-or-STOP loss over
all policy rows and destination loss over relocation rows with weight
n_relocation/n_policy. Thus STOP-only trees still train the policy.

For a visited feasible action, the Q target is the fraction of unique decided
visited descendant leaves with verified Z=1. Leaf counts are structural physical
evidence, not repeated simulation visits. A decided STOP contributes one leaf;
unresolved leaves contribute no decided label. Intermediate negative STOP probes
supervise STOP rows but do not add leaves to a relocation subtree once that
state has visited children; this is the structural leaf convention. Q uses binary cross entropy
weighted by log(1+n_decided). It learns continuation success under explored
search continuations, not geometric progress or a proof of existential feasibility.

The approved E16-v1 cohort contains 16 new independent source components/domain
(K0/K1/K2/K3/NONE quotas 3/4/3/4/2). Components join any shared parent-family,
layout, raw hash or input hash; they are split-disjoint. Prior physical-search
families are excluded. Each domain has fresh P0-guided R0 and O0 P1/Q1-guided R1
search seeds on this same declared root pool, followed by P1/Q1 and pooled-R0/R1
P2/Q2 fitting. Completed-iteration prefixes are separately checksum-certified
from interrupted attempts without labelling their unfinished queries. Recovered
prefixes augment final P2; they also enter the first 3D P1 because recovery became
available before any 3D P1 epoch. The already completed 2D P1/R1 remain unchanged.
Clean-only P2 is preserved as a coverage control. All-feasible O0/O1 and successful-only O0 use model seeds 0/1/2,
45 fixed epochs, batch size 64, AdamW learning rate .001, weight decay .0001,
constant learning rate, and CPU execution. Successful-only P2 starts from the
corresponding all-feasible P1 so that the current policy-edge filter is isolated.
O0/O1 share identical physical supervision; O1 does not receive a separate
search campaign. Model-seed variation is not independent teacher-data replication.
Legacy trainer fields named `val_*` monitor TRAIN rows under this fixed-epoch
schedule; they are not benchmark VAL measurements and do not select checkpoints.
The clean-only P2 control changes current P2 supervision, retaining its matched
P1 initialization; it is not an entirely clean-only training curriculum.
In 3D this control is a separate `3d_P2Q2_strictclean` fit on 31 clean trees.
The initial pooled `3d_P2Q2` had already inherited the recovered R0 prefix and
cannot serve as that control. Its original weights remain archived. The final
primary model uses 32 eligible trees including that prefix; the corrected
coverage contrast changes current supervision while preserving the P1 seed,
initial weights, architecture, optimizer and epoch schedule.

The collection ceilings are 1,024 adapter intents / four CPU and active wall hours
in 2D and 512 intents / eight CPU and active wall hours in 3D. Queries are bounded
at 60/120 seconds. Neural fitting has a separate aggregate 30-minute ceiling.
All jobs use one low-priority CPU worker on gvlab, with zero GPU allocation,
4 GiB combined RAM and 10 GiB new campaign disk ceilings. Limits include censored
attempts, termination grace and reserved measured controller overhead.

## Evaluation and statistics

Strict O0 open-loop inference commits one sequence, NOOP or ABSTAIN before any
simulator initialization or physical candidate evaluation. Instrumented selection
counters must all remain zero; physical execution is independent verification
after that commitment. Closed-loop O0 and O1 choose one action from the current
actual observation, execute it once, and observe the resulting state. There is
no teacher lookahead, MCTS, online fitting or retry. A failed or unresolved
attempt aborts according to the frozen rule; uncertain physical state is not
teleported back for another candidate.

A separate VAL evaluation envelope, model/rule selection and SELECTION_FREEZE
must precede final TEST execution. E16-v1 does not authorize these evaluations.
Known historical TEST exposure is excluded from the proposed new subset, but
exhaustive external exposure is not attested. Therefore any later use of this
planned subset is exploratory held-out evaluation, not untouched confirmation.

For each predeclared root we average verified-success indicators over the fixed
network seeds, then average roots. Missing/unresolved trials remain in the
intention-to-evaluate denominator without being called physical negatives.
Report decided-only success, coverage, unknown count and pessimistic/optimistic
bounds separately. The 95% intervals use 10,000 source-family cluster bootstrap
replicates (seed 20261117), retaining seeds within roots. Per-K results, K0 NOOP,
NONE explicit abstention, connector/relocation/target failures, neural latency,
physical calls, actual travel when available and compute costs remain separate.
DISCO ablation differences must bootstrap the same roots and aligned seeds.

## Current measured evidence and limitations

Before expanded training, the original 30 lightweight/analytical tests passed;
all 17 Stage 2 checks passed after correcting deployment directory structure.
All 92 archived checkpoint/teacher hashes match. The changed implementation
reproduced 315/315 archived primary predictions (1,785 total arm predictions)
without new physics. These are preservation checks, not final task metrics.

Four fresh TRAIN order-parity fixtures agree 4/4 with the expected ordered and
reversed physical outcomes, using 12 returned adapter queries. Old interrupted
3D K3 evidence without parent state/journal is quarantined: actual calls and CPU
are unknown. A new 3D K3 pilot completed 24 calls, 15 feasible relocations, reached
depth three, and found zero verified repairs. Parent CPU/elapsed cost was
399.403797/400.546165 seconds. Its best shaped return of .566 is not success.

E16 attempted 16 independent TRAIN roots/domain in two rounds. In 2D, 544
charged query intents yielded 531 returned results; 19 root-rounds were clean
and 13 quarantined. In 3D, 411 charged queries all returned; 31 root-rounds
were clean and one stopped at a resource guard after returned evidence.
Certified completed prefixes produce final 2D supervision from 26 trees on
13 roots (231 relocation-policy, 247 object/STOP and 309 Q rows); 3D uses
32 trees on 16 roots (181, 213 and 269 rows). These counts are data coverage,
not independent held-out prediction trials. There are 63 completed 45-epoch
fits including controls; P0's six existing checkpoints are reused unchanged.

Completed R0/R1 checkpoint edges at depths 1/2/3 are 37/48/29 and 37/47/33
in 2D, and 38/27/7 and 48/44/17 in 3D. All 45 returned terminal probes on
the 3D K3 TRAIN roots passed X but failed canonical Y with no feasible side
grasp. This establishes missing successful endpoint evidence under the pinned
teacher, rather than demonstrating universal impossibility or measuring
learned-policy K3 task success. The final 69-test suite passes; all 92 protected
checkpoint/teacher hashes match. Tables regenerate from the stored JSON/CSV
and source-backed report generator in this release.



<!-- MEASURED_STAGE2_RESULTS -->

## Primary physical task results

| Domain | Protocol | K1–K3 verified task success, 95% root CI |
|---|---|---|
| 2D | O0 open loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 6 |
| 2D | O0 closed loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 5 |
| 2D | O1 closed loop | 2/45 = 4.44% [0.00%, 11.11%]; 15 roots; unknown 4 |
| 3D | O0 open loop | 15/45 = 33.33% [15.56%, 51.11%]; 15 roots; unknown 4 |
| 3D | O0 closed loop | 17/45 = 37.78% [20.00%, 57.78%]; 15 roots; unknown 0 |
| 3D | O1 closed loop | 5/45 = 11.11% [0.00%, 26.67%]; 15 roots; unknown 40 |

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
| 3D | O1 closed loop | 0 | 3/15 = 20.00% [0.00%, 60.00%]; 5 roots; unknown 12 |
| 3D | O1 closed loop | 1 | 3/15 = 20.00% [0.00%, 60.00%]; 5 roots; unknown 12 |
| 3D | O1 closed loop | 2 | 2/15 = 13.33% [0.00%, 40.00%]; 5 roots; unknown 13 |
| 3D | O1 closed loop | 3 | 0/15 = 0.00% [0.00%, 0.00%]; 5 roots; unknown 15 |
| 3D | O1 closed loop | NONE | NOT_RUN |

## Stopping, execution failures and inference costs

| Domain | Protocol | K0 verified NOOP | K0 relocation predictions | NONE explicit abstention | X=0,Y=1 | Neural latency median / p95 ms |
|---|---|---|---|---|---|---|
| 2D | O0 open loop | 0/15 | 15 | 0/15 | 17 | 12.599 / 16.2117 |
| 2D | O0 closed loop | 0/15 | 15 | 0/15 | 13 | 18.409661017358303 / 37.61256784200668 |
| 2D | O1 closed loop | 0/15 | 15 | 0/15 | 12 | 20.45479998923838 / 37.60697022080421 |
| 3D | O0 open loop | 6/15 | 6 | 0/15 | 3 | 6.047000000000001 / 10.723 |
| 3D | O0 closed loop | 7/15 | 8 | 0/15 | 2 | 14.677264029160142 / 25.743696175049987 |
| 3D | O1 closed loop | 0/15 | 3 | 0/15 | 0 | 16.436462989076972 / 17.918345978250727 |

X=0,Y=1 denotes execution failure at a target-feasible endpoint; it does not establish that order alone caused the failure. Complete failure phases/kinds, action counts and reference path travel remain in FINAL_METRICS.json. Travel measures accepted corrective joint waypoints plus the certified connector, excluding target Y; actual servo-integrated arc is NOT_RECORDED. Cached certificates reduce physical calls, not neural latency measurements.

## Paired DISCO-only ablations

| Domain / contrast | Task-success difference | 95% root CI | Roots / fixed seeds | Unknown paired trials |
|---|---|---|---|---|
| test|2d|O0_P1Q1_minus_O0_P1_success_onlyQ1|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 14 |
| test|2d|O0_P2Q2_minus_O0_P0|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 13 |
| test|2d|O0_P2Q2_minus_O0_P1Q1|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 14 |
| test|2d|O0_P2Q2_minus_O0_P2_clean_onlyQ2|eta0.0 | 0.00 pp | [0.00, 0.00] pp | 15 / [0] | 14 |
| test|2d|O0_P2Q2_minus_O0_P2_success_onlyQ2|eta0.0 | -6.67 pp | [-17.78, 4.44] pp | 15 / [0, 1, 2] | 8 |
| test|2d|O0_P2Q2_minus_O0_P2|eta0.0 | 4.44 pp | [0.00, 11.11] pp | 15 / [0, 1, 2] | 15 |
| test|2d|O1_closed_P2Q2_minus_O0_closed_P2Q2|eta0.0 | 0.00 pp | [-6.67, 6.67] pp | 15 / [0, 1, 2] | 7 |
| test|3d|O0_P1Q1_minus_O0_P1_success_onlyQ1|eta0.0 | 6.67 pp | [0.00, 20.00] pp | 15 / [0] | 14 |
| test|3d|O0_P2Q2_minus_O0_P0|eta0.0 | 26.67 pp | [6.67, 46.67] pp | 15 / [0] | 15 |
| test|3d|O0_P2Q2_minus_O0_P1Q1|eta0.0 | 20.00 pp | [0.00, 40.00] pp | 15 / [0] | 13 |
| test|3d|O0_P2Q2_minus_O0_P2_clean_onlyQ2|eta0.0 | 20.00 pp | [0.00, 40.00] pp | 15 / [0] | 9 |
| test|3d|O0_P2Q2_minus_O0_P2_success_onlyQ2|eta0.0 | 17.78 pp | [6.67, 31.11] pp | 15 / [0, 1, 2] | 26 |
| test|3d|O0_P2Q2_minus_O0_P2|eta0.0 | 33.33 pp | [15.56, 51.11] pp | 15 / [0, 1, 2] | 40 |
| test|3d|O1_closed_P2Q2_minus_O0_closed_P2Q2|eta0.0 | -26.67 pp | [-46.67, -8.89] pp | 15 / [0, 1, 2] | 40 |

Q on/off, policy evolution, all-feasible/successful-only, clean/prefix data and observed-joint effects use identical frozen roots and common model seeds. Secondary evolution/coverage arms use seed 0. These are descriptive paired estimates without multiplicity-adjusted hypothesis tests. No improvement is inferred from fitting loss. Successful-only P2 starts from all-feasible P1, and the clean-data contrast holds current-P2 fitting controls fixed; neither is a whole-curriculum or root-count learning curve.

## VAL-only selection and provenance

Selected eta: `{"2d": 0.0, "3d": 0.0}`. SELECTION_FREEZE.json records the VAL evidence hashes and selected TEST job identities before TEST execution.

final_predictions.jsonl, final_verifications.jsonl, final_root_manifest.json and final_checkpoints.json preserve the actual model/root bindings. The checkpoint registry has SHA-256 hashes; all large weights, optimizer/RNG states and physical witnesses remain on gvlab. The completed TRAIN inventory verified 315 checkpoint files from 63 fits. The prospective 3D clean-control correction used no held-out outcome; original candidates and weights remain archived.

## Resource accounting

| Phase | Domain | Predictions attempted / frozen | Charged adapter calls | Charged CPU s | Active wall s |
|---|---|---|---|---|---|
| val | 2d | 145/255 | 381 | 3560.354 | 2658.970 |
| val | 3d | 162/255 | 339 | 7111.527 | 3928.404 |
| test | 2d | 412/525 | 923 | 10720.036 | 2847.155 |
| test | 3d | 237/525 | 403 | 9913.317 | 2891.509 |

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
