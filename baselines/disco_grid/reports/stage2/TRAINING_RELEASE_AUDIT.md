> Snapshot captured before completion of the authorized physical evaluation.
> For current measured results use FINAL_DISCO_STAGE2_REPORT.md.

# DISCO-Grid Stage 2 release audit

**Verdict: PARTIAL. TRAIN execution and model freezing are complete. The user authorized both VAL and TEST; guarded physical release V15_F25_v1_20261117 is running. Final learned-policy metrics remain unavailable until execution finishes. NOT_RUN is not 0% success.**

This audit is generated from stored records by `report_training_release.py`.
It does not replace the preserved D0–D8 or Stage 1 results. The release contains
no competing-method performance study.

## Source, implementation and preservation

Branch: `naren/disco-grid-stage2`, based on verified validation commit
`8c5213fd0c7cb739e2358452564320eac1891db5`. The physical collection/training
engine is immutable commit `89f16995f5ad0d127b3cf3b807cb66bcf9565bfc`.
The corrected physical-evaluation engine and its tested sources are
`4aae3d12720be39a175c010059c35c31b320c8fa`. Later report-only commits do not change these engines.

The final gvlab suite reports **69 passed in 17.64s**. All 92 protected checkpoint/teacher
hashes pass the final archive audit. Historical prediction preservation is
315/315 primary predictions exact within 1,785 archived arm predictions, with
zero new physical calls. Four fresh ordered/reversed TRAIN fixtures agree 4/4
using 12 returned adapter queries. These are preservation/parity evidence,
not final learned-policy scores.

The existing implementation was retained. Narrow changes harden durable
query intents/results, parent-state hashing, identity-scoped watchdogs, strict
call caps, exact tree/optimizer/RNG checkpoint recovery, STOP-only training,
joint categorical loss normalization, common Q initialization before O1 padding,
root-family statistics, and independent no-retry evaluation. Search remains
UCB (C=1.5), with widening k=2, alpha=0.3 checked before a two-proposal batch.
E16 resolves to at most 12 search iterations in each domain, batch 2,
three relocations and 32/16 adapter calls per 2D/3D root-round. YAML defaults
are not substituted for these actual configurations.

O0 remains genuinely q-blind and supports strict open-loop action selection.
O1 adds actual observed joint sin/cos/visibility to policy and Q, for closed-loop
or saved physical tree states. Full simulator/gripper state is carried physically
but is not a learned input. O0/O1 share supervision; missing or synthesized q
cannot silently enter O1 deployment. The original robot geometry, action grammar,
terminal connector and independent canonical Y teacher are preserved.

## Executed E16 search and distillation

Run: `/scratch/nav/disco_grid/stage2/campaigns/E16_v1_20261117` on gvlab.
Each domain's TRAIN roster has independent source-component quotas
K0/K1/K2/K3/NONE = 3/4/3/4/2; connected lineage joins shared parent, layout,
raw or input hashes. Both rounds were attempted on the frozen roster.

| Domain | Independent attempted TRAIN roots | Root-round attempts | Clean / quarantined | Charged intents / returned queries | Child CPU / wall seconds |
|---|---:|---:|---:|---:|---:|
| 2D | 16 | 32 | 19 / 13 | 544 / 531 | 3051.345 / 3293.410 |
| 3D | 16 | 32 | 31 / 1 | 411 / 411 | 6910.110 / 6996.630 |

All charged attempts remain in the denominator and cost ledger. Thirteen 2D
intents lack returned evidence; their actual dispatch/execution cannot be
certified, so they are charged and remain unknown. The quarantined 3D R0 NONE
attempt returned all 11 queries before a resource-guard stop; only its completed
eight-call checkpoint is eligible. Its three returned tail queries remain
archived, outside fitting. The old interrupted Stage 1 K3 run is separately
QUARANTINED_UNRECOVERABLE; its call and CPU counts remain UNKNOWN.

| Domain/round | Feasible checkpoint edges at depth 1 | Depth 2 | Depth 3 |
|---|---:|---:|---:|
| 2D R0 | 37 | 48 | 29 |
| 2D R1 | 37 | 47 | 33 |
| 3D R0 | 38 | 27 | 7 |
| 3D R1 | 48 | 44 | 17 |

