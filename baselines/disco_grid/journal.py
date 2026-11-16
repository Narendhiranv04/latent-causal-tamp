"""Durable query evidence and an external, process-identity-scoped watchdog."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import pickle
import resource
import signal
import time


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('wb') as f:
        f.write(content); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def atomic_json(path, obj):
    atomic_bytes(path, json.dumps(obj, sort_keys=True, indent=2).encode())


def process_identity(pid=None):
    pid = pid or os.getpid()
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start_ticks': int(fields[19]), 'pgid': os.getpgid(pid)}
    except (FileNotFoundError, ProcessLookupError): return None


class QueryJournal:
    """A charged intent precedes dispatch. Missing completion means censored work."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.active = None

    def append(self, record):
        with (self.directory/'queries.jsonl').open('a') as f:
            f.write(json.dumps(record, sort_keys=True)+'\n'); f.flush(); os.fsync(f.fileno())

    def start(self, qid, kind, state_blob, metadata):
        if self.active is not None: raise RuntimeError('Nested physical query')
        if (self.directory/'ACTIVE_QUERY.json').exists():
            raise ValueError('Unreconciled query; dispatch refused')
        parent_name = f'query_{qid:06d}_parent.pkl'
        atomic_bytes(self.directory/parent_name, state_blob)
        rec = dict(metadata, event='started', kind=kind, query_id=qid,
                   identity=process_identity(), parent_identity=process_identity(os.getppid()),
                   parent_blob=parent_name, parent_blob_sha256=hashlib.sha256(state_blob).hexdigest(),
                   monotonic_s=time.monotonic(), wall_time=time.time(), process_cpu_s=time.process_time())
        rec['attempt_id'] = hashlib.sha256((str(self.directory.resolve())+json.dumps(rec,sort_keys=True)).encode()).hexdigest()
        # Intent is durable before caller can dispatch. ACTIVE is for the parent timer.
        self.append(rec)
        atomic_json(self.directory/'ACTIVE_QUERY.json',rec)
        self.active = rec
        return rec

    def finish(self, result):
        if self.active is None: raise RuntimeError('Completion without intent')
        r = self.active
        blob = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
        name = f"query_{r['query_id']:06d}.pkl"
        atomic_bytes(self.directory/name,blob)
        def value(key, default=None):
            return result.get(key,default) if isinstance(result,dict) else getattr(result,key,default)
        child = value('next_state')
        rec = dict(r, event='finished', result_blob=name, result_sha256=hashlib.sha256(blob).hexdigest(),
                   wall_s=time.monotonic()-r['monotonic_s'], cpu_s=time.process_time()-r['process_cpu_s'],
                   status=value('status'), failure_kind=value('failure_kind'),
                   planner_calls=value('planner_calls'),
                   raw_teacher_outcome=value('raw_teacher_outcome'),
                   accounting=value('accounting'),
                   child_state_hash=child.state_hash() if child else None,
                   child_blob_sha256=hashlib.sha256(pickle.dumps(child)).hexdigest() if child else None)
        self.append(rec)
        (self.directory/'ACTIVE_QUERY.json').unlink()
        self.active = None
        return rec


def read_events(directory):
    path=Path(directory)/'queries.jsonl'
    if not path.exists(): return []
    # A torn last line after a hard crash is never silently accepted as a clean boundary.
    return [json.loads(line) for line in path.read_text().splitlines()]


def certify_journal(directory, expected_calls):
    events=read_events(directory)
    starts=[e for e in events if e['event']=='started']
    ends=[e for e in events if e['event']=='finished']
    if len(starts)!=expected_calls or len(ends)!=expected_calls:
        raise ValueError('Query/checkpoint counter mismatch; reconciliation required')
    if [r['query_id'] for r in starts]!=list(range(1,expected_calls+1)):
        raise ValueError('Duplicate or noncontiguous query identities')
    if [r['attempt_id'] for r in starts]!=[r['attempt_id'] for r in ends]:
        raise ValueError('Missing or reordered query completion')
    for row in ends:
        if hashlib.sha256((Path(directory)/row['result_blob']).read_bytes()).hexdigest()!=row['result_sha256']:
            raise ValueError('Query result checksum mismatch')
    for row in starts:
        if hashlib.sha256((Path(directory)/row['parent_blob']).read_bytes()).hexdigest()!=row['parent_blob_sha256']:
            raise ValueError('Parent state checksum mismatch')


def wait_for_child(proc, seconds, grace_s=5., directory=None, query_wall_s=None, resource_check=None):
    """Bound our own child even when a teacher replaces alarms or ignores TERM.

    A separately created session permits targeted cleanup of only this job's group.
    Sampling CPU is a lower bound; reaped child CPU is measured by the OS.
    """
    start=time.monotonic(); identity=process_identity(proc.pid)
    before=resource.getrusage(resource.RUSAGE_CHILDREN)
    reason=None; peak=0; observed_cpu=None; last_check=start
    monitor_error=None
    try:
        while proc.is_alive():
            elapsed=time.monotonic()-start
            if elapsed>=seconds: reason='RUN_WALL_LIMIT'
            if directory:
                for path in Path(directory).rglob('ACTIVE_QUERY.json'):
                    try: active=json.loads(path.read_text())
                    except FileNotFoundError: active=None
                    if active and query_wall_s and time.monotonic()-active['monotonic_s']>=query_wall_s:
                        reason='SINGLE_QUERY_WALL_LIMIT'
            try:
                st=Path(f'/proc/{proc.pid}/status').read_text().splitlines()
                peak=max([peak]+[int(x.split()[1]) for x in st if x.startswith(('VmRSS:','VmHWM:'))])
                fields=Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')',1)[1].split()
                observed_cpu=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
            except (FileNotFoundError,ProcessLookupError): pass
            if resource_check and time.monotonic()-last_check>=5:
                try: resource_check()
                except RuntimeError: reason='RESOURCE_HEADROOM_LOST'
                last_check=time.monotonic()
            if reason: break
            proc.join(timeout=min(.1,max(0.,seconds-elapsed)))
    except BaseException as error:
        reason='MONITOR_ERROR';monitor_error=error
    if reason and proc.is_alive():
        current=process_identity(proc.pid)
        if current is None or current["start_ticks"] != identity["start_ticks"]:
            raise RuntimeError('Child identity changed; refusing signal')
        proc.terminate(); proc.join(timeout=grace_s)
        if proc.is_alive():
            current=process_identity(proc.pid)
            if current and current['start_ticks']==identity['start_ticks']:
                if current['pgid']==proc.pid: os.killpg(proc.pid,signal.SIGKILL)
                else: proc.kill()
            proc.join(timeout=grace_s)
    proc.join()
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    if directory:
        atomic_json(Path(directory)/'WATCHDOG_ACCOUNTING.json',{
            'reason':reason,'child_identity':identity,'wall_s':time.monotonic()-start,
            'limit_s':seconds,'grace_s':grace_s,'query_wall_s':query_wall_s,
            'reaped_child_cpu_s':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            'observed_cpu_s_lower_bound':observed_cpu,'sampled_peak_rss_kib':peak or None,
            'exitcode':proc.exitcode,'gpu_allocation':False})
    if monitor_error is not None:raise RuntimeError("Parent monitor failed; own child was cancelled and charged") from monitor_error
    return reason is not None
