"""Regenerate the pre-evaluation release audit from actual archived TRAIN records.

This never supplies missing task-success numbers. Once physical metrics exist,
use analyze_evaluation.py and update the numerical release instead of replacing
it with this explicitly partial, pre-evaluation report.
"""
import argparse, collections, csv, datetime, hashlib, json
from pathlib import Path


def read(path):return json.loads(path.read_text())
def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')


def report(root):
    if (root/'FINAL_METRICS.json').exists() and read(root/'FINAL_METRICS.json').get('metrics'):raise ValueError('Do not replace measured physical results with a pre-evaluation report')
    coverage=read(root/'training_release_v2/training_coverage.json');resources=read(root/'RESOURCE_TOTALS.json')
    figures=root/'training_release_v2/train_figures_corrected'
    with (figures/'DISTILLATION_COVERAGE.csv').open() as file:fits=list(csv.DictReader(file))
    tests=(root/'training_release_v2/tests.log').read_text().strip().splitlines()[-1]
    envelope=read(root/'EVALUATION_ENVELOPE_REQUEST.json');prep=read(root/'evaluation_preparation_manifest.json')
    cohort=read(root/'evaluation_cohorts_v2.json');checkpoints=read(root/'trained_checkpoint_manifest.json')
    def fit(dom,name):return next(x for x in fits if x['domain']==dom and x['fit']==name and x['schema']=='o0_v1' and x['edges_mode']=='all_feasible' and x['seed']=='0')
    def row(dom):return coverage['totals'][dom]
    collection_table='\n'.join(f"| {dom.upper()} | {row(dom)['n_independent_attempted_roots']} | {row(dom)['n_attempted']} | {row(dom)['n_clean']} / {row(dom)['n_quarantined']} | {row(dom)['charged_intents']} / {row(dom)['returned_queries']} | {row(dom)['cpu_s']:.3f} / {row(dom)['wall_s']:.3f} |" for dom in ('2d','3d'))
    fit_table='\n'.join(f"| {dom.upper()} | {x['n_trees']} | {13 if dom=='2d' else 16} | {x['trees_with_solution']} | {x['physical_calls_in_data']} | {x['destination_rows']} / {x['obj_rows']} / {x['value_rows']} |" for dom in ('2d','3d') for x in [fit(dom,f'{dom}_P2Q2_knownprefix')])
    depth_table=[]
    for dom in ('2d','3d'):
        for rnd in ('R0','R1'):
            counts=collections.Counter()
            for item in coverage['records']:
                if item['domain']==dom and item['round']==rnd:counts.update(item['checkpoint_depth_counts'])
            depth_table.append(f"| {dom.upper()} {rnd} | {counts['1']} | {counts['2']} | {counts['3']} |")
    native=read(root/'training_release_v1/scenes/scene_manifest.json')
    paragraphs=f'''# DISCO-Grid Stage 2 release audit

**Verdict: PARTIAL. TRAIN execution and model freezing are complete. New learned-policy physical VAL/TEST metrics are NOT_RUN, awaiting the separate evaluation authorization. NOT_RUN is not 0% success.**

This audit is generated from stored records by `report_training_release.py`.
It does not replace the preserved D0–D8 or Stage 1 results. The release contains
no competing-method performance study.

## Source, implementation and preservation

Branch: `naren/disco-grid-stage2`, based on verified validation commit
`8c5213fd0c7cb739e2358452564320eac1891db5`. The physical collection/training
engine is immutable commit `89f16995f5ad0d127b3cf3b807cb66bcf9565bfc`.
The corrected physical-evaluation engine and its tested sources are
`{prep['source_commit']}`. Later report-only commits do not change these engines.

The final gvlab suite reports **{tests}**. All 92 protected checkpoint/teacher
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
{collection_table}

All charged attempts remain in the denominator and cost ledger. Thirteen 2D
intents lack returned evidence; their actual dispatch/execution cannot be
certified, so they are charged and remain unknown. The quarantined 3D R0 NONE
attempt returned all 11 queries before a resource-guard stop; only its completed
eight-call checkpoint is eligible. Its three returned tail queries remain
archived, outside fitting. The old interrupted Stage 1 K3 run is separately
QUARANTINED_UNRECOVERABLE; its call and CPU counts remain UNKNOWN.

| Domain/round | Feasible checkpoint edges at depth 1 | Depth 2 | Depth 3 |
|---|---:|---:|---:|
{chr(10).join(depth_table)}

Depth/STOP tables use completed checkpoints, including separately certified
prefixes, and exclude unfinished iteration tails. A successful absorbing STOP
child is not counted again as a second physical STOP observation.

P0 is the unchanged previously trained isolated-placement model. New work
completes P0 → R0 → P1/Q1 → fresh R1 → P2/Q2 in both domains. There are
**{len(fits)} completed 45-epoch fits**, model seeds 0/1/2, batch 64,
AdamW lr .001, weight decay .0001, constant learning rate, fixed final epoch.
O0/O1 all-feasible and O0 successful-only controls are trained. Policy-edge
controls retain bitwise-identical Q weights within each matched data/schedule
condition. Successful-only P2 starts from all-feasible P1; it is not a wholly
successful-only curriculum. Legacy `val_*` loss fields monitor TRAIN rows here.

| Final primary data | Eligible trees/prefixes | Independent TRAIN roots | Trees with a solution | Adapter queries represented | Destination / object-or-STOP / Q rows |
|---|---:|---:|---:|---:|---:|
{fit_table}

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
rates and O1 benefit require the pending independent verification. X=0,Y=1 alone
will be reported as execution failure at a feasible endpoint, not causal proof
that order was the sole error.

## Compute, artifacts and visual evidence

Only gvlab ran physical collection and model fitting: one low-priority CPU
worker, one thread, zero GPU allocation. The other three hosts were inventory
only. Existing workloads were preserved. Source-only analytical tests and JSON
plot prototypes also ran locally; no local physical experiment was launched.

Collection children used {resources['collection']['child_cpu_s']:.3f} CPU seconds
and {resources['collection']['child_wall_s']:.3f} elapsed seconds across 64 attempts.
Fitting children used {resources['fitting']['child_cpu_s']:.3f} CPU seconds and
{resources['fitting']['child_wall_s']:.3f} elapsed seconds across nine attempts,
including interruptions. Recorded cumulative controller work is
{resources['recorded_controller_overhead']['cpu_s']:.3f} CPU /
{resources['recorded_controller_overhead']['wall_s']:.3f} active wall seconds.
The E16 recorded subtotal is {resources['recorded_E16_subtotal']['cpu_s']:.3f}
CPU / {resources['recorded_E16_subtotal']['active_wall_s']:.3f} active wall seconds.
Do not add overlapping per-domain/shared upper bounds again.

The conservatively charged fitting upper bound is
{resources['neural_charged_upper_bound']['cpu_s']:.3f} CPU /
{resources['neural_charged_upper_bound']['wall_s']:.3f} active wall seconds,
below both 1,800-second limits. Peak sampled collection-child RSS is
{resources['collection']['sampled_peak_child_rss_kib']} KiB; fitting-child RSS
{resources['fitting']['sampled_peak_child_rss_kib']} KiB. These are sampled child
peaks, not a falsely exact combined-machine RSS maximum. Earlier pilot,
test, rendering and audit costs are separate. Unprofiled CPU and the old
unrecoverable query are UNKNOWN; no all-stage exact grand total is claimed.

There are {len(native)} native saved-state frames: first frozen TRAIN roots in
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

## Physical results and remaining gate

**2D O0 open loop, O0 closed loop and O1 closed loop: NOT_RUN.**
**3D O0 open loop, O0 closed loop and O1 closed loop: NOT_RUN.**
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

E16 explicitly excluded final TEST. The separate V15-F25-v1 request remains
pending: 510 VAL trials, then at most 1,050 selected TEST trials, one CPU worker,
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
'''
    (root/'FINAL_DISCO_STAGE2_REPORT.md').write_text(paragraphs)
    statuses={
        'S2.0':('DONE','Verified source/archive replay, 92 hashes and split locks; transitive historical asset checksums not fully attested'),
        'S2.1':('DONE','Old interruption quarantined with UNKNOWN accounting; new journals and independent watchdogs verified'),
        'S2.2':('DONE','Search/STOP/Q/state/checkpoint fixes and 69-test suite; no empirical Q benefit inferred'),
        'S2.3':('DONE','Bounded physical pilots and four fresh order-parity fixtures executed'),
        'S2.4':('DONE','Frozen independent TRAIN roster and explicit E16 authorization; exploratory evaluation roster frozen'),
        'S2.5':('DONE','Both actual iterative cycles and matched O0/O1/filter controls trained within E16; limited K3 positives and no saturation claim'),
        'S2.6':('PARTIAL','Models/ablation matrices prepared; physical VAL/paired effects and root/budget ladders NOT_RUN'),
        'S2.7':('BLOCKED','Separate physical VAL/TEST compute approval pending; every final task-success metric NOT_RUN'),
        'S2.8':('PARTIAL','Native frames and TRAIN plots complete; held-out performance/failure/calibration figures NOT_RUN'),
        'S2.9':('PARTIAL','Implementation and auditable TRAIN release pushed; final numerical physical release incomplete')}
    write(root/'STAGE2_FINAL_STATUS.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),overall='PARTIAL',physical_task_results='NOT_RUN',
        gates={key:dict(status=value[0],reason=value[1]) for key,value in statuses.items()},generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    write(root/'FINAL_METRICS.json',dict(status='NOT_RUN',metrics={},paired={},reason='No new physical VAL/TEST outcome; awaiting the separate evaluation approval',training_counts_are_not_task_success=True))
    write(root/'final_config.json',envelope);write(root/'final_checkpoints.json',checkpoints);write(root/'final_root_manifest.json',cohort)
    with (root/'FINAL_METRICS.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=['domain','protocol','status','planned_roots','planned_task_roots','planned_primary_model_seeds','verified_success','success_rate','ci95_low','ci95_high']);writer.writeheader()
        for dom in ('2d','3d'):
            for protocol in ('O0_open_loop','O0_closed_loop','O1_closed_loop'):writer.writerow(dict(domain=dom,protocol=protocol,status='NOT_RUN',planned_roots=25,planned_task_roots=15,planned_primary_model_seeds='0,1,2'))
    with (root/'ABLATIONS.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=['comparison','physical_status','delta','ci95_low','ci95_high']);writer.writeheader()
        for name in ('P0_P1_P2','Q2_on_off','P1_all_feasible_success_only','P2_all_feasible_success_only','P2_clean_recovered_prefix_data','O0_O1_closed_loop','TRAIN_root_ladder','search_budget_ladder'):writer.writerow(dict(comparison=name,physical_status='NOT_RUN'))
    for name in ('SEARCH_COVERAGE.csv','CENSORING_LEDGER.csv','RESOURCE_ACCOUNTING.csv'):(root/name).write_bytes((figures/name).read_bytes())
    return dict(status='PARTIAL',new_fits=len(fits),physical_results='NOT_RUN',test_result=tests)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);args=parser.parse_args();print(json.dumps(report(args.root),indent=2))
