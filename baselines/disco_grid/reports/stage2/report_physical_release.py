"""Write a standalone audit from measured, frozen DISCO release metrics.

Reporting only: this module never loads a model, changes selection, or calls a
teacher. Missing TEST evidence stays NOT_RUN, including when VAL gates stop a run.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

PRIMARY = ('O0_P2Q2', 'O0_closed_P2Q2', 'O1_closed_P2Q2')
NAMES = dict(zip(PRIMARY, ('O0 open loop', 'O0 closed loop', 'O1 closed loop')))


def read(path):
    return json.loads(path.read_text())


def percent(value):
    return 'unavailable' if value is None else f'{100 * value:.2f}%'


def measured_cell(item):
    if not item or item.get('status') == 'NOT_RUN':
        return 'NOT_RUN'
    low, high = item['ci95']
    return (f"{item['n_verified_success']}/{item['n_expected_predictions']} = "
            f"{percent(item['success_rate'])} [{percent(low)}, {percent(high)}]; "
            f"{item['n_roots']} roots; unknown {item['n_unresolved_or_unexecuted']}")


def report(release, metrics_dir, training_reports):
    data = read(metrics_dir / 'FINAL_METRICS.json')
    envelope = read(release / 'APPROVED_ENVELOPE.json')
    freeze = read(release / 'SELECTION_FREEZE.json') if (release / 'SELECTION_FREEZE.json').exists() else None
    complete = read(release / 'COMPLETE.json') if (release / 'COMPLETE.json').exists() else None
    resources = read(training_reports / 'RESOURCE_TOTALS.json')
    groups = data['metrics']

    def entry(domain, arm):
        found = [v for k, v in groups.items()
                 if k.split('|')[:2] == ['test', domain] and k.split('|')[3] == arm]
        if len(found) > 1:
            raise ValueError('Multiple TEST thresholds: refusing outcome-dependent selection')
        return found[0] if found else None

    primary = [entry(d, a) for d in ('2d', '3d') for a in PRIMARY]
    test_complete = bool(complete) and all(
        m and m['overall']['status'] == 'MEASURED' for m in primary)
    phase_costs = []
    for phase in ('val', 'test'):
        for domain in ('2d', '3d'):
            p = release / f'{phase}_{domain}' / 'ACCOUNTING.json'
            if p.exists():
                phase_costs.append(dict(phase=phase, domain=domain, **read(p)))
    physical_cost = dict(
        phase_cpu_s=sum(p['cpu_s'] for p in phase_costs),
        phase_active_wall_s=sum(p['active_wall_s'] for p in phase_costs),
        charged_adapter_calls=sum(p['adapter_calls'] for p in phase_costs),
        phase_attempted_predictions=sum(p['n_attempted'] for p in phase_costs),
        phase_not_run_predictions=sum(p['n_not_run'] for p in phase_costs),
        release_total_cpu_s=complete.get('total_cpu_s') if complete else None,
        release_total_wall_s=complete.get('total_wall_s') if complete else None,
        scope='Phase CPU includes controller plus reaped workers. Release totals include shared overhead; do not add both. Absent release totals are UNKNOWN.',
        phases=phase_costs)
    if physical_cost['charged_adapter_calls'] > envelope['global_adapter_call_ceiling']:
        raise ValueError('Physical-call authorization exceeded')
    for p in phase_costs:
        cap = envelope['ceilings'][p['domain']][p['phase']]
        if max(p['cpu_s'], p['active_wall_s']) > cap:
            raise ValueError('Recorded phase cost exceeds approved ceiling')

    lines = [
        '# DISCO-Grid Stage 2 final physical release audit', '',
        '**Overall status: PARTIAL.** Physical evaluation status: **' +
        ('MEASURED' if test_complete else 'PARTIAL / NOT_RUN where indicated') + '**.', '',
        'This is a standalone DISCO study. All rates below come from independently '
        'executed teacher episodes or exact, source-bound verification certificates. '
        'Training loss and search success are never substituted for learned-policy performance.', '',
        f"Run: `{release}`. Execution host: {envelope['host']}; {envelope.get('workers',1)} low-priority CPU worker(s), zero GPU allocation. "
        'Both VAL and TEST were explicitly authorized. Previous archives remain preserved.', '',
        'The cohort contains 15 VAL and 25 exploratory TEST roots/domain, balanced '
        'over K0/K1/K2/K3/NONE. The three primary protocols use three fixed model '
        'seeds, so their K1–K3 denominator is 15 roots and 45 predictions. '
        'Source-family bootstrap intervals use 10,000 replicates, seed 20261117; '
        'model seeds remain within each root. These small balanced cohorts are '
        'neither full-TEST population estimates nor untouched confirmation.', '',
        'Missing or interrupted outcomes remain in the fixed denominator and the '
        'unknown ledger. Verified-success rates are intention-to-evaluate lower '
        'bounds when outcomes are unknown; unknowns are never certified physical '
        'negatives. Explicit abstention uses no physical query.', '',
        '## Primary physical task results', '',
        '| Domain | Protocol | K1–K3 verified task success, 95% root CI |',
        '|---|---|---|']
    for domain in ('2d', '3d'):
        for arm in PRIMARY:
            m = entry(domain, arm)
            lines.append(f"| {domain.upper()} | {NAMES[arm]} | {measured_cell(m['tasks_K1_K2_K3'] if m else None)} |")
    lines += ['', '## Per-stratum results', '',
              'K0 and NONE physical success are shown separately from their intended '
              'NOOP and explicit-abstention diagnostics. A newly verified NONE '
              'repair is retained rather than relabeled from the legacy stratum.', '',
              '| Domain | Protocol | K | Verified physical success, 95% root CI |',
              '|---|---|---|---|']
    for domain in ('2d', '3d'):
        for arm in PRIMARY:
            m = entry(domain, arm)
            for k in ('0', '1', '2', '3', 'NONE'):
                lines.append(f"| {domain.upper()} | {NAMES[arm]} | {k} | {measured_cell(m['by_K'][k] if m else None)} |")
    lines += ['', '## Stopping, execution failures and inference costs', '',
              '| Domain | Protocol | K0 verified NOOP | K0 relocation predictions | NONE explicit abstention | X=0,Y=1 | Neural latency median / p95 ms |',
              '|---|---|---|---|---|---|---|']
    for domain in ('2d', '3d'):
        for arm in PRIMARY:
            m = entry(domain, arm)
            if not m:
                lines.append(f'| {domain.upper()} | {NAMES[arm]} | NOT_RUN | — | — | — | — |')
                continue
            d = m['deployment_diagnostics'];lat = d['latency_ms']
            lines.append(f"| {domain.upper()} | {NAMES[arm]} | {d['n_verified_NOOP_K0']}/{d['n_expected_K0']} | {d['n_unnecessary_relocation_K0']} | {d['n_explicit_abstention_NONE']}/{d['n_expected_NONE']} | {d['execution_failure_at_target_feasible_endpoint']} | {lat['median']} / {lat['p95']} |")
    lines += ['', 'X=0,Y=1 denotes execution failure at a target-feasible endpoint; '
              'it does not establish that order alone caused the failure. Complete '
              'failure phases/kinds, action counts and reference path travel remain '
              'in FINAL_METRICS.json. Travel measures accepted corrective joint '
              'waypoints plus the certified connector, excluding target Y; actual '
              'servo-integrated arc is NOT_RECORDED. Cached certificates reduce '
              'physical calls, not neural latency measurements.', '',
              '## Paired DISCO-only ablations', '',
              '| Domain / contrast | Task-success difference | 95% root CI | Roots / fixed seeds | Unknown paired trials |',
              '|---|---|---|---|---|']
    for name, item in sorted(data['paired'].items()):
        if not name.startswith('test|'):
            continue
        if item.get('delta') is None:
            lines.append(f"| {name} | {item.get('status','NOT_RUN')} | unavailable | {item['n_roots']} / {item['fixed_seeds']} | {item['unknown_pair_trials']} |")
            continue
        lo, hi = item['ci95']
        lines.append(f"| {name} | {100*item['delta']:.2f} pp | [{100*lo:.2f}, {100*hi:.2f}] pp | {item['n_roots']} / {item['fixed_seeds']} | {item['unknown_pair_trials']} |")
    if not any(k.startswith('test|') for k in data['paired']):
        lines.append('| All TEST contrasts | NOT_RUN | unavailable | unavailable | unavailable |')
    lines += ['', 'Q on/off, policy evolution, all-feasible/successful-only, clean/prefix '
              'data and observed-joint effects use identical frozen roots and common '
              'model seeds. Secondary evolution/coverage arms use seed 0. '
              'These are descriptive paired estimates without multiplicity-adjusted '
              'hypothesis tests. No improvement is inferred from fitting loss. '
              'Successful-only P2 starts from all-feasible P1, and the clean-data '
              'contrast holds current-P2 fitting controls fixed; neither is a '
              'whole-curriculum or root-count learning curve.', '',
              '## VAL-only selection and provenance', '',
              ('Selected eta: `' + json.dumps(freeze['selected_eta'], sort_keys=True) +
               '`. SELECTION_FREEZE.json records the VAL evidence hashes and '
               'selected TEST job identities before TEST execution.' if freeze else
               '**No selection freeze exists. TEST is NOT_RUN; no threshold is '
               'selected from incomplete or TEST outcomes.**'), '',
              'final_predictions.jsonl, final_verifications.jsonl, final_root_manifest.json '
              'and final_checkpoints.json preserve the actual model/root bindings. '
              'The checkpoint registry has SHA-256 hashes; all large weights, '
              'optimizer/RNG states and physical witnesses remain on gvlab. '
              'The completed TRAIN inventory verified 315 checkpoint files from '
              '63 fits. The prospective 3D clean-control correction used no held-out '
              'outcome; original candidates and weights remain archived.', '',
              '## Resource accounting', '',
              '| Phase | Domain | Predictions attempted / frozen | Charged adapter calls | Charged CPU s | Active wall s |',
              '|---|---|---|---|---|---|']
    for p in phase_costs:
        lines.append(f"| {p['phase']} | {p['domain']} | {p['n_attempted']}/{p['n_frozen_jobs']} | {p['adapter_calls']} | {p['cpu_s']:.3f} | {p['active_wall_s']:.3f} |")
    lines += ['', 'PHYSICAL_RESOURCE_TOTALS.json provides non-overlapping phase costs '
              'and, when available, shared-overhead-inclusive release totals. '
              'All interrupted attempts are charged. Phase limits and the 5,523-call '
              'global ceiling are checked against the explicit approval. TRAIN '
              f"recorded subtotal: {resources['recorded_E16_subtotal']['cpu_s']:.3f} CPU / "
              f"{resources['recorded_E16_subtotal']['active_wall_s']:.3f} active-wall seconds. "
              'These scopes must not be summed with overlapping upper bounds. '
              'Older unprofiled work remains UNKNOWN; no exact all-stage total is claimed.', '',
              '## Implementation, TRAIN evidence and remaining work', '',
              'TRAINING_RELEASE_AUDIT.md retains the detailed search/distillation '
              'audit: 16 independent attempted TRAIN roots/domain in two rounds, '
              '544/411 charged intents (2D/3D), certified prefix handling and the '
              'P0→R0→P1/Q1→R1→P2/Q2 chain. O0 is q-blind; O1 consumes actual '
              'observed joints in closed loop. Geometry and the independent physical '
              'X/Y contract are unchanged. The deployed physical engine is pinned '
              'in the preparation manifest, separately from later reporting code.', '',
              'Search remains UCB C=1.5, widening k=2 and alpha=.3 before a '
              'two-proposal batch, with a 12-iteration E16 cap. Q is learned from '
              'decided descendant-leaf success fractions; its unvisited-child prior '
              'is overwritten by shaped-return backup. All 45 returned 3D K3 '
              'TRAIN terminal probes passed X and failed target Y with no feasible '
              'side grasp. This diagnoses missing successful endpoint evidence, '
              'not universal impossibility or learned-policy performance.', '',
              'DONE: source/archive audit, journal/watchdog/checkpoint fixes, '
              'bounded physical pilots, two iterative TRAIN rounds, 63 completed '
              'fits and frozen candidates. Physical evaluation completion is '
              'reported from evidence above. PARTIAL: overall Stage 2 because '
              'root-count/search-budget task-success ladders were not collected. '
              'NOT_RUN: additional ladder rungs, capacity-matched joint controls, '
              'reward/widening/retry experiments and full-arm animation. '
              'NOT_RECORDED: actual servo arc. UNKNOWN: exhaustive external TEST '
              'exposure, historical transitive assets and old unrecoverable query '
              'costs. No saturation or sufficiently trained K3 claim is made.', '',
              'Sixteen native saved-state frames and TRAIN loss/search-coverage '
              'figures accompany the release. Held-out plots use measured metrics '
              'only. ROOT_STOP_DIAGNOSTICS.json uses independent root STOP probes '
              'for descriptive raw-Q calibration, never legacy K labels or fitted '
              'TEST calibration. Reproduction commands are in REPRODUCTION.md.', '']
    if (release/'HOST_MIGRATION.json').exists():
        migration=read(release/'HOST_MIGRATION.json')
        lines += ['## User-directed host migration', '',
            'The user revoked gvlab execution and authorized girish-laptop. '
            'Existing gvlab evidence was copied with byte-hash checks; finished '
            'and interrupted trials were retained without retry. The primary '
            'models, roots, rules and precommitted open-loop sequences are unchanged. '
            'VAL therefore includes both hosts where recorded; TEST is on the '
            'laptop. Only file paths and the explicit host guard were amended.', '',
            'All gvlab query intents and reaped worker CPU remain charged. The '
            'detached gvlab controller\'s final CPU could not be recovered, so '
            'its entire elapsed interval is conservatively charged as controller '
            'CPU, in addition to exact reaped worker CPU. Thus phase/total CPU '
            'figures containing gvlab work are charged upper bounds, not exact '
            'CPU measurements. Worker accounts and HOST_MIGRATION.json retain '
            'the distinction. Environment installation/transfer qualification is '
            'reported separately from physical query runtime.', '']
    if (release/'PARALLEL_HANDOFF.json').exists():
        lines += ['## Explicitly authorized three-worker execution', '',
            'The user authorized at least three CPU workers and both laptops. '
            'The run uses three one-thread physical workers on Girish, each '
            'with its own supervisor and durable query journal. Total CPU and '
            'adapter-call quotas are reserved before dispatch; active wall time '
            'is elapsed pool time, not the sum of concurrent worker durations. '
            'All prior serial attempts remain charged and are not retried.', '',
            'The other methodology job was observed using 16 workers on Girish '
            'and 14 on the user laptop. DISCO physical workers use nice 19 and '
            'leave the other processes unchanged. The user laptop had only '
            'about 6 GiB available RAM, below the unchanged 8 GiB headroom '
            'guard, so no physical DISCO worker was allocated there. The pool '
            'retains the shared 4 GiB RSS ceiling plus individual watchdogs. '
            'Configured workers do not guarantee three simultaneously active '
            'trials near the end of a queue or budget.', '',
            'Frozen CPU inference is retained. Measured 2D neural-selection '
            'latencies totalled 0.85 seconds during a 1,747.74-second physical '
            'phase, so GPU inference was not the runtime bottleneck. No GPU '
            'speedup is claimed. Parallel execution changes scheduling, not '
            'the model, action grammar, verification caps or TEST selection. '
            'PARALLEL_HANDOFF.json and per-phase accounts record topology, '
            'prior cost bounds and actual pool costs.', '']
    (metrics_dir / 'FINAL_DISCO_STAGE2_REPORT.md').write_text('\n'.join(lines))
    (metrics_dir / 'PHYSICAL_RESOURCE_TOTALS.json').write_text(json.dumps(physical_cost, indent=2)+'\n')
    statuses = read(training_reports / 'STAGE2_FINAL_STATUS.json')
    statuses.update(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), overall='PARTIAL',
                    physical_task_results='MEASURED' if test_complete else 'PARTIAL_OR_NOT_RUN')
    statuses['gates']['S2.7'] = dict(status='DONE' if test_complete else 'PARTIAL',
        reason='See fixed-denominator metrics, censoring ledger and phase accounting; no unknown outcome imputed as a physical negative.')
    statuses['gates']['S2.6'] = dict(status='PARTIAL', reason='Prepared arms physically evaluated where recorded; additional root/search-budget ladders NOT_RUN.')
    statuses['gates']['S2.8'] = dict(status='DONE' if test_complete and (metrics_dir/'figures/figure_sources.json').exists() else 'PARTIAL',
        reason='Native TRAIN frames preserved; measured held-out plots and deterministic saved-state failure frames generated where actual evidence exists. Missing independent STOP probes or failure states are not fabricated.')
    statuses['gates']['S2.9'] = dict(status='PARTIAL', reason='Standalone evidence/report packaged; unexecuted ladder experiments and other limitations explicitly retained.')
    statuses['report_generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (metrics_dir / 'STAGE2_FINAL_STATUS.json').write_text(json.dumps(statuses, indent=2)+'\n')
    base = (training_reports / 'PAPER_METHODS_AND_RESULTS.md').read_text()
    base = base.split('<!-- MEASURED_STAGE2_RESULTS -->')[0]
    base = base.split('Final evaluation is proposed')[0]
    base = base.replace('Final independently\nverified model task-success results are NOT_RUN.',
                        'Measured physical evidence and completion limits follow below.')
    base = base.replace('Historical results are not\nsubstituted for the pending study.',
                        'Historical results are not substituted for this physical study.')
    base += '\n<!-- MEASURED_STAGE2_RESULTS -->\n\n' + '\n'.join(lines[lines.index('## Primary physical task results'):])
    (metrics_dir / 'PAPER_METHODS_AND_RESULTS.md').write_text(base)
    return dict(physical_status=statuses['physical_task_results'], phase_costs=physical_cost,
                report_sha256=hashlib.sha256((metrics_dir/'FINAL_DISCO_STAGE2_REPORT.md').read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('release', type=Path)
    parser.add_argument('metrics_dir', type=Path)
    parser.add_argument('training_reports', type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.release, args.metrics_dir, args.training_reports), indent=2))