Depth/STOP tables use completed checkpoints, including separately certified
prefixes, and exclude unfinished iteration tails. A successful absorbing STOP
child is not counted again as a second physical STOP observation.

P0 is the unchanged previously trained isolated-placement model. New work
completes P0 → R0 → P1/Q1 → fresh R1 → P2/Q2 in both domains. There are
**63 completed 45-epoch fits**, model seeds 0/1/2, batch 64,
AdamW lr .001, weight decay .0001, constant learning rate, fixed final epoch.
O0/O1 all-feasible and O0 successful-only controls are trained. Policy-edge
controls retain bitwise-identical Q weights within each matched data/schedule
condition. Successful-only P2 starts from all-feasible P1; it is not a wholly
successful-only curriculum. Legacy `val_*` loss fields monitor TRAIN rows here.

| Final primary data | Eligible trees/prefixes | Independent TRAIN roots | Trees with a solution | Adapter queries represented | Destination / object-or-STOP / Q rows |
|---|---:|---:|---:|---:|---:|
| 2D | 26 | 13 | 11 | 512 | 231 / 247 / 309 |
| 3D | 32 | 16 | 15 | 408 | 181 / 213 / 269 |

These are training/search counts, never held-out success percentages. Seven
2D completed prefixes augment 19 clean trees, giving 26 trees on 13 roots;
the earlier six-prefix/25-tree prose was incorrect. The saved data and weights
were already correct. In 3D, the one recovered R0 prefix was available before
P1 and therefore also entered the first pooled P2. The original `3d_P2Q2`
folder is preserved and is not called clean-only. The genuine current-P2 clean
control is `3d_P2Q2_strictclean`: 31 clean trees, 16 roots, 400 represented calls,
180 destination rows, 212 object/STOP rows and 266 Q rows. It uses the identical
P1 initialization and training settings. The 2D clean control has 19 trees and
405 represented calls. Neither contrast is a root-count learning curve.

The prospective correction changed only the 3D coverage-control entries:
`CANDIDATE_CONTROL_CORRECTION.json` verifies 3,470 other candidate jobs retain
their model bindings and decisions. Ninety control entries across the three
candidate thresholds use the corrected control. No held-out outcome informed
this repair; all original runs and candidate files remain archived.

## Failure diagnosis supported so far

All 45 returned terminal probes on the E16 3D K3 TRAIN roots passed X and
failed canonical Y with “no feasible side grasp.” None supplies a positive K3
terminal witness. Search now reaches physically executed depth-three states,
but these terminal probes failed to clear a target-feasible endpoint under the
pinned teacher. This does not exclude ordering problems among rejected
transitions and is not a universal physical impossibility theorem. A shaped
progress return or decreasing training loss does not establish task success.

The learned Q target is the decided visited descendant-leaf success fraction,
weighted by log(1+n_decided), rather than geometric progress. In tree search it
initializes unvisited children; the first root-path backup overwrites that prior
with shaped return. Final Q benefit, K0 stopping, NONE abstention, ordering-failure
rates and O1 benefit require the active independent verification. X=0,Y=1 alone
will be reported as execution failure at a feasible endpoint, not causal proof
that order was the sole error.

## Compute, artifacts and visual evidence

Only gvlab ran physical collection and model fitting: one low-priority CPU
worker, one thread, zero GPU allocation. The other three hosts were inventory
only. Existing workloads were preserved. Source-only analytical tests and JSON
plot prototypes also ran locally; no local physical experiment was launched.

Collection children used 9961.455 CPU seconds
and 10290.040 elapsed seconds across 64 attempts.
Fitting children used 677.550 CPU seconds and
1165.656 elapsed seconds across nine attempts,
including interruptions. Recorded cumulative controller work is
296.146 CPU /
41.980 active wall seconds.
The E16 recorded subtotal is 10935.151
CPU / 11497.676 active wall seconds.
Do not add overlapping per-domain/shared upper bounds again.

