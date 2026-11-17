"""After the exact authorized process exits, package measured evidence once.

This observer never starts or restarts physical work. It also packages partial
evidence if the frozen physical release stops at a guard or VAL evidence gate.
"""
import argparse
import datetime
import fcntl
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def start_ticks(stat):
    return stat.rpartition(')')[2].split()[19]


def same_process(launch):
    path = Path('/proc') / str(launch['pid']) / 'stat'
    try:
        stat = path.read_text()
    except FileNotFoundError:
        return False
    return start_ticks(stat) == start_ticks(launch['proc_stat']) and stat.rpartition(')')[2].split()[0] != 'Z'


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(release, out, training):
    analyzer = load('analyze_evaluation')
    result = analyzer.analyze(release, out)
    for name in ('APPROVED_ENVELOPE.json','HOST_MIGRATION.json','PARALLEL_HANDOFF.json','ORIGINAL_TRANSFER_INDEX.json','RESERVED_CORES_HANDOFF.json'):
        source=release/name
        if source.exists():
            (out/name).write_bytes(source.read_bytes())
    # One deterministic first failure per protocol/stratum/kind, not selected by
    # visual appeal. These reference the real physical journals, not new rollouts.
    failures = {}
    rows = [json.loads(line) for line in (out/'final_verifications.jsonl').read_text().splitlines()]
    for row in rows:
        if row.get('verified') == 1 or row.get('status') == 'ABSTAIN':
            continue
        key = '|'.join(str(row.get(k)) for k in ('domain','protocol','K_legacy','failure_kind'))
        if key not in failures:
            failures[key] = row
    (out/'FAILURE_EXAMPLES.json').write_text(json.dumps(dict(
        selection='First frozen TEST job in each domain/protocol/legacy-K/failure-kind; no new physics or model tuning',
        examples=failures), indent=2)+'\n')
    states = []
    selected = []
    for domain in ('2d', '3d'):
        # First actually failed open-loop primary K3 job in frozen execution
        # order. Select at most its original and final queried parent states.
        for row in rows:
            if (row.get('domain') != domain or row.get('arm') != 'O0_P2Q2'
                    or str(row.get('K_legacy')) != '3' or row.get('verified') != 0
                    or row.get('status') == 'ABSTAIN'):
                continue
            directory = Path(row.get('execution_evidence',{}).get('directory',''))
            journal = directory/'queries.jsonl'
            if not journal.is_file():
                continue
            events = [json.loads(line) for line in journal.read_text().splitlines()]
            starts = [e for e in events if e['event']=='started']
            if not starts:
                continue
            paths = list(dict.fromkeys(directory/e['parent_blob'] for e in (starts[0],starts[-1])))
            states.extend(paths)
            selected.append(dict(job_id=row['job_id'],root_id=row['root_id'],domain=domain,
                verified=row['verified'],failure_kind=row.get('failure_kind'),states=list(map(str,paths))))
            break
    (out/'FAILURE_SCENE_SELECTION.json').write_text(json.dumps(dict(
        rule='First independently failed primary open-loop K3 job/domain with actual query-parent blobs; original and last queried parent, at most four frames',
        selections=selected),indent=2)+'\n')
    if states:
        load('scene_evidence').run(states,out/'failure_scenes')
    if result['observed_test_outcomes']:
        load('evaluation_figures').plot(out/'FINAL_METRICS.json', out/'figures')
    reported = load('report_physical_release').report(release, out, training)
    (out/'ANALYSIS_COMPLETE.json').write_text(json.dumps(dict(
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), analysis=result,
        report=reported, physical_queries=0), indent=2)+'\n')


def finish(launch_path, out, training):
    launch = read(launch_path)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise PermissionError('CPU-only reporting')
    # Wall spent observing an existing worker is not active analysis wall time.
    observer_cpu = time.process_time()
    while same_process(launch):
        time.sleep(15)
    release = Path(launch['output'])
    if not (release/'APPROVED_ENVELOPE.json').exists():
        raise RuntimeError('Physical release never passed startup; inspect its log')
    sys.path.insert(0, str(HERE.parents[1]))
    import collect as C
    import data as D
    import journal as J
    C.require_headroom()
    out.mkdir(parents=True, exist_ok=False)
    with (D.DISCO_ROOT/'active_physical.lock').open('a') as lock:
        # Do not overlap with an orphan physical worker or any other DISCO run.
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if same_process(launch):
            raise RuntimeError('Physical process still active')
        ledger = release/'COMPLETE.json'
        if not ledger.exists():
            ledger = release/'EXECUTION_STOPPED.json'
            log = Path(launch['log'])
            J.atomic_json(ledger, dict(status='STOPPED_BEFORE_RELEASE_COMPLETE',
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                launch_sha256=hashlib.sha256(launch_path.read_bytes()).hexdigest(),
                log=str(log),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                tail=log.read_text()[-6000:],reason='See exact logged exception/guard; no restart or outcome imputation'))
        worker = mp.get_context('spawn').Process(target=analyze,args=(release,out,training))
        worker.start()
        J.wait_for_child(worker, 600, directory=out, cpu_seconds=600,
                         rss_limit_kib=3*2**20, resource_check=C.require_headroom)
        if not (out/'ANALYSIS_COMPLETE.json').exists():
            raise RuntimeError('Analysis incomplete: retained watchdog evidence, no physical restart')
        inventory = load('artifact_index').index(release, ledger, out/'physical_evidence_index.json')
        J.atomic_json(out/'FINISH_COMPLETE.json', dict(
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            launch_sha256=hashlib.sha256(launch_path.read_bytes()).hexdigest(),
            inventory=inventory, observer_and_finisher_cpu_s=time.process_time()-observer_cpu,
            physical_queries=0, automatic_physical_restarts=0))
    return str(out/'FINISH_COMPLETE.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('launch', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('training_reports', type=Path)
    args = parser.parse_args()
    print(finish(args.launch, args.out, args.training_reports), flush=True)
