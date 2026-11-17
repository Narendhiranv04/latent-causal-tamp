# DISCO-Grid (adapted): standalone methods and evidence

**Working manuscript. Stage 2 TRAIN execution is ongoing. Final independently
verified model task-success results are NOT_RUN.** Historical results are not
substituted for the pending study.

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

The existing 2D 3R arm, full-width links and gripper geometry, collision checks,
grasp settings, per-root geometry implementation and physical budgets are reused.
The 3D xArm7 shelf environment retains its original meshes, side-grasp search,
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

MCTS uses UCB, not PUCT, with exploration constant C=1.5. Progressive widening
allows further feasible relocation children when their count is less than
2 max(N,1)^0.3; each expansion samples up to two previously unattempted actions.
STOP is evaluated at physical states and cached as one observation. Verified
successful STOP is absorbing on revisits. The correction depth limit is three;
the extra STOP child is bookkeeping, not a fourth relocation. Geometric shaping
and root-path backup guide search; shaped return is not the learned success
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
P2/Q2 fitting. All-feasible O0/O1 and successful-only O0 use model seeds 0/1/2,
45 fixed epochs, batch size 64, AdamW learning rate .001, weight decay .0001,
constant learning rate, and CPU execution. Successful-only P2 starts from the
corresponding all-feasible P1 so that the current policy-edge filter is isolated.
O0/O1 share identical physical supervision; O1 does not receive a separate
search campaign. Model-seed variation is not independent teacher-data replication.

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

Expanded E16-v1 numerical coverage and checkpoints will be regenerated from
`training_coverage.json` and the immutable campaign tree/result records.
**Final model task-success percentages, CIs, VAL-selected STOP calibration,
O0/O1 task effects, Q effectiveness and sample-efficiency learning curves are
NOT_RUN at this manuscript revision.** No positive or negative improvement claim
is inferred from fitting losses or TRAIN discovery alone.