The conservatively charged fitting upper bound is
973.697 CPU /
1207.637 active wall seconds,
below both 1,800-second limits. Peak sampled collection-child RSS is
834248 KiB; fitting-child RSS
689268 KiB. These are sampled child
peaks, not a falsely exact combined-machine RSS maximum. Earlier pilot,
test, rendering and audit costs are separate. Unprofiled CPU and the old
unrecoverable query are UNKNOWN; no all-stage exact grand total is claimed.

There are 16 native saved-state frames: first frozen TRAIN roots in
all five strata per domain, plus every saved endpoint pose of the ordered
fixtures. The 3D figures retain actual subcell geometry; their inset is explicitly
a canonical-cell projection. Eight 3D model constructions each perform 5,000
initialization integration steps, discarded before saved-state restoration.
Post-restoration integration and planning are zero. Profiled frame generation
used 189.05 CPU seconds / 188.94 wall seconds, peak RSS 1,065,176 KiB.
The repeated fixture's native mesh-vertex hashes match the earlier snapshot;
an exhaustive historical transitive-asset checksum attestation is unavailable.

Large states, witnesses, trainer states and exported weights stay in the
versioned gvlab store, with byte hashes and completed-export checks. Git carries
small manifests, CSV/JSON, plots, frame exports, source and reproduction commands.
`trained_checkpoint_manifest.json` identifies the deployed model paths/seeds/
schemas and hashes. Completed-fit manifests additionally cover unused trained
controls and resumable optimizer/RNG states.

## Physical results and active execution

**2D O0 open loop, O0 closed loop and O1 closed loop: RUNNING_VAL; final results pending.**
**3D O0 open loop, O0 closed loop and O1 closed loop: queued within the authorized run; final results pending.**
Numerators, confidence intervals, per-K success, latency, ordering failures and
paired ablation effects are unavailable, not zero. No final prediction or
verification JSONL is manufactured before VAL selection and actual execution.

The frozen proposal uses 15 VAL and 25 exploratory TEST roots per domain,
three/five per legacy stratum. Each primary TEST protocol has 25 distinct roots
and 75 fixed-model-seed trials; K1–K3 task results have 15 roots / 45 trials.
Secondary evolution/coverage comparisons use common seed 0. This is a balanced
resource-limited cohort, not the full 749/370-root TEST splits or untouched
confirmation. Known own exposed source components are excluded; exhaustive
external exposure is not attested. Statistics retain unresolved/unexecuted
trials and use 10,000 root-family bootstrap replicates, RNG seed 20261117.

E16 explicitly excluded final TEST. The separate V15-F25-v1 request is explicitly approved: 510 VAL trials, then at most 1,050 selected TEST trials, one CPU worker,
zero GPUs, 4 GiB RAM / 10 GiB new disk, and the same 4-hour 2D / 8-hour 3D combined
CPU/active-wall ceilings. Corrected candidate hashes are frozen before any
physical outcome; the 5,523 charged-call ceiling is enforced even though the
uncached matrix upper bound is six calls larger. Lawful reuse can reduce calls.
VAL alone selects admission eta; TEST requires a persisted selection freeze.

Root-count and search-call performance ladders are NOT_RUN (only the E16 rung
was collected). Actual servo integration arc length is NOT_RECORDED; accepted
corrective/reference waypoint travel will be labeled separately. Full-arm
animation, capacity-matched q controls, reward/widening ablations and retry
experiments are NOT_RUN. No saturation or sufficiently trained K3 performance
claim is made. The next permitted resource-dependent step is the separately
approved serial physical evaluation, followed by stored-outcome analysis and
completion of the numerical methods/results section.

See `REPRODUCTION.md`, `RESOURCE_TOTALS.json`, `STAGE2_FINAL_STATUS.json`,
`training_release_v2/`, `training_release_v1/scenes/` and the final byte index.

## Evaluation authorization and launch

The user explicitly replied “Authorize VAL and TEST for both domains”.
`EVALUATION_APPROVED.json` records the unchanged resource ceilings and the
prospective clean-control correction. `EVALUATION_LAUNCH.json` records the
identity-scoped gvlab launch at 2026-11-17T12:02:09Z, with zero GPU allocation.
VAL runs first; the preregistered coverage gate and VAL-only eta selection
freeze the TEST branch before TEST execution. No additional collection or
competing method is authorized by this release.
